import selectors
import socket
import sys
import traceback
import yaml
import libserver
import os
from datetime import datetime
from database_setup import database_setup

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Read config file
yaml_path = "config.yaml"
with open(yaml_path) as y:
    config_dict = yaml.safe_load(y)
version = config_dict["version"]
key = config_dict["key"]
db_path = config_dict["db_path"]

active_clients = {} # key: username, value: socket
# Set up selector and database
sel = selectors.DefaultSelector()
database_setup(db_path)

# Accept a new socket connection
def accept_wrapper(sock, protocol):
    conn, addr = sock.accept()  # Should be ready to read
    print(f"Accepted connection from {addr}")

    conn.setblocking(False) # Set non-blocking mode so other sockets can connect
    if not protocol:
        message = libserver.Message(sel, conn, addr, db_path=db_path, active_clients=active_clients)
    else:
        print("HERE")
        message = libserver.MessageCustom(sel, conn, addr, db_path=db_path, active_clients=active_clients)
    sel.register(conn, selectors.EVENT_READ, data=message)

# Main loop
# if len(sys.argv) != 4:
#     print(f"Usage: {sys.argv[0]} <host> <port>")
#     sys.exit(1)

host, port, protocol = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]) # TODO: refactor input enforcement
# Create a listening socket
lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Avoid bind() exception: OSError: [Errno 48] Address already in use
lsock.bind((host, port))
lsock.listen()
print(f"Listening on {(host, port)}")
lsock.setblocking(False) # Set non-blocking mode so other sockets can connect
sel.register(lsock, selectors.EVENT_READ, data=None)


try:
    while True:
        events = sel.select(timeout=None)
        # For each event
        for key, mask in events:
            if key.data is None:
                accept_wrapper(key.fileobj, protocol) # Accept a new connection
            else:
                message = key.data # Service existing connection
                try:
                    message.process_events(mask)
                except Exception:
                    print(
                        f"Main: Error: Exception for {message.addr}:\n"
                        f"{traceback.format_exc()}"
                    )
                    message.close()
except KeyboardInterrupt:
    print("Caught keyboard interrupt, exiting")
finally:
    sel.close()

# Cleanup
os.remove(db_path)