"""Run the hands-on one step at a time and see what your code does with the real model.

    uv run python -m launchkit.step llm              # run the step you're on
    uv run python -m launchkit.step llm --step 2     # run a specific step
    uv run python -m launchkit.step llm --no-image   # skip the paid image call

The runner works out which TODOs in approach_llm/app.py are done by trying your
functions on scripted inputs (no model calls), then runs the matching step live:
the request, what came back, checks, and the limitation that motivates the next TODO.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import importlib
import io
import json
import os
import re
import sys
import textwrap
import traceback
from pathlib import Path

from .brand import load_brand
from .images import read_meta
from .paths import ROOT
from .spec import FIELDS, PosterSpec, SpecError, validate_spec, word_count
from .step_fixtures import (CLEAN_REPLY, FOLLOW_UP, R1, RECORDED_FENCED_REPLY,
                            RECORDED_VIOLATING_REPLY, TRAP_REQUEST)

APP_FILE = ROOT / "approach_llm" / "app.py"
TODO_OF = {"build_prompt": 1, "parse_spec": 2, "get_valid_spec": 3, "handle": 4}
MAX_CHAT_CALLS = 3
WIDTH = 100
TICK, CROSS = "✓", "✗"

LIMITATION = {
    0: "The model doesn't know Harbor's rules or the shape of answer we need.",
    1: "The reply is text, not data; one stray sentence breaks it.",
    2: "We can read the reply, but nothing stops it breaking the rules.",
    3: "The copy is baked into the picture, so it can't be edited, resized or set in "
       "Harbor's font, and spelling isn't guaranteed.",
    4: "A single call has no memory. The follow-up starts from nothing, so it can't edit "
       "the poster we just made.",
}
NEXT = {
    0: "TODO 1, build the prompt (build_prompt in approach_llm/app.py).",
    1: "TODO 2, parse the reply (parse_spec in approach_llm/app.py).",
    2: "TODO 3, validate and allow one repair (get_valid_spec in approach_llm/app.py).",
    3: "TODO 4, picture only (the generate_image line in handle, approach_llm/app.py).",
    4: "git checkout session-01-langgraph",
}
TITLE = {0: "nothing done yet", 1: "prompt done", 2: "parsing done", 3: "validation done", 4: "all done"}


class CallBudgetUsed(Exception):
    """This step has already made MAX_CHAT_CALLS model calls."""


# ---------------------------------------------------------------- output helpers

def say(text: str = "", indent: int = 0) -> None:
    pad = " " * indent
    for line in (text.splitlines() or [""]):
        wrapped = textwrap.wrap(line, WIDTH - indent, subsequent_indent="  ",
                                break_long_words=False, break_on_hyphens=False) or [""]
        for part in wrapped:
            print(pad + part, flush=True)


def section(title: str) -> None:
    print()
    say(title)


def check(ok: bool, text: str) -> None:
    say(f"{TICK if ok else CROSS} {text}", indent=2)


def show(text: str, limit: int = 900) -> None:
    """A model reply, indented and cut down to a readable size."""
    text = text.strip() or "(empty reply)"
    if len(text) > limit:
        text = text[:limit].rstrip() + f" … ({len(text) - limit} more characters)"
    say(text, indent=4)


def show_messages(messages: list[dict]) -> None:
    for m in messages:
        content = " ".join(str(m.get("content", "")).split())
        if len(content) > 140:
            content = content[:140] + f" … ({len(content)} characters)"
        say(f"{m.get('role', '?'):<9} {content}", indent=4)


def show_spec(spec: PosterSpec, brand: dict) -> None:
    limits = brand["copy_limits"]
    for f in FIELDS:
        value = getattr(spec, f)
        note = f"  ({word_count(value)} words, limit {limits[f]})" if f in limits else ""
        say(f"{f:<15} {value}{note}", indent=4)


def highlight(text: str, part: str) -> str:
    i = text.lower().find(part.lower())
    if i < 0 or not part:
        return text
    return f"{text[:i]}>>>{text[i:i + len(part)]}<<<{text[i + len(part):]}"


def error_line(e: Exception) -> str:
    return f"{type(e).__name__}: {' '.join(str(e).split())[:200]}"


# ---------------------------------------------------------------- loading and patching

def load_app():
    try:
        return importlib.import_module("approach_llm.app")
    except SyntaxError as e:
        say(f"approach_llm/app.py doesn't load: {e.msg} at line {e.lineno}.")
        say("Check the snippet you just pasted: indentation, and that you replaced the whole function.")
    except Exception as e:
        line = next((f.lineno for f in reversed(traceback.extract_tb(e.__traceback__))
                     if Path(f.filename).resolve() == APP_FILE), None)
        say(f"approach_llm/app.py doesn't load: {error_line(e)}" + (f" (line {line})" if line else ""))
    sys.exit(1)


@contextlib.contextmanager
def patched(module, name: str, value):
    old = getattr(module, name)
    setattr(module, name, value)
    try:
        yield
    finally:
        setattr(module, name, old)


@contextlib.contextmanager
def replaced(app, name: str, value):
    """Replace a function both in the app module and where it's defined, then restore both."""
    from . import images, llm

    home = {"complete": llm, "generate_image": images}[name]
    with patched(app, name, value), patched(home, name, value):
        yield


@contextlib.contextmanager
def env(name: str, value: str):
    old = os.environ.get(name)
    os.environ[name] = value
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = old


# ---------------------------------------------------------------- detecting progress

def scripted(*replies: str):
    """A stand-in for complete() that returns the given replies in order (detection only)."""
    calls: list[list[dict]] = []

    def fake(messages, *args, **kwargs):
        calls.append(copy.deepcopy(messages))
        if len(calls) > 5:
            raise RuntimeError("called the model more than 5 times")
        return replies[min(len(calls), len(replies)) - 1]

    return fake, calls


def probe_prompt(app, brand) -> tuple[bool, str]:
    try:
        messages = app.build_prompt("A poster for the bottle.", brand)
    except Exception as e:
        return False, f"build_prompt raised {error_line(e)}"
    roles = [m.get("role") for m in messages] if isinstance(messages, list) else []
    if roles[:2] != ["system", "user"]:
        return False, (f"build_prompt returns {len(roles)} message(s) ({', '.join(map(str, roles))}); "
                       "it should return a system message, then the user message")
    system = str(messages[0].get("content", ""))
    missing = [f'banned claim "{c}"' for c in brand["banned_claims"] if c.lower() not in system.lower()]
    missing += [f"{f} limit ({n} words)" for f, n in brand["copy_limits"].items()
                if not re.search(rf"\b{n}\b", system)]
    missing += [f'key "{f}"' for f in FIELDS if f not in system]
    if missing:
        return False, "the system message is missing: " + ", ".join(missing)
    return True, "build_prompt sends Harbor's rules and the JSON shape"


def probe_parse(app, brand) -> tuple[bool, str]:
    clean = json.loads(CLEAN_REPLY)
    cases = {"inside a ```json fence": f"```json\n{CLEAN_REPLY}\n```",
             "inside prose": f"Here's the spec: {CLEAN_REPLY} Hope that helps."}
    for where, raw in cases.items():
        try:
            spec = app.parse_spec(raw)
        except Exception as e:
            return False, f"parse_spec can't read JSON {where} ({error_line(e)})"
        if getattr(spec, "headline", None) != clean["headline"]:
            return False, f"parse_spec read JSON {where} but returned the wrong spec"
    try:
        app.parse_spec("Sorry, I can't help with that.")
    except SpecError:
        return True, "parse_spec finds JSON in prose and fences, and raises SpecError when there's none"
    except Exception as e:
        return False, f"with no JSON in the reply, parse_spec raised {type(e).__name__}; it should raise SpecError"
    return False, "with no JSON in the reply, parse_spec returned a spec; it should raise SpecError"


def probe_repair(app, brand) -> tuple[bool, str]:
    messages = [{"role": "system", "content": "probe"}, {"role": "user", "content": "probe"}]
    fake, calls = scripted(RECORDED_VIOLATING_REPLY, CLEAN_REPLY)
    try:
        with replaced(app, "complete", fake):
            spec = app.get_valid_spec(messages, brand)
    except Exception as e:
        return False, f"get_valid_spec raised {error_line(e)} on a reply one repair would fix"
    if len(calls) == 1:
        return False, "get_valid_spec called the model once and returned a spec that breaks Harbor's rules"
    if len(calls) != 2:
        return False, f"get_valid_spec called the model {len(calls)} times; allow exactly one repair"
    if "Fix these problems" not in json.dumps(calls[1]):
        return False, 'the repair call should include "Fix these problems" and the list of problems'
    if getattr(spec, "headline", None) != json.loads(CLEAN_REPLY)["headline"]:
        return False, "get_valid_spec didn't return the repaired spec"

    fake, calls = scripted(RECORDED_VIOLATING_REPLY)
    try:
        with replaced(app, "complete", fake):
            app.get_valid_spec(messages, brand)
    except SpecError:
        return True, "get_valid_spec validates, repairs once, then raises SpecError"
    except Exception as e:
        return False, f"a reply that stays bad should raise SpecError, but get_valid_spec raised {error_line(e)}"
    return False, "a reply that stays bad should raise SpecError, but get_valid_spec returned a spec"


def probe_image(app, brand) -> tuple[bool, str]:
    sent: list[str] = []

    def recorder(visual_concept, *args, **kwargs):
        sent.append(visual_concept)
        return "probe.png"

    fake, _ = scripted(CLEAN_REPLY)
    try:
        with replaced(app, "complete", fake), replaced(app, "generate_image", recorder), \
                env("LAUNCHKIT_IMAGES", "placeholder"):
            res = app.handle(R1, workspace="harbor", conversation_id="step-probe", attachments=[])
    except Exception as e:
        return False, f"handle() raised {error_line(e)}"
    if not sent:
        return False, f"handle() never called generate_image ({getattr(res, 'error', None) or 'no error given'})"
    clean = json.loads(CLEAN_REPLY)
    if clean["headline"].lower() in sent[0].lower():
        return False, "handle() sends the headline to the image model"
    if clean["visual_concept"] not in sent[0]:
        return False, "handle() doesn't send the visual concept to the image model"
    return True, "handle() sends the picture only"


PROBES = [probe_prompt, probe_parse, probe_repair, probe_image]


def detect(app, brand) -> list[tuple[bool, str]]:
    results = []
    for probe in PROBES:
        with contextlib.redirect_stdout(io.StringIO()):  # hide any prints in the trainee's code
            results.append(probe(app, brand))
    return results


# ---------------------------------------------------------------- live calls

class Session:
    """Wraps the real complete() with a logger and a per-step call budget."""

    def __init__(self, app, paid_images: bool):
        self.app = app
        self.paid_images = paid_images
        self.calls: list[tuple[list[dict], str]] = []

    @contextlib.contextmanager
    def logging(self):
        real = self.app.complete

        def logged(messages, *args, **kwargs):
            if len(self.calls) >= MAX_CHAT_CALLS:
                raise CallBudgetUsed()
            reply = real(messages, *args, **kwargs)
            self.calls.append((copy.deepcopy(messages), reply))
            return reply

        with replaced(self.app, "complete", logged):
            yield

    def ask(self, messages: list[dict]) -> str:
        print()
        say("Calling the model (live)…", indent=2)
        with self.logging():
            return self.app.complete(messages)

    def handle(self, text: str, conversation_id: str, paid_image: bool = True):
        image = "a paid image" if paid_image and self.paid_images else "a placeholder image, no paid call"
        print()
        say(f"Running your handle() (live model, {image})…", indent=2)
        images = "openai" if paid_image and self.paid_images else "placeholder"
        with self.logging(), env("LAUNCHKIT_IMAGES", images):
            return self.app.handle(text, workspace="harbor", conversation_id=conversation_id, attachments=[])


def try_parse(app, raw: str):
    """Run the trainee's parse_spec; return (spec, None) or (None, the exception)."""
    try:
        return app.parse_spec(raw), None
    except Exception as e:
        return None, e


def problems_of(app, raw: str, brand: dict) -> list[str]:
    spec, err = try_parse(app, raw)
    return [f"parse_spec: {error_line(err)}"] if err else validate_spec(spec, brand)


def show_image(res, spec: PosterSpec) -> bool:
    path = res.images[0]
    prompt = read_meta(path).get("prompt", "")
    rel = os.path.relpath(path, ROOT)
    placeholder = " (placeholder, no paid call)" if os.getenv("LAUNCHKIT_IMAGES") == "placeholder" else ""
    section("Image")
    say(f"{rel}{placeholder}", indent=4)
    section("Prompt sent to the image model")
    say(highlight(prompt, spec.headline), indent=4)
    clean = spec.headline.lower() not in prompt.lower()
    if not clean:
        say("(>>> <<< marks the headline)", indent=4)
    print()
    check(clean, "the image prompt has no headline" if clean
          else f'the headline "{spec.headline}" was sent to the image model')
    return clean


# ---------------------------------------------------------------- steps

def request(text: str, conversation: str | None = None) -> None:
    section("Request" + (f" (conversation {conversation})" if conversation else ""))
    say(text, indent=4)


def step0(s: Session, brand: dict) -> None:
    request(R1)
    messages = s.app.build_prompt(R1, brand)
    section("Messages your build_prompt sends")
    show_messages(messages)
    raw = s.ask(messages)
    section("Model reply (live)")
    show(raw)
    section("Checks")
    check(any(m.get("role") == "system" for m in messages), "the model was told Harbor's rules")
    spec, err = try_parse(s.app, raw)
    if err:
        check(False, f"parse_spec (TODO 2) failed on the reply: {error_line(err)}")
        return
    check(True, "parse_spec read the reply as a PosterSpec")
    problems = validate_spec(spec, brand)
    check(not problems, "the copy follows Harbor's rules" if not problems else "; ".join(problems))


def step1(s: Session, brand: dict) -> None:
    request(R1)
    messages = s.app.build_prompt(R1, brand)
    section("Messages your build_prompt sends")
    show_messages(messages)
    raw = s.ask(messages)
    section("Model reply (live)")
    show(raw)
    section("Your parse_spec on that reply")
    spec, err = try_parse(s.app, raw)
    if err:
        check(False, f"parse_spec failed: {error_line(err)}")
    else:
        check(True, "parse_spec read it (the model sent clean JSON this time)")
        show_spec(spec, brand)

    section("Your parse_spec on a reply the model gave on another run (recorded)")
    show(RECORDED_FENCED_REPLY)
    print()
    spec, err = try_parse(s.app, RECORDED_FENCED_REPLY)
    if err:
        check(False, f"parse_spec failed: {error_line(err)}")
    else:
        check(True, "parse_spec read it")


def step2(s: Session, brand: dict) -> None:
    request(TRAP_REQUEST)
    raw = s.ask(s.app.build_prompt(TRAP_REQUEST, brand))
    section("Model reply (live)")
    show(raw)
    section("Your parse_spec on that reply")
    spec, err = try_parse(s.app, raw)
    if err:
        check(False, f"parse_spec raised {error_line(err)}")
    else:
        check(True, "parse_spec read it")
        show_spec(spec, brand)

    section("validate_spec (the runner reports these; nothing in your code enforces them yet)")
    problems = validate_spec(spec, brand) if spec else []
    for p in problems:
        check(False, p)
    if spec and problems:
        return
    if spec:
        check(True, "no problems")
        say("The model followed the rules this time. It won't always:", indent=2)
    else:
        say("This reply couldn't be read, so here's one that could:", indent=2)
    section("A reply the model gave on another run (recorded)")
    show(RECORDED_VIOLATING_REPLY)
    print()
    for p in problems_of(s.app, RECORDED_VIOLATING_REPLY, brand):
        check(False, p)


def show_attempts(s: Session, brand: dict) -> list[str]:
    problems: list[str] = []
    for i, (messages, reply) in enumerate(s.calls, 1):
        if i > 1:
            section("Repair message your get_valid_spec sent")
            show(str(messages[-1].get("content", "")))
        section(f"Attempt {i} (live reply)")
        show(reply, limit=600)
        print()
        problems = problems_of(s.app, reply, brand)
        for p in problems:
            check(False, p)
        if not problems:
            check(True, "no problems")
    return problems


def step3(s: Session, brand: dict) -> None:
    request(TRAP_REQUEST)
    res = s.handle(TRAP_REQUEST, "step-3")
    show_attempts(s, brand)
    if len(s.calls) == 1 and res.spec:
        print()
        say("Attempt 1 was already clean, so no repair was needed this time. The runner tested the "
            "repair path with a scripted reply before this run; that's how it knows TODO 3 is done.", indent=2)
    if res.error:
        print()
        check(True, f"get_valid_spec stopped instead of returning a bad poster: {res.error}")
        say("To show the image prompt, trying the plain request once more:", indent=2)
        request(R1)
        before = len(s.calls)
        try:
            res = s.handle(R1, "step-3")
        except CallBudgetUsed:
            say(f"Skipped: this step makes at most {MAX_CHAT_CALLS} model calls. Run it again.", indent=2)
            return
        if res.error:
            check(False, f"no poster this time either: {res.error}")
            return
        say(f"({len(s.calls) - before} more model call(s))", indent=4)

    section("Spec returned by get_valid_spec")
    show_spec(res.spec, brand)
    problems = validate_spec(res.spec, brand)
    print()
    check(not problems, "the spec follows Harbor's rules" if not problems else "; ".join(problems))
    show_image(res, res.spec)


def step4(s: Session, brand: dict) -> None:
    request(R1, "step-demo")
    first = s.handle(R1, "step-demo")
    if first.error:
        print()
        check(False, f"no poster: {first.error}")
        return
    section("Spec")
    show_spec(first.spec, brand)
    problems = validate_spec(first.spec, brand)
    print()
    check(not problems, "the spec follows Harbor's rules" if not problems else "; ".join(problems))
    show_image(first, first.spec)

    request(FOLLOW_UP, "step-demo")
    used = len(s.calls)
    try:
        second = s.handle(FOLLOW_UP, "step-demo", paid_image=False)
    except CallBudgetUsed:
        say(f"Stopped: this step makes at most {MAX_CHAT_CALLS} model calls and the first poster "
            f"used {used}. Run it again.", indent=2)
        return
    section("Headlines")
    say(f'first      "{first.spec.headline}" ({word_count(first.spec.headline)} words)', indent=4)
    if second.spec:
        say(f'follow-up  "{second.spec.headline}" ({word_count(second.spec.headline)} words)', indent=4)
        section("Visual concepts")
        say(f"first      {first.spec.visual_concept}", indent=4)
        say(f"follow-up  {second.spec.visual_concept}", indent=4)
    else:
        say(f"follow-up  no poster: {second.error}", indent=4)
    sent = json.dumps([messages for messages, _ in s.calls[used:]]).lower()
    print()
    if first.spec.visual_concept.lower() in sent:  # the headline alone can match Harbor's facts
        check(True, "the follow-up call showed the model the first poster")
    else:
        check(False, f'the follow-up call never showed the model the first poster ("{first.spec.headline}"), '
                     "so it can't edit it")


STEPS = [step0, step1, step2, step3, step4]


# ---------------------------------------------------------------- errors

def api_fix(err: Exception) -> str | None:
    """One line telling the trainee how to fix an API error, or None if it isn't one."""
    import openai

    from .check_setup import _api_fix

    if not isinstance(err, openai.OpenAIError):
        return None
    if not isinstance(err, openai.APIError):  # raised before any request, e.g. no key
        return "No OpenAI key found. Add OPENAI_API_KEY to .env in the repo root (copy .env.example first)"
    url = str(getattr(getattr(err, "request", None), "url", ""))
    if "/images/" in url:
        return _api_fix(err, os.getenv("LAUNCHKIT_IMAGE_MODEL", "gpt-image-1"), "LAUNCHKIT_IMAGE_MODEL") + \
            ". Or add --no-image to skip the paid image call"
    return _api_fix(err, os.getenv("LAUNCHKIT_MODEL", "gpt-4.1-mini"), "LAUNCHKIT_MODEL")


def where_in_app(err: Exception) -> str | None:
    frames = [f for f in traceback.extract_tb(err.__traceback__) if Path(f.filename).resolve() == APP_FILE]
    if not frames:
        return None
    f = frames[-1]
    todo = TODO_OF.get(f.name)
    return f"{f.name}() at approach_llm/app.py line {f.lineno}" + (f" (TODO {todo})" if todo else "")


# ---------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("approach", choices=["llm"])
    parser.add_argument("--step", type=int, choices=range(5), metavar="{0..4}", help="run this step")
    parser.add_argument("--no-image", action="store_true", help="skip the paid image call")
    args = parser.parse_args(argv)
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(errors="replace")

    app = load_app()  # also loads .env
    if args.no_image:
        os.environ["LAUNCHKIT_IMAGES"] = "placeholder"
    paid_images = os.getenv("LAUNCHKIT_IMAGES", "openai") != "placeholder"
    brand = load_brand("harbor")

    progress = detect(app, brand)
    current = next((i for i, (done, _) in enumerate(progress) if not done), len(progress))
    step = current if args.step is None else args.step

    say("LaunchKit step runner: approach_llm/app.py")
    say("  ".join(f"{TICK if done else CROSS} TODO {i}" for i, (done, _) in enumerate(progress, 1)))
    later = [i for i, (done, _) in enumerate(progress, 1) if done and i > current + 1]
    if later:
        done = f"TODOs {', '.join(map(str, later))} look" if len(later) > 1 else f"TODO {later[0]} looks"
        say(f"\n{done} done, but TODO {current + 1} isn't: "
            f"{progress[current][1]}. Finish TODO {current + 1} first.")
    if step > current:
        needed = [str(i) for i in range(current + 1, step + 1)]
        todos = f"TODOs {', '.join(needed[:-1])} and {needed[-1]}" if len(needed) > 1 else f"TODO {needed[0]}"
        say(f"\nStep {step} needs {todos} done first.")
        say(f"TODO {current + 1} isn't done yet: {progress[current][1]}.")
        say("Run `uv run python -m launchkit.step llm` (without --step) to run the step you're on.")
        return 1
    if step < current:
        say(f"\nRe-running step {step} with your current code; later TODOs are done, so the output may "
            "look better than it did the first time.")
    if not paid_images:
        why = "--no-image" if args.no_image else "LAUNCHKIT_IMAGES=placeholder"
        say(f"Images: placeholder ({why}), no paid image call.")

    print()
    say(f"=== Step {step} of 4: {TITLE[step]} " + "=" * 40)
    session = Session(app, paid_images)
    try:
        STEPS[step](session, brand)
    except CallBudgetUsed:
        say(f"\nStopped: this step makes at most {MAX_CHAT_CALLS} model calls. Run it again.")
        return 1
    except Exception as e:
        fix = api_fix(e)
        if fix:
            say(f"\n{CROSS} {fix}")
            return 1
        where = where_in_app(e)
        if where is None:
            raise
        say(f"\n{CROSS} Your code raised {error_line(e)}")
        say(f"  in {where}")
        return 1

    print()
    say(f"Limitation: {LIMITATION[step]}")
    say(f"Next: {NEXT[step]}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(1)
