import json
import struct
import sys

def measure_size_json(opcode, payload):
    """Measure JSON request and response size."""
    request = json.dumps({"opcode": opcode, "payload": payload}).encode("utf-8")
    request_size = sys.getsizeof(request)

    # Simulating server response (Replace with actual server call if needed)
    response = json.dumps({"status": "OK"}).encode("utf-8")
    response_size = sys.getsizeof(response)

    return request_size, response_size

def measure_size_custom(opcode, payload):
    """Measure custom binary request and response size."""
    if not isinstance(opcode, int):
        raise ValueError(f"Opcode must be an integer, got {type(opcode)}: {opcode}")

    encoded_payload = json.dumps(payload).encode("utf-8")
    request = struct.pack(">H", opcode) + struct.pack(">H", len(encoded_payload)) + encoded_payload
    request_size = sys.getsizeof(request)

    # Simulating server response (Replace with actual server call)
    response = struct.pack(">H", 0)  # Example response
    response_size = sys.getsizeof(response)

    return request_size, response_size

def main():
    operations = [
        ("CheckAccountExists", 1, {"username": "Hannah"}),
        ("CreateAccount", 2, {"username": "Jude", "password": "123", "bio": ""}),
        ("Login", 3, {"username": "Hannah", "password": "123"}),
        ("SendEmptyMessage", 4, {"sender": "Hannah", "receiver": "Jude", "content": ""}),
        ("SendShortMessage", 5, {"sender": "Hannah", "receiver": "Jude", "content": "H"}),
        ("SendHelloMessage", 6, {"sender": "Hannah", "receiver": "Jude", "content": "Hello"}),
        ("FetchUnread", 7, {"username": "Jude", "num": 1}),
        ("DeleteMessage", 8, {"username": "Jude", "msg_id": 1}),
        ("ListAccounts", 9, {"pattern": ""}),
        ("DeleteAccount", 10, {"username": "Hannah", "password": "123"})
    ]

    print("Testing JSON and Custom Binary protocols...\n")
    results = []
    for operation, opcode, payload in operations:
        json_size = measure_size_json(opcode, payload)
        custom_size = measure_size_custom(opcode, payload)
        results.append({"operation": operation, "json": json_size, "custom": custom_size})
    
    print("Results:")
    for result in results:
        print(result)

if __name__ == "__main__":
    main()
