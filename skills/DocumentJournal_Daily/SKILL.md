---
name: DocumentJournal_Daily
description: 工作日志追加 — 基于当前会话对话历史，生成结构化章节并追加到当日 MD+HTML 双格式日志。用户选择归属分类（ChinapostAMC / ScholarshipEarning / OtherRelationship）以区分文件存储路径。触发词：worklogue、工作日志、每日总结、写日志。
---

# /DocumentJournal_Daily — 工作日志追加

## 角色定位

工作日志记录 Agent。将本会话的工作内容总结为结构化章节，追加到当日日志文件。**全程仅基于本会话对话历史，严禁读取 memory 或其他窗口的文件内容。**

## 路由

本 Skill 不绑定特定 MCP Server。依赖：
- 文件系统读写（日志 MD + HTML 文件）
- `Bash` 工具（日期解析、目录守卫、锁操作、写入校验）
- `Read` / `Write` 工具（模板读取、文件写入）
- 会话对话历史（内存上下文，Step 6 回顾）

## 输入格式

用户直接调用，无需上游数据输入。Skill 激活后：
1. 从当前会话对话历史（内存上下文）提取工作内容
2. 从 `date` 命令获取当前日期
3. 从用户确认获取归属分类（Step 1.5）

可选参考文件（仅当存在时读取）：
- `~/.gil_factors/backtest_memory.md` — 回测决策记忆，日志中可引用为"今日回测发现"

## 与其他 Skill 的勾稽关系

| 上游/下游 | Skill | 数据流 |
|-----------|-------|--------|
| 上游（可选参考） | `ResearchGil_Report_Performance` | backtest_memory.md 中的回测结论 → 日志中可引用为"今日回测发现" |

本 Skill 的输入为当前会话对话历史（内存上下文），不从文件读取。输出为独立产物。

## 文件路径约定

日志文件存储路径由用户在 Step 1.5 中选择的**归属分类**决定：

| 归属分类 | 关键词 | 日志目录 | 年份子目录 |
|---------|--------|---------|:---------:|
| **ChinapostAMC** | 工作、本职、中邮 | `/Users/junye_shi/中邮资管/工作日志/{YEAR}/` | ✅ 有 |
| **ScholarshipEarning** | 学习、研究、探索 | `/Users/junye_shi/Scholarship is a new sexy/ScholarshipEarning/` | ❌ 无 |
| **OtherRelationship** | 其他、兴趣、个人 | `/Users/junye_shi/Scholarship is a new sexy/OtherRelationship/` | ❌ 无 |

| 角色 | 约定路径 | 说明 |
|------|----------|------|
| **输出** | `{日志目录}/{TODAY} worklogue.md` + `.html` | 当日工作日志双格式，`{日志目录}` 由分类决定 |
| 可选参考 | `~/.gil_factors/backtest_memory.md` | Report_Performance 产出的回测决策记忆，日志可引用 |

> 路径索引：`/Users/junye_shi/AgentFiles/SkillsRelationship_output/03_Document_Pipeline/02_Journal/index.html`

---

## 执行流程（9 步主流程 + 2 个可选步骤，严格顺序执行）

### Step 0：命令行标志解析（可选）

在进入主流程前，检查用户输入中是否包含以下可选标志：

| 标志 | 作用 | 示例 |
|------|------|------|
| `--category <值>` | 跳过 Step 1.5 交互，直接使用指定分类 | `--category A` 或 `--category ChinapostAMC` |
| `--date YYYY-MM-DD` | 覆盖当前日期（补记历史日志） | `--date 2026-07-01` |
| `--amend N` | 章节补充模式，N 为中文数字（见 Step 10） | `--amend 三` |

**`--category` 取值支持短码和全名**：

| 输入 | 等价于 | CATEGORY |
|------|:------:|----------|
| `A` / `ChinapostAMC` / `中邮` / `工作` | A | `ChinapostAMC` |
| `B` / `ScholarshipEarning` / `学习` / `研究` | B | `ScholarshipEarning` |
| `C` / `OtherRelationship` / `其他` / `个人` | C | `OtherRelationship` |

**解析逻辑**：
- 若提供 `--category`，将值匹配到 A/B/C（支持短码、全名、中文关键词）→ 按 Step 1.5 映射表设定 `CATEGORY` 和 `BASE_DIR` → **跳过 Step 1.5**
- 若值无法匹配任何分类 → 提示 `⚠️ 无法识别的分类 "<值>"，支持: A/ChinapostAMC/中邮, B/ScholarshipEarning/学习, C/OtherRelationship/其他`，回退到 Step 1.5 交互
- 若未提供 `--category` → 正常进入 Step 1.5
- 若提供 `--date` → 将 `TODAY` 和 `YEAR` 设为指定值，跳过 Step 1 的 `date` 命令
- 若提供 `--amend` → 标记 `AMEND_MODE=true`，`AMEND_CHAPTER="<N>"`，Step 9 后执行 Step 10

### Step 1：日期解析

获取当前日期（若未通过 `--date` 覆盖）：
- `TODAY` = `YYYY-MM-DD`（如 `2026-06-16`）
- `YEAR` = `YYYY`（如 `2026`）

```bash
TODAY=$(date +%Y-%m-%d)
YEAR=$(date +%Y)
```

### Step 1.5：归属分类确认（若 Step 0 已提供 `--category` 则跳过）

**若 Step 0 已通过 `--category` 设定 `CATEGORY` 和 `BASE_DIR`，则跳过本步骤，直接进入 Step 2。**

否则，Claude 必须向用户确认本次日志的归属分类。不允许自动推断。

向用户展示三个选项：

```
📋 本次日志归属分类？

  A) 中邮工作 — ChinapostAMC
     保存到: /Users/junye_shi/中邮资管/工作日志/{YEAR}/{TODAY} worklogue.md

  B) 学习探索 — ScholarshipEarning
     保存到: /Users/junye_shi/Scholarship is a new sexy/ScholarshipEarning/{TODAY} worklogue.md

  C) 其他/兴趣 — OtherRelationship
     保存到: /Users/junye_shi/Scholarship is a new sexy/OtherRelationship/{TODAY} worklogue.md

  请选择 [A / B / C]：
```

用户选择后，设定以下变量：

| 用户选择 | CATEGORY | 日志目录 BASE_DIR | 年份子目录 |
|---------|----------|-------------------|:---------:|
| A | `ChinapostAMC` | `/Users/junye_shi/中邮资管/工作日志/${YEAR}` | ✅ `${YEAR}/` |
| B | `ScholarshipEarning` | `/Users/junye_shi/Scholarship is a new sexy/ScholarshipEarning` | ❌ 无 |
| C | `OtherRelationship` | `/Users/junye_shi/Scholarship is a new sexy/OtherRelationship` | ❌ 无 |

**禁止**：替用户选择分类。必须等待用户明确回答 A/B/C。

### Step 2：目录守卫

确保目标目录存在：
```bash
mkdir -p "<BASE_DIR>/"
```

### Step 3：获取文件写锁

使用 `mkdir` 原子操作作为互斥锁，防止多窗口并发写冲突：
```bash
LOCK_DIR="/tmp/DocumentJournal_Daily_${CATEGORY}_${TODAY}.lock"
# 循环尝试 mkdir，最多等待 30 秒
for i in $(seq 1 60); do
  if mkdir "$LOCK_DIR" 2>/dev/null; then
    break
  fi
  sleep 0.5
done
```

`mkdir` 成功返回 0 且目录被创建 = 获取锁成功。若 60 次都失败（30s），报告"无法获取锁，可能其他窗口正在写入，请稍后重试"并终止。

### Step 4：文件审查

```bash
MD_FILE="<BASE_DIR>/${TODAY} worklogue.md"
```

检查 `MD_FILE` 是否存在：

- **不存在** → 创建新文件，写入一级标题：
  ```markdown
  # 工作日志 — ${TODAY}
  ```
  当前章节序号 = `一`

- **存在** → 跳到 Step 5 计算序号

### Step 5：序号计算

```bash
# 从已有 MD 中提取所有 ## X、 章节标题，计数
CHAPTER_COUNT=$(grep -c '^## [一二三四五六七八九十]、' "$MD_FILE" 2>/dev/null || echo 0)
```

当前章节序号 = `CHAPTER_COUNT + 1`，转为中文数字（映射表见下方）。

### Step 6：生成章节内容

**重要：信息源约束**
- ✅ 仅使用**本会话对话历史**中的内容
- ❌ 禁止读取 `~/.claude/projects/` 下的 memory 文件
- ❌ 禁止读取该目录下其他窗口创建的任何文件来推断"做了什么"
- ❌ 禁止通过 `ls`、`git log`、文件时间戳等推测其他窗口的活动

**回顾本会话**：浏览当前对话历史，识别：
1. 本次解决了什么问题 / 完成了什么任务
2. 涉及哪些文件（新建/修改）
3. 遇到了哪些问题、如何修复
4. 测试/验证结果
5. 还有哪些待完成

**按以下模板生成章节**（完整复刻现有日志风格）：

```markdown
## X、<章节主题>

### 1. 背景与目标

<一段话说明任务背景和要达成的目标>

### 2. 架构设计 / 实现文件

<列表或表格列出涉及的文件及其功能>

| 文件 | 功能 |
|------|------|
| `path/to/file.py` | 功能描述 |

### 3. 关键问题与修复

<如无问题可省略本节，或写"无重大问题">

| 类别 | 问题 | 修复 |
|------|------|------|
| 问题类别 | 具体问题描述 | 修复措施 |

### 4. 穿行测试 / 验证结果

<列表展示测试覆盖和结果>
- 测试项 1：结果
- 测试项 2：结果

### 5. 待完成 / 待部署

<为每个待完成项，在上方生成一行 HTML 注释作为结构化元数据，格式为：
  `<!-- task: <CATEGORY_PREFIX>-<NNN> | status: pending | priority: <high/medium/low> | files: <逗号分隔路径> -->`
  其中：
  - CATEGORY_PREFIX = `AMC` (ChinapostAMC) / `SCH` (ScholarshipEarning) / `OTH` (OtherRelationship)
  - NNN = 从 001 开始递增（全局序号，不按章节重置）
  - priority 依据：🔴=high, 🟡=medium, 无标记/🟢=low
  - files = 项中提及的文件路径，无可省略>

<列表列出下一步行动项，每项前有结构化注释>
- 待完成项 1
- 待完成项 2
```

**元数据示例**：
```markdown
<!-- task: AMC-001 | status: pending | priority: high | files: server.py, strategy.py -->
- [ ] **MCP server.py 同步新 CSV** — ``server.py`` 需新增 CSV 读取工具

<!-- task: AMC-002 | status: completed | priority: medium -->
- 演示前 30 分钟执行检查清单（DB 预热、MCP 状态确认、投屏测试）
```

> **向前兼容**：HTML 注释在渲染时不可见，旧版 Review 忽略注释仍能提取 `- ` 列表项。

**风格要求**：
- 信息密度高，大量使用表格压缩信息
- 术语规范：代码标识符用 ` `` ` 包裹，文件名/路径用 ` `` ` 包裹
- 数值表达：`~45 个候选`、`+1080.72%`、`偏差 0.5%`
- 状态标记：✅ / ❌ / 🆕 / ✏️
- 如本会话内容不足以填充某个小节（如"关键问题"为空），则省略该小节

### Step 7：追加写入 MD

```bash
# 将 Step 6 生成的章节内容追加到当日 MD 文件末尾
cat << 'CHAPTER_EOF' >> "$MD_FILE"

<Step 6 生成的完整章节 markdown>
CHAPTER_EOF
```

**🔒 写入校验（强制）**：

```bash
# 校验 1: 新章节标题已出现在 MD 文件末尾（最后 20 行内）
CHAPTER_TITLE=$(printf '%s' "${CHAPTER_NUM_CN}、${CHAPTER_TOPIC}")
if ! tail -20 "$MD_FILE" | grep -qF "## ${CHAPTER_TITLE}"; then
  echo "❌ 写入失败：新章节标题未在 MD 文件末尾 20 行内找到"
  # 回退措施：重新执行 cat 追加
  exit 1
fi
echo "✅ MD 写入验证通过: 第${CHAPTER_NUM_CN}章「${CHAPTER_TOPIC}」已追加"

# 校验 2: MD 文件行数合理（至少含标题行 + 本章内容 ≥ 3 行）
TOTAL_LINES=$(wc -l < "$MD_FILE")
if [ "$TOTAL_LINES" -lt 3 ]; then
  echo "❌ MD 文件异常: 仅 ${TOTAL_LINES} 行"
  exit 1
fi
echo "✅ MD 文件共 ${TOTAL_LINES} 行"
```

| 检查项 | 阈值 | 不达标处理 |
|--------|:----:|-----------|
| 新章节标题在文件末尾 | 最后 20 行内找到 | 重新追加写入 |
| MD 文件行数 | ≥ 3 行 | 报告异常并终止 |

### Step 8：渲染 HTML（Python 渲染器）

调用专用 Python 脚本完成 MD→HTML 转换与校验：

```bash
/opt/anaconda3/bin/python3 \
  ~/.claude/skills/DocumentJournal_Daily/render_html.py \
  "$MD_FILE" \
  "$HOME/.claude/skills/DocumentJournal_Daily/template.html" \
  "${MD_FILE%.md}.html" \
  "$TODAY"

if [ $? -ne 0 ]; then
  echo "❌ HTML 渲染失败，检查上方错误信息"
  exit 1
fi
echo "✅ HTML 渲染与校验已通过: ${MD_FILE%.md}.html"
```

**渲染器内部逻辑**（`render_html.py`）：
1. 读取 MD 文件，剥离 H1 标题行（模板 `<h1>` 已含日期）
2. 使用 Python `markdown` 库（extensions: extra, tables, fenced_code, sane_lists）转为 HTML
3. 使用 Jinja2 渲染 `template.html`：替换 `__DATE__` → `$TODAY`，注入 HTML → `{{CONTENT}}`
4. 内置 5 项校验（同下方校验表），任一失败则 exit 1

| 检查项 | 阈值 | 不达标处理 |
|--------|:----:|-----------|
| HTML 文件大小 | ≥ 500 字节 | exit 1，重新渲染 |
| 关键闭合标签 | `</html>` `</head>` `</body>` 均存在 | exit 1 |
| 占位符无残留 | 不含 `{{CONTENT}}` `__DATE__` | exit 1 |
| HTML ≥ MD × 80% | 是 | exit 1 |
| 含当日日期 | 是 | exit 1 |

### Step 9：释放锁并告知用户

```bash
rmdir "$LOCK_DIR"
```

**🔒 锁释放校验（强制）**：

```bash
# 校验锁目录已删除
if [ -d "$LOCK_DIR" ]; then
  echo "❌ 锁释放失败: $LOCK_DIR 仍存在，强制清理"
  rm -rf "$LOCK_DIR"
  if [ -d "$LOCK_DIR" ]; then
    echo "❌ 强制清理也失败，请手动删除: rmdir $LOCK_DIR"
    exit 1
  fi
fi
echo "✅ 锁已释放: $LOCK_DIR"
```

| 检查项 | 阈值 | 不达标处理 |
|--------|:----:|-----------|
| 锁目录已删除 | 不存在 | 强制 `rm -rf`；仍失败则提示手动删除 |

向用户输出：
> 已追加第 <中文数字> 章「<章节主题>」到 `[<CATEGORY>] <BASE_DIR>/${TODAY} worklogue.md`，MD + HTML 双文件已更新。
> 校验通过: MD ✅ | HTML ✅ | 锁释放 ✅

### Step 10：章节补充（仅 `--amend N` 模式）

若 Step 0 中提供了 `--amend N`（如 `--amend 三`），在主流程完成后执行本章节补充。

**定位章节**：
1. 读取 `$MD_FILE`，找到 `## N、` 标题行（如 `## 三、`）
2. 若章节不存在 → 报错终止：`❌ 章节 ${N} 不存在于当日日志中`
3. 定位该章节的结束位置：下一个 `## ` 行之前，或文件末尾

**生成补充内容**：
- 基于当前会话对话历史（同 Step 6 信息源约束）
- 按以下模板生成补充小节：

```markdown
### 6. 补充说明（${TODAY}）

<补充内容，按照 Step 6 风格要求>
```

**插入 MD**：
- 在目标章节的最后一个 `###` 小节之后、下一个 `## ` 之前插入
- 若为最后一章，直接追加到文件末尾

```bash
# 定位章节结束行（下一章标题前一行，或文件末尾）
NEXT_CHAPTER_LINE=$(awk '/^## / && NR > <chapter_start_line> {print NR; exit}' "$MD_FILE")
if [ -z "$NEXT_CHAPTER_LINE" ]; then
  NEXT_CHAPTER_LINE=$(wc -l < "$MD_FILE")
fi
# 在章节末尾前插入补充内容
```

**重新渲染 HTML**：
- 调用 Step 8 的 Python 渲染器重新生成 HTML（覆盖写入）
- 确保 MD 变更与 HTML 同步

```bash
/opt/anaconda3/bin/python3 \
  ~/.claude/skills/DocumentJournal_Daily/render_html.py \
  "$MD_FILE" \
  "$HOME/.claude/skills/DocumentJournal_Daily/template.html" \
  "${MD_FILE%.md}.html" \
  "$TODAY"
```

**告知用户**：
> 📝 第 <N> 章「<章节主题>」补充已添加，MD + HTML 已同步更新。

---

## 中文数字映射表

| 数字 | 中文 | 数字 | 中文 |
|------|------|------|------|
| 1 | 一 | 11 | 十一 |
| 2 | 二 | 12 | 十二 |
| 3 | 三 | 13 | 十三 |
| 4 | 四 | 14 | 十四 |
| 5 | 五 | 15 | 十五 |
| 6 | 六 | 16 | 十六 |
| 7 | 七 | 17 | 十七 |
| 8 | 八 | 18 | 十八 |
| 9 | 九 | 19 | 十九 |
| 10 | 十 | 20 | 二十 |

超过 20 时，直接使用数字（如 `21`）。

---

## 文件路径速查

| 用途 | 路径 |
|------|------|
| ChinapostAMC 日志目录 | `/Users/junye_shi/中邮资管/工作日志/<YYYY>/` |
| ChinapostAMC 当日 MD | `/Users/junye_shi/中邮资管/工作日志/<YYYY>/<YYYY-MM-DD> worklogue.md` |
| ScholarshipEarning 日志目录 | `/Users/junye_shi/Scholarship is a new sexy/ScholarshipEarning/` |
| ScholarshipEarning 当日 MD | `/Users/junye_shi/Scholarship is a new sexy/ScholarshipEarning/<YYYY-MM-DD> worklogue.md` |
| OtherRelationship 日志目录 | `/Users/junye_shi/Scholarship is a new sexy/OtherRelationship/` |
| OtherRelationship 当日 MD | `/Users/junye_shi/Scholarship is a new sexy/OtherRelationship/<YYYY-MM-DD> worklogue.md` |
| HTML 模板 | `~/.claude/skills/DocumentJournal_Daily/template.html` |
| 锁文件 | `/tmp/DocumentJournal_Daily_<CATEGORY>_<YYYY-MM-DD>.lock` |
| Python 渲染器 | `~/.claude/skills/DocumentJournal_Daily/render_html.py` |

---

## 禁止行为

- ❌ 在未提供 `--category` 时替用户决定归属分类（必须询问用户 A/B/C）
- ❌ 跳过 Step 7/8/9 的强制校验（任何校验失败必须阻断并修复）
- ❌ 读取 memory 或其他窗口文件推断工作内容
- ❌ 在校验未全部通过时告知用户"写入成功"
- ❌ `--amend` 模式下对不存在的章节号强行写入

## 关键约束

1. **信息源隔离**：总结内容仅来自本会话对话历史，不读 memory、不读文件、不读其他窗口输出
2. **追加而非覆盖**：MD 文件使用 `>>` 追加，HTML 文件通过 `render_html.py` 基于完整 MD 重建
3. **非交互支持**：`--category A/B/C` 可跳过交互确认；未提供时回退到 Step 1.5 交互
4. **并发安全**：`mkdir` 锁确保同一时刻只有一个窗口写入同一分类
5. **去重保护**：Step 4/5 的文件审查 + 序号计算确保不会重复创建 `#` 标题
6. **模板不动**：CSS / 字体 / 配色固定在模板中，Skill 执行时不改样式
7. **产出必验**：Step 7（MD 校验）/ Step 8（Python 渲染器内置校验）/ Step 9（锁释放校验）是强制门禁
8. **分类隔离**：不同归属分类的日志写入不同目录，锁按分类隔离，互不干扰
9. **结构化任务元数据**：待完成项必须包含 `<!-- task: ... -->` 注释，确保 Review 可靠解析
10. **章节可补充**：`--amend N` 支持对已有章节追加补充说明，自动同步 MD+HTML
