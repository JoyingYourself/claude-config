---
name: ExploreScholar_Report
description: 量化研究周度报告生成 — 综合全量分析结果，生成三部分递进结构周报（全景总结 + 35篇精要 + 5-8篇深度汇报），HTML+MD 双格式，不限篇幅。触发词：周报生成、研究报告、每周研报、research report。
---

# /ExploreScholar_Report — 量化研究周度报告生成

## 角色定位

研究报告生成器。综合本周扫描、筛选、深度分析、因子提取、回测验证的全量结果，生成四部分递进结构的综合周报（HTML + MD 双格式），**不设篇幅上限**。

## 与其他 Skill 的勾稽关系

```
上游输入（来自 Workflow Phase 1-5）：
  ├── classified_papers.json     ← 35 篇精选论文
  ├── paper_001_analysis.json    ← 每篇深度分析结果
  ├── extracted_factors.json     ← 提取的因子
  ├── replicable_factors.json    ← Gildata 可复现因子
  └── backtest results          ← 回测结果

ExploreScholar_Report（本 Skill）
    ↓
weekly_report.html + weekly_report.md（最终产出）
    ↓
DocumentObsidian_Vault + DocumentJournal_Daily（下游沉淀）
```

> 本 Skill 由 `PersonalResearch_PaperDigestWeekly` Workflow 的 Phase 6 调用。

## 报告结构（四部分 + 附录，不限篇幅）

### 第一部分：近期研究方向全景总结（~2000-3000 字）

由 Agent 综合本周 35 篇论文的发现，总结近期量化选股研究的整体趋势：
- 哪些因子类别是当前研究热点？
- 出现了哪些新的因子构造方法？
- 方法论层面有什么新的趋势？（如因果推断的应用）
- A股市场的独特发现与海外市场的差异
- 对当前策略组合的潜在影响

### 第二部分：35 篇论文核心成果精要（每篇 150-300 字）

按三大类分组：

```
├── 财务基本面因子（20 篇，EN 12 + ZH 8）
│   └── 每篇：[标题] [作者/年份] [核心发现] [因子构造] [关键结果] [A股复现价值评估]
├── 动量因子（10 篇，EN 6 + ZH 4）
│   └── ...
└── 另类数据因子（5 篇，EN 3 + ZH 2）
    └── ...
```

### 第三部分：重点论文深度汇报（5-8 篇）

选取标准：新颖性高 + 成果显著 + A股复现潜力大

每篇 ~1500-3000 字：
- 研究背景与动机
- 核心方法论（含关键公式）
- 实证结果（主表/图示数据复述）
- 与已有文献的关系
- A股复现方案（需要哪些 Gildata 字段、如何构造）
- 初步复现结果（如有）
- 建议：是否值得纳入策略模块

### 第四部分：复现执行结果

已执行回测的因子结果汇总表（IC 曲线、分层收益、DSR 通过情况）。

### 附录

- A. 全量扫描论文清单（标题/作者/来源/链接）
- B. 排除论文及原因（通过关键词但 LLM 判断不在范围内的）
- C. 本周扫描统计（各来源论文数、过滤率、分类分布）

## 执行流程

### Step 1: 汇总上游数据

从 Workflow 传递的中间文件中读取全量数据，包括：
- 全量扫描清单（merged_all.json）
- 关键词过滤结果（keyword_filtered.json）
- LLM 分类结果（classified_papers.json）
- 35 篇深度分析（analysis/paper_*.json）
- 因子提取结果（extracted_factors.json）
- 回测结果（backtests/）

### Step 2: Agent 生成报告内容

使用 `prompts/weekly_report.md` 作为系统提示，综合全部数据生成结构化报告 JSON。

### Step 3: 渲染输出

```bash
python3 scripts/render_report.py \
  --input /tmp/weekly_report.json \
  --output-dir "Weekly_ResearchReport/YYYY-MM-DD/" \
  --week "2026-W27"
```

产出文件：
- `weekly_report.html` — 自包含 HTML（深色主题，表格 + 图表）
- `weekly_report.md` — Markdown 纯文本版本

## 报告样式要求

- HTML 深色主题（`#0d1117` 背景）
- 自包含，无需外部 CSS/JS
- 表格清晰，数字右对齐
- 重点论文标记 ★★★ / ★★☆ / ★☆☆
- 回测结果含 IC 曲线（Base64 内嵌图表）
- 附录可折叠（`<details>` 标签）

## 交互协议

本 Skill 由 Workflow 自动调用。

当用户直接调用 `/ExploreScholar_Report` 时：
1. 要求用户提供输入数据目录路径
2. 执行数据汇总
3. Agent 生成报告 JSON
4. 渲染 HTML + MD
5. 返回报告路径

## 禁止行为

- ❌ 不要限制报告篇幅（任务要求"不限篇幅"）
- ❌ 不要跳过附录生成
- ❌ 不要在深度汇报中缩减公式（必须保留完整公式）
- ❌ 不要丢失任何一篇入选论文（35 篇必须全部出现在第二部分）
