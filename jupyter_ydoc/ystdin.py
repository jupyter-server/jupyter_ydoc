# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from pycrdt import Map, Text


def add_stdin(cell: Map, prompt: str = "", password: bool = False) -> None:
    """
    Adds an stdin Map in the cell outputs.

    Schema:

    .. code-block:: json

        {
            "state": Map[
                "pending": bool,
                "password": bool
            ],
            "prompt": str,
            "input": Text
        }
    """
    stdin = Map(
        {
            "output_type": "stdin",
            "state": {
                "pending": True,
                "password": password,
            },
            "prompt": prompt,
            "input": Text(),
        }
    )
    outputs = cell.get("outputs")
    outputs.append(stdin)
