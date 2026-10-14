import struct

from stream import _u32


def home_add_house_payload(house_id: int, x: int, y: int, flag: int = 1) -> bytes:
    """Encode HOME_ADD_HOUSE (10011): flag byte followed by ID/X/Y."""
    return struct.pack(">B3I", int(flag) & 0xFF, _u32(house_id), _u32(x), _u32(y))


def home_tool_add_payload(item_id: int, x: int, y: int) -> bytes:
    """Encode HOME_TOOL_ADD (10023): item ID and placement coordinates."""
    return struct.pack(">3I", _u32(item_id), _u32(x), _u32(y))


def home_pot_add_payload(plot_no: int, x: int, y: int, pot_id: int) -> bytes:
    """Encode HOME_ADD_POT (10005): plot number, coordinates and pot ID."""
    return struct.pack(">4I", _u32(plot_no), _u32(x), _u32(y), _u32(pot_id))


def home_pot_back_payload(plot_no: int, pot_id: int) -> bytes:
    """Encode HOME_BACK_POT (10006): plot number and returned pot ID."""
    return struct.pack(">2I", _u32(plot_no), _u32(pot_id))


def home_add_plant_payload(plant: dict) -> bytes:
    """Encode HOME_ADD_PLANT (10007)'s complete 64-byte plant record."""
    p = lambda key, default=0: plant.get(key, default)
    out = bytearray(struct.pack(">3I", _u32(p("plot_no")), _u32(p("plant_id")), _u32(p("magic_id"))))
    out += struct.pack(">2BI4B", int(p("state")) & 0xFF, int(p("level")) & 0xFF,
                       _u32(p("experience")), int(p("quality")) & 0xFF,
                       int(p("pollen_count")) & 0xFF, int(p("flower_count")) & 0xFF,
                       int(p("seed_count")) & 0xFF)
    out += struct.pack(">8I", *[_u32(p(key)) for key in (
        "tool_state", "tool_time", "pot_id", "pollen_type", "nutrient", "moisture", "x", "y"
    )])
    out += struct.pack(">I2BI", _u32(p("owner_id")), int(p("next_state")) & 0xFF,
                       int(p("next_level")) & 0xFF, _u32(p("next_time")))
    return bytes(out)


def home_plant_tool_payload(tool_type: int, plot_no: int, tool_id: int, plant: dict | None = None) -> bytes:
    """Encode HOME_PLANT_TOOL (10022) response.

    Harvest responses have their own variable-length wire format.  In
    particular, the byte immediately after type 3 is PlantOrPet; it is not
    the plot number used by the other tool response types.
    """
    if int(tool_type) == 3:
        p = plant or {}
        if int(p.get("pet_id", 0) or 0):
            return struct.pack(">IBIB", 3, 2, _u32(p["pet_id"]), int(p.get("exp", 0)) & 0xFF)
        flowers = p.get("flowers") or []
        out = bytearray(struct.pack(">IB2IB", 3, 1, _u32(plot_no), _u32(p.get("seed_id", 0)), len(flowers) & 0xFF))
        for flower in flowers:
            out += struct.pack(">IB", _u32(flower.get("id", 0)), int(flower.get("amount", 0)) & 0xFF)
        out += struct.pack(">b", max(-128, min(127, int(p.get("exp", 0) or 0))))
        return bytes(out)
    if int(tool_type) == 2:
        return struct.pack(">2I", 2, _u32(plot_no))
    p = plant or {}
    return struct.pack(">3I4B3I", int(tool_type) & 0xFFFFFFFF, _u32(plot_no), _u32(tool_id),
                       int(p.get("state", 0)) & 0xFF, int(p.get("level", 0)) & 0xFF,
                       int(p.get("next_state", 0)) & 0xFF, int(p.get("next_level", 0)) & 0xFF,
                       _u32(p.get("next_time", 0)), 0, 0)


def home_house_position_payload(owner_id: int, house_id: int, x: int, y: int) -> bytes:
    """Encode HOME_UPDATE_HOUSE (10014): owner, house and position."""
    return struct.pack(">4I", _u32(owner_id), _u32(house_id), _u32(x), _u32(y))


def home_house_back_payload(house_id: int, success: bool = True, reason: int = 0) -> bytes:
    """Encode HOME_BACK_HOUSE (10012)'s flag/ID response."""
    if success:
        return struct.pack(">BI", 1, _u32(house_id))
    return struct.pack(">BIB", 0, _u32(house_id), int(reason) & 0xFF)
