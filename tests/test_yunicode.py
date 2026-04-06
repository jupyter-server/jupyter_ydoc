# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import pytest
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


@pytest.mark.timeout(15)
def test_set_fast_path_for_large_initial_content():
    text = YUnicode()

    # Simulate opening a large (1GB) text file from an empty document.
    large_content = "a" * (1024 * 1024 * 1024)
    text.set(large_content)

    assert text.get() == large_content


@pytest.mark.parametrize(
    "initial, updated, granular",
    [
        (
            # emojis swapped
            "I like security 🎨 but I really love painting 🔒",
            "I like security 🔒 but I really love painting 🎨",
            True,
        ),
        (
            # text changes, emojis stay in place
            "Here is a rocket: ⭐ and a star: 🚀",
            "Here is a star: ⭐ and a rocket: 🚀",
            True,
        ),
        (
            # change of text and emojis
            "Here are some happy faces: 😀😁😂",
            "Here are some sad faces: 😞😢😭",
            True,
        ),
        (
            # change of characters with combining marks
            "Combining characters: á é í ó ú",
            "Combining characters: ú ó í é á",
            True,
        ),
        (
            "Flags: 🇺🇸🇬🇧🇨🇦",
            "Flags: 🇨🇦🇬🇧🇺🇸",
            True,
        ),
        (
            # Emoji with skin tone modifiers
            "Waving hands: 👋👋🏻👋🏿",
            "Waving hands: 👋🏿👋🏻👋",
            False,  # overlapping grapheme clusters, should trigger hard reload
        ),
        (
            # Zero-width joiner sequences (family emoji)
            "A family 👨‍👩‍👧‍👦 (with two children)",
            "A family 👨‍👩‍👧 (with one child)",
            True,
        ),
        (
            # Mixed RTL/LTR text
            "Hello שלום world",
            "Hello עולם world",
            True,
        ),
        (
            # Zero-width characters
            "Word​break vs Word​​break",  # zero-width space
            "Word​​break vs Word​break",
            True,
        ),
        (
            # Keycap sequences
            "Numbers: 1️⃣2️⃣3️⃣",
            "Numbers: 3️⃣2️⃣1️⃣",
            True,
        ),
        (
            # Mixed emoji presentation styles
            "Text style: ☺︎ vs emoji style: ☺️",
            "Text style: ☹︎ vs emoji style: ☹️",
            True,
        ),
        (
            # NFD vs NFC normalization (é can be one or two codepoints)
            "Café" + "\u0301",  # e + combining acute accent at the end
            "Caff" + "\u0301",
            True,
        ),
        (
            # Emoji at boundaries
            "👋 middle text 🎉",
            "🎉 middle text 👋",
            True,
        ),
        (
            # Consecutive emoji with different byte lengths
            "Grinning face + a flag 😀🏴",
            "Grinning face + a flag 🏴😀",
            False,  # overlapping grapheme clusters, should trigger hard reload
        ),
        (
            # Japanese characters
            "こんにちは世界",
            "こんにちは地球",
            True,
        ),
        (
            # Julia math operators
            "x ∈ [1, 2, 3] && y ≥ 0",
            "x ∉ [1, 2, 3] || y ≤ 0",
            True,
        ),
    ],
)
def test_multibyte_unicode(initial, updated, granular):
    text = YUnicode()
    text.set(initial)

    changes = []

    def record_changes(topic, event):
        changes.append((topic, event))  # pragma: nocover

    text.observe(record_changes)

    text.set(updated)

    assert len(changes) == 1
    source_events = [e for t, e in changes if t == "source"]

    expected_min_delta_length = 3 if granular else 2

    assert len(source_events[0].delta) >= expected_min_delta_length
    assert text.get() == updated
