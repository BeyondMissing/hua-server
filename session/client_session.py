import asyncio
import struct
from typing import Dict, Optional

from codec.taomee_codec import TaomeeCodec
from constant.consts import MAX_PACKET
from entity.response import Response
from exception.protocol_error import ProtocolError
from handler.handler import Handler
from log.log import LOG
from utils import byte_arr_to_hex


class ClientSession:

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, codec: TaomeeCodec):
        self.reader = reader
        self.writer = writer
        self.codec = codec
        self.send_lock = asyncio.Lock()
        self.peer = writer.get_extra_info("peername")
        self.state: Dict[str, object] = {}

    async def send(self, command_id: int, *, user_id: int, sequence: int = 0, result: int = 0, payload: bytes = b"") -> None:
        frame = self.codec.encode(command_id, user_id, sequence, result, bytes(payload))
        async with self.send_lock:
            self.writer.write(frame)
            await self.writer.drain()

    async def send_response(self, command_id: int, *, user_id: int, status: int = 0, error: int = 0, payload: bytes = b"") -> None:
        frame = self.codec.encode_response(command_id, user_id, status=status, error=error, payload=bytes(payload))
        async with self.send_lock:
            self.writer.write(frame)
            LOG.debug("send cmd=%d uid=%d stat=%d len=%d payload=%s", command_id, user_id, status, len(payload), byte_arr_to_hex(payload))
            await self.writer.drain()

    async def run(
        self,
        handlers: Dict[int, Handler],
        default_handler: Optional[Handler],
        initial_length: Optional[bytes] = None,
    ) -> None:

        LOG.info("client connected: %s", self.peer)
        try:
            while True:
                raw_len = initial_length if initial_length is not None else await self.reader.readexactly(4)
                initial_length = None
                length = struct.unpack(self.codec.struct_prefix + "I", raw_len)[0]
                if length < self.codec.header_length or length > MAX_PACKET:
                    raise ProtocolError(f"invalid packet length {length}")
                frame = raw_len + await self.reader.readexactly(length - 4)
                packet = self.codec.decode(frame)
                LOG.debug("recv cmd=%d uid=%d seq=%d len=%d payload=%s", packet.command_id, packet.user_id, packet.sequence, len(packet.payload), byte_arr_to_hex(packet.payload))
                handler = handlers.get(packet.command_id, default_handler)
                if handler is None:
                    continue
                try:
                    result = handler(self, packet)
                    if asyncio.iscoroutine(result):
                        result = await result
                except Exception:
                    # A handler failure must still produce a protocol response;
                    # otherwise RemoteServicManager waits until its timeout and
                    # the connection may appear to have silently dropped the
                    # request (notably CHAT_SAVE_WORDS/1556).
                    LOG.exception(
                        "handler failed cmd=%d uid=%d seq=%d",
                        packet.command_id,
                        packet.user_id,
                        packet.sequence,
                    )
                    await self.send_response(
                        packet.command_id,
                        user_id=packet.user_id,
                        status=5001,
                    )
                    continue
                # Some Taomee commands fan out into an acknowledgement plus
                # several server-push frames.  Preserve handler order while
                # retaining the original single-response behavior.
                results = result if isinstance(result, (list, tuple)) else (result,)
                for item in results:
                    if item is None:
                        continue
                    if isinstance(item, Response):
                        await self.send_response(
                            item.command_id if item.command_id is not None else packet.command_id,
                            user_id=item.user_id if item.user_id is not None else packet.user_id,
                            status=item.status,
                            error=item.error,
                            payload=item.payload,
                        )
                    else:
                        await self.send_response(packet.command_id, user_id=packet.user_id, payload=bytes(item))
        except asyncio.IncompleteReadError:
            pass
        except (ProtocolError, UnicodeError) as exc:
            LOG.warning("closing %s due to protocol error: %s", self.peer, exc)
        finally:
            cleanup = self.state.get("on_disconnect")
            if cleanup:
                try:
                    result = cleanup(self)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as exc:
                    LOG.warning("session cleanup failed for %s: %s", self.peer, exc)
            self.writer.close()
            await self.writer.wait_closed()
            LOG.info("client disconnected: %s", self.peer)
            
