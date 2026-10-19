from launchkit.harness.search import TOP_K, memory_index, render_results
from launchkit.harness.trace import Trace
from launchkit.harness.workspace import Workspace


def make_get_brand_details(ws: Workspace, trace: Trace):
    """v3: rank chunks by what the words mean (embeddings, cosine similarity) and return the top TOP_K.
    Every chunk is embedded once into one in-memory list; the query is embedded on each call."""

    def get_brand_details(query: str) -> str:
        """Look up this brand's guide and product facts. Ask one specific question, for example
        "is the lid dishwasher-safe" or "headline word limit". Returns the matching sections,
        best first. Call it before you state any product fact. Use only what it returns; if it
        does not say something, do not claim it. Ask again with other words for another fact."""
        index = memory_index(ws.root.parent)
        if index.refresh():
            trace.note(f"get_brand_details embedded {len(index.entries)} chunks into one in-memory list")
        top = [chunk for _, chunk in index.search(query, TOP_K)]
        trace.note(f"get_brand_details ranked {len(index.entries)} chunks by meaning, returned {len(top)}")
        return render_results(query, top)

    return get_brand_details
