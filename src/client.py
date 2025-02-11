import selectors
import socket
import sys
import ast
# import yaml
import traceback
import libclient
import tkinter as tk
import threading
import libclient
from client_ui import Interface as UI

# Read config file
# yaml_path = "config.yaml"
# with open(yaml_path) as y:
#     config_dict = yaml.safe_load(y)
# version = config_dict["version"]
# key = config_dict["key"]
# db_path = config_dict["db_path"]

# Setup selector
sel = selectors.DefaultSelector()

# Create a dictionary of request information
def create_request(opcode, args):
    return dict(
        # byteorder = sys.byteorder,
        # content_type="json",
        content_encoding="utf-8",
        opcode = opcode,
        content={"args": args},
    )

# Create a new connection to the server
def start_connection(host, port, request):
    addr = (host, port)
    print(f"Starting connection to {addr}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    message = libclient.Message(sel, sock, addr, request)
    sel.register(sock, events, data=message)

# Main loop
if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <host> <port>")
    sys.exit(1)

# host, port = sys.argv[1], int(sys.argv[2])
# action, args = sys.argv[3], sys.argv[4]
# args = ast.literal_eval(args) # TODO: transform tkinter gui to args
# request = create_request(action, args)
# start_connection(host, port, request)

if __name__ == "__main__":
    # #Start the GUI 
    ui = UI()
    ui.root.mainloop()

    #Open the socket connection 
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