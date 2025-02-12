import sqlite3
from enum import Enum
from codes import ResponseCode
from typing import Union
import yaml

# TODO: logging

# Read config file
yaml_path = "config.yaml"
with open(yaml_path) as y:
    config_dict = yaml.safe_load(y)
version = config_dict["version"]
key = config_dict["key"]
db_path = config_dict["db_path"] # TODO: can probably pass in the main server file
min_username_len = config_dict["min_username_len"]
min_password_len = config_dict["min_password_len"]
max_username_len = config_dict["max_username_len"]
max_password_len = config_dict["max_password_len"]
min_message_len = config_dict["min_message_len"]
max_message_len = config_dict["max_message_len"]

class DatabaseHandler():
    def __init__(self, path):
        """ Initialize connection given database path """
        try:
            self.path = path
            self.conn = sqlite3.connect(self.path)
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")

    def create_account(self, username, password) -> dict[int]:
        """ Given username and password, return account creation status """
        try:
            # Enforce username and password constraints
            if len(username) < min_username_len or len(password) < 1 or len(username) > 100 or len(password) > 100:
                return {"status_code": ResponseCode.BAD_REQUEST.value}
            # Check if account exists
            if self.account_exists(username):
                return {"status_code": ResponseCode.ACCOUNT_EXISTS.value}
            # Create account
            self.cursor.execute("INSERT INTO accounts (username, password) VALUES (?, ?)", (username, password))
            self.conn.commit()
            return {"status_code": ResponseCode.SUCCESS.value}
        except sqlite3.Error as e:
            return {"status_code": ResponseCode.DATABASE_ERROR.value}
    
    def login_account(self, username, password) -> dict[int, Union[int, list[tuple]]]:
        """ Given username and password, return login status and homepage data """
        try:
            # Authenticate account
            # TODO: decrypt password
            self.cursor.execute("SELECT * FROM accounts WHERE username=? AND password=?", (username, password))
            user = self.cursor.fetchone()
            if not user:
                return {"status_code": ResponseCode.INVALID_CREDENTIALS.value}
            # Fetch homepage
            return self.fetch_homepage(username)
        except sqlite3.Error as e:
            return {"status_code": ResponseCode.DATABASE_ERROR.value}

    def delete_account(self, username, password) -> dict[int]:
        """ Given username and password, return account deletion status """
        try:
            # Check if account exists
            if not self.account_exists(username):
                return {"status_code": ResponseCode.ACCOUNT_NOT_FOUND.value}
            # Delete account
            self.cursor.execute("DELETE FROM accounts WHERE username=? AND password=?", (username, password))
            self.conn.commit() # NOTE: unsent messages will be stored in undelivered
            return {"status_code": ResponseCode.SUCCESS.value}
        except sqlite3.Error as e:
            return {"status_code": ResponseCode.DATABASE_ERROR.value}
    
    def fetch_homepage(self, username) -> dict[int, Union[int, list[tuple]]]:
        """ Given a username, return homepage data: count of unread messages and a list of last 5 read messages """
        try:
            # Fetch up to last 5 messages
            self.cursor.execute("SELECT * FROM messages WHERE receiver=? AND delivered=1 ORDER BY timestamp DESC LIMIT 5", (username,)) # TODO: add 5 to config, restructure config
            messages = self.cursor.fetchall()
            # Count unread messages
            count = self.count_messages(username, False)
            assert(count != -1)
            return {"status_code": ResponseCode.SUCCESS.value, "data": [count] + messages}
        except sqlite3.Error as e:
            return {"status_code": ResponseCode.DATABASE_ERROR.value}

    def list_accounts(self) -> dict[int, list[tuple]]:
        """ Return a list of all accounts """
        try:
            # Fetch all accounts
            self.cursor.execute("SELECT * FROM accounts")
            accounts = self.cursor.fetchall()
            return {"status_code": ResponseCode.SUCCESS.value, "data": accounts}
        except sqlite3.Error as e:
            return {"status_code": ResponseCode.DATABASE_ERROR.value}
        
    def insert_message(self, sender, receiver, content, timestamp: int, delivered: bool) -> dict[int]:
        """ Given message content, return message insertion status """
        try:
            # Check both accounts exist
            if not self.account_exists(sender) or not self.account_exists(receiver):
                return {"status_code": ResponseCode.ACCOUNT_NOT_FOUND.value}
            # Enforce message constraints
            if len(content) < min_message_len or len(content) > max_message_len:
                return {"status_code": ResponseCode.BAD_REQUEST.value}
            # Insert message
            self.cursor.execute("INSERT INTO messages (sender, receiver, content, timestamp, delivered) VALUES (?, ?, ?, ?, ?)", 
                (sender, receiver, content, timestamp, delivered))
            self.conn.commit()
            return {"status_code": ResponseCode.SUCCESS.value}
        except sqlite3.Error as e:
            return {"status_code": ResponseCode.MESSAGE_SEND_FAILURE.value}
    
    def delete_messages(self, username, message_ids: list) -> dict[int, Union[int, list[tuple]]]:
        """ Given a list of message ids, return message deletion status and updated homepage data """
        try:
            # Delete all messages from sender to receivers
            # placeholders = ','.join('?' * (len(message_ids)))
            # query = f"DELETE FROM messages id IN ({placeholders})"
            # self.cursor.execute(query, message_ids) # NOTE: efficient?
            for m in message_ids:
                self.cursor.execute("DELETE FROM messages WHERE receiver=? AND id=?", (username, m))
            self.conn.commit()
            return self.fetch_homepage(username)
        except sqlite3.Error as e:
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
            return {"status_code": ResponseCode.DATABASE_ERROR.value}
    
    def fetch_messages_undelivered(self, username, n: int) -> dict[int, Union[int, list[tuple]]]:
        """ Given a username and n, fetch their last n undelivered messages and return their updated homepage data """
        try:
            # Fetch last n messages of type undelivered
            self.cursor.execute("SELECT * FROM messages WHERE receiver=? AND delivered=0 ORDER BY timestamp DESC LIMIT ?",
                                (username, n))
            messages = self.cursor.fetchall()
            assert(len(messages) <= n)
            # Mark messages as delivered
            message_ids = [m[0] for m in messages]
            placeholders = ','.join('?' * len(message_ids))
            query = f"UPDATE messages SET delivered=1 WHERE id IN ({placeholders})"
            self.cursor.execute(query, message_ids)
            self.conn.commit()
            # Fetch homepage
            return self.fetch_homepage(username)
        except sqlite3.Error as e:
            return {"status_code": ResponseCode.DATABASE_ERROR.value}
    
    def count_messages(self, username, delivered: bool) -> int:
        """ Given a username and delivered status, return the count of delivered or undelivered messages """
        try:
            # Count messages to reciever of type delivered or undelivered
            self.cursor.execute("SELECT COUNT(*) FROM messages WHERE receiver=? AND delivered=?", (username, delivered))
            count = self.cursor.fetchone()[0]
            return count
        except sqlite3.Error as e:
            return -1
    
    def account_exists(self, username) -> bool:
        """ Given a username, return whether the account exists """
        try:
            # Check if account exists
            self.cursor.execute("SELECT * FROM accounts WHERE username=?", (username,))
            user = self.cursor.fetchone()
            if user is not None:
                return {"status_code": ResponseCode.SUCCESS.value, "data": []}
            # else:
        except sqlite3.Error as e:
            return -1
    
    def close(self):
        self.conn.close()
        # os.remove('messages.db')

# database_setup()
# DB = DatabaseHandler()
# status = DB.create_account("hannah", "password")
# status = DB.account_exists("hannah")
# print(status)
# DB.close()
# status = DB.create_account("bob", "pa$$word")
# print(status)
# status = DB.login_account("hannah", "secret")
# print(status)
# status = DB.login_account("hannah", "$ecret")
# print(status)

# status = DB.insert_message("hannah", "bob", "Hello, Bob!", 1234567890, 0)
# status = DB.insert_message("hannah", "bob", "BOB RESPOND!", 1234567895, 0)
# print(status)
# DB.login_account("bob", "pa$$word")
# count = DB.count_messages("bob", False)
# print(count)
# status = DB.fetch_messages("bob", 2, False)
# print(status)
