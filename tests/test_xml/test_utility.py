import io
from textwrap import dedent

import pytest  # type: ignore

from rads.xml import ParseError
from rads.xml.utility import (
    fromstring,
    fromstringlist,
    parse,
    rads_fixer,
    rootless_fixer,
    strip_blanklines,
    strip_comments,
    strip_processing_instructions,
)


def test_strip_comments_single_line_comments():
    xml = """\
    <!--single line comment!-->
    <a>Hello World</a>
    <!--single line comment!-->
    <a>Goodbye</a>
    """
    assert strip_comments(dedent(xml)).splitlines() == [
        "",
        "<a>Hello World</a>",
        "",
        "<a>Goodbye</a>",
    ]


def test_strip_comments_inline_comments():
    xml = """\
    <!--inline comment!-->  <a>Hello World</a> <!--inline comment!-->
    <a>Goodbye</a>
    """
    assert strip_comments(dedent(xml)).splitlines() == [
        "  <a>Hello World</a> ",
        "<a>Goodbye</a>",
    ]


def test_strip_comments_multiline_comments():
    xml = """\
    <a>Hello World</a>
    <!--multi
    line
    comment--> <a>Goodbye</a> <!--another multi
    line comment-->
    """
    assert strip_comments(dedent(xml)).splitlines() == [
        "<a>Hello World</a>",
        " <a>Goodbye</a> ",
    ]


def test_strip_processing_instructions():
    xml = """\
    <?xml version="1.0"?>
    <a>Hello World</a>
    """
    assert strip_processing_instructions(dedent(xml)).splitlines() == [
        "",
        "<a>Hello World</a>",
    ]


def test_strip_blanklines():
    xml = """\
     \t   \t   \t
    <a>Hello World</a>
    
    <a>Goodbye</a>
    
    """  # noqa: W293
    assert strip_blanklines(dedent(xml)).splitlines() == [
        "<a>Hello World</a>",
        "<a>Goodbye</a>",
    ]


def test_rads_fixer():
    xml = """\
    <?xml version="1.0"?>
    <!--This is a RADS XML file.-->
    <var name="range_s">
        <compress>int3 1e-4</compress>
    </var>
    <satellite>ENVISAT1</satellite>
    """
    assert rads_fixer(dedent(xml)).splitlines() == [
        '<?xml version="1.0"?>',
        "<__ROOTLESS__>",
        "<!--This is a RADS XML file.-->",
        '<var name="range_s">',
        "    <compress>int4 1e-4</compress>",
        "</var>",
        "<satellite>ENVISAT1</satellite>",
        "</__ROOTLESS__>",
    ]


def test_rootless_fixer():
    xml = """\
    <a>Hello World</a>
    <a>Goodbye</a>
    """
    assert rootless_fixer(dedent(xml)).splitlines() == [
        "<__ROOTLESS__>",
        "<a>Hello World</a>",
        "<a>Goodbye</a>",
        "</__ROOTLESS__>",
    ]


def test_rootless_fixer_with_empty_file():
    xml = """\
    <?xml version="1.0"?>
    <!-- This is an empty rootless XML file-->
    """
    assert rootless_fixer(dedent(xml)).splitlines() == [
        '<?xml version="1.0"?>',
        "<__ROOTLESS__>",
        "<!-- This is an empty rootless XML file-->",
        "</__ROOTLESS__>",
    ]
    assert rootless_fixer(dedent(xml), preserve_empty=False).splitlines() == [
        '<?xml version="1.0"?>',
        "<__ROOTLESS__>",
        "<!-- This is an empty rootless XML file-->",
        "</__ROOTLESS__>",
    ]
    assert (
        rootless_fixer(dedent(xml), preserve_empty=True).splitlines()
        == dedent(xml).splitlines()
    )


# NOTE: A full path file is used below since the API is allowed to expand to a
#   full path which breaks comparisons.


def test_fromstring():
    xml = """\
    <message>
        <sender>John Smith</sender>
        <content>Hello World</content>
    </message>
    """
    root = fromstring(dedent(xml))
    assert root.tag == "message"
    assert root.down().tag == "sender"
    assert root.down().text == "John Smith"
    assert root.down().next().tag == "content"
    assert root.down().next().text == "Hello World"


def test_fromstring_with_file():
    xml = """\
    <a>Hello World</a>
    """
    root = fromstring(dedent(xml), file="/a_file.xml")
    assert root.file == "/a_file.xml"


def test_fromstring_with_empty_xml():
    # processing instructions and comments do not count as content
    xml = """\
    <?xml version="1.0"?>
    <!--single line comment!-->
    """
    with pytest.raises(ParseError):
        fromstring(dedent(xml))


def test_fromstring_with_empty_xml_and_file():
    # processing instructions and comments do not count as content
    xml = """\
    <?xml version="1.0"?>
    <!--single line comment!-->
    """
    with pytest.raises(ParseError) as exc_info:
        fromstring(dedent(xml), file="/a_file.xml")
    assert exc_info.value.filename == "/a_file.xml"


def test_fromstring_with_fixer():
    xml = """\
    <message>
        <sender>John Smith</sender>
        <content>Hello World</content>
    </message>
    """

    def fixer(text):
        return text.replace("John Smith", "Nobody").replace("Hello World", "Goodbye")

    root = fromstring(dedent(xml), fixer=fixer)
    assert root.tag == "message"
    assert root.down().tag == "sender"
    assert root.down().text == "Nobody"
    assert root.down().next().tag == "content"
    assert root.down().next().text == "Goodbye"


def test_fromstringlist():
    xml = [
        "<message>",
        "<sender>John Smith</sender>",
        "<content>Hello World</content>",
        "</message>",
    ]
    root = fromstringlist(xml)
    assert root.tag == "message"
    assert root.down().tag == "sender"
    assert root.down().text == "John Smith"
    assert root.down().next().tag == "content"
    assert root.down().next().text == "Hello World"


def test_fromstringlist_with_file():
    xml = ["<a>Hello World</a>"]
    root = fromstringlist(xml, file="/a_file.xml")
    assert root.file == "/a_file.xml"


def test_fromstringlist_with_empty_xml():
    # processing instructions and comments do not count as content
    xml = ['<?xml version="1.0"?>', "<!--single line comment!-->"]
    with pytest.raises(ParseError):
        fromstringlist(xml)


def test_fromstringlist_with_empty_xml_and_file():
    # processing instructions and comments do not count as content
    xml = ['<?xml version="1.0"?>', "<!--single line comment!-->"]
    with pytest.raises(ParseError) as exc_info:
        fromstringlist(xml, file="/a_file.xml")
    assert exc_info.value.filename == "/a_file.xml"


def test_fromstringlist_with_fixer():
    xml = [
        "<message>",
        "<sender>John Smith</sender>",
        "<content>Hello World</content>",
        "</message>",
    ]

    def fixer(text):
        return text.replace("John Smith", "Nobody").replace("Hello World", "Goodbye")

    root = fromstringlist(xml, fixer=fixer)
    assert root.tag == "message"
    assert root.down().tag == "sender"
    assert root.down().text == "Nobody"
    assert root.down().next().tag == "content"
    assert root.down().next().text == "Goodbye"


# TODO: Add parse unit tests.


def test_parse():
    xml = """\
    <message>
        <sender>John Smith</sender>
        <content>Hello World</content>
    </message>
    """
    file = io.StringIO(dedent(xml))
    file.name = "/a_file.xml"
    root = parse(file)
    assert root.file == "/a_file.xml"
    assert root.tag == "message"
    assert root.down().tag == "sender"
    assert root.down().text == "John Smith"
    assert root.down().next().tag == "content"
    assert root.down().next().text == "Hello World"


def test_parse_with_empty_file():
    # processing instructions and comments do not count as content
    xml = """\
    <?xml version="1.0"?>
    <!--single line comment!-->
    """
    file = io.StringIO(dedent(xml))
    file.name = "/a_file.xml"
    with pytest.raises(ParseError) as exc_info:
        parse(file)
    assert exc_info.value.filename == "/a_file.xml"


def test_parse_with_fixer():
    xml = """\
    <message>
        <sender>John Smith</sender>
        <content>Hello World</content>
    </message>
    """

    file = io.StringIO(dedent(xml))
    file.name = "a_file.xml"

    def fixer(text):
        return text.replace("John Smith", "Nobody").replace("Hello World", "Goodbye")

    root = parse(file, fixer=fixer)
    assert root.tag == "message"
    assert root.down().tag == "sender"
    assert root.down().text == "Nobody"
    assert root.down().next().tag == "content"
    assert root.down().next().text == "Goodbye"
