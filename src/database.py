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
        match_check = self.cursor.execute("SELECT EXISTS(SELECT 1 FROM accounts WHERE username=?)", (username))
        if match_check.fetchone()[0] > 0:
            status = "Account already exists"
        # Create account
        else:
            self.cursor.execute("INSERT INTO accounts (username, password) VALUES (?, ?)", (username, password))
            self.conn.commit()
            status = "Successfully created account"
        return status

    def login_account(self, username, password):
        # Authenticate account
        match_password = self.cursor.execute("SELECT * FROM accounts WHERE username=? AND password=?", (username, password))
        if match_password.fetchone():
            status = "Successfully logged in"
        else:
            status = "Invalid credentials"
        return status
    
    def update_account(self, username, password):
        pass

    def delete_account(self, username, password):
        # Check existing account
        match_check = self.cursor.execute("SELECT EXISTS(SELECT 1 FROM accounts WHERE username=?)", (username))
        if match_check.fetchone()[0] == 0:
            status = "Account does not exist"
        else:
            self.cursor.execute("DELETE FROM accounts WHERE username=? AND password=?", (username, password))
            self.conn.commit()
            status = "Successfully deleted account"
        # TODO: handle unsent messages.
        return status
    
    def list_all_accounts(self):
        # Fetch all accounts
        self.cursor.execute("SELECT * FROM accounts")
        accounts = self.cursor.fetchall()
        status = "Successfully fetched all accounts" # TODO: formatting?
        return status

    def insert_message(self, sender, receiver, content, timestamp, delivered):
        # TODO: in caller: handle timestamp
        # TODO: in caller: send to client
        # TODO: in caller: check if receiver is open
        # Add message to table
        self.cursor.execute("INSERT INTO messages (sender, receiver, content, timestamp, delivered) VALUES (?, ?, ?, ?, ?)", 
               (sender, receiver, content, timestamp, delivered))
        status = "Successfully sent message"
        return status
    
    def delete_messages(self, message_ids: list):
        # Delete all messages from sender to receivers
        for m in message_ids:
            self.cursor.execute("DELETE FROM messages WHERE id=?", (id))
            # TODO: handle nonexistent ids?
        self.conn.commit()
        status = "Successfully deleted messages"
        return status

    def fetch_messages(self, username, n: int, delivered: bool):
        # Fetch the last n messages sent to the client
        self.cursor.execute("SELECT * FROM messages WHERE sender=? AND delivered=? ORDER BY timestamp DESC LIMIT ?",
                             (username, n, delivered))
        messages = self.cursor.fetchall()
        if delivered:
            status = f"Successfully fetched last {n} read messages"
        else:
            status = f"Successfully fetched last {n} unread messages"
        return status


    def close(self):
        self.conn.close()