# Files stage 6 · What happens to shared files

> Harbor's brand book has a different tone section this week, and nobody at Harbor edited it.

One job tidied it while doing something else, and every job since has used the tidied version. The brand's shared files sit in the same tree as the conversation's work, and nothing said they were different. This stage has no build: stage 3's check already holds it, because reads resolve into the workspace or into `brand/`, and writes resolve into the workspace only. The room sees it hold, then argues where the rule belongs.

## Before you start

The page is running on the working copy where stage 5's checks went green.

## The slot

Nothing to build. The rule lives in `launchkit/files/paths.py`, in the same function every path passes.

## See it hold

As **Maya at Harbor**, in the Breeze conversation:

> Read brand/brand-book.md and tell me Harbor's tone.

The Trace shows `read brand/brand-book.md`, and the reply quotes the tone section. Then:

> In brand/brand-book.md, change the tone section to "bold and loud".

The Trace shows `refused   edit_file('brand/brand-book.md'): <the reason>` (or `write_file`, if the agent reaches for that), and the brand book is as it was.

## Prove it

```
uv run pytest checks/test_files.py -m stage6
```

- Shared brand files are readable by the agent and not writable by it.

## The discussion

Read-only, writable with approval, or writable? Each is shipped somewhere. The question for the room is where the rule belongs: in the check, in the tool, or in the layout. Here it is the layout: the brand folder is a sibling of the conversation workspace, not a drawer inside it, so reads resolve into either and writes resolve into one. That is one more comparison in the same function rather than a new concept. What it would take to allow a write with a person's approval is one `kind="write"` entry and the Allow and Deny the room already built in Session 2.
