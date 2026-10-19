# RAG step 2 · Return only what matches (CP1.2b)

Step 1 returns the whole brand guide on every call: about 2,000 tokens for Harbor, and it grows with every product and placement.
Every turn pays for it, the one rule that matters sits among thousands, and any edit changes the prompt prefix so caching breaks.

The obvious fix is a summary. A fixed summary decides what matters before anyone asks, and drops "the lid is hand-wash only".
The tool should return only the parts that match the question.

1. Split the guide into chunks: one `## ` section each (facts.md: one fact per line). A good chunk is one idea and makes sense alone.
2. Score each chunk by the words it shares with the query (BM25: rare words count more, long chunks a little less).
3. Return the top 5. Only the relevant part reaches the prompt.

## The slot

- `launchkit/harness/search.py` · `split_by_heading`, `bm25`, `render_results`. Supplied.
- `launchkit/harness/brand.py` · the tool now takes a `query`.

## Prompt card, for your coding agent

```
In launchkit/harness/brand.py, change get_brand_details to take query: str. It loads the
workspace's chunks with load_chunks(ws.root), ranks them with bm25(query, chunks), keeps
the top TOP_K (5), records a trace note with how many it scored and returned, and returns
render_results(query, top). Each chunk is rendered with its id, for example
[brand-book.md#product-facts-flask-trail-750-tidal-colourway]. The docstring asks the model
for one specific question per call. Still no workspace parameter.
```

## Prove it

```
uv run launchkit check rag2
```

- The guide is split by heading; facts.md one fact per line.
- The tool takes a query and returns at most 5 chunks.
- The dishwasher copy is still correct.
- The tool result is a fraction of step 1's whole guide.

## See it

```
uv run launchkit run harbor "Poster for the Tidal bottle. Mention it's dishwasher-safe." --session rag2
```

`tool get_brand_details("is the Tidal bottle dishwasher-safe") → … · 294 tokens back`, down from about 1,970.

Show the class the two halves of it:

```
uv run launchkit chunks harbor                              # how the guide is split: 41 chunks, id and size each
uv run launchkit lookup harbor "How do I clean the lid?"    # the chunks that come back, their BM25 scores, and the exact text
```

The trace (terminal and the page's Trace tab) lists every returned chunk with its rank and score:
`chunk #1 brand-book.md#product-facts-harbor-mug · score 3.531 · Harbor Mug is 350 ml with a sliding lid…`.
Keywords put the mug first because it says "lid" and "dishwasher-safe"; the hand-wash fact is second.

## Next problem

Ask the tool "Will it spill in my bag?". The answer is "leak-proof lid", but the two share no words, so BM25 finds nothing.
"Warm on a long shift?" only matches "long days outside", not "hot for 12 hours". A synonym list fixes one question and misses the next.
We need to match what the words mean. On Harbor's guide, "How do I clean the lid?" still works by keywords, because "lid" is in the chunk.

## Stuck?

The answer is on the branch `session-01-rag-step2`.
