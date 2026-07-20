---
name: ResearchGil_Factor_Test
description: 因子研究 — 数据字段发现、因子构造测试、因子库注册 (合并原 Data_Discover + Factor_Test + Factor_Validate)
---

# /ResearchGil_Factor_Test — 因子发现·测试·注册

## ⛔ 硬约束（每次执行前必读）

1. **禁止手写 Python 脚本**：因子 IC 测试、分层收益、多因子对比等所有计算，必须走 `local_runner.py`，不得手写自定义 .py 脚本
2. **禁止调 MCP factor_Gil 的长耗时工具**：test_factor / compare_factors / group_returns / correlation_matrix / ic_decay / turnover_analysis 一律走 runner
3. **MCP 仅用于快速操作**：list_packages, compose_packages (≤3包), load_dataset, save_factor

## 路由

**长耗时计算**: `local_runner.py` (本地 Python，无 30s 超时)
**快速操作**: `data_Gil` MCP (数据提取) + `factor_Gil` MCP (load/save)

runner 路径: `~/AgentFiles/ClaudeCode-MCP_related/local_runner.py`
用法: `python3 ~/AgentFiles/ClaudeCode-MCP_related/local_runner.py <task_type> <task_json_path>`
任务类型: test_factor, group_returns, compare_factors, correlation_matrix, ic_decay, turnover_analysis

## 文件路径约定

| 角色 | 路径 | 说明 |
|------|------|------|
| 因子库 | `~/.gil_factors/{name}.json` | 注册后的因子，供 Strategy_Backtest 消费 |
| 测试结果 | `~/.gil_factors/test_results/{name}.json` | test_factor 原始输出 |
| 数据集 | `~/.gil_datasets/{name}.parquet` | compose_packages 产出的 Parquet 数据集 |

## 前置条件

1. **先查因子库**：调用 `backtest_Gil.factor_registry.list_factors()` 检查因子是否已存在。已有且 status=PASS → 跳过测试，直接引用。
2. **优先配方匹配**：根据用户需求匹配 RECIPES 字典（见下方「📦 RECIPES 配方字典」），命中则直接 `compose_packages` → 获得 dataset_path。深度通道（discover→design→save）仅作回退。

## 交互协议（7 步，含强制约束）

### Step 1: 路由识别
- 用户需求是"新因子构造"还是"已有因子查询"？
- 已有因子 → 直接从因子库返回 IC/IR 摘要
- 新因子 → 继续以下步骤

### Step 2: 数据集获取（配方匹配优先）

**⚠️ 强制要求：数据集必须是 compose_packages 产出（含 sql 字段）。手动 enrich 的数据集（无 sql）不可用于 runner。**

**2a. 配方匹配（首选路径）**

1. 根据用户需求关键词（如"红利质量""价值低波""成长动量"），在 RECIPES 字典中匹配
2. 匹配逻辑：
   - 精确匹配：用户明确指定配方名 → 直接使用
   - 模糊匹配：用户描述需求 → 匹配 RECIPES 中 description 最相关的配方
   - 无匹配 → 进入 2b 深度通道
3. 调用 `data_Gil.list_packages()` 确认配方中的包均可用
4. **compose_packages 硬限制：每次 ≤3 包。** 超 3 包 MCP 必超时。需要更多字段时分批 compose 或复用已有 dataset
5. 调用 `data_Gil.compose_packages(package_ids, fin_date, mkt_date)` → 获得 dataset_path。**超时后必须先 `ls -lt ~/.gil_datasets/` 检查产物**：时间戳匹配 → 假报错直接用；无新文件 → 报告用户，禁止盲重试
6. **必须确认**：向用户展示匹配到的配方及对应包列表，确认后执行 compose
7. 若 compose 返回 field_schema → 展示可用字段清单及其中文名

**2b. 深度通道（回退，仅配方不匹配时使用）**

1. 用关键词调用 `data_Gil.discover(keywords)` 搜索可用字段
2. 展示候选字段表（中文名、单位、缺失率）
3. 如需理解字段含义 → 调用 `data_Gil.explain(keywords)`
4. 后续走 discover→design→save 完整流程（见 Data_Discover SKILL.md 协议）

### Step 3: 表达式确认
1. 用户给出因子表达式（如 `rank(1/pe_ttm_cut)`）
2. **必须检查**：表达式中引用的字段名是否在 COLUMN_TABLE_MAP 或 Dataset field_schema 中存在
3. 确认参数（区间、频率、IC方法、中性化）— 用户可回复"默认"一次性确认全部

### Step 4: 执行测试

**必须使用 local_runner.py，禁止手写 Python 脚本。**

```bash
# 1. 写 task.json
cat > /tmp/task.json << 'EOF'
{
  "name": "<因子名>",
  "dataset_path": "<Step 2 获得的 dataset JSON 路径>",
  "expression": "<Step 3 确认的表达式>",
  "start_date": "2020-01-01", "end_date": "2024-12-31",
  "frequency": "monthly", "board_scope": "exclude_bse",
  "ic_method": "rank_ic", "winsorize_method": "mad",
  "market_cap_neutralize": true,
  "output_path": "~/.gil_factors/test_results/{name}_result.json"
}
EOF

# 2. 执行
python3 ~/AgentFiles/ClaudeCode-MCP_related/local_runner.py test_factor /tmp/task.json

# 3. 读结果
cat ~/.gil_factors/test_results/{name}_result.json
```

其他任务类型同理替换 `test_factor` → `group_returns` / `compare_factors` / `correlation_matrix` / `ic_decay` / `turnover_analysis`。

### Step 5: 结果评判
按 4 级标准评判：

| 评判 | 条件 | 后续 |
|------|------|------|
| 🟢 PASS | IC |t|>2, IR>0.3, 多空 Sharpe>0.5, 胜率>55% | 可保存到因子库 |
| 🟡 REVISE | IC方向正确但显著性不足 | 建议调整构造方式后重测 |
| 🟠 RESCORE | 分层单调性差、IC不稳定 | 建议改用 rank() 或更换聚合方式 |
| 🔴 REJECT | IC≈0、多空不显著 | 因子无 alpha，不建议继续 |

### Step 6: 保存到因子库
- **仅 PASS 或 REVISE 可保存**
- 调用 `factor_Gil.save_factor(...)` → 自动写入 `~/.gil_factors/{name}.json` + 更新 index.json
- 因子库协议字段: name, label, expression, columns_needed, ic_stats, winsorize, neutralize, status
- **columns_needed 是关键**：告诉回测引擎需要加载哪些数据库列

### Step 7: 提示下游
- 因子已保存 → 展示 `run_pipeline` 可用的 factors 配置片段
- 提醒：因子可在 Strategy_Backtest 中通过 `"factors": {"{name}": {"expression": "..."}}` 引用

---

## 📦 RECIPES 配方字典

常用因子研究场景 → extraction 包组合。Agent 按需求关键词匹配，调用 `compose_packages(package_ids, fin_date, mkt_date)` 一键获取宽表。

**⚠️ MCP 超时警告**: Claude Code MCP 客户端硬编码 30s 超时。超过 3 个包的 compose_packages **必然超时**。
- 🟢 安全: "全市场基础"(3包) / "金融专项"(3包)
- 🔴 超时: "红利质量"(6包) / "价值低波"(4包) / "成长动量"(5包) / "质量筛选"(4包)
- 🔧 超时配方替代: 使用已有 parquet 数据集(`load_dataset`)或直接 Python 调用 `run_pipeline_from_config`

```python
RECIPES = {
    "红利质量": {
        "packages": ["BasicExtraction_latest", "QualityExtraction_ttm", "ValueExtraction_latest"],
        "description": "红利+质量因子核心底座: ROE_TTM/FCFY/EP/BP/DY。",
        "extras": ["QualityExtraction_ttm3(3Y波动率)", "DividendExtraction(分红)", "IndustryExtraction(行业)"],
        "factor_compute": ["compute_roe_ttm", "compute_fcfy", "compute_ep_bp_sp"],
    },
    "价值低波": {
        "packages": ["BasicExtraction_latest", "ValueExtraction_latest", "BasicMarket"],
        "description": "价值+低波因子: EP/BP/SP + 波动率/动量(引擎面板生成)。",
        "extras": ["IndustryExtraction(行业)"],
        "factor_compute": ["compute_ep_bp_sp"],
    },
    "成长动量": {
        "packages": ["BasicExtraction_latest", "GrowthExtraction_ttm", "BasicMarket"],
        "description": "成长+动量: 营收/净利/OCF 同比(compute_growth_yoy) + 动量(引擎面板生成)。",
        "extras": ["GrowthExtraction_ttm3(3Y CAGR)", "IndustryExtraction(行业)"],
        "factor_compute": ["compute_growth_yoy"],
    },
    "质量筛选": {
        "packages": ["BasicExtraction_latest", "QualityExtraction_ttm", "IndustryExtraction"],
        "description": "纯质量因子: ROE_TTM + 毛利率/净利率/资产周转率 + 应计项目。",
        "extras": ["QualityExtraction_ttm3(ROE 3Y均值/波动率)"],
        "factor_compute": ["compute_roe_ttm", "compute_margin", "compute_accruals"],
    },
    "金融专项": {
        "packages": ["BasicExtraction_latest", "FinancialExtraction", "IndustryExtraction"],
        "description": "金融行业专项: 银行拨备覆盖率/不良率/NIM/资本充足率。EAV透视引擎直接产出宽列。",
        "extras": [],
        "factor_compute": [],
    },
    "全市场基础": {
        "packages": ["BasicExtraction_latest", "ValueExtraction_latest", "IndustryExtraction"],
        "description": "全市场基础数据: 行业+上市天数+ST标记+PE/PB/DY/EV快照。因子测试最小底座。",
        "extras": [],
        "factor_compute": ["compute_ep_bp_sp"],
    },
}
```

> **扩展包使用规则**：需要 extras 中的字段时，先用核心 3 包 compose，再对 extras 单独 compose → pandas merge。不得一次性塞 >3 包。

**使用示例**：
```
用户: 帮我测 ROE 因子在红利质量策略中的效果
Agent: [匹配 "红利质量" 配方] 
       → compose_packages(["BasicExtraction_latest", "QualityExtraction_ttm", ...], "2024-05-17")
       → dataset: 30,534行×134列
       → 可用因子列: netprofit_parent_t0..t7, totalequity_t0..t7, ...
       → factor_compute.py: compute_roe_ttm(), compute_roe_3y(), compute_fcfy(), compute_dy_final()
```

---

## 表达式语法

**截面/算术算子**(test_factor 与 run_pipeline 同款 ExpressionEvaluator,均已实现):
- `rank(field)` — 横截面排名标准化 (0~1)
- `zscore(field)` — Z-score 标准化
- `winsorize(field, 0.01, 0.99)` — 分位数缩尾
- `where(cond, a, b)` — 向量化条件
- `1/field` / `a + b` / `a * b` / `abs` / `log` / `sqrt` — 算术

**逐期操作数(组合因子基元)**:除 field_schema 原始列外,可直接引用 `enrich()` **按需补齐**的
派生逐期列 —— `sq_roe_t0..t11`(单季ROE)、`roe_ttm_t*`、`roe_yoy_diff`、`fcfy`、`quality_zscore` 等。
test_factor / run_pipeline 取数后自动派生(决策12 单一事实源 factor_compute),**无需手写 Python**。

**写组合因子前先查目录**:调 `data_Gil.list_capabilities()` 看可用**算子**(single_quarter /
ttm / yoy_rel / yoy_abs / lag / zscore / pct_rank / winsorize)与**操作数**(sq_roe_t* 等 + 依赖包)。

**组合示例 —— SlopeROE(单季ROE同比变化的环比)**:相对变化算子 `(x_t0−x_t4)/abs(x_t4)` 复用两次:
```
((sq_roe_t0-sq_roe_t4)/abs(sq_roe_t4) - (sq_roe_t1-sq_roe_t5)/abs(sq_roe_t5)) / ((sq_roe_t1-sq_roe_t5)/abs(sq_roe_t5))
```
底座 = `质量筛选` 配方(含 QualityExtraction_ttm3 → netprofit_t*/totalequity_t*/enddate_t*)。
enrich 自动派生 sq_roe_t*,表达式一行完成。⚠️ 分母近零会爆炸/变号,真用套 winsorize 或改 abs 分母。
> 同一表达式在 run_pipeline 策略 config 的 `factors`(或因子库按名引用)中通用 —— 研究通过后
> save_factor 即可在通用回测里驱动打分。两条链共用同一富集与求值引擎。

字段名使用 compose_packages/field_schema 中的键名(小写),或 list_capabilities 的派生操作数名。

## 禁止行为

- ❌ **禁止手写 Python 脚本做因子测试**：所有计算走 local_runner.py，不得自己写 .py 文件
- ❌ **禁止调用 MCP `mcp__moor__factor_gil__test_factor`** 等长耗时工具：一律走 local_runner
- ❌ 替用户编写因子表达式
- ❌ 跳过因子库查重直接测试
- ❌ 检测到行业/板块字段时不询问范围
- ❌ 不保存 test_result 就提示进入下游
- ❌ 在 REJECT 状态下仍保存因子到因子库
- ❌ 绕过 COLUMN_TABLE_MAP 使用未注册的字段名
- ❌ 配方匹配可用时走深度通道（compose_packages 优先于 discover）

## 典型对话

```
用户: /ResearchGil_Factor_Test 帮我测 ROE 因子在红利策略中的效果

Claude: [查因子库] 因子库中未找到 "roe_ttm"。
        [配方匹配] "红利" → 匹配 RECIPES["红利质量"]
        配方包: BasicExtraction_latest + QualityExtraction_ttm + QualityExtraction_ttm3
               + ValueExtraction_latest + DividendExtraction + IndustryExtraction (6包)
        [compose_packages] → dataset: 30,534行×134列
        可用 ROE 相关列: netprofit_parent_t0..t7, totalequity_t0..t7
        建议表达式: rank(roe_ttm) — 由 factor_compute.py 预计算
        请确认？

用户: 确认，2020-01-01 ~ 2024-12-31，默认参数

Claude: [load_dataset + test_factor] IC mean=0.038, IR=0.71, t=2.9, win_rate=65%
        🟢 PASS — 因子有显著 alpha。
        是否保存为 "roe_ttm" 到因子库？

用户: 保存

Claude: [调用 save_factor] ✅ 已保存到 ~/.gil_factors/roe_ttm.json
        在 Strategy_Backtest 中引用: "factors": {"roe_ttm": {"expression": "roe_ttm"}}
```
```
用户: /ResearchGil_Factor_Test 帮我构造一个自定义因子：自由现金流/企业价值

Claude: [查因子库] 未找到。
        [配方匹配] "现金流+估值" → 匹配 RECIPES["红利质量"] (含 FCFY 相关字段)
        compose_packages → 可用列: operate_cf_ttm_t0..t7, capex_ttm_t0..t7, ev
        factor_compute.py 已预计算 fcfy = (operate_cf_ttm - capex_ttm) / ev
        可直接使用。是否用 rank(fcfy) 表达式测试？
```
