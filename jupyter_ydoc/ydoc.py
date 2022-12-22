import copy
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

import y_py as Y

from .utils import cast_all


class YBaseDoc(ABC):
    """
    Base YDoc class.
    This class, defines the minimum API that any document must provide
    to be able to get and set the content of the document as well as
    subscribe to changes in the document.
    """

    def __init__(self, ydoc: Y.YDoc):
        """
        Constructs a YBaseDoc.

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

        :return: The document's state.
        :rtype: :class:`y_py.YMap`
        """
        return self._ystate

    @property
    def ydoc(self) -> Y.YDoc:
        """
        The underlying :class:`y_py.YDoc` that contains the data.

        :return: The document's ydoc.
        :rtype: :class:`y_py.YDoc`
        """
        return self._ydoc

    @property
    def source(self) -> Any:
        """
        Returns the content of the document.

        :return: The content of the document.
        :rtype: Any
        """
        return self.get()

    @source.setter
    def source(self, value: Any):
        """
        Sets the content of the document.

        :param value: The content of the document.
        :type value: Any
        """
        return self.set(value)

    @property
    def dirty(self) -> Optional[bool]:
        """
        Returns whether the document is dirty.

        :return: Whether the document is dirty.
        :rtype: Optional[bool]
        """
        return self._ystate["dirty"]

    @dirty.setter
    def dirty(self, value: bool) -> None:
        """
        Sets the document as clean (all changes committed) or dirty (uncommitted changes).

        :param value: Whether the document is clean or dirty.
        :type value: bool
        """
        with self._ydoc.begin_transaction() as t:
            self._ystate.set(t, "dirty", value)

    @property
    def path(self) -> Optional[str]:
        """
        Returns document's path.

        :return: Document's path.
        :rtype: Optional[str]
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
    def get(self) -> Any:
        """
        Returns the content of the document.

        :return: Document's content.
        :rtype: Any
        """
        pass

    @abstractmethod
    def set(self, value: Any) -> None:
        """
        Sets the content of the document.

        :param value: The content of the document.
        :type value: Any
        """
        pass

    @abstractmethod
    def observe(self, callback: Callable[[Any], None]) -> None:
        """
        Subscribes to document changes.

        :param callback: Callback that will be called when the document changes.
        :type callback: Callable[[Any], None]
        """
        pass

    def unobserve(self) -> None:
        """
        Unsubscribes to document changes.

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

    def __init__(self, ydoc: Y.YDoc):
        """
        Constructs a YFile.

        :param ydoc: The :class:`y_py.YDoc` that will hold the data of the document.
        :type ydoc: :class:`y_py.YDoc`
        """
        super().__init__(ydoc)
        self._ysource = self._ydoc.get_text("source")

    def get(self) -> str:
        """
        Returns the content of the document.

        :return: Document's content.
        :rtype: str
        """
        return str(self._ysource)

    def set(self, value: str) -> None:
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

    def observe(self, callback: Callable[[Any], None]) -> None:
        """
        Subscribes to document changes.

        :param callback: Callback that will be called when the document changes.
        :type callback: Callable[[Any], None]
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
            "meta": YMap[
                "nbformat": Int,
                "nbformat_minor": Int,
                "metadata": YMap
            ],
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

    def __init__(self, ydoc: Y.YDoc):
        """
        Constructs a YNotebook.

        :param ydoc: The :class:`y_py.YDoc` that will hold the data of the document.
        :type ydoc: :class:`y_py.YDoc`
        """
        super().__init__(ydoc)
        self._ymeta = self._ydoc.get_map("meta")
        self._ycells = self._ydoc.get_array("cells")

    def get_cell(self, index: int) -> Dict[str, Any]:
        """
        Returns a cell.

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

    def append_cell(self, value: Dict[str, Any], txn: Optional[Y.YTransaction] = None) -> None:
        """
        Appends a cell.

        :param value: A cell.
        :type value: Dict[str, Any]

        :param txn: A YTransaction, defaults to None
        :type txn: :class:`y_py.YTransaction`, optional.
        """
        ycell = self.create_ycell(value)
        if txn is None:
            with self._ydoc.begin_transaction() as txn:
                self._ycells.append(txn, ycell)
        else:
            self._ycells.append(txn, ycell)

    def set_cell(
        self, index: int, value: Dict[str, Any], txn: Optional[Y.YTransaction] = None
    ) -> None:
        """
        Sets a cell into indicated position.

        :param index: The index of the cell.
        :type index: int

        :param value: A cell.
        :type value: Dict[str, Any]

        :param txn: A YTransaction, defaults to None
        :type txn: :class:`y_py.YTransaction`, optional.
        """
        ycell = self.create_ycell(value)
        self.set_ycell(index, ycell, txn)

    def create_ycell(self, value: Dict[str, Any]) -> Y.YMap:
        """
        Creates YMap with the content of the cell.

        :param value: A cell.
        :type value: Dict[str, Any]

        :return: A new cell.
        :rtype: :class:`y_py.YMap`
        """
        cell = copy.deepcopy(value)
        if "id" not in cell:
            cell["id"] = str(uuid4())
        cell_type = cell["cell_type"]
        cell_source = cell["source"]
        cell_source = "".join(cell_source) if isinstance(cell_source, list) else cell_source
        cell["source"] = Y.YText(cell_source)
        cell["metadata"] = Y.YMap(cell.get("metadata", {}))

        if cell_type in ("raw", "markdown"):
            if "attachments" in cell and not cell["attachments"]:
                del cell["attachments"]
        elif cell_type == "code":
            cell["outputs"] = Y.YArray(cell.get("outputs", []))

        return Y.YMap(cell)

    def set_ycell(self, index: int, ycell: Y.YMap, txn: Optional[Y.YTransaction] = None) -> None:
        """
        Sets a Y cell into the indicated position.

        :param index: The index of the cell.
        :type index: int

        :param ycell: A YMap with the content of a cell.
        :type ycell: :class:`y_py.YMap`

        :param txn: A YTransaction, defaults to None
        :type txn: :class:`y_py.YTransaction`, optional.
        """
        if txn is None:
            with self._ydoc.begin_transaction() as txn:
                self._ycells.delete(txn, index)
                self._ycells.insert(txn, index, ycell)
        else:
            self._ycells.delete(txn, index)
            self._ycells.insert(txn, index, ycell)

    def get(self) -> Dict:
        """
        Returns the content of the document.

        :return: Document's content.
        :rtype: Dict
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

    def set(self, value: Dict) -> None:
        """
        Sets the content of the document.

        :param value: The content of the document.
        :type value: Dict
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
            self._ymeta.set(t, "nbformat", nb["nbformat"])
            self._ymeta.set(t, "nbformat_minor", nb["nbformat_minor"])
            self._ymeta.set(t, "metadata", Y.YMap(nb.get("metadata", {})))

    def observe(self, callback: Callable[[Any], None]) -> None:
        """
        Subscribes to document changes.

        :param callback: Callback that will be called when the document changes.
        :type callback: Callable[[Any], None]
        """
        self.unobserve()
        self._subscriptions[self._ystate] = self._ystate.observe(callback)
        self._subscriptions[self._ymeta] = self._ymeta.observe_deep(callback)
        self._subscriptions[self._ycells] = self._ycells.observe_deep(callback)
