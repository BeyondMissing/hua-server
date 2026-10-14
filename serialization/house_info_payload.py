import struct

from stream import _u32


def house_info_payload(owner_id: int, house_id: int, goods: list[dict]) -> bytes:
    """Encode HOUSE_INFO (10101): owner/house header plus six uint32 fields."""
    out = bytearray(struct.pack(">3I", _u32(owner_id), _u32(house_id), len(goods)))
    for good in goods:
        out += struct.pack(
            ">6I",
            _u32(good.get("no", 0)),
            _u32(good.get("item_id", 0)),
            _u32(good.get("x", 0)),
            _u32(good.get("y", 0)),
            _u32(good.get("m", 0)),
            _u32(good.get("z", 0)),
        )
    return bytes(out)


def pet_simple_info_payload(pets: list[dict]) -> bytes:
    """Encode the shared 10200/10208/10221 pet list format.

    Res_PetSimple_Info reads a count followed by pet id, VIP flag and value.
    """
    out = bytearray(struct.pack(">I", len(pets)))
    for pet in pets:
        value = (pet.get("wonderful_value")
                 if int(pet.get("is_vip", 0) or 0) == 1
                 else pet.get("love_energy"))
        out += struct.pack(
            ">3I",
            _u32(pet.get("pet_id")),
            _u32(pet.get("is_vip")),
            _u32(value),
        )
    return bytes(out)


def pet_inhouse_info_payload(pets: list[dict] | None = None) -> bytes:
    """Encode PET_INHOUSE_INFO (10208), using the shared pet-list format."""
    return pet_simple_info_payload(pets or [])


def house_add_goods_payload(item_id: int, no: int, x: int, y: int) -> bytes:
    """Encode HOUSE_ADD_GOODS (10102) response."""
    return struct.pack(">4I", _u32(item_id), _u32(no), _u32(x), _u32(y))


def house_del_goods_payload(no: int, item_id: int) -> bytes:
    """Encode HOUSE_DEL_GOODS (10103) response."""
    return struct.pack(">2I", _u32(no), _u32(item_id))
