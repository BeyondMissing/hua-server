from typing import Callable, Union, Sequence, Awaitable

from entity.packet import Packet
from entity.response import Response

SingleHandlerResult = Union[bytes, bytearray, memoryview, Response, None]
HandlerResult = Union[SingleHandlerResult, Sequence[SingleHandlerResult]]
Handler = Callable[["ClientSession", Packet], Union[HandlerResult, Awaitable[HandlerResult]]]
