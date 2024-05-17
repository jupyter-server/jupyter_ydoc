# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from jupyter_ydoc import YBlob, YNotebook, add_stdin


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


def test_stdin():
    ynotebook = YNotebook()
    ynotebook.append_cell(
        {
            "cell_type": "code",
            "source": "",
        }
    )
    ycell = ynotebook.ycells[0]
    add_stdin(ycell, prompt="pwd:", password=True)
    stdin = ycell["outputs"][0]["input"]
    stdin += "mypassword"
    cell = ycell.to_py()
    # cell ID is random, ignore that
    del cell["id"]
    # input ID is random, ignore that
    del cell["outputs"][0]["id"]
    assert cell == {
        "outputs": [
            {
                "output_type": "stdin",
                "input": "mypassword",
                "prompt": "pwd:",
                "password": True,
                "submitted": False,
            }
        ],
        "source": "",
        "metadata": {},
        "cell_type": "code",
    }
