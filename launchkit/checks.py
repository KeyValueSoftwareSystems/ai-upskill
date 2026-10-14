"""Pass/fail checks for the four requests. Each returns (passed, reason)."""
from .images import read_meta
from .spec import validate_spec, word_count


PRODUCT_WORDS = {"tidal", "bottle", "harbor", "flask", "trail", "colour", "colours", "palette", "with", "from", "that", "this", "soft"}


def _words(text):
    words = {w.strip(".,;:'\"").lower() for w in text.split() if len(w) > 3}
    return words - PRODUCT_WORDS


def _valid(res, brand):
    if res is None or res.error:
        return False, f"no poster: {res.error if res else 'nothing returned'}"
    if res.spec is None:
        return False, "no poster spec returned"
    problems = validate_spec(res.spec, brand)
    if problems:
        return False, "invalid spec: " + "; ".join(problems)
    if not res.images:
        return False, "no image generated"
    return True, ""


def check_r1(res, prev, brand):
    ok, why = _valid(res, brand)
    if not ok:
        return ok, why
    prompt = read_meta(res.images[0]).get("prompt", "")
    if res.spec.headline.lower() in prompt.lower():
        return False, "the headline was sent to the image model"
    return True, "valid spec, picture-only image"


def check_r2(res, prev, brand):
    before = next((p for p in reversed(prev) if p and p.spec), None)
    if before is None:
        return False, "R1 produced no poster to edit"
    ok, why = _valid(res, brand)
    if not ok:
        return ok, why + " (the call can't see the earlier poster)" if "spec" in why else why
    if word_count(res.spec.headline) >= word_count(before.spec.headline):
        return False, (f'headline not shorter ("{res.spec.headline}" vs "{before.spec.headline}"): '
                       "the earlier poster isn't in the model's context")
    if len(_words(before.spec.visual_concept) & _words(res.spec.visual_concept)) < 3:
        return False, "a different poster came back: the earlier concept isn't in the model's context"
    return True, f'"{before.spec.headline}" became "{res.spec.headline}"'


def check_r3(res, prev, brand, attachment="assets/tidal_photo.png"):
    ok, why = _valid(res, brand)
    if not ok:
        return ok, why
    ref = read_meta(res.images[0]).get("reference")
    if not ref or not ref.endswith(attachment):
        return False, "the uploaded photo was ignored"
    return True, "poster built from the uploaded photo"


def check_r4(res, prev, brand):
    before = next((p for p in reversed(prev) if p and p.images), None)
    if before is None:
        return False, "no earlier poster to resize"
    if res is None or res.error or not res.images:
        return False, f"no image: {res.error if res else 'nothing returned'}"
    meta = read_meta(res.images[-1])
    if tuple(meta.get("size", [])) != (1080, 1920):
        w, h = (meta.get("size") or ["?", "?"])[:2]
        return False, f"got a new {w}x{h} image instead of resizing the poster"
    if meta.get("derived_from") != before.images[0]:
        return False, "a new image was generated instead of resizing the existing poster"
    return True, "resized the existing poster to 1080x1920"


CHECKS = {"R1": check_r1, "R2": check_r2, "R3": check_r3, "R4": check_r4}
