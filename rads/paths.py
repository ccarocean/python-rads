"""All (Py)RADS specific paths."""

from pathlib import Path

from appdirs import AppDirs, system  # type: ignore

from .typing import PathLike

_APPNAME = "pyrads"
_APPDIRS = AppDirs(_APPNAME, appauthor=False, roaming=False)


# Config paths (listed in loading order)
################################################################################


def rads_xml(dataroot: PathLike) -> Path:
    """Path to the main RADS configuration file.

    This will be at `<dataroot>/conf/rads.xml`.

    .. note:

        PyRADS specific XML tags are not allowed in this file.

    :param dataroot:
        Path to the RADS data root.

    :return:
        Path to the main RADS configuration file.
    """
    return Path(dataroot) / "conf" / "rads.xml"


def site_config() -> Path:
    r"""Path to the PyRADS site/system configuration file.

    ================  ================================================
    Operating System  Path
    ================  ================================================
    Mac OS X          /Library/Application Support/pyrads/settings.xml
    Unix              /etc/pyrads
    Windows           C:\ProgramData\pyrads\settings.xml
    ================  ================================================

    .. note:

        RADS, not only PyRADS overrides are allowed in this file.

    :return:
        Path to the PyRADS site/system wide configuration file.
    """
    if system in ("win32", "darwin"):
        return Path(_APPDIRS.site_config_dir)
    # appdirs does not handle site config on linux properly
    return Path("/etc") / _APPNAME / "settings.xml"


def user_xml() -> Path:
    """Path to the user local RADS configuration file.

    This will be at `~/.rads/rads.xml` regardless of operating system.

    .. note:

        PyRADS specific XML tags are not allowed in this file.

    :return:
        Path to the user local RADS configuration file.
    """
    return Path("~/.rads/rads.xml").expanduser()


def user_config() -> Path:
    r"""Path to the PyRADS user local configuration file.

    ================  =====================================================
    Operating System  Path
    ================  =====================================================
    Mac OS X          ~/Library/Preferences/pyrads/settings.xml
    Unix              ~/.config/pyrads/settings.xml
    Windows           C:\Users\<username>\AppData\Local\pyrads\settings.xml
    ================  =====================================================

    .. note:

        RADS, not only PyRADS overrides are allowed in this file.

    :return:
        Path to the PyRADS user local configuration file.
    """
    return Path(_APPDIRS.user_config_dir) / "settings.xml"


def local_xml() -> Path:
    """Path to the local RADS configuration file.

    This will be `rads.xml` in the current directory.

    .. note:

        PyRADS specific XML tags are not allowed in this file.

    :return:
        Path to the local RADS configuration file.
    """
    return Path("rads.xml")


def local_config() -> Path:
    """Path to the local RADS configuration file.

    This will be `pyrads.xml` in the current directory.

    .. note:

        RADS, not only PyRADS overrides are allowed in this file.

    :return:
        Path to the local RADS configuration file.
    """
    return Path("pyrads.xml")


# Cache path
################################################################################


def cache() -> Path:
    """Path to cache directory.

    :return:
        Path to the PyRADS cache directory.
    """
    return Path(_APPDIRS.user_cache_dir)
