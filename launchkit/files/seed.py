#!/usr/bin/env python3
"""Builds the state Breeze week left behind, for Session 4's branch.

This runs in prep, never in the room. `uv run launchkit setup` puts the result in place, and running it again
puts it back, so a participant who breaks something can reset in one command.

What it makes, and which requirement each part is there for:

    data/outputs/        posters from Harbor and Ember in one folder, named by the millisecond   (1)
    data/sizes/          their resized versions, same shared folder                              (1)
    data/audio/          Sam's voice-over                                                        (1)
    data/uploads/        keyed by the name of the file the person attached, so two people         (1)
                         attaching brief.md overwrite each other
    data/competitors/    five Breeze competitor briefs, two of them making the                   (3)
                         lifetime-guarantee claim
    data/campaign-brief.md  the brief the research produced, with the line Maya asks about       (3, 4)
    data/files/harbor/k7c1/outputs/campaign-brief.md  the approved campaign brief, in Maya's workspace-to-be  (4, 5)
    data/files/ember/t3a9/outputs/  Jonas's own folder, empty, so a path can climb out of it  (5)
    data/files/ember/t3a9-old/  a conversation named like Jonas's t3a9, which is the prefix case  (5)

Session 5 adds, on top of Session 4's state:

    data/files/harbor/k7c1/uploads/breeze-results.csv   Breeze's first week of ads, one row per channel per day  (S5: 1, 3)
    data/files/harbor/k7c1/outputs/breeze-poster.png    the approved Breeze poster the fourteen sizes are cut from (S5: 4, 5)
    data/files/ember/t3a9/uploads/autumn-results.csv    Jonas's own results file, the one he asks the agent to tidy (S5: 2)
    data/jobs/                                          emptied, so no job from an earlier run is left over       (S5: 4, 5)

Everything except Maya's approved campaign brief lands in shared folders on purpose. That is the system the room inherits.

    data/conversations/harbor/maya/k7c1.json    Maya's Breeze conversation, with a fixed id          (all)
    data/conversations/harbor/sam/s5b2.json     Sam's, the intern who added the voice-over           (1)
    data/conversations/ember/jonas/t3a9.json    Jonas's autumn posters                               (5)

The conversation ids are fixed on purpose. The app mints a random one for a new conversation, which is right for
a product and no use for a room: the stage 3 attack names Harbor's workspace, and it has to be a path everyone can
type. Maya works in k7c1 and Jonas in t3a9, so after stage 1 Maya's brief lands in files/harbor/k7c1 and Jonas
can ask for it by name.

Run it:  uv run launchkit setup
"""

import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

COMPETITORS = {
    "kestrel.md": [
        "# Kestrel, for the Breeze campaign",
        "",
        "Positioning: the bottle that goes everywhere.",
        "Pricing: mid-range, one size.",
        "Channels: outdoor shops, and a launch week on social.",
        "Claims: none about guarantees.",
        "Bottle: double-walled steel, in five colours.",
        "Launch: spring, with a hiking partner.",
    ],
    "marlow.md": [
        "# Marlow, for the Breeze campaign",
        "",
        "Positioning: buy it once and stop thinking about it.",
        "Pricing: premium, a single size.",
        "Channels: their own shop and gift guides.",
        "Claims: a lifetime guarantee on the cap and the body.",
        "Bottle: powder-coated steel with a wide mouth.",
        "Launch: autumn, with a gift set.",
    ],
    "northfield.md": [
        "# Northfield, for the Breeze campaign",
        "",
        "Positioning: the plain, honest bottle.",
        "Pricing: premium, two sizes.",
        "Channels: retail partners and a pricing page.",
        "Claims: 'lifetime guarantee' is the headline of their pricing page.",
        "Bottle: brushed steel, no coating.",
        "Launch: all year, with no campaign.",
    ],
    "tern.md": [
        "# Tern, for the Breeze campaign",
        "",
        "Positioning: light enough to forget it is there.",
        "Pricing: budget, three sizes.",
        "Channels: supermarkets and a price promotion.",
        "Claims: none about guarantees.",
        "Bottle: lightweight plastic, with a flip cap.",
        "Launch: summer, with a price cut.",
    ],
    "alder.md": [
        "# Alder, for the Breeze campaign",
        "",
        "Positioning: the bottle that looks like it belongs on a desk.",
        "Pricing: mid-range, two sizes.",
        "Channels: design shops and an influencer drop.",
        "Claims: none about guarantees.",
        "Bottle: matte glass in a sleeve.",
        "Launch: winter, with a limited colour.",
    ],
}

CAMPAIGN_BRIEF = [
    "# Breeze campaign brief",
    "",
    "## Positioning",
    "",
    "avoid the lifetime-guarantee framing, two competitors use it",
    "",
    "Breeze is the one you keep using, not the one you bought once.",
    "",
    "## Tone",
    "",
    "warm, plain, never clever",
    "",
    "## Placements",
    "",
    "square for social, tall for print",
    "",
]


def millisecond_name(prefix: str, suffix: str, offset: int) -> str:
    """The naming this system shipped with: a prefix and the millisecond it was made. No brand anywhere in it."""
    stamp = int((time.time() - offset) * 1000)
    return f"{prefix}-{stamp}{suffix}"


def placeholder_png() -> bytes:
    """A one-pixel PNG. The seeded posters only have to exist and be listed, never to be looked at."""
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a49444154789c6360000002000100ffff03000006000557bfabd400"
        "00000049454e44ae426082"
    )


CONVERSATIONS = {
    ("harbor", "maya", "k7c1"): [
        ("user", "Concepts for the Breeze launch, please. Three headlines, the tall poster first."),
        ("assistant", "Three directions for Breeze. One, a quiet one: 'Keep using it.' Two, a practical one: 'Five years, one bottle.' Three, a dry one: 'Still here after the second winter.' The tall poster follows the first."),
        ("user", "Research five competitors for the campaign and tell me what to avoid copying."),
        ("assistant", "Five competitors read. Two of them lean on a lifetime-guarantee line, so Breeze should not. The rest sell on price or on convenience, which leaves warranty and durability open to us."),
    ],
    ("harbor", "sam", "s5b2"): [
        ("user", "Add a voice-over to the winning Breeze poster."),
        ("assistant", "Done. The voice-over is saved with the poster's other versions."),
    ],
    ("ember", "jonas", "t3a9"): [
        ("user", "Autumn poster for the Night Shift roast, dark and warm."),
        ("assistant", "A dark amber poster for Night Shift, with the headline 'Stays up with you.' Saved with Ember's autumn set."),
    ],
}

# Only these are the seed's to own. data/ also holds conversations, the brand index and Session 3's memory
# database, so this never removes the data directory itself.
SEEDED = ("outputs", "sizes", "audio", "uploads", "competitors", "files", "jobs")

CHANNELS = ("Search", "Social", "Video", "Email", "Display")
# Per channel: spend a day in pounds, impressions, click rate, and the share of clicks that sign up.
CHANNEL_SHAPE = {
    "Search": (420, 38000, 0.040, 0.040),
    "Social": (610, 120000, 0.020, 0.040),
    "Video": (880, 210000, 0.0052, 0.047),
    "Email": (95, 18000, 0.040, 0.022),
    "Display": (300, 160000, 0.004, 0.034),
}


def breeze_results() -> str:
    """Breeze's first week of ads, 14 to 20 November, one row per channel per day, as Maya downloads it.

    Built so that reading it by eye gives the wrong answer. Email is the cheapest channel per sign-up on most single
    days, and one bad day makes it lose over the week; Social and Search are close. Only adding the columns up says
    which channel is cheapest, which is what Session 5's first demo is about.
    """
    import random

    rng = random.Random(5)
    rows = ["date,channel,spend,impressions,clicks,signups"]
    for day in range(14, 21):
        for channel in CHANNELS:
            spend, impressions, click_rate, signup_rate = CHANNEL_SHAPE[channel]
            spend = round(spend * rng.uniform(0.85, 1.15), 2)
            impressions = int(impressions * rng.uniform(0.85, 1.15))
            clicks = int(impressions * click_rate * rng.uniform(0.9, 1.1))
            signups = int(clicks * signup_rate * rng.uniform(0.85, 1.15))
            if channel == "Email" and day == 18:  # the send that went to the wrong list
                spend, signups = round(spend * 4.5, 2), 0
            if channel == "Email" and day != 18:
                signups = int(signups * 1.45)
            rows.append(f"2026-11-{day},{channel},{spend:.2f},{impressions},{clicks},{signups}")
    return "\n".join(rows) + "\n"


AUTUMN_RESULTS = """Date , Channel,Spend (GBP),Clicks ,Sign ups
14/11/2026, social ,"1,204.50", 1830,61
14/11/2026,Search,  612.00,940 , 38
15/11/2026, Social,"1,180.00",1795 ,58
15/11/2026,search ,598.40, 911,36
16/11/2026,SOCIAL,"1,250.10", 1902, 64
16/11/2026,Search,630.00,968 ,39
"""


def breeze_poster() -> bytes:
    """The approved Breeze poster, 1080 by 1350: a picture with real pixels, because the jobs demo cuts fourteen sizes from it."""
    import io

    from PIL import Image, ImageDraw, ImageFont

    width, height = 1080, 1350
    picture = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(picture)
    top, bottom = (16, 42, 67), (143, 190, 180)
    for y in range(height):
        share = y / height
        draw.line([(0, y), (width, y)], fill=tuple(int(a + (b - a) * share) for a, b in zip(top, bottom)))
    draw.rounded_rectangle([440, 430, 640, 1080], radius=60, fill=(222, 231, 228), outline=(16, 42, 67), width=6)
    draw.rectangle([480, 380, 600, 440], fill=(16, 42, 67))
    try:
        big, small = ImageFont.load_default(size=110), ImageFont.load_default(size=48)
    except TypeError:  # an older Pillow has one fixed-size font
        big = small = ImageFont.load_default()
    draw.text((width / 2, 170), "Breeze", font=big, fill=(240, 244, 242), anchor="mm")
    draw.text((width / 2, 1220), "Keep using it.", font=small, fill=(16, 42, 67), anchor="mm")
    out = io.BytesIO()
    picture.save(out, format="PNG")
    return out.getvalue()


def build(data: Path) -> None:
    for name in SEEDED:
        folder = data / name
        if folder.exists():
            shutil.rmtree(folder)
    (data / "campaign-brief.md").unlink(missing_ok=True)

    outputs = data / "outputs"
    sizes = data / "sizes"
    audio = data / "audio"
    uploads = data / "uploads"
    competitors = data / "competitors"
    for folder in (outputs, sizes, audio, uploads, competitors):
        folder.mkdir(parents=True, exist_ok=True)

    # Breeze week: both brands into the same three folders, named by the millisecond.
    for offset, prefix in [(604800, "poster"), (604500, "poster"), (604200, "poster"), (603900, "poster")]:
        (outputs / millisecond_name(prefix, ".png", offset)).write_bytes(placeholder_png())
    for offset in (603600, 603300, 603000, 602700, 602400):
        (sizes / millisecond_name("scaled", ".png", offset)).write_bytes(placeholder_png())
    (audio / millisecond_name("voice", ".wav", 602100)).write_bytes(b"RIFF....WAVEfmt ")

    # Uploads keyed by the attached file's name, so two people attaching brief.md collide.
    (uploads / "brief.md").write_text("Maya's attachment, which overwrote Jonas's.\n", encoding="utf-8")
    (uploads / "reference.png").write_bytes(placeholder_png())

    # The research the session is about. Written down here only because prep wrote it: the product does not.
    for name, lines in COMPETITORS.items():
        (competitors / name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    (data / "campaign-brief.md").write_text("\n".join(CAMPAIGN_BRIEF), encoding="utf-8")

    # The approved campaign brief, in the folder Maya's conversation's workspace will be once stage 1 builds it. Stages 2
    # and 3 edit it and read it by path. The competitor briefs are not seeded: the room's own research makes them.
    breeze = data / "files" / "harbor" / "k7c1"
    (breeze / "outputs").mkdir(parents=True, exist_ok=True)
    (breeze / "outputs" / "campaign-brief.md").write_text("\n".join(CAMPAIGN_BRIEF), encoding="utf-8")
    # Jonas's own folder, empty. A path cannot climb out of a folder that is not there, so stage 3's attack needs it.
    (data / "files" / "ember" / "t3a9" / "outputs").mkdir(parents=True, exist_ok=True)

    # Session 5: Breeze's first week of ads and its approved poster in Maya's conversation, and Jonas's own results.
    (breeze / "uploads").mkdir(parents=True, exist_ok=True)
    (breeze / "uploads" / "breeze-results.csv").write_text(breeze_results(), encoding="utf-8")
    (breeze / "outputs" / "breeze-poster.png").write_bytes(breeze_poster())
    jonas_uploads = data / "files" / "ember" / "t3a9" / "uploads"
    jonas_uploads.mkdir(parents=True, exist_ok=True)
    (jonas_uploads / "autumn-results.csv").write_text(AUTUMN_RESULTS, encoding="utf-8")

    # Conversations with fixed ids, so the room can name another brand's workspace. Only these three are the seed's.
    for (brand, person, session), turns in CONVERSATIONS.items():
        folder = data / "conversations" / brand / person
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{session}.json").write_text(json.dumps({
            "session_id": session,
            "turns": [{"role": r, "text": t, "files": []} if r == "user" else {"role": r, "reply": t, "files": []} for r, t in turns],
        }, indent=2), encoding="utf-8")

    # The prefix case for stage 3: a conversation whose name starts the same way as Jonas's t3a9.
    lookalike = data / "files" / "ember" / "t3a9-old"
    lookalike.mkdir(parents=True, exist_ok=True)
    (lookalike / "notes.md").write_text("# Left over from an earlier conversation\n\nNobody has looked at this in a year.\n", encoding="utf-8")


def main() -> int:
    data = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data"
    build(data)
    files = sum(1 for p in data.rglob("*") if p.is_file())
    print(f"seeded {data} with {files} files, in shared folders, owned by nobody")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
