"""PyRADS XML file loader functions."""
import os
from functools import wraps
from pathlib import Path
from typing import IO, Any, Callable, Dict, Iterable, Mapping, Optional, TypeVar, cast

from dataclass_builder import MissingFieldError

from ..data.dataroot import Dataroot
from ..exceptions import ConfigError, InvalidDataroot
from ..paths import (
    local_config,
    local_xml,
    rads_xml,
    site_config,
    user_config,
    user_xml,
)
from ..typing import PathLike, PathLikeOrFile, PathOrFile
from ..utility import isio
from ..xml import ParseError, parse, rads_fixer
from .ast import ASTEvaluationError, NullStatement, Statement
from .builders import PreConfigBuilder, SatelliteBuilder
from .grammar import dataroot_grammar, pre_config_grammar, satellite_grammar
from .tree import Config, PreConfig
from .xml_parsers import Parser, TerminalXMLParseError

__all__ = ["config_files", "get_dataroot", "load_config", "xml_loader"]

# TODO: Remove satellites from blacklist.

# GEOS-3 (g3)    - configuration in rads.xml not complete
# SEASAT-A (ss)  - configuration in rads.xml not complete
#
# This is required because unlike the official RADS, PyRADS attempts to
# load all satellites instead of just one and therefore it will break
# for incomplete configurations.
_BLACKLISTED_SATELLITES = ["g3", "ss"]


def _to_config_error(exc: Exception) -> ConfigError:
    """Convert an exception into a :class:`rads.config.loader.ConfigError`.

    If the exception has file/line information this function will attempt to
    copy it to the new exception.

    :param exc:
        The original exception.

    :return rads.config.loader.ConfigError:
        The new configuration exception.
    """
    if isinstance(exc, ParseError):
        return ConfigError(exc.msg, exc.lineno, exc.filename, original=exc)
    if isinstance(exc, (TerminalXMLParseError, ASTEvaluationError)):
        return ConfigError(exc.message, exc.line, exc.file, original=exc)
    if isinstance(exc, MissingFieldError):
        return ConfigError(f"tag '<{exc.field.name}>' is not optional")
    return ConfigError(str(exc), original=exc)


def config_files(
    dataroot: Optional[PathLike] = None, rads: bool = True, pyrads: bool = True
) -> Iterable[Path]:
    """Get a list of the paths that configuration files will be searched for.

    The full list of configuration files for Unix (other operating systems
    differ) are listed below in the order they are returned from this function,
    which is also the default loading order:

        1. <dataroot>/conf/rads.xml
        2. /etc/pyrads/settings.xml
        3. ~/.rads/rads.xml
        4. ~/.config/pyrads/settings.xml
        5. rads.xml
        6. pyrads.xml

    This can be used to add another xml file when loading the configuration.

    .. code-block:: python

        load_config(config_files=(xml_files() + '/path/to/custom/config.xml'))

    :param dataroot:
        Optionally specify the path to the RADS dataroot.  If not given
        :func:`get_dataroot` will be used with default arguments to retrieve
        the RADS dataroot.
    :param rads:
        Set to False to disable all RADS only configuration files.  These are
        the configuration files used by the official RADS implementation and
        are (in order):

            1. ``<dataroot>/conf/rads.xml``
            2. ``~/.rads/rads.xml``
            3. ``rads.xml``
    :param pyrads:
        Set to False to disable all PyRADS configuration files.  These are the
        new configuration files added by PyRADS in which PyRADS exclusive tags
        can be used:

            1. ``/etc/pyrads/settings.xml``
            2. ``~/.config/pyrads/settings.xml``
            3. ``pyrads.xml``

        .. note::

            The files listed above are only for Unix, other operating systems
            differ.

    :return:
        The locations that configuration files can be, in the order that they
        are loaded.
    """
    files = []
    if rads:
        dataroot = get_dataroot(dataroot)  # verify or find dataroot
        if dataroot:
            files.append(rads_xml(dataroot))
    if pyrads:
        files.append(site_config())
    if rads:
        files.append(user_xml())
    if pyrads:
        files.append(user_config())
    if rads:
        files.append(local_xml())
    if pyrads:
        files.append(local_config())
    return files


def get_dataroot(
    dataroot: Optional[PathLike] = None,
    *,
    xml_files: Optional[Iterable[PathLikeOrFile]] = None,
) -> Dataroot:
    """Get the RADS dataroot.

    The *dataroot* or RADSDATAROOT as it is referred to in the official RADS
    user manual is a directory that contains the ``conf`` directory along with
    the individual satellite directories full of data.  In particular, it must
    contain ``conf/rads.xml`` to be considered the *dataroot*.

    The priority of retrieving the *dataroot* is as follows:

        1. If the `dataroot` is given directly it will be used.
        2. If the ``RADSDATAROOT`` environment variable is set then it will be
           used as the location of the RADS *dataroot*.
        3. If given `xml_files` they will be searched for the ``<dataroot>``
           tag and its value will be used as the location of the *dataroot*.
        4. The default PyRADS specific configuration files will be searched for
           the ``<dataroot>`` tag.

    :param dataroot:
        Optionally specify the *dataroot* directly, this function will only
        verify that the path is a *dataroot* if this is given.
    :param xml_files:
        Optionally specify which configuration files to look for the
        ``<dataroot>`` tag in.  This tag specifies the *dataroot* if it exists.
        The files that will be used if this parameter is not given are (for
        Unix, other operating systems will vary):

            1. ``/etc/pyrads/settings.xml``
            2. ``~/.config/pyrads/settings.xml``
            3. ``pyrads.xml``

        .. note::

            The ``<dataroot>`` tag is a PyRADS only tag.  Adding it to any
            official RADS configuration file will result in an error if the
            official RADS implementation is used.

    :return:
        The path to the RADS *dataroot* or None if it cannot be found.

    :raises rads.exceptions.InvalidDataroot:
        If the *dataroot* the given/configured *dataroot* is not a valid RADS
        *dataroot*.
    """
    # find the dataroot
    if dataroot is not None:
        dataroot_ = Path(dataroot)
    elif os.getenv("RADSDATAROOT"):
        dataroot_ = Path(os.environ["RADSDATAROOT"]).expanduser()
    else:  # read from XML files
        if xml_files is None:
            xml_files = config_files(dataroot, rads=False, pyrads=True)
        dataroot_value: Optional[str] = None
        for file in _filter_files(xml_files):
            dataroot_value = _load_dataroot(file, dataroot_value)
        if dataroot_value is None:
            raise InvalidDataroot("cannot find RADS data directory")
        dataroot_ = Path(os.path.expanduser(os.path.expandvars(dataroot_value)))

    # verify and return the dataroot
    return Dataroot(dataroot_)


def _filter_files(files: Iterable[PathLikeOrFile]) -> Iterable[PathOrFile]:
    for file in files:
        if isio(file, read=True):
            yield cast(IO[Any], file)
        else:
            path = Path(cast(PathLike, file))
            if path.is_file():
                yield path


def load_config(
    *,
    dataroot: Optional[PathLike] = None,
    xml_files: Optional[Iterable[PathLikeOrFile]] = None,
    satellites: Optional[Iterable[str]] = None,
) -> Config:
    """Load the PyRADS configuration from one or more XML files.

    :param dataroot:
        Optionally set the RADS *dataroot*.  If not given :func:`get_dataroot`
        will be used.  If `xml_files` were given they will be passed to the
        :func:`get_dataroot` function.
    :param xml_files:
        Optionally supply the list of XML files to load the configuration from.
        If not given the result of :func:`config_files` will be used as the
        default.
    :param satellites:
        Optionally specify which satellites to load the configuration for by
        their 2 character id strings.  The default is to load the configuration
        for all non-blacklisted satellites.

    :return:
        The resulting PyRADS configuration object.

    :raises RuntimeError:
        If the *dataroot* cannot be found or the given/configured *dataroot* is
        not a valid RADS *dataroot*.
    :raises rads.config.loader.ConfigError:
        If there is any problem loading the configuration files.

    .. seealso::

        :class:`rads.config.tree.Config`
            PyRADS configuration object.
    """
    # load pre-config
    pre_config = _load_preconfig(
        dataroot=dataroot, xml_files=xml_files, satellites=satellites
    )

    # initialize configuration object and satellite configuration builders
    builders: Mapping[str, Any] = {
        sat: SatelliteBuilder()
        for sat in pre_config.satellites
        if sat not in pre_config.blacklist
    }

    # parse and evaluate each configuration file
    for file in pre_config.config_files:
        builders = _load_satellites(file, builders)

    # build each satellite configuration object
    satellites = {}
    for sat, builder in builders.items():
        try:
            satellites[sat] = builder.build()
        except MissingFieldError as err:
            raise _to_config_error(err) from err

    return Config(pre_config, satellites)


T = TypeVar("T")


def xml_loader(grammar: Parser) -> Callable[[Callable[..., T]], Callable[..., T]]:
    r"""Decorate a function taking an AST to allow it to take a file path.

    This decorates a function which takes an AST statement (and any extra
    arguments) and replaces the first argument (the AST statement) with a file
    path.  It also adds error handling for loading, parsing, and evaluation (if
    the decorated function attempts to evaluate the AST statement).  It does
    this by converting all errors to :class:`ConfigError`\ s.

    If the file is empty the decorated function will get a
    :class:`rads.config.ast.NullStatement`.

    :param grammar:
        The grammar to parse the file with.

    :return:
        The decorator.

    :raises rads.exceptions.ConfigError:
        By the decorated function if the given file cannot be loaded, parsed,
        or evaluated.
    """

    def _decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def _loader(source: PathLikeOrFile, *args: Any, **kwargs: Any) -> T:
            try:
                return func(_load_ast(source, grammar), *args, **kwargs)
            except ASTEvaluationError as err:
                raise _to_config_error(err) from err

        return _loader

    return _decorator


def _load_ast(source: PathLikeOrFile, grammar: Parser) -> Statement:
    """Load AST from a file.

    :param source:
        Path of the file to load the AST from.
    :param grammar:
        Grammar used to generate the AST.

    :return:
        The resulting AST.  This will be :class:`rads.config.ast.NullStatement`
        if the file is empty.

    :raises ConfigError:
        If there is any problem reading the given XML file or in parsing it
        with the given `grammar`.
    """
    try:
        return cast(Statement, grammar(parse(source, fixer=rads_fixer).down())[0])
    except StopIteration:
        return NullStatement()
    except (ParseError, TerminalXMLParseError) as err:
        raise _to_config_error(err) from err


@xml_loader(dataroot_grammar())
def _load_dataroot(ast: Statement, dataroot: Optional[str] = None) -> Optional[str]:
    env: Dict[str, str] = {}
    ast.eval(env, {})
    return env.get("dataroot", dataroot)


def _load_preconfig(
    *,
    dataroot: Optional[PathLike] = None,
    xml_files: Optional[Iterable[PathLikeOrFile]] = None,
    satellites: Optional[Iterable[str]] = None,
) -> PreConfig:
    """Load the pre-configuration object.

    See :func:`load_config` for argument documentation.

    """
    # get dataroot and xml paths
    dataroot_ = get_dataroot(dataroot, xml_files=xml_files)
    if xml_files is None:
        xml_files = config_files(dataroot_, rads=True, pyrads=True)

    # load preconfig
    builder = PreConfigBuilder()
    for file in _filter_files(xml_files):
        builder = _load_preconfig2(file, builder)
    builder.dataroot = dataroot_
    builder.config_files = list(_filter_files(xml_files))
    try:
        pre_config: PreConfig = builder.build()
    except MissingFieldError as err:
        raise _to_config_error(err) from err

    # allow satellite subsetting
    if satellites is not None:
        # check that all provided satellites are in the configuration files
        for satellite in satellites:
            if satellite not in pre_config.satellites:
                raise ValueError(f"satellite '{satellite}' is not available")
        pre_config.satellites = list(satellites)

    # add hardcoded blacklist
    pre_config.blacklist = list(
        set(pre_config.blacklist).union(set(_BLACKLISTED_SATELLITES))
    )

    return pre_config


@xml_loader(pre_config_grammar())
def _load_preconfig2(ast: Statement, builder: T) -> T:
    ast.eval(builder, {})
    return builder


@xml_loader(satellite_grammar())
def _load_satellites(ast: Statement, builders: Mapping[str, T]) -> Mapping[str, T]:
    for sat, builder in builders.items():
        ast.eval(builder, {"id": sat})
    return builders
