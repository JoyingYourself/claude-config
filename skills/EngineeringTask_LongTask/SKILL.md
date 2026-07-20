---
name: EngineeringTask_LongTask
description: 长任务执行器 — bypass模式下启动/监控/审计长时间运行的量化研究任务。集成对抗式代码审计(连续3次0问题)+架构审计(组件连续3次+终审连续5次)+心跳注册+checkpoint持久化。触发词：长任务、long task、通宵任务、bypass任务、后台任务、无人值守任务
---

# /EngineeringTask_LongTask — 长任务执行器

## 角色定位

在 bypass 模式下启动长时间运行的量化研究任务（批量回测、全市场因子扫描、参数网格搜索等），提供完整的任务规划→穿行测试→审计循环→心跳监控→结果审计闭环。

**核心原则**：不接受任何妥协。代码审计连续通过才算通过，中间任何失败→修复→计数器归零→重来。

**与其他 Engineering Task Skill 的分工**：
- `EngineeringTask_Plan` → 项目宏观规划（多 Phase 任务拆分）
- `EngineeringTask_PhaseGate` → 阶段转换门控（README+教训+进度+审计四检）
- **`EngineeringTask_LongTask`** → 单任务执行闭环（本 Skill，细粒度审计+心跳+checkpoint）

## 路由

本 Skill 不绑定特定 MCP Server。依赖：
- `Bash` / `Read` / `Write` / `Edit` — 文件操作
- `Skill` 工具 — 调用 `EngineeringCoding_Audit` / `EngineeringFrame_Audit`
- 系统 crontab — 心跳监控（独立于 Claude Code 运行）

## 输入格式

用户直接调用，传入任务描述或完整命令：

```
/long-task <任务描述或shell命令>
```

例：
```
/long-task 全市场成长因子IC测试，5个因子，2012-2025月频
/long-task python3 ~/backtest/run_grid_search.py --config dividend.json
```

---

## 交互协议（7 Phase，严格顺序）

---

### Phase 0: 模式门禁

**Claude 必须**：自动检测当前是否 bypass 模式。

检测方法：尝试执行 `bash -c 'echo bypass_check'`，若需要用户审批确认 → 非 bypass 模式。

若为非 bypass 模式：
```
❌ 模式门禁未通过

/long-task 必须在 bypass 模式下运行。切换方式（三选一）:
  1. 启动参数: claude --dangerously-skip-permissions
  2. 会话内: Shift+Tab 切换到红色 bypass 条
  3. 永久设置: settings.json 中 "defaultMode": "bypassPermissions"

请切换后重新调用 /long-task。
```

若为 bypass 模式：✅ 门禁通过，进入 Phase 1。

---

### Phase 1: 任务规划

#### Step 1.1: 获取 README 路径

```
📋 请提供项目的 README.md 路径：
> [用户输入，支持回车自动查找]

自动查找规则：
  · 当前工作目录下找 README.md
  · 父目录逐级向上查找
  · 列出找到的候选 → 用户选择
```

#### Step 1.2: 读取 README + 生成计划

1. 读取用户指定的 README.md 全文
2. 提取关键信息：
   - 项目目标与背景
   - 技术栈与依赖
   - 已有成果（已完成什么）
   - 踩坑记录（已知问题）
   - 产出物格式约定
3. 解析用户的任务描述，拆分为任务阶段
4. 逐项检查：

| 检查项 | 内容 | 来源 |
|--------|------|------|
| 命令 | 可执行的完整 shell 命令 | 用户输入 |
| 工作目录 | 必须为绝对路径 | CLAUDE.md □3 |
| 预期耗时 | 用于心跳判定（CPU=0 超时阈值=10min） | 心跳需求 |
| 产出物 | 每个子任务产出文件路径 + 预期大小/行数范围 | CLAUDE.md □1 |
| 磁盘空间 | `df` 确认产出目录可用空间 > 预期产出的 2× | lessons.md |
| 网络依赖 | 是否需要 MCP/API/数据库，网络是否稳定 | CLAUDE.md |
| 数据有效期 | 依赖的外部数据是否会过期（如估值表） | lessons.md |
| 重启命令 | 必须与首次启动幂等或兼容（覆盖写 vs 追加写） | 心跳需求 |

#### Step 1.3: 持久化计划

```bash
# 写入 /tmp/longtask-<id>-plan.json
```

```json
{
  "id": "lt_20260719_001",
  "task": "全市场成长因子IC测试",
  "readme": "/Users/.../README.md",
  "bypass": true,
  "phases": [
    {"phase": 0, "name": "模式门禁", "status": "done"},
    {"phase": 1, "name": "任务规划", "status": "running"},
    {"phase": 2, "name": "逐脚本执行+审计", "status": "pending", "scripts": [], "coding_audit_target": 3},
    {"phase": 3, "name": "组件级架构审计", "status": "pending", "components": [], "frame_audit_target": 3},
    {"phase": 4, "name": "穿行测试", "status": "pending"},
    {"phase": 5, "name": "执行+心跳注册", "status": "pending"},
    {"phase": 6, "name": "终审", "status": "pending", "frame_audit_target": 5},
    {"phase": 7, "name": "结果审计", "status": "pending"}
  ],
  "last_checkpoint": "Phase 1: 计划已生成，等待用户确认"
}
```

#### Step 1.4: 展示计划 + 等待确认

```
╔══════════════════════════════════════╗
║  📋 长任务执行计划                     ║
╠══════════════════════════════════════╣
║  任务: <描述>                         ║
║  README: <路径>                      ║
║  工作目录: <pwd>                      ║
║                                      ║
║  Phase 2: 编写 N 个脚本              ║
║    ├ script_1.py                     ║
║    ├ script_2.py                     ║
║    └ ...                             ║
║  审计: Coding(连续3次) Frame(组件3次) ║
║  终审: Frame(连续5次)                ║
║                                      ║
║  预计耗时: <X>h | 产出: <N> 个文件    ║
║  重启命令: <cmd>                     ║
║  磁盘可用: <size>                    ║
║                                      ║
║  [🟢 门控通过 / 🟡 有风险 / 🔴 阻断]  ║
╚══════════════════════════════════════╝

确认开始执行？[是 / 修改计划 / 取消]
```

---

### Phase 2: 逐脚本执行 + Coding Audit 循环

**审计规则（硬性，不可妥协）**：

```
每个脚本写完后:
  ┌──────────────────────────────────────┐
  │  EngineeringCoding_Audit (full)      │
  │  目标: 连续 3 次 0 问题               │
  │                                      │
  │  pass_count = 0                      │
  │  while pass_count < 3:               │
  │    执行审计                            │
  │    if 发现任何问题(含LOW):              │
  │      修复代码                          │
  │      pass_count = 0    ← 归零！       │
  │    else:                              │
  │      pass_count += 1                  │
  │                                      │
  │  连续 3 次 ✅ → 此脚本通过 → 下一脚本    │
  └──────────────────────────────────────┘

  ⚠️ 不接受:
    · "这是已知问题，先跳过"
    · "风险可控，后续处理"
    · "LOW 级别不影响功能，先通过"
    · 任何形式的妥协
```

**Claude 必须**：
1. 每完成一个脚本的编写 → 立即调用 `Skill` 工具触发 `EngineeringCoding_Audit --mode=full <脚本路径>`
2. 维护 `pass_count` 计数器
3. 审计发现问题 → 修复 → 计数器归零 → 重新审计
4. 连续 3 次 0 问题 → 更新 `plan.json` 的 checkpoint
5. 所有脚本通过 → 进入 Phase 3

---

### Phase 3: 组件级架构审计

**审计规则（硬性，不可妥协）**：

```
每个组件(模块/子目录)完成后:
  ┌──────────────────────────────────────┐
  │  EngineeringFrame_Audit              │
  │  目标: 连续 3 次 0 问题               │
  │                                      │
  │  pass_count = 0                      │
  │  while pass_count < 3:               │
  │    执行架构审计                         │
  │    if 发现任何问题:                     │
  │      修复代码                          │
  │      pass_count = 0    ← 归零！       │
  │    else:                              │
  │      pass_count += 1                  │
  │                                      │
  │  连续 3 次 ✅ → 此组件通过 → 下一组件    │
  └──────────────────────────────────────┘
```

组件划分规则：
- 单一文件项目 → 对整个文件做 Frame Audit，视为 1 个组件
- 多文件项目 → 按子目录/模块划分，每个子目录视为 1 个组件
- 若项目只有 1 个组件 → Phase 3 与 Phase 6 不重复：Phase 3 计数目标=3，Phase 6 计数目标=5（独立执行，不复用 Phase 3 的计数）

---

### Phase 4: 穿行测试

**硬性规定（来自 lessons.md 2026-07-10 教训）**：禁止用现成产物当输入绕过生产环节。必须走完整生产链路。

#### Step 4.1: 最小规模执行

```bash
# 用最小参数跑完整链路
# 例：回测任务 → 1年数据/单期调仓
#     因子任务 → 单期IC测试
```

验证：
- [ ] 命令可跑通，无语法/导入/权限错误
- [ ] 产出文件存在且非空
- [ ] 产出格式与 README 约定一致
- [ ] Python 文件通过 `py_compile`（auto-validate.py 规范）

#### Step 4.2: 产物校验

| 检查项 | 操作 | 来源 |
|--------|------|------|
| 文件存在 | `ls -la` 确认非空 | CLAUDE.md □1 |
| 格式正确 | CSV 列数匹配、JSON 可解析、HTML 结构完整 | CLI |
| 数据合理 | 行数/大小在预期量级 | CLAUDE.md □2 |
| 路径真实 | 如引用外部文件，用 Read 确认存在 | CLAUDE.md □4 |

#### Step 4.3: 失败处置

测试失败 → 修复 → 重新执行 Step 4.1 → 直到通过。未通过不得进入 Phase 5。

---

### Phase 5: 执行 + 心跳注册

#### Step 5.1: 心跳环境自检

```bash
# 自动检查
1. /tmp/autopilot_state.json 存在且可写？
2. autopilot-heartbeat 系统 crontab 已配置？
   → 否：自动配置 */5 * * * * bash ~/.claude/hooks/autopilot-heartbeat.sh
3. 重启命令幂等性：若产出使用覆盖写(>) → ✅
                    若产出使用追加写(>>) → ⚠️ 警告用户重启会重复追加
4. 日志路径：若在 /tmp/ → ⚠️ 警告可能被系统清理
```

#### Step 5.2: 启动 + 注册

```bash
# Fire-and-forget 启动
nohup <命令> > <日志路径> 2>&1 &
PID=$!

# 注册到心跳
python3 -c "
import json, os
STATE = '/tmp/autopilot_state.json'
data = {}
if os.path.exists(STATE):
    try: data = json.load(open(STATE))
    except: pass
if 'processes' not in data:
    data['processes'] = {}
data['processes']['<任务名>'] = {
    'pid': $PID,
    'restart_cmd': '<完整重启命令>',
    'log': '<日志路径>',
    'started_at': '$(date -u +%Y-%m-%dT%H:%M:%SZ)',
    'restarts': 0,
    'status': 'running'
}
json.dump(data, open(STATE, 'w'), indent=2, ensure_ascii=False)
"
```

#### Step 5.3: 汇报

```
✅ 任务已启动

  PID:      12345
  日志:     /tmp/longtask-backtest.log
  计划文件:  /tmp/longtask-lt_20260719_001-plan.json
  心跳:     每5分钟检查 (系统 crontab)
  重启次数上限: 3

  可关闭此会话。下次 SessionStart 会自动检测未完成任务。
```

---

### Phase 6: 终审

**审计规则（硬性，不可妥协）**：

```
任务执行完毕后:
  ┌──────────────────────────────────────┐
  │  EngineeringFrame_Audit              │
  │  目标: 连续 5 次 0 问题               │
  │                                      │
  │  pass_count = 0                      │
  │  while pass_count < 5:               │
  │    执行架构审计                         │
  │    if 发现任何问题:                     │
  │      修复代码                          │
  │      pass_count = 0    ← 归零！       │
  │    else:                              │
  │      pass_count += 1                  │
  │                                      │
  │  连续 5 次 ✅ → 终审通过               │
  └──────────────────────────────────────┘
```

**区分 Phase 3 与 Phase 6**：
- Phase 3（组件审计）：在编码阶段执行，每个组件 3 次，追求开发期质量
- Phase 6（终审）：在任务产出完成后执行，5 次，追求交付级质量
- 二者独立计数，不互相复用

**如果在 Phase 6 发现需要修改代码的问题**：
1. 修复代码
2. 该修改过的脚本 → 回到 Phase 2 重新 Coding Audit（3 次）
3. 该修改过的组件 → 回到 Phase 3 重新 Frame Audit（3 次）
4. 全部通过后 → Phase 6 计数器继续（从修复前的计数继续，非归零）

**终审通过条件**：
- [ ] 连续 5 次 Frame Audit 0 问题
- [ ] 所有因修复触发的 Phase 2/3 回流已完成

---

### Phase 7: 结果审计

#### Step 7.1: 进程状态（心跳日志交叉验证）

```bash
# 读取 autopilot_state.json
cat /tmp/autopilot_state.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
p = d['processes']['<任务名>']
print(f'PID: {p[\"pid\"]}')
print(f'状态: {p[\"status\"]}')
print(f'被心跳重启次数: {p[\"restarts\"]}')
"
```

#### Step 7.2: 产出物完整性（CLAUDE.md 校验清单）

| 检查项 | 操作 | 来源 |
|--------|------|------|
| □1 数据溯源 | 所有数字从源文件逐字引用，禁止凭记忆 | CLAUDE.md |
| □2 计算验证 | 涉及计算展示完整过程，交叉验证 | CLAUDE.md |
| □3 代码逻辑 | 所有边界条件下正确运行 | CLAUDE.md |
| □4 文件引用 | 引用的路径真实存在 | CLAUDE.md |
| □5 逻辑一致性 | 结论与前面分析一致，无前后矛盾 | CLAUDE.md |
| □6 完整性 | 没有遗漏用户要求的任何部分 | CLAUDE.md |

#### Step 7.3: 审计分类

| 状态 | 条件 | 处置 |
|------|------|------|
| ✅ 成功 | exit 0，产出完整，Phase 2/3/6 均通过 | 汇报结果，记录正面经验 |
| 🟡 部分成功 | exit ≠0，部分产出存在 | 分析缺失项，建议补救方案 |
| 🔴 失败 | exit ≠0，无有效产出 | 查看日志根因，自动追加 lessons.md |
| ⚫ 卡死 | CPU=0 >10min 被心跳 kill | 审计重启后的结果，记录卡死原因 |

#### Step 7.4: 更新 plan.json

```bash
# 标记所有 phase 完成，写入最终状态
python3 -c "
import json
with open('/tmp/longtask-<id>-plan.json') as f:
    plan = json.load(f)
for p in plan['phases']:
    p['status'] = 'done'
plan['last_checkpoint'] = '全部完成: $(date)'
plan['result'] = '<✅/🟡/🔴/⚫>'
json.dump(plan, open('/tmp/longtask-<id>-plan.json', 'w'), indent=2, ensure_ascii=False)
"
```

#### Step 7.5: 清理心跳注册

```bash
# 任务正常结束后清理注册
python3 -c "
import json
STATE = '/tmp/autopilot_state.json'
d = json.load(open(STATE))
d['processes'].pop('<任务名>', None)
json.dump(d, open(STATE, 'w'), indent=2, ensure_ascii=False)
"
```

---

## checkpoint 持久化与恢复

### 写入时机

以下任一事件发生时立即更新 `/tmp/longtask-<id>-plan.json` 的 `last_checkpoint`：
- Phase 1 计划确认
- 每个脚本 Coding Audit 连续 3 次通过
- 每个组件 Frame Audit 连续 3 次通过
- Phase 4 穿行测试通过
- Phase 5 心跳注册完成
- Phase 6 终审通过
- Phase 7 结果审计完成

### 恢复机制

```
SessionStart hook (session-briefing.sh) 检测:
  /tmp/longtask-*.json 存在且 phases 中有 status != "done" 的项
  → 注入提示: "⚠️ 检测到未完成的长任务: <id> — <任务描述>"
  → Claude 读取 plan.json → 从 last_checkpoint 继续
  → 所有审计计数器从 plan.json 中恢复
```

---

## 与其他 Skill 的勾稽关系

| 上游/下游 | Skill | 数据流 |
|-----------|-------|--------|
| 上游 | `EngineeringTask_Plan` | Plan 产出任务规划 → LongTask 读取 README 并执行 |
| 上游 | `EngineeringTask_PhaseGate` | PhaseGate 门控通过 → LongTask 启动执行 |
| 同级 | `EngineeringCoding_Audit` | LongTask Phase 2 逐脚本调用 Coding Audit（连续3次） |
| 同级 | `EngineeringFrame_Audit` | LongTask Phase 3/6 调用 Frame Audit（连续3+5次） |
| 下游 | `DocumentJournal_Daily` | LongTask 结果 → Journal 记录当日长任务执行摘要 |

## 文件路径约定

| 角色 | 约定路径 | 说明 |
|------|----------|------|
| 计划文件 | `/tmp/longtask-<id>-plan.json` | checkpoint 持久化，跨压缩恢复 |
| 心跳状态 | `/tmp/autopilot_state.json` | 进程注册，系统 crontab 读取 |
| 心跳日志 | `/tmp/autopilot_heartbeat.log` | 心跳监控活动日志 |
| 任务日志 | `/tmp/longtask-<id>.log` | 任务 stdout/stderr |

---

## 禁止行为

- ❌ bypass 模式未开启时继续执行（Phase 0 阻断后不得绕过）
- ❌ 跳过 Phase 1 README 询问步骤直接开始写代码
- ❌ Coding Audit 未达到连续 3 次 0 问题就声称"审计通过"
- ❌ Frame Audit 未达到连续 3 次（组件）/ 5 次（终审）0 问题就声称"审计通过"
- ❌ 审计发现问题后不归零计数器，以"小问题不影响"为由继续
- ❌ 接受任何形式的妥协（"已知问题先跳过""风险可控后续处理""LOW级别不阻塞"）
- ❌ Phase 2/3 审计发现问题修复后不回流重审
- ❌ Phase 4 穿行测试用现成产物当输入绕过生产链路（lessons.md 2026-07-10 教训）
- ❌ Phase 5 启动前不检查心跳 crontab 是否配置
- ❌ Phase 7 不读取心跳日志交叉验证进程状态
- ❌ task-plan.json 不写入 checkpoint 导致压缩后无法恢复
- ❌ 在 Phase 6 发现需改代码的问题后，不回流 Phase 2/3 重审
- ❌ 修改 SKILL.md 时不遵守本 Skill 自身的审计规范（本 Skill 本身就是任务产物）
