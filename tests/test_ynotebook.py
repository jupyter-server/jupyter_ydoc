# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import json
from time import monotonic
from uuid import uuid4

import pytest
from anyio import create_task_group, lowlevel
from pycrdt import ArrayEvent, Map, MapEvent, TextEvent
from pytest import mark
from utils import ExpectedEvent

from jupyter_ydoc import YNotebook

pytestmark = mark.anyio


def make_code_cell(source: str, id: str | None = None):
    cell = {
        "cell_type": "code",
        "source": source,
        "metadata": {},
        "outputs": [],
        "execution_count": None,
    }
    if id is not None:
        cell["id"] = id
    return cell


class AnyInstanceOf:
    def __init__(self, cls):
        self.cls = cls

    def __eq__(self, other):
        return isinstance(other, self.cls)


async def test_set_preserves_cells_when_unchanged(do):
    nb = YNotebook()

    assert nb.version == "2.0.0"

    await do(nb, "set", {"cells": [make_code_cell("print('a')\n"), make_code_cell("print('b')\n")]})

    changes = []

    def record_changes(topic, event):
        changes.append((topic, event))  # pragma: nocover

    nb.observe(record_changes)

    model = await do(nb, "get")

    # Call set with identical structure
    await do(nb, "set", model)

    # No changes should be observed at all
    assert changes == []


async def test_set_populates_metadata(do):
    nb = YNotebook()
    await do(nb, "set", {"cells": []})
    assert (await do(nb, "get"))["metadata"] == {
        "kernelspec": {"display_name": "", "name": ""},
        "language_info": {"name": ""},
    }


@pytest.mark.parametrize("progressive", [False, True], ids=["not progressive", "progressive"])
async def test_set_preserves_cells_with_insert_and_remove(do, progressive):
    nb = YNotebook()
    await do(
        nb,
        "set",
        {
            "cells": [
                make_code_cell("print('a')\n"),  # original 0
                make_code_cell("print('b')\n"),  # original 1 (will remove)
                make_code_cell("print('c')\n"),  # original 2
            ]
        },
    )

    # Capture textual content for sanity check
    cell0_source_text = str(nb.ycells[0]["source"])
    cell2_source_text = str(nb.ycells[2]["source"])

    # Get the model as Python object
    model = await do(nb, "get")

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
    if progressive:
        await nb.aset_progressively(model)
    else:
        await do(nb, "set", model)

    assert nb.cell_number == 3

    # Content of the first and last cells should remain the same
    assert str(nb.ycells[0]["source"]) == cell0_source_text
    assert str(nb.ycells[2]["source"]) == cell2_source_text

    # The middle cell should have a different source now
    assert str(nb.ycells[1]["source"]) == "print('x')\n"

    cell_events = [e for t, e in changes if t == "cells"]
    if progressive:
        assert len(cell_events) == 2
        event_transactions = cell_events[0]
        assert len(event_transactions) == 1
        assert event_transactions[0].delta == [
            {"retain": 1},
            {"delete": 1},
        ]
        event_transactions = cell_events[1]
        assert len(event_transactions) == 1
        assert event_transactions[0].delta == [
            {"retain": 1},
            {"insert": [AnyInstanceOf(Map)]},
        ]
    else:
        # We should have one cell event
        assert len(cell_events) == 1
        event_transactions = cell_events[0]
        assert len(event_transactions) == 1
        assert event_transactions[0].delta == [
            {"retain": 1},
            {"delete": 1},
            {"insert": [AnyInstanceOf(Map)]},
        ]


async def test_aset_progressively_populates_metadata_before_cells():
    nb = YNotebook()
    changes = []

    def record_changes(topic, event):
        changes.append((topic, event))

    nb.observe(record_changes)
    await nb.aset_progressively(
        {
            "cells": [
                make_code_cell("print('a')\n", id="cell-a"),
                make_code_cell("print('b')\n", id="cell-b"),
            ]
        }
    )

    topics = [topic for topic, _ in changes]
    assert topics[0] == "meta"

    cell_events = [event for topic, event in changes if topic == "cells"]
    assert len(cell_events) == 2
    assert cell_events[0][0].delta == [{"insert": [AnyInstanceOf(Map)]}]
    assert cell_events[1][0].delta == [{"retain": 1}, {"insert": [AnyInstanceOf(Map)]}]


async def test_aset_progressively_delays_large_outputs_until_after_cells():
    nb = YNotebook()
    outputs = [{"name": "stdout", "output_type": "stream", "text": "x" * 1024}]
    cell = make_code_cell("print('x')\n", id="cell-with-output")
    cell["outputs"] = outputs
    snapshots = []

    def record_changes(topic, event):
        if topic == "cells":
            snapshots.append(nb.ycells.to_py())

    nb.observe(record_changes)
    await nb.aset_progressively(
        {"cells": [cell]},
        delay_outputs_above_mb=0,
    )

    assert len(snapshots) == 2
    assert snapshots[0][0]["outputs"] == []
    assert snapshots[1][0]["outputs"] == outputs
    assert nb.ycells[0]["outputs"][0]["text"].to_py() == outputs[0]["text"]

    model = await nb.aget()
    assert model["cells"][0]["outputs"] == outputs


async def test_aset_progressively_keeps_small_outputs_with_cell():
    nb = YNotebook()
    outputs = [{"name": "stdout", "output_type": "stream", "text": "x"}]
    cell = make_code_cell("print('x')\n", id="cell-with-small-output")
    cell["outputs"] = outputs
    snapshots = []

    def record_changes(topic, event):
        if topic == "cells":
            snapshots.append(nb.ycells.to_py())

    nb.observe(record_changes)
    await nb.aset_progressively(
        {"cells": [cell]},
        delay_outputs_above_mb=100,
    )

    assert len(snapshots) == 1
    assert snapshots[0][0]["outputs"] == outputs


async def test_aset_progressively_restores_delayed_outputs_after_hard_reload():
    nb = YNotebook()
    await nb.aset(
        {
            "cells": [
                {
                    "id": "cell-to-reload",
                    "cell_type": "markdown",
                    "source": "old",
                    "metadata": {},
                }
            ]
        }
    )

    outputs = [{"name": "stdout", "output_type": "stream", "text": "x" * 1024}]
    cell = make_code_cell("print('x')\n", id="cell-to-reload")
    cell["outputs"] = outputs

    await nb.aset_progressively(
        {"cells": [cell]},
        delay_outputs_above_mb=0,
    )

    model = await nb.aget()
    assert model["cells"][0]["cell_type"] == "code"
    assert model["cells"][0]["outputs"] == outputs


async def test_aset_progressively_hard_reload_does_not_emit_partial_cell_update():
    nb = YNotebook()
    await nb.aset(
        {
            "cells": [
                make_code_cell("print('keep')\n", id="keep-cell"),
                {
                    "id": "cell-to-reload",
                    "cell_type": "markdown",
                    "source": "old",
                    "metadata": {},
                },
            ]
        }
    )
    model = await nb.aget()
    model["cells"][1] = make_code_cell("print('new')\n", id="cell-to-reload")
    cell_events = []

    def record_changes(topic, event):
        if topic == "cells":
            cell_events.extend(event)

    nb.observe(record_changes)
    await nb.aset_progressively(model)

    assert all(event.path == [] for event in cell_events)
    assert cell_events[0].delta == [{"retain": 1}, {"delete": 1}]
    assert cell_events[1].delta == [{"retain": 1}, {"insert": [AnyInstanceOf(Map)]}]


async def test_aset_non_progressive_does_not_delay_outputs():
    nb = YNotebook()
    outputs = [{"name": "stdout", "output_type": "stream", "text": "x" * 1024}]
    cell = make_code_cell("print('x')\n", id="cell-with-output")
    cell["outputs"] = outputs
    snapshots = []

    def record_changes(topic, event):
        if topic == "cells":
            snapshots.append(nb.ycells.to_py())

    nb.observe(record_changes)
    await nb.aset({"cells": [cell]})

    assert len(snapshots) == 1
    assert snapshots[0][0]["outputs"] == outputs


async def test_aset_progressively_rejects_negative_delay_outputs_threshold():
    nb = YNotebook()
    with pytest.raises(ValueError, match="delay_outputs_above_mb"):
        await nb.aset_progressively(
            {"cells": [make_code_cell("print('x')\n")]},
            delay_outputs_above_mb=-1,
        )


def test_outputs_should_be_delayed_uses_configured_mb_threshold():
    nb = YNotebook()
    outputs = [{"name": "stdout", "output_type": "stream", "text": "x"}]
    output_size = len(
        json.dumps(
            outputs,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    )

    assert not nb._outputs_should_be_delayed(outputs, output_size / 1024 / 1024)
    assert nb._outputs_should_be_delayed(outputs, (output_size - 1) / 1024 / 1024)


@mark.parametrize(
    "modifications, expected_events",
    [
        # modifications of single attributes
        ([["source", "'b'"]], [ExpectedEvent(TextEvent)]),
        ([["execution_count", 2]], [ExpectedEvent(MapEvent)]),
        ([["metadata", {"tags": []}]], [ExpectedEvent(MapEvent)]),
        ([["new_key", "test"]], [ExpectedEvent(MapEvent)]),
        # outputs can be cleared using granular logic
        ([["outputs", []]], [ExpectedEvent(ArrayEvent, path=[0, "outputs"])]),
        # stream outputs require a hard cell reload, which is why we expect top-level array change
        (
            [["outputs", [{"name": "stdout", "output_type": "stream", "text": "b\n"}]]],
            [ExpectedEvent(ArrayEvent, path=[])],
        ),
        # other output types can be changed granularly
        (
            [
                [
                    "outputs",
                    [
                        {
                            "data": {"text/plain": ["1"]},
                            "execution_count": 1,
                            "metadata": {},
                            "output_type": "execute_result",
                        }
                    ],
                ]
            ],
            [ExpectedEvent(ArrayEvent, path=[0, "outputs"])],
        ),
        # multi-attribute modifications
        (
            [["source", "10"], ["execution_count", 10]],
            [ExpectedEvent(MapEvent), ExpectedEvent(TextEvent)],
        ),
    ],
)
async def test_modify_single_cell(modifications, expected_events, do):
    nb = YNotebook()
    await do(
        nb,
        "set",
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
        },
    )

    # Get the model as Python object
    model = await do(nb, "get")

    # Make changes
    for modification in modifications:
        key, new_value = modification
        model["cells"][0][key] = new_value

    changes = []

    def record_changes(topic, event):
        changes.append((topic, event))

    nb.observe(record_changes)
    await do(nb, "set", model)

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


async def test_get_merges_exact_duplicates(do):
    """Test that identical cells with the same IDs get merged on get()."""
    nb = YNotebook()
    await do(
        nb,
        "set",
        {
            "cells": [
                {"id": "cell-A", "cell_type": "markdown", "source": "a", "metadata": {}},
                {"id": "cell-B", "cell_type": "markdown", "source": "b", "metadata": {}},
            ]
        },
    )

    # Manually inject a duplicate ID to simulate corrupted state
    nb.ycells.append(
        nb.create_ycell(
            {"id": "cell-B", "cell_type": "markdown", "source": "b", "metadata": {}},
        )
    )

    # Verify we have a duplicate
    assert len(nb.ycells) == 3

    # Get the model as Python object
    model = await do(nb, "get")
    cells = model["cells"]

    # Should have exactly 2 cells with no duplicates
    ids = [cell["id"] for cell in cells]
    assert ids == ["cell-A", "cell-B"]


async def test_get_resolves_cell_id_duplicates(do):
    """Test that non-identical cells with the same IDs get different IDs on get()."""
    nb = YNotebook()
    await do(
        nb,
        "set",
        {
            "cells": [
                {"id": "cell-A", "cell_type": "markdown", "source": "a", "metadata": {}},
                {"id": "cell-B", "cell_type": "markdown", "source": "b", "metadata": {}},
            ]
        },
    )

    # Manually inject a cell with duplicate ID to simulate corrupted state
    nb.ycells.append(
        nb.create_ycell(
            {"id": "cell-B", "cell_type": "markdown", "source": "X", "metadata": {}},
        )
    )

    # Verify we have three cells
    assert len(nb.ycells) == 3

    # Get the model as Python object - should emit a warning
    with pytest.warns(
        UserWarning, match=r"Non-unique cell ID 'cell-B'.*Corrected to.*Cells differ in.*source"
    ):
        model = await do(nb, "get")

    cells = model["cells"]

    # Should have exactly 3 cells with no duplicate IDs
    ids = [cell["id"] for cell in cells]
    assert len(set(ids)) == 3  # all IDs are unique

    # Call get again to ensure stable IDs
    model2 = await do(nb, "get")
    cells2 = model2["cells"]
    ids2 = [cell["id"] for cell in cells2]
    assert ids2 == ids


async def test_set_reorder_does_not_duplicate_cells(do):
    """Test that reordering cells with the same IDs doesn't create duplicates."""
    nb = YNotebook()
    await do(
        nb,
        "set",
        {
            "cells": [
                {"id": "cell-A", "cell_type": "markdown", "source": "a", "metadata": {}},
                {"id": "cell-B", "cell_type": "markdown", "source": "b", "metadata": {}},
                {"id": "cell-C", "cell_type": "markdown", "source": "c", "metadata": {}},
            ]
        },
    )

    # Get the model as Python object
    model = await do(nb, "get", deduplicate=False)
    cells = model["cells"]

    # Reorder to C, B, A (same cells, different order)
    model["cells"] = [cells[2], cells[1], cells[0]]

    await do(nb, "set", model)

    # Should have exactly 3 cells with no duplicates
    ids = [cell["id"] for cell in (await do(nb, "get", deduplicate=False))["cells"]]
    assert ids == ["cell-C", "cell-B", "cell-A"]


async def test_set_removes_preexisting_duplicate_ids(do):
    """Test that set() cleans up pre-existing duplicate cell IDs."""
    nb = YNotebook()
    await do(
        nb,
        "set",
        {
            "cells": [
                {"id": "cell-A", "cell_type": "markdown", "source": "a", "metadata": {}},
                {"id": "cell-B", "cell_type": "markdown", "source": "b", "metadata": {}},
                {"id": "cell-C", "cell_type": "markdown", "source": "c", "metadata": {}},
            ]
        },
    )

    # Manually inject a duplicate ID to simulate corrupted state
    duplicate_cell = nb.create_ycell(
        {"id": "cell-B", "cell_type": "markdown", "source": "b-duplicate", "metadata": {}}
    )
    nb.ycells.append(duplicate_cell)

    # Verify we have a duplicate
    assert nb.cell_number == 4
    ids = [cell["id"] for cell in nb.ycells.to_py()]
    assert ids.count("cell-B") == 2

    # Get the model as Python object (with canonical data - only one cell-B)
    model = {
        "cells": [
            {"id": "cell-A", "cell_type": "markdown", "source": "a", "metadata": {}},
            {"id": "cell-B", "cell_type": "markdown", "source": "b", "metadata": {}},
            {"id": "cell-C", "cell_type": "markdown", "source": "c", "metadata": {}},
        ]
    }
    await do(nb, "set", model)

    # Should have exactly 3 cells with no duplicates
    ids = [cell["id"] for cell in (await do(nb, "get", deduplicate=False))["cells"]]
    assert ids == ["cell-A", "cell-B", "cell-C"]


async def test_set_reorder_with_mixed_operations(do):
    """Test reordering cells while also adding and removing cells."""
    nb = YNotebook()
    await do(
        nb,
        "set",
        {
            "cells": [
                {"id": "cell-A", "cell_type": "markdown", "source": "a", "metadata": {}},
                {"id": "cell-B", "cell_type": "markdown", "source": "b", "metadata": {}},
                {"id": "cell-C", "cell_type": "markdown", "source": "c", "metadata": {}},
                {"id": "cell-D", "cell_type": "markdown", "source": "d", "metadata": {}},
            ]
        },
    )

    # Get the model as Python object
    model = await do(nb, "get")
    cells = model["cells"]

    # Keep A and C from original cells
    cell_a = cells[0]
    cell_c = cells[2]

    # New inserted cell
    new_cell = {"id": "cell-NEW", "cell_type": "markdown", "source": "new", "metadata": {}}

    # Target: C, NEW, A (delete B and D, reorder C and A, insert NEW)
    model["cells"] = [cell_c, new_cell, cell_a]
    await do(nb, "set", model)

    ids = [cell["id"] for cell in (await do(nb, "get"))["cells"]]
    assert ids == ["cell-C", "cell-NEW", "cell-A"]


async def test_set_simple_adjacent_swap(do):
    """Test swapping two adjacent cells (common operation)."""
    nb = YNotebook()
    await do(
        nb,
        "set",
        {
            "cells": [
                {"id": "cell-A", "cell_type": "markdown", "source": "a", "metadata": {}},
                {"id": "cell-B", "cell_type": "markdown", "source": "b", "metadata": {}},
                {"id": "cell-C", "cell_type": "markdown", "source": "c", "metadata": {}},
            ]
        },
    )

    # Get the model as Python object
    model = await do(nb, "get")
    cells = model["cells"]

    # Swap B and C: A, C, B
    model["cells"] = [cells[0], cells[2], cells[1]]
    await do(nb, "set", model)

    ids = [cell["id"] for cell in (await do(nb, "get"))["cells"]]
    assert ids == ["cell-A", "cell-C", "cell-B"]


async def test_async_notebook():
    nb_dict0 = {"cells": [make_code_cell("print('a')\n", id=str(uuid4())) for _ in range(10_000)]}

    # measure the time to set synchronously
    nb = YNotebook()
    t0 = monotonic()
    nb.set(nb_dict0)
    t1 = monotonic()
    set_time = t1 - t0

    async def get_max_blocking_time():
        nonlocal t0, max_blocking_time
        while True:
            await lowlevel.checkpoint()
            t1 = monotonic()
            dt = t1 - t0
            if dt > max_blocking_time:
                max_blocking_time = dt
            t0 = t1

    t0 = monotonic()
    max_blocking_time = 0
    nb = YNotebook()

    async with create_task_group() as tg:
        tg.start_soon(get_max_blocking_time)
        await nb.aset(nb_dict0)
        tg.cancel_scope.cancel()

    # check that the max blocking time is at least 8 times
    # smaller than if we did a blocking set:
    assert max_blocking_time < set_time / 8
    nb_dict1 = nb.get()
    del nb_dict1["metadata"]
    del nb_dict1["nbformat"]
    del nb_dict1["nbformat_minor"]
    assert nb_dict0 == nb_dict1

    # having the notebook already populated adds extra-processing,
    # check that too:
    t0 = monotonic()
    nb.set(nb_dict0)
    t1 = monotonic()
    set_time = t1 - t0
    t0 = monotonic()
    max_blocking_time = 0

    async with create_task_group() as tg:
        tg.start_soon(get_max_blocking_time)
        await nb.aset(nb_dict0)
        tg.cancel_scope.cancel()

    # check that the max blocking time is at least 6 times
    # smaller than if we did a blocking set:
    assert max_blocking_time < set_time / 6
    nb_dict1 = nb.get()
    del nb_dict1["metadata"]
    del nb_dict1["nbformat"]
    del nb_dict1["nbformat_minor"]
    assert nb_dict0 == nb_dict1

    # measure the time to get synchronously:
    t0 = monotonic()
    nb.get()
    t1 = monotonic()
    get_time = t1 - t0

    t0 = monotonic()
    max_blocking_time = 0

    async with create_task_group() as tg:
        tg.start_soon(get_max_blocking_time)
        await nb.aget()
        tg.cancel_scope.cancel()

    # check that the max blocking time is at least 20 times
    # smaller than if we did a blocking get:
    assert max_blocking_time < get_time / 20
