"""Pet records used by the administration UI."""

from __future__ import annotations

from typing import Any

import pymysql

from admin.core.errors import ValidationError


PET_TYPES = {
    1500001: "智慧花宝",
    1500002: "美丽花宝",
    1500003: "爱心花宝",
    1500004: "古灵花宝",
    1500005: "勇气花宝",
}
PET_FIELDS = (
    "user_id", "pet_id", "age", "love_energy", "nickname", "hungry_index",
    "clean_index", "mood_index", "health_state", "is_vip", "wonderful_value", "rest_at",
)
UINT32_FIELDS = {"love_energy", "wonderful_value"}
RANGE_FIELDS = {"hungry_index": (0, 10000000), "clean_index": (0, 10000000), "mood_index": (0, 10000000)}


class PetRepository:
    def __init__(self, mysql_config: dict[str, Any]):
        self.mysql_config = dict(mysql_config)
        self.connection = pymysql.connect(**self.mysql_config, charset="utf8mb4", autocommit=True,
                                          cursorclass=pymysql.cursors.DictCursor)
        self._validate_schema()

    def _ensure_connection(self):
        self.connection.ping(reconnect=True)

    def _validate_schema(self):
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME='player_pets'", (self.mysql_config["database"],))
            found = {row["COLUMN_NAME"] for row in cursor.fetchall()}
        missing = (set(PET_FIELDS) | {"skills_json"}) - found
        if missing:
            raise RuntimeError(f"player_pets table is missing columns: {', '.join(sorted(missing))}")

    def close(self):
        self.connection.close()

    @staticmethod
    def _row(row):
        result = {}
        for field in PET_FIELDS:
            value = row.get(field)
            if field == "nickname":
                result[field] = "" if value is None else str(value)
            else:
                result[field] = int(value or 0)
        result["pet_name"] = PET_TYPES.get(result["pet_id"], str(result["pet_id"]))
        return result

    def list(self, *, page=1, page_size=20, user_id=None):
        self._ensure_connection()
        page = max(1, int(page)); page_size = min(100, max(1, int(page_size)))
        where = " WHERE user_id=%s" if user_id is not None else ""
        params = [user_id] if user_id is not None else []
        with self.connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) AS total FROM player_pets{where}", params)
            total = int(cursor.fetchone()["total"])
            cursor.execute(f"SELECT {', '.join(PET_FIELDS)} FROM player_pets{where} ORDER BY user_id DESC, pet_id LIMIT %s OFFSET %s", [*params, page_size, (page - 1) * page_size])
            items = [self._row(row) for row in cursor.fetchall()]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def get(self, user_id: int, pet_id: int):
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(f"SELECT {', '.join(PET_FIELDS)} FROM player_pets WHERE user_id=%s AND pet_id=%s LIMIT 1", (user_id, pet_id))
            row = cursor.fetchone()
        return self._row(row) if row else None

    @staticmethod
    def _integer(data, field):
        value = data.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, str)) or value == "":
            raise ValidationError(f"{field} must be an integer")
        try: return int(value)
        except (TypeError, ValueError) as exc: raise ValidationError(f"{field} must be an integer") from exc

    @classmethod
    def _values(cls, data: dict[str, Any], *, creating=False):
        allowed = set(PET_FIELDS) if creating else set(PET_FIELDS) - {"user_id"}
        unknown = set(data) - allowed
        if unknown: raise ValidationError(f"unsupported pet fields: {', '.join(sorted(unknown))}")
        if creating:
            missing = allowed - set(data)
            if missing: raise ValidationError(f"missing pet fields: {', '.join(sorted(missing))}")
        values = {}
        if creating:
            value = cls._integer(data, "user_id")
            if not 1 <= value <= 4294967295: raise ValidationError("user_id is out of range")
            values["user_id"] = value
        if "pet_id" in data:
            value = cls._integer(data, "pet_id")
            if value not in PET_TYPES: raise ValidationError("invalid pet_id")
            values["pet_id"] = value
        if "age" in data:
            value = cls._integer(data, "age")
            if not 0 <= value <= 4294967295: raise ValidationError("age must be an unsigned uint32")
            values["age"] = value
        if "nickname" in data:
            value = data["nickname"]
            if not isinstance(value, str) or not 2 <= len(value) <= 8: raise ValidationError("nickname must contain 2 to 8 characters")
            values["nickname"] = value
        for field in UINT32_FIELDS:
            if field in data:
                value = cls._integer(data, field)
                if not 0 <= value <= 4294967295: raise ValidationError(f"{field} must be an unsigned uint32")
                values[field] = value
        for field, (low, high) in RANGE_FIELDS.items():
            if field in data:
                value = cls._integer(data, field)
                if not low <= value <= high: raise ValidationError(f"{field} must be between {low} and {high}")
                values[field] = value
        for field, allowed in {"health_state": {0, 1}, "is_vip": {0, 1}, "rest_at": {0, 1, 2}}.items():
            if field in data:
                value = cls._integer(data, field)
                if value not in allowed: raise ValidationError(f"invalid {field}")
                values[field] = value
        if not values: raise ValidationError("at least one field must be changed")
        return values

    def create(self, data: dict[str, Any]):
        values = self._values(data, creating=True)
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM accounts WHERE user_id=%s LIMIT 1", (values["user_id"],))
            if cursor.fetchone() is None: raise LookupError("account not found")
            cursor.execute("SELECT 1 FROM player_pets WHERE user_id=%s LIMIT 1", (values["user_id"],))
            if cursor.fetchone() is not None:
                raise pymysql.err.IntegrityError(1062, "player already has a pet")
            cursor.execute(
                f"INSERT INTO player_pets ({', '.join(PET_FIELDS)}, skills_json) "
                f"VALUES ({', '.join(['%s'] * (len(PET_FIELDS) + 1))})",
                [*(values[field] for field in PET_FIELDS), "{}"],
            )
        return self.get(values["user_id"], values["pet_id"])

    def update(self, user_id: int, pet_id: int, data: dict[str, Any]):
        values = self._values(data)
        self._ensure_connection()
        assignments = ", ".join(f"{field}=%s" for field in values)
        with self.connection.cursor() as cursor:
            cursor.execute(f"UPDATE player_pets SET {assignments} WHERE user_id=%s AND pet_id=%s", [*values.values(), user_id, pet_id])
            if cursor.rowcount == 0 and self.get(user_id, pet_id) is None: return None
        return self.get(user_id, values.get("pet_id", pet_id))
