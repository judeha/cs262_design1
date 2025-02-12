import selectors
import socket
import sys
import ast
import yaml
import yaml
import traceback
import tkinter as tk
import threading
import libclient
import queue
from codes import ResponseCode, RESPONSE_MESSAGES, OpCode, OPCODE_INPUTS

class Interface:
    def __init__(self, host, port):

        self.queue = queue.Queue()
        #Create and connect socket
        self.addr = (host, port)
        self.sel = selectors.DefaultSelector()
        self.sock, self.events = self.start_connection()
        self.message = libclient.Message(self.sel, self.sock, self.addr, self.queue)
        self.sel.register(self.sock, self.events, data=self.message)
        
        self.root = tk.Tk()
        self.root.title("Multi-Client Chat System")
        self.root.geometry("1000x700")
        self.container = tk.Frame(self.root)
        self.container.pack(fill="both", expand=True)
        self.frames = {}
        self.setup_frames()
        self._show_frame("main")  

        #Start GUI in a separate thread
        listener = threading.Thread(target=self.listen_for_events, daemon=True)
        listener.start()
        self.root.mainloop()

    def start_connection(self):
        print(f"Starting connection to {self.addr}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.connect_ex((host, port))
        events = selectors.EVENT_READ | selectors.EVENT_WRITE

        return sock, events

    def listen_for_events(self):
        '''
        Continues to listen for events and closes socket upon user exit
        '''
        try:
            while True:
                events = self.sel.select(timeout=1)
                print("Main: events", events)
                for key, mask in events: 
                    message = key.data 
                    try:
                        message.process_events(mask)
                    except Exception:
                        print(
                            f"Main: Error: Exception for {message.addr}:\n"
                            f"{traceback.format_exc()}"
                        )
                        message.close()
                # Check for a socket being monitored to continue.
                if not self.sel.get_map():
                    break
        except KeyboardInterrupt:
            print("Caught keyboard interrupt, exiting")
        finally:
            self.sel.close()

    def create_request(self, opcode, args):
        '''
        Create a request with arguments in the correct dict format
        '''
        return dict(
            # byteorder = sys.byteorder,
            # content_type="json",
            content_encoding="utf-8",
            opcode = opcode,
            content={"args": args},
        )
##############################################################################
##############Setting up GUI Frames 
##############################################################################

    def setup_frames(self):
        """Creates and stores all the frames."""
        self.frames["main"] = self.setup_main_frame()
        self.frames["home"] = self.setup_home_frame()
        self.frames["login"] = self.setup_login_frame()
        self.frames["create_account"] = self.setup_create_account_frame()
        self.frames["list_accounts"] = self.setup_list_accounts_frame()

        for frame in self.frames.values():
            frame.place(x=0, y=0, width=500, height=500)

    def setup_main_frame(self):
        """Frame that asks for username"""

        print("IN SETUP MAIN FRAME")

        frame = tk.Frame(self.container)
        tk.Label(frame, text="Username:").pack(pady=5)
        username = tk.Entry(frame)
        username.pack(side='top')

        next_btn = tk.Button(frame, text="Next", command=lambda: self._on_check_username(username))
        next_btn.pack(side='top')

        return frame

    def setup_create_account_frame(self):
        """Frame that asks for the password for the new account"""
        frame = tk.Frame(self.container)
        tk.Label(frame, text="New Password:").pack(pady=5)
        self.new_password_entry = tk.Entry(frame, show="*")
        self.new_password_entry.pack(pady=5)

        create_btn = tk.Button(frame, text='Create', command=lambda: self._on_create_account())
        create_btn.pack(pady=10)

        return frame

    def setup_login_frame(self):
        """Frame that asks for the password to login into existing account"""

        print("SETTING UP THE LOGIN FRAME")
        frame = tk.Frame(self.container)
        tk.Label(frame, text="Password:").pack(pady=5)
        self.password = tk.Entry(frame, show="*")
        self.password.pack(pady=5)

        login_btn = tk.Button(frame, text='Login', command=lambda: self._on_login())
        login_btn.pack(pady=10)

        return frame

    def setup_home_frame(self):

        """Frame that contains the main logic"""

        #TODO: Setup a section for unread messages 
        #TODO: Setup a box for sent messages next to the received messages 
        
        frame = tk.Frame(self.container)
        frame.pack(padx=10, pady=10, fill='both', expand=True)

        # Create a frame for chat display and accounts list (side by side)
        chat_frame = tk.Frame(frame)
        chat_frame.pack(fill='both', expand=True)

        # Chatbox (read-only text widget)
        chat_display = tk.Text(chat_frame, width=50, height=20, state='disabled', wrap='word')
        chat_display.pack(side='left', padx=(0, 5), fill='both', expand=True)

        # Frame for message input and buttons (placed below chat_frame)
        input_frame = tk.Frame(frame)
        input_frame.pack(fill='x', pady=(10, 0))

        # Message input field
        message_entry = tk.Entry(input_frame)
        message_entry.pack(side='left', padx=10, fill="x", expand=True)

        # Send button
        send_btn = tk.Button(input_frame, text='Send', 
                             command=lambda: self._on_send_message)
        send_btn.pack(side='left', padx=5)

        list_acc_btn = tk.Button(input_frame, text='List Accounts', 
                             command=lambda: self._show_frame("list_accounts"))
        list_acc_btn.pack(side='left', padx=5)

        return frame

    def setup_list_accounts_frame(self):
        '''
        Lists all the accounts on the application
        '''
        frame = tk.Frame(self.container)
        frame.pack(padx=10, pady=10, fill='both', expand=True)

        # Create a frame for chat display and accounts list (side by side)
        accs_frame = tk.Frame(frame)
        accs_frame.pack(fill='both', expand=True)

        # Delete Account button
        delete_acc_btn = tk.Button(accs_frame, text='Delete Account', 
                                   command=lambda: self._on_delete_account())
        delete_acc_btn.pack(side='left', padx=5)

        home_btn = tk.Button(accs_frame, text='Home', 
                                   command=lambda: self._show_frame("home"))
        home_btn.pack(side='left', padx=5)

        return frame
  
    def update_home_frame(self):
        '''
        Messages: 
            - Show unread messages
            - Send messages
            - Receive messages

        Account:
            - Another client deletes their account
            - Current client deletes their account
        '''
        pass

    def update_acc_frame(self):
        '''
        Delete account
        Other clients create accounts 
        '''

##############################################################################
##############Helper Functions
##############################################################################
    def process_queue(self):
        '''
        Processes server responses from Queue and updates UI accordingly
        '''

        while not self.queue.empty():
            message = self.queue.get()
            print(f"Processing message from queue: {message}")

            opcode = message["opcode"]
            status_code = message["status_code"]
            data = message["data"]

            if opcode == OpCode.ACCOUNT_EXISTS.value and status_code == ResponseCode.SUCCESS:
                print("From server: the account exists!")
                self.setup_login_frame() 
            else: self.setup_create_account_frame()

            if status_code != ResponseCode.SUCCESS.value: pass
            else:
                if opcode == OpCode.CREATE_ACCOUNT.value:
                    self._show_frame["home"]
                elif opcode == OpCode.LOGIN_ACCOUNT.value:
                    self._show_frame["home"]
                elif opcode == OpCode.DELETE_ACCOUNT.value:
                    self.update_home_frame()
                    self._show_frame["main"]
                elif opcode == OpCode.LIST_ACCOUNTS.value:
                    self._show_frame["list_accounts"]
                elif opcode == OpCode.LOGOUT_ACCOUNT.value:
                    pass
                elif opcode == OpCode.READ_MSG_DELIVERED.value:
                    print("Here are your messages: ", data[1:])
                    print("You have ", data[0], " unread messages.")
                    self.update_home_frame()
                    self._show_frame["home"]
                elif opcode == OpCode.READ_MSG_UNDELIVERED.value:
                    print("Here are your messages: ", data[1])
                    print("You have ", data[0], " unread messages.")
                    self.update_home_frame()
                    self._show_frame["home"]
                elif opcode == OpCode.DELETE_MSG.value:
                    self.update_home_frame()
                    self._show_frame["home"]
                elif opcode == OpCode.HOMEPAGE.value:
                    print("Here are your messages: ", data[1:])
                    print("You have ", data[0], " unread messages.")
                    self._show_frame["home"]
                elif opcode == "send_msg":
                    self._show_frame["home"]
                elif opcode == "receive_msg":
                    print("You have a new message. Here are your messages: ", data)
                    self._show_frame["home"]
                else:
                    print("Unknown opcode")

        self.root.after(100, self.process_queue)

    def _show_frame(self, frame_name):
        """Brings the specified frame to the front."""
        self.frames[frame_name].tkraise()

    def _on_check_username(self, username):
        """Handles username checking action."""
        # print("ON CHECK USERNAME")
        username = username.get()
        # if not username: 
        #     print("Error: Username cannot be empty")
        #     return
        
        request = self.create_request(OpCode.ACCOUNT_EXISTS.value, [username])
        self.message._set_selector_events_mask("w")
        self.message.queue_request(request)
        self.message.write()

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

    def _on_login(self):
        '''handles login request. validates password!!'''
        pass

    def _on_delete_message(self):
        pass

    def _on_delete_account(self):
        pass

    def _on_send_message(self):
        pass

    def _on_read_message(self):
        pass

    def _on_list_account(self):
        pass

if __name__ == "__main__":

    # Read config file 
    yaml_path = "config.yaml"

    with open(yaml_path) as y:
        config_dict = yaml.safe_load(y)

    version = config_dict["version"]
    key = config_dict["key"]
    db_path = config_dict["db_path"]

    #Get the appropriate arguments
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <host> <port>")
        sys.exit(1)

    host, port = sys.argv[1], int(sys.argv[2])

    #Start the GUI
    gui = Interface(host, port)

    # TODO: transform tkinter gui to args
    # action, args = sys.argv[3], sys.argv[4]
    # args = ast.literal_eval(args) 
    # request = create_request(action, args)

#TODO: ERROR Check and just display the error message
    