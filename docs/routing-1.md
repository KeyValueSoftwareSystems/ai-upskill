# Routing hands-on 1 · A model for each job

Every job in LaunchKit runs on one model, set once in `.env` as `LAUNCHKIT_MODEL`. A big model does good work but is slow and expensive for small jobs. A small model is cheap, but the work breaks.

In this hands-on you write **`route()`**: one function that picks a model for each job. At the end, launch copy runs on the best writer, research on a mid model, and a quick question on the cheapest one.

## Before you start

```
git checkout session-03-routing
uv sync
uv run launchkit index harbor
uv run launchkit check routing0
```

`check routing0` must say `7 passed`.

In `.env`, set these two lines:

```
LAUNCHKIT_MODEL=gpt-5.5
LAUNCHKIT_SEARCH=saved
```

Start the chat page with `uv run launchkit ui`. Sign in as Maya at Harbor and open the **Trace** tab. Leave the **Model** box empty.

## The three asks

You send these three asks several times. Send each one in a **new conversation**.

1. "Write three headlines for the Breeze feed post." (launch copy)
2. "How are Hydro Flask and Stanley launching bottles this season?" (research)
3. "How many ml is the Breeze?" (one product fact)

## How to read the Trace tab

At the end of each answer:

- `route` says which model did a job, and why. Example: `route  short_text · gpt-5-nano · rank 1`.
- `score` says, for one model, how many calls it made, how long they took, and what they cost.
- `total` adds up the whole answer.
- `quality` says how Harbor's checks ended.

## Break it first

**Round 1: the top model for every job.** `LAUNCHKIT_MODEL=gpt-5.5` is already set. Send the three asks.

- Every `score` line is `gpt-5.5`.
- The research costs the most (about $0.17), then the headlines (about $0.03), then the size (about $0.02).
- The one-line size answer pays the top price.

**Round 2: the smallest model for every job.** In `.env`, change the line to `LAUNCHKIT_MODEL=gpt-5-nano`. Stop the chat page (Ctrl+C), start it again, and send the three asks again.

- The cost drops a lot.
- The work gets worse: weaker headlines, a thin research summary, sometimes the wrong skill.
- It can even be slower: a small model can think for thousands of tokens.

One model cannot be right for every job.

## What is already there

You do not build these. They are listed so you know what changed.

- **Jobs.** Every model call now asks for a model for its job:

  | Job | What it is |
  | --- | --- |
  | `long_text` | the main agent's reply, such as launch copy |
  | `short_text` | the main agent's reply to a short question |
  | `research` | the research helpers |
  | `memory_write` | the memory write |
  | `vision` | the photo checks |

  Pictures and voice-overs are not routed: there is one model for each.
- **The rank lists:** `launchkit/ranking.json`. One list of models per job, best first. Run `uv run launchkit models` to see them, with their prices.
- **The skill's model:** the `ingest_image` skill asks for `gpt-5.5` to read photos, in one line of its `skill.md`.
- **The Model box** is Maya's own choice. **The Switched off box** turns models off for an outage. A switched-off model is not offered in the Model box.
- **The scoreboard:** the `route`, `score`, `total` and `quality` lines. The cost is what the LiteLLM proxy charged.

## Prompt for your coding agent

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

1. In `.env`, empty the line: `LAUNCHKIT_MODEL=`. Stop the chat page and start it again.
2. Send the three asks. Each one now runs on its own model:

   ```
   route  long_text  · gpt-5.5      · rank 1   the headlines
   route  research   · gpt-4.1-mini · rank 1   the research
   route  short_text · gpt-5-nano   · rank 1   the size
   ```

3. **The skill's model.** Attach `samples/shoot/breeze-cap.jpg` with 📎 and send: "Breeze launches next month. Same as Tidal: concepts, then every size." The trace shows `route  vision · gpt-5.5 · skill`. The photo check finds another brand's logo on the cap and stops.
4. **The outage.** Type `gpt-4.1-mini` in the **Switched off** box (no restart). Ask: "What are hikers talking about this week?" The trace shows `route  research · gpt-5-mini · fallback`, and you still get an answer. Clear the box when you are done.

## Prove it

```
uv run launchkit check routing1
```

It must say `8 passed`. The check runs on scripted models, so everyone gets the same result.

## Why it matters

Every model choice trades quality, time and cost. One setting makes that trade once for every job. A rank list per job makes it per job, and the fallback keeps the launch going when a model goes away.

## See it

The trainer shows these; you do not build them:

- **Thinking effort:** the same model thinks a little or a lot (`LAUNCHKIT_EFFORT=low` or `high` in `.env`). A big plan gets better; a short headline only gets slower and dearer.
- **One gateway:** with OpenAI's models switched off, the headlines go to Claude, through the same proxy, with no code change. Gemini and DeepSeek, picked in the Model box, refuse LaunchKit's fixed answer shape, so LaunchKit falls back to `gpt-5.5`.

## Stuck?

The answer is on the branch `session-03-routing-step1`.

No model access? Set `LAUNCHKIT_FAKE_MODELS=1` in `.env` and restart. The `route` lines still show, but the costs and the quality mean nothing.
