import tkinter as tk
import ast

class Interface:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Multi-Client Chat System")
        self.root.geometry("1000x700")

        self.container = tk.Frame(self.root)
        self.container.pack(fill="both", expand=True)

        self.frames = {}
        self.setup_frames()
        self.show_frame("main")  # Show the main frame initially

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

        next_btn = tk.Button(frame, text="Next", command=lambda: self.show_frame("login"))
        next_btn.pack(side='top')

        return frame

    def setup_create_account_frame(self):
        """Frame that asks for the password for the new account"""
        frame = tk.Frame(self.container)
        tk.Label(frame, text="New Password:").pack(pady=5)
        self.new_password_entry = tk.Entry(frame, show="*")
        self.new_password_entry.pack(pady=5)

        create_btn = tk.Button(frame, text='Create', command=lambda: self.show_frame("home"))
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