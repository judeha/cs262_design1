import sqlite3
from enum import Enum
import struct

class ResponseCode(Enum):
    """Enumeration of server response codes."""
    SUCCESS = 200
    ACCOUNT_EXISTS = 4001
    INVALID_CREDENTIALS = 4002
    ACCOUNT_NOT_FOUND = 4041
    MESSAGE_SEND_FAILURE = 5001
    DATABASE_ERROR = 5000
    BAD_REQUEST = 4000
    STARTING = 0 # TODO: fragile

# Dictionary mapping response codes to human-readable messages"""
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
    """Enumeration of client request opcodes."""
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

# Dictionary mapping Python types to type codes
TypeCode = {
    'int': 0,
    'str': 1,
    'bool': 2,
    'list': 3,
    'tuple': 4
}

# Dictionary mapping type codes to struct format strings
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
            return struct.pack("B", type_code) + struct.pack(">I", length) + encoded_inner # Prefix with type code and length
        else:  # Base case: primitive types (int, str, bool, etc.)
            type_code = TypeCode[type(value).__name__]
            method = TypeCode2[type_code]
            encoded_value = value.encode("utf-8") if method == ">s" else struct.pack(method, value) # Encode content
            return struct.pack("B", type_code) + struct.pack(">I", len(encoded_value)) + encoded_value # Prefix with type code and length

    # Call the recursive function for each item in the list
    for item in arg_lst:
        encoded += encode_value(item)
    
    return encoded

def decode_protocol(bytes_str):
    """Recursively decodes bytes into structured data (lists, tuples, and primitives)."""
    decoded = []

    def decode_value(byte_data):
        """Recursively decodes a single value."""
        # Enforce nonempty byte string checks
        nonlocal bytes_str
        if not byte_data:
            return None, b""

        # Enforce there are at least 5 bytes (1 type_code + 4 length bytes)
        if len(byte_data) < 5:
            raise ValueError("Insufficient bytes for type_code and length unpacking.")

        # Extract type code and length
        type_code = struct.unpack("B", byte_data[:1])[0]
        byte_data = byte_data[1:]
        if len(byte_data) < 4:
            raise ValueError("Insufficient bytes to extract length field.")
        length = struct.unpack(">I", byte_data[:4])[0]
        byte_data = byte_data[4:]
        if len(byte_data) < length:
            raise ValueError(f"Expected {length} bytes but got only {len(byte_data)}.")

        # Extract the data
        sub_bytes = byte_data[:length]
        byte_data = byte_data[length:]  # Remaining bytes

        # Recursively decode nested structures
        if type_code in [TypeCode["list"], TypeCode["tuple"]]:
            sublist = []
            # Decode each value in the list/tuple
            while sub_bytes:
                value, sub_bytes = decode_value(sub_bytes)
                if value is not None:
                    sublist.append(value)
            return (sublist if type_code == TypeCode["list"] else tuple(sublist)), byte_data
        # Base case: decode primitive types
        else:
            method = TypeCode2.get(type_code, None)
            if not method:
                raise ValueError(f"Unknown type code: {type_code}")
            # Decode value as its type
            value = sub_bytes[:length].decode("utf-8") if method == ">s" else struct.unpack(method, sub_bytes[:length])[0]
            return value, byte_data

    # Decode each value in the list
    while bytes_str:
        value, bytes_str = decode_value(bytes_str)
        if value is not None:
            decoded.append(value)

    return decoded

def database_setup(db_path):
    """Creates the database and tables if they don't exist."""
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