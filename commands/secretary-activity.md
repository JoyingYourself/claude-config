---
name: secretary-activity
description: Show recent brain decisions and activity log
args: "[N]"
---

Show the claudectl secretary brain's recent activity — what decisions it made, on what tools, with what confidence.

Optionally pass a number (default 10): `/secretary-activity 20`

## What to do

Run these checks and present the results as a clean activity feed:

```bash
# 1. Read recent decisions from the log
DECISIONS_LOG="$HOME/.claudectl/brain/decisions.jsonl"
if [ -f "$DECISIONS_LOG" ] && [ -s "$DECISIONS_LOG" ]; then
    echo "=== RECENT_DECISIONS ==="
    tail -20 "$DECISIONS_LOG" | python3 -c "
import json, sys
from datetime import datetime

decisions = []
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        d = json.loads(line)
        decisions.append(d)
    except:
        pass

if not decisions:
    print('暂无决策记录')
    sys.exit(0)

# Show last N (user can specify count)
decisions = decisions[-10:]

print(f'## 📋 最近 {len(decisions)} 条决策\n')
print('| 时间 | 工具 | 命令 | 决策 | 置信度 | 推理 |')
print('|------|------|------|------|--------|------|')
for d in reversed(decisions):
    ts = d.get('timestamp', '?')
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        ts_str = dt.strftime('%m-%d %H:%M')
    except:
        ts_str = ts[:16]
    tool = d.get('tool', '?')
    cmd = d.get('command', '?')[:50]
    action = d.get('action', '?')
    conf = d.get('confidence', 0)
    reasoning = d.get('reasoning', '')[:60]
    
    action_emoji = {'approve': '✅', 'deny': '🛑', 'ask': '❓'}.get(action, '❓')
    conf_bar = '█' * int(conf * 10) + '░' * (10 - int(conf * 10))
    
    print(f'| {ts_str} | {tool} | `{cmd}` | {action_emoji} {action} | {conf:.0%} | {reasoning} |')

# Summary stats
total = len(decisions)
approves = sum(1 for d in decisions if d.get('action') == 'approve')
denies = sum(1 for d in decisions if d.get('action') == 'deny')
asks = sum(1 for d in decisions if d.get('action') == 'ask')
avg_conf = sum(d.get('confidence', 0) for d in decisions) / max(total, 1)

print(f'\n### 📊 本批统计')
print(f'| 批准 | 拒绝 | 询问 | 平均置信度 |')
print(f'|------|------|------|-----------|')
print(f'| {approves} | {denies} | {asks} | {avg_conf:.0%} |')
"
else
    echo "📭 暂无决策记录。秘书需要积累更多审批数据。"
fi

# 2. Check pending outcomes (unprocessed results)
PENDING_DIR="$HOME/.claudectl/brain/pending-outcomes"
if [ -d "$PENDING_DIR" ]; then
    PENDING=$(ls "$PENDING_DIR" 2>/dev/null | wc -l | tr -d ' ')
else
    PENDING=0
fi
echo ""
echo "📥 待处理结果: ${PENDING} 个 (reaper 每15分钟自动收割)"

# 3. Check resolved outcomes
OUTCOMES_DIR="$HOME/.claudectl/brain/outcomes"
if [ -d "$OUTCOMES_DIR" ]; then
    RESOLVED=$(ls "$OUTCOMES_DIR" 2>/dev/null | wc -l | tr -d ' ')
else
    RESOLVED=0
fi
echo "✅ 已匹配结果: ${RESOLVED} 个"

# 4. Total decisions all-time
if [ -f "$DECISIONS_LOG" ]; then
    TOTAL=$(wc -l < "$DECISIONS_LOG" | tr -d ' ')
else
    TOTAL=0
fi
echo "🧠 历史总决策: ${TOTAL} 条"
```

Present results as a clean activity feed with timestamp, tool, command, decision, and confidence.
If no decisions exist yet, encourage the user that the brain needs more activity to build its decision history.
