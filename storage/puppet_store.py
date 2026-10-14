"""Database access for the per-user puppet state."""

from __future__ import annotations



def fetch_puppet(connection, user_id: int) -> dict:
    """Return one user's puppet state, defaulting to no puppet."""
    user_id = int(user_id) & 0xFFFFFFFF
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT user_id, puppet_id, follow_flag, rest_tech_point, flower_num, "
            "love_value, kind_value, evil_value "
            "FROM player_puppets WHERE user_id=%s LIMIT 1",
            (user_id,),
        )
        row = cursor.fetchone()
    return row or {
        "user_id": user_id,
        "puppet_id": 0,
        "follow_flag": 0,
        "rest_tech_point": 0,
        "flower_num": 0,
        "love_value": 0,
        "kind_value": 0,
        "evil_value": 0,
    }
