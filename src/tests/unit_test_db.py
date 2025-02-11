import unittest
import sqlite3
import sys
import os
# Adjust path to ensure tests can import database_handler
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database import DatabaseHandler  # Assuming this is saved as database_handler.py
from database_setup import database_setup
from codes import ResponseCode


db_path = "messages.db"

class TestDatabaseHandler(unittest.TestCase):
    def setUp(self):
        # Initialize test database
        database_setup(db_path)
        self.db = DatabaseHandler(db_path)

    def tearDown(self):
        os.remove("messages.db")
        self.db.close()

    def test_create_account(self):
        result = self.db.create_account("test_user", "password123")
        self.assertEqual(result["status_code"], ResponseCode.SUCCESS.value)
        
        duplicate_result = self.db.create_account("test_user", "password123")
        self.assertEqual(duplicate_result["status_code"], ResponseCode.ACCOUNT_EXISTS.value)

    def test_login_account(self):
        self.db.create_account("test_user", "password123")
        result = self.db.login_account("test_user", "password123")
        self.assertEqual(result["status_code"], ResponseCode.SUCCESS.value)

        wrong_password = self.db.login_account("test_user", "wrongpassword")
        self.assertEqual(wrong_password["status_code"], ResponseCode.INVALID_CREDENTIALS.value)

    def test_insert_message(self):
        self.db.create_account("sender_user", "password")
        self.db.create_account("receiver_user", "password")
        result = self.db.insert_message("sender_user", "receiver_user", "Hello!", 1234567890, 0)
        self.assertEqual(result["status_code"], ResponseCode.SUCCESS.value) 

    def test_fetch_messages_undelivered(self):
        self.db.create_account("sender_user", "password")
        self.db.create_account("receiver_user", "password")
        self.db.insert_message("sender_user", "receiver_user", "Hello!", 1234567890, 0)
        self.db.insert_message("sender_user", "receiver_user", "How are you?", 1234567895, 0)
        
        result = self.db.fetch_messages_undelivered("receiver_user", 2)
        self.assertTrue(result["status_code"], ResponseCode.SUCCESS.value)
        self.assertTrue(result["data"][0] == 0)  # 0 unread messages should be returned
        self.assertEqual(len(result["data"][1:]), 2)  # 2 messages should be returned
        self.assertEqual(result["data"][1][1], "sender_user")

    def test_fetch_messages_delivered(self):
        self.db.create_account("sender_user", "password")
        self.db.create_account("receiver_user", "password")
        self.db.insert_message("sender_user", "receiver_user", "Hello!", 1234567890, 1)
        self.db.insert_message("sender_user", "receiver_user", "How are you?", 1234567895, 0)
        
        result = self.db.fetch_messages_delivered("receiver_user", 2)
        self.assertTrue(result["status_code"], ResponseCode.SUCCESS.value)
        self.assertTrue(len(result["data"]) == 1)  # 1 read message should be returned
        self.assertEqual(result["data"][0][0], 1)  # 2 messages should be returned
        self.assertEqual(result["data"][0][1], "sender_user")

    def test_count_messages(self):
        self.db.create_account("sender_user", "password")
        self.db.create_account("receiver_user", "password")
        self.db.insert_message("sender_user", "receiver_user", "Hello!", 1234567890, 0)
        count = self.db.count_messages("receiver_user", False)
        self.assertEqual(count, 1)

    def test_delete_account(self):
        self.db.create_account("test_user", "password123")
        result = self.db.delete_account("test_user", "password123")
        self.assertEqual(result["status_code"], ResponseCode.SUCCESS.value)

        non_existing = self.db.delete_account("fake_user", "password123")
        self.assertEqual(non_existing["status_code"], ResponseCode.ACCOUNT_NOT_FOUND.value)

    def test_delete_messages(self):
        self.db.create_account("sender_user", "password")
        self.db.create_account("receiver_user", "password")
        self.db.insert_message("sender_user", "receiver_user", "Hello!", 1234567890, 0)
        self.db.insert_message("sender_user", "receiver_user", "How are you?", 1234567895, 0)
        
        message_ids = [1, 2]
        result = self.db.delete_messages("sender_user", message_ids)
        self.assertEqual(result["status_code"], ResponseCode.SUCCESS.value)

if __name__ == '__main__':
    unittest.main()