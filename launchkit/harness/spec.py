import re
from typing import Literal

from pydantic import BaseModel, Field


class PosterSpec(BaseModel):
    headline: str = Field(description="The big line on the poster. Up to 6 words.")
    subheadline: str = Field(description="The line under the headline. Up to 12 words.")
    body: str = Field(description="One short paragraph. Up to 25 words.")
    image_prompt: str = Field(description="What the picture shows: subject, setting, light, colours. No words to print.")
    format: str = Field(default="A3 portrait", description="Poster format, for example A3 portrait.")


class Turn(BaseModel):
    kind: Literal["poster", "reply"] = Field(description="poster when the marketer asks for a poster or a change to one. reply for anything else: a greeting, a question, small talk.")
    reply: str | None = Field(default=None, description="When kind is reply: a short, helpful message in the brand's voice. Otherwise null.")
    spec: PosterSpec | None = Field(default=None, description="When kind is poster: the filled poster form. Otherwise null.")


class SpecError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


WORD_LIMITS = {"headline": 6, "subheadline": 12, "body": 25}


def validate_spec(spec: PosterSpec, rules: dict) -> list[str]:
    # TODO step 2: word limits, banned claims from rules["banned_claims"], copy leaking into image_prompt
    return []


def repair_message(errors: list[str]) -> str:
    return "The poster spec broke these rules. Fix every one and return the whole spec again.\n- " + "\n- ".join(errors)
