"""Setup checks for the Session 3 alternative branch: the commands, the brands and the seeded database a fresh clone needs."""

from launchkit import cli


def test_setup_command_exists():
    """setup: `launchkit setup` is a command"""
    assert "setup" in cli.COMMANDS


def test_check_knows_the_alt_names():
    """setup: `launchkit check` accepts alt-setup, alt-ready, alt-build-a, alt-build-b and alt-build-c"""
    for name in ("alt-setup", "alt-ready", "alt-build-a", "alt-build-b", "alt-build-c"):
        assert name in cli.CHECK_NAMES


def test_check_maps_an_alt_name_to_its_test_file():
    """setup: check alt-build-a runs checks/test_alt_build_a.py"""
    assert cli.check_targets("alt-build-a") == [cli.ROOT / "checks" / "test_alt_build_a.py"]
    assert cli.check_targets("alt") == [cli.ROOT / "checks" / "test_alt_setup.py", cli.ROOT / "checks" / "test_alt_ready.py"]
