import pytest  # type: ignore

from rads import get_dataroot, load_config
from rads.exceptions import InvalidDataroot


def test_for_dataroot():
    try:
        get_dataroot()
    except InvalidDataroot:
        return False
    return True


if not test_for_dataroot():
    pytest.skip(
        "skipping integration tests (no RADS dataroot)", allow_module_level=True
    )


def test_load_config():
    config = load_config()
    sats = [
        "2a",
        "3a",
        "3b",
        "c2",
        "e1",
        "e2",
        "g1",
        "gs",
        "j1",
        "j2",
        "j3",
        "n1",
        "pn",
        "tx",
        "sa",
    ]
    for sat in sats:
        assert sat in config.satellites
        assert "sla" in config.satellites[sat].variables
