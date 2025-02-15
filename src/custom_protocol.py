import struct
from codes import TypeCode, TypeCode2

""" Given a list of arguments, convert them to bytes prefixed with their type code and length """
def encode_protocol(arg_lst):
    encoded = b''
    # For each argument
    for a in arg_lst:
        # Get argument type
        type_code = TypeCode[type(a).__name__]
        method = TypeCode2[type_code]
        print(method)
        # Encode argument content
        if method == ">s":
            encoded_arg = bytes(a, "utf-8") # encode string
        else:
            encoded_arg = struct.pack(method, a) # encode other types
        # Get argument length and pack
        encoded += struct.pack("B", type_code) + struct.pack(">I", len(encoded_arg)) + encoded_arg
    return encoded

def decode_protocol(bytes_str):
    """ Given a byte string, decode it into a list of arguments """
    decoded = []
    # For each argument
    while bytes_str:
        # Get type code
        type_code = TypeCode2[struct.unpack("B", bytes_str[:1])[0]]
        bytes_str = bytes_str[1:]
        # Get argument length
        length = struct.unpack(">I", bytes_str[:4])[0]
        bytes_str = bytes_str[4:]
        # Decode argument content
        if type_code == ">s":
            arg = bytes_str[:length].decode("utf-8")
        else:
            arg = struct.unpack(type_code, bytes_str[:length])[0]
        # Update bytes string and decoded result
        bytes_str = bytes_str[length:]
        decoded += [arg]
    return decoded

# a = {"status_code": [200], "data": [8,[(1,"amy","hannah","hi hannah",12002,False),(2, "jane","hannah","hi :)",12040,True)]]}

# flattened_lst = a["status_code"] + [a["data"][0]] + [item for message in a["data"][1:][0] for item in message]
# print(flattened_lst)

# encoded_a = encode_protocol(flattened_lst)
# print(encoded_a)

# decoded_a = decode_protocol(encoded_a)
# print(decoded_a)