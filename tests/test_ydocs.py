# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from jupyter_ydoc import YNotebook


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
