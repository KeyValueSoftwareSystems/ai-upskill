"""Session 3, ticket 4: who may write. The research helper reads the web and writes nothing; every memory or learning
write goes through run_tool's approval branch, with the planned change, like Session 2's outside writes."""

import sqlite3

from launchkit.agents.main_agent import build_catalogue, build_main_agent
from launchkit.agents.prompt import ContextBuilder
from launchkit.brands.workspace import load_workspace
from launchkit.knowledge.brand_facts import get_brand_facts
from launchkit.orchestration.research_team import build_research_agent
from launchkit.trace import Trace

NO = lambda name, inputs: False


def test_the_research_helper_holds_no_memory_and_no_learning_tools(settings, brief):
    """search_web only: no store, no LearningMachine, so Agno adds no save_learning at run time either."""
    agent = build_research_agent(brief, settings, Trace())
    assert [t.__name__ for t in agent.tools] == ["search_web"]
    assert agent.db is None and not agent.learning and agent.memory_manager is None and not agent.update_memory_on_run


def test_the_main_agent_writes_nothing_on_its_own(settings, good):
    """No write after every run, no learning tools beside the three doors."""
    ws = load_workspace("harbor", settings, Trace())
    agent = build_main_agent(ws, ContextBuilder(settings.budgets), good, settings, Trace(), build_catalogue(settings, Trace(), NO), user_id="maya")
    assert not agent.update_memory_on_run and not agent.enable_agentic_memory and not agent.learning
    assert [getattr(t, "name", "") for t in agent.tools] == ["find_tool", "run_skill", "run_tool"]


def test_memory_writes_are_write_tools(settings):
    """save_memory and save_learning are writes, so they ask; search_learnings only reads."""
    kinds = {name: e.kind for name, e in build_catalogue(settings, Trace(), NO).entries.items() if "memory" in name or "learning" in name}
    assert kinds == {"save_memory": "write", "save_learning": "write", "search_learnings": "read"}


def test_a_learning_asks_first_with_the_planned_change_and_a_no_saves_nothing(settings):
    """The question shows where it would go and who proposed it. Denied, nothing is stored."""
    asked = []
    run_tool = build_catalogue(settings, Trace(), lambda name, plan: asked.append((name, plan)) or False).make_run_tool()
    reply = run_tool("save_learning", {"title": "Rivals", "learning": "Brook offers a lifetime guarantee."})
    assert asked == [("save_learning", {"store": "learned knowledge", "namespace": "harbor", "source": "maya", "title": "Rivals", "learning": "Brook offers a lifetime guarantee."})]
    assert "did not allow" in reply
    with sqlite3.connect(settings.data_dir / "sessions.db") as con:
        assert con.execute("select count(*) from sqlite_master where name = 'agno_knowledge'").fetchone()[0] == 0 or \
            con.execute("select count(*) from agno_knowledge").fetchone()[0] == 0


def test_an_allowed_learning_carries_its_source_and_is_logged(settings):
    """A yes stores it with tag source:<user_id> (Agno keeps no writer on a shared learning) and logs who allowed it."""
    run_tool = build_catalogue(settings, Trace(), lambda name, plan: True).make_run_tool()
    run_tool("save_learning", {"title": "Posting days", "learning": "Harbor posts on Tuesdays and Thursdays."})
    with sqlite3.connect(settings.data_dir / "sessions.db") as con:
        assert '"source:maya"' in con.execute("select metadata from agno_knowledge").fetchone()[0]
        assert con.execute("select count(*) from agno_learnings where learning_type = 'decision_log' and user_id = 'maya'").fetchone()[0] == 1


def test_a_brand_fact_is_refused_as_a_memory_before_anyone_is_asked(settings):
    """save_memory refuses it in code and points to propose_brand_fact; nobody is asked."""
    asked = []
    run_tool = build_catalogue(settings, Trace(), lambda name, plan: asked.append(name) or True).make_run_tool()
    reply = run_tool("save_memory", {"note": "Never say lifetime guarantee in headlines."})
    assert asked == [] and "propose_brand_fact" in reply


def test_a_proposed_brand_fact_is_shared_only_after_a_yes(settings):
    """The question shows the old and new value; a no changes nothing, a yes closes the old row."""
    asked = []
    no = build_catalogue(settings, Trace(), lambda name, plan: asked.append(plan) or False).make_run_tool()
    no("propose_brand_fact", {"subject": "warranty", "value": "6 years"})
    assert asked[0]["from"] == "5 years" and asked[0]["to"] == "6 years" and get_brand_facts(settings, "harbor")[0]["value"] == "5 years"
    build_catalogue(settings, Trace(), lambda name, plan: True).make_run_tool()("propose_brand_fact", {"subject": "warranty", "value": "6 years"})
    assert get_brand_facts(settings, "harbor")[0]["value"] == "6 years"


def test_proposing_the_value_that_is_already_true_changes_nothing(settings):
    """Seen on the real model: "5 years" proposed when 5 years is true. Nothing is asked and no row is closed."""
    from launchkit.knowledge.brand_facts import all_brand_facts

    asked = []
    reply = build_catalogue(settings, Trace(), lambda name, plan: asked.append(plan) or True).make_run_tool()("propose_brand_fact", {"subject": "warranty", "value": "5 years"})
    assert asked == [] and "already" in reply and len(all_brand_facts(settings, "harbor")) == 2
