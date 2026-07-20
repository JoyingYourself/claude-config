---
name: ResearchGil_Paper_Implement
description: 论文驱动多Agent复现 — 从论文化合中提取因子公式，自动映射 Gildata 字段，串联已有 Skill 链（Data_Discover → Factor_Test → Factor_Validate → Strategy_Backtest → Report_Performance）完成复现验证。触发词：论文复现、因子提取、paper implement、复现评估。
---

# /ResearchGil_Paper_Implement — 论文驱动多 Agent 因子复现

## 角色定位

论文因子复现引擎。从深度分析结果中提取可复现因子，自动映射到 Gildata 数据库字段，串联已有 ResearchGil_* Skill 链完成端到端回测验证。

## 与其他 Skill 的勾稽关系

```
上游输入：
  ├── paper_analysis（35 篇深度分析 JSON）
  └── classified_papers.json

ResearchGil_Paper_Implement（本 Skill）
    │
    ├── 因子提取（Agent：公式 → 变量 → 数据源 → 信号方向）
    ├── Gildata 字段映射（Agent：匹配 Gil 数据库字段）
    │
    └── 调用已有 Skill 链：
        ├── compose_packages (data_Gil)   ← 配方匹配→一键获取宽表 (替代 Data_Discover)
        ├── ResearchGil_Factor_Test       ← IC/IR/分层收益 (含RECIPES配方匹配)
        ├── ResearchGil_Factor_Validate  ← DSR + 三闸门
        ├── ResearchGil_Strategy_Backtest ← 策略组装回测
        └── ResearchGil_Report_Performance ← 绩效归因
```

> 本 Skill 由 `PersonalResearch_PaperDigestWeekly` Workflow 的 Phase 4-5 调用。

## 执行流程

### Step 1: 因子公式提取（Phase 4）

使用 `prompts/factor_extraction.md` 作为系统提示，从每篇论文的结构化分析中提取因子：

```json
{
  "factor_id": "FACTOR_2026W27_001",
  "factor_name": "Gross Profitability Premium",
  "source_paper": "arxiv:2506.12345",
  "formula": "GP / Total Assets",
  "formula_latex": "\\frac{GrossProfit}{TotalAssets}",
  "variables": [
    {
      "name": "GrossProfit",
      "definition": "营业收入 - 营业成本",
      "gil_field": "FS_IncomeStatement.gross_profit",
      "frequency": "quarterly"
    },
    {
      "name": "TotalAssets",
      "definition": "总资产",
      "gil_field": "FS_BalanceSheet.total_assets",
      "frequency": "quarterly"
    }
  ],
  "signal_direction": "positive",
  "universe": "A股全市场（剔除ST/金融/上市不满1年）",
  "rebalancing_freq": "monthly",
  "expected_ic": 0.03,
  "confidence": "high"
}
```

### Step 2: Gildata 字段映射（包匹配优先）

对每个提取的因子，自动匹配 Gildata 数据库字段：

**2a. 配方匹配（首选）**

1. 根据因子所需的字段类型（如 quality/value/growth/dividend），匹配 RECIPES 字典（见 ResearchGil_Factor_Test SKILL.md）
2. 调用 `data_Gil.list_packages()` 确认配方包可用
3. 调用 `data_Gil.compose_packages(package_ids, fin_date, mkt_date)` → 获得含所有需要的列的宽表
4. 从返回的 field_schema 确认因子变量对应的列名

**2b. 深度通道（回退）**

1. 因子变量名 → 搜索 `data_Gil.discover` 的字段列表
2. 确认字段存在于哪些表中（如 `FS_IncomeStatement`, `FS_BalanceSheet`）
3. 生成 `field_mapping.json`
   - ✅ **可直接复现**：所有字段在 Gil 中可直接使用
   - ⚠️ **需替代变量**：需要近似替代（如用其他指标替代缺失字段）
   - ❌ **无法复现**：关键字段缺失且无替代方案

### Step 3: 复现优先级排序

综合评分 = 可复现性 × 创新性 × 预期 IC：

| 维度 | 权重 | 评分标准 |
|------|:---:|------|
| 字段可用性 | 40% | 所有字段可直接使用=1.0, 需替代=0.5, 无法复现=0 |
| 方法创新性 | 30% | 全新方法=1.0, 改进已有=0.7, 应用性=0.4 |
| 预期 IC | 30% | IC>0.05=1.0, 0.03-0.05=0.7, <0.03=0.4 |

按评分降序排列，取前 8-15 个因子进入回测。

### Step 4: 串联回测 Skill 链（Phase 5）

对每个入选因子，依次调用：

```
ResearchGil_Data_Discover（确认字段存在）
    ↓
ResearchGil_Factor_Test（IC/IR/分层收益快速测试）
    ↓
ResearchGil_Factor_Validate（DSR + 三闸门防过拟合验证）
    ↓
ResearchGil_Strategy_Backtest（策略组装 + 完整回测）
    ↓
ResearchGil_Report_Performance（绩效归因报告）
```

### Step 5: 汇总复现结果

输出：
- `extracted_factors.json` — 所有提取的因子（15-25 个）
- `replicable_factors.json` — Gildata 可复现的因子（8-15 个）
- `field_mapping.json` — 因子 → Gildata 字段映射
- 每个已回测因子的绩效报告

## 结构化 Schema

### PAPER_ANALYSIS_SCHEMA

```json
{
  "paper_id": "string",
  "title": "string",
  "authors": ["string"],
  "year": "number",
  "core_finding": "string (≤200字)",
  "methodology": "string",
  "key_formulas": [{"latex": "string", "description": "string"}],
  "empirical_results": {
    "ic": "number|null",
    "ic_ir": "number|null",
    "long_short_spread": "string|null",
    "sample_period": "string"
  },
  "factors": [{
    "name": "string",
    "formula": "string",
    "variables": [{"name": "string", "definition": "string"}],
    "signal_direction": "positive|negative",
    "replicability_assessment": "high|medium|low|none",
    "a_share_adaptation": "string"
  }],
  "a_share_replication_value": "high|medium|low",
  "gil_field_mapping": [{"factor_variable": "string", "gil_field": "string", "availability": "direct|proxy|unavailable"}]
}
```

## 交互协议

本 Skill 由 Workflow 自动调用。

当用户直接调用 `/ResearchGil_Paper_Implement` 时：
1. 要求用户提供论文分析 JSON 路径
2. 执行因子提取
3. 执行 Gildata 字段映射
4. 询问是否执行回测（需确认 token 消耗）
5. 执行回测 Skill 链
6. 汇总结果

---

## 链式自动化协议（非交互模式）

为解决各 Skill 交互式设计阻断程序化调用的问题，Paper_Implement 通过**预填参数 JSON** 实现链式自动调用。

### 自动化调用约定

当从 Paper_Implement 调用下游 Skill 时，使用 `--batch` 参数 + 预填 JSON：

```
/ResearchGil_Data_Discover --batch '{
  "keywords": ["netoperatecashflow", ...],
  "fields": {"netoperatecashflow": "lc_cashflowstatementall", ...},
  "missing_policy": {"netoperatecashflow": "drop", ...},
  "aggregation": {"netoperatecashflow": "ttm", ...},
  "ttm_periods": 4,
  "additional_filters": "pe > 0",
  "fin_date": "2024-12-31",
  "mkt_date": "2024-12-31",
  "save_name": "paper_factor_001",
  "accept_stib_only": false,
  "accept_fast_mode": true
}'

/ResearchGil_Factor_Test --batch '{
  "dataset_path": "/Users/.../paper_factor_001.json",
  "expression": "rank(1/pe)",
  "start_date": "2020-01-01",
  "end_date": "2024-12-31",
  "factor_name": "paper_FACTOR_001",
  "board_scope": "all",
  "frequency": "monthly",
  "accept_defaults": true
}'

/ResearchGil_Strategy_Backtest --batch '{
  "name": "Paper Replication: FACTOR_001",
  "start_date": "2020-01-01",
  "end_date": "2024-12-31",
  "benchmark": "H00300",
  "dataset": "paper_factor_001",
  "factors": [{"name": "paper_FACTOR_001", "weight": 1.0}],
  "rebalance_months": [5, 11],
  "pools": {...},
  "output_dir": "/Users/.../paper_backtest_FACTOR_001",
  "skip_validation_check": false
}'
```

### 各 Skill 的 --batch JSON Schema

#### compose_packages / Data_Discover (--batch)

**首选（配方模式 · Phase 2 新增）**：
```json
{
  "recipe": "红利质量",
  "package_ids": ["BasicExtraction_latest", "QualityExtraction_ttm", "ValueExtraction_latest"],
  "fin_date": "2024-12-31",
  "mkt_date": "2024-12-31",
  "save_name": "paper_factor_001"
}
```

**回退（深度通道 · 仅配方不匹配时使用）**：
```json
{
  "keywords": ["string"],
  "fields": {"variable_name": "table.field"},
  "missing_policy": {"variable_name": "drop|fill_zero"},
  "aggregation": {"variable_name": "latest|ttm|yoy|none"},
  "ttm_periods": 4,
  "additional_filters": "pe > 0 AND pb > 0",
  "fin_date": "YYYY-MM-DD",
  "mkt_date": "YYYY-MM-DD",
  "save_name": "dataset_name",
  "description": "optional",
  "accept_stib_only": false,
  "accept_fast_mode": true
}
```

#### Factor_Test (--batch)

```json
{
  "dataset_path": "/absolute/path/to/dataset.json",
  "expression": "rank(1/pe)",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "factor_name": "factor_name_for_save",
  "board_scope": "all|exclude_bse|exclude_bse_stib",
  "frequency": "monthly|weekly",
  "industry_scope": "all",
  "fin_date_rule": "prev_trading_day",
  "mkt_date_rule": "prev_month_end",
  "accept_defaults": true
}
```

#### Strategy_Backtest (--batch)

```json
{
  "name": "strategy_name",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "benchmark": "H00300",
  "dataset": "dataset_name",
  "factors": [{"name": "factor_name", "weight": 1.0}],
  "rebalance_months": [5, 11],
  "cost_bps": 0.0,
  "pools": { ... full pool config ... },
  "output_dir": "/absolute/path",
  "skip_validation_check": false
}
```

### 链式调用的 Fallback 策略

| Skill | 执行方式 | 失败处理 | 超时处理 |
|-------|---------|---------|---------|
| compose_packages | MCP (≤3包) 或 `local_runner compose` | 跳过，已有 dataset 则复用 | 超时后 `ls -lt ~/.gil_datasets/` 查产物 |
| Factor_Test | **`local_runner.py test_factor`** | 标记 `skipped`，记录原因 | 无超时限制（本地 Python） |
| Factor_Validate | Python trials.db | 标记 `skipped: validate_unavailable` | — |
| Strategy_Backtest | `save_script` → 本地 .py 执行 | 🔴 阻止（accepted≠1 禁入）| 无超时限制（独立进程） |
| Report_Performance | MCP（快速查询） | 跳过，仅记录 IC 统计 | — |

---

## 禁止行为

- ❌ 不要跳过 Gildata 字段验证直接回测
- ❌ 不要在缺少关键字段时标记为"可直接复现"
- ❌ 不要跳过 Factor_Validate（DSR 验证）直接进入回测
- ❌ 不要对未通过三闸门验证的因子做策略回测
- ❌ --batch 模式下禁止弹出交互式确认（所有参数必须预填）
