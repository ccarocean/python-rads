import pytest  # type: ignore

from rads.config.ast import append, delete, edit_append, merge, replace
from rads.config.utility import parse_action
from rads.config.xml_parsers import TerminalXMLParseError


def test_parse_action_replace_is_default(mocker):
    m = mocker.Mock(attributes={})
    assert parse_action(m) == replace


def test_parse_action_replace(mocker):
    m = mocker.Mock(attributes={"action": "replace"})
    assert parse_action(m) == replace


def test_parse_action_append(mocker):
    m = mocker.Mock(attributes={"action": "append"})
    assert parse_action(m) == append


def test_parse_action_delete(mocker):
    m = mocker.Mock(attributes={"action": "delete"})
    assert parse_action(m) == delete


def test_parse_action_merge(mocker):
    m = mocker.Mock(attributes={"action": "merge"})
    assert parse_action(m) == merge


def test_parse_action_invalid(mocker):
    m = mocker.Mock(attributes={"action": "add"})
    with pytest.raises(TerminalXMLParseError):
        parse_action(m)


def test_parse_action_edit_append(mocker):
    m = mocker.Mock(attributes={"edit": "append"})
    assert parse_action(m) == edit_append


def test_parse_action_invalid_edit(mocker):
    m = mocker.Mock(attributes={"edit": "replace"})
    with pytest.raises(TerminalXMLParseError):
        parse_action(m)
