ORDER = ("rules", "task", "facts")
HEADERS = {"rules": "# Rules", "task": "# Task", "facts": "# Facts"}


def approx_tokens(text: str) -> int:
    return round(len(text) / 4)


def trim_to_budget(text: str, budget_tokens: int) -> tuple[str, bool]:
    limit = budget_tokens * 4
    if len(text) <= limit:
        return text, False
    cut = text.rfind("\n", 0, limit)
    return text[: cut if cut > 0 else limit], True


class ContextBuilder:
    def __init__(self, budgets: dict[str, int]):
        self.budgets = dict(budgets)
        self.sections: dict[str, str] = {}

    def set(self, name: str, text: str):
        if name not in ORDER:
            raise ValueError(f"unknown section {name!r}; sections are {ORDER}")
        self.sections[name] = text.strip()

    def rendered_sections(self) -> list[tuple[str, str, bool]]:
        out = []
        for name in ORDER:
            text = self.sections.get(name, "")
            if not text:
                continue
            kept, trimmed = trim_to_budget(text, self.budgets.get(name, 10**9))
            out.append((name, kept, trimmed))
        return out

    def render(self) -> str:
        return "\n\n".join(f"{HEADERS[name]}\n{text}" for name, text, _ in self.rendered_sections())

    def report(self) -> list[dict]:
        rows = []
        for name in ORDER:
            text = self.sections.get(name, "")
            kept, trimmed = trim_to_budget(text, self.budgets.get(name, 10**9)) if text else ("", False)
            rows.append(
                {
                    "section": name,
                    "tokens": approx_tokens(kept),
                    "given": approx_tokens(text),
                    "budget": self.budgets.get(name),
                    "trimmed": trimmed,
                }
            )
        return rows
