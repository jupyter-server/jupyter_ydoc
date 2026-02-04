# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from pycrdt import Awareness, Doc

from jupyter_ydoc import YBlob, YNotebook


def test_yblob():
    yblob = YBlob()
    assert yblob.get() == b""
    yblob.set(b"012")
    assert yblob.get() == b"012"
    changes = []

    def callback(topic, event):
        changes.append((topic, event))

    yblob.observe(callback)
    yblob.set(b"345")
    assert len(changes) == 1
    topic, event = changes[0]
    assert topic == "source"
    assert event.keys["bytes"]["oldValue"] == b"012"
    assert event.keys["bytes"]["newValue"] == b"345"


def test_ynotebook_undo_manager():
    ynotebook = YNotebook()
    cell0 = {
        "cell_type": "code",
        "source": "Hello",
    }
    ynotebook.append_cell(cell0)
    source = ynotebook.ycells[0]["source"]
    source += ", World!\n"
    cell1 = {
        "cell_type": "code",
        "source": "print(1 + 1)\n",
    }
    ynotebook.append_cell(cell1)
    assert len(ynotebook.ycells) == 2
    assert str(ynotebook.ycells[0]["source"]) == "Hello, World!\n"
    assert str(ynotebook.ycells[1]["source"]) == "print(1 + 1)\n"
    assert ynotebook.undo_manager.can_undo()
    ynotebook.undo_manager.undo()
    assert len(ynotebook.ycells) == 1
    assert str(ynotebook.ycells[0]["source"]) == "Hello, World!\n"
    assert ynotebook.undo_manager.can_undo()
    ynotebook.undo_manager.undo()
    assert len(ynotebook.ycells) == 1
    assert str(ynotebook.ycells[0]["source"]) == "Hello"
    assert ynotebook.undo_manager.can_undo()
    ynotebook.undo_manager.undo()
    assert len(ynotebook.ycells) == 0
    assert not ynotebook.undo_manager.can_undo()


def test_awareness():
    yblob = YBlob()
    assert yblob.awareness is None

    ydoc = Doc()
    awareness = Awareness(ydoc)
    yblob = YBlob(ydoc, awareness)
    assert yblob.awareness == awareness


def test_state():
    ynotebook = YNotebook()
    changes = []

    def callback(topic, event):
        changes.append((topic, event))

    ynotebook.observe(callback)
    ynotebook.ystate["foo"] = "bar"

    assert ynotebook.ystate["foo"] == "bar"
    assert len(changes) == 1
    topic, event = changes[0]
    assert topic == "state"
    assert event.keys == {"foo": {"action": "add", "newValue": "bar"}}
