import struct


def pet_use_tool_payload(pet: dict) -> bytes:
    """Encode the five uint32 values read by HuabaoShowView on success."""
    fields = ("hungry_index", "clean_index", "mood_index", "love_energy", "love_up_limit")
    values = [int(pet.get(field, 0) or 0) & 0xFFFFFFFF for field in fields]
    return struct.pack(">5I", *values)
