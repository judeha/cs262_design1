import unittest
from unittest.mock import MagicMock, patch
import os
import threading
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import handler_pb2
import handler_pb2_grpc
from server_grpc import HandlerService
from database import DatabaseHandler
from utils import ResponseCode, database_setup
import queue

# Use a temporary database for testing
TEST_DB_PATH = "test2.db"

class TestHandlerService(unittest.TestCase):
    def setUp(self):
        """Set up a fresh HandlerService with a clean database for each test."""
        # Ensure test database resets before each test
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

        database_setup(TEST_DB_PATH)  # Fresh setup each time

        self.service = HandlerService()
        self.service.set_path(TEST_DB_PATH)

        self.addCleanup(self.tearDown)

    def tearDown(self):
        """Clean up database after each test."""
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

    def test_create_account_success(self):
        """Test successful account creation."""
        request = handler_pb2.CreateAccountRequest(username="testuser", password="password", bio="Test Bio")
        response = self.service.CreateAccount(request, None)

        self.assertEqual(response.status_code, ResponseCode.SUCCESS.value)

    def test_create_duplicate_account_fails(self):
        """Test that creating a duplicate account fails."""
        request = handler_pb2.CreateAccountRequest(username="testuser", password="password", bio="Test Bio")
        self.service.CreateAccount(request, None)  # First creation should succeed

        # Second attempt should fail
        response = self.service.CreateAccount(request, None)
        self.assertEqual(response.status_code, ResponseCode.ACCOUNT_EXISTS.value)

    def test_check_account_exists(self):
        """Test checking if an account exists."""
        self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="existing_user", password="password", bio="bio"), None)

        request = handler_pb2.AccountExistsRequest(username="existing_user")
        response = self.service.CheckAccountExists(request, None)

        self.assertEqual(response.status_code, ResponseCode.ACCOUNT_EXISTS.value)
        self.assertTrue(response.exists)

    def test_check_nonexistent_account(self):
        """Test checking an account that does not exist."""
        request = handler_pb2.AccountExistsRequest(username="missing_user")
        response = self.service.CheckAccountExists(request, None)

        self.assertEqual(response.status_code, ResponseCode.ACCOUNT_NOT_FOUND.value)
        self.assertFalse(response.exists)

    def test_login_success(self):
        """Test successful login."""
        self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="testuser", password="password", bio="bio"), None)

        request = handler_pb2.LoginAccountRequest(username="testuser", password="password")
        response = self.service.LoginAccount(request, None)

        self.assertEqual(response.status_code, ResponseCode.SUCCESS.value)

    def test_login_failure_wrong_password(self):
        """Test failed login due to incorrect password."""
        self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="testuser", password="password", bio="bio"), None)

        request = handler_pb2.LoginAccountRequest(username="testuser", password="wrongpassword")
        response = self.service.LoginAccount(request, None)

        self.assertEqual(response.status_code, ResponseCode.INVALID_CREDENTIALS.value)

    def test_list_accounts(self):
        """Test listing accounts."""
        self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="user1", password="password", bio="bio1"), None)
        self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="user2", password="password", bio="bio2"), None)

        list_request = handler_pb2.ListAccountRequest(pattern="")
        list_response = self.service.ListAccount(list_request, None)

        self.assertEqual(list_response.status_code, ResponseCode.SUCCESS.value)
        self.assertEqual(len(list_response.acct_lst), 2)

    def test_delete_account(self):
        """Test deleting an account."""
        self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="deleteuser", password="password", bio="bio"), None)

        request = handler_pb2.DeleteAccountRequest(username="deleteuser", password="password")
        response = self.service.DeleteAccount(request, None)

        self.assertEqual(response.status_code, ResponseCode.SUCCESS.value)

        # Confirm account is now gone
        check_request = handler_pb2.AccountExistsRequest(username="deleteuser")
        check_response = self.service.CheckAccountExists(check_request, None)

        self.assertEqual(check_response.status_code, ResponseCode.ACCOUNT_NOT_FOUND.value)

    def test_send_message_success(self):
        """Test sending a message between users."""
        self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="alice", password="password", bio="bio"), None)
        self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="bob", password="password", bio="bio"), None)

        # Simulate login to add them to active clients
        self.service.LoginAccount(handler_pb2.LoginAccountRequest(username="alice", password="password"), None)
        self.service.LoginAccount(handler_pb2.LoginAccountRequest(username="bob", password="password"), None)

        request = handler_pb2.SendMessageRequest(sender="alice", receiver="bob", content="Hello, Bob!")
        response = self.service.SendMessage(request, None)

        self.assertEqual(response.status_code, ResponseCode.SUCCESS.value)

    def test_receive_message(self):
        """Test that a logged-in user can receive messages."""
        self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="alice", password="password", bio="bio"), None)
        self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="bob", password="password", bio="bio"), None)

        # Simulate login to add them to active clients
        self.service.LoginAccount(handler_pb2.LoginAccountRequest(username="alice", password="password"), None)
        self.service.LoginAccount(handler_pb2.LoginAccountRequest(username="bob", password="password"), None)

        # Alice sends a message to Bob
        self.service.SendMessage(handler_pb2.SendMessageRequest(sender="alice", receiver="bob", content="Hello, Bob!"), None)

        # Bob receives the message
        request = handler_pb2.ReceiveMessageRequest(username="bob")
        response = next(self.service.ReceiveMessage(request, None))

        self.assertEqual(len(response.msg_lst), 1)
        self.assertEqual(response.msg_lst[0].content, "Hello, Bob!")

    def test_delete_message(self):
        """Test deleting a message."""
        self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="alice", password="password", bio="bio"), None)
        self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="bob", password="password", bio="bio"), None)

        # Simulate login
        self.service.LoginAccount(handler_pb2.LoginAccountRequest(username="alice", password="password"), None)
        self.service.LoginAccount(handler_pb2.LoginAccountRequest(username="bob", password="password"), None)

        # Alice sends a message to Bob
        self.service.SendMessage(handler_pb2.SendMessageRequest(sender="alice", receiver="bob", content="Hello, Bob!"), None)

        # Bob receives it
        receive_request = handler_pb2.ReceiveMessageRequest(username="bob")
        response = next(self.service.ReceiveMessage(receive_request, None))
        msg_id = response.msg_lst[0].id

        # Delete the message
        delete_request = handler_pb2.DeleteMessageRequest(username="bob", message_id_lst=[msg_id])
        delete_response = self.service.DeleteMessage(delete_request, None)

        self.assertEqual(delete_response.status_code, ResponseCode.SUCCESS.value)

    def test_login_success(self):
        """Test successful login with correct credentials."""
        self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="login_user", password="securepass", bio="test"), None)
        request = handler_pb2.LoginAccountRequest(username="login_user", password="securepass")
        response = self.service.LoginAccount(request, None)

        self.assertEqual(response.status_code, ResponseCode.SUCCESS.value)
        self.assertGreaterEqual(response.count, 0)

    def test_login_failure_wrong_password(self):
        """Test failed login due to incorrect password."""
        self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="wrong_pass_user", password="correctpass", bio="test"), None)
        request = handler_pb2.LoginAccountRequest(username="wrong_pass_user", password="incorrectpass")
        response = self.service.LoginAccount(request, None)

        self.assertEqual(response.status_code, ResponseCode.INVALID_CREDENTIALS.value)

    def test_delete_account_success(self):
        """Test successful account deletion."""
        self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="delete_user", password="pass", bio="test"), None)
        request = handler_pb2.DeleteAccountRequest(username="delete_user", password="pass")
        response = self.service.DeleteAccount(request, None)

        self.assertEqual(response.status_code, ResponseCode.SUCCESS.value)

    def test_delete_account_failure(self):
        """Ensure deletion fails for non-existent accounts."""
        request = handler_pb2.DeleteAccountRequest(username="nonexistent_user", password="pass")
        response = self.service.DeleteAccount(request, None)

        self.assertEqual(response.status_code, ResponseCode.ACCOUNT_NOT_FOUND.value)

    def test_send_message_success(self):
        """Test sending a message between two users."""
        self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="sender", password="pass", bio="test"), None)
        self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="receiver", password="pass", bio="test"), None)

        request = handler_pb2.SendMessageRequest(sender="sender", receiver="receiver", content="Hello!")
        response = self.service.SendMessage(request, None)

        self.assertEqual(response.status_code, ResponseCode.SUCCESS.value)

    def test_fetch_unread_messages(self):
        """Test retrieving unread messages."""
        self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="unread_user", password="pass", bio="test"), None)
        self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="sender", password="pass", bio="test"), None)

        self.service.SendMessage(handler_pb2.SendMessageRequest(sender="sender", receiver="unread_user", content="Unread message"), None)
        
        request = handler_pb2.FetchMessagesUnreadRequest(username="unread_user", num=10)
        response = self.service.FetchMessageUnread(request, None)

        self.assertEqual(response.status_code, ResponseCode.SUCCESS.value)
        self.assertGreater(len(response.msg_lst), 0)

    def test_list_accounts(self):
        """Test listing all accounts."""
        self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="user1", password="pass", bio="bio1"), None)
        self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="user2", password="pass", bio="bio2"), None)

        request = handler_pb2.ListAccountRequest(pattern="")
        response = self.service.ListAccount(request, None)

        self.assertEqual(response.status_code, ResponseCode.SUCCESS.value)
        self.assertGreaterEqual(len(response.acct_lst), 2)

def test_receive_message_stream(self):
    """Test receiving messages via stream without hanging."""
    self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="receiver", password="pass", bio="test"), None)
    self.service.CreateAccount(handler_pb2.CreateAccountRequest(username="sender", password="pass", bio="test"), None)

    self.service.LoginAccount(handler_pb2.LoginAccountRequest(username="receiver", password="pass"), None)

    # Ensure message is sent before streaming
    send_request = handler_pb2.SendMessageRequest(sender="sender", receiver="receiver", content="Live message")
    self.service.SendMessage(send_request, None)

    # Call ReceiveMessage (this should return quickly)
    receive_request = handler_pb2.ReceiveMessageRequest(username="receiver")
    responses = list(self.service.ReceiveMessage(receive_request, None))  # Convert generator to list

    # Assert that at least one message is received
    self.assertGreater(len(responses), 0)
    self.assertGreater(len(responses[0].msg_lst), 0)
    self.assertEqual(responses[0].msg_lst[0].content, "Live message")

if __name__ == "__main__":
    unittest.main()

