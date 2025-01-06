# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import sys

from ._version import __version__ as __version__
from .yblob import YBlob as YBlob
from .yblob import YBlobDoc as YBlobDoc
from .yfile import YFile as YFile
from .yfile import YFileDoc as YFileDoc
from .ynotebook import YNotebook as YNotebook
from .ynotebook import YNotebookDoc as YNotebookDoc
from .yunicode import YUnicode as YUnicode
from .yunicode import YUnicodeDoc as YUnicodeDoc

# See compatibility note on `group` keyword in
# https://docs.python.org/3/library/importlib.metadata.html#entry-points
if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points

ydocs = {ep.name: ep.load() for ep in entry_points(group="jupyter_ydoc")}
