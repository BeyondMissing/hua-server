import time
from typing import Any

import pymysql

from admin.config import ACCOUNT_FIELDS, BOOL_FIELDS
from admin.core.errors import ValidationError
from admin.core.validation import validate_account


class AccountRepository:
    """Parameterised account queries against the existing accounts table."""

    INITIAL_CLOTH_IDS = (
        100004, 100007, 100008, 100009, 100010, 100011, 100012, 100013,
        100444, 100445, 100446, 100447, 100448, 100449, 100450, 100451,
        100452, 100453, 100454, 100455, 100456, 100457, 100458
    )

    def __init__(self, mysql_config: dict[str, Any]):
        self.mysql_config = dict(mysql_config)
        self.connection = self._connect()
        self.columns = self._load_columns()

        missing = set(ACCOUNT_FIELDS) - self.columns
        if missing:
            names = ", ".join(sorted(missing))
            raise RuntimeError(f"accounts table is missing columns: {names}")

    def _connect(self):
        return pymysql.connect(
            **self.mysql_config,
            charset="utf8mb4",
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def _ensure_connection(self) -> None:
        self.connection.ping(reconnect=True)

    def _load_columns(self) -> set[str]:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='accounts'",
                (self.mysql_config["database"],),
            )
            return {str(row["COLUMN_NAME"]) for row in cursor.fetchall()}

    def close(self) -> None:
        self.connection.close()

    @staticmethod
    def _row(row: dict[str, Any]) -> dict[str, Any]:
        result = {}
        for field in ACCOUNT_FIELDS:
            value = row.get(field)
            if field in BOOL_FIELDS:
                result[field] = int(bool(value))
            elif field == "user_id":
                result[field] = int(value)
            else:
                result[field] = "" if value is None else str(value)
        return result

    def list(self, search: str = "", page: int = 1, page_size: int = 20) -> dict[str, Any]:
        self._ensure_connection()
        page = max(1, int(page))
        page_size = min(100, max(1, int(page_size)))
        search = search.strip()

        where = ""
        params: list[Any] = []
        if search:
            where = " WHERE login_name LIKE %s OR CAST(user_id AS CHAR) LIKE %s"
            term = f"%{search}%"
            params.extend((term, term))

        with self.connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) AS total FROM accounts{where}", params)
            total = int(cursor.fetchone()["total"])
            cursor.execute(
                f"SELECT {', '.join(ACCOUNT_FIELDS)} FROM accounts{where} "
                "ORDER BY user_id DESC LIMIT %s OFFSET %s",
                [*params, page_size, (page - 1) * page_size],
            )
            rows = [self._row(row) for row in cursor.fetchall()]

        return {"items": rows, "total": total, "page": page, "page_size": page_size}

    def get(self, user_id: int) -> dict[str, Any] | None:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {', '.join(ACCOUNT_FIELDS)} FROM accounts WHERE user_id=%s",
                (user_id,),
            )
            row = cursor.fetchone()
        return self._row(row) if row else None

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        self._ensure_connection()
        values = validate_account(data, creating=True)
        fields = list(ACCOUNT_FIELDS)
        placeholders = ", ".join(["%s"] * len(fields))
        sql = f"INSERT INTO accounts ({', '.join(fields)}) VALUES ({placeholders})"
        user_id = values["user_id"]
        login_name = values["login_name"]
        now = int(time.time())

        # Account creation initializes the records required by the game in one
        # transaction so a failed related insert cannot leave a partial account.
        self.connection.begin()
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, [values[field] for field in fields])
                cursor.execute(
                    "INSERT INTO player_profiles "
                    "(user_id, nickname, map_id, map_x, map_y, new_user_job, "
                    "login_time, reg_time, money) "
                    "VALUES (%s, %s, 1, 400, 400, 11, %s, %s, 500)",
                    (user_id, login_name, now, now),
                )
                cursor.execute(
                    "INSERT INTO player_homes (user_id, home_name, weather, temperature) "
                    "VALUES (%s, %s, 6, %s)",
                    (user_id, login_name, "晴天23℃~30℃"),
                )
                cursor.executemany(
                    "INSERT INTO player_clothes (user_id, cloth_id) VALUES (%s, %s)",
                    [(user_id, cloth_id) for cloth_id in self.INITIAL_CLOTH_IDS],
                )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        return self.get(values["user_id"])

    def update(self, user_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        self._ensure_connection()
        values = validate_account(data, creating=False)
        assignments = []
        params: list[Any] = []
        for field, value in values.items():
            if field == "user_id":
                continue
            assignments.append(f"{field}=%s")
            params.append(value)

        if not assignments:
            raise ValidationError("at least one field must be changed")

        params.append(user_id)
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE accounts SET {', '.join(assignments)} WHERE user_id=%s",
                params,
            )
            if cursor.rowcount == 0:
                return None
        return self.get(user_id)

    def delete(self, user_id: int) -> bool:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute("DELETE FROM accounts WHERE user_id=%s", (user_id,))
            return cursor.rowcount == 1
