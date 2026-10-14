"""Player action inventory and magic action catalog queries."""

from __future__ import annotations

from typing import Any

import pymysql


class ActionsRepository:
    def __init__(self, mysql_config: dict[str, Any]):
        self.mysql_config = dict(mysql_config)
        self.connection = self._connect()
        self._validate_schema()

    def _connect(self):
        return pymysql.connect(
            **self.mysql_config,
            charset="utf8mb4",
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def _ensure_connection(self) -> None:
        self.connection.ping(reconnect=True)

    def _validate_schema(self) -> None:
        required = {
            "player_magics": {"user_id", "action_id", "amount"},
            "type_magics": {"id", "name"},
        }
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            for table, required_columns in required.items():
                cursor.execute(
                    "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
                    (self.mysql_config["database"], table),
                )
                columns = {str(row["COLUMN_NAME"]) for row in cursor.fetchall()}
                missing = required_columns - columns
                if missing:
                    raise RuntimeError(
                        f"{table} table is missing columns: {', '.join(sorted(missing))}"
                    )

    def close(self) -> None:
        self.connection.close()

    @staticmethod
    def _row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "user_id": int(row["user_id"]),
            "action_id": int(row["action_id"]),
            "name": "" if row.get("name") is None else str(row["name"]),
            "amount": int(row["amount"]),
        }

    @staticmethod
    def _account_exists(cursor, user_id: int) -> bool:
        cursor.execute("SELECT 1 FROM accounts WHERE user_id=%s LIMIT 1", (user_id,))
        return cursor.fetchone() is not None

    def list(self, user_id: int) -> list[dict[str, Any]] | None:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            if not self._account_exists(cursor, user_id):
                return None
            cursor.execute(
                "SELECT pa.user_id, pa.action_id, tm.name, pa.amount "
                "FROM player_magics pa "
                "LEFT JOIN type_magics tm ON tm.id=pa.action_id "
                "WHERE pa.user_id=%s ORDER BY pa.action_id",
                (user_id,),
            )
            return [self._row(row) for row in cursor.fetchall()]

    def options(self) -> list[dict[str, Any]]:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT id, name FROM type_magics ORDER BY id")
            return [
                {
                    "id": int(row["id"]),
                    "name": "" if row.get("name") is None else str(row["name"]),
                }
                for row in cursor.fetchall()
            ]

    def create(self, user_id: int, action_id: int, amount: int) -> dict[str, Any]:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            if not self._account_exists(cursor, user_id):
                raise LookupError("account not found")
            cursor.execute("SELECT 1 FROM type_magics WHERE id=%s LIMIT 1", (action_id,))
            if cursor.fetchone() is None:
                raise LookupError("action not found")
            cursor.execute(
                "INSERT INTO player_magics (user_id, action_id, amount) "
                "VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE amount=amount+VALUES(amount)",
                (user_id, action_id, amount),
            )
        return self.get(user_id, action_id)

    def get(self, user_id: int, action_id: int) -> dict[str, Any] | None:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT pa.user_id, pa.action_id, tm.name, pa.amount "
                "FROM player_magics pa LEFT JOIN type_magics tm ON tm.id=pa.action_id "
                "WHERE pa.user_id=%s AND pa.action_id=%s LIMIT 1",
                (user_id, action_id),
            )
            row = cursor.fetchone()
        return self._row(row) if row else None

    def update(self, user_id: int, action_id: int, amount: int) -> dict[str, Any] | None:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE player_magics SET amount=%s WHERE user_id=%s AND action_id=%s",
                (amount, user_id, action_id),
            )
            if cursor.rowcount == 0:
                cursor.execute(
                    "SELECT 1 FROM player_magics WHERE user_id=%s AND action_id=%s LIMIT 1",
                    (user_id, action_id),
                )
                if cursor.fetchone() is None:
                    return None
        return self.get(user_id, action_id)
