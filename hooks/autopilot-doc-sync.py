#!/usr/bin/env python3
"""PostToolUse hook: Write/Edit .py 文件后检查注释/文档中的旧命名是否已同步"""
import sys, os, re, json

# 已知重命名映射 (old_name → new_name)
RENAMES = {
    "gross_margin": "operating_margin",
    "pe_extracted_t0": "pe_ttm_cut",
    "pb_extracted_t0": "pb_mrq",
    "ev_extracted_t0": "ev_ex_cash",
    "dy_extracted_t0": "dy_ttm",
    "revenue_yoy": "operatingrevenue_yoy",
    "ocf_yoy": "operate_cf_yoy",
}

def check_file(filepath):
    """检查文件中是否还有旧命名的注释/文档引用"""
    if not filepath.endswith('.py') and not filepath.endswith('.md'):
        return []
    if not os.path.exists(filepath):
        return []

    issues = []
    with open(filepath, 'r') as f:
        lines = f.readlines()

    for i, line in enumerate(lines, 1):
        # 跳过代码行（只检查注释和文档字符串）
        stripped = line.strip()
        if not (stripped.startswith('#') or stripped.startswith('"""') or
                stripped.startswith("'''") or '"' in stripped or
                'description' in stripped.lower() or 'label' in stripped.lower()):
            # 也检查注释中的命名
            pass

        for old, new in RENAMES.items():
            if old in line and new not in line:
                # 排除代码中的赋值/引用（这些是故意的）
                if f'"{old}"' in line or f"'{old}'" in line or f'"{old}' in line:
                    continue
                # 只在注释/文档中检查
                if '#' in line or '"""' in line or "'''" in line or 'description' in line.lower():
                    issues.append((i, old, new, line.strip()[:120]))

    return issues

if __name__ == '__main__':
    # CLAUDE_TOOL_INPUT_FILE_PATH is set by Claude Code for Write/Edit hooks
    filepath = os.environ.get('CLAUDE_TOOL_INPUT_FILE_PATH', '')
    if not filepath:
        sys.exit(0)

    issues = check_file(filepath)
    if issues:
        print(f"[DOC-SYNC] ⚠️ {filepath}: {len(issues)} 处可能需更新命名:", file=sys.stderr)
        for line_no, old, new, context in issues[:5]:
            print(f"  L{line_no}: '{old}' → '{new}' — {context}", file=sys.stderr)

    sys.exit(0)  # 永不阻断
