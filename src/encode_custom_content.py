import struct

encode_dict = {
    "str": ">s",
    "int": ">H", # TODO: maybe need to specify unsigned, other integer types. does type(arg) in python go that granular?
}

def encode_custom_content(*args):
    encoded_content = b''

    # While arguments left
    for arg in args:
        # Create argument type header, argument type length
        arg_type_hdr = type(arg).__name__
        if arg_type_hdr != "str":
            arg_len_hdr = 4
        else:
            arg_len_hdr = len(arg)
        # Encode argument headers
        hdr = struct.pack(">H",arg_len_hdr) + bytes(arg_type_hdr, encoding="utf-8")
        # TODO: create dict for types
        # TODO: > is for big endian, may need to add support for little endian thru another fn input or similar
        # Get proper encoding code for the content type
        code = encode_dict[arg_type_hdr]
        # Encode argument
        if code == ">s":
            arg = bytes(arg, encoding="utf-8") # NOTE: struct expects fixed size, for var length use bytes
        else:
            arg = struct.pack(code,arg)

        encoded_content += (hdr + arg)
        # print(encoded_content)

    # Prefix with num of args header
    num_args = len(args)
    encoded_content = struct.pack(">H",num_args) + encoded_content
    
    return encoded_content

a = "create_account"
b = "hjkim"
c = 14

encoded = encode_custom_content(a,b,c)
print("ENCODED:",encoded)