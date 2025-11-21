# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from dataclasses import dataclass

from pycrdt import ArrayEvent, Map, MapEvent, TextEvent
from pytest import mark

from jupyter_ydoc import YNotebook


def make_code_cell(source: str):
    return {
        "cell_type": "code",
        "source": source,
        "metadata": {},
        "outputs": [],
        "execution_count": None,
    }


class AnyInstanceOf:
    def __init__(self, cls):
        self.cls = cls

    def __eq__(self, other):
        return isinstance(other, self.cls)


def test_set_preserves_cells_when_unchanged():
    nb = YNotebook()

    assert nb.version == "2.0.0"

    nb.set({"cells": [make_code_cell("print('a')\n"), make_code_cell("print('b')\n")]})

    changes = []

    def record_changes(topic, event):
        changes.append((topic, event))  # pragma: nocover

    nb.observe(record_changes)

    model = nb.get()

    # Call set with identical structure
    nb.set(model)

    # No changes should be observed at all
    assert changes == []


def test_set_populates_metadata():
    nb = YNotebook()
    nb.set({"cells": []})
    assert nb.get()["metadata"] == {
        "kernelspec": {"display_name": "", "name": ""},
        "language_info": {"name": ""},
    }


def test_set_preserves_cells_with_insert_and_remove():
    nb = YNotebook()
    nb.set(
        {
            "cells": [
                make_code_cell("print('a')\n"),  # original 0
                make_code_cell("print('b')\n"),  # original 1 (will remove)
                make_code_cell("print('c')\n"),  # original 2
            ]
        }
    )

    # Capture textual content for sanity check
    cell0_source_text = str(nb.ycells[0]["source"])
    cell2_source_text = str(nb.ycells[2]["source"])

    # Get the model as Python object
    model = nb.get()

    # Remove the middle cell and insert a new one between the retained cells
    cells = model["cells"]
    assert len(cells) == 3

    # The cell ids are needed for retention logic; keep first and last
    first = cells[0]
    last = cells[2]

    # New inserted cell
    inserted = make_code_cell("print('x')\n")
    model["cells"] = [first, inserted, last]

    changes = []

    def record_changes(topic, event):
        changes.append((topic, event))

    nb.observe(record_changes)
    nb.set(model)

    assert nb.cell_number == 3

    # Content of the first and last cells should remain the same
    assert str(nb.ycells[0]["source"]) == cell0_source_text
    assert str(nb.ycells[2]["source"]) == cell2_source_text

    # The middle cell should have a different source now
    assert str(nb.ycells[1]["source"]) == "print('x')\n"

    # We should have one cell event
    cell_events = [e for t, e in changes if t == "cells"]
    assert len(cell_events) == 1
    event_transactions = cell_events[0]
    assert len(event_transactions) == 1
    assert event_transactions[0].delta == [
        {"retain": 1},
        {"delete": 1},
        {"insert": [AnyInstanceOf(Map)]},
    ]


@dataclass
class ExpectedEvent:
    kind: type
    path: str | None = None

    def __eq__(self, other):
        if not isinstance(other, self.kind):
            return False
        if self.path is not None and self.path != other.path:
            return False
        return True

    def __repr__(self):
        if self.path is not None:
            return f"ExpectedEvent({self.kind.__name__}, path={self.path!r})"
        return f"ExpectedEvent({self.kind.__name__})"


@mark.parametrize(
    "modifications, expected_events",
    [
        # modifications of single attributes
        ([["source", "'b'"]], [ExpectedEvent(TextEvent)]),
        ([["outputs", []]], [ExpectedEvent(ArrayEvent, path=[0, "outputs"])]),
        (
            [["outputs", [{"name": "stdout", "output_type": "stream", "text": "b\n"}]]],
            [ExpectedEvent(ArrayEvent, path=[])],
        ),
        ([["execution_count", 2]], [ExpectedEvent(MapEvent)]),
        ([["metadata", {"tags": []}]], [ExpectedEvent(MapEvent)]),
        ([["new_key", "test"]], [ExpectedEvent(MapEvent)]),
        # multi-attribute modifications
        (
            [["source", "10"], ["execution_count", 10]],
            [ExpectedEvent(MapEvent), ExpectedEvent(TextEvent)],
        ),
    ],
)
def test_modify_single_cell(modifications, expected_events):
    nb = YNotebook()
    nb.set(
        {
            "cells": [
                {
                    "id": "8800f7d8-6cad-42ef-a339-a9c185ffdd54",
                    "cell_type": "code",
                    "source": "'a'",
                    "metadata": {"tags": ["test-tag"]},
                    "outputs": [{"name": "stdout", "output_type": "stream", "text": ["a\n"]}],
                    "execution_count": 1,
                },
            ]
        }
    )

    # Get the model as Python object
    model = nb.get()

    # Make changes
    for modification in modifications:
        key, new_value = modification
        model["cells"][0][key] = new_value

    changes = []

    def record_changes(topic, event):
        changes.append((topic, event))

    nb.observe(record_changes)
    nb.set(model)

    for modification in modifications:
        key, new_value = modification
        after = nb.ycells[0][key]
        after_py = after.to_py() if hasattr(after, "to_py") else after
        assert after_py == new_value

    # there should be only one change
    assert len(changes) == 1
    cell_events = [e for t, e in changes if t == "cells"]
    # and it should be a cell change
    assert len(cell_events) == 1
    # but it should be a change to cell data, not a change to the cell list
    events = cell_events[0]
    assert events == expected_events
