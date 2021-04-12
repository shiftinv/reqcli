from typing import Any, Dict, Optional


def is_dict_subset_deep(a: Optional[Dict[Any, Any]], b: Optional[Dict[Any, Any]]) -> bool:
    if a is None:
        return True
    elif b is None:
        return False

    try:
        for k, v in a.items():
            other_v = b[k]
            if type(v) == dict:
                if not other_v or type(other_v) != dict:
                    return False
                if not is_dict_subset_deep(v, other_v):
                    return False
            else:
                if v is not None and v != other_v:
                    return False
    except KeyError:
        return False
    return True
