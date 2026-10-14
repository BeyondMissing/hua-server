from http import HTTPStatus
from urllib.parse import parse_qs

import pymysql

from admin.core.errors import ValidationError

def _int(query, name, default=None):
    raw = query.get(name, [""])[0]
    if raw == "": return default
    try: return int(raw)
    except ValueError as exc: raise ValidationError(f"{name} must be an integer") from exc

def list_pets(handler, query_string):
    try:
        query = parse_qs(query_string)
        user_id = _int(query, "user_id")
        if user_id is not None and user_id < 0: raise ValidationError("user_id must be at least 0")
        result = handler.app.pets.list(page=_int(query, "page", 1), page_size=_int(query, "page_size", 20), user_id=user_id)
    except ValidationError as exc: handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc)); return
    except Exception as exc: handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc)); return
    handler.send_json(HTTPStatus.OK, result)

def get_pet(handler, user_id, pet_id):
    try: row = handler.app.pets.get(user_id, pet_id)
    except Exception as exc: handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc)); return
    if row is None: handler.send_error_json(HTTPStatus.NOT_FOUND, "pet not found"); return
    handler.send_json(HTTPStatus.OK, row)

def update_pet(handler, user_id, pet_id, body):
    try: row = handler.app.pets.update(user_id, pet_id, body)
    except ValidationError as exc: handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc)); return
    except pymysql.err.IntegrityError: handler.send_error_json(HTTPStatus.CONFLICT, "该玩家已拥有宠物，无法重复添加或更改为已有宠物"); return
    except Exception as exc: handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc)); return
    if row is None: handler.send_error_json(HTTPStatus.NOT_FOUND, "pet not found"); return
    handler.send_json(HTTPStatus.OK, row)

def create_pet(handler, body):
    try: row = handler.app.pets.create(body)
    except ValidationError as exc: handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc)); return
    except LookupError: handler.send_error_json(HTTPStatus.NOT_FOUND, "玩家不存在，请检查 User ID"); return
    except pymysql.err.IntegrityError: handler.send_error_json(HTTPStatus.CONFLICT, "该玩家已拥有宠物，请使用编辑功能"); return
    except Exception as exc: handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc)); return
    handler.send_json(HTTPStatus.CREATED, row)
