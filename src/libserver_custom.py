import io
import json
import selectors
import struct
import sys
import ast
import datetime
from enum import Enum
from response_codes import ResponseCode
from database import DatabaseHandler

version = 1.0

class Message:
    def __init__(self, selector, sock, addr):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self._recv_buffer = b""
        self._send_buffer = b""
        self._header_len = None
        self._header = None
        self.request = None
        self.response_created = False
        self.db = DatabaseHandler() # TODO: should we move this outside?
        self.active_clients = {} # TODO: in-session tracking improved?
        self.is_custom = False

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
                # Close when the buffer is drained. The response has been sent.
                if sent and not self._send_buffer:
                    self.close()

    def _json_encode(self, obj, encoding):
        return json.dumps(obj, ensure_ascii=False).encode(encoding)

    def _json_decode(self, json_bytes, encoding):
        tiow = io.TextIOWrapper(
            io.BytesIO(json_bytes), encoding=encoding, newline=""
        )
        obj = json.load(tiow)
        tiow.close()
        return obj

    def _custom_encode(self, obj, encoding):
        #TODO encode the custom action to send to tkinter...
        pass

    def _custom_decode(self, obj, encoding):
        return obj.decode(encoding)
        pass

    def _stub_server_package(
        self, response
    ):
        # Encode content
        content_bytes = self._json_encode(response, self._header["content_encoding"])
        # Encode header
        jsonheader = self._header
        jsonheader["content_length"] = len(content_bytes)
        jsonheader_bytes = self._json_encode(jsonheader, self._header["content_encoding"])
        # Encode protoheader and package message
        message_hdr = struct.pack(">H",version), struct.pack(">H", len(jsonheader_bytes))
        message = message_hdr + jsonheader_bytes + content_bytes
        return message

    def _create_custom_message(self, response):
        # Encode content
        content = response["result"]["status_code"] + response["result"].get("data", [])
        content_str = str.join("|", content)
        content_bytes = bytes(content_str, self._header["content_encoding"])
        # Encode header
        jsonheader = self._header
        jsonheader["content_length"] = len(content_bytes)
        jsonheader_str = str.join("|", [jsonheader["byteorder"],
                                        jsonheader["content_type"],
                                        jsonheader["content_encoding"],
                                        str(jsonheader["content_length"])])
        jsonheader_bytes = bytes(jsonheader_str, self._header["content_encoding"])
        # Encode protoheader and package message
        message_hdr = struct.pack(">H", self.is_custom) + struct.pack(">H", len(jsonheader_bytes))
        message = message_hdr + jsonheader_bytes + content_bytes
        return message

    def _create_response_content(self):
        args = self.request.get("args")
        # TODO: catch input exceptions here
        opcode = self._header["opcode"]
        if opcode == "create_account":
            result = self.db.create_account(*args)
        elif opcode == "login_account":
            result = self.db.login_account(*args)
            # Add to active clients
            if result["status_code"] == ResponseCode.SUCCESS.value:
                pass
                # self.active_clients[result["data"]["username"]] = self.sock
        elif opcode == "list_accounts":
            result = self.db.list_accounts()
        elif opcode == "delete_account":
            result = self.db.delete_account(*args)
        elif opcode == "homepage":
            result = self.db.fetch_homepage(*args)
        elif opcode == "read_msg_undelivered":
            result = self.db.fetch_messages_undelivered(*args)
        elif opcode == "read_msg_delivered":
            result = self.db.fetch_messages_delivered(*args)
        elif opcode == "delete_msg":
            result = self.db.delete_messages(*args)
        elif opcode == "send_msg":
            # Check if receiver exists
            if not self.db.account_exists(args[1]):
                result = {"status_code": ResponseCode.ACCOUNT_NOT_FOUND.value}
                return result
            # TODO: Check if receiver is online. verify sending
            msg_sent = True
            if not msg_sent:
                result = {"status_code": ResponseCode.MESSAGE_SEND_FAILURE.value}
                delivered = False
            else:
                delivered = True
            # Insert message into database
            timestamp = round(datetime.datetime.now().microsecond)
            result = self.db.insert_message(*self.request, timestamp, delivered)
        elif opcode == "receive_msg":
            pass
        else:
            pass
        response = result["status_code"], result.get("data", [])
        return response

    def process_events(self, mask):
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()

    def read(self):
        # Read in bytes
        self._read()

        # Decode protoheader: get request type
        if self._header_len is None:
            self.process_protoheader()
            
        # Decode header and content
        if self._header_len is not None and self._header is None:
            self.process_header()
        
        if self._header and self.request is None:
            self.process_request()
            
    def write(self):
        if self.request and not self.response_created:
            self.create_response()

        self._write()

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
            # NOTE: new
            if hasattr(self, 'active_clients'):
                for username, client_sock in list(self.active_clients.items()):
                    if client_sock == self.sock:
                        del self.active_clients[username]
            self.sock = None

    def process_protoheader(self):
        # Get header length
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
                # "content_type",
                "content_encoding",
                "content_length",
                "opcode"
            ):
                if reqhdr not in self._header:
                    raise ValueError(f"Missing required header '{reqhdr}'.")

    def process_request(self):
        # Check if request is fully received
        content_len = self._header["content_length"]
        if not len(self._recv_buffer) >= content_len: # TODO: exception
            return
        
        # Save data from receive buffer
        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]

        # Encode data as request
        encoding = self._header["content_encoding"]
        self.request = self._json_decode(data, encoding)
        print(f"Received request {self.request!r} from {self.addr}")
        print(f"Request type: {type(self.request)}")
        
        # Set selector to listen for write events, we're done reading.
        self._set_selector_events_mask("w")

    def process_custom_header(self):
        hdrlen = self._header_len
        if len(self._recv_buffer) >= hdrlen and hdrlen!=0:
            # Read header data
            data = self._recv_buffer[:hdrlen]
            # Decode data
            hdr = data.decode("utf-8").split("|")
            self._header = {
                "byteorder": hdr[0],
                "content_type": hdr[1],
                "content_encoding": hdr[2],
                "content_length": int(hdr[3])
            }
            self._recv_buffer = self._recv_buffer[hdrlen:]
        # TODO: catch exception
    
    def process_custom_request(self):
        # Check if request is fully received
        content_len = self._header["content_length"]
        if not len(self._recv_buffer) >= content_len: # TODO: exception
            return
        
        # Save data from receive buffer
        encoding = self._header["content_encoding"]
        data = self._recv_buffer[:content_len].decode(encoding)
        self._recv_buffer = self._recv_buffer[content_len:]
        
        # Decode data as request
        req = data.split("|")
        self.request = {
            "opcode": req[0],
            "args": req[1:-1]
        }

        print(f"Received request {self.request!r} from {self.addr}")
        print(f"Request type: {type(self.request)}")
        
        # Set selector to listen for write events, we're done reading.
        self._set_selector_events_mask("w")

    def create_response(self):
        # Create response
        result = self._create_response_content()

        # Encode response as json or custom
        status_code, data = result
        response = {"status_code": status_code, "data": data}
        message = self._stub_server_package(response)
        # else:
        #     message = self._create_custom_message(response)
            
        # Load send buffer
        self.response_created = True
        self._send_buffer += message