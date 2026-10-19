import inspect
import re

from launchkit.harness.brand import make_get_brand_details
from launchkit.harness.context import approx_tokens
from launchkit.harness.run import run_request
from launchkit.harness.search import TOP_K, split_by_heading
from launchkit.harness.trace import Trace
from launchkit.harness.workspace import load_workspace

DISHWASHER = "Poster for the Tidal bottle. Mention it's dishwasher-safe."


def chunk_ids(result: str) -> list[str]:
    return re.findall(r"^\[([^\]]+)\]", result, flags=re.M)


def harbor_tool(settings):
    return make_get_brand_details(load_workspace("harbor", settings, Trace()), Trace())


def test_the_guide_is_split_by_heading():
    """Each "## " section is one chunk; a file with no sections is one fact per line."""
    book = split_by_heading("# Book\nIntro.\n\n## Colours\nNavy.\n\n## Lid\nHand-wash only.\n", "brand-book.md")
    assert [(c.id, c.heading, c.text) for c in book] == [
        ("brand-book.md#introduction", "Introduction", "Intro."),
        ("brand-book.md#colours", "Colours", "Navy."),
        ("brand-book.md#lid", "Lid", "Hand-wash only."),
    ]
    facts = split_by_heading("Cold for 24 hours.\n\nLeak-proof lid.\n", "facts.md")
    assert [c.text for c in facts] == ["Cold for 24 hours.", "Leak-proof lid."]


def test_the_tool_takes_a_query(settings):
    """get_brand_details(query): the agent says what it needs to know. Still no workspace argument."""
    params = inspect.signature(harbor_tool(settings)).parameters
    assert list(params) == ["query"]


def test_it_returns_at_most_five_chunks(settings):
    """However broad the question, at most 5 chunks come back, best match first."""
    result = harbor_tool(settings)("poster placement logo headline navy sand print file")
    assert 0 < len(chunk_ids(result)) <= TOP_K == 5


def test_the_dishwasher_copy_is_still_correct(settings, images, trace, request_for, lookup):
    """'Mention it's dishwasher-safe' still says the lid is hand-wash only, from the matching chunk."""
    result = run_request(request_for(text=DISHWASHER), settings=settings, model=lookup, images=images, trace=trace)
    assert "lid is hand-wash only" in result.spec.body.lower()
    assert "fully dishwasher-safe" not in result.spec.body.lower()


def test_the_prompt_is_smaller_than_in_step_one(settings, images, trace, request_for, lookup):
    """The tool result is a fraction of the whole guide that step 1 returned on every call."""
    run_request(request_for(text=DISHWASHER), settings=settings, model=lookup, images=images, trace=trace)
    whole_guide = approx_tokens((settings.workspaces_dir / "harbor" / "brand-book.md").read_text())
    returned = trace.tool_calls("get_brand_details")[0].detail["result_tokens"]
    assert returned < whole_guide / 3, f"{returned} tokens back, the whole guide is {whole_guide}"


def test_next_problem_keywords_miss_meaning(settings):
    """The failure step 3 fixes: a paraphrase shares no words with the chunk that answers it."""
    tool = harbor_tool(settings)
    assert "leak-proof" not in tool("Will it spill in my bag?").lower()
    assert "hot for 12 hours" not in tool("Warm on a long shift?").lower()


def test_the_trace_shows_each_chunk_and_its_score(settings, images, trace, request_for, lookup):
    """The trace lists every chunk the tool returned, best first, with its BM25 score, so you can see what the model reads."""
    run_request(request_for(text=DISHWASHER), settings=settings, model=lookup, images=images, trace=trace)
    lines = [line for line in trace.lines() if line.startswith("chunk")]
    assert 0 < len(lines) <= 5 and lines[0].startswith("chunk     #1 ") and "score" in lines[0]


def test_chunks_shows_how_the_guide_is_split(settings, monkeypatch, capsys):
    """`launchkit chunks harbor` lists every chunk with its id and size, before anything is searched."""
    import launchkit.cli as cli

    from rich.console import Console

    monkeypatch.setattr(cli, "settings", settings)
    monkeypatch.setattr(cli, "console", Console(width=200))
    assert cli.main(["chunks", "harbor"]) == 0
    out = capsys.readouterr().out
    assert "brand-book.md#product-facts-flask-trail-750" in out and "facts.md#4" in out
