# RAG step 3 · Match what the words mean (CP1.2c)

Step 2 matches words. "Will it spill in my bag?" shares no words with "leak-proof lid", so it finds nothing.
"Warm on a long shift?" misses "hot for 12 hours". A synonym list fixes one question and misses the next; the list never ends.

An embedding model turns text into a list of numbers that captures its meaning. Texts that mean similar things sit close together.
Embed every chunk once; embed the query on each call; rank chunks by how close they are (cosine similarity).

The model is local: `BAAI/bge-small-en-v1.5` through sentence-transformers. It runs on a laptop CPU, needs no key,
has no rate limit, and gives the same numbers on every run. `LAUNCHKIT_EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2` swaps it.

## Before class

The first use downloads the model (about 130 MB) into the Hugging Face cache. Run the check once on a good connection:

```
uv sync
uv run launchkit check rag3
```

`uv sync` installs the CPU build of torch, so no CUDA download.

## The slot

- `launchkit/harness/search.py` · `embed()`, `cosine()` and `MemoryIndex`. `embed()` is supplied.
- `launchkit/harness/brand.py` · the tool ranks the index by meaning instead of BM25.

## Prompt card, for your coding agent

```
In launchkit/harness/search.py, write MemoryIndex(workspaces_dir): a plain list of
(chunk, vector) for every brand's chunks, embedded once with embed(). refresh() embeds
again only when a brand file changes. search(query, k) embeds the query, scores every
entry with cosine(), and returns the top k.

In launchkit/harness/brand.py, get_brand_details(query) asks memory_index(ws.root.parent)
for the top TOP_K chunks and returns render_results(query, top). Trace a note when the
index is embedded and on each search.
```

## Prove it

```
uv run launchkit check rag3
```

- "Clean the lid" ranks the hand-wash chunk first; "spill in my bag" ranks leak-proof first.
- "Warm on a long shift" finds "hot for 12 hours".
- Still at most 5 chunks. Chunks are embedded once; each later call embeds only the query.

## See it

```
uv run launchkit run harbor "How do I clean the lid?" --session rag3
```

The reply: hand-wash the lid, the body is dishwasher-safe.

Compare the two rankers on the same questions. Each chunk line shows its rank, id and cosine score:

```
uv run launchkit lookup harbor "Will it spill in my bag?"     # leak-proof is #1; in step 2 nothing matched
uv run launchkit lookup harbor "Warm on a long shift?"        # "hot for 12 hours" is in the top 5
```

## Next problem

```
uv run launchkit run ember "Write a poster about our next launch." --user jonas --session rag3
```

Show it before the poster: `uv run launchkit lookup ember "Write a poster about our next launch."` returns five chunks, all `harbor/…`.

Every brand's chunks sit in one list, ranked by meaning alone. Harbor's embargoed Tidal launch is the closest thing to "our next launch",
so Ember's poster says "Flask Trail 750 lands in six weeks". Dropping other brands' chunks afterwards leaves Ember with nothing,
because the top 5 were all Harbor's. The filter has to be part of the search, not a step after it.

## Stuck?

The answer is on the branch `session-01-rag-step3`.
