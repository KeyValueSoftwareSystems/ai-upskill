# RAG step 3 · Match what the words mean (CP1.2c)

Step 2 matches words. "Will it spill in my bag?" shares no words with "leak-proof lid", so it finds nothing.
"Warm on a long shift?" only matches "long days outside", not "hot for 12 hours". A synonym list fixes one question and misses the next.

**Semantic search** matches what the words mean:

1. An **embedding model** turns text into a list of numbers (a vector) that captures its meaning. Texts that mean similar things get vectors that point the same way.
2. Every chunk is embedded **once**, when the brand document is processed, and stored with its vector in a **vector database**.
3. On each lookup only the **question** is embedded. The database compares it with every stored vector (cosine similarity) and returns the closest 5.

The embedding model is local: `BAAI/bge-small-en-v1.5` through sentence-transformers. It runs on a laptop CPU, needs no key,
has no rate limit, and gives the same numbers on every run. `LAUNCHKIT_EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2` swaps it.

The vector database is **LanceDB**: embedded, so it is a folder on disk (`data/brand-store/`), no server. One table, one row per chunk:
its id, brand, heading, text, a hash of the text, and its 384-number vector. The vectors survive a restart, and a chunk is embedded again only when its text changes.

## Indexing is document processing, done once

- Uploading a brand file (onboarding, the Brand library) chunks, embeds and stores it straight away.
- Brands whose files were written by hand, like Harbor and Ember in this repo, are indexed with `uv run launchkit index`.
- A turn never reads brand files or embeds chunks. `get_brand_details` embeds the question and runs one query.
- A brand that was never indexed says so in the tool result and the trace.

## Before class

```
uv sync
uv run launchkit index        # Harbor 41 chunks, Ember 15, embedded once; run it again and 0 are embedded
uv run launchkit check rag3
```

The first use downloads the embedding model (about 130 MB) into the Hugging Face cache. `uv sync` installs the CPU build of torch, so no CUDA download.

## The slot

- `launchkit/harness/search.py` · `embed()`. Supplied.
- `launchkit/harness/store.py` · `BrandStore`: `index(workspace, root)` writes a brand's rows; `search(query)` runs the vector query.
- `launchkit/harness/brand.py` · the tool searches the store by meaning instead of BM25.
- `launchkit/harness/onboard.py` and `launchkit index`: index the brand when its document is processed.

## Prompt card, for your coding agent

```
In launchkit/harness/store.py, write BrandStore(path) over a LanceDB table with columns
ref, workspace, heading, text, hash, vector (384 floats). index(workspace_id, root) chunks the
brand's files with load_chunks, reuses stored vectors whose text hash matches, embeds only the
rest with embed(), and replaces that brand's rows. search(query, k) embeds the question and runs
table.search(vector).metric("cosine").limit(k); the score is 1 - distance.

Call index_brand(workspace_id, settings, trace) at the end of onboard_workspace, and add a
`launchkit index [brand...]` command for brands written by hand.

In launchkit/harness/brand.py, get_brand_details(query) says so when the brand has no rows,
otherwise returns render_results(query, top) from store.search(query, TOP_K), tracing each chunk
with its cosine score. It never reads brand files or embeds chunks.
```

## Prove it

```
uv run launchkit check rag3
```

- "Clean the lid" ranks the hand-wash chunk first; "spill in my bag" ranks leak-proof first; "warm on a long shift" finds "hot for 12 hours".
- Still at most 5 chunks.
- A lookup embeds only the question. The vectors survive a restart; an edited file embeds only what changed.
- Onboarding indexes the new brand; `launchkit index` the hand-written ones; an unindexed brand says so.

## See it

```
uv run launchkit lookup harbor "Will it spill in my bag?"            # leak-proof is #1; in step 2 nothing matched
uv run launchkit lookup harbor "Will my drink stay hot on the train?" # "hot for 12 hours" is #1; no shared word but "hot"
uv run launchkit run harbor "How do I clean the lid?" --session rag3
```

Each chunk line in the trace shows its rank, id and cosine score.

## Next problem

```
uv run launchkit lookup ember "Write a poster about our next launch."
uv run launchkit run ember "Write a poster about our next launch." --user jonas --session rag3
```

The store holds every brand's chunks, and the search ranks all of them by meaning alone. Harbor's embargoed Tidal launch is the closest
thing to "our next launch", so the five chunks are all `harbor/…` and Ember's poster says "Flask Trail 750 lands in six weeks".
It goes the other way too: Harbor asking "Warm on a long shift?" gets Ember's Night Shift coffee as #1, and
"How long does my coffee stay warm?" gets Ember's subscription.
Dropping other brands' chunks after the search leaves Ember with nothing, because the top 5 were all Harbor's.
Every row already says which brand it belongs to. The search has to use that.

## Stuck?

The answer is on the branch `session-01-rag-step3`.
