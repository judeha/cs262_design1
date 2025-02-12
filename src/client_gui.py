#!/usr/bin/env python3
import argparse
import socket
import yaml
import selectors
import threading
import tkinter as tk
from tkinter import scrolledtext
import queue
from codes import OpCode, ResponseCode
from libclient import Message

# Read config file
yaml_path = "config.yaml"
with open(yaml_path) as y:
    config_dict = yaml.safe_load(y)
BG_COLOR = config_dict['bg_color']
BTN_TXT_COLOR = config_dict['btn_txt_color']
BTN_BG_COLOR = config_dict['btn_bg_color']
max_view = config_dict['max_view']

# TODO: loggin
# TODO: error enforcement
# TODO: matching
# TODO: custom protocol
# TODO: password security
# TODO: delete messages, delete account, list account string matching

# -----------------------------------------------------------------------------
# Background Thread: manages the selector event while loop
# -----------------------------------------------------------------------------

class SelectorThread(threading.Thread):
    """
    Runs a selector event loop in the background so the GUI remains responsive.
    """
    def __init__(self, sel, stop_event, incoming_queue):
        """
        :param sel: selectors.DefaultSelector instance
        :param stop_event: threading.Event used to signal the thread to stop
        :param incoming_queue: queue.Queue for passing server responses back to GUI
        """
        super().__init__(daemon=True)
        self.sel = sel
        self.stop_event = stop_event
        self.incoming_queue = incoming_queue

    def run(self):
        """Run the event loop until stop_event is set."""
        while not self.stop_event.is_set():
            events = self.sel.select(timeout=1)
            for key, mask in events:
                message_obj = key.data  # This should be a `Message` instance
                try:
                    message_obj.process_events(mask)
                except Exception as e:
                    print(f"[SelectorThread] Error in process_events: {e}")
                    message_obj.close()

        # Cleanup when stop_event is triggered
        self.sel.close()

# -----------------------------------------------------------------------------
# GUI Class: basic chat window
# -----------------------------------------------------------------------------

class ChatGUI:
    """
    A simple Tkinter GUI that displays incoming messages and sends new requests.
    """
    def __init__(self, root, message_obj, incoming_queue):
        """
        :param root: Tk root
        :param message_obj: The libclient.Message instance handling socket I/O
        :param incoming_queue: queue.Queue for receiving updates from the server
        """
        self.root = root
        self.message_obj = message_obj
        self.incoming_queue = incoming_queue

        # Set up the main window
        self.root.title("MyChat")
        self.root.geometry("800x600") # TODO: put in config
        self.container = tk.Frame(root, bg=BG_COLOR)
        self.container.pack(expand=True, fill=tk.BOTH)

        # Set up all wireframes
        self.frames = {}
        self.setup_frames()
        self.show_frame("main") # Show the main frame initially

        # Periodically poll the incoming queue
        self.poll_incoming()

        # Initialize chat display
        self.messages = [] # TODO: fragile
        self.count = 0
        self.accounts = []

    def send_message(self, opcode, args):
        """
        Sends a request to the server using the existing `message_obj`.
        For example, we might send an OpCode.SEND_MSG request or something else.
        """
        if opcode is not None:
            # Here is where you craft the request dictionary that your `Message` object expects
            request = dict(
                content_encoding= "utf-8", # TODO: put in config
                opcode=opcode,
                content= {"args": args},
            )
            # Queue the request
            self.message_obj.request = request
            self.message_obj.queue_request()
            self.message_obj._request_queued = True
            # Modify the selector so we listen for write events
            self.message_obj._set_selector_events_mask("rw")

    def poll_incoming(self):
        """
        Check the thread-safe queue for incoming server responses
        and update the chat display accordingly.
        """
        while True:
            try:
                response_str = self.incoming_queue.get_nowait()
                
                # Get the opcode, status code, and data from the response
                opcode = response_str["opcode"]
                status_code = response_str["status_code"]
                data = response_str["data"]

                # Handle the response based on the opcode
                if opcode == OpCode.STARTING.value:
                    self.show_frame("main") # TODO: fragile, starting condition
                elif opcode != OpCode.ACCOUNT_EXISTS.value and status_code != ResponseCode.SUCCESS.value:
                    # Stay in the same frame if the request failed
                    self.display_error("Invalid request or incorrect credentials.") # TODO: shows on wrong page
                else:
                    if opcode == OpCode.ACCOUNT_EXISTS.value and status_code == ResponseCode.ACCOUNT_NOT_FOUND.value:
                        self.show_frame("create_account")
                    elif opcode == OpCode.ACCOUNT_EXISTS.value and status_code == ResponseCode.ACCOUNT_EXISTS.value:
                        self.show_frame("login")
                    elif opcode == OpCode.CREATE_ACCOUNT.value:
                        self.show_frame("login")
                    elif opcode == OpCode.LOGIN_ACCOUNT.value:
                        self.count = data.pop(0)
                        self.messages = data
                        self.show_frame("homepage")
                    elif opcode == OpCode.LIST_ACCOUNTS.value:
                        self.accounts = data
                        self.show_frame("list_accounts")
                    elif opcode == OpCode.DELETE_ACCOUNT.value:
                        self.show_frame("main") # TODO: add a success message
                    elif opcode == OpCode.HOMEPAGE.value:
                        self.count = data.pop(0)
                        self.messages = data # TODO: refactor for redundancy
                        self.show_frame("homepage")
                    elif opcode == OpCode.READ_MSG_UNDELIVERED.value:
                        self.count = data.pop(0)
                        self.messages = data
                        self.show_frame("homepage")
                    elif opcode == OpCode.READ_MSG_DELIVERED.value:
                        self.messages = data
                        self.show_frame("homepage")
                    elif opcode == OpCode.DELETE_MSG.value:
                        self.count = data.pop(0)
                        self.messages = data
                        self.show_frame("homepage")
                    elif opcode == OpCode.SEND_MSG.value:
                        self.show_frame("homepage")
                    elif opcode == OpCode.RECEIVE_MSG.value:
                        self.messages += data
                        if len(self.messages) > max_view:
                            self.messages.pop(0)
                        self.show_frame("homepage")
            except queue.Empty:
                break
            else:
                pass
                # self._append_chat(response_str)

        # Schedule next poll
        self.root.after(2, self.poll_incoming) # TODO: put in config
    
    def setup_main_frame(self):
        """Set up the main frame with a simple welcome message."""        
        frame = tk.Frame(self.container, bg=BG_COLOR)

        # Messages
        tk.Label(frame, text="Welcome to MyChat! Check if you have an account.").pack(pady=10)
        # Error message (initially hidden)
        self.error_label = tk.Label(frame, text="", fg="black", bg=BG_COLOR)
        self.error_label.pack(pady=5)  # Show at the top

        # Username entry field
        tk.Label(frame, text="Username:").pack(pady=5)
        username = tk.Entry(frame)
        username.pack(side='top')

        # Next button
        next_btn = tk.Button(frame, text="Next", command=lambda: self._on_check_username(username))
        next_btn.pack(side='top')

        return frame
    
    def setup_create_account_frame(self):
        frame = tk.Frame(self.container, bg=BG_COLOR)

        # Messages
        tk.Label(frame, text="Please create an account to continue.").pack(pady=10) # TODO: use config username/password enforcements
        # Error message (initially hidden)
        self.error_label = tk.Label(frame, text="", fg="black", bg=BG_COLOR)
        self.error_label.pack(pady=5)  # Show at the top

        # Username, password entry fields
        tk.Label(frame, text="Username:").pack(pady=5)
        username = tk.Entry(frame)
        username.pack(pady=5)
        tk.Label(frame, text="Password:").pack(pady=5)
        password = tk.Entry(frame, show="*")
        password.pack(pady=5)

        # Next button
        create_btn = tk.Button(frame, text="Create", command=lambda: self._on_create_account(username, password))
        create_btn.pack(pady=10)

        return frame
    
    def setup_login_frame(self):
        frame = tk.Frame(self.container, bg=BG_COLOR)

        # Messages
        tk.Label(frame, text="Enter your username and password to login").pack(pady=10)

        # Error message (initially hidden)
        self.error_label = tk.Label(frame, text="", fg="black", bg=BG_COLOR)
        self.error_label.pack(pady=5)  # Show at the top

        # Username, password entry fields
        tk.Label(frame, text="Username:").pack(pady=5)
        username = tk.Entry(frame)
        username.pack(pady=5)
        tk.Label(frame, text="Password:").pack(pady=5)
        password = tk.Entry(frame, show="*")
        password.pack(pady=5)

        # Next button
        login_btn = tk.Button(frame, text="Login", command=lambda: self._on_login_account(username, password))
        login_btn.pack(pady=10)
        
        return frame

    def setup_homepage_frame(self):
        frame = tk.Frame(self.container, bg=BG_COLOR)

        # Messages
        if self.username:
            text = f"Welcome, {self.username}!"
        else:
            text = "MyChat"
        tk.Label(frame, text=text).pack(pady=5)
        # Error message (initially hidden)
        self.error_label = tk.Label(frame, text="", fg="black", bg=BG_COLOR)
        self.error_label.pack(pady=5)  # Show at the top

        # Create a frame for chat display and accounts list (side by side)
        chat_frame = tk.Frame(frame)
        chat_frame.pack(fill='both', expand=False)
        # Scrollbar for chat display
        scrollbar = tk.Scrollbar(chat_frame)
        scrollbar.pack(side='right', fill='y')
        # Chatbox (read-only text widget)
        self.chat_display = tk.Text(chat_frame, width=50, height=20, state='disabled', wrap='word', yscrollcommand=scrollbar.set)
        self.chat_display.pack(side='left', padx=(0, 5), fill='both', expand=True)
        scrollbar.config(command=self.chat_display.yview)  # Link scrollbar

        # Frame for message input and buttons (placed below chat_frame)
        input_frame = tk.Frame(frame)
        input_frame.pack(fill='x', pady=(10, 0))

        # Receiver, message entry fields
        receiver_entry = tk.Entry(input_frame)
        receiver_entry.pack(side='left', padx=10, fill="x", expand=True)
        message_entry = tk.Entry(input_frame)
        message_entry.pack(side='left', padx=10, fill="x", expand=True)
        receiver_label = tk.Label(frame, text="recipient", fg=BG_COLOR, highlightbackground=BG_COLOR)
        receiver_label.pack(side='left', padx=50)
        message_label = tk.Label(frame, text="your message", fg=BG_COLOR, highlightbackground=BG_COLOR)
        message_label.pack(side='left', padx=100)

        # Send button
        send_btn = tk.Button(input_frame, text='Send', command=lambda: self._on_send_message(receiver_entry, message_entry))
        send_btn.pack(side='left', padx=5)

        # Delete Account button
        delete_acc_btn = tk.Button(input_frame, text='Delete Account', command=lambda: self._on_delete_account(self.username, self.password))
        delete_acc_btn.pack(side='top', fill='x', pady=5)

        # List Account button
        list_acc_btn = tk.Button(input_frame, text='List Account', command=lambda: self._on_list_accounts()) # TODO change to text field
        list_acc_btn.pack(side='top', fill='x', pady=5)

        # Fetch last X delivered messages button
        num_read_msgs_entry = tk.Entry(input_frame)
        num_read_msgs_entry.pack(side='right', padx=5)
        fetch_read_btn = tk.Button(input_frame, text='See older messages', command=lambda: self._on_fetch_read_message( num_read_msgs_entry))
        fetch_read_btn.pack(side='top', fill='x', pady=5)
        
        # Fetch last Y undelivered messages button
        num_unread_msgs_entry = tk.Entry(input_frame)
        num_unread_msgs_entry.pack(side='right', padx=5)
        fetch_unread_btn = tk.Button(input_frame, text='See new messages', command=lambda: self._on_fetch_unread_message(num_unread_msgs_entry))
        fetch_unread_btn.pack(side='top', fill='x', pady=5)

        return frame
    
    def setup_list_accounts_frame(self):
        frame = tk.Frame(self.container, bg=BG_COLOR)
        tk.Label(frame, text="List of Accounts").pack(pady=5)

        # Create a frame for accounts list (side by side)
        accounts_frame = tk.Frame(frame)
        accounts_frame.pack(fill='both', expand=True)

        # Chatbox (read-only text widget)
        self.accounts_display = tk.Text(accounts_frame, width=50, height=20, state='disabled', wrap='word')
        self.accounts_display.pack(side='left', padx=(0, 5), fill='both', expand=True)

        # Home button
        home_btn = tk.Button(frame, text='Homepage', command=lambda: self.show_frame("homepage")) # TODO: should you fetch homepage again?
        home_btn.pack(side='left', padx=5)

        return frame

    def setup_my_matches_frame(self):
        pass

    def setup_frames(self):
        self.frames["main"] = self.setup_main_frame()
        self.frames["create_account"] = self.setup_create_account_frame()
        self.frames["login"] = self.setup_login_frame()
        self.frames["homepage"] = self.setup_homepage_frame()
        self.frames["list_accounts"] = self.setup_list_accounts_frame()
        # self.frames["my_matches"] = self.setup_my_matches_frame()

        for frame in self.frames.values():
            # Place each frame in the same row/column so they overlap
            frame.grid(row=0, column=0, sticky="nsew")

    def show_frame(self, frame_name):
        """Brings the specified frame to the front."""
        self.frames[frame_name].tkraise()
        # self.frames[frame_name].pack()

        # If switching to homepage, refresh messages
        if frame_name == "homepage":
            self.display_messages()
        
        if frame_name == "list_accounts":
            self.display_accounts()

    def display_error(self, message):
        """Displays an error message on the current frame without switching frames."""
        if hasattr(self, "error_label"):  # Ensure the label exists
            self.error_label.config(text=message)
    
    def display_messages(self):
        """Display messages in chat_display, ordered from oldest to newest."""
        self.chat_display.config(state='normal')  # Enable editing temporarily
        self.chat_display.delete(1.0, tk.END)  # Clear old messages

        self.chat_display.insert(tk.END, f"Unread messages: {self.count}\n\n")

        sorted_messages = self.messages
        print("HEY", sorted_messages)

        # Sort messages by timestamp (ascending order)
        # sorted_messages = sorted(self.messages, key=lambda x: x[4])  # x[4] is timestamp

        for msg in sorted_messages:
            msg_id, sender, receiver, content, timestamp, delivered = msg
            delivered_status = "✔" if delivered else "❌"
            message_text = f"[{msg_id}: {sender} -> {receiver}] {timestamp}: {delivered_status}\ncontent: {content}\n\n"
            self.chat_display.insert(tk.END, message_text)

        self.chat_display.config(state='disabled')  # Disable editing again
        self.chat_display.see(tk.END)  # Auto-scroll to latest message

    def display_accounts(self):
        """Display messages in chat_display, ordered from oldest to newest."""
        self.accounts_display.config(state='normal')  # Enable editing temporarily
        self.accounts_display.delete(1.0, tk.END)  # Clear old accounts

        for acc in self.accounts:
            print("HEY", acc)
            id, username = acc
            text = f"{id}:{username}----------------------\n"
            self.accounts_display.insert(tk.END, text)

        self.accounts_display.config(state='disabled')  # Disable editing again
        self.accounts_display.see(tk.END)  # Auto-scroll to latest message

    # def _append_chat(self, text):
    #     """Helper to insert text into the chat display."""
    #     self.chat_display.config(state='normal')
    #     self.chat_display.insert(tk.END, text + "\n")
    #     self.chat_display.config(state='disabled')
    #     self.chat_display.see(tk.END)

    def _on_check_username(self, username):
        # Call the server to check if the username exists
        self.send_message(OpCode.ACCOUNT_EXISTS.value, [username.get()])

    def _on_create_account(self, username, password):
        # Call the server to create an account
        self.send_message(OpCode.CREATE_ACCOUNT.value, [username.get(), password.get()])

    def _on_login_account(self, username, password):
        # TODO: sketch
        self.username = username.get()
        self.password = password.get()
        self.send_message(OpCode.LOGIN_ACCOUNT.value, [username.get(), password.get()])
    
    def _on_delete_account(self, username, password):
        self.send_message(OpCode.DELETE_ACCOUNT.value, [username.get(), password.get()])

    def _on_send_message(self, receiver, message):
        self.send_message(OpCode.SEND_MSG.value, [self.username, receiver.get(), message.get()])
        # Clear the message field
        message.delete(0, tk.END)
        receiver.delete(0, tk.END)

    def _on_list_accounts(self):
        self.send_message(OpCode.LIST_ACCOUNTS.value, [])

    def _on_fetch_unread_message(self, num_msgs):
        self.send_message(OpCode.READ_MSG_UNDELIVERED.value, [self.username, int(num_msgs.get())])

    def _on_fetch_read_message(self, num_msgs):
        self.send_message(OpCode.READ_MSG_DELIVERED.value, [self.username, int(num_msgs.get())])
# -----------------------------------------------------------------------------
# Main Client Launcher
# -----------------------------------------------------------------------------

def start_connection(host, port, incoming_queue):
    """
    Creates a non-blocking socket, registers it with a selector using
    our libclient.Message class, and returns (selector, message_obj).
    """
    sel = selectors.DefaultSelector()

    # Create and connect socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    try:
        sock.connect((host, port))
    except BlockingIOError:
        pass

    # Build initial request
    initial_request = {
        "content_encoding": "utf-8",
        "opcode": -1,
        "content": {"args": []},  # TODO: fragile
    }

    # Create the Message object
    addr = (host, port)
    msg_obj = Message(selector=sel, sock=sock, addr=addr, request=initial_request, incoming_queue=incoming_queue)

    # Register the socket with the selector
    sel.register(sock, selectors.EVENT_READ | selectors.EVENT_WRITE, data=msg_obj)

    return sel, msg_obj

def main(args):
    host = args.host # TODO: put in config?
    port = args.port

    # A queue for receiving messages from the server in the main thread
    incoming_queue = queue.Queue()

    # 1) Set up socket + selector + register them with an initial request
    sel, message_obj = start_connection(host, port, incoming_queue)

    # 2) Create a stop event so we can shut down the selector thread
    stop_event = threading.Event()

    # 3) Start the background selector thread
    sel_thread = SelectorThread(sel, stop_event, incoming_queue)
    sel_thread.start()

    # 4) Set up Tkinter in the main thread
    root = tk.Tk()
    app = ChatGUI(root, message_obj, incoming_queue)

    # On close, signal the selector thread to stop, close the socket, etc.
    def on_close():
        """Handle cleanup when closing the client window."""
        # Stop selector thread
        stop_event.set()
        # Close connection
        message_obj.close()
        # Destroy GUI
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=65432)
    args = parser.parse_args()

    main(args)
