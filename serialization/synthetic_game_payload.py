"""Big-endian payloads matching the three AS3 syntheticGame decoders."""

import struct


def activate_goods_payload(rows):
    payload = bytearray(struct.pack(">I", len(rows)))
    for row in rows:
        materials = row["materials"]
        payload.extend(struct.pack(">3I", row["goods_index"], row["exp_done"], len(materials)))
        for item_id, amount in materials:
            payload.extend(struct.pack(">2I", item_id, amount))
    return bytes(payload)


def synthetic_start_payload(result):
    return struct.pack(">I", result)


def synthetic_score_payload(result):
    # ScoreDecoder reads exactly these six uint32 values, in this order.
    return struct.pack(">6I", *result)
