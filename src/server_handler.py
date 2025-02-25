import io
import json
import yaml
import selectors
import struct
import time
import ssl
import logging
from database import DatabaseHandler
from utils import encode_protocol, decode_protocol, ResponseCode, OpCode
import handler_pb2 as handler_pb2

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
    """
    Handles standard communication between the server and a client using JSON encoding. Message is (fuzzily) equivalent to a server-stub.

    Methods:
    - _set_selector_events_mask(self, mode): Set the selector to listen for events.
    - _read(self): Read incoming data from the client.
    - _write(self): Write outgoing data to the client.
    - _json_encode(self, obj, encoding): Encode a Python object as JSON.
    - _json_decode(self, json_bytes, encoding): Decode JSON bytes into a Python object.
    - _package_response(self, response): Package a response message for sending.
    - _process_request(self): Process the client request and generate a response.
    - _generate_action(self, opcode, args): Execute the requested action and return the result.
    - process_events(self, mask): Process events based on the mask.
    - read(self): Read and process incoming data from the client.
    - write(self): Write outgoing data to the client.
    - close(self): Close the connection.
    - process_protoheader(self): Process protoheader from received buffer.
    - process_header(self): Process header from received buffer.
    - process_content(self): Process content from received buffer.
    """
    def __init__(self, selector, sock, addr, db_path, active_clients={}):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self._recv_buffer = b""
        self._send_buffer = b""
        self._header_len = None
        self._header = None # Parsed header data
        self.request = None # Parsed request data
        self.response_created = False
        self.db = DatabaseHandler(DB_PATH)
        # Active clients mapping (username -> Message object)
        self.active_clients = active_clients

        logging.info(f"New connection established: {addr}")

    def _set_selector_events_mask(self, mode):
        """Set selector to listen for events: mode is 'r', 'w', or 'rw'."""
        if mode == "r":
            events = selectors.EVENT_READ
        elif mode == "w":
            events = selectors.EVENT_WRITE
        elif mode == "rw":
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
        else:
            raise ValueError(f"Invalid events mask mode {mode!r}.")
        self.selector.modify(self.sock, events, data=self)

    def _read(self):
        """Reads incoming data from the client socket."""
        try:
            # Should be ready to read
            data = self.sock.recv(4096)
        except BlockingIOError:
            # Resource temporarily unavailable (errno EWOULDBLOCK)
            pass
        except Exception as e:
            logging.error(f"Read error from {self.addr}: {e}")
            self.close()
        else:
            if data:
                self._recv_buffer += data
            else:
                # Socket closed, remove from active clients
                for username, client in list(self.active_clients.items()):
                    if client is self:
                        del self.active_clients[username]
                        logging.info(f"Removed {username} from active clients.")
                        break
                raise RuntimeError("Peer closed.")

    def _write(self):
        """Writes data from the send buffer to the client socket."""
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
                # Close when the buffer is drained. The response has been sent.
                if sent and not self._send_buffer:
                    pass

    def _json_encode(self, obj, encoding):
        return json.dumps(obj, ensure_ascii=False).encode(encoding)

    def _json_decode(self, json_bytes, encoding):
        tiow = io.TextIOWrapper(
            io.BytesIO(json_bytes), encoding=encoding, newline=""
        )
        obj = json.load(tiow)
        tiow.close()
        return obj

    def _package_response(self, response):
        """Encodes and packages the server response before sending (JSON format)."""
        # Encode response content
        content_bytes = self._json_encode(response, self._header["content_encoding"])
        # Encode response header
        jsonheader = self._header
        jsonheader["content_length"] = len(content_bytes)
        jsonheader_bytes = self._json_encode(jsonheader, self._header["content_encoding"])
        # Encode protoheader and package message
        message_hdr = struct.pack(">H",VERSION) + struct.pack(">H", len(jsonheader_bytes))
        message = message_hdr + jsonheader_bytes + content_bytes
        return message

    def _process_request(self):
        """Process client request and generate response."""
        # Get action and arguments
        opcode = self._header["opcode"]
        args = self.request.get("args",[])

        # Create response
        result = self._generate_action(opcode, args)
        status_code = result["status_code"]
        data = result.get("data", [])

        # Encode response as json or custom
        response = {"status_code": status_code, "data": data}
        message = self._package_response(response)
            
        # Load send buffer
        self.response_created = True
        self._send_buffer += message
        
    def _generate_action(self, opcode, args):
        """Execute the requested action and return the result.
        
        Args:
        - opcode: The operation code for the requested action.
        - args: The arguments for the requested action.

        Returns:
        - result: The result of the requested
            - "status_code": The status code of the operation.
            - "data": Optional List of data returned by the operation.
        """
        if opcode == OpCode.STARTING.value:
            result = {"status_code": ResponseCode.SUCCESS.value}
        elif opcode == OpCode.ACCOUNT_EXISTS.value:
            result = self.db.account_exists(args[0])
            # Parse result of account_exists, which is a bool
            if not result:
                result = {"status_code": ResponseCode.ACCOUNT_NOT_FOUND.value}
            else:
                result = {"status_code": ResponseCode.ACCOUNT_EXISTS.value} # TODO: cleanup
        elif opcode == OpCode.CREATE_ACCOUNT.value:
            print(args)
            result = self.db.create_account(*args)
        elif opcode == OpCode.LOGIN_ACCOUNT.value:
            result = self.db.login_account(*args)
            # Add to active clients if login successful
            if result["status_code"] == ResponseCode.SUCCESS.value:
                self.active_clients[args[0]] = self
        elif opcode == OpCode.LIST_ACCOUNTS.value:
            # List accounts based on search query
            if len(args) > 0:
                result = self.db.list_accounts("".join(args))
            else:
                result = self.db.list_accounts()
        elif opcode == OpCode.DELETE_ACCOUNT.value:
            result = self.db.delete_account(*args)
        elif opcode == OpCode.HOMEPAGE.value:
            result = self.db.fetch_homepage(*args)
        elif opcode == OpCode.READ_MSG_UNDELIVERED.value:
            result = self.db.fetch_messages_undelivered(*args)
        elif opcode == OpCode.READ_MSG_DELIVERED.value:
            result = self.db.fetch_messages_delivered(*args)
        elif opcode == OpCode.DELETE_MSG.value:
            result = self.db.delete_messages(*args)
        elif opcode == OpCode.MATCH.value:
            result = self.db.match_users(*args)
            print("RESULT   ", result)
        elif opcode == OpCode.SEND_MSG.value:
            sender = args[0]
            receiver = args[1]
            msg_content = args[2]
            # If receiver online: try sending immediately
            if receiver in self.active_clients:
                try:
                    # Insert message into database
                    result = self.db.insert_message(*args, round(time.time()), True)

                    # We have a Message object for the receiver
                    receiver_msg = self.active_clients[receiver]
                
                    # Construct a new header or payload for the receiver
                    new_args = [self.db.cursor.lastrowid] + args
                    response = {
                        "status_code": ResponseCode.SUCCESS.value,
                        "data": [(*new_args, round(time.time()), True)]
                    }
                    
                    # Temporarily update our opcode to "RECEIVE_MSG" 
                    old_opcode = self._header["opcode"]
                    self._header["opcode"] = OpCode.RECEIVE_MSG.value

                    # Build the message
                    packaged = self._package_response(response)
                    self._header["opcode"] = old_opcode

                    # Send data by appending to the receiver's buffer
                    receiver_msg._send_buffer += packaged
                    # Ensure the receiver is listening for EVENT_WRITE
                    receiver_msg._set_selector_events_mask("w")
                except Exception as e:
                    logging.error(f"Failed to send message: {e}")
                    result = self.db.insert_message(*args, round(time.time()), False)
            else:
                # If user not online, just store in DB
                self.db.insert_message(sender, receiver, msg_content,
                                       round(time.time()),
                                       False)
                result = {"status_code": ResponseCode.SUCCESS.value}
        else:
            with Exception as e:
                logging.error(f"Unknown opcode: {e}")
                result = {"status_code": ResponseCode.SUCCESS.value} #
        return result

    def process_events(self, mask):
        """Process read/write events. Entrypoint into the class. """
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()
    
    def read(self):
        """Handle incoming data and process response."""
        # Reset previous request info
        self.response_created = False
        self._header_len = None
        self._header = None
        self.request = None

        # Read in bytes
        self._read()

        # Decode protoheader: get request type
        if self._header_len is None:
            self.process_protoheader()
            
        # Decode header and content
        if self._header_len is not None and self._header is None:
            self.process_header()
                
        if self._header and self.request is None:
            self.process_content()
            
    def write(self):
        """Send queued request data."""
        # Make sure request is processed
        if self.request and not self.response_created:
            self._process_request()

        self._write()

        # Set selector to listen for read events, we're done writing.
        self._set_selector_events_mask("r")

    def close(self):
        """Unregister and close the socket."""
        # logging("Closing connection to {self.addr}")
        try:
            self.selector.unregister(self.sock)
        except Exception as e:
            logging.error(f"Error: selector.unregister() exception for {self.addr}: {e!r}")
        try:
            self.sock.close()
        except OSError as e:
            logging.error(f"Error: socket.close() exception for {self.addr}: {e!r}")
        finally:
            self.sock = None

    def process_protoheader(self):
        """Process protocol header"""
        hdrlen = 2
                
        # Get version
        if len(self._recv_buffer) >= hdrlen:
            v = struct.unpack(
                ">H", self._recv_buffer[:hdrlen]
            )[0]
            if v != VERSION: 
                logging.error(f"Unsupported version: {v}")
            self._recv_buffer = self._recv_buffer[hdrlen:]

        # Get header length
        if len(self._recv_buffer) >= hdrlen:
            self._header_len = struct.unpack(
                ">H", self._recv_buffer[:hdrlen]
            )[0]
            self._recv_buffer = self._recv_buffer[hdrlen:]

    def process_header(self):
        """Process message header from received buffer."""
        hdrlen = self._header_len

        if len(self._recv_buffer) >= hdrlen:
            # Read header data
            self._header = self._json_decode(self._recv_buffer[:hdrlen], "utf-8")
            self._recv_buffer = self._recv_buffer[hdrlen:]
            # Check header data
            for reqhdr in (
                "content_encoding",
                "content_length",
                "opcode"
            ):
                if reqhdr not in self._header:
                    logging.error(f"Missing required header '{reqhdr}'.")

    def process_content(self):
        """Process message content from received buffer."""
        # Check if request is fully received
        content_len = self._header["content_length"]
        if not len(self._recv_buffer) >= content_len:
            logging.error("Insufficient data for content.")
            return
        
        # Save data from receive buffer
        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]

        # Encode data as request
        encoding = self._header["content_encoding"]
        self.request = self._json_decode(data, encoding)
        print(f"Received request {self.request!r} from {self.addr}")
        
        # Set selector to listen for write events, we're done reading.
        self._set_selector_events_mask("w")

class MessageCustom(Message):
    """ Handles communication between the server and a client using a custom protocol. Inherited from Message. 
    
    Modified methods:
    - _package_response
    - _process_request
    - process_header
    - process_content
    """
    def __init__(self, selector, sock, addr, db_path, active_clients={}):
        """ Initialize the custom message handler. """
        super().__init__(selector, sock, addr, db_path, active_clients)

    def _package_response(self, response):
        """Custom response packaging using custom encode_protocol as a separator instead of JSON.
        
        Args:
        - response: The response to package.
            - status_code: The status code of the response.
            - data: Optional list of data returned by the operation.
        
        Returns:
        - message: The packaged response message
            -  proto_hdr: The protocol header
            -  message_hdr: The message header
            -  message: The message content
        """
        # Encode content
        content_data = [response["status_code"]] + response.get("data", [])
        content_bytes = encode_protocol(content_data)

        # Encode header in custom format
        header = [self._header['content_encoding'], len(content_bytes), self._header['opcode']]
        header_bytes = encode_protocol(header)

        # Encode protoheader and package message
        message_hdr = struct.pack(">H", VERSION) + struct.pack(">H", len(header_bytes))
        message = message_hdr + header_bytes + content_bytes
        return message

    def _process_request(self):
        """Process client request and generate response."""
        # Get action and arguments
        opcode = self._header["opcode"]
        args = self.request.get("args", [])

        # Create response
        result = self._generate_action(opcode, args)
        status_code = result["status_code"]
        data = result.get("data", [])

        # Encode response using custom format
        response = {"status_code": status_code, "data": data}
        message = self._package_response(response)

        # Load send buffer
        self.response_created = True
        self._send_buffer += message

    def process_header(self):
        """Custom header processing using decode_protocol instead of JSON."""
        hdrlen = self._header_len

        # Check if header is fully received
        if len(self._recv_buffer) >= hdrlen:
            try:
                # Decode header data
                encoding, content_length, opcode = decode_protocol(self._recv_buffer[:hdrlen])
                self._header = {
                    "content_encoding": encoding,
                    "content_length": content_length,
                    "opcode": opcode,
                }
                self._recv_buffer = self._recv_buffer[hdrlen:]
            except ValueError as e:
                logging.error(f"Error decoding header: {e}")

            # Check header fields   
            for reqhdr in ("content_encoding", "content_length", "opcode"):
                if reqhdr not in self._header:
                    logging.error(f"Missing required header '{reqhdr}'.")

    def process_content(self):
        """Custom processing of message content using decode_protocol."""

        # Check if request is fully received
        content_len = self._header["content_length"]
        if len(self._recv_buffer) < content_len:
            return

        # Extract and decode content
        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]
        request = decode_protocol(data)

        # Save request data
        self.request = {"args": request}
        logging.info(f"Received request {self.request!r} from {self.addr}")

        # Set selector to listen for write events, indicating readiness
        self._set_selector_events_mask("w")