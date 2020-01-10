import os
from pathlib import Path

import pytest  # type: ignore

from rads.data.dataroot import Dataroot
from rads.exceptions import InvalidDataroot


@pytest.fixture
def dataroot(fs):

    # config
    fs.create_file("/var/rads/conf/rads.xml")

    # satellite ab - phase 1 - cycle 1
    fs.create_file("/var/rads/ab/1/c001/.passindex")
    fs.create_file("/var/rads/ab/1/c001/abp0001c001.nc")
    fs.create_file("/var/rads/ab/1/c001/abp0002c001.nc")

    # satellite ab - phase a - cycle 2
    fs.create_file("/var/rads/ab/a/c002/.passindex")
    fs.create_file("/var/rads/ab/a/c002/abp0001c002.nc")
    fs.create_file("/var/rads/ab/a/c002/abp0002c002.nc")
    fs.create_file("/var/rads/ab/a/c002/abp0003c002.nc")
    fs.create_file("/var/rads/ab/a/c002/abp0004c002.nc")

    # satellite ab - phase 2 - cycle 3
    fs.create_file("/var/rads/ab/2/c003/.passindex")
    fs.create_file("/var/rads/ab/2/c003/abp0001c003.nc")
    fs.create_file("/var/rads/ab/2/c003/abp0002c003.nc")
    fs.create_file("/var/rads/ab/2/c003/abp0003c003.nc")
    fs.create_file("/var/rads/ab/2/c003/abp0004c003.nc")
    fs.create_file("/var/rads/ab/2/c003/abp0005c003.nc")
    fs.create_file("/var/rads/ab/2/c003/abp0006c003.nc")
    fs.create_file("/var/rads/ab/2/c003/abp0007c003.nc")
    fs.create_file("/var/rads/ab/2/c003/abp0008c003.nc")

    # satellite xy - phase a - cycle 447
    fs.create_file("/var/rads/xy/a/c447/.passindex")
    fs.create_file("/var/rads/xy/a/c447/xyp0010c447.nc")
    fs.create_file("/var/rads/xy/a/c447/xyp0011c447.nc")
    fs.create_file("/var/rads/xy/a/c447/xyp0012c447.nc")
    fs.create_file("/var/rads/xy/a/c447/xyp0013c447.nc")
    fs.create_file("/var/rads/xy/a/c447/xyp0015c447.nc")
    fs.create_file("/var/rads/xy/a/c447/xyp0016c447.nc")

    # satellite xy - phase a - cycle 448
    fs.create_file("/var/rads/xy/a/c448/.passindex")
    fs.create_file("/var/rads/xy/a/c448/xyp0001c448.nc")
    fs.create_file("/var/rads/xy/a/c448/xyp0002c448.nc")
    fs.create_file("/var/rads/xy/a/c448/xyp0003c448.nc")

    return fs


class TestDataroot:
    def test_init(self, dataroot):
        assert Dataroot("/var/rads").path == Path("/var/rads")

    def test_init_with_invalid_dataroot(self, dataroot):
        Path("/var/rads/conf/rads.xml").unlink()
        with pytest.raises(InvalidDataroot):
            Dataroot("/var/rads").path

    def test_str(self, dataroot):
        assert str(Dataroot("/var/rads")) == "/var/rads"

    def test_repr(self, dataroot):
        assert repr(Dataroot("/var/rads")) == "Dataroot('/var/rads')"

    def test_fspath(self, dataroot):
        assert os.fspath(Dataroot("/var/rads")) == "/var/rads"

    def test_eq(self, dataroot):
        dataroot.create_file("/var/rads2/conf/rads.xml")
        assert Dataroot("/var/rads") == Dataroot("/var/../var/rads")
        assert not Dataroot("/var/rads") == Dataroot("/var/rads2")

    def test_ne(self, dataroot):
        dataroot.create_file("/var/rads2/conf/rads.xml")
        assert not Dataroot("/var/rads") != Dataroot("/var/../var/rads")
        assert Dataroot("/var/rads") != Dataroot("/var/rads2")

    def test_satellites(self, dataroot):
        assert set(Dataroot("/var/rads").satellites()) == {"ab", "xy"}

    def test_satellite_paths(self, dataroot):
        assert set(Dataroot("/var/rads").satellite_paths()) == {
            Path("/var/rads/ab"),
            Path("/var/rads/xy"),
        }

    def test_satellite_paths_with_extra_dirs(self, dataroot):
        dataroot.create_dir("/var/rads/log")
        assert set(Dataroot("/var/rads").satellite_paths()) == {
            Path("/var/rads/ab"),
            Path("/var/rads/xy"),
        }

    def test_phases(self, dataroot):
        assert set(Dataroot("/var/rads").phases("ab")) == {"1", "2", "a"}
        assert set(Dataroot("/var/rads").phases("xy")) == {"a"}

    def test_phase_paths(self, dataroot):
        assert set(Dataroot("/var/rads").phase_paths()) == {
            Path("/var/rads/ab/1"),
            Path("/var/rads/ab/a"),
            Path("/var/rads/ab/2"),
            Path("/var/rads/xy/a"),
        }

    def test_phase_paths_with_extra_dirs(self, dataroot):
        dataroot.create_dir("/var/rads/ab/a.xyz")
        assert set(Dataroot("/var/rads").phase_paths()) == {
            Path("/var/rads/ab/1"),
            Path("/var/rads/ab/a"),
            Path("/var/rads/ab/2"),
            Path("/var/rads/xy/a"),
        }

    def test_phase_paths_with_satellite(self, dataroot):
        assert set(Dataroot("/var/rads").phase_paths("ab")) == {
            Path("/var/rads/ab/1"),
            Path("/var/rads/ab/a"),
            Path("/var/rads/ab/2"),
        }
        assert set(Dataroot("/var/rads").phase_paths("xy")) == {Path("/var/rads/xy/a")}

    def test_phase_paths_with_invalid_satellite(self, dataroot):
        assert set(Dataroot("/var/rads").phase_paths("uv")) == set()

    def test_cycles(self, dataroot):
        assert set(Dataroot("/var/rads").cycles("ab")) == {1, 2, 3}
        assert set(Dataroot("/var/rads").cycles("xy")) == {447, 448}

    def test_cycles_with_phase(self, dataroot):
        assert set(Dataroot("/var/rads").cycles("ab", "1")) == {1}
        assert set(Dataroot("/var/rads").cycles("ab", "a")) == {2}
        assert set(Dataroot("/var/rads").cycles("ab", "2")) == {3}
        assert set(Dataroot("/var/rads").cycles("xy", "a")) == {447, 448}

    def test_cycles_with_invalid_satellite(self, dataroot):
        assert set(Dataroot("/var/rads").cycles("uv")) == set()

    def test_cycles_with_invalid_phase(self, dataroot):
        assert set(Dataroot("/var/rads").cycles("xy", "b")) == set()

    def test_cycle_paths(self, dataroot):
        assert set(Dataroot("/var/rads").cycle_paths()) == {
            Path("/var/rads/ab/1/c001"),
            Path("/var/rads/ab/2/c003"),
            Path("/var/rads/ab/a/c002"),
            Path("/var/rads/xy/a/c447"),
            Path("/var/rads/xy/a/c448"),
        }

    def test_cycle_paths_with_extra_dirs(self, dataroot):
        dataroot.create_dir("/var/rads/ab/1/log")
        dataroot.create_dir("/var/rads/xy/a/log")
        assert set(Dataroot("/var/rads").cycle_paths()) == {
            Path("/var/rads/ab/1/c001"),
            Path("/var/rads/ab/2/c003"),
            Path("/var/rads/ab/a/c002"),
            Path("/var/rads/xy/a/c447"),
            Path("/var/rads/xy/a/c448"),
        }

    def test_cycle_paths_with_satellite(self, dataroot):
        assert set(Dataroot("/var/rads").cycle_paths("ab")) == {
            Path("/var/rads/ab/1/c001"),
            Path("/var/rads/ab/2/c003"),
            Path("/var/rads/ab/a/c002"),
        }
        assert set(Dataroot("/var/rads").cycle_paths("xy")) == {
            Path("/var/rads/xy/a/c447"),
            Path("/var/rads/xy/a/c448"),
        }

    def test_cycle_paths_with_invalid_satellite(self, dataroot):
        assert set(Dataroot("/var/rads").cycle_paths("uv")) == set()

    def test_cycle_paths_with_satellite_and_phase(self, dataroot):
        assert set(Dataroot("/var/rads").cycle_paths("ab", "1")) == {
            Path("/var/rads/ab/1/c001")
        }
        assert set(Dataroot("/var/rads").cycle_paths("ab", "a")) == {
            Path("/var/rads/ab/a/c002")
        }
        assert set(Dataroot("/var/rads").cycle_paths("ab", "2")) == {
            Path("/var/rads/ab/2/c003")
        }
        assert set(Dataroot("/var/rads").cycle_paths("xy", "a")) == {
            Path("/var/rads/xy/a/c447"),
            Path("/var/rads/xy/a/c448"),
        }

    def test_cycle_paths_with_satellite_and_invalid_phase(self, dataroot):
        assert set(Dataroot("/var/rads").cycle_paths("xy", "b")) == set()

    def test_passes(self, dataroot):
        assert set(Dataroot("/var/rads").passes("ab", "1", 1)) == {1, 2}
        assert set(Dataroot("/var/rads").passes("ab", "a", 2)) == {1, 2, 3, 4}
        assert set(Dataroot("/var/rads").passes("ab", "2", 3)) == {
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
        }
        assert set(Dataroot("/var/rads").passes("xy", "a", 447)) == {
            10,
            11,
            12,
            13,
            15,
            16,
        }
        assert set(Dataroot("/var/rads").passes("xy", "a", 448)) == {1, 2, 3}

    def test_passes_with_invalid_satellite(self, dataroot):
        assert set(Dataroot("/var/rads").passes("uv", "1", 1)) == set()

    def test_passes_with_invalid_phase(self, dataroot):
        assert set(Dataroot("/var/rads").passes("xy", "2", 1)) == set()

    def test_passes_with_invalid_cycle(self, dataroot):
        assert set(Dataroot("/var/rads").passes("xy", "1", 999)) == set()

    def test_pass_files(self, dataroot):
        assert set(Dataroot("/var/rads").pass_files()) == {
            Path("/var/rads/ab/1/c001/abp0001c001.nc"),
            Path("/var/rads/ab/1/c001/abp0002c001.nc"),
            Path("/var/rads/ab/a/c002/abp0001c002.nc"),
            Path("/var/rads/ab/a/c002/abp0002c002.nc"),
            Path("/var/rads/ab/a/c002/abp0003c002.nc"),
            Path("/var/rads/ab/a/c002/abp0004c002.nc"),
            Path("/var/rads/ab/2/c003/abp0001c003.nc"),
            Path("/var/rads/ab/2/c003/abp0002c003.nc"),
            Path("/var/rads/ab/2/c003/abp0003c003.nc"),
            Path("/var/rads/ab/2/c003/abp0004c003.nc"),
            Path("/var/rads/ab/2/c003/abp0005c003.nc"),
            Path("/var/rads/ab/2/c003/abp0006c003.nc"),
            Path("/var/rads/ab/2/c003/abp0007c003.nc"),
            Path("/var/rads/ab/2/c003/abp0008c003.nc"),
            Path("/var/rads/xy/a/c447/xyp0010c447.nc"),
            Path("/var/rads/xy/a/c447/xyp0011c447.nc"),
            Path("/var/rads/xy/a/c447/xyp0012c447.nc"),
            Path("/var/rads/xy/a/c447/xyp0013c447.nc"),
            Path("/var/rads/xy/a/c447/xyp0015c447.nc"),
            Path("/var/rads/xy/a/c447/xyp0016c447.nc"),
            Path("/var/rads/xy/a/c448/xyp0001c448.nc"),
            Path("/var/rads/xy/a/c448/xyp0002c448.nc"),
            Path("/var/rads/xy/a/c448/xyp0003c448.nc"),
        }

    def test_pass_files_with_satellite(self, dataroot):
        assert set(Dataroot("/var/rads").pass_files("ab")) == {
            Path("/var/rads/ab/1/c001/abp0001c001.nc"),
            Path("/var/rads/ab/1/c001/abp0002c001.nc"),
            Path("/var/rads/ab/a/c002/abp0001c002.nc"),
            Path("/var/rads/ab/a/c002/abp0002c002.nc"),
            Path("/var/rads/ab/a/c002/abp0003c002.nc"),
            Path("/var/rads/ab/a/c002/abp0004c002.nc"),
            Path("/var/rads/ab/2/c003/abp0001c003.nc"),
            Path("/var/rads/ab/2/c003/abp0002c003.nc"),
            Path("/var/rads/ab/2/c003/abp0003c003.nc"),
            Path("/var/rads/ab/2/c003/abp0004c003.nc"),
            Path("/var/rads/ab/2/c003/abp0005c003.nc"),
            Path("/var/rads/ab/2/c003/abp0006c003.nc"),
            Path("/var/rads/ab/2/c003/abp0007c003.nc"),
            Path("/var/rads/ab/2/c003/abp0008c003.nc"),
        }
        assert set(Dataroot("/var/rads").pass_files("xy")) == {
            Path("/var/rads/xy/a/c447/xyp0010c447.nc"),
            Path("/var/rads/xy/a/c447/xyp0011c447.nc"),
            Path("/var/rads/xy/a/c447/xyp0012c447.nc"),
            Path("/var/rads/xy/a/c447/xyp0013c447.nc"),
            Path("/var/rads/xy/a/c447/xyp0015c447.nc"),
            Path("/var/rads/xy/a/c447/xyp0016c447.nc"),
            Path("/var/rads/xy/a/c448/xyp0001c448.nc"),
            Path("/var/rads/xy/a/c448/xyp0002c448.nc"),
            Path("/var/rads/xy/a/c448/xyp0003c448.nc"),
        }

    def test_pass_files_with_satellite_and_phase(self, dataroot):
        assert set(Dataroot("/var/rads").pass_files("ab", "1")) == {
            Path("/var/rads/ab/1/c001/abp0001c001.nc"),
            Path("/var/rads/ab/1/c001/abp0002c001.nc"),
        }
        assert set(Dataroot("/var/rads").pass_files("ab", "a")) == {
            Path("/var/rads/ab/a/c002/abp0001c002.nc"),
            Path("/var/rads/ab/a/c002/abp0002c002.nc"),
            Path("/var/rads/ab/a/c002/abp0003c002.nc"),
            Path("/var/rads/ab/a/c002/abp0004c002.nc"),
        }
        assert set(Dataroot("/var/rads").pass_files("ab", "2")) == {
            Path("/var/rads/ab/2/c003/abp0001c003.nc"),
            Path("/var/rads/ab/2/c003/abp0002c003.nc"),
            Path("/var/rads/ab/2/c003/abp0003c003.nc"),
            Path("/var/rads/ab/2/c003/abp0004c003.nc"),
            Path("/var/rads/ab/2/c003/abp0005c003.nc"),
            Path("/var/rads/ab/2/c003/abp0006c003.nc"),
            Path("/var/rads/ab/2/c003/abp0007c003.nc"),
            Path("/var/rads/ab/2/c003/abp0008c003.nc"),
        }
        assert set(Dataroot("/var/rads").pass_files("xy", "a")) == {
            Path("/var/rads/xy/a/c447/xyp0010c447.nc"),
            Path("/var/rads/xy/a/c447/xyp0011c447.nc"),
            Path("/var/rads/xy/a/c447/xyp0012c447.nc"),
            Path("/var/rads/xy/a/c447/xyp0013c447.nc"),
            Path("/var/rads/xy/a/c447/xyp0015c447.nc"),
            Path("/var/rads/xy/a/c447/xyp0016c447.nc"),
            Path("/var/rads/xy/a/c448/xyp0001c448.nc"),
            Path("/var/rads/xy/a/c448/xyp0002c448.nc"),
            Path("/var/rads/xy/a/c448/xyp0003c448.nc"),
        }

    def test_pass_files_with_satellite_phase_and_cycle(self, dataroot):
        assert set(Dataroot("/var/rads").pass_files("ab", "1", 1)) == {
            Path("/var/rads/ab/1/c001/abp0001c001.nc"),
            Path("/var/rads/ab/1/c001/abp0002c001.nc"),
        }
        assert set(Dataroot("/var/rads").pass_files("ab", "a", 2)) == {
            Path("/var/rads/ab/a/c002/abp0001c002.nc"),
            Path("/var/rads/ab/a/c002/abp0002c002.nc"),
            Path("/var/rads/ab/a/c002/abp0003c002.nc"),
            Path("/var/rads/ab/a/c002/abp0004c002.nc"),
        }
        assert set(Dataroot("/var/rads").pass_files("ab", "2", 3)) == {
            Path("/var/rads/ab/2/c003/abp0001c003.nc"),
            Path("/var/rads/ab/2/c003/abp0002c003.nc"),
            Path("/var/rads/ab/2/c003/abp0003c003.nc"),
            Path("/var/rads/ab/2/c003/abp0004c003.nc"),
            Path("/var/rads/ab/2/c003/abp0005c003.nc"),
            Path("/var/rads/ab/2/c003/abp0006c003.nc"),
            Path("/var/rads/ab/2/c003/abp0007c003.nc"),
            Path("/var/rads/ab/2/c003/abp0008c003.nc"),
        }
        assert set(Dataroot("/var/rads").pass_files("xy", "a", 447)) == {
            Path("/var/rads/xy/a/c447/xyp0010c447.nc"),
            Path("/var/rads/xy/a/c447/xyp0011c447.nc"),
            Path("/var/rads/xy/a/c447/xyp0012c447.nc"),
            Path("/var/rads/xy/a/c447/xyp0013c447.nc"),
            Path("/var/rads/xy/a/c447/xyp0015c447.nc"),
            Path("/var/rads/xy/a/c447/xyp0016c447.nc"),
        }
        assert set(Dataroot("/var/rads").pass_files("xy", "a", 448)) == {
            Path("/var/rads/xy/a/c448/xyp0001c448.nc"),
            Path("/var/rads/xy/a/c448/xyp0002c448.nc"),
            Path("/var/rads/xy/a/c448/xyp0003c448.nc"),
        }

    def test_pass_file(self, dataroot):
        assert Dataroot("/var/rads").pass_file("ab", "1", 1, 1) == Path(
            "/var/rads/ab/1/c001/abp0001c001.nc"
        )
        assert Dataroot("/var/rads").pass_file("ab", "1", 1, 2) == Path(
            "/var/rads/ab/1/c001/abp0002c001.nc"
        )
        assert Dataroot("/var/rads").pass_file("xy", "a", 447, 13) == Path(
            "/var/rads/xy/a/c447/xyp0013c447.nc"
        )

    def test_pass_file_with_missing_file(self, dataroot):
        with pytest.raises(FileNotFoundError):
            Dataroot("/var/rads").pass_file("xy", "a", 447, 14)
        with pytest.raises(FileNotFoundError):
            Dataroot("/var/rads").pass_file("xy", "a", 449, 10)
        with pytest.raises(FileNotFoundError):
            Dataroot("/var/rads").pass_file("xy", "b", 449, 10)
        with pytest.raises(FileNotFoundError):
            Dataroot("/var/rads").pass_file("uv", "b", 449, 10)

    def test_passindex_files(self, dataroot):
        assert set(Dataroot("/var/rads").passindex_files()) == {
            Path("/var/rads/ab/1/c001/.passindex"),
            Path("/var/rads/ab/a/c002/.passindex"),
            Path("/var/rads/ab/2/c003/.passindex"),
            Path("/var/rads/xy/a/c447/.passindex"),
            Path("/var/rads/xy/a/c448/.passindex"),
        }

    def test_passindex_files_with_satellite(self, dataroot):
        assert set(Dataroot("/var/rads").passindex_files("ab")) == {
            Path("/var/rads/ab/1/c001/.passindex"),
            Path("/var/rads/ab/a/c002/.passindex"),
            Path("/var/rads/ab/2/c003/.passindex"),
        }
        assert set(Dataroot("/var/rads").passindex_files("xy")) == {
            Path("/var/rads/xy/a/c447/.passindex"),
            Path("/var/rads/xy/a/c448/.passindex"),
        }

    def test_passindex_files_with_invalid_satellite(self, dataroot):
        assert set(Dataroot("/var/rads").passindex_files("uv")) == set()

    def test_passindex_files_with_satellite_and_phase(self, dataroot):
        assert set(Dataroot("/var/rads").passindex_files("ab", "1")) == {
            Path("/var/rads/ab/1/c001/.passindex")
        }
        assert set(Dataroot("/var/rads").passindex_files("ab", "a")) == {
            Path("/var/rads/ab/a/c002/.passindex")
        }
        assert set(Dataroot("/var/rads").passindex_files("ab", "2")) == {
            Path("/var/rads/ab/2/c003/.passindex")
        }
        assert set(Dataroot("/var/rads").passindex_files("xy", "a")) == {
            Path("/var/rads/xy/a/c447/.passindex"),
            Path("/var/rads/xy/a/c448/.passindex"),
        }

    def test_passindex_files_with_satellite_and_invalid_phase(self, dataroot):
        assert set(Dataroot("/var/rads").passindex_files("xy", "b")) == set()

    def test_passindex_files_with_satellite_phase_and_cycle(self, dataroot):
        assert set(Dataroot("/var/rads").passindex_files("ab", "1", 1)) == {
            Path("/var/rads/ab/1/c001/.passindex")
        }
        assert set(Dataroot("/var/rads").passindex_files("ab", "a", 2)) == {
            Path("/var/rads/ab/a/c002/.passindex")
        }
        assert set(Dataroot("/var/rads").passindex_files("ab", "2", 3)) == {
            Path("/var/rads/ab/2/c003/.passindex")
        }
        assert set(Dataroot("/var/rads").passindex_files("xy", "a", 447)) == {
            Path("/var/rads/xy/a/c447/.passindex")
        }
        assert set(Dataroot("/var/rads").passindex_files("xy", "a", 448)) == {
            Path("/var/rads/xy/a/c448/.passindex")
        }

    def test_passindex_files_with_satellite_phase_and_invalid_cycle(self, dataroot):
        assert set(Dataroot("/var/rads").passindex_files("xy", "a", 999)) == set()

    def test_passindex_files_with_satellite_and_cycle(self, dataroot):
        assert set(Dataroot("/var/rads").passindex_files("ab", cycle=1)) == {
            Path("/var/rads/ab/1/c001/.passindex")
        }
        assert set(Dataroot("/var/rads").passindex_files("ab", cycle=2)) == {
            Path("/var/rads/ab/a/c002/.passindex")
        }
        assert set(Dataroot("/var/rads").passindex_files("ab", cycle=3)) == {
            Path("/var/rads/ab/2/c003/.passindex")
        }
        assert set(Dataroot("/var/rads").passindex_files("xy", cycle=447)) == {
            Path("/var/rads/xy/a/c447/.passindex")
        }
        assert set(Dataroot("/var/rads").passindex_files("xy", cycle=448)) == {
            Path("/var/rads/xy/a/c448/.passindex")
        }

    def test_passindex_files_with_satellite_and_invalid_cycle(self, dataroot):
        assert set(Dataroot("/var/rads").passindex_files("xy", cycle=999)) == set()

    def test_passindex_file(self, dataroot):
        assert Dataroot("/var/rads").passindex_file("ab", "1", 1) == Path(
            "/var/rads/ab/1/c001/.passindex"
        )
        assert Dataroot("/var/rads").passindex_file("ab", "1", 1) == Path(
            "/var/rads/ab/1/c001/.passindex"
        )
        assert Dataroot("/var/rads").passindex_file("xy", "a", 447) == Path(
            "/var/rads/xy/a/c447/.passindex"
        )

    def test_passindex_file_with_missing_file(self, dataroot):
        with pytest.raises(FileNotFoundError):
            Dataroot("/var/rads").passindex_file("xy", "a", 449)
        with pytest.raises(FileNotFoundError):
            Dataroot("/var/rads").passindex_file("xy", "b", 447)
        with pytest.raises(FileNotFoundError):
            Dataroot("/var/rads").passindex_file("uv", "b", 449)
