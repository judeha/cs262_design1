import struct

encode_dict = {
    "str": ">s",
    "int": ">H", # TODO: maybe need to specify unsigned, other integer types. does type(arg) in python go that granular?
}

hdrlen = 2 # TODO: elim hard code
hdr_typelen = 3

def decode_custom_content(request: bytes) -> list:
    decoded_content = []
    print('request', request)

    # Get num of args
    num_args = struct.unpack(">H",request[:hdrlen])[0] # TODO: add check
    request = request[hdrlen:]
    print("NUM_ARGS:",num_args)
    print(f'request: {request}')

    # While arguments left
    for i in range(num_args):
        # Read argument length and type header
        arg_len = struct.unpack(">H",request[:hdrlen])[0]
        request = request[hdrlen:]
        arg_type = request[:hdr_typelen].decode("utf-8")
        request = request[hdr_typelen:]
        # Read next LEN bytes of content
        if arg_type != "str":
            arg = struct.unpack(encode_dict[arg_type],request[:arg_len])[0]
        else:
            arg = request[:arg_len].decode('utf-8')
        request = request[arg_len:]
        # Append to list
        decoded_content.append(arg)
        print(arg)
    
    # check that all bytes are read
    if len(request) > 0:
        raise ValueError("Not all bytes read")
    
    return decoded_content


encoded = b'\x00\x03\x00\x0estrcreate_account\x00\x05strhjkim\x00\x04int\x00\x0e'

decoded = decode_custom_content(encoded)
print("DECODED:",decoded)

# TODO: maybe can swap in string delimiters
# ['int', '4', 'str', 'username']
# then bytes