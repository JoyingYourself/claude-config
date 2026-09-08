#!/usr/bin/env python3
"""
PostToolUse hook: detect config file changes and remind Claude to self-verify.

Trigger: Write/Edit to .mcp.json or ~/.claude/skills/*/SKILL.md
Action:  Print a reminder suggesting /EngineeringConfig_Verify
"""

import os
import sys

def main():
    file_path = sys.argv[1] if len(sys.argv) > 1 else ""

    if not file_path:
        return

    # Normalize path
    file_path = os.path.abspath(file_path)
    skills_dir = os.path.expanduser("~/.claude/skills")

    # Check patterns
    is_mcp_config = (
        file_path.endswith(".mcp.json") or
        file_path.endswith("mcp.json")
    )
    is_skill_md = (
        file_path.startswith(skills_dir) and
        file_path.endswith("SKILL.md")
    )

    if not (is_mcp_config or is_skill_md):
        return  # Not a config file, silent exit

    # Build reminder
    if is_mcp_config:
        config_name = os.path.basename(file_path)
        msg = (
            f"\n{'='*50}\n"
            f"🔧 检测到 MCP 配置变更: {config_name}\n"
            f"💡 建议运行自检: /EngineeringConfig_Verify --mcp <server-name>\n"
            f"   (自动验证 MCP 连接 + 工具发现，无需重启 Claude)\n"
            f"{'='*50}\n"
        )
    else:
        skill_name = os.path.basename(os.path.dirname(file_path))
        msg = (
            f"\n{'='*50}\n"
            f"🔧 检测到 Skill 文件变更: {skill_name}/SKILL.md\n"
            f"💡 建议运行自检: /EngineeringConfig_Verify --skill {skill_name}\n"
            f"   (自动验证 Skill 语法 + 新会话发现，无需重启 Claude)\n"
            f"{'='*50}\n"
        )

    # Print to stdout — this becomes system feedback for Claude
    print(msg)

if __name__ == "__main__":
    main()
