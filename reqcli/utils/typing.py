from typing import Mapping, Union


# `Mapping` since `Dict` is invariant in its value type
RequestDict = Mapping[str, Union[int, str, bytes]]
