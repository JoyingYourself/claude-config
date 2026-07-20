#!/usr/bin/env bash
# brain-fewshot-bridge.sh — Few-shot learning bridge for claudectl brain
#
# Reads past decisions from decisions.jsonl, finds similar examples,
# injects them into the prompt, and calls Ollama API directly.
#
# This bypasses claudectl --brain-query because upstream v0.64.0's
# internal decision store doesn't read from decisions.jsonl yet.
# When upstream adds hook_events → decisions reconciliation, we can
# switch back to the native path.
#
# Input (via stdin or args):
#   JSON hook payload: {"tool_name":"Bash","tool_input":{"command":"..."},...}
#
# Output (stdout):
#   JSON decision: {"action":"approve|deny|ask","confidence":0.0-1.0,
#                   "reasoning":"...","source":"brain","few_shot_count":N,
#                   "below_threshold":false}
#
# Always exits 0. Any error falls through silently.

set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434/v1/chat/completions}"
MODEL="${BRAIN_MODEL:-qwen3:14b}"
TIMEOUT_SEC="${BRAIN_TIMEOUT:-30}"
MAX_EXAMPLES="${MAX_FEWSHOT_EXAMPLES:-8}"
DECISIONS_LOG="$HOME/.claudectl/brain/decisions.jsonl"
ADVISORY_PROMPT="$HOME/.claudectl/brain/prompts/advisory.md"
GATE_MODE_FILE="$HOME/.claudectl/brain/gate-mode"

# ── Gate mode check ─────────────────────────────────────────────────
GATE_MODE="on"
if [ -f "$GATE_MODE_FILE" ]; then
    GATE_MODE=$(tr -d '[:space:]' < "$GATE_MODE_FILE" 2>/dev/null || echo "on")
fi
if [ "$GATE_MODE" = "off" ]; then
    exit 0
fi

# ── Read input ──────────────────────────────────────────────────────
INPUT=$(cat)
if [ -z "$INPUT" ]; then
    exit 0
fi

# ── Extract fields ──────────────────────────────────────────────────
if command -v jq &>/dev/null; then
    TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty')
    case "$TOOL_NAME" in
        Bash) TOOL_INPUT=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty') ;;
        Write|Edit|NotebookEdit) TOOL_INPUT=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty') ;;
        *) TOOL_INPUT=$(printf '%s' "$INPUT" | jq -c '.tool_input // {}' | head -c 200) ;;
    esac
    SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"')
else
    TOOL_NAME=$(echo "$INPUT" | sed -n 's/.*"tool_name" *: *"\([^"]*\)".*/\1/p')
    TOOL_INPUT=""
    SESSION_ID="unknown"
fi

if [ -z "$TOOL_NAME" ]; then
    exit 0
fi

PROJECT=$(basename "${PWD:-unknown}")

# ── Build few-shot examples from decisions.jsonl ────────────────────
build_fewshot_examples() {
    if [ ! -f "$DECISIONS_LOG" ] || [ ! -s "$DECISIONS_LOG" ]; then
        echo ""
        return
    fi

    if ! command -v jq &>/dev/null; then
        echo ""
        return
    fi

    # Strategy: prefer same (tool, project), then same tool, then anything.
    # Score by recency and similarity. Take top MAX_EXAMPLES.
    local examples
    examples=$(jq -s --arg tool "$TOOL_NAME" --arg project "$PROJECT" --arg cmd "$TOOL_INPUT" --argjson max "$MAX_EXAMPLES" '
        # Score each decision for relevance
        map(. + {
            _score: (
                (if .tool == $tool then 30 else 0 end) +
                (if .project == $project then 20 else 0 end) +
                (if (.command | length > 0) and ($cmd | length > 0) and
                    ((.command | split(" ")[0]) == ($cmd | split(" ")[0])) then 10 else 0 end)
            )
        }) |
        sort_by(-._score, -.timestamp) |
        .[0:$max] |
        map({
            tool: .tool,
            command: .command,
            action: .action,
            confidence: .confidence,
            reasoning: (.reasoning | if length > 120 then .[0:120] + "..." else . end),
            accepted: .accepted
        })
    ' "$DECISIONS_LOG" 2>/dev/null || echo "[]")

    if [ "$examples" = "[]" ] || [ -z "$examples" ]; then
        echo ""
        return
    fi

    local count
    count=$(echo "$examples" | jq 'length' 2>/dev/null || echo 0)

    # Format examples as text for the prompt
    echo "$examples" | jq -r '
        "## Past Decisions (learn from these)\n",
        (to_entries[] | "\(.key + 1). [\(.value.tool)] `\(.value.command)` → **\(.value.action)** (confidence: \(.value.confidence))\n   Reason: \(.value.reasoning)\n   Accepted: \(.value.accepted)\n"),
        "\n---\n"
    ' 2>/dev/null || echo ""

    # Return the count for metadata
    echo "FEWSHOT_COUNT:$count" >&2
}

FEWSHOT_TEXT=$(build_fewshot_examples 2>/tmp/fewshot-meta.txt)
FEWSHOT_COUNT=0
if [ -f /tmp/fewshot-meta.txt ]; then
    FEWSHOT_COUNT=$(grep "FEWSHOT_COUNT:" /tmp/fewshot-meta.txt 2>/dev/null | sed 's/FEWSHOT_COUNT://' || echo 0)
    rm -f /tmp/fewshot-meta.txt
fi

# ── Build system prompt ─────────────────────────────────────────────
SYSTEM_PROMPT="You are a session supervisor for Claude Code (an AI coding assistant). You evaluate tool calls and decide: approve, deny, or ask (require user confirmation).

## Decision Rules

### Immediately Approve
- Read-only operations: ls, cat, head, tail, grep, find, git status, git diff, git log
- Project test commands: cargo test, pytest, npm test, go test
- Project build commands: cargo build, npm run build, make
- Package management within project: pip install, npm install, cargo add
- Safe shell builtins: echo, pwd, cd, printf, test, true, false
- Help/info: git --help, man, which, type

### Immediately Deny
- Recursive force delete: rm -rf /, rm -rf ~, sudo rm
- Force push to main/master: git push --force origin main, git push --force origin master
- Pipe to shell: curl ... | sh, curl ... | bash, wget ... | bash
- Privilege escalation: sudo, chmod 777
- Database destruction: DROP TABLE, DROP DATABASE
- Container force delete: docker rm -f, docker system prune -af

### Ask User
- Push to remote (non-force, non-main)
- Write/Edit config files (config/, .env, settings.json)
- Delete non-empty directories
- Network requests: curl, wget (non-pipe)
- First-time tool/command types

## Context Awareness
- Session fixing errors → lean approve for fixes and tests
- High cost with no output → suggest terminate
- Multiple sessions editing same file → detect conflict
- Same command repeated 5+ times in 10 minutes → possible loop

## Output Format
Return ONLY valid JSON, no other text:
{
  \"action\": \"approve|deny|ask\",
  \"confidence\": 0.0-1.0,
  \"reasoning\": \"Brief reasoning in English\"
}"

# If advisory.md exists, use it as the primary system prompt
if [ -f "$ADVISORY_PROMPT" ]; then
    SYSTEM_PROMPT=$(cat "$ADVISORY_PROMPT")
fi

# Append few-shot examples if available
if [ -n "$FEWSHOT_TEXT" ]; then
    SYSTEM_PROMPT="$SYSTEM_PROMPT

---

$FEWSHOT_TEXT"
fi

# ── Build user message ──────────────────────────────────────────────
USER_MSG="Current Tool Call:
- Tool: $TOOL_NAME
- Input: $TOOL_INPUT
- Project: $PROJECT
- Session: $SESSION_ID

Evaluate this tool call and respond with JSON."

# ── Call Ollama API ─────────────────────────────────────────────────
call_ollama() {
    local system_prompt="$1"
    local user_msg="$2"

    # Escape for JSON
    local sys_escaped user_escaped
    if command -v jq &>/dev/null; then
        sys_escaped=$(jq -n --arg s "$system_prompt" '$s')
        user_escaped=$(jq -n --arg s "$user_msg" '$s')
    else
        # Fallback: basic escaping
        sys_escaped="\"$(echo "$system_prompt" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\n' ' ')\""
        user_escaped="\"$(echo "$user_msg" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\n' ' ')\""
    fi

    local payload
    payload=$(cat <<EOF
{
  "model": "$MODEL",
  "messages": [
    {"role": "system", "content": $sys_escaped},
    {"role": "user", "content": $user_escaped}
  ],
  "temperature": 0.1,
  "max_tokens": 300,
  "stream": false,
  "reasoning_effort": "none"
}
EOF
)

    # Call with timeout
    if command -v timeout &>/dev/null; then
        timeout "$TIMEOUT_SEC" curl -s "$OLLAMA_URL" \
            -H "Content-Type: application/json" \
            -d "$payload" 2>/dev/null || echo '{"error":"timeout_or_failure"}'
    else
        # macOS doesn't have timeout; use perl fallback or just curl
        curl -s --max-time "$TIMEOUT_SEC" "$OLLAMA_URL" \
            -H "Content-Type: application/json" \
            -d "$payload" 2>/dev/null || echo '{"error":"timeout_or_failure"}'
    fi
}

RESPONSE=$(call_ollama "$SYSTEM_PROMPT" "$USER_MSG")

# ── Parse response ──────────────────────────────────────────────────
if [ -z "$RESPONSE" ]; then
    exit 0  # API unavailable → fall through
fi

# Check for error
if echo "$RESPONSE" | grep -q '"error"' 2>/dev/null; then
    exit 0
fi

# Extract the assistant's content
if command -v jq &>/dev/null; then
    CONTENT=$(printf '%s' "$RESPONSE" | jq -r '.choices[0].message.content // empty' 2>/dev/null)
else
    CONTENT=$(echo "$RESPONSE" | sed -n 's/.*"content" *: *"\([^"]*\)".*/\1/p')
fi

if [ -z "$CONTENT" ]; then
    exit 0
fi

# Try to parse the content as JSON directly.
# The model might wrap in markdown code blocks — strip those first.
CONTENT_CLEAN=$(echo "$CONTENT" | sed -n '/```json/,/```/p' | grep -v '```' | tr -d '\n')
if [ -z "$CONTENT_CLEAN" ]; then
    CONTENT_CLEAN=$(echo "$CONTENT" | sed -n '/```/,/```/p' | grep -v '```' | tr -d '\n')
fi
if [ -z "$CONTENT_CLEAN" ]; then
    CONTENT_CLEAN="$CONTENT"
fi

# Parse the decision JSON from the content
if command -v jq &>/dev/null; then
    ACTION=$(echo "$CONTENT_CLEAN" | jq -r '.action // empty' 2>/dev/null)
    CONFIDENCE=$(echo "$CONTENT_CLEAN" | jq -r '.confidence // 0' 2>/dev/null)
    REASONING=$(echo "$CONTENT_CLEAN" | jq -r '.reasoning // empty' 2>/dev/null)
else
    ACTION=$(echo "$CONTENT_CLEAN" | sed -n 's/.*"action" *: *"\([^"]*\)".*/\1/p')
    CONFIDENCE=$(echo "$CONTENT_CLEAN" | sed -n 's/.*"confidence" *: *\([0-9.]*\).*/\1/p')
    REASONING=$(echo "$CONTENT_CLEAN" | sed -n 's/.*"reasoning" *: *"\([^"]*\)".*/\1/p')
fi

# Validate action
case "$ACTION" in
    approve|deny|ask) ;;
    *) exit 0 ;;  # Unknown action → fall through
esac

# ── Determine below_threshold ───────────────────────────────────────
BELOW="false"
if command -v jq &>/dev/null; then
    CONF_NUM=$(printf '%s' "$CONFIDENCE" | jq -r '. as $n | if type=="number" then $n else 0 end' 2>/dev/null || echo 0)
else
    CONF_NUM="$CONFIDENCE"
fi
THRESHOLD=0.65
if [ "$(echo "$CONF_NUM < $THRESHOLD" | bc -l 2>/dev/null || echo 0)" = "1" ]; then
    BELOW="true"
fi

# ── Output decision ─────────────────────────────────────────────────
if command -v jq &>/dev/null; then
    jq -n \
        --arg action "$ACTION" \
        --argjson confidence "$CONFIDENCE" \
        --arg reasoning "$REASONING" \
        --argjson few_shot_count "$FEWSHOT_COUNT" \
        --argjson below_threshold "$BELOW" \
        --arg source "brain" \
        '{
            action: $action,
            confidence: $confidence,
            reasoning: $reasoning,
            source: $source,
            few_shot_count: $few_shot_count,
            below_threshold: $below_threshold
        }'
else
    printf '{"action":"%s","confidence":%s,"reasoning":"%s","source":"brain","few_shot_count":%s,"below_threshold":%s}\n' \
        "$ACTION" "$CONFIDENCE" "$REASONING" "$FEWSHOT_COUNT" "$BELOW"
fi
