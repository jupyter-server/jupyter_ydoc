# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from jupyter_ydoc import YUnicode


def test_set_no_op_if_unchaged():
    text = YUnicode()
    text.set("test content")

    changes = []

    def record_changes(topic, event):
        changes.append((topic, event))

    text.observe(record_changes)

    model = text.get()

    # Call set with identical text
    text.set(model)

    # No changes should be observed at all
    assert changes == []
