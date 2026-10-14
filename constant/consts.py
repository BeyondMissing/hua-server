MAX_PACKET = 8 * 1024 * 1024  # SocketImpl.PACKAGE_MAX

LOGIN_NAME_SIZE = 64
LOGIN_FIELDS_SIZE = 66
LOGIN_AD_SIZE = 128
LOGIN_PAYLOAD_SIZE = LOGIN_FIELDS_SIZE + LOGIN_AD_SIZE

MAX_CLOTH_CHANGES = 64

MAX_CHAT_MESSAGE_BYTES = 512
FAIRY_ACTION_TYPES = frozenset(range(6))

# Values written to player_friends.status and sent as UserInfo.FriendTeam.
FRIEND_STATUS_PENDING = 0
FRIEND_STATUS_FRIEND = 10
FRIEND_STATUS_INTIMATE = 11
FRIEND_STATUS_BLACKLIST = 100

# UserInfo.clothUpDown() in the AS3 client uses this exact mapping.
CLOTHING_SLOT_BY_TYPE = {
    1: "tool",
    2: "headdress",
    3: "mask",
    4: "hair",
    5: "earring",
    6: "necklace",
    7: "belt",
    8: "cloth",
    9: "bangle",
    10: "shoes",
    11: "anklet",
    12: "skirt",
    13: "wing",
    102: "eyebrow",
    103: "eye",
    104: "lip",
    105: "face",
}
