"""Session 3, ticket 3: scope. A brand is a namespace; a brand fact never rides in a person's memory."""

from launchkit.agents.main_agent import build_catalogue, build_main_agent
from launchkit.agents.prompt import ContextBuilder
from launchkit.brands.workspace import load_workspace
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
    """The rows tickets 1 and 2 are about name a brand fact, so they never reach the prompt."""
    reset_to_snapshot(settings)
    memory = prompt_for(settings, good, "harbor", "maya").split("# memory", 1)[1]
    assert "lifetime guarantee" not in memory and "2 years" not in memory and "friday mornings" in memory


def test_learnings_are_kept_per_brand(settings, good):
    """The main agent's learnings sit in the brand's namespace, not "global". Until ticket 4 that is its LearningMachine;
    from ticket 4 it is where save_learning writes."""
    ws = load_workspace("alder", settings, Trace())
    catalogue = build_catalogue(settings, Trace(), NO, ws=ws, user="agency-manager")
    agent = build_main_agent(ws, ContextBuilder(settings.budgets), good, settings, Trace(), catalogue, user_id="agency-manager")
    namespace = agent.learning.namespace if agent.learning else catalogue.entries["save_learning"].plan({"title": "t", "learning": "l"})["namespace"]
    assert namespace == "alder"


def test_a_brand_namespace_keeps_learnings_apart(settings):
    """Saved in Harbor's namespace, found on Harbor, not on Alder."""
    from launchkit.memory.long_term import learning_machine

    learning_machine(settings, "harbor").learned_knowledge_store.save(title="Posting days", learning="Harbor posts on Tuesdays and Thursdays.", namespace="harbor")
    assert learning_machine(settings, "harbor").learned_knowledge_store.search("posting days", namespace="harbor")
    assert not learning_machine(settings, "alder").learned_knowledge_store.search("posting days", namespace="alder")
