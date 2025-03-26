from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class EndingRequest(_message.Message):
    __slots__ = ("username",)
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    username: str
    def __init__(self, username: _Optional[str] = ...) -> None: ...

class EndingResponse(_message.Message):
    __slots__ = ("status_code",)
    STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
    status_code: int
    def __init__(self, status_code: _Optional[int] = ...) -> None: ...

class AccountExistsRequest(_message.Message):
    __slots__ = ("username",)
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    username: str
    def __init__(self, username: _Optional[str] = ...) -> None: ...

class AccountExistsResponse(_message.Message):
    __slots__ = ("status_code", "exists")
    STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
    EXISTS_FIELD_NUMBER: _ClassVar[int]
    status_code: int
    exists: bool
    def __init__(self, status_code: _Optional[int] = ..., exists: bool = ...) -> None: ...

class CreateAccountRequest(_message.Message):
    __slots__ = ("username", "password", "bio")
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    PASSWORD_FIELD_NUMBER: _ClassVar[int]
    BIO_FIELD_NUMBER: _ClassVar[int]
    username: str
    password: str
    bio: str
    def __init__(self, username: _Optional[str] = ..., password: _Optional[str] = ..., bio: _Optional[str] = ...) -> None: ...

class CreateAccountResponse(_message.Message):
    __slots__ = ("status_code",)
    STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
    status_code: int
    def __init__(self, status_code: _Optional[int] = ...) -> None: ...

class LoginAccountRequest(_message.Message):
    __slots__ = ("username", "password")
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    PASSWORD_FIELD_NUMBER: _ClassVar[int]
    username: str
    password: str
    def __init__(self, username: _Optional[str] = ..., password: _Optional[str] = ...) -> None: ...

class LoginAccountResponse(_message.Message):
    __slots__ = ("status_code", "count", "msg_lst")
    STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    MSG_LST_FIELD_NUMBER: _ClassVar[int]
    status_code: int
    count: int
    msg_lst: _containers.RepeatedCompositeFieldContainer[Message]
    def __init__(self, status_code: _Optional[int] = ..., count: _Optional[int] = ..., msg_lst: _Optional[_Iterable[_Union[Message, _Mapping]]] = ...) -> None: ...

class ListAccountRequest(_message.Message):
    __slots__ = ("pattern",)
    PATTERN_FIELD_NUMBER: _ClassVar[int]
    pattern: str
    def __init__(self, pattern: _Optional[str] = ...) -> None: ...

class ListAccountResponse(_message.Message):
    __slots__ = ("status_code", "acct_lst")
    STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
    ACCT_LST_FIELD_NUMBER: _ClassVar[int]
    status_code: int
    acct_lst: _containers.RepeatedCompositeFieldContainer[Account]
    def __init__(self, status_code: _Optional[int] = ..., acct_lst: _Optional[_Iterable[_Union[Account, _Mapping]]] = ...) -> None: ...

class DeleteAccountRequest(_message.Message):
    __slots__ = ("username", "password")
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    PASSWORD_FIELD_NUMBER: _ClassVar[int]
    username: str
    password: str
    def __init__(self, username: _Optional[str] = ..., password: _Optional[str] = ...) -> None: ...

class DeleteAccountResponse(_message.Message):
    __slots__ = ("status_code",)
    STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
    status_code: int
    def __init__(self, status_code: _Optional[int] = ...) -> None: ...

class FetchHomepageRequest(_message.Message):
    __slots__ = ("username",)
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    username: str
    def __init__(self, username: _Optional[str] = ...) -> None: ...

class FetchHomepageResponse(_message.Message):
    __slots__ = ("status_code", "count", "msg_lst")
    STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    MSG_LST_FIELD_NUMBER: _ClassVar[int]
    status_code: int
    count: int
    msg_lst: _containers.RepeatedCompositeFieldContainer[Message]
    def __init__(self, status_code: _Optional[int] = ..., count: _Optional[int] = ..., msg_lst: _Optional[_Iterable[_Union[Message, _Mapping]]] = ...) -> None: ...

class FetchMessagesReadRequest(_message.Message):
    __slots__ = ("username", "num")
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    NUM_FIELD_NUMBER: _ClassVar[int]
    username: str
    num: int
    def __init__(self, username: _Optional[str] = ..., num: _Optional[int] = ...) -> None: ...

class FetchMessagesReadResponse(_message.Message):
    __slots__ = ("status_code", "msg_lst")
    STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
    MSG_LST_FIELD_NUMBER: _ClassVar[int]
    status_code: int
    msg_lst: _containers.RepeatedCompositeFieldContainer[Message]
    def __init__(self, status_code: _Optional[int] = ..., msg_lst: _Optional[_Iterable[_Union[Message, _Mapping]]] = ...) -> None: ...

class FetchMessagesUnreadRequest(_message.Message):
    __slots__ = ("username", "num")
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    NUM_FIELD_NUMBER: _ClassVar[int]
    username: str
    num: int
    def __init__(self, username: _Optional[str] = ..., num: _Optional[int] = ...) -> None: ...

class FetchMessagesUnreadResponse(_message.Message):
    __slots__ = ("status_code", "count", "msg_lst")
    STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    MSG_LST_FIELD_NUMBER: _ClassVar[int]
    status_code: int
    count: int
    msg_lst: _containers.RepeatedCompositeFieldContainer[Message]
    def __init__(self, status_code: _Optional[int] = ..., count: _Optional[int] = ..., msg_lst: _Optional[_Iterable[_Union[Message, _Mapping]]] = ...) -> None: ...

class DeleteMessageRequest(_message.Message):
    __slots__ = ("username", "message_id_lst")
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_ID_LST_FIELD_NUMBER: _ClassVar[int]
    username: str
    message_id_lst: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, username: _Optional[str] = ..., message_id_lst: _Optional[_Iterable[int]] = ...) -> None: ...

class DeleteMessageResponse(_message.Message):
    __slots__ = ("status_code", "count", "msg_lst")
    STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    MSG_LST_FIELD_NUMBER: _ClassVar[int]
    status_code: int
    count: int
    msg_lst: _containers.RepeatedCompositeFieldContainer[Message]
    def __init__(self, status_code: _Optional[int] = ..., count: _Optional[int] = ..., msg_lst: _Optional[_Iterable[_Union[Message, _Mapping]]] = ...) -> None: ...

class SendMessageRequest(_message.Message):
    __slots__ = ("sender", "receiver", "content", "timestamp")
    SENDER_FIELD_NUMBER: _ClassVar[int]
    RECEIVER_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    sender: str
    receiver: str
    content: str
    timestamp: int
    def __init__(self, sender: _Optional[str] = ..., receiver: _Optional[str] = ..., content: _Optional[str] = ..., timestamp: _Optional[int] = ...) -> None: ...

class SendMessageResponse(_message.Message):
    __slots__ = ("status_code",)
    STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
    status_code: int
    def __init__(self, status_code: _Optional[int] = ...) -> None: ...

class ReceiveMessageRequest(_message.Message):
    __slots__ = ("username",)
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    username: str
    def __init__(self, username: _Optional[str] = ...) -> None: ...

class ReceiveMessageResponse(_message.Message):
    __slots__ = ("msg_lst",)
    MSG_LST_FIELD_NUMBER: _ClassVar[int]
    msg_lst: _containers.RepeatedCompositeFieldContainer[Message]
    def __init__(self, msg_lst: _Optional[_Iterable[_Union[Message, _Mapping]]] = ...) -> None: ...

class Message(_message.Message):
    __slots__ = ("id", "sender", "receiver", "content", "timestamp", "delivered")
    ID_FIELD_NUMBER: _ClassVar[int]
    SENDER_FIELD_NUMBER: _ClassVar[int]
    RECEIVER_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    DELIVERED_FIELD_NUMBER: _ClassVar[int]
    id: int
    sender: str
    receiver: str
    content: str
    timestamp: int
    delivered: bool
    def __init__(self, id: _Optional[int] = ..., sender: _Optional[str] = ..., receiver: _Optional[str] = ..., content: _Optional[str] = ..., timestamp: _Optional[int] = ..., delivered: bool = ...) -> None: ...

class Account(_message.Message):
    __slots__ = ("id", "username", "bio")
    ID_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    BIO_FIELD_NUMBER: _ClassVar[int]
    id: int
    username: str
    bio: str
    def __init__(self, id: _Optional[int] = ..., username: _Optional[str] = ..., bio: _Optional[str] = ...) -> None: ...

class Entry(_message.Message):
    __slots__ = ("action", "username", "password", "bio", "sender", "receiver", "content", "num", "message_id_lst", "timestamp", "pattern")
    ACTION_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    PASSWORD_FIELD_NUMBER: _ClassVar[int]
    BIO_FIELD_NUMBER: _ClassVar[int]
    SENDER_FIELD_NUMBER: _ClassVar[int]
    RECEIVER_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    NUM_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_ID_LST_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    PATTERN_FIELD_NUMBER: _ClassVar[int]
    action: str
    username: str
    password: str
    bio: str
    sender: str
    receiver: str
    content: str
    num: int
    message_id_lst: _containers.RepeatedScalarFieldContainer[int]
    timestamp: int
    pattern: str
    def __init__(self, action: _Optional[str] = ..., username: _Optional[str] = ..., password: _Optional[str] = ..., bio: _Optional[str] = ..., sender: _Optional[str] = ..., receiver: _Optional[str] = ..., content: _Optional[str] = ..., num: _Optional[int] = ..., message_id_lst: _Optional[_Iterable[int]] = ..., timestamp: _Optional[int] = ..., pattern: _Optional[str] = ...) -> None: ...

class VoteRequest(_message.Message):
    __slots__ = ("cand_id", "cand_term", "prev_log_idx", "prev_log_term")
    CAND_ID_FIELD_NUMBER: _ClassVar[int]
    CAND_TERM_FIELD_NUMBER: _ClassVar[int]
    PREV_LOG_IDX_FIELD_NUMBER: _ClassVar[int]
    PREV_LOG_TERM_FIELD_NUMBER: _ClassVar[int]
    cand_id: int
    cand_term: int
    prev_log_idx: int
    prev_log_term: int
    def __init__(self, cand_id: _Optional[int] = ..., cand_term: _Optional[int] = ..., prev_log_idx: _Optional[int] = ..., prev_log_term: _Optional[int] = ...) -> None: ...

class VoteResponse(_message.Message):
    __slots__ = ("term", "success")
    TERM_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    term: int
    success: bool
    def __init__(self, term: _Optional[int] = ..., success: bool = ...) -> None: ...

class AppendEntriesRequest(_message.Message):
    __slots__ = ("leader_addr", "term", "prev_log_term", "prev_log_idx", "entries", "commit")
    LEADER_ADDR_FIELD_NUMBER: _ClassVar[int]
    TERM_FIELD_NUMBER: _ClassVar[int]
    PREV_LOG_TERM_FIELD_NUMBER: _ClassVar[int]
    PREV_LOG_IDX_FIELD_NUMBER: _ClassVar[int]
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    COMMIT_FIELD_NUMBER: _ClassVar[int]
    leader_addr: str
    term: int
    prev_log_term: int
    prev_log_idx: int
    entries: _containers.RepeatedCompositeFieldContainer[Entry]
    commit: int
    def __init__(self, leader_addr: _Optional[str] = ..., term: _Optional[int] = ..., prev_log_term: _Optional[int] = ..., prev_log_idx: _Optional[int] = ..., entries: _Optional[_Iterable[_Union[Entry, _Mapping]]] = ..., commit: _Optional[int] = ...) -> None: ...

class AppendEntriesResponse(_message.Message):
    __slots__ = ("term", "success")
    TERM_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    term: int
    success: bool
    def __init__(self, term: _Optional[int] = ..., success: bool = ...) -> None: ...

class GetLeaderResponse(_message.Message):
    __slots__ = ("leader_addr",)
    LEADER_ADDR_FIELD_NUMBER: _ClassVar[int]
    leader_addr: str
    def __init__(self, leader_addr: _Optional[str] = ...) -> None: ...
