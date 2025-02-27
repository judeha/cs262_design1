import selectors
import yaml
import queue
import threading
from utils import database_setup
import yaml
import time
import logging
from database import DatabaseHandler
from utils import ResponseCode
import handler_pb2
import handler_pb2_grpc
from concurrent import futures
import grpc

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
lock = threading.Lock()

# Initialize the selector and database
database_setup(DB_PATH)
    
# Load configuration
yaml_path = "config.yaml"
with open(yaml_path, "r") as y:
    config = yaml.safe_load(y)

# Defaults
VERSION = config["version"]
DB_PATH = config["db_path"]
MIN_MESSAGE_LEN = config["min_message_len"]
MAX_MESSAGE_LEN = config["max_message_len"]

class HandlerService(handler_pb2_grpc.HandlerServicer):
    """
    Handles standard communication between the server and a client using JSON encoding. Message is (fuzzily) equivalent to a server-stub.
    """
    def __init__(self):
        # self.db = DatabaseHandler(DB_PATH)
        # Active clients mapping (username -> Message object)
        global active_clients
        self.db_path = DB_PATH

        # logging.info(f"New connection established: {addr}")

    def set_path(self, path):
        self.db_path = path

    def Starting(self, request, context):
        response = handler_pb2.StartingResponse()
        response.status_code = ResponseCode.SUCCESS.valuef
        return response
    
    def CheckAccountExists(self, request, context):
        db = DatabaseHandler(self.db_path)  # Create fresh DB instance
        # Process the request
        response = handler_pb2.AccountExistsResponse()
        result = db.account_exists(request.username)
        # Package the response
        if not result:
            response.status_code = ResponseCode.ACCOUNT_NOT_FOUND.value
        else:
            response.status_code = ResponseCode.ACCOUNT_EXISTS.value
            response.exists = result
        return response

    def CreateAccount(self, request, context):
        db = DatabaseHandler(self.db_path)  # Create fresh DB instance
        # Process the request
        response = handler_pb2.CreateAccountResponse()
        result = db.create_account(request.username, request.password, request.bio)
        # Package the response
        response.status_code = result["status_code"]
        return response
    
    def LoginAccount(self, request, context):
        db = DatabaseHandler(self.db_path)  # Create fresh DB instance
        # Process the request
        response = handler_pb2.LoginAccountResponse()
        result = db.login_account(request.username, request.password)
        # Package the response
        response.status_code = result["status_code"]
        if result["status_code"] == ResponseCode.SUCCESS.value:
            data = result["data"]
            response.count = data.pop(0)
            data = [handler_pb2.Message(id=msg[0], sender=msg[1], receiver=msg[2],
                                        content=msg[3],timestamp=msg[4]) for msg in data]
            response.msg_lst.extend(data)
            # Add the client to the active clients mapping
            with lock:
                active_clients[request.username] = queue.Queue()
        
        return response
        
    def ListAccount(self, request, context):
        db = DatabaseHandler(self.db_path)  # Create fresh DB instance
        response = handler_pb2.ListAccountResponse()
        result = db.list_accounts(request.pattern)

        result = db.list_accounts(pattern=request.pattern or "")

        response.status_code = result["status_code"]
        if result["status_code"] == ResponseCode.SUCCESS.value:
            data = result["data"]
            data = [handler_pb2.Account(id=acct[0], username=acct[1], bio=acct[2]) for acct in data]
            response.acct_lst.extend(data)

        return response 
    
    def DeleteAccount(self, request, context):
        db = DatabaseHandler(self.db_path)  # Create fresh DB instance
        response = handler_pb2.DeleteAccountResponse()
        result = db.delete_account(request.username, request.password)
        # Package the response
        response.status_code = result["status_code"]

        return response

    def FetchHomepage(self, request, context):
        db = DatabaseHandler(self.db_path)  # Create fresh DB instance
        # Create fresh DB instance
        response = handler_pb2.FetchHomepageResponse()
        result = db.fetch_homepage(request.username)

        response.status_code = result["status_code"]
        if result["status_code"] == ResponseCode.SUCCESS.value:
            data = result["data"]
            data = [handler_pb2.Message(id=msg[0], sender=msg[1], receiver=msg[2],
                                        content=msg[3],timestamp=msg[4]) for msg in data]
            response.msg_lst.extend(data)

        return response 

    def FetchMessageRead(self, request, context):
        db = DatabaseHandler(self.db_path)  # Create fresh DB instance
        response = handler_pb2.FetchMessagesReadResponse()
        result = db.fetch_messages_delivered(request.username, request.num)

        response.status_code = result["status_code"]
        if result["status_code"] == ResponseCode.SUCCESS.value:
            data = result["data"]
            data = [handler_pb2.Message(id=msg[0], sender=msg[1], receiver=msg[2],
                                        content=msg[3],timestamp=msg[4]) for msg in data]
            response.msg_lst.extend(data)

        return response 

    def FetchMessageUnread(self, request, context):
        db = DatabaseHandler(self.db_path)  # Create fresh DB instance
        response = handler_pb2.FetchMessagesUnreadResponse()
        result = db.fetch_messages_undelivered(request.username, request.num)

        response.status_code = result["status_code"]
        if result["status_code"] == ResponseCode.SUCCESS.value:
            data = result["data"]
            response.count = data.pop(0)
            data = [handler_pb2.Message(id=msg[0], sender=msg[1], receiver=msg[2],
                                        content=msg[3],timestamp=msg[4]) for msg in data]
            response.msg_lst.extend(data)
        # return self.FetchHomepage(request.username)
        return response


    def DeleteMessage(self, request, context):
        db = DatabaseHandler(self.db_path)  # Create fresh DB instance
        # Process the request
        response = handler_pb2.DeleteMessageResponse()
        result = db.delete_messages(request.username, request.message_id_lst)
        # Package the response
        response.status_code = result["status_code"]
        if result["status_code"] == ResponseCode.SUCCESS.value:
            data = result["data"]
            response.count = data.pop(0)
            data = [handler_pb2.Message(id=msg[0], sender=msg[1], receiver=msg[2],
                                        content=msg[3],timestamp=msg[4]) for msg in data]
            response.msg_lst.extend(data)
    
        return response
    
    def SendMessage(self, request, context):
        db = DatabaseHandler(self.db_path)  # Create fresh DB instance
        # Process the request
        response = handler_pb2.SendMessageResponse()
        sender = request.sender
        receiver = request.receiver
        msg_content = request.content
        timestamp = round(time.time())
        with lock:
            delivered = receiver in active_clients

        # Insert the message into the database
        result = db.insert_message(sender, receiver, msg_content, timestamp, delivered)

        # Create SendMessageResponse for the sender
        response.status_code = result["status_code"]

        # If receiver online: try sending immediately
        if response.status_code == ResponseCode.SUCCESS.value and delivered:
            try:
                # Create a ReceiveMessageResponse for the receiver
                msg = handler_pb2.Message(
                    id=result["data"][0],
                    sender=sender,
                    receiver=receiver,
                    content=msg_content,
                    timestamp=timestamp,
                    delivered=delivered
                )
                # Send the message to the receiver
                with lock:
                    active_clients[receiver].put(msg)

            except Exception as e:
                print("Error sending message:", e)

        return response
    
    def ReceiveMessage(self, request, context):
        """Continuously stream new messages to the client."""
        username = request.username
        with lock:
            if username not in active_clients:
                return

            user_queue = active_clients[username]

        while True:
            try:
                # block for up to 30s waiting for a new message
                msg = user_queue.get(timeout=5)
                response = handler_pb2.ReceiveMessageResponse()
                response.msg_lst.append(msg)
                yield response

            except queue.Empty:
                # no messages arrived in 30s, keep waiting
                continue

    def Ending(self, request, context):
        """Removes a client from active_clients."""
        username = request.username
        with lock:
            if username in active_clients:
                del active_clients[username]
                response = handler_pb2.EndingResponse()
                response.status_code = ResponseCode.SUCCESS.value
                return response

def serve(host, port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    handler_pb2_grpc.add_HandlerServicer_to_server(HandlerService(), server)
    server.add_insecure_port(f'{host}:{port}')
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    # Parse optional command-line arguments
    import argparse

    parser = argparse.ArgumentParser(description="Start the chat server.")
    parser.add_argument("--host", type=str, default=DEFAULT_HOST, help="Server host (default from config)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server port (default from config)")

    args = parser.parse_args()
    serve(host=args.host, port=args.port)