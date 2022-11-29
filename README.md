[![Build Status](https://github.com/jupyter-server/jupyter_ydoc/workflows/Tests/badge.svg)](https://github.com/jupyter-server/jupyter_ydoc/actions)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyPI](https://img.shields.io/pypi/v/jupyter-ydoc)](https://pypi.org/project/jupyter-ydoc/)
[![npm (scoped)](https://img.shields.io/npm/v/@jupyter/ydoc)](https://www.npmjs.com/package/@jupyter/ydoc)

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
import pkg_resources

ydocs = {ep.name: ep.load() for ep in pkg_resources.iter_entry_points(group="jupyter_ydoc")}
```

Or directly import them:
```py
from jupyter_ydoc import YFile, YNotebook
```

The `"jupyter_ydoc"` entry point group can be populated with your own documents, e.g. by adding the
following to your package's `setup.cfg`:

```
[options.entry_points]
jupyter_ydoc =
    my_document = my_package.my_file:MyDocumentClass
```
