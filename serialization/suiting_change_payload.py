import struct


SUITING_PART_COUNT = 13
SUITING_ADD_PAYLOAD_SIZE = SUITING_PART_COUNT * 4
SUITING_PART_COLUMNS = (
    "tool_id", "headdress_id", "mask_id", "hair_id", "earring_id",
    "necklace_id", "belt_id", "cloth_id", "bangle_id", "shoes_id",
    "anklet_id", "skirt_id", "wing_id",
)


class SuitingProtocolError(ValueError):
    pass


def parse_suiting_add_request(payload: bytes):
    if len(payload) != SUITING_ADD_PAYLOAD_SIZE:
        raise SuitingProtocolError(
            f"SUITING_ADD payload must be {SUITING_ADD_PAYLOAD_SIZE} bytes"
        )
    return struct.unpack(">13I", payload)


def parse_suiting_delete_request(payload: bytes) -> int:
    if len(payload) != 4:
        raise SuitingProtocolError("SUITING_DELETE payload must be 4 bytes")
    return struct.unpack(">I", payload)[0]


def suiting_add_response(slot_index: int) -> bytes:
    return struct.pack(">I", int(slot_index) & 0xFFFFFFFF)
