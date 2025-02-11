from enum import Enum

class ResponseCode(Enum):
    SUCCESS = 200
    ACCOUNT_EXISTS = 4001
    INVALID_CREDENTIALS = 4002
    ACCOUNT_NOT_FOUND = 4041
    MESSAGE_SEND_FAILURE = 5001
    DATABASE_ERROR = 5000

RESPONSE_MESSAGES = {
    ResponseCode.SUCCESS: "Operation successful",
    ResponseCode.ACCOUNT_EXISTS: "Account already exists",
    ResponseCode.INVALID_CREDENTIALS: "Invalid credentials",
    ResponseCode.ACCOUNT_NOT_FOUND: "Account does not exist",
    ResponseCode.MESSAGE_SEND_FAILURE: "Failed to send message",
    ResponseCode.DATABASE_ERROR: "Database error",
}

class Schema(Enum):
    ACCOUNTS = 3,
    CLIENT_MSG = 5, # id auto-generated
    SERVER_MSG = 6, # tuple(id, sender_username, receiver_username, msg_content, timestamp, delivered/undelivered bool)


class OpCode(Enum):
    ACCOUNT_EXISTS = 0
    CREATE_ACCOUNT = 1
    LOGIN_ACCOUNT = 2
    LIST_ACCOUNTS = 3
    DELETE_ACCOUNT = 4
    HOMEPAGE = 5
    READ_MSG_UNDELIVERED = 6
    READ_MSG_DELIVERED = 7
    DELETE_MSG = 8
    SEND_MSG = 9
    RECEIVE_MSG = 10
    LOGOUT_ACCOUNT = 11

OPCODE_MESSAGES = {
}

OPCODE_INPUTS = {
    OpCode.ACCOUNT_EXISTS: 1,
    OpCode.CREATE_ACCOUNT: 2,
    OpCode.LOGIN_ACCOUNT: 2,
    OpCode.LIST_ACCOUNTS: 0,
    OpCode.DELETE_ACCOUNT: 2,
    OpCode.HOMEPAGE: 1,
    OpCode.READ_MSG_UNDELIVERED: 2,
    OpCode.READ_MSG_DELIVERED: 2,
    OpCode.DELETE_MSG: -1,
    OpCode.SEND_MSG: 1,
    OpCode.RECEIVE_MSG: 1,
    OpCode.LOGOUT_ACCOUNT: 1,
}

OPCODE_OUTPUTS = {
    OpCode.ACCOUNT_EXISTS: [],
    OpCode.CREATE_ACCOUNT: ["username", "password"],
    OpCode.LOGIN_ACCOUNT: ["username", "password"],
    OpCode.LIST_ACCOUNTS: [],
    OpCode.DELETE_ACCOUNT: ["username", "password"],
    OpCode.HOMEPAGE: ["username"],
    OpCode.READ_MSG_UNDELIVERED: ["username","num_msgs"],
    OpCode.READ_MSG_DELIVERED: ["username","num_msgs"],
    OpCode.DELETE_MSG: ["message_ids"],
    OpCode.SEND_MSG: ["message"],
    OpCode.RECEIVE_MSG: ["message"],
    OpCode.LOGOUT_ACCOUNT: ["username"],
}