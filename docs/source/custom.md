# Custom documents

Writing an application for a new kind of collaborative document requires the definition of a custom YDoc.

This section will focus on extending documents to use in JupyterLab. In JupyterLab, the front-end conforms to the `ISharedDocument` interface and expects a `YDocument`, both present in the [`@jupyter/ydoc`](./overview.md#jupyter-ydoc) package. In contrast, the back-end conforms to the `YBaseDoc` class in [`jupyter_ydoc`](./overview.md#jupyterydoc).

On a few occasions, we can extend the front-end model and reuse the back-end counterpart without extending it. Extending only the front-end will prevent JupyterLab from saving the new attributes to disk since those new attributes will not be exported by the back-end model when requesting the document's content. This could be the case, for example, when creating a commenting extension where we want to sync the comments through different clients, but we do not want to save them to disk, or at least not within the document.

Once we implement our new models, it is time to export them to be consumed by JupyterLab. In JupyterLab, we register new file types or new document models for existing file types from the front-end. For this reason, the wording that we will use from now on is highly tight to JupyterLab development, and we highly recommend reading JupyterLab's documentation or at least [the section about documents](https://jupyterlab.readthedocs.io/en/stable/extension/documents.html) before continuing reading.

The front-end's models are more complicated because JupyterLab wraps the shared models (that is how we name Jupyter YDoc in the JupyterLab source code) inside the old document's models from JupyterLab. In addition, JupyterLab's document models expose the shared models as a single property, and registering new documents involves more knowledge of the document system. For this reason, we recommend following JupyterLab's documentation, [the section about documents](https://jupyterlab.readthedocs.io/en/stable/extension/documents.html) to register new documents on the front-end side.

On the other side, to export a back-end model, we have to use the entry points provided by Python. We can export our new models by adding them to the configuration file of our Python project using the entry point `jupyter_ydoc`. For example, using a `pyproject.toml` configuration file, we will export our custom model for a `my_document` type as follows:

```toml
[project.entry-points.jupyter_ydoc]
my_document = "my_module.my_file:YCustomDocument"
```

You can find an example of a custom document in the [JupyterCAD extension](https://github.com/QuantStack/jupytercad). With an implementation of a new document model [here](https://github.com/jupytercad/jupytercad/blob/21e54e98fbfbc5dd0303901f30cec1619fd5a109/python/jupytercad-core/jupytercad_core/jcad_ydoc.py) and registering it [here](https://github.com/jupytercad/jupytercad/blob/21e54e98fbfbc5dd0303901f30cec1619fd5a109/python/jupytercad-core/pyproject.toml#L34).
