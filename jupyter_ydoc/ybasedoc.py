# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

from pycrdt import Doc, Map


class YBaseDoc(ABC):
    """
    Base YDoc class.
    This class, defines the minimum API that any document must provide
    to be able to get and set the content of the document as well as
    subscribe to changes in the document.
    """

    def __init__(self, ydoc: Optional[Doc] = None):
        """
        Constructs a YBaseDoc.

        :param ydoc: The :class:`pycrdt.Doc` that will hold the data of the document, if provided.
        :type ydoc: :class:`pycrdt.Doc`, optional.
        """
        if ydoc is None:
            self._ydoc = Doc()
        else:
            self._ydoc = ydoc
        self._ydoc["state"] = self._ystate = Map()
        self._subscriptions: Dict[Any, str] = {}

    @property
    @abstractmethod
    def version(self) -> str:
        """
        Returns the version of the document.

        :return: Document's version.
        :rtype: str
        """

    @property
    def ystate(self) -> Map:
        """
        A :class:`pycrdt.Map` containing the state of the document.

        :return: The document's state.
        :rtype: :class:`pycrdt.Map`
        """
        return self._ystate

    @property
    def ydoc(self) -> Doc:
        """
        The underlying :class:`pycrdt.Doc` that contains the data.

        :return: The document's ydoc.
        :rtype: :class:`pycrdt.Doc`
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
    def dirty(self) -> Optional[bool]:
        """
        Returns whether the document is dirty.

        :return: Whether the document is dirty.
        :rtype: Optional[bool]
        """
        return self._ystate.get("dirty")

    @dirty.setter
    def dirty(self, value: bool) -> None:
        """
        Sets the document as clean (all changes committed) or dirty (uncommitted changes).

        :param value: Whether the document is clean or dirty.
        :type value: bool
        """
        self._ystate["dirty"] = value

    @property
    def path(self) -> Optional[str]:
        """
        Returns document's path.

        :return: Document's path.
        :rtype: Optional[str]
        """
        return self._ystate.get("path")

    @path.setter
    def path(self, value: str) -> None:
        """
        Sets document's path.

        :param value: Document's path.
        :type value: str
        """
        self._ystate["path"] = value

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
