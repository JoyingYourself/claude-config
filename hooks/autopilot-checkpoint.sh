#!/bin/bash
# autopilot-checkpoint.sh — 记录当前进度到 /tmp/autopilot_checkpoint.json
# 触发: PhaseGate 调用后 / Stop hook / 后台任务启动前

set -uo pipefail

CHECKPOINT_FILE="/tmp/autopilot_checkpoint.json"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EVENT="${1:-unknown}"

python3 << PYEOF
import json, os, time

cf = "${CHECKPOINT_FILE}"
event = "${EVENT}"
ts = "${TIMESTAMP}"

data = {"last_event": event, "last_time": ts, "checkpoints": []}
if os.path.exists(cf):
    try:
        with open(cf) as f:
            data = json.load(f)
    except:
        pass

data["last_event"] = event
data["last_time"] = ts
data["checkpoints"].append({"event": event, "time": ts})

# 只保留最近 50 条
data["checkpoints"] = data["checkpoints"][-50:]

with open(cf, "w") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
PYEOF

exit 0
