import selectors
import socket
import traceback
import yaml
import os
import server_handler
from utils import database_setup

import io
import json
import yaml
import struct
import time
import ssl
import logging
from database import DatabaseHandler
from utils import encode_protocol, decode_protocol, ResponseCode, OpCode
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

# Initialize the selector and database
sel = selectors.DefaultSelector()
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
    def __init__(self, selector, sock, addr, db_path, active_clients={}):
        self.db = DatabaseHandler(DB_PATH)
        # Active clients mapping (username -> Message object)
        self.active_clients = active_clients

        # logging.info(f"New connection established: {addr}")

    def Starting(self, request, context):
        response = handler_pb2.StartingResponse()
        response.status_code = ResponseCode.SUCCESS.value
        return response
    
    def CheckAccountExists(self, request, context):
        # Process the request
        response = handler_pb2.AccountExistsResponse()
        result = self.db.account_exists(request.username)
        # Package the response
        if not result:
            response.status_code = ResponseCode.ACCOUNT_NOT_FOUND.value
        else:
            response.status_code = ResponseCode.ACCOUNT_EXISTS.value
            response.exists = result
        return response

    def CreateAccount(self, request, context):
        # Process the request
        response = handler_pb2.CreateAccountResponse()
        result = self.db.create_account(request.username, request.password, request.bio)
        # Package the response
        response.status_code = result["status_code"]
        return response
    
    def LoginAccount(self, request, context):
        # Process the request
        response = handler_pb2.LoginAccountResponse()
        result = self.db.login_account(request.username, request.password)
        # Package the response
        response.status_code = result["status_code"]
        if result["status_code"] == ResponseCode.SUCCESS.value:
            data = result["data"]
            response.count = data.pop(0)
            response.msg_lst = data
        return response

    def _generate_action(self, opcode, args):
        if opcode == OpCode.STARTING.value:
            result = {"status_code": ResponseCode.SUCCESS.value}
        elif opcode == OpCode.LOGIN_ACCOUNT.value:
            result = self.db.login_account(*args)
            # Add to active clients if login successful
            if result["status_code"] == ResponseCode.SUCCESS.value:
                self.active_clients[args[0]] = self
        elif opcode == OpCode.LIST_ACCOUNTS.value:
            # List accounts based on search query
            if len(args) > 0:
                result = self.db.list_accounts("".join(args))
            else:
                result = self.db.list_accounts()
        elif opcode == OpCode.DELETE_ACCOUNT.value:
            result = self.db.delete_account(*args)
        elif opcode == OpCode.HOMEPAGE.value:
            result = self.db.fetch_homepage(*args)
        elif opcode == OpCode.READ_MSG_UNDELIVERED.value:
            result = self.db.fetch_messages_undelivered(*args)
        elif opcode == OpCode.READ_MSG_DELIVERED.value:
            result = self.db.fetch_messages_delivered(*args)
        elif opcode == OpCode.DELETE_MSG.value:
            result = self.db.delete_messages(*args)
        elif opcode == OpCode.MATCH.value:
            result = self.db.match_users(*args)
            print("RESULT   ", result)
        elif opcode == OpCode.SEND_MSG.value:
            sender = args[0]
            receiver = args[1]
            msg_content = args[2]
            # If receiver online: try sending immediately
            if receiver in self.active_clients:
                try:
                    # Insert message into database
                    result = self.db.insert_message(*args, round(time.time()), True)

                    # We have a Message object for the receiver
                    receiver_msg = self.active_clients[receiver]
                
                    # Construct a new header or payload for the receiver
                    new_args = [self.db.cursor.lastrowid] + args
                    response = {
                        "status_code": ResponseCode.SUCCESS.value,
                        "data": [(*new_args, round(time.time()), True)]
                    }
                    
                    # Temporarily update our opcode to "RECEIVE_MSG" 
                    old_opcode = self._header["opcode"]
                    self._header["opcode"] = OpCode.RECEIVE_MSG.value

                    # Build the message
                    packaged = self._package_response(response)
                    self._header["opcode"] = old_opcode

                    # Send data by appending to the receiver's buffer
                    receiver_msg._send_buffer += packaged
                    # Ensure the receiver is listening for EVENT_WRITE
                    receiver_msg._set_selector_events_mask("w")
                except Exception as e:
                    logging.error(f"Failed to send message: {e}")
                    result = self.db.insert_message(*args, round(time.time()), False)
            else:
                # If user not online, just store in DB
                self.db.insert_message(sender, receiver, msg_content,
                                       round(time.time()),
                                       False)
                result = {"status_code": ResponseCode.SUCCESS.value}
        else:
            with Exception as e:
                logging.error(f"Unknown opcode: {e}")
                result = {"status_code": ResponseCode.SUCCESS.value} #
        return result
    
def serve(host, port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    handler_pb2_grpc.add_HandlerService_to_server(HandlerService(), server)
    server.add_insecure_port(f'{host}:{port}')
    server.start()
    print(f"Server listening on {host}:{port}")
    server.wait_for_termination()

if __name__ == "__main__":
    # Parse optional command-line arguments
    import argparse

    parser = argparse.ArgumentParser(description="Start the chat server.")
    parser.add_argument("--host", type=str, default=DEFAULT_HOST, help="Server host (default from config)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server port (default from config)")

    args = parser.parse_args()
    serve(host=args.host, port=args.port)