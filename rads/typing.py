"""Type aliases."""

import os
from typing import IO, TYPE_CHECKING, Any, Union

import numpy as np  # type: ignore

__all__ = ["PathLike", "PathLikeOrFile", "PathOrFile", "IntOrArray", "FloatOrArray"]

if TYPE_CHECKING:
    PathLike = Union[str, os.PathLike[str]]
    PathOrFile = Union[os.PathLike[str], IO[Any]]
else:
    PathLike = Union[str, os.PathLike]
    PathOrFile = Union[os.PathLike, IO[Any]]

PathLikeOrFile = Union[PathLike, IO[Any]]

IntOrArray = Union[int, np.generic, np.ndarray]
FloatOrArray = Union[float, np.generic, np.ndarray]
