#!/usr/bin/env python3
import argparse
import socket
import selectors
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext
import queue

# Adjust the following import paths as needed:
# from libclient import Message
from codes import OpCode, ResponseCode  # If you need these enums
import yaml
import struct
import json
from libclient import Message

# -----------------------------------------------------------------------------
# Background Thread: Manages the Selector Event Loop
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
            # Optional: other periodic tasks...

        # Cleanup when stop_event is triggered
        self.sel.close()

# -----------------------------------------------------------------------------
# GUI Class: Basic Chat Window
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
        self.root.geometry("1000x700")
        self.message_obj = message_obj
        self.incoming_queue = incoming_queue

        # Set up the main window
        self.root.title("Selector-Based Client")
        self.container = tk.Frame(root)
        self.container.pack(expand=True, fill=tk.BOTH)
        # self.container.pack(side="top", fill="both", expand=True)

        # self.setup_main_frame()
        self.frames = {}
        self.setup_frames()
        self.show_frame("main") # show the main frame initially

        # # Text widget for displaying chat / server responses
        # self.chat_display = scrolledtext.ScrolledText(self.frame, wrap=tk.WORD, state='disabled')
        # self.chat_display.pack(side=tk.TOP, expand=True, fill=tk.BOTH)

        # # Entry + send button
        # self.entry_frame = tk.Frame(self.frame)
        # self.entry_frame.pack(side=tk.BOTTOM, fill=tk.X)

        # self.input_field = tk.Entry(self.entry_frame)
        # self.input_field.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # self.send_button = tk.Button(self.entry_frame, text="Send", command=lambda: self.send_message(OpCode.SEND_MSG.value, ["message"]))
        # self.send_button.pack(side=tk.RIGHT)

        # Periodically poll the incoming queue
        self.poll_incoming()

    def send_message(self, opcode, args):
        """
        Sends a request to the server using the existing `message_obj`.
        For example, we might send an OpCode.SEND_MSG request or something else.
        """
        # msg_text = self.input_field.get().strip()
        # self.input_field.delete(0, tk.END)
        # print("ARGS", args)

        if opcode is not None:
            # Here is where you craft the request dictionary that your `Message` object expects
            request = dict(
                content_encoding= "utf-8", # TODO: put in config
                opcode=opcode,  # Example usage
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
                
                opcode = response_str["opcode"]
                status_code = response_str["status_code"]
                data = response_str["data"]

                if opcode != OpCode.ACCOUNT_EXISTS.value and status_code != ResponseCode.SUCCESS.value:
                    print("HERE")
                    pass # TODO: display error
                else:
                    if opcode == OpCode.ACCOUNT_EXISTS.value and status_code != ResponseCode.SUCCESS.value:
                        self.show_frame("create_account") # TODO: replace with opcode
                    elif opcode == OpCode.ACCOUNT_EXISTS.value and status_code == ResponseCode.SUCCESS.value:
                        self.show_frame("login")
                    elif opcode == OpCode.CREATE_ACCOUNT.value:
                        self.show_frame("login")
                    elif opcode == OpCode.LOGIN_ACCOUNT.value:
                        self.show_frame("homepage")
                    elif opcode == OpCode.LIST_ACCOUNTS.value:
                        pass
                    elif opcode == OpCode.DELETE_ACCOUNT.value:
                        pass
                    elif opcode == OpCode.HOMEPAGE.value:
                        pass
                    elif opcode == OpCode.READ_MSG_UNDELIVERED.value:
                        pass
                    elif opcode == OpCode.READ_MSG_DELIVERED.value:
                        pass
                    elif opcode == OpCode.DELETE_MSG.value:
                        pass
                    elif opcode == OpCode.SEND_MSG.value:
                        pass
                    elif opcode == OpCode.RECEIVE_MSG.value:
                        pass
                    elif opcode == OpCode.LOGOUT_ACCOUNT.value:
                        pass

            except queue.Empty:
                break
            else:
                pass
                # self._append_chat(response_str)

        # Schedule next poll
        self.root.after(2, self.poll_incoming)
    
    def setup_main_frame(self):
        frame = tk.Frame(self.container)
        tk.Label(frame, text="Username:").pack(pady=5)
        username = tk.Entry(frame)
        username.pack(side='top')

        next_btn = tk.Button(frame, text="Next", command=lambda: self.on_check_username(username))
        next_btn.pack(side='top') # TODO: handle initial request bc right now it skips the first frame

        return frame
    
    def setup_create_account_frame(self):
        frame = tk.Frame(self.container)
        tk.Label(frame, text="Username:").pack(pady=5)
        username = tk.Entry(frame)
        username.pack(pady=5) # TODO: should these all be self?
        tk.Label(frame, text="Password:").pack(pady=5)
        password = tk.Entry(frame, show="*")
        password.pack(pady=5)

        create_btn = tk.Button(frame, text="Create", command=lambda: self._on_create_account(username, password))
        create_btn.pack(pady=10)

        return frame
    
    def setup_login_frame(self):
        frame = tk.Frame(self.container)
        tk.Label(frame, text="Username:").pack(pady=5)
        username = tk.Entry(frame)
        username.pack(pady=5)
        tk.Label(frame, text="Password:").pack(pady=5)
        password = tk.Entry(frame, show="*")
        password.pack(pady=5)

        login_btn = tk.Button(frame, text="Login", command=lambda: self._on_login_account(username, password))
        login_btn.pack(pady=10)
        
        return frame


    def setup_homepage_frame(self):
        frame = tk.Frame(self.container)
        # frame.pack(padx=10, pady=10, fill='both', expand=True)
        tk.Label(frame, text="Homepage").pack(pady=5)

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
        send_btn = tk.Button(input_frame, text='Send', command=lambda: self.show_frame("home"))
        send_btn.pack(side='left', padx=5)

        # Delete Account button
        delete_acc_btn = tk.Button(input_frame, text='Delete Account', command=lambda: self.show_frame("accounts"))
        delete_acc_btn.pack(side='left', padx=5)

        return frame

    def setup_frames(self):
        self.frames["main"] = self.setup_main_frame()
        self.frames["create_account"] = self.setup_create_account_frame()
        self.frames["login"] = self.setup_login_frame()
        self.frames["homepage"] = self.setup_homepage_frame()

        for frame in self.frames.values():
            # Place each frame in the same row/column so they overlap
            frame.grid(row=0, column=0, sticky="nsew")


    def show_frame(self, frame_name):
        """Brings the specified frame to the front."""
        self.frames[frame_name].tkraise()
        # self.frames[frame_name].pack()

    def _append_chat(self, text):
        """Helper to insert text into the chat display."""
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, text + "\n")
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)

    def _on_check_username(self, username):
        # Check if username exists
        self.send_message(OpCode.ACCOUNT_EXISTS.value, [username.get()])

    def _on_create_account(self, username, password):
        # Check if username exists
        self.send_message(OpCode.CREATE_ACCOUNT.value, [username.get(), password.get()])

    def _on_login_account(self, username, password):
        # Check if username exists
        self.send_message(OpCode.LOGIN_ACCOUNT.value, [username.get(), password.get()])

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
        # It's normal for connect() to raise this in non-blocking mode
        pass

    # Build initial request. Example: a simple "login" or "handshake"
    initial_request = {
        "content_encoding": "utf-8",
        "opcode": 0,
        "content": {"args": ["dummy_name"]},  # just an example
    }
    # TODO: should be able to do without initial request

    # Create the Message object
    addr = (host, port)
    msg_obj = Message(selector=sel, sock=sock, addr=addr, request=initial_request, incoming_queue=incoming_queue)

    # We'll watch both READ and WRITE events initially, so we can send the handshake
    sel.register(sock, selectors.EVENT_READ | selectors.EVENT_WRITE, data=msg_obj)

    # Pass a reference to the incoming_queue so we can push server data to the GUI
    # Typically, you'd do this by customizing your Message class to call a callback
    # or a queue put whenever it has a complete "response". For example:
    #
    # def _generate_action(self, opcode, status_code, data):
    #     # Instead of printing, we might do something like:
    #     #   self.incoming_queue.put(f"Opcode: {opcode}, Data: {data}")
    #     # This snippet below shows how you might do that inline:

    return sel, msg_obj

def main(args):
    host = args.host
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
        stop_event.set()
        message_obj.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=65432)
    args = parser.parse_args()

    main(args)
