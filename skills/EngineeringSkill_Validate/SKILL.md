---
name: EngineeringSkill_Validate
description: Skill 校验 — 扫描 SKILL.md 变更、识别新建/修订 Skill、逐 Skill 功能穿行测试、通过后自动更新 AgentSkillAnnouncement.html。触发词：维护skill、skill维护、更新skill目录、刷新skill列表、检测skill变更、skill校验、校验skill、验证skill。
disable-model-invocation: true
---

# /EngineeringSkill_Validate — Skill 校验

## 角色定位

Skill 注册表维护与功能校验 Agent。三阶段流水线：① 扫描 5 个 Skill 路径（全局 + 4 个项目工作区）的 `SKILL.md` 文件 mtime 识别新建/修订 Skill → ② 对变更 Skill 执行多维度功能穿行测试 → ③ 测试全部通过后自动更新 `AgentSkillAnnouncement.html`。

**核心原则**：先验证功能正常，再更新 HTML。任何 Skill 功能测试不通过，HTML 不更新。

## 路由

本 Skill 不绑定特定 MCP Server。依赖：
- 文件系统读写（5 个 Skill 路径 + `/Users/junye_shi/AgentFiles/AgentSkillAnnouncement.html`）
- `Skill` 工具（用于实际调用被测 Skill）
- `Bash` 工具（用于文件扫描、mtime 比较、HTML 编辑）
- `Read` / `Edit` / `Write` 工具（用于文件操作）

## 输入格式

用户直接调用，无需上游数据输入。

**状态文件**：`/Users/junye_shi/AgentFiles/.skill-registry-state.json`
- 首次运行时自动创建
- 记录每个 SKILL.md 的来源路径、上次 mtime 和校验状态
- 格式：
```json
{
  "last_scan": "2026-06-22T10:00:00",
  "scan_paths": [
    "~/.claude/skills",
    "~/AgentFiles/.claude/skills",
    "~/Scholarship is a new sexy/.claude/skills",
    "~/中邮资管/.claude/skills",
    "~/AccumulatingWisdom/.claude/skills"
  ],
  "skills": {
    "~/.claude/skills/DocumentJournal_Daily": {
      "mtime": "2026-06-20T14:30:00",
      "status": "validated",
      "last_validated": "2026-06-20T14:35:00"
    }
  }
}
```

---

## 交互协议（3 个 Phase，严格顺序）

### Phase 1：变更检测

#### Step 1.0：读取 Skill 路径配置

Skill 分布在 5 个路径下：

```bash
SKILL_PATHS=(
  "$HOME/.claude/skills"
  "$HOME/AgentFiles/.claude/skills"
  "$HOME/Scholarship is a new sexy/.claude/skills"
  "$HOME/中邮资管/.claude/skills"
  "$HOME/AccumulatingWisdom/.claude/skills"
)
```

**Claude 必须**：扫描时对每个路径独立执行 find，记录 Skill 来源路径。

#### Step 1.1：扫描 SKILL.md 文件

```bash
# 对每个 SKILL_PATHS 中的路径，分别获取所有 SKILL.md 文件的 mtime
for sp in "${SKILL_PATHS[@]}"; do
  if [ -d "$sp" ]; then
    find "$sp" -maxdepth 2 -name "SKILL.md" -exec stat -f "%m %N" {} \; 2>/dev/null
  fi
done | sort
```

#### Step 1.2：读取状态文件

读取 `/Users/junye_shi/AgentFiles/.skill-registry-state.json`。
- 若文件不存在 → 所有 Skill 均标记为 `NEW`
- 若文件存在 → 逐 Skill 对比 mtime

#### Step 1.3：分类变更

| 分类 | 判定条件 | 含义 |
|------|---------|------|
| `NEW` | 状态文件中无此路径+Skill 名的记录 | 首次发现此 Skill |
| `MODIFIED` | mtime 与状态文件中记录不同 | SKILL.md 发生了修订 |
| `UNCHANGED` | mtime 与状态文件中记录一致 | 无变更，跳过后续阶段 |

**Claude 必须**：变更清单中标注每个 Skill 的来源路径（如 `[全局]`、`[中邮资管]`、`[Scholarship]`）。

#### Step 1.4：展示变更清单

向用户输出变更摘要：

```
🔍 Skill 变更检测结果（2026-06-22 10:00）

【🆕 新建】2 个
  • EngineeringSkill_Validate [全局] — 首次发现

【✏️ 修订】1 个
  • ResearchGil_Factor_Test [中邮资管] — mtime 2026-06-21 → 2026-06-22

【✅ 无变更】9 个

是否继续 Phase 2 功能穿行测试？[是 / 跳过指定Skill / 取消]
```

**Claude 必须**：等待用户确认后再进入 Phase 2。用户可选择性跳过某些 Skill 的测试。

---

### Phase 2：功能穿行测试

对每个 `NEW` 或 `MODIFIED` 的 Skill，**逐一执行**以下测试维度。全部通过才进入 Phase 3。

---

#### 测试维度 1：唤起验证

**测试目标**：确认 Skill 能被正常激活。

| 测试项 | 操作 | 通过标准 |
|--------|------|---------|
| 1a. 中文触发词唤起 | 说出 SKILL.md 中定义的第一个中文触发词 | Skill 被正确路由激活 |
| 1b. 英文触发词唤起 | 说出 SKILL.md 中定义的英文触发词（如有） | Skill 被正确路由激活 |
| 1c. Slash 命令唤起 | 通过 `Skill` 工具以完整 Skill 名调用 | Skill 被正确加载 |
| 1d. 模糊匹配 | 说出与触发词含义相近但不完全一致的表达 | 理想情况仍能匹配；若不能，记录为 ⚠️ 建议补充触发词 |

**Claude 必须**：
- 使用 `Skill` 工具实际调用被测 Skill
- 记录唤起成功/失败状态
- 若唤起失败 → 直接标记为 🔴 致命，进入下一 Skill

---

#### 测试维度 2：交互协议逐 Step 可执行性

**测试目标**：确认 SKILL.md 中定义的每个交互 Step 在真实环境下可执行。

**操作**：
1. 读取被测 Skill 的 SKILL.md 全文
2. 提取「交互协议」章节中所有 Step
3. **逐 Step 执行**，模拟用户按协议交互：

| 测试项 | 操作 | 通过标准 |
|--------|------|---------|
| 2a. Step 1 前提条件 | 检查 Step 1 的依赖是否满足（如"读取某文件"→ 文件存在？） | 前提条件满足或 Skill 给出明确引导 |
| 2b. Step 1 核心操作 | 执行 Step 1 要求的具体操作 | 操作完成，无报错 |
| 2c. Step 1 产出校验 | 检查 Step 1 是否产出了协议约定的中间产物 | 中间产物存在且格式正确 |
| 2d-2x. 后续 Step | 对 Step 2, 3, ... N 重复 2a-2c | 每个 Step 可执行且产出正确 |
| 2y. 最终产出 | 检查整个协议执行完毕后的最终产物 | 与 SKILL.md 中宣称的产出一致 |
| 2z. 协议闭环 | 确认协议不会让用户卡在某个 Step 无法前进 | 每个 Step 有明确的下一步指引或完成声明 |

**Claude 必须**：
- 对每个 Step 记录通过/失败/跳过，附说明
- 若某 Step 依赖上游 Skill 的输出且当前不可用 → 标记为 ⚠️ 跳过并注明原因
- 若某 Step 报错且无回退方案 → 标记为 🔴 致命

---

#### 测试维度 3：依赖可用性

**测试目标**：确认 Skill 声明的外部依赖真实可用。

| 测试项 | 操作 | 通过标准 |
|--------|------|---------|
| 3a. MCP Server 连接 | 对 SKILL.md「路由」中声明的每个 MCP Server，尝试调用其基础工具（如 `list_tables`） | Server 在线且响应正常 |
| 3b. 文件路径存在 | 对 SKILL.md 中引用的每个硬编码文件路径，检查是否存在 | 路径存在；若不存在但 Skill 有创建逻辑 → 通过 |
| 3c. 外部 API/服务 | 若 Skill 依赖 GitHub API、WebFetch 等 | 进行一次基础调用确认连通 |
| 3d. 依赖版本 | 若 Skill 声明了 Python 包版本要求（如 `numpy>=1.24`） | 检查已安装版本是否满足 |

**Claude 必须**：
- MCP 不可用 → 标记为 🔴 致命
- 文件路径缺失但 Skill 会自动创建 → ✅ 通过

---

#### 测试维度 4：功能正确性（正常路径）

**测试目标**：用合法输入驱动 Skill 完整执行，验证产出正确。

| 测试项 | 操作 | 通过标准 |
|--------|------|---------|
| 4a. 典型输入 | 构造/使用一组常规、合法的输入参数 | Skill 正常执行完成 |
| 4b. 产出格式 | 检查最终产出的格式 | 与 SKILL.md「输入格式 或 产出」中定义的格式一致 |
| 4c. 产出内容 | 检查产出内容的关键要素 | 核心数据/结论/文件 存在且合理 |
| 4d. 幂等性（如有写入） | 用相同输入再次执行 | 不产生重复/冲突；或明确告知"已存在" |

---

#### 测试维度 5：异常处理与边界

**测试目标**：确认 Skill 在异常情况下不会静默失败，能给出清晰反馈。

| 测试项 | 操作 | 通过标准 |
|--------|------|---------|
| 5a. 缺少必填输入 | 用户不提供必填参数，或提供空值 | Skill 明确提示缺少什么、如何提供，而非崩溃 |
| 5b. 非法输入 | 提供格式错误或超出范围的输入（如日期"2026-13-40"、路径"/nonexist/"） | Skill 明确报错并说明合法格式/范围 |
| 5c. 依赖不可用 | 模拟 MCP 断开 / 文件不存在 | Skill 有回退方案或清晰报错，而非静默失败 |
| 5d. 边界输入 | 提供极大/极小/空/超长输入 | 不崩溃，有合理的边界处理（截断/拒绝/提示） |
| 5e. 并发冲突（如有锁） | 若 Skill 使用了锁机制，模拟锁被占用 | 给出"请稍后重试"提示，而非死等或覆盖 |

---

#### 测试维度 6：上下游配合（联动测试）

**测试目标**：确认 Skill 在 Skill 链中能正确接收上游数据和向下游传递数据。

| 测试项 | 操作 | 通过标准 |
|--------|------|---------|
| 6a. 上游→本 Skill | 若 SKILL.md「勾稽关系」中声明了上游 Skill：取上游 Skill 的真实输出，喂给本 Skill | 本 Skill 能正确消费上游数据，无格式不匹配 |
| 6b. 本 Skill→下游 | 取本 Skill 的真实输出，检查下游 Skill 的 SKILL.md 是否声明了匹配的输入格式 | 下游 Skill 的输入定义能接受本 Skill 的输出格式 |
| 6c. 同级边界 | 与同模块/同场景 Skill 对比功能范围 | 无明显重叠或灰色地带；若存在 → ⚠️ 记录建议 |
| 6d. 端到端链路 | 若条件允许：上游 → 本 Skill → 下游 完整跑通一次 | 数据在各环节正确传递，无断点 |

**Claude 必须**：
- 若上下游 Skill 均未安装/不可用 → 标记为 ⚠️ 无法测试并记录
- 接口格式不匹配 → 标记为 🔴 致命

---

#### 测试维度 7：触发词冲突检测

**测试目标**：确认触发词不会与其他 Skill 冲突。

| 测试项 | 操作 | 通过标准 |
|--------|------|---------|
| 7a. 精确冲突 | 检查本 Skill 的触发词是否与其他 Skill 的触发词完全一致 | 无完全一致；若重复 → ⚠️ 记录冲突 |
| 7b. 包含冲突 | 检查本 Skill 的触发词是否被其他 Skill 的触发词包含（如"数据校验" vs "数据校验报告"） | 评估是否需要调整 |
| 7c. 歧义测试 | 对每个触发词，说出它，观察路由到了哪个 Skill | 路由到预期的 Skill |

---

#### 测试维度 8：安全审查

**测试目标**：确认 Skill 执行过程中无安全风险。

| 测试项 | 操作 | 通过标准 |
|--------|------|---------|
| 8a. 敏感信息 | 检查 SKILL.md 和 Skill 执行过程中是否硬编码了 Token/密码/API Key | 无敏感信息泄露 |
| 8b. 文件写入范围 | 检查 Skill 写入的文件路径是否在预期目录内 | 无 `/tmp/` 以外的系统目录写操作（除锁文件） |
| 8c. 命令注入风险 | 若 Skill 使用了用户输入拼接 Shell 命令 | 输入经过转义或参数化，无注入风险 |

---

#### 测试结果汇总

每个 Skill 测试完成后输出：

```
🔬 穿行测试报告: <Skill名> [NEW / MODIFIED]

【1. 唤起验证】
  1a. 中文触发词: ✅ ResearchGil_Factor_Test 已激活
  1b. 英文触发词: ✅ factor test 已激活
  1c. Slash 命令: ✅
  1d. 模糊匹配: ⚠️ "测一下因子" 未匹配，建议添加触发词

【2. 交互协议可执行性】
  Step 1 (加载数据集): ✅
  Step 2 (确认表达式): ✅
  Step 3 (IC/IR分析): ✅ (IR=0.42)
  ...

【3. 依赖可用性】
  3a. MCP factor_Gil: ✅ 在线
  3b. 文件路径: ✅ 全部存在

【4. 功能正确性】
  4a. 典型输入: ✅ 正常执行
  4b. 产出格式: ✅ DataFrame + 图表
  4c. 产出内容: ✅ IC序列/分组收益/衰减图 均生成
  4d. 幂等性: ✅ 重复执行未重复写入

【5. 异常处理】
  5a. 缺少输入: ✅ 提示"请提供因子表达式"
  5b. 非法输入: ✅ 提示"日期格式应为 YYYY-MM-DD"
  5c. 依赖不可用: ⚠️ MCP断开时等待超时 60s 才报错（建议加超时配置）

【6. 上下游配合】
  6a. 上游(Data_Discover)→本: ✅ 可消费 DataFrame
  6b. 本→下游(Strategy_Backtest): ✅ 因子ID可传递
  6c. 同级边界: ✅ 与 Factor_Validate 边界清晰
  6d. 端到端: ✅ Discover→Test→Backtest→Report 链路完整

【7. 触发词冲突】
  7a. 精确冲突: ✅ 无
  7b. 包含冲突: ✅ 无

【8. 安全审查】
  8a. 敏感信息: ✅ 无
  8b. 写入范围: ✅ ~/.claude/skills/ 内
  8c. 注入风险: ✅ 无

【结论】
  ✅ 全部 8 维度通过（1 项 ⚠️ 建议优化，0 项 🔴 致命）
  → 准入 Phase 3 HTML 维护
```

**通过标准**：
- 🔴 致命 = 0 → 允许进入 Phase 3
- 🔴 致命 > 0 → 终止该 Skill，不更新 HTML，向用户报告致命项

---

### Phase 3：HTML 维护

**前置条件**：Phase 2 全部 Skill 通过（0 项 🔴 致命）。

#### Step 3.1：读取当前 HTML

读取 `/Users/junye_shi/AgentFiles/AgentSkillAnnouncement.html` 全文。

#### Step 3.2：处理 NEW Skill

对每个 `NEW` Skill：

1. **读取 SKILL.md**：获取功能说明、触发词、交互协议
2. **确定分类**：根据 Skill 名前缀确定所属分类区块（`Research*` → 量化研究 / `Engineering*` → 工程构建 / `Explore*` → 探索发现 / `Document*` → 文档日志）
3. **构造 Skill 卡片**：按 HTML 中现有卡片的 DOM 结构生成完整卡片，包含：
   - `skill-card-header`（名称 + skill-id + **`📅 最后更新: YYYY-MM-DD`**）
   - `info-block`（功能说明）
   - `info-block`（触发方式 + trigger-list）
   - `conv-flow`（交互流程，从 SKILL.md 提取）
   - `trace-section`（输入流转追踪，从 SKILL.md 提取）
   - `tags`
4. **定位插入位置**：在该分类 `</div>`（category 闭合标签）之前插入
5. **更新统计栏**：对应分类的计数 +1
6. **更新目录**：在 TOC 对应分类下添加 `<a>` 锚点链接
7. **更新时间戳**：卡片头部的 `<span class="skill-updated">📅 最后更新: YYYY-MM-DD</span>` 设为当日日期

#### Step 3.3：处理 MODIFIED Skill

对每个 `MODIFIED` Skill：

1. **定位现有卡片**：在 HTML 中搜索 `id="<Skill名>"`
2. **读取变更内容**：对比当前 SKILL.md 与状态文件中记录的上一版本
3. **更新卡片内容**：
   - 功能说明变更 → 更新 `info-block`
   - 触发词变更 → 更新 `trigger-list`
   - 交互流程变更 → 更新 `conv-flow`
   - 输入流转变更 → 更新 `trace-section`
   - 标签变更 → 更新 `tags`
4. **更新该卡片的时间戳**：`<span class="skill-updated">📅 最后更新: YYYY-MM-DD</span>` 改为当日日期
5. **保持未变更部分不变**

#### Step 3.4：更新元数据

1. **页眉**：更新总计数（如 `12 个` → `13 个`）和日期（`.meta` 中的 `最后更新：YYYY-MM-DD`）
2. **统计栏**：更新各分类的 `<strong>` 数字
3. **目录**：新增/删除/移动 TOC 条目
4. **页脚**：更新 `.footer` 中的日期为当日

#### Step 3.5：HTML 结构校验（强制）

```bash
HTML_FILE="/Users/junye_shi/AgentFiles/AgentSkillAnnouncement.html"

# 校验 1: 文件存在且非空
[ -f "$HTML_FILE" ] && [ "$(wc -c < "$HTML_FILE")" -gt 500 ] || exit 1

# 校验 2: HTML 结构完整
for tag in '</html>' '</head>' '</body>'; do
  grep -qF "$tag" "$HTML_FILE" || exit 1
done

# 校验 3: 每个 Skill 卡片正确闭合
# skill-card div 数量 = </div> 配对正确
OPEN=$(grep -c '<div class="skill-card"' "$HTML_FILE")
CLOSE_AFTER=$(grep -c '</div>' "$HTML_FILE")
# 粗略校验：总 div 闭合数应 >= skill-card 数

# 校验 4: 无残留占位符或空卡片
! grep -q '功能说明' "$HTML_FILE" | grep -q '<p></p>'

# 校验 5: 所有锚点可跳转
# 每个 href="#..." 在文件中能找到对应的 id="..."
grep -oP 'href="#([^"]*)"' "$HTML_FILE" | while read -r link; do
  id=$(echo "$link" | grep -oP '(?<=#)[^"]*')
  grep -q "id=\"$id\"" "$HTML_FILE" || echo "⚠️ 断链: $link"
done
```

| 检查项 | 阈值 | 不达标处理 |
|--------|:----:|-----------|
| HTML 文件存在且 > 500B | 是 | 重新生成 |
| `</html>` `</head>` `</body>` 均存在 | 是 | 重新生成 |
| skill-card div 数量 × 4 ≈ 总 div 闭合数 | 误差 < 10% | 检查遗漏 |
| 无空 `<p></p>` | 是 | 填充或删除 |
| 锚点链接全部有效 | 0 断链 | 修复断链 |

#### Step 3.6：更新状态文件

```bash
# 写入新的状态文件，记录本次扫描结果
# 将 Phase 2 通过的 Skill 的 mtime 和校验时间写入
cat > /Users/junye_shi/AgentFiles/.skill-registry-state.json << 'STATEOF'
{
  "last_scan": "<当前时间 ISO 8601>",
  "skills": {
    ...
  }
}
STATEOF
```

#### Step 3.7：告知用户

```
✅ Skill 校验完成

| 阶段 | 结果 |
|------|------|
| Phase 1 变更检测 | 🆕 1 个新建, ✏️ 1 个修订, ✅ 10 个无变更 |
| Phase 2 穿行测试 | ✅ 全部通过 (0 🔴, 2 ⚠️ 建议) |
| Phase 3 HTML 维护 | ✅ AgentSkillAnnouncement.html 已更新 |

⚠️ 建议优化项（不阻塞）：
  • ResearchGil_Factor_Test: "测一下因子" 未匹配触发词，建议添加
  • ResearchGil_Factor_Test: MCP 超时可配置化
```

---

## 与其他 Skill 的勾稽关系

| 上游/下游 | Skill | 数据流 |
|-----------|-------|--------|
| 上游 | 被测 Skill（任意） | 读取其 SKILL.md → 按交互协议执行穿行测试 |
| 同级 | `EngineeringSkill_Scaffold` | Scaffold 创建新 Skill → Validate 检测到 NEW → 穿行测试 |
| 同级 | `skills` | Validate 更新 AgentSkillAnnouncement.html → `/skills` 展示时引用同源数据 |
| 下游 | `DocumentJournal_Daily` | （参考关系）参考其 HTML 追加编辑 + 写入校验模式 |

## 文件路径约定

| 角色 | 约定路径 | 说明 |
|------|----------|------|
| **输出 1** | `/Users/junye_shi/AgentFiles/AgentSkillAnnouncement.html` | Phase 3 更新，skills 元 Skill 读取展示分类列表 |
| **输出 2** | `/Users/junye_shi/AgentFiles/.skill-registry-state.json` | 注册表状态基线，记录每个 SKILL.md 的来源路径 + mtime + 校验状态 |
| 输入 | 5 个 Skill 路径下的 `*/SKILL.md` | 扫描所有路径的 SKILL.md，检测 mtime 变更 |

**Skill 扫描路径**：
1. `~/.claude/skills/` — 全局（所有项目可见）
2. `~/AgentFiles/.claude/skills/` — AgentFiles 项目（MCP/Skill 工程）
3. `~/Scholarship is a new sexy/.claude/skills/` — Scholarship 项目（数据基础层）
4. `~/中邮资管/.claude/skills/` — 中邮资管项目（策略研发与实盘）
5. `~/AccumulatingWisdom/.claude/skills/` — Knowledge 项目（知识沉淀）

> 路径索引：`/Users/junye_shi/AgentFiles/SkillsRelationship_output/02_Engineering_Pipeline/02_Validate/index.html`

---

## 关键约束

1. **先验证，后更新**：Phase 2 有 🔴 致命 → Phase 3 整体跳过（仅通过部分仍需人工介入）
2. **变更检测基于 mtime**：不依赖 git、不依赖文件内容 diff（mtime 变了就触发重新校验）
3. **状态文件持久化**：`.skill-registry-state.json` 是下次扫描的基线
4. **HTML 编辑参考 DocumentJournal_Daily**：追加式更新、写入后必须通过结构校验
5. **穿行测试必须真实调用**：使用 `Skill` 工具实际激活被测 Skill，不可仅阅读 SKILL.md 推断功能
6. **用户可见决策点**：Phase 1 完成后展示变更清单→等待确认；Phase 2 完成后展示测试报告→等待确认→进入 Phase 3

---

## 禁止行为

- ❌ Phase 2 未完成或存在 🔴 致命时进入 Phase 3 更新 HTML
- ❌ 跳过 Phase 1 用户确认直接进入测试
- ❌ 仅读 SKILL.md 做"纸面审查"而不实际调用 Skill 工具
- ❌ 穿行测试中遇到报错不记录、不报告
- ❌ HTML 更新后不执行 Step 3.5 结构校验
- ❌ 状态文件更新后不校验写入完整性
- ❌ 测试过程中修改被测 Skill 的 SKILL.md（Validate 只检测不修改）
- ❌ 对 UNCHANGED Skill 重复执行穿行测试（除非用户明确要求）
- ❌ 在 NEW Skill 的穿行测试无法区分"Skill 功能 bug"和"Skill 依赖环境未就绪"时直接判 🔴
