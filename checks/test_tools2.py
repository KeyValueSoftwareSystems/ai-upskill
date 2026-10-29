import json

from launchkit.harness.catalogue import load_skills
from launchkit.harness.picture_tools import PictureDesk, window_around
from launchkit.harness.trace import Trace

BOTTLE = [492, 596, 660, 950]
SIZES = [(1080, 1080), (1080, 1350), (1080, 1920), (1200, 628), (300, 250)]
NO = lambda name, inputs: False


def test_the_skill_says_when_to_pick_it_and_how():
    """skills/resize_image/skill.md says when to pick it, names its tools, never scales, and hides the raw tools."""
    skill = load_skills().get("resize_image")
    assert skill is not None, "no launchkit/skills/resize_image/skill.md yet"
    assert "size" in skill.note.lower()
    text = skill.text.lower()
    assert all(name in text for name in ("detect_focal_point", "crop", "expand_canvas"))
    assert "never" in text and "scale" in text
    assert {"crop", "expand_canvas", "scale", "detect_focal_point"} <= set(skill.hides)


def test_the_fit_rule_keeps_the_bottle_in_every_harbor_size():
    """For every Harbor size, the fit rule gives a window of that shape, inside the poster, around the whole bottle."""
    for w, h in SIZES:
        window = window_around(BOTTLE, (1200, 1200), (w, h))
        assert window is not None, f"no window for {w}x{h}"
        left, top, right, bottom = window
        assert 0 <= left and 0 <= top and right <= 1200 and bottom <= 1200
        assert left <= BOTTLE[0] and top <= BOTTLE[1] and right >= BOTTLE[2] and bottom >= BOTTLE[3]
        assert abs((right - left) / (bottom - top) - w / h) < 0.02


def test_the_fit_rule_says_no_when_the_bottle_cannot_fit():
    """A shape too thin for the bottle and its margin gets no window, so nothing gets cut."""
    assert window_around(BOTTLE, (1200, 1200), (1200, 100)) is None


def test_crop_without_a_window_cuts_around_the_bottle(settings):
    """crop with no window uses the fit rule: the product stays whole, and a shape it cannot fit says so."""
    desk = PictureDesk(settings, {"navy": "#1F3A5F"}, Trace())
    assert all(desk.crop(w, h)["product_whole"] for w, h in SIZES)
    assert desk.crop(1200, 100)["status"] == "does not fit"


def test_the_main_agent_follows_the_skill(settings, trace, request_for):
    """Asked for all the sizes, the main agent loads resize_image, finds the bottle once, and every size keeps it whole."""
    from launchkit.adapters.fakes import ToolsModel
    from launchkit.harness.main import run_main

    run_main(request_for(text="Love the poster. Now all the sizes, please."), settings=settings, model=ToolsModel(), trace=trace, approve=NO)
    assert [e.detail["arguments"] for e in trace.tool_calls("run_skill")] == [{"name": "resize_image"}]
    assert len(trace.tool_calls("detect_focal_point")) == 1
    crops = trace.tool_calls("crop")
    assert len(crops) == 5 and all(json.loads(json.dumps(e.detail["result"]))["product_whole"] for e in crops)
    assert trace.tool_calls("scale") == []


def test_check_copy_catches_long_words_and_banned_claims(settings):
    """Ready-made: check_copy flags a headline over the limit and a banned claim, so the agent can fix them while it works."""
    from launchkit.harness.main import build_catalogue

    check_copy = build_catalogue(settings, Trace(), NO).entries["check_copy"].fn
    result = check_copy("The bottle that stays cold forever on trails", "Eco-friendly steel", "")
    assert not result["ok"] and any("headline" in p for p in result["problems"]) and any("banned" in p for p in result["problems"])
