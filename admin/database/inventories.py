"""Repositories for player flowers, seeds, and materials."""

from __future__ import annotations

from typing import Any

import pymysql


INVENTORY_DEFINITIONS = {
    "flowers": ("player_flowers", "type_flowers", "item_id"),
    "seeds": ("player_seeds", "type_seeds", "item_id"),
    "materials": ("player_materials", "type_materials", "item_id"),
    "pet-supplies": ("player_pet_supplies", "type_pet_supplies", "item_id"),
    "tools": ("player_home_props", "type_home_props", "item_id"),
    "pollens": ("player_pollens", "type_pollens", "pollen_id"),
}


class InventoryRepository:
    def __init__(self, mysql_config: dict[str, Any], kind: str):
        if kind not in INVENTORY_DEFINITIONS:
            raise ValueError(f"unsupported inventory kind: {kind}")
        self.kind = kind
        self.player_table, self.type_table, self.item_column = INVENTORY_DEFINITIONS[kind]
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
        catalog_columns = {"id", "name"}
        if self.kind == "pet-supplies":
            catalog_columns.update({"grade", "hungry", "sanitary", "spirit"})
        required = {
            self.player_table: {"user_id", self.item_column, "amount"},
            self.type_table: catalog_columns,
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

    def _row(self, row: dict[str, Any]) -> dict[str, Any]:
        result = {
            "user_id": int(row["user_id"]),
            "item_id": int(row["item_id"]),
            "name": "" if row.get("name") is None else str(row["name"]),
            "amount": int(row["amount"]),
        }
        if self.kind == "pet-supplies":
            result.update({
                "grade": "" if row.get("grade") is None else str(row["grade"]),
                "hungry": row.get("hungry"),
                "sanitary": row.get("sanitary"),
                "spirit": row.get("spirit"),
            })
        return result

    @staticmethod
    def _account_exists(cursor, user_id: int) -> bool:
        cursor.execute("SELECT 1 FROM accounts WHERE user_id=%s LIMIT 1", (user_id,))
        return cursor.fetchone() is not None

    def list(
        self,
        user_id: int,
        *,
        name: str = "",
        page: int = 1,
        page_size: int | None = 10,
    ) -> dict[str, Any] | None:
        self._ensure_connection()
        name = name.strip()
        conditions = ["p.user_id=%s"]
        filter_params: list[Any] = [user_id]
        if name:
            conditions.append("t.name LIKE %s")
            filter_params.append(f"%{name}%")
        where = " AND ".join(conditions)
        with self.connection.cursor() as cursor:
            if not self._account_exists(cursor, user_id):
                return None
            cursor.execute(
                f"SELECT COUNT(*) AS total FROM {self.player_table} p "
                f"LEFT JOIN {self.type_table} t ON t.id=p.{self.item_column} WHERE {where}",
                filter_params,
            )
            total = int(cursor.fetchone()["total"])
            metadata = ", t.grade, t.hungry, t.sanitary, t.spirit" if self.kind == "pet-supplies" else ""
            sql = (
                f"SELECT p.user_id, p.{self.item_column} AS item_id, t.name, p.amount{metadata} "
                f"FROM {self.player_table} p LEFT JOIN {self.type_table} t ON t.id=p.{self.item_column} "
                f"WHERE {where} ORDER BY p.{self.item_column}"
            )
            params = list(filter_params)
            if page_size is not None:
                sql += " LIMIT %s OFFSET %s"
                params.extend((page_size, (page - 1) * page_size))
            cursor.execute(sql, params)
            items = [self._row(row) for row in cursor.fetchall()]
        if page_size is None:
            return {"items": items, "total": total}
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def options(self) -> list[dict[str, Any]]:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            extra = ", grade, hungry, sanitary, spirit" if self.kind == "pet-supplies" else ""
            cursor.execute(f"SELECT id, name{extra} FROM {self.type_table} ORDER BY id")
            return [
                ({
                    "id": int(row["id"]),
                    "name": "" if row.get("name") is None else str(row["name"]),
                } | ({
                    "grade": "" if row.get("grade") is None else str(row["grade"]),
                    "hungry": row.get("hungry"),
                    "sanitary": row.get("sanitary"),
                    "spirit": row.get("spirit"),
                } if self.kind == "pet-supplies" else {}))
                for row in cursor.fetchall()
            ]

    def create(self, user_id: int, item_id: int, amount: int) -> dict[str, Any]:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            if not self._account_exists(cursor, user_id):
                raise LookupError("account not found")
            cursor.execute(f"SELECT 1 FROM {self.type_table} WHERE id=%s LIMIT 1", (item_id,))
            if cursor.fetchone() is None:
                raise LookupError("item not found")
            cursor.execute(
                f"INSERT INTO {self.player_table} (user_id, {self.item_column}, amount) "
                f"VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE amount=amount+VALUES(amount)",
                (user_id, item_id, amount),
            )
        return self.get(user_id, item_id)

    def get(self, user_id: int, item_id: int) -> dict[str, Any] | None:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"SELECT p.user_id, p.{self.item_column} AS item_id, t.name, p.amount"
                f"{', t.grade, t.hungry, t.sanitary, t.spirit' if self.kind == 'pet-supplies' else ''} "
                f"FROM {self.player_table} p "
                f"LEFT JOIN {self.type_table} t ON t.id=p.{self.item_column} "
                f"WHERE p.user_id=%s AND p.{self.item_column}=%s LIMIT 1",
                (user_id, item_id),
            )
            row = cursor.fetchone()
        return self._row(row) if row else None

    def update(self, user_id: int, item_id: int, amount: int) -> dict[str, Any] | None:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE {self.player_table} SET amount=%s WHERE user_id=%s AND {self.item_column}=%s",
                (amount, user_id, item_id),
            )
            if cursor.rowcount == 0:
                cursor.execute(
                    f"SELECT 1 FROM {self.player_table} WHERE user_id=%s AND {self.item_column}=%s LIMIT 1",
                    (user_id, item_id),
                )
                if cursor.fetchone() is None:
                    return None
        return self.get(user_id, item_id)
