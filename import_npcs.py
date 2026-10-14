"""Import the client NPC XML into the ``type_npcs`` table.

Example:
    python import_npcs.py --mysql-password root
"""

from __future__ import annotations

import argparse
from pathlib import Path
from xml.etree import ElementTree

import pymysql

from storage.npc_store import NPC_TABLE_DDL


DEFAULT_XML = Path(
    r"E:\AS3Projects\hua_scripts\scripts_2013\_assets\4_newuserjob.Npcs_xmlCls_newuserjob.Npcs_xmlCls.bin"
)

NUMERIC_COLUMNS = (
    "id", "sex", "map_id", "init_x", "init_y", "face", "skin", "eyebrow",
    "eye", "lip", "tool", "headdress", "mask", "hair", "earring", "necklace",
    "belt", "top", "bangle", "shoes", "anklet", "bottom", "wing", "nationality",
    "hide", "org_talk", "near_width", "near_height",
)


def _uint(attrs: dict[str, str], name: str) -> int:
    try:
        return int(attrs.get(name, 0) or 0) & 0xFFFFFFFF
    except (TypeError, ValueError):
        return 0


def read_npcs(path: Path) -> list[tuple]:
    root = ElementTree.parse(path).getroot()
    rows = []
    for node in root.findall("npc"):
        attrs = node.attrib
        values = [_uint(attrs, column) for column in NUMERIC_COLUMNS]
        values.insert(1, attrs.get("name", ""))
        values.append(attrs.get("dancePartyTopic", ""))
        rows.append(tuple(values))
    return rows


def import_npcs(connection, rows: list[tuple]) -> int:
    columns = ("id", "name", "sex", "map_id", "init_x", "init_y", "face", "skin",
               "eyebrow", "eye", "lip", "tool", "headdress", "mask", "hair",
               "earring", "necklace", "belt", "top", "bangle", "shoes", "anklet",
               "bottom", "wing", "nationality", "hide", "org_talk", "near_width",
               "near_height", "dance_party_topic")
    placeholders = ",".join(["%s"] * len(columns))
    sql = (
        f"INSERT INTO type_npcs ({','.join(columns)}) VALUES ({placeholders}) "
        "ON DUPLICATE KEY UPDATE "
        + ",".join(f"{column}=VALUES({column})" for column in columns[1:])
    )
    with connection.cursor() as cursor:
        cursor.execute(NPC_TABLE_DDL)
        cursor.executemany(sql, rows)
    connection.commit()
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xml", type=Path, default=DEFAULT_XML)
    parser.add_argument("--mysql-host", default="127.0.0.1")
    parser.add_argument("--mysql-port", type=int, default=3306)
    parser.add_argument("--mysql-user", default="root")
    parser.add_argument("--mysql-password", default="root")
    parser.add_argument("--mysql-database", default="hua_2013")
    args = parser.parse_args()

    rows = read_npcs(args.xml)
    connection = pymysql.connect(
        host=args.mysql_host,
        port=args.mysql_port,
        user=args.mysql_user,
        password=args.mysql_password,
        database=args.mysql_database,
        charset="utf8mb4",
        autocommit=False,
    )
    try:
        count = import_npcs(connection, rows)
    finally:
        connection.close()
    print(f"Imported {count} NPC records from {args.xml}")


if __name__ == "__main__":
    main()
