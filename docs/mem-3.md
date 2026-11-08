# Memory ticket 3 · A brand is a namespace

> "Our agency manager saw Harbor's never-say list come up while working on another brand."

Memory is kept by `user_id`. Dana, the agency manager at Fieldnote, is one `user_id` on Harbor and on Alder. Her rows hold Harbor's colours, sizes and never-say list, with nothing marking the brand, so they load on Alder too. Shared learnings and entity facts sit in Agno's default namespace, `"global"`: every brand reads them.

## The slot

- `launchkit/memory/scope.py` · `brand_fact`. Today it returns None for every row.
- `launchkit/agents/main_agent.py` · `build_main_agent`: the main agent's `learning_machine(settings)` gets the brand's namespace.

`brand_words(workspaces_dir)` is ready-made: every never-say phrase, colour name and code, and size in every brand's `rules.yaml`, and every subject in a brand's `brand_facts.yaml`. The main agent already leaves out any row `held_back` names, and the Trace and the Memory tab already show it.

## Break it first

`uv run launchkit memory reset`, restart the page, pick **Brand: Alder** and **Person: Dana**, press **New conversation** and send:

> Which phrases should I keep out of Alder's spring copy?

The reply lists Harbor's never-say list: "lifetime guarantee", "eco-friendly", "sustainable", "unbreakable", "cold forever", "fully dishwasher-safe". Alder has no never-say list; open `workspaces/alder/rules.yaml` and check.

The Trace says `memory loaded 18 rows`: all of hers, Harbor's included. Open the **Memory** tab: "Never say 'lifetime guarantee', 'eco-friendly', …" is one of her rows, word for word the list in the reply. Beside it: "Prefers navy #1F3A5F as the lead colour.", "Sizes needed: 1080x1080, 1080x1350…". Which brand are they about? The rows can't say.

A second ask shows the same leak in colours and sizes:

> Which colour should lead Alder's spring poster, and which sizes do I need?

Alder's poster size (2480x3508) in none, and navy #1F3A5F as the lead colour in 2. Alder's colours are moss, slate and birch.

## Prompt card, for your coding agent

```
In launchkit/memory/scope.py, brand_fact(text, settings) -> str | None: for each word in
brand_words(settings.workspaces_dir), if the lower-cased text contains it as a whole word (not inside a
longer word, and a colour code not after another #), return
'a brand fact ("<word>"): it belongs to the brand, not the person'. Else return None.
Remove the @todo mark.

In launchkit/agents/main_agent.py, build_main_agent: pass the brand to the learning machine,
learning=learning_machine(settings, namespace=ws.id), so learned knowledge and entity memory are kept
per brand instead of in "global".
```



## Prove it

```
uv run launchkit check mem3
```

- From the snapshot, the agency manager's Harbor rows stay out of Alder; her own preferences still load.
- Maya's inverted rule and stale warranty row are not loaded.
- The main agent's learnings sit in the brand's namespace.
- A brand namespace keeps learnings apart.



## Run it again

Restart the page. Same brand, same person, new conversation, same ask. The Trace:

```
memory    loaded 13 rows for this person · held back 5 that name a brand fact or personal data · 204 tokens in the prompt
```

The **Memory** tab's "not loaded because" column names the word each held-back row matched. Switch to **Maya at Harbor**: 15 of her 39 rows are held back now, the eleven navy rows, the inverted rule and the 2-year warranty among them. Her phone and token rows still load; ticket 6 deals with them. Harbor's navy and never-say list still reach every Harbor turn, from Harbor's own files. In prep, on the finished branch, all 3 Alder headlines were about the Ridge Skillet, with no Harbor words.

Not caught: "Headlines up to six words", "Audience is weekend hikers…". No word from a brand file is in them. Code holds back what the brand files name; a habit written in plain words still travels.

## Why it matters

Three tickets, one cause: a row holds text, topics and a timestamp, and nothing about scope, source or time. Ticket 1 said what a row may hold, 2 gave a fact its time, and this one gives it its owner. Personal, shared, tenant: decide for every row which one it is.

## Stuck?

The answer is on the branch `session-3-memory`.