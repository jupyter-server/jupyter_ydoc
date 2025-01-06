# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from .yunicode import YUnicode, YUnicodeDoc

# For backwards-compatibility:


class YFile(YUnicode):
    pass


class YFileDoc(YUnicodeDoc):
    pass
