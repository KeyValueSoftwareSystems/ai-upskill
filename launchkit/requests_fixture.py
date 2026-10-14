"""The four Harbor requests every approach is scored on.

Order matters: R2 follows R1 in conversation A, R4 follows R3 in conversation B.
"""
REQUESTS = [
    {"id": "R1", "conversation": "A", "tests": "A concept becomes a valid poster",
     "text": "Poster for the Tidal bottle on a misty lakeshore at dawn. Headline idea: cold for 24 hours.",
     "attachments": []},
    {"id": "R2", "conversation": "A", "tests": "A follow-up edit in the same conversation",
     "text": "Make the headline shorter.",
     "attachments": []},
    {"id": "R3", "conversation": "B", "tests": "A photo upload is used",
     "text": "Use this photo of the bottle. Make the bottle bigger and the lake moodier.",
     "attachments": ["assets/tidal_photo.png"]},
    {"id": "R4", "conversation": "B", "tests": "A resize-only request",
     "text": "Now give me the story size (1080x1920) of that poster.",
     "attachments": []},
]
