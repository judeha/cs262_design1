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
        self.is_json = True

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

    def _create_json_message(
        self, response
    ):
        # Encode content
        content_bytes = self._json_encode(response, self._header["content_encoding"])
        # Encode header
        jsonheader = self._header
        jsonheader["content_length"] = len(content_bytes)
        jsonheader_bytes = self._json_encode(jsonheader, self._header["content_encoding"])
        # Encode protoheader and package message
        message_hdr = struct.pack(">H", len(jsonheader_bytes))
        message = message_hdr + jsonheader_bytes + content_bytes
        return message

    def _create_custom_message(self, response):
        pass

    def _create_response_content(self):
        # TODO: catch input exceptions here
        opcode = self.request.get("opcode")
        if opcode == "create_account":
            result = self.db.create_account(*self.request.get("args"))
        elif opcode == "login_account":
            result = self.db.login_account(*self.request.get("args"))
            # Add to active clients
            if result["status_code"] == ResponseCode.SUCCESS.value:
                pass
                # self.active_clients[result["data"]["username"]] = self.sock
        elif opcode == "list_accounts":
            result = self.db.list_accounts()
        elif opcode == "delete_account":
            result = self.db.delete_account(*self.request.get("args"))
        elif opcode == "homepage":
            result = self.db.fetch_homepage(*self.request.get("args"))
        elif opcode == "read_msg_undelivered":
            result = self.db.fetch_messages_undelivered(*self.request.get("args"))
        elif opcode == "read_msg_delivered":
            result = self.db.fetch_messages_delivered(*self.request.get("args"))
        elif opcode == "delete_msg":
            result = self.db.delete_messages(*self.request.get("args"))
        elif opcode == "send_msg":
            # Check if receiver exists
            if not self.db.account_exists(self.request.get("args")[1]):
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
            result = self.db.insert_message(*self.request.get("args"), timestamp, delivered)
        elif opcode == "receive_msg":
            pass
        else:
            pass
        response = {"opcode": opcode, "result": result}
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
        if self.is_json:
            if self._header_len is not None and self._header is None:
                self.process_jsonheader()
            
            if self._header and self.request is None:
                self.process_json_request()
        else:
            if self._header_len is not None and self._header is None:
                self.process_custom_header()
            
            if self._header and self.request is None:
                self.process_custom_request()
            
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
        #Process proto header
        hdrlen = 2
        if len(self._recv_buffer) >= hdrlen:
            self._header_len = struct.unpack(
                ">H", self._recv_buffer[:hdrlen]
            )[0]
            self._recv_buffer = self._recv_buffer[hdrlen:]
        # TODO: handle is_json

    def process_jsonheader(self):
        hdrlen = self._header_len
        if len(self._recv_buffer) >= hdrlen:
            self._header = self._json_decode(self._recv_buffer[:hdrlen], "utf-8")
            self._recv_buffer = self._recv_buffer[hdrlen:]
            for reqhdr in (
                "byteorder",
                "content_type",
                "content_encoding",
                "content_length",
            ):
                if reqhdr not in self._header:
                    raise ValueError(f"Missing required header '{reqhdr}'.")

    def process_json_request(self):
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
        pass
    
    def process_custom_request(self):
        pass

    def create_response(self):
        # Create response
        response = self._create_response_content()

        # Encode response as json or custom
        if self._header["content_type"] == "json": # NOTE: type may be a redundant field
            message = self._create_json_message(response)
        else:
            message = self._create_custom_message(response)
            
        # Load send buffer
        self.response_created = True
        self._send_buffer += message