import io
import json
import selectors
import struct
import sys
from response_codes import ResponseCode, RESPONSE_MESSAGES  

"""
Request packaged as a message:
protoheader: 00 (length) + 01 (type)
jsonheader: {
    "byteorder": "big",
    "content_type": "json",
    "content_encoding": "utf-8",
    "content_length": 123
}
content: {
    "opcode": "create_account",
    "args": ["test_user", "password123"]
}

Response packaged as a message:
protoheader: 00 (length) + 01 (type)
jsonheader: {
    "byteorder": "big",
    "content_type": "json",
    "content_encoding": "utf-8",
    "content_length": 123
}
content: {
    "opcode": "create_account",
    "result": {
        "status_code": 0,
        "data": {"field": "value"}
    }
}
"""
class Message:
    def __init__(self, selector, sock, addr, request):
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
        pass

    def _custom_decode(self, obj, encoding):
        pass

    def _create_json_message(
        self, req):
        # Encode content
        content_bytes = self._json_encode(req["content"], req["content_encoding"])
        # Encode header
        jsonheader = {
            "byteorder": sys.byteorder,
            "content_type": req['content_type'],
            "content_encoding": req['content_encoding'],
            "content_length": len(content_bytes),
        }
        jsonheader_bytes = self._json_encode(jsonheader, req["content_encoding"])
        # Encode protoheader and pakcage message
        message_hdr = struct.pack(">H", len(jsonheader_bytes))
        message = message_hdr + jsonheader_bytes + content_bytes
        return message

    def _create_custom_message(self, req):
        pass
    
    def _process_response_content(self):
        content = self.response
        opcode = content.get("opcode")
        status_code = content['result'].get("status_code")
        print(RESPONSE_MESSAGES.get(ResponseCode(status_code), "Unknown response code"))
        if status_code != ResponseCode.SUCCESS.value:
            pass
            # TODO: stay on the page
        else:
            if opcode == "create_account":
                pass
                # TODO: display login page
            elif opcode == "login_account":
                print("Here are your messages: ", content.get("data").get("messages"))
                print("You have ", content.get("data").get("count"), " unread messages.")
                # TODO: display homepage
            elif opcode == "delete_account":
                pass
                # TODO: display create account page
            elif opcode == "read_msg_delivered":
                print("Here are your messages: ", content.get("data").get("messages"))
                print("You have ", content.get("data").get("count"), " unread messages.")
                # TODO: display homepage
            elif opcode == "read_msg_undelivered":
                print("Here are your messages: ", content.get("data").get("messages"))
                print("You have ", content.get("data").get("count"), " unread messages.")
                # TODO: display homepage
            elif opcode == "delete_msg":
                pass
                # TODO: display homepage
            elif opcode == "list_all_accounts":
                print("Here are all the accounts: ", content.get("data").get("accounts"))
                # TODO: display accounts
            elif opcode == "homepage":
                print("Here are your messages: ", content.get("data").get("messages"))
                print("You have ", content.get("data").get("count"), " unread messages.")
                # TODO: display homepage
            elif opcode == "send_msg":
                pass
                # TODO: display homepage
            elif opcode == "receive_msg":
                print("You have a new message. Here are your messages: ", content.get("data").get("messages"))
                # TODO: display homepage UNLESS they are viewing all the account lists. hannah pls decide
            else:
                print("Unknown opcode")

    def process_events(self, mask):
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()

    def read(self):
        self._read()

        # Decode protoheader: get request type
        if self._header_len is None:
            self.process_protoheader()

        # Decode header
        if self.is_json:
            if self._header_len is not None and self._header is None:
                self.process_json_header()
        else:
            if self._header_len is not None and self._header is None:
                self.process_custom_header()

        # Decode content 
        if self._header and self.response is None:
            self.process_response()

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

        try:
            self.sock.close()
        except OSError as e:
            print(f"Error: socket.close() exception for {self.addr}: {e!r}")
        finally:
            # Delete reference to socket object for garbage collection
            self.sock = None

    def process_protoheader(self):
        hdrlen = 2
        if len(self._recv_buffer) >= hdrlen:
            self._header_len = struct.unpack(
                ">H", self._recv_buffer[:hdrlen]
            )[0]
            self._recv_buffer = self._recv_buffer[hdrlen:]
        # TODO: handle is_json
        self.is_json = True

    def process_json_header(self):
        hdrlen = self._header_len
        if len(self._recv_buffer) >= hdrlen:
            self._header = self._json_decode(self._recv_buffer[:hdrlen], "utf-8")
            self._recv_buffer = self._recv_buffer[hdrlen:]
            for reqhdr in (
                "byteorder",
                "content_length",
                "content_type",
                "content_encoding",
            ):
                if reqhdr not in self._header:
                    raise ValueError(f"Missing required header '{reqhdr}'.")

    def process_response(self):
        # Check if request is fully received
        content_len = self._header["content_length"]
        if not len(self._recv_buffer) >= content_len: # TODO: exception
            return
        
        # Save data from receive buffer
        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]

        # Decode response data
        if self._header["content_type"] == "json":
            encoding = self._header["content_encoding"]
            self.response = self._json_decode(data, encoding)
        else:
            self.response = self._custom_decode(data, encoding)
        print(f"Received response {self.response!r} from {self.addr}")

        # Process response content
        self._process_response_content()

        # Close when response has been processed
        self.close()

    def queue_request(self):
        # print("PRE REQUEST", self.request)
        if self.is_json:
            message = self._create_json_message(self.request)
        else:
            message = self._create_custom_message(self.request)
        # print("POST REQUEST", message)
        self._send_buffer += message
        self._request_queued = True