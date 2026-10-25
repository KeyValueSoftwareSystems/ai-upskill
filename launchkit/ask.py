"""Send one request through an approach and see everything that happened.

    uv run python -m launchkit.ask R1                       # one of Maya's four requests
    uv run python -m launchkit.ask "Poster for the Tidal bottle on a beach"
    uv run python -m launchkit.ask R1 --no-image            # skip the paid image call
    uv run python -m launchkit.ask --approach graph R1

It prints every model call (what was sent, what came back), the poster spec checked
against Harbor's rules, any answer, and the images that were made. `uv run python -m launchkit.ui`
shows the same thing in your browser.
"""
import argparse
import os
import textwrap

from . import llm
from .poster import FIELDS, ROOT, load_brand, validate_spec, word_count
from .scoreboard import APPROACHES, REQUESTS, load_handle


def run(text: str, *, handle, workspace: str = "harbor", conversation_id: str = "playground",
        no_image: bool = False) -> dict:
    """Run one request through `handle` and collect everything worth showing."""
    maya = next((r for r in REQUESTS if r["id"] == text.strip().upper()), None)
    if maya:
        text = maya["text"]
    brand = load_brand(workspace)

    first_call = len(llm.CALLS)
    old_images = os.environ.get("LAUNCHKIT_IMAGES")
    if no_image:
        os.environ["LAUNCHKIT_IMAGES"] = "placeholder"
    try:
        res = handle(text, workspace=workspace, conversation_id=conversation_id)
        error, spec, images, answer = res.error, res.spec, res.images, res.answer
    except Exception as e:  # show it like any other result instead of crashing
        error, spec, images, answer = f"{type(e).__name__}: {e}", None, [], None
    finally:
        if no_image:
            os.environ.pop("LAUNCHKIT_IMAGES", None) if old_images is None else os.environ.update(LAUNCHKIT_IMAGES=old_images)

    calls, sent_before = [], []
    for messages, reply in llm.CALLS[first_call:]:
        # A repair call resends the whole earlier conversation; only show what's new.
        repeated = len(sent_before) if sent_before and messages[:len(sent_before)] == sent_before else 0
        calls.append({"repeated": repeated, "messages": messages[repeated:], "reply": reply})
        sent_before = messages + [{"role": "assistant", "content": reply}]

    out = {"request": text, "calls": calls, "error": error, "answer": answer,
           "spec": None, "problems": [], "images": []}
    if spec:
        out["spec"] = []
        for f in FIELDS:
            value = getattr(spec, f)
            if isinstance(value, list):  # the storyboard's frames
                value = " · ".join(value)
            out["spec"].append({"field": f, "value": value, "words": word_count(value),
                                "limit": brand["copy_limits"].get(f)})
        out["problems"] = validate_spec(spec, brand)
    for p in images:
        out["images"].append({"path": os.path.relpath(p.path, ROOT), "size": list(p.size), "prompt": p.prompt,
                              "resized_from": p.resized_from and os.path.basename(p.resized_from),
                              "placeholder": p.placeholder, "source": p.source})
    return out


def heading(title: str) -> None:
    print(f"\n── {title} " + "─" * max(0, 60 - len(title)))


def show(label: str, text: str) -> None:
    body = textwrap.indent(text.strip() or "(empty)", " " * 12)
    print(f"  {label:<9} {body.lstrip()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("request", help="R1 to R4 (Maya's requests), or your own request")
    parser.add_argument("--approach", default="llm", choices=list(APPROACHES))
    parser.add_argument("--workspace", default="harbor")
    parser.add_argument("--conv", default="playground", help="reuse the same name to stay in one conversation")
    parser.add_argument("--no-image", action="store_true", help="draw a placeholder instead of a paid image call")
    args = parser.parse_args()

    r = run(args.request, handle=load_handle(args.approach), workspace=args.workspace,
            conversation_id=args.conv, no_image=args.no_image)

    heading("Request")
    print("  " + r["request"])
    for i, call in enumerate(r["calls"], 1):
        heading(f"Model call {i}")
        if call["repeated"]:
            print(f"  (everything from call {i - 1}, including its reply, then:)")
        for m in call["messages"]:
            show(m["role"], str(m["content"]))
        show("→ reply", call["reply"])
    if r["error"]:
        heading("No poster")
        print("  " + r["error"])
    if r["answer"]:
        heading("Answer")
        print(textwrap.indent(r["answer"].strip(), "  "))
    if r["spec"]:
        heading("Poster spec")
        for row in r["spec"]:
            print(f"  {row['field']:<15} {row['value']}" +
                  (f"  ({row['words']} words, limit {row['limit']})" if row["limit"] else ""))
        heading("Harbor's rules (checked here, whatever your code does)")
        for p in r["problems"]:
            print(f"  ✗ {p}")
        if not r["problems"]:
            print("  ✓ all followed")
    if r["images"]:
        heading("Images")
        for img in r["images"]:
            w, h = img["size"]
            if img["resized_from"]:
                how = f"resized by code from {img['resized_from']}"
            elif img["placeholder"]:
                how = ("PLACEHOLDER drawn by code, no image model call (--no-image or LAUNCHKIT_IMAGES=placeholder). "
                       f"The image model would have been asked for: {img['prompt']}")
            else:
                how = f"made by the image model from: {img['prompt']}"
            print(f"  {img['path']}  ({w}x{h})\n      {how}")


if __name__ == "__main__":
    main()
