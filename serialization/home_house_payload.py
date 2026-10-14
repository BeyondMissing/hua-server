import struct
from typing import Dict

from stream import _u32


def home_house_payload(houses: list[Dict[str, object]]) -> bytes:
    """
    Encode Res_HOME_HOUSE (10001): count plus 21 bytes per house.
    """

    out = bytearray(struct.pack('>I', len(houses)))

    for house in houses:

        h = lambda key, default=0: house.get(key, default)
        out += struct.pack('>5I',
            _u32(h('item_id')),
            _u32(h('x')),
            _u32(h('y')),
            _u32(h('open_flag')),
            _u32(h('reserved')),
        )

    return bytes(out)
