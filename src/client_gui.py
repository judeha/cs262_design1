#!/usr/bin/env python3
import argparse
import socket
import yaml
import logging
import copy
import selectors
import threading
import tkinter as tk
import time
import queue
import hashlib
from utils import OpCode, ResponseCode, RESPONSE_MESSAGES
from client_handler import Message, MessageCustom
import random

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load configuration
yaml_path = "config.yaml"
with open(yaml_path, "r") as y:
    config = yaml.safe_load(y)

# Defaults
BG_COLOR = config['bg_color']
BTN_TXT_COLOR = config['btn_txt_color']
BTN_BG_COLOR = config['btn_bg_color']
HOST = config['host']
PORT = config['port']
PROTOCOL = config['protocol']
UI_DIMENSIONS = config['ui_dimensions']
CONTENT_ENCODING = config['encoding']
EMOJIS = config['emojis']
MAX_VIEW = config["max_view"]

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
                    logging.error(f"[SelectorThread] Error in process_events: {e}")
                    message_obj.close()

        # Cleanup when stop_event is triggered
        self.sel.close()

# -----------------------------------------------------------------------------
# GUI Class: basic chat window
# -----------------------------------------------------------------------------

class ChatGUI:
    """
    A client GUI that displays incoming messages and sends new requests.
    """
    def __init__(self, root, message_obj, incoming_queue,protocol=0):
        """
        :param root: Tk root
        :param message_obj: The client_handler.Message instance handling socket I/O
        :param incoming_queue: queue.Queue for receiving updates from the server
        """
        self.root = root
        self.message_obj = message_obj
        self.incoming_queue = incoming_queue

        # Set up the main window
        self.root.title("MyChat")
        self.root.geometry(UI_DIMENSIONS) 
        self.container = tk.Frame(root, bg=BG_COLOR)
        self.container.pack(expand=True, fill=tk.BOTH)

        # Initialize chat display variables
        self.messages = []
        self.count = 0
        self.accounts = []
        self.username = ""

        # Set up all wireframes
        self.frames = {}
        self.setup_frames()
        self.show_frame("main") # Show the main frame initially

        # Periodically poll the incoming queue
        self.poll_incoming()

        # Define which wire protocol to use
        self.protocol = protocol

    def send_message(self, opcode, args):
        """
        Sends a request to the server using the existing `message_obj`.
        For example, we might send an OpCode.SEND_MSG request or something else.
        """
        if opcode is not None:
            # Here is where you craft the request dictionary that your `Message` object expects
            request = dict(
                content_encoding= CONTENT_ENCODING, 
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
                # Starting page
                if opcode == OpCode.STARTING.value:
                    self.show_frame("main")
                elif opcode != OpCode.ACCOUNT_EXISTS.value and status_code != ResponseCode.SUCCESS.value:
                    # Stay in the same frame if the request failed and display error message
                    self.display_error(RESPONSE_MESSAGES[status_code])
                else:
                    # If new user, create account
                    if opcode == OpCode.ACCOUNT_EXISTS.value and status_code == ResponseCode.ACCOUNT_NOT_FOUND.value:
                        self.show_frame("create_account")
                    # If existing user, login
                    elif opcode == OpCode.ACCOUNT_EXISTS.value and status_code == ResponseCode.ACCOUNT_EXISTS.value:
                        self.show_frame("login")
                    # If account creation successful, login
                    elif opcode == OpCode.CREATE_ACCOUNT.value:
                        self.show_frame("login")
                    # If operation requires homepage to be fetched, show homepage
                    elif opcode in [OpCode.LOGIN_ACCOUNT.value, OpCode.HOMEPAGE.value, OpCode.READ_MSG_UNDELIVERED.value, OpCode.DELETE_MSG.value]:
                        self.count = data.pop(0)
                        self.messages = data
                        self.show_frame("homepage")
                    # If listing accounts, show accounts
                    elif opcode == OpCode.LIST_ACCOUNTS.value:
                        self.accounts = data
                        self.show_frame("list_accounts")
                    # If account deletion successful, show main
                    elif opcode == OpCode.DELETE_ACCOUNT.value:
                        self.show_frame("main")
                    # If fetching archived messages, extend homepage length
                    elif opcode == OpCode.READ_MSG_DELIVERED.value:
                        self.messages = data
                        self.show_frame("homepage")
                    # If sending message, stay on homepage
                    elif opcode == OpCode.SEND_MSG.value:
                        self.show_frame("homepage")
                    # If receiving message, update messages and stay on homepage
                    elif opcode == OpCode.RECEIVE_MSG.value:
                        self.messages += data
                        if len(self.messages) > MAX_VIEW:
                            self.messages.pop(0)
                        self.show_frame("homepage")
            except queue.Empty:
                break
            else:
                pass

        # Schedule next poll
        self.root.after(2, self.poll_incoming) # TODO: put in config
    
    def setup_main_frame(self):
        """Set up the main frame with a simple welcome message."""        
        frame = tk.Frame(self.container, bg=BG_COLOR)

        # Messages
        tk.Label(frame, text="Welcome to MyChat! Check if you have an account.").pack(pady=10)
        # Error message (initially hidden)
        self.error_label = tk.Label(frame, text="", fg="white", bg=BG_COLOR)
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
        """Set up the create account frame with username and password fields."""
        frame = tk.Frame(self.container, bg=BG_COLOR)

        # Messages
        tk.Label(frame, text="Please create an account to continue.").pack(pady=10) # TODO: use config username/password enforcements
        # Error message (initially hidden)
        self.error_label = tk.Label(frame, text="", fg="white", bg=BG_COLOR)
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
        """Set up the login frame with username and password fields."""
        frame = tk.Frame(self.container, bg=BG_COLOR)

        # Messages
        tk.Label(frame, text="Enter your username and password to login").pack(pady=10)

        # Error message (initially hidden)
        self.error_label = tk.Label(frame, text="", fg="white", bg=BG_COLOR)
        self.error_label.pack(pady=5,)  # Show at the top

        # Username, password entry fields
        tk.Label(frame, text="Username:").pack(pady=5)
        username = tk.Entry(frame)
        username.pack(pady=5, padx=20)
        tk.Label(frame, text="Password:").pack(pady=5)
        password = tk.Entry(frame, show="*")
        password.pack(pady=5,padx=20)

        # Next button
        login_btn = tk.Button(frame, text="Login", command=lambda: self._on_login_account(username, password))
        login_btn.pack(pady=10)
        
        return frame

    def update_homepage_title(self):
        """Dynamically update the homepage title with the logged-in username."""
        if hasattr(self, "homepage_title_label"):
            text = f"Welcome, {self.username}!" if self.username else "MyChat"
            self.homepage_title_label.config(text=text)

    def setup_homepage_frame(self):
        """Set up the homepage frame with chat display and message entry."""
        frame = tk.Frame(self.container, bg=BG_COLOR)

        # Welcome message
        self.homepage_title_label = tk.Label(frame, text="MyChat", font=("Arial", 14, "bold"), fg="white", bg=BG_COLOR)
        self.homepage_title_label.grid(row=0, column=0, columnspan=3, pady=10, sticky="w")

        # Error message (initially empty)
        self.error_label = tk.Label(frame, text="", fg="red", bg=BG_COLOR)
        self.error_label.grid(row=1, column=0, columnspan=3, pady=5, sticky="w")

        # Chat Display
        chat_frame = tk.Frame(frame)
        chat_frame.grid(row=2, column=0, columnspan=3, pady=10, sticky="nsew")

        scrollbar = tk.Scrollbar(chat_frame)
        scrollbar.pack(side='right', fill='y')

        self.chat_display = tk.Text(chat_frame, width=50, height=20, 
                                    state='disabled', wrap='word', 
                                    yscrollcommand=scrollbar.set)
        self.chat_display.pack(side='left', padx=(0, 5), fill='both', expand=True)

        scrollbar.config(command=self.chat_display.yview)  # Link scrollbar

        # Right-side controls (buttons + entry fields)
        control_frame = tk.Frame(frame, bg=BG_COLOR)
        control_frame.grid(row=2, column=3, padx=20, sticky="ns")

        def add_placeholder(entry_widget, placeholder_text):
            """ Adds a placeholder to an Entry widget. """
            entry_widget.insert(0, placeholder_text)
            entry_widget.config(fg="gray")  # Makes the text gray for placeholder effect

            def on_focus_in(event):
                if entry_widget.get() == placeholder_text:
                    entry_widget.delete(0, tk.END)
                    entry_widget.config(fg="black")  # Set text color back to black

            def on_focus_out(event):
                if not entry_widget.get():
                    entry_widget.insert(0, placeholder_text)
                    entry_widget.config(fg="gray")  # Restore placeholder color

            entry_widget.bind("<FocusIn>", on_focus_in)
            entry_widget.bind("<FocusOut>", on_focus_out)

        # Delete Account
        delete_acc_btn = tk.Button(control_frame, text='Delete Account', 
                                command=lambda: self._on_delete_account(self.username, self.password))
        delete_acc_btn.grid(row=1, column=0, pady=5, sticky="ew")

        # Delete Messages
        delete_msgs_entry = tk.Entry(control_frame)
        delete_msgs_entry.grid(row=4, column=0, pady=2, sticky="ew")
        delete_btn = tk.Button(control_frame, text="Delete Messages", 
                            command=lambda: self._on_delete_messages(self.username, delete_msgs_entry))
        delete_btn.grid(row=3, column=0, pady=5, sticky="ew")

        # List Accounts
        list_acc_entry = tk.Entry(control_frame)
        list_acc_entry.grid(row=7, column=0, pady=2, sticky="ew")
        list_acc_btn = tk.Button(control_frame, text='List Account', 
                                command=lambda: self._on_list_accounts(list_acc_entry))
        list_acc_btn.grid(row=6, column=0, pady=5, sticky="ew")

        # Fetch Read Messages
        num_read_msgs_entry = tk.Entry(control_frame)
        num_read_msgs_entry.grid(row=10, column=0, pady=2, sticky="ew")
        fetch_read_btn = tk.Button(control_frame, text='See older messages', 
                                bg=BTN_BG_COLOR,
                                command=lambda: self._on_fetch_read_message(num_read_msgs_entry))
        fetch_read_btn.grid(row=9, column=0, pady=5, sticky="ew")

        # Fetch Unread Messages
        num_unread_msgs_entry = tk.Entry(control_frame)
        num_unread_msgs_entry.grid(row=13, column=0, pady=2, sticky="ew")
        fetch_unread_btn = tk.Button(control_frame, text='See new messages', 
                                    command=lambda: self._on_fetch_unread_message(num_unread_msgs_entry))
        fetch_unread_btn.grid(row=12, column=0, pady=5, sticky="ew")

        # Bottom section: Message Entry & Send Button
        input_frame = tk.Frame(frame, bg=BG_COLOR)
        input_frame.grid(row=3, column=0, columnspan=3, pady=15, sticky="nsew")

        receiver_entry = tk.Entry(input_frame)
        receiver_entry.grid(row=1, column=0, padx=10, sticky="ew")
        add_placeholder(receiver_entry, "Recipient username")

        message_entry = tk.Entry(input_frame)
        message_entry.grid(row=1, column=1, padx=10, sticky="ew")
        add_placeholder(message_entry, "Type your message here")

        send_btn = tk.Button(input_frame, text='Send', 
                            command=lambda: self._on_send_message(receiver_entry, message_entry))
        send_btn.grid(row=1, column=2, padx=5, sticky="ew")

        return frame
    
    def setup_list_accounts_frame(self):
        """Set up the list accounts frame with a list of accounts."""
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

    def setup_frames(self):
        """Set up all the frames for the chat application."""
        self.frames["main"] = self.setup_main_frame()
        self.frames["create_account"] = self.setup_create_account_frame()
        self.frames["login"] = self.setup_login_frame()
        self.frames["homepage"] = self.setup_homepage_frame()
        self.frames["list_accounts"] = self.setup_list_accounts_frame()

        for frame in self.frames.values():
            # Place each frame in the same row/column so they overlap
            frame.grid(row=0, column=0, sticky="nsew")

    def show_frame(self, frame_name):
        """Brings the specified frame to the front."""
        self.frames[frame_name].tkraise()
        # self.frames[frame_name].pack()

        # If switching to homepage, refresh messages
        if frame_name == "homepage":
            self.update_homepage_title()
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

        self.messages.sort(key=lambda x: x[4], reverse=False)
        
        # Display in reverse order so newest messages are at the bottom
        for msg in self.messages:
            msg_id, sender, receiver, content, timestamp, _ = msg
            timestamp = timestamp / 1_000_000
            readable_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
            message_text = f"{msg_id}: {sender} -> {receiver} @ {readable_time} | {content}\n\n"
            self.chat_display.insert(tk.END, message_text)
            
        self.chat_display.config(state='disabled')  # Disable editing again
        self.chat_display.see(tk.END)  # Auto-scroll to latest message

    def display_accounts(self):
        """Display messages in chat_display, ordered from oldest to newest."""
        self.accounts_display.config(state='normal')  # Enable editing temporarily
        self.accounts_display.delete(1.0, tk.END)  # Clear old accounts
        for acc in self.accounts:
            id, username = acc
            emoji_idx = random.randint(0, len(EMOJIS) - 1)
            text = f"{EMOJIS[emoji_idx]} {id} : {username}\n"
            self.accounts_display.insert(tk.END, text)

        self.accounts_display.config(state='disabled')  # Disable editing again
        self.accounts_display.see(tk.END)  # Auto-scroll to latest message
    
    def _on_check_username(self, username):
        # Call the server to check if the username exists
        self.send_message(OpCode.ACCOUNT_EXISTS.value, [username.get()])

    def _on_create_account(self, username, password):
        # Call the server to create an account
        self.send_message(OpCode.CREATE_ACCOUNT.value, 
                          [username.get(), self._hash_password(password.get())])

    def _hash_password(self, password):
        # Hash the password before sending it to the server
        return hashlib.sha256(password.encode()).hexdigest()

    def _on_login_account(self, username, password):
        # Call the server to login
        self.username = copy.deepcopy(username.get())
        self.password = password.get()
        self.send_message(OpCode.LOGIN_ACCOUNT.value, 
                          [username.get(), self._hash_password(password.get())])
    
    def _on_delete_account(self, username, password):
        # Call the server to delete the account
        self.send_message(OpCode.DELETE_ACCOUNT.value, [username, password])

    def _on_delete_messages(self, username, delete_msgs):
        # Call the server to delete messages
        delete_msgs = delete_msgs.get().split(",")
        delete_msgs = [int(msg) for msg in delete_msgs] # TODO: find a better way
        self.send_message(OpCode.DELETE_MSG.value, [username, delete_msgs])

    def _on_send_message(self, receiver, message):
        # Call the server to send a message
        self.send_message(OpCode.SEND_MSG.value, [self.username, receiver.get(), message.get()])
        # Clear the message field
        message.delete(0, tk.END)
        receiver.delete(0, tk.END)

    def _on_list_accounts(self, list_acc_entry):
        # Call the server to list accounts
        if list_acc_entry.get() == "":
            self.send_message(OpCode.LIST_ACCOUNTS.value, [])
        else:
            self.send_message(OpCode.LIST_ACCOUNTS.value, list_acc_entry.get())

    def _on_fetch_unread_message(self, num_msgs):
        # Call the server to fetch unread messages
        self.send_message(OpCode.READ_MSG_UNDELIVERED.value, [self.username, int(num_msgs.get())])

    def _on_fetch_read_message(self, num_msgs):
        # Call the server to fetch read messages
        self.send_message(OpCode.READ_MSG_DELIVERED.value, [self.username, int(num_msgs.get())])
# -----------------------------------------------------------------------------
# Main Client Launcher
# -----------------------------------------------------------------------------

def start_connection(host, port, incoming_queue, protocol=0):
    """
    Creates a non-blocking socket, registers it with a selector using
    our client_handler.Message class, and returns (selector, message_obj).
    """
    sel = selectors.DefaultSelector()

    # Create and connect socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)

    try:
        sock.connect((host, port))
    except BlockingIOError:
        pass

    # Build initial request for server
    initial_request = {
        "content_encoding": CONTENT_ENCODING,
        "opcode": OpCode.STARTING.value,
        "content": {"args": []},  # TODO: fragile
    }

    # Create the Message object
    addr = (host, port)
    
    # Use the default or custom protocol
    if not protocol:
        msg_obj = Message(selector=sel, sock=sock, addr=addr, request=initial_request, incoming_queue=incoming_queue)
    else:
        msg_obj = MessageCustom(selector=sel, sock=sock, addr=addr, request=initial_request, incoming_queue=incoming_queue)

    # Register the socket with the selector
    sel.register(sock, selectors.EVENT_READ | selectors.EVENT_WRITE, data=msg_obj)

    return sel, msg_obj

def main(args):
    host = args.host
    port = args.port
    protocol = int(args.protocol)

    # A queue for receiving messages from the server in the main thread
    incoming_queue = queue.Queue()

    # Set up socket + selector + register them with an initial request
    sel, message_obj = start_connection(host, port, incoming_queue, protocol)

    # Create a stop event to shut down the selector thread
    stop_event = threading.Event()

    # Start the background selector thread
    sel_thread = SelectorThread(sel, stop_event, incoming_queue)
    sel_thread.start()

    # Set up client GUI
    root = tk.Tk()
    app = ChatGUI(root, message_obj, incoming_queue, protocol=protocol)

    # Define close loop
    def on_close():
        """Handle cleanup when closing the client window."""
        stop_event.set() # stop selector thread
        message_obj.close() # close socket
        root.destroy() # destroy client gui
    # Set close event as window close
    root.protocol("WM_DELETE_WINDOW", on_close)

    root.mainloop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--protocol", default=PROTOCOL)
    args = parser.parse_args()

    main(args)