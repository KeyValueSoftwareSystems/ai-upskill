# Step 3 · Lookup: find the right skill

Maya keeps asking for new things, one at a time. Each one fails, then works once its skill and tool are added. Ready-made, with their moments:

| Skill + tool | Maya asks | What it adds |
| --- | --- | --- |
| `market_research` + `search_web` | "What are hikers talking about this season?" | Sees the outside world, and says where each trend came from |
| `ingest_image` + `describe_image` | "Use our shoot photo, not an AI one." | Checks her photo has no words and no other brand, then uses it. No paid picture |
| `voice_over` + `text_to_speech` | "A 10-second voice-over for the story ad." | A new kind of output: audio, within a word limit |

Each addition also makes the prompt longer: every tool's name, inputs and description, and every skill's line, ride along on every turn, used or not.

The fix: the agent holds three doors instead of every tool. `find_tool` matches each "pick me when" note against a short query and gives back only the best few, each with the exact call to make. `run_skill` loads one skill's file, for this job only. `run_tool` runs any tool by name. A skill's "Hides" line keeps the raw tools it prefers over out of `find_tool`'s answer, so the agent cannot skip the skill. `find_tool`'s ranking comes ready-made.

## The slot

- `launchkit/harness/catalogue.py` · `Catalogue.make_run_tool`. Today it returns a slot marked todo, so the agent still holds every tool directly.
- `launchkit/harness/main.py` · the note on `generate_image`. Today it clashes with `ingest_image`'s note: both sound like "the poster's picture".

## Break it first

```
uv run launchkit main harbor "Use our shoot photo for the story size." --model fake:tools
```

The agent holds every tool and skill at once. On the fake it picks a new paid picture over her photo, because two notes sound alike. On the real model it may pick right: then show the cost instead, with `launchkit explain harbor` before and after this step.

## Prompt card, for your coding agent

```
In launchkit/harness/catalogue.py, replace make_run_tool's slot with a real
run_tool(name: str, inputs: dict) -> str, about 20 lines:
find the entry by name (drop a "functions." prefix models sometimes add); if there is
none, say so and point at find_tool. Check the inputs against the tool's schema with
inspect.signature(entry.fn).bind(**inputs); on a TypeError, say which inputs were wrong
and do not run it. Then run it through self.leash(name, entry.fn, inputs) when there is
a leash (the leash also writes the trace), else call it and record self.trace.tool(...).
Return the result as text: a string as it is, anything else as JSON.
Delete run_tool_todo.

In launchkit/harness/main.py, change generate_image's note so it ends with
", only when no photo is given".
```

## Prove it

```
uv run launchkit check tools3
```

- `run_tool` runs a tool by name and traces it; an unknown tool or wrong inputs come back as a message.
- `find_tool` gives back the best few with their notes, and hides the raw tools a skill prefers over.
- The main agent holds three doors: `find_tool`, `run_skill`, `run_tool`.
- With the note fixed, "use our shoot photo" loads `ingest_image` and pays for no picture.
- The picture budget still holds through `run_tool`.
- Ready-made: trends with addresses; a voice-over file.

## Run it again

The photo ask, on the real model. Search, read, act, answer: `find_tool`, then `run_skill("ingest_image")`, then `describe_image`, `detect_focal_point` and `crop` through `run_tool`. The agent never sees the whole list.

## Stuck?

The answer is on the branch `session-02-tools-step3`.
