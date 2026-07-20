#!/bin/bash
# autopilot-heartbeat.sh — 后台进程心跳监控 + 自动重启
# Cron: */5 * * * * (durable)
# 检查 /tmp/autopilot_state.json 中注册的进程，死亡则自动重启

set -uo pipefail  # 无 -e: hook 永不阻断

STATE_FILE="/tmp/autopilot_state.json"
LOG_FILE="/tmp/autopilot_heartbeat.log"

[ ! -f "$STATE_FILE" ] && exit 0  # 无任务，跳过

echo "[$(date '+%H:%M:%S')] heartbeat" >> "$LOG_FILE"

python3 << 'PYEOF' 2>> "$LOG_FILE"
import json, os, subprocess, time

state_file = "/tmp/autopilot_state.json"
try:
    with open(state_file) as f:
        state = json.load(f)
except:
    exit(0)

procs = state.get("processes", {})
if not procs:
    exit(0)

for name, info in list(procs.items()):
    pid = info.get("pid")
    if not pid:
        continue

    # 检查存活
    try:
        result = subprocess.run(["ps", "-p", str(pid), "-o", "pid=,cpu=,etime="],
                                capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            raise Exception("process not found")
        line = result.stdout.strip()
        if not line:
            raise Exception("empty ps output")
        parts = line.split()
        cpu = float(parts[1]) if len(parts) > 1 else 0

        # CPU=0% 持续 >10min → 卡死
        elapsed = parts[2] if len(parts) > 2 else "00:00"
        if cpu == 0 and ":" in elapsed:
            mins = int(elapsed.split(":")[0]) if len(elapsed.split(":")) == 2 else 0
            if mins > 10:
                print(f"[HEARTBEAT] {name} (PID={pid}) CPU=0% for {elapsed} — 卡死, kill")
                subprocess.run(["kill", str(pid)])
                raise Exception("stuck process killed")

        info["last_check"] = time.strftime("%H:%M:%S")
        info["cpu"] = cpu
        continue  # 存活

    except Exception as e:
        restarts = info.get("restarts", 0)
        if restarts >= 3:
            print(f"[HEARTBEAT] {name} 已达最大重启次数(3), 放弃")
            info["status"] = "abandoned"
            continue

        # 自动重启
        restart_cmd = info.get("restart_cmd", "")
        if not restart_cmd:
            print(f"[HEARTBEAT] {name} 无重启命令, 放弃")
            info["status"] = "no_restart_cmd"
            continue

        restarts += 1
        print(f"[HEARTBEAT] {name} 进程死亡, 自动重启 (第{restarts}次)")
        try:
            new_proc = subprocess.Popen(restart_cmd, shell=True,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            info["pid"] = new_proc.pid
            info["restarts"] = restarts
            info["last_restart"] = time.strftime("%H:%M:%S")
            info["last_check"] = time.strftime("%H:%M:%S")
            print(f"[HEARTBEAT] {name} 重启成功, 新PID={new_proc.pid}")
        except Exception as e2:
            print(f"[HEARTBEAT] {name} 重启失败: {e2}")
            info["status"] = "restart_failed"

# 写回
state["processes"] = procs
with open(state_file, "w") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
PYEOF

exit 0
