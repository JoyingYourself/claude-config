#!/usr/bin/env bash
# lesson-guard.sh — PreToolUse/PostToolUse hook: 操作级精确教训索引注入
#
# 设计原则:
#   - 100% 触发（不采样），仅在匹配时注入
#   - 从 lessons.md 读取 trigger_patterns 匹配
#   - 单次最多注入 3 条教训（防上下文污染）
#   - 不阻塞操作（always approve）
#
# 输出格式: {"decision":"approve","hookSpecificOutput":{"systemMessage":"..."}}

set -uo pipefail

LESSONS_FILE="$HOME/.claude/lessons.md"

# ============================================================
# 解析 stdin JSON
# ============================================================
RAW=$(cat)

TOOL_NAME=$(echo "$RAW" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || echo "")

# 提取参数：文件路径 / 命令 / MCP Server
FILE_PATH=""
COMMAND=""
MCP_SERVER=""

case "$TOOL_NAME" in
    Write|Edit|NotebookEdit)
        FILE_PATH=$(echo "$RAW" | python3 -c "
import json,sys
d=json.load(sys.stdin)
ti=d.get('tool_input',{})
print(ti.get('file_path',''))
" 2>/dev/null || echo "")
        ;;
    Bash)
        COMMAND=$(echo "$RAW" | python3 -c "
import json,sys
d=json.load(sys.stdin)
ti=d.get('tool_input',{})
print(ti.get('command',''))
" 2>/dev/null || echo "")
        ;;
    mcp__*)
        # MCP tool: extract server name from tool name (mcp__moor__server__tool)
        MCP_SERVER=$(echo "$TOOL_NAME" | python3 -c "
import sys
parts=sys.stdin.read().split('__')
print(parts[2] if len(parts) >= 3 else '')
" 2>/dev/null || echo "")
        # Also extract tool input as command for keyword matching
        COMMAND=$(echo "$RAW" | python3 -c "
import json,sys
d=json.load(sys.stdin)
ti=d.get('tool_input',{})
# Serialize all values for keyword matching
print(' '.join(str(v) for v in ti.values() if isinstance(v,str)))
" 2>/dev/null || echo "")
        ;;
    *)
        exit 0
        ;;
esac

# ============================================================
# Python: 读取 lessons.md，匹配 trigger_patterns，返回命中教训
# ============================================================
MATCHED=$(python3 - "$LESSONS_FILE" "$TOOL_NAME" "$FILE_PATH" "$COMMAND" "$MCP_SERVER" << 'PYEOF'
import sys, re, os

lessons_file = sys.argv[1]
tool_name = sys.argv[2]
file_path = sys.argv[3]
command = sys.argv[4]
mcp_server = sys.argv[5]

if not os.path.exists(lessons_file):
    sys.exit(0)

with open(lessons_file, 'r') as f:
    content = f.read()

# Parse lessons with trigger_patterns
lessons = []
current = None
in_patterns = False
patterns = {"tool_keywords": [], "file_patterns": [], "mcp_servers": []}

for line in content.split('\n'):
    if line.startswith('## [') and '—' in line:
        # Save previous
        if current:
            current['patterns'] = patterns
            lessons.append(current)
        current = {'title': line, 'body': []}
        patterns = {"tool_keywords": [], "file_patterns": [], "mcp_servers": []}
        in_patterns = False
    elif current is not None:
        if line.startswith('trigger_patterns:'):
            in_patterns = True
            continue
        if in_patterns:
            if line.strip().startswith('tool_keywords:'):
                try:
                    patterns['tool_keywords'] = eval(line.split(':',1)[1].strip())
                except: pass
            elif line.strip().startswith('file_patterns:'):
                try:
                    patterns['file_patterns'] = eval(line.split(':',1)[1].strip())
                except: pass
            elif line.strip().startswith('mcp_servers:'):
                try:
                    patterns['mcp_servers'] = eval(line.split(':',1)[1].strip())
                except: pass
            if not line.strip() or line.startswith('>'):
                in_patterns = False
        current['body'].append(line)

if current:
    current['patterns'] = patterns
    lessons.append(current)

# Match
matched = []
for l in lessons:
    p = l['patterns']
    score = 0

    # Match tool_keywords against command
    for kw in p.get('tool_keywords', []):
        if kw and kw in command:
            score += 1

    # Match file_patterns against file_path
    for fp in p.get('file_patterns', []):
        if fp and file_path:
            import fnmatch
            if fnmatch.fnmatch(file_path, fp):
                score += 2  # file match is stronger
            elif fp.replace('*','') in file_path:
                score += 2

    # Match mcp_servers against current MCP server
    for ms in p.get('mcp_servers', []):
        if ms and ms == mcp_server:
            score += 3  # MCP match is strongest

    if score > 0:
        # Extract the lesson message (WHEN + RULE lines)
        msg_lines = []
        for bline in l['body']:
            if bline.startswith('> WHEN:') or bline.startswith('> RULE:'):
                msg_lines.append(bline[2:])
        matched.append((score, '\n'.join(msg_lines)))

# Sort by score desc, take top 3
matched.sort(key=lambda x: x[0], reverse=True)
for _, msg in matched[:3]:
    print(msg)
    print("---")
PYEOF
)

# ============================================================
# 输出
# ============================================================
if [[ -n "$MATCHED" ]]; then
    cat <<EOFOUT
{"decision":"approve","hookSpecificOutput":{"systemMessage":"⚠️ lesson-guard 匹配:\n${MATCHED}"}}
EOFOUT
fi

exit 0
