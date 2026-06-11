#!/usr/bin/env python3
"""
Evaluation harness for Scheme Eligibility Navigator agent.
"""

import asyncio
import json
import sys
from pathlib import Path

from agent.agent import run_agent
from agent.rule_engine import eligible_scheme_ids
from evals.scorer import CaseScore, aggregate, score_case


def _load_data() -> tuple[list[dict], list[dict], set[str]]:
    test_cases_path = Path("evals/test_cases.json")
    schemes_path = Path("data/schemes.json")

    if not test_cases_path.exists():
        print(f"Error: {test_cases_path} not found")
        sys.exit(1)
    if not schemes_path.exists():
        print(f"Error: {schemes_path} not found")
        sys.exit(1)

    with open(test_cases_path) as f:
        test_data = json.load(f)
    with open(schemes_path) as f:
        schemes_data = json.load(f)

    schemes = schemes_data["schemes"]
    valid_ids = {s["id"] for s in schemes}
    return test_data["test_cases"], schemes, valid_ids


async def evaluate(
    system_prompt: str | None = None,
    limit: int | None = None,
) -> tuple[list[CaseScore], dict]:
    test_cases, schemes, valid_ids = _load_data()
    cases_to_run = test_cases[:limit] if limit else test_cases

    scores: list[CaseScore] = []
    for case in cases_to_run:
        case_id = case["id"]
        profile_text = case["profile_text"]
        canonical = case["canonical"]

        ground_truth = eligible_scheme_ids(canonical, schemes)
        run = await run_agent(profile_text, system_prompt=system_prompt)
        s = score_case(case_id, ground_truth, run, valid_ids)
        scores.append(s)

    agg = aggregate(scores)
    return scores, agg


def print_scorecard(scores: list[CaseScore], agg: dict) -> None:
    for s in scores:
        status = f"ERR({s.error})" if s.error else f"F1={s.f1:.3f}"
        print(
            f"  {s.case_id}: {status}  precision={s.precision:.3f}"
            f"  recall={s.recall:.3f}  halluc={s.hallucination_count}"
            f"  composite={s.composite:.3f}"
        )
    print(
        f"\nMean F1: {agg['mean_f1']:.3f}  |  Mean composite: {agg['mean_composite']:.3f}"
        f"  |  Hallucinations: {agg['total_hallucinations']}  |  Errors: {agg['n_errors']}"
    )


async def _main_async() -> None:
    limit = None
    if len(sys.argv) > 1 and sys.argv[1] == "--limit":
        limit = int(sys.argv[2])

    print(f"Running eval on {'all' if not limit else limit} test cases...\n")
    scores, agg = await evaluate(limit=limit)
    print_scorecard(scores, agg)


def main() -> None:
    asyncio.run(_main_async())


if __name__ == "__main__":
    main()
