"""Parsers for text within a tag.

The parsers in this file should all take a string and a mapping of attributes
for the tag and return a value or take one or more parser functions and return
a new parsing function.

If a parser deals with generic XML then it should be rads.config.xml_parsers
and if it returns a rads.config.xml_parsers.Parser but is not generic then it
belongs in rads.config.grammar.
"""

from datetime import datetime
from numbers import Real
from typing import (Any, Callable, Dict, Iterable, List, Mapping, Optional,
                    Sequence, TypeVar)

import numpy as np  # type: ignore

from .tree import Compress, Cycles, Range, ReferencePass, Repeat, Unit
from .._utility import fortran_float

__all__ = ['lift', 'list_of', 'one_of', 'range_of', 'compress', 'cycles',
           'nop', 'ref_pass', 'repeat', 'time', 'unit']

T = TypeVar('T')


# COMBINATORS
#
# This section contains parser combinators that can be used to glue multiple
# text parsers together and return a new text parser.


def lift(string_parser: Callable[[str], T]) \
        -> Callable[[str, Mapping[str, str]], T]:
    """Lift a simple string parser to a text parser that accepts attributes.

    This is very similar to lifting a plain function into a monad.

    Parameters
    ----------
    string_parser
        A simple parser that takes a string and returns a value.

    Returns
    -------
    function
        The given :paramref:`string_parser` with an added argument to accept
        and ignore the attributes for the text tag.

    """
    def _parser(string: str, _: Mapping[str, str]) -> T:
        return string_parser(string)

    _parser._lifted = string_parser.__qualname__  # type: ignore
    return _parser


def list_of(parser: Callable[[str, Mapping[str, str]], T],
            sep: Optional[str] = None) \
        -> Callable[[str, Mapping[str, str]], List[T]]:
    """Convert parser into a parser of lists.

    Parameters
    ----------
    parser
        Original parser.
    sep
        Item delimiter.  Default is to separate by one or more spaces.

    Returns
    -------
    function
        The new parser of delimited lists.

    """
    def _parser(string: str, attr: Mapping[str, str]) -> List[T]:
        return [parser(s, attr) for s in string.split(sep=sep)]

    return _parser


def range_of(parser: Callable[[str, Mapping[str, str]], Real]) \
        -> Callable[[str, Mapping[str, str]], Range]:
    """Create a range parser from a given parser for each range element.

    The resulting parser will parse space separated lists of length 2 and use
    the given :paramref:`parser` for both elements.

    Parameters
    ----------
    parser
        Parser to use for the min and max values.

    Returns
    -------
    function
        New range parser.

    Raises
    ------
    ValueError
        Resulting parser raises this if given a string that does not contain
        two space separated elements.

    """
    def _parser(string: str, attr: Mapping[str, str]) -> Range:
        minmax = [parser(s, attr) for s in string.split()]
        if not minmax:
            raise ValueError(
                'ranges require exactly 2 values, but none were given')
        if len(minmax) == 1:
            raise ValueError(
                'ranges require exactly 2 values, but only 1 was given')
        if len(minmax) > 2:
            raise ValueError(
                'ranges require exactly 2 values, '
                f'but {len(minmax)} were given')
        return Range(*minmax)

    return _parser


def one_of(parsers: Iterable[Callable[[str, Mapping[str, str]], Any]]) \
        -> Callable[[str, Mapping[str, str]], Any]:
    """Convert parsers into a parser that tries each one in sequence.

    .. note::

        Each parser will be tried in sequence.  The next parser will be tried
        if TypeError, ValueError, or KeyError is raised.

    Parameters
    ----------
    parsers
        A sequence of parsers the new parsers should try in order.

    Returns
    -------
    function
        The new parser which tries each of the given :paramref:`parsers` in
        order until once succeeds.

    Raises
    ------
    TypeError
        Resulting parser raises this if given a string that cannot be parsed by
        any of the given :paramref:`parsers`.

    """
    def _parser(string: str, attr: Mapping[str, str]) -> Any:
        for parser in parsers:
            try:
                return parser(string, attr)
            except (TypeError, ValueError, KeyError):
                pass

        # build list of parser types
        parser_types = []
        for parser in parsers:
            try:
                parser_types.append(parser._lifted)  # type: ignore
            except AttributeError:
                parser_types.append(parser.__qualname__)

        raise ValueError(f"cannot convert '{string}' to any of the following "
                         f"types: {', '.join(parser_types)}")

    return _parser


# PARSERS
#
# This section contains the actual text parsers that take a string and return
# a value.


def compress(string: str, _: Mapping[str, str]) -> Compress:
    """Parse a string into a :class:`Compress` object.

    Parameters
    ----------
    string
        String to parse into a :class:`Compress` object.  It should be in the
        following form:

            <type:type> [scale_factor:float] [add_offset:float]

        where only the first value is required and should be one of the
        following 4 character RADS data type values:

            * `int1` - maps to numpy.int8
            * `int2` - maps to numpy.int16
            * `int4` - maps to numpy.int32
            * `real` - maps to numpy.float32
            * `dble` - maps to numpy.float64

        The attribute mapping of the tag the string came from.  Not currently
        used by this function.
    _
        Mapping of tag attributes.  Not used by this function.

    Returns
    -------
    Compress
        A new :class:`Compress` object created from the parsed string.

    Raises
    ------
    ValueError
        If the <type> is not in the given :paramref:`string` or if too many
        values are in the :paramref:`string`.  Also, if one of the values
        cannot be converted.

    """
    parts = string.split()
    try:
        funcs: Iterable[Callable[[str], Any]] = (
            _rads_type, fortran_float, fortran_float, lambda x: x)
        return Compress(*(f(s) for f, s in zip(funcs, parts)))
    except TypeError:
        if len(parts) > 3:
            raise ValueError(
                "too many values given, expected only 'type', "
                "'scale_factor', and 'add_offset'")
        raise ValueError("'missing 'type'")


def cycles(string: str, _: Mapping[str, str]) -> Cycles:
    """Parse a string into a :class:`Cycles` object.

    Parameters
    ----------
    string
        String to parse into a :class:`Cycles` object.  It should be in the
        following form:

        .. code-block:: text

            <first cycle in phase> <last cycle in phase>
    _
        Mapping of tag attributes.  Not used by this function.

    Returns
    -------
    Cycles
        A new :class:`Cycles` object created from the parsed string.

    Raises
    ------
    ValueError
        If the wrong number of values are given in the :paramref:`string` or
        one of the values is not parsable to an integer.

    """
    try:
        return Cycles(*(int(s) for s in string.split()))
    except TypeError:
        num_values = len(string.split())
        if num_values == 0:
            raise ValueError("missing 'first' cycle")
        if num_values == 1:
            raise ValueError("missing 'last' cycle")
        raise ValueError(
            "too many cycles given, expected only 'first' and 'last'")


def nop(string: str, _: Mapping[str, str]) -> str:
    """No operation parser, returns given string unchanged.

    This exists primarily as a default for when no parser is given as the use
    of `lift(str)` is recommended when the parsed value is supposed to be a
    string.

    Parameters
    ----------
    string
        String to return.
    _
        Mapping of tag attributes.  Not used by this function.

    Returns
    -------
    str
        The given :paramref:`string`.

    """
    return string


def ref_pass(string: str, _: Mapping[str, str]) -> ReferencePass:
    """Parse a string into a :class:`ReferencePass` object.

    Parameters
    ----------
    string
        String to parse into a:class:`ReferencePass` object.  It should be in
        the following form:

        .. code-block:: text

            <yyyy-mm-ddTHH:MM:SS> <lon> <cycle> <pass> [absolute orbit number]

        where the last element is optional and defaults to 1.  The date can
        also be missing seconds, minutes, and hours.
    _
        Mapping of tag attributes.  Not used by this function.

    Returns
    -------
    ReferencePass
        A new :class:`ReferencePass` object created from the parsed string.

    Raises
    ------
        If the wrong number of values are given in the :paramref:`string` or
        one of the values is not parsable.

    """
    parts = string.split()
    try:
        funcs: Sequence[Callable[[str], Any]] = (
            _time, float, int, int, int, lambda x: x)
        return ReferencePass(*(f(s) for f, s in zip(funcs, parts)))
    except TypeError:
        if not parts:
            raise ValueError("missing 'time' of reference pass")
        if len(parts) == 1:
            raise ValueError(
                "missing equator crossing 'longitude' of reference pass")
        if len(parts) == 2:
            raise ValueError("missing 'cycle number' of reference pass")
        if len(parts) == 3:
            raise ValueError("missing 'pass number' of reference pass")
        # absolute orbit number is defaulted in ReferencePass
        raise ValueError("too many values given, expected only 'time', "
                         "'longitude', 'cycle number', 'pass number', and "
                         "optionally 'absolute orbit number'")


def repeat(string: str, _: Mapping[str, str]) -> Repeat:
    """Parse a string into a :class:`Repeat` object.

    Parameters
    ----------
    string
        String to parse into a :class:`Repeat` object. It should be in the
        following form:

        .. code-block:: text

            <days:float> <passes:int> [longitude drift per cycle:float]

        where the last value is optional.
    _
        Mapping of tag attributes.  Not used by this function.

    Returns
    -------
    Repeat
        A new :class:`Repeat` object created from the parsed string.

    Raises
    ------
    ValueError
        If the wrong number of values are given in the :paramref:`string` or
        one of the values is not parsable.

    """
    parts = string.split()
    try:
        funcs: Sequence[Callable[[str], Any]] = (
            float, int, float, lambda x: x)
        return Repeat(*(f(s) for f, s in zip(funcs, parts)))
    except TypeError:
        if not parts:
            raise ValueError("missing length of repeat cycle in 'days'")
        if len(parts) == 1:
            raise ValueError("missing length of repeat cycle in 'passes'")
        raise ValueError(
            "too many values given, expected only 'days', "
            "'passes', and 'longitude_drift'")


def time(string: str, _: Mapping[str, str]) -> datetime:
    """Parse a string into a :class:`datetime` object.

    Parameters
    ----------
    string
        String to parse into a :class:`datetime` object. It should be in one of
        the following forms:

            * yyyy-mm-ddTHH:MM:SS
            * yyyy-mm-ddTHH:MM
            * yyyy-mm-ddTHH
            * yyyy-mm-ddT
            * yyyy-mm-dd
    _
        Mapping of tag attributes.  Not used by this function.

    Returns
    -------
        A new :class:`datetime` object created from the parsed string.

    Raises
    ------
    ValueError
        If the date/time :paramref:`string` cannot be parsed.

    """
    return _time(string)


def unit(string: str, _: Mapping[str, str]) -> Unit:
    """Parse a string into a :class:`Unit` object.

    .. _cf_units: https://github.com/SciTools/cf-units

    .. _`issue 30`: https://github.com/SciTools/cf-units/issues/30

    Parameters
    ----------
    string
        String to parse into a :class:`Unit` object.  See the cf_units_ package
        for supported units.  If given 'dB' or 'decibel' a no_unit object will
        be returned and if given 'yymmddhhmmss' an unknown unit will be
        returned.
    _
        Mapping of tag attributes.  Not used by this function.

    Returns
    -------
    Unit
        A new :class:`Unit` object created from the parsed string.  In the case
        of 'dB' and 'decibel' this will be a no_unit and in the case of
        'yymmddhhmmss' it will be 'unknown'.  See `issue 30`_.

    Raises
    ------
    ValueError
        If the given :paramref:`string` does not represent a valid unit.

    """
    try:
        return Unit(string)
    except ValueError:
        string = string.strip()
        # TODO: Remove this hack when
        #  https://github.com/SciTools/cf-units/issues/30 is fixed.
        if string in ('dB', 'decibel'):
            return Unit('no unit')
        if string == 'yymmddhhmmss':
            return Unit('unknown')
        raise ValueError(f"failed to parse unit '{string}'")


def _time(string: str) -> datetime:
    try:
        return datetime.strptime(string, '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        try:
            return datetime.strptime(string, '%Y-%m-%dT%H:%M')
        except ValueError:
            try:
                return datetime.strptime(string, '%Y-%m-%dT%H')
            except ValueError:
                try:
                    return datetime.strptime(string, '%Y-%m-%dT')
                except ValueError:
                    try:
                        return datetime.strptime(string, '%Y-%m-%d')
                    except ValueError:
                        # required to avoid 'unconverted data' message from
                        # strptime
                        raise ValueError(
                            "time data '{:s}' does not match format "
                            "'%Y-%m-%dT%H:%M:%S'".format(string))


def _rads_type(string: str) -> type:
    switch: Dict[str, type] = {
        'int1': np.int8,
        'int2': np.int16,
        'int4': np.int32,
        'real': np.float32,
        'dble': np.float64
    }
    try:
        return switch[string.lower()]
    except KeyError:
        raise ValueError(f"invalid RADS type string '{string}'")