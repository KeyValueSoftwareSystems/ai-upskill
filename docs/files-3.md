# Files stage 3 · How the agent finds a file

> Maya, Harbor: "Somewhere in the briefs you saved, a competitor mentions a holiday. Find it." The agent reads every brief, one by one.

With stage 1 built, the agent can list and read. To answer a question about the five competitor briefs it reads all five into its context, which is expensive, and still answers vaguely. There is no search, and a search that returned whole files would have the same problem as reading the folder.

## Before you start

The page is running on the working copy where stage 2's checks went green. Maya's Breeze conversation, `k7c1`, holds the competitor briefs the research in stages 1 and 2 saved.

## The slot

- `launchkit/tools/search_files.py` · `make_search_files`. Today it raises and is not registered.
- `launchkit/tools/read_file.py` · `read_file` reads a whole file. It cannot take a line range yet.

## Break it first

As **Maya at Harbor**, in the Breeze conversation, send:

> Look in our saved briefs: which of them mention a holiday, and what do they say?

The agent lists the folder. Then it either reads the briefs one by one, which the Trace shows as a `read competitors/<name>.md` line for each, and the **Context** tab shows what that costs, or it gives up early and says that none of them mention a holiday, or it reads one or two and answers as if they were all of them. The last two are wrong answers: several of the briefs do mention one, and nothing in the reply says it missed any. All three outcomes are what this stage fixes.

The agent remembers its last few turns, so a second ask for the same thing is answered from what it already read. Ask it once, or open a new conversation and run the research again.

## Prompt card, for your coding agent

```
Build stage 3 of Session 4: a search the agent can use instead of reading every file, capped from the start.

1. launchkit/tools/search_files.py: make_search_files(workspace, trace) returning an Entry with kind "read" and the
   function search_files(pattern, folder="."). One match per line, formatted `path:line: snippet`, with the path
   relative to the workspace. The snippet is about 160 characters of the line centred on the match. Mark a cut end with
   "...". Stop after 10 matches and add a final line that says it stopped early. Skip anything whose suffix is not
   .md .txt .json .yaml .yml .csv, and anything over 500,000 bytes. Case-insensitive. Plain Python, not a call to
   ripgrep: rg is not installed by default.
   Add a `search` trace line to Trace.line in launchkit/trace.py.

2. launchkit/tools/read_file.py: add first_line=1 and last_line=0 (0 means to the end), counting from 1, so the
   agent can read the lines a search points at.

3. Register the search in build_catalogue, and word its Entry note this way:
     search_files  "pick me to search the saved files, competitor briefs and documents for a word or phrase, to find
                    which of them mention it and which line says so, before reading any of them"

4. In MAIN_TASK in launchkit/agents/main_agent.py, add search_files to the workspace paragraph: the agent looks in the
   workspace with list_files, search_files and read_file.

Do NOT: change any line that is already in Trace.line, or its spacing; add any path checking (stage 5); touch the other tools beyond the line range; build an index or use
embeddings.

Done when `uv run pytest checks/test_files.py -m "stage1 or stage2 or stage3"` passes and the rest of `uv run pytest checks -q
--ignore=checks/test_files.py` still passes.
```

## Prove it

```
uv run pytest checks/test_files.py -m "stage1 or stage2 or stage3"
```

- A search returns a path, a line number and a snippet that contains the word it found, even when the line is long.
- It stops after a set number of matches, and says when it stopped early.
- It skips files that are not text or are over a size limit.
- Answering "where did this line come from" costs a search and a read or two, not every file.
- The search says which line, and a read can then take just that part of the file.

## Run it again

Send the same ask in a fresh conversation, after the research has run there. The Trace shows one `search 'holiday'` line and perhaps one `read`, the **Context** tab's tool results are a fraction of what they were, and the reply names the briefs and quotes the lines. The wording that works is an instruction to look in the saved briefs. A question about the topic alone sends the agent to the research skill. The cap, ten matches and a line saying it stopped, is covered by the checks.

## Why it matters

Search the text, or build an index? An index is a copy of your files in another shape, and the moment you own a copy you own keeping it true and keeping it separated per tenant. It drifts four ways, each with a symptom the room will recognise: stale after an update, so a re-uploaded contract still returns the old clause; deleted content still returned, which is deleted data leaking; a missing tenant filter on one code path, so one customer's query returns another's paragraph; and one search type not being enough, since "clause 14.2" works with text search and fails with meaning search, and "the part about cancelling early" is the other way round. The missing tenant filter is the same bug as stage 3's path check, in another place.
