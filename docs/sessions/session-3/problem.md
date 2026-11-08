# Session 3 · Agent memory: the problem and the ticket queue

The agent remembered the wrong thing.

Where Session 2 ended: "Nothing remembers yesterday. What should our agents remember, which agent should remember it, and for how long?" Session 3 takes that question as its agenda, but not its old example. The problem below is the production version of it.

## The problem statement

When the room last saw LaunchKit, it served one brand. Nine months later it served forty. Around three hundred marketers used it every day, and a dozen agency teams used it across several brands at once, switching from one client's workspace to another in the same afternoon. Harbor was still the first customer, and Maya was still the one who wrote in first when something felt wrong.

Memory had arrived six months earlier, and it arrived quietly. After the earlier sessions had built tools, skills, subagents and the approval rule, adding memory took one line of configuration: `update_memory_on_run=True`. From that moment, every conversation was mined for facts about whoever was typing, and those facts were stored against their user ID in the project database and loaded back into every later conversation they had. Nobody designed what a saved fact should contain, who it belonged to, or when it should stop being true, because nothing in that one line asked those questions. For three months this looked like a success. The agent seemed to know people, and support tickets went down.

Then the support queue began to fill, and the tickets did not look alike at first. One marketer said the agent kept using a phrase she had told it never to use. Another said it quoted a product fact that had been true in spring but not since. An agency manager said one client's rules had shown up while she was working for a different client. An engineer said a single heavy user's conversations had become slow and expensive, and that the agent had lost track of the brief halfway through a long job. Legal asked where a customer's phone number had come from, and then asked for everything about one user to be deleted by Friday, which turned out to be a harder question than anyone expected. Read together, these were not six bugs. They were one failure seen from six sides: the agent remembered the wrong thing, for the wrong person, for too long, and nobody could say what it knew or prove that it had forgotten.

One line in Harbor's brief tied the whole queue together: the warranty. When memory was switched on, Harbor's bottles carried a two-year warranty. It was five years by the time the queue filled. "Lifetime guarantee" had always been on Harbor's never-say list, and a competitor's website used exactly that phrase. Over one quarter, that single fact was remembered as a wish instead of a rule, remembered twice with no way to tell which version was current, remembered for a brand that never had it, remembered from the competitor's page by a research helper that should never have been allowed to save anything, and stored in the same row as a customer's phone number. Fixing the warranty line properly means answering the question that every product which turns memory on with one line eventually has to answer:

> What should our agents remember, which agent should remember it, for whom, for how long, and how do we know?

- **Cast:** Maya at Harbor · an agency manager on Harbor and Alder · LaunchKit on Agno 3.1.3
- **Running fact:** Harbor's warranty, 2 years → 5 years
- **Starting state:** a checked-in snapshot of the memory database the morning the queue filled (`fixtures/memory-snapshot.db`)

## The ticket queue

Six tickets, worked in order. Tickets 1, 2a and 3 share one cause and one build; so do 2b, 4 and 5.

| Ticket | In Maya's words | Checkpoint |
| --- | --- | --- |
| 1 | "It keeps putting 'lifetime guarantee' in headlines. I told it never to." | A · what one fact holds |
| 2a | "The warranty is five years. It still says two. Sometimes it says both." | A · what one fact holds |
| 3 | "Our agency manager saw Harbor's never-say list come up while working on another brand." | A · what one fact holds |
| 2b | "…and it says lifetime, which we never say." | B · who writes, reads, how long |
| 4 | "It got slow and expensive. Also it forgot the brief halfway through a long job." | B · who writes, reads, how long |
| 5 | "A customer's phone number is in a headline draft. And legal wants everything about one user deleted by Friday." | B · who writes, reads, how long |
| 6 | "Prove it's better now." | Test, then discussion |

### Ticket 1 · Formation

- **What is actually wrong.** Automatic extraction after every run saved the quoted phrase from the never-say list as a preference. It also saved eleven near-duplicate lines about Harbor navy. Automatic learning tends to find something every time it runs.
- **Agno concept.** `update_memory_on_run` vs `enable_agentic_memory`; MemoryManager capture instructions; the memory data model, one row = one fact with topics and `updated_at`.
- **Live moment.** Rerun extraction on her message. Then read the rows.
- **The build (shared with 2a and 3).** Capture instructions: one fact per row, preferences only in user memory, a quoted never-say phrase is a rule, not a wish, no personal data. The Summarize strategy shown on the duplicates, not written.
- **Topics it opens.** Formation · writing style of a fact · consolidating · the four kinds with LaunchKit examples (a preference, the Tidal launch, the warranty, "always attach PNG and PDF") · when a fact is saved.
- **Alternative that would have changed it.** Mem0's extract, compare, merge pass; a filesystem MEMORY.md a human can read line by line.

### Ticket 2a · Fact validity

- **What is actually wrong.** Two rows, no dates, no winner. Memory stored "is", not "was true from". The extraction model usually updates the old row and sometimes leaves both standing; that variance is the demo.
- **Agno concept.** A memory carries `updated_at` but no validity window. Entity memory has dated events (`add_event`) but a fact has no valid-from / valid-to and no "superseded by".
- **Live moment.** "Warranty is five years now, redo the Tidal headline." Row updated, second row added, or a headline citing both.
- **The build.** Brand facts leave user memory. A brand table where one row holds subject, value, scope, source, valid_from, valid_to; a plain-code `get_brand_facts` returns only what is true today.
- **Topics it opens.** Conflicting facts · valid-from / valid-to · on-run save vs background job · "if code can do it, code should", again.
- **Alternative that would have changed it.** Graphiti: time is a property of the edge, with invalidation built in.

### Ticket 3 · Scope

- **What is actually wrong.** Memory is scoped by `user_id` across every session. An agency user is one `user_id` on forty brands. Brand facts were stored as user facts.
- **Agno concept.** Threads by `session_id`, memory by `user_id`; entity memory and learned knowledge with a `namespace`, whose default is global.
- **Live moment.** The agency manager asks for Alder's spring headline and gets Harbor navy and Harbor's never-say list.
- **The build.** Scope on every row; a brand is a namespace; user memory never carries a brand fact.
- **Topics it opens.** Personal vs shared vs tenant · how memory is shared · user, tenant, product.
- **Alternative that would have changed it.** Honcho's per-app, per-user model; multi-tenant keys in Mem0.

### Ticket 2b · Poisoning (same ticket as 2a, second cause)

- **What is actually wrong.** The research subagent read a saved competitor page that says "lifetime guarantee" and wrote it back as a learning. Learned knowledge is shared across users by design.
- **Agno concept.** Propose mode is intended for learned knowledge only, and is not an approval control on its own; enforce approval in application code.
- **Live moment.** Run the competitor skill from Session 2 with `save_learning` in reach; show the poisoned row.
- **The build (shared with 4 and 5).** Every memory write goes through the same "needs approval" branch in `run_tool` as Session 2's outside writes. The subagent keeps `search_web` and loses `save_learning`. A proposed brand fact needs the brand owner's yes.
- **Topics it opens.** Memory poisoning · sharing memory with subagents · the approval gate, which pays Session 2's parked question "ask every time, or remember a yes?"
- **Alternative that would have changed it.** None fixes it alone; the gate is yours in every store.

### Ticket 4 · Scale and cost

- **What is actually wrong.** All of a user's memories are loaded into every turn, and a power user has 600 rows after three months. Session history and summaries are a separate problem being solved with the same hammer.
- **Agno concept.** `num_history_runs`, session summaries, session context; memory optimisation strategies (Summarize); a cheaper model on the MemoryManager; prune by age.
- **Live moment.** Shown, not built: one power user's turn with 600 rows vs after prune and Summarize, in tokens and seconds, measured in prep.
- **The build.** A retention job: prune user memory by age, Summarize the rest; history runs and session summaries for the long job.
- **Topics it opens.** Tiers (always-loaded profile · searched memory · outside provider) · compaction · retention · cost per turn · what loads into the system prompt.
- **Alternative that would have changed it.** File tiers; a bigger context window, and why not.

### Ticket 5 · Personal data and deletion

- **What is actually wrong.** Personal data extracted from a pasted board card; a token Maya pasted once lives in a memory; deleting a user's memories does not delete the session summaries, the decision log or the shared learning they seeded.
- **Agno concept.** Redaction via manager instructions; deletes honour `user_id`; the decision log as an audit trail; the learnings as the deletion surface.
- **Live moment.** Grep the snapshot for the phone number and the token; delete the user; show where she still appears.
- **The build.** Redact at capture (the same instructions as ticket 1); a delete that cascades by `user_id` across memories, summaries, learnings and the decision log.
- **Topics it opens.** Personal data and credentials in memory · deletion cascade · what "forgotten" must mean in a contract.
- **Alternative that would have changed it.** Providers with deletion APIs vs a filesystem you grep; two systems means two deletions.

### Ticket 6 · Benchmarking and the store choice

- **What is actually wrong.** No eval. Nobody can say whether the fixes made recall better or just cheaper.
- **Agno concept.** `get_user_memories` for a debug view. Evals sit outside the framework.
- **The test.** The room scores two candidates, a relational store with a schema you own vs a temporal graph, against tickets 1 to 5 using the choice test: does a fact carry time, who may see it, how is it read back, when is it written, can you forget on demand, can you export and prove it. Then the ops column: self-hosted or SaaS, residency, latency per turn, cost per fact, the exit.
- **Discussion.** The stores side by side (Mem0, Graphiti, Honcho, Cognee, HindSight, SuperMemory, filesystem) · what is used in production and when to use what · LongMemEval, LoCoMo, MemoryAgentBench · the cost of storing vs re-deriving · the rule: one primary store and a schema you own, a second system only when a query the first cannot answer becomes the product.

## Two checkpoints and a test

- **A · What one fact holds** (tickets 1, 2a, 3; about 35 minutes). One cause: a saved row holds text, topics and a timestamp, and nothing about scope, source or time. Build: the fact schema (subject, value, scope, source, valid-from, valid-to) and the writing rule in the capture instructions. Show: Summarize on the navy duplicates.
- **B · Who writes, who reads, how long** (tickets 2b, 4, 5; about 35 minutes). One cause: anyone could write, everything was read, nothing was ever forgotten. Build: one write door through `run_tool` approval, and a retention rule with a cascading delete. Show: the 600-row turn before and after, measured in prep. Pays Session 2's parked "remember a yes?" question.
- **The test · Ticket 6** (about 15 minutes, then the close). Choosing a store is a test on your own tickets, not a feature tour.

The question the room will ask hardest, at ticket 1: can't a better prompt fix it? Instructions lower the error rate; the snapshot shows what three months of a low error rate looks like.
