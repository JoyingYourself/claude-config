---
name: EngineeringTask_PhaseGate
description: 阶段门控 — 每阶段转换时强制执行 README读取+教训提醒+进度核对+审计触发，防止上下文断裂导致偏离计划
---

# /EngineeringTask_PhaseGate — 阶段门控

## 角色定位

在通宵任务等多阶段工程中，每进入新阶段/新子任务前强制执行四项纪律检查：
① 读取对应项目 README/核心文档（防止目标漂移）
② 提取 `~/.claude/lessons.md` 相关教训（防止重复犯错）
③ 核对 plan 文件进度（防止偏离计划）
④ 触发工程审计（线1每子阶段，线2/3全部完成后）

**设计理念**: 不依赖 Agent 记忆，每次阶段转换显式调用本 Skill 即强制执行全部检查。

## 路由

无特定 MCP Server 依赖。纯文件系统读取（plan + README + lessons.md）。

## 输入格式

调用时通过 args 传入 `线号 阶段号`：
```
/EngineeringTask_PhaseGate 1 2    # 线1, 进入阶段2
/EngineeringTask_PhaseGate 2 1    # 线2, 进入阶段1
/EngineeringTask_PhaseGate 3 1    # 线3, 进入阶段1
```

---

## 交互协议

### Step 1: 读取 Plan + 确认当前阶段

1. 读取 `/Users/junye_shi/.claude/plans/scalable-snuggling-sedgewick.md` 全文
2. 定位当前线（1/2/3）和当前阶段的计划内容
3. 输出：`📋 当前阶段: 线{line} Phase {phase} — {阶段描述}`

### Step 2: 读取对应项目 README

按线读取核心文档：

| 线 | 必读文件 |
|----|---------|
| 1 | `MCP_Migration/README.md` (读"任务阶段"表+勾稽关系图+Phase 4 G5 状态) + `PROGRESS.md` |
| 2 | `SecretaryAgent_Qwen3/secretary-agent/README.md` (读"未实现需求"§6 + "踩坑记录"§4) |
| 3 | `成长策略/vault/00-总览.md` (读回测结果汇总表+演进树) + `成长因子构造手册_第一梯队因子详解.md` (读因子公式) |

输出：`✅ README 已读取 — 关键状态: {摘要}`

### Step 3: 提取相关 Lessons

1. 读取 `~/.claude/lessons.md`
2. 按当前任务类型过滤相关教训：
   - 线1 → #MCP #测试 #穿行测试 #架构 #验证
   - 线2 → #Skill #MCP #工程规范 #工作流
   - 线3 → #回测 #因子 #Obsidian #工作流 #记录
3. 输出 Top 5 最相关教训（每条含日期+规则一句话）

输出：`⚠️ 相关教训 (Top 5): {列表}`

### Step 4: 核对 Plan 进度

1. 对比当前阶段的实际产出 vs Plan 中该阶段的交付物
2. 检查：是否有遗漏？是否有偏离（做了 plan 之外的事）？
3. 若偏离 → 记录偏离原因并确认是否需要更新 plan

输出：`📐 进度核对: {on_track / deviated} — {说明}`

### Step 5: 触发工程审计（按线规则）

| 线 | 触发条件 | 审计 Skill |
|----|---------|-----------|
| 1 | **每子阶段完成后** | EngineeringCoding_Audit + EngineeringFrame_Audit |
| 2 | 全部完成后 | EngineeringCoding_Audit + EngineeringFrame_Audit |
| 3 | 全部完成后 | EngineeringCoding_Audit + EngineeringFrame_Audit |

- 若当前阶段需要审计 → 调用对应审计 Skill → 读取审计报告 → 列出发现的问题
- 若不需要 → 输出 `⏭️ 当前阶段无需审计（线{line}规则：{规则说明}）`

输出：`🔬 审计: {触发/跳过} — {发现 N 个问题 / 无问题}`

### Step 6: 汇总门控结论

```
╔══════════════════════════════════════╗
║  Phase Gate: 线{line} Phase{phase}   ║
╠══════════════════════════════════════╣
║  ✅ README 已读取                    ║
║  ⚠️  N 条相关教训已提醒              ║
║  📐 进度: on_track / deviated        ║
║  🔬 审计: 触发/跳过 — N issues       ║
╠══════════════════════════════════════╣
║  🟢 门控通过 / 🟡 有风险继续 / 🔴 阻断 ║
╚══════════════════════════════════════╝
```

门控判据：
- 🟢 通过: README 已读 + lessons 已提醒 + 进度 on_track + 审计 0 阻断问题
- 🟡 有风险继续: 有非阻断问题但可后续修复
- 🔴 阻断: 进度严重偏离或审计发现阻断级问题，需暂停修复

---

## 与其他 Skill 的勾稽关系

| 上游/下游 | Skill | 数据流 |
|-----------|-------|--------|
| 上游 | `EngineeringTask_Plan` | Plan 产出 plan 文件 → PhaseGate 读取并核对进度 |
| 同级 | `EngineeringCoding_Audit` | PhaseGate Step 5 触发 Coding Audit |
| 同级 | `EngineeringFrame_Audit` | PhaseGate Step 5 触发 Frame Audit |

## 禁止行为

- ❌ 跳过任何 Step（1-6 必须全部执行）
- ❌ Step 2 不实际读取 README 就声称"已读"
- ❌ Step 3 不读取 lessons.md 就输出空列表
- ❌ Step 4 不对比 plan 文件直接写 on_track
- ❌ Step 5 该触发审计时不触发
- ❌ 门控🔴阻断时仍继续执行后续任务
