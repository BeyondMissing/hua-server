from typing import Any

from admin.config import BOOL_FIELDS
from admin.core.errors import ValidationError
from admin.core.security import double_md5


def _int_field(data: dict[str, Any], field: str, *, required: bool) -> int | None:
    if field not in data or data[field] in (None, ""):
        if required:
            raise ValidationError(f"{field} is required")
        return None

    value = data[field]
    if isinstance(value, bool) or isinstance(value, (dict, list)):
        raise ValidationError(f"{field} must be an integer")

    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field} must be an integer") from exc


def _password_hash(value: Any) -> str:
    password_hash = str(value)
    is_hex = all(character in "0123456789abcdefABCDEF" for character in password_hash)
    if len(password_hash) != 32 or not is_hex:
        raise ValidationError("password_hash must be a 32-character hexadecimal string")
    return password_hash.lower()


def validate_account(data: dict[str, Any], *, creating: bool) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValidationError("request body must be an object")

    result: dict[str, Any] = {}
    user_id = _int_field(data, "user_id", required=creating)
    if user_id is not None:
        if user_id < 100000:
            raise ValidationError("user_id must be at least 100000")
        result["user_id"] = user_id

    if creating or "login_name" in data:
        login_name = str(data.get("login_name", ""))
        if not 2 <= len(login_name) <= 8:
            raise ValidationError("login_name must contain 2 to 8 characters")
        result["login_name"] = login_name

    if creating:
        password = data.get("password")
        if isinstance(password, str) and password:
            result["password_hash"] = double_md5(password)
        elif "password_hash" in data:
            result["password_hash"] = _password_hash(data["password_hash"])
        else:
            raise ValidationError("password is required")
    elif "password" in data and data["password"] != "":
        if not isinstance(data["password"], str):
            raise ValidationError("password must be a string")
        result["password_hash"] = double_md5(data["password"])
    elif "password_hash" in data:
        result["password_hash"] = _password_hash(data["password_hash"])

    for field in BOOL_FIELDS:
        if not creating and field not in data:
            continue

        value = _int_field(data, field, required=False)
        if value is None:
            value = 0
        if value not in (0, 1):
            raise ValidationError(f"{field} must be 0 or 1")
        result[field] = value

    return result
