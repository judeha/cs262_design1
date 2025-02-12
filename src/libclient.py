import io
import json
import selectors
import struct
import yaml
import sys
import tkinter as tk
import threading
import yaml
import client
from codes import ResponseCode, RESPONSE_MESSAGES, OpCode, OPCODE_MESSAGES 

#Read config file
yaml_path = "config.yaml"
with open(yaml_path) as y:
    config_dict = yaml.safe_load(y)

version = config_dict["version"]
key = config_dict["key"]
db_path = config_dict["db_path"]


class Message:
    def __init__(self, selector, sock, addr, queue):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self.queue = queue
        self.request = None
        self._recv_buffer = b""
        self._send_buffer = b""
        self._request_queued = False
        self._header_len = None
        self._header = None
        self.response = None
        self.events = selectors.EVENT_READ | selectors.EVENT_WRITE

    ## ORIGINAL FUNCTIONS
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
        # print(f"Modifying selector for {self.sock} with mode {mode}")


    def _read(self):
        print("_REadinggggggggg")
        
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
             # Should be ready to write
            if self.sock is None:
                raise RuntimeError("Socket is None before writing")
            if self.sock.fileno() == -1:
                raise RuntimeError("Socket is closed before writing")
            try:
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
        print("IN PACKAGE REQUEST", req)

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

        print("IN PROCESS RESPONSE")
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

        self.queue.put(self.response)

        # Get opcode, status code, and data from self._header and self.response
        opcode = self._header.get("opcode")
        status_code = self.response.get("status_code")
        data = self.response.get("data")

        # print("here is the info:", opcode, status_code, data)
        # print("HALLELUIGHA Got the status and opcode and everything")

        # Process response content
        # self._generate_action(opcode, status_code, data)

        # Close when response has been processed
        # self.close() # TODO: fix

    def _generate_action(self, opcode, status_code, data):

        print("IN GENERATE ACTION")

        pass
        

    def process_events(self, mask):
        print("IN PROCESS EVENTS")

        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()

    def read(self):
        print("IN READ")

        self._read()

        # Decode protoheader: get request type
        if self._header_len is None:
            self.process_protoheader()

        # Decode header and content
        if self._header_len is not None and self._header is None:
            self.process_header()

        if self._header and self.response is None:
            self.process_content()

    def write(self):
        print("IN WRITE")

        if not self.request:
            print("No request to send, skipping write.")
            return  # Do nothing if there's no r

        if not self._request_queued:
            self.queue_request(self.request)
        
        print(f"🚀 Sending request: {self._send_buffer!r}")

        self._write()

        print("SUCCESSFULLY SENT")

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

        try:
            self.sock.close()
        except OSError as e:
            print(f"Error: socket.close() exception for {self.addr}: {e!r}")
        finally:
            # Delete reference to socket object for garbage collection
            self.sock = None

    def queue_request(self, request):
        print("IN QUEUE REQUEST")
        self.request = request 
        message = self._package_request(request)
        self._send_buffer += message
        self._request_queued = True
        self._set_selector_events_mask("rw")
        print("Queue request done!")
        
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
                
    def process_content(self):
        print("IN PROCESS CONTENT")

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

        # Process response content
        self._process_response()

        # Close when response has been processed
        # self.close()



    