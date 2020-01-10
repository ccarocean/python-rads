"""Utility functions."""

import datetime
import io
import os
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    List,
    Optional,
    TypeVar,
    Union,
    cast,
    overload,
)

import numpy as np  # type: ignore
from wrapt import ObjectProxy  # type: ignore

from .constants import EPOCH
from .typing import PathLike, PathLikeOrFile

__all__ = [
    "ensure_open",
    "filestring",
    "isio",
    "xor",
    "contains_sublist",
    "merge_sublist",
    "delete_sublist",
    "fortran_float",
    "datetime_to_timestamp",
    "timestamp_to_datetime",
    "get",
    "getsorted",
    "outliers",
]


class _NoCloseIOWrapper(ObjectProxy):  # type: ignore
    def __exit__(self, *args: object, **kwargs: object) -> None:
        pass

    def close(self) -> None:
        pass


def ensure_open(
    file: PathLikeOrFile,
    mode: str = "r",
    buffering: int = -1,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
    closefd: bool = True,
    closeio: bool = False,
) -> IO[Any]:
    """Open file or leave file-like object open.

    This function behaves identically to :func:`open` but can also accept a
    file-like object in the `file` parameter.

    :param file:
        A path-like object giving the pathname (absolute or relative to the
        current working directory) of the file to be opened or an integer file
        descriptor of the file to be wrapped or a file-like object.

        .. note::

            If a file descriptor is given, it is closed when the
            returned I/O object is closed, unless `closefd` is set to False.

        .. note::

            If a file-like object is given closing the returned I/O object will
            not close the given file unless `closeio` is set to True.
    :param mode:
        See :func:`open`
    :param buffering:
        See :func:`open`
    :param encoding:
        See :func:`open`
    :param errors:
        See :func:`open`
    :param newline:
        See :func:`open`
    :param closefd:
        See :func:`open`
    :param closeio:
        If set to True then if `file` is a file like object it will be closed
        when either the __exit__ or close methods are called on the returned
        I/O object.  By default these methods will be ignored when `file` is
        a file-like object.

    :return:
        An I/O object or the original file-like object if `file` is a file-like
        object.  If this is the original file-like object and `closeio` is set
        to False (the default) then it's close and __exit__ methods will be
        no-ops.

    .. seealso:: :func:`open`
    """
    if hasattr(file, "read"):
        if not closeio:
            return cast(IO[Any], _NoCloseIOWrapper(file))
        return cast(IO[Any], file)
    return open(
        cast(Union[PathLike, int], file),
        mode,
        buffering,
        encoding,
        errors,
        newline,
        closefd,
    )


def filestring(file: PathLikeOrFile) -> Optional[str]:
    """Convert a PathLikeOrFile to a string.

    :param file:
        file or file-like object to get the string for.

    :return:
        The string representation of the filename or path.  If it cannot get
        the name/path of the given file or file-like object or cannot convert
        it to a str, None will be returned.
    """
    if isinstance(file, int):
        return None
    if hasattr(file, "read"):
        try:
            return cast(IO[Any], file).name
        except AttributeError:
            return None
    if not isinstance(file, (str, bytes)):
        file = os.fspath(cast(PathLike, file))
    if isinstance(file, str):
        return file
    if isinstance(file, bytes):
        try:
            return cast(bytes, file).decode("utf-8")
        except UnicodeDecodeError:
            return None
    raise TypeError(f"'{type(file)}' is not a file like object")


def isio(obj: Any, *, read: bool = False, write: bool = False) -> bool:
    """Determine if object is IO like and is read and/or write.

    .. note::

        Falls back to :code:`isinstnace(obj, io.IOBase)` if neither `read` nor
        `write` is True.

    :param obj:
        Object to check if it is an IO like object.
    :param read:
        Require `obj` to be readable if True.
    :param write:
        Require `obj` to be writable if True.

    :return:
        True if the given `obj` is readable and/or writeable as defined by the
        `read` and `write` arguments.
    """
    if read or write:
        return (not read or hasattr(obj, "read")) and (
            not write or hasattr(obj, "write")
        )
    return isinstance(obj, io.IOBase)


def xor(a: bool, b: bool) -> bool:
    """Boolean XOR operator.

    This implements the XOR boolean operator and has the following truth table:

    ===== ===== =======
    a       b   a XOR b
    ===== ===== =======
    True  True  False
    True  False True
    False True  True
    False False False
    ===== ===== =======

    :param a:
        First boolean value.
    :param b:
        Second boolean value.

    :return:
        The result of `a` XOR `b` from the truth table above.
    """
    return (a and not b) or (not a and b)


def contains_sublist(list_: List[Any], sublist: List[Any]) -> bool:
    """Determine if a `list` contains a `sublist`.

    :param list_:
        list to search for the `sublist` in.
    :param sublist:
        Sub list to search for.

    :return:
        True if `list` contains `sublist`.

    """
    # Adapted from: https://stackoverflow.com/a/12576755
    if not sublist:
        return False
    for i in range(len(list_)):
        if list_[i] == sublist[0] and list_[i : i + len(sublist)] == sublist:
            return True
    return False


def merge_sublist(list_: List[Any], sublist: List[Any]) -> List[Any]:
    """Merge a `sublist` into a given `list_`.

    :param list_:
        List to merge `sublist` into.
    :param sublist:
        Sublist to merge into `list_`

    :return:
        A copy of `list_` with `sublist` at the end if `sublist` is not a
        sublist of `list_`.  Otherwise, a copy of `list_` is returned
        unchanged.
    """
    if contains_sublist(list_, sublist):
        return list_[:]
    return list_ + sublist


def delete_sublist(list_: List[Any], sublist: List[Any]) -> List[Any]:
    """Remove a `sublist` from the given `list_`.

    :param list_:
        List to remove the `sublist` from.
    :param sublist:
        Sublist to remove from `list_`.

    :return:
        A copy of `list_` with the `sublist` removed.
    """
    if not sublist:
        return list_[:]
    for i in range(len(list_)):
        if list_[i] == sublist[0] and list_[i : i + len(sublist)] == sublist:
            return list_[:i] + list_[i + len(sublist) :]
    return list_[:]


def fortran_float(string: str) -> float:
    """Construct :class:`float` from Fortran style float strings.

    This function can convert strings to floats in all of the formats below:

        * ``3.14e10``  (also parsable with :class:`float`)
        * ``3.14E10``  (also parsable with :class:`float`)
        * ``3.14d10``
        * ``3.14D10``
        * ``3.14e+10``  (also parsable with :class:`float`)
        * ``3.14E+10``  (also parsable with :class:`float`)
        * ``3.14d+10``
        * ``3.14D+10``
        * ``3.14e-10``  (also parsable with :class:`float`)
        * ``3.14E-10``  (also parsable with :class:`float`)
        * ``3.14d-10``
        * ``3.14D-10``
        * ``3.14+100``
        * ``3.14-100``

    .. note::

        Because RADS was written in Fortran, exponent characters in
        configuration and passindex files sometimes use 'D' or 'd' as
        the exponent separator instead of 'E' or 'e'.

    .. warning::

        If you are Fortran developer stop using 'Ew.d' and 'Ew.dDe' formats
        and use 'Ew.dEe' instead.  The first two are not commonly supported
        by other languages while the last version is the standard for nearly
        all languages.  Ok, rant over.

    :param string:
        String to attempt to convert to a float.

    :return:
        The float parsed from the given `string`.

    :raises ValueError:
        If `string` does not represent a valid float.
    """
    try:
        return float(string)
    except ValueError as err:
        try:
            return float(string.replace("d", "e").replace("D", "E"))
        except ValueError:
            try:
                return float(string.replace("+", "e+").replace("-", "e-"))
            except ValueError:
                raise err


def datetime_to_timestamp(
    time: datetime.datetime, *, epoch: datetime.datetime = EPOCH
) -> float:
    """Convert datetime object to timestamp relative to an epoch.

    :param time:
        Date and time.
    :param epoch:
        Date and time of epoch.  Defaults to the RADS epoch.

    :return:
        The number of seconds between the `epoch` and the given `time`.
    """
    return (time - epoch).total_seconds()


def timestamp_to_datetime(
    seconds: float, *, epoch: datetime.datetime = EPOCH
) -> datetime.datetime:
    """Convert timestamp relative to an epoch to a datetime.

    :param seconds:
        Seconds since the given `epoch`.
    :param epoch:
        Date and time of epoch.  Defaults to the RADS epoch.

    :return:
        Date and time corresponding to the given `seconds` since the `epoch`.
    """
    return epoch + datetime.timedelta(seconds=seconds)


# type variables used with get below
_K = TypeVar("_K", contravariant=True)
_V = TypeVar("_V", covariant=True)
_D = TypeVar("_D")

if TYPE_CHECKING:
    from typing_extensions import Protocol

    class SupportsGetItem(Protocol[_K, _V]):
        def __getitem__(self, item: _K) -> _V:
            pass


@overload
def get(
    obj: "SupportsGetItem[_K, _V]", item: _K, default: _D
) -> Union[_V, _D]:  # noqa: D103
    pass


@overload
def get(obj: "SupportsGetItem[_K, _V]", item: _K) -> Union[_V, None]:  # noqa: D103
    pass


def get(
    obj: "SupportsGetItem[_K, _V]", item: _K, default: Optional[_D] = None
) -> Union[_V, Optional[_D]]:
    """Return value of `item` if found, otherwise returns the `default`.

    Extends dict.get to any type supporting :func:`__getitem__`.

    :param obj:
        An object supporting :func:`__getitem__`.  It should raise
        :class:`IndexError` or :class:`KeyError` if the index/key is outside
        of the valid range or does not exist.
    :param item:
        Index or key to get from the container.
    :param default:
        The default value when the `item` does not exist.  Defaults to `None`.

    :return:
        The value associated with the given index/key.
    """
    try:
        return obj[item]
    except (IndexError, KeyError):
        return default


def getsorted(
    array: np.ndarray,
    value: Any,
    *,
    sorter: Optional[np.ndarray] = None,
    valid_only: bool = False,
) -> Union[np.ndarray, int]:
    """Get index of value in array.

    This is similar to :func:`numpy.searchsorted` but is focused on looking up
    a value in a sorted array instead of inserting into it.

    :param array:
        Sorted 1D array to find value in.
    :param value:
        Value or array of values to search for.
    :param sorter:
        Optional array of integer indices that sort the array into ascending
        order.  It is typically the result of :func:`numpy.argsort`.
    :param valid_only:
        Set to True to only return valid indices, the returned array may no
        longer be the same shape as `value`.  Ignored when value is a scalar.

    :return:
        Index or indices of the `value` or values in the given `array`.
        `N`, where N is the length of `array`, is returned if value cannot be
        found.
    """
    # search with bisection for a theoretical insertion location
    indices = np.searchsorted(array, value, sorter=sorter)

    if sorter is None:
        # scalar - invalidate if the given value is not found
        if np.isscalar(value):
            if indices < len(array) and array[indices] == value:
                return indices
            return len(array)

        # array - invalidate locations where the given value is not found
        valid = indices < len(array)
        value = np.asarray(value)
        valid[valid] = array[indices[valid]] == value[valid]
        indices[~valid] = len(array)
        if valid_only:
            return indices[valid]
        return indices

    # scalar - invalidate if the given value is not found
    if np.isscalar(value):
        if indices < len(array) and array[sorter[indices]] == value:
            return sorter[indices]
        return len(array)

    # array - invalidate locations where the given value is not found
    valid = indices < len(array)
    value = np.asarray(value)
    valid[valid] = array[sorter[indices[valid]]] == value[valid]
    indices[~valid] = len(array)
    if valid_only:
        return sorter[indices[valid]]
    result = len(array) * np.ones(indices.size)
    result[valid] = sorter[indices[valid]]
    return result


def outliers(data: np.ndarray, zscore_limit: float = 3.5) -> np.ndarray:
    """Detect outliers.

    Based the modified Z-value method at:
        https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm

    Upstream reference:
         Boris Iglewicz and David Hoaglin (1993), "Volume 16: How to Detect and
         Handle Outliers", The ASQC Basic References in Quality Control:
         Statistical Techniques, Edward F. Mykytka, Ph.D., Editor.

    :param data:
        Data to detect outliers in.
    :param zscore_limit:
        Z-score limit, defaults to 3.5 which is recommended by Iglewicz and Hoaglin.

    :return:
        Boolean array giving location of outliers in `data`.
    """
    median = np.median(data)
    median_absolute_deviation = np.median(np.abs(data - median))
    if median_absolute_deviation == 0:
        return np.zeros(data.shape, dtype=bool)
    return np.abs(0.6745 * (data - median) / median_absolute_deviation) > zscore_limit
