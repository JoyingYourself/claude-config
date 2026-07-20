#!/usr/bin/env python3
"""
render_report.py — 周报 JSON → HTML + MD 双格式渲染
深色主题，自包含 HTML，不限篇幅

用法:
  python3 render_report.py \
    --input /tmp/weekly_report.json \
    --output-dir "Weekly_ResearchReport/2026-07-05/" \
    --week "2026-W27"
"""

import argparse
import json
import os
import sys
from datetime import datetime


def render_html(report: dict, week: str) -> str:
    """Render report JSON to self-contained HTML with dark theme"""

    # Escape helper
    def esc(text: str) -> str:
        if not text:
            return ""
        return (text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;"))

    parts = []
    parts.append(f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>量化研究周度论文报告 — {week}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans SC', sans-serif;
    background: #0d1117; color: #c9d1d9; line-height: 1.7;
    max-width: 1100px; margin: 0 auto; padding: 40px 24px;
  }}
  h1 {{ color: #58a6ff; font-size: 2em; border-bottom: 2px solid #30363d; padding-bottom: 16px; margin-bottom: 24px; }}
  h2 {{ color: #f0883e; font-size: 1.5em; margin-top: 40px; margin-bottom: 16px; border-left: 4px solid #f0883e; padding-left: 12px; }}
  h3 {{ color: #d2a8ff; font-size: 1.2em; margin-top: 24px; margin-bottom: 10px; }}
  h4 {{ color: #7ee787; font-size: 1.05em; margin-top: 16px; }}
  p {{ margin: 8px 0; }}
  table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 0.9em; }}
  th {{ background: #161b22; color: #58a6ff; padding: 10px 12px; text-align: left; border: 1px solid #30363d; }}
  td {{ padding: 8px 12px; border: 1px solid #30363d; }}
  tr:nth-child(even) {{ background: #161b22; }}
  tr:hover {{ background: #1c2129; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .metric-pos {{ color: #3fb950; }}
  .metric-neg {{ color: #f85149; }}
  .tag {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; margin: 2px; }}
  .tag-high {{ background: #238636; color: #fff; }}
  .tag-mid {{ background: #9e6a03; color: #fff; }}
  .tag-low {{ background: #6e7681; color: #fff; }}
  .star-3 {{ color: #f0883e; }}
  .star-2 {{ color: #d2a8ff; }}
  .star-1 {{ color: #8b949e; }}
  .panel {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin: 16px 0; }}
  .paper-entry {{ border-left: 3px solid #30363d; padding: 12px 16px; margin: 8px 0; background: #0d1117; }}
  .paper-entry.fundamental {{ border-left-color: #58a6ff; }}
  .paper-entry.momentum {{ border-left-color: #f0883e; }}
  .paper-entry.alternative {{ border-left-color: #7ee787; }}
  .highlight {{ background: #1c2129; border: 1px solid #30363d; border-radius: 8px; padding: 24px; margin: 20px 0; }}
  .highlight h4 {{ margin-top: 0; }}
  details {{ margin: 12px 0; }}
  summary {{ cursor: pointer; color: #58a6ff; padding: 8px 0; }}
  summary:hover {{ color: #79c0ff; }}
  .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin: 16px 0; }}
  .stat-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; text-align: center; }}
  .stat-value {{ font-size: 2em; color: #58a6ff; font-weight: bold; }}
  .stat-label {{ font-size: 0.85em; color: #8b949e; margin-top: 4px; }}
  .formula {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 16px 20px; margin: 12px 0; overflow-x: auto; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.95em; }}
  hr {{ border: none; border-top: 1px solid #30363d; margin: 32px 0; }}
  .toc {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px 24px; margin: 16px 0; }}
  .toc a {{ color: #58a6ff; text-decoration: none; }}
  .toc a:hover {{ text-decoration: underline; }}
  .toc ul {{ list-style: none; padding-left: 16px; }}
</style>
</head>
<body>
""")

    # Title
    parts.append(f'<h1>📊 量化研究周度论文报告 — {week}</h1>')
    parts.append(f'<p style="color:#8b949e;">生成时间：{report.get("generated_at", "")}</p>')

    # TOC
    parts.append('<div class="toc"><h3>📑 目录</h3><ul>')
    parts.append('<li><a href="#part1">第一部分：近期研究方向全景总结</a></li>')
    parts.append('<li><a href="#part2">第二部分：35 篇论文核心成果精要</a></li>')
    parts.append('<li><a href="#part3">第三部分：重点论文深度汇报</a></li>')
    parts.append('<li><a href="#part4">第四部分：复现执行结果</a></li>')
    parts.append('<li><a href="#appendix">附录</a></li>')
    parts.append('</ul></div>')

    # Stats grid
    stats = report.get("stats", {})
    parts.append('<div class="stat-grid">')
    parts.append(f'<div class="stat-card"><div class="stat-value">{stats.get("total_scanned", "N/A")}</div><div class="stat-label">全量扫描</div></div>')
    parts.append(f'<div class="stat-card"><div class="stat-value">{stats.get("keyword_filtered", "N/A")}</div><div class="stat-label">关键词过滤后</div></div>')
    parts.append(f'<div class="stat-card"><div class="stat-value">{stats.get("llm_selected", 35)}</div><div class="stat-label">LLM精选</div></div>')
    parts.append(f'<div class="stat-card"><div class="stat-value">{stats.get("factors_extracted", "N/A")}</div><div class="stat-label">因子提取</div></div>')
    parts.append(f'<div class="stat-card"><div class="stat-value">{stats.get("factors_backtested", "N/A")}</div><div class="stat-label">已完成回测</div></div>')
    parts.append('</div>')

    # Part 1: Panoramic Summary
    parts.append('<h2 id="part1">第一部分：近期研究方向全景总结</h2>')
    summary = report.get("part1_summary", "")
    if summary:
        for para in summary.split("\n\n"):
            para = para.strip()
            if para:
                parts.append(f"<p>{esc(para)}</p>")
    else:
        parts.append('<p style="color:#8b949e;">（待 Agent 生成）</p>')

    # Part 2: 35 Paper Summaries
    parts.append('<h2 id="part2">第二部分：35 篇论文核心成果精要</h2>')

    categories = [
        ("fundamental", "财务基本面因子", "20 篇 (EN 12 + ZH 8)"),
        ("momentum", "动量因子", "10 篇 (EN 6 + ZH 4)"),
        ("alternative", "另类数据因子", "5 篇 (EN 3 + ZH 2)"),
    ]

    paper_summaries = report.get("part2_summaries", {})
    for cat_key, cat_label, cat_quota in categories:
        cat_papers = paper_summaries.get(cat_key, [])
        parts.append(f'<h3>📁 {cat_label} <span style="font-size:0.7em;color:#8b949e;">({cat_quota})</span></h3>')
        if cat_papers:
            for p in cat_papers:
                a_share_val = p.get("a_share_replication_value", "medium")
                tag_class = "tag-high" if a_share_val == "high" else "tag-mid" if a_share_val == "medium" else "tag-low"
                parts.append(f'''<div class="paper-entry {cat_key}">
  <strong>{esc(p.get("title", ""))}</strong><br>
  <span style="color:#8b949e;">{esc(", ".join(p.get("authors", [])[:3]))} ({p.get("year", "")})</span>
  <span class="tag {tag_class}">A股复现：{a_share_val}</span>
  <p style="margin-top:6px;">🔍 {esc(p.get("core_finding", ""))}</p>
  <p>📐 因子：{esc(p.get("factor_construction", ""))}</p>
  <p>📊 结果：{esc(p.get("key_results", ""))}</p>
</div>''')
        else:
            parts.append('<p style="color:#8b949e;">（待 Agent 生成）</p>')

    # Part 3: Deep Dives
    parts.append('<h2 id="part3">第三部分：重点论文深度汇报（5-8 篇）</h2>')
    deep_dives = report.get("part3_deep_dives", [])
    if deep_dives:
        for i, dd in enumerate(deep_dives):
            stars = dd.get("stars", 3)
            star_str = "★★★" if stars >= 3 else "★★☆" if stars == 2 else "★☆☆"
            star_class = "star-3" if stars >= 3 else "star-2" if stars == 2 else "star-1"
            parts.append(f'<div class="highlight">')
            parts.append(f'<h4><span class="{star_class}">{star_str}</span> {esc(dd.get("title", ""))}</h4>')
            parts.append(f'<p style="color:#8b949e;">{esc(", ".join(dd.get("authors", [])[:5]))} ({dd.get("year", "")}) — {esc(dd.get("source", ""))}</p>')

            for section in ["background", "methodology", "empirical_results", "literature_relation",
                           "a_share_replication_plan", "preliminary_results", "recommendation"]:
                content = dd.get(section, "")
                if content:
                    section_labels = {
                        "background": "📖 研究背景与动机",
                        "methodology": "⚙️ 核心方法论",
                        "empirical_results": "📊 实证结果",
                        "literature_relation": "📚 与已有文献的关系",
                        "a_share_replication_plan": "🇨🇳 A股复现方案",
                        "preliminary_results": "🔬 初步复现结果",
                        "recommendation": "💡 建议",
                    }
                    parts.append(f'<h4>{section_labels.get(section, section)}</h4>')
                    for para in content.split("\n\n"):
                        para = para.strip()
                        if para:
                            parts.append(f"<p>{esc(para)}</p>")

            # Render formulas if present
            formulas = dd.get("key_formulas", [])
            if formulas:
                for f_item in formulas:
                    if isinstance(f_item, dict):
                        parts.append(f'<div class="formula">{esc(f_item.get("latex", ""))}<br><span style="color:#8b949e;">{esc(f_item.get("description", ""))}</span></div>')
                    else:
                        parts.append(f'<div class="formula">{esc(str(f_item))}</div>')

            parts.append('</div>')
    else:
        parts.append('<p style="color:#8b949e;">（待 Agent 生成）</p>')

    # Part 4: Backtest Results
    parts.append('<h2 id="part4">第四部分：复现执行结果</h2>')
    backtest_results = report.get("part4_backtest_results", [])
    if backtest_results:
        parts.append('<table><thead><tr>'
                     '<th>因子名</th><th>来源论文</th><th>IC均值</th><th>ICIR</th>'
                     '<th>分层收益(多-空)</th><th>DSR通过</th><th>状态</th>'
                     '</tr></thead><tbody>')
        for br in backtest_results:
            ic_val = br.get("ic_mean", 0)
            ic_class = "metric-pos" if ic_val > 0 else "metric-neg"
            dsr_pass = "✅" if br.get("dsr_passed") else "❌"
            parts.append(f'<tr>'
                         f'<td>{esc(br.get("factor_name", ""))}</td>'
                         f'<td style="font-size:0.85em;">{esc(br.get("source_paper", "")[:60])}...</td>'
                         f'<td class="num {ic_class}">{ic_val:.4f}</td>'
                         f'<td class="num">{br.get("ic_ir", 0):.2f}</td>'
                         f'<td class="num">{br.get("long_short_spread", "N/A")}</td>'
                         f'<td style="text-align:center;">{dsr_pass}</td>'
                         f'<td>{esc(br.get("status", ""))}</td>'
                         f'</tr>')
        parts.append('</tbody></table>')
    else:
        parts.append('<p style="color:#8b949e;">（无回测结果 或 待执行）</p>')

    # Appendix
    parts.append('<hr><h2 id="appendix">附录</h2>')

    # A: Full scan list
    parts.append('<details><summary><strong>A. 全量扫描论文清单</strong></summary>')
    appendix_a = report.get("appendix_a_full_list", [])
    if appendix_a:
        parts.append('<table><thead><tr><th>#</th><th>标题</th><th>作者</th><th>来源</th><th>链接</th></tr></thead><tbody>')
        for i, p in enumerate(appendix_a, 1):
            parts.append(f'<tr><td>{i}</td><td>{esc(p.get("title", "")[:80])}</td>'
                         f'<td>{esc(", ".join(p.get("authors", [])[:2]))}</td>'
                         f'<td>{esc(p.get("source", ""))}</td>'
                         f'<td><a href="{esc(p.get("url", "#"))}" target="_blank">链接</a></td></tr>')
        parts.append('</tbody></table>')
    else:
        parts.append('<p style="color:#8b949e;">（待填充）</p>')
    parts.append('</details>')

    # B: Excluded papers
    parts.append('<details><summary><strong>B. 排除论文及原因</strong></summary>')
    appendix_b = report.get("appendix_b_excluded", [])
    if appendix_b:
        parts.append('<table><thead><tr><th>标题</th><th>排除原因</th><th>来源</th></tr></thead><tbody>')
        for p in appendix_b:
            parts.append(f'<tr><td>{esc(p.get("title", "")[:80])}</td>'
                         f'<td>{esc(p.get("exclude_reason", ""))}</td>'
                         f'<td>{esc(p.get("source", ""))}</td></tr>')
        parts.append('</tbody></table>')
    else:
        parts.append('<p style="color:#8b949e;">（待填充）</p>')
    parts.append('</details>')

    # C: Statistics
    parts.append('<details><summary><strong>C. 本周扫描统计</strong></summary>')
    stats_c = report.get("appendix_c_stats", {})
    if stats_c:
        parts.append('<table><thead><tr><th>指标</th><th>数值</th></tr></thead><tbody>')
        for k, v in stats_c.items():
            parts.append(f'<tr><td>{esc(str(k))}</td><td>{esc(str(v))}</td></tr>')
        parts.append('</tbody></table>')
    else:
        parts.append('<p style="color:#8b949e;">（待填充）</p>')
    parts.append('</details>')

    # Footer
    parts.append(f'<hr><p style="text-align:center;color:#484f58;font-size:0.85em;">'
                 f'Generated by ResearchGil_WeeklyPaperDigest Workflow | {week}</p>')

    parts.append('</body></html>')
    return "\n".join(parts)


def render_markdown(report: dict, week: str) -> str:
    """Render report JSON to Markdown"""
    lines = []
    lines.append(f"# 量化研究周度论文报告 — {week}")
    lines.append(f"\n> 生成时间：{report.get('generated_at', '')}\n")

    stats = report.get("stats", {})
    lines.append(f"| 阶段 | 数量 |")
    lines.append(f"|------|------|")
    lines.append(f"| 全量扫描 | {stats.get('total_scanned', 'N/A')} |")
    lines.append(f"| 关键词过滤后 | {stats.get('keyword_filtered', 'N/A')} |")
    lines.append(f"| LLM精选 | {stats.get('llm_selected', 35)} |")
    lines.append(f"| 因子提取 | {stats.get('factors_extracted', 'N/A')} |")
    lines.append(f"| 已完成回测 | {stats.get('factors_backtested', 'N/A')} |")
    lines.append("")

    # Part 1
    lines.append("## 第一部分：近期研究方向全景总结")
    lines.append(report.get("part1_summary", "（待生成）"))
    lines.append("")

    # Part 2
    lines.append("## 第二部分：35 篇论文核心成果精要")
    paper_summaries = report.get("part2_summaries", {})
    for cat_key, cat_label in [("fundamental", "财务基本面因子"), ("momentum", "动量因子"), ("alternative", "另类数据因子")]:
        lines.append(f"### {cat_label}")
        for p in paper_summaries.get(cat_key, []):
            lines.append(f"- **{p.get('title', '')}** — {', '.join(p.get('authors', [])[:3])} ({p.get('year', '')})")
            lines.append(f"  - 核心发现：{p.get('core_finding', '')}")
            lines.append(f"  - 因子构造：{p.get('factor_construction', '')}")
            lines.append(f"  - 关键结果：{p.get('key_results', '')}")
            lines.append(f"  - A股复现价值：{p.get('a_share_replication_value', '')}")
        lines.append("")

    # Part 3
    lines.append("## 第三部分：重点论文深度汇报")
    for dd in report.get("part3_deep_dives", []):
        stars = "★★★" if dd.get("stars", 3) >= 3 else "★★☆" if dd.get("stars", 3) == 2 else "★☆☆"
        lines.append(f"### {stars} {dd.get('title', '')}")
        lines.append(f"\n{dd.get('background', '')}\n")
    lines.append("")

    # Part 4
    lines.append("## 第四部分：复现执行结果")
    lines.append("| 因子名 | 来源论文 | IC均值 | ICIR | 分层收益 | DSR通过 | 状态 |")
    lines.append("|--------|---------|--------|------|---------|---------|------|")
    for br in report.get("part4_backtest_results", []):
        lines.append(f"| {br.get('factor_name', '')} | {br.get('source_paper', '')[:40]} | "
                     f"{br.get('ic_mean', 0):.4f} | {br.get('ic_ir', 0):.2f} | "
                     f"{br.get('long_short_spread', 'N/A')} | "
                     f"{'✅' if br.get('dsr_passed') else '❌'} | {br.get('status', '')} |")
    lines.append("")

    # Appendix
    lines.append("## 附录")
    lines.append("### A. 全量扫描论文清单")
    lines.append(f"共 {len(report.get('appendix_a_full_list', []))} 篇")
    lines.append("### B. 排除论文及原因")
    lines.append(f"共 {len(report.get('appendix_b_excluded', []))} 篇")
    lines.append("### C. 本周扫描统计")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Render weekly report to HTML + MD")
    parser.add_argument("--input", required=True, help="Input JSON (weekly_report.json)")
    parser.add_argument("--output-dir", required=True, help="Output directory for HTML and MD files")
    parser.add_argument("--week", default="", help="Week label (e.g., 2026-W27)")
    args = parser.parse_args()

    # Load report JSON
    with open(args.input) as f:
        report = json.load(f)

    week = args.week or report.get("week", f"{datetime.now():%Y-W%W}")

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Render HTML
    html_content = render_html(report, week)
    html_path = os.path.join(args.output_dir, "weekly_report.html")
    with open(html_path, "w") as f:
        f.write(html_content)

    # Render MD
    md_content = render_markdown(report, week)
    md_path = os.path.join(args.output_dir, "weekly_report.md")
    with open(md_path, "w") as f:
        f.write(md_content)

    print(f"Report rendered:", file=sys.stderr)
    print(f"  HTML: {html_path} ({len(html_content):,} bytes)", file=sys.stderr)
    print(f"  MD:   {md_path} ({len(md_content):,} bytes)", file=sys.stderr)
    print(json.dumps({"status": "ok", "html": html_path, "md": md_path}))


if __name__ == "__main__":
    main()
