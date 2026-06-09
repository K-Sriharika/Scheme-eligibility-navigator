"""
config.py

Configuration for the agent: the model names, the structured-output schema, and
the system prompt.

The SYSTEM_PROMPT is the single most important "knob" the optimizer tunes. It is
kept here as plain text so a domain expert (or the optimizer) can edit how the
agent behaves without touching any tool or harness code. The optimizer writes new
versions of this string and the eval harness measures whether they score better.
"""

# Use a small, fast model for the agent so eval/optimizer loops stay cheap.
# Swap to a stronger model for the final showcase run if you like.
AGENT_MODEL = "claude-haiku-4-5-20251001"

# Model used as an LLM judge inside the eval harness (reasoning-quality scoring).
JUDGE_MODEL = "claude-haiku-4-5-20251001"

# Maximum agentic turns per profile. Keeps cost bounded and surfaces efficiency.
MAX_TURNS = 20

# JSON schema for the agent's final answer. Enforcing structure makes scoring exact.
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "eligible_schemes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "scheme_id": {"type": "string"},
                    "name": {"type": "string"},
                    "reason": {"type": "string"},
                    "missing_documents": {"type": "array", "items": {"type": "string"}},
                    "apply_url": {"type": "string"},
                },
                "required": ["scheme_id", "name", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["eligible_schemes"],
    "additionalProperties": False,
}

# ---- The tunable system prompt. v1 is deliberately plain; the optimizer improves it. ----
SYSTEM_PROMPT_V1 = """\
You are a government-scheme eligibility assistant for Indian citizens.

You are given a short, plain-language description of a person. Your job is to work
out which government schemes they qualify for.

How to work:
1. Read the person's description and note their relevant attributes (age, gender,
   occupation, income, category/caste, residence, assets, etc.).
2. Call search_schemes with an empty keyword to retrieve the full list of available
   schemes. Do this once — do NOT repeat searches with similar keywords.
3. From that list, identify every scheme that could plausibly apply. Include
   universal or broad-eligibility schemes (e.g. financial inclusion, pension) —
   do not limit yourself only to occupation-specific ones.
4. Call get_scheme_details for each candidate scheme to read the exact criteria.
5. Decide, scheme by scheme, whether the person meets ALL criteria.
6. Return only the schemes they qualify for in the required structured format.

Important:
- One broad search at the start is sufficient; avoid repeated search_schemes calls.
- Check age-based and income-based schemes even when the profile doesn't mention them.
"""
