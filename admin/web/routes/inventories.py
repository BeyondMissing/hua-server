from http import HTTPStatus
from urllib.parse import parse_qs

import pymysql

from admin.core.errors import ValidationError
from admin.database.inventories import INVENTORY_DEFINITIONS


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


def _item_id(value) -> int:
    item_id = _integer(value, "item_id")
    if not 1 <= item_id <= 4294967295:
        raise ValidationError("item_id is out of range")
    return item_id


def _amount(value) -> int:
    amount = _integer(value, "amount")
    if not 0 <= amount <= 4294967295:
        raise ValidationError("amount must be between 0 and 4294967295")
    return amount


def _repo(handler, kind: str):
    if kind not in INVENTORY_DEFINITIONS:
        raise KeyError(kind)
    return getattr(handler.app, kind.replace("-", "_"))


def list_inventory(handler, kind: str, query_string: str) -> None:
    query = parse_qs(query_string)
    try:
        user_id = _user_id(query.get("user_id", [None])[0])
        if kind in ("pet-supplies", "tools"):
            page, page_size = 1, None
        else:
            page = _integer(query.get("page", [1])[0], "page")
            page_size = _integer(query.get("page_size", [10])[0], "page_size")
            if page < 1:
                raise ValidationError("page must be at least 1")
            if page_size not in (10, 50, 100):
                raise ValidationError("page_size must be one of 10, 50, or 100")
        result = _repo(handler, kind).list(
            user_id,
            name=query.get("name", [""])[0],
            page=page,
            page_size=page_size,
        )
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


def options(handler, kind: str) -> None:
    try:
        items = _repo(handler, kind).options()
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    handler.send_json(HTTPStatus.OK, {"items": items})


def create_inventory(handler, kind: str, body) -> None:
    try:
        user_id = _user_id(body.get("user_id"))
        item_id = _item_id(body.get("item_id"))
        amount = _amount(body.get("amount"))
        row = _repo(handler, kind).create(user_id, item_id, amount)
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


def update_inventory(handler, kind: str, user_id: int, item_id: int, body) -> None:
    try:
        user_id = _user_id(user_id)
        item_id = _item_id(item_id)
        amount = _amount(body.get("amount"))
        row = _repo(handler, kind).update(user_id, item_id, amount)
    except ValidationError as exc:
        handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        return
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    if row is None:
        handler.send_error_json(HTTPStatus.NOT_FOUND, "inventory item not found")
        return
    handler.send_json(HTTPStatus.OK, row)
