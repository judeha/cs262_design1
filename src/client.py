import selectors
import socket
import sys
import ast
import traceback
import libclient
import tkinter as tk
import threading

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

if len(sys.argv) != 5:
    print(f"Usage: {sys.argv[0]} <host> <port> <action> <value>")
    sys.exit(1)

host, port = sys.argv[1], int(sys.argv[2])
action, args = sys.argv[3], sys.argv[4]
args = ast.literal_eval(args)
request = create_request(action, args)
start_connection(host, port, request)

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