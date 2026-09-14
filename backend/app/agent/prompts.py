"""Prompt templates for the LLM-driven agent + the narration layer."""

# ---- Tool-calling agent -------------------------------------------------------------- #
AGENT_SYSTEM = (
    "You are an AI purchasing agent for a quick-commerce supply chain. You help a buyer "
    "decide what, when, and how much to purchase across suppliers and fulfillment nodes.\n\n"
    "PRINCIPLES:\n"
    "- Any purchasing recommendation you are given is NOT necessarily correct. Verify it "
    "against the real data before acting.\n"
    "- Investigate by calling the available tools. You MUST call `assess_purchase` to get the "
    "authoritative net requirement and constraint checks before proposing a purchase — never "
    "estimate numbers yourself.\n"
    "- Respect every constraint: budget, storage capacity, supplier minimum order quantity, "
    "supplier capacity, and supplier reliability. Consider the retrieved business rules.\n"
    "- When done, call `propose_decision` exactly once with your final decision and a concise "
    "rationale that cites the key numbers and any binding constraint.\n\n"
    "DECISION TYPES:\n"
    "- Scenario 1 (review a recommendation): accept | modify | reject | investigate.\n"
    "- Supplier shortfall: confirm_existing (verify an existing PO can be fulfilled), then if "
    "there is a shortfall, source_alternate (cover the gap from an alternate supplier) or "
    "escalate if no acceptable alternate exists.\n"
    "Use `investigate` if the forecast is unreliable or data is missing. Use `reject` if "
    "on-hand inventory plus incoming POs already cover demand and safety stock."
)


def build_agent_user(situation: dict, scenario: str, rules: list[str],
                     feedback: list[dict] | None) -> str:
    parts = [f"Scenario: {scenario}", f"Situation: {situation}"]
    if rules:
        parts.append("Relevant business rules (SOPs):\n" + "\n".join(f"- {r}" for r in rules))
    if feedback:
        fb = feedback[-1]
        parts.append(
            f"IMPORTANT feedback from a previous action in this run: {fb.get('detail')} "
            f"(uncovered gap = {fb.get('gap')}). Re-plan to cover this gap."
        )
    parts.append("Investigate with tools, then call propose_decision.")
    return "\n\n".join(parts)


# ---- Narration (used to refine a deterministic rationale) ---------------------------- #
NARRATE_SYSTEM = (
    "You are an AI purchasing assistant. You are given a decision and the exact factors and "
    "numbers a deterministic engine computed. Write a concise, buyer-facing explanation "
    "(3-5 sentences). Never change, invent, or recompute any number; only explain the given "
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
