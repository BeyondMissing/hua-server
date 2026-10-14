from http import HTTPStatus
from urllib.parse import parse_qs

import pymysql

from admin.core.errors import ValidationError
from admin.database.house_goods import ALLOWED_PAGE_SIZES


def _integer(value, name: str) -> int:
    if isinstance(value, bool) or value in (None, ""):
        raise ValidationError(f"{name} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name} must be an integer") from exc


def _user_id(value) -> int:
    user_id = _integer(value, "user_id")
    if not 1 <= user_id <= 4294967295:
        raise ValidationError("user_id is out of range")
    return user_id


def _values(body, *, creating: bool) -> dict[str, int]:
    fields = ("x", "y", "m", "z", "is_set")
    result = {field: _integer(body.get(field), field) for field in fields}
    if creating:
        result["item_id"] = _integer(body.get("item_id"), "item_id")
    if not 0 <= result["x"] <= 4294967295:
        raise ValidationError("x must be between 0 and 4294967295")
    if not 0 <= result["y"] <= 4294967295:
        raise ValidationError("y must be between 0 and 4294967295")
    if result["m"] not in (0, 2):
        raise ValidationError("m must be 0 or 2")
    if not 0 <= result["z"] <= 99:
        raise ValidationError("z must be between 0 and 99")
    if result["is_set"] not in (0, 1):
        raise ValidationError("is_set must be 0 or 1")
    return result


def list_goods(handler, query_string: str) -> None:
    query = parse_qs(query_string)
    try:
        user_id = _user_id(query.get("user_id", [None])[0])
        page = _integer(query.get("page", [1])[0], "page")
        page_size = _integer(query.get("page_size", [10])[0], "page_size")
        if page < 1:
            raise ValidationError("page must be at least 1")
        if page_size not in ALLOWED_PAGE_SIZES:
            raise ValidationError("page_size must be one of 10, 50, or 100")
        result = handler.app.house_goods.list(user_id, page=page, page_size=page_size)
    except ValidationError as exc:
        handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        return
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    if result is None:
        handler.send_error_json(HTTPStatus.NOT_FOUND, "account not found")
        return
    handler.send_json(HTTPStatus.OK, result)


def options(handler) -> None:
    try:
        items = handler.app.house_goods.options()
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    handler.send_json(HTTPStatus.OK, {"items": items})


def create_goods(handler, body) -> None:
    try:
        user_id = _user_id(body.get("user_id"))
        row = handler.app.house_goods.create(user_id, _values(body, creating=True))
    except ValidationError as exc:
        handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        return
    except LookupError as exc:
        handler.send_error_json(HTTPStatus.NOT_FOUND, str(exc))
        return
    except pymysql.err.IntegrityError as exc:
        handler.send_error_json(HTTPStatus.CONFLICT, str(exc))
        return
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    handler.send_json(HTTPStatus.CREATED, row)


def update_goods(handler, user_id: int, no: int, body) -> None:
    try:
        user_id = _user_id(user_id)
        if not 1 <= no <= 4294967295:
            raise ValidationError("no is out of range")
        row = handler.app.house_goods.update(user_id, no, _values(body, creating=False))
    except ValidationError as exc:
        handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        return
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    if row is None:
        handler.send_error_json(HTTPStatus.NOT_FOUND, "house goods item not found")
        return
    handler.send_json(HTTPStatus.OK, row)


def delete_goods(handler, user_id: int, no: int) -> None:
    try:
        user_id = _user_id(user_id)
        if not 1 <= no <= 4294967295:
            raise ValidationError("no is out of range")
        deleted = handler.app.house_goods.delete(user_id, no)
    except ValidationError as exc:
        handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        return
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    if not deleted:
        handler.send_error_json(HTTPStatus.NOT_FOUND, "house goods item not found")
        return
    handler.send_json(HTTPStatus.OK, {"deleted": True})
