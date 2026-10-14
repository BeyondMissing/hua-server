import struct
from typing import Dict

from stream import _u32, fixed_utf8, _u8


def home_info_payload(home: Dict[str, object], plants: list[Dict[str, object]]) -> bytes:
    """
    Encode Res_HOME_INFO (10000): 77-byte header plus 75 bytes per plant.
    """

    h = lambda key, default=0: (
        home.get(key, default)
    )

    out = bytearray(struct.pack('>6I',
        _u32(h('user_id')),
        _u32(h('charm')),
        _u32(h('plant_exp')),
        _u32(h('background_id')),
        _u32(h('vip_level')),
        _u32(h('pet_level')),
    ))

    out += fixed_utf8(str(h('home_name', '')), 16)
    out += struct.pack('>B', _u8(h('weather')))
    out += fixed_utf8(str(h('temperature', '')), 32)
    out += struct.pack('>I', len(plants))

    for plant in plants:

        p = lambda key, default=0: (
            plant.get(key, default)
        )

        out += struct.pack('>3I',
            _u32(p('plot_no')),
            _u32(p('plant_id')),
            _u32(p('magic_id'))
        )

        out += struct.pack('>2BI4B',
            _u8(p('state')),
            _u8(p('level')),
            _u32(p('experience')),
            _u8(p('quality')),
            _u8(p('pollen_count')),
            _u8(p('flower_count')),
            _u8(p('seed_count'))
        )

        out += struct.pack('>8I',
            _u32(p('tool_state')),
            _u32(p('tool_time')),
            _u32(p('pot_id')),
            _u32(p('pollen_type')),
            _u32(p('nutrient')),
            _u32(p('moisture')),
            _u32(p('x')),
            _u32(p('y'))
        )

        out += struct.pack('>I2BI',
            _u32(p('owner_id')),
            _u8(p('next_state')),
            _u8(p('next_level')),
            _u32(p('next_time'))
        )

        out += struct.pack('>BIBI',
            _u8(p('dust_count')),
            _u32(p('grass')),
            _u8(p('item_use_flag')),
            _u32(p('add_flower_flag'))
        )

    return bytes(out)
