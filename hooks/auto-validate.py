#!/usr/bin/env python3
"""PostToolUse Hook: Python 语法编译检查（py_compile，标准库，零额外依赖）"""
import sys
import os
import py_compile
from pathlib import Path

file_path = sys.argv[1] if len(sys.argv) > 1 else ""

# 跳过空路径、不存在的文件、Skill/Hook 维护路径
if not file_path or not os.path.exists(file_path):
    sys.exit(0)
if "/.claude/skills/" in file_path or "/.claude/hooks/" in file_path:
    sys.exit(0)

if Path(file_path).suffix == '.py':
    try:
        py_compile.compile(file_path, doraise=True)
        print(f"✅ py_compile: {os.path.basename(file_path)} 语法通过")
    except py_compile.PyCompileError as e:
        print(f"❌ py_compile: {os.path.basename(file_path)} 语法错误")
        print(f"   {e}")
