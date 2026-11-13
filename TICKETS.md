# Session 4: one feature request, built in stages, then one ticket

Four months after the memory work, LaunchKit serves forty brands and about three hundred marketers. Agency teams work on several brands in an afternoon.

File handling never got the attention memory did. It was written when LaunchKit served one brand and has not changed since. Every poster, every resized version and every voice-over goes into one folder under `data/`, named by the millisecond it was made. Uploads go into another shared folder, keyed by the name of the file the person attached. Nothing on disk records which brand or which conversation owns any of it.

There are also no general file tools. `launchkit/tools/` has `generate_image`, `resize_poster`, `text_to_speech`, `save_memory`, `search_web` and the brand lookups, and nothing that reads, lists, writes or searches a file. Every artifact is written by a tool that already knows its own output path, and the agent cannot go back and look at any of it. Session 2's research team is the clearest case: `research_many` fans five subagents out over a list of competitors, each one searches the web, and what comes back is a paragraph in the chat that nobody writes down.

Breeze's launch week was last week. Maya and Sam made Breeze concepts, a reviewer threw two out, the winner went to every Harbor size and Sam added a voice-over. At Ember, Jonas made his autumn posters the same week. All of it landed in the same three folders.

You start from what that week left behind. `uv run launchkit setup` puts it in place. Open the chat page as Maya at Harbor and look at the **Files** panel.

## The feature request

> Harbor, in the renewal call: "We want the agent to keep its work. Drafts, plans, the artifacts it makes, so we can come back the next day and ask for the thing it already made instead of asking for it again."
>
> "Done, for us, means four things. I can come back to the same campaign the next day and get the file it already made, not a new one. I only see finished work, not its drafts. Nobody outside Harbor can see any of it, because Breeze is under embargo until the fourteenth. And I can see what it made for me, next to the message where I asked, because right now things it produces never show up in the chat and we cannot tell whether it did the work."

Those four sentences stay on the board. Every acceptance criterion the room writes has to trace back to one of them.

## How to work this session

This is not a queue of complaints. The room scopes one feature request together and builds it in stages. Each stage runs like red and green in test-driven work: something fails on the chat page, the room argues what to do about it and writes the acceptance criteria for it, the lead explains the prompt and runs it, and that stage's checks go green. The next failure then appears on top of what you just built. When the last stage ships, one ticket arrives.

- Read each stage below and watch it fail on the chat page before anyone explains it.
- The room writes each stage's criteria before that stage's build, one to four at a time. They are the test; there is no separate test at the end. `uv run pytest checks/test_files.py -m stage1` runs one stage's checks.
- Build with your coding agent. The hints say what to ask for and what to check in its answer. They are not the prompt. Open one only when you need it.
- "Done" is seen on the chat page, never in a terminal.
- Write your decision in `DECISIONS.md`, a few words. The room compares them after the build.
- Stuck? Move on. Nothing before your stage is touched by it, and the lead's prompt for the stage is the backup.

The six stages share one cause: nothing decides which files a request owns. Stages 1 to 5 each end in a build and stage 6 is a short discussion with none. The ticket at the end is its own build.

What is already there, and what each piece does, is in `READY-MADE.md`.

---

## Stage 1 · Where the work lives, and the file tools

> Maya, Harbor: "Give me Monday's approved brief." She gets a brand new one.

**What is actually wrong.** The agent has no file tools at all. Every tool that writes a file already knows its own output path, all of those paths are shared folders, and nothing records which conversation a file belongs to or which version anyone approved. There is no way to ask for yesterday's work because the agent cannot look at anything it made.

**Done when**

- Sign in as Maya at Harbor, ask for a poster, and the **Files** panel shows it under this conversation rather than in a folder shared with every brand.
- Ask for the same thing in a second conversation. The two sets of files do not mix.
- The workspace name comes from the request. Nothing the model writes can change which folder a file lands in.
- Ask the agent to write the Breeze brief, then in the same conversation ask for the brief you just made. You get that file back, not a new one.

<details><summary>Hint 1, a nudge</summary>
<code>launchkit/brands/request.py</code> already resolves a brand to a folder, and refuses a bad one. Nothing does the same for a conversation. Look at how <code>Pictures</code> in <code>launchkit/memory/attached_pictures.py</code> scopes itself, because one feature already solved this for one file type and nobody generalised it. Then look at <code>build_catalogue</code> in <code>launchkit/agents/main_agent.py</code>, which is where a tool becomes something the agent can call.
</details>

<details><summary>Hint 2, the approach</summary>
Ask your coding agent for a <code>Workspace</code> in <code>launchkit/files/workspace.py</code> that takes the brand and the conversation from the request and gives back one folder with drawers inside it: uploads, work, outputs, competitors. Then three tools on top of it, <code>read_file</code>, <code>list_files</code> and <code>write_file</code>, registered with the agent. Check its answer resolves the folder from the request object and never from an argument a tool passes in, and that the drawers are named in one place rather than spelled out at each call site.
</details>

<details><summary>Hint 3, nearly the answer</summary>
One class, four or five lines of real work: the root is <code>settings.data_dir / "files" / brand / conversation</code>, and the brand's own files are <code>settings.workspaces_dir / brand</code>, kept outside it, a method per drawer, and <code>mkdir(parents=True, exist_ok=True)</code> on first use. Each tool is a few lines that joins its path onto the root and reads or writes. Build only that: nothing here has to decide whether a path is safe yet, because that is a later stage. The drawers decide what the panel shows later, so put finished work in <code>outputs/</code> and drafts in <code>work/</code> now.
</details>

**Decision to write down.** Who names the workspace, and what stops the model from naming it?

---

## Stage 2 · How the agent finds a file

> Maya, Harbor: "The brief says to avoid the lifetime-guarantee framing. Where did that come from?"

**What is actually wrong.** The agent can list and read, so to answer it reads all five competitor briefs into its context, costs a fortune and still answers vaguely. There is no search, and a search that returns whole files would have the same problem as reading the folder.

**Done when**

- Ask where a line came from. The trace shows one search and one or two line reads, not every file in the folder.
- The answer names the file and the line.
- A search over a folder with a large binary in it still returns in a moment, and says when it stopped early.

<details><summary>Hint 1, a nudge</summary>
Ask the agent where the lifetime-guarantee line came from, then open the Context tab and read what the tool results cost. That number is what this stage has to bring down.
</details>

<details><summary>Hint 2, the approach</summary>
Ask your coding agent for <code>search_files</code> in <code>launchkit/tools/search_files.py</code>, capped from the start: a path, a line number and a short snippet per match instead of the file, a limit on matches, skip anything that is not text, skip anything over a size limit, and a line in the result saying it stopped early. Register it with the agent. Check the answer returns the path, the line number and the snippet as separate fields rather than one blob of text, because the agent has to be able to read just that line next.
</details>

<details><summary>Hint 3, nearly the answer</summary>
Roughly fifteen lines of Python, one match per line as <code>path:line: snippet</code>. Walk the workspace, skip files whose suffix is not text or whose size is over the limit, read line by line, keep the first N matches with their line numbers and about eighty characters either side, and return a flag when you stopped. It is deliberately not a wrapper around <code>ripgrep</code>: <code>rg</code> is not installed by default on any of the three operating systems, and nobody should spend session time installing one. Most coding editors do bundle their own copy for speed, which is worth knowing and is not what we need here.
</details>

**Decision to write down.** Search the text, or build an index? Name the cost of the one you did not pick.

---

## Stage 3 · Who may touch which file

> Jonas, Ember: "I asked about `../../harbor/k7c1/campaign-brief.md` and it read it to me."

**What is actually wrong.** Every segment of that path is legal. Nothing resolves it before using it, so a path that looks local reaches a sibling folder. Separately, the chat page lists every file written under `data/` since the run began, whoever is signed in, and nothing on that route goes through a file tool at all.

**Done when**

- Sign in as Jonas at Ember and ask for a path with `..` in it. The agent refuses, and the Trace tab shows the refusal with the tool name and the reason.
- The same for an absolute path, for a symbolic link that points out, and for a folder whose name starts the same way as the real one. `t3a9-old` is not `t3a9`.
- A legitimate read of Ember's own brand book still works. A fence that is too tight is also a defect.
- Nothing made for Harbor appears in Ember's **Files** panel or downloads from Ember's session.

<details><summary>Hint 1, a nudge</summary>
Four callers need the same answer: the file tools, the search, the page's file list and the download route. Find all four before writing anything, because a check that only one of them calls is not a fence.
</details>

<details><summary>Hint 2, the approach</summary>
Ask your coding agent for one function in <code>launchkit/files/paths.py</code> that takes a workspace root and a path and either returns the real location inside it or raises. Check that it resolves first and compares after, and that the comparison is between resolved paths rather than between strings. Ask what its answer does with a symbolic link, and with <code>t3a9-old</code> when the conversation is <code>t3a9</code>.
</details>

<details><summary>Hint 3, nearly the answer</summary>
<code>Path.resolve()</code> on both, then compare with <code>is_relative_to</code>. String prefix matching is the bug: <code>"/data/files/ember/t3a9-old".startswith("/data/files/ember/t3a9")</code> is true. Raise your own error so the tool layer can turn it into a refusal on the trace rather than a stack trace in the chat.
</details>

**Decision to write down.** May one person at a brand reach another person's conversation at that brand? Yes or no, and what breaks either way.

---

## Stage 4 · How a file gets changed

> The reviewer, on Breeze: "Take out the lifetime-guarantee line." Two other paragraphs come back reworded.

**What is actually wrong.** The only way to change a file today is to write the whole thing again, so the model rewrites everything and drifts in the parts nobody asked about.

**Done when**

- Ask for one line to change. That line changes and nothing else in the file does.
- Ask for a line that is not there. The agent says so instead of writing something.
- Ask for text that appears twice. The agent says so instead of guessing which one.

<details><summary>Hint 1, a nudge</summary>
There are five ways to change a file: write it all again, replace a line range, replace an exact piece of text, apply a patch, or run a shell command. Four of them can change the wrong thing without telling you. Work out which, then pick.
</details>

<details><summary>Hint 2, the approach</summary>
Ask your coding agent for one function in <code>launchkit/tools/edit_file.py</code> that takes a path, the old text and the new text, and refuses rather than guessing. Check its answer refuses in two separate cases, not one: the old text missing, and the old text appearing more than once. Ask it what happens when the file changed since the agent last read it, and keep the answer; the ticket comes back to it.
</details>

<details><summary>Hint 3, nearly the answer</summary>
<code>content.count(old)</code> first. Zero means refuse and say so. More than one means refuse and say how many. Exactly one means replace and write. Appending is not part of this tool; that question arrives at the fork after the ticket.
</details>

**Decision to write down.** What must an edit tool check before it writes? Name both checks, and which one you built.

---

## Stage 5 · What gets recorded when the agent produces something

> Maya, Harbor: "I asked for five competitor briefs. The chat shows one Ember poster and nothing else."

**What is actually wrong.** `new_files` in `launchkit/web/app.py` finds the turn's artifacts by globbing all of `data/` for anything modified since the run started, filtered to picture and sound types. Two lines, four defects:

1. No workspace filter, so a poster Ember generated during Maya's turn appears in Maya's chat.
2. No `.md` in the media list, so a brief can never appear at all.
3. Selection by modification time rather than by who wrote the file, so anything else that touched disk counts.
4. The list is assembled by the web layer after the run, so a turn that crashes halfway saves its error and loses every artifact it made on the way.

**Done when**

- Ask for something that writes a `.md` file. It appears in the **Files** panel.
- Nothing another brand produced during the same minute appears in Maya's panel.
- Each entry says which message asked for it and which tool wrote it.
- Make a turn fail partway on purpose. The artifacts it wrote before the failure are still listed.

<details><summary>Hint 1, a nudge</summary>
Read <code>new_files</code> and <code>_worker</code> in <code>launchkit/web/app.py</code> together. Look at what happens on the exception paths, and at what is written to the conversation in the <code>finally</code> block.
</details>

<details><summary>Hint 2, the approach</summary>
Ask your coding agent for a record in <code>launchkit/files/record.py</code>, written by whoever produces an artifact rather than collected afterwards, carrying the session, the message, the tool call and the writer. Then change the page's file list to read that record instead of scanning the disk. Check its answer writes the entry at the moment the file is written, not at the end of the turn, because that is the only version that survives a crash.
</details>

<details><summary>Hint 3, nearly the answer</summary>
One <code>record(path, by, message_id)</code> call inside each writing tool, and <code>new_files</code> replaced by a read of the record for this conversation. Keep the entry small: the relative path, the writer, the message, the time. The chat page then shows what the agent made rather than what the disk happened to change.
</details>

**Decision to write down.** Who writes the record, and why not the main agent at the end of the turn?

---

## Stage 6 · What happens to shared files

> Harbor's brand book has a different tone section this week, and nobody at Harbor edited it.

**What is actually wrong.** One job tidied it while doing something else, and every job since has used the tidied version. The brand's shared files sit in the same tree as the conversation's work and nothing says they are different.

**Done when**

- The agent reads `workspaces/harbor/brand-book.md` and `rules.yaml` normally.
- The agent cannot write either one, and a refused write shows on the trace with the reason.
- A legitimate read of a shared brand file still succeeds.

<details><summary>Hint 1, a nudge</summary>
Once stage 3's check exists this is cheap. The question is where the rule belongs: in the check, in the tool, or in the layout.
</details>

<details><summary>Hint 2, the approach</summary>
Ask your coding agent to mark the brand's own files read-only to the agent, in one place. Check its answer does not special-case file names in each tool, and ask what it would take to allow a write with a person's approval instead, because one of the three products does exactly that.
</details>

<details><summary>Hint 3, nearly the answer</summary>
The brand folder is a sibling of the conversation workspace, not a drawer inside it. Reads resolve into either; writes resolve into the workspace only. That is one more comparison in the same function rather than a new concept.
</details>

**Decision to write down.** Read-only, writable with approval, or writable? Name a product that ships your answer.

---

## The specification

The room writes these on screen as it goes. They are the done checks on this branch and the checks that run.

1. Every file the agent writes lands inside the workspace for the signed-in brand and conversation, and the workspace comes from the request rather than from anything the model supplies.
2. The chat page shows finished work only. Drafts and rejected variants exist and are not shown.
3. A search returns a path, a line number and a snippet, stops after a set number of matches, skips files that are not text or are over a size limit, and says when it stopped early.
4. Answering "where did this line come from" costs one search and one or two line reads rather than every file in the folder.
5. A path that resolves outside the workspace is refused, in every form: climbing out with `..`, an absolute path, a symbolic link, and a folder whose name starts the same way.
6. An edit replaces the text it was asked to replace and nothing else, and refuses when the old text is missing or appears more than once.
7. Every artifact the agent produces is recorded against the session and the message, by the code that wrote it, and the record survives a turn that fails partway.
8. The chat page's file list is read from that record rather than from a scan of `data/` by modification time.
9. The brand's shared files are readable by the agent and not writable by it.
10. A legitimate read of a shared brand file still succeeds, because a fence that is too tight is also a defect.
11. Every refusal is on the trace with the tool name and the reason, and can be counted.
12. No file made for one brand is listed, linked or downloadable for another.

Criteria 3 and 6 are the room's own. The rest trace back to one of Harbor's four sentences.

---

## After it ships: the ticket

> Maya, Harbor: "I asked it to research five competitors. The chat shows one brief. Did it do the other four?"

**What is actually wrong.** It did. All five files are on disk. Four of them are missing from the record, so the chat cannot show them.

`research_many` runs five subagents inside a `ThreadPoolExecutor`. Each writes its own `competitors/<name>.md`, which never collides, and then each appends one line to the shared artifact record by reading it, adding a line, and writing the whole thing back. All five read the record at the start, all five write it back from what they read, and the last one wins.

The edit tool from stage 4 does not help, and working out why is the point. Every one of the five edits matched exactly once, because each subagent was appending a different line and none of them touched another's text. Exact-text matching catches a collision that overwrote your lines and silently permits one that did not. The check is about content, not about write ordering.

Nobody specified this. All twelve criteria are met and the bug is real.

**Done when**

- Ask for five competitors. All five briefs appear in the **Files** panel.
- Run it again. Still five.
- A tool call that times out and runs again does not put the same entry in twice.

<details><summary>Hint 1, a nudge</summary>
Watch the trace. Five writers, five successful writes, one surviving entry. Nothing errored. Ask what each writer read before it wrote.
</details>

<details><summary>Hint 2, the approach</summary>
There are three answers: one file per entry with the directory as the index, an append-only log, or a write that refuses when the file moved on. Two are layout changes and one is a lock. Ask your coding agent for the one you pick and check its answer never reads the whole record in order to add to it. Then ask it what happens when a timed-out call runs twice.
</details>

<details><summary>Hint 3, nearly the answer</summary>
If you take the log: one line per entry, opened for append, never read-modify-written, and each entry carries an id so a retry is caught rather than doubled. If you take one file per entry: the directory listing is the record, and the filename has to carry what the line used to.
</details>

**Decision to write down.** Which of the three, and what does your answer cost once the files are in a bucket?

Three more criteria go in `DECISIONS.md` afterwards, as the regression test that stops this coming back.

## The fork

**An append-only log, or the directory as the index.** Both ship in production and the code differs.

The log costs you compaction, and a reader that tolerates a half-written last line. The directory costs you a listing on every read, and a filename convention that has to carry what the entry used to say. The log's atomicity holds on a pod's local disk and disappears over a bucket mount, where a write is a whole new object and there is no real append.

The app works out which path you took from your own trace lines. Nothing to set, nothing to declare.
