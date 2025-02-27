import unittest
import sys
import os
import struct
import hashlib
from unittest.mock import MagicMock, patch
import selectors
import socket
# Adjust path to ensure tests can import database_handler
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database import DatabaseHandler
from utils import database_setup, ResponseCode, OpCode, encode_protocol, decode_protocol
from client_handler import Message, MessageCustom

db_path = "test_messages.db"

class TestDatabaseHandler(unittest.TestCase):
    def setUp(self):
        # Initialize test database
        database_setup(db_path)
        self.db = DatabaseHandler(db_path)

    def tearDown(self):
        os.remove(db_path)
        self.db.close()

    ## UNIT TESTS

    def test_create_account_success(self):
        """Test successful account creation."""
        response = self.db.create_account("testuser", "password123")
        self.assertEqual(response["status_code"], ResponseCode.SUCCESS.value)

    def test_create_account_already_exists(self):
        """Test account creation when the username already exists."""
        self.db.create_account("testuser", "password123")
        response = self.db.create_account("testuser", "newpassword")
        self.assertEqual(response["status_code"], ResponseCode.ACCOUNT_EXISTS.value)
    
    def test_create_account_special_char(self):
        """Test account creation for fields with special characters."""
        result = self.db.create_account("test_user", "pa$$word123")
        self.assertEqual(result["status_code"], ResponseCode.SUCCESS.value)

    def test_login_success(self):
        """Test successful login."""
        self.db.create_account("testuser", "password123")
        response = self.db.login_account("testuser", "password123")
        self.assertEqual(response["status_code"], ResponseCode.SUCCESS.value)

    def test_login_invalid_credentials(self):
        """Test login with incorrect credentials."""
        self.db.create_account("testuser", "password123")
        response = self.db.login_account("testuser", "wrongpassword")
        self.assertEqual(response["status_code"], ResponseCode.INVALID_CREDENTIALS.value)

    def test_login_special_char(self):
        """Test login for credential with special characters."""
        self.db.create_account("test_user", "pa$$word123")
        result = self.db.login_account("test_user", "pa$$word123")
        self.assertEqual(result["status_code"], ResponseCode.SUCCESS.value)

    def test_delete_account_success(self):
        """Test successful account deletion."""
        self.db.create_account("testuser", "password123")
        response = self.db.delete_account("testuser", "password123")
        self.assertEqual(response["status_code"], ResponseCode.SUCCESS.value)

    def test_delete_account_not_found(self):
        """Test deletion of a non-existent account."""
        response = self.db.delete_account("nonexistent", "password123")
        self.assertEqual(response["status_code"], ResponseCode.ACCOUNT_NOT_FOUND.value)

    def test_list_all_accounts(self):
        """Test retrieving all accounts."""
        self.db.create_account("amy", "pass1")
        self.db.create_account("hannah", "pass2")
        self.db.conn.commit()

        response = self.db.list_accounts()
        self.assertEqual(response["status_code"], ResponseCode.SUCCESS.value)
        self.assertEqual(len(response["data"]), 2)

    def test_list_accounts_with_pattern(self):
        """Test listing accounts with a pattern."""
        self.db.create_account("amy", "pass1")
        self.db.create_account("hannah", "pass2")
        self.db.create_account("alex", "pass2")
        self.db.create_account("amanda", "pass2")
        self.db.conn.commit()
    
        response = self.db.list_accounts(pattern="am")
        self.assertEqual(response["status_code"], ResponseCode.SUCCESS.value)
        usernames = [username for _, username in response["data"]]
        self.assertCountEqual(usernames, ["amy", "amanda"])  # Expecting only "amy" and "amanda"

    def test_list_accounts_with_no_match(self):
        """Test listing accounts with a pattern that has no matches."""
        response = self.db.list_accounts("xyz")
        self.assertEqual(response["status_code"], ResponseCode.SUCCESS.value)
        self.assertEqual(response["data"], [])  # Expecting an empty list

    def test_list_accounts_db_error(self):
        """Test handling of a database error."""
        self.db.cursor.execute("DROP TABLE accounts")  # Cause a database error
        response = self.db.list_accounts()
        self.assertEqual(response["status_code"], ResponseCode.DATABASE_ERROR.value)

    def test_insert_message_success(self):
        """Test successful message insertion."""
        self.db.create_account("user1", "pass1")
        self.db.create_account("user2", "pass2")
        response = self.db.insert_message("user1", "user2", "Hello", 1234567890, False)
        self.assertEqual(response["status_code"], ResponseCode.SUCCESS.value)

    def test_fetch_homepage(self):
        """Test fetching homepage data."""
        self.db.create_account("user1", "pass1")
        response = self.db.fetch_homepage("user1")
        self.assertEqual(response["status_code"], ResponseCode.SUCCESS.value)
       
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

    ## BOUNDARY TESTS

    def test_create_account_empty_username(self):
        """Test account creation with an empty username."""
        response = self.db.create_account("", "password123")
        self.assertEqual(response["status_code"], ResponseCode.BAD_REQUEST.value)

    def test_create_account_long_username(self):
        """Test account creation with a very long username."""
        long_username = "u" * 300
        response = self.db.create_account(long_username, "password123")
        self.assertEqual(response["status_code"], ResponseCode.BAD_REQUEST.value)

    def test_login_empty_password(self):
        """Test login with an empty password."""
        self.db.create_account("user1", "pass1")
        response = self.db.login_account("user1", "")
        self.assertEqual(response["status_code"], ResponseCode.INVALID_CREDENTIALS.value)

    def test_insert_message_long_content(self):
        """Test inserting a message with long content."""
        long_message = "A" * 10000
        self.db.create_account("user1", "pass1")
        self.db.create_account("user2", "pass2")
        response = self.db.insert_message("user1", "user2", long_message, 1234567890, False)
        self.assertEqual(response["status_code"], ResponseCode.BAD_REQUEST.value)

    def test_insert_message_long_timestamp(self):
        """Test inserting a message with long content."""
        long_timestamp = 2^64
        self.db.create_account("user1", "pass1")
        self.db.create_account("user2", "pass2")
        response = self.db.insert_message("user1", "user2", "a", long_timestamp, False)
        self.assertEqual(response["status_code"], ResponseCode.SUCCESS.value)

    def test_fetch_messages_zero(self):
        """Test fetching 0 messages."""
        self.db.create_account("user1", "pass1")
        response = self.db.fetch_messages_delivered("user1", 0)
        self.assertEqual(response["status_code"], ResponseCode.SUCCESS.value)
        self.assertEqual(len(response["data"]), 0)

    def test_fetch_messages_limit(self):
        """Test fetching more messages than exist."""
        self.db.create_account("user1", "pass1")
        response = self.db.fetch_messages_delivered("user1", 2)
        self.assertEqual(response["status_code"], ResponseCode.SUCCESS.value)
        self.assertEqual(len(response["data"]), 0)

    ## ERROR TESTS

    def test_delete_nonexistent_message(self):
        """Test deletion of a message that does not exist."""
        self.db.create_account("user1", "pass1")
        response = self.db.delete_messages("user1", [999])
        self.assertEqual(response["status_code"], ResponseCode.SUCCESS.value)

    def test_insert_message_invalid_user(self):
        """Test inserting a message for a non-existent user."""
        response = self.db.insert_message("user1", "fakeuser", "Hello", 1234567890, False)
        self.assertEqual(response["status_code"], ResponseCode.ACCOUNT_NOT_FOUND.value)

    def test_fetch_messages_invalid_user(self):
        """Test fetching messages for a non-existent user."""
        response = self.db.fetch_messages_delivered("fakeuser", 5)
        self.assertEqual(response["status_code"], ResponseCode.SUCCESS.value)
        self.assertEqual(len(response["data"]), 0)

    def test_count_messages_invalid_user(self):
        """Test counting messages for a non-existent user."""
        count = self.db.count_messages("fakeuser", True)
        self.assertEqual(count, 0)

    def test_account_exists_invalid_sql(self):
        """Test account existence check for an invalid SQL case."""
        response = self.db.account_exists("' OR '1'='1")
        self.assertFalse(response)


class TestProtocolEncoding(unittest.TestCase):
    
    def test_simple_types(self):
        """Test encoding and decoding of primitive types."""
        test_cases = [
            ([42], [42]),  # Integer
            (["hello"], ["hello"]),  # String
            ([True, False], [True, False]),  # Boolean
        ]
        for original, expected in test_cases:
            with self.subTest(original=original):
                encoded = encode_protocol(original)
                decoded = decode_protocol(encoded)
                self.assertEqual(decoded, expected)

    def test_nested_tuples(self):
        """Test encoding and decoding of nested tuples."""
        original = [200, 0, [(1, "amy", "hannah", "hiii", 3030, False)]]
        encoded = encode_protocol(original)
        decoded = decode_protocol(encoded)
        self.assertEqual(decoded, original)

    def test_multiple_nested_tuples(self):
        """Test encoding and decoding of multiple nested tuples in a list."""
        original = [200, 0, [(1, "amy", "hannah", "hiii", 3030, False), 
                             (2, "hannah", "amy", "booo", 3031, True)]]
        encoded = encode_protocol(original)
        decoded = decode_protocol(encoded)
        self.assertEqual(decoded, original)

    def test_empty_list(self):
        """Test encoding and decoding of an empty list."""
        original = []
        encoded = encode_protocol(original)
        decoded = decode_protocol(encoded)
        self.assertEqual(decoded, original)

    def test_single_element_tuple(self):
        """Test encoding and decoding of a list containing a tuple with one element."""
        original = [(1,)]
        encoded = encode_protocol(original)
        decoded = decode_protocol(encoded)
        self.assertEqual(decoded, original)

    def test_mixed_types(self):
        """Test encoding and decoding of a list containing mixed types."""
        original = [200, "hello", [1,"hi"], False, (1, "amy", "hannah", "hi", 3030, False)]
        encoded = encode_protocol(original)
        decoded = decode_protocol(encoded)
        self.assertEqual(decoded, original)

    def test_deeply_nested_structure(self):
        """Test encoding and decoding of deeply nested lists and tuples."""
        original = [200, 0, [(1, "amy", ["hannah", ["hi", 3030]], False)]]
        encoded = encode_protocol(original)
        decoded = decode_protocol(encoded)
        self.assertEqual(decoded, original)


class TestPassswordHashing(unittest.TestCase):
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def test_hash_password(self):
        password = "securepassword"
        hashed_password = self.hash_password(password)
        self.assertNotEqual(password, hashed_password)  # Ensure password is hashed
        self.assertEqual(len(hashed_password), 64)  # SHA-256 hash length is always 64
    
    def test_check_password_valid(self):
        password = "securepassword"
        hashed_password = self.hash_password(password)
        self.assertEqual(self.hash_password(password), hashed_password)
    
    def test_check_password_invalid(self):
        password = "securepassword"
        wrong_password = "wrongpassword"
        hashed_password = self.hash_password(password)
        self.assertNotEqual(self.hash_password(wrong_password), hashed_password)


class TestMessage(unittest.TestCase):

    def setUp(self):
        """Set up mock objects for testing"""
        self.selector = selectors.DefaultSelector()
        self.sock = MagicMock(spec=socket.socket)
        self.addr = ("127.0.0.1", 65432)
        self.request = {
            "content_encoding": "utf-8",
            "opcode": 1,
            "content": {"args": ["test"]}
        }
        self.incoming_queue = MagicMock()

        self.client_message = Message(self.selector, self.sock, self.addr, self.request, self.incoming_queue)

    def test_json_encoding_decoding(self):
        """Test JSON encoding and decoding"""
        obj = {"key": "value"}
        encoded = self.client_message._json_encode(obj, "utf-8")
        decoded = self.client_message._json_decode(encoded, "utf-8")
        self.assertEqual(obj, decoded)

    def test_package_request(self):
        """Test packaging a request"""
        packed_request = self.client_message._package_request(self.request)
        self.assertIsInstance(packed_request, bytes)
        self.assertGreater(len(packed_request), 0)

    def test_process_protoheader(self):
        """Test processing protoheader"""
        self.client_message._recv_buffer = struct.pack(">H", 1) + struct.pack(">H", 10)
        self.client_message.process_protoheader()
        self.assertEqual(self.client_message._header_len, 10)

    def test_process_header(self):
        """Test processing headers"""
        header = {
            "content_encoding": "utf-8",
            "content_length": 15,
            "opcode": 1
        }
        encoded_header = self.client_message._json_encode(header, "utf-8")
        self.client_message._recv_buffer = encoded_header
        self.client_message._header_len = len(encoded_header)

        self.client_message.process_header()
        self.assertEqual(self.client_message._header["opcode"], 1)
        self.assertEqual(self.client_message._header["content_length"], 15)

    def test_queue_request(self):
        """Test queuing a request for sending"""
        self.client_message.queue_request()
        self.assertTrue(self.client_message._request_queued)
        self.assertGreater(len(self.client_message._send_buffer), 0)

    def test_generate_action(self):
        """Test generating an action"""
        self.client_message._generate_action(1, 200, ["OK"])
        self.client_message.incoming_queue.put.assert_called_with({"opcode": 1, "status_code": 200, "data": ["OK"]})

class TestMessageCustom(unittest.TestCase):

    def setUp(self):
        """Set up mock objects for testing"""
        self.selector = selectors.DefaultSelector()
        self.sock = MagicMock(spec=socket.socket)
        self.addr = ("127.0.0.1", 65432)
        self.request = {
            "content_encoding": "utf-8",
            "opcode": 1,
            "content": {"args": ["test"]}
        }
        self.incoming_queue = MagicMock()

        self.client_message_custom = MessageCustom(self.selector, self.sock, self.addr, self.request, self.incoming_queue)

    def test_package_request_custom(self):
        """Test packaging a request in custom format"""
        packed_request = self.client_message_custom._package_request(self.request)
        self.assertIsInstance(packed_request, bytes)
        self.assertGreater(len(packed_request), 0)

    def test_process_header_custom(self):
        """Test processing headers in custom format"""
        header = encode_protocol(["utf-8", 15, 1])
        self.client_message_custom._recv_buffer = header
        self.client_message_custom._header_len = len(header)

        self.client_message_custom.process_header()
        self.assertEqual(self.client_message_custom._header["opcode"], 1)
        self.assertEqual(self.client_message_custom._header["content_length"], 15)

    def test_generate_action_custom(self):
        """Test generating an action in custom format"""
        self.client_message_custom._generate_action(1, 200, ["OK"])
        self.client_message_custom.incoming_queue.put.assert_called_with({"opcode": 1, "status_code": 200, "data": ["OK"]})

if __name__ == '__main__':
    unittest.main()