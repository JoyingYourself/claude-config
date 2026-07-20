#!/usr/bin/env python3
"""TradingAgents-style two-phase decision memory for backtest performance.

Phase A — Store decision: record hypothesis + config + expectation (pending)
Phase B — Settle outcome: N days later, update with actual returns

Format:
    [{date} | {strategy_name} | {sharpe} | pending|settled]
    DECISION: ...
    EXPECTATION: ...
    OUTCOME: ...  (filled in Phase B)

    <!-- ENTRY_END -->

Source: adapted from TauricResearch/TradingAgents Memory Log pattern (MIT License)
"""

import os
from datetime import date as Date
from pathlib import Path

MEMORY_PATH = os.path.expanduser("~/.gil_factors/backtest_memory.md")
_SEPARATOR = "\n\n<!-- ENTRY_END -->\n\n"


def store_decision(
    strategy_name: str,
    config: str,
    expectation: str,
    sharpe: float = 0.0,
    date: str | None = None,
    path: str | None = None,
) -> str:
    """Phase A: Append a [pending] entry to the memory log.

    No LLM call needed — just writes a structured Markdown block.
    Returns the entry tag for later settlement.
    """
    file_path = Path(path or MEMORY_PATH)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    today = date or Date.today().isoformat()
    tag = f"[{today} | {strategy_name} | SR={sharpe:.2f} | pending]"
    entry = f"""{tag}

## DECISION

{config}

## EXPECTATION

{expectation}

## OUTCOME

*(pending — will be settled at next review)*
{_SEPARATOR}"""

    if file_path.exists():
        content = file_path.read_text(encoding="utf-8")
    else:
        content = "# Backtest Decision Memory\n\n> Two-phase memory: decisions recorded first, outcomes settled later.\n\n"

    file_path.write_text(content + entry, encoding="utf-8")
    return tag


def settle_outcome(
    tag: str,
    actual_return_pct: float,
    actual_sharpe: float,
    alpha_vs_benchmark_pct: float,
    reflection: str,
    path: str | None = None,
) -> bool:
    """Phase B: Update a [pending] entry with actual outcomes.

    Finds the entry by tag, replaces [pending] with [settled], and adds:
    - Actual return (vs expected)
    - Actual Sharpe
    - Alpha vs benchmark
    - Reflection on the decision
    """
    file_path = Path(path or MEMORY_PATH)
    if not file_path.exists():
        return False

    content = file_path.read_text(encoding="utf-8")
    if tag not in content:
        return False

    settled_tag = tag.replace("pending]", "settled]")
    outcome_block = f"""## OUTCOME

- **Actual Return**: {actual_return_pct:+.2f}%
- **Actual Sharpe**: {actual_sharpe:.2f}
- **Alpha vs Benchmark**: {alpha_vs_benchmark_pct:+.2f}%

## REFLECTION

{reflection}"""

    # Replace [pending] tag + old OUTCOME block
    old_outcome = "## OUTCOME\n\n*(pending"
    if old_outcome in content:
        # Find the OUTCOME section in this entry
        entry_start = content.index(tag)
        next_sep = content.find(_SEPARATOR, entry_start)
        if next_sep == -1:
            next_sep = len(content)
        entry_text = content[entry_start:next_sep]

        if "## OUTCOME" in entry_text:
            outcome_start = entry_text.index("## OUTCOME")
            old_full = entry_text[outcome_start:]
            new_entry = entry_text[:outcome_start] + outcome_block
            content = content.replace(tag, settled_tag)
            content = content.replace(entry_text, new_entry)

    file_path.write_text(content, encoding="utf-8")
    return True


def list_pending(path: str | None = None) -> list[dict]:
    """List all pending entries that need settlement."""
    file_path = Path(path or MEMORY_PATH)
    if not file_path.exists():
        return []

    content = file_path.read_text(encoding="utf-8")
    entries = content.split(_SEPARATOR)
    pending = []
    for entry in entries:
        if "[pending]" in entry:
            lines = entry.strip().split("\n")
            tag_line = lines[0] if lines else ""
            pending.append({
                "tag": tag_line.strip("- "),
                "raw": entry.strip(),
            })
    return pending


def latest_entries(limit: int = 5, path: str | None = None) -> str:
    """Get recent entries for context injection."""
    file_path = Path(path or MEMORY_PATH)
    if not file_path.exists():
        return "(no prior decisions)"

    content = file_path.read_text(encoding="utf-8")
    entries = content.split(_SEPARATOR)
    recent = [e.strip() for e in entries if e.strip() and not e.strip().startswith("#")][-limit:]
    if not recent:
        return "(no prior decisions)"
    return "\n\n---\n\n".join(recent)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  store <name> <sharpe> <config_summary> <expectation>")
        print("  settle <tag> <return_pct> <sharpe> <alpha_pct> <reflection>")
        print("  pending")
        print("  recent [limit]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "store":
        tag = store_decision(
            strategy_name=sys.argv[2],
            sharpe=float(sys.argv[3]),
            config=sys.argv[4],
            expectation=sys.argv[5],
        )
        print(f"Stored: {tag}")
    elif cmd == "settle":
        ok = settle_outcome(
            tag=sys.argv[2],
            actual_return_pct=float(sys.argv[3]),
            actual_sharpe=float(sys.argv[4]),
            alpha_vs_benchmark_pct=float(sys.argv[5]),
            reflection=sys.argv[6],
        )
        print("Settled." if ok else "Entry not found.")
    elif cmd == "pending":
        for entry in list_pending():
            print(entry["tag"])
    elif cmd == "recent":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        print(latest_entries(limit))
