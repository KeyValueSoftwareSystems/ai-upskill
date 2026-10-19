# RAG step 4 · Keep each brand to its own chunks (CP1.2d)

Step 3 searches the vector database by meaning, across every row. Ember asks for a poster about its next launch, and the five closest
chunks are Harbor's embargoed Tidal launch. Ember's poster says "Six weeks till Tidal". It goes both ways: Harbor asking
"Warm on a long shift?" gets Ember's Night Shift coffee.

The obvious fix is to rank as before, then drop every chunk that isn't Ember's. The top 5 were all Harbor's, so Ember gets nothing.
And every query still scores every customer's chunks.

**Metadata.** Every row in the store already carries more than its vector: the brand it belongs to (`workspace`), its id, heading and text.
A vector database can filter on those columns **inside** the search: only rows where `workspace = 'ember'` are ranked at all,
so the top 5 are always Ember's best 5.

**Who sets the filter.** The workspace comes from the trusted request (step 4 of the harness), bound by the harness when it builds the tool.
The tool takes no workspace argument, so the model cannot name another brand or widen the filter. The id is checked against the
allow-list again before it is written into the query.

**Each claim names a chunk.** Every chunk comes back with its id; the spec lists the ids its facts came from in `sources`, and the harness
refuses a source the tool did not return in this run.

When it is overkill: a short, stable document for one customer can live in the prompt. Reach for a vector database with filters when
documents grow, change, or belong to different customers.

## The slot

- `launchkit/harness/store.py` · `BrandStore.search(workspace_id, query)`: one line, `.where(scope(workspace_id), prefilter=True)`.
- `launchkit/harness/brand.py` · the tool passes `ws.id`, which came from the request.
- `launchkit/harness/spec.py` · `PosterSpec.sources`, and `validate_spec` checks them against what the tool returned.

## Prompt card, for your coding agent

```
In launchkit/harness/store.py, BrandStore.search takes workspace_id first and adds
.where(scope(workspace_id), prefilter=True) to the vector query, so the filter runs inside the
search. scope() checks the id against WORKSPACE_ID before writing workspace = '<id>'.

In launchkit/harness/brand.py, get_brand_details(query) calls store.search(ws.id, query, TOP_K).
ws comes from the request; there is still no workspace parameter. Trace the filter.

Add sources: list[str] to PosterSpec, and make validate_spec refuse a source that
get_brand_details did not return in this run.
```

## Prove it

```
uv run launchkit check rag4
uv run launchkit check rag     # all four retrieval steps
```

- Ember never gets a Harbor chunk or "Tidal", and still gets its own 5. Harbor never gets Ember's.
- The filter is inside the search: filtering the global top 5 afterwards would leave Ember nothing.
- The tool takes no workspace argument, and the filter only takes allow-listed ids.
- Dishwasher copy: body yes, lid never; the claim names its chunk; a made-up source is refused.

## See it

Run the questions that crossed brands in step 3:

```
uv run launchkit lookup ember "Write a poster about our next launch."   # five chunks, all ember/…, Slow Burn among them
uv run launchkit lookup harbor "Warm on a long shift?"                   # harbor/… only; "hot for 12 hours" first
uv run launchkit run ember "Write a poster about our next launch." --user jonas --session rag4
uv run launchkit run harbor "Poster for the Tidal bottle. Mention it's dishwasher-safe." --session rag4
```

The trace says `searched ember's chunks only (filter workspace = 'ember' inside the query)`. Ember's poster is about Slow Burn, its own
March launch. Harbor's says the lid is hand-wash only and lists its chunk ids in `sources`.

This clears CP1.2 checks 1 to 4. Check 5 belongs to the context builder.

## Stuck?

The answer is on the branch `session-01-rag-step4`.
