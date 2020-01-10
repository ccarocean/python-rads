"""Dataroot traversal."""

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

from ..exceptions import InvalidDataroot
from ..typing import PathLike

if TYPE_CHECKING:
    _PathLike = os.PathLike[str]
else:
    _PathLike = os.PathLike


__all__ = ["Dataroot"]

_RE_CYCLE = re.compile(r"^c\d\d\d$")


class Dataroot(_PathLike):
    """Representation of a RADS dataroot allowing for easy traversal."""

    def __init__(self, dataroot: PathLike):
        """
        :param dataroot:
            Path to RADS dataroot to build this abstraction for.

        :raises rads.exceptions.InvalidDataroot:
            If the *dataroot* the given/configured *dataroot* is not a valid RADS
            *dataroot*.
        """
        dataroot_ = Path(dataroot).resolve()
        if dataroot_.is_dir() and (dataroot_ / "conf" / "rads.xml").is_file():
            self._path = dataroot_
        else:
            raise InvalidDataroot(f"'{str(dataroot_)}' is not a RADS data directory")

    @property
    def path(self) -> Path:
        """Absolute path to the dataroot."""
        return self._path

    def __str__(self) -> str:
        """Get string giving absolute path to the datatroot.

        :return:
            Absolute path to dataroot.
        """
        return str(self._path)

    def __repr__(self) -> str:
        """Get string representation of this object.

        This can be round tripped:

        .. code-block:: python

            eval(repr(dataroot))

        :return:
            String representation of this object.
        """
        return f"{self.__class__.__qualname__}({repr(str(self._path))})"

    def __fspath__(self) -> str:
        """os.fspath interface.

        :return:
            Absolute path to dataroot.
        """
        return str(self._path)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Dataroot) and self._path == other._path

    def __ne__(self, other: Any) -> bool:
        return not isinstance(other, Dataroot) or self._path != other._path

    def satellites(self) -> Iterator[str]:
        """Get satellite names in the dataroot.

        :return:
            Iterator of 2 character names of satellites in the dataroot.
        """
        for path in self.satellite_paths():
            yield path.name

    def satellite_paths(self) -> Iterator[Path]:
        """Get absolute paths to satellite directories in the dataroot.

        :return:
            Iterator of absolute paths to satellite directories in the dataroot.
        """
        for path in self._path.iterdir():
            satellite = path.name
            if path.is_dir() and len(satellite) == 2 and satellite.isalnum():
                yield path

    def phases(self, satellite: str) -> Iterator[str]:
        """Get phase names for the given satellite.

        If the given satellite does not exist or does not have any phases the
        returned iterator will be of length 0.

        :param satellite:
            2 character satellite name to get phase names for.

        :return:
            Iterator of single character phase names for the given satellite.
        """
        for path in self.phase_paths(satellite):
            yield path.name

    def phase_paths(self, satellite: str = "") -> Iterator[Path]:
        """Get absolute paths to phase directories in the dataroot.

        If the given satellite does not exist or does not have any phases the
        returned iterator will be of length 0.

        :param satellite:
            2 character satellite name to get phase paths for, defaults to all
            satellites.

        :return:
            Iterator of absolute paths to phase directories in the dataroot,
            optionally for the given satellite.
        """
        for satellite_ in [satellite] if satellite else self.satellites():
            try:
                for path in (self._path / satellite_).iterdir():
                    phase = path.name
                    # phase must:
                    #   * be a directory
                    #   * be a single alphanumeric character
                    #   * not be a symlink to another phase
                    if (
                        path.is_dir()
                        and len(phase) == 1
                        and phase.isalnum()
                        and (
                            not path.is_symlink()
                            or path.resolve().parent != path.parent.resolve()
                        )
                    ):
                        yield path
            except FileNotFoundError:
                pass

    def cycles(self, satellite: str, phase: str = "") -> Iterator[int]:
        """Get cycles for the given satellite and phase.

        If the given satellite and/or phase does not exist or does not have any
        cycles the returned iterator will be of length 0.

        :param satellite:
            2 character satellite name to get cycles for.
        :param phase:
            1 character phase name to get cycles for.

        :return:
            Iterator of cycle numbers for the given satellite and cycle.
        """
        for path in self.cycle_paths(satellite, phase):
            yield int(path.name[1:])

    def cycle_paths(self, satellite: str = "", phase: str = "") -> Iterator[Path]:
        """Get absolute paths to cycle directories in the dataroot.

        If the given satellite and/or phase does not exist or does not have any
        cycles the returned iterator will be of length 0.

        :param satellite:
            2 character satellite name to get cycle paths for, defaults to all
            satellites.
        :param phase:
            1 character phase name to get cycle paths for, defaults to all
            phases.

        :return:
            Iterator of absolute paths to cycle directories in the dataroot,
            optionally for the given satellite and/or phase.
        """
        for satellite_ in [satellite] if satellite else self.satellites():
            satellite_path = self._path / satellite_
            for phase_ in [phase] if phase else self.phases(satellite_):
                try:
                    for path in (satellite_path / phase_).iterdir():
                        cycle = path.name
                        if path.is_dir and _RE_CYCLE.match(cycle):
                            yield path
                except FileNotFoundError:
                    pass

    def passes(self, satellite: str, phase: str, cycle: int) -> Iterator[int]:
        """Get pass numbers for the given satellite, phase, and cycle number.

        If the given satellite, phase, and/or cycle does not exist or does not
        have any passes the returned iterator will be of length 0.

        :param satellite:
            2 character satellite name.
        :param phase:
            1 character phase name.
        :param cycle:
            Cycle number, between 0 and 999.

        :return:
            Iterator of pass numbers for the given satellite, phase, and cycle.
        """
        for path in self.pass_files(satellite, phase, cycle):
            yield int(path.name[3:7])

    def pass_files(
        self, satellite: str = "", phase: str = "", cycle: int = -1
    ) -> Iterator[Path]:
        """Get pass files for the given satellite, phase, and cycle.

        If the given satellite, phase, and/or cycle does not exist or does not
        have any passes the returned iterator will be of length 0.

        :param satellite:
            2 character satellite name, defaults to all satellites.
        :param phase:
            1 character phase name, defaults to all phases.
        :param cycle:
            Cycle number, between 0 and 999, defaults to all cycles.

        :return:
            Iterator of absolute paths to pass files for the given satellite,
            phase, and cycle number.
        """
        for satellite_ in [satellite] if satellite else self.satellites():
            satellite_path = self._path / satellite_
            for phase_ in [phase] if phase else self.phases(satellite_):
                phase_path = satellite_path / phase_
                for cycle_ in (
                    [cycle] if cycle >= 0 else self.cycles(satellite_, phase_)
                ):
                    cycle_string = f"c{cycle_:03d}"
                    try:
                        for path in (phase_path / cycle_string).iterdir():
                            if (
                                path.is_file()
                                and path.name[0:2] == satellite_
                                and path.name[7:11] == cycle_string
                                and path.suffix == ".nc"
                            ):
                                yield path
                    except FileNotFoundError:
                        pass

    def pass_file(self, satellite: str, phase: str, cycle: int, pass_: int) -> Path:
        """Get path to a pass file give satellite, phase, cycle, and pass.

        :param satellite:
            2 character satellite name.
        :param phase:
            1 character phase name.
        :param cycle:
            Cycle number, between 0 and 999.
        :param pass_:
            Pass number, between 0 and 9999.

        :return:
            Path to the associated pass data file.

        :raises FileExistsError:
            If the pass file does not exist.
        """
        filename = f"{satellite}p{pass_:04d}c{cycle:03d}.nc"
        path = self._path / satellite / phase / f"c{cycle:03d}" / filename
        if path.is_file():
            return path
        raise FileNotFoundError(f"{path} does not exist")

    def passindex_files(
        self, satellite: str = "", phase: str = "", cycle: int = -1
    ) -> Iterator[Path]:
        """Get pass files for the given satellite, phase, and cycle.

        If the given satellite, phase, and/or cycle does not exist or does not
        have any passes the returned iterator will be of length 0.

        :param satellite:
            2 character satellite name, defaults to all satellites.
        :param phase:
            1 character phase name, defaults to all phases.
        :param cycle:
            Cycle number, between 0 and 999, defaults to all cycles.

        :return:
            Iterator of absolute paths to passindex files for the given
            satellite, phase, and cycle number.
        """
        for satellite_ in [satellite] if satellite else self.satellites():
            satellite_path = self._path / satellite_
            for phase_ in [phase] if phase else self.phases(satellite_):
                phase_path = satellite_path / phase_
                for cycle_ in (
                    [cycle] if cycle >= 0 else self.cycles(satellite_, phase_)
                ):
                    try:
                        for path in (phase_path / f"c{cycle_:03d}").iterdir():
                            if path.name == ".passindex":
                                yield path
                    except FileNotFoundError:
                        pass

    def passindex_file(self, satellite: str, phase: str, cycle: int) -> Path:
        """Get pass file for the given satellite, phase, and cycle.

        If the given satellite, phase, and/or cycle does not exist a
        have any passes the returned iterator will be of length 0.

        :param satellite:
            2 character satellite name.
        :param phase:
            1 character phase name.
        :param cycle:
            Cycle number, between 0 and 999.

        :return:
            Absolute path to the pass
            Iterator of absolute paths to passindex files for the given
            satellite, phase, and cycle number.

        :raises FileNotFoundError:
            If there is no passindex file for the given satellite, phase, and cycle.
        """
        path = self._path / satellite / phase / f"c{cycle:03d}" / ".passindex"
        if path.is_file():
            return path
        raise FileNotFoundError(f"{path} does not exist")
