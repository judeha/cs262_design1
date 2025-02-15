import struct
from codes import TypeCode, TypeCode2

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
