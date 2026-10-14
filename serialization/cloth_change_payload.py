import struct

from constant.consts import MAX_CLOTH_CHANGES
from exception.cloth_change_protocol_error import ClothChangeProtocolError


def parse_cloth_change_request(payload: bytes):
    """Decode count:uint32 followed by count * (cloth_id, action)."""
    if len(payload) < 4:
        raise ClothChangeProtocolError("missing clothes count")
    count = struct.unpack_from(">I", payload, 0)[0]
    if count == 0 or count > MAX_CLOTH_CHANGES:
        raise ClothChangeProtocolError("invalid clothes count")
    if len(payload) != 4 + count * 8:
        raise ClothChangeProtocolError("invalid clothes payload length")

    changes = []
    for offset in range(4, len(payload), 8):
        cloth_id, action = struct.unpack_from(">2I", payload, offset)
        if cloth_id == 0 or action not in (0, 1):
            raise ClothChangeProtocolError("invalid cloth change record")
        changes.append((cloth_id, action))
    return changes


def cloth_change_payload(user_id: int, records) -> bytes:
    """Encode UID, count, then (UpID, Type, DownID) response records."""
    out = bytearray(struct.pack(">2I", int(user_id) & 0xFFFFFFFF, len(records)))
    for cloth_id, action, down_id in records:
        out += struct.pack(">3I", cloth_id, action, down_id)
    return bytes(out)
