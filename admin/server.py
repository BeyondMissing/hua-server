"""Hua 2013 account administration server entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from admin.config import ADMIN_USERNAME
from admin.database.accounts import AccountRepository
from admin.database.actions import ActionsRepository
from admin.database.clothes import ClothesRepository
from admin.database.house_goods import HouseGoodsRepository
from admin.database.inventories import InventoryRepository
from admin.database.profiles import ProfileRepository
from admin.database.pets import PetRepository
from admin.database.gardens import GardenRepository
from admin.database.houses import HouseRepository
from admin.database.tasks import TaskRepository
from admin.web.server import AdminServer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hua 2013 account administration")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--mysql-host", default="127.0.0.1")
    parser.add_argument("--mysql-port", type=int, default=3306)
    parser.add_argument("--mysql-user", default="root")
    parser.add_argument("--mysql-password", default="root")
    parser.add_argument("--mysql-database", default="hua_2013")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    mysql_config = {
        "host": args.mysql_host,
        "port": args.mysql_port,
        "user": args.mysql_user,
        "password": args.mysql_password,
        "database": args.mysql_database,
    }
    accounts = AccountRepository(mysql_config)
    clothes = ClothesRepository(mysql_config)
    house_goods = HouseGoodsRepository(mysql_config)
    actions = ActionsRepository(mysql_config)
    flowers = InventoryRepository(mysql_config, "flowers")
    seeds = InventoryRepository(mysql_config, "seeds")
    materials = InventoryRepository(mysql_config, "materials")
    pet_supplies = InventoryRepository(mysql_config, "pet-supplies")
    tools = InventoryRepository(mysql_config, "tools")
    pollens = InventoryRepository(mysql_config, "pollens")
    profiles = ProfileRepository(mysql_config)
    gardens = GardenRepository(mysql_config)
    houses = HouseRepository(mysql_config)
    tasks = TaskRepository(mysql_config)
    pets = PetRepository(mysql_config)
    server = AdminServer((args.host, args.port), accounts, clothes, profiles, house_goods, actions, flowers, seeds, materials, gardens, pets, pet_supplies, tools, pollens, houses, tasks)
    print(
        f"Hua admin listening on http://{args.host}:{args.port}/ "
        f"(login: {ADMIN_USERNAME})"
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        accounts.close()
        clothes.close()
        profiles.close()
        house_goods.close()
        actions.close()
        flowers.close()
        seeds.close()
        materials.close()
        gardens.close()
        pets.close()
        pet_supplies.close()
        tools.close()
        pollens.close()
        houses.close()
        tasks.close()


if __name__ == "__main__":
    main()
