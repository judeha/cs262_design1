import sqlite3
from enum import Enum
import struct

class ResponseCode(Enum):
    SUCCESS = 200
    ACCOUNT_EXISTS = 4001
    INVALID_CREDENTIALS = 4002
    ACCOUNT_NOT_FOUND = 4041
    MESSAGE_SEND_FAILURE = 5001
    DATABASE_ERROR = 5000
    BAD_REQUEST = 4000
    STARTING = 0 # TODO: fragile

RESPONSE_MESSAGES = {
    ResponseCode.SUCCESS: "Operation successful",
    ResponseCode.ACCOUNT_EXISTS: "Account already exists",
    ResponseCode.INVALID_CREDENTIALS: "Invalid credentials",
    ResponseCode.BAD_REQUEST: "Bad request",
    ResponseCode.ACCOUNT_NOT_FOUND: "Account does not exist",
    ResponseCode.MESSAGE_SEND_FAILURE: "Failed to send message",
    ResponseCode.DATABASE_ERROR: "Database error",
}

class OpCode(Enum):
    STARTING = 0
    ACCOUNT_EXISTS = 1
    CREATE_ACCOUNT = 2
    LOGIN_ACCOUNT = 3
    LIST_ACCOUNTS = 4
    DELETE_ACCOUNT = 5
    HOMEPAGE = 6
    READ_MSG_UNDELIVERED = 7
    READ_MSG_DELIVERED = 8
    DELETE_MSG = 9
    SEND_MSG = 10
    RECEIVE_MSG = 11

TypeCode = {
    'int': 0,
    'str': 1,
    'bool': 2,
    'list': 3,
    'tuple': 4
}

TypeCode2 = {
    0: '>I',
    1: '>s',
    2: '?',
}

def encode_protocol(arg_lst):
    """Recursively encodes complex structures (lists, tuples) into bytes."""
    encoded = b''

    def encode_value(value):
        """Recursively encodes a single value."""
        if isinstance(value, (list, tuple)):  # If it's a nested structure
            type_code = TypeCode["list"] if isinstance(value, list) else TypeCode["tuple"]
            encoded_inner = b''.join(encode_value(v) for v in value)  # Recursively encode elements
            length = len(encoded_inner)
            return struct.pack("B", type_code) + struct.pack(">I", length) + encoded_inner
        else:  # Primitive types (int, str, bool, etc.)
            type_code = TypeCode[type(value).__name__]
            method = TypeCode2[type_code]
            encoded_value = value.encode("utf-8") if method == ">s" else struct.pack(method, value)
            return struct.pack("B", type_code) + struct.pack(">I", len(encoded_value)) + encoded_value

    for item in arg_lst:
        encoded += encode_value(item)
    
    return encoded

def decode_protocol(bytes_str):
    """Recursively decodes bytes into structured data (lists, tuples, and primitives)."""
    decoded = []

    def decode_value(byte_data):
        """Recursively decodes a single value."""
        nonlocal bytes_str  # Ensures we're modifying the original byte string
        if not byte_data:  # Prevent processing empty byte data
            return None, b""

        # Ensure there is at least 5 bytes (1 type_code + 4 length bytes)
        if len(byte_data) < 5:
            raise ValueError("Insufficient bytes for type_code and length unpacking.")

        type_code = struct.unpack("B", byte_data[:1])[0]  # Get type code
        byte_data = byte_data[1:]

        # Ensure there are enough bytes to read length
        if len(byte_data) < 4:
            raise ValueError("Insufficient bytes to extract length field.")

        length = struct.unpack(">I", byte_data[:4])[0]  # Get length
        byte_data = byte_data[4:]

        # Ensure there are enough bytes to read the actual data
        if len(byte_data) < length:
            raise ValueError(f"Expected {length} bytes but got only {len(byte_data)}.")

        sub_bytes = byte_data[:length]  # Extract the data
        byte_data = byte_data[length:]  # Remaining bytes after extraction

        if type_code in [TypeCode["list"], TypeCode["tuple"]]:  # If it's a nested structure
            sublist = []
            while sub_bytes:
                value, sub_bytes = decode_value(sub_bytes)
                if value is not None:
                    sublist.append(value)
            return (sublist if type_code == TypeCode["list"] else tuple(sublist)), byte_data
        else:  # Primitive types
            method = TypeCode2.get(type_code, None)  # Ensure method is retrieved safely
            if not method:
                raise ValueError(f"Unknown type code: {type_code}")
            value = sub_bytes[:length].decode("utf-8") if method == ">s" else struct.unpack(method, sub_bytes[:length])[0]
            return value, byte_data

    while bytes_str:
        value, bytes_str = decode_value(bytes_str)
        if value is not None:
            decoded.append(value)

    return decoded

# Connect to an SQLite database (or create it if it doesn't exist)
def database_setup(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create table
    cursor.execute('''CREATE TABLE IF NOT EXISTS accounts (
                   id INTEGER PRIMARY KEY,
                   username TEXT NOT NULL,
                   password TEXT NOT NULL)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
                   id INTEGER PRIMARY KEY,
                   sender TEXT NOT NULL,
                   receiver TEXT NOT NULL,
                   content TEXT,
                   timestamp INTEGER,
                   delivered INTEGER)''')

    # Save (commit) the changes
    conn.commit()
    conn.close()