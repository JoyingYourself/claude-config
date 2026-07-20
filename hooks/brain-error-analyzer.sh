#!/usr/bin/env bash
# brain-error-analyzer.sh — 从 outcomes 发现高频错误模式
#
# 分析已收割的 outcomes，检测：
#   1. 同一命令失败 3+ 次
#   2. 高频工具失败率
#   3. 审批准确率趋势
#
# 将发现写入 ~/.claudectl/brain/proactive-suggestions.json
# (合并到现有建议中) 和 /tmp/brain-error-report.txt
#
# Scheduled via launchd (建议每 30 分钟) 或 Stop hook 触发。

set -euo pipefail

BRAIN_DIR="$HOME/.claudectl/brain"
OUTCOMES_DIR="$BRAIN_DIR/outcomes"
DECISIONS_LOG="$BRAIN_DIR/decisions.jsonl"
SUGGESTIONS_FILE="$BRAIN_DIR/proactive-suggestions.json"
REPORT_FILE="/tmp/brain-error-report.txt"
LOG_FILE="/tmp/brain-error-analyzer.log"

log_msg() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"; }

# ── 检查数据 ──────────────────────────────────────────────────────────
if [ ! -d "$OUTCOMES_DIR" ]; then
    log_msg "No outcomes directory — skipping."
    exit 0
fi

OUTCOME_COUNT=$(ls "$OUTCOMES_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')
if [ "$OUTCOME_COUNT" -lt 3 ]; then
    log_msg "Only $OUTCOME_COUNT resolved outcomes — need ≥3 for analysis. Skipping."
    exit 0
fi

# ── Python 分析 ───────────────────────────────────────────────────────
ANALYZER_PY=$(cat <<'PYEOF'
import json, sys, os, glob
from collections import defaultdict, Counter
from datetime import datetime, timezone

outcomes_dir = sys.argv[1]
decisions_log = sys.argv[2]

# Load all resolved outcomes
outcomes = []
for f in sorted(glob.glob(os.path.join(outcomes_dir, "*.json"))):
    try:
        with open(f) as fh:
            outcomes.append(json.load(fh))
    except: pass

if len(outcomes) < 3:
    print(json.dumps({"errors": [], "summary": "not_enough_data"}))
    sys.exit(0)

# ── Analysis 1: Repeated command failures ──────────────────────────
cmd_failures = defaultdict(list)  # cmd_prefix -> [(exit_code, tool, ts)]
for o in outcomes:
    cmd = o.get('command', '')[:80]
    ec = o.get('exit_code', 0)
    if ec != 0:
        prefix = cmd.split('\n')[0][:60]  # first line, first 60 chars
        cmd_failures[prefix].append({
            'exit_code': ec,
            'tool': o.get('tool'),
            'stderr_tail': o.get('stderr_tail', '')[:100]
        })

# Filter: only commands that failed 3+ times
repeated_failures = []
for cmd_prefix, failures in cmd_failures.items():
    if len(failures) >= 3:
        repeated_failures.append({
            'command': cmd_prefix,
            'fail_count': len(failures),
            'exit_codes': list(set(f['exit_code'] for f in failures)),
            'tool': failures[0]['tool']
        })

# ── Analysis 2: Approval accuracy ───────────────────────────────────
total = len(outcomes)
approve_correct = sum(1 for o in outcomes if o.get('brain_action') == 'approve' and o.get('exit_code') == 0)
approve_wrong = sum(1 for o in outcomes if o.get('brain_action') == 'approve' and o.get('exit_code') != 0)
deny_count = sum(1 for o in outcomes if o.get('brain_action') == 'deny')
accuracy = approve_correct / max(approve_correct + approve_wrong, 1)

# ── Analysis 3: Per-tool error rates ────────────────────────────────
tool_stats = defaultdict(lambda: {'total': 0, 'errors': 0})
for o in outcomes:
    t = o.get('tool', 'unknown')
    tool_stats[t]['total'] += 1
    if o.get('exit_code', 0) != 0:
        tool_stats[t]['errors'] += 1

tool_errors = []
for tool, stats in tool_stats.items():
    if stats['total'] >= 2 and stats['errors'] > 0:
        rate = stats['errors'] / stats['total']
        tool_errors.append({
            'tool': tool,
            'total': stats['total'],
            'errors': stats['errors'],
            'error_rate': round(rate, 2)
        })

# ── Build report ────────────────────────────────────────────────────
report = {
    'analyzed_outcomes': total,
    'approval_accuracy': round(accuracy, 3),
    'approve_correct': approve_correct,
    'approve_wrong': approve_wrong,
    'deny_count': deny_count,
    'repeated_failures': repeated_failures,
    'tool_error_rates': sorted(tool_errors, key=lambda x: x['error_rate'], reverse=True),
    'analyzed_at': datetime.now(timezone.utc).isoformat()
}

print(json.dumps(report, ensure_ascii=False, indent=2))
PYEOF
)

ANALYSIS=$(python3 -c "$ANALYZER_PY" "$OUTCOMES_DIR" "$DECISIONS_LOG" 2>/dev/null || echo '{"errors":[],"summary":"parse_failed"}')

# ── 写入报告 ──────────────────────────────────────────────────────────
echo "$ANALYSIS" | python3 -c "
import json, sys
d = json.load(sys.stdin)

# Write human-readable report
lines = []
lines.append('=== Brain Error Pattern Analysis ===')
lines.append(f\"Analyzed at: {d.get('analyzed_at', 'unknown')}\")
lines.append(f\"Total outcomes: {d.get('analyzed_outcomes', 0)}\")
lines.append(f\"Approval accuracy: {d.get('approval_accuracy', 0)*100:.1f}%\")
lines.append(f\"  Approve+Correct: {d.get('approve_correct', 0)}\")
lines.append(f\"  Approve+Wrong:   {d.get('approve_wrong', 0)}\")
lines.append(f\"  Deny:            {d.get('deny_count', 0)}\")
lines.append('')

rf = d.get('repeated_failures', [])
if rf:
    lines.append('⚠️  REPEATED COMMAND FAILURES (≥3 times):')
    for f in rf:
        lines.append(f\"  ❌ [{f['tool']}] {f['command'][:80]}\")
        lines.append(f\"     Failed {f['fail_count']} times, exit codes: {f['exit_codes']}\")
else:
    lines.append('✅ No repeated command failures detected.')

lines.append('')

te = d.get('tool_error_rates', [])
if te:
    lines.append('📊 TOOL ERROR RATES:')
    for t in te:
        lines.append(f\"  {t['tool']:12s} errors={t['errors']}/{t['total']} rate={t['error_rate']*100:.0f}%\")

with open('/tmp/brain-error-report.txt', 'w') as f:
    f.write('\n'.join(lines))
" 2>/dev/null || true

# ── 检查是否需要生成 proactive suggestions ───────────────────────────
REPEAT_COUNT=$(echo "$ANALYSIS" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('repeated_failures',[])))" 2>/dev/null || echo 0)

if [ "$REPEAT_COUNT" -gt 0 ]; then
    # 生成新建议
    NEW_SUGGESTIONS=$(echo "$ANALYSIS" | python3 -c "
import json, sys
d = json.load(sys.stdin)
suggestions = []
for f in d.get('repeated_failures', []):
    suggestions.append({
        'rule': 'error_pattern',
        'watch_path': '',
        'age_days': 0,
        'last_seen': '',
        'message': f\"⚠️ 命令 '{f['command'][:60]}' 失败了 {f['fail_count']} 次，建议检查原因或调整审批策略。\",
        'scanned_at': d.get('analyzed_at', '')
    })
print(json.dumps(suggestions, ensure_ascii=False))
" 2>/dev/null || echo '[]')

    # 合并到现有 suggestions
    if [ -f "$SUGGESTIONS_FILE" ] && [ "$(wc -c < "$SUGGESTIONS_FILE" 2>/dev/null)" -gt 2 ]; then
        python3 -c "
import json
with open('$SUGGESTIONS_FILE') as f:
    existing = json.load(f)
new_items = json.loads('''$NEW_SUGGESTIONS''')
merged = existing + new_items
with open('$SUGGESTIONS_FILE', 'w') as f:
    json.dump(merged, f, ensure_ascii=False, indent=2)
print(f'Merged {len(new_items)} new error suggestions. Total: {len(merged)}')
" 2>/dev/null || true
    else
        echo "$NEW_SUGGESTIONS" > "$SUGGESTIONS_FILE"
    fi
fi

log_msg "Error analysis complete: ${OUTCOME_COUNT} outcomes, ${REPEAT_COUNT} repeated failure(s)"
