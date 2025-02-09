import unittest
import sqlite3
import sys
import os

# Adjust path to ensure tests can import database_handler
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database import DatabaseHandler  # Assuming this is saved as database_handler.py
from database_setup import database_setup

class TestDatabaseHandler(unittest.TestCase):
    def setUp(self):
        # Initialize test database
        database_setup()
        self.db = DatabaseHandler()

    def tearDown(self):
        os.remove("messages.db")
        self.db.close()

    def test_create_account(self):
        result = self.db.create_account("test_user", "password123")
        self.assertEqual(result, ["Successfully created account"])
        
        duplicate_result = self.db.create_account("test_user", "password123")
        self.assertEqual(duplicate_result, ["Account already exists"])

    def test_login_account(self):
        self.db.create_account("test_user", "password123")
        result = self.db.login_account("test_user", "password123")
        self.assertEqual(result[0], "Successfully logged in")

        wrong_password = self.db.login_account("test_user", "wrongpassword")
        self.assertEqual(wrong_password, ["Invalid credentials"])

    def test_insert_message(self):
        self.db.create_account("sender_user", "password")
        self.db.create_account("receiver_user", "password")
        result = self.db.insert_message("sender_user", "receiver_user", "Hello!", 1234567890, 0)
        self.assertEqual(result, ["Successfully sent message"])

    def test_fetch_messages(self):
        self.db.create_account("sender_user", "password")
        self.db.create_account("receiver_user", "password")
        self.db.insert_message("sender_user", "receiver_user", "Hello!", 1234567890, 0)
        self.db.insert_message("sender_user", "receiver_user", "How are you?", 1234567895, 0)
        
        result = self.db.fetch_messages("receiver_user", 2, False)
        self.assertTrue("Successfully fetched last 2 unread messages" in result[0])
        self.assertEqual(len(result) - 1, 2)  # 2 messages should be returned

    def test_count_messages(self):
        self.db.create_account("sender_user", "password")
        self.db.create_account("receiver_user", "password")
        self.db.insert_message("sender_user", "receiver_user", "Hello!", 1234567890, 0)
        count = self.db.count_messages("receiver_user", False)
        self.assertEqual(count, ["Successfully counted 1 unread messages", 1])

    def test_delete_account(self):
        self.db.create_account("test_user", "password123")
        result = self.db.delete_account("test_user", "password123")
        self.assertEqual(result, ["Successfully deleted account"])

        non_existing = self.db.delete_account("fake_user", "password123")
        self.assertEqual(non_existing, ["Account does not exist"])

    def test_delete_messages(self):
        self.db.create_account("sender_user", "password")
        self.db.create_account("receiver_user", "password")
        self.db.insert_message("sender_user", "receiver_user", "Hello!", 1234567890, 0)
        self.db.insert_message("sender_user", "receiver_user", "How are you?", 1234567895, 0)
        
        message_ids = [1, 2]
        result = self.db.delete_messages(message_ids)
        self.assertEqual(result, ["Successfully deleted messages"])

if __name__ == '__main__':
    unittest.main()