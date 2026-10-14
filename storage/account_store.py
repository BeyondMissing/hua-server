import json
import pymysql
import time

from typing import Dict, Optional
from entity.account import Account
from constant.consts import (
    CLOTHING_SLOT_BY_TYPE,
    FRIEND_STATUS_PENDING,
    FRIEND_STATUS_FRIEND,
    FRIEND_STATUS_INTIMATE,
    FRIEND_STATUS_BLACKLIST,
)
from exception.suiting_error import SuitingError
from exception.clothing_change_error import ClothingChangeError
from storage.cloth_type_store import ClothTypeStore
from storage.npc_store import fetch_npcs, fetch_npc_jobs
from storage.puppet_store import fetch_puppet
from storage.synthetic_game_store import SyntheticGameStore


class AccountStore:
    """Manage a connection to the existing MySQL ``hua.accounts`` table.

    Social DDL is applied idempotently at startup. Expected account columns
    include user_id, login_name, password_hash, role_created, banned, and
    enable_friends_application.
    """
    def __init__(self, host: str, port, user, password, database):
        self._connect_kwargs = dict(host=host, port=port, user=user, password=password, database=database)
        self.connection = pymysql.connect(**self._connect_kwargs, charset="utf8mb4", autocommit=True,
                                          cursorclass=pymysql.cursors.DictCursor)
        self.cloth_types = ClothTypeStore.load(self.connection)
        self.synthetic_games = SyntheticGameStore(self)

    def pet_rows(self, user_id: int, rest_at: int | None = None):
        """Return a player's pets, optionally limited to one rest location."""
        self._ensure_connection()
        sql = "SELECT * FROM player_pets WHERE user_id=%s"
        params = [int(user_id)]
        if rest_at is not None:
            sql += " AND rest_at=%s"
            params.append(int(rest_at))
        sql += " ORDER BY pet_id"
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            return list(cursor.fetchall() or [])


    def pet_letter_tasks(self, user_id: int, pet_id: int = 0):
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT task_id, step, status, process, letter_time, total_process "
                "FROM player_pet_letters WHERE user_id=%s AND (pet_id=0 OR pet_id=%s) "
                "ORDER BY letter_time, id",
                (int(user_id), int(pet_id)),
            )
            return list(cursor.fetchall() or [])

    def pet_letter_replies(self, user_id: int, pet_id: int, mail_type: int):
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT mail_id, send_time, state, reply_time "
                "FROM player_pet_replies WHERE user_id=%s AND (pet_id=0 OR pet_id=%s) "
                "AND mail_type=%s ORDER BY send_time, id",
                (int(user_id), int(pet_id), int(mail_type)),
            )
            return list(cursor.fetchall() or [])

    def pet_reply_content(self, user_id: int, pet_id: int, send_time: int):
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT reply_time, content FROM player_pet_replies "
                "WHERE user_id=%s AND pet_id=%s AND send_time=%s "
                "AND mail_type=3 AND reply_time>0 ORDER BY id DESC LIMIT 1",
                (int(user_id), int(pet_id), int(send_time)),
            )
            return cursor.fetchone()

    def mark_pet_letter_read(self, user_id: int, pet_id: int, send_time: int):
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE player_pet_replies SET state=1 WHERE user_id=%s AND pet_id=%s "
                "AND send_time=%s AND mail_type IN (1,2)",
                (int(user_id), int(pet_id), int(send_time)),
            )

    def reply_pet_letter(self, user_id: int, pet_id: int, send_time: int, content: str, reply_time: int):
        self._ensure_connection()
        user_id, pet_id, send_time, reply_time = map(int, (user_id, pet_id, send_time, reply_time))
        connection = self.connection
        try:
            connection.begin()
            with connection.cursor() as cursor:
                cursor.execute(
                "SELECT mail_id, mail_type, send_time FROM player_pet_replies "
                "WHERE user_id=%s AND pet_id=%s AND send_time=%s AND mail_type IN (1,2) "
                "ORDER BY id LIMIT 1 FOR UPDATE",
                (user_id, pet_id, send_time),
                )
                original = cursor.fetchone()
                if not original:
                    connection.rollback()
                    return False
                cursor.execute(
                "INSERT INTO player_pet_replies "
                "(user_id, pet_id, mail_id, mail_type, send_time, state, reply_time, content) "
                "VALUES (%s,%s,%s,3,%s,0,%s,%s)",
                (user_id, pet_id, int(original["mail_id"]), send_time, reply_time, content),
                )
                cursor.execute(
                "UPDATE player_pet_replies SET state=2 WHERE user_id=%s AND pet_id=%s "
                "AND send_time=%s AND mail_type IN (1,2)",
                (user_id, pet_id, send_time),
                )
                cursor.execute(
                    "UPDATE player_pets SET love_energy=COALESCE(love_energy,0)+10 "
                    "WHERE user_id=%s AND pet_id=%s", (user_id, pet_id)
                )
            connection.commit()
            return True
        except Exception:
            connection.rollback()
            raise

    def rename_pet(self, user_id: int, pet_id: int, nickname: str):
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE player_pets SET nickname=%s WHERE user_id=%s AND pet_id=%s",
                (nickname, int(user_id), int(pet_id)),
            )
            return cursor.rowcount

    def rename_player(self, user_id: int, nickname: str) -> int:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE player_profiles SET nickname=%s WHERE user_id=%s",
                (nickname, int(user_id)),
            )
            return cursor.rowcount

    def set_new_user_job(self, user_id: int, new_user_job: int) -> int:
        """Persist the SET_NEWUSERJOB (1040) tutorial progress value."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE player_profiles SET new_user_job=%s WHERE user_id=%s",
                (int(new_user_job) & 0xFFFFFFFF, int(user_id)),
            )
            return cursor.rowcount

    def set_medal_show_flag(self, user_id: int, medal_id: int, show_flag: int) -> int:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE player_medals SET show_flag=%s WHERE user_id=%s AND medal_id=%s",
                (int(show_flag), int(user_id), int(medal_id)),
            )
            return cursor.rowcount

    def set_pet_follow(self, user_id: int, pet_id: int) -> int:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE player_pets SET rest_at=0 WHERE user_id=%s AND pet_id=%s",
                (int(user_id), int(pet_id)),
            )
            return cursor.rowcount

    def put_pet_back(self, user_id: int, pet_id: int, rest_at: int) -> int:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE player_pets SET rest_at=%s WHERE user_id=%s AND pet_id=%s",
                (int(rest_at), int(user_id), int(pet_id)),
            )
            return cursor.rowcount

    def delete_pet_letters(self, user_id: int, pet_id: int, send_times):
        self._ensure_connection()
        values = [int(value) for value in send_times]
        if not values:
            return 0
        placeholders = ",".join(["%s"] * len(values))
        with self.connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM player_pet_replies WHERE user_id=%s AND pet_id=%s "
                "AND mail_type IN (1,2) AND send_time IN (" + placeholders + ")",
                (int(user_id), int(pet_id), *values),
            )
            return cursor.rowcount


    def pet_info(self, user_id: int, pet_id: int):
        """Return one player's pet record for PET_BASE_INFO (1044)."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM player_pets WHERE user_id=%s AND pet_id=%s LIMIT 1",
                (int(user_id), int(pet_id)),
            )
            return cursor.fetchone()

    def house_goods(self, user_id: int):
        """Return a user's placed furniture in HOUSE_INFO field order."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, item_id, no, x, y, m, z
                FROM player_house_goods
                WHERE user_id=%s AND is_set=1
                ORDER BY no
                """,
                (int(user_id),),
            )
            return list(cursor.fetchall() or [])

    def house_depot_items(self, user_id: int):
        """Aggregate a player's unplaced furniture for HOUSE_DEPOT (10104)."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT item_id, COUNT(*) AS amount
                FROM player_house_goods
                WHERE user_id=%s AND is_set=0
                GROUP BY item_id
                ORDER BY item_id
                """,
                (int(user_id),),
            )
            return list(cursor.fetchall() or [])

    def add_house_good(self, user_id: int, item_id: int, x: int, y: int, m: int, z: int):
        """Take one unplaced inventory row, place it, and return its NO."""
        self._ensure_connection()
        user_id = int(user_id)
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT no
                FROM player_house_goods
                WHERE user_id=%s AND item_id=%s AND is_set=0
                ORDER BY no
                LIMIT 1
                """,
                (user_id, int(item_id)),
            )
            row = cursor.fetchone()
            if not row:
                return None
            no = int(row["no"])
            cursor.execute(
                """
                UPDATE player_house_goods
                SET x=%s, y=%s, m=%s, z=%s, is_set=1
                WHERE user_id=%s AND no=%s AND is_set=0
                """,
                (int(x), int(y), int(m), int(z), user_id, no),
            )
        return no

    def remove_house_good(self, user_id: int, no: int):
        """Move one placed furniture row back to the depot."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT item_id FROM player_house_goods "
                "WHERE user_id=%s AND no=%s AND is_set=1 LIMIT 1",
                (int(user_id), int(no)),
            )
            row = cursor.fetchone()
            if not row:
                return None
            cursor.execute(
                "UPDATE player_house_goods SET is_set=0 "
                "WHERE user_id=%s AND no=%s",
                (int(user_id), int(no)),
            )
            return int(row["item_id"])

    def update_house_goods(self, user_id: int, house_id: int, goods: list[dict]):
        """Persist changed furniture positions from HOUSE_UPDATE (10105)."""
        self._ensure_connection()
        user_id = int(user_id)
        with self.connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO player_house_goods
                    (user_id, item_id, no, x, y, m, z, is_set)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
                ON DUPLICATE KEY UPDATE
                    item_id=VALUES(item_id),
                    x=VALUES(x),
                    y=VALUES(y),
                    m=VALUES(m),
                    z=VALUES(z),
                    is_set=1
                """,
                [
                    (
                        user_id,
                        int(good["item_id"]),
                        int(good["no"]),
                        int(good["x"]),
                        int(good["y"]),
                        int(good["m"]),
                        int(good["z"]),
                    )
                    for good in goods
                ],
            )

    def add_task_item(self, user_id: int, item_id: int) -> None:
        """Increment one task-item inventory row for PICK_UP_JOB (1028)."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE player_task_items SET amount=amount+1 "
                "WHERE user_id=%s AND item_id=%s",
                (int(user_id), int(item_id)),
            )
            if cursor.rowcount:
                return
            cursor.execute(
                "SELECT COALESCE(`Type`, 1) AS item_type FROM task_items WHERE ID=%s",
                (int(item_id),),
            )
            row = cursor.fetchone()
            item_type = int(row["item_type"]) if row else 1
            try:
                cursor.execute(
                    f"INSERT INTO player_task_items "
                    "(user_id, item_type, item_id, amount) VALUES (%s, %s, %s, 1)",
                    (int(user_id), item_type, int(item_id)),
                )
            except pymysql.err.IntegrityError:
                # Another request inserted the same item between UPDATE and
                # INSERT; apply this pickup to that row.
                cursor.execute(
                    f"UPDATE player_task_items SET amount=amount+1 "
                    "WHERE user_id=%s AND item_id=%s",
                    (int(user_id), int(item_id)),
                )

    @staticmethod
    def _task_req_items(value) -> list[tuple[int, int]]:
        """Parse ``req_item`` entries such as ``8/1100014;1/1100016``."""
        result = []
        for entry in str(value or "").split(";"):
            try:
                if "/" in entry:
                    amount, item_id = entry.split("/", 1)
                    amount, item_id = int(amount), int(item_id)
                else:
                    amount, item_id = 1, int(entry)
            except (TypeError, ValueError):
                continue
            if item_id:
                result.append((amount, item_id))
        return result

    def _recycle_task_items(self, cursor, user_id: int, value) -> None:
        """Remove the configured ``recycle_item`` quantities for one step.

        Task-item rows include ``item_type`` in their primary key, so consume
        matching rows in order rather than assuming one row per item ID.  If
        the player owns fewer items than requested, all owned items are
        removed and the remainder is ignored.
        """
        for requested, item_id in self._task_req_items(value):
            remaining = int(requested)
            if remaining <= 0:
                continue
            cursor.execute(
                "SELECT item_type, amount FROM player_task_items "
                "WHERE user_id=%s AND item_id=%s AND amount>0 "
                "ORDER BY item_type",
                (int(user_id), int(item_id)),
            )
            for row in cursor.fetchall() or ():
                available = int(row.get("amount") or 0)
                consumed = min(available, remaining)
                if consumed <= 0:
                    continue
                new_amount = available - consumed
                if new_amount > 0:
                    cursor.execute(
                        "UPDATE player_task_items SET amount=%s "
                        "WHERE user_id=%s AND item_id=%s AND item_type=%s",
                        (new_amount, int(user_id), int(item_id), int(row["item_type"])),
                    )
                else:
                    cursor.execute(
                        "DELETE FROM player_task_items "
                        "WHERE user_id=%s AND item_id=%s AND item_type=%s",
                        (int(user_id), int(item_id), int(row["item_type"])),
                    )
                remaining -= consumed
                if remaining <= 0:
                    break

    def _grant_task_items(self, cursor, user_id: int, value) -> None:
        """Grant ``got_item`` entries to the task-item inventory."""
        for amount, item_id in self._task_req_items(value):
            if amount <= 0:
                continue
            cursor.execute(
                "SELECT COALESCE(`Type`, 1) AS item_type FROM task_items WHERE ID=%s",
                (item_id,),
            )
            row = cursor.fetchone() or {}
            item_type = int(row.get("item_type") or 1)
            cursor.execute(
                "INSERT INTO player_task_items (user_id, item_type, item_id, amount) "
                "VALUES (%s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE amount=amount+VALUES(amount), item_type=VALUES(item_type)",
                (int(user_id), item_type, item_id, amount),
            )

    def _grant_task_reward(self, cursor, user_id: int, item_id: int, amount: int) -> None:
        """Grant one normal task reward to its catalog-backed inventory."""
        catalogs = (
            ("type_clothes", "player_clothes", "id", "cloth_id", True),
            ("type_flowers", "player_flowers", "id", "item_id", False),
            ("type_seeds", "player_seeds", "id", "item_id", False),
            ("type_materials", "player_materials", "id", "item_id", False),
            ("type_home_props", "player_home_props", "id", "item_id", False),
            ("type_pet_supplies", "player_pet_supplies", "id", "item_id", False),
            ("type_pollens", "player_pollens", "id", "pollen_id", False),
            ("type_house_goods", "player_house_goods", "id", "item_id", False),
        )
        for catalog, table, catalog_id, player_id, unique in catalogs:
            cursor.execute(f"SELECT 1 FROM {catalog} WHERE {catalog_id}=%s LIMIT 1", (item_id,))
            if cursor.fetchone() is None:
                continue
            if unique:
                cursor.execute(
                    f"INSERT IGNORE INTO {table} (user_id, {player_id}) VALUES (%s, %s)",
                    (int(user_id), item_id),
                )
            elif table == "player_house_goods":
                cursor.execute(
                    "SELECT COALESCE(MAX(no), 0) AS max_no FROM player_house_goods "
                    "WHERE user_id=%s FOR UPDATE",
                    (int(user_id),),
                )
                next_no = int((cursor.fetchone() or {}).get("max_no") or 0) + 1
                for offset in range(int(amount)):
                    cursor.execute(
                        "INSERT INTO player_house_goods "
                        "(user_id, item_id, no, x, y, m, z, is_set) "
                        "VALUES (%s, %s, %s, 0, 0, 0, 0, 0)",
                        (int(user_id), item_id, next_no + offset),
                    )
            else:
                cursor.execute(
                    f"INSERT INTO {table} (user_id, {player_id}, amount) VALUES (%s, %s, %s) "
                    f"ON DUPLICATE KEY UPDATE amount=amount+VALUES(amount)",
                    (int(user_id), item_id, int(amount)),
                )
            return

    def start_task(self, user_id: int, job_id: int, step: int) -> None:
        """Accept a task and mark its requested step as active."""
        self._ensure_connection()
        user_id, job_id, step = int(user_id), int(job_id), int(step)
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT step, flag FROM player_task_progress WHERE user_id=%s AND job_id=%s LIMIT 1",
                (user_id, job_id),
            )
            current = cursor.fetchone()
            if current and int(current.get("step") or 0) == step and int(current.get("flag") or 0):
                return
            cursor.execute(
                "SELECT got_item, start_need FROM task_list WHERE main_id=%s AND id=%s",
                (job_id, step),
            )
            task = cursor.fetchone() or {}
            cursor.execute(
                "SELECT step_need FROM type_npc_jobs WHERE job_id=%s AND step=%s "
                "ORDER BY npc_id LIMIT 1",
                (job_id, step),
            )
            step_row = cursor.fetchone() or {}
            total = int(step_row.get("step_need") or task.get("start_need") or 0)
            cursor.execute(
                "UPDATE player_task_progress SET step=%s, flag=1, process=0, total_process=%s "
                "WHERE user_id=%s AND job_id=%s",
                (step, total, user_id, job_id),
            )
            if cursor.rowcount:
                self._grant_task_items(cursor, user_id, task.get("got_item"))
                return
            cursor.execute(
                "SELECT step_need FROM type_npc_jobs "
                "WHERE job_id=%s AND step=%s ORDER BY npc_id LIMIT 1",
                (job_id, step),
            )
            row = cursor.fetchone() or {}
            total = int(row.get("step_need") or task.get("start_need") or 0)
            cursor.execute(
                "INSERT INTO player_task_progress "
                "(user_id, job_id, step, flag, process, total_process, get_time) "
                "VALUES (%s, %s, %s, 1, 0, %s, %s)",
                (user_id, job_id, step, total, int(time.time())),
            )
            self._grant_task_items(cursor, user_id, task.get("got_item"))

    def finish_task_step(self, user_id: int, job_id: int, step: int, reward_id: int = 0,
                         nationality: int = 1) -> int:
        """Consume the current step's task items and advance when possible."""
        self._ensure_connection()
        user_id, job_id, step = int(user_id), int(job_id), int(step)
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT req_item, got_item, recycle_item, reward_item_girl, reward_item_boy, "
                "give_item_num "
                "FROM task_list WHERE main_id=%s AND id=%s",
                (job_id, step),
            )
            task = cursor.fetchone() or {}
            response_id = int(reward_id)
            item_ids = {item_id for _, item_id in self._task_req_items(task.get("req_item"))}
            if item_ids:
                placeholders = ",".join(["%s"] * len(item_ids))
                cursor.execute(
                    "DELETE FROM player_task_items WHERE user_id=%s "
                    f"AND item_id IN ({placeholders})",
                    (user_id, *sorted(item_ids)),
                )

            self._recycle_task_items(cursor, user_id, task.get("recycle_item"))

            cursor.execute(
                "SELECT step_need FROM type_npc_jobs "
                "WHERE job_id=%s AND step=%s ORDER BY npc_id LIMIT 1",
                (job_id, step + 1),
            )
            next_step = cursor.fetchone()
            if next_step is not None:
                cursor.execute(
                    "SELECT got_item FROM task_list WHERE main_id=%s AND id=%s",
                    (job_id, step + 1),
                )
                next_task = cursor.fetchone() or {}
                cursor.execute(
                    "UPDATE player_task_progress SET step=%s, process=0, "
                    "total_process=%s WHERE user_id=%s AND job_id=%s",
                    (step + 1, int(next_step.get("step_need") or 0), user_id, job_id),
                )
                self._grant_task_items(cursor, user_id, next_task.get("got_item"))
            else:
                reward_field = "reward_item_boy" if int(nationality) == 5 else "reward_item_girl"
                rewards = self._task_req_items(task.get(reward_field))
                reward_ids = {item_id for _, item_id in rewards}
                if rewards and response_id not in reward_ids:
                    response_id = rewards[0][1]
                # give_item_num=3 is the client's "claim all" flow.  The
                # other reward modes select exactly one item (the selected
                # ID for type 1, or the server fallback for type 2).
                if int(task.get("give_item_num") or 0) == 3:
                    for amount, item_id in rewards:
                        self._grant_task_reward(cursor, user_id, item_id, amount)
                elif rewards:
                    amount = next(amount for amount, item_id in rewards if item_id == response_id)
                    self._grant_task_reward(cursor, user_id, response_id, amount)
                cursor.execute(
                    "INSERT INTO player_completed_tasks (user_id, job_id, completed_at) "
                    "VALUES (%s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE completed_at=VALUES(completed_at)",
                    (user_id, job_id, int(time.time())),
                )
            return response_id

    def use_task_item(self, user_id: int, item_id: int) -> bool:
        """Consume one task item and complete its active progress if depleted."""
        self._ensure_connection()
        user_id, item_id = int(user_id), int(item_id)
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT amount FROM player_task_items WHERE user_id=%s AND item_id=%s LIMIT 1",
                (user_id, item_id),
            )
            row = cursor.fetchone()
            if not row or int(row.get("amount") or 0) <= 0:
                return False
            amount = int(row["amount"]) - 1
            if amount:
                cursor.execute(
                    "UPDATE player_task_items SET amount=%s WHERE user_id=%s AND item_id=%s",
                    (amount, user_id, item_id),
                )
            else:
                cursor.execute(
                    "DELETE FROM player_task_items WHERE user_id=%s AND item_id=%s",
                    (user_id, item_id),
                )
            if amount:
                return True
            cursor.execute(
                "SELECT main_id, id, req_item, got_item FROM task_list "
                "WHERE req_item LIKE %s OR got_item LIKE %s",
                (f"%/{item_id}%", f"%/{item_id}%"),
            )
            for task in cursor.fetchall() or []:
                req_match = any(required_id == item_id for _, required_id in self._task_req_items(task.get("req_item")))
                got_match = any(required_id == item_id for _, required_id in self._task_req_items(task.get("got_item")))
                if not req_match and not got_match:
                    continue
                cursor.execute(
                    "UPDATE player_task_progress SET process=total_process "
                    "WHERE user_id=%s AND job_id=%s AND step=%s AND flag=1",
                    (user_id, int(task["main_id"]), int(task["id"])),
                )
            return True

    def complete_task_event(self, user_id: int, job_id: int, step: int) -> int:
        """Mark the matching task step as complete for a task event."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE player_task_progress SET process=total_process "
                "WHERE user_id=%s AND job_id=%s AND step=%s LIMIT 1",
                (int(user_id), int(job_id), int(step)),
            )
            return cursor.rowcount

    def add_task_item_and_progress(self, user_id: int, item_id: int) -> list[tuple[int, int]]:
        """Store a pickup and increment every active job step requiring it."""
        self._ensure_connection()
        user_id, item_id = int(user_id), int(item_id)
        self.add_task_item(user_id, item_id)
        over = []
        with self.connection.cursor() as cursor:
            # The deployed schema stores task requirements in task_list.req_item.
            cursor.execute(
                "SELECT main_id, id, req_item FROM task_list "
                "WHERE req_item LIKE %s",
                (f"%/{item_id}%",),
            )
            required = {
                (int(row["main_id"]), int(row["id"]))
                for row in (cursor.fetchall() or [])
                if any(required_id == item_id for _, required_id in self._task_req_items(row.get("req_item")))
            }
            for job_id, step in sorted(required):
                cursor.execute(
                    "UPDATE player_task_progress SET process=process+1 "
                    "WHERE user_id=%s AND job_id=%s AND step=%s "
                    "AND flag=1 AND process < total_process",
                    (user_id, job_id, step),
                )
                if cursor.rowcount:
                    cursor.execute(
                        "SELECT process, total_process FROM player_task_progress "
                        "WHERE user_id=%s AND job_id=%s AND step=%s",
                        (user_id, job_id, step),
                    )
                    progress = cursor.fetchone() or {}
                    if int(progress.get("total_process") or 0) > 0 and int(progress.get("process") or 0) >= int(progress.get("total_process") or 0):
                        over.append((job_id, step))
        return over

    def inventory_items(self, user_id: int, item_type: int):
        """Read owned items for the requested AS3 ITEM_TYPE_INFO category."""
        self._ensure_connection()
        user_id, item_type = int(user_id), int(item_type)
        queries = {
            7: ("""SELECT inv.item_id, inv.amount FROM player_flowers inv
                 INNER JOIN type_flowers catalog ON catalog.id=inv.item_id
                 WHERE inv.user_id=%s AND inv.amount>0 ORDER BY inv.item_id""", (user_id,)),
            2: ("""SELECT inv.item_id, inv.amount FROM player_seeds inv
                 INNER JOIN type_seeds catalog ON catalog.id=inv.item_id
                 WHERE inv.user_id=%s AND inv.amount>0 ORDER BY inv.item_id""", (user_id,)),
            16: ("""SELECT inv.item_id, inv.amount FROM player_materials inv
                  INNER JOIN type_materials catalog ON catalog.id=inv.item_id
                  WHERE inv.user_id=%s AND inv.amount>0 ORDER BY inv.item_id""", (user_id,)),
            13: ("""SELECT inv.pollen_id AS item_id, inv.amount FROM player_pollens inv
                  INNER JOIN type_pollens catalog ON catalog.id=inv.pollen_id
                  WHERE inv.user_id=%s AND inv.amount>0 ORDER BY inv.pollen_id""", (user_id,)),
            8: ("""SELECT item_id, amount FROM player_pet_supplies
                 WHERE user_id=%s AND amount>0 ORDER BY item_id""", (user_id,)),
        }
        if item_type in (11, 17):
            # Type 11 is the task-item bag.  Keep type 17 on the selected
            # compatibility table used by older database layouts.
            with self.connection.cursor() as cursor:
                if item_type == 11:
                    cursor.execute(
                        f"SELECT item_id, amount FROM player_task_items "
                        "WHERE user_id=%s AND amount>0 ORDER BY item_id",
                        (user_id,),
                    )
                else:
                    cursor.execute(
                        f"SELECT item_id, amount FROM player_task_items "
                        "WHERE user_id=%s AND item_type=%s AND amount>0 ORDER BY item_id",
                        (user_id, item_type),
                    )
                return list(cursor.fetchall() or [])
        query = queries.get(item_type)
        if query is None:
            return []
        with self.connection.cursor() as cursor:
            cursor.execute(query[0], query[1])
            return list(cursor.fetchall() or [])

    def inventory_item_counts(self, user_id: int, item_ids):
        """Return quantities for legacy CHECK_ITEM requests.

        Command 1023 addresses items directly instead of using the category
        format used by ITEM_TYPE_INFO (1034).  Item IDs are spread across the
        player inventory tables, so query each supported store and merge the
        results by ID.  Missing items intentionally remain at zero.
        """
        self._ensure_connection()
        user_id = int(user_id)
        item_ids = list(dict.fromkeys(int(item_id) for item_id in item_ids))
        if not item_ids:
            return {}

        placeholders = ",".join(["%s"] * len(item_ids))
        sources = (
            # Task requirements are kept in a separate per-player inventory.
            # The AS3 TASK_LIST flow follows command 1103 with CHECK_ITEM and
            # uses these counts to recalculate Process, so omitting this table
            # makes every task-item-backed progress value appear as zero.
            ("player_task_items", "item_id"),
            ("player_flowers", "item_id"),
            ("player_seeds", "item_id"),
            ("player_materials", "item_id"),
            ("player_pollens", "pollen_id"),
            ("player_pet_supplies", "item_id"),
            ("player_home_props", "item_id"),
            ("player_magics", "action_id"),
        )
        counts = {item_id: 0 for item_id in item_ids}
        with self.connection.cursor() as cursor:
            for table, column in sources:
                cursor.execute(
                    f"SELECT {column} AS item_id, SUM(amount) AS amount "
                    f"FROM {table} WHERE user_id=%s AND {column} IN ({placeholders}) "
                    f"GROUP BY {column}",
                    (user_id, *item_ids),
                )
                for row in cursor.fetchall() or ():
                    item_id = int(row["item_id"])
                    if item_id in counts:
                        counts[item_id] += int(row["amount"] or 0)
        return counts

    def task_progress_rows(self, user_id: int):
        """Return active/unaccepted task rows, excluding completed jobs.

        A completed job can retain its progress row after the final step is
        submitted.  Command 1103 has a separate completed-job section, so
        returning that stale progress row would make the client show the job
        as still active as well.
        """
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT progress.* FROM player_task_progress AS progress "
                "LEFT JOIN player_completed_tasks AS completed "
                "ON completed.user_id=progress.user_id "
                "AND completed.job_id=progress.job_id "
                "WHERE progress.user_id=%s AND completed.job_id IS NULL",
                (int(user_id),),
            )
            return list(cursor.fetchall() or [])

    def home_depot_items(self, user_id: int):
        """Return all items shown in the HOME_DEPOT (10003) inventory.

        Seeds, planting tools, and pots are quantity-based inventory rows.
        Furniture is stored as one row per item, so unplaced rows are counted
        by item ID.  Houses and backgrounds are catalog-owned in this server
        and the legacy client expects every catalog entry with quantity one.
        """
        self._ensure_connection()
        user_id = int(user_id)
        with self.connection.cursor() as cursor:
            cursor.execute(
                """SELECT inv.item_id, inv.amount FROM player_seeds inv
                   INNER JOIN type_seeds catalog ON catalog.id=inv.item_id
                   WHERE inv.user_id=%s AND inv.amount>0
                   UNION ALL
                   SELECT inv.pollen_id AS item_id, inv.amount FROM player_pollens inv
                   INNER JOIN type_pollens catalog ON catalog.id=inv.pollen_id
                   WHERE inv.user_id=%s AND inv.amount>0
                   UNION ALL
                   SELECT inv.item_id, inv.amount FROM player_home_props inv
                   INNER JOIN type_home_props catalog ON catalog.id=inv.item_id
                   WHERE inv.user_id=%s AND inv.amount>0
                   UNION ALL
                   SELECT inv.item_id, inv.amount FROM player_pots inv
                   WHERE inv.user_id=%s AND inv.amount>0
                   UNION ALL
                   SELECT item_id, COUNT(*) AS amount
                   FROM player_home_goods
                   WHERE user_id=%s AND is_set=0
                   GROUP BY item_id
                   UNION ALL
                   SELECT id AS item_id, 1 AS amount
                   FROM type_houses
                   UNION ALL
                   SELECT id AS item_id, 1 AS amount
                   FROM type_home_bg
                   ORDER BY item_id""",
                (user_id, user_id, user_id, user_id, user_id),
            )
            return list(cursor.fetchall() or [])


    def beauty_profile(self, user_id: int):
        """Load an optional beauty-pageant profile, including its JSON arrays."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM player_beauty_profiles WHERE user_id=%s LIMIT 1",
                (int(user_id),),
            )
            row = cursor.fetchone()
        if not row:
            return None
        row = dict(row)
        for column, key in (("clothes_json", "clothes"), ("recent_presents_json", "recent_presents")):
            raw = row.pop(column, None)
            if raw:
                try:
                    decoded = json.loads(raw) if isinstance(raw, (str, bytes, bytearray)) else raw
                    row[key] = decoded if isinstance(decoded, list) else []
                except (TypeError, ValueError):
                    row[key] = []
            else:
                row[key] = []
        return row

    def npc_rows(self, map_id: int):
        self._ensure_connection()
        return fetch_npcs(self.connection, map_id)

    def npc_job_rows(self, npc_id: int, user_id: int):
        self._ensure_connection()
        return fetch_npc_jobs(self.connection, npc_id, user_id)

    def puppet_info(self, user_id: int):
        self._ensure_connection()
        return fetch_puppet(self.connection, user_id)

    def set_friends_application(self, user_id: int, enabled: int) -> None:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE accounts SET enable_friends_application=%s WHERE user_id=%s",
                (1 if enabled else 0, int(user_id)),
            )

    def touch_last_contact(self, owner_user_id: int, friend_user_id: int) -> None:
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE player_friends SET last_contact_time=%s "
                "WHERE owner_user_id=%s AND friend_user_id=%s",
                (int(time.time()), int(owner_user_id), int(friend_user_id)),
            )

    def set_friend_status(self, owner_user_id: int, friend_user_id: int, status: int) -> bool:
        """Change one owner's existing friend relation between statuses 10 and 11."""
        self._ensure_connection()
        owner_user_id, friend_user_id, status = int(owner_user_id), int(friend_user_id), int(status)
        if status not in (FRIEND_STATUS_FRIEND, FRIEND_STATUS_INTIMATE):
            return False
        try:
            self.connection.begin()
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT status FROM player_friends "
                    "WHERE owner_user_id=%s AND friend_user_id=%s FOR UPDATE",
                    (owner_user_id, friend_user_id),
                )
                relation = cursor.fetchone()
                if not relation or int(relation["status"]) not in (
                    FRIEND_STATUS_FRIEND, FRIEND_STATUS_INTIMATE
                ):
                    self.connection.rollback()
                    return False
                cursor.execute(
                    "UPDATE player_friends SET status=%s "
                    "WHERE owner_user_id=%s AND friend_user_id=%s",
                    (status, owner_user_id, friend_user_id),
                )
            self.connection.commit()
            return True
        except Exception:
            self.connection.rollback()
            raise

    def add_black_friend(self, owner_user_id: int, friend_user_id: int) -> bool:
        """Create or replace the owner's one-way blacklist relation."""
        self._ensure_connection()
        owner_user_id, friend_user_id = int(owner_user_id), int(friend_user_id)
        if owner_user_id == friend_user_id:
            return False
        try:
            self.connection.begin()
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM accounts WHERE user_id=%s LIMIT 1",
                    (friend_user_id,),
                )
                if cursor.fetchone() is None:
                    self.connection.rollback()
                    return False
                cursor.execute(
                    "INSERT INTO player_friends "
                    "(owner_user_id,friend_user_id,status,application_time,added_time) "
                    "VALUES (%s,%s,%s,%s,%s) "
                    "ON DUPLICATE KEY UPDATE status=VALUES(status), added_time=VALUES(added_time)",
                    (owner_user_id, friend_user_id, FRIEND_STATUS_BLACKLIST,
                     int(time.time()), int(time.time())),
                )
            self.connection.commit()
            return True
        except Exception:
            self.connection.rollback()
            raise

    def delete_black_friend(self, owner_user_id: int, friend_user_id: int) -> bool:
        """Physically remove the owner's one-way blacklist relation."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM player_friends WHERE owner_user_id=%s "
                "AND friend_user_id=%s AND status=%s",
                (int(owner_user_id), int(friend_user_id), FRIEND_STATUS_BLACKLIST),
            )
            return cursor.rowcount > 0

    def is_blacklisted(self, owner_user_id: int, other_user_id: int) -> bool:
        """Return whether owner_user_id blocks other_user_id."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM player_friends WHERE owner_user_id=%s "
                "AND friend_user_id=%s AND status=%s LIMIT 1",
                (int(owner_user_id), int(other_user_id), FRIEND_STATUS_BLACKLIST),
            )
            return cursor.fetchone() is not None

    def delete_friend(self, owner_user_id: int, friend_user_id: int) -> bool:
        """Physically remove both directional rows for a friend relation."""
        self._ensure_connection()
        owner_user_id, friend_user_id = int(owner_user_id), int(friend_user_id)
        try:
            self.connection.begin()
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM player_friends WHERE "
                    "(owner_user_id=%s AND friend_user_id=%s) OR "
                    "(owner_user_id=%s AND friend_user_id=%s)",
                    (owner_user_id, friend_user_id, friend_user_id, owner_user_id),
                )
                deleted = cursor.rowcount
            self.connection.commit()
            return deleted > 0
        except Exception:
            self.connection.rollback()
            raise

    def friend_rows(self, owner_user_id: int, statuses, limit: int):
        self._ensure_connection()
        marks = ",".join(["%s"] * len(statuses))
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM player_friends WHERE owner_user_id=%s "
                f"AND status IN ({marks}) ORDER BY COALESCE(added_time, application_time, 0) DESC "
                f"LIMIT %s",
                (int(owner_user_id), *[int(v) for v in statuses], int(limit)),
            )
            return list(cursor.fetchall() or [])

    def incoming_friend_requests(self, user_id: int, limit: int = 100):
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT pf.* FROM player_friends pf "
                "WHERE pf.friend_user_id=%s AND pf.status=%s "
                "AND NOT EXISTS (SELECT 1 FROM player_friends blocked "
                "WHERE blocked.owner_user_id=%s AND blocked.friend_user_id=pf.owner_user_id "
                "AND blocked.status=%s) "
                "ORDER BY pf.application_time ASC LIMIT %s",
                (int(user_id), FRIEND_STATUS_PENDING, int(user_id),
                 FRIEND_STATUS_BLACKLIST, int(limit)),
            )
            return list(cursor.fetchall() or [])

    def answer_friend_request(self, recipient_user_id: int, requester_user_id: int, accepted: int) -> int:
        """Accept or reject a pending request addressed to the current user."""
        self._ensure_connection()
        recipient_user_id, requester_user_id = int(recipient_user_id), int(requester_user_id)
        now = int(time.time())
        try:
            self.connection.begin()
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT status FROM player_friends WHERE owner_user_id=%s AND friend_user_id=%s FOR UPDATE",
                    (requester_user_id, recipient_user_id),
                )
                pending = cursor.fetchone()
                if not pending or int(pending["status"]) != FRIEND_STATUS_PENDING:
                    self.connection.rollback()
                    return 404
                if accepted:
                    for owner, friend in ((requester_user_id, recipient_user_id),
                                          (recipient_user_id, requester_user_id)):
                        cursor.execute(
                            "INSERT INTO player_friends "
                            "(owner_user_id,friend_user_id,status,application_time,added_time) "
                            "VALUES (%s,%s,%s,%s,%s) "
                            "ON DUPLICATE KEY UPDATE status=%s, added_time=VALUES(added_time)",
                            (owner, friend, FRIEND_STATUS_FRIEND, now, now, FRIEND_STATUS_FRIEND),
                        )
                else:
                    cursor.execute(
                        "DELETE FROM player_friends WHERE "
                        "(owner_user_id=%s AND friend_user_id=%s) OR "
                        "(owner_user_id=%s AND friend_user_id=%s)",
                        (requester_user_id, recipient_user_id, recipient_user_id, requester_user_id),
                    )
            self.connection.commit()
            return 0
        except Exception:
            self.connection.rollback()
            raise

    def friend_user_row(self, friend_user_id: int, friend_team: int):
        account = self.get_by_id(int(friend_user_id))
        if not account:
            return None
        row = dict(account.profile or {})
        try:
            row.update(self.profile(int(friend_user_id)))
        except Exception:
            pass
        row.update(user_id=account.user_id, friend_team=int(friend_team))
        row.setdefault("nickname", account.login_name)
        row.setdefault("vip_level", 0)
        row.setdefault("home_pollen", row.get("pollen", 0))
        return row

    def add_friend_request(self, owner_user_id: int, friend_user_id: int) -> int:
        """Create a pending request, or complete a reciprocal request."""
        self._ensure_connection()
        owner_user_id, friend_user_id = int(owner_user_id), int(friend_user_id)
        now = int(time.time())
        try:
            self.connection.begin()
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT user_id, enable_friends_application FROM accounts WHERE user_id IN (%s,%s)",
                    (owner_user_id, friend_user_id),
                )
                accounts = {int(r["user_id"]): r for r in cursor.fetchall() or []}
                if owner_user_id == friend_user_id or friend_user_id not in accounts:
                    self.connection.rollback()
                    return 404
                enabled = accounts[friend_user_id].get("enable_friends_application")
                if enabled is None:
                    enabled = 1
                if not enabled:
                    self.connection.rollback()
                    return 403
                cursor.execute(
                    "SELECT owner_user_id, friend_user_id FROM player_friends "
                    "WHERE ((owner_user_id=%s AND friend_user_id=%s) OR "
                    "(owner_user_id=%s AND friend_user_id=%s)) AND status=%s "
                    "FOR UPDATE",
                    (owner_user_id, friend_user_id, friend_user_id, owner_user_id,
                     FRIEND_STATUS_BLACKLIST),
                )
                if cursor.fetchone() is not None:
                    self.connection.rollback()
                    return 403
                cursor.execute(
                    "SELECT status FROM player_friends WHERE owner_user_id=%s AND friend_user_id=%s FOR UPDATE",
                    (owner_user_id, friend_user_id),
                )
                current = cursor.fetchone()
                if current and int(current["status"]) in (FRIEND_STATUS_FRIEND, FRIEND_STATUS_INTIMATE):
                    self.connection.rollback()
                    return 0
                cursor.execute(
                    "SELECT status FROM player_friends WHERE owner_user_id=%s AND friend_user_id=%s FOR UPDATE",
                    (friend_user_id, owner_user_id),
                )
                reciprocal = cursor.fetchone()
                if reciprocal and int(reciprocal["status"]) == FRIEND_STATUS_PENDING:
                    for source, target in ((owner_user_id, friend_user_id), (friend_user_id, owner_user_id)):
                        cursor.execute(
                            "INSERT INTO player_friends "
                            "(owner_user_id,friend_user_id,status,application_time,added_time) "
                            "VALUES (%s,%s,%s,%s,%s) "
                            "ON DUPLICATE KEY UPDATE status=%s, added_time=VALUES(added_time)",
                            (source, target, FRIEND_STATUS_FRIEND, now, now, FRIEND_STATUS_FRIEND),
                        )
                else:
                    cursor.execute(
                        "INSERT INTO player_friends "
                        "(owner_user_id,friend_user_id,status,application_time) VALUES (%s,%s,%s,%s) "
                        "ON DUPLICATE KEY UPDATE status=VALUES(status), application_time=VALUES(application_time)",
                        (owner_user_id, friend_user_id, FRIEND_STATUS_PENDING, now),
                    )
            self.connection.commit()
            return 0
        except Exception:
            self.connection.rollback()
            raise

    def _ensure_connection(self):
        """Reconnect transparently after MySQL has dropped an idle connection."""
        try:
            self.connection.ping(reconnect=True)
        except Exception:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = pymysql.connect(**self._connect_kwargs, charset="utf8mb4", autocommit=True,
                                              cursorclass=pymysql.cursors.DictCursor)

    def close(self):
        self.connection.close()

    def get(self, login_name: str) -> Optional[Account]:
        self._ensure_connection()
        numeric_id = int(login_name) if login_name.isdigit() else -1
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT * FROM accounts WHERE login_name=%s OR user_id=%s LIMIT 1", (login_name, numeric_id))
            row = cursor.fetchone()
        if not row:
            return None
        return Account(int(row["user_id"]), str(row.get("login_name", row["user_id"])), str(row.get("password_hash", "")),
                       bool(row.get("role_created", 1)), bool(row.get("banned", 0)), dict(row))

    def get_by_id(self, user_id: int) -> Optional[Account]:
        return self.get(str(user_id))

    def profile(self, user_id: int) -> Dict[str, object]:
        """Load the optional player_profile row and normalize clothing JSON."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT * FROM player_profiles WHERE user_id=%s LIMIT 1", (user_id,))
            row = cursor.fetchone() or {}
        result = dict(row)
        # Only a pet with rest_at=0 is carried by the player in login/map
        # records. Resting pets are delivered by 10200/10208 instead.
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM player_pets WHERE user_id=%s AND rest_at=0 "
                "ORDER BY pet_id LIMIT 1", (int(user_id),)
            )
            followed = cursor.fetchone()
        result["pet"] = followed
        # Clothing and multi-effect arrays are intentionally JSON columns:
        # their lengths change with client versions and splitting them into
        # dozens of nullable columns makes migrations brittle.
        for column in ("clothing_json", "mult_effects_json"):
            raw = result.pop(column, None)
            if raw:
                try:
                    decoded = json.loads(raw) if isinstance(raw, (str, bytes, bytearray)) else raw
                    if column == "clothing_json" and isinstance(decoded, dict):
                        result.update(decoded)
                    elif column == "mult_effects_json" and isinstance(decoded, list):
                        result["mult_effects"] = decoded
                except (TypeError, ValueError):
                    pass
        return result

    def money(self, user_id: int) -> int:
        """Return the current player's shop currency from ``player_profiles``."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT money FROM player_profiles WHERE user_id=%s LIMIT 1",
                (int(user_id),),
            )
            row = cursor.fetchone()
        # A missing profile is treated as a zero balance.  This keeps the
        # response shape valid while allowing callers to distinguish database
        # failures through the exception path.
        return int((row or {}).get("money") or 0) & 0xFFFFFFFF

    def buy_shop_item(self, user_id: int, item_id: int, quantity: int):
        """Atomically buy a shop item with the player's money.

        Returns ``(status, item_id, quantity)`` on success or ``(status, 0,
        0)`` when the purchase is rejected. Status 0 is success, 10 is a
        duplicate clothing item, 23 is a duplicate house, 10008 is a missing
        catalog item, 1205 is insufficient money, and 1206 is an invalid
        quantity.
        """
        self._ensure_connection()
        user_id, item_id, quantity = map(int, (user_id, item_id, quantity))
        if quantity < 1 or quantity > 0xFFFFFFFF:
            return 1206, 0, 0

        # Clothes and houses are unique records, so a quantity other than one
        # is not meaningful and is rejected with the protocol's bad-quantity
        # status. Furniture, props, pet supplies, and legacy pots are stackable.
        unique_status = None
        if 100000 <= item_id < 200000:
            catalog_table, inventory_table, unique_status = "type_clothes", "player_clothes", 10
        elif 200000 <= item_id < 300000:
            catalog_table, inventory_table = "type_seeds", "player_seeds"
        elif 300000 <= item_id < 400000:
            catalog_table, inventory_table = "type_home_props", "player_home_props"
        elif 400000 <= item_id < 500000:
            catalog_table, inventory_table, unique_status = "type_houses", "player_houses", 23
        elif 500000 <= item_id < 600000:
            catalog_table, inventory_table = "type_house_goods", "player_house_goods"
        elif 800000 <= item_id < 900000:
            catalog_table, inventory_table = "type_pet_supplies", "player_pet_supplies"
        elif 900000 <= item_id < 1000000:
            catalog_table, inventory_table = "type_pots", "player_pots"
        else:
            return 10008, 0, 0
        if unique_status is not None and quantity != 1:
            return 1206, 0, 0

        try:
            self.connection.begin()
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT price FROM {catalog_table} WHERE id=%s LIMIT 1",
                    (item_id,),
                )
                catalog = cursor.fetchone()
                price = None if not catalog else catalog.get("price")
                if price is None or int(price) < 0:
                    self.connection.rollback()
                    return 10008, 0, 0
                price = int(price)
                total = price * quantity

                cursor.execute(
                    "SELECT money FROM player_profiles WHERE user_id=%s LIMIT 1 FOR UPDATE",
                    (user_id,),
                )
                profile = cursor.fetchone()
                if not profile:
                    self.connection.rollback()
                    return 5001, 0, 0

                if unique_status is not None:
                    key_column = "cloth_id" if inventory_table == "player_clothes" else "house_id"
                    cursor.execute(
                        f"SELECT 1 FROM {inventory_table} WHERE user_id=%s AND {key_column}=%s "
                        "LIMIT 1 FOR UPDATE",
                        (user_id, item_id),
                    )
                    if cursor.fetchone():
                        self.connection.rollback()
                        return unique_status, 0, 0

                money = int(profile.get("money") or 0)
                if money < total:
                    self.connection.rollback()
                    return 1205, 0, 0

                if inventory_table == "player_clothes":
                    cursor.execute(
                        "INSERT INTO player_clothes (user_id, cloth_id) VALUES (%s, %s)",
                        (user_id, item_id),
                    )
                elif inventory_table == "player_houses":
                    cursor.execute(
                        "INSERT INTO player_houses (user_id, house_id) VALUES (%s, %s)",
                        (user_id, item_id),
                    )
                elif inventory_table == "player_house_goods":
                    # This legacy table represents inventory as one row per
                    # item, with ``no`` as the per-user sequence number.
                    cursor.execute(
                        "SELECT COALESCE(MAX(no), 0) AS max_no FROM player_house_goods "
                        "WHERE user_id=%s FOR UPDATE",
                        (user_id,),
                    )
                    next_no = int((cursor.fetchone() or {}).get("max_no") or 0) + 1
                    if next_no + quantity - 1 > 0xFFFFFFFF:
                        self.connection.rollback()
                        return 1206, 0, 0
                    for offset in range(0, quantity, 1000):
                        batch_size = min(1000, quantity - offset)
                        cursor.executemany(
                            "INSERT INTO player_house_goods "
                            "(user_id, item_id, no, x, y, m, z, is_set) "
                            "VALUES (%s, %s, %s, 0, 0, 0, 0, 0)",
                            [
                                (user_id, item_id, next_no + index)
                                for index in range(offset, offset + batch_size)
                            ],
                        )
                else:
                    cursor.execute(
                        f"INSERT INTO {inventory_table} (user_id, item_id, amount) "
                        "VALUES (%s,%s,%s) "
                        "ON DUPLICATE KEY UPDATE amount=amount+VALUES(amount)",
                        (user_id, item_id, quantity),
                    )
                if total:
                    cursor.execute(
                        "UPDATE player_profiles SET money=money-%s "
                        "WHERE user_id=%s AND money >= %s",
                        (total, user_id, total),
                    )
                    if cursor.rowcount != 1:
                        self.connection.rollback()
                        return 1205, 0, 0
            self.connection.commit()
            return 0, item_id, quantity
        except pymysql.err.IntegrityError as exc:
            self.connection.rollback()
            if unique_status is not None and exc.args and exc.args[0] == 1062:
                return unique_status, 0, 0
            raise
        except Exception:
            self.connection.rollback()
            raise

    def sell_flower(self, user_id: int, flower_id: int, amount: int):
        """Sell owned flowers and return ``(status, earned_money)``."""
        self._ensure_connection()
        user_id, flower_id, amount = map(int, (user_id, flower_id, amount))
        if amount < 1 or amount > 0xFFFFFFFF:
            return 1206, 0

        try:
            self.connection.begin()
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT sell FROM type_flowers WHERE id=%s LIMIT 1 FOR UPDATE",
                    (flower_id,),
                )
                flower = cursor.fetchone()
                sell_price = None if not flower else flower.get("sell")
                if sell_price is None or int(sell_price) < 0:
                    self.connection.rollback()
                    return 10008, 0
                income = int(sell_price) * amount

                cursor.execute(
                    "SELECT money FROM player_profiles WHERE user_id=%s LIMIT 1 FOR UPDATE",
                    (user_id,),
                )
                profile = cursor.fetchone()
                if profile is None:
                    self.connection.rollback()
                    return 5001, 0
                if int(profile.get("money") or 0) + income > 0xFFFFFFFF:
                    self.connection.rollback()
                    return 5001, 0

                cursor.execute(
                    "UPDATE player_flowers SET amount=amount-%s "
                    "WHERE user_id=%s AND item_id=%s AND amount>=%s",
                    (amount, user_id, flower_id, amount),
                )
                if cursor.rowcount != 1:
                    self.connection.rollback()
                    return 140, 0
                cursor.execute(
                    "UPDATE player_profiles SET money=money+%s WHERE user_id=%s",
                    (income, user_id),
                )
            self.connection.commit()
            return 0, income
        except Exception:
            self.connection.rollback()
            raise

    def rows(self, table: str, user_id: int):
        self._ensure_connection()
        key = "map_id" if table == "map_items" else "user_id"
        with self.connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {table} WHERE {key}=%s", (user_id,))
            return list(cursor.fetchall() or [])

    def map_materials(self, map_id: int):
        """Return the configured pickable materials for one outdoor map."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT item_id, x, y FROM map_materials WHERE map_id=%s ORDER BY id",
                (int(map_id),),
            )
            return list(cursor.fetchall() or [])

    def add_map_material(self, user_id: int, item_id: int) -> None:
        """Add one picked map material, creating its inventory row if needed."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO player_materials (user_id, item_id, amount) VALUES (%s, %s, 1) "
                "ON DUPLICATE KEY UPDATE amount=amount+1",
                (int(user_id), int(item_id)),
            )

    def home_state(self, user_id: int):
        """Load the four storage groups used by the home-entry push frames."""
        self._ensure_connection()
        user_id = int(user_id)
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT * FROM player_homes WHERE user_id=%s LIMIT 1", (user_id,))
            home = cursor.fetchone() or {}
            cursor.execute(
                "SELECT * FROM player_home_plants WHERE user_id=%s ORDER BY plot_no",
                (user_id,),
            )
            plants = list(cursor.fetchall() or [])
            cursor.execute(
                "SELECT * FROM player_home_houses WHERE user_id=%s ORDER BY slot_index",
                (user_id,),
            )
            houses = list(cursor.fetchall() or [])
            cursor.execute(
                "SELECT * FROM player_home_goods WHERE user_id=%s ORDER BY slot_index",
                (user_id,),
            )
            goods = list(cursor.fetchall() or [])
        return dict(home), plants, houses, goods

    def collect_home_pollen(self, visitor_id: int, owner_id: int, plot_no: int):
        """Collect one pollen from another player's plant atomically.

        The plant belongs to ``owner_id`` while the inventory mutation belongs
        to ``visitor_id``.  Both rows are protected by the same transaction so
        concurrent requests cannot collect the last pollen twice.
        """
        self._ensure_connection()
        visitor_id, owner_id, plot_no = map(int, (visitor_id, owner_id, plot_no))
        try:
            self.connection.begin()
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pollen_id, pollen_count FROM player_home_plants "
                    "WHERE user_id=%s AND plot_no=%s FOR UPDATE",
                    (owner_id, plot_no),
                )
                plant = cursor.fetchone()
                if not plant:
                    self.connection.rollback()
                    return {"ok": False, "reason": 2, "pollen_id": 0}
                pollen_id = int(plant.get("pollen_id") or 0)
                pollen_count = int(plant.get("pollen_count") or 0)
                if pollen_id <= 0 or pollen_count <= 0:
                    self.connection.rollback()
                    return {"ok": False, "reason": 1, "pollen_id": max(0, pollen_id)}
                cursor.execute(
                    "UPDATE player_home_plants SET pollen_count=pollen_count-1 "
                    "WHERE user_id=%s AND plot_no=%s AND pollen_id=%s AND pollen_count>0",
                    (owner_id, plot_no, pollen_id),
                )
                if cursor.rowcount != 1:
                    self.connection.rollback()
                    return {"ok": False, "reason": 1, "pollen_id": pollen_id}
                cursor.execute(
                    "INSERT INTO player_pollens (user_id, pollen_id, amount) "
                    "VALUES (%s, %s, 1) "
                    "ON DUPLICATE KEY UPDATE amount=amount+VALUES(amount)",
                    (visitor_id, pollen_id),
                )
            self.connection.commit()
            return {"ok": True, "plot_no": plot_no, "pollen_id": pollen_id}
        except Exception:
            self.connection.rollback()
            raise

    def collect_all_home_pollen(self, visitor_id: int, owner_id: int):
        """Collect all available pollen from another player's home."""
        self._ensure_connection()
        visitor_id, owner_id = map(int, (visitor_id, owner_id))
        try:
            self.connection.begin()
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT plot_no, pollen_id, pollen_count FROM player_home_plants "
                    "WHERE user_id=%s AND pollen_id>0 AND pollen_count>0 "
                    "ORDER BY plot_no FOR UPDATE",
                    (owner_id,),
                )
                plants = list(cursor.fetchall() or [])
                amounts = {}
                for plant in plants:
                    plot_no = int(plant["plot_no"])
                    pollen_id = int(plant["pollen_id"])
                    cursor.execute(
                        "UPDATE player_home_plants SET pollen_count=pollen_count-1 "
                        "WHERE user_id=%s AND plot_no=%s AND pollen_id=%s AND pollen_count>0",
                        (owner_id, plot_no, pollen_id),
                    )
                    if cursor.rowcount == 1:
                        amounts[pollen_id] = amounts.get(pollen_id, 0) + 1
                for pollen_id, amount in amounts.items():
                    cursor.execute(
                        "INSERT INTO player_pollens (user_id, pollen_id, amount) "
                        "VALUES (%s, %s, %s) "
                        "ON DUPLICATE KEY UPDATE amount=amount+VALUES(amount)",
                        (visitor_id, pollen_id, amount),
                    )
            self.connection.commit()
            return amounts
        except Exception:
            self.connection.rollback()
            raise

    def change_home_house(self, user_id: int, house_id: int, x: int, y: int):
        """Replace the player's displayed house and return its placement."""
        self._ensure_connection()
        user_id, house_id, x, y = map(int, (user_id, house_id, x, y))
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT id FROM type_houses WHERE id=%s LIMIT 1", (house_id,))
            if not cursor.fetchone():
                return None
            cursor.execute(
                "SELECT x, y FROM player_home_houses "
                "WHERE user_id=%s AND slot_index=1 LIMIT 1",
                (user_id,),
            )
            house = cursor.fetchone()
            if not house:
                cursor.execute(
                    "INSERT INTO player_home_houses "
                    "(user_id, slot_index, item_id, x, y, open_flag, reserved) "
                    "VALUES (%s, 1, %s, %s, %s, 1, 0)",
                    (user_id, house_id, x, y),
                )
                return {"item_id": house_id, "x": x, "y": y}
            cursor.execute(
                "UPDATE player_home_houses SET item_id=%s "
                "WHERE user_id=%s AND slot_index=1",
                (house_id, user_id),
            )
        return {"item_id": house_id, "x": int(house["x"]), "y": int(house["y"])}

    def update_home_house_position(self, user_id: int, house_id: int, x: int, y: int):
        """Update one displayed house position and return the saved values."""
        self._ensure_connection()
        user_id, house_id, x, y = map(int, (user_id, house_id, x, y))
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM player_home_houses "
                "WHERE user_id=%s AND item_id=%s AND slot_index=1 LIMIT 1",
                (user_id, house_id),
            )
            if not cursor.fetchone():
                return None
            cursor.execute(
                "UPDATE player_home_houses SET x=%s, y=%s "
                "WHERE user_id=%s AND item_id=%s AND slot_index=1",
                (x, y, user_id, house_id),
            )
        return {"owner_id": user_id, "item_id": house_id, "x": x, "y": y}

    def back_home_house(self, user_id: int, house_id: int) -> bool:
        """Remove the displayed house for HOME_BACK_HOUSE (10012)."""
        self._ensure_connection()
        user_id, house_id = int(user_id), int(house_id)
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM player_home_houses "
                "WHERE user_id=%s AND item_id=%s AND slot_index=1 LIMIT 1",
                (user_id, house_id),
            )
            if not cursor.fetchone():
                return False
            cursor.execute(
                "DELETE FROM player_home_houses "
                "WHERE user_id=%s AND item_id=%s AND slot_index=1",
                (user_id, house_id),
            )
            return cursor.rowcount == 1

    def update_home_plant_positions(self, user_id: int, positions: list[dict]) -> bool:
        """Atomically update multiple plant/pot coordinates by plot number."""
        self._ensure_connection()
        user_id = int(user_id)
        try:
            self.connection.begin()
            with self.connection.cursor() as cursor:
                for position in positions:
                    plot_no = int(position["plot_no"])
                    x = int(position["x"])
                    y = int(position["y"])
                    cursor.execute(
                        "SELECT 1 FROM player_home_plants "
                        "WHERE user_id=%s AND plot_no=%s FOR UPDATE",
                        (user_id, plot_no),
                    )
                    if not cursor.fetchone():
                        self.connection.rollback()
                        return False
                    cursor.execute(
                        "UPDATE player_home_plants SET x=%s, y=%s "
                        "WHERE user_id=%s AND plot_no=%s",
                        (x, y, user_id, plot_no),
                    )
            self.connection.commit()
            return True
        except Exception:
            self.connection.rollback()
            raise

    def back_home_pot(self, user_id: int, plot_no: int):
        """Delete a plant/pot row and return its pot to player_pots atomically."""
        self._ensure_connection()
        user_id, plot_no = int(user_id), int(plot_no)
        try:
            self.connection.begin()
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pot_id FROM player_home_plants "
                    "WHERE user_id=%s AND plot_no=%s FOR UPDATE",
                    (user_id, plot_no),
                )
                plant = cursor.fetchone()
                if not plant or int(plant.get("pot_id", 0) or 0) == 0:
                    self.connection.rollback()
                    return None
                pot_id = int(plant["pot_id"])
                cursor.execute(
                    "DELETE FROM player_home_plants WHERE user_id=%s AND plot_no=%s",
                    (user_id, plot_no),
                )
                if cursor.rowcount != 1:
                    self.connection.rollback()
                    return None
                cursor.execute(
                    "INSERT INTO player_pots (user_id, item_id, amount) "
                    "VALUES (%s, %s, 1) "
                    "ON DUPLICATE KEY UPDATE amount=amount+1",
                    (user_id, pot_id),
                )
            self.connection.commit()
            return {"plot_no": plot_no, "pot_id": pot_id}
        except Exception:
            self.connection.rollback()
            raise

    def change_home_background(self, user_id: int, background_id: int) -> bool:
        """Set the player's selected garden background after catalog validation."""
        self._ensure_connection()
        user_id, background_id = int(user_id), int(background_id)
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT id FROM type_home_bg WHERE id=%s LIMIT 1", (background_id,))
            if not cursor.fetchone():
                return False
            cursor.execute("SELECT 1 FROM player_homes WHERE user_id=%s LIMIT 1", (user_id,))
            if not cursor.fetchone():
                return False
            cursor.execute(
                "UPDATE player_homes SET background_id=%s WHERE user_id=%s",
                (background_id, user_id),
            )
            return True

    def add_home_good(self, user_id: int, item_id: int, x: int, y: int):
        """Take one unplaced garden decoration and return its placed state."""
        self._ensure_connection()
        user_id, item_id, x, y = map(int, (user_id, item_id, x, y))
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT slot_index FROM player_home_goods "
                "WHERE user_id=%s AND item_id=%s AND is_set=0 "
                "ORDER BY slot_index LIMIT 1",
                (user_id, item_id),
            )
            row = cursor.fetchone()
            if not row:
                return None
            slot_index = int(row["slot_index"])
            cursor.execute(
                "UPDATE player_home_goods SET x=%s, y=%s, is_set=1 "
                "WHERE user_id=%s AND slot_index=%s AND is_set=0",
                (x, y, user_id, slot_index),
            )
            if cursor.rowcount != 1:
                return None
        return {"item_id": item_id, "x": x, "y": y}

    def add_home_pot(self, user_id: int, pot_id: int, x: int, y: int):
        """Consume one pot and create its empty plant slot atomically."""
        self._ensure_connection()
        user_id, pot_id, x, y = map(int, (user_id, pot_id, x, y))
        try:
            self.connection.begin()
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT amount FROM player_pots "
                    "WHERE user_id=%s AND item_id=%s FOR UPDATE",
                    (user_id, pot_id),
                )
                inventory = cursor.fetchone()
                if not inventory or int(inventory.get("amount", 0) or 0) < 1:
                    self.connection.rollback()
                    return None

                cursor.execute(
                    "SELECT COALESCE(MAX(plot_no), 99) + 1 AS plot_no "
                    "FROM player_home_plants WHERE user_id=%s FOR UPDATE",
                    (user_id,),
                )
                plot_no = int(cursor.fetchone()["plot_no"])
                cursor.execute(
                    "UPDATE player_pots SET amount=amount-1 "
                    "WHERE user_id=%s AND item_id=%s AND amount>0",
                    (user_id, pot_id),
                )
                if cursor.rowcount != 1:
                    self.connection.rollback()
                    return None
                cursor.execute(
                    "INSERT INTO player_home_plants "
                    "(user_id, plot_no, pot_id, x, y, owner_id) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (user_id, plot_no, pot_id, x, y, user_id),
                )
            self.connection.commit()
            return {"plot_no": plot_no, "x": x, "y": y, "pot_id": pot_id}
        except Exception:
            self.connection.rollback()
            raise

    def add_home_plant(self, user_id: int, pot_id: int, plant_id: int, x: int, y: int, requested_plot_no: int = 0):
        """Consume one seed and plant it, filling an existing empty pot when requested."""
        self._ensure_connection()
        user_id, pot_id, plant_id, x, y, requested_plot_no = map(
            int, (user_id, pot_id, plant_id, x, y, requested_plot_no)
        )
        try:
            self.connection.begin()
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT amount FROM player_seeds WHERE user_id=%s AND item_id=%s FOR UPDATE",
                    (user_id, plant_id),
                )
                seed = cursor.fetchone()
                if not seed or int(seed.get("amount", 0) or 0) < 1:
                    self.connection.rollback()
                    return None

                cursor.execute(
                    "SELECT nutrient_max, moisture_max, stage_vals1, flower_out_put_id_1, poll_out_put_id "
                    "FROM seed_plant_parameters WHERE id=%s LIMIT 1",
                    (plant_id,),
                )
                plant_parameters = cursor.fetchone()
                if not plant_parameters:
                    self.connection.rollback()
                    return None
                nutrient_max = max(0, int(plant_parameters.get("nutrient_max") or 0))
                moisture_max = max(0, int(plant_parameters.get("moisture_max") or 0))
                stage_vals1 = float(plant_parameters.get("stage_vals1") or 0)
                next_time = int(100 / stage_vals1 + 0.5) if stage_vals1 > 0 else 0
                flower_id = max(0, int(plant_parameters.get("flower_out_put_id_1") or 0))
                pollen_id = max(0, int(plant_parameters.get("poll_out_put_id") or 0))
                nutrient = nutrient_max * 100000 // 2
                moisture = moisture_max * 100000 // 2

                plant = None
                if pot_id:
                    if requested_plot_no:
                        cursor.execute(
                            "SELECT * FROM player_home_plants WHERE user_id=%s AND plot_no=%s "
                            "AND pot_id=%s AND plant_id=0 FOR UPDATE",
                            (user_id, requested_plot_no, pot_id),
                        )
                        plant = cursor.fetchone()
                        if not plant:
                            cursor.execute(
                                "SELECT * FROM player_home_plants WHERE user_id=%s AND pot_id=%s "
                                "AND plant_id=0 ORDER BY plot_no LIMIT 1 FOR UPDATE",
                                (user_id, pot_id),
                            )
                    else:
                        cursor.execute(
                            "SELECT * FROM player_home_plants WHERE user_id=%s AND pot_id=%s "
                            "AND plant_id=0 ORDER BY plot_no LIMIT 1 FOR UPDATE",
                            (user_id, pot_id),
                        )
                    if plant is None:
                        plant = cursor.fetchone()
                    if not plant:
                        self.connection.rollback()
                        return None
                    plot_no = int(plant["plot_no"])
                else:
                    cursor.execute(
                        "SELECT COALESCE(MAX(plot_no), 99) + 1 AS plot_no "
                        "FROM player_home_plants WHERE user_id=%s FOR UPDATE",
                        (user_id,),
                    )
                    plot_no = int(cursor.fetchone()["plot_no"])

                cursor.execute(
                    "UPDATE player_seeds SET amount=amount-1 "
                    "WHERE user_id=%s AND item_id=%s AND amount>0",
                    (user_id, plant_id),
                )
                if cursor.rowcount != 1:
                    self.connection.rollback()
                    return None

                values = {
                    "user_id": user_id, "plot_no": plot_no, "plant_id": plant_id,
                    "magic_id": 0, "state": 1, "level": 1, "experience": 0,
                    "quality": 100, "pollen_count": 0, "flower_count": 0, "seed_count": 0,
                    "tool_state": 0, "tool_time": 0, "pot_id": pot_id, "pollen_type": 0,
                    "flower_id": flower_id, "pollen_id": pollen_id,
                    "nutrient": nutrient, "moisture": moisture, "x": x, "y": y,
                    "owner_id": user_id, "next_state": 2, "next_level": 2, "next_time": next_time,
                    "dust_count": 0, "grass": 0, "item_use_flag": 0, "add_flower_flag": 0,
                }
                if plant:
                    cursor.execute(
                        "UPDATE player_home_plants SET plant_id=%s, magic_id=0, state=1, level=1, "
                        "experience=0, quality=100, pollen_id=%s, pollen_count=0, flower_id=%s, flower_count=0, seed_count=0, "
                        "tool_state=0, tool_time=0, pollen_type=0, nutrient=%s, moisture=%s, "
                        "x=%s, y=%s, owner_id=%s, next_state=2, next_level=2, next_time=%s, "
                        "dust_count=0, grass=0, item_use_flag=0, add_flower_flag=0 "
                        "WHERE user_id=%s AND plot_no=%s",
                        (plant_id, pollen_id, flower_id, nutrient, moisture, x, y, user_id, next_time, user_id, plot_no),
                    )
                else:
                    cursor.execute(
                        "INSERT INTO player_home_plants "
                        "(user_id, plot_no, plant_id, magic_id, state, level, experience, quality, pollen_id, "
                        "pollen_count, flower_id, flower_count, seed_count, tool_state, tool_time, pot_id, pollen_type, "
                        "nutrient, moisture, x, y, owner_id, next_state, next_level, next_time, dust_count, "
                        "grass, item_use_flag, add_flower_flag) "
                        "VALUES (%(user_id)s, %(plot_no)s, %(plant_id)s, %(magic_id)s, %(state)s, %(level)s, "
                        "%(experience)s, %(quality)s, %(pollen_id)s, %(pollen_count)s, %(flower_id)s, %(flower_count)s, %(seed_count)s, "
                        "%(tool_state)s, %(tool_time)s, %(pot_id)s, %(pollen_type)s, %(nutrient)s, %(moisture)s, "
                        "%(x)s, %(y)s, %(owner_id)s, %(next_state)s, %(next_level)s, %(next_time)s, "
                        "%(dust_count)s, %(grass)s, %(item_use_flag)s, %(add_flower_flag)s)",
                        values,
                    )
                cursor.execute(
                    "SELECT * FROM player_home_plants WHERE user_id=%s AND plot_no=%s",
                    (user_id, plot_no),
                )
                saved = cursor.fetchone()
            self.connection.commit()
            return saved
        except Exception:
            self.connection.rollback()
            raise

    def use_home_plant_tool(self, user_id: int, plot_no: int, tool_id: int):
        """Consume a home tool and apply it to a plant atomically."""
        self._ensure_connection()
        user_id, plot_no, tool_id = map(int, (user_id, plot_no, tool_id))
        try:
            self.connection.begin()
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT tool_type, add_water_num, add_nutrition_num "
                    "FROM type_home_props WHERE id=%s LIMIT 1",
                    (tool_id,),
                )
                catalog = cursor.fetchone()
                if not catalog or catalog.get("tool_type") is None:
                    self.connection.rollback()
                    return None
                tool_type = int(catalog["tool_type"])
                if tool_type not in (0, 1, 2, 3, 4, 6):
                    self.connection.rollback()
                    return None
                cursor.execute(
                    "SELECT amount FROM player_home_props WHERE user_id=%s AND item_id=%s FOR UPDATE",
                    (user_id, tool_id),
                )
                inventory = cursor.fetchone()
                if not inventory or int(inventory.get("amount", 0) or 0) < 1:
                    self.connection.rollback()
                    return None
                cursor.execute(
                    "SELECT * FROM player_home_plants WHERE user_id=%s AND plot_no=%s FOR UPDATE",
                    (user_id, plot_no),
                )
                plant = cursor.fetchone()
                if not plant:
                    self.connection.rollback()
                    return None
                cursor.execute(
                    "UPDATE player_home_props SET amount=amount-1 "
                    "WHERE user_id=%s AND item_id=%s AND amount>0",
                    (user_id, tool_id),
                )
                if cursor.rowcount != 1:
                    self.connection.rollback()
                    return None
                if tool_type == 2:
                    if int(plant.get("pot_id") or 0) != 0:
                        cursor.execute(
                            "UPDATE player_home_plants SET plant_id=0, state=0, level=0, "
                            "pollen_count=0, flower_count=0, seed_count=0, pollen_type=0, "
                            "nutrient=0, moisture=0, next_state=0, next_level=0, dust_count=0 "
                            "WHERE user_id=%s AND plot_no=%s",
                            (user_id, plot_no),
                        )
                        if cursor.rowcount != 1:
                            self.connection.rollback()
                            return None
                        cursor.execute(
                            "SELECT * FROM player_home_plants WHERE user_id=%s AND plot_no=%s",
                            (user_id, plot_no),
                        )
                        plant = cursor.fetchone()
                    else:
                        cursor.execute(
                            "DELETE FROM player_home_plants WHERE user_id=%s AND plot_no=%s",
                            (user_id, plot_no),
                        )
                        if cursor.rowcount != 1:
                            self.connection.rollback()
                            return None
                elif tool_type == 3:
                    flower_id = int(plant.get("flower_id") or 0)
                    flower_count = int(plant.get("flower_count") or 0)
                    cursor.execute(
                        "SELECT pet_id, exp_good, exp_bad, flower_out_put_id_1 "
                        "FROM seed_plant_parameters WHERE id=%s LIMIT 1",
                        (int(plant.get("plant_id") or 0),),
                    )
                    plant_parameters = cursor.fetchone() or {}
                    pet_id = max(0, int(plant_parameters.get("pet_id") or 0))
                    harvest_exp = max(0, int(plant_parameters.get("exp_good") or 0))
                    if pet_id:
                        # Element flowers produce a pet rather than an item.
                        # Keep the one-pet rule inside this transaction so two
                        # concurrent harvests cannot create duplicate pets.
                        cursor.execute(
                            "SELECT 1 FROM player_pets WHERE user_id=%s LIMIT 1 FOR UPDATE",
                            (user_id,),
                        )
                        if cursor.fetchone() is None:
                            cursor.execute(
                                "INSERT INTO player_pets "
                                "(user_id, pet_id, age, love_energy, nickname, hungry_index, "
                                "clean_index, mood_index, health_state, is_vip, wonderful_value, "
                                "skills_json, rest_at) "
                                "VALUES (%s, %s, %s, 0, %s, 5000000, 5000000, 5000000, 0, 0, 0, %s, 0)",
                                (user_id, pet_id, int(time.time()), "宠物", "{}"),
                            )
                        harvest_result = {"pet_id": pet_id, "exp": harvest_exp}
                    else:
                        flowers = []
                        if flower_id and flower_count > 0:
                            flowers.append({"id": flower_id, "amount": flower_count})
                        seed_id = int(plant.get("plant_id") or 0) if int(plant.get("seed_count") or 0) > 0 else 0
                        harvest_result = {
                            "flowers": flowers,
                            "seed_id": seed_id,
                            "exp": harvest_exp,
                        }
                    if flower_id and flower_count > 0:
                        cursor.execute(
                            "INSERT INTO player_flowers (user_id, item_id, amount) "
                            "VALUES (%s, %s, %s) "
                            "ON DUPLICATE KEY UPDATE amount=amount+VALUES(amount)",
                            (user_id, flower_id, flower_count),
                        )
                    cursor.execute(
                        "DELETE FROM player_home_plants WHERE user_id=%s AND plot_no=%s",
                        (user_id, plot_no),
                    )
                    if cursor.rowcount != 1:
                        self.connection.rollback()
                        return None
                else:
                    updates = {}
                    plant_parameters = None
                    if tool_type in (0, 1, 4):
                        cursor.execute(
                            "SELECT moisture_max, nutrient_max "
                            "FROM seed_plant_parameters WHERE id=%s LIMIT 1",
                            (int(plant.get("plant_id") or 0),),
                        )
                        plant_parameters = cursor.fetchone()
                        if not plant_parameters:
                            self.connection.rollback()
                            return None
                        moisture_max = max(0, int(plant_parameters.get("moisture_max") or 0)) * 100000
                        nutrient_max = max(0, int(plant_parameters.get("nutrient_max") or 0)) * 100000
                    if tool_type in (0, 4):
                        updates["moisture"] = min(
                            moisture_max,
                            int(plant.get("moisture") or 0)
                            + max(0, int(catalog.get("add_water_num") or 0)) * 100000,
                        )
                    if tool_type in (1, 4):
                        updates["nutrient"] = min(
                            nutrient_max,
                            int(plant.get("nutrient") or 0)
                            + max(0, int(catalog.get("add_nutrition_num") or 0)) * 100000,
                        )
                    if tool_type in (4, 6):
                        updates["state"] = 6 if int(plant.get("level") or 0) in (5, 6, 7) else 1
                    if updates:
                        assignments = ", ".join(f"{column}=%s" for column in updates)
                        cursor.execute(
                            f"UPDATE player_home_plants SET {assignments} "
                            "WHERE user_id=%s AND plot_no=%s",
                            (*updates.values(), user_id, plot_no),
                        )
                    cursor.execute(
                        "SELECT * FROM player_home_plants WHERE user_id=%s AND plot_no=%s",
                        (user_id, plot_no),
                    )
                    plant = cursor.fetchone()
            self.connection.commit()
            if tool_type == 3:
                return {
                    "tool_type": tool_type,
                    "plot_no": plot_no,
                    "tool_id": tool_id,
                    "plant": harvest_result,
                }
            return {"tool_type": tool_type, "plot_no": plot_no, "tool_id": tool_id, "plant": plant}
        except Exception:
            self.connection.rollback()
            raise

    def clothes(self, user_id: int):
        """Return the player's owned decoration IDs in deterministic order."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
            "SELECT cloth_id FROM player_clothes WHERE user_id=%s ORDER BY cloth_id",
            (int(user_id),),)
        return [int(row["cloth_id"]) for row in (cursor.fetchall() or [])]

    def user_background(self, user_id: int):
        """Return the selected personal background, or zero when unset."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT background_id FROM player_homes WHERE user_id=%s LIMIT 1",
                (int(user_id),),
            )
            row = cursor.fetchone()
            return int((row or {}).get("background_id", 0) or 0) & 0xFFFFFFFF

    def user_backgrounds(self, user_id: int):
        """Return background IDs owned by the player in stable order."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT pc.cloth_id AS item_id "
                "FROM player_clothes pc INNER JOIN type_home_bg bg ON bg.id=pc.cloth_id "
                "WHERE pc.user_id=%s ORDER BY pc.cloth_id",
                (int(user_id),),
            )
            return [int(row["item_id"]) for row in (cursor.fetchall() or [])]

    def suitings(self, user_id: int):
        """Return saved 13-part outfits ordered by their client-visible slot."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM player_suitings WHERE user_id=%s ORDER BY slot_index",
                (int(user_id),),
            )
        return list(cursor.fetchall() or [])

    def actions(self, user_id: int):
        """Return the player's available type-19 magic actions."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT action_id, amount FROM player_magics "
                "WHERE user_id=%s AND amount>0 ORDER BY action_id",
                (int(user_id),),
            )
            return list(cursor.fetchall() or [])

    def consume_action(self, user_id: int, action_id: int) -> bool:
        """Atomically consume one owned type-19 magic action."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE player_magics SET amount=amount-1 "
                "WHERE user_id=%s AND action_id=%s AND amount>0",
                (int(user_id), int(action_id)),
            )
            return cursor.rowcount == 1

    def add_flower_game_reward(self, user_id: int, item_id: int, amount: int) -> None:
        """Add a validated flower-game reward to the player's inventory.

        The mini-game can offer normal catalog items from these three stores.
        Keeping the table mapping here prevents a client supplied item id from
        becoming an SQL identifier and makes the grant atomic with the row
        upsert.
        """
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            self._add_material_game_reward(cursor, user_id, item_id, amount)

    @staticmethod
    def _add_material_game_reward(cursor, user_id: int, item_id: int, amount: int) -> None:
        user_id, item_id, amount = int(user_id), int(item_id), int(amount)
        if amount <= 0:
            raise ValueError("reward amount must be positive")
        table_by_item = {
            1600001: ("player_materials", "type_materials"),
            1600002: ("player_materials", "type_materials"),
            1600003: ("player_materials", "type_materials"),
        }
        table_info = table_by_item.get(item_id)
        if table_info is None:
            raise ValueError(f"unsupported flower-game reward item: {item_id}")
        player_table, catalog_table = table_info
        cursor.execute(
            f"SELECT 1 FROM {catalog_table} WHERE id=%s LIMIT 1",
            (item_id,),
        )
        if cursor.fetchone() is None:
            raise ValueError(f"flower-game reward item is not in the catalog: {item_id}")
        cursor.execute(
            f"INSERT INTO {player_table} (user_id, item_id, amount) VALUES (%s,%s,%s) "
            "ON DUPLICATE KEY UPDATE amount=amount+VALUES(amount)",
            (user_id, item_id, amount),
        )

    def add_pve_game_rewards(self, user_id: int, rewards) -> None:
        """Grant the configured PVE materials together, or roll back all."""
        self._ensure_connection()
        try:
            self.connection.begin()
            with self.connection.cursor() as cursor:
                for item_id, amount in rewards:
                    self._add_material_game_reward(cursor, user_id, item_id, amount)
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def add_suiting(self, user_id: int, cloth_ids, max_slots: int = 5) -> int:
        """Save one 13-part outfit and return its client-visible index."""
        self._ensure_connection()
        user_id = int(user_id)
        values = tuple(int(value) & 0xFFFFFFFF for value in cloth_ids)
        if len(values) != 13:
            raise SuitingError("a suiting must contain exactly 13 cloth ids")
        max_slots = int(max_slots)
        if max_slots < 1:
            raise SuitingError("invalid suiting limit")
        try:
            self.connection.begin()
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT slot_index FROM player_suitings "
                    "WHERE user_id=%s ORDER BY slot_index FOR UPDATE",
                    (user_id,),
                )
                used = {int(row["slot_index"]) for row in (cursor.fetchall() or [])}
                if len(used) >= max_slots:
                    raise SuitingError("suiting limit reached", status=181)
                slot_index = 1
                while slot_index in used:
                    slot_index += 1
                columns = ("user_id", "slot_index") + (
                    "tool_id", "headdress_id", "mask_id", "hair_id", "earring_id",
                    "necklace_id", "belt_id", "cloth_id", "bangle_id", "shoes_id",
                    "anklet_id", "skirt_id", "wing_id",
                )
                placeholders = ",".join(["%s"] * len(columns))
                cursor.execute(
                    f"INSERT INTO player_suitings ({','.join(columns)}) "
                    f"VALUES ({placeholders})",
                    (user_id, slot_index, *values),
                )
            self.connection.commit()
            return slot_index
        except Exception:
            self.connection.rollback()
            raise

    def delete_suiting(self, user_id: int, slot_index: int) -> None:
        """Delete one saved outfit belonging to the requesting player."""
        self._ensure_connection()
        user_id = int(user_id)
        slot_index = int(slot_index) & 0xFFFFFFFF
        try:
            self.connection.begin()
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT slot_index FROM player_suitings "
                    "WHERE user_id=%s AND slot_index=%s FOR UPDATE",
                    (user_id, slot_index),
                )
                if not cursor.fetchone():
                    raise SuitingError("suiting does not exist", status=404)
                cursor.execute(
                    "DELETE FROM player_suitings WHERE user_id=%s AND slot_index=%s",
                    (user_id, slot_index),
                )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def change_clothing(self, user_id: int, changes):
        """Atomically apply CLOTH_CHANGE records and return response triples."""
        self._ensure_connection()
        user_id = int(user_id)
        ids = list(dict.fromkeys(int(cloth_id) for cloth_id, _ in changes))
        placeholders = ",".join(["%s"] * len(ids))

        try:
            self.connection.begin()
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT clothing_json FROM player_profiles "
                    "WHERE user_id=%s LIMIT 1 FOR UPDATE",
                    (user_id,),
                )
                profile_row = cursor.fetchone()
                if not profile_row:
                    raise ClothingChangeError("player profile does not exist")

                raw = profile_row.get("clothing_json")
                try:
                    clothing = json.loads(raw) if raw else {}
                except (TypeError, ValueError) as exc:
                    raise ClothingChangeError("invalid clothing_json") from exc
                if not isinstance(clothing, dict):
                    raise ClothingChangeError("clothing_json is not an object")

                cursor.execute(
                    f"SELECT * FROM player_clothes WHERE user_id=%s "
                    f"AND cloth_id IN ({placeholders})",
                    (user_id, *ids),
                )
                owned = {int(row["cloth_id"]): row for row in cursor.fetchall()}
                if set(ids) != set(owned):
                    raise ClothingChangeError("player does not own every requested cloth")

                records = []
                for cloth_id, action in changes:
                    row = owned[cloth_id]
                    cloth_type = (
                            row.get("cloth_type")
                            or row.get("clothing_type")
                            or row.get("slot_type")
                            or self.cloth_types.get(cloth_id)
                    )
                    if not cloth_type and action == 0:
                        cloth_type = next(
                            (kind for kind, slot in CLOTHING_SLOT_BY_TYPE.items()
                             if int(clothing.get(slot, 0) or 0) == cloth_id),
                            None,
                        )
                    slot = CLOTHING_SLOT_BY_TYPE.get(int(cloth_type or 0))
                    if slot is None:
                        raise ClothingChangeError(
                            f"cloth {cloth_id} has no client ClothType metadata"
                        )

                    previous = int(clothing.get(slot, 0) or 0)
                    if action == 1:
                        clothing[slot] = cloth_id
                        down_id = previous if previous != cloth_id else 0
                    else:
                        if previous != cloth_id:
                            raise ClothingChangeError(
                                f"cloth {cloth_id} is not equipped in {slot}"
                            )
                        clothing[slot] = 0
                        down_id = 0
                    records.append((cloth_id, action, down_id))
                cursor.execute(
                    "UPDATE player_profiles SET clothing_json=%s WHERE user_id=%s",
                    (json.dumps(clothing, ensure_ascii=False, separators=(",", ":")), user_id),
                )
            self.connection.commit()
            return clothing, records
        except Exception:
            self.connection.rollback()
            raise

    def get_once_flag(self, user_id: int, flag_id: int) -> int:
        """Return a persisted COMMON_ONCE_FLAG value, defaulting to zero."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT flag_value FROM player_once_flags WHERE user_id=%s AND flag_id=%s LIMIT 1",
                (int(user_id), int(flag_id)),
            )
            row = cursor.fetchone()
        return int((row or {}).get("flag_value", 0))

    def set_once_flag(self, user_id: int, flag_id: int, value: int = 1) -> None:
        """Persist a COMMON_SET_FLAG value."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO player_once_flags (user_id, flag_id, flag_value) VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE flag_value=VALUES(flag_value)",
                (int(user_id), int(flag_id), int(value) & 0xFF),
            )

    def set_login_location(self, user_id: int, location: int) -> None:
        """Store the latest ClientConfig.REG_location value from cmd 2163."""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO player_login_locations (user_id, location) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE location=VALUES(location)",
                (int(user_id), int(location) & 0xFFFFFFFF),
            )

    def servers(self, start: Optional[int] = None, end: Optional[int] = None):
        """Return enabled login targets from the existing game_servers table."""
        self._ensure_connection()
        sql = "SELECT * FROM game_servers WHERE enabled=1"
        params = []
        if start is not None and end is not None:
            sql += " AND id BETWEEN %s AND %s"
            params.extend((start, end))
        sql += " ORDER BY id"
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            return list(cursor.fetchall() or [])

    def use_pet_supply(self, user_id: int, pet_id: int, item_id: int):
        """Atomically validate, consume and apply one pet supply."""
        self._ensure_connection()
        user_id, pet_id, item_id = int(user_id), int(pet_id), int(item_id)
        try:
            self.connection.begin()
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM player_pets WHERE user_id=%s AND pet_id=%s LIMIT 1 FOR UPDATE",
                    (user_id, pet_id),
                )
                pet = cursor.fetchone()
                if not pet:
                    self.connection.rollback()
                    return 404, None

                cursor.execute(
                    "SELECT amount FROM player_pet_supplies "
                    "WHERE user_id=%s AND item_id=%s LIMIT 1 FOR UPDATE",
                    (user_id, item_id),
                )
                inventory = cursor.fetchone()
                if not inventory or int(inventory.get("amount", 0) or 0) < 1:
                    self.connection.rollback()
                    return 10005, None

                cursor.execute(
                    "SELECT energy, hungry, sanitary, spirit, grade "
                    "FROM type_pet_supplies WHERE id=%s LIMIT 1",
                    (item_id,),
                )
                supply = cursor.fetchone()
                if not supply:
                    self.connection.rollback()
                    return 404, None

                energy = int(pet.get("love_energy", 0) or 0)
                pet_grade = 1 if energy < 300 else 2 if energy < 1500 else 3
                allowed_grades = {
                    int(value.strip())
                    for value in str(supply.get("grade", "")).split(",")
                    if value.strip().isdigit()
                }
                if pet_grade not in allowed_grades:
                    self.connection.rollback()
                    return 10006, None

                hungry = int(pet.get("hungry_index", 0) or 0) + int(supply.get("hungry", 0) or 0) * 100000
                clean = int(pet.get("clean_index", 0) or 0) + int(supply.get("sanitary", 0) or 0) * 100000
                mood = int(pet.get("mood_index", 0) or 0) + int(supply.get("spirit", 0) or 0) * 100000
                hungry = min(hungry, 10000000)
                clean = min(clean, 10000000)
                mood = min(mood, 10000000)
                love_energy = energy + int(supply.get("energy", 0) or 0)
                health_state = int(pet.get("health_state", 0) or 0)
                if item_id == 800018:
                    health_state = 0

                cursor.execute(
                    "UPDATE player_pet_supplies SET amount=amount-1 "
                    "WHERE user_id=%s AND item_id=%s AND amount>0",
                    (user_id, item_id),
                )
                if cursor.rowcount != 1:
                    self.connection.rollback()
                    return 10005, None
                cursor.execute(
                    "UPDATE player_pets SET hungry_index=%s, clean_index=%s, mood_index=%s, "
                    "love_energy=%s, health_state=%s WHERE user_id=%s AND pet_id=%s",
                    (hungry, clean, mood, love_energy, health_state, user_id, pet_id),
                )
                result = {
                    "hungry_index": hungry,
                    "clean_index": clean,
                    "mood_index": mood,
                    "love_energy": love_energy,
                    # Supplies do not impose an energy cap; show the normal client bar.
                    "love_up_limit": 0,
                }
            self.connection.commit()
            return 0, result
        except Exception:
            self.connection.rollback()
            raise
