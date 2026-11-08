"""Build B, who writes, who reads, how long: tickets 4, 5 and 6. These pass once the slots are built, on the answer branches.

The fork tests select the path the answer branch took through FORK in conftest.
"""

import pytest
from agno.db.schemas.memory import UserMemory

from launchkit.memory.store import MemoryStore
from launchkit.memory.write_door import decide_save
from launchkit.settings import settings
from launchkit.trace import Trace

pytestmark = pytest.mark.answer


def test_a_row_from_a_web_page_never_reaches_memory(tmp_path):
    """build b, ticket 4: a save whose source is a web page is refused at the door and leaves a trace line"""
    trace = Trace()
    store = MemoryStore(str(tmp_path / "s.db"), "harbor", "research-helper", trace, decide=lambda text, topics: decide_save(text, topics, approve=lambda n, i: "Just me", settings=settings))
    store.upsert_user_memory(UserMemory(memory="a lifetime guarantee sells", user_id="harbor:brand", topics=["scope:brand:harbor", "source:web"]))
    assert store.get_user_memories(user_id="harbor:brand") == []
    assert any(e.kind == "memory_refused" for e in trace.events)


def test_the_research_helper_has_no_save_tool(tmp_path):
    """build b, ticket 4: the helper keeps search_web and loses its save tool"""
    from dataclasses import replace

    from launchkit.adapters.fakes import GoodModel
    from launchkit.orchestration.research_team import build_research_agent

    store = MemoryStore(str(tmp_path / "s.db"), "harbor", "research-helper", Trace())
    agent = build_research_agent(GoodModel(), replace(settings, search="saved"), Trace(), store=store)
    assert [getattr(t, "__name__", "") for t in agent.tools] == ["search_web"]


@pytest.mark.fork_a
def test_the_ask_door_maps_the_three_answers():
    """build b, fork 1 path A: Just me keeps it for the person, Everyone keeps it for the brand, Don't keep refuses"""
    answers = iter(["Just me", "Everyone at the brand", "Don't keep"])
    approve = lambda name, inputs: next(answers)  # noqa: E731
    assert decide_save("prefers own photos", ["kind:preference"], approve, settings) == (True, "user")
    assert decide_save("we never say lifetime guarantee", ["kind:preference"], approve, settings) == (True, "brand")
    assert decide_save("yes, attach them", ["kind:fact"], approve, settings) == (False, None)


@pytest.mark.fork_b
def test_the_confidence_door_keeps_a_row_at_point_seven(monkeypatch):
    """build b, fork 1 path B: a row the model is at least 0.7 sure of is kept without asking; a less sure one is not"""
    from launchkit.memory import write_door

    monkeypatch.setattr(write_door, "confidence", lambda text, settings: 0.9 if "never" in text or "prefer" in text else 0.4)
    never_asked = lambda name, inputs: pytest.fail("the confidence door must not ask")  # noqa: E731
    assert decide_save("prefers own photos", ["kind:preference"], never_asked, settings).keep is True
    assert decide_save("yes, attach them", ["kind:fact"], never_asked, settings).keep is False
