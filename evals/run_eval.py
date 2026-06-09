"""
run_eval.py

Runs the agent over every test case, computes the ground truth with the rule
engine, scores each run, and prints a scorecard.

Usage:
    python -m evals.run_eval
    python -m evals.run_eval --limit 3        # quick smoke test on 3 cases

Returns (when imported) the list of CaseScore plus the aggregate dict, so the
optimizer can reuse it.
"""

from __future__ import annotations
import argparse
import asyncio
import json
import pathlib
from typing import Any

from agent.agent import run_agent
from agent.tools import load_schemes
from agent.rule_engine import eligible_scheme_ids
from evals.scorer import score_case, aggregate, CaseScore

_CASES_PATH = pathlib.Path(__file__).parent / "test_cases.json"


def load_cases() -> list[dict[str, Any]]:
    return json.loads(_CASES_PATH.read_text())["cases"]


async def evaluate(system_prompt: str | None = None, limit: int | None = None) -> tuple[list[CaseScore], dict[str, Any]]:
    schemes = load_schemes()
    valid_ids = {s["id"] for s in schemes}
    cases = load_cases()
    if limit:
        cases = cases[:limit]

    scores: list[CaseScore] = []
    for case in cases:
        expected = eligible_scheme_ids(case["attributes"], schemes)
        run = await run_agent(case["profile_text"], system_prompt=system_prompt)
        scores.append(score_case(case["id"], expected, run, valid_ids))

    return scores, aggregate(scores)


def print_scorecard(scores: list[CaseScore], agg: dict[str, Any]) -> None:
    print("\n" + "=" * 78)
    print(f"{'case':<28}{'F1':>6}{'prec':>7}{'rec':>7}{'halluc':>8}{'tools':>7}{'$':>9}")
    print("-" * 78)
    for s in scores:
        flag = "  ERR" if s.error else ""
        print(f"{s.case_id:<28}{s.f1:>6}{s.precision:>7}{s.recall:>7}"
              f"{s.hallucination_count:>8}{s.tool_calls:>7}{s.cost_usd:>9}{flag}")
    print("-" * 78)
    print(f"mean F1 {agg['mean_f1']}   mean composite {agg['mean_composite']}   "
          f"hallucinations {agg['total_hallucinations']}   "
          f"tool calls {agg['total_tool_calls']}   cost ${agg['total_cost_usd']}")
    print("=" * 78 + "\n")


async def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    scores, agg = await evaluate(limit=args.limit)
    print_scorecard(scores, agg)


if __name__ == "__main__":
    asyncio.run(_main())
