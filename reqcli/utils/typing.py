from typing import Mapping, Union, TypeVar, Callable, Any


TFuncAny = TypeVar('TFuncAny', bound=Callable[..., Any])


# `Mapping` since `Dict` is invariant in its value type
RequestDict = Mapping[str, Union[int, str, bytes]]
