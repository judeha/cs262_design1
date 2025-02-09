import sqlite3

# TODO: for all, return status + fetches
# TODO: catch exceptions

class DatabaseHandler():
    def __init__(self):
        self.conn = sqlite3.connect("messages.db")
        self.cursor = self.conn.cursor()
        # NOTE: design choice to keep open the whole connection

    def create_account(self, username, password):
        # Check existing account
        match_check = self.cursor.execute("SELECT EXISTS(SELECT 1 FROM accounts WHERE username=?)", (username,))
        if match_check.fetchone()[0] > 0:
            status = "Account already exists"
        # Create account
        else:
            self.cursor.execute("INSERT INTO accounts (username, password) VALUES (?, ?)", (username, password))
            self.conn.commit()
            status = "Successfully created account"
        return [status]

    def login_account(self, username, password):
        # Authenticate account
        print(username, password)
        self.cursor.execute("SELECT * FROM accounts WHERE username=? AND password=?", (username, password))
        if self.cursor.fetchall():
            status = "Successfully logged in"
        else:
            status = "Invalid credentials"
            return [status]
        # Fetch last 5 delivered messages
        self.cursor.execute("SELECT * FROM messages WHERE receiver=? AND delivered=1 ORDER BY timestamp DESC LIMIT 5", (username,))
        messages = self.cursor.fetchall()
        # Fetch count of undelivered messages
        count = self.count_messages(username,False)
        return [status, count] + messages
    
    def update_account(self, username, password):
        pass

    def delete_account(self, username, password):
        # Check existing account
        match_check = self.cursor.execute("SELECT EXISTS(SELECT 1 FROM accounts WHERE username=?)", (username,))
        if match_check.fetchone()[0] == 0:
            status = "Account does not exist"
        else:
            self.cursor.execute("DELETE FROM accounts WHERE username=? AND password=?", (username, password))
            self.conn.commit()
            status = "Successfully deleted account"
        # TODO: handle unsent messages.
        return [status]
    
    def list_all_accounts(self):
        # Fetch all accounts
        self.cursor.execute("SELECT * FROM accounts")
        accounts = self.cursor.fetchall()
        status = "Successfully fetched all accounts" # TODO: formatting?
        return [status] + accounts

    def insert_message(self, sender, receiver, content, timestamp, delivered):
        # TODO: in caller: handle timestamp
        # TODO: in caller: send to client
        # TODO: in caller: check if receiver is open
        # Add message to table
        self.cursor.execute("INSERT INTO messages (sender, receiver, content, timestamp, delivered) VALUES (?, ?, ?, ?, ?)", 
               (sender, receiver, content, timestamp, delivered))
        status = "Successfully sent message"
        return [status]
    
    def delete_messages(self, message_ids: list):
        # Delete all messages from sender to receivers
        # placeholders = ','.join('?' * (len(message_ids)))
        # query = f"DELETE FROM messages id IN ({placeholders})"
        # self.cursor.execute(query, message_ids) # NOTE: efficient?
        # TODO: handle nonexistent ids?
        for m in message_ids:
            self.cursor.execute("DELETE FROM messages WHERE id=?", (m,))
        self.conn.commit()
        status = "Successfully deleted messages"
        return [status]
    
    def count_messages(self, username, delivered: bool):
        # Count all unread messages
        self.cursor.execute("SELECT COUNT(*) FROM messages WHERE receiver=? AND delivered=?", (username,delivered))
        count = self.cursor.fetchone()[0]
        status = f"Successfully counted {count} unread messages"
        return [status, count]

    def fetch_messages(self, username, n: int, delivered: bool): # NOTE: split into two functions?
        # Fetch the last n messages sent to the client
        self.cursor.execute("SELECT * FROM messages WHERE receiver=? AND delivered=? ORDER BY timestamp DESC LIMIT ?",
                        (username,delivered,n))
        messages = self.cursor.fetchall()
        # get the message ids:
        print(messages)
        if delivered:
            status = f"Successfully fetched last {n} read messages"
        else:
            # Mark messages as delivered
            message_ids = [m[0] for m in messages]
            placeholders = ','.join('?' * (len(message_ids)))
            query = f"UPDATE messages SET delivered=1 WHERE id IN ({placeholders})"
            self.cursor.execute(query, message_ids) # NOTE: efficient?
            status = f"Successfully fetched last {n} unread messages"
        return [status] + messages

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
