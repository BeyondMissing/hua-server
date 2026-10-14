import json
import struct

from stream import _u32, fixed_utf8


def pet_base_info_payload(pet: dict) -> bytes:
    """Encode PET_BASE_INFO (1044) for ``HuabaoData.readHuaData``.

    Index values are stored in the database as their wire values, where
    100000 represents 1.0 in the AS3 client.
    """
    skills = pet.get("skills_json", pet.get("skills", []))
    if isinstance(skills, str):
        try:
            skills = json.loads(skills)
        except (TypeError, ValueError):
            skills = []
    if not isinstance(skills, (list, tuple)):
        skills = []
    skills = [_u32(value) for value in skills]

    out = bytearray(struct.pack(
        ">4I",
        _u32(pet.get("user_id")),
        _u32(pet.get("pet_id")),
        _u32(pet.get("age")),
        _u32(pet.get("love_energy")),
    ))
    out += fixed_utf8(str(pet.get("nickname", "")), 16)
    out += struct.pack(
        ">5I",
        _u32(pet.get("hungry_index", 100000)),
        _u32(pet.get("clean_index", 100000)),
        _u32(pet.get("mood_index", 100000)),
        _u32(pet.get("health_state", 0)),
        _u32(pet.get("is_vip", 0)),
    )
    if _u32(pet.get("is_vip", 0)) != 0:
        out += struct.pack(">2I", _u32(pet.get("wonderful_value")), len(skills))
        out += struct.pack(">" + ("I" * len(skills)), *skills) if skills else b""
    return bytes(out)
