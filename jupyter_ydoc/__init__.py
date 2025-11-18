# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from ._version import __version__ as __version__
from .yblob import YBlob as YBlob
from .yfile import YFile as YFile
from .ynotebook import YNotebook as YNotebook
from .yunicode import YUnicode as YUnicode

from importlib.metadata import entry_points

ydocs = {ep.name: ep.load() for ep in entry_points(group="jupyter_ydoc")}
