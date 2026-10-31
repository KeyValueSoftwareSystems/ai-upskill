from dataclasses import dataclass

from agno.exceptions import StopAgentRun


@dataclass(frozen=True)
class Limits:
    step_cap: int = 6
    image_budget: int = 3


def make_leash(limits: Limits, trace):
    calls = {"total": 0, "generate_image": 0}

    def leash(function_name: str, function_call, arguments: dict):
        calls["total"] += 1
        if calls["total"] > limits.step_cap:
            trace.stop(f"step cap of {limits.step_cap} tool calls reached, run ended")
            raise StopAgentRun(f"Step cap of {limits.step_cap} tool calls reached")
        if function_name == "generate_image":
            calls["generate_image"] += 1
            if calls["generate_image"] > limits.image_budget:
                reason = f"image budget of {limits.image_budget} spent"
                trace.refused(function_name, reason)
                return {"status": "refused", "reason": reason}
        before = len(trace.events)
        result = function_call(**arguments)
        if function_name != "run_tool" or len(trace.events) == before:
            trace.tool(function_name, arguments, result)
        return result

    return leash
