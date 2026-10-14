# What the model saw, in what order, at what cost

Three commands for the talk after the build.

```
uv run launchkit explain
```
Prints the last run: the four sections in order (rules, task, facts, history), tokens per section against
its budget, total input, cached and output tokens, and the cost. Add `--show` to print the system message as sent.

```
uv run launchkit run harbor "Mention it's dishwasher-safe" --facts workspaces/harbor/brand-book.md
uv run launchkit explain
```
Loads the whole brand book into the facts section. The budget trims it. The line "the lid is hand-wash only"
falls below the cut, and the copy says dishwasher-safe. The fact existed. The model never saw it.

## The four rules

1. Fixed order: rules, task, facts, history.
2. A budget per section. `settings.py` holds the numbers.
3. Stable part first, so the provider can cache it. History changes every turn, so it goes last.
4. Fetch detail just in time, as a tool call, not up front.

Budgets stop the bill. They do not pick the lines. The facts section needs retrieval. That is the next part.
