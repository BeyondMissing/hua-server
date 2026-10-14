import struct
from typing import Dict

from entity.account import Account
from stream import fixed_utf8, _u32


def _profile_value(account: Account, key: str, default=None):
    return (account.profile or {}).get(key, default)


def _uint_list(value) -> list[int]:
    if not isinstance(value, (list, tuple)):
        return []
    return [_u32(item) for item in value]


def _enter_map_eff_payload(row: Dict[str, object]) -> bytes:
    """Encode one AS3 ``Res_ENTER_MAP`` record with fixed-width fields.

    ``Res_ENTER_MAP`` reads every value after the 16-byte nickname as a
    big-endian ``uint32``.  Keeping the field groups explicit makes it harder
    to accidentally append a one-byte flag and shift the rest of the record.
    """
    value = lambda key, default=0: _u32(row.get(key, default))
    appearance = ('face_color', 'face', 'eye', 'eyebrow', 'lip', 'title_id')
    clothing = (
        'tool', 'headdress', 'mask', 'hair', 'earring', 'necklace', 'belt',
        'cloth', 'bangle', 'shoes', 'anklet', 'skirt', 'wing', 'dust',
        'faerie_follow_id',
    )

    out = bytearray(struct.pack(
        '>7I',
        value('user_id'), value('vip_level'), value('map_x', 480),
        value('map_y', 280), value('action'), value('action_other'),
        value('nationality', 1),
    ))
    out += fixed_utf8(str(row.get('nickname', row.get('user_id', ''))), 16)
    out += struct.pack('>6I', *(value(key) for key in appearance))
    out += struct.pack('>15I', *(value(key) for key in clothing))

    pet = row.get('pet') or {}
    pet_id = _u32(pet.get('pet_id'))
    out += struct.pack('>I', pet_id)
    if pet_id:
        # pet_vip, pet_value/pet_love_energy and pet_action are all uint32.
        out += struct.pack(
            '>3I', _u32(pet.get('is_vip')), _u32(
                pet.get('wonderful_value', 0) if int(pet.get('is_vip', 0) or 0) == 1
                else pet.get('love_energy', 0)
            ), value('pet_action')
        )
    out += struct.pack('>I', value('pet_adoption'))

    expected_length = 148 if pet_id else 136
    if len(out) != expected_length:
        raise AssertionError(
            f'ENTER_MAP record length {len(out)} != {expected_length}'
        )
    return bytes(out)


def byte_arr_to_hex(bs):
    s = ""
    for b in bs:
        n = hex(b)[2:].upper()
        if len(n) < 2:
            n = '0' + n
        s += n + ' '
    return s
