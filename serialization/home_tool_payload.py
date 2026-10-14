import struct
from typing import Dict

from stream import _u32, _u8


def home_tool_payload(tools: list[Dict[str, object]]) -> bytes:
    """
    Encode the observed HOME_TOOL_INFO (10025) 25-byte wire record.

    The decompiled Res_HOME_TOOL_INFO consumes only the first 17 bytes, while
    the captured production response contains two additional uint32 values in
    every record.  They are retained as reserved fields so the response can
    reproduce the actual server wire format without discarding data.
    """

    out = bytearray(struct.pack('>I', len(tools)))

    for tool in tools:

        t = lambda key, default=0: (
            tool.get(key, default)
        )
        out += struct.pack('>6I',
            _u32(t('item_id')),
            _u32(t('x')),
            _u32(t('y')),
            _u32(t('state')),
            _u32(t('reserved_1')),
            _u32(t('reserved_2'))
        )

    return bytes(out)


def home_depot_payload(items: list[Dict[str, object]]) -> bytes:
    """Encode HOME_DEPOT (10003): count followed by ID/quantity pairs."""
    out = bytearray(struct.pack('>I', len(items)))
    for item in items:
        out += struct.pack('>2I', _u32(item.get('item_id')), _u32(item.get('amount')))
    return bytes(out)
