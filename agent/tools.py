"""
tools.py

Custom in-process tools exposed to the agent via the Claude Agent SDK.

The agent gets two tools:
  - search_schemes: find candidate schemes by keyword/category (deliberately
    returns only summaries, so the agent must dig deeper to judge eligibility).
  - get_scheme_details: full criteria + documents for one scheme.

There is intentionally NO "check_eligibility" oracle tool. Deciding eligibility
is the reasoning work we want to measure, so the agent must do it itself.
"""

from __future__ import annotations
import json
import pathlib
from typing import Any

from claude_agent_sdk import tool, create_sdk_mcp_server

_DATA_PATH = pathlib.Path(__file__).parent.parent / "data" / "schemes.json"


def load_schemes() -> list[dict[str, Any]]:
    return json.loads(_DATA_PATH.read_text())["schemes"]


_SCHEMES = load_schemes()
_BY_ID = {s["id"]: s for s in _SCHEMES}


@tool(
    "search_schemes",
    "Search for government schemes by free-text keyword and/or category. "
    "Returns a short list of matching schemes with id, name, category and a one-line summary. "
    "Use an empty keyword to browse everything. Does NOT return full eligibility rules.",
    {"keyword": str, "category": str},
)
async def search_schemes(args: dict[str, Any]) -> dict[str, Any]:
    keyword = (args.get("keyword") or "").strip().lower()
    category = (args.get("category") or "").strip().lower()

    results = []
    for s in _SCHEMES:
        haystack = f"{s['name']} {s['category']} {s['summary']}".lower()
        if keyword and keyword not in haystack:
            continue
        if category and category not in s["category"].lower():
            continue
        results.append(
            {"id": s["id"], "name": s["name"], "category": s["category"], "summary": s["summary"]}
        )

    payload = {"count": len(results), "schemes": results}
    return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}]}


@tool(
    "get_scheme_details",
    "Get the full details of one scheme by its id, including the exact eligibility "
    "criteria, benefit, required documents and application URL.",
    {"scheme_id": str},
)
async def get_scheme_details(args: dict[str, Any]) -> dict[str, Any]:
    scheme_id = (args.get("scheme_id") or "").strip()
    scheme = _BY_ID.get(scheme_id)
    if scheme is None:
        msg = {"error": f"No scheme with id '{scheme_id}'. Use search_schemes to find valid ids."}
        return {"content": [{"type": "text", "text": json.dumps(msg)}]}
    return {"content": [{"type": "text", "text": json.dumps(scheme, ensure_ascii=False)}]}


def build_scheme_server():
    """Create the in-process MCP server that hosts the two tools."""
    return create_sdk_mcp_server(
        name="schemes",
        version="1.0.0",
        tools=[search_schemes, get_scheme_details],
    )


# Tool names as the agent must reference them: mcp__<server>__<tool>
ALLOWED_TOOLS = [
    "mcp__schemes__search_schemes",
    "mcp__schemes__get_scheme_details",
]
