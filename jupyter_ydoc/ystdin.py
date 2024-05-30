# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from pycrdt import Array, Map, Text


def add_stdin_output(outputs: Array, prompt: str = "", password: bool = False) -> int:
    """
    Adds an stdin output Map in the cell outputs, and returns its index.

    Schema:

    .. code-block:: json

        {
            "output_type": "stdin",
            "submitted": bool,
            "password": bool
            "prompt": str,
            "value": Text
        }
    """
    stdin_output = Map(
        {
            "output_type": "stdin",
            "submitted": False,
            "password": password,
            "prompt": prompt,
            "value": Text(),
        }
    )
    stdin_idx = len(outputs)
    outputs.append(stdin_output)
    return stdin_idx
