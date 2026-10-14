"""Task catalog and player task-progress administration queries."""

from __future__ import annotations

import re
import time
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pymysql


class TaskRepository:
    def __init__(self, mysql_config: dict[str, Any]):
        self.mysql_config = dict(mysql_config)
        self.connection = self._connect()
        self.columns = self._load_columns("task_available")
        required = {"main_id", "name", "start_npc_name"}
        missing = required - set(self.columns)
        if missing:
            raise RuntimeError(f"task_available table is missing columns: {', '.join(sorted(missing))}")

    def _connect(self):
        return pymysql.connect(**self.mysql_config, charset="utf8mb4", autocommit=True,
                               cursorclass=pymysql.cursors.DictCursor)

    def _ensure_connection(self) -> None:
        self.connection.ping(reconnect=True)

    def _load_columns(self, table: str) -> list[str]:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION",
                (self.mysql_config["database"], table),
            )
            return [str(row["COLUMN_NAME"]) for row in cursor.fetchall()]

    def close(self) -> None:
        self.connection.close()

    @staticmethod
    def _json_value(value: Any) -> Any:
        if isinstance(value, (datetime, date)):
            return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value

    def list(self, user_id: int) -> dict[str, Any]:
        self._ensure_connection()
        columns_sql = ", ".join(f"ta.`{column}`" for column in self.columns)
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {columns_sql}, p.step AS progress_step, p.process AS progress_process, "
                "p.total_process AS progress_total "
                "FROM task_available ta "
                "LEFT JOIN player_task_progress p ON p.user_id=%s AND p.job_id=ta.main_id "
                "ORDER BY ta.main_id",
                (int(user_id),),
            )
            rows = []
            for row in cursor.fetchall():
                item = {column: self._json_value(row.get(column)) for column in self.columns}
                item.update({
                    "step": row.get("progress_step") if row.get("progress_step") is not None else None,
                    "process": row.get("progress_process") if row.get("progress_process") is not None else None,
                    "total_process": row.get("progress_total") if row.get("progress_total") is not None else None,
                })
                rows.append(item)
        return {"columns": self.columns, "items": rows}

    def reset(self, user_id: int, job_id: int) -> dict[str, Any]:
        self._ensure_connection()
        user_id, job_id = int(user_id), int(job_id)
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM task_available WHERE main_id=%s LIMIT 1", (job_id,))
            if cursor.fetchone() is None:
                raise LookupError("task not found")
            cursor.execute("SELECT got_item FROM task_list WHERE main_id=%s", (job_id,))
            values = [row.get("got_item") for row in cursor.fetchall()]
            item_ids = sorted({int(match) for value in values for match in re.findall(r"11\d{5}", str(value or ""))})

            self.connection.begin()
            try:
                cursor.execute("DELETE FROM player_completed_tasks WHERE user_id=%s AND job_id=%s", (user_id, job_id))
                cursor.execute("DELETE FROM player_task_progress WHERE user_id=%s AND job_id=%s", (user_id, job_id))
                if item_ids:
                    placeholders = ",".join(["%s"] * len(item_ids))
                    cursor.execute(
                        f"DELETE FROM player_task_items WHERE user_id=%s AND item_id IN ({placeholders})",
                        (user_id, *item_ids),
                    )
                cursor.execute(
                    "INSERT INTO player_task_progress "
                    "(user_id, job_id, step, flag, process, total_process, get_time) "
                    "VALUES (%s, %s, 1, 0, 0, 0, %s)",
                    (user_id, job_id, int(time.time())),
                )
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise
        return {"user_id": user_id, "job_id": job_id, "step": 1}
