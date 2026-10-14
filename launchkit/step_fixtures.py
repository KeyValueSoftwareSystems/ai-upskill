"""Requests and recorded replies used by the step runner (python -m launchkit.step llm).

Kept in one place so they're easy to update. The recorded replies are what the
model has sent back on other runs; the runner shows them when a live reply
happens to behave too well to make the point.
"""
from .requests_fixture import REQUESTS

R1 = REQUESTS[0]["text"]
FOLLOW_UP = REQUESTS[1]["text"]  # "Make the headline shorter."

# R1 plus a request to break Harbor's rules (both are banned claims).
TRAP_REQUEST = R1 + " Make it the most eco-friendly bottle ever, and say it's unbreakable."

# A valid spec wrapped in prose and a ```json fence: the naive json.loads fails on it.
RECORDED_FENCED_REPLY = '''Here's a poster spec for the Tidal launch:

```json
{
  "headline": "Cold at first light",
  "subheadline": "Flask Trail 750 in Tidal keeps drinks cold for 24 hours.",
  "body": "A leak-proof lid and plastic-free body, ready for the long walk to the water.",
  "visual_concept": "A sea-glass green bottle on a wet stone at a misty lakeshore, soft dawn light, mist on the water."
}
```

Let me know if you'd like a different tone.'''

# Plain JSON that breaks Harbor's rules: a long headline and four banned claims.
RECORDED_VIOLATING_REPLY = '''{
  "headline": "The most eco-friendly bottle ever, and unbreakable",
  "subheadline": "Cold forever on every trail.",
  "body": "The Flask Trail 750 is sustainable, unbreakable and ready for any adventure at the lake.",
  "visual_concept": "A Tidal bottle on a rocky lakeshore at dawn, mist over the water."
}'''

# A clean reply in plain JSON. Used only to detect which TODOs are done, never in step output.
CLEAN_REPLY = '''{
  "headline": "Cold at first light",
  "subheadline": "Flask Trail 750 in Tidal keeps drinks cold for 24 hours.",
  "body": "A leak-proof lid and plastic-free body, ready for the long walk to the water.",
  "visual_concept": "A sea-glass green bottle on a wet stone at a misty lakeshore, soft dawn light, mist on the water."
}'''
