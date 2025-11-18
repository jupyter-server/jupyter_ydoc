# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from pycrdt import Map

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
    nb.set({"cells": [make_code_cell("print('a')\n"), make_code_cell("print('b')\n")]})

    changes = []

    def record_changes(topic, event):
        changes.append((topic, event))

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
