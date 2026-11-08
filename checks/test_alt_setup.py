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


def test_alder_exists_with_the_agency_manager():
    """setup: the Alder brand exists, and Dana the agency manager works at Alder and at Harbor"""
    from launchkit.brands.users import list_logins
    from launchkit.settings import settings

    logins = {(l["workspace_id"], l["user_id"]): l for l in list_logins(settings)}
    assert ("alder", "dana") in logins and logins[("alder", "dana")]["role"] == "agency manager"
    assert ("harbor", "dana") in logins
    assert logins[("alder", "dana")]["label"] == "Dana · Alder"


def test_the_seeded_database_holds_the_story(tmp_path):
    """setup: the seed holds the backwards rule, eleven navy rows, two open warranties, Dana's rows, a phone number, a token, a web learning and a summary"""
    import shutil
    from datetime import date

    from launchkit.memory.brand_facts import BrandFacts
    from launchkit.memory.store import MemoryStore
    from launchkit.trace import Trace

    seed = cli.ROOT / "samples" / "memory" / "seed.db"
    copy = tmp_path / "seed.db"
    shutil.copyfile(seed, copy)
    store = MemoryStore(str(copy), "harbor", "maya", Trace())
    maya = store.get_user_memories(user_id="maya")
    texts = [r.memory for r in maya]
    assert sum("navy" in t.lower() for t in texts) == 11
    assert any("lifetime guarantee" in t for t in texts)
    assert any("555-0142" in t for t in texts) and any("sk-live" in t for t in texts)
    dana = [r.memory for r in store.get_user_memories(user_id="dana")]
    assert any("lifetime guarantee" in t for t in dana)
    learning = store.get_user_memories(user_id="harbor:brand")
    assert any("source:web" in (r.topics or []) for r in learning)
    assert any("555-0142" in r.memory for r in learning)
    assert all("brand:harbor" in (r.topics or []) for r in maya + store.get_user_memories(user_id="dana"))
    assert any("topic:photography" in (r.topics or []) for r in maya)
    warranties = [f for f in BrandFacts(str(copy)).current("harbor", date(2026, 11, 1)) if f.subject == "warranty"]
    assert sorted(f.value for f in warranties) == ["2 years", "5 years"]
    sessions = store.get_sessions(user_id="maya")
    assert any(s.summary and "555-0142" in s.summary.summary for s in sessions)
