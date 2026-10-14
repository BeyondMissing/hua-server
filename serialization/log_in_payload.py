import struct

from entity.account import Account
from stream import _u32, fixed_utf8
from utils import _profile_value


def log_in_payload(account: Account) -> bytes:
    """
    Encode Res_LOGIN_IN (1000):
    17 ints meta + 16B nickname + 9 ints appearance + 15 ints cloth + pet info
    """

    vals = [
        account.user_id,
        _profile_value(account, "map_id"),
        _profile_value(account, "map_x"),
        _profile_value(account, "map_y"),
        _profile_value(account, 'new_user_job'),
        _profile_value(account, 'login_time'),
        _profile_value(account, 'birthday'),
        _profile_value(account, 'nationality'),
        _profile_value(account, 'love'),
        _profile_value(account, 'beautiful'),
        _profile_value(account, 'wisdom'),
        _profile_value(account, 'plant_grade'),
        _profile_value(account, 'faerie_grade'),
        _profile_value(account, 'login_count'),
        _profile_value(account, 'online_time_all'),
        _profile_value(account, 'login_last'),
        _profile_value(account, 'online_time_today')
    ]
    nickname = str(_profile_value(account, 'nickname', account.login_name))
    appearance = ['face_color', 'face', 'eye', 'eyebrow', 'lip', 'title_id', 'vip_level', 'vip_end_time']
    clothing = ['tool', 'headdress', 'mask', 'hair', 'earring', 'necklace', 'belt', 'cloth', 'bangle', 'shoes',
                'anklet', 'skirt', 'wing', 'dust', 'faerie_follow_id']

    pet = (account.profile or {}).get('pet') or {}
    pet_vip = pet.get('is_vip', 0)
    pet_id = pet.get('pet_id', 0)
    pet_nickname = pet.get('nickname', '')
    pet_value = (pet.get('wonderful_value', 0)
                 if int(pet_vip or 0) == 1 else pet.get('love_energy', 0))

    out =  bytearray(struct.pack('>17I', *[_u32(v) for v in vals]))
    out += fixed_utf8(nickname, 16)
    out += struct.pack('>8I',  *[_u32(_profile_value(account, k)) for k in appearance])
    if 'enable_friends_application' in (account.profile or {}):
        # The database column is a semantic boolean; the legacy wire flag is
        # inverted (AS3 treats zero as "allow").
        enabled = _profile_value(account, 'enable_friends_application', 1)
        friend_flag = 0 if (enabled is None or bool(enabled)) else 1
    else:
        friend_flag = _profile_value(account, 'friend_flag', 0)
    out += struct.pack('>I', _u32(friend_flag))
    out += struct.pack('>15I', *[_u32(_profile_value(account, k)) for k in clothing])
    out += struct.pack('>2I',  _u32(pet_vip), _u32(pet_id))

    if pet_id:
        out += fixed_utf8(str(pet_nickname), 16)
        out += struct.pack('>I', _u32(pet_value))

    out += struct.pack('>I', 0)
    return out
