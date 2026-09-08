"""
MCP Bridge — Parses CrewAI Task outputs for tool requests.
Used by the EngineeringMultiAgent_Accomplishment Skill (Claude Code side).

The bridge detects tool requests in two formats:
  1. Structured: <!--TOOL_REQUEST--> JSON <!--TOOL_REQUEST-->
  2. Natural language: Agent describes what tool it needs (fallback)
"""

import json
import re
from typing import Optional


def extract_tool_requests(text: str) -> list[dict]:
    """
    Scan CrewAI Task output for structured or natural-language tool requests.

    Returns: list of {tool, params, reason, format: "structured"|"natural"}
    """
    requests = []

    # ── Format 1: Structured JSON blocks ──
    marker = "<!--TOOL_REQUEST-->"
    pattern = re.compile(rf"{re.escape(marker)}\s*({{.+?}})\s*{re.escape(marker)}", re.DOTALL)
    for match in pattern.finditer(text):
        try:
            payload = json.loads(match.group(1))
            payload["format"] = "structured"
            requests.append(payload)
        except json.JSONDecodeError:
            continue

    # ── Format 2: Natural language fallback ──
    if not requests:
        nl_requests = _parse_natural_language_tool_requests(text)
        requests.extend(nl_requests)

    return requests


def _parse_natural_language_tool_requests(text: str) -> list[dict]:
    """
    Detect natural-language tool needs.
    Looks for patterns like:
      - "我需要调用 run_backtest ..."
      - "需要执行 test_factor ..."
      - "请运行 MCP 工具 ..."
    """
    requests = []
    patterns = [
        r'(?:我需要|需要|请|必须)\s*(?:调用|执行|运行|使用)\s*[`"]?(mcp__\w+__\w+__\w+)[`"]?\s*[，,]\s*(.+?)(?:[。\n]|$)',
        r'(?:call|run|execute|invoke)\s+[`"]?(mcp__\w+__\w+__\w+)[`"]?\s*(?:with|using)?\s*(.+?)(?:[.\n]|$)',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            tool_name = match.group(1)
            description = match.group(2).strip()
            requests.append({
                "tool": tool_name,
                "params": {},
                "reason": description,
                "format": "natural",
            })

    return requests


def has_unresolved_requests(text: str) -> bool:
    """Check if text contains unresolved tool requests."""
    return len(extract_tool_requests(text)) > 0


def format_mcp_result_for_context(tool_name: str, result: str, success: bool = True) -> str:
    """Format an MCP call result for injection into the next Task's context."""
    status = "✅ 成功" if success else "❌ 失败"
    return f"""
<!--TOOL_RESULT-->
## 工具执行结果: {tool_name} {status}

```
{_truncate(result, max_chars=8000)}
```

请基于以上结果继续执行任务。
<!--TOOL_RESULT-->
"""


def _truncate(text: str, max_chars: int = 8000) -> str:
    """Truncate text to max_chars, preserving structure."""
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + f"\n\n... (截断 {len(text) - max_chars} 字符) ...\n\n" + text[-half:]


def summarize_crew_output(crew_output: str, max_length: int = 500) -> str:
    """Extract a summary from CrewAI CrewOutput string."""
    # Try to find the final answer
    markers = ["## Final Answer", "最终答案", "## 总结", "## Summary", "结论：", "结果："]
    for marker in markers:
        idx = crew_output.find(marker)
        if idx >= 0:
            return crew_output[idx:idx + max_length]
    # Fallback: return last portion
    return crew_output[-max_length:] if len(crew_output) > max_length else crew_output
