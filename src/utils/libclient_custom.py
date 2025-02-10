import struct

def _package_request(
    self, req):
    # Encode content
    encoding = req["content_encoding"]
    content_bytes = self._json_encode(req["content"], encoding)
    # Encode header
    jsonheader = {
        # "byteorder": sys.byteorder,
        # "content_type": req['content_type'],
        "content_encoding": encoding,
        "content_length": len(content_bytes),
        "opcode": req["opcode"]
    }
    jsonheader_bytes = self._json_encode(jsonheader, encoding)
    # Encode protoheader and package message
    message_hdr = struct.pack(">H", len(jsonheader_bytes))
    message = message_hdr + jsonheader_bytes + content_bytes
    return message

def _process_response_content(self):
    # Get opcode, status_code, and data from self._header and self.response
    opcode = self._header.get("opcode")
    status_code = self.response.pop()
    data = self.response
    pass

def process_header(self):
    hdrlen = self._header_len
    if len(self._recv_buffer) >= hdrlen:
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
    data = self._recv_buffer[:content_len]
    self._recv_buffer = self._recv_buffer[content_len:]

    # Decode response data
    req = data.split("|")
    self.response = {
        "opcode": req[0],
        "result": {"status_code": req[1]}
    }
    if len(req) > 2:
        self.response["data"] = req[2]

    print(f"Received response {self.response!r} from {self.addr}")

    # Process response content
    self._process_response_content()

    # Close when response has been processed
    self.close()

def _create_custom_message(self, req):
    # Encode content
    content = [req['content']['opcode']] + req['content']['args']
    content_str = str.join("|", content)
    content_bytes = bytes(content_str, req["content_encoding"])
    # Encode header
    jsonheader = [req['byteorder'],req['content_type'],req['content_encoding'],str(len(content_bytes))]
    jsonheader_str = str.join("|", jsonheader)
    jsonheader_bytes = bytes(jsonheader_str, req["content_encoding"])
    message_hdr = struct.pack(">H", self.is_custom) + struct.pack(">H", len(jsonheader_bytes))
    message = message_hdr + jsonheader_bytes + content_bytes
    return message