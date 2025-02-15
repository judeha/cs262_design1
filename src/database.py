import sqlite3
from utils import ResponseCode
from typing import Union
import yaml
import logging
from sentence_transformers import SentenceTransformer
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load configuration
yaml_path = "config.yaml"
with open(yaml_path, "r") as y:
    config = yaml.safe_load(y)

# Defaults
VERSION = config["version"]
DB_PATH = config["db_path"]
MIN_USERNAME_LEN = config["min_username_len"]
MIN_PASSWORD_LEN = config["min_password_len"]
MAX_USERNAME_LEN = config["max_username_len"]
MAX_PASSWORD_LEN = config["max_password_len"]
MIN_MESSAGE_LEN = config["min_message_len"]
MAX_MESSAGE_LEN = config["max_message_len"]
MAX_VIEW = config["max_view"]

# Load embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')  # Fast and accurate

class DatabaseHandler():
    """ Database handler class that executes actions given to it by the server.
    
    Methods:
    - create_account(username, password, bio): status_code
    - login_account(username, password): status_code, data[unread_count, messages]
    - delete_account(username, password): status_code
    - fetch_homepage(username): status_code, data[unread_count, messages]
    - list_accounts(pattern): status_code, data[accounts]
    - insert_message(sender, receiver, content, timestamp, delivered): status_code
    - delete_messages(username, message_ids): status_code, data[unread_count, messages]
    - fetch_messages_delivered(username, n): status_code, data[messages]
    - fetch_messages_undelivered(username, n): status_code, data[unread_count, messages]
    - count_messages(username, delivered): count
    - account_exists(username): bool
    - close()
    """
    def __init__(self, path):
        """ Initialize connection given database path """
        try:
            self.path = path
            self.conn = sqlite3.connect(self.path)
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")

    def create_account(self, username, password, bio) -> dict[int]:
        """ Given username and password, return account creation status """
        try:
            # Enforce username and password constraints
            if len(username) < MIN_USERNAME_LEN or len(password) < MIN_PASSWORD_LEN or len(username) > MAX_USERNAME_LEN or len(password) > MAX_PASSWORD_LEN:
                return {"status_code": ResponseCode.BAD_REQUEST.value}
            # Check if account exists
            if self.account_exists(username):
                return {"status_code": ResponseCode.ACCOUNT_EXISTS.value}
            # Create account
            self.cursor.execute("INSERT INTO accounts (username, password, bio) VALUES (?, ?, ?)", (username, password, bio))
            # Embed bio
            bio_embedding = model.encode(bio)  # convert bio to vector
            bio_embedding_blob = bio_embedding.tobytes()  # convert to BLOB object
            self.cursor.execute("UPDATE accounts SET bio_embedding = ? WHERE username = ?", (bio_embedding_blob, username))
            self.conn.commit()
            return {"status_code": ResponseCode.SUCCESS.value}
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            return {"status_code": ResponseCode.DATABASE_ERROR.value}
    
    def login_account(self, username, password) -> dict[int, Union[int, list[tuple]]]:
        """ Given username and password, return login status and homepage data
        
        Returns:
        - status_code: Response code
        - data: Homepage data
        """
        try:
            # Authenticate account
            self.cursor.execute("SELECT * FROM accounts WHERE username=? AND password=?", (username, password))
            user = self.cursor.fetchone()
            if not user:
                return {"status_code": ResponseCode.INVALID_CREDENTIALS.value}
            # Fetch homepage
            return self.fetch_homepage(username)
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            return {"status_code": ResponseCode.DATABASE_ERROR.value}

    def delete_account(self, username, password) -> dict[int]:
        """ Given username and password, return account deletion status """
        try:
            # Check if account exists
            if not self.account_exists(username):
                return {"status_code": ResponseCode.ACCOUNT_NOT_FOUND.value}
            # Delete account
            self.cursor.execute("DELETE FROM accounts WHERE username=?", (username,))
            self.conn.commit() # NOTE: unsent messages will be stored in undelivered
            # Delete all messages to this username
            self.cursor.execute("DELETE FROM messages WHERE receiver=?", (username,))
            self.conn.commit()
            return {"status_code": ResponseCode.SUCCESS.value}
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            return {"status_code": ResponseCode.DATABASE_ERROR.value}
    
    def fetch_homepage(self, username) -> dict[int, Union[int, list[tuple]]]:
        """ Given a username, return homepage data: count of unread messages and a list of last MAX_VIEW read messages """
        try:
            # Fetch up to last 5 messages
            self.cursor.execute("SELECT * FROM messages WHERE receiver=? AND delivered=1 ORDER BY timestamp DESC LIMIT ?", (username,MAX_VIEW,))
            messages = self.cursor.fetchall()
            # Count unread messages
            count = self.count_messages(username, False)
            assert(count != -1)
            return {"status_code": ResponseCode.SUCCESS.value, "data": [count] + messages}
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            return {"status_code": ResponseCode.DATABASE_ERROR.value}

    def list_accounts(self, pattern:str=None) -> dict[int, list[tuple]]:
        """ Return a list of all accounts, optionally filtered by a pattern """
        try:
            # Fetch all accounts that match the pattern
            if pattern is not None:
                self.cursor.execute("SELECT id, username, bio FROM accounts WHERE username LIKE ?", (f"%{pattern}%",))
            # Fetch all accounts
            else:
                self.cursor.execute("SELECT id, username, bio FROM accounts")
            accounts = self.cursor.fetchall()
            return {"status_code": ResponseCode.SUCCESS.value, "data": accounts}
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            return {"status_code": ResponseCode.DATABASE_ERROR.value}
                    
    def insert_message(self, sender, receiver, content, timestamp: int, delivered: bool) -> dict[int]:
        """ Given message content, return message insertion status """
        try:
            # Check both accounts exist
            if not self.account_exists(sender) or not self.account_exists(receiver):
                return {"status_code": ResponseCode.ACCOUNT_NOT_FOUND.value}
            # Enforce message constraints
            if len(content) < MIN_MESSAGE_LEN or len(content) > MAX_MESSAGE_LEN:
                return {"status_code": ResponseCode.BAD_REQUEST.value}
            # Insert message
            self.cursor.execute("INSERT INTO messages (sender, receiver, content, timestamp, delivered) VALUES (?, ?, ?, ?, ?)", 
                (sender, receiver, content, timestamp, delivered))
            self.conn.commit()
            return {"status_code": ResponseCode.SUCCESS.value}
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            return {"status_code": ResponseCode.MESSAGE_SEND_FAILURE.value}
    
    def delete_messages(self, username, message_ids: list) -> dict[int, Union[int, list[tuple]]]:
        """ Given a list of message ids, return message deletion status and updated homepage data """
        try:
            # Delete messages
            for m in message_ids:
                self.cursor.execute("DELETE FROM messages WHERE receiver=? AND id=?", (username, m))
            self.conn.commit()
            # Fetch updated homepage
            return self.fetch_homepage(username)
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            return {"status_code": ResponseCode.DATABASE_ERROR.value}
        # TODO: handle nonexistent ids?

    def fetch_messages_delivered(self, username, n: int) -> dict[int, list[tuple]]: 
        """ Given a username and n, return their last n delivered messages """
        try:
            # Fetch last n messages of type delivered
            self.cursor.execute("SELECT * FROM messages WHERE receiver=? AND delivered=1 ORDER BY timestamp DESC LIMIT ?",
                                (username, n))
            messages = self.cursor.fetchall()
            return {"status_code": ResponseCode.SUCCESS.value, "data": messages}
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            return {"status_code": ResponseCode.DATABASE_ERROR.value}
    
    def fetch_messages_undelivered(self, username, n: int) -> dict[int, Union[int, list[tuple]]]:
        """ Given a username and n, fetch their last n undelivered messages and return their updated homepage data """
        try:
            # Fetch last n messages of type undelivered
            self.cursor.execute("SELECT * FROM messages WHERE receiver=? AND delivered=0 ORDER BY timestamp DESC LIMIT ?",
                                (username, n))
            messages = self.cursor.fetchall()
            # Mark messages as delivered
            message_ids = [m[0] for m in messages]
            placeholders = ','.join('?' * len(message_ids))
            query = f"UPDATE messages SET delivered=1 WHERE id IN ({placeholders})"
            self.cursor.execute(query, message_ids)
            self.conn.commit()
            # Fetch homepage
            return self.fetch_homepage(username)
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            return {"status_code": ResponseCode.DATABASE_ERROR.value}
        
    def match_users(self, username) -> list:
        """Find the most similar user based on bio using cosine similarity."""
        try:
            # Fetch the user's embedding
            self.cursor.execute("SELECT bio_embedding FROM accounts WHERE username=?", (username,))
            my_blob = self.cursor.fetchone()[0]
            # Convert BLOB back to NumPy array
            my_embedding = np.frombuffer(my_blob, dtype=np.float32)

            # Fetch all other users' embeddings
            user_ids, _, bio_vectors = self.get_all_embeddings()

            # Compute cosine similarity
            similarities = np.dot(bio_vectors, my_embedding) / (np.linalg.norm(bio_vectors, axis=1) * np.linalg.norm(my_embedding))

            # Get the worst match
            worst_idx = np.argmin(similarities)
            # Get how much you don't match
            worst_similarity = round(similarities[worst_idx] * 100)

            # Return the worst match's username and bio
            self.cursor.execute("SELECT username, bio FROM accounts WHERE id=?", (user_ids[worst_idx],))
            worst_match = self.cursor.fetchone()
            return {"status_code": ResponseCode.SUCCESS.value, "data": [worst_match, worst_similarity]}
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            return {"status_code": ResponseCode.DATABASE_ERROR.value}

    def get_all_embeddings(self):
        self.cursor.execute("SELECT id, username, bio_embedding FROM accounts WHERE bio_embedding IS NOT NULL")
        users = self.cursor.fetchall()
        
        user_ids, usernames, bio_vectors = [], [], []
        
        for user_id, username, blob in users:
            bio_vector = np.frombuffer(blob, dtype=np.float32)  # Convert BLOB back to NumPy array
            user_ids.append(user_id)
            usernames.append(username)
            bio_vectors.append(bio_vector)
        
        return user_ids, usernames, np.array(bio_vectors)

    def count_messages(self, username, delivered: bool) -> int:
        """ Given a username and delivered status, return the count of delivered or undelivered messages """
        try:
            # Count messages to reciever of type delivered or undelivered
            self.cursor.execute("SELECT COUNT(*) FROM messages WHERE receiver=? AND delivered=?", (username, delivered))
            count = self.cursor.fetchone()[0]
            return count
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            return -1
    
    def account_exists(self, username) -> bool:
        """ Given a username, return whether the account exists """
        try:
            # Check if account exists
            self.cursor.execute("SELECT * FROM accounts WHERE username=?", (username,))
            user = self.cursor.fetchone()
            return user is not None
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            return -1
    
    def close(self):
        """ Close the database connection """
        self.conn.close()