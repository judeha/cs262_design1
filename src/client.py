import selectors
import socket
import sys
import ast
import traceback
from utils import libclient
import tkinter as tk
import threading
import ui_client

sel = selectors.DefaultSelector()

def create_request(opcode, args):
    return dict(
        # byteorder = sys.byteorder,
        # content_type="json",
        content_encoding="utf-8",
        opcode = opcode,
        content={"args": args},
    )

def start_connection(host, port, request):
    addr = (host, port)
    print(f"Starting connection to {addr}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    message = libclient.Message(sel, sock, addr, request)
    sel.register(sock, events, data=message)

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <host> <port> <action> <value>")
    sys.exit(1)

host, port = sys.argv[1], int(sys.argv[2])
# action, args = sys.argv[3], sys.argv[4]

root = tk.Tk()
root.title("Login System")
root.geometry("350x200")

width = 350
height = 200

def show_frame(frame_name):
    """Brings the specified frame to the front."""
    frames[frame_name].tkraise()

def create_main_frame(container):
    """Creates the main menu frame."""
    frame = tk.Frame(container)
    
    login_btn = tk.Button(frame, text='Login', command=lambda: show_frame("login"))
    create_btn = tk.Button(frame, text='Create Account', command=lambda: show_frame("create"))

    login_btn.pack(pady=10)
    create_btn.pack(pady=10)

    return frame

def create_login_frame(container):
    """Creates the login frame."""
    frame = tk.Frame(container)
    
    tk.Label(frame, text="Username:").pack(pady=5)
    username_entry = tk.Entry(frame)
    username_entry.pack(pady=5)

    tk.Label(frame, text="Password:").pack(pady=5)
    password_entry = tk.Entry(frame, show="*")
    password_entry.pack(pady=5)

    back_btn = tk.Button(frame, text="Back", command=lambda: show_frame("main"))
    back_btn.pack(pady=10)

    return frame

def create_account_frame(container):
    """Creates the create account frame."""
    frame = tk.Frame(container)
    
    tk.Label(frame, text="New Username:").pack(pady=5)
    new_username_entry = tk.Entry(frame)
    new_username_entry.pack(pady=5)

    tk.Label(frame, text="New Password:").pack(pady=5)
    new_password_entry = tk.Entry(frame, show="*")
    new_password_entry.pack(pady=5)

    # create_account_btn = tk.Button(frame, text="Create Account", command=lambda: show_frame("main"))
    create_btn = tk.Button(frame, text='Create', command=lambda: on_create_account(new_username_entry.get(), new_password_entry.get()))
    create_btn.pack(pady=10)

    return frame

def on_create_account(new_username, new_password):
    '''Handles create account request'''

    args = [new_username, new_password]

    if not new_username or not new_password:
        print("Error: Empty username or password")

    action = "create_account"
    args = ast.literal_eval(args)
    request = create_request(action, args)
    start_connection(host, port, request)

    # request.send()
    # root.after(100, process_response) 

# Initialize main window
root = tk.Tk()
root.title("Login System")
root.geometry("500x300")

# Create a container frame to hold all other frames
container = tk.Frame(root)
container.pack(fill="both", expand=True)

# Create and store frames
frames = {
    "main": create_main_frame(container),
    "login": create_login_frame(container),
    "create": create_account_frame(container),
}

# Pack all frames and raise the main frame
for frame in frames.values():
    frame.place(x=0, y=0, width=350, height=200)

show_frame("main")  # Show the main frame initially

root.mainloop()
# args = ast.literal_eval(args)
# request = create_request(action, args)
# start_connection(host, port, request)

try:
    while True:
        events = sel.select(timeout=1)
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
        if not sel.get_map():
            break
except KeyboardInterrupt:
    print("Caught keyboard interrupt, exiting")
finally:
    sel.close()