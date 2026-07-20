#!/usr/bin/env python3
"""
MD→HTML 渲染器 for DocumentJournal_Daily.
替换 SKILL.md Step 8 中脆弱的 bash 正则替换，使用 Python markdown 库 + Jinja2 模板。

用法:
  python3 render_html.py <md_file> <template_file> <html_file> <date>

退出码: 0=成功, 1=校验失败
"""

import sys
import os
import re
from pathlib import Path

import markdown
from jinja2 import Template


def validate_html(html_content: str, md_content: str, today: str) -> list[str]:
    """校验 HTML 输出，返回错误列表（空=通过）。"""
    errors = []

    # 1. 非空且 ≥ 500 字节
    size = len(html_content.encode("utf-8"))
    if size < 500:
        errors.append(f"HTML 文件过小 ({size} 字节)，渲染可能失败")

    # 2. 关键闭合标签存在
    for tag in ["</html>", "</head>", "</body>"]:
        if tag not in html_content:
            errors.append(f"HTML 缺少关键闭合标签: {tag}")

    # 3. 模板占位符无残留
    if "{{CONTENT}}" in html_content:
        errors.append("HTML 含未替换的模板占位符 {{CONTENT}}")
    if "__DATE__" in html_content:
        errors.append("HTML 含未替换的模板占位符 __DATE__")

    # 4. HTML ≥ MD × 80%
    md_size = len(md_content.encode("utf-8"))
    if md_size > 0 and size < md_size * 0.8:
        errors.append(f"HTML ({size}B) 小于 MD ({md_size}B) 的 80%，内容可能截断")

    # 5. 含当日日期
    if today not in html_content:
        errors.append(f"HTML 不含当日日期 {today}")

    return errors


def convert_md_to_html(md_text: str) -> str:
    """将 Markdown 文本转换为 HTML。"""
    # 剥离 H1 标题行（模板的 <h1> 已含日期）
    lines = md_text.split("\n")
    if lines and re.match(r"^# 工作日志\b", lines[0]):
        lines = lines[1:]
        # 移除 H1 后的空白行
        while lines and lines[0].strip() == "":
            lines.pop(0)
    body = "\n".join(lines)

    # MD → HTML，扩展: extra(表格/围栏代码块/脚注), sane_lists(列表嵌套)
    html_body = markdown.markdown(
        body,
        extensions=["extra", "sane_lists"],
        output_format="html5",
    )
    return html_body


def main():
    if len(sys.argv) != 5:
        print(f"用法: {sys.argv[0]} <md_file> <template_file> <html_file> <date>",
              file=sys.stderr)
        sys.exit(1)

    md_path = Path(sys.argv[1])
    template_path = Path(sys.argv[2])
    html_path = Path(sys.argv[3])
    today = sys.argv[4]

    # 读取 MD
    if not md_path.exists():
        print(f"❌ MD 文件不存在: {md_path}", file=sys.stderr)
        sys.exit(1)
    md_content = md_path.read_text(encoding="utf-8")

    # 读取模板
    if not template_path.exists():
        print(f"❌ 模板文件不存在: {template_path}", file=sys.stderr)
        sys.exit(1)
    template_str = template_path.read_text(encoding="utf-8")

    # MD → HTML
    html_body = convert_md_to_html(md_content)

    # 渲染模板：替换 __DATE__，注入 HTML
    template_str = template_str.replace("__DATE__", today)
    template = Template(template_str)
    html_content = template.render(CONTENT=html_body)

    # 校验
    errors = validate_html(html_content, md_content, today)
    if errors:
        for e in errors:
            print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    # 写入
    html_path.write_text(html_content, encoding="utf-8")

    # 诊断输出
    html_size = len(html_content.encode("utf-8"))
    md_size = len(md_content.encode("utf-8"))
    print(f"✅ HTML 渲染通过: {html_path} ({html_size} 字节, MD={md_size} 字节)")
    for tag in ["</html>", "</head>", "</body>"]:
        print(f"   ✓ {tag}")
    print(f"   ✓ 日期校验: {today}")


if __name__ == "__main__":
    main()
