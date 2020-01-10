from datetime import datetime

import numpy as np  # type: ignore
import pytest  # type: ignore
from cf_units import Unit  # type: ignore

from rads.config.text_parsers import (
    TerminalTextParseError,
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
from rads.config.tree import (
    Compress,
    Constant,
    Cycles,
    Flags,
    Grid,
    MultiBitFlag,
    NetCDFAttribute,
    NetCDFVariable,
    Range,
    ReferencePass,
    Repeat,
    SingleBitFlag,
    SurfaceType,
)
from rads.rpn import Expression


def test_exceptions():
    # A TextParseError is also a TerminalTextParseError because exceptions for
    # TerminalTextParseErrors should also catch TextParseErrors.
    with pytest.raises(TerminalTextParseError):
        raise TextParseError


def test_lift():
    assert lift(str)("3", {}) == "3"
    assert lift(int)("3", {}) == 3
    assert lift(float)("3.14", {}) == 3.14
    with pytest.raises(TextParseError):
        lift(float)("not_a_float", {})
    with pytest.raises(TerminalTextParseError):
        lift(float, terminal=True)("not_a_float", {})
    assert lift(int)._lifted == "int"  # type: ignore


def test_list_of(mocker):
    assert list_of(lift(int))("1 2 3 4 5", {}) == [1, 2, 3, 4, 5]
    assert list_of(lift(int))("1   2 3      4 5", {}) == [1, 2, 3, 4, 5]
    assert list_of(lift(int))("", {}) == []
    m = mocker.Mock()
    m.return_value = 3
    list_of(m)("abc 123", {"stuff": "3.14"})
    assert m.call_count == 2
    m.assert_any_call("abc", {"stuff": "3.14"})
    m.assert_any_call("123", {"stuff": "3.14"})
    with pytest.raises(TextParseError):
        list_of(lift(int))("a b c", {})
    with pytest.raises(TerminalTextParseError):
        list_of(lift(int), terminal=True)("a b c", {})


def test_range_of(mocker):
    assert range_of(lift(int))("2 3", {}) == Range(2, 3)
    assert range_of(lift(float))("2.5 3.14", {}) == Range(2.5, 3.14)
    assert range_of(lift(int))("2   3", {}) == Range(2, 3)
    m = mocker.Mock()
    range_of(m)("2.5 3.14", {"stuff": "3.14"})
    assert m.call_count == 2
    m.assert_any_call("2.5", {"stuff": "3.14"})
    m.assert_any_call("3.14", {"stuff": "3.14"})
    with pytest.raises(TextParseError):
        range_of(lift(int))("2.5 3.14", {})
    with pytest.raises(TextParseError):
        range_of(lift(int))(" ", {})
    with pytest.raises(TextParseError):
        range_of(lift(int))("1", {})
    with pytest.raises(TextParseError):
        range_of(lift(int))("1 2 3", {})
    with pytest.raises(TerminalTextParseError):
        range_of(lift(int), terminal=True)(" ", {})


def test_one_of(mocker):
    int_float_str = one_of((lift(int), lift(float), lift(str)))
    assert int_float_str("3", {}) == 3
    assert type(int_float_str("3", {})) == int
    assert int_float_str("3.14", {}) == 3.14
    assert type(int_float_str("3.14", {})) == float
    assert int_float_str("3abc", {}) == "3abc"
    assert type(int_float_str("3abc", {})) == str
    m1 = mocker.Mock()
    m2 = mocker.Mock()
    one_of((m1, m2))("abc", {"stuff": "123"})
    m1.assert_called_once_with("abc", {"stuff": "123"})
    assert m2.call_count == 0
    with pytest.raises(TextParseError):
        one_of((lift(int), lift(float)))("abc", {})
    with pytest.raises(TextParseError):
        one_of((time,))("abc", {})
    with pytest.raises(TerminalTextParseError):
        one_of((time,), terminal=True)("abc", {})


def test_compress():
    assert compress("int1", {}) == Compress(np.int8)
    assert compress("int2", {}) == Compress(np.int16)
    assert compress("int4", {}) == Compress(np.int32)
    assert compress("real", {}) == Compress(np.float32)
    assert compress("dble", {}) == Compress(np.float64)
    assert compress("int4 2e-3", {}) == Compress(np.int32, 2e-3)
    assert compress("int4 2d-3", {}) == Compress(np.int32, 2e-3)
    assert compress("int4 2e-3 1300e3", {}) == Compress(np.int32, 2e-3, 1300e3)
    assert compress("int4 2d-3 1300d3", {}) == Compress(np.int32, 2e-3, 1300e3)
    assert compress("int4 2-3 1300+3", {}) == Compress(np.int32, 2e-3, 1300e3)
    assert compress("int4   2d-3    1300d3", {}) == Compress(np.int32, 2e-3, 1300e3)
    with pytest.raises(TextParseError):
        compress("", {})
    with pytest.raises(TextParseError):
        compress("int", {})
    with pytest.raises(TextParseError):
        compress("int2 2a-3", {})
    with pytest.raises(TextParseError):
        compress("int2 2e-3 1300a3", {})
    with pytest.raises(TextParseError):
        compress("int4 2e-3 1300e3 5", {})


def test_cycles():
    assert cycles("100 200", {}) == Cycles(100, 200)
    assert cycles("  100    200       ", {}) == Cycles(100, 200)
    with pytest.raises(TextParseError):
        cycles("100 2.5", {})
    with pytest.raises(TextParseError):
        cycles("1.5 200", {})
    with pytest.raises(TextParseError):
        cycles("", {})
    with pytest.raises(TextParseError):
        cycles("100", {})
    with pytest.raises(TextParseError):
        cycles("100 200 300", {})


def test_data_as_constant():
    # explicit constant
    assert data("3", {"source": "constant"}) == Constant(3)
    assert data("3.14", {"source": "constant"}) == Constant(3.14)
    # implicit constant
    assert data("3", {}) == Constant(3)
    assert data("3.14", {}) == Constant(3.14)
    # not a constant
    assert not isinstance(data("abc", {}), Constant)
    assert not isinstance(data("abc.nc", {}), Constant)
    assert not isinstance(data("3.14 2.72 ADD", {}), Constant)
    # not a constant, explicit leads to terminal error
    with pytest.raises(TerminalTextParseError) as exc_info:
        data("", {"source": "constant"})
    assert exc_info.type is TerminalTextParseError
    with pytest.raises(TerminalTextParseError) as exc_info:
        data("abc", {"source": "constant"})
    assert exc_info.type is TerminalTextParseError
    with pytest.raises(TerminalTextParseError) as exc_info:
        data("3.14 2.72", {"source": "constant"})
    assert exc_info.type is TerminalTextParseError


def test_data_as_flags():
    assert data("5", {"source": "flags"}) == SingleBitFlag(5)
    assert data("5 9", {"source": "flags"}) == MultiBitFlag(5, 9)
    assert data("surface_type", {"source": "flags"}) == SurfaceType()
    # never parsed as flags without source
    assert not isinstance(data("surface_type", {}), Flags)
    # invalid flags leads to terminal error
    with pytest.raises(TerminalTextParseError) as exc_info:
        data("", {"source": "flags"})
    assert exc_info.type is TerminalTextParseError
    with pytest.raises(TerminalTextParseError) as exc_info:
        data("5.5", {"source": "flags"})
    assert exc_info.type is TerminalTextParseError
    with pytest.raises(TerminalTextParseError) as exc_info:
        data("5 9.5", {"source": "flags"})
    assert exc_info.type is TerminalTextParseError
    with pytest.raises(TerminalTextParseError) as exc_info:
        data("5 9 3", {"source": "flags"})
    assert exc_info.type is TerminalTextParseError
    with pytest.raises(TerminalTextParseError) as exc_info:
        data("surface", {"source": "flags"})
    # negative bit is invalid
    with pytest.raises(TerminalTextParseError) as exc_info:
        data("-1", {"source": "flags"})
    assert exc_info.type is TerminalTextParseError
    # multibit must have multiple bits
    with pytest.raises(TerminalTextParseError) as exc_info:
        data("0 0", {"source": "flags"})
    assert exc_info.type is TerminalTextParseError


def test_data_as_grid():
    # explicit grid, default x and y
    assert data("gridfile.nc", {"source": "grid"}) == Grid(
        "gridfile.nc", "lon", "lat", "linear"
    )
    assert data("gridfile.nc", {"source": "grid_l"}) == Grid(
        "gridfile.nc", "lon", "lat", "linear"
    )
    assert data("gridfile.nc", {"source": "grid_s"}) == Grid(
        "gridfile.nc", "lon", "lat", "spline"
    )
    assert data("gridfile.nc", {"source": "grid_c"}) == Grid(
        "gridfile.nc", "lon", "lat", "spline"
    )
    assert data("gridfile.nc", {"source": "grid_q"}) == Grid(
        "gridfile.nc", "lon", "lat", "nearest"
    )
    assert data("gridfile.nc", {"source": "grid_n"}) == Grid(
        "gridfile.nc", "lon", "lat", "nearest"
    )
    # explicit grid, custom x and y
    assert data("gridfile.nc", {"source": "grid", "x": "x", "y": "y"}) == Grid(
        "gridfile.nc", "x", "y", "linear"
    )
    assert data("gridfile.nc", {"source": "grid_l", "x": "x", "y": "y"}) == Grid(
        "gridfile.nc", "x", "y", "linear"
    )
    assert data("gridfile.nc", {"source": "grid_s", "x": "x", "y": "y"}) == Grid(
        "gridfile.nc", "x", "y", "spline"
    )
    assert data("gridfile.nc", {"source": "grid_c", "x": "x", "y": "y"}) == Grid(
        "gridfile.nc", "x", "y", "spline"
    )
    assert data("gridfile.nc", {"source": "grid_q", "x": "x", "y": "y"}) == Grid(
        "gridfile.nc", "x", "y", "nearest"
    )
    assert data("gridfile.nc", {"source": "grid_n", "x": "x", "y": "y"}) == Grid(
        "gridfile.nc", "x", "y", "nearest"
    )
    # implicit grid, default x and y
    assert data("gridfile.nc", {}) == Grid("gridfile.nc", "lon", "lat", "linear")
    # implicit grid, custom x and y
    assert data("gridfile.nc", {"x": "x", "y": "y"}) == Grid(
        "gridfile.nc", "x", "y", "linear"
    )
    # not a grid
    assert not isinstance(data("3.14", {}), Grid)
    assert not isinstance(data("abc", {}), Grid)
    assert not isinstance(data("3.14 2.72 ADD", {}), Grid)


def test_data_as_math():
    # explicit math
    assert data("", {"source": "math"}) == Expression("")
    assert data("3.14", {"source": "math"}) == Expression("3.14")
    assert data("abc", {"source": "math"}) == Expression("abc")
    assert data("3.14 2.72 ADD", {"source": "math"}) == Expression("3.14 2.72 ADD")
    assert data("3.14 ADD", {"source": "math"}) == Expression("3.14 ADD")
    # implicit math
    assert data("3.14 2.72 ADD", {}) == Expression("3.14 2.72 ADD")
    assert data("3.14 ADD", {}) == Expression("3.14 ADD")
    # not math
    assert not isinstance(data("3.14", {}), Expression)
    assert not isinstance(data("ADD", {}), Expression)
    assert not isinstance(data("abc", {}), Expression)
    assert not isinstance(data("abc.nc", {}), Expression)
    assert not isinstance(data("abc xyz.nc", {}), Expression)
    # not math, explicit leads to terminal error
    # assert exc_info.type is TerminalTextParseError
    with pytest.raises(TerminalTextParseError) as exc_info:
        data("abc.nc", {"source": "math"})
    assert exc_info.type is TerminalTextParseError
    # invalid math, explicit leads to terminal error
    with pytest.raises(TerminalTextParseError) as exc_info:
        data("3abc 4xyz", {"source": "math"})
    assert exc_info.type is TerminalTextParseError
    # invalid math, implicit leads to terminal error
    with pytest.raises(TerminalTextParseError) as exc_info:
        data("3abc 4xyz", {})
    assert exc_info.type is TerminalTextParseError


def test_data_as_netcdf():
    # explicit netcdf
    assert data("alt_gdre", {"source": "nc"}) == NetCDFVariable("alt_gdre")
    assert data("alt_gdre", {"source": "netcdf"}) == NetCDFVariable("alt_gdre")
    assert data("range_ku:add_offset", {"source": "nc"}) == NetCDFAttribute(
        "add_offset", "range_ku"
    )
    assert data("range_ku:add_offset", {"source": "netcdf"}) == NetCDFAttribute(
        "add_offset", "range_ku"
    )
    assert data(":range_bias_ku", {"source": "nc"}) == NetCDFAttribute("range_bias_ku")
    assert data(":range_bias_ku", {"source": "netcdf"}) == NetCDFAttribute(
        "range_bias_ku"
    )
    # explicit netcdf, with branch
    assert data("alt_gdre", {"source": "nc", "branch": ".mydata"}) == NetCDFVariable(
        "alt_gdre", ".mydata"
    )
    assert data(
        "alt_gdre", {"source": "netcdf", "branch": ".mydata"}
    ) == NetCDFVariable("alt_gdre", ".mydata")
    assert data(
        "range_ku:add_offset", {"source": "nc", "branch": ".mydata"}
    ) == NetCDFAttribute("add_offset", "range_ku", ".mydata")
    assert data(
        "range_ku:add_offset", {"source": "netcdf", "branch": ".mydata"}
    ) == NetCDFAttribute("add_offset", "range_ku", ".mydata")
    assert data(
        ":range_bias_ku", {"source": "nc", "branch": ".mydata"}
    ) == NetCDFAttribute("range_bias_ku", branch=".mydata")
    assert data(
        ":range_bias_ku", {"source": "netcdf", "branch": ".mydata"}
    ) == NetCDFAttribute("range_bias_ku", branch=".mydata")
    # implicit netcdf
    assert data("alt_gdre", {}) == NetCDFVariable("alt_gdre")
    assert data("range_ku:add_offset", {}) == NetCDFAttribute("add_offset", "range_ku")
    assert data(":range_bias_ku", {}) == NetCDFAttribute("range_bias_ku")
    # implicit netcdf, with branch
    assert data("alt_gdre", {"branch": ".mydata"}) == NetCDFVariable(
        "alt_gdre", ".mydata"
    )
    assert data("range_ku:add_offset", {"branch": ".mydata"}) == NetCDFAttribute(
        "add_offset", "range_ku", ".mydata"
    )
    assert data(":range_bias_ku", {"branch": ".mydata"}) == NetCDFAttribute(
        "range_bias_ku", branch=".mydata"
    )
    # not netcdf variable
    assert not isinstance(data("3.14", {}), NetCDFVariable)
    assert not isinstance(data("abc:xyz", {}), NetCDFVariable)
    assert not isinstance(data(":xyz", {}), NetCDFVariable)
    assert not isinstance(data("abc.nc", {}), NetCDFVariable)
    assert not isinstance(data("3.14 2.72 ADD", {}), NetCDFVariable)
    # not netcdf attribute
    assert not isinstance(data("3.14", {}), NetCDFAttribute)
    assert not isinstance(data("abc", {}), NetCDFAttribute)
    assert not isinstance(data("abc.nc", {}), NetCDFAttribute)
    assert not isinstance(data("3.14 2.72 ADD", {}), NetCDFAttribute)
    # not netcdf variable or attribute, explicit leads to terminal error
    with pytest.raises(TerminalTextParseError) as exc_info:
        data("3.14", {"source": "nc"})
    assert exc_info.type is TerminalTextParseError
    with pytest.raises(TerminalTextParseError) as exc_info:
        data("var.nc", {"source": "nc"})
    assert exc_info.type is TerminalTextParseError
    with pytest.raises(TerminalTextParseError) as exc_info:
        data("3.14 2.72 ADD", {"source": "nc"})
    assert exc_info.type is TerminalTextParseError
    # should not default with explict source
    assert not isinstance(data("abc", {"source": "math"}), NetCDFVariable)
    assert not isinstance(data("abc", {"source": "math"}), NetCDFAttribute)


def test_data_with_invalid():
    with pytest.raises(TerminalTextParseError) as exc_info:
        data("", {})
    assert exc_info.type is TerminalTextParseError


def test_nop():
    assert nop("  abc   ", {}) == "  abc   "


def test_ref_pass():
    assert ref_pass("2016-03-01T21:00:11 -41.5 116 105", {}) == ReferencePass(
        datetime(2016, 3, 1, 21, 0, 11), -41.5, 116, 105
    )
    assert ref_pass("2016-03-01T21:00:11 -41.5 116 105 3", {}) == ReferencePass(
        datetime(2016, 3, 1, 21, 0, 11), -41.5, 116, 105, 3
    )
    # invalid values
    with pytest.raises(TextParseError):
        ref_pass("2016-03-01T99:00:11 -41.5 116 105 3", {})
    with pytest.raises(TextParseError):
        ref_pass("2016-03-01T21:00:11 2016-03-01T21:00:11 116 105 3", {})
    with pytest.raises(TextParseError):
        ref_pass("2016-03-01T21:00:11 -41.5 116.5 105 3", {})
    with pytest.raises(TextParseError):
        ref_pass("2016-03-01T21:00:11 -41.5 116 105.5 3", {})
    with pytest.raises(TextParseError):
        ref_pass("2016-03-01T21:00:11 -41.5 116 105 3.5", {})
    # missing values
    with pytest.raises(TextParseError):
        ref_pass("", {})
    with pytest.raises(TextParseError):
        ref_pass("2016-03-01T21:00:11", {})
    with pytest.raises(TextParseError):
        ref_pass("2016-03-01T21:00:11 -41.5", {})
    with pytest.raises(TextParseError):
        ref_pass("2016-03-01T21:00:11 -41.5 116", {})
    # too many values
    with pytest.raises(TextParseError):
        ref_pass("2016-03-01T21:00:11 -41.5 116 105 3 5", {})


def test_repeat():
    assert repeat("9.91 254", {}) == Repeat(9.91, 254)
    assert repeat("9.91 254 0.2", {}) == Repeat(9.91, 254, 0.2)
    # invalid values
    with pytest.raises(TextParseError):
        repeat("abc 254", {})
    with pytest.raises(TextParseError):
        repeat("9.91 254.5", {})
    with pytest.raises(TextParseError):
        repeat("9.91 254 abc", {})
    # missing values
    with pytest.raises(TextParseError):
        repeat("", {})
    with pytest.raises(TextParseError):
        repeat("9.91", {})
    # too many values
    with pytest.raises(TextParseError):
        repeat("9.91 254 0.2 1", {})


def test_time():
    assert time("2012-05-07T14:57:08", {}) == datetime(2012, 5, 7, 14, 57, 8)
    assert time("2012-05-07T14:57", {}) == datetime(2012, 5, 7, 14, 57)
    assert time("2012-05-07T14", {}) == datetime(2012, 5, 7, 14)
    assert time("2012-05-07T", {}) == datetime(2012, 5, 7)
    assert time("2012-05-07", {}) == datetime(2012, 5, 7)
    with pytest.raises(TextParseError):
        time("2012-05", {})
    with pytest.raises(TextParseError):
        time("2012-05-07 14:57:08", {})


def test_unit():
    assert unit("km", {}) == Unit("km")
    assert unit("dB", {}) == Unit("no unit")
    assert unit("decibel", {}) == Unit("no unit")
    assert unit("yymmddhhmmss", {}) == Unit("unknown")
    with pytest.raises(TextParseError):
        unit("abc", {})
