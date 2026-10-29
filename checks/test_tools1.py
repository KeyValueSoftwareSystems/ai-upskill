from PIL import Image

from launchkit.harness.main import build_catalogue
from launchkit.harness.picture_tools import PictureDesk
from launchkit.harness.trace import Trace

BOTTLE = [492, 596, 660, 950]
SIZES = [(1080, 1080), (1080, 1350), (1080, 1920), (1200, 628), (300, 250)]
COLOURS = {"navy": "#1F3A5F", "sea_glass": "#A8D5BA"}


def desk(settings, trace=None):
    return PictureDesk(settings, COLOURS, trace or Trace())


def holds_bottle(window) -> bool:
    left, top, right, bottom = window
    return left <= BOTTLE[0] and top <= BOTTLE[1] and right >= BOTTLE[2] and bottom >= BOTTLE[3]


def test_centre_crop_makes_every_size(settings):
    """centre_crop gives back a file at each Harbor size."""
    d = desk(settings)
    for w, h in SIZES:
        result = d.centre_crop(w, h)
        assert Image.open(result["file"]).size == (w, h)


def test_centre_crop_cuts_the_bottle_in_the_banner(settings):
    """Cutting from the centre keeps the bottle whole in four sizes and cuts its base in the web banner."""
    d = desk(settings)
    kept = {(w, h): holds_bottle(d.centre_crop(w, h)["window"]) for w, h in SIZES}
    assert kept.pop((1200, 628)) is False
    assert all(kept.values())


def test_detect_focal_point_finds_the_bottle_once(settings):
    """detect_focal_point gives the bottle's box. It asks the model once per poster and keeps the box."""
    trace = Trace()
    d = desk(settings, trace)
    assert d.detect_focal_point()["box"] == BOTTLE
    d.detect_focal_point()
    assert sum("detect_focal_point asked" in str(e.detail) for e in trace.events) == 1


def test_crop_cuts_the_window_it_is_given(settings):
    """crop cuts any window, not only the centre, and scales it to the new size."""
    result = desk(settings).crop(1200, 628, 0, 560, 1200, 1188)
    assert Image.open(result["file"]).size == (1200, 628)


def test_expand_canvas_keeps_everything_and_adds_brand_bars(settings):
    """expand_canvas cuts nothing: the whole poster fits, and the new space is the brand colour asked for."""
    img = Image.open(desk(settings).expand_canvas(1200, 628, "navy")["file"])
    assert img.size == (1200, 628)
    assert img.getpixel((5, 300)) == (0x1F, 0x3A, 0x5F)


def test_scale_stretches_to_the_new_size(settings):
    """scale stretches the poster to the new shape: fast, and it squashes the bottle."""
    assert Image.open(desk(settings).scale(1080, 1920)["file"]).size == (1080, 1920)


def test_the_built_tools_join_the_catalogue(settings):
    """Once built, the five picture tools are in the main agent's catalogue."""
    entries = build_catalogue(settings, Trace(), lambda name, inputs: False).entries
    assert {"centre_crop", "detect_focal_point", "crop", "expand_canvas", "scale"} <= set(entries)
