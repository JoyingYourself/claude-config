#!/usr/bin/env bash
# lessons-inject.sh — SessionStart hook: 注入跨项目教训到会话上下文
# 触发时机: startup (新会话) + compact (上下文压缩后重新注入)
#
# 用法:
#   lessons-inject.sh              → 自动模式: 联动项目类型判定注入
#                                     simple   → 仅注入 KEYWORDS 索引(轻量)
#                                     complex  → 全量注入(兼容现有行为)
#                                     unset    → 全量注入(保守, 与旧行为一致)
#   lessons-inject.sh --full       → 固定全量注入(供 startup 挂载使用, 不读状态;
#                                     startup 时判定未重置, 残留状态不可信)
#   lessons-inject.sh "MCP,回测"   → 仅注入关键词匹配的教训(手动按需, 不联动状态)
#   lessons-inject.sh --count      → 仅输出数量（用于 hook 内部判断）
#
# 状态来源: ~/.claude/scripts/project-type.sh (与 project-type-prompt.sh 同源)
#   目录 key: CLAUDE_PROJECT_DIR 优先, 否则 $PWD

set -uo pipefail

LESSONS_FILE="${HOME}/.claude/lessons.md"
CONTEXT_HINT="${1:-}"

# 文件不存在 → 跳过
if [[ ! -f "$LESSONS_FILE" ]]; then
    exit 0
fi

# 统计总教训数
TOTAL_LESSONS=$(grep -cE '^## \[.+\] 20[0-9]{2}-[0-9]{2}-[0-9]{2}' "$LESSONS_FILE" 2>/dev/null; true)
TOTAL_LESSONS=$(echo "${TOTAL_LESSONS:-0}" | tr -d '[:space:]')

# --count 模式
if [[ "$CONTEXT_HINT" == "--count" ]]; then
    echo "${TOTAL_LESSONS:-0}"
    exit 0
fi

# 输出头部
print_header() {
    echo ""
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║  📚 量化研究教训库 (auto-loaded via lessons-inject)  ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo ""
}

# 全量注入
inject_all() {
    print_header
    cat "$LESSONS_FILE"
    echo ""
    echo "---"
    echo "📋 已加载全部 ${TOTAL_LESSONS} 条跨项目教训。"
    echo ""
}

# ============================================================
# 项目类型联动: 读取 project-type.sh 状态
#   返回值: complex | simple | unset (get 失败时视为 unset)
# ============================================================
get_project_type() {
    local dir="${CLAUDE_PROJECT_DIR:-$PWD}"
    local state
    state=$(PTYPE_DIR="$dir" bash "$HOME/.claude/scripts/project-type.sh" get 2>/dev/null || true)
    echo "${state:-unset}"
}

# 索引注入 (simple 模式): 仅 KEYWORDS INDEX 表, 详细教训由
# PreToolUse lesson-guard.sh 按实际操作实时匹配注入, 不丢失覆盖
inject_index() {
    print_header
    echo "📋 普通任务(simple): 仅注入关键词索引; 详细教训由 lesson-guard 按操作实时匹配。"
    echo ""
    # 提取 KEYWORDS INDEX 表: 从 "## KEYWORDS INDEX" 到第一个 "# 章节标题" 前
    awk '/^## KEYWORDS INDEX/{f=1} f&&/^# [A-Z]/{exit} f' "$LESSONS_FILE"
    echo ""
    echo "---"
    echo "📋 已加载关键词索引(共 ${TOTAL_LESSONS} 条教训按需匹配)。"
    echo "   手动全量注入: bash ~/.claude/hooks/lessons-inject.sh \"关键词1,关键词2\""
    echo ""
}

# ============================================================
# 关键词过滤注入
# ============================================================
inject_filtered() {
    local hint="$1"
    print_header
    echo "📋 匹配关键词: ${hint}"
    echo ""

    # 解析关键词（逗号/空格/中文逗号分隔）
    local keywords_csv=$(echo "$hint" | tr ',， ' '\n' | grep -v '^$' | tr '\n' '|' | sed 's/|$//')

    if [[ -z "$keywords_csv" ]]; then
        inject_all
        return
    fi

    # 在 KEYWORDS INDEX 表中查找匹配行
    # 格式: | key1, key2 | refs |
    local matched_refs=""
    local matched_count=0

    # 用 grep 找每个关键词匹配的 INDEX 行，提取 refs 列
    for kw in $(echo "$hint" | tr ',， ' '\n' | grep -v '^$'); do
        local found_lines=$(grep -i "$kw" "$LESSONS_FILE" | grep -E '^\|.*\|.*\|' | head -5)
        if [[ -n "$found_lines" ]]; then
            while IFS= read -r line; do
                # 提取第三列：refs
                local refs=$(echo "$line" | awk -F'|' '{print $3}' | xargs)
                for ref in $(echo "$refs" | tr ',' '\n'); do
                    ref=$(echo "$ref" | xargs)
                    # 去重检查
                    if ! echo "$matched_refs" | grep -qF "$ref"; then
                        matched_refs="${matched_refs} ${ref}"
                        matched_count=$((matched_count + 1))
                    fi
                done
            done <<< "$found_lines"
        fi
    done

    # 无匹配 → 降级全量
    if [[ $matched_count -eq 0 ]]; then
        echo "⚠️  关键词 \"${hint}\" 未匹配到任何教训，降级为全量注入。"
        echo ""
        cat "$LESSONS_FILE"
        echo ""
        echo "---"
        echo "📋 已加载全部 ${TOTAL_LESSONS} 条跨项目教训。"
        echo ""
        return
    fi

    # 有匹配 → 提取对应章节
    local print_mode=0
    while IFS= read -r line; do
        # 检测新章节开始（## [...] YYYY-MM-DD）
        if echo "$line" | grep -qE '^## \[.+\] 20[0-9]{2}-[0-9]{2}-[0-9]{2}'; then
            print_mode=0
            local ref_id=$(echo "$line" | sed -E 's/^## \[([A-Za-z\/]+)\] (20[0-9]{2}-[0-9]{2}-[0-9]{2}[-a-z]*).*/\1\/\2/')
            if echo "$matched_refs" | grep -qF "$ref_id"; then
                print_mode=1
            fi
        fi

        if [[ $print_mode -eq 1 ]]; then
            # 跳过段间分隔和段标题
            if echo "$line" | grep -qE '^---$|^# [A-Z]'; then
                continue
            fi
            echo "$line"
        fi
    done < "$LESSONS_FILE"

    echo ""
    echo "---"
    echo "📋 已加载 ${matched_count}/${TOTAL_LESSONS} 条相关教训（关键词: ${hint}）"
    echo "   完整教训库 ${TOTAL_LESSONS} 条，本条消息仅展示匹配项。"
    echo ""
}

# ============================================================
# Main
# ============================================================

if [[ "$CONTEXT_HINT" == "--full" ]]; then
    # 固定全量注入, 不读项目类型状态(startup 挂载专用)
    inject_all
    exit 0
fi

if [[ -z "$CONTEXT_HINT" ]]; then
    # 自动模式: 联动项目类型判定
    case "$(get_project_type)" in
        simple)
            inject_index
            ;;
        *)  # complex 或 unset(未判定/读取失败): 全量注入, 与旧行为一致
            inject_all
            ;;
    esac
else
    inject_filtered "$CONTEXT_HINT"
fi
