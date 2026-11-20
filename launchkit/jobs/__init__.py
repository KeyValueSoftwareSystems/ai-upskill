"""Long jobs (Session 5, stages 4 and 5).

A turn used to live inside the web request that started it: reload the page and its progress was gone, nothing could
stop it, and two messages to one conversation ran at once. A job is the same turn, given its own record on disk, its
own event log the page can replay, a Stop, and one job at a time per conversation (stage 4). Stage 5 adds steps on
disk, so a restart carries on where the job had got to and nothing it finished is done twice.
"""
