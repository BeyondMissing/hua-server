import struct

from constant.consts import LOGIN_FIELDS_SIZE, LOGIN_PAYLOAD_SIZE, LOGIN_NAME_SIZE
from entity.login_request import LoginRequest
from entity.packet import Packet
from exception.protocol_error import ProtocolError
from stream import read_fixed_utf8


def parse_login_request(packet: Packet) -> LoginRequest:
    data = packet.payload
    if packet.user_id:
        if len(data) not in (LOGIN_FIELDS_SIZE, LOGIN_PAYLOAD_SIZE):
            raise ProtocolError(
                f"numeric login payload must be {LOGIN_FIELDS_SIZE} or "
                f"{LOGIN_PAYLOAD_SIZE} bytes, got {len(data)}"
            )
        name, offset = str(packet.user_id), 0
    else:
        expected_size = LOGIN_NAME_SIZE + LOGIN_PAYLOAD_SIZE
        if len(data) != expected_size:
            raise ProtocolError(f"named login payload must be {expected_size} bytes, got {len(data)}")
        name, offset = read_fixed_utf8(data[:LOGIN_NAME_SIZE]), LOGIN_NAME_SIZE
    verifier = data[offset: offset + 32].decode("ascii").lower()
    if len(verifier) != 32 or any(c not in "0123456789abcdef" for c in verifier):
        raise ProtocolError("invalid MD5 verifier")
    location, game_id, user_ip = struct.unpack_from(">III", data, offset + 32)
    return LoginRequest(name, verifier, location, game_id, user_ip, data[offset + 44:offset + LOGIN_FIELDS_SIZE])