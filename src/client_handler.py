import io
import json
import selectors
import struct
import yaml
import hashlib
import yaml
import logging
from utils import encode_protocol, decode_protocol

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load configuration
yaml_path = "config.yaml"
with open(yaml_path, "r") as y:
    config = yaml.safe_load(y)

# Defaults
VERSION = config["version"]
DB_PATH = config["db_path"]
MIN_MESSAGE_LEN = config["min_message_len"]
MAX_MESSAGE_LEN = config["max_message_len"]

class Message:
    """ Message class for handling client-server communication using JSON encoding. Message is (fuzzily) equivalent to a client-stub.

    Methods:
    - _set_selector_events_mask(self, mode): Set selector to listen for events: mode is 'r', 'w', or 'rw'.
    - _read(self): Read data from socket.
    - _write(self): Write data to socket.
    - _json_encode(self, obj, encoding): Encode JSON object.
    - _json_decode(self, json_bytes, encoding): Decode JSON object.
    - _package_request(self, req): Package a request into a message.
    - _process_response(self): Process received response data.
    - _generate_action(self, opcode, status_code, data): Generate an action based on response data.
    - process_events(self, mask): Process events based on mask.
    - read(self): Read data from socket.
    - write(self): Write data to socket.
    - close(self): Close the connection.
    - queue_request(self): Queue a request for sending.
    - process_protoheader(self): Process protoheader from received buffer.
    - process_header(self): Process header from received buffer.
    - _hash_password(self, password): Hash a password using SHA-256.
    """
    def __init__(self, selector, sock, addr, request, incoming_queue=None):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self.request = request # Request to send
        self._recv_buffer = b""
        self._send_buffer = b""
        self._request_queued = False
        self._header_len = None
        self._header = None
        self.response = None # Response received
        # Incoming queue for processing responses, shared with client GUI
        self.incoming_queue = incoming_queue

    def _set_selector_events_mask(self, mode):
        """Set selector to listen for events: mode is 'r', 'w', or 'rw'."""
        if mode == "r":
            events = selectors.EVENT_READ
        elif mode == "w":
            events = selectors.EVENT_WRITE
        elif mode == "rw":
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
        else:
            logging.error(f"Invalid events mask: {mode}")
        self.selector.modify(self.sock, events, data=self)

    def _read(self):
        """Read data from socket."""
        try:
            # Should be ready to read
            data = self.sock.recv(4096)
        except BlockingIOError:
            # Resource temporarily unavailable (errno EWOULDBLOCK)
            pass
        else:
            if data:
                self._recv_buffer += data
            else:
                logging.info(f"Closing connection to {self.addr}")

    def _write(self):
        """Write data to socket."""
        if self._send_buffer:
            print(f"Sending {self._send_buffer!r} to {self.addr}")
            try:
                # Should be ready to write
                sent = self.sock.send(self._send_buffer)
            except BlockingIOError:
                # Resource temporarily unavailable (errno EWOULDBLOCK)
                pass
            else:
                self._send_buffer = self._send_buffer[sent:]

    def _json_encode(self, obj, encoding):
        """Encode JSON object."""
        return json.dumps(obj, ensure_ascii=False).encode(encoding)

    def _json_decode(self, json_bytes, encoding):
        """Decode JSON object."""
        tiow = io.TextIOWrapper(
            io.BytesIO(json_bytes), encoding=encoding, newline=""
        )
        obj = json.load(tiow)
        tiow.close()
        return obj

    def _package_request(
        self, req):
        """Package a request into a message."""
        # Encode content
        encoding = req["content_encoding"]
        content_bytes = self._json_encode(req["content"], encoding)
        # Encode header
        jsonheader = {
            # "byteorder": sys.byteorder,
            # "content_type": req['content_type'],
            "content_encoding": encoding,
            "content_length": len(content_bytes),
            "opcode": req["opcode"]
        }
        jsonheader_bytes = self._json_encode(jsonheader, encoding)
        # Encode protoheader and package message
        message_hdr = struct.pack(">H", VERSION) + struct.pack(">H", len(jsonheader_bytes))
        message = message_hdr + jsonheader_bytes + content_bytes

        return message
    
    def _process_response(self):
        """Process received response data."""
        # Check if request is fully received
        content_len = self._header["content_length"]
        if not len(self._recv_buffer) >= content_len: # TODO: exception
            return
        
        # Save data from receive buffer
        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]

        # Decode response data
        encoding = self._header["content_encoding"]
        self.response = self._json_decode(data, encoding)
        print(f"Received response {self.response!r} from {self.addr}")

        # Get opcode, status code, and data from self._header and self.response
        opcode = self._header.get("opcode")
        status_code = self.response.get("status_code")
        data = self.response.get("data")

        # Process response content
        self._generate_action(opcode, status_code, data)

    def _generate_action(self, opcode, status_code, data):
        """Queue an action based on response data."""
        self.incoming_queue.put({"opcode": opcode, "status_code": status_code, "data": data})

    def process_events(self, mask):
        """Process incoming events based on mask."""
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()

    def read(self):
        """Read and process data from socket."""
        # Clear previous read data
        self._header_len = None
        self._header = None
        self.response = None
        self._request_queued = False
        self._read()

        # Decode protoheader
        if self._header_len is None:
            self.process_protoheader()

        # Decode header and content
        if self._header_len is not None and self._header is None:
            self.process_header()

        if self._header and self.response is None:
            self._process_response()

    def write(self):
        """Write data to socket."""
        # Make sure there is a request to send
        if not self._request_queued:
            self.queue_request()
        
        self._write()

        if self._request_queued and not self._send_buffer:
            # Set selector to listen for read events, we're done writing.
            self._set_selector_events_mask("r")

    def close(self):
        """Close the connection."""
        logging.info(f"Closing connection to {self.addr}")
        try:
            self.selector.unregister(self.sock)
        except Exception as e:
            logging.error(f"Error: selector.unregister() exception for {self.addr}: {repr(e)}")

    def queue_request(self):
        """Queue a request to _send_buffer for sending."""
        message = self._package_request(self.request)
        self._send_buffer += message
        self._request_queued = True
        
    def process_protoheader(self):
        """Process protoheader from received buffer."""
        hdrlen = 2
        
        if len(self._recv_buffer) >= hdrlen:
            v = struct.unpack(
                ">H", self._recv_buffer[:hdrlen]
            )[0]
            if v != VERSION: 
                logging.error(f"Invalid protocol version: {v}")
            self._recv_buffer = self._recv_buffer[hdrlen:]


        if len(self._recv_buffer) >= hdrlen:
            self._header_len = struct.unpack(
                ">H", self._recv_buffer[:hdrlen]
            )[0]
            self._recv_buffer = self._recv_buffer[hdrlen:]

    def process_header(self):
        """Process header from received buffer."""
        hdrlen = self._header_len
        # Check if header is fully received
        if len(self._recv_buffer) >= hdrlen:
            self._header = self._json_decode(self._recv_buffer[:hdrlen], "utf-8")
            self._recv_buffer = self._recv_buffer[hdrlen:]
            # Validate header fields
            for reqhdr in (
                "content_length",
                "content_encoding",
                "opcode"
            ):
                if reqhdr not in self._header:
                    logging.error(f"Missing required header '{reqhdr}'.")
                
    def _hash_password(self, password):
        # Hash a password using SHA-256
        return hashlib.sha256(password)

class MessageCustom(Message):
    """Custom message class for handling client-server communication using a custom encoding protocol. Inherited from Message.
    
    Modified methods:
    - _package_request(self, req)
    - _process_response(self)
    - process_header(self)
    """
    def __init__(self, selector, sock, addr, request, incoming_queue=None):
        super().__init__(selector=selector, sock=sock, addr=addr, request=request, incoming_queue=incoming_queue)

    def _package_request(self, req):
        """Package a request into a custom format before sending."""
        encoding = req["content_encoding"]
        content_bytes = encode_protocol(req["content"]["args"])  # Serialize content

        # Encode header
        header = [encoding, len(content_bytes), req["opcode"]]
        header_bytes = encode_protocol(header)  # Serialize header

        # Encode protoheader and package message
        message_hdr = struct.pack(">H", VERSION) + struct.pack(">H", len(header_bytes))
        message = message_hdr + header_bytes + content_bytes

        return message

    def _process_response(self):
        """Process received response data."""
        content_len = self._header["content_length"]
        if len(self._recv_buffer) < content_len:
            return  # Incomplete data

        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]

        # Decode content using custom protocol
        decoded_data = decode_protocol(data)
        if not decoded_data:
            logging.error("Failed to decode response data.")

        # Extract status code and remaining response data
        status_code = decoded_data[0]
        response_data = decoded_data[1:]
        logging.info(f"Received response: status_code={status_code}, data={response_data}")

        opcode = self._header.get("opcode")
        self._generate_action(opcode, status_code, response_data)

    def process_header(self):
        """Process message header from received buffer."""
        hdrlen = self._header_len
        if len(self._recv_buffer) >= hdrlen and hdrlen != 0:
            # Read and decode header data
            header_data = self._recv_buffer[:hdrlen]
            self._recv_buffer = self._recv_buffer[hdrlen:]

            decoded_header = decode_protocol(header_data)
            if not decoded_header or len(decoded_header) < 3:
                logging.error("Failed to decode header data.")
                return

            self._header = {
                "content_encoding": decoded_header[0],
                "content_length": decoded_header[1],
                "opcode": decoded_header[2],
            }

            # Validate header fields
            for reqhdr in ("content_encoding", "content_length", "opcode"):
                if reqhdr not in self._header:
                    logging.error(f"Missing required header '{reqhdr}'.")