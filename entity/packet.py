from dataclasses import dataclass


@dataclass(frozen=True)
class Packet:
    version: str
    command_id: int
    user_id: int
    sequence: int
    result: int
    error: int
    payload: bytes

    # On the wire the 4-byte word after user_id has no direction-independent
    # name: SocketImpl.send() writes the request sequence there, while
    # HeadInfo interprets the same word in a response as result/error status.
    # ``sequence`` is therefore the request-side spelling used by handlers.