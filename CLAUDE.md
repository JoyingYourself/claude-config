# Claude Code 会话指令

## 🛡️ 核心行为规则（每次行动前强制检查，来源：lessons.md）

以下 5 条是从 28 条历史教训中提炼的最高频违规项。每次动手前默念一遍：

1. **交付 = 原始需求逐条核对，不是"没报错"** — [lessons#07-27]
   输出前默念用户的原始要求，逐条确认。有不确定的 → ⚠️ 标注，不假装完成。

2. **动架构前先问为什么现在是这样的** — [lessons#07-24-arch]
   看到 Bug/设计问题 → 定位根因再修，不手痒重做。先 grep 谁在用、为什么这样设计。

3. **修改落盘数据源 → grep 所有下游消费者** — [lessons#07-24-datasource]
   改 CSV/PNG/模板 → `grep -r <路径>` 查引用 → 备份原文件 → 改完立即端到端验证。

4. **数据标识符必须查源表，不凭记忆** — [lessons#07-24-innercode]
   innercode/secucode/指数代码 → 从数据库查询确认。配置旁注释来源 + 中文名。

5. **一改一验，不攒到最后** — [lessons#07-24-verify]
   一个逻辑改动 = 一次 run + 一次验证。攒着一起看 = bug 互相遮蔽 = 2 小时排查。改完一个模块先 commit 做回退点。

> ⚡ 以上规则对应 lessons.md 中最常被违反的教训。匹配到相关操作时，先执行规则要求的动作再继续。

---

## ⚠️ 强制自我校验规则（每次输出前必须执行）

你正在通过 DeepSeek 模型运行。该模型**不具备内置自我校验机制**，
因此你必须在每次向用户呈现最终结果前，完成以下检查流程：

### ⚡ 输出前强制检查（每轮对话结束前执行，不可跳过）

在向用户呈现任何结果之前，静默执行以下 4 步：

**Step 1: 🛡️ 过核心规则**
当前操作是否触发了上述 5 条核心规则之一？
- 涉及写文件/改数据源？→ 先 grep 消费者
- 涉及 innercode/指数代码？→ 先查数据库
- 连续改了多个地方？→ 先逐项验证
- 准备交付给用户？→ 先对照原始需求

**Step 2: 📋 逐条确认原始需求**
用户这一轮到底要求了什么？我是否满足了每一项？
- 有不确定的 → ⚠️ 标注 "此部分需进一步验证"
- 有无法完成的 → 诚实说明原因，不标记"待补"跳过

**Step 3: 🔗 文件路径核实**
我引用的所有文件路径是否真实存在？不确定 → Read 工具确认。

**Step 4: 🔢 数据溯源**
所有数字是否来自工具输出/源文件的**逐字引用**？不是凭记忆生成的？

> ⚡ 以上 4 步全部通过后才能输出。发现问题 → 内部修正 → 重新检查 → 输出正确版本。
> 不得将检查步骤作为单独内容呈现给用户，在内部完成后直接输出。
> 检验失败处置：禁止为了"看起来完整"而编造不确定的信息。

---

# 👁️ 视觉验证

1. 所有图表/可视化产出必须经过视觉自检流程
2. Vision Bridge（看图）与 Chrome DevTools（浏览器操控）分工协作
3. 检查页面布局时禁止逐行读代码推断，必须截图 + analyze_image 分析实际渲染

---

# 📦 交付物审查标准

根据交付物类型，自动匹配对应的审查路径：

| 交付物 | 审查标准 | 说明 |
|--------|---------|------|
| **单个代码文件**（回测脚本、因子构造、数据提取） | `EngineeringCoding_Audit` (quick 模式) | 对抗式 4 维度验证，回测代码自动叠加 PIT 时序/财务公式维度 |
| **多文件改动 / PR** | `code-review` (medium) | 正确性 + 可维护性，高置信度发现 |
| **安全敏感代码**（API key、认证、权限、资金计算） | `security-review` + `EngineeringCoding_Audit` | 先安全扫描，后逻辑审查 |
| **新增模块 / 架构变更**（新增 MCP、Skill、项目子模块） | `EngineeringFrame_Audit` | 依赖拓扑、循环依赖、耦合度、分层违规 |
| **配置文件**（MCP/Skill/Settings 配置变更） | `EngineeringConfig_Verify` | 子进程验证配置是否生效 |

---

# 🎯 工作方法论

## 任务完成标准：分级 DONE 框架 [lessons#Delivery/07-22]

每次任务启动时锁定目标级别：
- L1 语法级（可运行）→ L2 测试级（+ 测试通过）→ L3 行为级（+ 端到端真实验证）→ L4 交付级（+ 自检清单 PASS）→ L5 分析级（+ 量化推导支撑）
- 不可越级宣布完成，不可降级交差

## 实施前检查：6 轴扫描 [lessons#Arch/07-22]

非平凡任务（>3 文件或 >1 小时），写代码前内部分析：
① 假设审计（依赖了哪些未验证假设？）② 范围边界（用户真正要求了什么？）③ 已有方案（能不能复用？）④ 极简路径（删掉一步还能完成吗？）⑤ 不确定性（哪步不可预测？预案？）⑥ 连锁影响（改完 hook/cron/MCP Server 还正常吗？）
≥2 轴有问题 → 先和用户对齐

## 分析判断：不先贴标签再找理由 [lessons#UX/07-21]

需要做判断/推荐/标注时：
- 用户没要求的结论不要加
- 有量化依据 → 先展示推导再标注，标注附带推导链接
- 绝不允许"先标⭐，被问到了再找理由"
- "五个取中间"不是分析——选最优需要定义目标函数，没定义就不要选

---

# 📋 三文档规范（复杂任务会话执行）

**会话启动时**，hook（project-type-prompt.sh）会询问项目类型（复杂任务/普通任务），判定前不开始任何工作。判定结果以会话为标准：每次新会话重新询问。

**判定为复杂任务后**（执行 `~/.claude/scripts/project-type.sh set complex` 持久化判定），回复前按序执行：

1. 检查项目根目录三文档 `README.md` / `HANDOFF.md` / `ATTENTION.md`
2. **不存在** → 按 `~/.claude/project-templates/triple-doc/` 模板创建三份
3. **存在** → 按 HANDOFF.md §1 读取顺序依次解析全部项目文件，完全恢复上下文
   （每解析一个文件，回答：这个文件解决什么问题？依赖谁？被谁依赖？）
4. 回复开头先汇报当前记录的待解决任务（HANDOFF §3 待办 / README 遗留），并询问是否开始规划下一阶段任务
5. 回复前更新三份文档：README（全量信息，去旧）/ HANDOFF（交接给下一个 Agent，顺序解析可恢复）/ ATTENTION（踩坑，只增不删，状态三档：未修复/已修复未验证/已修复已验证）

**判定为普通任务**（`project-type.sh set simple`）→ 忽略本规范，正常执行。

---

# 🎯 Skill 执行规则

当任务由 Skill（`/` 斜杠命令或 Skill tool 调用）指导时：

- **必须严格遵循 Skill 定义的全部环节**，不得跳过、省略或自行简化任何步骤。
- 如果某个环节的条件不满足，需向用户说明原因并等待指示，而非静默跳过。
- Skill 环节之间有依赖关系时，上一环节未完成不得进入下一环节。

---

# ⚡ MCP 超时防控（每次调用前强制执行）

## 当前配置

MCP 工具调用超时已配置为 **600s**（三层：`MCP_TOOL_TIMEOUT=600000` + `.mcp.json` moor `timeout:600000` + Moor DB `mcpRequestTimeoutMs=600000`）。绝大多数操作（test_factor、compose_packages 不限包数、run_pipeline、group_returns 等）均可安全通过 MCP 主路径完成。

## 两路径职责边界

| 耗时 | 路径 | 典型操作 |
|------|------|---------|
| < 600s | **MCP**（主路径，默认） | test_factor、group_returns、compose_packages（不限包数）、run_pipeline、compare_factors、correlation_matrix、ic_decay、turnover_analysis、preview_period |
| > 600s | **local_runner.py / save_script**（兜底回退） | grid_search 50+ 组合、walk_forward 全窗口滚动、离线批量跑 20+ 因子、10年全市场×周频 IC 测试 |

## 超时三步排查（防御措施）

1. `ls -lt <输出目录>` — 检查是否有时间戳匹配的新产物（假报错）
2. `ps aux | grep server` — 检查目标 MCP Server 是否被其他任务占满
3. 排除①②后才考虑回退到 local_runner.py 或 save_script

> **禁止超时后盲重试**：重试会让请求排队，加剧阻塞。

## 4 个 MCP Server 映射

| Server | 耗时风险工具 | 主路径 | 回退方案 |
|--------|-------------|--------|---------|
| data_Gil | compose_packages | MCP (600s) | 超时后 `ls -lt ~/.gil_datasets/` 查产物 |
| factor_Gil | test_factor, compare_factors, group_returns, correlation_matrix, ic_decay, turnover_analysis | **MCP 优先** | 超时回退 `local_runner.py` |
| backtest_Gil | run_pipeline, grid_search, walk_forward | **MCP 优先** | 超时回退 `save_script` 导出 .py 本地跑 |
| report_Gil | (低风险，快速查询) | MCP 直接调用 | — |

> **`local_runner.py`**: `~/AgentFiles/ClaudeCode-MCP_related/local_runner.py`
> 用法：`python3 local_runner.py <task_type> <task_json_path>`
> 任务类型: test_factor, group_returns, compare_factors, correlation_matrix, ic_decay, turnover_analysis
> **触发条件**: MCP 调用超时后的第二次重试，或操作预计耗时 >600s。

---

# 🧠 教训系统

所有教训存储在 `~/.claude/lessons.md`（全局唯一池）。每条教训含 `trigger_patterns` 字段。
SessionStart 不加载教训。PreToolUse Hook（lesson-guard.sh）根据当前操作精确匹配并注入命中的教训。

## 记录新教训

触发条件：用户指出错误 / 同一操作连续失败 2 次 / 用户说"记住这个" / 回测结果严重不符根因明确
流程：调用 EngineeringLesson_Record Skill → 自动推断 trigger_patterns → 写入 lessons.md

## Rule Promotion

某条教训被触发 ≥3 次 → 提示用户是否提升到 CLAUDE.md 作为永久指令。
CLAUDE.md 只有用户明确同意才能修改。
