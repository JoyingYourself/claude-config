#!/bin/bash
# ============================================================
# project-type-prompt.sh — 动态 hook 生成器: 项目类型判定 + 三文档规范注入
#
# 替代 settings.json 中两处写死的 echo hook:
#   - SessionStart     → reset 判定(会话级) + systemMessage"⚠️ 待确认" + 判定指令
#   - UserPromptSubmit → 读状态三态注入:
#       unset   → 判定指令(先询问, 回答后执行 set)
#       complex → 三文档规范动作链(找文档→恢复上下文→汇报待办→更新文档)
#       simple  → 一行提示忽略三文档
#
# hook 环境变量: CLAUDE_HOOK_EVENT_NAME(事件) / CLAUDE_PROJECT_DIR(项目根)
# 输出: 合法 hook JSON(经 python3 json.dumps 转义, 无注入风险)
# ============================================================

PTYPE_SCRIPT="$HOME/.claude/scripts/project-type.sh"

# --- 解析项目目录: hook 环境变量优先, 否则 pwd ---
resolve_dir() {
    if [ -n "$CLAUDE_PROJECT_DIR" ]; then
        echo "$CLAUDE_PROJECT_DIR"
    else
        echo "$PWD"
    fi
}

# --- JSON 转义: python3 json.dumps(无依赖, hooks 已大量使用 python3) ---
json_escape() {
    printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read(), ensure_ascii=False))'
}

# --- 输出 hook JSON: $1=systemMessage(空则省略) $2=additionalContext ---
emit() {
    local sys_msg="$1" ctx="$2"
    local sys_field=""
    if [ -n "$sys_msg" ]; then
        sys_field="\"systemMessage\": $(json_escape "$sys_msg"), "
    fi
    printf '{%s"hookSpecificOutput": {"hookEventName": "%s", "additionalContext": %s}}' \
        "$sys_field" "$CLAUDE_HOOK_EVENT_NAME" "$(json_escape "$ctx")"
}

EVENT="${CLAUDE_HOOK_EVENT_NAME:-}"

case "$EVENT" in
    SessionStart)
        # 会话级判定核心: 每次新会话重置 → 强制重新询问
        PTYPE_DIR="$(resolve_dir)" bash "$PTYPE_SCRIPT" reset
        emit "⚠️ 项目类型待确认: 此项目是否为复杂任务? 回复 是 → 执行三文档规范(README/HANDOFF/ATTENTION); 回复 否 → 正常处理" \
            "【硬性要求-项目类型判定】你的第一条回复必须先向用户询问: 此项目是否为复杂任务? 在用户明确回答之前, 禁止开始任何项目工作/任务/工具调用。用户回答后立即执行判定持久化: 是 → 运行 ~/.claude/scripts/project-type.sh set complex 并按三文档规范执行(README/HANDOFF/ATTENTION, 模板 ~/.claude/project-templates/triple-doc/); 否 → 运行 ~/.claude/scripts/project-type.sh set simple 后正常处理。"
        ;;
    UserPromptSubmit)
        state=$(PTYPE_DIR="$(resolve_dir)" bash "$PTYPE_SCRIPT" get 2>/dev/null || true)
        case "$state" in
            complex)
                emit "" "【三文档规范-复杂任务】本会话已判定为复杂任务, 回复前执行:
1. 判定持久化: 运行 ~/.claude/scripts/project-type.sh set complex(状态栏显示 🔧 复杂任务)
2. 检查项目根目录三文档 README.md / HANDOFF.md / ATTENTION.md:
   - 不存在 → 按 ~/.claude/project-templates/triple-doc/ 模板创建三份; README 模板已预填"通用工程规范"章节(用户逐条审批固化), 创建时必须完整保留该章节, 只补齐 {项目名}/{YYYY-MM-DD} 占位符
   - 存在 → 按 HANDOFF.md §1 读取顺序依次解析全部项目文件(每文件回答: 解决什么问题/依赖谁/被谁依赖), 完全恢复上下文
3. 恢复完成后, 回复开头先汇报当前记录的待解决任务(HANDOFF §3 待办 / README 遗留)
4. 回复前更新三份文档: README(全量信息, 去旧) / HANDOFF(交接给下一个Agent, 顺序解析可恢复) / ATTENTION(踩坑, 只增不删, 状态三档: 未修复/已修复未验证/已修复已验证)
用户中途表示临时需求或要求切换类型 → 运行 ~/.claude/scripts/project-type.sh set simple 停止三文档维护"
                ;;
            simple)
                emit "" "【会话类型-普通任务】本项目已判定为普通任务, 忽略三文档规范, 正常执行。若用户要求重新判定为复杂任务, 运行 ~/.claude/scripts/project-type.sh set complex 并按三文档规范执行。"
                ;;
            *)
                emit "" "【硬性要求-项目类型判定】本条回复必须先向用户询问: 此项目是否为复杂任务? 在用户明确回答之前, 禁止开始任何项目工作/任务/工具调用。用户回答后立即执行判定持久化: 是 → 运行 ~/.claude/scripts/project-type.sh set complex 并按三文档规范执行(模板 ~/.claude/project-templates/triple-doc/); 否 → 运行 ~/.claude/scripts/project-type.sh set simple 后正常处理。"
                ;;
        esac
        ;;
    *)
        # 未知事件: 不输出(无副作用)
        exit 0
        ;;
esac
