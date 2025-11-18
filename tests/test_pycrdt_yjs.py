# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import json
from pathlib import Path

import pytest
from anyio import Event, create_task_group, fail_after, move_on_after, sleep
from httpx_ws import aconnect_ws
from pycrdt import Doc, Map, Provider
from utils import Websocket

from jupyter_ydoc import YNotebook
from jupyter_ydoc.utils import cast_all

files_dir = Path(__file__).parent / "files"


def stringify_source(nb: dict) -> dict:
    """Stringify in-place the cell sources."""
    for cell in nb["cells"]:
        cell["source"] = (
            "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
        )

    return nb


class YTest:
    def __init__(self, ydoc: Doc, timeout: float = 1.0):
        self.timeout = timeout
        ydoc["_test"] = self.ytest = Map()
        self.clock = -1.0

    def run_clock(self):
        self.clock = max(self.clock, 0.0)
        self.ytest["clock"] = self.clock

    async def clock_run(self):
        change = Event()

        def callback(event):
            if "clock" in event.keys:
                clk = event.keys["clock"]["newValue"]
                if clk > self.clock:
                    self.clock = clk + 1.0
                    change.set()

        subscription_id = self.ytest.observe(callback)
        async with create_task_group():
            with move_on_after(self.timeout):
                await change.wait()

        self.ytest.unobserve(subscription_id)

    @property
    def source(self):
        return cast_all(self.ytest["source"], float, int)


@pytest.mark.asyncio
@pytest.mark.parametrize("yjs_client", "0", indirect=True)
async def test_ypy_yjs_0(yws_server, yjs_client):
    port, _ = yws_server
    ydoc = Doc()
    ynotebook = YNotebook(ydoc)
    room_name = "my-roomname"
    async with aconnect_ws(f"http://localhost:{port}/{room_name}") as websocket, Provider(
        ydoc, Websocket(websocket, room_name)
    ):
        nb = stringify_source(json.loads((files_dir / "nb0.ipynb").read_text()))
        ynotebook.source = nb
        ytest = YTest(ydoc, 3.0)
        ytest.run_clock()
        await ytest.clock_run()
        assert ytest.source == nb


@pytest.mark.asyncio
@pytest.mark.parametrize("yjs_client", "1", indirect=True)
async def test_ypy_yjs_1(yws_server, yjs_client):
    port, _ = yws_server
    ydoc = Doc()
    ynotebook = YNotebook(ydoc)
    nb = stringify_source(json.loads((files_dir / "nb1.ipynb").read_text()))
    ynotebook.source = nb
    room_name = "my-roomname"
    async with aconnect_ws(f"http://localhost:{port}/{room_name}") as websocket, Provider(
        ydoc, Websocket(websocket, room_name)
    ):
        output_text = ynotebook.ycells[0]["outputs"][0]["text"]
        assert output_text.to_py() == "Hello,"

        with fail_after(10):
            while True:
                await sleep(0.1)
                if output_text.to_py() == "Hello, World!":
                    break


def test_plotly_renderer():
    """This test checks in particular that the type cast is not breaking the data."""
    ydoc = Doc()
    ynotebook = YNotebook(ydoc)
    nb = stringify_source(json.loads((files_dir / "plotly_renderer.ipynb").read_text()))
    ynotebook.source = nb
    assert ynotebook.source == nb
