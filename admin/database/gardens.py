"""Player garden/home queries for the administration application."""

from __future__ import annotations

from typing import Any

import pymysql

from admin.core.errors import ValidationError


ALLOWED_PAGE_SIZES = (10, 50, 100)
WEATHER_VALUES = (1, 2, 6, 7, 8)
MAX_UNSIGNED_INT = 4294967295


class GardenRepository:
    """Read and update the player's home and its single configured house."""

    def __init__(self, mysql_config: dict[str, Any]):
        self.mysql_config = dict(mysql_config)
        self.connection = self._connect()
        self.home_table = self._validate_schema()

    def _connect(self):
        return pymysql.connect(
            **self.mysql_config,
            charset="utf8mb4",
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def _ensure_connection(self) -> None:
        self.connection.ping(reconnect=True)

    def _validate_schema(self) -> str:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT TABLE_NAME FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA=%s AND TABLE_NAME IN ('player_home', 'player_homes')",
                (self.mysql_config["database"],),
            )
            tables = {str(row["TABLE_NAME"]) for row in cursor.fetchall()}
            home_table = "player_home" if "player_home" in tables else "player_homes"
            if home_table not in tables:
                raise RuntimeError("player_home/player_homes table is missing")
            required = {
                home_table: {"user_id", "background_id", "home_name", "weather", "temperature"},
                "player_home_houses": {"user_id", "slot_index", "item_id", "x", "y", "open_flag"},
                "type_home_bg": {"id", "name"},
                "type_houses": {"id", "name"},
            }
            for table, required_columns in required.items():
                cursor.execute(
                    "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
                    (self.mysql_config["database"], table),
                )
                found = {str(row["COLUMN_NAME"]) for row in cursor.fetchall()}
                missing = required_columns - found
                if missing:
                    raise RuntimeError(
                        f"{table} table is missing columns: {', '.join(sorted(missing))}"
                    )
        return home_table

    def close(self) -> None:
        self.connection.close()

    @staticmethod
    def _row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "user_id": int(row["user_id"]),
            "background_id": int(row.get("background_id") or 0),
            "background_name": "" if row.get("background_name") is None else str(row["background_name"]),
            "home_name": "" if row.get("home_name") is None else str(row["home_name"]),
            "weather": int(row.get("weather") or 0),
            "temperature": "" if row.get("temperature") is None else str(row["temperature"]),
            "item_id": None if row.get("item_id") is None else int(row["item_id"]),
            "house_name": "" if row.get("house_name") is None else str(row["house_name"]),
            "x": None if row.get("x") is None else int(row["x"]),
            "y": None if row.get("y") is None else int(row["y"]),
            "open_flag": None if row.get("open_flag") is None else int(bool(row["open_flag"])),
            "slot_index": None if row.get("slot_index") is None else int(row["slot_index"]),
        }

    def _select_sql(self) -> str:
        # The deployed schema uses slot_index=1 for the single house.
        return (
            f"SELECT ph.user_id, ph.background_id, bg.name AS background_name, "
            "ph.home_name, ph.weather, ph.temperature, "
            "hh.slot_index, hh.item_id, h.name AS house_name, hh.x, hh.y, hh.open_flag "
            f"FROM {self.home_table} ph "
            "LEFT JOIN type_home_bg bg ON bg.id=ph.background_id "
            "LEFT JOIN player_home_houses hh ON hh.user_id=ph.user_id AND hh.slot_index=1 "
            "LEFT JOIN type_houses h ON h.id=hh.item_id "
        )

    def list(self, *, user_id: int | None = None, page: int = 1, page_size: int = 10) -> dict[str, Any]:
        self._ensure_connection()
        page = max(1, int(page))
        if page_size not in ALLOWED_PAGE_SIZES:
            raise ValidationError("page_size must be one of 10, 50, or 100")
        with self.connection.cursor() as cursor:
            where = " WHERE ph.user_id=%s" if user_id is not None else ""
            params: tuple[Any, ...] = (user_id,) if user_id is not None else ()
            cursor.execute(f"SELECT COUNT(*) AS total FROM {self.home_table} ph{where}", params)
            total = int(cursor.fetchone()["total"])
            cursor.execute(
                self._select_sql() + f"{where} ORDER BY ph.user_id LIMIT %s OFFSET %s",
                params + (page_size, (page - 1) * page_size),
            )
            items = [self._row(row) for row in cursor.fetchall()]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def options(self, user_id: int | None = None) -> dict[str, list[dict[str, Any]]]:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT id, name FROM type_home_bg ORDER BY id")
            backgrounds = [{"id": int(row["id"]), "name": str(row["name"])} for row in cursor.fetchall()]
            if user_id is None:
                cursor.execute("SELECT id, name FROM type_houses ORDER BY id")
            else:
                cursor.execute(
                    "SELECT h.id, h.name FROM type_houses h INNER JOIN player_houses ph "
                    "ON ph.house_id=h.id WHERE ph.user_id=%s ORDER BY h.id", (user_id,)
                )
            houses = [{"id": int(row["id"]), "name": str(row["name"])} for row in cursor.fetchall()]
        return {"backgrounds": backgrounds, "houses": houses, "weather": list(WEATHER_VALUES)}

    def get(self, user_id: int) -> dict[str, Any] | None:
        result = self.list(user_id=user_id, page=1, page_size=10)
        return result["items"][0] if result["items"] else None

    def update(self, user_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(f"SELECT 1 FROM {self.home_table} WHERE user_id=%s LIMIT 1", (user_id,))
            if cursor.fetchone() is None:
                return None
            cursor.execute("SELECT 1 FROM type_home_bg WHERE id=%s LIMIT 1", (data["background_id"],))
            if cursor.fetchone() is None:
                raise ValidationError("background_id not found")
            cursor.execute("SELECT 1 FROM type_houses WHERE id=%s LIMIT 1", (data["item_id"],))
            if cursor.fetchone() is None:
                raise ValidationError("item_id not found")
            cursor.execute(
                f"UPDATE {self.home_table} SET background_id=%s, home_name=%s, weather=%s, temperature=%s "
                "WHERE user_id=%s",
                (data["background_id"], data["home_name"], data["weather"], data["temperature"], user_id),
            )
            cursor.execute(
                "UPDATE player_home_houses SET item_id=%s, x=%s, y=%s, open_flag=%s "
                "WHERE user_id=%s AND slot_index=1",
                (data["item_id"], data["x"], data["y"], data["open_flag"], user_id),
            )
        return self.get(user_id)
