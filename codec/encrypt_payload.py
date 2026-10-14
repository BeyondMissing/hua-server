from codec.xor_with_as_key import xor_with_as_key


def encrypt_payload(plaintext: bytes, key: bytes) -> bytes:
    """Python equivalent of com.fcc.MEncrypt (including the +1 byte)."""
    mixed = bytearray(xor_with_as_key(plaintext, key))
    mixed.append(0)

    # Exact translation of the decompiled backwards loop.  All writes are
    # byte-sized, hence the explicit ``& 0xff`` masks.
    for pos in range(len(mixed) - 1, 0, -1):
        prev = mixed[pos - 1]
        cur = mixed[pos]
        mixed[pos] = ((prev >> 3) | cur) & 0xFF
        mixed[pos - 1] = (prev << 5) & 0xFF
    if mixed:
        mixed[0] |= 3
    return bytes(mixed)
