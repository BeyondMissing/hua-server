"""Taomee/Flash socket protocol server.

The AS3 client in this repository uses a big-endian, length-prefixed
framing protocol.  This module implements the framing, the reversible
MEncrypt/MDecrypt transform used by ``debugTestFlg`` and an asyncio TCP server.

The game-specific TMF classes are deliberately not hard-coded here: a Python
handler receives raw bytes and returns raw bytes, which is the only safe way to
support the many command schemas found in the client tree.
"""

from __future__ import annotations

import asyncio
from typing import Dict, Optional

from codec.taomee_codec import TaomeeCodec
from handler.handler import Handler
from log.log import LOG
from session.client_session import ClientSession


class TaomeeServer:

    def __init__(self, host: str = "0.0.0.0", port: int = 8430, codec: Optional[TaomeeCodec] = None):
        self.host = host
        self.port = port
        self.codec = codec or TaomeeCodec()
        self.handlers: Dict[int, Handler] = {}
        self.default_handler: Optional[Handler] = None
        self._server: Optional[asyncio.AbstractServer] = None

    def on(self, command_id: int, handler: Handler) -> Handler:
        self.handlers[command_id] = handler
        return handler

    async def _accept(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await ClientSession(reader, writer, self.codec).run(self.handlers, self.default_handler)

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._accept, self.host, self.port)
        sockets = self._server.sockets or []
        addresses = ", ".join(str(s.getsockname()) for s in sockets)
        LOG.info("Server listening on %s", addresses)
        async with self._server:
            await self._server.serve_forever()
