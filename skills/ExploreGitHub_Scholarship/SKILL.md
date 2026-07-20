---
name: ExploreGitHub_Scholarship
description: 全自动 GitHub 趋势项目发现与深度分析 — 三级分层(L1 Claude Code生态固定三方向 + L2 最近3条lesson驱动 + L3 用户指定)，分层搜索→克隆→深度源码分析→三章分层报告(MD+HTML)。触发词：github 趋势、github 项目分析、github scholarship、每周扫描、发现新项目。
---

# /ExploreGitHub_Scholarship — 全自动 GitHub 趋势项目分析

## 角色定位

全自动研究 Agent。执行 **三级分层搜索 → 深度源码分析 → 三章分层报告 + 更新检查** 工作流。**全程无需用户交互确认，自动推进。**

三个层级各有独立配额和选取策略：
- **L1**：Claude Code 生态 3 固定方向，每方向 3 项目（高星优先）
- **L2**：最近 3 条 lesson 驱动，每条 lesson 5 项目（高星 + 相关等权重）
- **L3**：用户指定关键词，每关键词 5 项目（相关度优先）

## 与其他 Skill 的勾稽关系

本 Skill 独立运行，无上下游文件依赖。产出分析报告（MD+HTML），仅供用户直接查阅。

> 路径索引：`/Users/junye_shi/AgentFiles/SkillsRelationship_output/index.html`（见「独立 Skill」）

---

## 三级分层体系

### Level 1：Claude Code 生态 — 固定三方向（3 方向 × 3 项目 = 9 项目）

聚焦 Claude Code 核心生态，每次执行必覆盖：

| # | 方向 | 搜索关键词 | 选取策略 |
|---|------|-----------|---------|
| L1-1 | **Claude Code MCP 生态** | `GitHub Claude Code MCP server tool plugin 2026 stars` | 高星优先，3 项目 |
| L1-2 | **Claude Code Skills 生态** | `GitHub Claude Code custom slash command skill workflow automation 2026` | 高星优先，3 项目 |
| L1-3 | **Claude Code Agent 框架生态** | `GitHub Claude Code agent SDK multi-agent orchestration framework 2026` | 高星优先，3 项目 |

**去重规则**：读取 `/Users/junye_shi/Scholarship is a new sexy/github_related/projects_tracker.csv`，与 `project_name` 列对比。已存在的项目不重复选取，顺位递补。选取后**立即追加**到 CSV 中（先写 CSV 再 clone，防止中断丢记录）。

**搜索策略**：每个方向可执行 1-2 路 WebSearch（不同角度关键词），合并去重后取 top 3 by stars。

### Level 2：最近 3 条 Lesson 驱动（3 lesson × 5 项目 = 15 项目）

**Step 2A：定位最近 3 条 lesson**

```bash
# 从 lessons.md 提取所有日期标题，按日期降序取前 3
grep -n '^## [0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}' ~/.claude/lessons.md | tail -3
```

> 注意：lessons.md 中条目按时间倒序追加，`tail -3` 取的是**文件末尾 3 条** = 最新 3 条。如果文件结构调整，改用日期排序取前 3。

**Step 2B：逐条提取关键词**

对每条 lesson 执行：

1. 读取完整条目内容（从 `## YYYY-MM-DD — 标题` 到下一个 `##` 或 `---`）
2. 提取以下字段作为关键词来源：

| 字段 | 提取方式 | 权重 |
|------|---------|:---:|
| **标签** (`**标签**:`) | 直接读取，去掉 `#` 前缀 | 最高 |
| **场景** (`**场景**:`) | 提取名词短语（工具名、技术栈、协议名） | 中 |
| **根因** (`**根因**:`) | 提取核心问题域（如"超时""单线程串行""伪端到端"） | 中 |
| **规则** (`**规则**:`) | 提取解决方案方向（如"产物检查""进程监控""穿行测试"） | 低 |

3. 综合生成 2-3 个搜索关键词，格式：`GitHub <lesson核心问题域> <lesson隐含的解决方案> 2026`

**Step 2C：搜索与选取**

每 2-3 个关键词合并为 1 路搜索。每条 lesson 选取 **5 个项目**，权重：

```
综合评分 = 0.5 × stars_normalized + 0.5 × relevance_score
```

- `stars_normalized`：该项目 star 数 / 该搜索结果中最高 star 数
- `relevance_score`：项目 README/描述与 lesson 问题的语义匹配度（由 Agent 判断，1-10 分）

**示例**（基于当前 lessons.md 最新 3 条）：

```
Lesson 1: "MCP 客户端超时 30s 不可配置" (标签: MCP, 超时, compose, 工作流)
  → 关键词: MCP timeout monitoring, server health check, process observability
  → 搜索: "GitHub MCP server timeout monitoring health check tools 2026"

Lesson 2: "MCP 超时报错≠操作失败:先检查文件系统产物"
  → 关键词: MCP async task tracking, file system watcher, output monitoring
  → 搜索: "GitHub MCP async task output monitoring file watcher 2026"

Lesson 3: "MCP 超时先查服务器状态(CPU/进程)"
  → 关键词: process monitor, server resource diagnostic, MCP health dashboard
  → 搜索: "GitHub process monitor server diagnostic dashboard MCP 2026"
```

### Level 3：用户指定关键词（M 关键词 × 5 项目）

用户调用时传入，逗号分隔：

```
/ExploreGitHub_Scholarship MCP observability dashboard, backtesting framework comparison
```

| 用户输入 | 搜索 query | 选取策略 |
|---------|-----------|---------|
| `MCP observability dashboard` | 直接使用，拼接 `GitHub <输入> 2026` | 相关度优先，5 项目 |
| `backtesting framework comparison` | 直接使用，拼接 `GitHub <输入> 2026` | 相关度优先，5 项目 |

- 每个关键词 1-2 路搜索，选取 **5 个最相关**项目
- 与 L1/L2 结果去重（已选取的项目不重复）

### 三级去重汇总

```
候选池 = L1 (9 项目) + L2 (15 项目) + L3 (5 × M 项目)
       ≈ 24-34 项目（去重后约 20-30）
```

去重优先级（保留高优先级版本）：**L1 > L2 > L3**

> ⚠️ 候选池较大（20-30 项目），所有项目均执行深度源码分析。最终报告约 3-5 万字，预计执行时间 30-60 分钟。

---

## 自动工作流

### 阶段 1：L1 搜索（3 方向，并行）

```
每方向 1-2 路 WebSearch 并行 → 合并去重 → 按 stars 排序 → 取 top 3
→ 与 projects_tracker.csv 历史项目去重 → 顺位递补
```

**输出**：L1 候选列表（9 个项目，标注方向来源和 star 数）

### 阶段 2：L2 搜索（3 lesson，串行处理）

```
Step A: 定位最近 3 条 lesson 标题
Step B: 逐条读取完整内容，提取关键词
Step C: 每 lesson 1-2 路 WebSearch
Step D: 综合评分 = 0.5×stars_norm + 0.5×relevance → 取 top 5
```

**输出**：L2 候选列表（15 个项目，标注来源 lesson 标题和综合评分）

### 阶段 3：L3 搜索（M 关键词，并行）

```
每关键词 1-2 路 WebSearch → 按相关度排序 → 取 top 5
```

**输出**：L3 候选列表（5×M 个项目，标注来源关键词）

### 阶段 4：三级汇总去重

```
合并 L1+L2+L3 → 去重(L1>L2>L3) → 输出最终候选池
```

打印汇总表：每项目的名称/stars/来源级别/来源方向，标注去重剔除的项目。

### 阶段 5：下载（并行 git clone）

```bash
BASE="/Users/junye_shi/Scholarship is a new sexy/github_related/github_related<YYYYMMDD>"
mkdir -p "$BASE/L1" "$BASE/L2" "$BASE/L3"
```

**多策略 clone 协议**（每项目必须依次尝试，不可因为一种方式失败就跳过）：

```bash
clone_with_fallback() {
  local org_repo=$1 level=$2
  local name=$(echo "$org_repo" | tr '/' '_')
  local url="https://github.com/${org_repo}.git"
  local dest="$BASE/$level/${name}-src"
  local tmpdir="/tmp/cc_clone_${name}_$$"

  echo "[$level] Cloning $org_repo..."

  # 策略 1: HTTPS git clone --depth 1（最快，首选）
  if git clone --depth 1 --single-branch "$url" "$tmpdir" 2>/dev/null; then
    echo "  ✅ HTTPS → $level/${name}-src"
    cp -r "$tmpdir" "$dest" && rm -rf "$tmpdir"
    return 0
  fi
  echo "  ⚠️ HTTPS 失败，尝试策略 2..."

  # 策略 2: SSH git clone（如果配置了 SSH key）
  local ssh_url="git@github.com:${org_repo}.git"
  if git clone --depth 1 --single-branch "$ssh_url" "$tmpdir" 2>/dev/null; then
    echo "  ✅ SSH → $level/${name}-src"
    cp -r "$tmpdir" "$dest" && rm -rf "$tmpdir"
    return 0
  fi
  echo "  ⚠️ SSH 失败，尝试策略 3..."

  # 策略 3: gh repo clone（GitHub CLI，可能有不同的认证/网络路径）
  if command -v gh &>/dev/null && gh repo clone "$org_repo" "$tmpdir" -- --depth 1 2>/dev/null; then
    echo "  ✅ gh CLI → $level/${name}-src"
    cp -r "$tmpdir" "$dest" && rm -rf "$tmpdir"
    return 0
  fi
  echo "  ⚠️ gh CLI 失败，尝试策略 4..."

  # 策略 4: tarball 下载（绕过 git 协议，走 HTTPS 下载）
  # 获取默认分支
  local branch=$(curl -sL "https://api.github.com/repos/${org_repo}" 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('default_branch','main'))" 2>/dev/null || echo "main")
  local tarball_url="https://github.com/${org_repo}/archive/refs/heads/${branch}.tar.gz"
  mkdir -p "$tmpdir"
  if curl -sL --connect-timeout 30 --max-time 120 "$tarball_url" 2>/dev/null | tar -xz -C "$tmpdir" --strip-components=1 2>/dev/null; then
    echo "  ✅ tarball ($branch) → $level/${name}-src"
    cp -r "$tmpdir" "$dest" && rm -rf "$tmpdir"
    return 0
  fi

  # 策略 5: tarball 用 main 分支重试（如果默认分支检测失败）
  if [ "$branch" != "main" ]; then
    tarball_url="https://github.com/${org_repo}/archive/refs/heads/main.tar.gz"
    rm -rf "$tmpdir" && mkdir -p "$tmpdir"
    if curl -sL --connect-timeout 30 --max-time 120 "$tarball_url" 2>/dev/null | tar -xz -C "$tmpdir" --strip-components=1 2>/dev/null; then
      echo "  ✅ tarball (main fallback) → $level/${name}-src"
      cp -r "$tmpdir" "$dest" && rm -rf "$tmpdir"
      return 0
    fi
  fi

  # 全部失败
  rm -rf "$tmpdir"
  echo "  ❌ ALL STRATEGIES FAILED: $org_repo"
  return 1
}
```

**策略优先级**：
| 策略 | 方式 | 优点 | 适用场景 |
|:---:|------|------|------|
| 1 | `git clone --depth 1` HTTPS | 最快，深度1 | 常规项目 |
| 2 | `git clone --depth 1` SSH | 不同认证通道 | HTTPS 被墙/限流 |
| 3 | `gh repo clone` | GitHub CLI 独立认证 | 前两种都失败 |
| 4 | tarball `curl` + `tar` | 纯 HTTPS 下载，绕过 git 协议 | 大型仓库/网络不稳定 |
| 5 | tarball fallback (main) | 兜底分支名 | 默认分支检测失败 |

**关键规则**：
- `<YYYYMMDD>` 为当天完整日期（如 `20260713`）
- 项目统一以 `<org>_<repo>-src` 命名，放在对应级别的子目录下
- **5 种策略全部失败才能标记为 FAILED**
- 每种策略之间间隔 2s（避免 GitHub 限流）
- 同一项目不同策略失败后不要立即跳过——下一个策略可能成功
- clone 成功后必须记录是哪种策略成功的（用于后续优化）
- 文件夹结构：
  ```
  github_related<YYYYMMDD>/
  ├── github_related<MMDD>.md        ← Markdown 分析报告
  ├── github_related<MMDD>.html      ← HTML 分析报告
  ├── L1/
  │   ├── <org>_<repo>-src/
  │   └── ...
  ├── L2/
  │   ├── <org>_<repo>-src/
  │   └── ...
  └── L3/
      ├── <org>_<repo>-src/
      └── ...
  ```

### 阶段 6：深度源码分析（三轮阅读）

对每个成功克隆的项目执行。分析深度标准同原 Skill：

- **第一轮**：结构扫描（`find -maxdepth 3`，识别关键文件）
- **第二轮**：核心子系统深读（编排器/状态机/验证/Agent 定义/MCP 工具）
- **第三轮**：实现细节补充

**每项目至少阅读 4-6 个关键源文件，提取 ≥ 2 段代码片段。**

### 阶段 7：已引入项目更新检查（独立于本次配额）

**目标**：检查 CSV 中 `introduced=yes` 的项目是否有新版本发布，自动下载更新。

**Step 7A：读取待检查列表**

```bash
# 从 CSV 提取 introduced=yes 的项目
grep ',yes,' /Users/junye_shi/Scholarship is a new sexy/github_related/projects_tracker.csv \
  | cut -d',' -f1,4  # project_name + version
```

**Step 7B：逐个检查更新**（通过 GitHub API，串行执行）

```bash
# 对每个项目，检查最近的 releases/tags
gh release list --repo <org/repo> --limit 1 --json tagName,publishedAt 2>/dev/null
# 或对比 latest commit
gh api repos/<org/repo>/commits/HEAD --jq '.sha[:7]' 2>/dev/null
```

- 对比 CSV 中记录的 `version` 与当前最新版本
- 相同 → 跳过，标注"无更新"
- 不同 → 标记为"有更新"

**Step 7C：下载更新**

对有更新的项目，clone 到当次扫描目录下的 `_updates/` 子目录（不占 L1/L2/L3 配额）：

```bash
mkdir -p "$BASE/_updates"
cd "$BASE/_updates"
git clone --depth 1 <repo_url> <org>_<repo>-update-<YYYYMMDD>
```

**Step 7D：生成更新摘要**

对比新旧版本，提取：
- 版本变化（tag A → tag B）
- 新增功能（从 CHANGELOG/Release Notes）
- 对当前工作的潜在影响

> ⚠️ 网络失败或 API 限流时，记录失败原因并跳过，不影响主流程。

### 阶段 8：输出三章分层报告 + 更新摘要

全部产物放在同一个文件夹下：

```
/Users/junye_shi/Scholarship is a new sexy/github_related/github_related<YYYYMMDD>/
├── github_related<MMDD>.md      ← Markdown 分析报告（文件名沿用 MMDD 格式）
├── github_related<MMDD>.html    ← HTML 分析报告（自动打开）
├── L1/
│   ├── <org>_<repo>-src/
│   └── ...
├── L2/
│   ├── <org>_<repo>-src/
│   └── ...
└── L3/
    ├── <org>_<repo>-src/
    └── ...
```

同时更新 `INDEX.md` 和 `projects_tracker.csv`。

---

## 报告内容模板（三章分层结构）

```markdown
# 🔥 GitHub Claude Code 生态 + 记忆驱动项目深度解析
> 检索时间：YYYY年MM月DD日 | 全自动执行 | 三级分层 | 覆盖 N 个项目

## 目录

## 第一章：Claude Code 核心生态（L1 固定方向，9 项目）

### 1.1 MCP 方向 — 3 项目深度解析
> 来源：L1 固定方向 — Claude Code MCP 生态
> 选取策略：高星优先，与历史项目去重

#### 项目 1：<org/repo>（⭐ X,XXX）
[完整深度分析：源码结构 / 核心设计模式 / 关键特性 / 代码片段]

#### 项目 2：...
#### 项目 3：...

**📊 MCP 方向引入优先级建议**：
| 优先级 | 项目 | 理由 |
|:---:|------|------|
| 🔴 优先 | ... | ... |
| 🟡 可选 | ... | ... |
| 🟢 观望 | ... | ... |

### 1.2 Skills 方向 — 3 项目深度解析
> 来源：L1 固定方向 — Claude Code Skills 生态

[同上结构]

### 1.3 Agent 框架方向 — 3 项目深度解析
> 来源：L1 固定方向 — Claude Code Agent 框架生态

[同上结构]

## 第二章：记忆驱动发现（L2 最近 3 条 Lesson，15 项目）

### 2.1 来自 Lesson：「<标题1>」— 5 项目
> 来源：L2 记忆驱动 — ~/.claude/lessons.md 最新第 1 条
> Lesson 日期：YYYY-MM-DD | 标签：tag1, tag2
> 搜索关键词：<L2 提取的关键词>

#### 项目 1-5：[同上深度分析结构]

**📊 解决方案优先级**：[表格]

### 2.2 来自 Lesson：「<标题2>」— 5 项目
> 同上

### 2.3 来自 Lesson：「<标题3>」— 5 项目
> 同上

## 第三章：定向探索（L3 用户指定，5×M 项目）

### 3.1 来自关键词：「<关键词1>」— 5 项目
> 来源：L3 用户指定
> 选取策略：相关度优先

#### 项目 1-5：[同上深度分析结构]

**📊 推荐优先级**：[表格]

### 3.2 来自关键词：「<关键词2>」— 5 项目
> 同上

## 附录
- A. 项目本地路径（按来源级别分组）
- B. 去重剔除清单（项目名 / 被谁去重 / 原因）
- C. 本次扫描统计（L1/L2/L3 各搜到多少、去重多少、最终克隆多少、分析多少）
- D. L2 Lesson 关键词提取明细（3 条 lesson 的提取过程）
- E. 已引入项目更新检查结果（检查了 N 个，发现 M 个更新，下载了 K 个）

## 附章：已引入项目更新报告

> 本节列出本次扫描中发现的已引入项目更新。更新项目不占本次配额。

| 项目 | 旧版本 | 新版本 | 更新内容 | 影响评估 |
|------|--------|--------|---------|:---:|
| org/repo | v1.0.0 | v1.2.0 | 新增XXX功能；修复YYY | 🔴高/🟡中/🟢低 |

无更新则标注：「本次检查 N 个已引入项目，均无可用更新。」
```

---

## HTML 样式规范

必须使用以下 CSS 变量体系（GitHub Dark）：

```css
:root {
  --bg: #0d1117; --bg-secondary: #161b22; --bg-tertiary: #21262d;
  --border: #30363d; --text: #c9d1d9; --text-secondary: #8b949e;
  --text-muted: #6e7681; --accent: #58a6ff; --accent2: #f0883e;
  --green: #3fb950; --yellow: #d2991d; --red: #f85149; --purple: #a371f7;
  --code-bg: #1c2128;
}
```

新增组件样式：
- `.chapter-header` — 章节大标题，底部双线边框
- `.source-tag` — 来源标注标签（L1 蓝色 / L2 紫色 / L3 绿色）
- `.priority-table` — 优先级建议表（P0 红色 / P1 黄色 / P2 绿色）
- `.lesson-ref` — Lesson 引用块（灰色背景 + 左边框）
- 保留原有 `.highlight-box`、`.key-box`、`.safety-box`、`.arch-box`

---

## INDEX.md 与 CSV 双轨更新规则

每次扫描完成后，同时更新两个文件。

### INDEX.md（人类可读索引）

追加记录到 `/Users/junye_shi/Scholarship is a new sexy/github_related/INDEX.md`。

```markdown
## 2026-MM-DD（第 N 次扫描）

| 级别 | 来源 | 项目 | Stars | 本地路径 | 一句话评价 |
|------|------|------|-------|----------|-----------|
| L1 | MCP生态 | org/repo | 12.3k | `L1/org_repo-src/` | ... |
| L2 | lesson: MCP超时 | org/tool | 5.2k | `L2/org_tool-src/` | ... |
| L3 | 用户: observability | org/monitor | 3.1k | `L3/org_monitor-src/` | ... |
```

已出现过的项目标注 `(第N次出现，上次: MMDD)`。

### projects_tracker.csv（机器可读去重数据源 + 版本追踪）

路径：`/Users/junye_shi/Scholarship is a new sexy/github_related/projects_tracker.csv`

**CSV 列定义**：

| 列名 | 类型 | 示例 |
|------|------|------|
| `project_name` | org/repo 唯一标识 | `TauricResearch/TradingAgents` |
| `description` | 功能简介（一句话） | `多Agent金融交易框架 — LangGraph五层Agent编排` |
| `introduced` | yes / no | `yes` |
| `version` | 引入时的版本/commit | `v1.2.0 (commit aa4b50e, 2026-04-24)` |
| `not_introduced_reason` | 不引入原因（introduced=no 时必填） | `仅Windows平台不适用` |

**去重流程**：
1. 新项目选取后 → 先查 CSV `project_name` 列是否已存在
2. `introduced=yes` → 跳过选取，记录到 INDEX.md 时标注"第N次出现"
3. `introduced=no` → 检查原因是否仍成立；如不再成立可重新评估
4. 选取后**立即追加 CSV 行**（在 git clone 前），防止中断丢记录

**版本追踪**：
- 引入项目时必须记录版本（`git describe --tags` + `git rev-parse --short HEAD` + `git log -1 --format=%ci`）
- 后续更新检查时对比此版本，发现更新后追加新行并标注更新内容

---

## 禁止行为

- ❌ L1 三个方向不可省略或替换（Claude Code MCP / Skills / Agent 框架）
- ❌ L2 只取最近 3 条 lesson，不可多取也不可少取（除非 lessons.md 不足 3 条）
- ❌ L2 关键词提取必须逐条读 lesson 内容后生成，禁止凭标题拍脑袋
- ❌ 忽略用户 L3 关键词
- ❌ 报告不按三章分层结构输出
- ❌ 每章不标注来源（方向/lesson/关键词）
- ❌ 不输出引入优先级建议表
- ❌ 跳过已引入项目更新检查（必须遍历 CSV 中 introduced=yes 的全部项目）
- ❌ 中途等待用户确认（全自动执行）
- ❌ 仅看 README 不读源码
- ❌ 省略代码片段（每个设计模式必须有源码引用）
- ❌ 忘记更新 INDEX.md 和 projects_tracker.csv
- ❌ 忘记用 `open` 打开 HTML
- ❌ 使用非 GitHub Dark 配色
- ❌ 报告中使用英文（全部中文，代码和专有名词除外）
- ❌ 跳过阶段门禁检查
- ❌ clone 失败直接跳过不尝试其他策略（必须 5 种策略依次尝试）

---

## 阶段门禁（强制检查）

### 门禁 1：L1 搜索完整性

| 检查项 | 阈值 | 不达标处理 |
|--------|:----:|-----------|
| 3 个方向均执行搜索 | 3/3 | 缺失方向补搜 |
| 每方向候选 ≥ 3 | 是 | 放宽关键词重搜 |
| 与 projects_tracker.csv 去重已执行 | 是 | 补齐去重步骤 |
| 最终 L1 选取 = 9 | 是 | 不足则降低 star 阈值补选 |

### 门禁 2：L2 Lesson 提取与搜索

| 检查项 | 阈值 | 不达标处理 |
|--------|:----:|-----------|
| 已定位最近 3 条 lesson | 是（或 lessons.md 全部条目） | 重新解析日期 |
| 每条 lesson 已提取关键词 | 3/3 | 逐条补提取 |
| 每条 lesson 已执行搜索 | 3/3 | 补搜 |
| 综合评分公式已应用 | 每项目有 stars_normalized + relevance | 补评分 |
| 每条 lesson 选取 = 5 | 15 项目 | 不足则降低阈值补选 |

### 门禁 3：L3 用户关键词搜索

| 检查项 | 阈值 | 不达标处理 |
|--------|:----:|-----------|
| 用户关键词全部解析 | M/M | 遗漏的补解析 |
| 每关键词选取 = 5 | 是 | 不足则放宽关键词 |

### 门禁 4：克隆完整性

```bash
BASE_DIR="/Users/junye_shi/Scholarship is a new sexy/github_related/github_related<YYYYMMDD>"
for proj_dir in "$BASE_DIR"/L*/*/; do
  if [ ! -d "$proj_dir" ] || [ -z "$(ls -A "$proj_dir" 2>/dev/null)" ]; then
    echo "❌ 克隆失败: $proj_dir"  # 重试一次，仍失败则跳过
  fi
done
```

| 检查项 | 阈值 | 不达标处理 |
|--------|:----:|-----------|
| clone 目录存在且非空(*-src/) | ≥ 90% | 失败项目检查是否5种策略都已尝试；未试完的补试 |
| 跳过项目数 | ≤ 2 | >2 则汇总失败原因（网络/DNS/仓库不存在/超大） |

### 门禁 5：源码分析深度

| 检查项 | 阈值 | 不达标处理 |
|--------|:----:|-----------|
| 每项目分析文件数 | ≥ 4 个关键源文件 | 追加阅读 |
| 每项目代码片段数 | ≥ 2 段 | 追加提取 |
| 跳过的项目 | 至少基于 README 做浅分析 | 补充 README 分析 |

### 门禁 6：报告结构完整性（最终门禁）

| 检查项 | 阈值 | 不达标处理 |
|--------|:----:|-----------|
| 第一章含 3 节（MCP/Skills/Agent） | 是 | 补充缺失节 |
| 第二章含 3 节（3 条 lesson） | 是 | 补充缺失节 |
| 第三章含 M 节（M 个关键词） | 是 | 补充缺失节 |
| 每节标注来源（级别+方向/lesson/关键词） | 100% | 补注 |
| 每节含引入优先级建议表 | 是 | 补表 |
| MD 文件 ≥ 5000 字节 | 是 | 补充内容 |
| HTML 含 `</html>` | 是 | 重新渲染 |
| HTML 含 `--bg:.*#0d1117` | 是（Dark 配色） | 修正 CSS |
| INDEX.md 含当日日期 | 是 | 追加记录 |
| projects_tracker.csv 含当日新项目行 | 是 | 追加行 |
| 报告含"已引入项目更新报告"附章 | 是 | 补充更新检查 |

### 门禁 7：更新检查完整性

| 检查项 | 阈值 | 不达标处理 |
|--------|:----:|-----------|
| CSV 中 introduced=yes 项目已遍历检查 | 100% | 补检遗漏项目 |
| 有更新的项目已下载到 `_updates/` | 是 | 补下载 |
| 更新摘要表已写入报告附章 | 是 | 补写 |
| 检查失败的项目已标注原因 | 是 | 标注网络/API错误 |

---

## 自动错误处理

| 场景 | 处理方式 |
|------|----------|
| WebSearch 无结果 | 记录到报告，该方向标注"未发现" |
| lessons.md 不足 3 条 | 有多少取多少，标注"lessons.md 仅 N 条" |
| L2 某 lesson 无搜索结果 | 放宽关键词重试，仍无则标注并跳过该 lesson |
| git clone 网络失败 | 依次尝试 5 种策略(HTTPS→SSH→gh CLI→tarball→main fallback)；全部失败才标记 FAILED |
| 项目源码过大（>200MB tarball 超时） | tarball 失败后，仅 clone 不读源码，基于 README 做浅分析 |
| 磁盘空间不足 | 警告用户，暂停执行 |
| GitHub API 限流（clone 阶段） | 全局加 3s 间隔；每项目策略间加 2s 间隔 |
| L3 无用户输入 | 第三章标注"本次无 L3 关键词"，不生成空章节 |
| GitHub API 限流（更新检查） | 记录失败项目名+原因，跳过，不阻塞主流程 |
| 已引入项目无新版本 | 附章标注"本次检查 N 个项目，均无可用更新" |

---

## 执行示例

```
用户: /ExploreGitHub_Scholarship MCP observability dashboard

Claude: [自动执行，无需交互]

  📋 阶段1: L1 Claude Code 生态搜索...
    L1-1 MCP生态: 2路搜索 → 17候选 → Top3 by stars ✅
    L1-2 Skills生态: 2路搜索 → 12候选 → Top3 by stars ✅
    L1-3 Agent框架: 2路搜索 → 9候选 → Top3 by stars ✅
    🧹 与 projects_tracker.csv 去重: 剔除 1 个 (已下载) → 递补 1 个
    📝 CSV 已追加 9 行
    🔒 门禁1: 3/3方向 ✅ | 9/9项目 ✅ | CSV已追加 ✅ → 通过

  📋 阶段2: L2 记忆驱动 (最近3条 lesson)...
    📖 定位最近 lesson:
      1. 2026-07-12 "MCP 客户端超时 30s 不可配置"
      2. 2026-07-12 "MCP 超时报错≠操作失败"
      3. 2026-07-12 "MCP 超时先查服务器状态"
    🔍 逐条提取关键词 + 搜索:
      Lesson 1 → "MCP timeout monitoring" → 8候选 → Top5 ✅
      Lesson 2 → "async task output file watcher" → 6候选 → Top5 ✅
      Lesson 3 → "process diagnostic dashboard" → 10候选 → Top5 ✅
    🔒 门禁2: 3/3 lesson ✅ | 15/15项目 ✅ → 通过

  📋 阶段3: L3 用户关键词...
    L3-1 "MCP observability dashboard" → 11候选 → Top5 by relevance ✅
    🔒 门禁3: 1/1关键词 ✅ | 5/5项目 ✅ → 通过

  📋 阶段4: 三级汇总去重...
    合并 9+15+5=29 → L2与L1重复1个(保留L1) → 最终 28 项目
    🔒 汇总: L1=9, L2=14(去重-1), L3=5 → 共 28 项目

  📋 阶段5: 并行克隆 28 项目...
    ✅ 27/28 成功，1 个网络失败已跳过
    🔒 门禁4: 27/28 (96%) ✅ | 跳过≤3 ✅ → 通过

  📋 阶段6: 深度源码分析...
    ✅ 27 项目 × ≥4 文件 = 135+ 关键文件阅读
    🔒 门禁5: 全项目≥4文件 ✅ | ≥2代码片段 ✅ → 通过

  📋 阶段7: 已引入项目更新检查...
    📋 读取 CSV: 0 个 introduced=yes 项目（当前无已部署项目）
    📊 结果: 无需检查更新
    🔒 门禁7: 已遍历 ✅ | 附章已写入 ✅

  📋 阶段8: 输出三章分层报告 + 更新摘要...
    第一章: L1 Claude Code生态 (MCP/Skills/Agent 三节) ✅
    第二章: L2 记忆驱动 (3条lesson三节) ✅
    第三章: L3 定向探索 (1个关键词一节) ✅
    附章: 已引入项目更新报告 (1个更新) ✅
    🔒 门禁6: 三章+附章完整 ✅ | 来源标注 ✅ | 优先级表 ✅
              MD 36KB ✅ | HTML 50KB ✅ | Dark配色 ✅ | INDEX.md ✅ | CSV ✅
    → open HTML ✅

📊 本次扫描完成：
  - L1: 3方向 × 3 = 9 | L2: 3lesson × 5 = 15 | L3: 1关键词 × 5 = 5
  - 去重后共 28 项目，深度分析 27 个
  - 更新检查: 50/52 已检查，发现 1 个更新
  - 报告: github_related20260713/github_related0713.html
  - 索引已更新: INDEX.md + projects_tracker.csv
  - 阶段门禁: 7/7 全部通过
```
