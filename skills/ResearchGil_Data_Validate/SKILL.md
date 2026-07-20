---
name: ResearchGil_Data_Validate
description: 数据质量校验 — 检查 Gil 数据库所有表的最后更新时间、数据库文件损坏检测、字段缺失率与异常值检查。触发词：数据质量、数据校验、validate、数据库检查。
---

> ⚠️ **@deprecated (2026-07-07, 更新 2026-07-10)**: 此 Skill 的功能已被以下机制覆盖：
> - **compose_packages 契约校验**: 引擎内置 requires→provides 列级契约校验，拒绝缺失列，无需人工检查
> - **backtest_Gil 诊断**: `preview_period` 的 pipeline_diagnosis 输出各层计数+数据质量警告
> - **factor_compute.py 验证**: pandas 因子层已在真库验证出数（中位 ROE=5.13% 等基准对拍），无需逐表扫描
> 此文件保留至 2026-10-07 过渡期结束后删除。

# /ResearchGil_Data_Validate — 数据质量校验

## 角色定位

检查 Gil (聚源) DuckDB 数据库文件的完整性与数据质量，充当 Research Gil 流水线的质量门禁。位于 `ResearchGil_Data_Discover` 和 `ResearchGil_Factor_Test` 之间——Discover 产出 Dataset JSON 后，Validate 校验目标数据是否可用，防止脏数据进入因子计算和回测。

## 路由

- **首选**: data_Gil MCP Server（连接 Gil DuckDB 数据库）
- **回退**: Python DuckDB 库 (`import duckdb; duckdb.connect(path, read_only=True)`) — 当 MCP Server 不可用时自动回退
- 必须使用 `read_only=True` 模式连接，禁止任何写操作

## 输入格式

支持以下输入方式：

1. **数据库路径** (直接): `/path/to/db.duckdb`
2. **Dataset JSON** (来自 Discover): 解析 `db_path` 字段获取目标数据库
3. **目录扫描** (批量): 指定 Gil 数据根目录，自动扫描所有 `.duckdb` 文件

若用户未指定路径 → 扫描常见 Gil 数据目录（`~/Scholarship is a new sexy/` 下各子目录）

---

## 交互协议

### Step 1: 连通性验证

1. 确定目标数据库路径（用户指定 / Dataset JSON 解析 / 目录扫描）
2. 检查文件是否存在、文件大小是否 > 0
3. 检查是否存在残留 WAL 文件 (`<db>.wal`) — 可能表示未合并的写入
4. 尝试 `duckdb.connect(path, read_only=True)` 连接
5. 若连接失败 → 分类报告错误类型：
   - 文件不存在 → 检查路径
   - WAL 回放失败 → 🔴 致命: 数据库损坏，需修复
   - 权限不足 → 检查文件权限
6. 若连接成功 → 记录数据库文件路径、文件大小、表数量、行数

### Step 2: 表级最后更新时间扫描

1. 通过 `sqlite_master` 获取所有用户表列表
2. 逐表通过 `PRAGMA table_info` 获取列信息，自动识别日期列（匹配 `*date*`, `*time*` 模式，不区分大小写）
3. 对每个日期列执行 `SELECT MAX("<col>")`，取最新日期作为该表新鲜度
4. 对于无日期列的表 → 标记 `⚠️ 无日期列`，报告行数作为替代指标
5. 汇总输出「表名 → 最后日期 → 行数 → 列数」清单
6. 交叉对比: 若存在 Main/Stib 配对文件，对比两者的最后更新日期，标记落差 > 3 天的情况

### Step 3: 数据库完整性检查

1. 尝试 `PRAGMA integrity_check` — **注意: DuckDB 不完全支持此 PRAGMA**
2. 若 PRAGMA 不可用 → 回退方案: 逐表执行 `SELECT COUNT(*) FROM "<t>"`
   - 全表可读 = 数据库文件未损坏
3. 检查 WAL 文件状态:
   - WAL 文件存在且无法回放 → 🔴 致命
   - WAL 文件存在但数据库可读 → 🟡 警告（建议执行 CHECKPOINT 合并)
4. 抽样验证: 对前 5 张大表执行 `LIMIT 1` 查询，确保数据行可解析

### Step 4: 字段质量统计（可选深度模式）

1. 逐表统计关键字段的 NULL 占比（采样前 15 列）
2. 数值字段异常检测:
   - 负值检查（金融数据中负值可能无效，如 EPS/持股数为负需关注）
   - 极端值标记（如日期列出现 1991-01-01 等基准日期）
3. 类别字段取值分布检查（如 `secucode` NULL 率 > 80% → 🟡 警告）

### Step 5: 生成校验报告

1. 汇总所有检查结果，按严重程度分级：
   - 🔴 致命：数据库无法打开 / WAL 损坏 / 核心表不可读
   - 🟡 警告：长期未更新（>7 天） / 字段缺失率过高（>50%） / 无日期列 / Main-Stib 不同步
   - 🟢 正常：最后更新在 7 天内，所有检查通过
2. 输出结构化报告: 终端打印 + 可选保存为 MD/JSON
3. 报告统计摘要: 文件数 / 表数 / 致命数 / 警告数 / 正常数 / 总数据量

---

## 与其他 Skill 的勾稽关系

| 上游/下游 | Skill | 数据流 |
|-----------|-------|--------|
| 上游 | `ResearchGil_Data_Discover` | Discover 产出 Dataset JSON → Validate 解析 `db_path` 定位目标数据库 |
| 下游 | `ResearchGil_Factor_Test` | Validate 确认数据健康 → Factor_Test 加载已验证的数据集 |
| 下游 | `ResearchGil_Strategy_Backtest` | 间接依赖: 策略回测使用的因子数据质量由 Validate 保障 |
| 同级 | `EngineeringDataInfra_Healthcheck` | Validate 专注 Gil DuckDB 快速诊断; Healthcheck 覆盖跨数据源基建层通用检查 |

## 文件路径约定

| 角色 | 约定路径 | 说明 |
|------|----------|------|
| **输出** | `~/.gil_factors/validate_reports/{YYYY-MM-DD}_{db_name}.json` | 校验报告，含连通性/新鲜度/完整性/字段质量/汇总 |
| 可选输出 | `~/.gil_factors/validate_reports/{YYYY-MM-DD}_{db_name}.md` | --save-md 时产出 Markdown 报告 |
| 输入 | 用户指定路径 / Dataset JSON 中的 db_path / 目录扫描 | 目标 DuckDB 数据库 |

> 路径索引：`/Users/junye_shi/AgentFiles/SkillsRelationship_output/01_Research_Pipeline/02_Validate_Report/index.html`

## 禁止行为

- ❌ 对数据库执行任何写操作（INSERT/UPDATE/DELETE/DROP/CHECKPOINT）
- ❌ 跳过连通性验证直接进行表扫描
- ❌ 在未确认数据库路径时假定默认路径（需先向用户确认或扫描目录后报告发现）
- ❌ 仅依赖 `PRAGMA integrity_check` — DuckDB 不完全支持，必须追加全表可读验证
- ❌ 忽略 WAL 文件存在警告
- ❌ 修改数据库的任何表结构或索引
- ❌ 在 MCP Server 不可用时直接失败 — 应尝试 Python DuckDB 回退
