
def xor_with_as_key(data: bytes, key: bytes) -> bytes:
    """Apply the exact key-index state machine emitted by CrossBridge.

    The decompiled code advances through offsets 0..34.  When the offset is
    35 it reads the base pointer (key[0]) and resets the offset to zero; the
    following iteration therefore reads key[0] a second time.  This gives the
    sequence 0..34, 0, 0, 1, 2... rather than ``i % 35``.
    """
    if not key:
        return bytes(data)
    if len(key) != 35:
        raise ValueError(f"MEncrypt key must contain 35 bytes, got {len(key)}")

    out = bytearray(len(data))
    key_index = 0
    for i, value in enumerate(data):
        if key_index == 35:
            out[i] = value ^ key[0]
            key_index = 0
        else:
            out[i] = value ^ key[key_index]
            key_index += 1
    return bytes(out)
