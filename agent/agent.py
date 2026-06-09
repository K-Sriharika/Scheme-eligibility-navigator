"""
agent.py

Runs a single citizen profile through the Claude Agent SDK and returns both the
agent's structured answer and the run metrics (tool calls, turns, cost) that the
eval harness needs.

This is built on the Claude Agent SDK (claude-agent-sdk), not raw Anthropic API
calls. The SDK provides the agent loop, tool-calling and structured output.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    ToolUseBlock,
    TextBlock,
)

from .tools import build_scheme_server, ALLOWED_TOOLS
from . import config


@dataclass
class AgentRun:
    """Everything the eval harness needs from one agent run."""
    eligible_ids: list[str]
    answer: dict[str, Any]
    tool_calls: int = 0
    num_turns: int = 0
    cost_usd: float = 0.0
    raw_text: str = ""
    error: str | None = None
    tool_call_names: list[str] = field(default_factory=list)


def _extract_answer(structured_output: Any, raw_text: str) -> dict[str, Any]:
    """Prefer the SDK's structured_output; fall back to parsing JSON from text."""
    if isinstance(structured_output, dict) and "eligible_schemes" in structured_output:
        return structured_output
    # Fallback: try to find a JSON object in the final text.
    text = raw_text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, dict) and "eligible_schemes" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass
    return {"eligible_schemes": []}


async def run_agent(profile_text: str, system_prompt: str | None = None) -> AgentRun:
    """Run one profile. system_prompt defaults to the v1 prompt in config."""
    options = ClaudeAgentOptions(
        mcp_servers={"schemes": build_scheme_server()},
        allowed_tools=ALLOWED_TOOLS,
        system_prompt=system_prompt or config.SYSTEM_PROMPT_V1,
        model=config.AGENT_MODEL,
        max_turns=config.MAX_TURNS,
        output_format={"type": "json_schema", "schema": config.OUTPUT_SCHEMA},
        permission_mode="bypassPermissions",  # tools are read-only and local
    )

    run = AgentRun(eligible_ids=[], answer={"eligible_schemes": []})

    try:
        async for message in query(prompt=profile_text, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, ToolUseBlock):
                        run.tool_calls += 1
                        run.tool_call_names.append(block.name)
                    elif isinstance(block, TextBlock):
                        run.raw_text = block.text
            elif isinstance(message, ResultMessage):
                run.num_turns = message.num_turns
                run.cost_usd = message.total_cost_usd or 0.0
                run.answer = _extract_answer(message.structured_output, run.raw_text)
    except Exception as exc:  # keep one bad run from killing a whole eval sweep
        run.error = f"{type(exc).__name__}: {exc}"

    run.eligible_ids = sorted(
        s.get("scheme_id", "") for s in run.answer.get("eligible_schemes", []) if s.get("scheme_id")
    )
    return run
