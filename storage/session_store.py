import secrets
import time


class SessionStore:

    def __init__(self, ttl=3000):
        self.ttl, self.items = ttl, {}

    def issue(self, uid):
        self.purge()
        token = secrets.token_bytes(16)
        self.items[token] = (uid, time.monotonic() + self.ttl)
        return token

    def valid(self, token, uid):
        self.purge()
        item = self.items.get(token)
        return item is not None and item[0] == uid

    def purge(self):
        now = time.monotonic()
        for token, (_, deadline) in list(self.items.items()):
            if deadline <= now: del self.items[token]
