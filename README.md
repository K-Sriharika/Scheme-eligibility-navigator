# Scheme Eligibility Navigator — an agent, an eval, and an optimizer

A working agent built on the **Claude Agent SDK** that reads a citizen's
plain-language description and works out which Indian government schemes they
qualify for, why, and how to apply. Shipped with a systematic eval harness and a
self-improving optimizer loop.

> Built on `claude-agent-sdk` (the framework behind Claude Code), not raw API
> calls. The SDK provides the agent loop, in-process tools, and structured output.

## Why this shape

The build is organised around three things that should sound familiar:

| Pillar | What it is here |
| --- | --- |
| A working agent | A scheme-eligibility agent: tool use, multi-step reasoning, structured output. |
| Measurable value | An eval harness that scores correctness objectively (precision / recall / F1), not by feel. |
| An improvement loop | An optimizer that measures, finds failures, changes one knob, and keeps the change only if the numbers improved. |

There is one more deliberate choice: the agent's domain knowledge lives in an
**editable rulebook** (`data/schemes.json`), so a non-developer can add a scheme
or change a threshold and it takes effect on the next run — no code change, no
developer queue. See `data/rulebook_guide.md`.

## How the agent works

Input: a free-text profile, e.g. *"I'm a 28-year-old woman running a small
tailoring business in Pune, earning about 3 lakh a year."*

The agent then:
1. Reads the profile and infers the person's attributes.
2. Calls `search_schemes` to find candidates.
3. Calls `get_scheme_details` to read each candidate's exact criteria.
4. Reasons, scheme by scheme, about whether the person meets every criterion.
5. Returns a structured list of eligible schemes with reasons, missing documents,
   and application links.

It is given scheme *information* tools but no eligibility *oracle* — judging
eligibility is the reasoning we want to measure.

## How the eval works

`evals/test_cases.json` holds profiles written as free text, each paired with a
hidden set of canonical attributes. The ground-truth eligible set is computed by
a deterministic rule engine (`agent/rule_engine.py`) over those attributes. The
agent only ever sees the text, so it has to recover the attributes and apply the
rules itself.

Each run is scored on:
- **precision / recall / F1** over the eligible-scheme set (core correctness),
- **hallucinations** — scheme ids that don't exist (hard-penalised),
- **efficiency** — tool calls, turns, and cost, read straight off the SDK result,
- a weighted **composite** that the optimizer targets.

## How the optimizer works

`optimizer/optimize.py` runs the eval, summarises the worst cases, asks Claude to
rewrite the agent's system prompt to fix those specific failure patterns, re-runs
the eval, and keeps the new prompt only if the composite score went up. It repeats
for a few rounds and prints a before/after table.

## Results

<!-- Fill in after running `python -m optimizer.optimize --rounds 2` -->

| Metric | Baseline | Optimized |
| --- | --- | --- |
| mean F1 | _tbd_ | _tbd_ |
| mean composite | _tbd_ | _tbd_ |
| hallucinations | _tbd_ | _tbd_ |

## Sample output

![Scheme demo](Scheme%20Demo.png)

## Run it

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...      # or run via Claude Code if you have Pro/Max

python run_demo.py                       # one profile, end to end (record this)
python -m evals.run_eval                 # full scorecard
python -m evals.run_eval --limit 3       # quick smoke test (cheap)
python -m optimizer.optimize --rounds 2  # baseline -> optimized, before/after
```

Everything runs on a small, fast model (Haiku) by default to keep cost negligible.

## Project layout

```
scheme-navigator/
  agent/
    tools.py        # search_schemes, get_scheme_details (in-process SDK tools)
    agent.py        # runs one profile, returns answer + metrics
    config.py       # models, output schema, the tunable system prompt
    rule_engine.py  # deterministic answer key (not exposed to the agent)
  evals/
    test_cases.json # free-text profiles + hidden canonical attributes
    scorer.py       # precision/recall/F1, hallucination, efficiency
    run_eval.py     # runs the agent over all cases, prints scorecard
  optimizer/
    optimize.py     # measure -> fix prompt -> measure -> keep if better
  data/
    schemes.json    # the editable rulebook
    rulebook_guide.md
  run_demo.py
```

## Note on data

The eligibility thresholds in `data/schemes.json` are **illustrative and
simplified** for this demonstration. They are not authoritative benefits advice
and should be verified against official sources (myscheme.gov.in and the relevant
ministry) before any real use. The point of this project is the agent + eval +
optimizer system, not the specific numbers.
