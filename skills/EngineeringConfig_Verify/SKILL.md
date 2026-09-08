---
name: EngineeringConfig_Verify
description: 配置变更自检 — 修改 MCP/Skill 配置后，通过子进程 Claude 会话自动验证变更是否生效，无需手动重启。触发词：验证配置、配置自检、校验MCP、校验skill生效、verify config、config check、MCP能连上吗、skill生效了吗、MCP配好了、配好了检查一下、skill创建完了、新建了MCP验证下、配置写好了、检查配置生效、帮我验证MCP、帮我检查skill、写完配置自检、改完配置测一下。
---

# /EngineeringConfig_Verify — 配置变更自检

## 角色定位

MCP/Skill 配置变更后的自动化验证 Agent。核心机制：

- **L1（语法+连接）**：`claude mcp list/get` — 同进程内直接检查，0 秒启动
- **L2（工具/技能发现）**：`claude -p "..."` — 启动子进程 Claude 会话（自动加载最新配置），在干净环境中验证工具/Skill 是否被正确发现
- **L3（端到端）**：`claude -p "..."` — 子进程会话中执行真实工作流，验证完整链路

**解决的核心痛点**：Claude Code 在会话启动时加载 `.mcp.json` 和 `~/.claude/skills/`，运行时修改配置不生效。必须重启才能验证。本 Skill 通过 `claude -p`（非交互模式）在子进程中启动全新会话（自动读取最新配置），绕过此限制。

## 路由

不绑定特定 MCP Server。依赖：

| 工具 | 用途 |
|------|------|
| `Bash` | 执行 `claude mcp list`、`claude mcp get`、`claude -p` |
| `Read` | 读取 `.mcp.json`、`SKILL.md` |
| `Write` / `Edit` | （可选）修复配置语法错误 |

## 输入格式

用户可通过以下方式调用：

```
# 自动检测最近变更
/EngineeringConfig_Verify

# 指定目标
/EngineeringConfig_Verify --mcp <server-name>
/EngineeringConfig_Verify --skill <skill-name>

# 指定验证深度
/EngineeringConfig_Verify --level 1    # 仅 L1 语法+连接
/EngineeringConfig_Verify --level 2    # L1 + L2 工具发现（默认）
/EngineeringConfig_Verify --level 3    # L1 + L2 + L3 端到端
```

---

## 交互协议（3 个 Phase，按需执行）

### Phase 1：变更检测

#### Step 1.1：确定验证目标

若用户指定了 `--mcp` 或 `--skill` → 直接进入 Phase 2，跳过检测。

否则，自动检测最近变更：

```bash
# 检测 .mcp.json 是否在最近 30 分钟内被修改
find .mcp.json -mmin -30 2>/dev/null

# 检测 ~/.claude/skills/ 下是否有最近 30 分钟内修改的 SKILL.md
find ~/.claude/skills/ -name "SKILL.md" -mmin -30 2>/dev/null
```

#### Step 1.2：展示检测结果

```
🔍 配置变更检测

【MCP 配置】
  • .mcp.json — ✏️ 7 分钟前修改

【Skill 文件】
  • EngineeringConfig_Verify/SKILL.md — 🆕 刚刚创建
  • ResearchGil_Factor_Test/SKILL.md — ✏️ 15 分钟前修改

【验证计划】
  L1 语法+连接 → L2 工具/技能发现

是否继续？[是 / 跳过指定项 / 仅 L1]
```

**Claude 必须**：等待用户确认后再执行 Phase 2。

---

### Phase 2：分级验证

#### Step 2.1：L1 — 语法与连接（< 5 秒，始终执行）

##### MCP 验证

```bash
# 1. 列出所有 MCP Server 及其连接状态
claude mcp list
```

**通过标准**：
- ✅ 目标 Server 显示 `✓ Connected`
- ⚠️ 显示 `⏸ Pending approval` → 需用户在 `.mcp.json` 中批准
- 🔴 显示 `✗ Disconnected` 或未出现在列表中 → 配置语法错误或 Server 未启动

```bash
# 2. 对目标 Server 获取详细信息
claude mcp get <server-name>
```

**通过标准**：
- ✅ Status: `✓ Connected`，Type/URL/Tools 数量正常
- 🔴 Status 非 Connected → 检查 Server 进程是否运行、URL 是否正确

##### Skill 验证

对目标 Skill 的 SKILL.md 执行基础检查：

1. **Frontmatter 语法**：YAML `---` 包裹是否闭合、`name` 和 `description` 是否存在
2. **目录位置**：是否在 `~/.claude/skills/<SkillName>/SKILL.md`
3. **命名规范**：是否符合 `<域><场景>_<模块>_<功能>` 格式

```bash
# 检查 frontmatter 是否闭合
python3 -c "
import sys, yaml
with open('$SKILL_PATH') as f:
    content = f.read()
parts = content.split('---')
if len(parts) < 3:
    print('🔴 Frontmatter 未闭合或缺失')
else:
    try:
        meta = yaml.safe_load(parts[1])
        print(f'✅ name={meta.get(\"name\")}, description={meta.get(\"description\",\"\")[:50]}...')
    except Exception as e:
        print(f'🔴 YAML 解析失败: {e}')
"
```

**L1 结果格式**：
```
📋 L1 验证结果

【MCP】moor
  claude mcp list: ✅ Connected
  claude mcp get:  ✅ HTTP, 127.0.0.1:9223, timeout=600s

【Skill】EngineeringConfig_Verify
  Frontmatter: ✅ name + description 完整
  目录位置:    ✅ ~/.claude/skills/EngineeringConfig_Verify/SKILL.md
  命名规范:    ✅ Engineering + Config + Verify
```

---

#### Step 2.2：L2 — 工具/技能发现（10-30 秒，默认执行）

核心机制：`claude -p` 启动全新 Claude 会话，该会话自动加载最新的 `.mcp.json` 和 `skills/` 配置，在干净环境中验证。

##### MCP L2 验证

```bash
# 验证 MCP Server 的工具列表是否可被新会话发现
claude -p "列出 MCP server '${SERVER_NAME}' 提供的所有工具名称，每行一个，不要其他内容" \
  --output-format text \
  --dangerously-skip-permissions \
  2>&1
```

**通过标准**：
- ✅ 返回了工具名称列表，与 Server 代码中定义的一致
- ⚠️ 返回了工具但数量少于预期 → 部分工具注册失败
- 🔴 返回 "No MCP servers found" 或类似错误 → 子会话未加载到该 Server

##### Skill L2 验证

```bash
# 验证 Skill 是否可被新会话发现和激活
claude -p "列出所有可用的 skills 名称，每行一个。然后尝试调用 /${SKILL_NAME}，确认它被正确激活并返回其描述。" \
  --output-format text \
  --dangerously-skip-permissions \
  2>&1
```

**通过标准**：
- ✅ 新会话能识别 Skill 名称并正确激活
- ⚠️ Skill 被识别但激活失败（触发词不匹配等）
- 🔴 新会话不识别该 Skill → SKILL.md 格式错误或目录位置不正确

**Claude 必须**：
- `claude -p` 默认可能需要 10-20 秒（模型响应 + MCP 连接），告知用户等待
- 若 `--dangerously-skip-permissions` 不可用，尝试不带该标志，但警告用户可能需要手动批准权限
- 若子会话超时（> 60s）→ 标记为 ⚠️ 超时，建议检查 MCP Server 响应速度

**L2 结果格式**：
```
📋 L2 验证结果

【MCP】moor
  工具发现:  ✅ 发现 24 个工具
  工具列表:  list_strategies, get_nav, run_backtest, ...

【Skill】EngineeringConfig_Verify
  技能发现:  ✅ 新会话识别成功
  激活测试:  ✅ /EngineeringConfig_Verify 正确激活
```

---

#### Step 2.3：L3 — 端到端（30-120 秒，用户明确要求时执行）

用最小可行输入驱动真实工作流，在子会话中完成端到端验证。

##### MCP L3 验证

对目标 MCP Server，选择一个**低风险、无副作用**的工具进行真实调用：

```bash
# 示例：验证 moor 的 list_strategies（纯读取，无副作用）
claude -p "调用 moor MCP server 的 list_strategies 工具，返回策略列表。只需返回策略名称即可。" \
  --output-format text \
  --dangerously-skip-permissions \
  2>&1
```

**通过标准**：
- ✅ 返回了真实的业务数据（如策略名称列表）
- ⚠️ 返回了数据但内容异常（空列表、格式错误等）
- 🔴 调用失败（超时、权限错误、Server 崩溃）

##### Skill L3 验证

对目标 Skill，执行其交互协议的 **Step 1**（最小可验证单元）：

```bash
# 示例：验证 ResearchGil_Factor_Test 的 Step 1
claude -p "调用 /ResearchGil_Factor_Test，只执行到 Step 1（加载数据集），完成后报告结果。" \
  --output-format text \
  --dangerously-skip-permissions \
  2>&1
```

**通过标准**：
- ✅ Skill 的 Step 1 正常执行，产出符合 SKILL.md 约定
- ⚠️ Step 1 执行但产出与预期有偏差
- 🔴 Step 1 执行失败

**Claude 必须**：
- L3 仅当用户明确要求 `--level 3` 时执行（耗时较长）
- 选择无副作用的验证目标（读操作优先，避免写文件/修改数据）
- 若 Skill 的 Step 1 需要用户输入 → 跳过 L3，建议用户在新会话中手动验证

**L3 结果格式**：
```
📋 L3 端到端验证

【MCP】moor → list_strategies
  调用结果:  ✅ 返回 2 个策略: 中邮价值1号, 中邮红利质量
  响应时间:  3.2s
  数据完整性: ✅ 策略名与预期一致

【Skill】ResearchGil_Factor_Test → Step 1
  执行结果:  ✅ 成功加载数据集
  数据集:    test_dataset.json, 包含 12 个字段
```

---

### Phase 3：汇总报告

```
╔══════════════════════════════════════════════╗
║         📋 配置自检报告                      ║
╠══════════════════════════════════════════════╣
║ 验证时间: 2026-07-22 15:30                   ║
║ 验证级别: L2                                 ║
╠══════════════════════════════════════════════╣
║                                              ║
║ 【MCP】moor                                   ║
║   L1 连接:  ✅ Connected                      ║
║   L2 发现:  ✅ 24 个工具                      ║
║                                              ║
║ 【Skill】EngineeringConfig_Verify             ║
║   L1 语法:  ✅ Frontmatter 完整               ║
║   L2 发现:  ✅ 新会话识别成功                 ║
║                                              ║
╠══════════════════════════════════════════════╣
║ 总结: 2/2 目标全部通过 ✅                     ║
║ 建议: 无需重启，配置已生效                    ║
╚══════════════════════════════════════════════╝
```

**结果判定**：

| 级别 | 判定 | 建议 |
|------|------|------|
| 全部 ✅ | 通过 | 无需重启，配置已生效 |
| 仅 L1 ✅ | 部分通过 | L2/L3 失败需排查：检查 MCP Server 进程、Skill 触发词配置 |
| L1 🔴 | 失败 | 语法/连接问题：检查 JSON 语法、Server URL、进程状态 |
| L2 🔴 | 失败 | 工具/Skill 发现失败：检查注册流程、触发词冲突 |

**Claude 必须**：
- 若 L1 全部通过但 L2 失败 → 给出具体排查建议（如 "检查 `claude mcp get <name>` 的 Tools 数量是否 > 0"）
- 若验证全部通过 → 明确告知用户"可以安全关闭当前会话并重新打开，或继续在当前会话工作，下次启动时配置自动生效"

---

## 与其他 Skill 的勾稽关系

| 上游/下游 | Skill | 数据流 |
|-----------|-------|--------|
| 上游 | `EngineeringMCP_Scaffold` | Scaffold 创建/修改 MCP → Verify 验证连接 + 工具发现 |
| 上游 | `EngineeringSkill_Scaffold` | Scaffold 创建新 Skill → Verify 验证语法 + 发现 |
| 上游 | `EngineeringSkill_Validate` | Validate 校验 Skill 功能 → Verify 验证配置层面（互补关系） |
| 同级 | `skills` | 配置变更后，Verify 确认配置 → 用户 `/skills` 查看更新后的分类 |

**与 EngineeringSkill_Validate 的分工**：
- `EngineeringSkill_Validate`：**功能层面** — Skill 的交互协议是否可执行、上下游是否联通
- `EngineeringConfig_Verify`：**配置层面** — MCP 能否连接、Skill 能否被新会话发现

## 文件路径约定

| 角色 | 约定路径 | 说明 |
|------|----------|------|
| 输入 | `.mcp.json`（项目）或 `~/.claude/.mcp.json`（全局） | MCP Server 配置 |
| 输入 | `~/.claude/skills/*/SKILL.md` | Skill 定义文件 |
| 输出 | 终端标准输出 | 验证报告直接打印，不写文件 |

---

## 关键约束

1. **L1 必须优先执行**：L1 失败时 L2/L3 必定失败，先修语法/连接问题
2. **L2 需要子进程**：`claude -p` 是唯一能模拟"重启后加载新配置"的机制
3. **L3 仅读不写**：选择无副作用的验证目标（list/get 类操作），避免污染数据
4. **超时处理**：`claude -p` 默认 30s 超时，若 MCP Server 响应慢，可能需要更长时间
5. **权限问题**：子会话可能触发权限审批，优先使用 `--dangerously-skip-permissions`（仅在安全环境）
6. **不修改被测配置**：本 Skill 只验证不修改（除非发现简单的语法错误且用户授权修复）

---

## 禁止行为

- ❌ 跳过 L1 直接跑 L2/L3（浪费时间）
- ❌ 在 L2/L3 中使用可能有副作用的工具（写文件、修改数据、发送请求）
- ❌ L1 失败后仍然报告"配置已生效"
- ❌ 修改 `.mcp.json` 或 `SKILL.md` 而不告知用户（修复语法错误除外）
- ❌ 阻塞等待超过 120s 的子进程（超时即报告，不重试）
- ❌ 在用户未指定 `--level 3` 时执行 L3 端到端验证
- ❌ 对 UNCHANGED 配置重复执行 L2/L3（L1 检查即可）
