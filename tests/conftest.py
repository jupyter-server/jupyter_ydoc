# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import json
import subprocess
from functools import partial
from pathlib import Path

import pytest
from anyio import Event, create_task_group
from hypercorn import Config
from hypercorn.asyncio import serve
from pycrdt.websocket import ASGIServer, WebsocketServer
from utils import ensure_server_running

# workaround until these PRs are merged:
# - https://github.com/yjs/y-websocket/pull/104


def update_json_file(path: Path, d: dict):
    with open(path, "rb") as f:
        package_json = json.load(f)
    package_json.update(d)
    with open(path, "w") as f:
        json.dump(package_json, f, indent=2)


here = Path(__file__).parent
d = {"type": "module"}
update_json_file(here.parent / "node_modules/y-websocket/package.json", d)


@pytest.fixture
async def yws_server(request, unused_tcp_port):
    try:
        async with create_task_group() as tg:
            try:
                kwargs = request.param
            except Exception:
                kwargs = {}
            websocket_server = WebsocketServer(**kwargs)
            app = ASGIServer(websocket_server)
            config = Config()
            config.bind = [f"localhost:{unused_tcp_port}"]
            shutdown_event = Event()
            async with websocket_server as websocket_server:
                tg.start_soon(
                    partial(serve, app, config, shutdown_trigger=shutdown_event.wait, mode="asgi")
                )
                await ensure_server_running("localhost", unused_tcp_port)
                pytest.port = unused_tcp_port
                yield unused_tcp_port, websocket_server
                shutdown_event.set()
    except Exception:
        pass


@pytest.fixture
def yjs_client(request):
    client_id = request.param
    p = subprocess.Popen(["node", f"{here / 'yjs_client_'}{client_id}.js", str(pytest.port)])
    yield p
    p.terminate()
    try:
        p.wait(timeout=10)
    except Exception:  # pragma: nocover
        p.kill()
