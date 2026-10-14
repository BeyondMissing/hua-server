from http import HTTPStatus
from urllib.parse import parse_qs

from admin.core.errors import ValidationError
from admin.database.gardens import ALLOWED_PAGE_SIZES, MAX_UNSIGNED_INT, WEATHER_VALUES


def _integer(value, name: str) -> int:
    if isinstance(value, bool) or value in (None, ""):
        raise ValidationError(f"{name} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name} must be an integer") from exc


def _user_id(value) -> int:
    user_id = _integer(value, "user_id")
    if not 1 <= user_id <= MAX_UNSIGNED_INT:
        raise ValidationError("user_id is out of range")
    return user_id


def _values(body) -> dict:
    background_id = _integer(body.get("background_id"), "background_id")
    item_id = _integer(body.get("item_id"), "item_id")
    weather = _integer(body.get("weather"), "weather")
    x = _integer(body.get("x"), "x")
    y = _integer(body.get("y"), "y")
    open_flag = _integer(body.get("open_flag"), "open_flag")
    home_name = body.get("home_name")
    temperature = body.get("temperature")
    if not isinstance(home_name, str) or len(home_name) > 64:
        raise ValidationError("home_name must be a string of at most 64 characters")
    if not isinstance(temperature, str) or len(temperature) > 64:
        raise ValidationError("temperature must be a string of at most 64 characters")
    if not 1 <= background_id <= MAX_UNSIGNED_INT:
        raise ValidationError("background_id is out of range")
    if not 1 <= item_id <= MAX_UNSIGNED_INT:
        raise ValidationError("item_id is out of range")
    if weather not in WEATHER_VALUES:
        raise ValidationError("weather must be one of 1, 2, 6, 7, or 8")
    if not 0 <= x <= MAX_UNSIGNED_INT or not 0 <= y <= MAX_UNSIGNED_INT:
        raise ValidationError("x and y must be between 0 and 4294967295")
    if open_flag not in (0, 1):
        raise ValidationError("open_flag must be 0 or 1")
    return {
        "background_id": background_id,
        "home_name": home_name,
        "weather": weather,
        "temperature": temperature,
        "item_id": item_id,
        "x": x,
        "y": y,
        "open_flag": open_flag,
    }


def list_gardens(handler, query_string: str) -> None:
    query = parse_qs(query_string)
    try:
        raw_user_id = query.get("user_id", [""])[0]
        user_id = _user_id(raw_user_id) if raw_user_id else None
        page = _integer(query.get("page", [1])[0], "page")
        page_size = _integer(query.get("page_size", [10])[0], "page_size")
        if page < 1:
            raise ValidationError("page must be at least 1")
        if page_size not in ALLOWED_PAGE_SIZES:
            raise ValidationError("page_size must be one of 10, 50, or 100")
        result = handler.app.gardens.list(user_id=user_id, page=page, page_size=page_size)
    except ValidationError as exc:
        handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        return
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    handler.send_json(HTTPStatus.OK, result)


def options(handler, query_string: str = "") -> None:
    try:
        query = parse_qs(query_string)
        raw_user_id = query.get("user_id", [None])[0]
        result = handler.app.gardens.options(_user_id(raw_user_id) if raw_user_id else None)
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    handler.send_json(HTTPStatus.OK, result)


def get_garden(handler, user_id: int) -> None:
    try:
        row = handler.app.gardens.get(_user_id(user_id))
    except ValidationError as exc:
        handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        return
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    if row is None:
        handler.send_error_json(HTTPStatus.NOT_FOUND, "player garden not found")
        return
    handler.send_json(HTTPStatus.OK, row)


def update_garden(handler, user_id: int, body) -> None:
    try:
        row = handler.app.gardens.update(_user_id(user_id), _values(body))
    except ValidationError as exc:
        handler.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        return
    except Exception as exc:
        handler.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return
    if row is None:
        handler.send_error_json(HTTPStatus.NOT_FOUND, "player garden not found")
        return
    handler.send_json(HTTPStatus.OK, row)
