import hmac
import struct

from constant.command_id import *
from entity.response import Response
from exception.protocol_error import ProtocolError
from log.log import LOG
from parse_login_request import parse_login_request
from storage.account_store import AccountStore
from storage.session_store import SessionStore
from stream import fixed_utf8, _u32


class HuaLoginApplication:

    def __init__(self, accounts: AccountStore, online_host: str, online_port: int, server_id: int, session_ttl: int):
        self.accounts = accounts
        self.online_host = online_host
        self.online_port = online_port
        self.server_id = server_id
        self.sessions = SessionStore(session_ttl)

    def install(self, server):
        server.on(CMD_CAPTCHA, self.captcha)
        server.on(CMD_LOGIN, self.login)
        server.on(CMD_SERVER_LIST, self.server_list)
        server.on(CMD_MORE_SERVER_LIST, self.more_server_list)
        server.on(CMD_ROLE_CREATED, self.role_created)

    @staticmethod
    def captcha(_session, packet):
        return Response(struct.pack(">I", 0), user_id=packet.user_id)

    def login(self, session, packet):
        try:
            request = parse_login_request(packet)
            if request.game_id != 5:
                return Response(user_id=packet.user_id, status=RESULT_SYSTEM_ERROR)
            account = self.accounts.get(request.login_name)
        except (ProtocolError, UnicodeError, ValueError):
            return Response(user_id=packet.user_id, status=RESULT_SYSTEM_ERROR)
        if account is None:
            return Response(user_id=packet.user_id, status=RESULT_NO_ACCOUNT)
        if account.banned:
            return Response(user_id=account.user_id, status=RESULT_BANNED)
        if not hmac.compare_digest(account.password_hash.lower(), request.password_hash):
            return Response(user_id=account.user_id, status=RESULT_BAD_PASSWORD)
        token = self.sessions.issue(account.user_id)
        session.state.update(user_id=account.user_id, session_token=token, role_created=account.role_created)
        return Response(struct.pack(">I", 0) + token + struct.pack(">I", int(account.role_created)), user_id=account.user_id)

    def _auth(self, session, packet):
        return session.state.get("user_id") == packet.user_id and len(packet.payload) >= 16 and self.sessions.valid(packet.payload[:16], packet.user_id)

    def server_list(self, session, packet):
        if not self._auth(session, packet):
            return Response(user_id=packet.user_id, status=401)
        try:
            rows = self.accounts.servers()
        except Exception as exc:
            LOG.warning("game_servers query failed: %s", exc)
            rows = []
        payload = struct.pack(">I", len(rows))
        for row in rows:
            payload += struct.pack(">II", _u32(row['id']), _u32(row['user_rate']))
            payload += fixed_utf8(row['ip'], 16)
            payload += struct.pack(">H", _u32(row['port']) & 0xffff)
            payload += struct.pack(">I", _u32(row['friends']))
        first = rows[0]
        payload += struct.pack(">II", _u32(first['server_num']), _u32(first['vip']))
        return Response(payload, user_id=packet.user_id)

    def more_server_list(self, session, packet):
        if session.state.get("user_id") != packet.user_id:
            return Response(user_id=packet.user_id, status=401)
        start = end = None
        if len(packet.payload) >= 8:
            start, end = struct.unpack_from(">II", packet.payload)
        try:
            rows = self.accounts.servers(start, end)
        except Exception as exc:
            LOG.warning("game_servers range query failed: %s", exc)
            rows = []
        if not rows:
            rows = [{"id": self.server_id, "user_rate": 0, "ip": self.online_host, "port": self.online_port}]
        payload = struct.pack(">I", len(rows))
        for row in rows:
            payload += struct.pack(">II", _u32(row.get("id")), _u32(row.get("user_rate")))
            payload += fixed_utf8(str(row.get("ip", self.online_host)), 16)
            payload += struct.pack(">H", _u32(row.get("port", self.online_port)) & 0xffff)
        return Response(payload, user_id=packet.user_id)

    def role_created(self, session, packet):
        if session.state.get("user_id") != packet.user_id:
            return Response(user_id=packet.user_id, status=401)
        return Response(struct.pack(">I", int(bool(session.state.get("role_created", True)))), user_id=packet.user_id)
