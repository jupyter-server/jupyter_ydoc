# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from collections.abc import Callable
from difflib import SequenceMatcher
from functools import partial
from typing import Any

from pycrdt import Awareness, Doc, Text

from .ybasedoc import YBaseDoc

# Heuristic threshold as recommended in difflib documentation
SIMILARITY_THREESHOLD = 0.6


class YUnicode(YBaseDoc):
    """
    Extends :class:`YBaseDoc`, and represents a plain text document, encoded as UTF-8.

    Schema:

    .. code-block:: json

        {
            "state": YMap,
            "source": YText
        }
    """

    def __init__(self, ydoc: Doc | None = None, awareness: Awareness | None = None):
        """
        Constructs a YUnicode.

        :param ydoc: The :class:`pycrdt.Doc` that will hold the data of the document, if provided.
        :type ydoc: :class:`pycrdt.Doc`, optional.
        :param awareness: The :class:`pycrdt.Awareness` that shares non persistent data
                          between clients.
        :type awareness: :class:`pycrdt.Awareness`, optional.
        """
        super().__init__(ydoc, awareness)
        self._ysource: Text = self._ydoc.get("source", type=Text)
        self.undo_manager.expand_scope(self._ysource)

    @property
    def version(self) -> str:
        """
        Returns the version of the document.

        :return: Document's version.
        :rtype: str
        """
        return "1.0.0"

    def get(self) -> str:
        """
        Returns the content of the document.

        :return: Document's content.
        :rtype: str
        """
        return str(self._ysource)

    def set(self, value: str) -> None:
        """
        Sets the content of the document.

        :param value: The content of the document.
        :type value: str
        """
        old_value = self.get()
        if old_value == value:
            # no-op if the values are already the same,
            # to avoid side-effects such as cursor jumping to the top
            return

        before_bytes = old_value.encode("utf-8")
        after_bytes = value.encode("utf-8")

        with self._ydoc.transaction():
            matcher = SequenceMatcher(a=before_bytes, b=after_bytes)

            if (
                matcher.real_quick_ratio() >= SIMILARITY_THREESHOLD
                and matcher.ratio() >= SIMILARITY_THREESHOLD
            ):
                operations = matcher.get_opcodes()

                # Fix byte ranges and check for problematic overlaps
                fixed_operations = []
                prev_end = 0
                prev_tag = None
                has_overlap = False

                for tag, i1, i2, j1, j2 in operations:
                    # Fix byte ranges to proper UTF-8 character boundaries
                    i1_fixed, i2_fixed = _fix_byte_range_to_char_boundary(before_bytes, i1, i2)
                    j1_fixed, j2_fixed = _fix_byte_range_to_char_boundary(after_bytes, j1, j2)

                    # Check if this operation overlaps with the previous one
                    # which can happen with grapheme clusters (emoji + modifiers, etc.)
                    if i1_fixed < prev_end and prev_tag != "equal":
                        has_overlap = True
                        break

                    prev_end = i2_fixed
                    prev_tag = tag
                    fixed_operations.append((tag, i1_fixed, i2_fixed, j1_fixed, j2_fixed))

                # If we detected overlapping operations, fall back to hard reload
                if has_overlap:
                    self._ysource.clear()
                    if value:
                        self._ysource += value
                else:
                    # Apply granular operations
                    offset = 0
                    for tag, i1, i2, j1, j2 in fixed_operations:
                        match tag:
                            case "replace":
                                self._ysource[i1 + offset : i2 + offset] = after_bytes[
                                    j1:j2
                                ].decode("utf-8")
                                offset += (j2 - j1) - (i2 - i1)
                            case "delete":
                                del self._ysource[i1 + offset : i2 + offset]
                                offset -= i2 - i1
                            case "insert":
                                self._ysource.insert(
                                    i1 + offset, after_bytes[j1:j2].decode("utf-8")
                                )
                                offset += j2 - j1
                            case "equal":
                                pass
                            case _:
                                raise ValueError(f"Unknown tag '{tag}' in sequence matcher")
            else:
                # for very different strings, just replace the whole content;
                # this avoids generating a huge number of operations

                # clear document
                self._ysource.clear()
                # initialize document
                if value:
                    self._ysource += value

    def observe(self, callback: Callable[[str, Any], None]) -> None:
        """
        Subscribes to document changes.

        :param callback: Callback that will be called when the document changes.
        :type callback: Callable[[str, Any], None]
        """
        self.unobserve()
        self._subscriptions[self._ystate] = self._ystate.observe(partial(callback, "state"))
        self._subscriptions[self._ysource] = self._ysource.observe(partial(callback, "source"))


def _is_utf8_continuation_byte(byte: int) -> bool:
    """Check if a byte is a UTF-8 continuation byte (10xxxxxx)."""
    return (byte & 0xC0) == 0x80


def _fix_byte_range_to_char_boundary(data: bytes, start: int, end: int) -> tuple[int, int]:
    """
    Adjust byte indices to proper UTF-8 character boundaries.

    :param data: The byte data.
    :param start: The start byte index.
    :param end: The end byte index.
    :return: A tuple of (adjusted_start, adjusted_end).
    """
    # Move start backward to the beginning of a UTF-8 character
    while start > 0 and start < len(data) and _is_utf8_continuation_byte(data[start]):
        start -= 1

    # Move end forward to the end of a UTF-8 character
    while end < len(data) and _is_utf8_continuation_byte(data[end]):
        end += 1

    return start, end
