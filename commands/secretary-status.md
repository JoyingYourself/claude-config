---
name: secretary-status
description: Show claudectl secretary brain health and on-duty status
args: ""
---

Show the current status of the claudectl secretary brain — whether it's on duty, healthy, and actively monitoring, plus recent activity summary.

## What to do

Run ALL of the following checks and present the results as a clean status dashboard:

```bash
echo "=== 秘书值班面板 ===\n"

# 1. Brain process status
echo "## 🏥 健康状态"
pgrep -fl "claudectl --brain" 2>/dev/null && echo "  🟢 秘书进程运行中" || echo "  🔴 秘书进程离线"

# 2. Gate mode
GATE=$(cat ~/.claudectl/brain/gate-mode 2>/dev/null || echo "on (默认)")
echo "  🚪 门控模式: $GATE"

# 3. Ollama reachability
if curl -sf -o /dev/null http://localhost:11434/api/tags 2>/dev/null; then
    echo "  🟢 Ollama 可达"
else
    echo "  🔴 Ollama 不可达"
fi

# 4. Model loaded status
curl -s localhost:11434/api/ps 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
models=[m['name'] for m in d.get('models',[])]
if models:
    # Show model + expiry
    for m in d['models']:
        exp = m.get('expires_at','')
        print(f'  🟢 模型已加载: {m[\"name\"]} (context: {m.get(\"context_length\",\"?\")}, 到期: {exp[11:19] if exp else \"?\"})')
else:
    print('  🟡 模型未加载（下次调用时自动加载，约3-8秒）')
" 2>/dev/null || echo "  ⚠️ 模型状态未知"

echo ""

# 5. Decision stats + recent activity
echo "## 📊 决策活动"
DECISIONS_LOG="$HOME/.claudectl/brain/decisions.jsonl"
if [ -f "$DECISIONS_LOG" ] && [ -s "$DECISIONS_LOG" ]; then
    python3 -c "
import json, sys
from datetime import datetime, timezone, timedelta

with open('$DECISIONS_LOG') as f:
    decisions = [json.loads(line) for line in f if line.strip()]

total = len(decisions)
approves = sum(1 for d in decisions if d.get('action') == 'approve')
denies = sum(1 for d in decisions if d.get('action') == 'deny')
asks = sum(1 for d in decisions if d.get('action') == 'ask')
avg_conf = sum(d.get('confidence', 0) for d in decisions) / max(total, 1)

# Count today's decisions
tz = timezone(timedelta(hours=8))
today_start = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
today_count = 0
for d in decisions:
    try:
        dt = datetime.fromisoformat(d['timestamp'].replace('Z', '+00:00'))
        if dt >= today_start:
            today_count += 1
    except:
        pass

print(f'  历史总决策: {total} | 今日: {today_count}')
print(f'  批准: {approves} | 拒绝: {denies} | 询问: {asks} | 平均置信度: {avg_conf:.0%}')
print()

# Show last 5 decisions
recent = decisions[-5:]
if recent:
    print('  最近 5 条:')
    for d in reversed(recent):
        ts = d.get('timestamp', '?')
        try:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            ts_str = dt.strftime('%m-%d %H:%M')
        except:
            ts_str = str(ts)[:16]
        tool = d.get('tool', '?')
        cmd = d.get('command', '?')[:55]
        action = d.get('action', '?')
        conf = d.get('confidence', 0)
        emoji = {'approve': '✅', 'deny': '🛑', 'ask': '❓'}.get(action, '❓')
        print(f'    {ts_str} {emoji} [{tool}] {cmd} ({conf:.0%})')
" 2>/dev/null || echo "  暂无决策数据"
else
    echo "  📭 暂无决策记录 — 秘书正在学习你的审批偏好..."
fi

echo ""

# 6. Pending outcomes
echo "## 📬 数据管线"
PENDING_DIR="$HOME/.claudectl/brain/pending-outcomes"
if [ -d "$PENDING_DIR" ]; then
    PENDING=$(ls "$PENDING_DIR" 2>/dev/null | wc -l | tr -d ' ')
else
    PENDING=0
fi
echo "  待处理结果: $PENDING 个 (reaper 每15分钟收割)"

# Session summaries
SUMM_DIR="$HOME/.claudectl/brain/session-summaries"
if [ -d "$SUMM_DIR" ]; then
    SUMM=$(ls "$SUMM_DIR" 2>/dev/null | wc -l | tr -d ' ')
else
    SUMM=0
fi
echo "  会话摘要: $SUMM 个"

# Proactive suggestions
SUGG="$HOME/.claudectl/brain/proactive-suggestions.json"
if [ -f "$SUGG" ]; then
    SUGG_COUNT=$(python3 -c "import json; print(len(json.load(open('$SUGG'))))" 2>/dev/null || echo 0)
    echo "  主动提醒: $SUGG_COUNT 条"
fi

echo ""
echo "📖 查看详细活动: /secretary-activity"
```

Present results as a clean dashboard with sections:
- 🏥 健康状态 (green/red indicators)
- 📊 决策活动 (today + total + recent 5)
- 📬 数据管线 (pending outcomes, session summaries, suggestions)
- Footer with link to /secretary-activity for details
