#!/usr/bin/env bash
# brain-session-summarizer.sh — Stop hook: 结构化提取会话摘要
#
# 当 Claude Code 会话结束时，扫描最新的 session transcript，
# 提取项目、文件操作、命令执行、耗时等信息，
# 写入 ~/.claudectl/brain/session-summaries/ 供跨会话记忆使用。
#
# 设计原则:
#   - Fail-open: 任何错误 exit 0，不阻塞 Claude Code
#   - 幂等: 同一 session_id 只写一次
#   - 轻量: 只读最近一个 transcript，不做全量扫描

set -uo pipefail  # -e removed: hook must never fail-stop the session

SUMMARIES_DIR="$HOME/.claudectl/brain/session-summaries"
TRANSCRIPTS_DIR="$HOME/.claude/projects"
LOG_FILE="/tmp/brain-summarizer.log"

mkdir -p "$SUMMARIES_DIR"

log_msg() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"; }

CWD="${PWD:-$HOME}"

# ── 找最近修改的 transcript（5 分钟内） ──────────────────────────────
LATEST_TRANSCRIPT=""
LATEST_MTIME=0

for proj_dir in "$TRANSCRIPTS_DIR"/*/; do
    [ -d "$proj_dir" ] || continue
    for f in "$proj_dir"/*.jsonl; do
        [ -f "$f" ] || continue
        mtime=$(stat -f '%m' "$f" 2>/dev/null || echo 0)
        age=$(( $(date +%s) - mtime ))
        if [ "$age" -lt 300 ] && [ "$mtime" -gt "$LATEST_MTIME" ]; then
            LATEST_MTIME=$mtime
            LATEST_TRANSCRIPT="$f"
        fi
    done
done

if [ -z "$LATEST_TRANSCRIPT" ]; then
    log_msg "No recent transcript found (last 5 min). CWD=$CWD — skipping."
    exit 0
fi

# ── 提取 session_id + 幂等检查 ───────────────────────────────────────
SESSION_ID=$(head -20 "$LATEST_TRANSCRIPT" | python3 -c "
import json, sys
for line in sys.stdin:
    try:
        d = json.loads(line.strip())
        if 'sessionId' in d:
            print(d['sessionId'])
            break
    except: pass
" 2>/dev/null)

if [ -z "$SESSION_ID" ]; then
    SESSION_ID=$(basename "$LATEST_TRANSCRIPT" .jsonl)
fi

OUTPUT_FILE="$SUMMARIES_DIR/${SESSION_ID}.json"
if [ -f "$OUTPUT_FILE" ]; then
    log_msg "Already summarized session $SESSION_ID — skipping."
    exit 0
fi

# ── Python 解析 transcript ───────────────────────────────────────────
SUMMARIZER_PY=$(cat <<'PYEOF'
import json, sys, os
from collections import Counter
from datetime import datetime

transcript_path = sys.argv[1]
session_id = sys.argv[2]

tool_calls = []      # [(name, input_str)]
user_texts = []      # [text]
first_ts = None
last_ts = None
cwd = None

with open(transcript_path, 'r') as f:
    for line in f:
        try:
            d = json.loads(line.strip())
        except json.JSONDecodeError:
            continue

        # Track timestamps
        ts_str = d.get('timestamp')
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                if first_ts is None or ts < first_ts:
                    first_ts = ts
                if last_ts is None or ts > last_ts:
                    last_ts = ts
            except: pass

        # Track cwd
        if not cwd:
            cwd = d.get('cwd')

        # Track tool calls
        msg = d.get('message', {})
        content = msg.get('content', [])
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get('type') == 'tool_use':
                    inp = item.get('input', {})
                    if isinstance(inp, dict):
                        inp_str = json.dumps(inp, ensure_ascii=False)[:200]
                    else:
                        inp_str = str(inp)[:200]
                    tool_calls.append((item.get('name', 'unknown'), inp_str))

        # Track user messages
        if msg.get('role') == 'user':
            uc = msg.get('content')
            if isinstance(uc, str):
                user_texts.append(uc[:200])
            elif isinstance(uc, list):
                for item in uc:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        user_texts.append(item.get('text', '')[:200])

# Compute stats
tool_counter = Counter(name for name, _ in tool_calls)
total_calls = len(tool_calls)

# Edited files (Write/Edit calls)
edited_files = list(set(inp for name, inp in tool_calls if name in ('Write', 'Edit')))

# Bash commands (first 20)
bash_cmds = [inp for name, inp in tool_calls if name == 'Bash'][:20]

# Duration
duration_sec = 0
duration_human = "unknown"
if first_ts and last_ts:
    delta = last_ts - first_ts
    duration_sec = int(delta.total_seconds())
    if duration_sec > 0:
        h, rem = divmod(duration_sec, 3600)
        m, s = divmod(rem, 60)
        if h > 0:
            duration_human = f"{h}h{m}m{s}s"
        else:
            duration_human = f"{m}m{s}s"

summary = {
    "session_id": session_id,
    "project": os.path.basename(cwd) if cwd else "unknown",
    "cwd": cwd or "unknown",
    "duration": duration_human,
    "duration_sec": duration_sec,
    "first_ts": first_ts.isoformat() if first_ts else None,
    "last_ts": last_ts.isoformat() if last_ts else None,
    "tool_stats": {
        "total": total_calls,
        "by_tool": dict(tool_counter)
    },
    "files_edited": edited_files,
    "recent_commands": bash_cmds,
    "user_message_preview": user_texts[:20],
    "summarized_at": datetime.utcnow().isoformat() + "Z",
    "transcript_file": os.path.basename(transcript_path)
}

print(json.dumps(summary, ensure_ascii=False, indent=2))
PYEOF
)

SUMMARY=$(python3 -c "$SUMMARIZER_PY" "$LATEST_TRANSCRIPT" "$SESSION_ID" 2>/dev/null || echo "")

if [ -z "$SUMMARY" ]; then
    log_msg "Python parsing failed for transcript: $LATEST_TRANSCRIPT"
    exit 0
fi

printf '%s\n' "$SUMMARY" > "$OUTPUT_FILE"

# 提取关键数字用于日志
TOTAL_TOOLS=$(echo "$SUMMARY" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['tool_stats']['total'])")
DUR=$(echo "$SUMMARY" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['duration'])")

log_msg "Session summarized: $SESSION_ID · $TOTAL_TOOLS tool calls · ${DUR} · → $OUTPUT_FILE"
