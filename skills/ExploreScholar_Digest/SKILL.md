---
name: ExploreScholar_Digest
description: 智能论文筛选与摘要 — 关键词白名单+黑名单双层过滤（零token），LLM三问审核按配额精选35篇（基本面20+动量10+另类5），生成分类摘要。触发词：论文筛选、论文摘要、学术筛选、paper digest。
---

# /ExploreScholar_Digest — 智能论文筛选与摘要

## 角色定位

双层过滤管道。第一层 Python 关键词过滤（零 token），从 300-500 篇中筛出 80-120 篇；第二层 LLM 三问审核，按因子大类分类并精选 35 篇（财务基本面 20 + 动量 10 + 另类数据 5，英文 60% / 中文 40%）。

## 与其他 Skill 的勾稽关系

```
ExploreScholar_Scan（上游：产出 merged_all.json）
    ↓
ExploreScholar_Digest（本 Skill：双层过滤 + 分类精选）
    ↓ classified_papers.json
Agent pipeline 深度分析（下游：每篇独立 Agent 分析）
```

> 本 Skill 由 `PersonalResearch_PaperDigestWeekly` Workflow 的 Phase 2 调用。

## 配置依赖

| 配置文件 | 用途 |
|---------|------|
| `config/scope_filter.yaml` | 白名单 ~80 词 + 黑名单 ~60 词 |
| `config/quotas.yaml` | 三类因子配额 + 语种配比 |

## 执行流程

### Step 1: 关键词过滤（Python，零 token）

```bash
python3 scripts/filter_keywords.py \
  --input /tmp/all_papers.json \
  --config config/scope_filter.yaml \
  --output /tmp/keyword_filtered.json
```

过滤逻辑：
- 标题 + 摘要中匹配白名单关键词 → 保留
- 标题 + 摘要中匹配黑名单关键词 → 排除
- 白名单优先级高于黑名单（既匹配白又匹配黑 → 保留）
- 目标：300-500 → 80-120 篇

白名单范围（~80 词）：
- 权益市场横截面收益预测（cross-section, stock return predictability, equity factor, anomaly）
- 选股因子（stock selection, trading signal, alpha, factor investing）
- A股/中国市场（A-share, Chinese stock market, China equity）
- 基本面/动量/另类数据关键词

黑名单范围（~60 词）：
- 衍生品定价（option pricing, futures pricing, derivatives）
- 固定收益（bond, credit default swap, sovereign debt, yield curve）
- 加密货币（cryptocurrency, bitcoin, blockchain）
- 宏观理论（DSGE, Taylor rule, monetary policy, inflation targeting）
- 高频做市（market making, HFT, order book, bid-ask spread）
- 银行监管（Basel, Solvency II, capital adequacy）
- 非权益资产（REITs, venture capital, private equity, real estate）

### Step 2: LLM 分类 + 三问审核

```bash
python3 scripts/classify_papers.py \
  --input /tmp/keyword_filtered.json \
  --prompt prompts/classify_filter.md \
  --output /tmp/classified_papers.json
```

对每篇通过关键词过滤的论文，Agent 回答：

1. **权益市场横截面收益预测？** (yes/no)
   - 核心发现是否涉及权益市场的横截面收益预测？
2. **可用财报/行情数据构建？** (yes/no)
   - 其因子/信号是否可以用财务报表或行情数据构建？
3. **中国A股有复现价值？** (yes/no)
   - 其方法论在中国A股市场是否有复现价值？

**仅当 3 个问题的答案均为 YES 时**，论文进入候选池。

### Step 3: 按配额精选 35 篇

| 因子大类 | 配额 | 英文 | 中文 | 优先级权重 |
|---------|:---:|:---:|:---:|:---:|
| **财务基本面因子** | 20 | 12 | 8 | 新颖性40% + 可复现性35% + 成果显著性25% |
| **动量因子** | 10 | 6 | 4 | 同上 |
| **另类数据因子** | 5 | 3 | 2 | 同上 |
| **合计** | **35** | **21** | **14** | |

选取优先级规则（在每类配额内排序）：
1. **新颖性**（40%）：2025-2026 年发表、因子构造方法创新
2. **可复现性**（35%）：数据源在 Gildata 中有对应字段、公式明确
3. **成果显著性**（25%）：IC/IR/Sharpe 等指标突出

### Step 4: 输出分类结果

输出 `classified_papers.json`，包含：
- 35 篇精选论文（按三大类分组的结构化数据）
- 每篇的三问审核结果
- 分类标签、语种、优先级评分
- 排除论文清单及排除原因

## 交互协议

本 Skill 由 Workflow 自动调用。

当用户直接调用 `/ExploreScholar_Digest` 时：
1. 要求用户提供输入 JSON 路径
2. 执行关键词过滤
3. 执行 LLM 分类审核
4. 汇报：各类入选/排除数量、语种分布
5. 返回 classified_papers.json 路径

## 禁止行为

- ❌ 不要跳过关键词过滤直接用 LLM（浪费 token）
- ❌ 不要擅自修改配额比例
- ❌ 不要在三问审核中降低标准（必须 3 个 YES）
- ❌ 不要在分类时混入排除范围的论文（衍生品/固收/加密货币/宏观等）
