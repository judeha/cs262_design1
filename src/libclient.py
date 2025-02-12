import io
import json
import selectors
import struct
import yaml
import sys
import tkinter as tk
import threading
import yaml
from codes import ResponseCode, RESPONSE_MESSAGES, OpCode, OPCODE_MESSAGES 

#Read config file
yaml_path = "config.yaml"
with open(yaml_path) as y:
    config_dict = yaml.safe_load(y)

version = config_dict["version"]
key = config_dict["key"]
db_path = config_dict["db_path"]


class Message:
    def __init__(self, selector, sock, addr):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self.request = None
        self._recv_buffer = b""
        self._send_buffer = b""
        self._request_queued = False
        self._header_len = None
        self._header = None
        self.response = None

        # self.events = selectors.EVENT_READ | selectors.EVENT_WRITE


        # # tkinter attributes
        # self.root = tk.Tk()
        # self.root.title("Multi-Client Chat System")
        # self.root.geometry("1000x700")

        # self.container = tk.Frame(self.root)
        # self.container.pack(fill="both", expand=True)

        # self.frames = {}
        # self.setup_frames()
        # self.show_frame("main")  # Show the main frame initially

        # root_thread = threading.Thread(target=self.root.mainloop(), daemon=True)
        # root_thread.start()

    # def create_request(self, opcode, args):
    #     new_request =  dict(
    #         # byteorder = sys.byteorder,
    #         # content_type="json",
    #         content_encoding="utf-8",
    #         opcode = opcode,
    #         content={"args": args},
    #     )
    #     # if new_request != self.request:
    #     self.request = new_request
    #     print(self.request)
    #     self.selector.modify(self.sock, self.events, data=self)

    def setup_frames(self):
        """Creates and stores all the frames."""
        self.frames["main"] = self.setup_main_frame()
        self.frames["home"] = self.setup_home_frame()
        self.frames["login"] = self.setup_login_frame()
        self.frames["create"] = self.setup_create_account_frame()

        for frame in self.frames.values():
            frame.place(x=0, y=0, width=500, height=500)

    def setup_main_frame(self):
        """Frame that asks for username"""

        frame = tk.Frame(self.container)
        tk.Label(frame, text="Username:").pack(pady=5)
        self.username = tk.Entry(frame)
        self.username.pack(side='top')

        next_btn = tk.Button(frame, text="Next", command=lambda: self.create_request(OpCode.ACCOUNT_EXISTS.value, [self.username.get()]))
        next_btn.pack(side='top')

        return frame

    def setup_create_account_frame(self):
        """Frame that asks for the password for the new account"""
        frame = tk.Frame(self.container)
        tk.Label(frame, text="New Password:").pack(pady=5)
        self.new_password_entry = tk.Entry(frame, show="*")
        self.new_password_entry.pack(pady=5)

        create_btn = tk.Button(frame, text='Create', command=lambda: self.create_request(OpCode.CREATE_ACCOUNT.value, [self.username.get(), self.new_password_entry.get()]))
        create_btn.pack(pady=10)

        return frame

    def setup_login_frame(self):
        """Frame that asks for the password to login into existing account"""
        frame = tk.Frame(self.container)
        tk.Label(frame, text="Password:").pack(pady=5)
        self.password = tk.Entry(frame, show="*")
        self.password.pack(pady=5)

        login_btn = tk.Button(frame, text='Login', command=lambda: self.show_frame("home"))
        login_btn.pack(pady=10)

        return frame

    def setup_home_frame(self):
        """Frame that contains the main logic"""

        #TODO: Setup a section for unread messages 
        
        frame = tk.Frame(self.container)
        frame.pack(padx=10, pady=10, fill='both', expand=True)

        # Create a frame for chat display and accounts list (side by side)
        chat_frame = tk.Frame(frame)
        chat_frame.pack(fill='both', expand=True)

        # Chatbox (read-only text widget)
        chat_display = tk.Text(chat_frame, width=50, height=20, state='disabled', wrap='word')
        chat_display.pack(side='left', padx=(0, 5), fill='both', expand=True)

        # Account names display (smaller)
        accounts_display = tk.Text(chat_frame, width=20, height=20, state='disabled', wrap='word')
        accounts_display.pack(side='left', padx=(5, 0), fill='y')

        # Frame for message input and buttons (placed below chat_frame)
        input_frame = tk.Frame(frame)
        input_frame.pack(fill='x', pady=(10, 0))

        # Message input field
        message_entry = tk.Entry(input_frame)
        message_entry.pack(side='left', padx=10, fill="x", expand=True)

        # Send button
        send_btn = tk.Button(input_frame, text='Send', command=lambda: self.show_frame("home"))
        send_btn.pack(side='left', padx=5)

        # Delete Account button
        delete_acc_btn = tk.Button(input_frame, text='Delete Account', command=lambda: self.show_frame("accounts"))
        delete_acc_btn.pack(side='left', padx=5)

        return frame

    def show_frame(self, frame_name):
        """Brings the specified frame to the front."""
        self.frames[frame_name].tkraise()
  
    def _check_username(self):
        """Handles username checking action."""
        username = self.username_entry.get()
        if not username:
            print("Error: Username cannot be empty")
            return

        action, args = "check_username", [username]
        request = self.create_request(action, args)
        self.start_connection(request)

    def _on_create_account(self):
        """Handles account creation request."""
        new_username = self.new_username_entry.get()
        new_password = self.new_password_entry.get()

        if not new_username or not new_password:
            print("Error: Empty username or password")
            return

        action = "create_account"
        args = [new_username, new_password]
        request = self.create_request(action, args)
        self.start_connection(request)

    def _on_delete_message(self):
        pass

    def _on_delete_account(self):
        pass

    def _on_send_message(self):
        pass

    def _on_read_message(self):
        pass

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

        # Get opcode, status code, and data from self._header and self.response
        opcode = self._header.get("opcode")
        status_code = self.response.get("status_code")
        data = self.response.get("data")

        # Process response content
        self._generate_action(opcode, status_code, data)

        # Close when response has been processed
        # self.close() # TODO: fix

    def _generate_action(self, opcode, status_code, data):
        # TODO: enforce I/O
        if status_code != ResponseCode.SUCCESS.value:
            pass
        else:
            if opcode == OpCode.ACCOUNT_EXISTS.value:
                # self.setup_login_frame()
                pass
            elif opcode == OpCode.CREATE_ACCOUNT.value:
                # self.setup_home_frame()
                pass
            elif opcode == OpCode.LOGIN_ACCOUNT.value:
                print("Here are your messages: ", data[1:])
                print("You have ", data[0], " unread messages.")
                # TODO: display homepage
            elif opcode == OpCode.DELETE_ACCOUNT.value:
                pass
                # TODO: display create account page
            elif opcode == OpCode.LIST_ACCOUNTS.value:
                print("Here are all the accounts: ", [data])
                # TODO: display accounts
            elif opcode == OpCode.LOGOUT_ACCOUNT.value:
                pass
            elif opcode == OpCode.READ_MSG_DELIVERED.value:
                print("Here are your messages: ", data[1:])
                print("You have ", data[0], " unread messages.")
                # TODO: display homepage
            elif opcode == OpCode.READ_MSG_UNDELIVERED.value:
                print("Here are your messages: ", data[1])
                print("You have ", data[0], " unread messages.")
                # TODO: display updated homepage
            elif opcode == OpCode.DELETE_MSG.value:
                pass
                # TODO: display updated homepage
            elif opcode == OpCode.HOMEPAGE.value:
                print("Here are your messages: ", data[1:])
                print("You have ", data[0], " unread messages.")
                # TODO: display homepage
            elif opcode == OpCode.SEND_MSG.value:
                pass
                # TODO: display homepage
            elif opcode == OpCode.RECEIVE_MSG.value:
                print("You have a new message. Here are your messages: ", data)
                # TODO: display homepage UNLESS they are viewing all the account lists. hannah pls decide
            else:
                print("Unknown opcode")

    def process_events(self, mask):
        print("IN PROCESS EVENTS")

        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()

    def read(self):
        print("IN READ")

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
        print("IN WRITE")

        if not self._request_queued:
            self.queue_request(self.request)

            self.queue_request()
        
        print("SEND_BUFFER", self._send_buffer)
        
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

    def queue_request(self, request):
        print("IN QUEUE REQUEST")
        self.queue_request = request
        message = self._package_request(request)
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
        # self.close()