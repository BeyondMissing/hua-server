import struct
from typing import Literal

from codec.decrypt_payload import decrypt_payload
from codec.encrypt_payload import encrypt_payload
from constant.consts import MAX_PACKET
from entity.packet import Packet
from exception.protocol_error import ProtocolError


class TaomeeCodec:
    """Encode/decode one complete Taomee packet."""

    def __init__(
        self,
        version: str = "1",
        encrypted: bool = False,
        key: bytes = b"v#93ta0mee+fl0WErd0t2eatMee&#$+@n0\x00",
        byte_order: Literal["big", "little"] = "big",
    ):
        if version not in ("1", "2"):
            raise ValueError("version must be '1' or '2'")
        if byte_order not in ("big", "little"):
            raise ValueError("byte_order must be 'big' or 'little'")
        self.version = version
        self.encrypted = encrypted
        self.key = key
        self.byte_order = byte_order
        self.struct_prefix = ">" if byte_order == "big" else "<"

    @property
    def header_length(self) -> int:
        return 17 if self.version == "1" else 21

    def decode(self, frame: bytes) -> Packet:
        if len(frame) < self.header_length:
            raise ProtocolError(f"short packet: {len(frame)} < {self.header_length}")
        length = struct.unpack_from(self.struct_prefix + "I", frame, 0)[0]
        if length != len(frame):
            raise ProtocolError(f"length field {length} != frame size {len(frame)}")
        if not (self.header_length <= length <= MAX_PACKET):
            raise ProtocolError(f"invalid packet length {length}")
        version = frame[4:5].decode("ascii", errors="strict")
        if version != self.version:
            raise ProtocolError(f"unexpected version {version!r}")
        command_id, user_id, sequence = struct.unpack_from(self.struct_prefix + "III", frame, 5)
        offset = 17
        # Word at offset 13 is sequence for a request and result for a
        # response. Keep it in both fields so callers can use the spelling
        # appropriate to their direction.
        result = sequence
        error = 0
        if self.version == "2":
            # Version 2 appends a second status word after the request
            # sequence/response result word.  For incoming requests this is
            # normally zero; for responses it is the protocol's ``error``.
            error = struct.unpack_from(self.struct_prefix + "I", frame, offset)[0]
            offset += 4
        payload = frame[offset:]
        if self.encrypted and payload:
            payload = decrypt_payload(payload, self.key)
        return Packet(version, command_id, user_id, sequence, result, error, payload)

    def encode(
        self,
        command_id: int,
        user_id: int,
        sequence: int = 0,
        result: int = 0,
        payload: bytes = b"",
    ) -> bytes:
        if self.encrypted and payload:
            payload = encrypt_payload(payload, self.key)
        head = bytearray(struct.pack(self.struct_prefix + "I", self.header_length + len(payload)))
        head += self.version.encode("ascii")
        head += struct.pack(self.struct_prefix + "III", command_id & 0xFFFFFFFF, user_id & 0xFFFFFFFF, sequence & 0xFFFFFFFF)
        if self.version == "2":
            head += struct.pack(self.struct_prefix + "I", result & 0xFFFFFFFF)
        return bytes(head) + payload

    def encode_response(
        self,
        command_id: int,
        user_id: int,
        *,
        status: int = 0,
        error: int = 0,
        payload: bytes = b"",
    ) -> bytes:
        """Encode a server-to-client response.

        In version 1 the word at offset 13 is ``result``.  In version 2 that
        same word remains ``result`` and a second word, ``error``, follows it.
        This differs from a client request, where offset 13 is the sequence.
        """
        if self.encrypted and payload:
            payload = encrypt_payload(payload, self.key)
        head = bytearray(struct.pack(self.struct_prefix + "I", self.header_length + len(payload)))
        head += self.version.encode("ascii")
        head += struct.pack(self.struct_prefix + "IIi", command_id & 0xFFFFFFFF, user_id & 0xFFFFFFFF, int(status))
        if self.version == "2":
            head += struct.pack(self.struct_prefix + "I", error & 0xFFFFFFFF)
        return bytes(head) + payload