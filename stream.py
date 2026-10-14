import hashlib


def double_md5(password: str) -> str:
    return hashlib.md5(hashlib.md5(password.encode("utf-8")).hexdigest().encode("ascii")).hexdigest()


def fixed_utf8(value: str, size: int) -> bytes:
    raw = value.encode("utf-8")
    return (raw[: size - 1] + b"\0") if len(raw) >= size else raw.ljust(size, b"\0")


def read_fixed_utf8(raw: bytes) -> str:
    return raw.split(b"\0", 1)[0].decode("utf-8")


def _u8(value) -> int:
    return _u32(value) & 0xff


def _u32(v) -> int:
    try: return int(v or 0) & 0xffffffff
    except (TypeError, ValueError): return 0
