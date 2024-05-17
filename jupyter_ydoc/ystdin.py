# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from uuid import uuid4

from pycrdt import Map, Text


def add_stdin(cell: Map, prompt: str = "", password: bool = False) -> str:
    """
    Adds an stdin Map in the cell outputs, and returns its ID.

    Schema:

    .. code-block:: json

        {
            "output_type": "stdin",
            "id": str,
            "submitted": bool,
            "password": bool
            "prompt": str,
            "input": Text
        }
    """
    idx = uuid4().hex
    stdin = Map(
        {
            "output_type": "stdin",
            "id": idx,
            "submitted": False,
            "password": password,
            "prompt": prompt,
            "input": Text(),
        }
    )
    outputs = cell.get("outputs")
    outputs.append(stdin)
    return idx
