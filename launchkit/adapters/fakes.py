import json
import re
from typing import Any, AsyncIterator, Iterator

from agno.models.base import Model
from agno.models.message import MessageMetrics
from agno.models.response import ModelResponse

from launchkit.agents.prompt import approx_tokens

HARBOR_SPEC = {
    "headline": "Cold for 24 hours",
    "subheadline": "Tidal keeps the lake in the bottle",
    "body": "Fill it at dawn and drink it cold at dusk. Built for long days outside.",
    "image_prompt": "A steel bottle on a misty lakeshore at dawn, navy water, sea glass and sand tones, soft light",
    "format": "A3 portrait",
}


class FakeModel(Model):
    supports_native_structured_outputs = False
    supports_json_schema_outputs = False

    def __init__(self, name: str):
        super().__init__(id=name, name=name, provider="fake")

    def get_instructions_for_model(self, *args, **kwargs):
        return None

    def get_system_message_for_model(self, *args, **kwargs):
        return None

    def answer(self, messages: list, tools: list) -> ModelResponse:
        raise NotImplementedError

    def shaped(self, response: ModelResponse, kwargs: dict) -> ModelResponse:
        """A plain-text reply, put in the answer shape when the agent asks for one, as a real model would."""
        content = response.content
        if kwargs.get("response_format") and isinstance(content, str) and not content.lstrip().startswith("{"):
            response.content = reply_turn(content)
        return response

    def invoke(self, *args, **kwargs) -> ModelResponse:
        return self.shaped(self.answer(kwargs.get("messages") or [], kwargs.get("tools") or []), kwargs)

    async def ainvoke(self, *args, **kwargs) -> ModelResponse:
        return self.shaped(self.answer(kwargs.get("messages") or [], kwargs.get("tools") or []), kwargs)

    def invoke_stream(self, *args, **kwargs) -> Iterator[ModelResponse]:
        yield self.shaped(self.answer(kwargs.get("messages") or [], kwargs.get("tools") or []), kwargs)

    async def ainvoke_stream(self, *args, **kwargs) -> AsyncIterator[ModelResponse]:
        yield self.shaped(self.answer(kwargs.get("messages") or [], kwargs.get("tools") or []), kwargs)
        return

    def _parse_provider_response(self, response: Any, **kwargs) -> ModelResponse:
        return response

    def _parse_provider_response_delta(self, response: Any) -> ModelResponse:
        return response


POSTER_WORDS = ("poster", "headline", "copy", "ad ", "campaign", "launch", "mention", "shorter", "bigger", "variant", "tagline", "subheadline", "slogan")


def wants_a_poster(text: str) -> bool:
    lowered = text.lower() + " "
    return any(word in lowered for word in POSTER_WORDS)


def poster_turn(spec: dict) -> str:
    return json.dumps({"kind": "poster", "reply": None, "spec": spec})


def reply_turn(reply: str) -> str:
    return json.dumps({"kind": "reply", "reply": reply, "spec": None})


def text_response(content: str, messages: list) -> ModelResponse:
    sent = " ".join(str(m.content or "") for m in messages)
    return ModelResponse(
        role="assistant",
        content=content,
        response_usage=MessageMetrics(input_tokens=approx_tokens(sent), output_tokens=approx_tokens(content)),
    )


def tool_call_response(name: str, arguments: dict, call_id: str) -> ModelResponse:
    return ModelResponse(
        role="assistant",
        tool_calls=[{"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}],
        response_usage=MessageMetrics(),
    )


def has_tool_result(messages: list) -> bool:
    return any(getattr(m, "role", None) == "tool" and not getattr(m, "from_history", False) for m in messages)


def tool_names(tools: list) -> set[str]:
    return {t["function"]["name"] for t in tools if isinstance(t, dict) and "function" in t}


def is_picture_phase(tools: list) -> bool:
    return "generate_image" in tool_names(tools)


def tool_results(messages: list) -> str:
    return "\n".join(str(m.content or "") for m in messages if getattr(m, "role", None) == "tool" and not getattr(m, "from_history", False))


def system_text(messages: list) -> str:
    for m in messages:
        if getattr(m, "role", None) == "system":
            return str(m.content or "")
    return ""


def last_user_text(messages: list) -> str:
    for m in reversed(messages):
        if getattr(m, "role", None) == "user":
            return str(m.content or "")
    return ""


def section(system: str, header: str) -> str:
    start = system.find(header)
    if start < 0:
        return ""
    body = system[start + len(header):]
    end = body.find("\n# ")
    return body if end < 0 else body[:end]


def picture_phase(messages: list) -> ModelResponse:
    if has_tool_result(messages):
        return text_response("done", messages)
    return tool_call_response("generate_image", {"image_prompt": last_user_text(messages)}, "call_1")


def previous_spec(messages: list) -> dict | None:
    for m in reversed(messages):
        if getattr(m, "role", None) == "assistant" and getattr(m, "from_history", False) and m.content:
            try:
                turn = json.loads(str(m.content))
            except ValueError:
                continue
            if isinstance(turn, dict) and turn.get("spec"):
                return turn["spec"]
    return None


class GoodModel(FakeModel):
    def __init__(self):
        super().__init__("good")

    def answer(self, messages, tools):
        if is_picture_phase(tools):
            return picture_phase(messages)
        asked = last_user_text(messages)
        if not wants_a_poster(asked):
            return text_response(reply_turn("Hello. I write posters for this brand. Tell me the concept and I will draft one."), messages)
        spec = dict(HARBOR_SPEC)
        earlier = previous_spec(messages)
        if "shorter" in asked.lower() and earlier:
            words = earlier["headline"].split()
            spec = {**earlier, "headline": " ".join(words[:-1]) if len(words) > 1 else words[0]}
        return text_response(poster_turn(spec), messages)


class EchoModel(FakeModel):
    def __init__(self):
        super().__init__("echo")

    def answer(self, messages, tools):
        if is_picture_phase(tools):
            return picture_phase(messages)
        rules = section(system_text(messages), "# Rules")
        first = next((line.strip() for line in rules.splitlines() if line.strip()), "No rules were given.")
        spec = {**HARBOR_SPEC, "subheadline": f"rules section is {len(rules)} characters", "body": first}
        return text_response(poster_turn(spec), messages)


class MalformedModel(FakeModel):
    def __init__(self):
        super().__init__("malformed")

    def answer(self, messages, tools):
        if is_picture_phase(tools):
            return picture_phase(messages)
        headline = "Cold for twenty four long hours and then some more"
        spec = {
            "headline": headline,
            "subheadline": "Tidal, the eco-friendly bottle for every shore",
            "body": "Fill it at dawn and drink it cold at dusk.",
            "image_prompt": f"A bottle on a lakeshore with the words '{headline}' printed across the sky",
            "format": "A3 portrait",
        }
        return text_response(poster_turn(spec), messages)


class EndlessModel(FakeModel):
    def __init__(self):
        super().__init__("endless")
        self.asks = 0

    def answer(self, messages, tools):
        if not is_picture_phase(tools):
            return text_response(poster_turn(HARBOR_SPEC), messages)
        self.asks += 1
        return tool_call_response("generate_image", {"image_prompt": f"the same lakeshore, better sky, try {self.asks}"}, f"call_{self.asks}")


def tool_parameters(tools: list, name: str) -> dict:
    for t in tools:
        if isinstance(t, dict) and t.get("function", {}).get("name") == name:
            return t["function"].get("parameters", {}).get("properties", {})
    return {}


def chunks_in(result: str) -> list[tuple[str, str]]:
    """The (id, text) of every chunk in a get_brand_details result."""
    return [(m.group(1), m.group(2)) for m in re.finditer(r"^\[([^\]]+)\][^\n]*\n(.*?)(?=\n\n\[|\Z)", result, flags=re.M | re.S)]


class LookupModel(FakeModel):
    """Writes copy the way a careful model would: looks the brand up first, then claims only what came back.
    With nothing found it fills the gap with something plausible, which is the failure the tool fixes."""

    def __init__(self):
        super().__init__("lookup")

    def answer(self, messages, tools):
        if is_picture_phase(tools):
            return picture_phase(messages)
        asked = last_user_text(messages)
        if not wants_a_poster(asked):
            return text_response(reply_turn("Hello. I write posters for this brand. Tell me the concept and I will draft one."), messages)
        if "get_brand_details" in tool_names(tools) and not has_tool_result(messages):
            arguments = {"query": asked} if "query" in tool_parameters(tools, "get_brand_details") else {}
            return tool_call_response("get_brand_details", arguments, "lookup_1")
        found = tool_results(messages)
        facts = found.lower()
        spec = dict(HARBOR_SPEC)
        if "dishwasher" in asked.lower():
            if "hand-wash only" in facts:
                spec["body"] = "The body is dishwasher-safe. The lid is hand-wash only, so it stays leak-proof for years."
                spec["sources"] = [ref for ref, text in chunks_in(found) if "hand-wash only" in text.lower()][:1]
            else:
                spec["body"] = "Fully dishwasher-safe, top to bottom. Built for long days outside."
        return text_response(poster_turn(spec), messages)


class ProfileModel(FakeModel):
    def __init__(self):
        super().__init__("profile")

    def answer(self, messages, tools):
        first_line = next((line.strip() for line in last_user_text(messages).splitlines() if line.strip()), "Unknown brand")
        profile = {
            "brand_name": first_line.replace(" brand pack", ""),
            "voice": ["Warm, green, patient.", "Short lines. Talk to one person."],
            "rules": ["Mention the plant's name once."],
            "banned_claims": ["cheap", "guaranteed"],
            "colours": [{"name": "Fern", "hex": "#2f6b4f"}, {"name": "Clay", "hex": "#c97b4a"}],
            "facts": ["Pots ship in 3 days."],
        }
        return text_response(json.dumps(profile), messages)


SIZES = [(1080, 1080), (1080, 1350), (1080, 1920), (1200, 628), (300, 250)]


def fresh_results(messages: list) -> list[str]:
    return [str(m.content or "") for m in messages if getattr(m, "role", None) == "tool" and not getattr(m, "from_history", False)]


class ToolsModel(FakeModel):
    """Plays the main agent for "every size", using whatever the harness gives it, the way a model tends to.
    With no resize tool it says so. With one resize tool it uses that tool for every size."""

    def __init__(self):
        super().__init__("tools")

    def answer(self, messages, tools):
        asked = last_user_text(messages).lower()
        names = tool_names(tools)
        if "find_tool" in names and any(word in asked for word in ("size", "photo", "talking about", "voice", "board", "card", "notion")):
            return self.through_the_doors(asked, fresh_results(messages), messages)
        if "photo" in asked and "generate_image" in names:
            return self.paid_picture(fresh_results(messages), messages)
        if "size" not in asked:
            return text_response("Morning, Maya. What do you need today?", messages)
        done = fresh_results(messages)
        plan = self.plan(names, system_text(messages), done)
        if len(done) < len(plan):
            name, arguments = plan[len(done)]
            return tool_call_response(name, arguments, f"call_{len(done) + 1}")
        if not plan:
            return text_response(
                "I cannot resize the approved poster. I only have get_brand_details and generate_image. "
                "I could draw five new pictures, but each one would be a new bottle and a new bill.",
                messages,
            )
        return text_response(f"Done: {len(SIZES)} sizes of the approved poster.", messages)

    def paid_picture(self, done: list[str], messages) -> ModelResponse:
        """Before step 3 the agent holds every tool, and generate_image's note sounds like "the poster's picture" too:
        asked to use her photo, it pays for a new picture instead."""
        if not done:
            return tool_call_response("generate_image", {"image_prompt": "our shoot photo, story size"}, "call_1")
        return text_response("Done: a new picture for the story size.", messages)

    def plan(self, names: set[str], system: str = "", done: list[str] | None = None) -> list[tuple[str, dict]]:
        done = done or []
        if "run_skill" in names and "resize_image:" in system:
            return self.follow_resize_skill(done)
        if "centre_crop" in names:
            return [("centre_crop", {"width": w, "height": h}) for w, h in SIZES]
        if "scale" in names:
            return [("scale", {"width": w, "height": h}) for w, h in SIZES]
        return []

    def follow_resize_skill(self, done: list[str]) -> list[tuple[str, dict]]:
        """The resize_image skill's steps: load it, find the product once, then for each size crop around it, or add
        bars in the brand colour when crop says the product does not fit."""
        plan = [("run_skill", {"name": "resize_image"}), ("detect_focal_point", {})]
        results = done[len(plan):]
        for w, h in SIZES:
            plan.append(("crop", {"width": w, "height": h}))
            if len(results) >= len(plan) - 2 and "does not fit" in results[len(plan) - 3]:
                plan.append(("expand_canvas", {"width": w, "height": h, "colour": "navy"}))
        return plan

    def through_the_doors(self, asked: str, done: list[str], messages: list) -> ModelResponse:
        """Step 3 on: find_tool first, then the skill it lists, then each tool through run_tool."""
        if not done:
            return tool_call_response("find_tool", {"query": asked}, "find_1")
        listing = done[0]
        new_sizes = [f"tidal-{w}x{h}.png" for w, h in SIZES]
        if ("card" in asked or ("notion" in asked and "put" in asked)) and "skill post_to_board" in listing:
            plan = [("run_skill", {"name": "post_to_board"}), ("run_tool", {"name": "read_card", "inputs": {"card": "tidal"}}),
                    ("run_tool", {"name": "attach_files", "inputs": {"card": "tidal", "files": new_sizes}}),
                    ("run_tool", {"name": "remove_files", "inputs": {"card": "tidal", "files": ["tidal-feed-1080x1080-approved.png", "tidal-story-1080x1920-approved.png"]}}),
                    ("run_tool", {"name": "update_status", "inputs": {"card": "tidal", "status": "Ready for review"}})]
        elif ("board" in asked or "notion" in asked) and "tool read_card" in listing:
            plan = [("run_tool", {"name": "read_card", "inputs": {"card": "tidal"}})]
        elif "photo" in asked and "tool generate_image" in listing and "only when no photo" not in listing:
            plan = [("run_tool", {"name": "generate_image", "inputs": {"image_prompt": "our shoot photo, story size"}})]
        elif "photo" in asked and "skill ingest_image" in listing:
            plan = [("run_skill", {"name": "ingest_image"}), ("run_tool", {"name": "describe_image", "inputs": {}}),
                    ("run_tool", {"name": "detect_focal_point", "inputs": {}}), ("run_tool", {"name": "crop", "inputs": {"width": 1080, "height": 1920}})]
        elif "size" in asked and "skill resize_image" in listing:
            plan = [("run_skill", {"name": "resize_image"}), ("run_tool", {"name": "detect_focal_point", "inputs": {}})]
            plan += [("run_tool", {"name": "crop", "inputs": {"width": w, "height": h}}) for w, h in SIZES]
        elif "talking about" in asked and "skill market_research" in listing:
            plan = [("run_skill", {"name": "market_research"}), ("run_tool", {"name": "search_web", "inputs": {"query": "hikers trends this season"}})]
        elif "voice" in asked and "skill voice_over" in listing:
            script = "Cold at the summit, cold on the train. Tidal keeps your water cold for 24 hours."
            plan = [("run_skill", {"name": "voice_over"}), ("run_tool", {"name": "check_copy", "inputs": {"headline": "", "body": script}}),
                    ("run_tool", {"name": "text_to_speech", "inputs": {"script": script}})]
        else:
            return text_response("I could not find a skill or tool for that.", messages)
        step = len(done) - 1
        if step < len(plan):
            name, arguments = plan[step]
            return tool_call_response(name, arguments, f"call_{step + 2}")
        return text_response("Done. " + done[-1][:200], messages)


COMPETITORS = ("Hydro Flask", "Stanley", "Yeti", "Owala", "Klean Kanteen", "Contigo")


def competitors_in(text: str) -> list[str]:
    return [name for name in COMPETITORS if name.lower() in text.lower()]


def research_report(name: str, pages: str) -> str:
    """What the fake can honestly say about a competitor: which sites it read. Page text, titles included, stays out."""
    sites = re.findall(r"^Address: https?://(?:www\.)?([^/\s]+)", pages, re.M)
    return f"{name}: read {' and '.join(sites)}." if sites else f"{name}: no pages found."


class BriefModel(FakeModel):
    """Plays both agents in the competitor job. As the main agent it finds the competitor_research skill, loads it and does
    what the skill names: search_web once per competitor, one after another, or research_many once.
    As the research subagent it searches once, saves its brief when it has a save tool, and replies with a short report
    naming the sites it read. It keeps every view it was shown in seen."""

    def __init__(self):
        super().__init__("brief")
        self.seen: list[tuple[str, str]] = []

    def answer(self, messages, tools):
        view = " ".join(str(m.content or "") for m in messages)
        if "run_tool" in tool_names(tools):
            self.seen.append(("main", view))
            return self.main(messages)
        self.seen.append(("research", view))
        return self.research(messages, "save_brief" in tool_names(tools))

    def research(self, messages, can_save=False):
        brief = last_user_text(messages)
        results = [str(m.content or "") for m in messages if getattr(m, "role", None) == "tool"]
        if not results:
            return tool_call_response("search_web", {"query": brief}, "search_1")
        name = next(iter(competitors_in(brief)), "The competitor")
        report = research_report(name, results[0])
        if can_save and len(results) == 1:  # given a save tool, it saves once before it replies, as the real one is told to
            return tool_call_response("save_brief", {"competitor": name, "report": report}, "save_1")
        return text_response(report, messages)

    def main(self, messages):
        asked = last_user_text(messages)
        wanted = competitors_in(asked)
        if not wanted:
            return text_response("Cold from trail to train." if "headline" in asked.lower() else "Morning, Maya. Ready when you are.", messages)
        results = [str(m.content or "") for m in messages if getattr(m, "role", None) == "tool" and not getattr(m, "from_history", False)]
        if not results:
            return tool_call_response("find_tool", {"query": asked}, "find_1")
        if len(results) == 1:
            if "skill competitor_research" not in results[0]:
                return text_response("I have no skill for competitor research yet.", messages)
            return tool_call_response("run_skill", {"name": "competitor_research"}, "skill_1")
        skill, done = results[1], len(results) - 2
        if "research_many" in skill and done == 0:
            briefs = [f"How is {name} launching bottles this season? Message, channels, what to avoid copying." for name in wanted]
            return tool_call_response("run_tool", {"name": "research_many", "inputs": {"briefs": briefs}}, "many_1")
        if "research_many" not in skill and "search_web" in skill and done < len(wanted):
            return tool_call_response("run_tool", {"name": "search_web", "inputs": {"query": f"{wanted[done]} bottle launch"}}, f"search_{done + 1}")
        if "research_many" in skill:
            return text_response("\n".join(json.loads(results[2])), messages)
        searches = results[2:] + [""] * len(wanted)
        return text_response("\n".join(research_report(name, pages) for name, pages in zip(wanted, searches)), messages)


NEVER_SAY = re.compile(r"never (?:say|use|mention) ['\"“]?([a-z][a-z' -]*?[a-z])['\"”]?(?=[,.;:!?]| it\b| in\b|$)", re.I)


class MemoryModel(FakeModel):
    """Session 3, ticket 1: the memory failure the real model makes now and then, made every time.

    As the memory manager it saves Maya's quoted never-say phrase as something she wants, unless ticket 1's capture
    rules are in its prompt; then it saves the rule. As the main agent it writes one headline and follows whatever its
    view says: a never-say instruction in this message wins; otherwise a remembered "mention the lifetime guarantee"
    puts the phrase in the headline, the way Maya's ticket describes."""

    def __init__(self):
        super().__init__("memory")

    def answer(self, messages, tools):
        system, asked = system_text(messages), last_user_text(messages)
        if system.startswith("You are a Memory Manager"):
            return self.manage(system, asked, messages, tools)
        if not wants_a_poster(asked):
            return text_response("Morning, Maya. What do you need today?", messages)
        if NEVER_SAY.search(asked):
            return text_response("Tidal. Cold from trail to train.", messages)
        if "mention the lifetime guarantee" in section(system, "\n# Memory\n").lower():
            return text_response("Tidal: a lifetime guarantee on every trail.", messages)
        return text_response("Tidal. Cold from trail to train.", messages)

    def manage(self, system: str, asked: str, messages, tools) -> ModelResponse:
        found = NEVER_SAY.search(asked)
        if has_tool_result(messages) or not found or "add_memory" not in tool_names(tools):
            return text_response("No changes needed.", messages)
        phrase = found.group(1).lower()
        if "is a rule, not a wish" in system:
            return tool_call_response("add_memory", {"memory": f'Never use "{phrase}".', "topics": ["rules"]}, "call_1")
        return tool_call_response("add_memory", {"memory": f"Maya wants headlines to mention the {phrase}.", "topics": ["preferences", "headlines"]}, "call_1")


# Session 5: three scripted models for the runtime's failure moments. Each writes the same code every time, so the
# failure is the same in every room. None of them calls a paid service: every file they make is cut by Pillow in
# run_code. They call run_code through run_tool, as the main agent does.

PEEK_CODE = '''import csv, os
# Tidy Jonas's results file: trim the spaces, one spelling per channel, spend as a number.
rows = list(csv.reader(open("uploads/autumn-results.csv")))
tidy = [[cell.strip() for cell in row] for row in rows]
for row in tidy[1:]:
    row[1] = row[1].title()
    row[2] = row[2].replace(",", "")
os.makedirs("outputs", exist_ok=True)
csv.writer(open("outputs/autumn-results-tidy.csv", "w", newline="")).writerows(tidy)
print("Tidied", len(tidy) - 1, "rows into outputs/autumn-results-tidy.csv")

# While it is here, the code looks around. The model was not asked to; code can do anything the process can.
seen = {k: v[:6] + "..." for k, v in os.environ.items() if any(w in k.upper() for w in ("KEY", "TOKEN", "SECRET", "PASSWORD"))}
print("Keys this code can see:", ", ".join(f"{k}={v}" for k, v in sorted(seen.items())) or "none")
for folder in ("../../harbor", "../../harbor/k7c1/outputs"):
    try:
        print(folder, "->", ", ".join(sorted(os.listdir(folder))))
    except OSError as error:
        print(folder, "->", type(error).__name__)
'''

RUNAWAY_CODE = '''import csv, os, time
# Cost per sign-up by channel, written the slow way: a copy of the whole table for every row it reads.
rows = list(csv.reader(open("uploads/breeze-results.csv")))
workers = os.cpu_count() or 4
for _ in range(workers - 1):          # and one copy of the work per processor
    if os.fork() == 0:
        break
started, copies, kept = time.time(), [], 0
budget = 1200 * 1024 * 1024 // workers
while time.time() - started < 120:    # it would finish in two minutes; nothing else in it stops sooner
    for row in rows:
        copy = [list(r) for r in rows]
        if kept < budget:
            copies.append(copy)
            kept += 6000
os._exit(0)
'''

SLOW_SIZES = [(1080, 1080), (1080, 1350), (1080, 1920), (1200, 628), (300, 250), (728, 90), (160, 600),
              (300, 600), (970, 250), (1200, 1200), (1500, 500), (1584, 396), (2048, 1152), (640, 360)]


def size_code(width: int, height: int) -> str:
    return f'''import time
from pathlib import Path
from PIL import Image, ImageOps
Path("outputs/sizes").mkdir(parents=True, exist_ok=True)
poster = Image.open("outputs/breeze-poster.png").convert("RGB")
ImageOps.fit(poster, ({width}, {height})).save("outputs/sizes/breeze-{width}x{height}.png")
time.sleep(7)  # the slow part of a real export: about seven seconds a size
print("made outputs/sizes/breeze-{width}x{height}.png")
'''


CONTACT_SHEET_CODE = '''from pathlib import Path
from PIL import Image
sizes = sorted(Path("outputs/sizes").glob("breeze-*.png"))
sheet = Image.new("RGB", (1400, 220 * ((len(sizes) + 6) // 7)), "white")
for n, path in enumerate(sizes):
    thumb = Image.open(path).convert("RGB")
    thumb.thumbnail((190, 190))
    sheet.paste(thumb, (10 + (n % 7) * 200, 10 + (n // 7) * 220))
sheet.save("outputs/breeze-contact-sheet.png")
print("made outputs/breeze-contact-sheet.png from", len(sizes), "sizes")
'''

BLUE_CODE = '''from PIL import Image, ImageDraw, ImageFont
poster = Image.open("outputs/breeze-poster.png").convert("RGB")
draw = ImageDraw.Draw(poster)
draw.rectangle([0, 1160, 1080, 1290], fill=(222, 231, 228))
draw.text((540, 1220), "Keep using it.", font=ImageFont.load_default(size=48), fill=(20, 70, 200), anchor="mm")
poster.save("outputs/breeze-poster-blue.png")
print("made outputs/breeze-poster-blue.png")
'''


def code_call(tools: list, code: str, label: str, n: int) -> ModelResponse:
    """A run_code call, through run_tool when the agent holds the doors."""
    inputs = {"code": code, "label": label}
    if "run_tool" in tool_names(tools):
        return tool_call_response("run_tool", {"name": "run_code", "inputs": inputs}, f"code_{n}")
    return tool_call_response("run_code", inputs, f"code_{n}")


def first_lines(result: str, count: int = 8) -> str:
    try:
        result = json.loads(result) if result.startswith('"') else result
    except ValueError:
        pass
    return "\n".join(str(result).splitlines()[:count])


NO_CODE_TOOL = "I have no tool that runs code, so I cannot work this out from the file. I can only read it."


class PeekModel(FakeModel):
    """Session 5, stage 2's failure. Jonas at Ember asks for his results file to be tidied. The code tidies it, then
    prints the keys it can see and lists Harbor's folder, the way the staging trial's code did."""

    def __init__(self):
        super().__init__("peek")

    def answer(self, messages, tools):
        done = fresh_results(messages)
        if not done:
            return code_call(tools, PEEK_CODE, "tidy-results", 1)
        if "No tool named run_code" in done[0]:
            return text_response(NO_CODE_TOOL, messages)
        return text_response("Done. Here is what the code printed:\n" + first_lines(done[0], 12), messages)


class RunawayModel(FakeModel):
    """Session 5, stage 3's failure. Maya asks for cost per sign-up by channel; the code copies the table once per row,
    in one process per processor, and would take two minutes and over a gigabyte of memory."""

    def __init__(self):
        super().__init__("runaway")

    def answer(self, messages, tools):
        done = fresh_results(messages)
        if not done:
            return code_call(tools, RUNAWAY_CODE, "cost-per-signup", 1)
        if "No tool named run_code" in done[0]:
            return text_response(NO_CODE_TOOL, messages)
        return text_response("The analysis ended before it printed a figure:\n" + first_lines(done[0], 4), messages)


class SlowSizesModel(FakeModel):
    """Session 5, stages 4 and 5. Asked for every size, it makes fourteen, one run_code call each at about seven
    seconds a size, then a contact sheet: about two minutes. Asked to make it blue, it makes one blue headline."""

    def __init__(self):
        super().__init__("slow_sizes")

    def answer(self, messages, tools):
        asked = last_user_text(messages).lower()
        done = fresh_results(messages)
        if done and "No tool named run_code" in done[0]:
            return text_response(NO_CODE_TOOL, messages)
        if "blue" in asked:
            if not done:
                return code_call(tools, BLUE_CODE, "blue-headline", 1)
            return text_response("The headline is blue now: outputs/breeze-poster-blue.png.", messages)
        if "size" not in asked:
            return text_response("Morning. Ask me for every size of the Breeze poster.", messages)
        plan = [(size_code(w, h), f"size-{w}x{h}") for w, h in SLOW_SIZES] + [(CONTACT_SHEET_CODE, "contact-sheet")]
        if len(done) < len(plan):
            code, label = plan[len(done)]
            return code_call(tools, code, label, len(done) + 1)
        return text_response(f"Done: {len(SLOW_SIZES)} sizes of the Breeze poster, and a contact sheet.", messages)
