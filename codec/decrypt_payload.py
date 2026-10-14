from codec.xor_with_as_key import xor_with_as_key


def _ror_stream_inverse(data: bytes) -> bytes:
    """Undo the byte-stream rotation performed by MEncrypt.

    MEncrypt first allocates ``len(plain)+1`` bytes, appends a zero byte, then
    walks backwards and combines adjacent bytes.  MDecrypt reconstructs the
    original ``len(cipher)-1`` bytes by walking forwards.
    """
    if len(data) < 2:
        return b""
    out = bytearray(len(data) - 1)
    for i in range(len(out)):
        out[i] = ((data[i] & 0xE0) >> 5) | ((data[i + 1] << 3) & 0xF8)
    return bytes(out)


def decrypt_payload(ciphertext: bytes, key: bytes) -> bytes:
    """Python equivalent of com.fcc.MDecrypt.

    ``key`` is the missing ``L__2E_str5`` constant from the supplied
    decompilation.  It is intentionally configurable; an empty key means no
    XOR stage, while still applying the stream inverse.
    """
    rotated = _ror_stream_inverse(ciphertext)
    return xor_with_as_key(rotated, key)