---
name: skills
description: Skill 分类目录 — 自动发现并归类所有自定义 Skill，内置 Skill 折叠展示。触发词：/skills、skill目录、分类、所有skill、技能列表。
---

# /skills — Skill 分类目录

## 角色定位

自动发现当前会话中所有可用 Skill。**自定义 Skill 按分类架构展示，内置 Skill 收拢为辅助区。**

分类权威来源：`/Users/junye_shi/AgentFiles/skills-architecture.md`

---

## 输出格式

### 主展示区：自定义 Skill（按四域分类）

必须严格按以下分类展示所有 `Research*` `Engineering*` `Explore*` `Document*` 前缀的 Skill，**含完整说明**：

```
📊 量化研究 (Research)
   ResearchGil_Data_Discover        数据发现与提取 — Dataset JSON
   ResearchGil_Factor_Test          单因子检测 — IC/IR/分层收益/衰减
   ResearchGil_Strategy_Backtest     策略组装与回测 — 逐Pool配置→完整回测
   ResearchGil_Report_Performance    绩效归因 — Brinson/行业/持仓/图表

🔧 工程开发 (Engineering)
   EngineeringBacktest_Audit_Code    代码架构审查 — 6维度×3模式
   EngineeringSkill_Scaffold         Skill 脚手架 — 按架构规范创建新Skill

🔍 外部探索 (Explore)
   ExploreGitHub_Scholarship         GitHub 趋势分析 — 6阶段自动工作流

📝 知识沉淀 (Document)
   DocumentObsidian_Vault            Obsidian 策略知识库 — Canvas+演进树
   DocumentJournal_Daily             工作日志 — MD+HTML 双格式
```

### 辅助区：内置 Skill（紧凑列表）

在自定义 Skill 展示完毕后，以简洁的单行格式列出内置 Skill，按功能分组：

```
🛡️ 内置 — 代码质量: code-review / simplify / verify / security-review / review
🔧 内置 — 开发工具: init / run / claude-api
⚙️ 内置 — 配置: update-config / keybindings-help / loop / fewer-permission-prompts
🔍 内置 — 研究: deep-research
```

---

## 分类规则

自定义 Skill 按前缀自动归类：

| 前缀 | 分类 |
|------|------|
| `Research*` | 📊 量化研究 |
| `Engineering*` | 🔧 工程开发 |
| `Explore*` | 🔍 外部探索 |
| `Document*` | 📝 知识沉淀 |

内置 Skill 不参与前缀匹配，固定归入辅助区。

---

## 交互协议

1. 用户输入 `/skills`
2. Claude 从当前会话的 `<system-reminder>` 中提取完整 Skill 列表
3. 按分类规则归类：
   - 匹配 `Research*` / `Engineering*` / `Explore*` / `Document*` → 主展示区
   - 其余 → 辅助区（内置 Skill）
4. 先展示主展示区（完整信息），再展示辅助区（紧凑格式）
5. 展示完毕后，询问用户是否需要调用某个 Skill

---

## 禁止行为

- ❌ 硬编码 Skill 列表（每次从 `<system-reminder>` 动态读取）
- ❌ 将自定义 Skill 归入错误分类
- ❌ 内置 Skill 在辅助区外单独展开占篇幅
- ❌ 遗漏任何自定义 Skill
- ❌ 遗漏内置 Skill（辅助区必须列出全部）
