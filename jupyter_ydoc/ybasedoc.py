# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable

from pycrdt import Awareness, Doc, Subscription, TypedDoc, TypedMap, UndoManager


class YState(TypedMap):
    dirty: bool
    hash: str
    path: str


class YDoc(TypedDoc):
    state: YState


class YBaseDoc(ABC):
    """
    Base YDoc class.
    This class, defines the minimum API that any document must provide
    to be able to get and set the content of the document as well as
    subscribe to changes in the document.
    """

    _ydoc: YDoc
    _ystate: YState
    _subscriptions: dict[Any, Subscription]
    _undo_manager: UndoManager

    def __init__(self, ydoc: YDoc | Doc | None = None, awareness: Awareness | None = None):
        """
        Constructs a YBaseDoc.

        :param ydoc: The :class:`pycrdt.Doc` that will hold the data of the document, if provided.
        :type ydoc: :class:`pycrdt.Doc`, optional.
        :param awareness: The :class:`pycrdt.Awareness` that shares non persistent data
                          between clients.
        :type awareness: :class:`pycrdt.Awareness`, optional.
        """
        if isinstance(ydoc, YDoc):
            self._ydoc = ydoc
        else:
            self._ydoc = YDoc(ydoc)
        self.awareness = awareness

        self._ydoc.state = self._ystate = YState()
        self._subscriptions = {}
        self._undo_manager = UndoManager(doc=self._ydoc._, capture_timeout_millis=0)

    @property
    @abstractmethod
    def version(self) -> str:
        """
        Returns the version of the document.

        :return: Document's version.
        :rtype: str
        """

    @property
    def undo_manager(self) -> UndoManager:
        """
        A :class:`pycrdt.UndoManager` for the document.

        :return: The document's undo manager.
        :rtype: :class:`pycrdt.UndoManager`
        """
        return self._undo_manager

    def ystate(self) -> YState:
        """
        A :class:`YState` containing the state of the document.

        :return: The document's state.
        :rtype: :class:`YState`
        """
        return self._ystate

    @property
    def ydoc(self) -> YDoc:
        """
        The :class:`YDoc` that contains the data.

        :return: The document's ydoc.
        :rtype: :class:`YDoc`
        """
        return self._ydoc

    @property
    def source(self) -> Any:
        """
        Returns the content of the document.

        :return: The content of the document.
        :rtype: Any
        """
        return self.get()

    @source.setter
    def source(self, value: Any):
        """
        Sets the content of the document.

        :param value: The content of the document.
        :type value: Any
        """
        return self.set(value)

    @property
    def dirty(self) -> bool | None:
        """
        Returns whether the document is dirty.

        :return: Whether the document is dirty.
        :rtype: bool | None
        """
        try:
            return self._ystate.dirty
        except KeyError:
            return None

    @dirty.setter
    def dirty(self, value: bool) -> None:
        """
        Sets the document as clean (all changes committed) or dirty (uncommitted changes).

        :param value: Whether the document is clean or dirty.
        :type value: bool
        """
        self._ystate.dirty = value

    @property
    def hash(self) -> str | None:
        """
        Returns the document hash as computed by contents manager.

        :return: The document hash.
        :rtype: str | None
        """
        try:
            return self._ystate.hash
        except KeyError:
            return None

    @hash.setter
    def hash(self, value: str) -> None:
        """
        Sets the document hash.

        :param value: The document hash.
        :type value: str
        """
        self._ystate.hash = value

    @property
    def path(self) -> str | None:
        """
        Returns document's path.

        :return: Document's path.
        :rtype: str | None
        """
        try:
            return self._ystate.path
        except KeyError:
            return None

    @path.setter
    def path(self, value: str) -> None:
        """
        Sets document's path.

        :param value: Document's path.
        :type value: str
        """
        self._ystate.path = value

    @abstractmethod
    def get(self) -> Any:
        """
        Returns the content of the document.

        :return: Document's content.
        :rtype: Any
        """

    @abstractmethod
    def set(self, value: Any) -> None:
        """
        Sets the content of the document.

        :param value: The content of the document.
        :type value: Any
        """

    @abstractmethod
    def observe(self, callback: Callable[[str, Any], None]) -> None:
        """
        Subscribes to document changes.

        :param callback: Callback that will be called when the document changes.
        :type callback: Callable[[str, Any], None]
        """

    def unobserve(self) -> None:
        """
        Unsubscribes to document changes.

        This method removes all the callbacks.
        """
        for k, v in self._subscriptions.items():
            k.unobserve(v)
        self._subscriptions = {}
