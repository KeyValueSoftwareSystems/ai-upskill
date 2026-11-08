"""Session 3, ticket 3: scope. A brand is a namespace; a brand fact never rides in a person's memory."""

from launchkit.agents.main_agent import build_catalogue, build_main_agent
from launchkit.agents.prompt import ContextBuilder
from launchkit.brands.workspace import load_workspace
from launchkit.knowledge.brand_facts import get_brand_facts
from launchkit.memory.memory_view import reset_to_snapshot
from launchkit.trace import Trace

NO = lambda name, inputs: False
HARBOR = ("#1f3a5f", "lifetime guarantee", "1080x1350", "sea glass", "warranty")


def prompt_for(settings, model, workspace: str, user: str) -> str:
    ws = load_workspace(workspace, settings, Trace())
    catalogue = build_catalogue(settings, Trace(), NO, ws=ws, user=user)
    return build_main_agent(ws, ContextBuilder(settings.budgets), model, settings, Trace(), catalogue, user_id=user).system_message.lower()


def test_the_agency_managers_harbor_rows_stay_out_of_alder(settings, good):
    """From the snapshot: her Harbor colours, sizes and never-say list are held back; her own preferences still load."""
    reset_to_snapshot(settings)
    memory = prompt_for(settings, good, "alder", "agency-manager").split("# memory", 1)[1]
    assert not [word for word in HARBOR if word in memory]
    assert "bullet-point summaries" in memory


def test_mayas_inverted_rule_and_stale_warranty_are_not_loaded(settings, good):
    """The rows ticket 1 and 2a are about name a brand fact, so they never reach the prompt."""
    reset_to_snapshot(settings)
    memory = prompt_for(settings, good, "harbor", "maya").split("# memory", 1)[1]
    assert "lifetime guarantee" not in memory and "2 years" not in memory and "friday mornings" in memory


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


def test_learnings_are_shared_within_one_brand(settings):
    """A Harbor learning is found on Harbor and not on Alder."""
    harbor = build_catalogue(settings, Trace(), lambda name, plan: True, ws=load_workspace("harbor", settings, Trace()))
    harbor.make_run_tool()("save_learning", {"title": "Posting days", "learning": "Harbor posts on Tuesdays and Thursdays."})
    alder = build_catalogue(settings, Trace(), NO, ws=load_workspace("alder", settings, Trace()), user="agency-manager")
    assert "Tuesdays" in harbor.entries["search_learnings"].fn("posting days")
    assert "Tuesdays" not in alder.entries["search_learnings"].fn("posting days")
