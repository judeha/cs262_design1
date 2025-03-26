import grpc
import handler_pb2
import handler_pb2_grpc
import sys

def measure_size_grpc(stub, request, func):
    """Measure gRPC request and response size."""
    request_size = sys.getsizeof(request.SerializeToString())

    try:
        response = func(request)
        response_size = sys.getsizeof(response.SerializeToString())
    except grpc.RpcError as e:
        print(f"gRPC Error: {e}")
        response_size = -1  # Indicate an error occurred

    return request_size, response_size

def test_grpc():
    """Test various gRPC requests and measure their sizes."""
    grpc_channel = grpc.insecure_channel("localhost:65432")  # Update port if necessary
    grpc_stub = handler_pb2_grpc.HandlerStub(grpc_channel)

    operations = [
        ("CheckAccountExists", handler_pb2.AccountExistsRequest(username="Hannah"), grpc_stub.CheckAccountExists),
        ("CreateAccount", handler_pb2.CreateAccountRequest(username="Jude", password="123", bio=""), grpc_stub.CreateAccount),
        ("Login", handler_pb2.LoginAccountRequest(username="Hannah", password="123"), grpc_stub.LoginAccount),
        ("SendEmptyMessage", handler_pb2.SendMessageRequest(sender="Hannah", receiver="Jude", content=""), grpc_stub.SendMessage),
        ("SendShortMessage", handler_pb2.SendMessageRequest(sender="Hannah", receiver="Jude", content="H"), grpc_stub.SendMessage),
        ("SendHelloMessage", handler_pb2.SendMessageRequest(sender="Hannah", receiver="Jude", content="Hello"), grpc_stub.SendMessage),
        ("FetchUnread", handler_pb2.FetchMessagesUnreadRequest(username="Jude", num=1), grpc_stub.FetchMessageUnread),
        ("DeleteMessage", handler_pb2.DeleteMessageRequest(username="Jude", message_id_lst=[1]), grpc_stub.DeleteMessage),
        ("ListAccounts", handler_pb2.ListAccountRequest(pattern=""), grpc_stub.ListAccount),
        ("DeleteAccount", handler_pb2.DeleteAccountRequest(username="Hannah", password="123"), grpc_stub.DeleteAccount)
    ]

    print("Testing gRPC protocol...\n")
    results = []

    for operation, grpc_request, grpc_func in operations:
        grpc_size = measure_size_grpc(grpc_stub, grpc_request, grpc_func)
        results.append({"operation": operation, "grpc": grpc_size})

    print("Results:")
    for result in results:
        print(result)

if __name__ == "__main__":
    test_grpc()
