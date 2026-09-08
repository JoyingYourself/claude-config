---
name: engineering
disable-model-invocation: true
---

# /engineering — 用户调用 Skill 路由

你是**用户调用**的 Router Skill。用户输入 `/engineering` 查看所有需要手动触发的 Skill。

## 路由表

以下 Skill 均为**用户调用**——Agent 不会自动触发，需用户显式输入名称或 `/` 命令：

### 中邮资管

| 输入 | Skill | 用途 |
|------|-------|------|
| `ChinapostAMC_StrategyOrder` | 策略下单 | 选股→调仓→池比对→下单模板 |

> ⚠️ 实盘汇报为脚本：`bash ~/中邮资管/工作文件依赖项/中邮产品实盘报告/定稿一页通报告脚本/run_all.sh`（一键六报告，2 产品 × 3 基准；旧一代 update_factsheet.py 已于 2026-08-20 归档至 `_archive/废弃脚本_20260820/`，勿再调用）

### 文档

| 输入 | Skill | 用途 |
|------|-------|------|
| `DocumentJournal_Daily` | 工作日志追加 | 对话历史→结构化日志 MD+HTML |
| `DocumentJournal_Review` | 日志回顾 | 前3日日志→待完成项→实现思路 |
| `DocumentObsidian_Vault` | Obsidian 知识层 | 策略脚本+回测→可编辑 Vault |

### 学术

| 输入 | Skill | 用途 |
|------|-------|------|
| `ExploreScholar_Digest` | 论文筛选摘要 | 关键词过滤→LLM三问审核→35篇精选 |
| `ExploreScholar_Report` | 周度研报 | 全景总结+精要+深度汇报 |
| `ExploreScholar_Scan` | 论文扫描 | 四源并行抓取→300-500篇池 |

### 工程 + 探索

| 输入 | Skill | 用途 |
|------|-------|------|
| `EngineeringSkill_Validate` | Skill 校验 | 穿行测试+自动更新公告 |
| `EngineeringTask_Plan` | 任务规划 | 生成 README + HTML 规划报告 |
| `ExploreGitHub_Scholarship` | GitHub 趋势分析 | 三级分层扫描→深度项目报告 |
| `ResearchGil_Paper_Implement` | 论文复现 | 公式提取→Gildata映射→回测验证 |
| `skills` | Skill 目录 | 所有 Skill 分类视图 |

---

## 哪些 Skill 是自动的（模型调用）

以下 Skill Agent 会根据你的自然语言**自动发现和触发**，无需手动输入：

- **工程**: `EngineeringCoding_Audit`, `EngineeringFrame_Audit`, `EngineeringMCP_Scaffold`, `EngineeringSkill_Scaffold`, `EngineeringTask_LongTask`, `EngineeringTask_PhaseGate`
- **研究**: `ResearchGil_Factor_Test`, `ResearchGil_Factor_Validate`, `ResearchGil_Factor_Combine`, `ResearchGil_Strategy_Backtest`, `ResearchGil_Report_Performance`, `ResearchGil_Data_Discover`, `ResearchGil_Data_Validate`
