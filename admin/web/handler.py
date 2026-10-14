import json
import mimetypes
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import unquote, urlparse

from admin.config import STATIC_DIR
from admin.core.errors import ValidationError
from admin.web.routes import actions, accounts, auth, clothes, gardens, house_goods, inventories, pets, profiles, houses, tasks
from admin.web.templates import render_index


class AdminHandler(BaseHTTPRequestHandler):
    server_version = "HuaAdmin/1.0"

    @property
    def app(self):
        return self.server

    def log_message(self, fmt, *args) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def session_token(self) -> str | None:
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        if auth.SESSION_COOKIE not in cookie:
            return None
        return cookie[auth.SESSION_COOKIE].value

    def send_json(
        self,
        status: int,
        value: Any,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        for name, header_value in (extra_headers or {}).items():
            self.send_header(name, header_value)
        self.end_headers()
        self.wfile.write(payload)

    def send_error_json(self, status: int, message: str) -> None:
        self.send_json(status, {"error": message})

    def read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError) as exc:
            raise ValidationError("request body must be valid JSON") from exc

        if not isinstance(body, dict):
            raise ValidationError("request body must be an object")
        return body

    def require_login(self) -> bool:
        if self.app.sessions.valid(self.session_token()):
            return True
        self.send_error_json(HTTPStatus.UNAUTHORIZED, "login required")
        return False

    def send_html(self) -> None:
        try:
            payload = render_index()
        except OSError:
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, "admin page is unavailable")
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_static(self, request_path: str) -> None:
        relative_path = unquote(request_path.removeprefix("/static/"))
        file_path = (STATIC_DIR / relative_path).resolve()
        if not file_path.is_relative_to(STATIC_DIR) or not file_path.is_file():
            self.send_error_json(HTTPStatus.NOT_FOUND, "not found")
            return

        payload = file_path.read_bytes()
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    @staticmethod
    def account_id(path: str) -> int | None:
        try:
            return int(path.rsplit("/", 1)[1])
        except ValueError:
            return None

    @staticmethod
    def clothing_ids(path: str) -> tuple[int, int] | None:
        parts = path.removeprefix("/api/player-clothes/").split("/")
        if len(parts) != 2:
            return None
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None

    @staticmethod
    def house_goods_ids(path: str) -> tuple[int, int] | None:
        parts = path.removeprefix("/api/player-house-goods/").split("/")
        if len(parts) != 2:
            return None
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None

    @staticmethod
    def action_ids(path: str) -> tuple[int, int] | None:
        parts = path.removeprefix("/api/player-actions/").split("/")
        if len(parts) != 2:
            return None
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None

    @staticmethod
    def inventory_ids(path: str, kind: str) -> tuple[int, int] | None:
        parts = path.removeprefix(f"/api/player-{kind}/").split("/")
        if len(parts) != 2:
            return None
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self.send_html()
            return
        if parsed.path.startswith("/static/"):
            self.send_static(parsed.path)
            return
        if parsed.path == "/api/session":
            auth.session(self)
            return
        if parsed.path == "/api/tasks":
            if self.require_login():
                tasks.list_tasks(self, parsed.query)
            return
        if parsed.path == "/api/accounts":
            if self.require_login():
                accounts.list_accounts(self, parsed.query)
            return
        if parsed.path == "/api/player-profiles":
            if self.require_login():
                profiles.list_profiles(self, parsed.query)
            return
        if parsed.path == "/api/player-pets":
            if self.require_login():
                pets.list_pets(self, parsed.query)
            return
        if parsed.path.startswith("/api/player-pets/"):
            if not self.require_login():
                return
            identifiers = self.pet_ids(parsed.path)
            if identifiers is None:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "invalid user_id or pet_id")
                return
            pets.get_pet(self, *identifiers)
            return
        if parsed.path == "/api/player-homes/options":
            if self.require_login():
                gardens.options(self, parsed.query)
            return
        if parsed.path == "/api/player-homes":
            if self.require_login():
                gardens.list_gardens(self, parsed.query)
            return
        if parsed.path.startswith("/api/player-homes/"):
            if not self.require_login():
                return
            user_id = self.account_id(parsed.path)
            if user_id is None:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "invalid user_id")
                return
            gardens.get_garden(self, user_id)
            return
        if parsed.path.startswith("/api/player-profiles/"):
            if not self.require_login():
                return
            suffix = parsed.path.removeprefix("/api/player-profiles/")
            parts = suffix.split("/")
            print(parts)
            try:
                user_id = int(parts[0])
            except (ValueError, IndexError):
                self.send_error_json(HTTPStatus.BAD_REQUEST, "invalid user_id")
                return
            if len(parts) == 2 and parts[1] == "options":
                print("non-options")
                profiles.profile_options(self, user_id)
            else:
                print("options")
                profiles.get_profile(self, user_id)
            return
        if parsed.path.startswith("/api/accounts/"):
            if not self.require_login():
                return
            user_id = self.account_id(parsed.path)
            if user_id is None:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "invalid user_id")
                return
            accounts.get_account(self, user_id)
            return
        if parsed.path == "/api/player-clothes/options":
            if self.require_login():
                clothes.options(self)
            return
        if parsed.path == "/api/player-clothes":
            if self.require_login():
                clothes.list_clothes(self, parsed.query)
            return
        if parsed.path == "/api/player-house-goods/options":
            if self.require_login():
                house_goods.options(self)
            return
        if parsed.path == "/api/player-actions/options":
            if self.require_login():
                actions.options(self)
            return
        if parsed.path == "/api/player-actions":
            if self.require_login():
                actions.list_actions(self, parsed.query)
            return
        for kind in ("flowers", "seeds", "materials", "pet-supplies", "tools", "pollens"):
            if parsed.path == f"/api/player-{kind}/options":
                if self.require_login():
                    inventories.options(self, kind)
                return
        if parsed.path == "/api/player-houses":
            if self.require_login():
                houses.list_houses(self, parsed.query)
            return
        for kind in ("flowers", "seeds", "materials", "pet-supplies", "tools", "pollens"):
            if parsed.path == f"/api/player-{kind}":
                if self.require_login():
                    inventories.list_inventory(self, kind, parsed.query)
                return
        if parsed.path == "/api/player-house-goods":
            if self.require_login():
                house_goods.list_goods(self, parsed.query)
            return
        self.send_error_json(HTTPStatus.NOT_FOUND, "not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            body = self.read_json()
        except ValidationError as exc:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
            return

        if parsed.path == "/api/login":
            auth.login(self, body)
            return
        if parsed.path == "/api/logout":
            auth.logout(self)
            return
        if not self.require_login():
            return
        if parsed.path == "/api/tasks/reset":
            tasks.reset_task(self, body)
            return
        if parsed.path == "/api/accounts":
            accounts.create_account(self, body)
            return
        if parsed.path == "/api/player-pets":
            pets.create_pet(self, body)
            return
        if parsed.path == "/api/player-clothes":
            clothes.acquire_clothing(self, body)
            return
        if parsed.path == "/api/player-house-goods":
            house_goods.create_goods(self, body)
            return
        if parsed.path == "/api/player-actions":
            actions.create_action(self, body)
            return
        for kind in ("flowers", "seeds", "materials", "pet-supplies", "tools", "pollens"):
            if parsed.path == f"/api/player-{kind}":
                inventories.create_inventory(self, kind, body)
                return
        if parsed.path.startswith("/api/player-houses/"):
            identifiers = self.house_ids(parsed.path)
            if identifiers is None:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "invalid user_id or house_id")
                return
            houses.toggle_house(self, *identifiers)
            return
        if parsed.path.startswith("/api/player-house-goods/"):
            identifiers = self.house_goods_ids(parsed.path)
            if identifiers is None:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "invalid user_id or no")
                return
            house_goods.update_goods(self, *identifiers, body)
            return
        if parsed.path.startswith("/api/player-actions/"):
            identifiers = self.action_ids(parsed.path)
            if identifiers is None:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "invalid user_id or action_id")
                return
            actions.update_action(self, *identifiers, body)
            return
        for kind in ("flowers", "seeds", "materials", "pet-supplies", "tools", "pollens"):
            if parsed.path.startswith(f"/api/player-{kind}/"):
                identifiers = self.inventory_ids(parsed.path, kind)
                if identifiers is None:
                    self.send_error_json(HTTPStatus.BAD_REQUEST, "invalid user_id or item_id")
                    return
                inventories.update_inventory(self, kind, *identifiers, body)
                return
        if parsed.path.startswith("/api/player-profiles/"):
            suffix = parsed.path.removeprefix("/api/player-profiles/")
            parts = suffix.split("/")
            try:
                user_id = int(parts[0])
            except (ValueError, IndexError):
                self.send_error_json(HTTPStatus.BAD_REQUEST, "invalid user_id")
                return
            if len(parts) == 2 and parts[1] == "clothing":
                profiles.update_clothing(self, user_id, body)
            elif len(parts) == 1:
                profiles.update_profile(self, user_id, body)
            else:
                self.send_error_json(HTTPStatus.NOT_FOUND, "not found")
            return
        if parsed.path.startswith("/api/player-pets/"):
            identifiers = self.pet_ids(parsed.path)
            if identifiers is None:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "invalid user_id or pet_id")
                return
            pets.update_pet(self, *identifiers, body)
            return
        if parsed.path.startswith("/api/player-homes/"):
            user_id = self.account_id(parsed.path)
            if user_id is None:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "invalid user_id")
                return
            gardens.update_garden(self, user_id, body)
            return
        if parsed.path.startswith("/api/accounts/"):
            user_id = self.account_id(parsed.path)
            if user_id is None:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "invalid user_id")
                return
            accounts.update_account(self, user_id, body)
            return
        self.send_error_json(HTTPStatus.NOT_FOUND, "not found")

    do_PUT = do_POST

    @staticmethod
    def pet_ids(path: str) -> tuple[int, int] | None:
        parts = path.removeprefix("/api/player-pets/").split("/")
        if len(parts) != 2:
            return None
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None

    @staticmethod
    def house_ids(path: str) -> tuple[int, int] | None:
        parts = path.removeprefix("/api/player-houses/").split("/")
        if len(parts) != 2:
            return None
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if not self.require_login():
            return
        if parsed.path.startswith("/api/player-clothes/"):
            identifiers = self.clothing_ids(parsed.path)
            if identifiers is None:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "invalid user_id or cloth_id")
                return
            clothes.discard_clothing(self, *identifiers)
            return
        if parsed.path.startswith("/api/player-house-goods/"):
            identifiers = self.house_goods_ids(parsed.path)
            if identifiers is None:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "invalid user_id or no")
                return
            house_goods.delete_goods(self, *identifiers)
            return
        if not parsed.path.startswith("/api/accounts/"):
            self.send_error_json(HTTPStatus.NOT_FOUND, "not found")
            return

        user_id = self.account_id(parsed.path)
        if user_id is None:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "invalid user_id")
            return
        accounts.delete_account(self, user_id)
