"""
optimize.py

The optimizer loop. This is the part that mirrors Proptimise's "weekly improvement
cycle": measure, find what's failing, change one knob (the system prompt), measure
again, keep the change only if it actually helped.

Loop:
  1. Run the eval with the current best prompt -> baseline score.
  2. Collect the cases that scored worst, with their expected vs predicted sets.
  3. Ask Claude (the "prompt engineer") to rewrite the system prompt to fix those
     specific failure patterns.
  4. Re-run the eval with the candidate prompt.
  5. Keep it only if mean composite improved. Repeat for N rounds.

Output: a before/after table and the winning prompt, saved to optimizer/result.json.

Usage:
    python -m optimizer.optimize --rounds 2
"""

from __future__ import annotations
import argparse
import asyncio
import json
import pathlib

from anthropic import AsyncAnthropic

from agent import config
from evals.run_eval import evaluate, print_scorecard

_RESULT_PATH = pathlib.Path(__file__).parent / "result.json"
_client = AsyncAnthropic()


def _failure_digest(scores) -> str:
    """Compact, readable summary of where the agent went wrong."""
    lines = []
    for s in sorted(scores, key=lambda x: x.composite)[:6]:
        lines.append(
            f"- {s.case_id}: expected={s.expected} predicted={s.predicted} "
            f"f1={s.f1} hallucinations={s.hallucination_count}"
            + (f" ERROR={s.error}" if s.error else "")
        )
    return "\n".join(lines)


async def propose_new_prompt(current_prompt: str, scores) -> str:
    """Ask Claude to rewrite the system prompt to fix the observed failures."""
    digest = _failure_digest(scores)
    instruction = f"""\
You are improving the system prompt of an eligibility-checking agent.

Here is the CURRENT system prompt, delimited by triple backticks:
```
{current_prompt}
```

When evaluated, the agent made these mistakes (expected vs predicted scheme sets):
{digest}

Common failure patterns to consider: over-recommending schemes when a criterion is
unstated, missing income or age thresholds, ignoring caste/category conditions,
assuming eligibility on missing information, or inventing scheme ids.

Rewrite the system prompt so the agent makes fewer of these mistakes. Keep it clear
and concise. Do not invent new tools. Output ONLY the new system prompt text, with
no preamble, no backticks, no commentary.
"""
    resp = await _client.messages.create(
        model=config.JUDGE_MODEL,
        max_tokens=800,
        messages=[{"role": "user", "content": instruction}],
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()


async def optimize(rounds: int = 2) -> dict:
    print("\n### Baseline ###")
    best_prompt = config.SYSTEM_PROMPT_V1
    best_scores, best_agg = await evaluate(system_prompt=best_prompt)
    print_scorecard(best_scores, best_agg)
    baseline_agg = best_agg

    history = [{"round": 0, "mean_composite": best_agg["mean_composite"], "mean_f1": best_agg["mean_f1"]}]

    for r in range(1, rounds + 1):
        print(f"\n### Optimization round {r}: proposing a new prompt ###")
        candidate_prompt = await propose_new_prompt(best_prompt, best_scores)
        cand_scores, cand_agg = await evaluate(system_prompt=candidate_prompt)
        print_scorecard(cand_scores, cand_agg)

        improved = cand_agg["mean_composite"] > best_agg["mean_composite"]
        history.append({
            "round": r,
            "mean_composite": cand_agg["mean_composite"],
            "mean_f1": cand_agg["mean_f1"],
            "kept": improved,
        })
        if improved:
            print(f"round {r}: improved {best_agg['mean_composite']} -> {cand_agg['mean_composite']}, keeping.")
            best_prompt, best_scores, best_agg = candidate_prompt, cand_scores, cand_agg
        else:
            print(f"round {r}: no improvement ({cand_agg['mean_composite']} <= {best_agg['mean_composite']}), discarding.")

    result = {
        "baseline": {"mean_f1": baseline_agg["mean_f1"], "mean_composite": baseline_agg["mean_composite"]},
        "optimized": {"mean_f1": best_agg["mean_f1"], "mean_composite": best_agg["mean_composite"]},
        "history": history,
        "winning_prompt": best_prompt,
    }
    _RESULT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    print("\n" + "#" * 50)
    print("BEFORE -> AFTER")
    print(f"  mean F1:        {baseline_agg['mean_f1']}  ->  {best_agg['mean_f1']}")
    print(f"  mean composite: {baseline_agg['mean_composite']}  ->  {best_agg['mean_composite']}")
    print("#" * 50)
    print(f"\nSaved full result to {_RESULT_PATH}")
    return result


async def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=2)
    args = ap.parse_args()
    await optimize(rounds=args.rounds)


if __name__ == "__main__":
    asyncio.run(_main())
