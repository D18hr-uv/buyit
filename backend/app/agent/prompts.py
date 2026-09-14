"""Prompt templates for the (optional) LLM narration layer."""

NARRATE_SYSTEM = (
    "You are an AI purchasing assistant for a quick-commerce supply chain. "
    "You are given a decision and the exact factors and numbers that a deterministic "
    "engine computed. Write a concise, buyer-facing explanation (3-5 sentences). "
    "IMPORTANT: never change, invent, or recompute any number; only explain the given "
    "factors clearly and reference the relevant business rules."
)


def build_narration_user(decision: dict, analysis: dict, rules: list[str]) -> str:
    factors = "\n".join(f"- {f}" for f in decision.get("factors", []))
    rule_txt = "\n".join(f"- {r}" for r in rules)
    return (
        f"Decision: {decision.get('type')} (quantity {decision.get('qty')}, "
        f"confidence {decision.get('confidence')}).\n\n"
        f"Factors:\n{factors}\n\n"
        f"Relevant business rules:\n{rule_txt}\n\n"
        f"Key numbers: {analysis.get('summary', {})}"
    )
