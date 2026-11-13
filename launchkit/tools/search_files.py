"""Stage 2: the agent's search tool.

Not built yet, and not registered with the agent. LaunchKit had no file tools at all before this session.
Built in stage 2, capped from the start: a path, a line number and a snippet per match, a match limit, rules for
what it skips, and a line saying it stopped early. About fifteen lines of Python rather than a wrapper around
ripgrep, because rg is not installed by default on any of the three operating systems.

Reference page 6, File tools.
"""
