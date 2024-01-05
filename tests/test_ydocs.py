from jupyter_ydoc import YBlob


def test_yblob():
    yblob = YBlob()
    assert yblob.get() == b""
    yblob.set(b"012")
    assert yblob.get() == b"012"
    changes = []

    def callback(topic, event):
        print(topic, event)
        changes.append((topic, event))

    yblob.observe(callback)
    yblob.set(b"345")
    assert len(changes) == 1
    topic, event = changes[0]
    assert topic == "source"
    assert event.keys["bytes"]["oldValue"] == b"012"
    assert event.keys["bytes"]["newValue"] == b"345"
