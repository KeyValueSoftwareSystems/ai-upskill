"""The agent's file system. Empty until the room builds it, one stage at a time.

Before this session LaunchKit had no file layer at all. Every artifact was written by a tool that already knew
its own output path, all of those paths were folders shared by every brand, and the agent could not go back and
look at any of it. Two modules below are stubs that name the stage that fills them; the third is ready-made.

workspace.py  stage 1  the folder one conversation owns, and its drawers
paths.py      stage 5  the one door every path passes before it is used
record.py     ready    what the agent produced, written as it is produced. It switches on when stage 1 is built

Nothing here is registered with the agent. Registering the tools is part of stage 1.
"""
