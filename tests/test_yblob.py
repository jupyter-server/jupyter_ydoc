# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from jupyter_ydoc import YBlob


def test_set_no_op_if_unchanged():
    blob = YBlob()

    assert blob.version == "2.0.0"

    content0 = b"012"
    blob.set(content0)

    changes = []

    def record_changes(topic, event):
        changes.append((topic, event))  # pragma: nocover

    blob.observe(record_changes)

    content1 = blob.get()
    assert content0 == content1

    # Call set with identical content
    blob.set(content0)

    # No changes should be observed at all
    assert changes == []
