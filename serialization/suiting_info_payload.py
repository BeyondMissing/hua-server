import struct
from typing import List, Dict

from stream import _u32


def suiting_info_payload(suits: List[Dict[str, object]]) -> bytes:
    part_columns = (
        'tool_id', 'headdress_id', 'mask_id', 'hair_id', 'earring_id',
        'necklace_id', 'belt_id', 'cloth_id', 'bangle_id', 'shoes_id',
        'anklet_id', 'skirt_id', 'wing_id',
    )
    out = bytearray(struct.pack('>I', len(suits)))
    for s in suits:
        values = [_u32(s.get('slot_index', 0))]
        values.extend(_u32(s.get(column, 0)) for column in part_columns)
        out += struct.pack('>14I', *values)
    return bytes(out)
