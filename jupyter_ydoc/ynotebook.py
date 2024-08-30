# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import copy
from functools import partial
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from pycrdt import Array, Doc, Map, Text

from .utils import cast_all
from .ybasedoc import YBaseDoc

# The default major version of the notebook format.
NBFORMAT_MAJOR_VERSION = 4
# The default minor version of the notebook format.
NBFORMAT_MINOR_VERSION = 5


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
                    "execution_state": str,
                    "execution_count": Int | None,
                    "outputs": [] | None,
                    "attachments": {} | None
                ]
            ]
        }
    """

    def __init__(self, ydoc: Optional[Doc] = None):
        """
        Constructs a YNotebook.

        :param ydoc: The :class:`pycrdt.Doc` that will hold the data of the document, if provided.
        :type ydoc: :class:`pycrdt.Doc`, optional.
        """
        super().__init__(ydoc)
        self._ymeta = self._ydoc.get("meta", type=Map)
        self._ycells = self._ydoc.get("cells", type=Array)
        self.undo_manager.expand_scope(self._ycells)

    @property
    def version(self) -> str:
        """
        Returns the version of the document.

        :return: Document's version.
        :rtype: str
        """
        return "2.0.0"

    @property
    def ycells(self):
        """
        Returns the Y-cells.

        :return: The Y-cells.
        :rtype: :class:`pycrdt.Array`
        """
        return self._ycells

    @property
    def cell_number(self) -> int:
        """
        Returns the number of cells in the notebook.

        :return: The cell number.
        :rtype: int
        """
        return len(self._ycells)

    def get_cell(self, index: int) -> Dict[str, Any]:
        """
        Returns a cell.

        :param index: The index of the cell.
        :type index: int

        :return: A cell.
        :rtype: Dict[str, Any]
        """
        meta = self._ymeta.to_py()
        cell = self._ycells[index].to_py()
        cell.pop("execution_state", None)
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

    def append_cell(self, value: Dict[str, Any]) -> None:
        """
        Appends a cell.

        :param value: A cell.
        :type value: Dict[str, Any]
        """
        ycell = self.create_ycell(value)
        self._ycells.append(ycell)

    def set_cell(self, index: int, value: Dict[str, Any]) -> None:
        """
        Sets a cell into indicated position.

        :param index: The index of the cell.
        :type index: int

        :param value: A cell.
        :type value: Dict[str, Any]
        """
        ycell = self.create_ycell(value)
        self.set_ycell(index, ycell)

    def create_ycell(self, value: Dict[str, Any]) -> Map:
        """
        Creates YMap with the content of the cell.

        :param value: A cell.
        :type value: Dict[str, Any]

        :return: A new cell.
        :rtype: :class:`pycrdt.Map`
        """
        cell = copy.deepcopy(value)
        if "id" not in cell:
            cell["id"] = str(uuid4())
        cell_type = cell["cell_type"]
        cell_source = cell["source"]
        cell_source = "".join(cell_source) if isinstance(cell_source, list) else cell_source
        cell["source"] = Text(cell_source)
        cell["metadata"] = Map(cell.get("metadata", {}))

        if cell_type in ("raw", "markdown"):
            if "attachments" in cell and not cell["attachments"]:
                del cell["attachments"]
        elif cell_type == "code":
            outputs = cell.get("outputs", [])
            for idx, output in enumerate(outputs):
                if output.get("output_type") == "stream":
                    output["text"] = Array(output.get("text", []))
                outputs[idx] = Map(output)
            cell["outputs"] = Array(outputs)
            cell["execution_state"] = "idle"

        return Map(cell)

    def set_ycell(self, index: int, ycell: Map) -> None:
        """
        Sets a Y cell into the indicated position.

        :param index: The index of the cell.
        :type index: int

        :param ycell: A YMap with the content of a cell.
        :type ycell: :class:`pycrdt.Map`
        """
        self._ycells[index] = ycell

    def get(self) -> Dict:
        """
        Returns the content of the document.

        :return: Document's content.
        :rtype: Dict
        """
        meta = self._ymeta.to_py()
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
            metadata=meta.get("metadata", {}),
            nbformat=int(meta.get("nbformat", 0)),
            nbformat_minor=int(meta.get("nbformat_minor", 0)),
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
        cells = value["cells"]

        with self._ydoc.transaction():
            # clear document
            self._ymeta.clear()
            self._ycells.clear()
            for key in [k for k in self._ystate.keys() if k not in ("dirty", "path")]:
                del self._ystate[key]

            # initialize document
            self._ycells.extend([self.create_ycell(cell) for cell in cells])
            self._ymeta["nbformat"] = nb.get("nbformat", NBFORMAT_MAJOR_VERSION)
            self._ymeta["nbformat_minor"] = nb.get("nbformat_minor", NBFORMAT_MINOR_VERSION)

            metadata = nb.get("metadata", {})
            metadata.setdefault("language_info", {"name": ""})
            metadata.setdefault("kernelspec", {"name": "", "display_name": ""})

            self._ymeta["metadata"] = Map(metadata)

    def observe(self, callback: Callable[[str, Any], None]) -> None:
        """
        Subscribes to document changes.

        :param callback: Callback that will be called when the document changes.
        :type callback: Callable[[str, Any], None]
        """
        self.unobserve()
        self._subscriptions[self._ystate] = self._ystate.observe(partial(callback, "state"))
        self._subscriptions[self._ymeta] = self._ymeta.observe_deep(partial(callback, "meta"))
        self._subscriptions[self._ycells] = self._ycells.observe_deep(partial(callback, "cells"))
