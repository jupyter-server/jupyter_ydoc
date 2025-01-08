# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

from functools import partial
from typing import Any, Callable

from pycrdt import Awareness, Doc, TypedMap

from .ybasedoc import YBaseDoc, YDoc


class YBlobSource(TypedMap):
    bytes: bytes


class YBlobDoc(YDoc):
    source: YBlobSource


class YBlob(YBaseDoc):
    """
    Extends :class:`YBaseDoc`, and represents a blob document.
    The Y document is set from bytes.

    Schema:

    .. code-block:: json

        {
            "state": YMap,
            "source": YMap
        }
    """

    _ydoc: YBlobDoc
    _ysource: YBlobSource

    def __init__(self, ydoc: Doc | None = None, awareness: Awareness | None = None):
        """
        Constructs a YBlob.

        :param ydoc: The :class:`pycrdt.Doc` that will hold the data of the document, if provided.
        :type ydoc: :class:`pycrdt.Doc`, optional.
        :param awareness: The :class:`pycrdt.Awareness` that shares non persistent data
                          between clients.
        :type awareness: :class:`pycrdt.Awareness`, optional.
        """
        super().__init__(YBlobDoc(ydoc), awareness)
        self._ydoc.source = self._ysource = YBlobSource()
        self.undo_manager.expand_scope(self._ysource._)

    @property
    def version(self) -> str:
        """
        Returns the version of the document.

        :return: Document's version.
        :rtype: str
        """
        return "2.0.0"

    def get(self) -> bytes:
        """
        Returns the content of the document.

        :return: Document's content.
        :rtype: bytes
        """
        try:
            return self._ysource.bytes
        except KeyError:
            return b""

    def set(self, value: bytes) -> None:
        """
        Sets the content of the document.

        :param value: The content of the document.
        :type value: bytes
        """
        self._ysource.bytes = value

    def observe(self, callback: Callable[[str, Any], None]) -> None:
        """
        Subscribes to document changes.

        :param callback: Callback that will be called when the document changes.
        :type callback: Callable[[str, Any], None]
        """
        self.unobserve()
        self._subscriptions[self._ystate] = self._ystate._.observe(partial(callback, "state"))
        self._subscriptions[self._ysource] = self._ysource._.observe(partial(callback, "source"))
