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
import grpc
import handler_pb2
import handler_pb2_grpc
from concurrent import futures
import google.protobuf.empty_pb2

# Configure logging
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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
# Background Thread: manages receiving messages
# -----------------------------------------------------------------------------
class GRPCClient:
    def __init__(self, server_address):
        """Initialize the gRPC client and start a background thread for receiving messages."""
        self.server_address = server_address
        self.channel = grpc.insecure_channel(self.server_address)
        self.stub = handler_pb2_grpc.HandlerStub(self.channel)

        # Queue for incoming messages (thread-safe)
        self.incoming_queue = queue.Queue()

        # Start the background thread for receiving messages
        self.stop_event = threading.Event()
        self.receiver_thread = threading.Thread(target=self._receive_messages, daemon=True)
        self.receiver_thread.start()

    def _receive_messages(self):
        """Continuously listens for new messages from the server."""
        try:
            for response in self.stub.ReceiveMessage(google.protobuf.empty_pb2.Empty()): # TODO change input
                if self.stop_event.is_set():
                    break  # Stop thread if the event is triggered
                
                # Add received messages to the queue
                self.incoming_queue.put((response.sender, response.content))

        except grpc.RpcError as e:
            print(f"Stream closed with error: {e}")

    def get_incoming_messages(self):
        """Retrieve messages from the queue in a non-blocking way."""
        messages = []
        while not self.incoming_queue.empty():
            messages.append(self.incoming_queue.get())
        return messages

    def stop(self):
        """Gracefully stop the client and close the connection."""
        self.stop_event.set()
        self.channel.close()
    
    def check_account(self, username):
        """Check if the account exists."""
        return self.stub.CheckAccountExists(handler_pb2.AccountExistsRequest(username=username))
    
    def create_account(self, username, password, bio):
        """Create a new account."""
        return self.stub.CreateAccount(handler_pb2.CreateAccountRequest(username=username, password=password, bio=bio))
    
    def login(self, username, password):
        """Login to an existing account."""
        return self.stub.LoginAccount(handler_pb2.LoginAccountRequest(username=username, password=password))
    
    def delete_account(self, username, password):
        """Delete an existing account."""
        return self.stub.DeleteAccount(handler_pb2.DeleteAccountRequest(username=username, password=password))
    
    def list_accounts(self, pattern):
        """List all accounts matching the pattern."""
        return self.stub.ListAccount(handler_pb2.ListAccountRequest(pattern=pattern))
    
    def delete_messages(self, username, msg_ids):
        """Delete messages by ID."""
        return self.stub.DeleteMessage(handler_pb2.DeleteMessageRequest(username=username, msg_ids=msg_ids))
    
    def send_message(self, sender, receiver, content):
        """Send a message to a recipient."""
        return self.stub.SendMessage(handler_pb2.SendMessageRequest(sender=sender, receiver=receiver, content=content))
    
    def fetch_unread_messages(self, username, num_msgs):
        """Fetch unread messages."""
        return self.stub.FetchMessagesUnread(handler_pb2.FetchMessagesUnreadRequest(username=username, num_msgs=num_msgs))
    
    def fetch_read_messages(self, username, num_msgs):
        """Fetch read messages."""
        return self.stub.FetchMessagesRead(handler_pb2.FetchMessagesReadRequest(username=username, num_msgs=num_msgs))
    
    def fetch_homepage(self, username):
        """Fetch the homepage."""
        return self.stub.FetchHomepage(handler_pb2.FetchHomepageRequest(username=username))

# -----------------------------------------------------------------------------
# GUI Class: basic chat window
# -----------------------------------------------------------------------------

class ChatGUI:
    """
    A client GUI that displays incoming messages and sends new requests.
    """
    def __init__(self, root, grpc_client):
        """
        :param root: Tk root
        :param message_obj: The client_handler.Message instance handling socket I/O
        :param incoming_queue: queue.Queue for receiving updates from the server
        """
        self.root = root
        self.grpc_client = grpc_client

        # Set up the main window
        self.root.title("MyChat")
        self.root.geometry(UI_DIMENSIONS) 
        self.container = tk.Frame(root, bg=BG_COLOR)
        self.container.pack(expand=True, fill=tk.BOTH)

        # Initialize chat display variables
        # Global error label (always visible)
        self.error_label = tk.Label(self.container, text="", fg="red", bg=BG_COLOR)
        self.error_label.grid(row=1, column=0, pady=10)
        self.messages = []
        self.count = 0
        self.accounts = []
        self.username = ""
        self.nemesis = []

        # Set up all wireframes
        self.frames = {}
        self.setup_frames()
        self.show_frame("main") # Show the main frame initially

        # Periodically poll the incoming queue
        self.poll_incoming()

    def poll_incoming(self):
        """
        Check the thread-safe queue for incoming server responses
        and update the chat display accordingly.
        """
        while not self.grpc_client.incoming_queue.empty():
            response = self.grpc_client.incoming_queue.get()
            # If receiving message, update messages and stay on homepage
            if isinstance(response, handler_pb2.ReceiveMessageResponse):
                self.messages += response.msg_lst
                if len(self.messages) > MAX_VIEW:
                    self.messages.pop(0)
                self.show_frame("homepage")

        # Schedule next poll
        self.root.after(2, self.poll_incoming) # TODO: put in config
    
    def setup_main_frame(self):
        """Set up the main frame with a simple welcome message."""        
        frame = tk.Frame(self.container, bg=BG_COLOR)

        # Messages
        tk.Label(frame, text="Welcome to MyChat! Check if you have an account.").pack(pady=10)

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

        # Username, password, bio entry fields
        tk.Label(frame, text="Username:").pack(pady=5)
        username = tk.Entry(frame)
        username.pack(pady=5)
        tk.Label(frame, text="Password:").pack(pady=5)
        password = tk.Entry(frame, show="*")
        password.pack(pady=5)
        tk.Label(frame, text="Bio:").pack(pady=5)
        bio = tk.Entry(frame)
        bio.pack(pady=5)

        # Next button
        create_btn = tk.Button(frame, text="Create", command=lambda: self._on_create_account(username, password, bio))
        create_btn.pack(pady=10)

        return frame
    
    def setup_login_frame(self):
        """Set up the login frame with username and password fields."""
        frame = tk.Frame(self.container, bg=BG_COLOR)

        # Messages
        tk.Label(frame, text="Enter your username and password to login").pack(pady=10)

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

        ## Find my nemesis
        # match_btn = tk.Button(control_frame, text='Find my nemesis', 
        #                     command=lambda: self.send_message(OpCode.MATCH.value, [self.username]))
        # match_btn.grid(row=15, column=0, pady=5, sticky="ew")

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

    def setup_nemesis_frame(self):
        """Set up the nemesis frame with information about your nemesis."""
        frame = tk.Frame(self.container, bg=BG_COLOR)
        tk.Label(frame, text="Your Nemesis", font=("Arial", 14, "bold"), fg="white", bg=BG_COLOR).pack(pady=5)

        # Create a frame for displaying nemesis information
        nemesis_frame = tk.Frame(frame, bg=BG_COLOR)
        nemesis_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Chatbox (read-only text widget)
        self.nemesis_display = tk.Text(nemesis_frame, width=50, height=10, state='disabled', wrap='word', bg="black", fg="white")
        self.nemesis_display.pack(fill='both', expand=True)

        # Home button
        home_btn = tk.Button(frame, text='Homepage', command=lambda: self.show_frame("homepage"))
        home_btn.pack(pady=10)

        return frame
        
    def display_nemesis(self, nemesis_data):
        """Displays match results in the text widget."""
        self.nemesis_display.config(state='normal')  # Enable editing temporarily
        self.nemesis_display.delete(1.0, tk.END)  # Clear old accounts
        username, bio = nemesis_data[0]
        percentage = nemesis_data[1]
        text = f"Your worst nemesis is {username}\nBio: {bio}\nYou and {username} are a {percentage}% match to be nemeses for life.\n"
        self.nemesis_display.insert(tk.END, text)

        self.nemesis_display.config(state='disabled')  # Disable editing again
        self.nemesis_display.see(tk.END)  # Auto-scroll to latest message       

    def setup_frames(self):
        """Set up all the frames for the chat application."""
        self.frames["main"] = self.setup_main_frame()
        self.frames["create_account"] = self.setup_create_account_frame()
        self.frames["login"] = self.setup_login_frame()
        self.frames["homepage"] = self.setup_homepage_frame()
        self.frames["list_accounts"] = self.setup_list_accounts_frame()
        self.frames["nemesis"] = self.setup_nemesis_frame()

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

        if frame_name == "nemesis":
            self.display_nemesis(self.nemesis)

    def display_error(self, message):
        """ Displays an error message in the global error label. """
        self.error_label.config(text=message)
    
    def display_messages(self):
        """Display messages in chat_display, ordered from oldest to newest."""
        self.chat_display.config(state='normal')  # Enable editing temporarily
        self.chat_display.delete(1.0, tk.END)  # Clear old messages

        self.chat_display.insert(tk.END, f"Unread messages: {self.count}\n\n")

        self.messages.sort(key=lambda x: x[4], reverse=False)
        
        # Display in reverse order so newest messages are at the bottom
        for msg in self.messages:
            msg_id = msg.msg_id
            sender = msg.sender
            receiver = msg.receiver
            content = msg.content
            timestamp = msg.timestamp 

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
            id = acc.id
            username = acc.username
            bio = acc.bio
            
            emoji_idx = random.randint(0, len(EMOJIS) - 1)
            text = f"{id}) {username} {EMOJIS[emoji_idx]} : {bio}\n\n"
            self.accounts_display.insert(tk.END, text)

        self.accounts_display.config(state='disabled')  # Disable editing again
        self.accounts_display.see(tk.END)  # Auto-scroll to latest message
    
    def _on_check_username(self, username):
        status_code, exists = self.grpc_client.check_account(username.get())
        if exists:
            self.display_error("Account already exists")
            return
        self.show_frame("create_account")

            #         # Check response type using isinstance()
            # if isinstance(response, handler_pb2.StartingResponse):
            #     self.show_frame("main")
            # elif isinstance(response, handler_pb2.AccountExistsResponse) and response.status_code != ResponseCode.SUCCESS.value:
            #     self.display_error(RESPONSE_MESSAGES.get(response.status_code, "Unknown error"))
            # else:
            #     self.display_error("")
                # If new user, create account
                # if isinstance(response, handler_pb2.AccountExistsResponse) and response.status_code == ResponseCode.ACCOUNT_NOT_FOUND.value:
                #     self.show_frame("create_account")
                # # If existing user, login
                # # elif isinstance(response, handler_pb2.AccountExistsResponse) and response.status_code == ResponseCode.ACCOUNT_EXISTS.value:
                #     self.show_frame("login")
                # # If account creation successful, login
                # elif isinstance(response, handler_pb2.CreateAccountResponse) and response.status_code == ResponseCode.SUCCESS.value:
                #     self.show_frame("login")
                # # If operation requires homepage to be fetched, show homepage
                # elif isinstance(response, handler_pb2.LoginAccountResponse) or isinstance(response, handler_pb2.FetchHomepageResponse) or isinstance(response, handler_pb2.FetchMessagesUnreadResponse) or isinstance(response, handler_pb2.DeleteMessageResponse):
                #     self.count = response.count
                #     self.messages = response.msg_lst
                #     self.show_frame("homepage")
                # # If listing accounts, show accounts
                # elif isinstance(response, handler_pb2.ListAccountResponse):
                #     self.accounts = response.acct_lst
                #     self.show_frame("list_accounts")
                # # If account deletion successful, show main
                # elif isinstance(response, handler_pb2.DeleteAccountResponse):
                #     self.show_frame("main")
                # # If fetching archived messages, extend homepage length
                # elif isinstance(response, handler_pb2.FetchMessagesReadResponse):
                #     self.messages = response.msg_lst
                #     self.show_frame("homepage")
                # # If sending message, stay on homepage
                # elif isinstance(response, handler_pb2.SendMessageResponse):
                #     self.show_frame("homepage")


    def _on_create_account(self, username, password, bio):
        # Call the server to create an account
        self.send_message(OpCode.CREATE_ACCOUNT.value, 
                          [username.get(), self._hash_password(password.get()), bio.get()])

    def _hash_password(self, password):
        # Hash the password before sending it to the server
        return hashlib.sha256(password.encode()).hexdigest()

    def _on_login_account(self, username, password):
        # Call the server to login
        self.username = copy.deepcopy(username.get())
        self.password = password.get()
        self.send_message(OpCode.LOGIN_ACCOUNT.value, 
                          [username.get(), self._hash_password(password.get())])
        
        # TODO: 
    def _on_login_account(self, username, password):
        """Login and start message streaming."""
        self.username = username.get()
        self.password = password.get()
        
        status_code, count, messages = self.grpc_client.login(self.username, self._hash_password(password.get()))
        if status_code != ResponseCode.SUCCESS.value:
            self.display_error("Invalid username or password")
            return
        
        self.count = count
        self.messages = messages
        self.show_frame("homepage")

        # Start receiving messages
        threading.Thread(target=self.grpc_client.receive_messages, args=(self.username, self.display_messages), daemon=True).start()

    
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

def main(args):
    host = args.host
    port = args.port

    # Set up grpc object (client stub)
    grpc_client = GRPCClient(host, port)

    # Set up client GUI
    root = tk.Tk()
    app = ChatGUI(root, grpc_client)

    # Define close loop
    def on_close():
        """Handle cleanup when closing the client window."""
        grpc_client.stop()  # Stop gRPC client
        root.destroy()
    # Set close event as window close
    root.protocol("WM_DELETE_WINDOW", on_close)

    root.mainloop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    main(args)
