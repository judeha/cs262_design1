import grpc
import pytest
from concurrent import futures
from server_2 import HandlerService  # Import your gRPC service
import handler_pb2
import handler_pb2_grpc


@pytest.fixture(scope="module")
def grpc_test_server():
    """Creates a test gRPC server with the HandlerService."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    handler_pb2_grpc.add_HandlerServicer_to_server(HandlerService(), server)
    port = server.add_insecure_port("[::]:65432")
    server.start()
    yield f"localhost:{port}"
    server.stop(0)


@pytest.fixture
def grpc_stub(grpc_test_server):
    """Creates a gRPC test client stub."""
    channel = grpc.insecure_channel(grpc_test_server)
    return handler_pb2_grpc.HandlerStub(channel)


def test_create_account(grpc_stub):
    """Test account creation with valid credentials."""
    response = grpc_stub.CreateAccount(
        handler_pb2.CreateAccountRequest(username="testuser", password="testpass", bio="Test Bio")
    )
    assert response.status_code == 0  # Assuming SUCCESS = 0


def test_check_account_exists(grpc_stub):
    """Test checking if an existing account exists."""
    response = grpc_stub.CheckAccountExists(
        handler_pb2.AccountExistsRequest(username="testuser")
    )
    assert response.status_code == 1  # Assuming ACCOUNT_EXISTS = 1
    assert response.exists


def test_login_account(grpc_stub):
    """Test logging into an existing account."""
    response = grpc_stub.LoginAccount(
        handler_pb2.LoginAccountRequest(username="testuser", password="testpass")
    )
    assert response.status_code == 0  # SUCCESS
    assert isinstance(response.count, int)


def test_list_accounts(grpc_stub):
    """Test listing accounts with an optional pattern."""
    response = grpc_stub.ListAccount(
        handler_pb2.ListAccountRequest(pattern="test")
    )
    assert response.status_code == 0  # SUCCESS
    assert len(response.acct_lst) > 0
    assert response.acct_lst[0].username == "testuser"


def test_send_message(grpc_stub):
    """Test sending a message between two users."""
    response = grpc_stub.SendMessage(
        handler_pb2.SendMessageRequest(sender="testuser", receiver="anotheruser", content="Hello!")
    )
    assert response.status_code == 0  # SUCCESS


def test_fetch_unread_messages(grpc_stub):
    """Test fetching unread messages."""
    response = grpc_stub.FetchMessageUnread(
        handler_pb2.FetchMessagesUnreadRequest(username="anotheruser", num=5)
    )
    assert response.status_code == 0  # SUCCESS
    assert isinstance(response.count, int)


def test_delete_account(grpc_stub):
    """Test deleting an account."""
    response = grpc_stub.DeleteAccount(
        handler_pb2.DeleteAccountRequest(username="testuser", password="testpass")
    )
    assert response.status_code == 0  # SUCCESS


def test_ending(grpc_stub):
    """Test ending the session."""
    response = grpc_stub.Ending(
        handler_pb2.EndingRequest(username="testuser")
    )
    assert response.status_code == 0  # SUCCESS



def test_ending(grpc_stub):
    pass

