# Overview

The `jupyter_ydoc` repository includes various models that JupyterLab uses for collaborative editing. These models use a specific implementation of a CRDT, the Y-CRDTs. To be more precise, the JavaScript package uses [yjs](https://github.com/yjs/yjs), while the Python package uses [pycrdt](https://github.com/jupyter-server/pycrdt).

Jupyter YDoc was designed to centralize the data structures used for composing a document in a single class, hide the complicated edge cases of CRDTs, and prevent users from inserting invalid data or adding new attributes to the document that are not part of the schema.

This repository holds a JavaScript package and its Python counterpart. In the JupyterLab context, the JavaScript package, or from now on, `@jupyter/ydoc`, contains the front-end models used to keep the documents in the client's memory. In contrast, the Python package contains the models used in the back-end to serve documents to each client.


## `@jupyter/ydoc`
Built on top of [yjs](https://github.com/yjs/yjs), `@jupyter/ydoc` is a JavaScript package that includes the models used in the JupyterLab front-end for real-time collaboration. This package contains two main classes, `YFile` used for plain text documents and `YNotebook` used for the Notebook format. In the JupyterLab context, we call the models exported by this package, shared models. In addition, this package contains the `IShared` interfaces used to abstract out the implementation of the shared models in JupyterLab to make it easier to replace the CRDT implementation (Yjs) for something else if needed.

**Source Code:** [GitHub](https://github.com/jupyter-server/jupyter_ydoc/tree/main/javascript)

**Package:** [NPM](https://www.npmjs.com/package/@jupyter/ydoc)

**API documentation:**: [JavaScript API](javascript_api.rst)



## `jupyter-ydoc`
Built on top of [pycrdt](https://github.com/jupyter-server/pycrdt), `jupyter-ydoc` is a Python package that includes the models used in the JupyterLab back-end for representing collaborative documents.

**Source Code:** [GitHub](https://github.com/jupyter-server/jupyter_ydoc/tree/main/jupyter_ydoc)

**Package:** [PyPI](https://pypi.org/project/jupyter-ydoc)

**API documentation:**: [Python API](python_api.rst)
