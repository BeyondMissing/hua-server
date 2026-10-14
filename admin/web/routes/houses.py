from http import HTTPStatus

from admin.core.errors import ValidationError


def _integer(value, name):
    if isinstance(value, bool) or value in (None, ""):
        raise ValidationError(f"{name} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name} must be an integer") from exc


def _id(value, name):
    result = _integer(value, name)
    if not 1 <= result <= 4294967295:
        raise ValidationError(f"{name} is out of range")
    return result


def list_houses(handler, query_string: str) -> None:
    from urllib.parse import parse_qs
    try:
        user_id = _id(parse_qs(query_string).get("user_id", [None])[0], "user_id")
        result = handler.app.houses.list(user_id)
    except ValidationError as exc:
        handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc)); return
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc)); return
    if result is None:
        handler.send_error_json(HTTPStatus.NOT_FOUND, "account not found"); return
    handler.send_json(HTTPStatus.OK, result)


def toggle_house(handler, user_id: int, house_id: int) -> None:
    try:
        result = handler.app.houses.toggle(_id(user_id, "user_id"), _id(house_id, "house_id"))
    except ValidationError as exc:
        handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc)); return
    except LookupError as exc:
        handler.send_error_json(HTTPStatus.NOT_FOUND, str(exc)); return
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc)); return
    if result is None:
        handler.send_error_json(HTTPStatus.NOT_FOUND, "account not found"); return
    handler.send_json(HTTPStatus.OK, result)
