# Step 4 · MCP: plug in Maya's Notion board

Maya: "Take the brief from our Notion board, and put the sizes there when done." Her launch brief and placement list live on the team's board. Without a way in, she retypes the brief, and the finished sizes go back by hand.

MCP (Model Context Protocol) is a common plug between an agent and an outside service. The service runs an MCP server that lists its own tools, each with a name, a description and a schema: the same three things the room wrote by hand in step 1. Any agent that speaks MCP can use them.

The board is your real Notion, through Notion's own MCP server. Run `uv run launchkit notion` once: it logs you in in the browser and puts the Tidal card in your Notion, with the brief and last week's approved files. Run it again any time to set the card back. Notion's server lists 68 tools and says which ones only read. The harness plugs in six board tools: `notion-search`, `notion-fetch`, `notion-update-page`, `notion-create-comment`, `notion-get-comments` and, on purpose, `notion-delete-pages`, which can do harm.

Offline, and for the checks and the fakes, `LAUNCHKIT_BOARD=local` uses a small MCP server in the repo instead (`launchkit/harness/board_server.py`): the same card, with the tools `read_card`, `attach_files`, `update_status` and `remove_files`.

Ready-made, with its moment: the `post_to_board` skill. It writes Harbor's routine down once: read the brief, add the sizes, move the card to "Ready for review".

## The slot

- `launchkit/harness/mcp_link.py` · `connect(server)`. Today it returns no tools, so the board is not in the catalogue.

`McpLink` (ready-made) holds the client open for the run and turns the async MCP calls into plain ones. `tool_function` (ready-made) wraps one MCP tool as a Python function with its name, description and inputs.

## Break it first

```
uv run launchkit main harbor "Take the brief from our Notion board." --model fake:tools
```

```
reply
I could not find a skill or tool for that.
```

## Prompt card, for your coding agent

```
In launchkit/harness/mcp_link.py, build connect(server). Open link = McpLink(server).
For each tool in link.list_tools(), make Entry(tool.name, note, kind,
tool_function(tool, link)), where note is the first line of tool.description and
kind is "read" when tool.annotations.readOnlyHint is true and "write" otherwise.
Return the list. A few lines: the server already describes its tools, so nothing
is written by hand.
```

The note is the first line only: Notion's descriptions run to 2,000 characters, and `find_tool` ranks on the note. The full description stays on the tool.

## Prove it

```
uv run launchkit check tools4
```

- Over MCP, the board's server lists its tools, each with a description, a schema, and whether it only reads.
- `connect` turns each tool into a catalogue entry, read or write as the server says.
- `run_tool` reads the Tidal card over MCP, and a write changes the board.
- Ready-made: `post_to_board` writes Harbor's routine down.
- Asked to put the sizes on the Tidal card, the main agent loads `post_to_board` and the files land on the card.

## Run it again

The same ask, on the real model and your Notion: `uv run launchkit main harbor "Take the brief from our Notion board."` `find_tool` now finds Notion's tools next to ours, and `run_tool` runs them. Then ask "Put these new sizes on the Tidal card: tidal-feed-1080x1350.png, tidal-web-1200x628.png. Then move it to Ready for review." and open the card in Notion. Check it: the agent can say "done" when Notion took the call but changed nothing. And Notion also offers `notion-delete-pages`: the agent can now change things Maya never asked it to touch.

## Stuck?

The answer is on the branch `session-02-tools-step4`.
