import io
from datetime import datetime

import pytest  # type: ignore

from rads.constants import EPOCH
from rads.utility import (
    contains_sublist,
    datetime_to_timestamp,
    delete_sublist,
    ensure_open,
    fortran_float,
    isio,
    merge_sublist,
    timestamp_to_datetime,
    xor,
)


def test_ensure_open_closeio_default():
    file = io.StringIO("content")
    with ensure_open(file) as f:
        assert not f.closed
    assert not f.closed


def test_ensure_open_closeio_true():
    file = io.StringIO("content")
    with ensure_open(file, closeio=True) as f:
        assert not f.closed
    assert f.closed


def test_ensure_open_closeio_false():
    file = io.StringIO("content")
    with ensure_open(file, closeio=False) as f:
        assert not f.closed
    assert not f.closed


def test_isio(mocker):
    assert isio(io.StringIO("content"))
    assert not isio("string is not io")
    m = mocker.Mock()
    m.read.return_value = "duck typing not accepted"
    assert not isio(m)


def test_isio_read(mocker):
    assert isio(io.StringIO("content"), read=True)
    assert not isio("string is not io", read=True)
    m = mocker.Mock(spec=["read"])
    m.read.return_value = "duck typing is accepted"
    assert isio(m, read=True)
    m = mocker.Mock(spec=["write"])
    m.write.return_value = "duck typing is accepted"
    assert not isio(m, read=True)


def test_isio_write(mocker):
    assert isio(io.StringIO("content"), write=True)
    assert not isio("string is not io", write=True)
    m = mocker.Mock(spec=["read"])
    m.read.return_value = "duck typing is accepted"
    assert not isio(m, write=True)
    m = mocker.Mock(spec=["write"])
    m.write.return_value = "duck typing is accepted"
    assert isio(m, write=True)


def test_xor():
    assert not xor(True, True)
    assert xor(True, False)
    assert xor(False, True)
    assert not xor(False, False)


def test_contains_sublist():
    assert contains_sublist([1, 2, 3, 4], [1, 2])
    assert contains_sublist([1, 2, 3, 4], [2, 3])
    assert contains_sublist([1, 2, 3, 4], [3, 4])
    assert contains_sublist([1, 2, 3, 4], [1, 2, 3, 4])
    assert not contains_sublist([1, 2, 3, 4], [2, 1])
    assert not contains_sublist([1, 2, 3, 4], [3, 2])
    assert not contains_sublist([1, 2, 3, 4], [4, 3])
    # while the empty list is technically a sublist of any list for this
    # function [] is never a sublist
    assert not contains_sublist([1, 2, 3, 4], [])


def test_merge_sublist():
    assert merge_sublist([1, 2, 3, 4], []) == [1, 2, 3, 4]
    assert merge_sublist([1, 2, 3, 4], [1, 2]) == [1, 2, 3, 4]
    assert merge_sublist([1, 2, 3, 4], [2, 3]) == [1, 2, 3, 4]
    assert merge_sublist([1, 2, 3, 4], [3, 4]) == [1, 2, 3, 4]
    assert merge_sublist([1, 2, 3, 4], [0, 1]) == [1, 2, 3, 4, 0, 1]
    assert merge_sublist([1, 2, 3, 4], [4, 5]) == [1, 2, 3, 4, 4, 5]
    assert merge_sublist([1, 2, 3, 4], [1, 1]) == [1, 2, 3, 4, 1, 1]


def test_delete_sublist():
    assert delete_sublist([1, 2, 3, 4], []) == [1, 2, 3, 4]
    assert delete_sublist([1, 2, 3, 4], [1, 2]) == [3, 4]
    assert delete_sublist([1, 2, 3, 4], [2, 3]) == [1, 4]
    assert delete_sublist([1, 2, 3, 4], [3, 4]) == [1, 2]
    assert delete_sublist([1, 2, 3, 4], [0, 1]) == [1, 2, 3, 4]
    assert delete_sublist([1, 2, 3, 4], [4, 5]) == [1, 2, 3, 4]
    assert delete_sublist([1, 2, 3, 4], [1, 1]) == [1, 2, 3, 4]


def test_fortran_float():
    assert fortran_float("3.14e10") == pytest.approx(3.14e10)
    assert fortran_float("3.14E10") == pytest.approx(3.14e10)
    assert fortran_float("3.14d10") == pytest.approx(3.14e10)
    assert fortran_float("3.14D10") == pytest.approx(3.14e10)
    assert fortran_float("3.14e+10") == pytest.approx(3.14e10)
    assert fortran_float("3.14E+10") == pytest.approx(3.14e10)
    assert fortran_float("3.14d+10") == pytest.approx(3.14e10)
    assert fortran_float("3.14D+10") == pytest.approx(3.14e10)
    assert fortran_float("3.14e-10") == pytest.approx(3.14e-10)
    assert fortran_float("3.14E-10") == pytest.approx(3.14e-10)
    assert fortran_float("3.14d-10") == pytest.approx(3.14e-10)
    assert fortran_float("3.14D-10") == pytest.approx(3.14e-10)
    assert fortran_float("3.14+100") == pytest.approx(3.14e100)
    assert fortran_float("3.14-100") == pytest.approx(3.14e-100)
    with pytest.raises(ValueError):
        fortran_float("not a float")


def test_datetime_to_epoch():
    epoch = datetime(2000, 1, 1, 0, 0, 0)
    assert datetime_to_timestamp(datetime(2000, 1, 1, 0, 0, 0), epoch=epoch) == 0.0
    assert datetime_to_timestamp(datetime(2000, 1, 1, 0, 0, 1), epoch=epoch) == 1.0
    assert datetime_to_timestamp(datetime(2000, 1, 1, 0, 1, 0), epoch=epoch) == 60.0
    assert datetime_to_timestamp(datetime(2000, 1, 1, 1, 0, 0), epoch=epoch) == 3600.0


def test_datetime_to_epoch_with_default_epoch():
    assert datetime_to_timestamp(
        datetime(2000, 1, 1, 0, 0, 0)
    ) == datetime_to_timestamp(datetime(2000, 1, 1, 0, 0, 0), epoch=EPOCH)
    assert datetime_to_timestamp(
        datetime(2000, 1, 1, 0, 0, 1)
    ) == datetime_to_timestamp(datetime(2000, 1, 1, 0, 0, 1), epoch=EPOCH)
    assert datetime_to_timestamp(
        datetime(2000, 1, 1, 0, 1, 0)
    ) == datetime_to_timestamp(datetime(2000, 1, 1, 0, 1, 0), epoch=EPOCH)
    assert datetime_to_timestamp(
        datetime(2000, 1, 1, 1, 0, 0)
    ) == datetime_to_timestamp(datetime(2000, 1, 1, 1, 0, 0), epoch=EPOCH)


def test_epoch_to_datetime():
    epoch = datetime(2000, 1, 1, 0, 0, 0)
    assert timestamp_to_datetime(0.0, epoch=epoch) == datetime(2000, 1, 1, 0, 0, 0)
    assert timestamp_to_datetime(1.0, epoch=epoch) == datetime(2000, 1, 1, 0, 0, 1)
    assert timestamp_to_datetime(60.0, epoch=epoch) == datetime(2000, 1, 1, 0, 1, 0)
    assert timestamp_to_datetime(3600.0, epoch=epoch) == datetime(2000, 1, 1, 1, 0, 0)


def test_epoch_to_datetime_with_default_epoch():
    assert timestamp_to_datetime(0.0) == timestamp_to_datetime(0.0, epoch=EPOCH)
    assert timestamp_to_datetime(1.0) == timestamp_to_datetime(1.0, epoch=EPOCH)
    assert timestamp_to_datetime(60.0) == timestamp_to_datetime(60.0, epoch=EPOCH)
    assert timestamp_to_datetime(3600.0) == timestamp_to_datetime(3600.0, epoch=EPOCH)
