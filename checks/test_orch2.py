from launchkit.harness.agent import build_research_agent
from launchkit.harness.main import run_main
from launchkit.harness.research import make_research_entries
from launchkit.harness.trace import Trace

ASK = "How are Northline, Ridgeway, Stillwater, Kestrel and Alder Co. launching bottles this season? One paragraph each."
FIVE = ["Northline", "Ridgeway", "Stillwater", "Kestrel", "Alder Co."]
PAGE_LINE = "Carry the mountain home"
NO = lambda name, inputs: False


def tool_names(agent) -> list[str]:
    return [getattr(t, "__name__", getattr(t, "name", "")) for t in agent.tools]


def test_the_research_agent_holds_only_search_web(settings, brief):
    """The research agent has search_web and nothing else: no board, no run_tool. And no session store, no chat history."""
    agent = build_research_agent(brief, settings, Trace())
    assert agent is not None, "build_research_agent still returns None"
    assert tool_names(agent) == ["search_web"]
    assert agent.db is None and not agent.add_history_to_context


def test_research_and_research_many_are_read_tools(settings, brief):
    """research and research_many go into the catalogue as ordinary read tools, so run_tool runs them without asking Maya."""
    kinds = {e.name: e.kind for e in make_research_entries(brief, settings, Trace())}
    assert kinds == {"research": "read", "research_many": "read"}


def test_the_research_agent_sees_none_of_mayas_chat(settings, request_for, brief):
    """The research agent sees its brief and its pages, never Maya's chat."""
    run_main(request_for(text="Morning! Concepts are due Friday, so keep it tight."), settings=settings, model=brief, approve=NO)
    run_main(request_for(text=ASK), settings=settings, model=brief, approve=NO)
    research_views = [view for role, view in brief.seen if role == "research"]
    assert len(research_views) >= 5
    assert not any("keep it tight" in view for view in research_views)
    assert any("keep it tight" in view for role, view in brief.seen if role == "main")


def test_the_main_agent_holds_the_reports_not_the_pages(settings, request_for, brief):
    """The pages stay in the research agents' views. The main agent gets five short reports, and the next turn carries no pages."""
    result = run_main(request_for(text=ASK), settings=settings, model=brief, approve=NO)
    main_views = " ".join(view for role, view in brief.seen if role == "main")
    assert PAGE_LINE not in main_views
    assert any(PAGE_LINE in view for role, view in brief.seen if role == "research")
    assert all(name in result.reply for name in FIVE)
    assert result.view_tokens < 500
    nxt = run_main(request_for(text="Write one headline for the hiker concept."), settings=settings, model=brief, approve=NO)
    assert nxt.history_tokens < 1000


def test_five_briefs_run_side_by_side(slow_search, request_for, brief):
    """Five research agents run at once: with a search that takes 0.4 s, the whole job takes about one search, not five."""
    trace = Trace()
    result = run_main(request_for(text=ASK), settings=slow_search, model=brief, trace=trace, approve=NO)
    assert len(trace.tool_calls("search_web")) == 5
    assert result.seconds < 2 * slow_search.search_delay


def test_reports_come_back_in_the_order_of_the_briefs(settings, brief):
    """research_many hands back one report per brief, in the order the briefs were given."""
    research_many = {e.name: e for e in make_research_entries(brief, settings, Trace())}["research_many"].fn
    reports = research_many(["How is Kestrel launching?", "How is Northline launching?", "How is Stillwater launching?"])
    assert [r.split(":")[0] for r in reports] == ["Kestrel", "Northline", "Stillwater"]
