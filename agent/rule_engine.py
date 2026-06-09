"""
rule_engine.py

A small, deterministic evaluator for the structured eligibility criteria in
data/schemes.json.

Important design note:
    This engine is used by the EVAL HARNESS to compute the ground-truth set of
    eligible schemes for each test profile. It is deliberately NOT exposed to the
    agent as a tool. If the agent could call this, the task would be trivial and
    the eval meaningless. The agent's job is to read a messy, free-text profile,
    work out the person's attributes, and reason about each scheme's rules itself.
    This engine is the "answer key", not a crutch for the agent.
"""

from __future__ import annotations
from typing import Any


def _check_leaf(attributes: dict[str, Any], cond: dict[str, Any]) -> bool:
    """Evaluate a single leaf condition against the profile attributes.

    Conservative rule: if the profile does not contain the field the condition
    needs, the condition is treated as NOT satisfied. We cannot confirm
    eligibility on missing information.
    """
    field = cond["field"]
    op = cond["op"]
    value = cond["value"]

    if field not in attributes or attributes[field] is None:
        return False

    actual = attributes[field]

    if op == "==":
        return actual == value
    if op == "!=":
        return actual != value
    if op == "<=":
        return actual <= value
    if op == ">=":
        return actual >= value
    if op == "<":
        return actual < value
    if op == ">":
        return actual > value
    if op == "in":
        return actual in value
    raise ValueError(f"Unknown operator: {op}")


def _check_condition(attributes: dict[str, Any], cond: dict[str, Any]) -> bool:
    """A condition is either a leaf, or an {"any_of": [...]} group (logical OR)."""
    if "any_of" in cond:
        return any(_check_condition(attributes, sub) for sub in cond["any_of"])
    return _check_leaf(attributes, cond)


def is_eligible(attributes: dict[str, Any], scheme: dict[str, Any]) -> bool:
    """A person is eligible for a scheme only if ALL its criteria are satisfied."""
    return all(_check_condition(attributes, c) for c in scheme["criteria"])


def eligible_scheme_ids(attributes: dict[str, Any], schemes: list[dict[str, Any]]) -> list[str]:
    """Return the sorted list of scheme ids the attributes qualify for."""
    return sorted(s["id"] for s in schemes if is_eligible(attributes, s))


if __name__ == "__main__":
    # Tiny self-test so you can sanity-check the engine without the API.
    import json
    import pathlib

    data = json.loads((pathlib.Path(__file__).parent.parent / "data" / "schemes.json").read_text())
    schemes = data["schemes"]

    sample = {
        "age": 24,
        "gender": "female",
        "annual_income": 180000,
        "occupation": "entrepreneur",
        "category": "OBC",
        "residence": "urban",
    }
    print("Eligible:", eligible_scheme_ids(sample, schemes))
