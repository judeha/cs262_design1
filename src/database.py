import sqlite3
from enum import Enum
from response_codes import ResponseCode
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database_setup import database_setup

# TODO: for all, return status + fetches
# TODO: catch exceptions
# TODO: logging

class DatabaseHandler():
    def __init__(self):
        try:
            self.conn = sqlite3.connect("messages.db")
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
        # NOTE: design choice to keep open the whole connection

    def create_account(self, username, password):
        try:
            # Check if account exists
            if self.account_exists(username):
                return {"status_code": ResponseCode.ACCOUNT_EXISTS.value}
            # Create account
            self.cursor.execute("INSERT INTO accounts (username, password) VALUES (?, ?)", (username, password))
            self.conn.commit()
            return {"status_code": ResponseCode.SUCCESS.value}
        except sqlite3.Error as e:
            return {"status_code": ResponseCode.DATABASE_ERROR.value}
    
    def login_account(self, username, password):
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

    def delete_account(self, username, password):
        try:
            # Check if account exists
            if self.account_exists(username):
                return {"status_code": ResponseCode.ACCOUNT_NOT_FOUND.value}
            # Delete account
            self.cursor.execute("DELETE FROM accounts WHERE username=? AND password=?", (username, password))
            self.conn.commit()
            return {"status_code": ResponseCode.SUCCESS.value}
        except sqlite3.Error as e:
            return {"status_code": ResponseCode.DATABASE_ERROR.value}
            # TODO: handle unsent messages
    
    def fetch_homepage(self, username):
        try:
            # Fetch up to last 5 messages
            self.cursor.execute("SELECT * FROM messages WHERE receiver=? AND delivered=1 ORDER BY timestamp DESC LIMIT 5", (username,))
            messages = self.cursor.fetchall()
            # Count unread messages
            count = self.count_messages(username, False)
            assert(count != -1)
            return {"status_code": ResponseCode.SUCCESS.value, "data": {"messages": messages, "count": count}}
        except sqlite3.Error as e:
            return {"status_code": ResponseCode.DATABASE_ERROR.value}

    def list_all_accounts(self):
        try:
            # Fetch all accounts
            self.cursor.execute("SELECT * FROM accounts")
            accounts = self.cursor.fetchall()
            return {"status_code": ResponseCode.SUCCESS.value, "data": {"accounts": accounts}}
        except sqlite3.Error as e:
            return {"status_code": ResponseCode.DATABASE_ERROR.value}
        
    def insert_message(self, sender, receiver, content, timestamp, delivered):
        # TODO: in caller: handle timestamp
        # TODO: in caller: send to client
        # TODO: in caller: check if receiver is open
        try:
            # Insert message
            self.cursor.execute("INSERT INTO messages (sender, receiver, content, timestamp, delivered) VALUES (?, ?, ?, ?, ?)", 
                (sender, receiver, content, timestamp, delivered))
            self.conn.commit()
            return {"status_code": ResponseCode.SUCCESS.value}
        except sqlite3.Error as e:
            return {"status_code": ResponseCode.MESSAGE_SEND_FAILURE.value}
    
    def delete_messages(self, username, message_ids: list):
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

    def fetch_messages_delivered(self, username, n: int): 
        try:
            # Fetch last n messages of type delivered
            self.cursor.execute("SELECT * FROM messages WHERE receiver=? AND delivered=1 ORDER BY timestamp DESC LIMIT ?",
                                (username, n))
            messages = self.cursor.fetchall()
            return {"status_code": ResponseCode.SUCCESS.value, "data": {"messages": messages}}
        except sqlite3.Error as e:
            return {"status_code": ResponseCode.DATABASE_ERROR.value}
    
    def fetch_messages_undelivered(self, username, n: int):
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
            self.commit()
            # Fetch homepage
            return self.fetch_homepage(username)
        except sqlite3.Error as e:
            return {"status_code": ResponseCode.DATABASE_ERROR.value}
    
    def count_messages(self, username, delivered: bool):
        try:
            # Count messages to reciever of type delivered or undelivered
            self.cursor.execute("SELECT COUNT(*) FROM messages WHERE receiver=? AND delivered=?", (username, delivered))
            count = self.cursor.fetchone()[0]
            return count
        except sqlite3.Error as e:
            return -1
    
    def account_exists(self, username):
        try:
            # Check if account exists
            self.cursor.execute("SELECT * FROM accounts WHERE username=?", (username,))
            user = self.cursor.fetchone()
            return user is not None
        except sqlite3.Error as e:
            return -1
    
    def close(self):
        self.conn.close()
        os.remove("messages.db")

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
