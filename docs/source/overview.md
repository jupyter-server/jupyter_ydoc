# Overview

The Jupyter YDoc repository includes various models that JupyterLab uses for collaborative editing. These models use a specific implementation of a CRDT, the Y-CRDTs. To be more precise, the JavaScript package uses [Yjs](https://github.com/yjs/yjs), while the Python package uses [YPy](https://github.com/y-crdt/ypy).

Jupyter YDoc was designed to centralize the data structures used for composing a document in a single class, hide the complicated edge cases of CRDTs, and prevent users from inserting invalid data or adding new attributes to the document that are not part of the schema.

This repository holds a javascript package and its python counterpart. In the JupyterLab context, the javascript package, or from now on, `@jupyter/ydoc`, contains the frontend models used to keep the documents in the client's memory. In contrast, the python package contains the models used in the backend to load documents from disk and serve them to each client.


## `@jupyter/ydoc`
Build using [Yjs](https://github.com/yjs/yjs). `@jupyter/ydoc` is a JavaScipt package that includes the models used in the JupyterLab front-end for real-time collaboration. This package contains two main classes, `YFile` used for plain text documents and `YNotebook` used for the Notebook format.

<!--
	Extend the documentation

- IShared interfaces
-
-->



## `jupyter-ydoc`
Build using [YPy](https://github.com/y-crdt/ypy). `jupyter-ydoc` is a Python package that includes the models used in the JupyterLab back-end for loading the documents from disk in real-time collaboration.

<!-- Extend the documentation -->
