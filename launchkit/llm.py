"""One function to call the language model: complete(messages) -> text.

All calls go through KeyValue's LiteLLM proxy, which speaks the OpenAI API, so we use the
openai client pointed at it. Reads LITELLM_API_KEY, LITELLM_BASE_URL and LAUNCHKIT_MODEL from .env.
Every call is also kept in CALLS, so `ask` can show you exactly what went to the model and back.
"""
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
_client: OpenAI | None = None
CALLS: list[tuple[list[dict], str]] = []  # (messages sent, reply text)


def client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("LITELLM_API_KEY"), base_url=os.getenv("LITELLM_BASE_URL"))
    return _client


def complete(messages: list[dict], temperature: float = 0.7) -> str:
    reply = client().chat.completions.create(
        model=os.getenv("LAUNCHKIT_MODEL", "gpt-4.1-mini"),
        messages=messages,
        temperature=temperature,
        # The proxy caches replies, so the same request would always get the same answer.
        # Skip the cache: seeing replies vary from run to run is part of the lesson.
        extra_body={"cache": {"no-cache": True}},
    )
    text = reply.choices[0].message.content or ""
    CALLS.append((list(messages), text))
    return text
