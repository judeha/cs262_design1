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

# Adjust the following import paths as needed:
# from libclient import Message
from codes import OpCode, ResponseCode  # If you need these enums
import yaml
import struct
import json
from libclient import Message

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
        self.root.title("Selector-Based Client")
        self.frame = tk.Frame(root)
        self.frame.pack(expand=True, fill=tk.BOTH)

        # Text widget for displaying chat / server responses
        self.chat_display = scrolledtext.ScrolledText(self.frame, wrap=tk.WORD, state='disabled')
        self.chat_display.pack(side=tk.TOP, expand=True, fill=tk.BOTH)

        # Entry + send button
        self.entry_frame = tk.Frame(self.frame)
        self.entry_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.input_field = tk.Entry(self.entry_frame)
        self.input_field.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.send_button = tk.Button(self.entry_frame, text="Send", command=lambda: self.send_message(OpCode.SEND_MSG.value, ["message"]))
        self.send_button.pack(side=tk.RIGHT)

        # Periodically poll the incoming queue
        self.poll_incoming()

    def send_message(self, opcode, args):
        """
        Sends a request to the server using the existing `message_obj`.
        For example, we might send an OpCode.SEND_MSG request or something else.
        """
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
            except queue.Empty:
                break
            else:
                self._append_chat(response_str)

        # Schedule next poll
        self.root.after(100, self.poll_incoming)

    def _append_chat(self, text):
        """Helper to insert text into the chat display."""
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, text + "\n")
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)

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

    # Build initial request. Example: a simple "login" or "handshake"
    initial_request = {
        "content_encoding": "utf-8",
        "opcode": 0,
        "content": {"args": ["dummy_name"]},  # just an example
    }

    # Create the Message object
    addr = (host, port)
    msg_obj = Message(selector=sel, sock=sock, addr=addr, request=initial_request)

    # We'll watch both READ and WRITE events initially, so we can send the handshake
    sel.register(sock, selectors.EVENT_READ | selectors.EVENT_WRITE, data=msg_obj)

    return sel, msg_obj

def main(args):
    host = args.host # TODO: put in config?
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