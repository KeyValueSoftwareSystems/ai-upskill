# Memory ticket 5 · How much is read, and for how long

> "It got slow and expensive. Also it forgot the brief halfway through a long job."

Every row about a person is loaded into every turn. Tomas, a heavy user, has 600 after three months: marketing trivia, none of it ever forgotten. And a long job is a different problem being solved with the same hammer: the brief from turn 1 leaves the history window, and only an accident keeps it.

## The slot

- `launchkit/memory/retention.py` · `retain`. Today it prunes nothing.
- `launchkit/agents/main_agent.py` · `build_main_agent`: three history runs and a session summary.

Ready-made: `summary_manager` and `summary_text` in `launchkit/memory/long_term.py`. Agno skips the summary when an agent writes its own system message, so LaunchKit already adds it to the prompt's memory section once there is one. `scripts/retention_job.py` calls `retain` and prints the table.

## Break it first

`uv run launchkit memory reset`, restart the page, sign in as **Tomas at Harbor**, new conversation:

> Write one headline for the Tidal poster.

The Trace says `memory loaded 600 rows · about 11,300 tokens in the prompt`; so does the Context tab's memory row. In prep, before ticket 4, that turn sent **39,611 tokens**: the main call, plus Agno's extraction call, which also carries all 600 rows. It took 7 to 9 s.

The long job: as **Maya at Harbor**, in one conversation, send these eight messages one by one (they are also in `scripts/memory_evidence.py`, `LONG_JOB`):

1. Here is the Tidal launch brief. Four tasks: 1) what hikers are talking about this season, 2) how five competitors are launching, 3) every Harbor size of the approved poster, 4) hand it back on the board. Deadline: Friday 13 November. Keep the lid out of all copy: it changes before launch. Just confirm you have it, nothing else yet.
2. Which of our placements does the web banner go on?
3. Give me three moods for a Breeze shoot.
4. What is our headline word limit?
5. Suggest a calm tagline for the Breeze colourway.
6. What colours does Harbor use?
7. Write one line for a Tuesday feed post about weekend hikes.
8. Back to the Tidal brief: list its four tasks, the deadline and the copy rule.

By turn 8, turn 1 has left the window of five turns. In prep, on the starting code, the brief still came back in 3 runs of 3: the after-every-turn extraction had saved the whole brief as a permanent row about Maya. The forgetting was hidden by keeping the brief in the wrong store, forever. After ticket 4 nothing saves on its own, and the window is all there is.

## Prompt card, for your coding agent

```
In launchkit/memory/retention.py, retain(manager, days, summarise_over, apply, now=None) -> list[dict]:
cutoff = (now or time.time()) - days * 86400. For every user_id in manager.db.get_user_memories():
take that person's rows (user_memories(manager.db, user)); the old ones are those with updated_at
before the cutoff. When apply, delete them: manager.db.delete_user_memories([ids], user_id=user).
If more than summarise_over rows are left and apply, fold them with
manager.optimize_memories(user_id=user, strategy=MemoryOptimizationStrategyType.SUMMARIZE, apply=True).
Append {"user", "before", "tokens_before", "pruned", "after", "tokens_after"} (tokens() is in the
file). Without apply, write nothing and report what it would do. Remove the @todo mark.

In launchkit/agents/main_agent.py, build_main_agent: num_history_runs=3 (was 5), and add
session_summary_manager=summary_manager(settings, trace, model) if model is not None and not
isinstance(model, FakeModel) else None. The fakes are scripted for the conversation only.
```

## Prove it

```
uv run launchkit check mem5
```

- The main agent keeps three turns and a summary, written by the cheaper model.
- The summary is put in the prompt.
- Retention prunes by age, and writes nothing without `--apply`.
- Retention never runs in a turn.

## Run it again

The retention job, in the terminal: it runs on a schedule, never in a turn.

```
uv run python scripts/retention_job.py --days 90           # what it would do; nothing written
uv run python scripts/retention_job.py --days 90 --apply   # prune, then Summarize whoever still has more than 100 rows
```

In prep: Tomas 600 rows → 309 pruned → 291 left → Summarize → one row of about 1,170 tokens. Restart the page and ask Tomas's headline again: `memory loaded 1 rows · about 1,200 tokens`. In prep that turn sent **2,361 tokens**, but took **about 13 s, not less**. The session summary runs after every turn on `gpt-5-nano`, a reasoning model, and Agno counts its tokens in the turn. Point at the tokens, not the clock: the small model is cheaper, not faster.

The long job again, in a new conversation: the **Memory** tab's session summaries show the running summary, and turn 8 reads from it. In prep, on the finished branch, the brief came back in full in 1 run of 3; twice the summary dropped the deadline or the lid rule. A summary is short because it leaves things out.

## Why it matters

What is always loaded, what is searched, what is summarised, and when anything is forgotten are four decisions, not one switch. The 600 rows were a retention problem; the lost brief was a conversation problem. Ticket 5 gives each its own answer: a job on a schedule for the first, a summary on the session for the second.

## Stuck?

The answer is on the branch `session-3-memory`.
