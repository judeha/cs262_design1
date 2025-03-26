import yaml
import queue
import threading
from utils import database_setup
import yaml
import time
import logging
from database import DatabaseHandler
from utils import ResponseCode, apply_action
import handler_pb2
import handler_pb2_grpc
from concurrent import futures
import grpc
import random
import sys

# Load configuration from YAML file
yaml_path = "config.yaml"
with open(yaml_path, "r") as y:
    config = yaml.safe_load(y)

# Get values from config
MIN_MESSAGE_LEN = config["min_message_len"]
MAX_MESSAGE_LEN = config["max_message_len"]
idx = int(sys.argv[1])
server_config = config.get("servers")[idx]
host = server_config.get("host", "localhost")
port = server_config.get("port", 65432)
DB_PATH = server_config.get("db_path", f"data/s{idx}.db")
LOG_PATH = server_config.get("log_path", f"logs/s{idx}.log")

# Global variables
active_clients = {} # Active clients mapping (username -> socket)
lock = threading.Lock()
# Initialize local logging
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.info("Server started")
logging.info(f"Host: {host}")
logging.info(f"Port: {port}")


# Initialize the database
database_setup(DB_PATH)

# Raft variables
class Role:
    FOLLOWER = 0
    CANDIDATE = 1
    LEADER = 2
role = Role.FOLLOWER
leader_addr = None
n_servers = len(config.get("servers"))
all_servers = [f"{config.get('servers')[i]['host']}:{config.get('servers')[i]['port']}" for i in range(n_servers)]
logs = []
term = 0
timer = random.randint(0,3)
commit_idx = 0
voted_for = None
votes_recv = 0
last_heartbeat = time.time()

class HandlerService(handler_pb2_grpc.HandlerServicer):
    """
    Handles standard communication between the server and a client using JSON encoding. Message is (fuzzily) equivalent to a server-stub.
    """
    def __init__(self):
        # self.db = DatabaseHandler(DB_PATH)
        # Active clients mapping (username -> Message object)
        global active_clients, logs
        self.db_path = DB_PATH

        # logging.info(f"New connection established: {addr}")

    def set_path(self, path):
        self.db_path = path

    def Starting(self, request, context):
        response = handler_pb2.StartingResponse()
        response.status_code = ResponseCode.SUCCESS.value
        return response
    
    def CheckAccountExists(self, request, context):
        # Add a new log entry
        logs.append(handler_pb2.Entry(acc_exists=request))

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
        # Add a new log entry
        logs.append(handler_pb2.Entry(create_acc=request))

        db = DatabaseHandler(self.db_path)  # Create fresh DB instance
        # Process the request
        response = handler_pb2.CreateAccountResponse()
        result = db.create_account(request.username, request.password, request.bio)
        # Package the response
        response.status_code = result["status_code"]
        return response
    
    def LoginAccount(self, request, context):
        logs.append(handler_pb2.Entry(login_acc=request))

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
        logs.append(handler_pb2.Entry(list_acc=request))

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
        logs.append(handler_pb2.Entry(create_acc=request))

        db = DatabaseHandler(self.db_path)  # Create fresh DB instance
        response = handler_pb2.DeleteAccountResponse()
        result = db.delete_account(request.username, request.password)
        # Package the response
        response.status_code = result["status_code"]

        return response

    def FetchHomepage(self, request, context):
        logs.append(handler_pb2.Entry(fetch_homepage=request))

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
        logs.append(handler_pb2.Entry(fetch_read=request))
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
        logs.append(handler_pb2.Entry(fetch_read=request))

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
        logs.append(handler_pb2.Entry(delete_msg=request))

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
    
    # def SendMessage(self, request, context):
    #     db = DatabaseHandler(self.db_path)  # Create fresh DB instance
    #     # Process the request
    #     response = handler_pb2.SendMessageResponse()
    #     sender = request.sender
    #     receiver = request.receiver
    #     msg_content = request.content
    #     timestamp = round(time.time())
        
    #     request.timestamp = timestamp
    #     logs.append(handler_pb2.Entry(send_msg=request))

    #     with lock:
    #         delivered = receiver in active_clients

    #     # Insert the message into the database
    #     result = db.insert_message(sender, receiver, msg_content, timestamp, delivered)

    #     # Create SendMessageResponse for the sender
    #     response.status_code = result["status_code"]

    #     # If receiver online: try sending immediately
    #     if response.status_code == ResponseCode.SUCCESS.value and delivered:
    #         try:
    #             # Create a ReceiveMessageResponse for the receiver
    #             msg = handler_pb2.Message(
    #                 id=result["data"][0],
    #                 sender=sender,
    #                 receiver=receiver,
    #                 content=msg_content,
    #                 timestamp=timestamp,
    #                 delivered=delivered
    #             )
    #             # Send the message to the receiver
    #             with lock:
    #                 active_clients[receiver].put(msg)

    #         except Exception as e:
    #             print("Error sending message:", e)

    #     return response
    
    def SendMessage(self, request_iterator, context):
        db = DatabaseHandler(self.db_path)
        delivered_count = 0
        total_count = 0

        for req in request_iterator:
            sender = req.sender
            receiver = req.receiver
            content = req.content
            timestamp = round(time.time())

            req.timestamp = timestamp
            logs.append(handler_pb2.Entry(send_msg=req))

            # Check if receiver is online
            with lock:
                is_online = receiver in active_clients

            # Insert message (delivered=1 if online, else 0)
            result = db.insert_message(sender, receiver, content, timestamp, is_online)
            total_count += 1
            if result["status_code"] == ResponseCode.SUCCESS.value:
                # If receiver is online, push to their queue
                if is_online:
                    with lock:
                        msg = handler_pb2.Message(
                            id=result["data"][0],  # e.g. DB returns newly inserted ID
                            sender=sender,
                            receiver=receiver,
                            content=content,
                            timestamp=timestamp
                        )
                        active_clients[receiver].put(msg)
                    delivered_count += 1

        # Build a final, single response
        response = handler_pb2.SendMessageResponse()
        response.status_code = ResponseCode.SUCCESS.value
        # response.delivered_count = delivered_count
        # response.total_count = total_count
        return response
    
    def ReceiveMessage(self, request, context):
        """Continuously stream new messages to the client."""

        logs.append(handler_pb2.Entry(receive_msg=request))

        username = request.username
        with lock:
            if username not in active_clients:
                return

            user_queue = active_clients[username]

        while True:
            try:
                # block for up to 30s waiting for a new message
                # msg = user_queue.get(timeout=5)
                msg = user_queue.get(block=True)
                response = handler_pb2.ReceiveMessageResponse()
                response.msg_lst.append(msg)
                yield response

            except queue.Empty:
                # no messages arrived in 30s, keep waiting
                continue

    def Ending(self, request, context):
        """Removes a client from active_clients."""
        logs.append(handler_pb2.Entry(ending=request))
        username = request.username
        with lock:
            if username in active_clients:
                del active_clients[username]
                response = handler_pb2.EndingResponse()
                response.status_code = ResponseCode.SUCCESS.value
                return response
            
class RaftService(handler_pb2_grpc.RaftServicer):
    def Vote(self, request, context):
        global term, voted_for, leader_addr
        # TODO: local logging
        if request.cand_term < term or voted_for is None:
            return handler_pb2.VoteResponse(term=term, success=False)
        # If candidate is ahead of me, vote for them + update my term
        if request.cand_term >= term:
            term = request.cand_term
            voted_for = request.cand_id
            leader_addr = None
            return handler_pb2.VoteResponse(term=term, success=True)

    def AppendEntries(self, request, context):
        """Followers respond to leader's heartbeat"""
        global leader_addr, logs, DB_PATH, timer, role, voted_for, last_heartbeat
        # TODO: implement checks if role is Role.LEADER
        # TODO: local logging
        voted_for = None
        timer = time.time() + random.uniform(0.3, 0.5) # NOTE: should this be +3 everytime?
        last_heartbeat = time.time()

        if role == "LEADER":
            pass
            # TODO: local logging
        role = "FOLLOWER"

        # 1) Update leader_addr?
        if request.leader_addr != leader_addr:
            leader_addr = request.leader_addr
            # TODO: local logging
        # 2) Exist new entries?
        if len(logs) - 1 == request.prev_log_idx:
            return handler_pb2.AppendEntriesResponse(term=term, success=True)
        # 3) Apply actions
        for entry in request.entries[request.commit + 1]:
            logs.append(entry)
            apply_action(entry, DB_PATH)
        return handler_pb2.AppendEntriesResponse(term=request.term, success=True)
    def GetLeader(self, request, context):
        global leader_addr
        return handler_pb2.GetLeaderResponse(leader_addr=leader_addr)

def serve():
    """Main loop"""
    global all_servers, votes_recv, idx, term, role, timer, logs, commit_idx, voted_for, n_servers, leader_addr, host, port

    # Setup
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    handler_pb2_grpc.add_HandlerServicer_to_server(HandlerService(), server)
    handler_pb2_grpc.add_RaftServicer_to_server(RaftService(), server)
    server.add_insecure_port(f'{host}:{port}')
    server.start()

    # Connect to all other servers + elect leader
    for s in all_servers:
        try:
            channel = grpc.insecure_channel(s)
            stub = handler_pb2_grpc.RaftStub(channel)
            response = stub.Vote(handler_pb2.VoteRequest(
                cand_term=0,
                cand_id=0, # auto select first server as leader to begin with
                prev_log_idx=0,
                prev_log_term=0
                )
            )
            # TODO: local logging
            channel.close()
            break
        except Exception as e:
            # TODO: local logging
            time.sleep(1)

    # TODO: local logging
    # Sleep for random amount of time to allow for election
    time.sleep(random.random())

    # Take actions based on role
    try:
        while True:
            print(leader_addr)
            if role == Role.FOLLOWER:
                # If no leader heartbeat: trigger election (will automatically call AppendEntries upon receiving)
                # if time.time() > timer:
                if time.time() - last_heartbeat > 1:
                    # TODO: local logging
                    term += 1
                    voted_for = None
                    role = Role.CANDIDATE
                    # timer = time.time() + random.uniform(1.0, 2.0)

            elif role == Role.CANDIDATE:
                if time.time() > timer:
                    timer = time.time() + random.uniform(3,5) # NOTE: why?

                    # Vote for self
                    votes_recv = 1
                    voted_for = idx
                    # TODO: local logging

                    # Request other servers to vote for me
                    for s in all_servers:
                        try:
                            channel = grpc.insecure_channel(s)
                            stub = handler_pb2_grpc.RaftStub(channel)
                            response = stub.Vote(handler_pb2.VoteRequest(
                                cand_id=idx,
                                cand_term=term,
                                prev_log_idx=len(logs) - 1,
                                prev_log_term=logs[-1].term if logs else 0,
                                )
                            )
                            # TODO: local logging
                            if response.success:
                                votes_recv += 1
                        except Exception as e:
                            continue
                            # TODO: local logging
                    # If you win the election
                    if votes_recv > n_servers // 2:
                        role = Role.LEADER
                        leader_addr = f"{host}:{port}"
                        # TODO: broadcast to all other servers + client?
                    # TODO: local logging
            elif role == Role.LEADER:
                # Send heartbeat
                ack = 0
                for s in all_servers:
                    try:
                        if s != leader_addr: # NEW
                            channel = grpc.insecure_channel(s)
                            stub = handler_pb2_grpc.RaftStub(channel)
                            # Send out all logs TODO: optimize to just send snapshot
                            response = stub.AppendEntries(handler_pb2.AppendEntriesRequest(
                                leader_addr=leader_addr,
                                term=term,
                                prev_log_term=logs[-1].term if logs else 0,
                                prev_log_idx=len(logs) - 1,
                                entries=logs,
                                commit=commit_idx)
                            )
                            # print(response.success)
                            ack += response.success
                            # TODO: local logging
                            channel.close()
                    except Exception as e:
                        # print(e)
                        # TODO: local logging
                        pass
                # If ACK successful
                if ack >= n_servers // 2:
                    # Commit change --> move forward index
                    commit_idx = len(logs) - 1
                else:
                    # Lose leader role
                    print("Lost leader", ack)
                    role = Role.FOLLOWER
                    leader_addr = None
                    # TODO: local logging
            else:
                pass
                # TODO: local logging
            time.sleep(0.1)
    except KeyboardInterrupt:
        server.stop(0)

    server.wait_for_termination()

if __name__ == "__main__":
    # Parse optional command-line arguments
    # TODO how to test multiple servers?
    import argparse

    # parser = argparse.ArgumentParser(description="Start the chat server.")
    # parser.add_argument("--host", type=str, default=DEFAULT_HOST, help="Server host (default from config)")
    # parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server port (default from config)")

    # args = parser.parse_args()
    # serve(host=args.host, port=args.port)
    serve()