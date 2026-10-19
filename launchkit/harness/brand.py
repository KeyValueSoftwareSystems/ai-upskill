from launchkit.harness.search import TOP_K, bm25, load_chunks, render_results
from launchkit.harness.trace import Trace
from launchkit.harness.workspace import Workspace


def make_get_brand_details(ws: Workspace, trace: Trace):
    """v2: the tool takes the agent's question and returns only the chunks that match it, at most TOP_K.
    The workspace is bound here, by the harness, from the trusted request. The model never names it."""

    def get_brand_details(query: str) -> str:
        """Look up this brand's guide and product facts. Ask one specific question, for example
        "is the lid dishwasher-safe" or "headline word limit". Returns the matching sections,
        best first. Call it before you state any product fact. Use only what it returns; if it
        does not say something, do not claim it. Ask again with other words for another fact."""
        chunks = load_chunks(ws.root)
        top = [chunk for _, chunk in bm25(query, chunks)[:TOP_K]]
        trace.note(f"get_brand_details scored {len(chunks)} chunks by shared words, returned {len(top)}")
        return render_results(query, top)

    return get_brand_details
