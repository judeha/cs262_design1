# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc
import warnings

from google.protobuf import empty_pb2 as google_dot_protobuf_dot_empty__pb2
import handler_pb2 as handler__pb2

GRPC_GENERATED_VERSION = '1.70.0'
GRPC_VERSION = grpc.__version__
_version_not_supported = False

try:
    from grpc._utilities import first_version_is_lower
    _version_not_supported = first_version_is_lower(GRPC_VERSION, GRPC_GENERATED_VERSION)
except ImportError:
    _version_not_supported = True

if _version_not_supported:
    raise RuntimeError(
        f'The grpc package installed is at version {GRPC_VERSION},'
        + f' but the generated code in handler_pb2_grpc.py depends on'
        + f' grpcio>={GRPC_GENERATED_VERSION}.'
        + f' Please upgrade your grpc module to grpcio>={GRPC_GENERATED_VERSION}'
        + f' or downgrade your generated code using grpcio-tools<={GRPC_VERSION}.'
    )


class HandlerStub(object):
    """gRPC service definition
    """

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Starting = channel.unary_unary(
                '/Handler/Starting',
                request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
                response_deserializer=handler__pb2.StartingResponse.FromString,
                _registered_method=True)
        self.CheckAccountExists = channel.unary_unary(
                '/Handler/CheckAccountExists',
                request_serializer=handler__pb2.AccountExistsRequest.SerializeToString,
                response_deserializer=handler__pb2.AccountExistsResponse.FromString,
                _registered_method=True)
        self.CreateAccount = channel.unary_unary(
                '/Handler/CreateAccount',
                request_serializer=handler__pb2.CreateAccountRequest.SerializeToString,
                response_deserializer=handler__pb2.CreateAccountResponse.FromString,
                _registered_method=True)
        self.LoginAccount = channel.unary_unary(
                '/Handler/LoginAccount',
                request_serializer=handler__pb2.LoginAccountRequest.SerializeToString,
                response_deserializer=handler__pb2.LoginAccountResponse.FromString,
                _registered_method=True)
        self.ListAccount = channel.unary_unary(
                '/Handler/ListAccount',
                request_serializer=handler__pb2.ListAccountRequest.SerializeToString,
                response_deserializer=handler__pb2.ListAccountResponse.FromString,
                _registered_method=True)
        self.DeleteAccount = channel.unary_unary(
                '/Handler/DeleteAccount',
                request_serializer=handler__pb2.DeleteAccountRequest.SerializeToString,
                response_deserializer=handler__pb2.DeleteAccountResponse.FromString,
                _registered_method=True)
        self.FetchHomepage = channel.unary_unary(
                '/Handler/FetchHomepage',
                request_serializer=handler__pb2.FetchHomepageRequest.SerializeToString,
                response_deserializer=handler__pb2.FetchHomepageResponse.FromString,
                _registered_method=True)
        self.FetchMessageUnread = channel.unary_unary(
                '/Handler/FetchMessageUnread',
                request_serializer=handler__pb2.FetchMessagesUnreadRequest.SerializeToString,
                response_deserializer=handler__pb2.FetchMessagesUnreadResponse.FromString,
                _registered_method=True)
        self.FetchMessageRead = channel.unary_unary(
                '/Handler/FetchMessageRead',
                request_serializer=handler__pb2.FetchMessagesReadRequest.SerializeToString,
                response_deserializer=handler__pb2.FetchMessagesReadResponse.FromString,
                _registered_method=True)
        self.DeleteMessage = channel.unary_unary(
                '/Handler/DeleteMessage',
                request_serializer=handler__pb2.DeleteMessageRequest.SerializeToString,
                response_deserializer=handler__pb2.DeleteMessageResponse.FromString,
                _registered_method=True)
        self.SendMessage = channel.unary_unary(
                '/Handler/SendMessage',
                request_serializer=handler__pb2.SendMessageRequest.SerializeToString,
                response_deserializer=handler__pb2.SendMessageResponse.FromString,
                _registered_method=True)
        self.ReceiveMessage = channel.unary_unary(
                '/Handler/ReceiveMessage',
                request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
                response_deserializer=handler__pb2.ReceiveMessageResponse.FromString,
                _registered_method=True)


class HandlerServicer(object):
    """gRPC service definition
    """

    def Starting(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def CheckAccountExists(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def CreateAccount(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def LoginAccount(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def ListAccount(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def DeleteAccount(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def FetchHomepage(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def FetchMessageUnread(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def FetchMessageRead(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def DeleteMessage(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def SendMessage(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def ReceiveMessage(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_HandlerServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'Starting': grpc.unary_unary_rpc_method_handler(
                    servicer.Starting,
                    request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
                    response_serializer=handler__pb2.StartingResponse.SerializeToString,
            ),
            'CheckAccountExists': grpc.unary_unary_rpc_method_handler(
                    servicer.CheckAccountExists,
                    request_deserializer=handler__pb2.AccountExistsRequest.FromString,
                    response_serializer=handler__pb2.AccountExistsResponse.SerializeToString,
            ),
            'CreateAccount': grpc.unary_unary_rpc_method_handler(
                    servicer.CreateAccount,
                    request_deserializer=handler__pb2.CreateAccountRequest.FromString,
                    response_serializer=handler__pb2.CreateAccountResponse.SerializeToString,
            ),
            'LoginAccount': grpc.unary_unary_rpc_method_handler(
                    servicer.LoginAccount,
                    request_deserializer=handler__pb2.LoginAccountRequest.FromString,
                    response_serializer=handler__pb2.LoginAccountResponse.SerializeToString,
            ),
            'ListAccount': grpc.unary_unary_rpc_method_handler(
                    servicer.ListAccount,
                    request_deserializer=handler__pb2.ListAccountRequest.FromString,
                    response_serializer=handler__pb2.ListAccountResponse.SerializeToString,
            ),
            'DeleteAccount': grpc.unary_unary_rpc_method_handler(
                    servicer.DeleteAccount,
                    request_deserializer=handler__pb2.DeleteAccountRequest.FromString,
                    response_serializer=handler__pb2.DeleteAccountResponse.SerializeToString,
            ),
            'FetchHomepage': grpc.unary_unary_rpc_method_handler(
                    servicer.FetchHomepage,
                    request_deserializer=handler__pb2.FetchHomepageRequest.FromString,
                    response_serializer=handler__pb2.FetchHomepageResponse.SerializeToString,
            ),
            'FetchMessageUnread': grpc.unary_unary_rpc_method_handler(
                    servicer.FetchMessageUnread,
                    request_deserializer=handler__pb2.FetchMessagesUnreadRequest.FromString,
                    response_serializer=handler__pb2.FetchMessagesUnreadResponse.SerializeToString,
            ),
            'FetchMessageRead': grpc.unary_unary_rpc_method_handler(
                    servicer.FetchMessageRead,
                    request_deserializer=handler__pb2.FetchMessagesReadRequest.FromString,
                    response_serializer=handler__pb2.FetchMessagesReadResponse.SerializeToString,
            ),
            'DeleteMessage': grpc.unary_unary_rpc_method_handler(
                    servicer.DeleteMessage,
                    request_deserializer=handler__pb2.DeleteMessageRequest.FromString,
                    response_serializer=handler__pb2.DeleteMessageResponse.SerializeToString,
            ),
            'SendMessage': grpc.unary_unary_rpc_method_handler(
                    servicer.SendMessage,
                    request_deserializer=handler__pb2.SendMessageRequest.FromString,
                    response_serializer=handler__pb2.SendMessageResponse.SerializeToString,
            ),
            'ReceiveMessage': grpc.unary_unary_rpc_method_handler(
                    servicer.ReceiveMessage,
                    request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
                    response_serializer=handler__pb2.ReceiveMessageResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'Handler', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers('Handler', rpc_method_handlers)


 # This class is part of an EXPERIMENTAL API.
class Handler(object):
    """gRPC service definition
    """

    @staticmethod
    def Starting(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/Handler/Starting',
            google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
            handler__pb2.StartingResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def CheckAccountExists(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/Handler/CheckAccountExists',
            handler__pb2.AccountExistsRequest.SerializeToString,
            handler__pb2.AccountExistsResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def CreateAccount(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/Handler/CreateAccount',
            handler__pb2.CreateAccountRequest.SerializeToString,
            handler__pb2.CreateAccountResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def LoginAccount(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/Handler/LoginAccount',
            handler__pb2.LoginAccountRequest.SerializeToString,
            handler__pb2.LoginAccountResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def ListAccount(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/Handler/ListAccount',
            handler__pb2.ListAccountRequest.SerializeToString,
            handler__pb2.ListAccountResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def DeleteAccount(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/Handler/DeleteAccount',
            handler__pb2.DeleteAccountRequest.SerializeToString,
            handler__pb2.DeleteAccountResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def FetchHomepage(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/Handler/FetchHomepage',
            handler__pb2.FetchHomepageRequest.SerializeToString,
            handler__pb2.FetchHomepageResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def FetchMessageUnread(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/Handler/FetchMessageUnread',
            handler__pb2.FetchMessagesUnreadRequest.SerializeToString,
            handler__pb2.FetchMessagesUnreadResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def FetchMessageRead(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/Handler/FetchMessageRead',
            handler__pb2.FetchMessagesReadRequest.SerializeToString,
            handler__pb2.FetchMessagesReadResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def DeleteMessage(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/Handler/DeleteMessage',
            handler__pb2.DeleteMessageRequest.SerializeToString,
            handler__pb2.DeleteMessageResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def SendMessage(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/Handler/SendMessage',
            handler__pb2.SendMessageRequest.SerializeToString,
            handler__pb2.SendMessageResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def ReceiveMessage(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/Handler/ReceiveMessage',
            google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
            handler__pb2.ReceiveMessageResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)
