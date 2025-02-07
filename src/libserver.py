import io
import json
import selectors
import struct
import sys
import ast

request_search = {
    "morpheus": "Follow the white rabbit. \U0001f430",
    "ring": "In the caves beneath the Misty Mountains. \U0001f48d",
    "\U0001f436": "\U0001f43e Playing ball! \U0001f3d0",
}


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

    def _create_message(
        self, *, content_bytes, content_type, content_encoding
    ):
        jsonheader = {
            "byteorder": sys.byteorder,
            "content-type": content_type,
            "content-encoding": content_encoding,
            "content-length": len(content_bytes),
        }
        jsonheader_bytes = self._json_encode(jsonheader, "utf-8")
        message_hdr = struct.pack(">H", len(jsonheader_bytes))
        message = message_hdr + jsonheader_bytes + content_bytes
        return message

    def _create_response_json_content(self):
        action = self.request.get("action")
        if action == "search":
            query = self.request.get("value")
            answer = request_search.get(query) or f"No match for '{query}'."
            content = {"result": answer}
        else:
            content = {"result": f"Error: invalid action '{action}'."}
        content_encoding = "utf-8"
        response = {
            "content_bytes": self._json_encode(content, content_encoding),
            "content_type": "text/json",
            "content_encoding": content_encoding,
        }
        return response

    def _create_response_binary_content(self):
        """
        1. retrieve opcode.
        2. if else
        3. action - pass for now
        4. return success messages
        """
        # TODO: change to not using ast later
        # TODO: separate file for wire protocol + separate config
        opcode = self.request.get("content-opcode")
        if opcode == "create_account":
            response = str(dict(
                status="success",
                data="your username is..."
            ))
        elif opcode == "login_account":
            response = str(dict(
                status="success",
                data="here are all your messages..."
            ))
        elif opcode == "list_accounts":
            response = str(
                dict(
                    status="success",
                    data="here are all the accounts..."
                )
            )
        elif opcode == "send_message":
            response = str(
                dict(
                    status="success",
                    data="message sent..."
                )
            )
        elif opcode == "show_new_message": # NOTE: show me the next 5
            response = str(
                dict(
                    status="success",
                    data="here are your seven new messages..."
                )
            )
        elif opcode == "delete_message":
            response = str(
                dict(
                    status="success",
                    data="message deleted..."
                )
            )
        elif opcode == "delete_account":
            response = str(
                dict(
                    status="success",
                    data="account deleted..."
                )
            )
        elif opcode == "go_home":
            response = str(
                dict(
                    status="success",
                    data="here are all your messages"
                )
            )
        else:
            response = str(
                dict(
                    status="error",
                    data="invalid opcode..."
                )
            )


        # response = {
        #     "content_bytes": b"First 10 bytes of request: "
        #     + self.request[:10],
        #     "content_type": "binary/custom-server-binary-type",
        #     "content_encoding": "binary",
        # }
        return response

    def process_events(self, mask):
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()

    def read(self):
        self._read()

        #TODO: Refactor. Simplify branching

        if self._header_len is None:
            self.process_protoheader()
        
        print(f"PROTO: {self.is_json} {self._header_len}")
    
        if self.is_json:
            if self._header_len is not None:
                if self._header is None:
                    self.process_json_header()
            
            print(f"HEADER: {self._header}")

            if self._header:
                if self.request is None:
                    self.process_json_request()
            
            print(f"CONTENT: {self.request}")
        else:
            if self._header_len is not None:
                if self._header is None:
                    self.process_custom_header()
            
            print(f"HEADER: {self._header}")

            if self._header:
                if self.request is None:
                    self.process_custom_request()
            
            print(f"CONTENT: {self.request}")


    def write(self):
        if self.request:
            if not self.response_created:
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
            self.sock = None

    def process_protoheader(self):
        #Process type header
        hdrlen = 2
        if len(self._recv_buffer) >= hdrlen:
            self.is_json = not struct.unpack(
                ">H", self._recv_buffer[:hdrlen]
            )[0]
            self._recv_buffer = self._recv_buffer[hdrlen:]

        #Process proto header
        hdrlen = 2
        if len(self._recv_buffer) >= hdrlen:
            self._header_len = struct.unpack(
                ">H", self._recv_buffer[:hdrlen]
            )[0]
            self._recv_buffer = self._recv_buffer[hdrlen:]

    def process_json_header(self):
        hdrlen = self._header_len
        if len(self._recv_buffer) >= hdrlen:
            self._header = self._json_decode(
                self._recv_buffer[:hdrlen], "utf-8"
            )
            self._recv_buffer = self._recv_buffer[hdrlen:]
            for reqhdr in (
                "byteorder",
                "content-length",
                "content-type",
                "content-encoding",
            ):
                if reqhdr not in self._header:
                    raise ValueError(f"Missing required header '{reqhdr}'.")
                
    def process_custom_header(self):
        hdrlen = self._header_len

        if len(self._recv_buffer) >= hdrlen:
            str_header = self._custom_decode(
                self._recv_buffer[:hdrlen], "utf-8"
            )
            self._recv_buffer = self._recv_buffer[hdrlen:]
            str_header = str_header.split('|')
            print("STR_HEADER:",str_header)
            self._header = {
                "content-length":int(str_header[3]), # TODO: fix hard encodings, casting is bad
                "content-type":str_header[1],
                "content-opcode":str_header[4] # TODO: fix hard encodings
            }
            #TODO write an exception to check data


    def process_json_request(self):
        #TODO: Refactor please. Get rid of outer conditional 
        content_len = self._header["content-length"]
        if not len(self._recv_buffer) >= content_len:
            return
        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]
        if self._header["content-type"] == "text/json":
            encoding = self._header["content-encoding"]
            self.request = self._json_decode(data, encoding)
            print(f"Received request {self.request!r} from {self.addr}")
            print(f"Request type: {type(self.request)}")
        else:
            # Binary or unknown content-type
            self.request = data
            print(
                f"Received {self._header['content-type']} "
                f"request from {self.addr}"
            )
        # Set selector to listen for write events, we're done reading.
        self._set_selector_events_mask("w")

    def process_custom_request(self):
        content_len = self._header['content-length']
        if not len(self._recv_buffer) >= content_len:
            return
        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]
        args = self._custom_decode(data, "utf-8")
        self.request = args.split(',')
        print(f"Received request {self.request!r} from {self.addr}")

        self._set_selector_events_mask('w')

    def create_response(self):
        if self._header["content-type"] == "text/json": # TODO: maybe this field isn't needed, can rely on self.is_json
            response = self._create_response_json_content()
        else:
            # Binary or unknown content-type
            print("HARD AT WORK")
            response = self._create_response_binary_content()
        message = self._create_message(**response)
        self.response_created = True
        print(f"STILL HARD AT WORK. PROOF: {message}")
        self._send_buffer += message

        