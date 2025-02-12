import io
import json
import yaml
import selectors
import struct
import datetime
from codes import ResponseCode, OpCode
from database import DatabaseHandler

# Read config file
yaml_path = "config.yaml"
with open(yaml_path) as y:
    config_dict = yaml.safe_load(y)
version = config_dict["version"]
key = config_dict["key"]
db_path = config_dict["db_path"] # TODO: can probably pass in the main server file
min_message_len = config_dict["min_message_len"]
max_message_len = config_dict["max_message_len"]

class Message:
    def __init__(self, selector, sock, addr, db_path="messages.db", active_clients={}):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self._recv_buffer = b""
        self._send_buffer = b""
        self._header_len = None
        self._header = None
        self.request = None
        self.response_created = False
        self.db = DatabaseHandler(db_path) # TODO: should we move this outside?
        self.active_clients = active_clients

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
                    pass 
                    # self.close()

    def _json_encode(self, obj, encoding):
        return json.dumps(obj, ensure_ascii=False).encode(encoding)

    def _json_decode(self, json_bytes, encoding):
        tiow = io.TextIOWrapper(
            io.BytesIO(json_bytes), encoding=encoding, newline=""
        )
        obj = json.load(tiow)
        tiow.close()
        return obj

    def _package_response(
        self, response
    ):
        # Encode content
        content_bytes = self._json_encode(response, self._header["content_encoding"])
        # Encode header
        jsonheader = self._header
        jsonheader["content_length"] = len(content_bytes)
        jsonheader_bytes = self._json_encode(jsonheader, self._header["content_encoding"])
        # Encode protoheader and package message
        message_hdr = struct.pack(">H",version) + struct.pack(">H", len(jsonheader_bytes))
        message = message_hdr + jsonheader_bytes + content_bytes
        return message

    def _process_request(self):
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
        # TODO: catch input exceptions here
        if opcode == OpCode.ACCOUNT_EXISTS.value:
            result = self.db.account_exists(args[0])
            # parse result of account_exists, which is a bool
            if not result:
                result = {"status_code": ResponseCode.ACCOUNT_NOT_FOUND.value}
            else:
                result = {"status_code": ResponseCode.ACCOUNT_EXISTS.value} # TODO: cleanup
        elif opcode == OpCode.CREATE_ACCOUNT.value:
            result = self.db.create_account(*args)
        elif opcode == OpCode.LOGIN_ACCOUNT.value:
            result = self.db.login_account(*args)
            # Add to active clients
            if result["status_code"] == ResponseCode.SUCCESS.value:
                self.active_clients[args[0]] = self
        elif opcode == OpCode.LIST_ACCOUNTS.value:
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
        elif opcode == OpCode.SEND_MSG.value:
            sender = args[0]
            receiver = args[1]
            msg_content = args[2]
            # Check both accounts exist
            if not self.db.account_exists(args[0]) or not self.db.account_exists(args[1]):
                return {"status_code": ResponseCode.ACCOUNT_NOT_FOUND.value}
            # Enforce message constraints
            if len(args[2]) < min_message_len or len(args[2]) > max_message_len:
                return {"status_code": ResponseCode.BAD_REQUEST.value}
            # If receiver online: try sending immediately
            if args[1] in self.active_clients:
                try:

                    # We have a Message object for the receiver
                    receiver_msg = self.active_clients[receiver]
                
                    # Construct a new header or payload for the receiver
                    response = {
                        "status_code": ResponseCode.SUCCESS.value,
                        "data": [(*args, round(datetime.datetime.now().microsecond), True)]
                    }
                    
                    # Temporarily update our opcode to "RECEIVE_MSG" 
                    old_opcode = self._header["opcode"]
                    self._header["opcode"] = OpCode.RECEIVE_MSG.value
                    #TODO: modify _package_response to take opcode as an argument

                    # Build the message
                    packaged = self._package_response(response)
                    self._header["opcode"] = old_opcode

                    # 3) Send data by appending to the receiver's buffer
                    receiver_msg._send_buffer += packaged
                    # Ensure the receiver is listening for EVENT_WRITE
                    receiver_msg._set_selector_events_mask("w")

                    # Insert message into database
                    result = self.db.insert_message(*args, round(datetime.datetime.now().microsecond), True)
                except Exception as e:
                    result = self.db.insert_message(*args, round(datetime.datetime.now().microsecond), False)
            else:
                # If user not online, just store in DB
                self.db.insert_message(sender, receiver, msg_content,
                                       round(datetime.datetime.now().microsecond),
                                       False)
                result = {"status_code": ResponseCode.SUCCESS.value}
        elif opcode == OpCode.LOGOUT_ACCOUNT.value:
            try:
                del self.active_clients[args[0]]
                result = {"status_code": ResponseCode.SUCCESS.value}
            except ValueError as e:
                result = {"status_code": ResponseCode.BAD_REQUEST.value} # TODO: return error message as data
            self.close()
        else:
            with Exception as e:
                result = {"status_code": ResponseCode.SUCCESS.value} #
            # TODO: as exception or as unknown opcode status code? also could move to header
            # NOTE: send an exception status code + data = exception message to client? or shouldn't be exposed. whole try loop
        return result

    def process_events(self, mask):
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()
    
    def read(self):
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
        if self.request and not self.response_created:
            self._process_request()

        self._write()

        self._set_selector_events_mask("r")

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
        hdrlen = 2
                
        # Get version
        if len(self._recv_buffer) >= hdrlen:
            v = struct.unpack(
                ">H", self._recv_buffer[:hdrlen]
            )[0]
            if v != version: 
                raise ValueError(f"Unsupported version: {v}")
            self._recv_buffer = self._recv_buffer[hdrlen:]

        # Get header length
        if len(self._recv_buffer) >= hdrlen:
            self._header_len = struct.unpack(
                ">H", self._recv_buffer[:hdrlen]
            )[0]
            self._recv_buffer = self._recv_buffer[hdrlen:]

    def process_header(self):
        hdrlen = self._header_len
        if len(self._recv_buffer) >= hdrlen:
            print(hdrlen, len(self._recv_buffer))
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

    def process_content(self):
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
        
        # Set selector to listen for write events, we're done reading.
        self._set_selector_events_mask("w")
