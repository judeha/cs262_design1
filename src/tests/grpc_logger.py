


logging.basicConfig(
    filename="grpc_message_sizes.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)

def log_message_size(func_name, direction, message):
    """Logs the size of a gRPC message."""
    size = sys.getsizeof(message)
    logging.info(f"{func_name} - {direction}: {size} bytes")