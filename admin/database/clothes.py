from datetime import datetime
from typing import Any

import pymysql

from admin.core.errors import ValidationError


ALLOWED_PAGE_SIZES = (10, 50, 100)


class ClothesRepository:
    """Queries the fixed clothes catalog and player ownership records."""

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
            "type_clothes": {"id", "name", "sex", "cloth_type"},
            "player_clothes": {"user_id", "cloth_id", "acquired_at"},
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

    def _account_exists(self, cursor, user_id: int) -> bool:
        cursor.execute("SELECT 1 FROM accounts WHERE user_id=%s LIMIT 1", (user_id,))
        return cursor.fetchone() is not None

    @staticmethod
    def _row(row: dict[str, Any]) -> dict[str, Any]:
        acquired_at = row.get("acquired_at")
        return {
            "id": int(row["id"]),
            "name": "" if row.get("name") is None else str(row["name"]),
            "sex": int(row.get("sex") or 0),
            "cloth_type": int(row["cloth_type"]),
            "acquired": acquired_at is not None,
            "acquired_at": acquired_at.isoformat(sep=" ") if acquired_at else None,
        }

    def list(
        self,
        user_id: int,
        *,
        name: str = "",
        sex: int | None = None,
        cloth_type: int | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> dict[str, Any] | None:
        self._ensure_connection()
        page = max(1, int(page))
        if page_size not in ALLOWED_PAGE_SIZES:
            raise ValidationError("page_size must be one of 10, 50, or 100")

        conditions: list[str] = []
        filter_params: list[Any] = []
        name = name.strip()
        if name:
            conditions.append("tc.name LIKE %s")
            filter_params.append(f"%{name}%")
        if sex is not None:
            conditions.append("COALESCE(tc.sex, 0)=%s")
            filter_params.append(sex)
        if cloth_type is not None:
            conditions.append("tc.cloth_type=%s")
            filter_params.append(cloth_type)

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        join = (
            " FROM type_clothes tc LEFT JOIN player_clothes pc "
            "ON pc.cloth_id=tc.id AND pc.user_id=%s"
        )
        with self.connection.cursor() as cursor:
            if not self._account_exists(cursor, user_id):
                return None
            cursor.execute(f"SELECT COUNT(*) AS total{join}{where}", [user_id, *filter_params])
            total = int(cursor.fetchone()["total"])
            cursor.execute(
                "SELECT tc.id, tc.name, tc.sex, tc.cloth_type, pc.acquired_at"
                f"{join}{where} ORDER BY tc.id LIMIT %s OFFSET %s",
                [user_id, *filter_params, page_size, (page - 1) * page_size],
            )
            items = [self._row(row) for row in cursor.fetchall()]

        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def acquire(self, user_id: int, cloth_id: int, acquired_at: datetime) -> dict[str, Any]:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            if not self._account_exists(cursor, user_id):
                raise LookupError("account not found")
            cursor.execute("SELECT 1 FROM type_clothes WHERE id=%s LIMIT 1", (cloth_id,))
            if cursor.fetchone() is None:
                raise LookupError("clothing not found")
            cursor.execute(
                "INSERT INTO player_clothes (user_id, cloth_id, acquired_at) VALUES (%s, %s, %s)",
                (user_id, cloth_id, acquired_at),
            )
        return {
            "user_id": user_id,
            "cloth_id": cloth_id,
            "acquired_at": acquired_at.isoformat(sep=" "),
        }

    def discard(self, user_id: int, cloth_id: int) -> bool:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM player_clothes WHERE user_id=%s AND cloth_id=%s",
                (user_id, cloth_id),
            )
            return cursor.rowcount == 1
