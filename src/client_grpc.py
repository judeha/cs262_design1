#!/usr/bin/env python3
import argparse
import yaml
import copy
import threading
import tkinter as tk
import time
import queue
import hashlib
from utils import ResponseCode, RESPONSE_MESSAGES
import random
import grpc
import handler_pb2
import handler_pb2_grpc
from grpc import RpcError

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
LIVE_SERVERS = config['live_servers']
LEADER_ID = config['leader_id']
PROTOCOL = config['protocol']
UI_DIMENSIONS = config['ui_dimensions']
CONTENT_ENCODING = config['encoding']
EMOJIS = config['emojis']
MAX_VIEW = config["max_view"]
POLL_INTERVAL = 3

# -----------------------------------------------------------------------------
# Background Thread: manages receiving messages
# -----------------------------------------------------------------------------
class GRPCClient:
    def __init__(self, live_servers, leader_id):
        """Initialize the gRPC client and start a background thread for receiving messages."""

        self.live_servers = live_servers
        self.leader_id = leader_id

        self.channel = grpc.insecure_channel(self.live_servers[leader_id])
        self.stub = handler_pb2_grpc.HandlerStub(self.channel)
        self.username = None

        # Queue for incoming messages (thread-safe)
        self.incoming_queue = queue.Queue()

        # Start the background thread for receiving messages
        self.stop_event = threading.Event()
        self.receiver_thread = None

    def _failover_to_leader(self, new_leader_addr):
        """Connect to the new leader given that we are connected to the wrong server"""

        print(f"Failing over to new leader at {new_leader_addr}")
        self.channel.close()
        self.channel = grpc.insecure_channel(new_leader_addr)
        self.stub = handler_pb2_grpc.HandlerStub(self.channel)

    def _find_new_leader(self):
        """Continues to ping the servers until the new leader's address provided"""

        response = self.stub.NewLeader(handler_pb2.NewLeaderResponse(new_leader_id=self.leader_id))
        return response.new_leader_id - 1

    def _start_stream(self):
        if self.receiver_thread is not None:
            return
        self.receiver_thread = threading.Thread(target=self._receive_messages, daemon=True)
        self.receiver_thread.start()

    def _receive_messages(self):
        """Continuously read streaming responses from server."""
        if not self.username:
            return
        try:
            request = handler_pb2.ReceiveMessageRequest(username=self.username)
            for response in self.stub.ReceiveMessage(request):
                # each response is a ReceiveMessageResponse with repeated msg_lst
                for msg in response.msg_lst:
                    self.incoming_queue.put(msg)
        except grpc.RpcError as e:
            return
        
    def poll_leader(self):
        """Background thread that checks that the client is still connected to an active leader"""
        while not self.stop_event.is_set():
            try:
                response = self.stub.Status(handler_pb2.Empty())
                if self.leader_id != response.current_leader_id: 
                    print(f"Current server is not leader!")
                    self.failover_to_leader(self.live_servers[response.current_leader_id])
            except RpcError as e:
                print(f"Lost connection to leader: {e}")
                self._find_new_leader()
            time.sleep(POLL_INTERVAL)

        
    def send_message(self, receiver, content):
        """Send a message (unary call)."""
        if not self.username:
            return
        req = handler_pb2.SendMessageRequest(sender=self.username, receiver=receiver, content=content)
        resp = self.stub.SendMessage(req)
        return resp

    def get_new_messages(self):
        """Retrieve any messages from the local queue."""
        messages = []
        while not self.incoming_queue.empty():
            m = self.incoming_queue.get()
            if isinstance(m, handler_pb2.Message):
                messages.append(m)
        return messages

    def stop(self):
        """Gracefully stop the client and close the connection."""
        _ = self.stub.Ending(handler_pb2.EndingRequest(username=self.username))
        self.stop_event.set()
        self.channel.close()
    
    def check_account(self, username):
        """Check if the account exists."""
        return self.stub.CheckAccountExists(handler_pb2.AccountExistsRequest(username=username))
    
    def create_account(self, username, password, bio):
        """Create a new account."""
        return self.stub.CreateAccount(handler_pb2.CreateAccountRequest(username=username, password=password, bio=bio))
    
    def login(self, username, password):
        """Login to the server, creates a queue on the server side."""
        self.username = username
        req = handler_pb2.LoginAccountRequest(username=username, password=password)
        resp = self.stub.LoginAccount(req)
        # store any initial messages
        for msg in resp.msg_lst:
            self.incoming_queue.put((msg.sender, msg.content))
        # start streaming thread
        self._start_stream()
        return resp
    
    def delete_account(self, username, password):
        """Delete an existing account."""
        return self.stub.DeleteAccount(handler_pb2.DeleteAccountRequest(username=username, password=password))
    
    def list_accounts(self, pattern=None):
        """List all accounts matching the pattern."""
        return self.stub.ListAccount(handler_pb2.ListAccountRequest(pattern=pattern))
    
    def delete_messages(self, username, msg_ids):
        """Delete messages by ID."""
        return self.stub.DeleteMessage(handler_pb2.DeleteMessageRequest(username=username, message_id_lst=msg_ids))
    
    def send_message(self, sender, receiver, content):
        """Send a message to a recipient."""
        return self.stub.SendMessage(handler_pb2.SendMessageRequest(sender=sender, receiver=receiver, content=content))
    
    def fetch_unread_messages(self, username, num_msgs):
        """Fetch unread messages."""
        return self.stub.FetchMessageUnread(handler_pb2.FetchMessagesUnreadRequest(username=username, num=num_msgs))
    
    def fetch_read_messages(self, username, num_msgs):
        """Fetch read messages."""
        return self.stub.FetchMessageRead(handler_pb2.FetchMessagesReadRequest(username=username, num=num_msgs))
    
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
        """Check for new messages in local queue."""
        new_msgs = self.grpc_client.get_new_messages()
        self.messages.extend(new_msgs)
        if len(new_msgs) > MAX_VIEW:
            self.messages = self.messages[-MAX_VIEW:]
        self.display_messages()

        # Schedule next poll
        self.root.after(500, self.poll_incoming) # TODO: put in config
    
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

        self.messages.sort(key=lambda x: x.timestamp, reverse=False)
        
        # Display in reverse order so newest messages are at the bottom
        for msg in self.messages:
            msg_id = msg.id
            sender = msg.sender
            receiver = msg.receiver
            content = msg.content
            timestamp = msg.timestamp
            # timestamp = timestamp / 1_000_000
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
            # id, username, bio = acc
            emoji_idx = random.randint(0, len(EMOJIS) - 1)
            text = f"{id}) {username} {EMOJIS[emoji_idx]} : {bio}\n\n"
            self.accounts_display.insert(tk.END, text)

        self.accounts_display.config(state='disabled')  # Disable editing again
        self.accounts_display.see(tk.END)  # Auto-scroll to latest message
    
    def _on_check_username(self, username):
        response = self.grpc_client.check_account(username.get())
        if response.exists:
            # self.display_error("Account already exists")
            self.show_frame("login")
            return
        self.show_frame("create_account")

    def _on_create_account(self, username, password, bio):
        # Call the server to create an account
        response = self.grpc_client.create_account(username.get(), self._hash_password(password.get()), bio.get())
        if response.status_code != ResponseCode.SUCCESS.value:
            self.display_error(RESPONSE_MESSAGES[response.status_code])
            return
        # Clear the message field
        username.delete(0, tk.END)
        self.show_frame("login")

    def _hash_password(self, password):
        # Hash the password before sending it to the server
        return hashlib.sha256(password.encode()).hexdigest()

    def _on_login_account(self, username, password):
        # Call the server to login
        self.username = copy.deepcopy(username.get()) 
        self.password = copy.deepcopy(password.get())    
        response = self.grpc_client.login(self.username, self._hash_password(password.get()))
        if response.status_code != ResponseCode.SUCCESS.value:
            self.display_error("Invalid username or password")
            return
        
        self.grpc_client.username = self.username
        self.poll_incoming()
        self.display_error("")
        
        # Clear the message field
        username.delete(0, tk.END)
        password.delete(0, tk.END)
        
        self.count = response.count
        self.messages = response.msg_lst
        self.show_frame("homepage")
    
    def _on_delete_account(self, username, password):
        # Call the server to delete the account
        response = self.grpc_client.delete_account(username, self._hash_password(password))
        if response.status_code != ResponseCode.SUCCESS.value:
            self.display_error(RESPONSE_MESSAGES[response.status_code])
            return
        self.show_frame("main")

    def _on_delete_messages(self, username, delete_msgs):
        # Call the server to delete messages
        delete_msgs = delete_msgs.get().split(",")
        delete_msgs = [int(msg) for msg in delete_msgs]
        response = self.grpc_client.delete_messages(username, delete_msgs)
        if response.status_code != ResponseCode.SUCCESS.value:
            self.display_error(RESPONSE_MESSAGES[response.status_code])
            return
        self.count = response.count
        self.messages = response.msg_lst
        self.show_frame("homepage")

    def _on_send_message(self, receiver, message):
        # Call the server to send a message
        self.grpc_client.send_message(self.username, receiver.get(), message.get())
        # Clear the message field
        message.delete(0, tk.END)
        receiver.delete(0, tk.END)

    def _on_list_accounts(self, list_acc_entry):
        # Call the server to list accounts
        if list_acc_entry.get() == "":
            response = self.grpc_client.list_accounts()
        else:
            response = self.grpc_client.list_accounts(list_acc_entry.get())
        if response.status_code != ResponseCode.SUCCESS.value:
            self.display_error(RESPONSE_MESSAGES[response.status_code])
            return
        self.accounts = response.acct_lst
        self.show_frame("list_accounts")

    def _on_fetch_unread_message(self, num_msgs):
        # Call the server to fetch unread messages
        response = self.grpc_client.fetch_unread_messages(self.username, int(num_msgs.get()))
        if response.status_code != ResponseCode.SUCCESS.value:
            self.display_error(RESPONSE_MESSAGES[response.status_code])
            return
        self.count = response.count
        self.messages = response.msg_lst
        self.show_frame("homepage")

    def _on_fetch_read_message(self, num_msgs):
        # Call the server to fetch read messages
        response = self.grpc_client.fetch_read_messages(self.username, int(num_msgs.get()))
        if response.status_code != ResponseCode.SUCCESS.value:
            self.display_error(RESPONSE_MESSAGES[response.status_code])
            return
        self.messages = response.msg_lst
        self.show_frame("homepage")
# -----------------------------------------------------------------------------
# Main Client Launcher
# -----------------------------------------------------------------------------

def main(args):
    # host = args.host
    # port = args.port
    live_servers = args.live_servers
    leader_id = args.leader_id

    # Set up grpc object (client stub)

    grpc_client = GRPCClient(live_servers, leader_id)

    # Set up client GUI
    root = tk.Tk()
    app = ChatGUI(root, grpc_client)

    grpc_client.poll_leader()

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
    # parser.add_argument("--host", default=HOST)
    # parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--live_servers", default=LIVE_SERVERS)
    parser.add_argument("--leader_id", default=LEADER_ID)

    args = parser.parse_args()

    main(args)
