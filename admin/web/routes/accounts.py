from http import HTTPStatus
from urllib.parse import parse_qs

import pymysql

from admin.core.errors import ValidationError


def list_accounts(handler, query_string: str) -> None:
    query = parse_qs(query_string)
    try:
        page = int(query.get("page", ["1"])[0])
        page_size = int(query.get("page_size", ["20"])[0])
    except ValueError:
        handler.send_error_json(HTTPStatus.BAD_REQUEST, "page and page_size must be integers")
        return

    try:
        result = handler.app.accounts.list(
            query.get("search", [""])[0],
            page,
            page_size,
        )
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return

    handler.send_json(HTTPStatus.OK, result)


def get_account(handler, user_id: int) -> None:
    row = handler.app.accounts.get(user_id)
    if row is None:
        handler.send_error_json(HTTPStatus.NOT_FOUND, "account not found")
        return
    handler.send_json(HTTPStatus.OK, row)


def create_account(handler, body) -> None:
    try:
        row = handler.app.accounts.create(body)
    except ValidationError as exc:
        handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        return
    except pymysql.err.IntegrityError:
        handler.send_error_json(HTTPStatus.CONFLICT, "user_id or login_name already exists")
        return
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    handler.send_json(HTTPStatus.CREATED, row)


def update_account(handler, user_id: int, body) -> None:
    try:
        row = handler.app.accounts.update(user_id, body)
    except ValidationError as exc:
        handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        return
    except pymysql.err.IntegrityError:
        handler.send_error_json(HTTPStatus.CONFLICT, "user_id or login_name already exists")
        return
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return

    if row is None:
        handler.send_error_json(HTTPStatus.NOT_FOUND, "account not found")
        return
    handler.send_json(HTTPStatus.OK, row)


def delete_account(handler, user_id: int) -> None:
    try:
        deleted = handler.app.accounts.delete(user_id)
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return

    if not deleted:
        handler.send_error_json(HTTPStatus.NOT_FOUND, "account not found")
        return
    handler.send_json(HTTPStatus.OK, {"deleted": True})
