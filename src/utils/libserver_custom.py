import struct

version = 1


def _process_request(self):
    # Create response
    result = self._generate_response()

    # Encode response as json or custom
    status_code, data = result
    response = {"status_code": status_code, "data": data}
    message = self._package_response(response)
    # else:
    #     message = self._create_custom_message(response)
        
    # Load send buffer
    self.response_created = True
    self._send_buffer += message
            
def _package_response(self, response):
    # Encode content
    content = response["result"]["status_code"] + response["result"].get("data", [])
    content_str = str.join("|", content)
    content_bytes = bytes(content_str, self._header["content_encoding"])
    # Encode header
    jsonheader = self._header
    jsonheader["content_length"] = len(content_bytes)
    jsonheader_str = str.join("|", [jsonheader["byteorder"],
                                    jsonheader["content_type"],
                                    jsonheader["content_encoding"],
                                    str(jsonheader["content_length"])])
    jsonheader_bytes = bytes(jsonheader_str, self._header["content_encoding"])
    # Encode protoheader and package message
    message_hdr = struct.pack(">H", self.is_custom) + struct.pack(">H", len(jsonheader_bytes))
    message = message_hdr + jsonheader_bytes + content_bytes
    return message

def _generate_response(self):
    args = self.request.get("args")
    
    # response = result["status_code"], result.get("data", [])
    return 0

def process_header(self):
    hdrlen = self._header_len
    if len(self._recv_buffer) >= hdrlen and hdrlen!=0:
        # Read header data
        data = self._recv_buffer[:hdrlen]
        # Decode data
        hdr = data.decode("utf-8").split("|")
        self._header = {
            "byteorder": hdr[0],
            "content_type": hdr[1],
            "content_encoding": hdr[2],
            "content_length": int(hdr[3])
        }
        self._recv_buffer = self._recv_buffer[hdrlen:]
    # TODO: catch exception
    
def process_content(self):
    # Check if request is fully received
    content_len = self._header["content_length"]
    if not len(self._recv_buffer) >= content_len: # TODO: exception
        return
    
    # Save data from receive buffer
    encoding = self._header["content_encoding"]
    data = self._recv_buffer[:content_len].decode(encoding)
    self._recv_buffer = self._recv_buffer[content_len:]
    
    # Decode data as request
    req = data.split("|")
    self.request = {
        "opcode": req[0],
        "args": req[1:-1]
    }

    print(f"Received request {self.request!r} from {self.addr}")
    print(f"Request type: {type(self.request)}")
    
    # Set selector to listen for write events, we're done reading.
    self._set_selector_events_mask("w")

def create_response(self):
    # Create response
    result = self._create_response_content()

    # Encode response as json or custom
    status_code, data = result
    response = {"status_code": status_code, "data": data}
    message = self._stub_server_package(response)
    # else:
    #     message = self._create_custom_message(response)
        
    # Load send buffer
    self.response_created = True
    self._send_buffer += message