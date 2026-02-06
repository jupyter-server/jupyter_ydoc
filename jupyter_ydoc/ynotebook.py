# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import copy
import warnings
from collections.abc import Callable
from functools import partial
from typing import Any, Iterator
from uuid import uuid4

from anyio import lowlevel
from pycrdt import Array, Awareness, Doc, Map, Text

from .utils import cast_all
from .ybasedoc import YBaseDoc

# The default major version of the notebook format.
NBFORMAT_MAJOR_VERSION = 4
# The default minor version of the notebook format.
NBFORMAT_MINOR_VERSION = 5

_CELL_KEY_TYPE_MAP = {"metadata": Map, "source": Text, "outputs": Array}


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

    def __init__(self, ydoc: Doc | None = None, awareness: Awareness | None = None):
        """
        Constructs a YNotebook.

        :param ydoc: The :class:`pycrdt.Doc` that will hold the data of the document, if provided.
        :type ydoc: :class:`pycrdt.Doc`, optional.
        :param awareness: The :class:`pycrdt.Awareness` that shares non persistent data
                          between clients.
        :type awareness: :class:`pycrdt.Awareness`, optional.
        """
        super().__init__(ydoc, awareness)
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

    def get_cell(self, index: int) -> dict[str, Any]:
        """
        Returns a cell.

        :param index: The index of the cell.
        :type index: int

        :return: A cell.
        :rtype: Dict[str, Any]
        """
        return self._cell_to_py(self._ycells[index])

    def _cell_to_py(self, ycell: Map, meta: dict[str, Any] | None = None) -> dict[str, Any]:
        if meta is None:
            meta = self._ymeta.to_py()
        cell = ycell.to_py()
        assert cell is not None
        cell.pop("execution_state", None)
        cast_all(cell, float, int)  # cells coming from Yjs have e.g. execution_count as float
        if (
            "id" in cell
            and int(meta.get("nbformat", 0)) == 4
            and int(meta.get("nbformat_minor", 0)) <= 4
        ):
            # strip cell IDs if we have notebook format 4.0-4.4
            del cell["id"]
        if (
            "attachments" in cell
            and cell["cell_type"] in ("raw", "markdown")
            and not cell["attachments"]
        ):
            del cell["attachments"]
        return cell

    def append_cell(self, value: dict[str, Any]) -> None:
        """
        Appends a cell.

        :param value: A cell.
        :type value: Dict[str, Any]
        """
        ycell = self.create_ycell(value)
        self._ycells.append(ycell)

    def set_cell(self, index: int, value: dict[str, Any]) -> None:
        """
        Sets a cell into indicated position.

        :param index: The index of the cell.
        :type index: int

        :param value: A cell.
        :type value: Dict[str, Any]
        """
        ycell = self.create_ycell(value)
        self.set_ycell(index, ycell)

    def create_ycell(self, value: dict[str, Any]) -> Map:
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
                    text = output.get("text", "")
                    if isinstance(text, str):
                        ytext = Text(text)
                    else:
                        ytext = Text("".join(text))
                    output["text"] = ytext
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

    def get(self, deduplicate: bool = True) -> dict:
        """
        Returns the content of the document.

        :return: Document's content.
        :rtype: Dict
        """
        # YNotebook._get is a generator that yields while processing cells.
        # It is used in YNotebook.get and YNotebook.aget, the former just
        # runs it until completion and the latter inserts async checkpoints
        # in order to not block the event loop for too long for notebooks
        # with a lot of cells.
        for val in self._get(deduplicate):
            pass

        assert val is not None
        return val

    def _get(self, deduplicate: bool) -> Iterator[dict | None]:
        meta = self._ymeta.to_py()
        cast_all(meta, float, int)  # notebook coming from Yjs has e.g. nbformat as float
        cells = []
        seen_ids: dict[str, tuple[int, dict]] = {}  # maps cell_id -> (index, cell converted to Python dict)

        for i in range(len(self._ycells)):
            yield None
            cell = self._cell_to_py(self._ycells[i], meta)
            cell_id = cell.get("id")

            if deduplicate and cell_id and cell_id in seen_ids:
                prev_index, prev_cell = seen_ids[cell_id]
                # Check if it's an exact duplicate
                if cell == prev_cell:
                    # Skip exact duplicates
                    continue
                else:
                    # Non-identical duplicate: assign a new ID
                    new_id = str(uuid4())
                    cell["id"] = new_id

                    # Update the ycell to persist the new ID for stable results
                    self._ycells[i]["id"] = new_id

                    # Find which fields differ
                    differing_fields = []
                    all_keys = set(cell.keys()) | set(prev_cell.keys())
                    for key in sorted(all_keys):
                        if cell.get(key) != prev_cell.get(key):
                            differing_fields.append(key)

                    # Emit warning
                    warnings.warn(
                        f"Non-unique cell ID '{cell_id}' used by non-identical cells detected. "
                        f"Corrected to '{new_id}'. Cells differ in {differing_fields}.",
                        UserWarning,
                        stacklevel=2,
                    )

                    seen_ids[new_id] = (i, cell)
            else:
                if deduplicate and cell_id:
                    seen_ids[cell_id] = (i, cell)

            cells.append(cell)

        yield dict(
            cells=cells,
            metadata=meta.get("metadata", {}),
            nbformat=int(meta.get("nbformat", 0)),
            nbformat_minor=int(meta.get("nbformat_minor", 0)),
        )

    def set(self, value: dict) -> None:
        """
        Sets the content of the document.

        :param value: The content of the document.
        :type value: Dict
        """
        # YNotebook._set is a generator that yields while processing cells.
        # It is used in YNotebook.set and YNotebook.aset, the former just
        # runs it until completion and the latter inserts async checkpoints
        # in order to not block the event loop for too long for notebooks
        # with a lot of cells.
        for _ in self._set(value):
            pass

    def _set(self, value: dict) -> Iterator[None]:
        nb_without_cells = {key: value[key] for key in value.keys() if key != "cells"}
        nb = copy.deepcopy(nb_without_cells)
        cast_all(nb, int, float)  # Yjs expects numbers to be floating numbers

        meta = self._ymeta.to_py()

        new_cells = value["cells"] or [
            {
                "cell_type": "code",
                "execution_count": None,
                # auto-created empty code cell without outputs ought be trusted
                "metadata": {"trusted": True},
                "outputs": [],
                "source": "",
                "id": str(uuid4()),
            }
        ]
        # Build dict of old cells by ID, keeping only the first occurrence of each ID
        # to handle the case where the stored doc already has duplicate IDs.
        old_ycells_by_id: dict[str, Map] = {}
        for ycell in self._ycells:
            yield
            cell_id = ycell.get("id")
            if cell_id is not None and cell_id not in old_ycells_by_id:
                old_ycells_by_id[cell_id] = ycell

        with self._ydoc.transaction():
            new_cell_list: list[dict] = []
            retained_cells = set()

            # Determine cells to be retained
            for new_cell in new_cells:
                yield
                cell_id = new_cell.get("id")
                if cell_id and (old_ycell := old_ycells_by_id.get(cell_id)):
                    old_cell = self._cell_to_py(old_ycell, meta)
                    updated_granularly = self._update_cell(
                        old_cell=old_cell, new_cell=new_cell, old_ycell=old_ycell
                    )

                    if updated_granularly:
                        new_cell_list.append(new_cell)
                        retained_cells.add(cell_id)
                        continue
                # New or changed cell
                new_cell_list.append(new_cell)

            # First delete all non-retained cells and duplicates
            if not retained_cells:
                # fast path if no cells were retained
                self._ycells.clear()
            else:
                index = 0
                seen: set[str] = set()
                while True:
                    yield
                    if index == len(self._ycells):
                        break
                    old_ycell = self._ycells[index]
                    cell_id = old_ycell.get("id")
                    if cell_id is None or cell_id not in retained_cells or cell_id in seen:
                        self._ycells.pop(index)
                    else:
                        seen.add(cell_id)
                        index += 1

            # Now reorder/insert cells to match new_cell_list
            for index, new_cell in enumerate(new_cell_list):
                yield
                new_id = new_cell.get("id")

                # Fast path: correct cell already at this position
                if len(self._ycells) > index and self._ycells[index].get("id") == new_id:
                    continue

                # Retained cell: find and move it into position
                if new_id is not None and new_id in retained_cells:
                    # Linear scan to find the cell (O(n) per retained cell)
                    for cur in range(index + 1, len(self._ycells)):
                        yield
                        if self._ycells[cur].get("id") == new_id:
                            # Use delete+recreate instead of move() for yjs 13.x compatibility
                            # (yjs 13.x doesn't support the move operation that pycrdt generates)
                            del self._ycells[cur]
                            self._ycells.insert(index, self.create_ycell(new_cell))
                            break
                    continue

                # New cell: insert at position
                self._ycells.insert(index, self.create_ycell(new_cell))

            # Remove any extra cells at the end
            del self._ycells[len(new_cell_list) :]

            for key in [
                k for k in self._ystate.keys() if k not in ("dirty", "path", "document_id")
            ]:
                del self._ystate[key]

            nbformat_major = nb.get("nbformat", NBFORMAT_MAJOR_VERSION)
            nbformat_minor = nb.get("nbformat_minor", NBFORMAT_MINOR_VERSION)

            if meta.get("nbformat") != nbformat_major:
                self._ymeta["nbformat"] = nbformat_major

            if meta.get("nbformat_minor") != nbformat_minor:
                self._ymeta["nbformat_minor"] = nbformat_minor

            old_metadata = meta.get("metadata")
            metadata = nb.get("metadata", {})

            if metadata != old_metadata:
                metadata.setdefault("language_info", {"name": ""})
                metadata.setdefault("kernelspec", {"name": "", "display_name": ""})
                self._ymeta["metadata"] = Map(metadata)

    async def aget(self, deduplicate: bool = True) -> dict:
        """
        Returns the content of the document, yielding to the event loop often enough
        to not block it for too long.

        :param deduplicate: Whether to deduplicate cells with the same ID.
        :type deduplicate: bool
        :return: Document's content.
        :rtype: Dict
        """
        for val in self._get(deduplicate):
            await lowlevel.checkpoint()

        assert val is not None
        return val

    async def aset(self, value: dict) -> None:
        """
        Sets the content of the document, yielding to the event loop often enough
        to not block it for too long.

        :param value: The content of the document.
        :type value: Dict
        """
        for val in self._set(value):
            await lowlevel.checkpoint()

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

    def _update_cell(self, old_cell: dict, new_cell: dict, old_ycell: Map) -> bool:
        if old_cell == new_cell:
            return True
        # attempt to update cell granularly
        old_keys = set(old_cell.keys())
        new_keys = set(new_cell.keys())

        shared_keys = old_keys & new_keys
        removed_keys = old_keys - new_keys
        added_keys = new_keys - old_keys

        for key in shared_keys:
            if old_cell[key] != new_cell[key]:
                value = new_cell[key]
                if (
                    key == "outputs"
                    and value
                    and any(output.get("output_type") == "stream" for output in value)
                ):
                    # Outputs with stream require complex handling as they have
                    # the Text type nested inside; for now skip creating them.
                    # Clearing all outputs is fine.
                    return False

                if key in _CELL_KEY_TYPE_MAP:
                    kind = _CELL_KEY_TYPE_MAP[key]

                    if not isinstance(old_ycell[key], kind):
                        # if our assumptions about types do not hold, fall back to hard update
                        return False

                    if kind == Text:
                        old_text: Text = old_ycell[key]
                        old_text.clear()
                        old_text += value
                    elif kind == Array:
                        old_array: Array = old_ycell[key]
                        old_array.clear()
                        old_array.extend(value)
                    elif kind == Map:
                        old_map: Map = old_ycell[key]
                        old_map.clear()
                        old_map.update(value)
                else:
                    old_ycell[key] = new_cell[key]

        for key in removed_keys:
            del old_ycell[key]

        for key in added_keys:
            if key in _CELL_KEY_TYPE_MAP:
                # we hard-reload cells when keys that require nested types get added
                # to allow the frontend to connect observers; this could be changed
                # in the future, once frontends learn how to observe all changes
                return False
            else:
                old_ycell[key] = new_cell[key]
        return True
