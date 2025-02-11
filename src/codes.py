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

class OpCode(Enum):
    CHECK_USERNAME = 0
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

OPCODE_MESSAGES = {
}

OPCODE_INPUTS = {
    OpCode.CHECK_USERNAME: ["username"],
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
}

OPCODE_OUTPUTS = {
    OpCode.CHECK_USERNAME: [],
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
}