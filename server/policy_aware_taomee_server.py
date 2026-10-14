# Flash Player may probe the target socket with this request before sending
# binary entity. It must be handled on the login port itself; otherwise the first
# four ASCII bytes ("<pol") are mistaken for a packet length (1014001516).
import asyncio

from server.taomee_server import TaomeeServer, ClientSession

SOCKET_POLICY_REQUEST = b"<policy-file-request/>\0"
SOCKET_POLICY_RESPONSE = (
    b'<?xml version="1.0"?>'
    b'<!DOCTYPE cross-domain-policy SYSTEM "http://www.adobe.com/xml/dtds/cross-domain-policy.dtd">'
    b'<cross-domain-policy><allow-access-from domain="*" to-ports="*" /></cross-domain-policy>\0'
)


class PolicyAwareTaomeeServer(TaomeeServer):

    async def _accept(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            prefix = await reader.readexactly(4)
        except asyncio.IncompleteReadError:
            writer.close()
            await writer.wait_closed()
            return
        if prefix == b"<pol":
            try:
                suffix = await asyncio.wait_for(reader.readuntil(b"\0"), timeout=5)
                if prefix + suffix == SOCKET_POLICY_REQUEST:
                    writer.write(SOCKET_POLICY_RESPONSE)
                    await writer.drain()
            except (asyncio.IncompleteReadError, asyncio.LimitOverrunError, asyncio.TimeoutError):
                pass
            finally:
                writer.close()
                await writer.wait_closed()
            return
        await ClientSession(reader, writer, self.codec).run(self.handlers, self.default_handler, initial_length=prefix)
