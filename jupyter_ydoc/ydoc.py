import copy
from uuid import uuid4

import y_py as Y
from ypy_websocket.websocket_server import YDoc

from .utils import cast_all


class YBaseDoc:
    def __init__(self, ydoc: YDoc):
        self._ydoc = ydoc
        self._ystate = self._ydoc.get_map("state")
        self._subscriptions = {}

    @property
    def ystate(self):
        return self._ystate

    @property
    def ydoc(self):
        return self._ydoc

    @property
    def source(self):
        raise RuntimeError("Y document source generation not implemented")

    @source.setter
    def source(self, value):
        raise RuntimeError("Y document source initialization not implemented")

    @property
    def dirty(self) -> None:
        return self._ystate["dirty"]

    @dirty.setter
    def dirty(self, value: bool) -> None:
        with self._ydoc.begin_transaction() as t:
            self._ystate.set(t, "dirty", value)

    def observe(self, callback):
        raise RuntimeError("Y document observe not implemented")

    def unobserve(self):
        for k, v in self._subscriptions.items():
            k.unobserve(v)
        self._subscriptions = {}

    def apply_update(self, update: bytes) -> None:
        Y.apply_update(self._ydoc, update)


class YFile(YBaseDoc):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ysource = self._ydoc.get_text("source")

    @property
    def source(self):
        return str(self._ysource)

    @source.setter
    def source(self, value):
        with self._ydoc.begin_transaction() as t:
            # clear document
            source_len = len(self._ysource)
            if source_len:
                self._ysource.delete(t, 0, source_len)
            # initialize document
            if value:
                self._ysource.push(t, value)

    def observe(self, callback):
        self.unobserve()
        self._subscriptions[self._ystate] = self._ystate.observe(callback)
        self._subscriptions[self._ysource] = self._ysource.observe(callback)


class YNotebook(YBaseDoc):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ycells = self._ydoc.get_array("cells")
        self._ymeta = self._ydoc.get_map("meta")

    @property
    def source(self):
        cells = self._ycells.to_json()
        meta = self._ymeta.to_json()
        cast_all(cells, float, int)
        cast_all(meta, float, int)
        for cell in cells:
            if "id" in cell and meta["nbformat"] == 4 and meta["nbformat_minor"] <= 4:
                # strip cell IDs if we have notebook format 4.0-4.4
                del cell["id"]
        return dict(
            cells=cells,
            metadata=meta["metadata"],
            nbformat=int(meta["nbformat"]),
            nbformat_minor=int(meta["nbformat_minor"]),
        )

    @source.setter
    def source(self, value):
        nb = copy.deepcopy(value)
        cast_all(nb, int, float)
        if not nb["cells"]:
            nb["cells"] = [
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": "",
                    "id": str(uuid4()),
                }
            ]
        with self._ydoc.begin_transaction() as t:
            # clear document
            cells_len = len(self._ycells)
            if cells_len:
                self._ycells.delete_range(t, 0, cells_len)
            for key in self._ymeta:
                self._ymeta.pop(t, key)
            for key in [k for k in self._ystate if k != "dirty"]:
                self._ystate.pop(t, key)

            # initialize document
            ycells = []
            for cell in nb["cells"]:
                cell["source"] = Y.YText(cell["source"])
                if "id" not in cell:
                    cell["id"] = str(uuid4())
                if "outputs" in cell:
                    cell["outputs"] = Y.YArray(cell["outputs"])
                ycell = Y.YMap(cell)
                ycells.append(ycell)

            if ycells:
                self._ycells.extend(t, ycells)
            self._ymeta.set(t, "metadata", nb["metadata"])
            self._ymeta.set(t, "nbformat", nb["nbformat"])
            self._ymeta.set(t, "nbformat_minor", nb["nbformat_minor"])

    def observe(self, callback):
        self.unobserve()
        self._subscriptions[self._ystate] = self._ystate.observe(callback)
        self._subscriptions[self._ycells] = self._ycells.observe_deep(callback)
        self._subscriptions[self._ymeta] = self._ymeta.observe(callback)
