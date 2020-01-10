import numpy as np  # type: ignore
import pytest  # type: ignore

from rads.config.tree import MultiBitFlag, SingleBitFlag, SurfaceType


class TestSingleBitFlag:
    def test_init(self):
        for bit in range(0, 63):
            SingleBitFlag(bit)
        with pytest.raises(TypeError):
            SingleBitFlag(1.5)  # type: ignore
        with pytest.raises(ValueError):
            SingleBitFlag(-1)

    def test_bit(self):
        for bit in range(0, 63):
            assert SingleBitFlag(bit).bit == bit

    def test_extract_with_value(self):
        assert not SingleBitFlag(0).extract(0)
        assert SingleBitFlag(0).extract(1)
        assert not SingleBitFlag(0).extract(2)
        assert SingleBitFlag(0).extract(3)
        assert not SingleBitFlag(0).extract(4)
        assert not SingleBitFlag(1).extract(0)
        assert not SingleBitFlag(1).extract(1)
        assert SingleBitFlag(1).extract(2)
        assert SingleBitFlag(1).extract(3)
        assert not SingleBitFlag(1).extract(4)

    def test_extract_with_array(self):
        np.testing.assert_equal(
            SingleBitFlag(0).extract(np.array([0, 1, 2, 3, 4])),
            np.array([False, True, False, True, False]),
        )
        np.testing.assert_equal(
            SingleBitFlag(1).extract(np.array([0, 1, 2, 3, 4])),
            np.array([False, False, True, True, False]),
        )


class TestMutiBitFlag:
    def test_init(self):
        for bit in range(0, 63):
            for length in range(2, 65 - bit):
                MultiBitFlag(bit, length)
        with pytest.raises(TypeError):
            MultiBitFlag(1.5, 5)  # type: ignore
        with pytest.raises(TypeError):
            MultiBitFlag(2, 3.5)  # type: ignore
        with pytest.raises(ValueError):
            MultiBitFlag(-1, 3)
        with pytest.raises(ValueError):
            MultiBitFlag(2, 0)
        with pytest.raises(ValueError):
            MultiBitFlag(2, -1)

    def test_bit(self):
        for bit in range(0, 63):
            for length in range(2, 65 - bit):
                assert MultiBitFlag(bit, length).bit == bit

    def test_length(self):
        for bit in range(0, 63):
            for length in range(2, 65 - bit):
                assert MultiBitFlag(bit, length).length == length

    def test_extract_with_value(self):
        # 2 bits
        assert MultiBitFlag(0, 2).extract(0b0110101) == 1
        assert MultiBitFlag(1, 2).extract(0b0110101) == 2
        assert MultiBitFlag(2, 2).extract(0b0110101) == 1
        assert MultiBitFlag(3, 2).extract(0b0110101) == 2
        assert MultiBitFlag(4, 2).extract(0b0110101) == 3
        assert MultiBitFlag(5, 2).extract(0b0110101) == 1
        assert MultiBitFlag(6, 2).extract(0b0110101) == 0
        # 3 bits
        assert MultiBitFlag(0, 3).extract(0b0110101) == 5
        assert MultiBitFlag(1, 3).extract(0b0110101) == 2
        assert MultiBitFlag(2, 3).extract(0b0110101) == 5
        assert MultiBitFlag(3, 3).extract(0b0110101) == 6
        assert MultiBitFlag(4, 3).extract(0b0110101) == 3
        assert MultiBitFlag(5, 3).extract(0b0110101) == 1
        assert MultiBitFlag(6, 3).extract(0b0110101) == 0
        # extract from 0b000000...
        for bit in range(0, 63):
            for length in range(2, 65 - bit):
                assert MultiBitFlag(bit, length).extract(0) == 0
        # extract from 0b111111...
        for bit in range(0, 64):
            for length in range(2, 65 - bit):
                assert MultiBitFlag(bit, length).extract(2 ** 64 - 1) == (
                    2 ** 64 - 1
                ) >> (64 - length)

    def test_extract_with_array(self):
        input = np.array([0, 2 ** 64 - 1], dtype=np.uint64)
        for bit in range(0, 63):
            for length in range(2, 65 - bit):
                result = MultiBitFlag(bit, length).extract(input)
                expected = np.array(
                    [0, (2 ** 64 - 1) >> (64 - length)], dtype=np.uint64
                )
                np.testing.assert_equal(result, expected)
                assert isinstance(result, (np.generic, np.ndarray))
                if length <= 8:
                    assert result.dtype == np.uint8
                elif length <= 16:
                    assert result.dtype == np.uint16
                elif length <= 32:
                    assert result.dtype == np.uint32
                else:  # length <= 64:
                    assert result.dtype == np.uint64


class TestSurfaceType:
    def test_init(self):
        SurfaceType()

    def test_extract_with_value(self):
        assert SurfaceType().extract(0b000000) == 0  # ocean
        assert SurfaceType().extract(0b100000) == 2  # lake
        assert SurfaceType().extract(0b010000) == 3  # land
        assert SurfaceType().extract(0b000100) == 4  # ice
        # with other bits set
        assert SurfaceType().extract(0b1101011) == 2  # lake
        assert SurfaceType().extract(0b1111011) == 3  # land
        assert SurfaceType().extract(0b1111111) == 4  # ice

    def test_extract_with_array(self):
        input = np.array([0b000000, 0b100000, 0b010000, 0b000100], dtype=np.int64)
        np.testing.assert_equal(SurfaceType().extract(input), [0, 2, 3, 4])
        # with other bits set
        input = np.array([0b1101011, 0b1111011, 0b1111111], dtype=np.int64)
        np.testing.assert_equal(SurfaceType().extract(input), [2, 3, 4])
