from http import HTTPStatus
from urllib.parse import parse_qs

from admin.core.errors import ValidationError


def _integer(value, name: str) -> int:
    if value in (None, "") or isinstance(value, bool):
        raise ValidationError(f"{name} must be an integer")
    try:
        value = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name} must be an integer") from exc
    if value < 1 or value > 4294967295:
        raise ValidationError(f"{name} is out of range")
    return value


def list_tasks(handler, query_string: str) -> None:
    query = parse_qs(query_string)
    try:
        user_id = _integer(query.get("user_id", [None])[0], "user_id")
        result = handler.app.tasks.list(user_id)
    except ValidationError as exc:
        handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        return
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    handler.send_json(HTTPStatus.OK, result)


def reset_task(handler, body) -> None:
    try:
        user_id = _integer(body.get("user_id"), "user_id")
        job_id = _integer(body.get("job_id"), "job_id")
        result = handler.app.tasks.reset(user_id, job_id)
    except ValidationError as exc:
        handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        return
    except LookupError as exc:
        handler.send_error_json(HTTPStatus.NOT_FOUND, str(exc))
        return
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    handler.send_json(HTTPStatus.OK, result)
