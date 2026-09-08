#!/bin/bash
# register-process.sh — 注册/注销/查看 autopilot 心跳守护进程
# 用法:
#   register-process.sh register <name> <pid> <restart_cmd>
#   register-process.sh unregister <name>
#   register-process.sh list
#   register-process.sh status <name>
#
# 设计目标: Claude Code 在启动长任务后调用此脚本注册进程，
# 系统 crontab 每5分钟运行的 autopilot-heartbeat.sh 监控注册的进程。

set -uo pipefail

STATE_FILE="/tmp/autopilot_state.json"
ACTION="${1:-}"
ARG_NAME="${2:-}"
ARG_PID="${3:-}"
ARG_RESTART_CMD="${4:-}"

_ensure_state_file() {
    if [ ! -f "$STATE_FILE" ]; then
        echo '{"processes":{}}' > "$STATE_FILE"
    fi
}

cmd_register() {
    local name="$1" pid="$2" restart_cmd="$3"
    if [ -z "$name" ] || [ -z "$pid" ]; then
        echo "用法: $0 register <name> <pid> [restart_cmd]"
        exit 1
    fi
    # 验证 PID 是否存在
    if ! ps -p "$pid" > /dev/null 2>&1; then
        echo "⚠️  警告: PID $pid 不存在，但仍会注册（可能尚未启动）"
    fi
    _ensure_state_file
    python3 << PYEOF
import json, os, time

state_file = "${STATE_FILE}"
name = "${name}"
pid = int("${pid}")
restart_cmd = """${restart_cmd}"""

with open(state_file) as f:
    state = json.load(f)

state.setdefault("processes", {})
state["processes"][name] = {
    "pid": pid,
    "restart_cmd": restart_cmd,
    "restarts": 0,
    "last_check": time.strftime("%H:%M:%S"),
    "cpu": 0,
    "status": "running",
    "registered_at": time.strftime("%Y-%m-%d %H:%M:%S")
}

with open(state_file, "w") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
print(f"✅ 已注册: {name} (PID={pid})")
if restart_cmd:
    print(f"   重启命令: {restart_cmd}")
PYEOF
}

cmd_unregister() {
    local name="$1"
    if [ -z "$name" ]; then
        echo "用法: $0 unregister <name>"
        exit 1
    fi
    if [ ! -f "$STATE_FILE" ]; then
        echo "⚠️  状态文件不存在，无需注销"
        exit 0
    fi
    python3 << PYEOF
import json

state_file = "${STATE_FILE}"
name = "${name}"

with open(state_file) as f:
    state = json.load(f)

procs = state.get("processes", {})
if name in procs:
    del procs[name]
    with open(state_file, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"✅ 已注销: {name}")
else:
    print(f"⚠️  进程 '{name}' 未注册")
PYEOF
}

cmd_list() {
    if [ ! -f "$STATE_FILE" ]; then
        echo "(无注册进程)"
        exit 0
    fi
    python3 << PYEOF
import json

state_file = "${STATE_FILE}"
with open(state_file) as f:
    state = json.load(f)

procs = state.get("processes", {})
if not procs:
    print("(无注册进程)")
    exit(0)

print(f"{'名称':<30} {'PID':<8} {'状态':<12} {'重启':<4} {'最后检查':<10}")
print("-" * 70)
for name, info in sorted(procs.items()):
    pid = info.get("pid", "?")
    status = info.get("status", "?")
    restarts = info.get("restarts", 0)
    last = info.get("last_check", "-")
    print(f"{name:<30} {str(pid):<8} {status:<12} {str(restarts):<4} {last:<10}")
PYEOF
}

cmd_status() {
    local name="$1"
    if [ -z "$name" ]; then
        echo "用法: $0 status <name>"
        exit 1
    fi
    if [ ! -f "$STATE_FILE" ]; then
        echo "❌ 状态文件不存在"
        exit 1
    fi
    python3 << PYEOF
import json

state_file = "${STATE_FILE}"
name = "${name}"

with open(state_file) as f:
    state = json.load(f)

procs = state.get("processes", {})
if name not in procs:
    print(f"❌ 进程 '{name}' 未注册")
    exit(1)

info = procs[name]
print(f"名称:       {name}")
print(f"PID:        {info.get('pid', '?')}")
print(f"状态:       {info.get('status', '?')}")
print(f"重启次数:   {info.get('restarts', 0)}")
print(f"重启命令:   {info.get('restart_cmd', '(无)')}")
print(f"最后检查:   {info.get('last_check', '-')}")
print(f"CPU:        {info.get('cpu', 0)}%")
print(f"注册时间:   {info.get('registered_at', '-')}")
PYEOF
}

case "$ACTION" in
    register)   cmd_register "$ARG_NAME" "$ARG_PID" "$ARG_RESTART_CMD" ;;
    unregister) cmd_unregister "$ARG_NAME" ;;
    list)       cmd_list ;;
    status)     cmd_status "$ARG_NAME" ;;
    *)
        echo "用法: $0 {register|unregister|list|status} [args...]"
        echo ""
        echo "  register <name> <pid> [restart_cmd]  — 注册进程到心跳守护"
        echo "  unregister <name>                    — 注销进程"
        echo "  list                                 — 列出所有注册进程"
        echo "  status <name>                        — 查看进程详细状态"
        exit 1
        ;;
esac
