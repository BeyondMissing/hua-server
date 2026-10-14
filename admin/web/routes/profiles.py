from http import HTTPStatus
from urllib.parse import parse_qs

import pymysql

from admin.core.errors import ValidationError
from admin.web.consts import BIRTHDAYS, NATIONALITIES


def _int_query(query, name: str):
    value = query.get(name, [""])[0]
    if value == "":
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValidationError(f"{name} must be an integer") from exc


def list_profiles(handler, query_string: str) -> None:
    query = parse_qs(query_string)
    try:
        user_id = _int_query(query, "user_id")
        nationality = _int_query(query, "nationality")
        if user_id is not None and user_id < 0:
            raise ValidationError("user_id must be at least 0")
        if nationality is not None and nationality not in NATIONALITIES:
            raise ValidationError("invalid nationality")
        result = handler.app.profiles.list(
            user_id=user_id,
            nickname=query.get("nickname", [""])[0],
            nationality=nationality,
            page=_int_query(query, "page") or 1,
            page_size=_int_query(query, "page_size") or 20,
        )
    except ValidationError as exc:
        handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        return
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    handler.send_json(HTTPStatus.OK, result)


def get_profile(handler, user_id: int) -> None:
    try:
        row = handler.app.profiles.get(user_id)
        if row is not None:
            row["options"] = handler.app.profiles.options(user_id)
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    if row is None:
        handler.send_error_json(HTTPStatus.NOT_FOUND, "player profile not found")
        return
    handler.send_json(HTTPStatus.OK, row)


def profile_options(handler, user_id: int) -> None:
    try:
        result = handler.app.profiles.options(user_id)
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    if result is None:
        handler.send_error_json(HTTPStatus.NOT_FOUND, "player profile not found")
        return
    handler.send_json(HTTPStatus.OK, result)


def update_profile(handler, user_id: int, body) -> None:
    try:
        row = handler.app.profiles.update(user_id, body)
    except ValidationError as exc:
        handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        return
    except pymysql.err.IntegrityError as exc:
        handler.send_error_json(HTTPStatus.CONFLICT, str(exc))
        return
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    if row is None:
        handler.send_error_json(HTTPStatus.NOT_FOUND, "player profile not found")
        return
    handler.send_json(HTTPStatus.OK, row)


def update_clothing(handler, user_id: int, body) -> None:
    try:
        row = handler.app.profiles.update_clothing(user_id, body.get("clothing"))
    except ValidationError as exc:
        handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        return
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    if row is None:
        handler.send_error_json(HTTPStatus.NOT_FOUND, "player profile not found")
        return
    handler.send_json(HTTPStatus.OK, {"clothing": row["clothing"]})
