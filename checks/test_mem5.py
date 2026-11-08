"""Session 3, ticket 5: personal data never kept, and a delete that cascades by user_id and says what is left."""

from launchkit.agents.main_agent import build_catalogue, build_main_agent
from launchkit.agents.prompt import ContextBuilder
from launchkit.brands.workspace import load_workspace
from launchkit.memory.chat_history import session_db
from launchkit.memory.forget import delete_user, still_naming
from launchkit.memory.long_term import user_memories
from launchkit.memory.memory_view import reset_to_snapshot
from launchkit.memory.scope import held_back
from launchkit.trace import Trace

NO = lambda name, inputs: False
PHONE, TOKEN = "07700 900461", "lkdemo-board-token-7f3a91c2e8b4d605"


def test_a_phone_number_and_a_token_are_personal_data_and_a_date_is_not(settings):
    assert held_back(f"Call Callum on {PHONE}.", settings).startswith("personal data")
    assert held_back(f"The board key is {TOKEN}.", settings).startswith("personal data")
    assert held_back("Maya reviews drafts on 2026-03-31 and on Fridays.", settings) is None


def test_the_snapshots_phone_number_and_token_never_reach_the_prompt(settings, good):
    """They are still in the snapshot's rows (the delete is what removes them), but never loaded."""
    reset_to_snapshot(settings)
    assert any(PHONE in m.memory for m in user_memories(session_db(settings), "maya"))
    ws = load_workspace("harbor", settings, Trace())
    prompt = build_main_agent(ws, ContextBuilder(settings.budgets), good, settings, Trace(), build_catalogue(settings, Trace(), NO), user_id="maya").system_message
    assert PHONE not in prompt and TOKEN not in prompt


def test_a_note_with_personal_data_is_refused_before_anyone_is_asked(settings):
    asked = []
    reply = build_catalogue(settings, Trace(), lambda name, plan: asked.append(name) or True).make_run_tool()("save_memory", {"note": f"Customer Callum Ferris, {PHONE}."})
    assert asked == [] and "personal data" in reply


def test_the_delete_cascades_and_leaves_everyone_else(settings):
    """Memories, summaries and decision log by user_id, and a learning they proposed by its source tag. Maya is untouched."""
    reset_to_snapshot(settings)
    build_catalogue(settings, Trace(), lambda name, plan: True, user="agency-manager").make_run_tool()("save_learning", {"title": "Client days", "learning": "Files go to clients on Mondays."})
    removed = dict(delete_user(settings, "agency-manager", apply=True))
    assert removed["memories"] == 18 and removed["conversations and their summaries"] == 2 and removed["shared learnings they proposed (tag source:agency-manager)"] == 1
    assert user_memories(session_db(settings), "agency-manager") == [] and len(user_memories(session_db(settings), "maya")) == 39


def test_what_still_names_her_is_listed(settings):
    """The learning seeded before the fix carries no source, so the cascade cannot find it by id: the search shows it."""
    reset_to_snapshot(settings)
    delete_user(settings, "agency-manager", apply=True)
    left = still_naming(settings, "agency-manager", ["Dana Whitlock"])
    assert left and all("Dana Whitlock's tip" in line for line in left)


def test_without_apply_nothing_is_deleted(settings):
    reset_to_snapshot(settings)
    delete_user(settings, "agency-manager", apply=False)
    assert len(user_memories(session_db(settings), "agency-manager")) == 18
