from __future__ import annotations

import argparse
import asyncio
import logging

from storage.account_store import AccountStore
from application.hua_login_application import HuaLoginApplication
from application.hua_online_application import HuaOnlineApplication
from server.policy_aware_taomee_server import PolicyAwareTaomeeServer
from server.taomee_server import TaomeeCodec


async def serve(args):

    accounts = AccountStore(
        args.mysql_host,
        args.mysql_port,
        args.mysql_user,
        args.mysql_password,
        args.mysql_database
    )

    login_server = PolicyAwareTaomeeServer(
        args.host,
        args.port,
        TaomeeCodec()
    )

    login_app = HuaLoginApplication(
        accounts,
        args.online_host,
        args.online_port,
        1,
        args.session_ttl
    )

    login_app.install(login_server)

    online_server = PolicyAwareTaomeeServer(
        args.host,
        args.online_port,
        TaomeeCodec()
    )

    online_app = HuaOnlineApplication(
        accounts,
        login_app.sessions,
        getattr(args, "shop_half_price_day", 0),
    )

    online_app.install(online_server)

    try:
        await asyncio.gather(login_server.start(), online_server.start())
    finally:
        accounts.close()


def main():

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8430)
    parser.add_argument("--mysql-host", default="127.0.0.1")
    parser.add_argument("--mysql-port", type=int, default=3306)
    parser.add_argument("--mysql-user", default="root")
    parser.add_argument("--mysql-password", default="root")
    parser.add_argument("--mysql-database", default="hua_2013")
    parser.add_argument("--online-host", default="127.0.0.1")
    parser.add_argument("--online-port", type=int, default=8431)
    parser.add_argument("--server-id", type=int, default=1)
    parser.add_argument("--session-ttl", type=int, default=300)
    parser.add_argument(
        "--shop-half-price-day",
        type=int,
        default=0,
        help="day of month for the shop half-price promotion; 0 disables it",
    )
    parser.add_argument("--debug", action="store_true", default=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    try:
        asyncio.run(serve(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
