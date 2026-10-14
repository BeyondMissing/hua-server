"""Database access for the static NPC and NPC-job catalogs."""

from __future__ import annotations


_TASK_INVENTORY_TYPES = {
    2: ("player_seeds", "item_id", "amount"),
    5: ("player_house_goods", "item_id", "COUNT(*)"),
    7: ("player_flowers", "item_id", "amount"),
    8: ("player_pet_supplies", "item_id", "amount"),
    11: ("player_task_items", "item_id", "amount"),
    13: ("player_pollens", "pollen_id", "amount"),
    16: ("player_materials", "item_id", "amount"),
}


def _npc_job_protocol_type(job_type: int) -> int:
    """Return the value expected in ``Res_NPCJOB_INFO.Type``.

    ``type_npc_jobs.job_type`` is the task-book category copied from the
    task XML.  The 1057 packet uses the same field for a *client control
    mode*: ``0`` makes ``NPCModule.clickBack`` skip ``NPCJobView`` and show
    ``beginjob_tip_talk`` directly.  The legacy task data contains ordinary
    multi-step jobs (notably jobs 10--13 and 16, including ``美丽的裙子``)
    with category 0; their ``beginjob_tip_talk`` is intentionally ``0``.
    Sending that category unchanged therefore opens a dummy dialog and never
    starts the task.  Normal NPC jobs must use the regular job-view mode (2).
    Other category values retain their historical meaning.
    """
    value = int(job_type)
    return 2 if value == 0 else value


def _task_item_type(item_id: int) -> int | None:
    """Extract the inventory type prefix from an item's five-digit suffix."""
    item_text = str(int(item_id))
    if len(item_text) <= 5:
        return None
    try:
        item_type = int(item_text[:-5])
    except ValueError:
        return None
    return item_type if item_type in _TASK_INVENTORY_TYPES else None


def _parse_task_items(value) -> list[tuple[int, int]]:
    """Parse task item strings such as ``8/1100048;1/1100049``."""
    items = []
    for entry in str(value or "").split(";"):
        if not entry or entry == "0":
            continue
        try:
            amount_text, item_text = entry.split("/", 1)
            amount, item_id = int(amount_text), int(item_text)
        except (TypeError, ValueError):
            continue
        if amount > 0 and item_id > 0:
            items.append((amount, item_id))
    return items


def _task_inventory_amounts(connection, user_id: int, item_ids: set[int]) -> dict[int, int]:
    """Load inventory quantities for the supported task-item type prefixes."""
    grouped: dict[tuple[str, str, str], set[int]] = {}
    for item_id in item_ids:
        item_type = _task_item_type(item_id)
        if item_type is None:
            continue
        definition = _TASK_INVENTORY_TYPES[item_type]
        grouped.setdefault(definition, set()).add(int(item_id))

    amounts = {int(item_id): 0 for item_id in item_ids}
    with connection.cursor() as cursor:
        for (table, column, amount_expression), grouped_ids in grouped.items():
            placeholders = ",".join(["%s"] * len(grouped_ids))
            if table == "player_house_goods":
                query = (
                    f"SELECT {column} AS item_id, COUNT(*) AS amount "
                    f"FROM {table} WHERE user_id=%s AND is_set=0 "
                    f"AND {column} IN ({placeholders}) GROUP BY {column}"
                )
            else:
                query = (
                    f"SELECT {column} AS item_id, SUM({amount_expression}) AS amount "
                    f"FROM {table} WHERE user_id=%s AND {column} IN ({placeholders}) "
                    f"GROUP BY {column}"
                )
            cursor.execute(query, (int(user_id), *sorted(grouped_ids)))
            for row in cursor.fetchall() or ():
                amounts[int(row["item_id"])] = int(row.get("amount") or 0)
    return amounts


def _task_progress_from_inventory(connection, user_id: int, req_item) -> int | None:
    """Return inventory-backed progress, or ``None`` for unsupported IDs."""
    requirements = _parse_task_items(req_item)
    if not requirements:
        return None
    # A task can contain multiple requirements.  Only replace the stored
    # progress when every requirement has a known inventory mapping; an
    # unsupported requirement must preserve the legacy progress value.
    if any(_task_item_type(item_id) is None for _, item_id in requirements):
        return None
    supported = [item_id for _, item_id in requirements]
    amounts = _task_inventory_amounts(connection, user_id, set(supported))
    return sum(min(required, amounts.get(item_id, 0)) for required, item_id in requirements)


def fetch_npcs(connection, map_id: int) -> list[dict]:
    """Return rows using the names expected by the map packet encoder."""
    query = """
        SELECT id AS user_id, map_id, init_x AS map_x, init_y AS map_y,
               name AS nickname, nationality, skin AS face_color,
               face, eye, eyebrow, lip, tool, headdress, mask, hair,
               earring, necklace, belt, top AS cloth, bangle, shoes,
               anklet, bottom AS skirt, wing
        FROM type_npcs
        WHERE map_id=%s AND id BETWEEN 1 AND 49999
        ORDER BY id
    """
    with connection.cursor() as cursor:
        cursor.execute(query, (int(map_id),))
        return list(cursor.fetchall() or [])


def fetch_npc_jobs(connection, npc_id: int, user_id: int) -> list[dict]:
    """Return each active task's latest player-progress step at ``npc_id``.

    A catalog row is only visible when the player has a corresponding
    ``player_task_progress`` row.  The correlated ``MAX(step)`` lookup keeps
    one latest step per task, and completed tasks are removed before the rows
    are converted to the NPC-job packet shape.
    """
    query = """
        SELECT j.npc_id, j.job_id, j.step, j.role_mask, j.job_type,
               j.step_need, j.start_npc, j.finish_npc,
               p.flag, p.process, p.total_process, p.get_time,
               task.req_item
        FROM type_npc_jobs AS j
        LEFT JOIN task_list AS task
            ON task.main_id=j.job_id AND task.id=j.step
        INNER JOIN player_task_progress AS p
            ON p.user_id=%s
           AND p.job_id=j.job_id
           AND p.step=j.step
           AND p.step=(
               SELECT MAX(latest.step)
               FROM player_task_progress AS latest
               WHERE latest.user_id=%s
                 AND latest.job_id=j.job_id
           )
        WHERE j.npc_id=%s
          AND NOT EXISTS (
              SELECT 1
              FROM player_completed_tasks AS completed
              WHERE completed.user_id=p.user_id
                AND completed.job_id=p.job_id
          )
        ORDER BY j.job_id, j.step
    """
    with connection.cursor() as cursor:
        cursor.execute(query, (int(user_id), int(user_id), int(npc_id)))
        rows = cursor.fetchall() or []

    result = []
    for row in rows:
        inventory_progress = _task_progress_from_inventory(connection, user_id, row.get("req_item"))
        result.append({
            "job_id": int(row["job_id"]),
            "step": int(row["step"]),
            "type": _npc_job_protocol_type(row["job_type"]),
            "status": 1 if int(row.get("flag") or 0) else 0,
            "process": inventory_progress if inventory_progress is not None else int(row.get("process") or 0),
            "get_time": int(row.get("get_time") or 0),
            "total_process": int(row.get("total_process") or row["step_need"] or 0),
        })
    return result
