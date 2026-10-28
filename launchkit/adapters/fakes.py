import json
import re
from typing import Any, AsyncIterator, Iterator

from agno.models.base import Model
from agno.models.message import MessageMetrics
from agno.models.response import ModelResponse

from launchkit.harness.context import approx_tokens

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

    def invoke(self, *args, **kwargs) -> ModelResponse:
        return self.answer(kwargs.get("messages") or [], kwargs.get("tools") or [])

    async def ainvoke(self, *args, **kwargs) -> ModelResponse:
        return self.answer(kwargs.get("messages") or [], kwargs.get("tools") or [])

    def invoke_stream(self, *args, **kwargs) -> Iterator[ModelResponse]:
        yield self.answer(kwargs.get("messages") or [], kwargs.get("tools") or [])

    async def ainvoke_stream(self, *args, **kwargs) -> AsyncIterator[ModelResponse]:
        yield self.answer(kwargs.get("messages") or [], kwargs.get("tools") or [])
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
        if "find_tool" in names and any(word in asked for word in ("size", "photo", "talking about", "voice", "board", "card")):
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
        if "card" in asked and "skill post_to_board" in listing:
            plan = [("run_skill", {"name": "post_to_board"}), ("run_tool", {"name": "read_card", "inputs": {"card": "tidal"}}),
                    ("run_tool", {"name": "attach_files", "inputs": {"card": "tidal", "files": new_sizes}}),
                    ("run_tool", {"name": "remove_files", "inputs": {"card": "tidal", "files": ["tidal-feed-1080x1080-approved.png", "tidal-story-1080x1920-approved.png"]}}),
                    ("run_tool", {"name": "update_status", "inputs": {"card": "tidal", "status": "Ready for review"}})]
        elif "board" in asked and "tool read_card" in listing:
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


COMPETITORS = ("Northline", "Ridgeway", "Stillwater", "Kestrel", "Alder Co.", "Ferro")


def competitors_in(text: str) -> list[str]:
    return [name for name in COMPETITORS if name.lower() in text.lower()]


def research_report(name: str) -> str:
    return f"{name}: launch line, channels and what to avoid copying, in two lines from two saved pages."


class BriefModel(FakeModel):
    """Plays both agents in the competitor job. As the main agent it finds the competitor_research skill, loads it and does
    what the skill names: search_web once per competitor, one after another, or research_many once.
    As the research subagent it searches once and replies with a two-line report. It keeps every view it was shown in seen."""

    def __init__(self):
        super().__init__("brief")
        self.seen: list[tuple[str, str]] = []

    def answer(self, messages, tools):
        view = " ".join(str(m.content or "") for m in messages)
        if "run_tool" in tool_names(tools):
            self.seen.append(("main", view))
            return self.main(messages)
        self.seen.append(("research", view))
        return self.research(messages)

    def research(self, messages):
        brief = last_user_text(messages)
        if not has_tool_result(messages):
            return tool_call_response("search_web", {"query": brief}, "search_1")
        return text_response(research_report(next(iter(competitors_in(brief)), "The competitor")), messages)

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
        return text_response("\n".join(research_report(name) for name in wanted), messages)
