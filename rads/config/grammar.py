"""RADS XML file parser expression grammar."""
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence, Tuple

import fortran_format_converter as ffc

from ..xml.base import Element
from .ast import (
    Alias,
    Assignment,
    CompoundStatement,
    If,
    NullStatement,
    Phase,
    SatelliteID,
    Satellites,
    Source,
    Statement,
    Variable,
)
from .text_parsers import (
    TextParseError,
    compress,
    cycles,
    data,
    lift,
    list_of,
    nop,
    one_of,
    range_of,
    ref_pass,
    repeat,
    time,
    unit,
)
from .tree import SubCycles
from .utility import (
    error_at,
    named_block_processor,
    parse_action,
    parse_condition,
    source_from_element,
)
from .xml_parsers import (
    Parser,
    TerminalXMLParseError,
    any,
    end,
    lazy,
    opt,
    star,
    start,
    tag,
)

__all__ = [
    "satellite_grammar",
    "pre_config_grammar",
    "dataroot_grammar",
    "ignore",
    "value",
    "if_statement",
    "block",
    "alias",
    "phase",
    "satellite_ids",
    "satellites",
    "subcycles",
    "variable",
    "variable_override",
    "variable_overrides",
]


def alias() -> Parser:
    """Return a parser to parse the <alias> tag.

    :return:
        A parser that consumes the <alias> XML tag and produces a
        :class:`rads.config.ast.Alias` AST node.

    :raises rads.config.xml_parsers.TerminalXMLParseError:
        Raised by the returned parser if an <alias> tag is empty or does not
        contain a "name" attribute.
    """

    def process(element: Element) -> Alias:
        try:
            alias = element.attributes["name"]
        except KeyError:
            raise error_at(element)("'name' attribute missing from <alias>")
        variables = element.text.split() if element.text else []
        if not variables:
            raise error_at(element)("<alias> cannot be empty")
        condition = parse_condition(element.attributes)
        action = parse_action(element)
        source = source_from_element(element)
        return Alias(alias, variables, condition, action, source=source)

    return tag("alias") ^ process


def ignore(tag_: Optional[str] = None) -> Parser:
    """Return a parser to ignore a given XML tag.

    :param tag_:
        The name of the tag to consume and ignore.  The default is to ignore
        any tag.

    :return:
        A parser that consumes the given XML `tag_` and produces a
        :class:`rads.config.ast.NullStatement` AST node which essentially
        throws away the tag.
    """

    def process(element: Element) -> NullStatement:
        return NullStatement(source=source_from_element(element))

    if tag_:
        return tag(tag_) ^ process
    return any() ^ process


def value(
    parser: Callable[[str, Mapping[str, str]], Any] = nop,
    tag_: Optional[str] = None,
    var: Optional[str] = None,
) -> Parser:
    """Return a parser to parse a simple value assignment XML tag.

    :param parser:
        The text parser to use for the contents of the given `tag_`.  It will
        also be given the attributes mapping.
    :param tag_:
        The name of the tag to parse.  The default is to consume any tag.
    :param var:
        Override the name the value is to be assigned to.  The default is the
        tag name.

        .. note::

            Use of this will break the AST's ability to make suggestions when
            attempting to assign to an invalid variable as that feature
            requires the tag and variable to have the same name.

    :return:
        A parser that consumes the given XML `tag_` and produces a
        :class:`rads.config.ast.Assignment` AST node.

    :raises rads.config.xml_parsers.TerminalXMLParseError:
        Raised by the returned parser if the consumed tag is empty or the given
        text `parser` produces a :class:`rads.config.text_parsers.TextParseError`.
    """

    def process(element: Element) -> Assignment:
        var_ = var if var else element.tag
        condition = parse_condition(element.attributes)
        action = parse_action(element)
        text = element.text if element.text else ""
        source = source_from_element(element)
        try:
            value = parser(text, element.attributes)
        except TextParseError as err:
            raise error_at(element)(str(err)) from err
        return Assignment(
            name=var_, value=value, condition=condition, action=action, source=source
        )

    if tag_:
        return tag(tag_) ^ process
    return any() ^ process


def if_statement(internal: Parser) -> Parser:
    """Return a parser to parse the <if> tag, opt. followed by <elseif> and <else>.

    In the case of <elseif> tags they will be converted to nested if/else.  Using
    Python conditionals as an example, the following:

    .. code-block:: python

        if a == 1:
            ...
        elif a == 2
            ...
        elif a == 3:
            ...
        else
            ...

    would be converted internally to:

    .. code-block:: python

        if a == 1:
            ...
        else:
            if a == 2:
                ...
            else:
                if a == 3:
                    ...
                else:
                    ...

    This is because the AST does not have an ElseIf node.

    :param internal:
        XML parser to handle the inside of the <if>, <elseif>, and <else> tags.
        None of its errors are caught by the <if> parser.

    :return:
        A parser that consumes the <if> XML tag, optionally followed by one or
        more <elseif> tags and/or a <else> tag, and produces an
        :class:`rads.config.ast.If` AST node.
    """

    def process(statements: Tuple[Element, Statement]) -> If:
        if_element, false_statement = statements
        condition = parse_condition(if_element.attributes)
        true_statement = internal(if_element.down())[0]
        source = source_from_element(if_element)
        return If(
            condition=condition,
            true_statement=true_statement,
            false_statement=false_statement,
            source=source,
        )

    return (
        tag("if") + opt(_elseif_statement(internal) | _else_statement(internal))
        ^ process
    )


def _elseif_statement(internal: Parser) -> Parser:
    """Return a parser to parse the <elseif> tag, opt. followed by <elseif> and <else>.

    See :func:`if_statement` for explanation of how this parser converts
    if/elseif/else to if/else.

    :param internal:
        XML parser to handle the inside of the <elseif> and <else> tags. None
        of its errors are caught by the <if> parser.

    :return:
        A parser that consumes the <elseif> XML tag, optionally followed by one
        or more <elseif> tags and/or a <else> tag, and produces an
        :class:`rads.config.ast.If` AST node.
    """

    def process(statements: Iterable[Any]) -> If:
        elseif_element, false_statement = statements
        condition = parse_condition(elseif_element.attributes)
        true_statement = internal(elseif_element.down())[0]
        source = source_from_element(elseif_element)
        return If(condition, true_statement, false_statement, source=source)

    return (
        tag("elseif")
        + opt(lazy(lambda: _elseif_statement(internal)) | _else_statement(internal))
        ^ process
    )


def _else_statement(internal: Parser) -> Parser:
    """Return a parser to parse the <else> tag.

    :param internal:
        XML parser to handle the inside of the <else> tag.  None of its errors
        are caught by the <if> parser.

    :return:
        A parser that consumes the <else> XML tag and produces an an AST node
        from the `internal` parser.
    """

    def process(element: Element) -> Any:
        return internal(element.down())[0]

    return tag("else") ^ process


def satellites() -> Parser:
    """Return a parser to parse the <satellites> tag.

    :return:
        A parser that consumes the <satellites> tag and produces a
        :class:`rads.config.ast.Satellites` AST node which when evaluated will
        set the 2 and 3 character IDs as well as the alternate names of a
        satellite.

    :raises rads.config.xml_parsers.TerminalXMLParseError:
        Raised by the returned parser if the text of the <satellites> tag
        cannot be parsed.
    """

    def process(element: Element) -> Satellites:
        source = source_from_element(element)
        if not element.text:
            return Satellites(source=source)
        satellites_ = []
        for num, line in enumerate(element.text.strip().splitlines()):
            line = line.strip()
            if line:
                line_ = element.opening_line + num + 1 if element.opening_line else None
                id_source = Source(line=line_, file=element.file)
                try:
                    id_, id3, *names = line.split()
                except ValueError:
                    raise TerminalXMLParseError(
                        id_source.file,
                        id_source.line,
                        f"missing 3 character ID for satellite '{id_}'",
                    )
                satellites_.append(SatelliteID(id_, id3, set(names), source=id_source))
        return Satellites(*satellites_, source=source)

    return tag("satellites") ^ process


def satellite_ids() -> Parser:
    """Return a parser to parse the <satellites> tag (2 character ID's only).

    :return:
        A parser that consumes the <satellites> tag and produces an
        :class:`rads.config.ast.Assignment` AST node which assigns to
        "satellites" a list of the 2 character satellite ID's.

    :raises rads.config.xml_parsers.TerminalXMLParseError:
        Raised by the returned parser if any of the satellite ID's is not
        exactly 2 characters long or the text of the <satellites> cannot
        otherwise be parsed.
    """

    def process(element: Element) -> Assignment:
        source = source_from_element(element)
        if not element.text:
            return Assignment(name="satellites", value=[], source=source)
        satellites_ = []
        for num, line in enumerate(element.text.strip().splitlines()):
            line = line.strip()
            if line:
                line_ = element.opening_line + num + 1 if element.opening_line else None
                id_source = Source(line=line_, file=element.file)
                id_, *_ = line.split()
                if len(id_) != 2:
                    raise TerminalXMLParseError(
                        id_source.file,
                        id_source.line,
                        "satellite id must be exactly 2 characters, found " f"'{id_}'",
                    )
                satellites_.append(id_)
        return Assignment(name="satellites", value=satellites_, source=source)

    return tag("satellites") ^ process


def subcycles() -> Parser:
    """Return a parser to parse the <subcycles> tag.

    :return:
        A parser that consumes the <subcycles> tag and produces an
        :class:`rads.config.ast.Assignment` AST node which assigns to
        "subcycles" a :class:`rads.config.tree.SubCycles` dataclass.

    :raises rads.config.xml_parsers.TerminalXMLParseError:
        Raised by the returned parser if the value of the "start" attribute or
        any of the sub-cycle lengths are not integers.
    """

    def process(element: Element) -> Assignment:
        start: Optional[int]
        condition = parse_condition(element.attributes)
        action = parse_action(element)
        try:
            start = int(element.attributes["start"])
        except KeyError:
            start = None
        except ValueError as err:
            raise error_at(element)(str(err))
        text = element.text if element.text else ""
        try:
            lengths = [int(s) for s in text.split()]
        except ValueError as err:
            raise error_at(element)(str(err))
        source = source_from_element(element)
        value = SubCycles(lengths, start=start)
        return Assignment(
            name="subcycles",
            value=value,
            condition=condition,
            action=action,
            source=source,
        )

    return tag("subcycles") ^ process


def block(
    parser: Parser, error_msg: str = "Invalid configuration block or value."
) -> Parser:
    """Return a parser to parse a block of XML tags.

    :param parser:
        The XML parser to use for the internals of the block.
    :param error_msg:
        Override the error message used when the block raises a
        :class:`rads.config.xml_parsers.XMLParseError`.

    :return:
        A parser that consumes the contents of an XML block between a set of
        tags and produces a :class:`rads.config.ast.Statement` usually a
        :class:`rads.config.ast.CompoundStatement.`.

    :raises rads.config.xml_parsers.TerminalXMLParseError:
        Raised by the returned parser if the internal `parser` produces a
        :class:`rads.config.xml_parsers.XMLParseError`.
    :raises rads.config.xml_parsers.TerminalXMLParseError:
        Raise by the returned parser if not all of the tags within the block
        are consumed.
    """

    def process(statements: Sequence[Statement]) -> Statement:
        # flatten if only a single statement
        if len(statements) == 1:
            return statements[0]
        return CompoundStatement(*statements)

    def recursive_parser() -> Parser:
        return block(parser, error_msg)

    block_parser = star(parser | if_statement(lazy(recursive_parser)) | value())
    return (start() + (block_parser ^ process) + end() << error_msg) ^ (lambda x: x[1])


def phase() -> Parser:
    """Return a parser to parse the <phase> XML tag and block.

    :return:
        A parser that consumes the <phase> XML block and it's contents and
        produces a :class:`rads.config.ast.Phase` AST node.
    """
    phase_block = block(
        value(lift(str), "mission")
        | value(cycles, "cycles")
        | value(repeat, "repeat")
        | value(ref_pass, "ref_pass", var="reference_pass")
        | value(time, "start_time")
        | value(time, "end_time")
        | subcycles()
    )
    process = named_block_processor(phase_block, Phase)
    return tag("phase") ^ process


def variable() -> Parser:
    """Return a parser to parse the <var> XML tag and block.

    :return:
        A parser that consumes the <var> XML block and it's contents and
        produces a :class:`rads.config.ast.Variable` AST Node.
    """
    # NOTE: These must be duplicated in the variable_overrides below.
    variable_block = block(
        value(lift(str), "long_name", var="name")
        | value(lift(str), "standard_name")
        | value(lift(str), "source")
        | value(lift(str), "comment")
        | value(unit, "units")
        | value(list_of(lift(str)), "flag_values")
        | value(list_of(lift(str)), "flag_masks")
        | value(range_of(one_of((lift(int), lift(float)))), "limits")
        | value(range_of(one_of((lift(int), lift(float)))), "plot_range")
        # used by rads for database generation, has no effect on end users
        | ignore("parameters")
        | value(data, "data")
        | value(list_of(lift(str)), "quality_flag")
        # not currently used
        | value(lift(int), "dimensions")
        | value(lift(ffc.convert), "format")
        | value(compress, "compress")
        | value(one_of((lift(int), lift(float))), "default")
    )
    process = named_block_processor(variable_block, Variable)
    return tag("var") ^ process


def variable_override(
    parser: Callable[[str, Mapping[str, str]], Any],
    tag_: str,
    field: Optional[str] = None,
) -> Parser:
    """Return a parser to the parse the named variable override XML tag.

    The RADS variable (which contains this field) is determined by the "var"
    attribute.

    :param parser:
        The text parser to use for the contents of the given `tag_`.  It will
        also be given the attributes mapping.
    :param tag_:
        The name of the XML tag (which is also the overriden value in the
        variable).
    :param field:
        The value to override in the variable.  If not given the value of
        `tag_` will be used.

    :return:
        A parser that consumes the given XML `tag_` and produces a
        :class:`rads.config.ast.Variable` AST node which overrides the given
        `field`.

    :raises rads.config.xml_parsers.TerminalXMLParseError:
        Raised by the returned parser if the consumed tag is empty or the given
        text `parser` produces a :class:`rads.config.text_parsers.TextParseError`.
    """

    def process(element: Element) -> Variable:
        try:
            name = element.attributes["var"]
        except KeyError:
            raise error_at(element)(f"<{tag_}> is missing 'var' attribute.")
        var_ = field if field else element.tag
        condition = parse_condition(element.attributes)
        action = parse_action(element)
        text = element.text if element.text else ""
        source = source_from_element(element)
        try:
            value = parser(text, element.attributes)
        except TextParseError as err:
            raise error_at(element)(str(err)) from err
        name_assignment = Assignment("id", name, source=source)
        assignment = Assignment(name=var_, value=value, action=action, source=source)
        statement = CompoundStatement(name_assignment, assignment, source=source)
        return Variable(statement, condition, source=source)

    return tag(tag_) ^ process


def variable_overrides() -> Parser:
    """Return a parser to parse all variable override tags.

    The returned parser is just a collection the parsers returned from
    :func:`variable_override` combined with
    :class:`rads.config.xml_parsers.Alternate` and is not a global constant
    only for consistency.

    :return:
        A parser that consumes a single variable override tag and produces
        :class:`rads.config.ast.Variable` AST node which overrides a field.
    """
    overrides = (
        variable_override(lift(str), "long_name", field="name")
        | variable_override(lift(str), "standard_name")
        | variable_override(lift(str), "source")
        | variable_override(lift(str), "comment")
        | variable_override(unit, "units")
        | variable_override(list_of(lift(str)), "flag_variable_overrides")
        | variable_override(list_of(lift(str)), "flag_masks")
        | variable_override(range_of(one_of((lift(int), lift(float)))), "limits")
        | variable_override(range_of(one_of((lift(int), lift(float)))), "plot_range")
        # used by rads for database generation, has no effect on end users
        | ignore("parameters")
        | variable_override(data, "data")
        | variable_override(list_of(lift(str)), "quality_flag")
        # not currently used
        | variable_override(lift(int), "dimensions")
        | variable_override(lift(ffc.convert), "format")
        | variable_override(compress, "compress")
        | variable_override(one_of((lift(int), lift(float))), "default")
    )
    return overrides


def satellite_grammar() -> Parser:
    """Return the grammar which is used to parse the XML file for a single satellite.

    The complete AST for evaluation of satellite specific information.

    :return:
        A parser that consumes the entire XML document and returns a
        :class:`rads.config.ast.CompoundStatement` that can be evaluated with
        the "id" selector to retrieve all information for the satellite with
        the given 2 character ID.
    """
    root_block = block(
        # ignore the global attributes
        ignore("global_attributes")
        # satellite id/names table
        | satellites()
        # top level satellite parameters
        | value(lift(str), "satellite", var="name")
        | ignore("satid")
        | value(lift(float), "dt1hz")
        | value(lift(float), "inclination")
        | value(list_of(lift(float)), "frequency")
        | ignore("xover_params")
        # satellite phase
        | phase()
        # variable aliases
        | alias()
        # variables
        | variable()
        | variable_overrides()
        # PyRADS specific tags
        | ignore("dataroot")
        | ignore("cache")
        | ignore("blacklist")
    )
    return root_block


def pre_config_grammar() -> Parser:
    """Return the grammar which is used to parse the XML file for pre configuration.

    :return:
        A parser that consumes the entire XML document and returns a
        :class:`rads.config.ast.CompoundStatement` that can be evaluated without
        selectors to retrieve pre configuration information such as the
        following:

        * 2 character ID's of available satellites.
        * 2 character ID's of satellites to blacklist.
    """
    root_block = block(
        satellite_ids()
        | value(list_of(lift(str)), "blacklist")
        | value(lift(lambda x: Path(x).resolve()), "cache")
        | ignore()  # ignore everything else
    )
    return root_block


def dataroot_grammar() -> Parser:
    """Return the grammar which is used to parse the XML file for the RADS data root.

    :return:
        A parser that consumes the entire XML document and returns a
        :class:`rads.config.ast.CompoundStatement` that can be evaluated
        without selectors to retrieve the RADS data root configured in the
        XML file.
    """
    root_block = block(
        value(lift(str), "dataroot") | ignore()  # ignore everything else
    )
    return root_block
