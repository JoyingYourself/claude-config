---
name: ChinapostAMC_FactsheetUpdate-DividendQuality
description: 红利质量策略实盘汇报一键更新 — 自动拉取估值表/聚源指数/行业分类/市场风格数据，更新第2页8个数据区域。触发词:/update-dividend、更新红利质量实盘报告
---

# /ChinapostAMC_FactsheetUpdate-DividendQuality — 红利质量策略实盘汇报更新

## 角色定位

为"中邮资管红利质量量化选股策略资产管理产品"的实盘汇报 HTML 执行一键数据更新。

- 第1页（策略介绍 + 回测绩效）：**固定不动，永不修改**
- 第2页（实盘运行情况）：**8 个 AUTO-BEGIN/END 标记区域自动替换**

运行 `update_factsheet.py` 脚本，自动从估值表 Excel、聚源 DuckDB、东方财富 API 拉取最新数据。

## 路由

无 MCP Server 依赖。使用 Bash 工具执行 Python 脚本。依赖本地环境：Python 3.13、openpyxl、duckdb、numpy、akshare。

## 输入格式

用户直接调用，无需上游数据输入。脚本自动扫描以下路径：

| 数据 | 路径 |
|------|------|
| 估值表 | `/Users/junye_shi/中邮资管/中邮金市/target_list/产品净值/中邮红利质量/` |
| 聚源指数 | `~/Scholarship is a new sexy/指数数据/IndexMarket.duckdb` |
| 聚源基本信息 | `~/Scholarship is a new sexy/Gildata_SecuCategory1&41_DuckDB/BasicData.duckdb` |
| HTML 模板 | `/Users/junye_shi/中邮资管/中邮金市/2026/红利质量路演材料/红利质量策略_实盘汇报.html` |
| 脚本 | `/Users/junye_shi/中邮资管/工作文件依赖项/中邮产品实盘报告/DividendQuality/update_factsheet.py` |

## 文件管理规范

每次更新自动执行：

1. **命名格式**：`【产品名称】回测及实盘情况汇报【生成日期】.html`
   - 示例：`【中邮红利质量】回测及实盘情况汇报【2026-07-19】.html`
2. **输出位置**：`/Users/junye_shi/中邮资管/中邮金市/2026/红利质量路演材料/`
3. **归档规则**：写入新报告前，自动将路演材料目录下所有旧 `【*】回测及实盘情况汇报【*】.html` 移入 `往期报告/` 子目录
4. **模板保护**：`红利质量策略_实盘汇报.html`（含 AUTO 标记的模板）不会被归档，每次从模板读取后写入新文件

---

## 交互协议

### Step 1：预检

执行预检，展示估值表和聚源数据的最新日期：

```bash
python3 /Users/junye_shi/中邮资管/工作文件依赖项/中邮产品实盘报告/DividendQuality/update_factsheet.py --dry-run
```

**输出解读**：
- 估值表文件数 + 最新日期 + 净值 → 判断估值表是否已到
- 聚源数据最新交易日 → 判断聚源是否更新
- HTML 标记数量（应为 16）→ 判断报告完整性
- 预检不通过 → 逐项报告具体问题和修复建议 → 等待用户确认后修复

**关键判断**：
- 若估值表最新日期早于聚源最新日期超过 2 天 → ⚠️ 提醒用户估值表可能缺失
- 若预检通过且估值表日期 = 上次更新日期 → 提示"数据无变化，是否仍要更新？"

### Step 2：确认执行

向用户汇报预检结果，格式：

```
🔍 预检报告
   估值表: N 份, 最新 YYYY-MM-DD (净值 X.XXXX)
   聚源数据: 最新交易日 YYYY-MM-DD
   HTML 标记: 16 个 ✅
   
   数据状态: [估值表已更新/无新数据] | [聚源已更新/滞后X天]

确认执行更新？
```

用户确认后进入 Step 3。

### Step 3：执行更新

```bash
python3 /Users/junye_shi/中邮资管/工作文件依赖项/中邮产品实盘报告/DividendQuality/update_factsheet.py
```

捕获 stdout 输出，提取关键信息向用户汇报：

```
✅ 更新完成
   净值日: YYYY-MM-DD | 报告日: YYYY-MM-DD
   产品累计: +X.XX% | 基准累计: +X.XX%
   行业最高: XX (XX%)
   市场风格: [大盘/小盘]占优 | [价值/成长]占优
```

### Step 4：异常处理

| 异常 | 处理方式 |
|------|---------|
| 估值表目录为空 | 提示"估值表未到，请检查邮件"，不执行更新 |
| 聚源 DuckDB 无法连接 | 提示"聚源数据库被锁定，请关闭其他进程后重试" |
| HTML 标记缺失 | 报告缺失的标记名称，提示"请检查第2页 HTML 是否被误改" |
| 脚本报错退出 | 完整输出 Python traceback，定位错误行和原因 |

---

## 与其他 Skill 的勾稽关系

| 上游/下游 | Skill | 数据流 |
|-----------|-------|--------|
| 同级 | `ChinapostAMC_StrategyOrder` | 无直接数据流，同属中邮资管业务域 |
| 同级 | `ChinapostAMC_FactsheetUpdate-ValueOne` | 同模块，脚本结构一致，独立运行 |

## 禁止行为

- ❌ 修改第 1 页 HTML 内容（第 1 页不含 AUTO 标记，已定稿）
- ❌ 手动编辑 HTML 中 AUTO 标记区域的内容（应通过脚本更新）
- ❌ 修改 `update_factsheet.py` 的 CONFIG 字典中的路径（除非用户明确要求）
- ❌ 删除或修改 HTML 中的 `<!-- AUTO-BEGIN: xxx -->` 和 `<!-- AUTO-END: xxx -->` 标记
- ❌ 在预检未通过时强制执行更新
- ❌ 跳过预检步骤直接执行脚本
