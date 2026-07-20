---
name: ResearchGil_Data_Discover
description: 数据发现与提取 — 通过 data_Gil MCP Server 理解需求、发现字段、制定查询方案
---

> ⚠️ **@deprecated (2026-07-07, 更新 2026-07-10)**: 此 Skill 已被 `compose_packages` + RECIPES 配方系统替代。
> - **首选**: 在 `ResearchGil_Factor_Test` 中通过 RECIPES 字典匹配配方 → `data_Gil.compose_packages(package_ids, fin_date)` 一键获取宽表
> - **深度通道**: 仅配方不匹配时，ResearchGil_Factor_Test Step 2b 回退到本 Skill 的 discover→design→save 流程
> - 配方系统覆盖 6 大场景（红利质量/价值低波/成长动量/质量筛选/金融专项/全市场基础），覆盖绝大多数因子研究需求
> 此文件保留至 2026-10-07 过渡期结束后删除。

# /ResearchGil_Data_Discover — 数据发现与提取

## 角色定位

**data_Gil 仅生成标准 SQL 模板，不执行数据提取。** 

- 日期使用 `{fin_date}` / `{mkt_date}` 占位符，而非硬编码日期
- 产出 Dataset JSON 包含：SQL 模板 + 字段 schema + 结构化占位符元数据
- 下游 factor_Gil / backtest_Gil 在实际执行时替换占位符为具体日期

## 路由

**仅使用 `data_Gil` MCP Server 的工具。** 不调用 factor_Gil 或 backtest_Gil。

可用工具: `explain` / `discover` / `plan` / `design` / `save` / `list_datasets`

## 与其他 Skill 的勾稽关系

| 上游/下游 | Skill | 数据流 |
|-----------|-------|--------|
| 上游（可选） | `ResearchGil_Data_Validate` | Validate 产出的校验报告（`~/.gil_factors/validate_reports/`）→ Discover 可选参考，辅助提示字段数据风险 |
| 下游 | `ResearchGil_Factor_Test` | Dataset JSON → Factor_Test 的 load_dataset() 入参 |
| 下游 | `ResearchGil_Strategy_Backtest` | Dataset JSON → Backtest 的数据底座 |

## 文件路径约定

| 角色 | 约定路径 | 说明 |
|------|----------|------|
| **输出** | `~/.gil_datasets/{name}.json` | save() 写入，{name} 由用户在 Step 4 指定 |
| 可选输入 | `~/.gil_factors/validate_reports/{YYYY-MM-DD}_{db_name}.json` | Data_Validate 产出，若存在则在 Step 1 展示字段时附带数据风险提示 |

> 路径索引：`/Users/junye_shi/AgentFiles/SkillsRelationship_output/01_Research_Pipeline/01_Dataset/index.html`

---

## 交互协议（逐层确认，禁止跳过）

### Step 1: 理解用户需求

用户提出变量需求（如 `/ResearchGil_Data_Discover ROE, 市盈率, 股息率`）后：

1. 调用 `explain(keywords=[...])` — 生成 Claude 推理 prompt
2. 调用 `discover(keywords=[...])` — 获取可用字段列表
3. **检测 STIB（科创板）覆盖**（必须执行，不可跳过）：
   - 对 discover 结果中涉及的所有表，检查是否存在 STIB 配对表
   - STIB 配对关系：`lc_mainindexnew` ↔ `lc_stibmaindata` | `lc_dindicesforvaluation` ↔ `lc_stibdindiforvalue` | `qt_performance` ↔ `lc_stibperformance` | `lc_cashflowstatementall` ↔ `lc_stibcashflowstate`
   - 逐个字段验证：**该字段在 STIB 配对表里是否存在？**
   - 若不存在，明确标注 🔴 科创板缺失，并说明影响
   - 若存在但字段名/单位不同，标注差异
   - **如果用户仅需主板数据，询问是否明确排除科创板**
4. **向用户展示并提问**：
   - 每个变量有哪些可选字段？（附缺失率、单位、STIB 覆盖）
   - 需要用户明确：选哪个表的哪个字段，是否接受仅主板覆盖

**禁止**: 替用户选择字段。必须列出选项后等待用户指定。禁止跳过 STIB 覆盖检查。

### Step 2: 制定查询方案

用户选定字段后：

1. 向用户确认：
   - 每个字段的**缺失值处理**：drop（剔除）还是 fill_zero（填0）？
   - 每个字段的**聚合方式**：latest（默认，取最新一期）/ ttm / yoy
     └─ 若选 ttm 或 yoy → 确认回溯期数（如 TTM 回溯 4 期单季度数据）

2. 调用 `plan(selections=[...])` 

3. **展示 plan 结果**：
   - 每张表的 PIT 列、主键、去重规则
   - **STIB 配对状态**：标注每张表的 STIB 配对表，以及字段在科创板是否可用
   - 关联路径
   - hints 和 warnings（特别注意主键含 enddate 的提示，以及 **STIB 字段覆盖不全的警告**）

4. **等待用户确认**方案是否正确。用户可能回复：
   - "认可" → 进入 Step 3，调用 `design(evaluation="认可", ...)`
   - "修订" → 调用 `design(evaluation="修订", ...)` 返回当前 PK 定义和表信息，供用户调整后重新确认

### Step 3: 生成 SQL 并预览

方案确认后：

1. 向用户确认：
   - 每张表的**主键定义**（可覆盖默认值）
   - 是否需要**附加过滤条件**（如 `pe > 0 AND pb > 0`）
   - **fin_date** 和 **mkt_date** 分别是什么
   - **是否接受数据仅覆盖主板？**（如 STIB 表缺字段，明确告知用户将仅返回主板数据，不含科创板）

2. 调用 `design(selections, primary_keys, fin_date, mkt_date, ...)`
   - `design` 已内置复杂度检测：3+ 表 / STIB UNION / TTM 聚合场景自动切换快速模式，跳过慢速预览，直接产出优化 SQL

3. **展示**：
   - SQL 语句（含 `{fin_date}` / `{mkt_date}` 占位符）
   - 预览数据（简单场景）或跳过预览提示（复杂场景）
   - 自动生成的建议命名

4. **等待用户确认**。用户可以选择"修订"回到 Step 2。

### Step 4: 保存

用户确认预览无误后：

1. **询问保存名称**（自动保存到 `~/.gil_datasets/`）：
   - 纯财务字段（仅含 `{fin_date}`）：建议 `{name}_fin`
   - 纯行情字段（仅含 `{mkt_date}`）：建议 `{name}_mkt`
   - 混合类型（两者都有）：建议 `{name}`
2. **询问数据集描述**（可选）

3. 调用 `save(sql, save_path, selections, primary_keys, description=..., ...)`

4. **告知用户**：
   - dataset_id 和完整路径
   - SQL 中使用的占位符列表（如 `{fin_date}`, `{mkt_date}`）
   - 占位符含义和 filter 类型（lte / eq）
   - **SQL 不包含实际日期，由下游 factor_Gil / backtest_Gil 替换后执行**

---

## 勾稽关系保障

`innercode`（股票标识）和 `changepct`（收益计算）由 SQL 生成层**自动注入**——用户无需手动选择，Dataset 的 field_schema 必定包含这两列，下游 `factor_Gil` / `backtest_Gil` 不会断链。

---

## ⚠️ design 工具已知行为

`design` 已内置复杂度检测。当涉及 3+ 表 / STIB UNION / TTM 聚合时，自动切换快速模式：
- 跳过 STIB UNION（仅主板）
- 跳过冗余 ROW_NUMBER（tradingday-eq 表）
- 跳过数据预览（避免慢速 SQL 执行）
- 直接产出优化 SQL

**无需手动处理**，`design` 自动决策。回调结果中的 `fast_mode: true` 表示快速模式已激活。

### 2. 跨表 JOIN 路径规则（构建 SQL 时必须遵守）

| 规则 | 说明 |
|------|------|
| **secumain 路径** | 必须使用 `BasicData.secumain`（**无引号，无 StockBasic_Main 前缀**） |
| **companycode → innercode 转换** | `JOIN BasicData.secumain s ON cf.companycode = s.companycode JOIN mkt ON s.innercode = mkt.innercode` |
| **子查询去重** | ⚠️ **仅 `enddate <= '{fin_date}'`(lte) 的表需要 ROW_NUMBER()**。`tradingday = '{mkt_date}'`(eq) 的表因主键唯一，**不需要去重**，直接 SELECT 即可 |
| **禁止 DISTINCT ON** | DuckDB 不支持 PostgreSQL 的 `DISTINCT ON` 语法，必须用 ROW_NUMBER() |
| **tradingday 过滤** | 使用 `= '{mkt_date}'`（精确匹配），因 mkt_date_rule 对应单日观察。**此类型表不需要 ROW_NUMBER() 去重** |
| **enddate 过滤** | 使用 `<= '{fin_date}'`（≤），取最新报告期。**此类型表必须 ROW_NUMBER() 去重** |
| **仅主板模式** | 涉及 3+ 表跨表 JOIN 时，优先排除科创板（告知用户），保证 SQL 可执行 |

### 3. 正确 SQL 模板（仅主板 + 财务表 + 估值/行情表）⚠️ 性能优化版

> **关键优化**：`tradingday = '{mkt_date}'` 的表 (lc_dindicesforvaluation, qt_performance) 不需要 ROW_NUMBER() 去重——主键 (innercode, tradingday) 保证唯一。去掉冗余窗口函数后，单次查询从 1.4s 降到 0.00s（400x 提升）。

```sql
-- 仅财务表需要 ROW_NUMBER 去重（enddate <= '{fin_date}' 可能返回多期）
WITH fin AS (
  SELECT companycode, <财务字段>
  FROM (
    SELECT companycode, <财务字段>,
      ROW_NUMBER() OVER (PARTITION BY companycode ORDER BY enddate DESC) AS _rn
    FROM StockFinace_Main."<财务表>"
    WHERE enddate <= '{fin_date}' AND <字段> IS NOT NULL
  ) _d WHERE _rn = 1
)
-- 估值表和行情表直接 JOIN，无需 CTE + ROW_NUMBER
SELECT v.<估值字段1>, v.<估值字段2>, ..., fin.<财务字段>, p.changepct, v.innercode
FROM StockMarket_Main."<估值表>" v
JOIN StockMarket_Main."qt_performance" p
  ON v.innercode = p.innercode AND v.tradingday = p.tradingday
JOIN BasicData.secumain s ON v.innercode = s.innercode
JOIN fin ON s.companycode = fin.companycode
WHERE v.tradingday = '{mkt_date}'
  AND v.<字段> IS NOT NULL
  AND p.changepct IS NOT NULL
JOIN BasicData.secumain s ON val.innercode = s.innercode
JOIN fin ON s.companycode = fin.companycode
```

### 4. save 前 SQL 自检清单（必须执行）

调用 save 前，逐项确认：
- [ ] SQL 中 `BasicData.secumain` 路径正确（不是 `StockBasic_Main."secumain"`）
- [ ] 无 `DISTINCT ON` 语法（全部用 `ROW_NUMBER()`）
- [ ] **`tradingday = '{mkt_date}'` 的表不包含 ROW_NUMBER() 去重**（冗余窗口函数使查询慢 400x）
- [ ] **`enddate <= '{fin_date}'` 的表包含 ROW_NUMBER() 去重**（取最新报告期）
- [ ] `innercode` + `changepct` 已自动注入（`_inject_mandatory_columns` 保证）
- [ ] 估值表+行情表直接 JOIN（不通过 CTE 嵌套，减少查询计划复杂度）
- [ ] 仅主板模式时，无 STIB UNION ALL 分支
- [ ] `{fin_date}` / `{mkt_date}` 占位符数量正确

### 5. TTM 聚合产生多行/股票

TTM 展开会按 enddate 产生多行，factor_Gil 无法处理。
- **替代方案**：优先使用 `latest` 聚合；若必须 TTM，在 SQL 层手动 SUM 后 GROUP BY 去重。

---

## 禁止行为

- ❌ 跳过任何一步
- ❌ 跳过 STIB 覆盖检查（必须核对每个字段在科创板配对表中是否存在）
- ❌ 在用户未确认时自动推进下一步
- ❌ 替用户选择字段、聚合方式、缺失值策略
- ❌ 在 plan 未确认时直接调用 design
- ❌ 在 design 未确认时直接调用 save
- ❌ 调用 factor_Gil 或 backtest_Gil 的工具

## 典型对话

```
用户: /ResearchGil_Data_Discover ROE 市盈率 股息率

Claude: [调用 explain + discover]
        找到以下可选字段：
        ROE: lc_mainindexnew.ROETTM (主板, 缺失率2.3%), lc_mainindexnew.ROE (主板,7.1%),
             lc_stibmaindata.ROE (科创板,4.65%) — ⚠️ ROETTM 科创板缺失
        股息率: lc_dindicesforvaluation.dividendratiolyr2 (主板,5.09%)
             — ⚠️ 科创估值表 lc_stibdindiforvalue 无此字段
        请选择每个变量使用的字段，是否接受仅主板覆盖？

用户: ROETTM, dividendratiolyr2（接受仅主板覆盖）

Claude: 缺失值处理？聚合方式？

用户: ROETTM: drop, ttm, 回溯6期。dividendratiolyr2: drop, latest

Claude: [调用 plan → 展示 PIT方案 + 主键 + 关联路径 + hints]
        确认方案？

用户: 确认

Claude: 主键定义？附加条件？fin_date和mkt_date？

用户: 默认主键，pe>0 AND pb>0，fin=2024-04-30, mkt=2024-06-28

Claude: [调用 design → 展示 SQL + 预览]
        命名建议: roettm_pe_pb_dividendratio。确认？

用户: 确认，保存到 /path/to/guoxin_value.json

Claude: [调用 save]
        ✅ 已保存: /path/to/guoxin_value.json
        占位符: {fin_date}(lte), {mkt_date}(eq)
        下游使用时替换占位符为实际日期即可执行。
```
