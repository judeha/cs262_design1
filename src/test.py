import struct

test = 0

packed = struct.pack(">H", test)
print(packed)

        # if len(self._recv_buffer) >= hdrlen:
        #     self._header_len = struct.unpack(
        #         ">H", self._recv_buffer[:hdrlen]
        #     )[0]
        #     self._recv_buffer = self._recv_buffer[hdrlen:]