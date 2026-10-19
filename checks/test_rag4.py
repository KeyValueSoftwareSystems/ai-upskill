import inspect
import re

import pytest

from launchkit.harness.brand import make_get_brand_details
from launchkit.harness.request import UnknownWorkspace
from launchkit.harness.run import run_request
from launchkit.harness.search import TOP_K, embed
from launchkit.harness.spec import PosterSpec, validate_spec
from launchkit.harness.store import brand_store, scope
from launchkit.harness.trace import Trace
from launchkit.harness.workspace import load_workspace

DISHWASHER = "Poster for the Tidal bottle. Mention it's dishwasher-safe."
EMBER_ASKS = [
    "Write a poster about our next launch.",
    "Tidal",
    "When does the new colourway launch? Is it embargoed?",
    "Is the lid dishwasher-safe?",
    "750 ml bottle cold for 24 hours",
]
HARBOR_ASKS = ["Warm on a long shift?", "How long does my coffee stay warm?", "What is the roast date?"]


def refs(result: str) -> list[str]:
    return re.findall(r"^\[([^\]]+)\]", result, flags=re.M)


def tool_for(workspace_id, settings, trace=None):
    return make_get_brand_details(load_workspace(workspace_id, settings, Trace()), trace or Trace(), settings)


def test_the_tool_takes_no_workspace_argument(settings):
    """The tool's only parameter is the query. The workspace filter comes from the trusted request, never the model."""
    assert list(inspect.signature(tool_for("harbor", settings)).parameters) == ["query"]


@pytest.mark.parametrize("asked", EMBER_ASKS)
def test_ember_never_gets_harbors_chunks(settings, asked):
    """Ember's searches run inside Ember's workspace: no Harbor chunk and no "Tidal", whatever Ember asks, and still Ember's own best 5."""
    result = tool_for("ember", settings)(asked)
    assert len(refs(result)) == TOP_K
    assert all(ref.startswith("ember/") for ref in refs(result))
    assert "tidal" not in result.lower()


@pytest.mark.parametrize("asked", HARBOR_ASKS)
def test_harbor_never_gets_embers_chunks(settings, asked):
    """It works both ways: "Warm on a long shift?" no longer brings Ember's Night Shift coffee to Harbor."""
    assert all(ref.startswith("harbor/") for ref in refs(tool_for("harbor", settings)(asked)))


def test_the_filter_is_inside_the_search_not_after_it(settings):
    """Ranking everyone and dropping other brands afterwards leaves Ember nothing; filtering inside the query gives Ember its best 5."""
    store = brand_store(settings.data_dir / "brand-store")
    question = "Write a poster about our next launch."
    everyone = store.table.search(embed([question])[0]).metric("cosine").limit(TOP_K).to_list()
    assert [r for r in everyone if r["workspace"] == "ember"] == [], "a filter after the search keeps none of the top 5"
    inside = store.search("ember", question)
    assert len(inside) == TOP_K and all(chunk.workspace == "ember" for _, chunk in inside)


def test_the_trace_shows_only_the_brands_own_chunks(settings):
    """Ember's launch question, traced chunk by chunk: five chunks, every one Ember's, and the filter named in the trace."""
    trace = Trace()
    tool_for("ember", settings, trace)("Write a poster about our next launch.")
    lines = trace.lines()
    assert any("filter workspace = 'ember' inside the query" in line for line in lines)
    chunks = [line for line in lines if line.startswith("chunk")]
    assert len(chunks) == 5 and all(" ember/" in line for line in chunks)


def test_the_workspace_filter_only_takes_allowed_ids():
    """The workspace id written into the filter is checked against the allow-list, so it cannot widen the search."""
    assert scope("ember") == "workspace = 'ember'"
    with pytest.raises(UnknownWorkspace):
        scope("ember' OR workspace = 'harbor")


def test_the_dishwasher_copy_names_its_chunk(settings, images, trace, request_for, lookup):
    """Dishwasher copy: body yes, lid never, and the claim names the Harbor chunk it came from."""
    result = run_request(request_for(text=DISHWASHER), settings=settings, model=lookup, images=images, trace=trace)
    assert "lid is hand-wash only" in result.spec.body.lower() and "fully dishwasher-safe" not in result.spec.body.lower()
    assert result.spec.sources and all(s.startswith("harbor/") for s in result.spec.sources)


def test_a_source_the_tool_never_returned_is_refused():
    """A spec that cites a chunk the tool did not return this run fails validation, so a made-up source cannot pass."""
    spec = PosterSpec(headline="Cold all day", subheadline="Built for long days", body="The lid is hand-wash only.",
                      image_prompt="A bottle on a shore", sources=["harbor/brand-book.md#made-up"])
    assert validate_spec(spec, {}, looked_up={"harbor/facts.md#4"}) == ["source harbor/brand-book.md#made-up was not returned by get_brand_details"]
    assert validate_spec(spec.model_copy(update={"sources": ["harbor/facts.md#4"]}), {}, looked_up={"harbor/facts.md#4"}) == []
