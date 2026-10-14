from __future__ import annotations

from typing import Any

import pymysql

from admin.core.errors import ValidationError


ALLOWED_PAGE_SIZES = (10, 50, 100)


class HouseGoodsRepository:
    """Queries player house goods and the fixed goods catalog."""

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
            "type_house_goods": {"id", "name"},
            "player_house_goods": {
                "user_id", "item_id", "no", "x", "y", "m", "z", "is_set",
            },
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
                    names = ", ".join(sorted(missing))
                    raise RuntimeError(f"{table} table is missing columns: {names}")

    def close(self) -> None:
        self.connection.close()

    @staticmethod
    def _row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "user_id": int(row["user_id"]),
            "item_id": int(row["item_id"]),
            "name": "" if row.get("name") is None else str(row["name"]),
            "no": int(row["no"]),
            "x": int(row["x"]),
            "y": int(row["y"]),
            "m": int(row["m"]),
            "z": int(row["z"]),
            "is_set": int(bool(row["is_set"])),
        }

    @staticmethod
    def _account_exists(cursor, user_id: int) -> bool:
        cursor.execute("SELECT 1 FROM accounts WHERE user_id=%s LIMIT 1", (user_id,))
        return cursor.fetchone() is not None

    def list(
        self,
        user_id: int,
        *,
        page: int = 1,
        page_size: int = 10,
    ) -> dict[str, Any] | None:
        self._ensure_connection()
        page = max(1, int(page))
        if page_size not in ALLOWED_PAGE_SIZES:
            raise ValidationError("page_size must be one of 10, 50, or 100")
        with self.connection.cursor() as cursor:
            if not self._account_exists(cursor, user_id):
                return None
            cursor.execute(
                "SELECT COUNT(*) AS total FROM player_house_goods WHERE user_id=%s",
                (user_id,),
            )
            total = int(cursor.fetchone()["total"])
            cursor.execute(
                "SELECT phg.user_id, phg.item_id, tg.name, phg.no, "
                "phg.x, phg.y, phg.m, phg.z, phg.is_set "
                "FROM player_house_goods phg "
                "LEFT JOIN type_house_goods tg ON tg.id=phg.item_id "
                "WHERE phg.user_id=%s ORDER BY phg.no LIMIT %s OFFSET %s",
                (user_id, page_size, (page - 1) * page_size),
            )
            items = [self._row(row) for row in cursor.fetchall()]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def options(self) -> list[dict[str, Any]]:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT id, name FROM type_house_goods ORDER BY id")
            return [
                {
                    "id": int(row["id"]),
                    "name": "" if row.get("name") is None else str(row["name"]),
                }
                for row in cursor.fetchall()
            ]

    def get(self, user_id: int, no: int) -> dict[str, Any] | None:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT phg.user_id, phg.item_id, tg.name, phg.no, "
                "phg.x, phg.y, phg.m, phg.z, phg.is_set "
                "FROM player_house_goods phg "
                "LEFT JOIN type_house_goods tg ON tg.id=phg.item_id "
                "WHERE phg.user_id=%s AND phg.no=%s LIMIT 1",
                (user_id, no),
            )
            row = cursor.fetchone()
        return self._row(row) if row else None

    def create(self, user_id: int, data: dict[str, int]) -> dict[str, Any]:
        self._ensure_connection()
        item_id = data["item_id"]
        with self.connection.cursor() as cursor:
            if not self._account_exists(cursor, user_id):
                raise LookupError("account not found")
            cursor.execute("SELECT 1 FROM type_house_goods WHERE id=%s LIMIT 1", (item_id,))
            if cursor.fetchone() is None:
                raise LookupError("goods item not found")
            cursor.execute(
                "SELECT COALESCE(MAX(no), 0) AS max_no "
                "FROM player_house_goods WHERE user_id=%s",
                (user_id,),
            )
            no = int(cursor.fetchone()["max_no"]) + 1
            if no > 4294967295:
                raise ValidationError("no is out of range")
            cursor.execute(
                "INSERT INTO player_house_goods "
                "(user_id, item_id, no, x, y, m, z, is_set) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    user_id, item_id, no, data["x"], data["y"],
                    data["m"], data["z"], data["is_set"],
                ),
            )
        return self.get(user_id, no)

    def update(self, user_id: int, no: int, data: dict[str, int]) -> dict[str, Any] | None:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE player_house_goods SET x=%s, y=%s, m=%s, z=%s, is_set=%s "
                "WHERE user_id=%s AND no=%s",
                (data["x"], data["y"], data["m"], data["z"], data["is_set"], user_id, no),
            )
            if cursor.rowcount == 0:
                cursor.execute(
                    "SELECT 1 FROM player_house_goods WHERE user_id=%s AND no=%s LIMIT 1",
                    (user_id, no),
                )
                if cursor.fetchone() is None:
                    return None
        return self.get(user_id, no)

    def delete(self, user_id: int, no: int) -> bool:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM player_house_goods WHERE user_id=%s AND no=%s",
                (user_id, no),
            )
            return cursor.rowcount == 1
