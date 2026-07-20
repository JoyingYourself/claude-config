---
name: DocumentJournal_Review
description: 日志回顾与任务追踪 — 读取前 3 个工作日 ChinapostAMC 日志，提取待完成项，交叉校验项目文件实际完成状态，对未完成项生成实现思路与任务规划。默认仅在对话窗口展示，传 --save 则额外落盘。触发词：/DocumentJournal_Review、日志回顾、review journal、任务追踪。
---

# /DocumentJournal_Review — 日志回顾与任务追踪

## 角色定位

日志回顾与任务追踪 Agent。读取前 3 个工作日 ChinapostAMC 日志，提取"待完成"条目，通过读取对应项目文件判断实际完成状态，对未完成项生成实现思路与任务规划，供用户决策是否执行。

**默认不落盘**：回顾报告直接在对话窗口展示。仅在用户传入 `--save` 时才额外写入本地文件。

## 路由

本 Skill 不绑定特定 MCP Server。依赖：
- `Bash` 工具（日期计算、工作日判断、文件搜索、Python 脚本执行）
- `Read` 工具（读取日志 MD 文件、读取项目文件、读取任务注册表 JSON）
- `Write` 工具（`--save` 时落盘回顾报告 + 每次 Review 更新任务注册表 JSON）
- Python 3（注册表 JSON 操作）

## 与其他 Skill 的勾稽关系

| 上游/下游 | Skill | 数据流 |
|-----------|-------|--------|
| 上游 | `DocumentJournal_Daily` | Daily 产出的 ChinapostAMC 日志 MD → Review 读取并提取待完成项 |
| 下游 | 用户决策 | Review 输出实现思路与任务规划 → 用户判断是否执行 |

本 Skill 的输出（回顾报告）为独立产物，供用户查阅。用户确认后可在新会话中执行未完成项。

## 文件路径约定

| 角色 | 约定路径 | 说明 |
|------|----------|------|
| **输入** | `/Users/junye_shi/中邮资管/工作日志/{YEAR}/{YYYY-MM-DD} worklogue.md` | 前 3 个工作日 ChinapostAMC 日志 |
| **输出** | `/Users/junye_shi/中邮资管/工作日志/{YEAR}/review-{YYYY-MM-DD}.md` | 回顾报告（仅 `--save` 时落盘，默认仅对话展示） |

---

## 执行流程（6 步主流程 + 3 个新增步骤，严格顺序执行）

### Step 0：标志解析 + 任务注册表加载

**A. 解析命令行标志**：

| 标志 | 作用 | 默认 |
|------|------|:--:|
| `--category <值>` | 仅审查指定分类（支持短码/全名/中文） | 默认 A（ChinapostAMC，向后兼容） |
| `--all` | 审查所有三分录 | — |
| `--save` | 回顾报告额外落盘 | 默认仅对话展示 |

**`--category` 取值支持短码和全名**：

| 输入 | 等价于 | CATEGORY |
|------|:------:|----------|
| `A` / `ChinapostAMC` / `中邮` / `工作` | A | `ChinapostAMC` |
| `B` / `ScholarshipEarning` / `学习` / `研究` | B | `ScholarshipEarning` |
| `C` / `OtherRelationship` / `其他` / `个人` | C | `OtherRelationship` |

分类映射：

| 标志 | CATEGORY | BASE_DIR |
|------|----------|----------|
| `--category A` | `ChinapostAMC` | `/Users/junye_shi/中邮资管/工作日志/${YEAR}` |
| `--category B` | `ScholarshipEarning` | `/Users/junye_shi/Scholarship is a new sexy/ScholarshipEarning` |
| `--category C` | `OtherRelationship` | `/Users/junye_shi/Scholarship is a new sexy/OtherRelationship` |
| `--all` | 全部三类 | 三类 BASE_DIR 均读取 |

**B. 加载/初始化任务注册表**：

```bash
REGISTRY_FILE="$HOME/.claude/journal_task_registry.json"

if [ -f "$REGISTRY_FILE" ]; then
  echo "📋 任务注册表已加载: $REGISTRY_FILE"
else
  echo "🆕 首次运行，将创建任务注册表"
fi
```

注册表 JSON Schema（首次运行时自动初始化）：

```json
{
  "schema_version": 1,
  "updated_at": "",
  "categories": {
    "ChinapostAMC": { "task_counter": 0, "tasks": {} },
    "ScholarshipEarning": { "task_counter": 0, "tasks": {} },
    "OtherRelationship": { "task_counter": 0, "tasks": {} }
  }
}
```

### Step 1：计算回顾日期范围

**目标**：确定前 3 个工作日（不含今日），跳过周六日。

```bash
TODAY=$(date +%Y-%m-%d)
TODAY_DOW=$(date +%u)  # 1=Mon ... 7=Sun
```

**工作日回溯逻辑**（按优先级执行）：

| 今日 | 回溯天数 | 实际覆盖 |
|------|:------:|------|
| 周一 | 3 天 | 上周五 + 上周四 + 上周三 |
| 周二～周五 | 3 天 | 昨日 + 前日 + 再前日 |
| 周六 | 1 天 | 周五 + 周四 + 周三 |
| 周日 | 2 天 | 周五 + 周四 + 周三 |

**实现方式**：使用 Bash 循环，逐日回退，跳过周六（6）和周日（7），累计收集满 3 个工作日：

```bash
WORK_DATES=()
CURRENT=$(date -v-1d +%Y-%m-%d)  # 从昨天开始
while [ ${#WORK_DATES[@]} -lt 3 ]; do
  DOW=$(date -j -f "%Y-%m-%d" "$CURRENT" +%u 2>/dev/null || date -d "$CURRENT" +%u 2>/dev/null)
  if [ "$DOW" != "6" ] && [ "$DOW" != "7" ]; then
    WORK_DATES+=("$CURRENT")
  fi
  # macOS: CURRENT=$(date -j -v-1d -f "%Y-%m-%d" "$CURRENT" +%Y-%m-%d)
  # Linux: CURRENT=$(date -d "$CURRENT -1 day" +%Y-%m-%d)
done
```

输出：`WORK_DATES` 数组含 3 个工作日日期（YYYY-MM-DD），从近到远排列。

### Step 2：读取日志文件

对 `WORK_DATES` 中的每个日期，根据 Step 0 确定的分类列表，读取对应日志：

| CATEGORY | 日志路径模式 |
|----------|-------------|
| `ChinapostAMC` | `/Users/junye_shi/中邮资管/工作日志/{YEAR}/{DATE} worklogue.md` |
| `ScholarshipEarning` | `/Users/junye_shi/Scholarship is a new sexy/ScholarshipEarning/{DATE} worklogue.md` |
| `OtherRelationship` | `/Users/junye_shi/Scholarship is a new sexy/OtherRelationship/{DATE} worklogue.md` |

> **注意**：ScholarshipEarning 和 OtherRelationship 目录无年份子目录，直接从 BASE_DIR 读取。

**容错**：若某个日期/分类的日志文件不存在（如假期、该分类当天未写日志），跳过并计入统计，继续读下一个。

### Step 3：提取"待完成"条目（双重策略）

对每篇日志，定位 `待完成` 或 `待部署` 标题行（`###` 级别），使用双重策略提取：

**策略 A：结构化元数据提取（优先）**
1. 在"待完成"标题与下一个 `###` 或 `##` 之间，搜索 `<!-- task:` 注释行
2. 解析管道符分隔的键值对：
   - `task` → 任务 ID（如 `AMC-001`）
   - `status` → 状态（`pending` / `completed` / `in_progress` / `deferred`）
   - `priority` → 优先级（`high` / `medium` / `low`）
   - `files` → 关联文件路径（逗号分隔，可选）
   - `tags` → 标签（逗号分隔，可选）
3. 读取紧跟在注释后的列表项（`- ` 或 `- [ ]`）作为任务描述
4. 记录：{元数据所有字段 + 原始描述 + 来源日期 + 来源章节主题 + 来源分类}

**策略 B：旧格式回退（策略 A 未匹配到的项）**
1. 在同一标题块中，提取未被策略 A 覆盖的 `- ` 列表项
2. 按原规则提取：描述 + 来源日期 + 章节主题 + 来源分类
3. 检查描述中是否有已知的任务 ID 模式（`[A-Z]+-\d+`）
4. 如包含文件路径（`` `...` ``），提取为 `file_ref`

**兼容处理**（两种策略共用）：
- 若包含"已完成""已修复""✅"标记 → 自动识别为已完成状态
- 若为纯描述性文本无文件引用 → 保留为上下文相关的待确认项

> **向前兼容**：日志中无 `<!-- task:` 注释时，全部通过策略 B 提取，行为与旧版一致。

### Step 3.5：与任务注册表合并

对 Step 3 提取的每个待完成项，与注册表进行合并：

**A. 项有任务 ID（来自策略 A 元数据）**：
- ID 在注册表中 → 更新 `last_review_date`、`status`（若 md 中标记为 completed 则更新）、追加 `status_history`
- ID 不在注册表中 → 在注册表中创建新条目，`task_counter` 递增

**B. 项无任务 ID（来自策略 B 回退）**：
- 取描述的前 40 字符作为模糊匹配键
- 在注册表同分类中查找相似 summary 的任务
- 匹配成功 → 关联已有 ID，更新审核日期
- 匹配失败 → 创建新条目，分配新 ID，`task_counter` 递增

**C. 注册表中的任务在本次日志中未出现**：
- 状态为 `pending` 或 `in_progress` → 保持原状态（任务可能仍在进行中）
- 若连续 2 次 Review 未出现 → 标记为 `deferred`（低优先级或暂停）
- 状态为 `completed` → 保持不变

**实现**：使用 Python 单行脚本操作 JSON：

```bash
/opt/anaconda3/bin/python3 -c "
import json, sys
reg = json.load(open('$REGISTRY_FILE'))
# ... 合并逻辑 ...
json.dump(reg, open('$REGISTRY_FILE', 'w'), ensure_ascii=False, indent=2)
"
```

### Step 4：交叉校验完成状态

对每个待完成项，根据其内容判断是否需要查文件：

**A. 有明确文件路径的项**：
```bash
# 检查文件是否存在
test -f "<extracted_path>"
# 检查文件内容是否含关键变更（通过 grep 搜索项中关键词）
```

判断逻辑：
- 文件存在 + 内容含关键变更 → ✅ 已完成
- 文件存在 + 但内容不匹配 → ⚠️ 部分完成（文件存在但可能不完整）
- 文件不存在 → ❌ 未开始
- 文件已修改时间晚于日志日期 → ✅ 已完成（后续会话中完成）

**B. 无文件路径但描述具体任务**：
- 通过任务关键词在相关项目目录中搜索：
  ```bash
  # 在 Chinapost 相关项目路径下搜索
  find /Users/junye_shi/中邮资管 -name "*.py" -newer "<日志日期>" 2>/dev/null | head
  ```
- 若找到相关变更 → 🔍 疑似已完成（列出找到的证据）
- 若无相关变更 → ⚠️ 待确认（无法自动判断）

**C. 纯描述性待完成项**（如"跟进XX事项"）：
- 标记为 👤 需人工确认（无法自动校验）

### Step 5：生成未完成项的实现思路

对于状态为 ⚠️ 或 ❌ 的项，根据内容生成实现思路：

**生成原则**：
1. 读取项中涉及的项目目录结构（`ls` 相关路径），了解已有代码上下文
2. 分析任务描述中的目标，拆解为可执行的子步骤
3. 列出需要的文件变更（新建/修改）
4. 标注关键技术点和潜在风险
5. 给出预估工作量（小/中/大）

**输出格式**（每个未完成项）：

```markdown
### {序号}. {任务简述}

- **ID**：{task_id}（来自注册表，未注册的标注 🆕）
- **来源**：{日期} 日志 · [{分类}] 第{X}章「{章节主题}」
- **状态**：{❌/⚠️/🔍}
- **审核历史**：{从注册表 status_history 读取，如"07-05 首次检测 pending → 07-06 持续 pending"}
- **证据**：{文件检查结果摘要}

**实现思路**：

1. {子步骤1}
2. {子步骤2}
...

**涉及文件**：
- `{新建/修改}` `path/to/file` — {说明}

**关键注意**：{技术要点或风险提示}

**预估工作量**：{小/中/大}（{具体说明}）
```

### Step 6：输出回顾报告

**默认行为**：在对话窗口直接展示回顾报告（Markdown 格式），不写文件。

**`--save` 模式**：用户传入 `--save` 时，在对话展示的同时，额外写入文件：

```
<BASE_DIR>/review-{YYYY-MM-DD}.md
```

多分类（`--all`）时，报告写入 ChinapostAMC 的 BASE_DIR。

**多分类报告**：当 `--all` 时，报告按分类分组：

```markdown
# 任务回顾报告 — {TODAY}

> 回顾范围：{DATE1} ~ {DATE3}（前 3 个工作日）
> 日志文件：{N} 篇（ChinapostAMC: {n1}, ScholarshipEarning: {n2}, OtherRelationship: {n3}）
> 提取待完成项：{M} 项
> 注册表任务总数：{R} 项

---

## 一、概览

| 分类 | 日志 | 待完成 | ✅ 已 | ⚠️ 部分 | ❌ 未 | 👤 人工 |
|------|:--:|:-----:|:----:|:------:|:---:|:-----:|
| ChinapostAMC | {n1} | {m1} | {a1} | {b1} | {c1} | {d1} |
| ScholarshipEarning | {n2} | {m2} | {a2} | {b2} | {c2} | {d2} |
| OtherRelationship | {n3} | {m3} | {a3} | {b3} | {c3} | {d3} |

| 状态 | 数量 | 说明 |
|------|:----:|------|
| ✅ 已完成 | {n1} | 项目文件确认已完成 |
| ⚠️ 部分完成 | {n2} | 文件存在但不完整 |
| ❌ 未开始 | {n3} | 对应文件不存在或无变更 |
| 👤 需人工确认 | {n4} | 无法自动校验（纯描述性任务） |
| 🗄️ 注册表存量 | {n5} | 注册表中仍在跟踪的任务 |

---

## 二、ChinapostAMC

### 已完成项
| # | 任务 | 来源日期 | 证据 |
|---|------|:------:|------|
| 1 | ... | 07-05 | 文件已创建 |

### 未完成项 — 实现思路
...

---

## 三、ScholarshipEarning（若有）

...

---

## 四、OtherRelationship（若有）

...
```

**单分类报告**（`--category A/B/C` 或无标志）：仅输出对应分类的章节，格式同上。

### Step 6.5：保存任务注册表

```bash
/opt/anaconda3/bin/python3 -c "
import json, os
reg_path = os.path.expanduser('$REGISTRY_FILE')
with open(reg_path) as f:
    reg = json.load(f)
reg['updated_at'] = '$TIMESTAMP'
# 按分类对任务排序，使 git diff 更清晰
for cat in reg['categories']:
    tasks = reg['categories'][cat]['tasks']
    reg['categories'][cat]['tasks'] = dict(sorted(tasks.items()))
with open(reg_path, 'w') as f:
    json.dump(reg, f, ensure_ascii=False, indent=2)
print(f'✅ 任务注册表已保存: {reg_path}')
print(f'   总任务数: {sum(len(c[\"tasks\"]) for c in reg[\"categories\"].values())}')
"
```

---

## 禁止行为

- ❌ 修改任何日志文件或项目文件
- ❌ 自动执行待完成项（仅生成规划，由用户决策）
- ❌ 跳过 Step 1 的日期计算直接硬编码日期
- ❌ 对无法校验的项强行判断"已完成/未完成"（标记为"需人工确认"）
- ❌ 未传 `--save` 时写入本地文件（默认仅对话展示；注册表文件除外）
- ❌ 删除或清空任务注册表中的历史记录（仅追加更新）

## 关键约束

1. **只读优先**：除注册表更新和 `--save` 落盘外，全程不写任何文件
2. **默认对话展示**：回顾报告直接在对话窗口呈现，减少文件维护负担
3. **默认 ChinapostAMC**：无 `--category` 或 `--all` 标志时仅审查 ChinapostAMC，向后兼容
4. **工作日感知**：自动跳过周末，确保覆盖真实的 3 个工作日
5. **容错处理**：缺失的日志文件不阻断流程，记录并继续
6. **证据驱动**：每个完成状态的判断必须有文件检查结果作为证据
7. **Uncertainty 标注**：无法自动判断的项标记为"需人工确认"，不强行给出结论
8. **实现思路要具体**：不能是"建议完成该任务"，而要给出具体的文件、步骤、注意事项
9. **注册表持久化**：每次 Review 自动更新注册表，确保任务状态跨会话追踪
10. **结构化优先**：优先解析 `<!-- task:` 元数据，无元数据时回退到原始正则提取
