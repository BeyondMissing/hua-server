from http import HTTPStatus

from admin.config import ADMIN_PASSWORD, ADMIN_USERNAME, SESSION_TTL


SESSION_COOKIE = "hua_admin_session"


def session(handler) -> None:
    handler.send_json(
        HTTPStatus.OK,
        {"authenticated": handler.app.sessions.valid(handler.session_token())},
    )


def login(handler, body) -> None:
    is_valid = (
        body.get("username") == ADMIN_USERNAME
        and body.get("password") == ADMIN_PASSWORD
    )
    if not is_valid:
        handler.send_error_json(HTTPStatus.UNAUTHORIZED, "invalid administrator credentials")
        return

    token = handler.app.sessions.create()
    cookie = (
        f"{SESSION_COOKIE}={token}; HttpOnly; SameSite=Lax; "
        f"Path=/; Max-Age={SESSION_TTL}"
    )
    handler.send_json(
        HTTPStatus.OK,
        {"authenticated": True},
        {"Set-Cookie": cookie},
    )


def logout(handler) -> None:
    handler.app.sessions.remove(handler.session_token())
    handler.send_json(
        HTTPStatus.OK,
        {"authenticated": False},
        {
            "Set-Cookie": (
                f"{SESSION_COOKIE}=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"
            )
        },
    )
