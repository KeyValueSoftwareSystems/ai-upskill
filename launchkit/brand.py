"""Load a workspace's brand pack and turn it into prompt-ready rules."""
import json

from .paths import ROOT


def load_brand(workspace: str) -> dict:
    path = ROOT / "workspaces" / workspace / "brand.json"
    return json.loads(path.read_text())


def brand_rules_text(brand: dict) -> str:
    """Brand rules as plain text you can drop into a prompt."""
    limits = brand["copy_limits"]
    lines = [
        f"Brand: {brand['name']}. Product: {brand['product']}.",
        f"Voice: {brand['voice']}",
        "Facts you may use: " + "; ".join(brand["facts"]) + ".",
        "Never use these claims: " + ", ".join(brand["banned_claims"]) + ".",
        f"Headline: at most {limits['headline']} words. "
        f"Subheadline: at most {limits['subheadline']} words. "
        f"Body: at most {limits['body']} words.",
    ]
    return "\n".join(lines)
