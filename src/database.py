import sqlite3
from enum import Enum
from response_codes import ResponseCode

# TODO: for all, return status + fetches
# TODO: catch exceptions
# TODO: logging e

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
            # Fetch up to last 5 messages
            self.cursor.execute("SELECT * FROM messages WHERE receiver=? AND delivered=1 ORDER BY timestamp DESC LIMIT 5", (username,))
            messages = self.cursor.fetchall()
            # Count unread messages
            count = self.count_messages(username, False)
            return {"status_code": ResponseCode.SUCCESS.value, "data": {"unread_count": count["count"], "messages": messages}}
        except sqlite3.Error as e:
            return {"status_code": ResponseCode.DATABASE_ERROR.value}

    def update_account(self, username, password):
        pass

    def delete_account(self, username, password):
        try:
            # Check if account exists
            if not self.account_exists(username):
                return {"status_code": ResponseCode.ACCOUNT_NOT_FOUND.value}
            # Delete account
            self.cursor.execute("DELETE FROM accounts WHERE username=? AND password=?", (username, password))
            self.conn.commit()
            return {"status_code": ResponseCode.SUCCESS.value}
        except sqlite3.Error as e:
            return {"status_code": ResponseCode.DATABASE_ERROR.value}
            # TODO: handle unsent messages
    
    def list_all_accounts(self):
        try:
            # Fetch all accounts
            self.cursor.execute("SELECT * FROM accounts")
            accounts = self.cursor.fetchall()
            return {"status_code": ResponseCode.SUCCESS.value, "data": accounts}
        except sqlite3.Error as e:
            return {"status_code": ResponseCode.DATABASE_ERROR.value}
        
    def account_exists(self, username):
        try:
            # Check if account exists
            match_check = self.cursor.execute("SELECT EXISTS(SELECT 1 FROM accounts WHERE username=?)", (username,))
            if match_check.fetchone()[0] == 0:
                return False
            return True
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
    
    def delete_messages(self, message_ids: list):
        try:
            # Delete all messages from sender to receivers
            placeholders = ','.join('?' * (len(message_ids)))
            query = f"DELETE FROM messages id IN ({placeholders})"
            self.cursor.execute(query, message_ids) # NOTE: efficient?
            self.conn.commit()
            return {"status_code": ResponseCode.SUCCESS.value}
        except sqlite3.Error as e:
            return {"status_code": ResponseCode.DATABASE_ERROR.value}
        # TODO: handle nonexistent ids?
        # for m in message_ids:
        #     self.cursor.execute("DELETE FROM messages WHERE id=?", (m,))
        # self.conn.commit()
        # status = "Successfully deleted messages"
    
    def count_messages(self, username, delivered: bool):
        try:
            # Count messages to reciever of type delivered or undelivered
            self.cursor.execute("SELECT COUNT(*) FROM messages WHERE receiver=? AND delivered=?", (username, delivered))
            count = self.cursor.fetchone()[0]
            return {"status_code": ResponseCode.SUCCESS.value, "count": count}
        except sqlite3.Error as e:
            return {"status_code": ResponseCode.DATABASE_ERROR.value}

    def fetch_messages(self, username, n: int, delivered: bool): 
        try:
            # Fetch last n messages of type delivered or undelivered
            self.cursor.execute("SELECT * FROM messages WHERE receiver=? AND delivered=? ORDER BY timestamp DESC LIMIT ?",
                                (username, delivered, n))
            messages = self.cursor.fetchall()
            if not delivered:
                # Mark messages as delivered
                message_ids = [m[0] for m in messages]
                placeholders = ','.join('?' * len(message_ids))
                query = f"UPDATE messages SET delivered=1 WHERE id IN ({placeholders})"
                self.cursor.execute(query, message_ids)
                self.conn.commit()
            return {"status_code": ResponseCode.SUCCESS.value, "data": messages}
        except sqlite3.Error as e:
            return {"status_code": ResponseCode.DATABASE_ERROR.value}

    def close(self):
        self.conn.close()

# DB = DatabaseHandler()
# status = DB.create_account("hannah", "$ecret")
# print(status)
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
