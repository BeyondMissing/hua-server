import struct

from constant.consts import MAX_CHAT_MESSAGE_BYTES, FAIRY_ACTION_TYPES
from exception.social_protocol_error import SocialProtocolError
from stream import fixed_utf8


def friend_info_payload(rows) -> bytes:
    """Encode the fixed relation records consumed by UserInfo.setForFriendInfo."""
    out = bytearray(struct.pack(">I", len(rows)))
    for row in rows:
        out += struct.pack(
            ">5I",
            int(row.get("user_id", 0)) & 0xFFFFFFFF,
            int(row.get("online_id", 0)) & 0xFFFFFFFF,
            int(row.get("home_pollen", 0)) & 0xFFFFFFFF,
            int(row.get("vip_level", 0)) & 0xFFFFFFFF,
            int(row.get("friend_team", 10)) & 0xFFFFFFFF,
        )
        out += fixed_utf8(str(row.get("nickname", row.get("user_id", ""))), 16)
        out += struct.pack(
            ">6I",
            *[
                int(row.get(field, 0) or 0) & 0xFFFFFFFF
                for field in ("face_color", "face", "eye", "eyebrow", "lip", "hair")
            ],
        )
    return bytes(out)


def friend_request_notice_payload(row, content: int = 0) -> bytes:
    """Encode NOTICE_INFO(Type=1), consumed by NoticeLogic as a friend ask."""
    return (
        struct.pack(">2I", 1, int(row.get("user_id", 0)) & 0xFFFFFFFF)
        + fixed_utf8(str(row.get("nickname", row.get("user_id", ""))), 16)
        + struct.pack(
            ">6I",
            *[
                int(row.get(field, 0) or 0) & 0xFFFFFFFF
                for field in ("face_color", "face", "eye", "eyebrow", "lip", "hair")
            ],
        )
        + struct.pack(">I", int(content) & 0xFFFFFFFF)
    )


def parse_chat_request(payload: bytes):
    if len(payload) < 8:
        raise SocialProtocolError("CHAT_INFO payload is shorter than its header")
    target_user_id, message_length = struct.unpack_from(">2I", payload)
    if message_length > MAX_CHAT_MESSAGE_BYTES:
        raise SocialProtocolError("CHAT_INFO message is too long")
    if len(payload) != 8 + message_length:
        raise SocialProtocolError("CHAT_INFO message length does not match payload")
    message = payload[8:]
    message.decode("utf-8")
    if message.endswith(b"0") or message.endswith(b"\0"):
        message = message[:-1]
    return target_user_id, message


def chat_info_payload(user_id: int, nickname: str, friend: int, message: bytes) -> bytes:
    return (
        struct.pack(">I", int(user_id) & 0xFFFFFFFF)
        + fixed_utf8(str(nickname), 16)
        + struct.pack(">2I", int(friend) & 0xFFFFFFFF, len(message))
        + bytes(message)
    )


def parse_fairy_action_request(payload: bytes):
    if len(payload) != 16:
        raise SocialProtocolError("FAIRY_ACTION payload must contain four uint32 values")
    values = struct.unpack(">4I", payload)
    if values[0] not in FAIRY_ACTION_TYPES:
        raise SocialProtocolError("unknown FAIRY_ACTION type")
    return values


def fairy_action_payload(user_id: int, action_values) -> bytes:
    action, action_other, x, y = action_values
    return struct.pack(">5I", int(user_id) & 0xFFFFFFFF, action, action_other, x, y)


def parse_item_type_request(payload: bytes) -> int:
    if len(payload) != 4:
        raise SocialProtocolError("ITEM_TYPE_INFO payload must contain one uint32")
    return struct.unpack(">I", payload)[0]


def item_type_info_payload(item_type: int, rows) -> bytes:
    actions = [
        (int(row.get("item_id", row.get("action_id", 0))) & 0xFFFFFFFF,
         int(row.get("amount", 0)) & 0xFFFFFFFF)
        for row in rows
        if int(row.get("item_id", row.get("action_id", 0))) > 0
        and int(row.get("amount", 0)) > 0
    ]
    payload = bytearray(struct.pack(">2I", int(item_type) & 0xFFFFFFFF, len(actions)))
    for action_id, amount in actions:
        payload += struct.pack(">2I", action_id, amount)
    return bytes(payload)


def parse_people_transform_request(payload: bytes):
    if len(payload) != 12:
        raise SocialProtocolError("PEOPLE_TRANSFORM payload must contain three uint32 values")
    return struct.unpack(">3I", payload)


def people_transform_payload(target_user_id: int, transform_type: int, action_id: int) -> bytes:
    return struct.pack(">3I", target_user_id, transform_type, action_id)
