"""check_copy: plain code the agent can call while it works. The same word limits and banned claims as the
harness check at the end, which stays: a rule in code is still the guarantee."""

import re

from launchkit.harness.spec import WORD_LIMITS
from launchkit.harness.workspace import Workspace


def make_check_copy(ws: Workspace):
    def check_copy(headline: str, subheadline: str = "", body: str = "") -> dict:
        """Check poster words against this brand's word limits and banned claims before you answer. Returns ok and
        the problems to fix."""
        problems = []
        for field, text in (("headline", headline), ("subheadline", subheadline), ("body", body)):
            words = len(text.split())
            if words > WORD_LIMITS[field]:
                problems.append(f"{field} has {words} words, limit is {WORD_LIMITS[field]}")
        copy = f"{headline} {subheadline} {body}".lower()
        problems += [f"banned claim: {c}" for c in ws.rules.get("banned_claims", []) if re.search(rf"\b{re.escape(c.lower())}\b", copy)]
        return {"ok": not problems, "problems": problems}

    return check_copy
