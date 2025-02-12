from enum import Enum

class ResponseCode(Enum):
    SUCCESS = 200
    ACCOUNT_EXISTS = 4001
    INVALID_CREDENTIALS = 4002
    ACCOUNT_NOT_FOUND = 4041
    MESSAGE_SEND_FAILURE = 5001
    DATABASE_ERROR = 5000
    BAD_REQUEST = 4000
    STARTING = -1 # TODO: fragile

RESPONSE_MESSAGES = {
    ResponseCode.SUCCESS: "Operation successful",
    ResponseCode.ACCOUNT_EXISTS: "Account already exists",
    ResponseCode.INVALID_CREDENTIALS: "Invalid credentials",
    ResponseCode.BAD_REQUEST: "Bad request",
    ResponseCode.ACCOUNT_NOT_FOUND: "Account does not exist",
    ResponseCode.MESSAGE_SEND_FAILURE: "Failed to send message",
    ResponseCode.DATABASE_ERROR: "Database error",
}

class Schema(Enum):
    ACCOUNTS = 3,
    CLIENT_MSG = 5, # id auto-generated
    SERVER_MSG = 6, # tuple(id, sender_username, receiver_username, msg_content, timestamp, delivered/undelivered bool)


class OpCode(Enum):
    STARTING = -1
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