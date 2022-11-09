import json
import subprocess
from pathlib import Path

import pytest
from websockets import serve  # type: ignore
from ypy_websocket import WebsocketServer

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
update_json_file(here / "node_modules/y-websocket/package.json", d)


@pytest.fixture
async def yws_server(request):
    try:
        kwargs = request.param
    except Exception:
        kwargs = {}
    websocket_server = WebsocketServer(**kwargs)
    async with serve(websocket_server.serve, "localhost", 1234):
        yield websocket_server


@pytest.fixture
def yjs_client(request):
    client_id = request.param
    p = subprocess.Popen(
        [
            "node",
            "--experimental-specifier-resolution=node",
            f"{here / 'yjs_client_'}{client_id}.js",
        ]
    )
    yield p
    p.kill()
