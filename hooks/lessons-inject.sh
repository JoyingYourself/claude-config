#!/usr/bin/env bash
# lessons-inject.sh — SessionStart hook: 注入跨项目教训到会话上下文
# 触发时机: startup (新会话) + compact (上下文压缩后重新注入)
#
# 逻辑:
#   - lessons.md 存在且有实际教训条目 → cat 输出 + 确认提示
#   - lessons.md 只有模板框架(无 ## 标题的教训条目) → 静默跳过
#   - lessons.md 不存在 → 静默跳过

set -uo pipefail  # -e removed: hook must never fail-stop the session

LESSONS_FILE="${HOME}/.claude/lessons.md"

# 文件不存在 → 跳过
if [[ ! -f "$LESSONS_FILE" ]]; then
    exit 0
fi

# 统计实际教训条目数 (以 "## 20" 开头的行，排除模板说明中的示例)
# 注意: grep -c 在 0 匹配时 exit code=1，不能直接 || echo 0
LESSON_COUNT=$(grep -cE '^## 20[0-9]{2}-[0-9]{2}-[0-9]{2}' "$LESSONS_FILE" 2>/dev/null; true)
# 去除可能的空白和多余的换行
LESSON_COUNT=$(echo "${LESSON_COUNT:-0}" | head -1 | tr -d '[:space:]')
LESSON_COUNT="${LESSON_COUNT:-0}"

# 输出注入内容
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  📚 量化研究教训库 (auto-loaded via lessons-inject)  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

if [[ "$LESSON_COUNT" -gt 0 ]]; then
    # 有实际教训 → 输出全部内容
    cat "$LESSONS_FILE"
    echo ""
    echo "---"
    echo "📋 已加载 ${LESSON_COUNT} 条跨项目教训。"
    echo "⚠️  你必须在回复开头简要确认已加载这些教训 (如 '已加载 N 条教训')。"
    echo ""
else
    # 只有模板 → 提示框架就绪
    echo "  ℹ️  教训库已初始化，暂无教训条目。"
    echo "  踩坑后我会自动追加。写入规则见 lessons.md。"
    echo ""
fi
