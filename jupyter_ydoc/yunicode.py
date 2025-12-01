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

        with self._ydoc.transaction():
            matcher = SequenceMatcher(a=old_value, b=value)

            if (
                matcher.real_quick_ratio() >= SIMILARITY_THREESHOLD
                and matcher.ratio() >= SIMILARITY_THREESHOLD
            ):
                operations = matcher.get_opcodes()
                offset = 0
                for tag, i1, i2, j1, j2 in operations:
                    match tag:
                        case "replace":
                            self._ysource[i1 + offset : i2 + offset] = value[j1:j2]
                            offset += (j2 - j1) - (i2 - i1)
                        case "delete":
                            del self._ysource[i1 + offset : i2 + offset]
                            offset -= i2 - i1
                        case "insert":
                            self._ysource.insert(i1 + offset, value[j1:j2])
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
