---
name: EngineeringLesson_Maintain
description: 教训体系维护 — 记录新教训（含 trigger_patterns 推断）+ 存量审计（格式/去重/覆盖盲区/索引重建）
---

# EngineeringLesson_Maintain · 教训体系维护

对 `~/.claude/lessons.md`（全局唯一教训池）的全生命周期管理：记录新教训、维护存量、审计质量。

## 触发条件

- 用户说"记住这个""记一条教训""下次别这样"
- 用户指出 Claude 的错误或纠正方向
- 同一操作连续失败 2 次以上
- 回测/因子测试结果与预期严重不符，且找到了根因
- 用户说"维护教训""检查教训""审计 lessons"

## 功能

### 记（记录新教训）

1. 收集场景信息（什么操作、什么文件、什么 MCP）
2. 提取根因（为什么会出错）
3. 生成规则（下次怎么做，必须可执行）
4. 自动推断 trigger_patterns（从场景信息提取，不编造）
5. 展示完整内容让用户确认
6. 写入 lessons.md + 更新 KEYWORDS INDEX

### 管（存量维护）

- **格式审计**：逐条检查 trigger_patterns / WHEN / RULE / TAGS 是否完整
- **重复检测**：patterns 重叠 > 50% 的教训对 → 建议合并
- **覆盖盲区**：哪些 MCP Server / 文件类型 / 操作完全没有教训覆盖
- **质量评估**：RULE 是否可执行（不能是空泛的"要注意"）
- **索引重建**：根据所有教训的 title 和 tags 重新生成 KEYWORDS INDEX

## 约束

- 只读分析优先于写入——先展示问题清单，用户确认后再修改
- trigger_patterns 不编造——不确定就空着
- 每次只记一条教训
- 不自动删除教训