from dataclasses import dataclass


@dataclass(frozen=True)
class Limits:
    step_cap: int = 6
    image_budget: int = 3


def make_leash(limits: Limits, trace):
    def leash(function_name: str, function_call, arguments: dict):
        # TODO step 3: count calls, stop at limits.step_cap, refuse render_image past limits.image_budget
        return function_call(**arguments)

    return leash
