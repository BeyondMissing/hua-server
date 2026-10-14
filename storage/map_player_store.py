from threading import RLock


class MapPlayerStore:
    """In-memory map membership and player snapshots.

    The store is intentionally scoped to one application process.  Active
    sessions are also process-local, so a native dictionary provides the same
    lifecycle and avoids an external service for this transient state.
    """

    def __init__(self):
        self._items = {}
        self._lock = RLock()

    @staticmethod
    def _scope(scope) -> tuple[int, int]:
        if isinstance(scope, (tuple, list)) and len(scope) == 2:
            return int(scope[0]), int(scope[1])
        return int(scope), 0

    def upsert(self, scope, row: dict) -> None:
        user_id = int(row["user_id"])
        normalized_scope = self._scope(scope)
        with self._lock:
            self._items.setdefault(normalized_scope, {})[user_id] = dict(row)

    def remove(self, scope, user_id: int) -> None:
        normalized_scope = self._scope(scope)
        with self._lock:
            players = self._items.get(normalized_scope)
            if players is None:
                return
            players.pop(int(user_id), None)
            if not players:
                self._items.pop(normalized_scope, None)

    def list_players(self, scope):
        normalized_scope = self._scope(scope)
        with self._lock:
            rows = [dict(row) for row in self._items.get(normalized_scope, {}).values()]
        return sorted(rows, key=lambda row: int(row.get("user_id", 0)))
