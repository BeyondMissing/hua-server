import secrets
import threading
import time

from admin.config import SESSION_TTL


class SessionStore:
    def __init__(self):
        self._sessions: dict[str, float] = {}
        self._lock = threading.Lock()

    def create(self) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._sessions[token] = time.time() + SESSION_TTL
        return token

    def valid(self, token: str | None) -> bool:
        if not token:
            return False

        with self._lock:
            expires = self._sessions.get(token, 0)
            if expires <= time.time():
                self._sessions.pop(token, None)
                return False
            return True

    def remove(self, token: str | None) -> None:
        if not token:
            return

        with self._lock:
            self._sessions.pop(token, None)
