---
name: ResearchGil_Strategy_Backtest
description: 策略回测与绩效报告 — 通过 backtest_Gil MCP Server 一键回测+报告 (合并原 Strategy_Backtest + Report_Performance)
---

# /ResearchGil_Strategy_Backtest — 策略回测·报告

## 路由

**强制使用 `backtest_Gil` MCP Server 的 run_pipeline / preview_period 工具。**
禁止绕过 pipeline 直接写 SQL 或手动组装 DataFrame。

可用工具: `run_pipeline` / `preview_period` / `list_modules` / `save_script`

## 与其他 Skill 的勾稽关系

| 上游/下游 | Skill | 数据流 |
|-----------|-------|--------|
| 上游 | `ResearchGil_Factor_Test` | 因子库 JSON → 策略回测的 factors 配置 |
| 下游 | (无) | run_pipeline 内嵌报告生成，无需单独 Report Skill |

## 文件路径约定

| 角色 | 路径 | 说明 |
|------|------|------|
| 因子库 | `~/.gil_factors/{name}.json` | 因子注册信息 |
| 回测输出 | 用户指定 output_dir | nav CSV + QuantStats HTML |

## 前置条件

1. **因子必须在因子库中注册**（通过 ResearchGil_Factor_Test），或在 config.factors 中以内联表达式声明。
2. 运行 `list_modules` 了解 8 个可用预置模块。
3. 硬编码基础设施（DuckDB 引擎、回测引擎等）由 MCP 自动处理，**Agent 不得手动干预**。

## 交互协议（5 步，含强制约束）

### Step 1: 信息收集
一次性收集以下信息：
- 策略名称
- 回测区间（start_date / end_date）
- 基准代码（默认 H00300）
- 调仓月份（默认 [3,6,9,12]）
- 交易摩擦 bps（默认 0）

### Step 2: 因子引用
1. 从因子库 index.json 展示可用因子（名、IC_IR、状态）
2. 用户选择因子 + 权重
3. config.factors 示例: `{"ep": {"expression": "1/pe_ttm_cut"}, "fcfy_1y": {"expression": "fcf_ttm_t0/ev"}}`

### Step 3: 模块选择
1. 调用 `list_modules` 展示 8 个预置模块及其参数说明：

| 模块 | 功能 |
|------|------|
| `filter_basic` | 板块过滤 + 上市天数 + ST剔除 + 流动性 + TTM利润 |
| `filter_quality_roe` | ROE均值/波动/同比 两阶段递进筛选 |
| `filter_quality_fcfy` | FCFY筛选 (非金融) |
| `filter_fin_sector` | 金融专项 (银行拨备/保险EV/券商杠杆) |
| `score_zscore_combo` | 分组 zscore 加权打分 |
| `weight_method` | 权重分配 (exp_decay / factor_proportional / equal) |
| `constraints` | 个股权重上限 + 行业集中度 + 换手率 |
| `dividend_method` | 股息率计算 (direct / expected_dps_fy_fallback) |

2. 用户选择模块 + 填参数。**必须优先使用预置模块**，仅当预置模块确实无法覆盖时才允许 `custom_filter`。
3. 展示完整 config JSON（人类可读格式）→ 等待用户确认。

### Step 4: 预览
1. **调用前检查**：`ps aux | grep backtest_Gil/server` — 若 CPU >100% 且运行时间 >1min，说明另一窗口正在跑回测，报告用户等待或 kill
2. 调用 `preview_period(config, date=...)` 展示单期 pool 计数
3. 检查诊断输出：
   - 若某层 drop 率 > 90% → 警告用户并建议放宽参数
   - 若 pool_5 = 0 → **必须**要求用户调整条件，不得继续
4. 用户确认后执行完整回测。

### Step 5: 执行 + 导出
1. 调用 `run_pipeline(config, output_dir=...)` 执行完整回测
2. **超时后**：`ls -lt <output_dir>/` 检查是否有 nav CSV / QuantStats HTML 生成 → 有则假报错直接用
3. 展示结果：累计收益、基准收益、超额收益、最大回撤、逐年收益、QuantStats 报告路径
4. 可选：调用 `save_script(config, path)` 导出独立 .py 脚本

---

## 强制约束（不可违反）

1. **必须使用 run_pipeline**：禁止 Agent 绕过 MCP 直接写 SQL 或手动组装 pandas DataFrame。
2. **必须使用预置模块**：在预置模块能覆盖的场景下，禁止使用 custom_filter。custom_filter 仅用于预置模块无法覆盖的边缘情况。
3. **必须预览**：preview_period 输出 pool_5=0 时，必须让用户调整参数，不得直接执行完整回测。
4. **因子必须注册**：config.factors 中的因子必须存在于因子库或以内联表达式声明。禁止引用不存在的因子名而不警告。
5. **不接受简化**：所有计算逻辑由 MCP Layer 1 硬编码基础设施精确执行，Agent 不得手动近似或跳过任何步骤。

## 禁止行为

- ❌ 绕过 run_pipeline 直接写 SQL 或手动组装数据
- ❌ 在预置模块可覆盖时使用 custom_filter
- ❌ 跳过 preview_period 直接执行完整回测
- ❌ 替用户决定筛选阈值（如 ROE 分位值）
- ❌ pool_5=0 时继续执行
- ❌ 手动计算净值或绩效指标（必须用 MCP 内置引擎）
- ❌ 调用 data_Gil 或 factor_Gil 的工具（数据加载由 pipeline 内部自动完成）

## 典型对话

```
用户: /ResearchGil_Strategy_Backtest 中邮价值1号

Claude: 回测区间？基准？调仓月份？
用户: 2012-12-31 ~ 2026-05-31, H00300, [3,6,9,12]

Claude: [查因子库] 可用因子: ep(IR=0.82), fcfy_1y(IR=0.55), dy(IR=0.48)
        请选择因子及权重？

用户: ep(0.5) + fcfy_1y(0.5)

Claude: [list_modules] 请选择预置模块并设参数：
        filter_basic → board_scope=exclude_bse ✅
        filter_quality_roe → roe_mean_q=0.30, roe_std_q=0.70 ✅
        ...

用户: [逐一确认]

Claude: [展示完整 config JSON] → 确认？

用户: 确认

Claude: [preview_period] pool_0=5132 → filter_basic=3890 → ... → pool_5=50 ✅
        预览正常，是否执行完整回测？

用户: 是

Claude: [run_pipeline] ✅ 回测完成。
        累计 +385.2% vs HS300 +108.3%, 超额 +277.0%
        最大回撤 -32.1%, QuantStats: /path/to/report.html
```
