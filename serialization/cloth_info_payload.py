import struct

from stream import _u32


def cloth_info_payload(cloth_ids: list):
    values = [_u32(cloth_id) for cloth_id in cloth_ids]
    payload = struct.pack('>I', len(values))
    if values:
        payload += struct.pack('>' + ('I' * len(values)), *values)
    return payload