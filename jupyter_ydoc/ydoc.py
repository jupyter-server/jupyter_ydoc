import copy
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from uuid import uuid4

import y_py as Y

from .utils import cast_all


class YBaseDoc(ABC):
    """
    Base YDoc class.
    This class, defines the minimum API that any documents must provide
    for the :class:`YDocWebSocketHandler` to be able to get and set the
    content of the document as well as subscribe to changes in the document.
    """

    def __init__(self, ydoc: Y.YDoc):
        """
        Construct a YBaseDoc.

        :param ydoc: The :class:`y_py.YDoc` that will hold the data of the document.
        :type ydoc: :class:`y_py.YDoc`
        """
        self._ydoc = ydoc
        self._ystate = self._ydoc.get_map("state")
        self._subscriptions = {}

    @property
    def ystate(self) -> Y.YMap:
        """
        A :class:`y_py.YMap` containing the state of the document.

        :return: That contains document's state.
        :rtype: :class:`y_py.YMap`
        """
        return self._ystate

    @property
    def ydoc(self) -> Y.YDoc:
        """
        The underlying :class:`y_py.YDoc` that contains the data.

        :return: That contains document's data.
        :rtype: :class:`y_py.YDoc`
        """
        return self._ydoc

    @property
    def source(self):
        """
        Returns the content of the document.

        :return: The content of the document.
        :rtype: Any
        """
        return self.get()

    @source.setter
    def source(self, value):
        """
        Sets the content of the document.

        :param value: The content of the document.
        :type value: Any
        """
        return self.set(value)

    @property
    def dirty(self) -> Optional[bool]:
        """
        Returns whether the document in memory has changes that are not on disk.

        :return: Whether the document in memory has changes that are not on disk.
        :rtype: bool | None
        """
        return self._ystate["dirty"]

    @dirty.setter
    def dirty(self, value: bool) -> None:
        """
        Sets whether the document in memory has changes that are not on disk.

        :param value: Whether the document in memory has changes that are not on disk.
        :type value: bool
        """
        with self._ydoc.begin_transaction() as t:
            self._ystate.set(t, "dirty", value)

    @property
    def path(self) -> Optional[str]:
        """
        Returns document's path.

        :return: Document's path.
        :rtype: str | None
        """
        return self._ystate.get("path")

    @path.setter
    def path(self, value: str) -> None:
        """
        Sets document's path.

        :param value: Document's path.
        :type value: str
        """
        with self._ydoc.begin_transaction() as t:
            self._ystate.set(t, "path", value)

    @abstractmethod
    def get(self):
        """
        Returns the content of the document.

        :return: Document's content.
        :rtype: Any
        """
        pass

    @abstractmethod
    def set(self, value):
        """
        Sets the content of the document.

        :param value: The content of the document.
        :type value: Any
        """
        pass

    @abstractmethod
    def observe(self, callback):
        """
        Subscribe to document changes.

        :param callback: Callback that will be called when the document changes.
        :type callback: function
        """
        pass

    def unobserve(self):
        """
        Unsubscribe to document changes.

        This method removes all the callbacks.
        """
        for k, v in self._subscriptions.items():
            k.unobserve(v)
        self._subscriptions = {}


class YFile(YBaseDoc):
    """
    Extends :class:`YBaseDoc`, and represents a plain text document.

    Schema:

    .. code-block:: json

        {
            "state": YMap,
            "source": YText
        }
    """

    def __init__(self, *args, **kwargs):
        """
        Construct a YFile.

        :param ydoc: The :class:`y_py.YDoc` that will hold the data of the document.
        :type ydoc: :class:`y_py.YDoc`
        """
        super().__init__(*args, **kwargs)
        self._ysource = self._ydoc.get_text("source")

    def get(self):
        """
        Returns the content of the document.

        :return: Document's content.
        :rtype: str
        """
        return str(self._ysource)

    def set(self, value):
        """
        Sets the content of the document.

        :param value: The content of the document.
        :type value: str
        """
        with self._ydoc.begin_transaction() as t:
            # clear document
            source_len = len(self._ysource)
            if source_len:
                self._ysource.delete_range(t, 0, source_len)
            # initialize document
            if value:
                self._ysource.extend(t, value)

    def observe(self, callback):
        """
        Subscribe to document changes.

        :param callback: Callback that will be called when the document changes.
        :type callback: function(event: YEvent)
        """
        self.unobserve()
        self._subscriptions[self._ystate] = self._ystate.observe(callback)
        self._subscriptions[self._ysource] = self._ysource.observe(callback)


class YNotebook(YBaseDoc):
    """
    Extends :class:`YBaseDoc`, and represents a Notebook document.

    Schema:

    .. code-block:: json

        {
            "state": YMap,
            "meta": YText,
            "cells": YArray[
                YMap[
                    "id": str,
                    "cell_type": str,
                    "source": YText,
                    "metadata": YMap,
                    "execution_count": Int | None,
                    "outputs": [] | None,
                    "attachments": {} | None
                ]
            ]
        }
    """

    def __init__(self, *args, **kwargs):
        """
        Construct a YNotebook.

        :param ydoc: The :class:`y_py.YDoc` that will hold the data of the document.
        :type ydoc: :class:`y_py.YDoc`
        """
        super().__init__(*args, **kwargs)
        self._ymeta = self._ydoc.get_map("meta")
        self._ycells = self._ydoc.get_array("cells")

    def get_cell(self, index: int) -> Dict[str, Any]:
        """
        Returns a cell from `self._ycells`.

        :param index: The index of the cell.
        :type index: int

        :return: A cell.
        :rtype: Dict[str, Any]
        """
        meta = self._ymeta.to_json()
        cell = self._ycells[index].to_json()
        cast_all(cell, float, int)  # cells coming from Yjs have e.g. execution_count as float
        if "id" in cell and meta["nbformat"] == 4 and meta["nbformat_minor"] <= 4:
            # strip cell IDs if we have notebook format 4.0-4.4
            del cell["id"]
        if (
            "attachments" in cell
            and cell["cell_type"] in ("raw", "markdown")
            and not cell["attachments"]
        ):
            del cell["attachments"]
        return cell

    def append_cell(self, value: Dict[str, Any], txn=None) -> None:
        """
        Adds a cell to `self._ycells`.

        :param value: A cell.
        :type value: Dict[str, Any]

        :param txn: A YTransaction, defaults to None
        :type txn: :class:`YTransaction`, optional.
        """
        ycell = self.create_ycell(value)
        if txn is None:
            with self._ydoc.begin_transaction() as txn:
                self._ycells.append(txn, ycell)
        else:
            self._ycells.append(txn, ycell)

    def set_cell(self, index: int, value: Dict[str, Any], txn=None) -> None:
        """
        Sets a cell into `self._ycells`.

        :param index: The index of the cell.
        :type index: int

        :param value: A cell.
        :type value: Dict[str, Any]

        :param txn: A YTransaction, defaults to None
        :type txn: :class:`YTransaction`, optional.
        """
        ycell = self.create_ycell(value)
        self.set_ycell(index, ycell, txn)

    def create_ycell(self, value: Dict[str, Any]) -> Y.YMap:
        """
        Creates YMap with the content of the cell.

        :param value: A cell.
        :type value: Dict[str, Any]

        :return: A new cell.
        :rtype: :class:`YMap`
        """
        cell = copy.deepcopy(value)
        if "id" not in cell:
            cell["id"] = str(uuid4())
        cell_type = cell["cell_type"]
        cell["source"] = Y.YText(cell["source"])
        cell["metadata"] = Y.YMap(cell.get("metadata", {}))

        if cell_type in ("raw", "markdown"):
            if "attachments" in cell and not cell["attachments"]:
                del cell["attachments"]
        elif cell_type == "code":
            cell["outputs"] = Y.YArray(cell.get("outputs", []))

        return Y.YMap(cell)

    def set_ycell(self, index: int, ycell: Y.YMap, txn=None) -> None:
        """
        Sets a cell into the `self._ycells`.

        :param index: The index of the cell.
        :type index: int

        :param ycell: A YMap with the content of a cell.
        :type ycell: :class:`YMap`

        :param txn: A YTransaction, defaults to None
        :type txn: :class:`YTransaction`, optional.
        """
        if txn is None:
            with self._ydoc.begin_transaction() as txn:
                self._ycells.delete(txn, index)
                self._ycells.insert(txn, index, ycell)
        else:
            self._ycells.delete(txn, index)
            self._ycells.insert(txn, index, ycell)

    def get(self):
        """
        Returns the content of the document.

        :return: Document's content.
        :rtype: Dic
        """
        meta = self._ymeta.to_json()
        cast_all(meta, float, int)  # notebook coming from Yjs has e.g. nbformat as float
        cells = []
        for i in range(len(self._ycells)):
            cell = self.get_cell(i)
            if "id" in cell and meta["nbformat"] == 4 and meta["nbformat_minor"] <= 4:
                # strip cell IDs if we have notebook format 4.0-4.4
                del cell["id"]
            if (
                "attachments" in cell
                and cell["cell_type"] in ["raw", "markdown"]
                and not cell["attachments"]
            ):
                del cell["attachments"]
            cells.append(cell)

        return dict(
            cells=cells,
            metadata=meta["metadata"],
            nbformat=int(meta["nbformat"]),
            nbformat_minor=int(meta["nbformat_minor"]),
        )

    def set(self, value):
        """
        Sets the content of the document.

        :param value: The content of the document.
        :type value: Dic
        """
        nb_without_cells = {key: value[key] for key in value.keys() if key != "cells"}
        nb = copy.deepcopy(nb_without_cells)
        cast_all(nb, int, float)  # Yjs expects numbers to be floating numbers
        cells = value["cells"] or [
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
            for key in self._ymeta:
                self._ymeta.pop(t, key)
            if cells_len:
                self._ycells.delete_range(t, 0, cells_len)
            for key in [k for k in self._ystate if k not in ("dirty", "path")]:
                self._ystate.pop(t, key)

            # initialize document
            self._ycells.extend(t, [self.create_ycell(cell) for cell in cells])
            self._ymeta.set(t, "metadata", nb["metadata"])
            self._ymeta.set(t, "nbformat", nb["nbformat"])
            self._ymeta.set(t, "nbformat_minor", nb["nbformat_minor"])

    def observe(self, callback):
        """
        Subscribe to document changes.

        :param callback: Callback that will be called when the document changes.
        :type callback: function(event: YEvent)
        """
        self.unobserve()
        self._subscriptions[self._ystate] = self._ystate.observe(callback)
        self._subscriptions[self._ymeta] = self._ymeta.observe(callback)
        self._subscriptions[self._ycells] = self._ycells.observe_deep(callback)
