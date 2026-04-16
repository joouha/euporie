from collections.abc import Callable, Generator

NOP = int2byte(0)
SGA = int2byte(3)
IAC = int2byte(255)
DO = int2byte(253)
DONT = int2byte(254)
LINEMODE = int2byte(34)
SB = int2byte(250)
WILL = int2byte(251)
WONT = int2byte(252)
MODE = int2byte(1)
SE = int2byte(240)
ECHO = int2byte(1)
NAWS = int2byte(31)
SUPPRESS_GO_AHEAD = int2byte(3)
TTYPE = int2byte(24)
SEND = int2byte(1)
IS = int2byte(0)
DM = int2byte(242)
BRK = int2byte(243)
IP = int2byte(244)
AO = int2byte(245)
AYT = int2byte(246)
EC = int2byte(247)
EL = int2byte(248)
GA = int2byte(249)

__all__ = [
    "TelnetProtocolParser",
]

def int2byte(number: int) -> bytes: ...

class TelnetProtocolParser:
    data_received_callback: Callable[[bytes], None]
    size_received_callback: Callable[[int, int], None]
    ttype_received_callback: Callable[[str], None]
    _parser = self._parse_coroutine()
    def __init__(
        self,
        data_received_callback: Callable[[bytes], None],
        size_received_callback: Callable[[int, int], None],
        ttype_received_callback: Callable[[str], None],
    ) -> None: ...
    def received_data(self, data: bytes) -> None: ...
    def do_received(self, data: bytes) -> None: ...
    def dont_received(self, data: bytes) -> None: ...
    def will_received(self, data: bytes) -> None: ...
    def wont_received(self, data: bytes) -> None: ...
    def command_received(self, command: bytes, data: bytes) -> None: ...
    def naws(self, data: bytes) -> None: ...
    def ttype(self, data: bytes) -> None: ...
    def negotiate(self, data: bytes) -> None: ...
    def _parse_coroutine(self) -> Generator[None, bytes]: ...
    def feed(self, data: bytes) -> None: ...
