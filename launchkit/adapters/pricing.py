PRICES_AS_OF = "2026-10-14"

PRICES_PER_MILLION = {
    "gpt-5.5": (5.00, 0.50, 30.00),
    "gpt-5.4-mini": (0.75, 0.075, 4.50),
    "gpt-5.4-nano": (0.20, 0.02, 1.25),
    "gpt-5.2": (1.75, 0.175, 14.00),
    "gpt-5-mini": (0.25, 0.025, 2.00),
    "gpt-5-nano": (0.05, 0.005, 0.40),
}


def cost_usd(model: str, input_tokens: int, cached_tokens: int, output_tokens: int) -> float | None:
    model_id = model.split(":", 1)[-1]
    prices = PRICES_PER_MILLION.get(model_id)
    if prices is None:
        return None
    fresh = max(input_tokens - cached_tokens, 0)
    return (fresh * prices[0] + cached_tokens * prices[1] + output_tokens * prices[2]) / 1_000_000
