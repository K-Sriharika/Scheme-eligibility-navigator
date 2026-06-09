"""
scorer.py

Turns one agent run into numbers. The metrics, and why each one matters:

  - precision / recall / F1 on the eligible-scheme set:
        Did it recommend the right schemes, no more and no fewer? This is the
        core correctness signal.
  - hallucination_count:
        Did it return any scheme_id that does not exist in the dataset? Inventing
        a benefit a citizen can't actually claim is the worst failure, so it is
        scored separately and weighted hard.
  - reasoning_ok (optional, LLM-judged):
        For each correctly-included scheme, does the stated reason actually match
        the real rule, or is it hand-wavy / wrong? Catches "right answer, wrong
        reasoning", which is what the optimizer often needs to fix.
  - efficiency (tool_calls, turns, cost):
        Reported for transparency. We do not punish thoroughness, but a sensible
        agent should not make wildly redundant calls.

The weighted composite score is what the optimizer tries to push up.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class CaseScore:
    case_id: str
    precision: float
    recall: float
    f1: float
    hallucination_count: int
    expected: list[str]
    predicted: list[str]
    tool_calls: int
    num_turns: int
    cost_usd: float
    composite: float
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _prf(expected: set[str], predicted: set[str]) -> tuple[float, float, float]:
    if not expected and not predicted:
        return 1.0, 1.0, 1.0
    tp = len(expected & predicted)
    precision = tp / len(predicted) if predicted else (1.0 if not expected else 0.0)
    recall = tp / len(expected) if expected else (1.0 if not predicted else 0.0)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return precision, recall, f1


def score_case(
    case_id: str,
    expected_ids: list[str],
    run,  # agent.AgentRun
    valid_scheme_ids: set[str],
) -> CaseScore:
    expected = set(expected_ids)
    predicted = set(run.eligible_ids)

    hallucinations = [sid for sid in predicted if sid not in valid_scheme_ids]
    # Hallucinated ids should not be credited as correct predictions.
    predicted_valid = predicted & valid_scheme_ids

    precision, recall, f1 = _prf(expected, predicted_valid)

    # Composite: F1 is the backbone; every hallucination applies a hard penalty.
    composite = max(0.0, f1 - 0.5 * len(hallucinations))

    return CaseScore(
        case_id=case_id,
        precision=round(precision, 3),
        recall=round(recall, 3),
        f1=round(f1, 3),
        hallucination_count=len(hallucinations),
        expected=sorted(expected),
        predicted=sorted(predicted),
        tool_calls=run.tool_calls,
        num_turns=run.num_turns,
        cost_usd=round(run.cost_usd, 5),
        composite=round(composite, 3),
        error=run.error,
    )


def aggregate(scores: list[CaseScore]) -> dict[str, Any]:
    n = len(scores) or 1
    return {
        "n_cases": len(scores),
        "mean_precision": round(sum(s.precision for s in scores) / n, 3),
        "mean_recall": round(sum(s.recall for s in scores) / n, 3),
        "mean_f1": round(sum(s.f1 for s in scores) / n, 3),
        "total_hallucinations": sum(s.hallucination_count for s in scores),
        "mean_composite": round(sum(s.composite for s in scores) / n, 3),
        "total_tool_calls": sum(s.tool_calls for s in scores),
        "total_cost_usd": round(sum(s.cost_usd for s in scores), 5),
        "n_errors": sum(1 for s in scores if s.error),
    }
