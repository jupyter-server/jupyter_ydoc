[![Build Status](https://github.com/davidbrochart/jupyter_ydoc/workflows/Tests/badge.svg)](https://github.com/davidbrochart/jupyter_ydoc/actions)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

# jupyter_ydoc

`jupyter_ydoc` provides [Ypy](https://github.com/y-crdt/ypy)-based data structures for various
documents used in the Jupyter ecosystem. Built-in documents include:
- `YFile`: a generic text document.
- `YNotebook`: a Jupyter notebook document.

These documents are registered via an entry point under the `"jupyter_ydoc"` group as `"file"` and
`"notebook"`, respectively. You can access them as follows:

```py
from jupyter_ydoc import ydocs

print(ydocs)
# {'file': <class 'jupyter_ydoc.ydoc.YFile'>, 'notebook': <class 'jupyter_ydoc.ydoc.YNotebook'>}
```

Which is just a shortcut to:

```py
import sys
import jupyter_ydoc

# See compatibility note on `group` keyword in https://docs.python.org/3/library/importlib.metadata.html#entry-points
if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points

ydocs = {ep.name: ep.load() for ep in entry_points(group="jupyter_ydoc")}
```

Or directly import them:
```py
from jupyter_ydoc import YFile, YNotebook
```

The `jupyter_ydoc` entry point group can be populated with your own document, e.g. by adding the
following to your package's `setup.cfg`:

```
[options.entry_points]
jupyter_ydoc =
    my_document = my_package.my_file:MyDocumentClass
```
