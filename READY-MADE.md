# What is already built

Everything on this branch that has nothing to do with the solution you build is already there. This table says what each piece does, which ticket it serves, and where the idea is explained in the reference. Every file below opens with the same note.

| File | What it does | Ticket | Reference page |
| --- | --- | --- | --- |
| `launchkit/memory/store.py` | `MemoryStore`, the one door every saved fact passes. It stamps who said it, where it came from, who may read it and when it became true, asks the write door, and writes a trace line. `rows_for` decides what one person at one brand reads (a slot). | 1 to 6 | 1 Where a fact lives |
| `launchkit/memory/capture_rules.md` | The extractor's instructions. One sentence today (a slot). | 1 | 3 Formation |
| `launchkit/memory/brand_facts.py` | The `brand_facts` table with `valid_from` and `valid_to`, the `record_brand_fact` tool, and the prompt's brand facts section. `record` and `current` are slots. | 2, 3 | 1, 7 Lifetime |
| `launchkit/memory/write_door.py` | `decide_save`, called for every row before it is kept (a slot, and the first fork). | 4 | 3 Formation |
| `launchkit/memory/index.py` | `memory_index` for the prompt and the `recall` tool (slots). `topic_of` names a row's topic. | 5 | 6 Reading memory back |
| `launchkit/memory/retention.py` | `prune`, old rows out (a slot). | 5 | 7 Lifetime |
| `launchkit/memory/forget.py` | `forget`, every copy of a fact out (a slot). | 6 | 7 Lifetime, 4 What never goes in |
| `launchkit/orchestration/research_team.py` | The research helper, with the `save_learning` tool it had when memory shipped. | 4 | 5 Scope |
| `launchkit/agents/main_agent.py` | Wires memory into the main agent: the extractor after every reply, the memory and brand facts sections of the prompt, the `recall` and `record_brand_fact` tools, one model per job. | all | 1, 11 |
| `launchkit/agents/prompt.py` | The prompt's sections in order: rules, task, brand facts, memory, facts. | 1, 5 | 6 |
| `launchkit/adapters/ranking.py`, `launchkit/ranking.json` | The rank file: three scores per model per job, weights per job, totals, `rank_list`. | 8 | 12 Rank lists as data |
| `launchkit/adapters/routing.py` | `route` and `on_failure` (slots, and the second fork). | 8 | 13, 14 |
| `launchkit/adapters/jobs.py` | `Jobs`: runs a job on the model `route` names and does what `on_failure` says when it fails. One `route` line per choice, one `call` line per model call. | 8 | 11 Jobs and the scoreboard |
| `launchkit/adapters/models.py` | Builds a model by name through the proxy, and reads what each call cost from the proxy's answer. `fake:down` is a model that is always down. | 8 | 15 Gateway |
| `launchkit/trace.py` | The trace lines for memory (`memory kept`, `memory not kept`) and routing (`route`, `call`, `score`, `total`). | all | 11 |
| `launchkit/web/app.py`, `launchkit/web/index.html` | The chat page: the Memory panel with Forget, choice buttons on a question, memory tokens in the Context tab, `GET /models`. | all | 6 |
| `workspaces/alder/` | Alder, the second brand. Dana, the agency manager, is in `alder/users.yaml` and in `harbor/users.yaml`. | 3 | 5 Scope |
| `samples/memory/seed.yaml`, `seed.db`, `scripts/build_seed.py` | The starting state the room inherits, and the script that built it in prep. | all | |
| `launchkit/cli.py` | `setup`, `forget`, `retention`, `models`, and `ui --reload`. | | |

## The Memory panel

<a id="memory-panel"></a>

Press **Memory** on the chat page. It shows, for the person and brand picked in the header, every row that person's chats load: the text, its kind, who may read it, where it came from and who said it, and since when. Under it, the brand's facts as the agent reads them today. The line at the top says how many tokens those rows add to every prompt. **Forget** removes one row, and only that row. The panel reads `GET /memories/{brand}/{person}`, which calls `rows_for` and `BrandFacts.current`.

## The scoreboard

After every turn the Trace tab ends with one `score` line per model (calls, seconds, dollars, the jobs it did) and a `total` line. The dollars come from the proxy's `x-litellm-response-cost` header when it sends one, else from `launchkit/adapters/pricing.py`. `uv run launchkit models` prints the rank file.
