from datetime import datetime
from http import HTTPStatus
from urllib.parse import parse_qs

import pymysql

from admin.core.errors import ValidationError
from admin.database.clothes import ALLOWED_PAGE_SIZES
from admin.web.consts import CLOTHING_SLOT_BY_TYPE


def _query_int(query, name: str, *, required: bool = False) -> int | None:
    value = query.get(name, [""])[0]
    if value == "":
        if required:
            raise ValidationError(f"{name} is required")
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name} must be an integer") from exc


def _body_int(body, name: str) -> int:
    value = body.get(name)
    if isinstance(value, bool) or value in (None, ""):
        raise ValidationError(f"{name} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name} must be an integer") from exc


def list_clothes(handler, query_string: str) -> None:
    query = parse_qs(query_string)
    try:
        user_id = _query_int(query, "user_id", required=True)
        page = _query_int(query, "page") or 1
        page_size = _query_int(query, "page_size") or 10
        sex = _query_int(query, "sex")
        cloth_type = _query_int(query, "cloth_type")
        if sex is not None and sex not in (0, 1, 2):
            raise ValidationError("sex must be 0, 1, or 2")
        if page_size not in ALLOWED_PAGE_SIZES:
            raise ValidationError("page_size must be one of 10, 50, or 100")
        result = handler.app.clothes.list(
            user_id,
            name=query.get("name", [""])[0],
            sex=sex,
            cloth_type=cloth_type,
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


def options(handler) -> None:
    handler.send_json(
        HTTPStatus.OK,
        {
            "cloth_types": [
                {"value": value, "name": name}
                for value, name in CLOTHING_SLOT_BY_TYPE.items()
            ]
        },
    )


def acquire_clothing(handler, body) -> None:
    try:
        user_id = _body_int(body, "user_id")
        cloth_id = _body_int(body, "cloth_id")
        raw_acquired_at = body.get("acquired_at")
        if not isinstance(raw_acquired_at, str) or not raw_acquired_at.strip():
            raise ValidationError("acquired_at is required")
        try:
            acquired_at = datetime.fromisoformat(raw_acquired_at.strip())
        except ValueError as exc:
            raise ValidationError("acquired_at must be a valid date and time") from exc
        row = handler.app.clothes.acquire(user_id, cloth_id, acquired_at)
    except ValidationError as exc:
        handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        return
    except LookupError as exc:
        handler.send_error_json(HTTPStatus.NOT_FOUND, str(exc))
        return
    except pymysql.err.IntegrityError:
        handler.send_error_json(HTTPStatus.CONFLICT, "clothing has already been acquired")
        return
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    handler.send_json(HTTPStatus.CREATED, row)


def discard_clothing(handler, user_id: int, cloth_id: int) -> None:
    try:
        deleted = handler.app.clothes.discard(user_id, cloth_id)
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    if not deleted:
        handler.send_error_json(HTTPStatus.NOT_FOUND, "acquired clothing not found")
        return
    handler.send_json(HTTPStatus.OK, {"deleted": True})
