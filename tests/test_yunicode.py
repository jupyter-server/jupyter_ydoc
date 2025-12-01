# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from pycrdt import TextEvent
from utils import ExpectedEvent

from jupyter_ydoc import YUnicode


def test_set_no_op_if_unchanged():
    text = YUnicode()

    assert text.version == "1.0.0"

    text.set("test content")

    changes = []

    def record_changes(topic, event):
        changes.append((topic, event))  # pragma: nocover

    text.observe(record_changes)

    model = text.get()

    # Call set with identical text
    text.set(model)

    # No changes should be observed at all
    assert changes == []


def test_set_granular_changes():
    text = YUnicode()

    text.set(
        "\n".join(
            [
                "Mary had a little lamb,",
                "Its fleece was white as snow.",
                "And everywhere that Mary went,",
                "The lamb was sure to go.",
            ]
        )
    )

    changes = []

    def record_changes(topic, event):
        changes.append((topic, event))  # pragma: nocover

    text.observe(record_changes)

    # Call set with the bunny version
    text.set(
        "\n".join(
            [
                "Mary had a little bunny,",
                "Its fur was white as snow.",
                "And everywhere that Mary went,",
                "The bunny was sure to hop.",
            ]
        )
    )

    assert len(changes) == 1
    source_events = [e for t, e in changes if t == "source"]
    assert source_events == [
        ExpectedEvent(
            TextEvent,
            delta=[
                # "Mary had a little <delete:lam>b"
                {"retain": 18},
                {"delete": 3},
                {"retain": 1},
                # "Mary had a little b<insert:unny>"
                {"insert": "unny"},
                # ",↵ Its f<delete:leece>"
                {"retain": 7},
                {"delete": 5},
                # ",↵ Its f<insert:ur>"
                {"insert": "ur"},
                # " was white as snow.↵"
                # "And everywhere that Mary went,↵"
                # "The <delete:lam>b"
                {"retain": 55},
                {"delete": 3},
                {"retain": 1},
                # "The b<insert:unny> was sure to"
                {"insert": "unny"},
                {"retain": 13},
                # "<delete:g><insert:h>o<insert:p>"
                {"delete": 1},
                {"insert": "h"},
                {"retain": 1},
                {"insert": "p"},
            ],
        )
    ]


def test_set_granular_append():
    text = YUnicode()

    text.set(
        "\n".join(
            [
                "Mary had a little lamb,",
                "Its fleece was white as snow.",
            ]
        )
    )

    changes = []

    def record_changes(topic, event):
        changes.append((topic, event))  # pragma: nocover

    text.observe(record_changes)

    # append a line
    text.set(
        "\n".join(
            [
                "Mary had a little lamb,",
                "Its fleece was white as snow.",
                "And everywhere that Mary went,",
            ]
        )
    )

    # append one more line
    text.set(
        "\n".join(
            [
                "Mary had a little lamb,",
                "Its fleece was white as snow.",
                "And everywhere that Mary went,",
                "The lamb was sure to go.",
            ]
        )
    )

    assert len(changes) == 2
    source_events = [e for t, e in changes if t == "source"]
    assert source_events == [
        ExpectedEvent(
            TextEvent, delta=[{"retain": 53}, {"insert": "\nAnd everywhere that Mary went,"}]
        ),
        ExpectedEvent(TextEvent, delta=[{"retain": 84}, {"insert": "\nThe lamb was sure to go."}]),
    ]


def test_set_hard_reload_if_very_different():
    text = YUnicode()

    text.set(
        "\n".join(
            [
                "Mary had a little lamb,",
                "Its fleece was white as snow.",
                "And everywhere that Mary went,",
                "The lamb was sure to go.",
            ]
        )
    )

    changes = []

    def record_changes(topic, event):
        changes.append((topic, event))  # pragma: nocover

    text.observe(record_changes)

    # Call set with a very different nursery rhyme
    twinkle_lyrics = "\n".join(
        [
            "Twinkle, twinkle, little star,",
            "How I wonder what you are!",
            "Up above the world so high,",
            "Like a diamond in the sky.",
        ]
    )
    text.set(twinkle_lyrics)

    assert len(changes) == 1
    source_events = [e for t, e in changes if t == "source"]
    assert source_events == [
        ExpectedEvent(TextEvent, delta=[{"delete": 109}, {"insert": twinkle_lyrics}])
    ]
