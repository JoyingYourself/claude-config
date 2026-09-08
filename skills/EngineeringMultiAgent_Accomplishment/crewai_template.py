"""
CrewAI Multi-Agent Task Execution Template
===========================================
Generated dynamically by EngineeringMultiAgent_Accomplishment Skill.
DO NOT edit manually — regenerated on each Skill invocation.

Architecture:
  - Agents have NO tools (pure LLM reasoning)
  - MCP tools are bridged via Claude Code Skill layer
  - Agent outputs structured <tool_request> blocks → Skill intercepts → injects results
"""

import os
import sys
import json
import uuid
import time
import traceback
from pathlib import Path
from datetime import datetime
from typing import Optional

# ── CrewAI imports ──────────────────────────────────────────────
from crewai import Agent, Task, Crew, Process, LLM
from crewai.flow import Flow, start, listen


# ═══════════════════════════════════════════════════════════════
# CONFIGURATION (injected by Skill at generation time)
# ═══════════════════════════════════════════════════════════════

RUN_ID = "{{RUN_ID}}"
OUTPUT_DIR = Path("{{OUTPUT_DIR}}")
CHECKPOINT_DIR = OUTPUT_DIR / "checkpoints"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

# Agent definitions — injected from Skill Step 1 decomposition
AGENT_DEFS = {{AGENT_DEFS}}       # list[dict] with role/goal/backstory
TASK_DEFS = {{TASK_DEFS}}         # list[dict] with description/expected_output/agent_idx/context_idxs/critical
PROCESS_TYPE = "{{PROCESS}}"      # "sequential" or "hierarchical"
USE_MEMORY = {{USE_MEMORY}}       # bool
MANAGER_LLM_MODEL = "{{MANAGER_LLM_MODEL}}"  # only for hierarchical; default "deepseek-chat"
MAX_RETRIES = 5
TASK_TIMEOUT_SEC = 1200  # 20 minutes
CREW_TIMEOUT_SEC = 3600   # 60 minutes

# LLM Configuration
# API key resolution: DEEPSEEK_API_KEY (set by Skill) → OPENAI_API_KEY (CrewAI fallback)
_API_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
if not _API_KEY:
    raise RuntimeError("DEEPSEEK_API_KEY or OPENAI_API_KEY must be set")

LLM_CONFIG = {
    "model": "deepseek-chat",           # DeepSeek V3/V4 (OpenAI-compatible endpoint)
    "base_url": "https://api.deepseek.com",
    "api_key": _API_KEY,
    "temperature": 0.1,
    "max_tokens": 4096,
}
# Note: CrewAI uses OpenAI SDK → must use DeepSeek's OpenAI-compatible endpoint
# (https://api.deepseek.com), NOT the Anthropic-compatible endpoint
# (https://api.deepseek.com/anthropic). Model name is "deepseek-chat", not
# "deepseek-v4-flash[1m]" (which is only for Anthropic protocol).


# ═══════════════════════════════════════════════════════════════
# UTILITY: Structured tool-request format for Skill bridge
# ═══════════════════════════════════════════════════════════════

TOOL_REQUEST_MARKER = "<!--TOOL_REQUEST-->"
TOOL_RESULT_MARKER  = "<!--TOOL_RESULT-->"

def format_tool_request(tool_name: str, params: dict, reason: str = "") -> str:
    """Produce a structured tool-request block that the Skill layer can parse."""
    payload = {
        "tool": tool_name,
        "params": params,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
    }
    return f"{TOOL_REQUEST_MARKER}\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n{TOOL_REQUEST_MARKER}"

def format_tool_result(tool_name: str, result: str, success: bool = True) -> str:
    """Format an injected tool result for the next Task's context."""
    status = "✅ 成功" if success else "❌ 失败"
    return f"""
{TOOL_RESULT_MARKER}
## 工具执行结果: {tool_name} {status}

```
{result}
```
{TOOL_RESULT_MARKER}
"""


# ═══════════════════════════════════════════════════════════════
# CHECKPOINT
# ═══════════════════════════════════════════════════════════════

def save_checkpoint(task_index: int, task_outputs: list, error: Optional[str] = None):
    """Save execution state for potential resume."""
    checkpoint = {
        "run_id": RUN_ID,
        "task_index": task_index,
        "completed_tasks": [
            {"description": t.get("description", ""), "output": t.get("output", ""),
             "agent": t.get("agent", ""), "timestamp": t.get("timestamp", "")}
            for t in task_outputs
        ],
        "error": error,
        "timestamp": datetime.now().isoformat(),
    }
    cp_file = CHECKPOINT_DIR / f"checkpoint_{RUN_ID}.json"
    cp_file.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2))
    return str(cp_file)


def load_checkpoint() -> Optional[dict]:
    """Load the latest checkpoint for this run."""
    cp_file = CHECKPOINT_DIR / f"checkpoint_{RUN_ID}.json"
    if cp_file.exists():
        return json.loads(cp_file.read_text())
    return None


# ═══════════════════════════════════════════════════════════════
# MAIN: Build and execute Crew
# ═══════════════════════════════════════════════════════════════

def build_crew(tool_results: Optional[dict[str, str]] = None):
    """
    Build the CrewAI Crew from definitions.
    tool_results: dict mapping task_description → injected tool result (from bridge)
    """
    # ── Resolve LLM ──
    if not LLM_CONFIG["api_key"]:
        raise RuntimeError(
            "API key not set. "
            "Set via: export DEEPSEEK_API_KEY=sk-...  or  export OPENAI_API_KEY=sk-..."
        )
    main_llm = LLM(**LLM_CONFIG)

    # ── Build Agents ──
    agents = []
    for ad in AGENT_DEFS:
        agent = Agent(
            role=ad["role"],
            goal=ad["goal"],
            backstory=ad.get("backstory", ""),
            tools=[],                        # No tools — bridge mode
            llm=main_llm,
            verbose=True,
            allow_delegation=False,
            max_iter=15,
        )
        agents.append(agent)

    # ── Build Tasks ──
    manager_llm = None
    if PROCESS_TYPE == "hierarchical":
        manager_llm = LLM(model=MANAGER_LLM_MODEL, **{k: v for k, v in LLM_CONFIG.items() if k != "model"})

    tasks = []
    for i, td in enumerate(TASK_DEFS):
        agent = agents[td["agent_idx"]]

        # Build description: inject tool results if this task depends on previous MCP calls
        description = td["description"]
        injected_context = ""
        for ctx_idx in td.get("context_idxs", []):
            if ctx_idx < len(TASK_DEFS):
                ctx_desc = TASK_DEFS[ctx_idx].get("description", "")
                if tool_results and ctx_desc in tool_results:
                    injected_context += tool_results[ctx_desc] + "\n"

        if injected_context:
            description = description + "\n\n--- 上游工具执行结果 ---\n" + injected_context

        task = Task(
            description=description,
            expected_output=td.get("expected_output", "完成任务并汇报结果"),
            agent=agent,
            context=[tasks[j] for j in td.get("context_idxs", []) if j < len(tasks)],
        )
        tasks.append(task)

    # ── Build Crew ──
    process = Process.sequential if PROCESS_TYPE == "sequential" else Process.hierarchical
    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=process,
        memory=USE_MEMORY,
        verbose=True,
        max_rpm=60,
        manager_llm=manager_llm,
        output_log_file=str(OUTPUT_DIR / f"crew_log_{RUN_ID}.txt"),
    )

    return crew, agents, tasks


def execute_with_retry(crew: Crew, tasks: list, run_id: str) -> dict:
    """
    Execute the Crew with retry logic.
    Returns: {success, outputs, failed_task_idx, error, checkpoint_path}
    """
    task_outputs = []
    checkpoint = load_checkpoint()
    start_idx = checkpoint["task_index"] if checkpoint else 0

    for i in range(start_idx, len(tasks)):
        task = tasks[i]
        td = TASK_DEFS[i]
        is_critical = td.get("critical", True)
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"\n{'='*60}")
                print(f"  Task [{i+1}/{len(tasks)}] — Attempt {attempt}/{MAX_RETRIES}")
                print(f"  Agent: {AGENT_DEFS[td['agent_idx']]['role']}")
                print(f"  Critical: {is_critical}")
                print(f"{'='*60}")

                # Execute single task via Crew (re-build crew with only remaining tasks)
                remaining_tasks = tasks[i:]
                sub_crew = Crew(
                    agents=crew.agents,
                    tasks=remaining_tasks,
                    process=crew.process,
                    verbose=True,
                    max_rpm=60,
                )
                result = sub_crew.kickoff()

                task_outputs.append({
                    "description": td["description"],
                    "output": str(result),
                    "agent": AGENT_DEFS[td["agent_idx"]]["role"],
                    "timestamp": datetime.now().isoformat(),
                    "attempts": attempt,
                })
                last_error = None
                break  # Success — exit retry loop

            except Exception as e:
                last_error = str(e)
                print(f"\n  ⚠️ Task [{i+1}] failed (attempt {attempt}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES:
                    print(f"  ↩️  Retrying...")
                    time.sleep(2 ** attempt)  # Exponential backoff
                traceback.print_exc()

        # After all retries exhausted
        if last_error:
            cp_path = save_checkpoint(i, task_outputs, last_error)
            if is_critical:
                return {
                    "success": False,
                    "outputs": task_outputs,
                    "failed_task_idx": i,
                    "error": f"Critical task failed after {MAX_RETRIES} retries. Last error: {last_error}",
                    "checkpoint_path": cp_path,
                }
            else:
                print(f"\n  ⚠️ Non-critical task [{i+1}] failed. Skipping and continuing.")
                task_outputs.append({
                    "description": td["description"],
                    "output": f"[SKIPPED — non-critical task failed: {last_error}]",
                    "agent": AGENT_DEFS[td["agent_idx"]]["role"],
                    "timestamp": datetime.now().isoformat(),
                    "attempts": MAX_RETRIES,
                    "skipped": True,
                })
                save_checkpoint(i + 1, task_outputs)

        # Save checkpoint after each successful task
        save_checkpoint(i + 1, task_outputs)

    return {
        "success": True,
        "outputs": task_outputs,
        "failed_task_idx": -1,
        "error": None,
        "checkpoint_path": None,
    }


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def main(tool_results: Optional[dict] = None) -> dict:
    """
    Main entry point. tool_results is a dict of task_description→injected_result
    supplied by the Skill bridge layer between retries.
    """
    print(f"\n🚀 CrewAI Multi-Agent Task Execution")
    print(f"   Run ID: {RUN_ID}")
    print(f"   Output: {OUTPUT_DIR}")
    print(f"   Process: {PROCESS_TYPE}")
    print(f"   Memory: {USE_MEMORY}")
    print(f"   Agents: {len(AGENT_DEFS)}")
    print(f"   Tasks:  {len(TASK_DEFS)}")
    print(f"   LLM:    {LLM_CONFIG['model']} @ {LLM_CONFIG['base_url']}")

    crew, agents, tasks = build_crew(tool_results)
    result = execute_with_retry(crew, tasks, RUN_ID)

    # Write final output
    output_file = OUTPUT_DIR / f"result_{RUN_ID}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))

    if result["success"]:
        print(f"\n✅ All tasks completed ({len(result['outputs'])}/{len(tasks)})")
    else:
        print(f"\n❌ Execution failed at task {result['failed_task_idx']+1}")
        print(f"   Error: {result['error']}")
        print(f"   Checkpoint: {result['checkpoint_path']}")
        print(f"   {len(result['outputs'])}/{len(tasks)} tasks completed before failure")

    print(f"   Output: {output_file}")
    return result


if __name__ == "__main__":
    # Allow tool_results to be passed as JSON file path or env var
    tool_results = None
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            tool_results = json.load(f)
    main(tool_results)
