# Memory ticket 2a · A fact carries when it was true

> "The warranty is five years. It still says two. Sometimes it says both."

When memory went on, Harbor's warranty was two years, and a row said so: "Harbor warranty is 2 years." It has been five years since September. A memory row holds text, topics and `updated_at`: "is", never "was true from … to …". When the fact changes, the manager either rewrites the row, adds a second one, or leaves the old one, and nothing says which is current.

## The slot

- `launchkit/knowledge/brand_facts.py` · `get_brand_facts`. Today it returns nothing.
- `launchkit/knowledge/brand_facts.py` · `set_brand_fact`. Today it changes nothing.
- `launchkit/skills/on_brand_copy/skill.md`: one line in `Uses:` and one step.

The table is ready-made: `brand_facts` in the project database, one row per fact (`brand, subject, value, scope, source, valid_from, valid_to`), with Harbor's warranty seeded as two rows. `_open(settings)` makes and seeds it. The catalogue already lists `get_brand_facts` as a read tool once the slot is built, with the brand bound from the request, as in Session 1: the model never names it.

## Break it first

`uv run launchkit memory reset`, restart the page, sign in as **Maya at Harbor**, press **New conversation** and send:

> The warranty is five years now, redo the Tidal headline.

Watch the Trace's `memory` lines. In prep, 3 runs of 3 rewrote the 2-year row in place ("Harbor warranty is 5 years now, updated from 2 years."). None added a second row, and no headline cited both. The room may see all three outcomes; prep saw one. Open the **Memory** tab and look for any date on the row that says when it became true: there is only `updated`.

## Prompt card, for your coding agent

```
In launchkit/knowledge/brand_facts.py:

get_brand_facts(settings, brand, today=None) -> list[dict]: the brand's rows true on `today` (default
date.today()): valid_from <= today and (valid_to is null or valid_to >= today), ordered by subject.
Each row as a dict with subject, value, scope, source, valid_from. Open the table with _open(settings)
inside contextlib.closing. Remove the @todo mark.

set_brand_fact(settings, brand, subject, value, source, scope="brand", today=None) -> dict: never
overwrite. In one transaction, close the open row for that brand and subject (valid_to = the day before
`today`) and insert a new row from `today` with valid_to null. Return brand, subject, value, source,
valid_from. Remove the @todo mark.

In launchkit/skills/on_brand_copy/skill.md: add get_brand_facts to the Uses line, after
get_brand_details. Change step 1 to: before you state any product fact, call get_brand_facts for the
facts that change over time (warranty, prices, dates) and get_brand_details for the rest. Use only what
they return. A fact from get_brand_facts wins over the brand guide and over anything remembered from
earlier conversations.
```

## Prove it

```
uv run launchkit check mem2a
```

- The warranty is two rows, and only one is true today.
- A date inside the old window gets the old value.
- Updating a fact closes the old row and opens a new one.
- `get_brand_facts` is a read tool bound to the request's brand.

## Run it again

Restart the page. The **Memory** tab now opens with Harbor's brand facts: 2 years from 2025-01-01 to 2026-08-31, 5 years from 2026-09-01, still true, "true today: yes". Send the same ask in a new conversation. The Trace shows:

```
tool      get_brand_facts() → [brand_facts/harbor/warranty] warranty: 5 years (true since 2026-09-01; source: …
```

The headline cites five years, with `brand_facts/harbor/warranty` as its source. The main agent still writes memory after every turn at this point, so a `memory` line may still change the old row. Ticket 2b closes that door.

## Why it matters

Time belongs to the fact, not to the memory. Code can answer "what is true today" the same way every time; a model rereading two rows cannot. If code can do it, code should, again.

The table is LaunchKit's, in the same database: no second memory system. A temporal graph (Graphiti) puts time on every edge; this table does it for the facts we know will change.

## Stuck?

The answer is on the branch `session-3-memory`.
