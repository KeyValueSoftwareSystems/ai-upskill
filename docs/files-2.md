# Files stage 2 · How the agent finds a file

> Maya, Harbor: "The brief says to avoid the lifetime-guarantee framing. Where did that come from?"

With stage 1 built, the agent can list and read. To answer a question about the five competitor briefs it reads all five into its context, costs a fortune and still answers from a blur. There is no search, and a search that returned whole files would have the same problem as reading the folder.

## Before you start

The page is running on the working copy where stage 1's checks went green. Maya's Breeze conversation holds the five competitor briefs from the research ask. If it does not, send the research ask from stage 1's "Run it again" first.

## The slot

- `launchkit/tools/search_files.py` · `make_search_files`. Today it raises and is not registered.
- `launchkit/tools/read_file.py` · `read_file` reads a whole file. It cannot take a line range yet.

## Break it first

As **Maya at Harbor**, in the Breeze conversation, with the five briefs saved, send:

> Check our saved competitor briefs: which of them mention influencers, and what exactly do they say?

In prep the agent listed the folder and read all five briefs, 3 runs of 3, with five `read competitors/<name>.md` lines in the Trace and 880 to 1,000 tokens of tool results in the **Context** tab. The number in the Context tab is what this stage brings down.

The ask is about influencers rather than the lifetime-guarantee line for a reason. The competitor-research skill tells the researchers never to repeat a lifetime-guarantee claim, so live research does not write that line into a brief, and the agent answers a "where did it come from" question from its own chat history without opening a file. Ask something the chat history cannot answer.

## Prompt card, for your coding agent

```
Build stage 2 of Session 4: a search the agent can use instead of reading every file, capped from the start.

1. launchkit/tools/search_files.py: make_search_files(workspace, trace) returning an Entry with kind "read" and the
   function search_files(pattern, folder="."). One match per line, formatted `path:line: snippet`, with the path
   relative to the workspace and the snippet cut to 160 characters. Stop after 10 matches and add a final line that
   says it stopped early. Skip anything whose suffix is not .md .txt .json .yaml .yml .csv, and anything over
   500,000 bytes. Case-insensitive. Plain Python, not a call to ripgrep: rg is not installed by default.
   Add a `search` trace line to Trace.line in launchkit/trace.py.

2. launchkit/tools/read_file.py: add first_line=1 and last_line=0 (0 means to the end), counting from 1, so the
   agent can read the lines a search points at.

3. Register the search in build_catalogue, and word its Entry note this way:
     search_files  "pick me to search the saved files, briefs and documents for a word or phrase and see which file
                    and line says it, before reading any of them"

Do NOT: add any path checking (stage 3); touch the other tools beyond the line range; build an index or use
embeddings.

Done when `uv run pytest checks/test_files.py -m "stage1 or stage2"` passes.
```

## Prove it

```
uv run pytest checks/test_files.py -m "stage1 or stage2"
```

- A search returns a path, a line number and a snippet.
- It stops after a set number of matches, and says when it stopped early.
- It skips files that are not text or are over a size limit.
- Answering "where did this line come from" costs a search and a read or two, not every file.
- The search says which line, and a read can then take just that part of the file.

## Run it again

Send the same ask. The Trace shows one `search 'influencer' · N matches` line and one or two `read competitors/<name>.md` lines, the **Context** tab's tool results are a fraction of what they were, and the reply names the file and the line.

## Why it matters

Search the text, or build an index? An index is a copy of your files in another shape, and the moment you own a copy you own keeping it true and keeping it separated per tenant. It drifts four ways, each with a symptom the room will recognise: stale after an update, so a re-uploaded contract still returns the old clause; deleted content still returned, which is deleted data leaking; a missing tenant filter on one code path, so one customer's query returns another's paragraph; and one search type not being enough, since "clause 14.2" works with text search and fails with meaning search, and "the part about cancelling early" is the other way round. The missing tenant filter is the same bug as stage 3's path check, in another place.
