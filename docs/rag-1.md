# RAG step 1 · A tool to fetch brand details (CP1.2a)

Harbor asks: "Mention it's dishwasher-safe." LaunchKit writes "Fully dishwasher-safe, top to bottom."
Harbor's fact sheet says the body is dishwasher-safe and the lid is hand-wash only.
The model has never seen the fact sheet, so it fills the gap with something plausible. Plausible is not true.

The model only knows what is in front of it. Give it a way to look things up: a tool.
The agent decides when to call it; the harness runs it. The harness, not the model, decides which brand's file it reads.

## The slot

- `launchkit/harness/brand.py` · `make_get_brand_details(ws, trace)`. It returns the tool.
- `launchkit/harness/agent.py` · `build_copy_agent`: add the tool to `tools=[...]`. One line in `SPEC_TASK` tells the model to look facts up before it states one.

## Prompt card, for your coding agent

```
In launchkit/harness/brand.py, write make_get_brand_details(ws, trace). It returns a
function get_brand_details() -> str with no parameters. It reads ws.root / "brand-book.md"
(or facts.md when there is no brand book), records trace.file(path) and returns the text.
The docstring is what the model reads: look the brand up before stating any product fact,
and claim only what it returns.

In launchkit/harness/agent.py, build_copy_agent adds tools=[make_get_brand_details(ws, trace)]
next to the leash hook, and SPEC_TASK gets one line: brand facts are not in this prompt;
call get_brand_details before stating one.
```

## Prove it

```
uv run launchkit check rag1
```

- The tool is registered on the copy agent and takes no workspace argument.
- A Harbor request reads Harbor's brand book; an Ember request never sees Harbor's.
- "Mention it's dishwasher-safe": the lid is hand-wash only, never "fully dishwasher-safe".
- Without the tool, the same fake writes the banned claim.
- The trace shows the tool call with its size in tokens.

## See it

```
uv run launchkit run harbor "Poster for the Tidal bottle. Mention it's dishwasher-safe."
uv run launchkit explain
```

The trace has `tool get_brand_details() → … · 1970 tokens back`. That is the whole guide, on every call. Step 2 starts there.

## Stuck?

The answer is on the branch `session-01-rag-step1`.
