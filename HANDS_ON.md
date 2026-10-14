# Next: the agent harness

Branch `session-01-harness`

This branch starts where the opener ended: the LLM call and the LangGraph pipeline are both solved. Check the scoreboard:

```bash
uv run python -m launchkit.scoreboard --approach llm      # R1 passes
uv run python -m launchkit.scoreboard --approach graph    # R1 and R2 pass
```

R3 (a photo) and R4 (a resize) still fail. The agent harness TODOs for the next segment will be added to this branch.
