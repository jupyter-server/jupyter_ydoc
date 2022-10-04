import asyncio
import json
from pathlib import Path

import pytest
import y_py as Y
from websockets import connect  # type: ignore
from ypy_websocket import WebsocketProvider

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
    def __init__(self, ydoc: Y.YDoc, timeout: float = 1.0):
        self.timeout = timeout
        self.ytest = ydoc.get_map("_test")
        with ydoc.begin_transaction() as t:
            self.ytest.set(t, "clock", 0)

    async def change(self):
        change = asyncio.Event()

        def callback(event):
            if "clock" in event.keys:
                change.set()

        self.ytest.observe(callback)
        return await asyncio.wait_for(change.wait(), timeout=self.timeout)

    @property
    def source(self):
        return cast_all(self.ytest["source"], float, int)


@pytest.mark.asyncio
@pytest.mark.parametrize("yjs_client", "0", indirect=True)
async def test_ypy_yjs_0(yws_server, yjs_client):
    ydoc = Y.YDoc()
    ynotebook = YNotebook(ydoc)
    websocket = await connect("ws://localhost:1234/my-roomname")
    WebsocketProvider(ydoc, websocket)
    nb = stringify_source(json.loads((files_dir / "nb0.ipynb").read_text()))
    ynotebook.source = nb
    ytest = YTest(ydoc)
    await ytest.change()
    assert ytest.source == nb


def test_plotly_renderer():
    """This test checks in particular that the type cast is not breaking the data."""
    ydoc = Y.YDoc()
    ynotebook = YNotebook(ydoc)
    nb = stringify_source(json.loads((files_dir / "plotly_renderer.ipynb").read_text()))
    ynotebook.source = nb
    assert ynotebook.source == nb
