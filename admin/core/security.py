import hashlib


def double_md5(value: str) -> str:
    """Return the lowercase hexadecimal MD5 digest applied twice."""
    first = hashlib.md5(value.encode("utf-8")).hexdigest()
    return hashlib.md5(first.encode("ascii")).hexdigest()
