# Memory ticket 5 · Personal data, and forgetting on demand

> "A customer's phone number is in a headline draft. And legal wants everything about one user deleted by Friday."

Maya once pasted a board card with a customer's name and phone number, and once a token. Both became rows about her and were loaded into every turn. Then legal asked for the agency manager to be deleted. Deleting her memories is one query. Her session summaries, the decision log and the shared learning that names her are somewhere else.

## The slot

- `launchkit/memory/scope.py` · `personal_data`. Today it finds nothing.
- `launchkit/memory/forget.py` · `delete_user`. Today it deletes nothing.

Ready-made: `held_back` already asks `personal_data` first, so a row it names is left out of the prompt and a note it names is refused by `save_memory`. `still_naming` in `forget.py` lists every place a person's id or name still appears. `scripts/delete_user.py` calls both.

## Break it first

`uv run launchkit memory reset`, restart the page, sign in as **Maya at Harbor** and open the **Memory** tab. One row holds "Callum Ferris (07700 900461)", another "lkdemo-board-token-…". The Trace of any turn says they are loaded. In the terminal:

```
grep -c -a "07700 900461" data/sessions.db
```

In a new conversation:

> Note this customer for a follow-up: Callum Ferris, 07700 900461.

If the agent calls `save_memory`, the chat asks whether to save it. Nothing in code says no; only the capture rules from ticket 1 might.

Then legal's ask, in the terminal:

```
uv run python scripts/delete_user.py agency-manager --name "Dana Whitlock"
```

It lists where she appears: 18 memories, 2 session summaries, 2 decision-log rows, a shared learning (its title and its text), her chat folders. The delete itself does nothing yet.

## Prompt card, for your coding agent

```
In launchkit/memory/scope.py, personal_data(text) -> str | None: for each (kind, pattern) in PERSONAL
(already written: a phone number, an email address, a token or key), if the pattern finds something,
return f"personal data ({kind}): never kept in memory". A phone number counts only with 10 digits or
more, so a date is not one. Else return None. Remove the @todo mark.

In launchkit/memory/forget.py, delete_user(settings, user_id, apply) -> list[tuple[str, int]]: one
(what, count) per store, deleting only when apply:
- for each (what, table, column) in TABLES, count and delete the rows where column = user_id
  (memories; sessions, which carry their summaries; the decision log and entity rows);
- learned knowledge: Agno keeps no user_id on a shared learning, so find the agno_knowledge rows whose
  metadata tags hold "source:<user_id>" (save_learning adds it), and remove each with
  learnings(settings).remove_content_by_id(id), which also removes its vectors;
- brand facts they proposed: keep the fact, set source to 'removed user';
- their chat page folders: _files(settings, user_id), removed with shutil.rmtree.
A table that does not exist yet is skipped. Remove the @todo mark.
```

## Prove it

```
uv run launchkit check mem5
```

- A phone number and a token are personal data; a date is not.
- The snapshot's phone number and token never reach the prompt.
- A note with personal data is refused before anyone is asked.
- The delete cascades by user_id, takes a learning they proposed by its source tag, and leaves everyone else.
- What still names her is listed.
- Without `--apply` nothing is deleted.

## Run it again

Restart the page. Maya's **Memory** tab marks the two rows "personal data: never kept in memory", and the Trace holds them back. The same note in a new conversation: if the agent calls `save_memory`, the Trace shows `refused save_memory: Not saved: personal data (a phone number)`, and nobody is asked.

The rows are still in the database. The fix stops new ones and stops loading old ones; deleting is a separate act. Now delete Dana:

```
uv run python scripts/delete_user.py agency-manager --name "Dana Whitlock" --apply
```

```
Removed:
    18  memories
     2  conversations and their summaries
     2  decision log and entity rows
     0  shared learnings they proposed (tag source:agency-manager)
     2  chat page conversations and pictures (folders)

After: still names them
   agno_knowledge: Dana Whitlock's tip: lead every poster with navy
   learned knowledge text: Dana Whitlock's tip: lead every poster with navy
```

That learning was saved before ticket 2b, with no source. No key reaches it; only a search for her name finds it. The folder count depends on what you did on the page. Restart the page: Dana's Memory tab is empty. Reset afterwards.

## Why it matters

"Forgotten" has to mean every store, and you can only prove it if every row says whose it is. The cascade is as good as the keys the writes left behind: a write without a source can't be deleted on demand, only found by a search. Two systems would mean two deletions, and two proofs.

## Stuck?

The answer is on the branch `session-3-memory`.
