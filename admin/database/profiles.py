"""Player profile and equipped-clothing queries for the admin application."""

from __future__ import annotations

import json
from typing import Any

import pymysql

from admin.core.errors import ValidationError
from admin.web.consts import BIRTHDAYS, CLOTHING_SLOT_BY_TYPE, NATIONALITIES


PROFILE_FIELDS = (
    "user_id", "nickname", "nationality", "reg_time", "login_last",
    "birthday", "love", "beautiful", "wisdom", "plant_grade", "faerie_grade",
    "money", "face_color", "face", "eye", "eyebrow", "lip",
)
EDITABLE_FIELDS = PROFILE_FIELDS[1:3] + PROFILE_FIELDS[5:]
ICON_FIELDS = {"face": 105, "eye": 103, "eyebrow": 102, "lip": 104}
NON_NEGATIVE_FIELDS = {"love", "beautiful", "wisdom", "money"}
POSITIVE_FIELDS = {"plant_grade", "faerie_grade"}


class ProfileRepository:
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
            "player_profiles": {"user_id", *PROFILE_FIELDS[1:], "clothing_json"},
            "player_clothes": {"user_id", "cloth_id"},
            "type_clothes": {"id", "name", "cloth_type"},
            "type_skin_colors": {"id", "name"},
            "type_cloth_icons": {"id", "name", "cloth_type"},
        }
        self._ensure_connection()
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
                    raise RuntimeError(
                        f"{table} table is missing columns: {', '.join(sorted(missing))}"
                    )

    def close(self) -> None:
        self.connection.close()

    @staticmethod
    def _row(row: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for field in PROFILE_FIELDS:
            value = row.get(field)
            if field == "nickname":
                result[field] = "" if value is None else str(value)
            else:
                result[field] = int(value or 0)
        raw = row.get("clothing_json")
        try:
            clothing = json.loads(raw) if raw else {}
            result["clothing"] = clothing if isinstance(clothing, dict) else {}
        except (TypeError, ValueError):
            result["clothing"] = {}
        return result

    def list(
        self,
        *,
        user_id: int | None = None,
        nickname: str = "",
        nationality: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        self._ensure_connection()
        page = max(1, int(page))
        page_size = min(100, max(1, int(page_size)))
        conditions: list[str] = []
        params: list[Any] = []
        if user_id is not None:
            conditions.append("user_id=%s")
            params.append(user_id)
        if nickname.strip():
            conditions.append("nickname LIKE %s")
            params.append(f"%{nickname.strip()}%")
        if nationality is not None:
            conditions.append("nationality=%s")
            params.append(nationality)
        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        fields = ", ".join(PROFILE_FIELDS[:5])
        with self.connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) AS total FROM player_profiles{where}", params)
            total = int(cursor.fetchone()["total"])
            cursor.execute(
                f"SELECT {fields} FROM player_profiles{where} "
                "ORDER BY user_id DESC LIMIT %s OFFSET %s",
                [*params, page_size, (page - 1) * page_size],
            )
            items = [self._row(row) for row in cursor.fetchall()]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def get(self, user_id: int) -> dict[str, Any] | None:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {', '.join(PROFILE_FIELDS)}, clothing_json "
                "FROM player_profiles WHERE user_id=%s LIMIT 1",
                (user_id,),
            )
            row = cursor.fetchone()
        return self._row(row) if row else None

    @staticmethod
    def _int_value(data: dict[str, Any], field: str) -> int:
        value = data.get(field)
        if isinstance(value, bool) or value in (None, ""):
            raise ValidationError(f"{field} must be an integer")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{field} must be an integer") from exc

    def _validate_values(self, data: dict[str, Any]) -> dict[str, Any]:
        unknown = set(data) - set(EDITABLE_FIELDS)
        if unknown:
            raise ValidationError(f"unsupported profile fields: {', '.join(sorted(unknown))}")
        result: dict[str, Any] = {}
        if "nickname" in data:
            nickname = data["nickname"]
            if not isinstance(nickname, str) or not 2 <= len(nickname) <= 8:
                raise ValidationError("nickname must contain 2 to 8 characters")
            result["nickname"] = nickname
        if "nationality" in data:
            value = self._int_value(data, "nationality")
            if value not in NATIONALITIES:
                raise ValidationError("invalid nationality")
            result["nationality"] = value
        if "birthday" in data:
            value = self._int_value(data, "birthday")
            if value not in BIRTHDAYS:
                raise ValidationError("invalid birthday")
            result["birthday"] = value
        for field in NON_NEGATIVE_FIELDS | POSITIVE_FIELDS:
            if field not in data:
                continue
            value = self._int_value(data, field)
            if field in NON_NEGATIVE_FIELDS and value < 0:
                raise ValidationError(f"{field} must be at least 0")
            if field in POSITIVE_FIELDS and value < 1:
                raise ValidationError(f"{field} must be at least 1")
            result[field] = value

        icon_checks = {field: data[field] for field in ICON_FIELDS if field in data}
        face_color = self._int_value(data, "face_color") if "face_color" in data else None
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            if face_color is not None:
                if face_color < 0:
                    raise ValidationError("face_color must be at least 0")
                cursor.execute("SELECT 1 FROM type_skin_colors WHERE id=%s LIMIT 1", (face_color,))
                if cursor.fetchone() is None:
                    raise ValidationError("invalid face_color")
                result["face_color"] = face_color
            for field, value in icon_checks.items():
                icon_id = self._int_value(data, field)
                if icon_id == 0:
                    result[field] = 0
                    continue
                cursor.execute(
                    "SELECT 1 FROM type_cloth_icons WHERE id=%s AND cloth_type=%s LIMIT 1",
                    (icon_id, ICON_FIELDS[field]),
                )
                if cursor.fetchone() is None:
                    raise ValidationError(f"invalid {field}")
                result[field] = icon_id
        return result

    def update(self, user_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        values = self._validate_values(data)
        if not values:
            raise ValidationError("at least one field must be changed")
        self._ensure_connection()
        assignments = ", ".join(f"{field}=%s" for field in values)
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE player_profiles SET {assignments} WHERE user_id=%s",
                [*values.values(), user_id],
            )
            if cursor.rowcount == 0:
                cursor.execute("SELECT 1 FROM player_profiles WHERE user_id=%s", (user_id,))
                if cursor.fetchone() is None:
                    return None
        return self.get(user_id)

    def options(self, user_id: int) -> dict[str, Any] | None:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM player_profiles WHERE user_id=%s LIMIT 1", (user_id,))
            if cursor.fetchone() is None:
                return None
            cursor.execute("SELECT id, name FROM type_skin_colors ORDER BY id")
            colors = [{"id": int(row["id"]), "name": str(row["name"])} for row in cursor.fetchall()]
            cursor.execute(
                "SELECT id, name, cloth_type FROM type_cloth_icons "
                "WHERE cloth_type IN (102,103,104,105) ORDER BY cloth_type, id"
            )
            icons = [
                {"id": int(row["id"]), "name": str(row["name"]), "cloth_type": int(row["cloth_type"])}
                for row in cursor.fetchall()
            ]
            cursor.execute(
                "SELECT pc.cloth_id AS id, tc.name, tc.cloth_type "
                "FROM player_clothes pc JOIN type_clothes tc ON tc.id=pc.cloth_id "
                "WHERE pc.user_id=%s ORDER BY tc.cloth_type, tc.id",
                (user_id,),
            )
            clothes = [
                {"id": int(row["id"]), "name": str(row["name"]), "cloth_type": int(row["cloth_type"])}
                for row in cursor.fetchall()
            ]
            owned_ids = {item["id"] for item in clothes}
            cursor.execute("SELECT clothing_json FROM player_profiles WHERE user_id=%s LIMIT 1", (user_id,))
            profile_row = cursor.fetchone() or {}
            try:
                current = json.loads(profile_row.get("clothing_json") or "{}")
            except (TypeError, ValueError):
                current = {}
            current_ids = {
                int(value) for value in current.values()
                if isinstance(value, int) and value > 0
            }
            missing_ids = current_ids - owned_ids
            if missing_ids:
                placeholders = ",".join(["%s"] * len(missing_ids))
                cursor.execute(
                    f"SELECT id, name, cloth_type FROM type_clothes WHERE id IN ({placeholders})",
                    list(missing_ids),
                )
                clothes.extend(
                    {"id": int(row["id"]), "name": str(row["name"]), "cloth_type": int(row["cloth_type"])}
                    for row in cursor.fetchall()
                )
                clothes.sort(key=lambda item: (item["cloth_type"], item["id"]))
        return {
            "nationalities": [{"id": k, "name": v} for k, v in NATIONALITIES.items()],
            "birthdays": [{"id": k, "name": v} for k, v in BIRTHDAYS.items()],
            "face_colors": colors,
            "icons": icons,
            "clothes": clothes,
            "slots": [{"cloth_type": k, "name": v} for k, v in CLOTHING_SLOT_BY_TYPE.items() if k < 100],
        }

    def update_clothing(self, user_id: int, clothing: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(clothing, dict):
            raise ValidationError("clothing must be an object")
        slot_names = {name for kind, name in CLOTHING_SLOT_BY_TYPE.items() if kind < 100}
        unknown = set(clothing) - slot_names
        if unknown:
            raise ValidationError(f"unsupported clothing slots: {', '.join(sorted(unknown))}")
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT clothing_json FROM player_profiles WHERE user_id=%s LIMIT 1", (user_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            try:
                current = json.loads(row.get("clothing_json") or "{}")
            except (TypeError, ValueError) as exc:
                raise ValidationError("invalid clothing_json") from exc
            if not isinstance(current, dict):
                raise ValidationError("invalid clothing_json")
            for slot, raw_id in clothing.items():
                if isinstance(raw_id, bool) or raw_id in (None, ""):
                    raise ValidationError(f"{slot} must be an integer")
                try:
                    cloth_id = int(raw_id)
                except (TypeError, ValueError) as exc:
                    raise ValidationError(f"{slot} must be an integer") from exc
                if cloth_id < 0:
                    raise ValidationError(f"{slot} must be at least 0")
                if cloth_id:
                    cloth_type = next(k for k, name in CLOTHING_SLOT_BY_TYPE.items() if name == slot)
                    cursor.execute(
                        "SELECT 1 FROM player_clothes pc JOIN type_clothes tc ON tc.id=pc.cloth_id "
                        "WHERE pc.user_id=%s AND pc.cloth_id=%s AND tc.cloth_type=%s LIMIT 1",
                        (user_id, cloth_id, cloth_type),
                    )
                    if cursor.fetchone() is None and int(current.get(slot, 0) or 0) != cloth_id:
                        raise ValidationError(f"{slot} clothing is not owned by this player")
                current[slot] = cloth_id
            cursor.execute(
                "UPDATE player_profiles SET clothing_json=%s WHERE user_id=%s",
                (json.dumps(current, ensure_ascii=False, separators=(",", ":")), user_id),
            )
        return self.get(user_id)
