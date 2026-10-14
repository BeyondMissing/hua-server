"""Player house ownership queries for the administration application."""

from __future__ import annotations

from typing import Any

import pymysql


class HouseRepository:
    def __init__(self, mysql_config: dict[str, Any]):
        self.mysql_config = dict(mysql_config)
        self.connection = pymysql.connect(
            **self.mysql_config,
            charset="utf8mb4",
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor,
        )
        self._validate_schema()

    def _validate_schema(self) -> None:
        required = {
            "player_houses": {"user_id", "house_id"},
            "type_houses": {"id", "name"},
        }
        self.connection.ping(reconnect=True)
        with self.connection.cursor() as cursor:
            for table, columns in required.items():
                cursor.execute(
                    "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
                    (self.mysql_config["database"], table),
                )
                found = {str(row["COLUMN_NAME"]) for row in cursor.fetchall()}
                missing = columns - found
                if missing:
                    raise RuntimeError(f"{table} table is missing columns: {', '.join(sorted(missing))}")

    def close(self) -> None:
        self.connection.close()

    def list(self, user_id: int) -> dict[str, Any] | None:
        self.connection.ping(reconnect=True)
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM accounts WHERE user_id=%s LIMIT 1", (user_id,))
            if cursor.fetchone() is None:
                return None
            cursor.execute(
                "SELECT h.id, h.name, EXISTS(SELECT 1 FROM player_houses ph "
                "WHERE ph.user_id=%s AND ph.house_id=h.id) AS owned "
                "FROM type_houses h ORDER BY h.id",
                (user_id,),
            )
            items = [
                {"id": int(row["id"]), "name": str(row.get("name") or ""), "owned": bool(row["owned"])}
                for row in cursor.fetchall()
            ]
        return {"items": items, "total": len(items), "user_id": user_id}

    def toggle(self, user_id: int, house_id: int) -> dict[str, Any] | None:
        self.connection.ping(reconnect=True)
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM accounts WHERE user_id=%s LIMIT 1", (user_id,))
            if cursor.fetchone() is None:
                return None
            cursor.execute("SELECT 1 FROM type_houses WHERE id=%s LIMIT 1", (house_id,))
            if cursor.fetchone() is None:
                raise LookupError("house not found")
            cursor.execute(
                "SELECT 1 FROM player_houses WHERE user_id=%s AND house_id=%s LIMIT 1",
                (user_id, house_id),
            )
            if cursor.fetchone() is None:
                cursor.execute("INSERT INTO player_houses (user_id, house_id) VALUES (%s, %s)", (user_id, house_id))
                owned = True
            else:
                cursor.execute("DELETE FROM player_houses WHERE user_id=%s AND house_id=%s", (user_id, house_id))
                owned = False
        return {"user_id": user_id, "house_id": house_id, "owned": owned}
