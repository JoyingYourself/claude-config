# Skill 设计词汇表

> 来源：mattpocock/skills · 移植日期：2026-07-20
> 根德：可预测性（Predictability）——Skill 让 Agent 每次按同样的**流程**执行（不是同样的输出）

---

## 核心术语

### 调用轴（Invocation）

| 术语 | 定义 | 你的 Skill 示例 |
|------|------|---------------|
| **模型调用**（Model-Invoked） | description 保留 = Agent 可自主发现触发 = 每条消息消耗 token 开销 | `ResearchGil_Factor_Test`（高频，值得开销） |
| **用户调用**（User-Invoked） | description 删除 = 只有人类输入名称才能触发 = 零 token 开销 | `EngineeringMCP_Scaffold`（低频，不值得开销） |
| **Context Load** | 模型调用 Skill 的 description 永远占用上下文窗口的 token 数 | 当前 27 个 Skill 全部模型调用 = 每条消息 ~1000+ token 额外开销 |
| **Cognitive Load** | 用户调用 Skill 的认知负担——人需要记住名称和用途 | 用户调用越多，越需要 Router Skill |
| **Router Skill** | 用户调用的单一入口，列出所有用户调用 Skill 及"什么时候用" | `/research`、`/engineering` |

### 信息层级（Information Hierarchy）

| 术语 | 定义 |
|------|------|
| **Steps** | 有序动作，Skill 的主干内容。每一步必须有可检查的完成标准 |
| **Reference** | 按需查阅的参考材料（定义、事实、参数），通过 context pointer 访问 |
| **External Reference** | Skill 外部的纯文件引用，无 description 无 steps，多个 Skill 共享 |
| **Progressive Disclosure** | 将 Reference 放到 Skill 外部的文件，只在需要时加载——节省 context |

### 操控（Steering）

| 术语 | 定义 |
|------|------|
| **Leading Word** | Skill 开头的动词，决定了 Agent 的行为模式。如"检查"vs"执行"vs"分析" |
| **Premature Completion** | Agent 在充分理解之前就声称完成——最常见的 Skill 故障模式 |
| **Completion Criterion** | 每个 Step 结束时的可验证条件——Agent 用来判断"我做到了吗？" |
| **Red Flag Table** | 嵌入 Skill 的元认知检查表——"如果你发现自己在想 X，停下来，重新执行 Y" |

### 修剪（Pruning）

| 术语 | 定义 |
|------|------|
| **Sediment** | 跨会话累积的未清理状态——过时的文件、残留的中间产物 |
| **Granularity** | Skill 拆分粒度——拆分越细，Context Load（模型调用）或 Cognitive Load（用户调用）越高 |
| **Deprecated Bucket** | 退役 Skill 的存放处——不删除，保留"为什么退役"的上下文 |

---

## 诊断工具

编写/审查 Skill 时，逐项检查：

### 检查清单 A：调用轴

- [ ] 这个 Skill 是否每周至少被触发 3 次？
  - 是 → 保留模型调用（description 保留）
  - 否 → 转为用户调用（`disable-model-invocation: true`）
- [ ] 如果有 5+ 个用户调用 Skill，是否已有 Router Skill？

### 检查清单 B：Premature Completion 防御

- [ ] 每个 Step 是否有可验证的完成标准？（不仅是"完成"两个字）
- [ ] 是否有 Red Flag Table？（高频/高风险 Skill 必须加）
- [ ] Leading Word 是否准确反映行为？（"检查"≠"执行"≠"分析"）

### 检查清单 C：信息层级

- [ ] Reference 是否放到了外部文件（而非挤在 SKILL.md 中）？
- [ ] Steps 是否在文件最前面（Reference 在 Steps 之后或外部）？
