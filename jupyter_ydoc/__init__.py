# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from importlib.metadata import entry_points

from ._version import __version__ as __version__
from .yblob import YBlob as YBlob
from .yfile import YFile as YFile
from .ynotebook import YNotebook as YNotebook
from .yunicode import YUnicode as YUnicode

ydocs = {ep.name: ep.load() for ep in entry_points(group="jupyter_ydoc")}
