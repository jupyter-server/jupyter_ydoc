# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

from functools import partial
from typing import Any, Callable

from pycrdt import Awareness, Doc, Text

from .ybasedoc import YBaseDoc, YDoc


class YUnicodeDoc(YDoc):
    source: Text


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

    _ydoc: YUnicodeDoc
    _ysource: Text

    def __init__(self, ydoc: Doc | None = None, awareness: Awareness | None = None):
        """
        Constructs a YUnicode.

        :param ydoc: The :class:`pycrdt.Doc` that will hold the data of the document, if provided.
        :type ydoc: :class:`pycrdt.Doc`, optional.
        :param awareness: The :class:`pycrdt.Awareness` that shares non persistent data
                          between clients.
        :type awareness: :class:`pycrdt.Awareness`, optional.
        """
        super().__init__(YUnicodeDoc(ydoc), awareness)
        self._ydoc.source = self._ysource = Text()
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
        with self._ydoc._.transaction():
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
        self._subscriptions[self._ystate] = self._ystate._.observe(partial(callback, "state"))
        self._subscriptions[self._ysource] = self._ysource.observe(partial(callback, "source"))
