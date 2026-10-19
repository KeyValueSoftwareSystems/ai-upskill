from launchkit.harness.search import TOP_K, render_results
from launchkit.harness.store import brand_store
from launchkit.harness.trace import Trace
from launchkit.harness.workspace import Workspace


def make_get_brand_details(ws: Workspace, trace: Trace, settings):
    """v3: semantic search in a vector database. The question is embedded and compared with every stored chunk
    by cosine similarity; the top TOP_K come back. The tool only reads the store: documents are chunked and
    embedded once, when they are processed."""
    store = brand_store(settings.data_dir / "brand-store")

    def get_brand_details(query: str) -> str:
        """Look up this brand's guide and product facts. Ask one specific question, for example
        "is the lid dishwasher-safe" or "headline word limit". Returns the matching sections,
        best first. Call it before you state any product fact. Use only what it returns; if it
        does not say something, do not claim it. Ask again with other words for another fact."""
        if not store.indexed(ws.id):
            trace.note(f"get_brand_details: {ws.id} has no chunks in the brand store; run `launchkit index {ws.id}` or upload its brand file")
            return f"{ws.id}'s brand guide has not been indexed yet, so there is nothing to look up. Do not claim any product fact."
        ranked = store.search(query, TOP_K)
        trace.note(f"get_brand_details searched the brand store by meaning (cosine similarity), every brand's chunks, returned {len(ranked)}")
        for rank, (score, chunk) in enumerate(ranked, 1):
            trace.chunk(rank, chunk.ref, score, chunk.text)
        return render_results(query, [chunk for _, chunk in ranked])

    return get_brand_details
