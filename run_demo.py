"""
run_demo.py

Run a single profile end to end and pretty-print the agent's answer plus the run
metrics. This is the script to screen-record for the demo video.

Usage:
    python run_demo.py
    python run_demo.py "I'm 22, a female student from an OBC family earning 1 lakh a year."
"""

import asyncio
import json
import sys

from agent.agent import run_agent

DEFAULT_PROFILE = (
    "I'm a 28-year-old woman running a small tailoring business in Pune. "
    "I earn roughly 3 lakh a year and want to grow it."
)


async def main():
    profile = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROFILE
    print(f"\nProfile:\n  {profile}\n")
    print("Running agent...\n")
    run = await run_agent(profile)

    if run.error:
        print(f"ERROR: {run.error}")
        return

    print("Eligible schemes:")
    for s in run.answer.get("eligible_schemes", []):
        print(f"  - {s.get('name')} ({s.get('scheme_id')})")
        print(f"      why: {s.get('reason')}")
        if s.get("missing_documents"):
            print(f"      still need: {', '.join(s['missing_documents'])}")
        if s.get("apply_url"):
            print(f"      apply: {s['apply_url']}")

    print(f"\nMetrics: {run.tool_calls} tool calls, {run.num_turns} turns, "
          f"${run.cost_usd:.5f}")
    print(f"Tools called: {run.tool_call_names}\n")


if __name__ == "__main__":
    asyncio.run(main())
