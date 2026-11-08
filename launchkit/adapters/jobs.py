"""Jobs: the piece that calls a model for one job, the way route() and on_failure() say.

Ready-made for ticket 8. Reference: page 11, "Jobs and the scoreboard".

A job is one kind of work that gets its own model: long_text, short_text, research, memory_write or
vision. `Jobs.first` gives the model a job starts with. `Jobs.in_order` runs a call and, when the
model fails, asks on_failure what to do next. Every choice is one `route` line in the trace, and every
call one `call` line, which is what the scoreboard adds up.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agno.exceptions import ModelProviderError

from launchkit.adapters.fakes import DownModel
from launchkit.adapters.models import model_name, resolve_model
from launchkit.adapters.routing import on_failure, route
from launchkit.trace import Trace


class Jobs:
    def __init__(self, settings, trace: Trace, models: dict[str, Any] | None = None, fixed: Any | None = None):
        self.settings = settings
        self.trace = trace
        # Ready-built models by name. The tests use it to hand in fakes; the app leaves it empty.
        self.given = dict(models or {})
        self.built: dict[tuple[str, str], Any] = {}
        # One model for every job, no routing: how `run_main(model=...)` and `--model fake:...` behave.
        self.fixed = fixed

    def build(self, job: str, name: str):
        """The model object for a name, built once per job and wired to write its calls to the scoreboard under
        that job. One object per job, so a model two jobs share bills each call to the right job."""
        if name in self.given:
            model = self.given[name]
        elif (job, name) in self.built:
            model = self.built[(job, name)]
        else:
            model = DownModel(name) if name in self.settings.down_models else resolve_model(self.settings, self.trace, name=name)
            self.built[(job, name)] = model
        if hasattr(model, "on_call") or not isinstance(model, (str, type(None))):
            try:
                model.on_call = lambda seconds, inp, cached, out, usd, job=job, name=name: self.trace.call(job, name, seconds, inp, cached, out, usd)
            except AttributeError:
                pass
        return model

    def choices(self, job: str, ask: str | None, skill: str | None) -> tuple[str, list[tuple[str, str]]]:
        if self.fixed is not None:
            return job, [(model_name(self.fixed), "given")]
        return route(job, self.settings, ask=ask, pick=self.settings.model or None, skill=skill)

    def first(self, job: str, ask: str | None = None, skill: str | None = None):
        """The model a job starts with, with its route line in the trace."""
        job, choices = self.choices(job, ask, skill)
        name, reason = choices[0]
        self.trace.route(job, name, reason)
        return self.fixed if self.fixed is not None else self.build(job, name)

    def in_order(self, job: str, call: Callable[[Any], Any], ask: str | None = None, skill: str | None = None):
        """Run `call(model)` on the job's first model; when it fails, do what on_failure says until it works or stops."""
        job, choices = self.choices(job, ask, skill)
        if self.fixed is not None:
            self.trace.route(job, choices[0][0], "given")
            return call(self.fixed)
        name, reason = choices[0]
        tried: list[str] = []
        while True:
            self.trace.route(job, name, reason)
            try:
                return call(self.build(job, name))
            except ModelProviderError as error:
                tried.append(name)
                remaining = [m for m, _ in choices if m not in tried]
                next_name = on_failure(job, tried, remaining, error)
                if next_name is None:
                    raise ModelProviderError(f"{name} did not answer for {job}: {getattr(error, 'message', error)}", status_code=503) from error
                reason = "retry" if next_name == name else "fallback"
                name = next_name
