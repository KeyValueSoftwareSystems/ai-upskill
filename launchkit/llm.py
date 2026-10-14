"""One function to call the language model: complete(messages) -> text.

Reads OPENAI_API_KEY (and optionally OPENAI_BASE_URL) and LAUNCHKIT_MODEL from .env.
"""
import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()
_client: OpenAI | None = None


def client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def complete(messages: list[dict], temperature: float = 0.7) -> str:
    reply = client().chat.completions.create(
        model=os.getenv("LAUNCHKIT_MODEL", "gpt-4.1-mini"),
        messages=messages,
        temperature=temperature,
    )
    return reply.choices[0].message.content or ""
