"""What each file tool says about itself, ready-made.

find_tool ranks the tools by the words they share with what the marketer said, and the agent only sees a tool if it
ranks near the top. So these lines are worded the way a person asks ("saved briefs", "change one line"), they are
checked without any model in checks/test_files.py (the routing checks), and the room does not rewrite them.

Reference page 6, File tools.
"""

WRITE_FILE = "pick me to save, write or create a file, brief, document, draft or plan in this conversation's workspace: finished work in outputs/, drafts in work/"

READ_FILE = ("pick me to open, read or show a saved file, brief, research, document or draft from this conversation's workspace, "
             "or a range of its lines, or to see what an earlier brief or research said; the brand's own files are brand/<name>")

LIST_FILES = "pick me to list, see or find what files, briefs, research, drafts and documents this conversation has already saved or found earlier"

SEARCH_FILES = ("pick me to search the saved files, competitor briefs and documents for a word or phrase, to find which of them "
                "mention it and which line says so, before reading any of them; give one distinctive word, the match is exact text")

EDIT_FILE = ("pick me to edit, change, update or fix one line or phrase in a saved file, brief or document without rewriting the rest: "
             "give the exact old text and the new text")
