import io
from datetime import datetime

import numpy as np  # type: ignore
import pytest  # type: ignore

from rads.constants import EPOCH
from rads.utility import (
    contains_sublist,
    datetime_to_timestamp,
    delete_sublist,
    ensure_open,
    fortran_float,
    get,
    getsorted,
    isio,
    merge_sublist,
    outliers,
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


def test_datetime_to_timestamp():
    epoch = datetime(2000, 1, 1, 0, 0, 0)
    assert datetime_to_timestamp(datetime(2000, 1, 1, 0, 0, 0), epoch=epoch) == 0.0
    assert datetime_to_timestamp(datetime(2000, 1, 1, 0, 0, 1), epoch=epoch) == 1.0
    assert datetime_to_timestamp(datetime(2000, 1, 1, 0, 1, 0), epoch=epoch) == 60.0
    assert datetime_to_timestamp(datetime(2000, 1, 1, 1, 0, 0), epoch=epoch) == 3600.0


def test_datetime_to_timestamp_with_default_epoch():
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


def test_timestamp_to_datetime():
    epoch = datetime(2000, 1, 1, 0, 0, 0)
    assert timestamp_to_datetime(0.0, epoch=epoch) == datetime(2000, 1, 1, 0, 0, 0)
    assert timestamp_to_datetime(1.0, epoch=epoch) == datetime(2000, 1, 1, 0, 0, 1)
    assert timestamp_to_datetime(60.0, epoch=epoch) == datetime(2000, 1, 1, 0, 1, 0)
    assert timestamp_to_datetime(3600.0, epoch=epoch) == datetime(2000, 1, 1, 1, 0, 0)


def test_timestamp_to_datetime_with_default_epoch():
    assert timestamp_to_datetime(0.0) == timestamp_to_datetime(0.0, epoch=EPOCH)
    assert timestamp_to_datetime(1.0) == timestamp_to_datetime(1.0, epoch=EPOCH)
    assert timestamp_to_datetime(60.0) == timestamp_to_datetime(60.0, epoch=EPOCH)
    assert timestamp_to_datetime(3600.0) == timestamp_to_datetime(3600.0, epoch=EPOCH)


def test_get_with_dict():
    dict_ = {"a": 1, "b": 2, "c": 3}
    assert get(dict_, "a") == 1
    assert get(dict_, "b") == 2
    assert get(dict_, "c") == 3
    assert get(dict_, "d") is None


def test_get_with_dict_and_custom_default():
    dict_ = {"a": 1, "b": 2, "c": 3}
    assert get(dict_, "a", 10) == 1
    assert get(dict_, "b", 10) == 2
    assert get(dict_, "c", 10) == 3
    assert get(dict_, "d", 10) == 10
    assert get(dict_, "d", "not found") == "not found"


def test_get_with_list():
    list_ = ["a", "b", "c"]
    assert get(list_, 0) == "a"
    assert get(list_, 1) == "b"
    assert get(list_, 2) == "c"
    assert get(list_, 3) is None


def test_get_with_list_and_custom_default():
    list_ = ["a", "b", "c"]
    assert get(list_, 0) == "a"
    assert get(list_, 1) == "b"
    assert get(list_, 2) == "c"
    assert get(list_, 3, 10) == 10
    assert get(list_, 3, "not found") == "not found"


def test_getsorted_with_scalar_value():
    array = np.array([1, 2, 4, 5, 7])
    n = len(array)
    assert getsorted(array, 0) == n
    assert getsorted(array, 1) == 0
    assert getsorted(array, 2) == 1
    assert getsorted(array, 3) == n
    assert getsorted(array, 4) == 2
    assert getsorted(array, 5) == 3
    assert getsorted(array, 6) == n
    assert getsorted(array, 7) == 4
    assert getsorted(array, 8) == n
    assert getsorted(array, 9) == n


def test_getsorted_with_vector_value():
    array = np.array([1, 2, 4, 5, 7])
    n = len(array)
    np.testing.assert_equal(
        getsorted(array, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
        np.array([n, 0, 1, n, 2, 3, n, 4, n, n]),
    )


def test_getsorted_with_vector_value_and_valid_only():
    array = np.array([1, 2, 4, 5, 7])
    np.testing.assert_equal(
        getsorted(array, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], valid_only=True),
        np.array([0, 1, 2, 3, 4]),
    )


def test_getsorted_with_scalar_value_and_sorter():
    array = np.array([2, 7, 1, 5, 4])
    sorter = np.argsort(array)
    n = len(array)
    assert getsorted(array, 0, sorter=sorter) == n
    assert getsorted(array, 1, sorter=sorter) == 2
    assert getsorted(array, 2, sorter=sorter) == 0
    assert getsorted(array, 3, sorter=sorter) == n
    assert getsorted(array, 4, sorter=sorter) == 4
    assert getsorted(array, 5, sorter=sorter) == 3
    assert getsorted(array, 6, sorter=sorter) == n
    assert getsorted(array, 7, sorter=sorter) == 1
    assert getsorted(array, 8, sorter=sorter) == n
    assert getsorted(array, 9, sorter=sorter) == n


def test_getsorted_with_vector_value_and_sorter():
    array = np.array([2, 7, 1, 5, 4])
    sorter = np.argsort(array)
    n = len(array)
    np.testing.assert_equal(
        getsorted(array, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], sorter=sorter),
        np.array([n, 2, 0, n, 4, 3, n, 1, n, n]),
    )


def test_getsorted_with_vector_value_and_valid_only_and_sorter():
    array = np.array([2, 7, 1, 5, 4])
    sorter = np.argsort(array)
    np.testing.assert_equal(
        getsorted(
            array, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], valid_only=True, sorter=sorter
        ),
        np.array([2, 0, 4, 3, 1]),
    )


def test_outliers():
    data = np.array([3, 30, 45, 50, 48, 52, 55, 70, 98])
    np.testing.assert_equal(
        outliers(data), [True, False, False, False, False, False, False, False, True]
    )
    np.testing.assert_equal(
        outliers(data, zscore_limit=1.0),
        [True, True, False, False, False, False, False, True, True],
    )
