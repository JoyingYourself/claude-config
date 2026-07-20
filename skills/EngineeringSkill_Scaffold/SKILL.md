---
name: EngineeringSkill_Scaffold
description: Skill 脚手架 — 按分类架构规范创建新 Skill，自动生成目录和 SKILL.md。触发词：创建skill、新建skill、skill scaffold、生成skill。
---

# /EngineeringSkill_Scaffold — Skill 脚手架

## 角色定位

按 `skills-architecture.md` 分类体系创建新 Skill。自动引导命名、生成目录结构、写入 SKILL.md 骨架、校验合规性、执行穿行测试。

**架构文档（唯一权威来源）**：`/Users/junye_shi/AgentFiles/skills-architecture.md`
**架构文档 HTML**：`/Users/junye_shi/AgentFiles/skills-architecture.html`（与 MD 同步维护）
**分类 CSV（机器可解析）**：`/Users/junye_shi/AgentFiles/skill-classification.csv`

## 路由

本 Skill 不绑定特定 MCP Server。依赖文件系统读写（`~/.claude/skills/` 目录）和架构文件（CSV + MD + HTML）。

## 与其他 Skill 的勾稽关系

| 上游/下游 | Skill | 数据流 |
|-----------|-------|--------|
| 下游 | `skills` | Scaffold 创建新 Skill 目录 + SKILL.md → `/skills` 自动发现并归类展示 |
| 同级 | `EngineeringSkill_Validate` | Scaffold 负责创建，Validate 负责事后校验命名/协议/门禁 |

## 文件路径约定

| 角色 | 约定路径 | 说明 |
|------|----------|------|
| **输出** | `~/.claude/skills/{SkillName}/SKILL.md` | 新建 Skill 的 SKILL.md，{SkillName} 在 Step 2b 由用户确认 |
| 下游消费 | `~/.claude/skills/{SkillName}/SKILL.md` | EngineeringSkill_Validate 扫描 mtime 变更发现新 Skill |

> 路径索引：`/Users/junye_shi/AgentFiles/SkillsRelationship_output/02_Engineering_Pipeline/01_New_Skills/index.html`

---

## 前置条件

Claude 执行本 Skill 前必须：
1. 读取 `/Users/junye_shi/AgentFiles/skills-architecture.md` 全文（获取命名规范 + 分类树 + 现有清单）
2. 读取 `/Users/junye_shi/AgentFiles/skill-classification.csv` 全文（查重 + 确定分类路径）

---

## 交互协议（6 步，严格顺序）

### Step 1：收集核心信息

向用户确认以下 3 个问题（必须逐项确认，不可跳过）：

**Q1: Skill 的中文描述是什么？**

> 一句话描述这个 Skill 做什么。示例："数据发现与提取 — 通过 data_Gil MCP Server 理解需求、发现字段、制定查询方案"

**Q2: 属于哪个一级域？**

```
📊 Research   — 因子/策略/数据/报告/论文（量化研究流水线）
🔧 Engineering — 代码审查/工具开发/MCP/Skill/数据运维/监控调度
🔍 Explore    — 外部信息采集/论文追踪/资讯监测
📝 Document   — 笔记/日志/会议/知识整理
```

**Q3: 场景是什么？**

| 域 | 场景选项 |
|----|---------|
| Research | `Gil`(聚源) `Wind`(万得) 其他数据源 |
| Engineering | `Backtest`(回测引擎) `MCP`(MCP服务) `Skill`(Skill系统) `DataInfra`(数据基建) |
| Explore | `GitHub` `ArXiv` `News`(行业资讯) 其他平台 |
| Document | `Obsidian` `Journal`(工作日志) `Meeting`(会议) `ADR`(决策代理) |

如果用户提出的场景不在上述列表中 → 这是新场景，需要在 CSV 和架构文档中注册。

---

### Step 2：确定模块与功能名

根据用户的描述，按以下规则拆分：

```
<一级域英文><场景英文>_<模块英文>_<功能名>
```

**模块**（Module）：该 Skill 归属的功能模块。取一个英文名词，首字母大写。
- 若该场景下已有同类模块 → 复用已有模块名
- 若为新模块 → 在 CSV 中新增

**功能名**（Function）：描述具体做什么。动词或名词，首字母大写。
- 好的例子：`Discover` `Test` `Backtest` `Audit` `Scaffold` `Validate` `Gen` `Track` `Learn`
- 坏的例子：`Tool` `Util` `Helper` `Manager` `Handler`（过于宽泛）

**Claude 必须**：
1. 查询 CSV 确认场景下已有的模块列表
2. 提出 2-3 个候选名称（含模块 + 功能名的组合），让用户选择
3. 解释每个候选名称的语义

**禁止**：替用户决定名称。必须列出候选并等待用户确认。

---

### Step 3：查重并最终确认

1. **查目录**：检查 `~/.claude/skills/<候选名>/` 是否已存在
2. **查 CSV**：检查 CSV 中是否已占用
3. **查命名规范**：逐条对照架构文档「1.2 命名规则清单」，验证：
   - 大小写正确？
   - 分隔符为 `_`？
   - 一级域无缩写？
   - 功能名具体不宽泛？

展示最终确认信息：

```
📋 新 Skill 确认

   Skill 名:  ResearchGil_Factor_Combine
   中文描述:  因子合成 — 多因子加权/正交化/降维/行业中性化
   分类路径:  Research → Gil → Factor
   目录位置:  ~/.claude/skills/ResearchGil_Factor_Combine/

   合规检查:
   ✅ 命名符合规范
   ✅ 未与现有 Skill 重名
   ✅ 分类路径存在

   确认创建？[是 / 修改名称 / 取消]
```

---

### Step 4：创建 Skill

用户确认后，执行以下操作：

**4a. 创建目录**

```bash
mkdir -p ~/.claude/skills/<Skill名>/
```

**4b. 写入 SKILL.md**

使用以下模板生成 SKILL.md，根据用户在 Step 1-3 提供的信息填充 `<>` 占位符：

```markdown
---
name: <Skill名>
description: <中文描述>
---

# /<Skill名> — <中文标题>

## 角色定位

<用户的描述>

## 路由

<如果有 MCP Server 或特定工具，在此说明；若无则写"本 Skill 不绑定特定 MCP Server">

## 输入格式

<如果 Skill 接收上游数据，在此定义输入格式（如 JSON 结构、文件路径、数据库连接串等）；若无上游输入则写"用户直接调用，无需上游数据输入">

---

## 交互协议

### Step 1: <第一步做什么>

1. <具体操作>
2. <具体操作>

### Step 2: <第二步做什么>

...

---

## 与其他 Skill 的勾稽关系

| 上游/下游 | Skill | 数据流 |
|-----------|-------|--------|
| 上游 | `<Skill名>` | <输入描述> |
| 下游 | `<Skill名>` | <输出描述> |

<若无上下游关系则写"本 Skill 独立运行，无上下游依赖">

## 禁止行为

- ❌ <列出不应做的事>
- ❌ <列出不应做的事>
```

**模板要求**：
- `name:` 字段必须与目录名完全一致
- `description:` 字段含中文关键词和触发词
- `## 路由` 章节明确使用的工具/MCP Server，若无则写"无特定依赖"
- `## 输入格式` 章节定义输入来源和格式；若 Skill 无上游数据输入则写"用户直接调用"
- `## 交互协议` 章节包含至少 2 个 Step
- `## 与其他 Skill 的勾稽关系` 章节必须列出上下游/同级 Skill 及数据流方向
- `## 禁止行为` 章节至少 3 条

**Claude 必须**：
- 根据用户描述生成有意义的交互协议，而非空模板
- 如果 Skill 涉及 MCP Server，在路由中明确 Server 名称
- 禁止行为要具体，不能泛泛写"禁止出错"

**4c. 验证写入**

```bash
# 校验 1: 目录存在
[ -d ~/.claude/skills/<Skill名>/ ] && echo "✅ 目录已创建"

# 校验 2: SKILL.md 存在
[ -f ~/.claude/skills/<Skill名>/SKILL.md ] && echo "✅ SKILL.md 已创建"

# 校验 3: name 字段一致
grep -q "^name: <Skill名>$" ~/.claude/skills/<Skill名>/SKILL.md && echo "✅ name 字段一致"

# 校验 4: 含必要章节
for sec in "角色定位" "路由" "输入格式" "交互协议" "与其他 Skill 的勾稽关系" "禁止行为"; do
  grep -q "## $sec" ~/.claude/skills/<Skill名>/SKILL.md && echo "✅ 章节: $sec"
done
```

---

### Step 5：更新分类文件并最终验证

**5a. 更新 CSV**

在 `/Users/junye_shi/AgentFiles/skill-classification.csv` 中添加一行：

```
<一级域中文>,<一级域英文>,<场景中文>,<场景英文>,<模块中文>,<模块英文>,<Skill名>,现有,<说明>,
```

如果是全新模块或场景，还需添加模块/场景的标题行。

**5b. 更新架构文档**（仅新建 Skill 时）

在 `/Users/junye_shi/AgentFiles/skills-architecture.md` 的「三、完整 Skill 清单」→「3.1 现有 Skill」表格中添加一行。

**同步更新** `/Users/junye_shi/AgentFiles/skills-architecture.html`：
- 现有 Skill 表格中添加一行
- 若原在规划中列表，从中移除
- 更新章节标题中的计数（如 `（9 个）` → `（10 个）`）

**如果是全新场景或全新模块**：还需更新「2.3 模块层与功能层的对应关系」表格，以及「二、分类体系」相关内容。MD 和 HTML 均需同步。

**5c. 最终验证（深度完整性检查）**

以下校验必须**全部通过**，不可仅依赖 `grep -q` 的浅层检查：

```bash
python3 << 'PYEOF'
import csv, re, os

SKILL = "<Skill名>"
BASE = "/Users/junye_shi/AgentFiles"
MD = f"{BASE}/skills-architecture.md"
HTML = f"{BASE}/skills-architecture.html"
CSV = f"{BASE}/skill-classification.csv"

errors = []

# ── 校验 1: 目录 + SKILL.md ──
if not os.path.isdir(os.path.expanduser(f"~/.claude/skills/{SKILL}")):
    errors.append("❌ 目录不存在")
else:
    print("✅ 目录存在")
if not os.path.isfile(os.path.expanduser(f"~/.claude/skills/{SKILL}/SKILL.md")):
    errors.append("❌ SKILL.md 不存在")
else:
    print("✅ SKILL.md 存在")

# ── 校验 2: CSV 行格式 ──
with open(CSV) as f:
    reader = csv.reader(f)
    rows = [r for r in reader if r and not r[0].startswith('#')]
found = [r for r in rows if len(r) >= 9 and r[6] == SKILL]
if not found:
    errors.append("❌ CSV 中未找到 Skill 行")
else:
    row = found[0]
    if len(row) < 9:
        errors.append(f"❌ CSV 行字段不足: {len(row)} (需要 >=9)")
    elif row[7] != "现有":
        errors.append(f"❌ CSV 状态应为'现有', 实际为'{row[7]}'")
    else:
        print(f"✅ CSV 行完整 — 域={row[0]}, 场景={row[2]}, 模块={row[4]}, 状态={row[7]}")

# ── 校验 3: CSV 行在正确的分类位置 ──
idx = rows.index(row) if found else -1
if idx > 0:
    prev_context = ""
    for j in range(idx-1, max(idx-10, 0), -1):
        if len(rows[j]) >= 5 and rows[j][4] and not rows[j][6]:
            prev_context = rows[j][4]
            break
    skill_parts = SKILL.split('_')
    expected_module = ""
    if len(skill_parts) >= 3:
        expected_module = skill_parts[1]  # 模块英文
    if prev_context and prev_context != expected_module:
        print(f"⚠️ CSV 行模块上下文: {prev_context}, 期望: {expected_module}")
    else:
        print(f"✅ CSV 行在正确的模块下: {prev_context or expected_module}")

# ── 校验 4: MD 表格行完整 + 计数更新 ──
with open(MD) as f:
    md = f.read()
if SKILL not in md:
    errors.append("❌ MD 中未找到 Skill 名")
else:
    print("✅ MD 已包含 Skill 名")
    # 只统计「3.1 现有 Skill」表格（在 "现有 Skill" 和 "规划中 Skill" 之间）
    existing_table = md.split("### 3.1 现有 Skill")[1].split("### 3.2 规划中 Skill")[0] if "### 3.2 规划中 Skill" in md else md.split("### 3.1 现有 Skill")[1]
    actual = len(re.findall(r'\| `(?:(?:Research|Engineering|Explore|Document)\w[\w_]*|skills)` \|', existing_table))
    existing_count_match = re.search(r'现有 Skill[（(](\d+)\s*个[）)]', md)
    if existing_count_match:
        count = int(existing_count_match.group(1))
        if count != actual:
            errors.append(f"❌ MD 计数不匹配: 标题 {count} 个 vs 实际 {actual} 行")
        else:
            print(f"✅ MD 计数一致: {count} 个")

# ── 校验 5: HTML 表格行完整 + 计数更新 ──
with open(HTML) as f:
    html = f.read()
if SKILL not in html:
    errors.append("❌ HTML 中未找到 Skill 名")
else:
    print("✅ HTML 已包含 Skill 名")
    existing_table_html = html.split("3.1 现有 Skill")[1].split("3.2 规划中 Skill")[0] if "3.2 规划中 Skill" in html else html.split("3.1 现有 Skill")[1]
    actual = len(re.findall(r'<code>(?:(?:Research|Engineering|Explore|Document)\w[\w_]*|skills)</code>', existing_table_html))
    existing_count_match = re.search(r'现有 Skill[（(](\d+)\s*个[）)]', html)
    if existing_count_match:
        count = int(existing_count_match.group(1))
        if count != actual:
            errors.append(f"❌ HTML 计数不匹配: 标题 {count} 个 vs 实际 {actual} 行")
        else:
            print(f"✅ HTML 计数一致: {count} 个")

# ── 校验 6: 若原在规划中列表，确认已移除 ──
# 只检查规划中表格本身（截断到下一个 ## / <h 标题），排除后面目录结构的干扰
planned_table_md = md.split("### 3.2 规划中 Skill")[1] if "### 3.2 规划中 Skill" in md else ""
if planned_table_md:
    next_sec = re.search(r'\n## ', planned_table_md)
    if next_sec:
        planned_table_md = planned_table_md[:next_sec.start()]
    if SKILL in planned_table_md:
        errors.append("❌ Skill 仍在 MD 规划中列表中，未移除")
    else:
        print("✅ MD 规划中列表无残留")
else:
    print("✅ MD 规划中列表无残留")

planned_table_html = html.split("3.2 规划中 Skill")[1] if "3.2 规划中 Skill" in html else ""
if planned_table_html:
    next_sec = re.search(r'<h[23]', planned_table_html)
    if next_sec:
        planned_table_html = planned_table_html[:next_sec.start()]
    if SKILL in planned_table_html:
        errors.append("❌ Skill 仍在 HTML 规划中列表中，未移除")
    else:
        print("✅ HTML 规划中列表无残留")
else:
    print("✅ HTML 规划中列表无残留")

# ── 校验 7: SKILL.md name 字段一致性 ──
skill_md_path = os.path.expanduser(f"~/.claude/skills/{SKILL}/SKILL.md")
with open(skill_md_path) as f:
    skill_md = f.read()
name_match = re.search(r'^name:\s*(\S+)', skill_md, re.MULTILINE)
if name_match and name_match.group(1) != SKILL:
    errors.append(f"❌ SKILL.md name 字段 '{name_match.group(1)}' != 目录名 '{SKILL}'")
else:
    print(f"✅ SKILL.md name 字段一致: {SKILL}")

# ── 汇总 ──
print(f"\n{'='*50}")
if errors:
    print(f"❌ {len(errors)} 项校验失败:")
    for e in errors:
        print(f"  {e}")
    exit(1)
else:
    print("✅ 全部校验通过 — 配置文件更新完整")
PYEOF

**关于 `/skills`**：`/skills` 是自动发现的——它从 `<system-reminder>` 动态读取 Skill 列表并按前缀匹配归类。**新 Skill 只要目录名符合命名规范，无需手动注册**即可在下一次 `/skills` 调用中自动出现在正确分类下。

**5d. 告知用户**

```
✅ Skill 创建完成

| 项目 | 内容 |
|------|------|
| Skill 名 | <Skill名> |
| 分类 | <一级域> → <场景> → <模块> |
| 目录 | ~/.claude/skills/<Skill名>/ |
| SKILL.md | ~/.claude/skills/<Skill名>/SKILL.md |
| CSV 已更新 | ✅ |
| 架构 MD 已更新 | ✅ |
| 架构 HTML 已更新 | ✅ |

> `/skills` 自动发现新 Skill，无需手动注册。下次会话中该 Skill 将出现在 `<system-reminder>` 可用列表中。
```

---

### Step 6：穿行测试（必要步骤，不可跳过）

创建完成后，必须对新 Skill 执行完整的穿行测试。**未通过穿行测试的 Skill 不得声称"创建完成"。**

#### 6a. 完整调用验证

1. 通过 `Skill` 工具实际调用新创建的 Skill
2. 按照 Skill 自身的交互协议逐步执行，验证每个 Step 是否可操作：
   - 每个 Step 的前提条件是否满足？
   - 依赖的工具 / MCP Server 是否可用？
   - 若依赖不可用 → 是否有回退方案？
3. 记录每个 Step 的执行结果（通过 / 失败 / 跳过）

#### 6b. 勾稽关系审查

1. 列出新 Skill 与同模块 / 同场景下已有 Skill 的关系：
   - 谁是上游（输出喂给本 Skill）？
   - 谁是下游（本 Skill 输出喂给谁）？
   - 谁是同级（功能互补 / 边界相邻）？
2. 检查接口一致性:
   - 上游 Skill 的输出格式是否能被本 Skill 消费？
   - 本 Skill 的输出格式是否能被下游 Skill 消费？
   - 是否存在数据格式缺口？
3. 检查边界是否清晰:
   - 与同级 Skill 是否有功能重叠？
   - 是否存在"灰色地带"（两个 Skill 都能做但都不完整）？

#### 6c. 配合执行完整测试

1. 设计至少 2 个联动场景，覆盖：
   - **正常流程**: 上游 Skill → 本 Skill → 下游 Skill 的完整调用链
   - **异常流程**: 本 Skill 检测到问题后，是否正确阻断下游？
2. 验证数据能在 Skill 间正确传递
3. 记录联动中的断点或摩擦点

#### 6d. 模拟数据检测（准确性验证）

1. 构造或利用已有数据模拟以下场景的检测准确性：
   - 正常数据 → Skill 应报告 🟢 通过
   - 过期数据（如最后更新 > 30 天）→ Skill 应报告 🟡 警告
   - 损坏数据（如文件损坏 / 表不可读）→ Skill 应报告 🔴 致命
   - 边界数据（如刚更新的数据 / 空表）→ Skill 应正确分类
2. 验证 Skill 的分级逻辑是否准确：
   - 是否有漏报（该报不报）？
   - 是否有误报（不该报报了）？
   - 严重程度分级是否合理？

#### 6e. 协议缺口修复

根据 6a-6d 的测试结果：
1. 列出所有发现的协议层缺口（如缺少回退方案、输入格式未定义、依赖工具不可用等）
2. 逐项修复 SKILL.md 中的问题
3. 修复后重新执行 6a 验证修复效果

#### 6f. 穿行测试报告

输出穿行测试报告，格式如下：

```
🔬 穿行测试报告: <Skill名>

【完整调用验证】
  Step 1: ✅/❌ <说明>
  Step 2: ✅/❌ <说明>
  ...

【勾稽关系】
  上游: <Skill名> — ✅ 接口一致 / ⚠️ 存在间隙: <说明>
  下游: <Skill名> — ✅ 接口一致 / ⚠️ 存在间隙: <说明>
  同级: <Skill名> — ✅ 边界清晰 / ⚠️ 存在重叠: <说明>

【配合执行测试】
  场景 1 (正常流程): ✅/❌ <说明>
  场景 2 (异常流程): ✅/❌ <说明>

【模拟数据检测】
  场景 1 (正常数据): ✅/❌
  场景 2 (过期数据): ✅/❌
  场景 3 (损坏数据): ✅/❌
  场景 4 (边界数据): ✅/❌

【协议缺口】
  ⚠️ <缺口 1> → 已修复 / 待修复
  ⚠️ <缺口 2> → 已修复 / 待修复

【结论】
  ✅ 穿行测试通过 / ⚠️ 存在待修复问题
```

#### 6g. 穿行测试通过标准

以下条件**全部满足**才算通过：

- [ ] 所有交互协议 Step 可执行（含回退方案）
- [ ] 上下游 Skill 接口一致（无格式缺口）
- [ ] 至少 2 个联动场景测试通过
- [ ] 至少 4 类模拟数据的检测结果准确
- [ ] 所有协议缺口已修复或在报告中明确标注待修复

---

## 决策速查表

以下规则帮助 Claude 在用户描述模糊时主动给出分类建议：

| 用户描述含… | 建议一级域 | 建议场景 |
|------------|-----------|----------|
| 因子/策略/回测/绩效/数据查询/论文复现 | Research | Gil（默认） |
| 代码审查/测试/性能/审计 | Engineering | Backtest |
| MCP Server/工具开发 | Engineering | MCP |
| Skill 开发/脚手架 | Engineering | Skill |
| 数据库/备份/健康检查 | Engineering | DataInfra |
| GitHub/开源项目 | Explore | GitHub |
| 论文/ArXiv | Explore | ArXiv |
| 新闻/政策/监管 | Explore | News |
| Obsidian/笔记/知识库 | Document | Obsidian |
| 日志/日报/周报 | Document | Journal |
| 会议/纪要 | Document | Meeting |
| 决策/风格学习 | Document | ADR |

---

## 扩展：新建场景/模块

如果用户的需求在现有分类树中找不到合适的场景或模块：

**新建场景**（如 Research 域新增数据源 `Tushare`）：
1. 在 CSV 中新增场景标题行
2. 在架构文档「2.2 场景层定义」表格中注册
3. 场景英文名可适度缩写，但需在文档中注明全称

**新建模块**（如 Explore 域 GitHub 场景下新增 `Actions` 模块）：
1. 在 CSV 中新增模块标题行
2. 在架构文档「2.3 模块层与功能层的对应关系」表格中新增

---

## 扩展：SkillsRelationship_output 维护

当新 Skill 存在勾稽关系（与已有 Skill 通过文件交换数据）时，必须在 `SkillsRelationship_output` 目录树中同步维护：

### 判定：是否需要维护 output 树

```
新 Skill 的勾稽关系中…
  ├── 存在上游 Skill（消费已有 Skill 的输出文件）？
  │     └── 是 → 勾稽到已有文件夹，在对应 index.html 中追加消费方记录
  ├── 存在下游 Skill（产出文件被已有/新 Skill 消费）？
  │     └── 是 → 在对应 Pipeline 下创建新文件夹 + index.html
  └── 完全独立（如 ExploreGitHub_Scholarship）？
        └── 无需操作
```

### 操作清单

| # | 操作 | 说明 |
|---|------|------|
| 1 | 确定 Pipeline | Research / Engineering / Document |
| 2 | 新建文件夹 | `mkdir -p SkillsRelationship_output/{Pipeline}/{NN}_{Module}/`，NN 为下一可用序号 |
| 3 | 创建 index.html | 参考已有 index.html 的 CSS 和表格结构，初始化空记录表 |
| 4 | 更新 Pipeline index.html | 在对应 Pipeline 的 `index.html` 中追加新阶段 |
| 5 | 更新总览 index.html | 在 `SkillsRelationship_output/index.html` 路径速查表中追加一行 |
| 6 | 更新上下游 SKILL.md | 在上游 Skill 的「文件路径约定」中添加新输出；在下游 Skill 中添加新输入 |

### index.html 模板要求

- CSS 使用 GitHub Dark 主题（与 DocumentJournal_Daily 模板同款变量体系）
- 表格按序号递增追加记录
- 空记录时显示 `（暂无记录 — 运行 /{SkillName} 后自动追加）`
- 页头含面包屑导航（← 返回 Pipeline 总览）
- meta 行标注约定路径 + 生产者 + 消费者

### 已有文件夹的勾稽方式

如果新 Skill 复用已有文件夹的路径（如新因子检测 Skill 也产出到 `~/.gil_factors/`）：
- 不新建文件夹
- 在已有 `index.html` 中追加一个新表格分区（如「二、新 Skill 产出」）
- 更新 meta 行增加新消费者

> 完整目录树索引：`/Users/junye_shi/AgentFiles/SkillsRelationship_output/index.html`

---

## 禁止行为

- ❌ 跳过 Step 1-3 的任何确认步骤
- ❌ 替用户决定 Skill 名称（必须列出候选等待确认）
- ❌ 创建不符合命名规范的 Skill（参考架构文档 1.2 规则清单）
- ❌ 创建与已有 Skill 重名的 Skill
- ❌ 不更新 CSV 就声称"创建完成"
- ❌ 生成的 SKILL.md 使用空模板（必须根据用户描述填充具体内容）
- ❌ 跳过 Step 4c 的写入验证
- ❌ 跳过 Step 6 穿行测试就声称"创建完成"
- ❌ 穿行测试未通过但不修复协议缺口
- ❌ 在用户未确认时创建目录或写入文件
- ❌ 创建新 Skill 后发现命名不合规时，必须删除旧目录后重建，不得遗留空目录
- ❌ 创建过程中若任何步骤失败，必须清理已创建的目录后再报告错误
- ❌ 新 Skill 存在勾稽关系时，不维护 SkillsRelationship_output 目录树就声称"创建完成"
