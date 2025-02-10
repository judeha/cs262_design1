import io
import json
import selectors
import struct
import sys
from response_codes import ResponseCode, RESPONSE_MESSAGES  

version = 1 # TODO: put in config file, change from >H if float

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

        # Process response content
        self._generate_action()

        # Close when response has been processed
        self.close()

    def _generate_action(self):
        # Get opcode, status code, and data from self._header and self.response
        opcode = self._header.get("opcode")
        status_code = self.response.get("status_code")
        data = self.response.get("data")

        # TODO: enforce I/O
        print(RESPONSE_MESSAGES.get(ResponseCode(status_code), "Unknown response code"))
        if status_code != ResponseCode.SUCCESS.value:
            pass
            # TODO: stay on the page
        else:
            if opcode == "create_account":
                pass
                # TODO: display login page
            elif opcode == "login_account":
                print("Here are your messages: ", data[1:])
                print("You have ", data[0], " unread messages.")
                # TODO: display homepage
            elif opcode == "delete_account":
                pass
                # TODO: display create account page
            elif opcode == "read_msg_delivered":
                print("Here are your messages: ", data[1:])
                print("You have ", data[0], " unread messages.")
                # TODO: display homepage
            elif opcode == "read_msg_undelivered":
                print("Here are your messages: ", data[1])
                print("You have ", data[0], " unread messages.")
                # TODO: display homepage
            elif opcode == "delete_msg":
                pass
                # TODO: display homepage
            elif opcode == "list_all_accounts":
                print("Here are all the accounts: ", [data])
                # TODO: display accounts
            elif opcode == "homepage":
                print("Here are your messages: ", data[1:])
                print("You have ", data[0], " unread messages.")
                # TODO: display homepage
            elif opcode == "send_msg":
                pass
                # TODO: display homepage
            elif opcode == "receive_msg":
                print("You have a new message. Here are your messages: ", data)
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

        # Decode header and content
        if self._header_len is not None and self._header is None:
            self.process_header()

        if self._header and self.response is None:
            self.process_content()

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
                
    def process_content(self):
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
        self.close()