import struct
from codes import TypeCode, TypeCode2

text = "hello\snfgkdsk`\nthis is my $ content| split here"
encoded = bytes(text, "utf-8")
decoded = encoded.decode("utf-8")
lst = decoded.split("|")
print(lst)

# # print the contents of a sqlite3 database
# import sqlite3

# conn = sqlite3.connect("messages.db")
# cursor = conn.cursor()
# cursor.execute("SELECT * FROM messages")
# rows = cursor.fetchall()
# for row in rows:
#     print(row)


emojis = ["🌺","🌸","👩🏼‍❤️‍💋‍👩🏽","👩🏼","💋","👳‍♂️","🏖","🖍"]
print(emojis[0])

# test = [8, "hi", False]
# a = "|".join(map(str, test)).encode("utf-8")
# print(a)
# print(type(a))
# b = a.decode("utf-8").split("|")
# print(b)

a = {"status_code": [200], "data": [8,[(1,"amy","hannah","hi hannah",12002,False),(2, "jane","hannah","hi :)",12040,True)]]}
# def encode_query(query_lst):
#     flattened_lst = [item for message in query_lst for item in message]
#     content_bytes = "|".join(map(str, flattened_lst)).encode('utf-8')

#     return content_bytes

# encoded_a = encode_query(a[1:][0])

# new_a = a["status_code"] + [a["data"][0]] + [item for message in a["data"][1:][0] for item in message]
# print(new_a)

# encoded_a = "|".join(map(str, new_a)).encode('utf-8')

# print(encoded_a)

# LEN_MSG = 6

# decoded_a = encoded_a.decode("utf-8").split("|")

# print(decoded_a)
# status_code = decoded_a.pop(0)
# count = decoded_a.pop(0)

# messages = [tuple(decoded_a[i:i+LEN_MSG]) for i in range(0, len(decoded_a), LEN_MSG)]

# print(messages)

# NOTE: doesn't work bc all messages come out as strings: [('1','amy',...)]

def encode_result(result):
    encoded = b''
    for r in result:
        t = type(r).__name__
        # get the type code
        type_code = TypeCode[t]
        method = TypeCode2[type_code]
        # encode
        if method == ">s":
            encoded_arg = bytes(r, "utf-8")
        else:
            encoded_arg = struct.pack(method,r)
        # pack
        encoded += struct.pack("B", type_code) + struct.pack(">I", len(encoded_arg)) + encoded_arg
    return encoded

flattened_lst = a["status_code"] + [a["data"][0]] + [item for message in a["data"][1:][0] for item in message]
print(flattened_lst)

encoded_a = encode_result(flattened_lst)
print(encoded_a)

def decode_result(result):
    decoded = []
    while result:
        type_code = struct.unpack("B", result[:1])[0]
        # print(type_code)
        method = TypeCode2[type_code]
        result = result[1:]
        length = struct.unpack(">I", result[:4])[0]
        # print(length)
        result = result[4:]
        if method == ">s":
            thing = result[:length].decode("utf-8")
            result = result[length:]
        else:
            thing = struct.unpack(method, result[:length])[0]
            result = result[length:]
        # print(thing)
        decoded += [thing]
    return decoded
#         type_code = struct.unpack("B", result[:1])[0]
#         print(result[:1], "T", type_code)
#         method = TypeCode2[type_code]
#         result = result[1:]
#         if method == ">s":
#             length = result.index(b"\x00")
#             decoded.append(result[:length].decode("utf-8"))
#             result = result[length+1:]
#         else:
#             decoded.append(struct.unpack(method, result[:struct.calcsize(method)])[0])
#             result = result[struct.calcsize(method):]

decoded_a = decode_result(encoded_a)
print(decoded_a)