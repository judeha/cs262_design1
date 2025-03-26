import selectors
import socket
import traceback
import yaml
import os
import server_handler
from utils import database_setup

# Load configuration from YAML file
yaml_path = "config.yaml"
with open(yaml_path, "r") as y:
    config = yaml.safe_load(y)

# Default values from config
DEFAULT_HOST = config.get("host", "127.0.0.1")
DEFAULT_PORT = config.get("port", 65432)
DEFAULT_PROTOCOL = config.get("protocol", 0)
DB_PATH = config.get("db_path", "server.db")

# Active clients mapping (username -> socket)
active_clients = {}

# Initialize the selector and database
sel = selectors.DefaultSelector()
database_setup(DB_PATH)


def accept_connection(sock, protocol):
    """
    Accepts a new incoming client connection, initializes the appropriate handler,
    and registers it with the selector for event-driven processing.

    :param sock: Listening socket accepting the connection.
    :param protocol: Protocol version (0 for default, 1 for custom).
    """
    conn, addr = sock.accept()
    print(f"New connection from {addr}")

    conn.setblocking(False)  # Set non-blocking mode
    # Handle messages using the default or custom protocol
    if protocol == 0:
        handler = server_handler.Message(sel, conn, addr, db_path=DB_PATH, active_clients=active_clients)
    else:
        print("Using custom protocol handler")
        handler = server_handler.MessageCustom(sel, conn, addr, db_path=DB_PATH, active_clients=active_clients)

    sel.register(conn, selectors.EVENT_READ, data=handler)


def start_server(host=DEFAULT_HOST, port=DEFAULT_PORT, protocol=DEFAULT_PROTOCOL):
    """
    Initializes and starts the server, handling client connections and requests.

    :param host: Server host (default from config).
    :param port: Server port (default from config).
    :param protocol: Communication protocol (0 for default, 1 for custom).
    """
    try:
        # Create and configure the listening socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Prevents address reuse issues
        server_socket.bind((host, port))
        server_socket.listen()
        print(f"Server listening on {host}:{port}")

        server_socket.setblocking(False)  # Allow non-blocking I/O
        sel.register(server_socket, selectors.EVENT_READ, data=None) # Register the server socket

        # Main event loop
        while True:
            events = sel.select(timeout=None)
            # For each event from the selector
            for key, mask in events:
                if key.data is None:
                    accept_connection(key.fileobj, protocol)  # Accept new clients
                else:
                    handler = key.data
                    try:
                        handler.process_events(mask)  # Process client requests
                    except Exception:
                        print(f"Error handling {handler.addr}:\n{traceback.format_exc()}")
                        handler.close()

    except KeyboardInterrupt:
        print("\nServer shutting down gracefully...")
    finally:
        sel.close()
        # os.remove(DB_PATH)  # Cleanup database file after shutdown


if __name__ == "__main__":
    # Parse optional command-line arguments
    import argparse

    parser = argparse.ArgumentParser(description="Start the chat server.")
    parser.add_argument("--host", type=str, default=DEFAULT_HOST, help="Server host (default from config)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server port (default from config)")
    parser.add_argument("--protocol", type=int, choices=[0, 1], default=DEFAULT_PROTOCOL, help="Protocol version (0: default, 1: custom)")

    args = parser.parse_args()
    start_server(host=args.host, port=args.port, protocol=args.protocol)