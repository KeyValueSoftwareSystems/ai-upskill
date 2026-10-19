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
