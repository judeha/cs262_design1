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
MIN_MESSAGE_LEN = config["min_message_len"]
MAX_MESSAGE_LEN = config["max_message_len"]
HEARTBEAT_LEN = config["heartbeat_len"]

# Load server configuration
idx = int(sys.argv[1])
server_config = config.get("servers")[idx]
host = server_config.get("host", "localhost")
port = server_config.get("port", 65432)
DB_PATH = server_config.get('db_path', "../data/s{idx}.db")
LOG_PATH = server_config.get('log_path', "../log/s{idx}.log")

# Global variables
active_clients = {} # Active clients mapping (username -> socket)
lock = threading.Lock()

# Initialize local logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
f_handle = logging.FileHandler(LOG_PATH)
# format
f_handle.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(f_handle)

logging.info(f"[START] server {idx} at {host}:{port}")

# Initialize the database
database_setup(DB_PATH)

# Raft variables
class Role:
    FOLLOWER = 0
    CANDIDATE = 1
    LEADER = 2

role: int = Role.FOLLOWER               # initial role
leader_addr: str = None                 # <host>:<port>, like "localhost:50051"
voted_for: int = None                   # candidate ID   
n_servers = len(config.get("servers"))  # number of servers
all_servers = [f"{config.get('servers')[i]['host']}:{config.get('servers')[i]['port']}" for i in range(n_servers)]                       # list of all server addresses
logs = []                               # log of all actions for replication
term = 0                                # tracks election cycle and log consistency 
commit_idx = 0                          # highest log index known to be safely replicated
votes_recv = 0                          # number of votes received
last_heartbeat = time.time()            # last time a heartbeat was received
timer = random.randint(0,3)             # election timer

class HandlerService(handler_pb2_grpc.HandlerServicer):
    """
    Handles standard communication between the server and a client using JSON encoding. Each RPC call logs to 'logs' for replication purposes, then applies the requested DB operation.
    """
    def __init__(self):
        global active_clients, logs
        self.db_path = DB_PATH

    def set_path(self, path):
        """Changes the DB path if needed for testing purposes"""
        self.db_path = path

    def Starting(self, request, context):
        """Ping to verify connection"""
        response = handler_pb2.StartingResponse()
        response.status_code = ResponseCode.SUCCESS.value
        return response
    
    def CheckAccountExists(self, request, context):
        """Check if an account with the given username exists"""
        # Add a new log entry
        logs.append(handler_pb2.Entry(acc_exists=request))

        # Create fresh DB instance
        db = DatabaseHandler(self.db_path)
        # Process the request
        response = handler_pb2.AccountExistsResponse()
        exists = db.account_exists(request.username)
        # Package the response
        if not exists:
            response.status_code = ResponseCode.ACCOUNT_NOT_FOUND.value
        else:
            response.status_code = ResponseCode.ACCOUNT_EXISTS.value
            response.exists = True
        return response

    def CreateAccount(self, request, context):
        """Create a new account (username, password, bio)"""
        logs.append(handler_pb2.Entry(create_acc=request))
        db = DatabaseHandler(self.db_path)

        response = handler_pb2.CreateAccountResponse()
        result = db.create_account(request.username, request.password, request.bio)
        response.status_code = result["status_code"]
        return response
    
    def LoginAccount(self, request, context):
        """Login to an existing account (username, password), returns some unread messages """
        logs.append(handler_pb2.Entry(login_acc=request))
        db = DatabaseHandler(self.db_path)
        
        response = handler_pb2.LoginAccountResponse()
        result = db.login_account(request.username, request.password)
        response.status_code = result["status_code"]
        # Fetch the messages if login was successful
        if result["status_code"] == ResponseCode.SUCCESS.value:
            data = result["data"]
            response.count = data.pop(0)
            data = [handler_pb2.Message(id=m[0],
                                        sender=m[1],
                                        receiver=m[2],
                                        content=m[3],
                                        timestamp=m[4])
                                        for m in data]
            response.msg_lst.extend(data)

            # Mark user as active
            with lock:
                active_clients[request.username] = queue.Queue()
        return response
        
    def ListAccount(self, request, context):
        """List all accounts matching an optoinal pattern"""
        logs.append(handler_pb2.Entry(list_acc=request))
        db = DatabaseHandler(self.db_path)  # Create fresh DB instance
        
        response = handler_pb2.ListAccountResponse()
        result = db.list_accounts(pattern=request.pattern or "")
        response.status_code = result["status_code"]
        if result["status_code"] == ResponseCode.SUCCESS.value:
            data = result["data"]
            pb_accts = [
                handler_pb2.Account(
                    id=a[0],
                    username=a[1],
                    bio=a[2]
                    )
                    for a in data
                ]
            response.acct_lst.extend(pb_accts)
        return response 
    
    def DeleteAccount(self, request, context):
        """Deletes an account (username, password)"""
        logs.append(handler_pb2.Entry(delete_acc=request))
        db = DatabaseHandler(self.db_path)

        response = handler_pb2.DeleteAccountResponse()
        result = db.delete_account(request.username, request.password)
        response.status_code = result["status_code"]
        return response

    def FetchHomepage(self, request, context):
        """Fetches homepage data for a user"""
        logs.append(handler_pb2.Entry(fetch_homepage=request))
        db = DatabaseHandler(self.db_path)

        response = handler_pb2.FetchHomepageResponse()
        result = db.fetch_homepage(request.username)
        response.status_code = result["status_code"]
        if result["status_code"] == ResponseCode.SUCCESS.value:
            data = result["data"]
            data = [
                handler_pb2.Message(
                    id=m[0],
                    sender=m[1],
                    receiver=m[2],
                    content=m[3],
                    timestamp=m[4]
                )
                for m in data
            ]
            response.msg_lst.extend(data)
        return response 

    def FetchMessageRead(self, request, context):
        """Fetches the last N delivered (read) messages"""
        logs.append(handler_pb2.Entry(fetch_read=request))
        db = DatabaseHandler(self.db_path)

        response = handler_pb2.FetchMessagesReadResponse()
        result = db.fetch_messages_delivered(request.username, request.num)
        response.status_code = result["status_code"]
        if result["status_code"] == ResponseCode.SUCCESS.value:
            data = result["data"]
            data = [
                handler_pb2.Message(
                    id=m[0],
                    sender=m[1],
                    receiver=m[2],
                    content=m[3],
                    timestamp=m[4]
                )
                for m in data
            ]
            response.msg_lst.extend(data)
        return response 

    def FetchMessageUnread(self, request, context):
        """Fetches the last N undelivered (unread) messages"""
        logs.append(handler_pb2.Entry(fetch_read=request))
        db = DatabaseHandler(self.db_path)  # Create fresh DB instance
        
        response = handler_pb2.FetchMessagesUnreadResponse()
        result = db.fetch_messages_undelivered(request.username, request.num)
        response.status_code = result["status_code"]
        if result["status_code"] == ResponseCode.SUCCESS.value:
            data = result["data"]
            response.count = data.pop(0)
            pb_msgs = [
                handler_pb2.Message(
                    id=m[0],
                    sender=m[1],
                    receiver=m[2],
                    content=m[3],
                    timestamp=m[4]
                )
                for m in data
            ]
            response.msg_lst.extend(pb_msgs)
        return response

    def DeleteMessage(self, request, context):
        """Delete specific messages by ID"""
        logs.append(handler_pb2.Entry(delete_msg=request))
        db = DatabaseHandler(self.db_path)

        response = handler_pb2.DeleteMessageResponse()
        result = db.delete_messages(request.username, request.message_id_lst)
        response.status_code = result["status_code"]
        if result["status_code"] == ResponseCode.SUCCESS.value:
            data = result["data"]
            response.count = data.pop(0)
            pb_msgs = [
                handler_pb2.Message(
                    id=m[0],
                    sender=m[1],
                    receiver=m[2],
                    content=m[3],
                    timestamp=m[4]
                )
                for m in data
            ]
            response.msg_lst.extend(pb_msgs)
        return response
    
    def SendMessage(self, request_iterator, context):
        """
        Client-streaming RPC:
        - Each "SendMessageRequest" from the iterator is a single message
        - Insert the message into the database
        - If the receiver is online, immediately push the message to their queue
        """
        db = DatabaseHandler(self.db_path)
        delivered_count = 0
        total_count = 0

        for req in request_iterator:
            sender = req.sender
            receiver = req.receiver
            content = req.content
            timestamp = round(time.time())

            # Add to 'logs' for replication
            req.timestamp = timestamp
            logs.append(handler_pb2.Entry(send_msg=req))

            # Mark as delivered if receiver is online
            with lock:
                is_online = receiver in active_clients

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
        """
        Continuously stream new messages to the client
        - Yields new messages from the user's queue as they arrive
        """
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
                # If no messages for some time, keep waiting
                continue

    def Ending(self, request, context):
        """Removes a client from active_clients (logout)."""
        logs.append(handler_pb2.Entry(ending=request))
        username = request.username
        with lock:
            if username in active_clients:
                del active_clients[username]
                response = handler_pb2.EndingResponse()
                response.status_code = ResponseCode.SUCCESS.value
                return response
            
class RaftService(handler_pb2_grpc.RaftServicer):
    """
    Basic Raft implementation for leader election and log replication
    """
    def Vote(self, request, context):
        """Vote in favor or or against depending on candidate logs"""
        global term, voted_for, leader_addr
        logging.info(f"[RAFT] Received VoteRequest | cand_id: {request.cand_id}, cand_term: {request.cand_term}, prev_log_idx: {request.prev_log_idx}, prev_log_term: {request.prev_log_term}")

        # If candidate is behind me, reject
        if request.cand_term < term or voted_for is None: # TODO: check
            logging.info(f"[RAFT] Rejected VoteRequest | cand_id: {request.cand_id}, cand_term: {request.cand_term}, term: {term}")
            return handler_pb2.VoteResponse(term=term, success=False)
        # If candidate is ahead of me, vote for them + update my term
        if request.cand_term >= term:
            logging.info(f"[RAFT] Accepted VoteRequest | cand_id: {request.cand_id}, cand_term: {request.cand_term}, term: {term}")
            term = request.cand_term
            voted_for = request.cand_id
            return handler_pb2.VoteResponse(term=term, success=True)

    def AppendEntries(self, request, context):
        """
        Followers respond to leader's heartbeat
        Used for log replication
        """
        global leader_addr, logs, DB_PATH, timer, role, voted_for, last_heartbeat
        logging.info(f"[RAFT] Received AppendEntriesRequest | leader_addr: {leader_addr}, term: {request.term}, prev_log_idx: {request.prev_log_idx}, prev_log_term: {request.prev_log_term}, commit: {request.commit}")

        # Reset vote
        voted_for = None

        # Update timers
        timer = time.time() + random.uniform(0, 0.5)
        last_heartbeat = time.time()
        
        # Become FOLLOWER if not already
        role = Role.FOLLOWER # NEW

        # 1) Update leader_addr?
        if request.leader_addr != leader_addr:
            logging.info(f"[RAFT] Switched leader | leader_addr: {leader_addr}, request.leader_addr: {request.leader_addr}")
            leader_addr = request.leader_addr
        # 2) Exist new entries?
        if len(logs) - 1 == request.prev_log_idx:
            return handler_pb2.AppendEntriesResponse(term=term, success=True)
        # 3) Apply actions
        for entry in request.entries[request.commit + 1]:
            logs.append(entry)
            logging.info(f"[RAFT] Applying action | entry: {entry}")
            apply_action(entry, DB_PATH)
        return handler_pb2.AppendEntriesResponse(term=request.term, success=True)
    
    def GetLeader(self, request, context):
        """Return the current leader address"""
        global leader_addr
        logging.info(f"[RAFT] Get leader | leader_addr: {leader_addr}")
        return handler_pb2.GetLeaderResponse(leader_addr=leader_addr)

def serve():
    """
    Main loop for starting the gRPC server. 
    Also runs a minimal 'Raft-like' election loop.
    """
    global all_servers, votes_recv, idx, term, role, timer, logs
    global commit_idx, voted_for, n_servers, leader_addr, host, port, last_heartbeat

    # Setup gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    handler_pb2_grpc.add_HandlerServicer_to_server(HandlerService(), server)
    handler_pb2_grpc.add_RaftServicer_to_server(RaftService(), server)
    server.add_insecure_port(f'{host}:{port}')
    server.start()
    time.sleep(0.5)  # Give time for the socket to bind

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
            logging.info(f"[RAFT] Connecting | server: {s}, leader_addr: {leader_addr}")
            channel.close()
            break
        except Exception as e:
            logging.error(f"[RAFT] Connection error | server: {s}, error: {e}")
            time.sleep(1)

    # Sleep for random amount of time to allow for election
    time.sleep(random.random())

    # Take actions based on role
    try:
        while True:
            if role == Role.FOLLOWER:
                # If no leader heartbeat: trigger election (will automatically call AppendEntries upon receiving)
                if time.time() - last_heartbeat > HEARTBEAT_LEN:
                    term += 1
                    voted_for = None
                    # leader_addr = None
                    role = Role.CANDIDATE
                    logging.info(f"[RAFT] Election | term: {term}")
            elif role == Role.CANDIDATE:
                if time.time() > timer:
                    # Reset timer
                    timer = time.time() + random.uniform(3,5)

                    # Vote for self
                    votes_recv = 1
                    voted_for = idx

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
                            if response.success:
                                votes_recv += 1
                            logging.info(f"[RAFT] Requesting vote | server: {s}, success: {response.success}, votes_recv: {votes_recv}, leader_addr: {leader_addr}")
                        except Exception as e:
                            logging.error(f"[RAFT] Connection error | server: {s}, error: {e}")
                            pass
                    # If you win the election
                    if votes_recv > n_servers // 2:
                        role = Role.LEADER
                        leader_addr = f"{host}:{port}"

                        logging.info(f"[RAFT] Won election | votes_recv: {votes_recv}, n_servers: {n_servers}, term: {term}, leader_addr: {leader_addr}")
                        # TODO: broadcast to all other servers + client?

                        for s in all_servers:
                            try:
                                if s == f"{host}:{port}":
                                    last_heartbeat = time.time()
                                    continue
                                channel = grpc.insecure_channel(s)
                                stub = handler_pb2_grpc.RaftStub(channel)
                                # Send out all logs TODO: optimize to just send snapshot
                                response = stub.AppendEntries(handler_pb2.AppendEntriesRequest(
                                    leader_addr=leader_addr,
                                    term=term,
                                    prev_log_term=logs[-1].term if logs else 0,
                                    prev_log_idx=len(logs) - 1,
                                    entries=logs,
                                    commit=commit_idx
                                    )
                                )
                                channel.close()
                                logging.info(f"[RAFT] Sent heartbeat | server: {s}, success: {response.success}")
                            except Exception as e:
                                logging.error(f"[RAFT] Sent heartbeat erro | server: {s}, error: {e}")
                                pass

                    else:
                        logging.info(f"[RAFT] Lost election | votes_recv: {votes_recv}, n_servers: {n_servers}, term: {term}, leader_addr: {leader_addr}")
            elif role == Role.LEADER:
                # Send heartbeat (AppendEntries)
                ack = 0
                for s in all_servers:
                    try:
                        if s == f"{host}:{port}":
                            last_heartbeat = time.time()
                            continue
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
                        ack += response.success
                        channel.close()
                        logging.info(f"[RAFT] Sent heartbeat | server: {s}, success: {response.success}, ack: {ack}")
                    except Exception as e:
                        logging.error(f"[RAFT] Sent heartbeat erro | server: {s}, error: {e}")
                        pass
                # If ACK successful
                if ack >= n_servers // 2:
                    # Commit change --> move forward index
                    commit_idx = len(logs) - 1
                    logging.info(f"[RAFT] Committed change | commit_idx: {commit_idx}")
                else:
                    # Lose leader role
                    role = Role.FOLLOWER
                    leader_addr = None
                    logging.info(f"[RAFT] Lost leader role | leader_addr: {leader_addr}")
            else:
                logging.error(f"[RAFT] Invalid role | role: {role}")
                pass
            time.sleep(0.1)
    except KeyboardInterrupt:
        logging.info(f"[END] server {idx} at {host}:{port}")
        server.stop(0)

    server.wait_for_termination()

if __name__ == "__main__":
    serve()