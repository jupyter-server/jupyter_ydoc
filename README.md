[![Build Status](https://github.com/jupyter-server/jupyter_ydoc/workflows/Tests/badge.svg)](https://github.com/jupyter-server/jupyter_ydoc/actions)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyPI](https://img.shields.io/pypi/v/jupyter-ydoc)](https://pypi.org/project/jupyter-ydoc/)
[![npm (scoped)](https://img.shields.io/npm/v/@jupyter/ydoc)](https://www.npmjs.com/package/@jupyter/ydoc)

# jupyter_ydoc

`jupyter_ydoc` provides [pycrdt](https://github.com/jupyter-server/pycrdt)-based data structures for various
documents used in the Jupyter ecosystem. Built-in documents include:
- `YBlob`: a generic immutable binary document.
- `YUnicode`: a generic UTF8-encoded text document (`YFile` is an alias to `YUnicode`).
- `YNotebook`: a Jupyter notebook document.

These documents are registered via an entry point under the `"jupyter_ydoc"` group as `"blob"`,
`"unicode"` (or `"file"`), and `"notebook"`, respectively. You can access them as follows:

```py
from jupyter_ydoc import ydocs

print(ydocs)
# {
#     'blob': <class 'jupyter_ydoc.yblob.YBlob'>,
#     'file': <class 'jupyter_ydoc.yfile.YFile'>,
#     'notebook': <class 'jupyter_ydoc.ynotebook.YNotebook'>,
#     'unicode': <class 'jupyter_ydoc.yunicode.YUnicode'>
# }
```

Which is just a shortcut to:

```py
from importlib.metadata import entry_points
# for Python < 3.10, install importlib_metadata and do:
# from importlib_metadata import entry_points

ydocs = {ep.name: ep.load() for ep in entry_points(group="jupyter_ydoc")}
```

Or directly import them:
```py
from jupyter_ydoc import YBlob, YUnicode, YNotebook
```

The `"jupyter_ydoc"` entry point group can be populated with your own documents, e.g. by adding the
following to your package's `pyproject.toml`:

```
[project.entry-points.jupyter_ydoc]
my_document = "my_package.my_file:MyDocumentClass"
```
