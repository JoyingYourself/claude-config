---
name: ResearchGil_Report_Performance
description: 绩效归因与报告 — 通过 report_Gil MCP Server 加载回测结果、绩效汇总、归因分析、生成图表
---

> ⚠️ **@deprecated (2026-07-07)**: 此 Skill 的绩效报告功能已嵌入 `run_pipeline` 工具中。回测完成后自动生成 QuantStats HTML 报告 + nav CSV + 逐年收益。请使用 `/ResearchGil_Strategy_Backtest`，报告随回测一步输出。
> `report_Gil` MCP Server 的工具 (summarize/analyze_holdings/run_brinson/generate_charts) 仍可作为独立分析工具使用。
> 此文件保留至 2026-10-07 过渡期结束后删除。

# /ResearchGil_Report_Performance — 绩效归因与报告

## 路由

**仅使用 `report_Gil` MCP Server 的工具。** 不调用 data_Gil / factor_Gil / backtest_Gil。

可用工具: `load_backtest_result` / `summarize` / `run_brinson` / `analyze_industry` / `analyze_holdings` / `generate_charts`

## 与其他 Skill 的勾稽关系

| 上游/下游 | Skill | 数据流 |
|-----------|-------|--------|
| 上游 | `ResearchGil_Strategy_Backtest` | backtest 输出目录（nav + pool CSV）→ 本 Skill |
| 上游 | `ResearchGil_Factor_Validate` | trials.db 记录（因子验证状态）→ 交叉验证回测表现 |
| 同级 | `DocumentJournal_Daily` | 回测结论 → 工作日志 |

## 文件路径约定

| 角色 | 约定路径 | 说明 |
|------|----------|------|
| **输出 1** | `~/.gil_backtests/{name}/charts/` | generate_charts() 写入的图表文件 |
| **输出 2** | `~/.gil_factors/backtest_memory.md` | 决策记忆追加（Phase A 假设 + Phase B 结算） |
| 输入 1 | `~/.gil_backtests/{name}/` | Strategy_Backtest 产出的回测输出目录（nav_history.csv + benchmark_nav.csv + pool_counts.csv） |
| 输入 2 | `~/.gil_factors/trials.db` | Factor_Validate 产出的因子验证状态（交叉验证用） |

> 路径索引：`/Users/junye_shi/AgentFiles/SkillsRelationship_output/01_Research_Pipeline/06_Performance/index.html`

---

## 前置条件

用户必须先通过 `/ResearchGil_Strategy_Backtest` 完成回测执行，产出 backtest 输出目录（含 pool CSV + nav CSV）。

---

## 交互协议

### Step 1: 加载回测结果

1. **询问 backtest 输出目录路径**
2. 调用 `load_backtest_result(output_dir)`
3. **展示摘要**：回测期数、日期范围、已发现的 pool 目录

### Step 2: 绩效汇总

1. 调用 `summarize()`
2. **展示**：累计收益、最大回撤、逐年收益、基准对比

### Step 3: 归因分析（询问用户要哪些）

1. `run_brinson()` — 行业归因分解
2. `analyze_industry()` — 行业配置
3. `analyze_holdings()` — 个股常驻

### Step 4: 图表生成（可选）

1. 调用 `generate_charts(output_dir)`
2. 告知图表保存路径

### Step 5: 诊断与反思（TradingAgents Memory Log 模式）

1. **性能退化诊断**（如果 IS/OOS 数据可用）：
   - 对比回测区间收益 vs 后续一段时间的实际收益（如已有）
   - 计算退化率：`OOS Sharpe / IS Sharpe`
   - 退化率 > 0.5 → 🟢 健康；0~0.5 → 🟡 边际；< 0 → 🔴 过拟合

2. **策略稳定性诊断**：
   - 逐年 Sharpe 的一致性（可用性高 → 策略稳定）
   - 逐年收益方向一致率（正收益年份占比 > 60% → 稳健）

3. **记忆追加**（TradingAgents 两阶段模式）：
   - **Phase A — 记录假设**：在 `~/.gil_factors/backtest_memory.md` 追加一条记录：
     ```
     [{date} | {strategy_name} | {sharpe:.2f} | pending]
     DECISION: {strategy config}
     EXPECTATION: {为什么这个策略应该有效}
     ```
   - **Phase B — 延迟结算**（下次运行同策略时）：对比实际表现 vs 预期

4. **给出评判**（PASS / MONITOR / SUNSET）：

| 评判 | 条件 | 建议 |
|------|------|------|
| 🟢 **PASS** | Sharpe>0.5, 超额>年化3%, 最大回撤<25%, 逐年为正>60% | 可进入实盘/纸交易 |
| 🟡 **MONITOR** | Sharpe 0~0.5, 超额正但不显著 | 继续观测，3个月后复盘 |
| 🔴 **SUNSET** | Sharpe<0, 超额为负, 逐年为正<40% | 建议弃用或大幅修改 |

---

## 禁止行为

- ❌ 未加载 backtest 结果就调用分析工具
- ❌ 跳过绩效汇总直接做归因
- ❌ 调用其他 Server 的工具

## 注意事项

- `load_backtest_result` 接受仅有净值数据（无 pool 子目录）的回测输出
- 空仓回测（0 持仓）的 `summarize` 正常返回 0% 收益，不会崩溃
- QuantStats 报告在组合收益为常数时无法生成（需至少一个非零收益日）

## 典型对话

```
用户: /ResearchGil_Report_Performance /path/to/backtest_output/

Claude: [调用 load_backtest_result]
        加载成功: 54 期, 2020-03 ~ 2024-12
        可用 pools: pool_0, pool_5

        === 绩效汇总 ===
        累计: +85.3% vs HS300 +32.1% | 超额: +53.2%
        最大回撤: -18.5%
        逐年: ...

        需要哪些归因分析？ Brinson / 行业 / 持仓 / 全部？

用户: 全部

Claude: [调用 run_brinson + analyze_industry + analyze_holdings]
        展示结果。是否生成图表？

用户: 是

Claude: [调用 generate_charts] 图表已保存。
```
