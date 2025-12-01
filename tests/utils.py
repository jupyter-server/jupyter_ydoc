# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from dataclasses import dataclass

from anyio import Lock, connect_tcp


class Websocket:
    def __init__(self, websocket, path: str):
        self._websocket = websocket
        self._path = path
        self._send_lock = Lock()

    @property
    def path(self) -> str:
        return self._path

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        try:
            message = await self.recv()
        except Exception:
            raise StopAsyncIteration()  # pragma: nocover
        return message

    async def send(self, message: bytes):
        async with self._send_lock:
            await self._websocket.send_bytes(message)

    async def recv(self) -> bytes:
        b = await self._websocket.receive_bytes()
        return bytes(b)


async def ensure_server_running(host: str, port: int) -> None:
    while True:
        try:
            await connect_tcp(host, port)
        except OSError:  # pragma: nocover
            pass
        else:
            break


@dataclass
class ExpectedEvent:
    kind: type
    path: str | None = None
    delta: list[dict] | None = None

    def __eq__(self, other):
        if not isinstance(other, self.kind):
            return False
        if self.path is not None and self.path != other.path:
            return False
        if self.delta is not None and self.delta != other.delta:
            return False
        return True

    def __repr__(self):
        fragments = [self.kind.__name__]
        if self.path is not None:
            fragments.append(f"path={self.path!r}")
        if self.delta is not None:
            fragments.append(f"delta={self.delta!r}")
        return f"ExpectedEvent({', '.join(fragments)})"
