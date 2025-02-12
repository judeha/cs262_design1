import io
import json
import selectors
import struct
import yaml
import sys
import tkinter as tk
import threading
import hashlib
# import yaml
from codes import OpCode 

# Read config file
yaml_path = "config.yaml"
with open(yaml_path) as y:
    config_dict = yaml.safe_load(y)
version = config_dict["version"]
key = config_dict["key"]
db_path = config_dict["db_path"]

class Message:
    def __init__(self, selector, sock, addr, request, incoming_queue=None):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self.request = request
        self._recv_buffer = b""
        self._send_buffer = b""
        self._request_queued = False
        self._header_len = None
        self._header = None
        self.response = None
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
            raise ValueError(f"Invalid events mask mode {mode!r}.")
        self.selector.modify(self.sock, events, data=self)

    def _read(self):
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
                raise RuntimeError("Peer closed.")

    def _write(self):
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
        return json.dumps(obj, ensure_ascii=False).encode(encoding)

    def _json_decode(self, json_bytes, encoding):
        tiow = io.TextIOWrapper(
            io.BytesIO(json_bytes), encoding=encoding, newline=""
        )
        obj = json.load(tiow)
        tiow.close()
        return obj

    def _package_request(
        self, req):
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
        message_hdr = struct.pack(">H", version) + struct.pack(">H", len(jsonheader_bytes))
        message = message_hdr + jsonheader_bytes + content_bytes
        return message
    
    def _process_response(self):
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

        # Close when response has been processed
        # self.close() # TODO: fix

    def _generate_action(self, opcode, status_code, data):
        self.incoming_queue.put({"opcode": opcode, "status_code": status_code, "data": data})

    def process_events(self, mask):
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()

    def read(self):
        self._header_len = None
        self._header = None
        self.response = None
        self._request_queued = False
        self._read()

        # Decode protoheader: get request type
        if self._header_len is None:
            self.process_protoheader()

        # Decode header and content
        if self._header_len is not None and self._header is None:
            self.process_header()

        if self._header and self.response is None:
            self._process_response()

    def write(self):
        if not self._request_queued:
            self.queue_request()
        
        self._write()

        if self._request_queued and not self._send_buffer:
            # Set selector to listen for read events, we're done writing.
            self._set_selector_events_mask("r") # TODO: why doesn't this keep the connection open?

    def close(self):
        print(f"Closing connection to {self.addr}")
        try:
            self.selector.unregister(self.sock)
        except Exception as e:
            print(
                f"Error: selector.unregister() exception for "
                f"{self.addr}: {e!r}"
            )

    def queue_request(self):
        message = self._package_request(self.request)
        self._send_buffer += message
        self._request_queued = True
        
    def process_protoheader(self):
        hdrlen = 2
        
        if len(self._recv_buffer) >= hdrlen:
            v = struct.unpack(
                ">H", self._recv_buffer[:hdrlen]
            )[0]
            if v != version: 
                raise ValueError(f"Unsupported version: {v}")
            self._recv_buffer = self._recv_buffer[hdrlen:]


        if len(self._recv_buffer) >= hdrlen:
            self._header_len = struct.unpack(
                ">H", self._recv_buffer[:hdrlen]
            )[0]
            self._recv_buffer = self._recv_buffer[hdrlen:]

    def process_header(self):
        hdrlen = self._header_len
        if len(self._recv_buffer) >= hdrlen:
            self._header = self._json_decode(self._recv_buffer[:hdrlen], "utf-8")
            self._recv_buffer = self._recv_buffer[hdrlen:]
            for reqhdr in (
                # "byteorder",
                "content_length",
                # "content_type",
                "content_encoding",
                "opcode"
            ):
                if reqhdr not in self._header:
                    raise ValueError(f"Missing required header '{reqhdr}'.")
                
    def _hash_password(self, password):
        return hashlib.sha256(password)

class MessageCustom:
    def __init__(self, selector, sock, addr, request, incoming_queue=None):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self.request = request
        self._recv_buffer = b""
        self._send_buffer = b""
        self._request_queued = False
        self._header_len = None
        self._header = None
        self.response = None
        self.incoming_queue = incoming_queue

    def _set_selector_events_mask(self, mode):
        """Set selector to listen for events: mode is 'r', 'w', or 'rw'."""
        events = {
            "r": selectors.EVENT_READ,
            "w": selectors.EVENT_WRITE,
            "rw": selectors.EVENT_READ | selectors.EVENT_WRITE,
        }.get(mode, None)

        if events is None:
            raise ValueError(f"Invalid events mask mode {mode!r}.")
        
        self.selector.modify(self.sock, events, data=self)

    def _read(self):
        try:
            data = self.sock.recv(4096)  # Read incoming data
        except BlockingIOError:
            pass  # Non-blocking mode: No data available yet
        else:
            if data:
                self._recv_buffer += data
            else:
                raise RuntimeError("Peer closed.")

    def _write(self):
        if self._send_buffer:
            try:
                sent = self.sock.send(self._send_buffer)  # Send pending data
            except BlockingIOError:
                pass  # No data sent, socket is busy
            else:
                self._send_buffer = self._send_buffer[sent:]

    def _package_request(self, req):
        """Package a request into a custom format before sending."""
        encoding = req["content_encoding"]
        content_str = "|".join(map(str, req["content"]["args"]))  # Serialize content
        content_bytes = content_str.encode(encoding)

        # Encode header
        jsonheader = f"{encoding}|{len(content_bytes)}|{req['opcode']}"
        jsonheader_bytes = jsonheader.encode(encoding)

        # Encode protoheader and package message
        message_hdr = struct.pack(">H", version) + struct.pack(">H", len(jsonheader_bytes))
        message = message_hdr + jsonheader_bytes + content_bytes

        return message

    def _process_response(self):
        """Process received response data."""
        content_len = self._header["content_length"]
        if len(self._recv_buffer) < content_len:
            return  # Incomplete data

        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]

        encoding = self._header["content_encoding"]
        response_str = data.decode(encoding)

        response_parts = response_str.split("|")

        status_code = int(response_parts[0])  # First part is status code
        data = response_parts[1:]  # Remaining parts are data

        print(f"Received response {response_parts!r} from {self.addr}")

        opcode = self._header.get("opcode")

        self._generate_action(opcode, status_code, data)

    def _generate_action(self, opcode, status_code, data):
        """Sends processed response to the incoming queue."""
        if self.incoming_queue:
            # Special parsing for messages and accounts
            self.incoming_queue.put({"opcode": opcode, "status_code": status_code, "data": data})

    def process_events(self, mask):
        """Process read/write events."""
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()

    def read(self):
        """Handle incoming data and process response."""
        self._header_len = None
        self._header = None
        self.response = None
        self._request_queued = False

        self._read()

        if self._header_len is None:
            self.process_protoheader()

        if self._header_len is not None and self._header is None:
            self.process_header()

        print("HEADER", self._header)
        if self._header and self.response is None:
            self._process_response()

    def write(self):
        """Send queued request data."""
        if not self._request_queued:
            self.queue_request()
        
        self._write()

        if self._request_queued and not self._send_buffer:
            self._set_selector_events_mask("r")  # Switch to read mode

    def close(self):
        """Unregister and close the socket."""
        print(f"Closing connection to {self.addr}")
        try:
            self.selector.unregister(self.sock)
        except Exception as e:
            print(f"Error: selector.unregister() exception for {self.addr}: {e!r}")
        try:
            self.sock.close()
        except OSError as e:
            print(f"Error: socket.close() exception for {self.addr}: {e!r}")
        finally:
            self.sock = None

    def queue_request(self):
        """Queue request for sending."""
        message = self._package_request(self.request)
        self._send_buffer += message
        self._request_queued = True

    def process_protoheader(self):
        """Process protocol header."""
        hdrlen = 2
        
        if len(self._recv_buffer) >= hdrlen:
            v = struct.unpack(">H", self._recv_buffer[:hdrlen])[0]
            if v != version: 
                raise ValueError(f"Unsupported version: {v}")
            self._recv_buffer = self._recv_buffer[hdrlen:]

        if len(self._recv_buffer) >= hdrlen:
            self._header_len = struct.unpack(">H", self._recv_buffer[:hdrlen])[0]
            self._recv_buffer = self._recv_buffer[hdrlen:]

    def process_header(self):
        """Process message header from received buffer."""
        hdrlen = self._header_len
        if len(self._recv_buffer) >= hdrlen and hdrlen != 0:
            # Read header data
            data = self._recv_buffer[:hdrlen]
            # Decode data
            hdr = data.decode("utf-8").split("|")
            self._header = {
                "content_encoding": hdr[0],
                "content_length": int(hdr[1]),
                "opcode": int(hdr[2])
            }
            self._recv_buffer = self._recv_buffer[hdrlen:]

            # Validate header fields
            for reqhdr in ("content_length", "content_encoding", "opcode"):
                if reqhdr not in self._header:
                    raise ValueError(f"Missing required header '{reqhdr}'.")

    def _hash_password(self, password):
        """Hashes a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()