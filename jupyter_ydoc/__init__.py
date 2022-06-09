import pkg_resources

from .ydoc import YFile, YNotebook  # noqa

ydocs = {ep.name: ep.load() for ep in pkg_resources.iter_entry_points(group="jupyter_ydoc")}

__version__ = "0.1.11"
