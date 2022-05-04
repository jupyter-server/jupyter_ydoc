from typing import Dict, List, Union


def cast_all(o: Union[List, Dict], from_type, to_type) -> Union[List, Dict]:
    if isinstance(o, list):
        for i, v in enumerate(o):
            if isinstance(v, from_type):
                o[i] = to_type(v)
            elif isinstance(v, (list, dict)):
                cast_all(v, from_type, to_type)
    elif isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, from_type):
                o[k] = to_type(v)
            elif isinstance(v, (list, dict)):
                cast_all(v, from_type, to_type)
    return o
