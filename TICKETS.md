# Session 3: the ticket queue

Nine months after Session 2, LaunchKit serves forty brands and about three hundred marketers. Agency teams work on several brands in one afternoon. Six months ago memory was switched on with one setting, `update_memory_on_run=True`: after every reply an extra model call reads the chat, pulls out facts about the person, and saves them. Every later chat of theirs loads those facts. For three months it looked like a success. Then the support queue filled with the tickets below.

You start from the database that queue left behind. `uv run launchkit setup` put it in place. Open the chat page, press **Memory**, and read what the agent kept for Maya.

How to work a ticket:

- Read the person's words, then what is actually wrong.
- Build the fix with your coding agent. The hints say what to ask for and what to check; they are not the prompt. Open a hint only when you need it.
- "Done" is seen on the chat page, never in a terminal.
- Write your decision in `DECISIONS.md`, a few words. The room compares them after each build.
- Stuck? Move to the next ticket. Every piece ships with a placeholder that runs.

Tickets 1, 2 and 3 share one cause and one build, build A. Tickets 4, 5 and 6 share another, build B. Ticket 7 is worked as a test in the room. Ticket 8 is build C.

The pieces that are already there, and what each does, are in `READY-MADE.md`.

---

## Ticket 1

> Maya, Harbor: "It keeps putting 'lifetime guarantee' in headlines. I told it never to."

**What is actually wrong.** The extractor saved Maya's rule backwards, as a preference for the phrase. It also saved the brand colour eleven times in eleven wordings, once per chat, because nothing checks for a row that already says it. The extractor's instructions are one sentence: save anything that seems useful about the user.

**Done when**

- Sign in as Maya at Harbor, open **Memory**: the rows the extractor saves from a new chat are each one plain fact, and none of them is a quoted phrase from the never-say list.
- Say "Never say 'lifetime guarantee'" in a new chat and read what was saved. Either a rule that it must not be said, or nothing at all. A preference for the phrase is the bug.
- Nothing personal is saved: say a phone number in a chat and the Memory panel does not show it.

<details><summary>Hint 1, a nudge</summary>
The extractor reads one file for its instructions. Find it under <code>launchkit/memory/</code>. Everything it does wrong follows from what that file does not say.
</details>

<details><summary>Hint 2, the approach</summary>
Ask your coding agent for capture rules in <code>launchkit/memory/capture_rules.md</code> that say what a row is (one fact, in plain words, that will still be true next month), what never becomes a row (a quoted phrase from the brand's never-say list, a phone number, an address, a key or token, a one-off instruction about one picture, a yes to one action), and what to do when the same fact is already saved (do not save it again). Check the file reads like instructions a person could follow, not a list of keywords.
</details>

<details><summary>Hint 3, nearly the answer</summary>
Four short paragraphs: what to save, how to word a row, what never to save, what to do with duplicates. Tell the extractor to label each row with a kind (preference, fact about the person, way of working) as a <code>kind:</code> topic, and with a one-word <code>topic:</code> label such as <code>photography</code> or <code>colour</code>; later tickets use those labels. Test it on Maya's sentence and on "the customer is on 555-0142".
</details>

**Decision to write down.** Should a rule the brand already has in its files ever be saved as a memory row too? Yes, or no, and why.

---

## Ticket 2

> Maya, Harbor: "The warranty is five years. It still says two. Sometimes it says both."

**What is actually wrong.** Two brand-fact rows for `warranty` are both open, `2 years` from February and `5 years` from October. Nothing on a row says when it stopped being true, and the prompt lists both as current. Open **Memory** and look at the brand facts table at the bottom: both rows show, with no end.

**Done when**

- In **Memory**, the brand facts table shows the 2-year warranty with an end date and the 5-year warranty as current.
- Ask as Maya for a Tidal headline: it uses five years and never two.
- Record a new brand fact in a chat ("the warranty is now six years"), allow it, and the 5-year row closes the same way.

<details><summary>Hint 1, a nudge</summary>
Brand facts have their own table, <code>brand_facts</code>, with <code>valid_from</code> and <code>valid_to</code> columns. Two methods on it decide what the prompt sees. Read their docstrings.
</details>

<details><summary>Hint 2, the approach</summary>
Ask for two changes in <code>launchkit/memory/brand_facts.py</code>. <code>record</code> closes the open rows for the same subject that started before the new one, by setting their <code>valid_to</code> to the new row's <code>valid_from</code>. <code>current</code> returns, for each subject, one row: the one valid on that day with the latest <code>valid_from</code>. The seed has two open rows for the warranty and no end dates, so the second rule is what fixes the ticket on the database you have. Check with two open rows for one subject that exactly one comes back, and that asking as of an earlier date gives the earlier value.
</details>

<details><summary>Hint 3, nearly the answer</summary>
In <code>record</code>, one UPDATE before the INSERT: set <code>valid_to</code> where the brand and subject match, <code>valid_to IS NULL</code> and <code>valid_from</code> is on or before the new date. In <code>current</code>, filter <code>history()</code> by the two dates, then keep the latest <code>valid_from</code> per subject. Dates are ISO strings in the table; compare them as <code>date</code> objects.
</details>

**Decision to write down.** When a fact changes, do you keep the old row with an end date, or delete it? What does each choice let you answer later?

---

## Ticket 3

> Maya, Harbor: "Our agency manager saw Harbor's never-say list come up while working on another brand."

**What is actually wrong.** Every row is filed under one user id, and Dana works on Harbor and on Alder with the same id. Harbor's rules were saved as her rows, so they load in her Alder chats. Sign in as Dana at Alder and ask for a headline: it comes back in Harbor navy, with Harbor's never-say list applied.

**Done when**

- Sign in as Dana at Alder, open **Memory**: none of her Harbor rows show.
- Ask as Dana at Alder for a spring headline: Alder's colours, Alder's rules, nothing from Harbor.
- A row saved for "everyone at the brand" shows for Maya and for Dana at Harbor, and for nobody at Alder.

<details><summary>Hint 1, a nudge</summary>
Every row carries two labels the door stamps on the way in: <code>scope:user:dana</code> or <code>scope:brand:harbor</code>, and <code>brand:harbor</code>, the brand it was saved at. One function decides which rows a person at a brand reads. It ignores both labels today.
</details>

<details><summary>Hint 2, the approach</summary>
Ask for <code>rows_for</code> in <code>launchkit/memory/store.py</code> to return the person's own rows whose <code>brand:</code> label is this brand, plus the brand's shared rows (filed under the brand's own user id, <code>&lt;brand&gt;:brand</code>), and nothing else. Decide what happens to a row with no brand label at all. Check that Dana's Harbor rows do not load at Alder, and that a brand row loads for everyone at that brand.
</details>

<details><summary>Hint 3, nearly the answer</summary>
In <code>rows_for</code>, read the person's rows and keep those whose <code>brand:</code> label matches this brand; then add <code>get_user_memories(user_id=brand_owner(workspace_id))</code>. Rows with no label are your call: the person's everywhere, or nowhere.
</details>

**Decision to write down.** Rows saved before the brand label existed: are they the person's at every brand, at the brand where they were most likely said, or nowhere?

---

## Ticket 4

> Maya, Harbor: "It's back: 'lifetime guarantee' again, in a Breeze draft. Nobody here said it this time."

**What is actually wrong.** Build A fixed what Maya typed. This time the phrase came from outside. The research helper read a competitor's page, decided "a lifetime guarantee sells" was worth keeping, and saved it with its own tool as a learning every chat at the brand reads. Open **Memory** as Maya and find the row with source `web`, said by `research-helper`.

This ticket is the first fork. Both ways below run in real products. Pick one and build it.

- **Path A, ask first.** Before a row is kept, the chat stops and asks the person: Just me, Everyone at the brand, or Don't keep. The same approval rule Session 2 used for writes.
- **Path B, save when sure.** A small model says how sure it is that the row is a lasting fact about the person, 0 to 1. At 0.7 or more it is kept and the Memory panel shows it with Forget. Below that, nothing. Nobody is asked.

Either way: a row whose source is a web page is never kept, and the helper loses its save tool.

**Done when**

- Run the competitor research skill as Maya: no new row from the web appears in **Memory**, and the Trace tab shows the refusal.
- Path A: say a new preference in a chat; the chat stops and asks; "Don't keep" saves nothing, "Everyone at the brand" shows the row for Dana at Harbor too.
- Path B: say a new preference; it appears in **Memory** without a question, with a Forget button; say "yes, attach them" and nothing appears.

<details><summary>Hint 1, a nudge</summary>
Every save passes <code>decide_save</code> in <code>launchkit/memory/write_door.py</code>. It keeps everything today. The helper's tool is <code>save_learning</code> in <code>launchkit/orchestration/research_team.py</code>.
</details>

<details><summary>Hint 2, the approach</summary>
First, in <code>decide_save</code>, refuse any row whose topics include <code>source:web</code>. Then the fork. Path A: call <code>approve("keep_in_memory", {...})</code> with the row's text, its kind and a <code>choices</code> list of the three answers; the page shows one button per choice and returns the chosen text; map the three answers to <code>Decision(True, "user")</code>, <code>Decision(True, "brand")</code>, <code>Decision(False, None)</code>. Path B: build <code>confidence(text, settings)</code> as one short model call that returns a number 0 to 1, keep at 0.7 or more, never call <code>approve</code>. Last, take <code>save_learning</code> out of the helper's tools in <code>build_research_agent</code>. Check that a web-sourced row never lands, whichever path.
</details>

<details><summary>Hint 3, nearly the answer</summary>
Path A: the question needs the row's text, its kind and the three choices in <code>inputs</code>; anything other than the first two answers is a no. Path B: get the memory_write job's model from <code>Jobs</code>, ask it for only a number for "how sure are you that this is a lasting fact about the person", parse it, and treat a parse failure as 0. For the helper, take the save tool out of the list in <code>build_research_agent</code>.
</details>

**Decision to write down.** Which path, and what the person being remembered would expect.

---

## Ticket 5

> Maya, Harbor: "It got slow and expensive. And it forgot the brief halfway through a long job."

**What is actually wrong.** Every row a person may read goes into every prompt. One power user has hundreds. The Context tab shows the memory tokens on every turn. The long job is a different problem with the same symptom. The agent rereads only the last five messages of a chat, so a brief given in message one is gone by message eight.

**Done when**

- Open **Memory** as Maya and note the token count. Build the index; the count drops to a few lines, one per topic.
- Ask as Maya for a Breeze headline using her photo rule: the Trace tab shows a `recall` call for the photography topic, then the headline uses her rule.
- Rows older than the retention limit go when `uv run launchkit retention harbor` runs; brand rows stay.

<details><summary>Hint 1, a nudge</summary>
The prompt's memory section is built by <code>memory_index</code> in <code>launchkit/memory/index.py</code>, and the agent already has a <code>recall</code> tool that calls <code>recall</code> in the same file. Both are placeholders. <code>prune</code> in <code>retention.py</code> is the third.
</details>

<details><summary>Hint 2, the approach</summary>
Ask for <code>memory_index</code> to return one line per topic, <code>- &lt;topic&gt;: &lt;n&gt; rows · recall("&lt;topic&gt;")</code>, topics in alphabetical order, each line at most 80 characters, with <code>topic_of</code> deciding a row's topic. Ask for <code>recall</code> to return every row under one topic in full, each with its kind, and for an unknown topic a line that names the topics that exist. Ask for <code>prune</code> to remove the person's rows whose <code>valid_from</code> is older than the limit and to leave brand rows alone. Check the index is shorter than the full list on the seed, and that recall of one topic returns only that topic.
</details>

<details><summary>Hint 3, nearly the answer</summary>
Group rows with <code>topic_of</code> into a dict of lists; "1 row" and "n rows" differ in the word; <code>memory_section([row])</code> already formats a row, so recall can reuse it without the scope and date. For the long job, the room discusses compaction; building it is a stretch: keep the sentences in the chat that contain never, always, must or only, and put them back into every prompt.
</details>

**Decision to write down.** An index means the agent can miss a fact it would have been handed. What in the index line makes it look?

---

## Ticket 6

> Maya, Harbor: "A customer's phone number is in a headline draft. Legal asked where it came from, and wants everything saved about that customer gone by Friday."

**What is actually wrong.** A phone number and a pasted token were saved as facts about Maya. Deleting her rows is not enough, because the number also sits in a chat summary and in a shared learning. Try it. `uv run launchkit forget harbor maya 555-0142` removes one row and reports zero summaries, and in **Memory** the brand's learning still has the number.

**Done when**

- `uv run launchkit forget harbor maya 555-0142` reports the rows, the summaries and the learnings it cleared, and a second run reports zeros.
- Search the database file afterwards (`grep -c 555-0142 data/sessions.db`): the number is nowhere, in the rows or in the file's free space.
- Dana's rows are untouched.

<details><summary>Hint 1, a nudge</summary>
<code>forget</code> in <code>launchkit/memory/forget.py</code> knows one of the three places. The other two are the session summaries (<code>get_sessions</code>, each with a <code>summary</code>) and the brand's rows under the brand's own user id.
</details>

<details><summary>Hint 2, the approach</summary>
Ask for <code>forget</code> to clear three places and count each: the person's rows containing the text; every session summary at the brand that contains it (blank the summary text and upsert the session); every brand row that contains it. Check that other people's own rows are never touched, even when the text is in them.
</details>

<details><summary>Hint 3, nearly the answer</summary>
Sessions come from <code>store.get_sessions()</code>; a summary is <code>session.summary.summary</code>; take out the sentence that holds the text and call <code>store.upsert_session(session)</code>. Brand rows come from <code>get_user_memories(user_id=brand_owner(workspace_id))</code>; delete with <code>delete_user_memories</code>. Keep to this brand: a person's rows carry a <code>brand:</code> label. SQLite keeps deleted bytes in free pages until <code>VACUUM</code> runs. Then redaction at capture, the stretch: a rule in <code>capture_rules.md</code> that a phone number or a token is never a row.
</details>

**Decision to write down.** What does "forgotten" have to mean in Harbor's contract: the row, every copy, or every copy plus the chat it came from?

---

## Ticket 7

> Product lead: "Harbor asks if this will happen again. Before we say no, how do we know the fixes worked and did not just make it cheaper?"

**What is actually wrong.** There is no test. Nobody can say whether memory now recalls the right things, or only fewer things.

This ticket is worked in the room, with no code. Two stores are scored on tickets 1 to 6: a table with a schema you own, which is what you built, and a temporal knowledge graph. For each, answer: does a fact carry time, who may see it, how is it read back, when is it written, can you forget on demand, can you prove it works. Then the operations column: self-hosted or a service, latency per turn, cost per fact, how you would leave.

**Decision to write down.** Which store you would ship for Harbor, and the one question it answers badly.

---

## Ticket 8

> Ops: "Monday 09:10 the top model was down for 40 minutes. Every ask failed. The bill has tripled since memory shipped."

**What is actually wrong.** One setting, `LAUNCHKIT_MODEL`, gives every job the same model: the launch copy, a one-line answer, the research helper, the extractor, the photo check. When that model is down, everything is down. The Trace tab shows a `route` line per job and a `call` line per model call, and a scoreboard at the end of every turn. Run two asks and read it.

This ticket is the second fork.

- **Path A, move on.** When the chosen model fails, try the next model on the job's list and say so in the trace. The launch carries on.
- **Path B, stop clearly.** Retry the same model once, then stop with an error the person can read. Nothing silently moves to a model nobody chose.

**Done when**

- With `LAUNCHKIT_MODEL` empty, the Trace tab shows a different model per job, each with its rank as the reason; `uv run launchkit models` shows the order.
- Attach a photo and run the ingest skill: the vision job runs on the model its skill pins, reason `skill`.
- Put the top model in `LAUNCHKIT_DOWN_MODELS` in `.env` and restart, so every call to it fails the way an outage does. Path A: the trace says `fallback` and the ask completes on the next model. Path B: the ask stops with an error that names the model. (`LAUNCHKIT_DISABLED_MODELS` is different: a model there leaves the list before any call.)

<details><summary>Hint 1, a nudge</summary>
Two functions in <code>launchkit/adapters/routing.py</code>: <code>route</code> decides the list before any call, <code>on_failure</code> decides what happens after one fails. <code>rank_list</code> in <code>ranking.py</code> already reads the file.
</details>

<details><summary>Hint 2, the approach</summary>
Ask for <code>route</code> to return, in order: the person's pick when there is one and the job is a main job (long text or short text); the skill's pin for the job; the job's rank list with disabled models left out, reasons "pick", "skill", "rank 1", "rank 2" and so on, with duplicates removed. A main-reply ask that is a short question (ends with a question mark, twelve words or fewer) becomes <code>short_text</code>. Then <code>on_failure</code> for your path: A returns the next model that remains, or None when nothing does; B returns the same model once more, then None. Check it by putting a model in <code>LAUNCHKIT_DOWN_MODELS</code> and watching the trace.
</details>

<details><summary>Hint 3, nearly the answer</summary>
Build the list as pairs, then drop a name you have already added. <code>MAIN_JOBS = ("long_text", "short_text")</code>. For path B, count how many times the failed model appears in <code>tried</code>.
</details>

**Decision to write down.** Which path, and what Maya would want in the middle of a launch: a different model, or a clear error.
