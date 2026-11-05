# Routing hands-on 1 · A model for each job

Breeze launch week. Every job LaunchKit does runs on one model, picked by one setting: the launch copy, a quick question about the product, the research helper, the memory write, the photo check. On the top model the work is good, and a one-line question waits and pays like the launch copy. On a small model it is fast and cheap, and the work breaks. Maya wants the same quality, faster and cheaper.

In this hands-on you write `route()`: one function that reads Maya's ask, names the job, and returns the models to try in order. At the end, each job has its own model, the scoreboard splits across them, and an outage of the top research model does not stop the launch.

## Before you start

In the terminal:

```
git checkout session-03-routing
uv sync
uv run launchkit index harbor
uv run launchkit check routing0
uv run launchkit models
```

**It worked when** `index harbor` says the chunks are in the brand store (once per clone: Session 1 did it, so it may say they are unchanged), `check routing0` prints `7 passed`, and `launchkit models` shows every model `enabled`.

In `.env`, set `LAUNCHKIT_MODEL=gpt-5.5` (the one setting LaunchKit has had so far: one model for every job), set `LAUNCHKIT_SEARCH=saved` so research reads the saved competitor pages and gives the same pages every time, and leave `LAUNCHKIT_DISABLED_MODELS` out. Then start the chat page:

```
uv run launchkit ui
```

Everything below happens on the chat page: sign in as Maya at Harbor and keep the **Trace** tab open. Leave the **Model** box at the top empty: it is Maya's own choice, and she does not pick a model in this hands-on. The team's settings live in `.env`: the one model (`LAUNCHKIT_MODEL`), the outage and thinking effort. After changing `.env`, stop the chat page (Ctrl+C) and run `uv run launchkit ui` again, because the page reads `.env` when it starts.

## What is already there

Nothing in this list is new to build. It is here so nothing changes without you knowing.

- **Jobs** (`launchkit/adapters/models.py`, `Jobs`). Every model call now asks for its job's model:
    - the main agent's reply: `long_text`, with Maya's message as the ask;
    - the onboarding agent: `long_text`;
    - the research subagent: `research`;
    - the memory write and the session summary: `memory_write`;
    - `describe_image` and `detect_focal_point`: `vision`, chosen at the moment of the call, so a skill loaded earlier in the turn can pin it.

  Until `route()` is built, every job runs on Maya's pick, or on `gpt-4.1-mini` when she made none: the same as every session before this one. Once it is built, `Jobs` calls `route()`, writes one `route` line in the trace for each choice, and when a call fails, tries the next model on the list.
- **The rank lists** (`launchkit/ranking.json`, read by `launchkit/adapters/ranking.py`). One list per job. Each model has three scores from 0 to 1: `eval`, how good its work is on Harbor's test asks (1 is the best); `latency`, how long it takes (1 is the slowest model in the file); and `cost`, what it costs (1 is the most expensive model in the file, 0 the cheapest, not free). Each job has weights. The total counts `eval` up and `latency` and `cost` down. `uv run launchkit models` shows the real price next to each model. `rank_list(job, settings)` gives the job's models by weighted total, best first. Edit the file and the next call reads it; no restart.
- **The skill's pin.** `ingest_image`'s `skill.md` has a `Model:` line: `Model: vision = gpt-5.5`. The skill loader reads it into `skill.pins`.
- **Switched-off models.** `LAUNCHKIT_DISABLED_MODELS` in `.env`, comma-separated. `is_enabled(name, settings)` says whether a model is on. It switches a model off inside LaunchKit only; the proxy would still answer. It stands in for an outage.
- **The scoreboard** (`Trace.bill()` and `Trace.scoreboard()` in `launchkit/trace.py`). At the end of every turn the trace gets one `score` line per model (the jobs it did, calls, tokens, seconds, and dollars: what the LiteLLM proxy says it charged, or, when it says nothing, an estimate from `launchkit/adapters/pricing.py`, marked ≈), one `total` line that adds up every model in the turn, and one `quality` line (Harbor's checks this turn: `check_copy`, the poster check, and whether the photo check caught words or a logo). Every real call is timed on its own `call` line.
- **Not on the scoreboard:** pictures and voice-overs. Pictures come from the GPU service, which has no price per call, and there is one model for each.
- **`uv run launchkit models`**: every job's rank list with scores, totals, and whether each model is enabled and served by the proxy.
- **`samples/shoot/breeze-cap.jpg`**: the Breeze shoot photo with a red cap in the background grass, carrying another brand's logo.
- **`LAUNCHKIT_FAKE_MODELS=1`**: every job runs on a scripted model and the trace keeps the routed name. For when the proxy is down.
- **Not routed:** `image_gen` and `tts` keep their own settings (`LAUNCHKIT_IMAGE_PROVIDER`, `LAUNCHKIT_TTS_MODEL`). There is one model for each today, so there is nothing to rank.

## The slot

`launchkit/adapters/routing.py`, `route()`. It is marked `@todo` and raises until you build it.

## Break it first

Two rounds on the chat page, one model for everything each time. Before `route()` is built, the one model in `LAUNCHKIT_MODEL` does every job. Each round sends the same three asks, each in its own new conversation. They need three very different models: launch copy needs the best writer, research needs a solid reader, and a product fact needs almost nothing.

1. "Write three headlines for the Breeze feed post."
2. "How are Hydro Flask and Stanley launching bottles this season?" The main agent hands this to two research helpers, one per brand.
3. "How many ml is the Breeze?"

**Round 1 · The top model on every job.** `LAUNCHKIT_MODEL=gpt-5.5` is already set. Send the three asks.

**What to look for** at the end of each turn in the Trace tab: one `score` line, for `gpt-5.5`, whatever the job. The research costs the most, because the helpers read whole pages at the top price. In our run: headlines about $0.03, research about $0.17, the size about $0.02. On the size question the agent may first load the competitor research skill, then find the brand guide: a few extra calls at the top price. The one-line answer about the size pays the same price per token as the launch copy. The seconds on a `score` line add up every call, so two research helpers working side by side count more than the time Maya waited.

**Round 2 · The smallest model on every job.** The team tries the cheapest model to cut the bill: set `LAUNCHKIT_MODEL=gpt-5-nano` in `.env`, restart the chat page, and send the same three asks.

**What to look for:** the cost drops on every `score` line. Then read the work. You may see any of these:

- headlines that are fine: some jobs never needed the top model;
- headlines with a never-say word in them, so `check_copy` fails on the `quality` line, or headlines that are flatter;
- a research summary that is thin, or that misses a brand;
- the wrong skill picked, or a tool called that does not exist;
- a turn that takes **longer** than on the top model: a small reasoning model can think for thousands of tokens. Cheaper is not always faster.

One setting cannot fit every job.

## Prompt card, for your coding agent

```
Implement route() in launchkit/adapters/routing.py. It's a stub right now: remove the @todo
decorator and the NotImplementedError when you're done.

Context: every model call in LaunchKit goes through Jobs in launchkit/adapters/models.py, and
Jobs calls route() once it's built. The routed jobs are long_text, short_text, research,
memory_write and vision. Rank lists live in launchkit/ranking.json; use rank_list(job, settings)
and is_enabled(name, settings) from launchkit/adapters/ranking.py, don't read the JSON yourself.

Keep the signature:
    route(job, settings, ask=None, pick=None, skill=None) -> (job, [(model, reason), ...])

Behaviour:
1. If job is "long_text" and the ask ends with "?" and has 12 words or fewer, the job becomes
   "short_text".
2. Build the order to try: the pick first (reason "pick"); then the skill's pin for this job, if
   it has one (skill.pins is a tuple of (job, model) pairs; reason "skill"); then rank_list(job)
   with reasons "rank 1", "rank 2", and so on.
3. Drop duplicates, keeping the first one.
4. Leave out every model that is_enabled() says is off, the pick included. If anything was left
   out before the first model you return, that model's reason is "fallback".

Keep it a pure function: no I/O and no trace calls (Jobs writes the trace). Don't change Jobs,
its callers or ranking.json.

Done when `uv run launchkit check routing1` passes.
```

## Run it again

Empty `LAUNCHKIT_MODEL` in `.env` (`LAUNCHKIT_MODEL=`), so no single model is set any more, and restart the chat page. The rank list now decides. Send the same three asks, each in a new conversation:

1. "Write three headlines for the Breeze feed post." The trace says `route  long_text · gpt-5.5 · rank 1`. When the agent checks the copy, the `quality` line shows `check_copy` passing.
2. "How are Hydro Flask and Stanley launching bottles this season?" The trace says `route  research · gpt-4.1-mini · rank 1` for each helper. Its `score` line is a fraction of round 1's research cost.
3. "How many ml is the Breeze?" The trace says `route  short_text · gpt-5-nano · rank 1`, with one `get_brand_details` call.

Each job now runs on its own model, and the `score` lines show three rows.

**The skill's model.** Press **New conversation**, attach `samples/shoot/breeze-cap.jpg` with 📎 and send: "Breeze launches next month. Same as Tidal: concepts, then every size." The trace says `route  vision · gpt-5.5 · skill`: the `ingest_image` skill asked for that model. The photo check finds the cap's logo and stops before any sizes are made.

## What changes, and why

- **Before:** one setting, `LAUNCHKIT_MODEL`, chose the model for every text job, the memory write included.
- **After:** every job asks `route()`. `LAUNCHKIT_MODEL` still works: if the team sets it, it fixes the model for the main agent's reply (`long_text` and `short_text`) and goes first, like Maya's own choice in the **Model** box. The research helper, the memory write and the photo check follow their own lists.
- The order is a policy: Maya's pick, then the skill's pin, then the rank list. With no pick and no pin, rank 1 is the choice. That is what "Auto" means here.
- A switched-off model is skipped wherever it comes from, so a pick that is down never runs, and the trace says `fallback`.

## Prove it

```
uv run launchkit check routing1
```

The check runs offline on scripted models, so it gives everyone the same result. All eight pass once `route()` is built.

- A short question becomes `short_text`; "Write three headlines…" stays `long_text`; "Can you write three headlines…?" becomes `short_text`.
- With no pick and no pin, the models come in rank order.
- Maya's pick comes first.
- A skill's pin beats the rank list.
- A switched-off model is skipped, the pick included, and the next one's reason is `fallback`.
- Every routed job gets a model.
- A failed call moves to the next model, and the trace says `fallback`.
- On the chat path, "How many ml is the Breeze?" runs as `short_text`, the memory write has its own model, and the scoreboard is in the trace.

## Why it matters

Every model choice trades quality, time and cost. One setting makes that trade once, for every job. A rank list per job makes it per job, and writes it down where the team can read and change it. The order (pick, pin, rank) is a policy someone chose. The fallback keeps a launch going when a model goes away.

## See it

The trainer shows these on the chat page; you do not build them.

- **Thinking effort.** Type `gpt-5.5` in **Model**. Set `LAUNCHKIT_EFFORT=low` in `.env` and restart the chat page; send "Plan the Breeze launch for the US, the UK and Germany, with the never-say list and the sizes for each market." and then "A shorter headline for the Breeze feed post.", each in a new conversation. Then `LAUNCHKIT_EFFORT=high`, restart, and the same two. Read time and cost off the `score` lines. Effort reaches the main agent's reply only.
- **One gateway.** One provider's models go in `LAUNCHKIT_DISABLED_MODELS` without warning, and the chat page is restarted. Then the same ask four times, with **Model** set to four models from four providers. One run's trace says `fallback`: `route()` skipped the switched-off pick.

## Stuck?

The answer is on the branch `session-03-routing-step1`.

No model access (offline, or no key)? Set `LAUNCHKIT_FAKE_MODELS=1` in `.env` and restart the chat page. The routing and the trace lines still show; quality, time and cost do not.
