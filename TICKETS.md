# Session 4: one feature request, built in three builds

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

This is not a queue of complaints. The room scopes one feature request together and builds it in three builds, called stages. Each stage works like red and green in test-driven development, where a test fails first and then passes. Something fails on the chat page. The room argues what to do about it and writes the acceptance criteria. The lead explains the prompt and runs it, and that stage's checks go green. The next failure then appears on top of what you just built. The chat page that lists what the agent made, the record behind it and the search code come ready: the page and the record switch on when stage 1 is built, and the agent is offered the search in stage 2.

- Read each stage below and watch it fail on the chat page before anyone explains it.
- The room writes each stage's criteria before that stage's build, one to four at a time. They are the test; there is no separate test at the end. `uv run pytest checks/test_files.py -m stage1` runs one stage's checks.
- Build with your coding agent. The hints say what to ask for and what to check in its answer. They are not the prompt. Open one only when you need it.
- "Done" is seen on the chat page, never in a terminal.
- Write your decision in `DECISIONS.md`, a few words. The room compares them after the build.
- Stuck? Move on. The stages before yours stay as they are, and the lead's prompt for your stage is the backup.

The three stages share one cause: nothing decides which files a request owns. Each ends in a build. The discussions that go with them are in the deck.

What is already there, and what each piece does, is in `READY-MADE.md`.

---

## Stage 1 · Where the work lives, and the file tools

> Maya, Harbor: "You researched five competitors for me an hour ago. I asked what you found about Stanley, and you either said you did not know or started the research again."

**What is actually wrong.** The agent has no file tools at all. Every tool that writes a file already knows its own output path, all of those paths are shared folders, and nothing records which conversation a file belongs to or which version anyone approved. There is no way to ask for yesterday's work because the agent cannot look at anything it made. The page that lists a turn's files, and the record it reads, are already built. They stay quiet until a conversation has a workspace.

**Done when**

- Sign in as Maya at Harbor, ask for a poster, and the **Files** panel shows it under this conversation rather than in a folder shared with every brand.
- Ask for the same thing in a second conversation. The two sets of files do not mix.
- The workspace name comes from the request. Nothing the model writes can change which folder a file lands in.
- Research five competitors, ask three short questions, then ask what the research said about one of them. The agent looks in its saved briefs and answers from the file, not from scratch.

<details><summary>Hint 1, a nudge</summary>
<code>launchkit/brands/request.py</code> already resolves a brand to a folder, and refuses a bad one. Nothing does the same for a conversation. Look at how <code>Pictures</code> in <code>launchkit/memory/attached_pictures.py</code> scopes itself, because one feature already solved this for one file type and nobody generalised it. Then look at <code>build_catalogue</code> in <code>launchkit/agents/main_agent.py</code>, which is where a tool becomes something the agent can call.
</details>

<details><summary>Hint 2, the approach</summary>
Ask your coding agent for a <code>Workspace</code> in <code>launchkit/files/workspace.py</code> that takes the brand and the conversation from the request and gives back one folder with drawers inside it: uploads, work, outputs, competitors. Then fill in the three stubs on top of it, <code>read_file</code> (with a line range, so a search can point at a line later), <code>list_files</code> and <code>write_file</code>, and register them with the agent. Check its answer resolves the folder from the request object and never from an argument a tool passes in, and that the drawers are named in one place rather than spelled out at each call site.
</details>

<details><summary>Hint 3, nearly the answer</summary>
One class, four or five lines of real work: the root is <code>settings.data_dir / "files" / brand / conversation</code>, and the brand's own files are <code>settings.workspaces_dir / brand</code>, kept outside it, a method per drawer, and <code>mkdir(parents=True, exist_ok=True)</code> on first use. Each tool is a few lines that joins its path onto the root and reads or writes. Each write is also added to the record in <code>launchkit/files/record.py</code>, which is ready-made: build a <code>Record</code> when the tool is built and add one entry after each write. Build only that: nothing here has to decide whether a path is safe yet, because that is a later stage. The drawers decide what the panel shows later, so put finished work in <code>outputs/</code> and drafts in <code>work/</code> now.
</details>

- Ask for research on five competitors and look at the **Files** panel. It lists all five briefs. The record is an append-only log, so five writers at once cannot lose each other's entries.

**Decision to write down.** Who names the workspace, and what stops the model from naming it?

---

## Stage 2 · How a file gets changed

> The reviewer, on Breeze: "Take out the lifetime-guarantee line." The trace shows the whole brief written again for one line.

**What is actually wrong.** The only way to change a file today is to write the whole thing again, so every line goes back through the write tool for one line's change, and nothing can tell the line that was asked for from the lines that were not.

**Done when**

- Ask which saved briefs mention a holiday. The trace shows one search and one or two line reads, not every file in the folder, and the answer names the file and the line.
- Ask for one line to change. That line changes and nothing else in the file does.
- The trace shows one edit, not a whole-file write.
- Ask for a line that is not there. The agent says so instead of writing something.
- Ask for text that appears twice. The agent says so instead of guessing which one.

<details><summary>Hint 1, a nudge</summary>
There are five ways to change a file: write it all again, replace a line range, replace an exact piece of text, apply a patch, or run a shell command. Four of them can change the wrong thing without telling you. Work out which, then pick.
</details>

<details><summary>Hint 2, the approach</summary>
Ask your coding agent to fill in the stub in <code>launchkit/tools/edit_file.py</code>: one function that takes a path, the old text and the new text, and refuses rather than guessing. Check its answer refuses in two separate cases, not one: the old text missing, and the old text appearing more than once. Ask it what happens when the file changed since the agent last read it, and keep the answer; the stretch comes back to it.
</details>

<details><summary>Hint 3, nearly the answer</summary>
<code>content.count(old)</code> first. Zero means refuse and say so. More than one means refuse and say how many. Exactly one means replace and write. Appending is not part of this tool. The ticket asks about it.
</details>

**What this check cannot see.** It looks at content. If another writer changed the file after the agent read it, the old text may still be there exactly once, and the edit goes through over the other writer's change. Checking that the file is the one that was read is the stretch.

**Decision to write down.** What must an edit tool check before it writes? Name both checks, and which one you built.

---

## Stage 3 · Who may touch which file

> Jonas, Ember: "I asked about `../../harbor/k7c1/outputs/campaign-brief.md` and it read it to me."

To see it fail, have Maya's brief saved in her conversation `k7c1`, and know that Jonas's own folder exists once `uv run launchkit setup` has run. A path cannot climb out of a folder that is not there.

**What is actually wrong.** Each piece of that path is allowed on its own. Nothing works out where the whole path really points before using it, so a path that looks local reaches a sibling folder. A second problem: the page's download route joins the name onto the workspace folder and serves whatever it finds, and it never goes through a file tool at all.

**Done when**

- Sign in as Jonas at Ember and ask for a path with `..` in it, such as the one above. The agent refuses, and the Trace tab shows the refusal with the tool name and the reason.
- The same for an absolute path, for a symbolic link that points out, and for a folder whose name starts the same way as the real one. `t3a9-old` is not `t3a9`.
- A legitimate read of Ember's own brand book still works. A fence that is too tight is also a defect.
- Nothing made for Harbor appears in Ember's **Files** panel or downloads from Ember's session.
- The agent reads `workspaces/harbor/brand-book.md` and `rules.yaml` normally, and cannot write either one. A refused write shows on the trace with the reason.

<details><summary>Hint 1, a nudge</summary>
Six callers need the same answer: the five file tools and the page's download route. The list of files a turn made comes from the record, which holds paths relative to the workspace. Find all six before writing anything, because a check that only one of them calls is not a fence.
</details>

<details><summary>Hint 2, the approach</summary>
Ask your coding agent for one function in <code>launchkit/files/paths.py</code> that takes a workspace root and a path and either returns the real location inside it or raises. Check that it resolves first and compares after, and that the comparison is between resolved paths rather than between strings. Ask what its answer does with a symbolic link, and with <code>t3a9-old</code> when the conversation is <code>t3a9</code>.
</details>

<details><summary>Hint 3, nearly the answer</summary>
<code>Path.resolve()</code> on both, then compare with <code>is_relative_to</code>. String prefix matching is the bug: <code>"/data/files/ember/t3a9-old".startswith("/data/files/ember/t3a9")</code> is true. Raise your own error so the tool layer can turn it into a refusal on the trace rather than a stack trace in the chat.
</details>

**Decisions to write down.** May one person at a brand reach another person's conversation at that brand? Yes or no, and what breaks either way. And the brand's shared files: read-only, writable with approval, or writable? Name a product that ships your answer.

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
8. The Files tab reads that record, not the disk.
9. The brand's shared files are readable by the agent and not writable by it.
10. A legitimate read of a shared brand file still succeeds, because a fence that is too tight is also a defect.
11. Every refusal is on the trace with the tool name and the reason, and can be counted.
12. No file made for one brand is listed, linked or downloadable for another.

Criterion 1 is stage 1, criterion 6 is stage 2, and criteria 5, 9, 10 and 11 are stage 3. Criteria 2, 3, 4, 7, 8 and 12 come ready: the record, the search code and the chat page that reads them. Their checks go green when stage 1 is built, so read them and do not build them. Criteria 3 and 4 show on the chat page only once stage 2 offers the search to the agent. Each one traces back to one of Harbor's four sentences.

---
