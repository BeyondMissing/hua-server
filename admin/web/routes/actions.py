from http import HTTPStatus
from urllib.parse import parse_qs

import pymysql

from admin.core.errors import ValidationError


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


def _action_id(value) -> int:
    action_id = _integer(value, "action_id")
    if not 1 <= action_id <= 4294967295:
        raise ValidationError("action_id is out of range")
    return action_id


def _amount(value) -> int:
    amount = _integer(value, "amount")
    if not 0 <= amount <= 4294967295:
        raise ValidationError("amount must be between 0 and 4294967295")
    return amount


def list_actions(handler, query_string: str) -> None:
    query = parse_qs(query_string)
    try:
        user_id = _user_id(query.get("user_id", [None])[0])
        result = handler.app.actions.list(user_id)
    except ValidationError as exc:
        handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        return
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    if result is None:
        handler.send_error_json(HTTPStatus.NOT_FOUND, "account not found")
        return
    handler.send_json(HTTPStatus.OK, {"items": result})


def options(handler) -> None:
    try:
        items = handler.app.actions.options()
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    handler.send_json(HTTPStatus.OK, {"items": items})


def create_action(handler, body) -> None:
    try:
        user_id = _user_id(body.get("user_id"))
        action_id = _action_id(body.get("action_id"))
        amount = _amount(body.get("amount"))
        row = handler.app.actions.create(user_id, action_id, amount)
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


def update_action(handler, user_id: int, action_id: int, body) -> None:
    try:
        user_id = _user_id(user_id)
        action_id = _action_id(action_id)
        amount = _amount(body.get("amount"))
        row = handler.app.actions.update(user_id, action_id, amount)
    except ValidationError as exc:
        handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        return
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    if row is None:
        handler.send_error_json(HTTPStatus.NOT_FOUND, "player action not found")
        return
    handler.send_json(HTTPStatus.OK, row)
