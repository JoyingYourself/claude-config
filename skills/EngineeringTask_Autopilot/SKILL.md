---
name: EngineeringTask_Autopilot
description: 彻夜任务脚手架 — 交互式引导创建 MISSION.md + PROGRESS.md，从 AutopilotNightshift 模板生成，复制 runner.sh 到项目目录。触发词：彻夜任务、通宵跑、autopilot、overnight、无人值守、晚上跑、nightshift、后台跑任务。
---

# /EngineeringTask_Autopilot — 彻夜任务脚手架

## 角色定位

将用户口述需求转化为可执行的彻夜任务配置。核心思路：bash 管流程（超时/重试/崩溃恢复），Agent 管内容。融合了 Nightcrawler（episodic 执行）、nightshift（验证门+晨报）、Fable-it（不可变 DoD）、cwc-long-running-agents（default-FAIL 合约）的成熟模式。

## 路由

- 模板文件：`~/Scholarship is a new sexy/ClaudeCode_related/AutopilotNightshift/templates/`
- 编排脚本：`~/Scholarship is a new sexy/ClaudeCode_related/AutopilotNightshift/runner.sh`
- 无需 MCP Server

## 输入格式

用户直接调用，通过交互式问答收集：项目路径、任务名称、目标、预算、时间上限、轮次上限、Phase 定义（名称+验收标准+详细说明）。

---

## 交互协议

### Step 1: 确认项目路径

询问用户任务在哪个目录下执行。默认：当前工作目录。若目录不存在则创建，记录为 `$PROJECT_DIR`。

### Step 2: 确认基础参数

逐项询问（提供默认值，回车即接受）：

| 参数 | 占位符 | 默认值 |
|------|--------|--------|
| 任务名称 | `{{TASK_NAME}}` | — |
| 一句话目标 | `{{TASK_GOAL}}` | — |
| 预算（¥） | `{{BUDGET_RMB}}` | 30 |
| 时间上限（h） | `{{MAX_HOURS}}` | 10 |
| 最大轮次 | `{{MAX_ROUNDS}}` | 50 |
| 外部约束 | `{{EXTERNAL_CONSTRAINT}}` | 留空 |

### Step 3: 确认 Phase 结构

1. 询问有几个 Phase
2. 逐个确认：名称、验收标准（`- [ ]` 格式）、详细说明（可选）、可用工具（可选）

### Step 4: 确认补充内容

询问（均为可选）：系统架构描述、补充执行规则、已完成可跳过的 Phase。

### Step 5: 生成文件

1. 读取 `templates/MISSION.md.tmpl`，替换占位符，处理 `{{#if}}`/`{{#each}}` 区块
2. 写入 `$PROJECT_DIR/MISSION.md`
3. 读取 `templates/PROGRESS.md.tmpl`，同样替换，写入 `$PROJECT_DIR/PROGRESS.md`
4. 复制 `runner.sh` 到 `$PROJECT_DIR/runner.sh`，创建 `output/` 和 `rounds/`

### Step 6: 交付

展示文件结构和启动命令：

```
$PROJECT_DIR/
├── MISSION.md     ← 任务定义
├── PROGRESS.md    ← 进度追踪
├── runner.sh      ← 编排器
├── output/        ← 晨报
└── rounds/        ← 轮次日志

启动: cd $PROJECT_DIR && bash runner.sh
停止: touch $PROJECT_DIR/STOP
```

---

## 与其他 Skill 的勾稽关系

| 上游/下游 | Skill | 数据流 |
|-----------|-------|--------|
| 下游 | `runner.sh` | MISSION.md + PROGRESS.md → 彻夜任务执行 |
| 同级 | `EngineeringTask_LongTask` | Autopilot 生成配置，LongTask 负责 bypass 模式监控审计 |
| 同级 | `EngineeringTask_PhaseGate` | Autopilot 的 MISSION.md 定义 PhaseGate 检查的阶段边界 |

## 模板语法

```
{{VARIABLE}}          — 简单替换
{{#if VARIABLE}}...{{/if}}  — 条件区块（VARIABLE 空则删除）
{{#each PHASES}}...{{/each}} — 循环区块
{{INDEX}}             — 循环内 1-based 序号
```

## 禁止行为

- ❌ 跳过任何确认步骤直接生成文件
- ❌ 在用户未确认前修改任何文件
- ❌ 替用户决定 Phase 的验收标准（必须逐条确认）
- ❌ 模板替换后残留未处理的 `{{...}}` 占位符
- ❌ 不在 Step 5 创建 `output/` 和 `rounds/` 目录
