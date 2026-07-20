---
name: DocumentObsidian_Vault
description: 策略研发的叙事知识层(实时伴随) — 把项目文件夹下分叉的策略脚本 + 回测结果 + 决策,实时整理成可独立打开、可编辑的 Obsidian Vault(笔记 + Canvas 演进画布 + 开发日志),单一真源 manifest 驱动。触发词：/DocumentObsidian_Vault、obsidian、sync。
---

# /DocumentObsidian_Vault — 策略知识库维护

## 角色定位

**策略研发的"叙事知识层"（实时研发伴随）**。把一个项目文件夹下不断分叉的近似策略脚本（`.py`）+ 其回测结果 + 用户的决策，实时整理成一个**可独立打开、可编辑**的 Obsidian Vault：结构化笔记 + 双向链接 + Canvas 演进画布 + 演进树 + 开发日志。

它**架在 git 和回测之上**，不替代二者：git 管内容历史，回测管净值指标，**本 Skill 回答"人"的问题——这条策略线怎么演化的、每步改了什么、为什么、结果如何**。

**核心原则**：
1. **可编辑,不锁死** — 笔记由 Claude 起草，但用户可随时修改。默认**不加 chmod 444**（"用户只看不改"哲学已废弃：它与实时伴随冲突，且会导致 Canvas EACCES 空白）。
2. **数据诚实,缺失即问** — 每个字段必须有明确来源；来源没有 → **立即询问用户，按反馈填写**；绝不猜、绝不留空（唯一例外：用户明确授权占位）。见《记录内容契约》。
3. **单一真源** — `vault/.vault-manifest.json` 是唯一真源；演进树 / Canvas / 笔记 frontmatter 全部由它派生并须与它一致。
4. **实时伴随** — 会话内我主动更新 + 用户可 `/sync` 兜底（见《触发契约》），放弃 hook。
5. **一个项目文件夹 = 一个策略家族**（单策略库；多家族发出警告），模板脚本不纳入追踪。
6. **Canvas / .obsidian 永不加锁**（Obsidian 需读写其状态）。

## 与其他 Skill 的勾稽关系

| 上游/下游 | Skill | 数据流 |
|-----------|-------|--------|
| 上游 | `ResearchGil_Strategy_Backtest` | 策略脚本（.py）→ 笔记 + Canvas + 演进树 |
| 上游 | 回测输出 `output_*/results.csv` / `report_gil` / `chinapostamc_strategy_callback` MCP | 回测指标 → 自动回填笔记回测表 + 总览汇总 + 开发日志 |
| 上游 | 用户指定项目目录 | 任意含 .py 策略脚本的目录 → 识别策略家族 |
| 上游 | 用户口头决策/回答 | 变更目的、基线/废弃/定稿、缺失字段 → 写入对应位置 |

本 Skill 的输出（Obsidian 笔记 + Canvas）为独立产物，不被下游 Skill 自动消费。

## 文件路径约定

| 角色 | 说明 |
|------|------|
| 输入 | 用户指定的项目目录（含 .py 策略脚本），或 Strategy_Backtest 产出的脚本路径 |
| 输出 | 用户 Obsidian Vault 目录（写入 .md 笔记 + Canvas 画布 + 演进树） |

> 路径索引：`/Users/junye_shi/AgentFiles/SkillsRelationship_output/03_Document_Pipeline/01_Obsidian/index.html`

---

## 模式判定

解析用户输入参数 `<arg_path>`：

```
第一个词是 "sync"？
    ├── 是 → 全量对账模式（见《触发契约 · C》）：/DocumentObsidian_Vault sync <项目目录>
    └── 否 → <arg_path> 是一个目录？
              ├── 是 → 新任务模式（Phase A）
              └── 否（是一个 .py 文件）→ 继续任务模式（Phase B）
```

---

## 触发契约（实时伴随 = A + C，放弃 hook）

**A · 会话内主动**：本会话中 Claude 一旦发生下列事件，**当场增量更新** vault，无需用户再次触发：
1. 新建/改写了一个策略 `.py`（非模板）→ 建/更笔记 + 更演进树 + 更 manifest + Canvas + 开发日志一行。
2. 跑完一次回测（产出 `results.csv` 等）→ 回填该脚本回测表 + 总览汇总 + 开发日志（见《回测结果自动吸收》）。
3. 用户口头给出决策（"这版设基线 / 放弃 / 定稿"）→ 更新 frontmatter status + 节点颜色 + 开发日志。

**C · 显式对账 `/sync`**：`/DocumentObsidian_Vault sync <项目目录>`。用于会话外发生的变化（在编辑器里写了脚本、在别处跑了回测）。动作：
1. 读 `.vault-manifest.json` 现状；
2. 扫描项目目录：发现**新脚本**（不在 manifest、非模板）→ 走 Phase B 建笔记；
3. 扫描各脚本的 `output_*/` → 有**新回测结果**未回填 → 回填；
4. 校验 manifest ↔ 演进树 ↔ Canvas ↔ frontmatter 一致，不一致则修正；
5. 汇报变更清单。

> ❌ **不使用 settings.json hook**：hook 只能跑命令、不能跑推理，对"判断父级/归纳差异"这类任务易误触、噪声大。

---

## 记录内容契约（Content Contract）

**所有写入 vault 的内容，无论会话内主动还是 /sync，都被下列七条框死。**

**A. 章节白名单**（每类笔记只允许下列**核心节** + 少量**可选节**，其余一律不许）：

| 笔记类型 | 核心章节（顺序固定） |
|---------|---------|
| 衍生笔记 | frontmatter / 定位（含变更目的）/ 相对 parent 差异表 / 关键参数 / 数据源 / 回测结果 / 子版本 |
| 初版笔记 | frontmatter / 策略概述 / 关键参数 / 数据源 / 回测结果 / 子版本 |
| 工具脚本 | frontmatter / 用途 / 输入输出（**无回测节**） |
| 00-总览 | 头部（含入口导航）/ 演进树 / 回测结果汇总 / 未归类 / 废弃分支 / 颜色图例 |
| 开发日志 | append-only 时间线条目 |

**允许的可选节**（可有可无，但不得超出此集）：`因子公式`（策略核心因子的定义/公式）、`备注`（风险 / 代码疑点 / 待核对）。

**章节命名规则**：规范名如上；可带括号限定词，规范名取"（"之前部分（如 `关键参数（核心逻辑）`、`差异表（相对 [[x]]）` 均合法，判重按 `关键参数` / `差异`）。

> **禁止出现**：核心节+可选节以外的自造章节、完整代码块（``` ```）、长 SQL 转储、推测性评论、与总览重复的大段文字。

**B. 字段获取顺序**（每个字段统一走这个流程）：

1. 先查**唯一合法来源**；2. 有 → 自动填 + 溯源标记；3. 没有 → **立即询问用户，按反馈填写**；4. 绝不猜、绝不留空。

| 字段 | 唯一合法来源 | 来源没有时 |
|------|-------------|-----------|
| 策略概述 / 关键参数 / 数据源 | 读代码 | **询问用户** |
| 回测指标（总收益/Sharpe/回撤/超额…） | **QuantStats 报告**（HTML 文件名/报告内容）→ 其次 results.csv/MCP | **询问用户 → 按其给的数填** |
| 父子 lineage | 文件名 + diff 推断 | **询问用户确认父级** |
| 变更目的 / 决策原因 | 用户口头原文 | **询问用户 → 按原话填** |

**C. 缺失即问纪律**：
- **合并提问**：一次更新里所有缺失字段**攒成一次**问用户（一次性列出），不逐条打断。
- **唯一留空例外**：用户**明确说**"先别填 / 还没跑" → 才标占位（这是用户授权，不是 skill 擅自留空），占位写 `⏳ 待用户补充（YYYY-MM-DD 授权）`。
- 仍然**永不编造**——"不猜"与"不留空"由"问用户"这个动作调和。

**D. 篇幅 / 高度**：笔记是"差异摘要"非代码转储；差异表逐条 ≤ 1 行；总览一屏；开发日志一行/条。

**E. 更新纪律**：开发日志 **append-only**（不改历史）；回测表以数据源为权威（每次覆盖为最新）；正文修正走覆盖。

**F. 单一真源 + 派生一致**：`.vault-manifest.json` 是唯一真源；演进树 / Canvas / frontmatter 由它派生。每次更新后**必须校验三者与 manifest 一致**（不一致即 bug）。

**G. 溯源标记**：非代码提取的值必须带来源，如回测表脚注 `来源: results.csv @ 2026-07-09` 或 `来源: 用户反馈 @ 2026-07-10`。

---

## `.vault-manifest.json` — 单一真源

位置：`<PROJ_DIR>/vault/.vault-manifest.json`（**不锁**）。schema：

```json
{
  "family": "<策略家族名>",
  "updated": "<YYYY-MM-DD>",
  "templates": ["<模板脚本名.py>"],
  "scripts": [
    {
      "name": "<脚本名(无.py)>",
      "parent": "<父脚本名 或 null>",
      "type": "root | variant | tool",
      "status": "active | experimental | abandoned | production",
      "color": "1..6",
      "note": "策略/<脚本名>.md",
      "backtest": { "filled": true, "source": "qs_html | results.csv | user | mcp", "as_of": "<YYYY-MM-DD>" },
      "pending_fields": []
    }
  ]
}
```

**时机**：任何更新的**第一步读它、最后一步写它**；新会话开工前先读它恢复"现状"（不再依赖会话记忆）。演进树、Canvas、frontmatter 全部由它渲染。

---

## 回测结果自动吸收

> 🔒 **硬规则:笔记里记录的一切回测指标,唯一权威来源是 QuantStats 报告**(HTML 文件名编码的指标,或报告内容)。**不得**用记忆、估计、或其它工具的数字。QS 报告没有该指标 → 询问用户,并在溯源标注用户来源。

> ⚠️ **数据源以实测为准（2026-07 穿行测试勘误）**：这些策略脚本的回测**不产出固定的 `results.csv`**。真实产物如下，**优先解析 QuantStats HTML 文件名**（最通用，指标直接编码在文件名里）。

**输出目录**：命名不固定——可能是 `output_<脚本名>/`（成长）或 `<策略名>/`（价值，无 output_ 前缀）。按脚本名/策略名模糊匹配定位。

**数据源优先级**：
1. **QuantStats HTML 文件名**（几乎必有）——指标编码在文件名中，直接正则解析：
   - `【<名>】_【<start>至<end>】_【总收益：X%】_【最大回撤：Y%】.html`
   - 或 `【<名>】_【<区间>】_【策略X%】_【基准Y%】_【超额Z%】.html`
   - 频率变体后缀 `_1month` / `_2months` 表示调仓频率，各记一行。
   - **可用正则（本会话实测 7/7 通过，直接用）**：
     ```
     名     = ^【([^】]+)】
     区间起  = 【(\d{4}-\d{2}-\d{2})至    区间止 = 至(\d{4}-\d{2}-\d{2})】
     总收益  = 总收益：([\-\d.]+%)        最大回撤 = 最大回撤：([\-\d.]+%)
     策略    = 策略([\-\d.]+%)   基准 = 基准([\-\d.]+%)   超额 = 超额([\-\d.]+%)
     频率    = _(\dmonths?)\.html
     ```
2. `results.csv` / `annual_returns.csv` / `nav_series.csv`（**仅部分目录有**）——取更全指标（Sharpe/年化/逐年）。
3. `report_gil` / `chinapostamc_strategy_callback` MCP（已上线策略）。
4. 都没有 → **询问用户**。

**回填三处**（一次都要更新）：
1. 该脚本笔记的"回测结果"表（+ 溯源脚注 `来源: QS HTML 文件名 @ <end>` 等）；
2. `00-总览.md` 的"回测结果汇总"表；
3. `开发日志.md` 追加一行（含关键指标 + 决策）；
   同时更新 `.vault-manifest.json` 该脚本 `backtest.filled/source/as_of`。

**完整性判定**：一条回测数据"算完整"至少含 **回测区间 + 基准 + 一项收益指标 + 最大回撤**；缺任一项 → 按《记录内容契约》B 询问用户补齐。所有结果都记录（含不理想的、含同一脚本的多频率变体，并注明原因，避免重复测试）。

---

## Phase A：新任务模式

**触发**：`/DocumentObsidian_Vault /path/to/project`

**适用场景**：全新项目，或已有模板脚本但尚未建立 Obsidian Vault。

### Step A1：路径校验

```bash
PROJ_DIR="<arg_path>"  # 必须是目录
```

- `PROJ_DIR` 不存在 → 报错终止："路径不存在：<arg_path>"
- `PROJ_DIR` 不是目录 → 报错终止："路径不是目录，请指定项目文件夹"

### Step A2：重复初始化检查

检查 `PROJ_DIR/vault/`（或其中的 `PROJ_DIR/vault/.obsidian/`）是否已存在：

**若已存在** → 询问用户（三选一）：

> 该目录下已存在 Obsidian Vault：
> A) **重新初始化** — 删除现有 vault/，从头开始
> B) **继续已有任务** — 使用 `/DocumentObsidian_Vault <project>/<script.py>` 追加新脚本
> C) **取消**

- 选 A → 执行 Step A3（清理重建）
- 选 B → 告知用户使用正确的文件路径形式，终止
- 选 C → 终止

**若不存在** → 继续 Step A3。

### Step A3：记录模板清单

扫描 `PROJ_DIR` 下所有 `.py` 文件，记录为**模板脚本（不追踪）**：

```bash
ls "$PROJ_DIR"/*.py 2>/dev/null
```

将文件名列表暂存，**Step A4 写入 `.vault-manifest.json` 的 `templates` 字段**（不再仅靠会话记忆——跨会话由 manifest 恢复）。后续所有操作中，这些文件被视为模板，不纳入 Obsidian 追踪。

> 📌 告知用户："检测到 N 个模板脚本（xxx.py, yyy.py），已排除追踪。后续新建的第一个 .py 文件将被标记为初版策略。"

### Step A4：创建 Vault 骨架

```bash
# 创建目录结构
mkdir -p "$PROJ_DIR/vault/策略"
mkdir -p "$PROJ_DIR/vault/.obsidian"   # ⚠️ 关键：没有它,vault/ 只是普通文件夹,无法作为独立 vault 打开
```

> 🔑 **核心修复(2026-07 复盘)**:此前版本只建 `vault/策略/`,不建 `.obsidian/`。
> 结果 `vault/` 被埋在用户总库深层目录里、无法单独打开、图谱孤岛 → 用户"根本看不到"。
> **必须**为每个策略 vault 建 `.obsidian/` 配置,使其成为可被 Obsidian 直接打开的独立 vault。

**创建 `.obsidian/` 配置(三个文件,使 vault 可独立打开)**：

`$PROJ_DIR/vault/.obsidian/app.json`：
```json
{}
```

`$PROJ_DIR/vault/.obsidian/appearance.json`：
```json
{}
```

`$PROJ_DIR/vault/.obsidian/core-plugins.json`（启用画布/图谱/文件树等核心插件,否则 Canvas 不渲染）：
```json
{
  "file-explorer": true,
  "global-search": true,
  "switcher": true,
  "graph": true,
  "backlink": true,
  "canvas": true,
  "outgoing-link": true,
  "tag-pane": true,
  "properties": true,
  "page-preview": true,
  "outline": true,
  "bookmarks": true
}
```

> ⚠️ `.obsidian/` 目录**不加 chmod 444 锁**（Obsidian 需读写自身配置,如 workspace 状态）。**只锁 `.md`；`.canvas` 也必须保持可写**（Canvas 打开即写视口状态,锁只读会报 EACCES 空白）。

**创建 `$PROJ_DIR/vault/开发日志.md`**（append-only 开发过程时间线,真正的版本管理载体）：

```markdown
---
type: dev-log
title: <策略家族名>开发日志
status: active
created: <当前日期>
updated: <当前日期>
tags: [<家族标签>, 开发日志, 版本管理]
---

# 📓 <策略家族名>开发日志

> **用途**:append-only 时间线,记录每一次因子/参数改动、回测结果与决策依据。
> 与 [[00-总览]] 的演进树互补 —— 总览看"结构",本日志看"过程"。
> **规则**:只在文末追加,不修改历史条目;数据逐字取自回测输出,不凭记忆填写。

---

## <当前日期> · 建立<策略家族名>知识库

- 初始化 vault,模板脚本 <xxx.py> 已排除追踪。

<!-- 新增条目在此行下方追加,保留全部历史 -->
```

**创建 `$PROJ_DIR/vault/00-总览.md`**（空 Hub）：

```markdown
# 策略演进总览

> 初始化时间：<当前日期>
> 初版策略：待创建

> 🧭 **入口导航**：[[开发日志]]（开发过程时间线） · [[画布-策略演进.canvas|策略演进画布]]

## 演进树

_等待第一个策略脚本..._

## 未归类脚本

_无_

## 废弃分支

_无_
```

**创建 `$PROJ_DIR/vault/画布-策略演进.canvas`**（空 Canvas）：

```json
{"nodes":[],"edges":[]}
```

**创建 `$PROJ_DIR/vault/.vault-manifest.json`**（单一真源，schema 见《`.vault-manifest.json`》）：初始 `family` = 家族名，`templates` = Step A3 的模板清单，`scripts` = `[]`，`updated` = 当日。

**默认不锁定（可编辑）**：v2 起笔记默认保持可写，供用户随时批注。`.canvas` / `.obsidian` / `.vault-manifest.json` 一律不锁。

> 可选归档锁：用户明确要求"锁定归档"时，才 `chmod 444` **仅 `.md`**（永不锁 canvas/.obsidian/manifest）：
> ```bash
> find "$PROJ_DIR/vault" -type f -name "*.md" -not -path "*/.obsidian/*" -exec chmod 444 {} \;
> ```

### Step A5：告知用户（含注册指引 — 解决"看不到"的关键）

> ✅ Obsidian Vault 就绪(已是可独立打开的完整 vault)。
>
> - Vault 路径：`$PROJ_DIR/vault/`
> - **一次性注册(必做,否则埋在总库深层看不到)**：Obsidian 左下角 vault 切换图标 → **Open another vault → Open folder as vault** → 选择上面这个 `vault/` 路径。之后它会出现在 vault 切换列表里,一键直达。
> - 打开后你会看到:`00-总览.md`(总览) + `开发日志.md`(开发过程) + `策略/`(各版本笔记) + `画布-策略演进.canvas`(演进图)
> - 模板脚本 `xxx.py, yyy.py` 已排除追踪
> - 后续每新建一个 .py，Claude 将自动创建对应策略笔记、更新演进树、并在开发日志追加一条记录

> ⚠️ **不要**直接改全局 `~/Library/Application Support/obsidian/obsidian.json` 来注册:若 Obsidian 正在运行,退出时会覆盖你的改动。始终用上面的 UI "Open folder as vault"。

### Step A6：会话内自动追踪

Step A5 完成后，本次会话中 Claude 的行为：
- 每创建一个 `.py` 文件（排除模板清单中的文件），自动执行 **Phase C（增量追加）**
- 无需用户再次手动触发 `/DocumentObsidian_Vault`

---

## Phase B：继续任务模式

**触发**：`/DocumentObsidian_Vault /path/to/project/script.py`

**适用场景**：Vault 已存在，新增了一个策略脚本，需要追加笔记。

### Step B1：前置校验

```bash
VAULT_DIR="$(dirname <arg_path>)/vault"
```

- `VAULT_DIR/00-总览.md` 不存在 → 报错终止："Vault 不存在，请先使用 /DocumentObsidian_Vault <项目目录> 初始化"
- `<arg_path>` 不是 `.py` 文件 → 报错终止："仅支持 .py 策略脚本"
- `<arg_path>` 文件不存在 → 报错终止："文件不存在：<arg_path>"

### Step B2：读取现有演进树

读取 `VAULT_DIR/00-总览.md`，提取：

1. **已追踪脚本清单**：从演进树中解析所有 `[[脚本名]]` 链接
2. **演进关系**：缩进层级表示的父子关系
3. **废弃分支列表**：从"废弃分支"章节提取
4. **未归类列表**：从"未归类脚本"章节提取

### Step B3：推断父级关系

对新脚本 `<arg_path>` 执行三级推断：

**L1：import 依赖（最高权重）**

```bash
# 读取新脚本的 import 语句
grep -E "^from |^import " <arg_path>
```

如果新脚本 `import` 了某个已追踪脚本的模块名，则该已追踪脚本为父级。

**L2：文件名模式（中等权重）**

检查新脚本文件名是否包含已追踪脚本的关键词：
- `strategy_v1.py` → `strategy_v2.py`：`strategy` 匹配，v2 暗示继承 v1
- `Dividend-CIR.py` → `Dividend-CIR-with-Backup.py`：基础名匹配
- `Dividend-CIR-with-Backup.py` → `Dividend-CIR-with-Backup-v2.py`：`-v2` 后缀暗示上级

判断逻辑：
- 提取新文件名中的"基础名"（去掉 `-v2`、`-ExpDY`、`-SafetyCushion` 等后缀变体标记）
- 在已追踪脚本中找最长公共前缀匹配
- 得分 = 公共前缀长度 / 新文件名长度

**L3：代码 diff 相似度（低权重）**

```bash
# 计算新脚本与每个已追踪脚本的相似度,取 diff 行数最少者为父级
best_tracked=""; best_score=999999
for tracked in <已追踪脚本列表>; do
    similarity=$(diff -u "$tracked" <arg_path> | wc -l)   # 越小越相似
    if [ "$similarity" -lt "$best_score" ]; then
        best_score=$similarity; best_tracked=$tracked
    fi
done
# best_tracked 即 diff 行数最少的已追踪脚本
```

`best_tracked`（diff 行数最少的已追踪脚本）最可能是父级。

**综合判定**：

```
if L1 命中（有明确 import）:
    parent = L1 结果
elif L2 置信度 > 60%:
    parent = L2 结果
elif L3 确定且唯一（最小 diff < 50 行且与次小差距 > 30%）:
    parent = L3 结果
else:
    parent = None → 放入"未归类脚本"
```

**多家族检测**：

在推断父级时，如果新脚本与所有已追踪脚本的 L1/L2/L3 均无关联（import 无匹配、命名无公共前缀、diff 均 > 100 行），判定为"潜在新家族"，发出警告：

> ⚠️ 警告：`<script.py>` 与当前演进树中的所有策略均无关联，可能是独立的新策略家族。
> 当前 Vault 约定为一个文件夹 = 一个策略家族。是否：
> A) 将其作为新家族的初版（在总览中新建一棵树）
> B) 取消，可能需要另建项目文件夹

### Step B4：创建策略笔记

**写入前**：v2 默认笔记可写，直接写即可。**仅当** vault 曾被"归档锁定"（`.md` 为 444）时，才先解锁：

```bash
# 仅归档锁定场景需要;默认可写无需此步
find "$VAULT_DIR" -type f -name "*.md" -not -path "*/.obsidian/*" -exec chmod u+w {} \;
```

**如果该脚本为初版（演进树为空）**→ 使用"初版模板"：

```markdown
---
type: strategy-root
status: active
created: <YYYY-MM-DD>
version: 1.0
sharpe: null
ic: null
tags: [<从文件名提取的标签>]
aliases: [<脚本名(无扩展名)>]
---

# <脚本名(无.py)>

## 策略概述

<描述策略的：
- 选股逻辑（筛选条件、排序因子）
- 调仓频率
- 基准
- 持仓数量/权重方案
- 使用的数据源
- 使用的因子
>

## 关键参数

| 参数 | 值 |
|------|-----|
| <参数名> | <值> |

## 数据源

| 表名 | 用途 |
|------|------|
| <表名> | <用途> |

## 回测结果

| 指标 | 值 |
|------|-----|
| Sharpe | — |
| 年化收益 | — |
| 最大回撤 | — |
| IC/Rank IC | — |

## 子版本

_暂无衍生版本_
```

**Claude 必须从代码中提取实际信息填入模板**：
- 读代码中的筛选逻辑、SQL 查询、参数常量
- 策略概述必须完整、准确，不是占位符
- 参数表中的值从代码中提取
- 回测结果：按《回测结果自动吸收》先查 `output_*/results.csv`/MCP；查不到则按《内容契约 B》**询问用户**，绝不留空（除非用户授权占位）

**如果该脚本为衍生版本**→ 使用"衍生版本模板"：

```markdown
---
type: strategy-variant
parent: "[[<parent_name>]]"
status: active
created: <YYYY-MM-DD>
version: N/A
sharpe: null
ic: null
tags: [<从文件名和父级继承的标签>]
aliases: [<脚本名(无扩展名)>]
---

# <脚本名(无.py)>

## 定位

基于 [[<parent_name>]] 的衍生版本。

**变更目的**：<一句话描述为什么做这个改动>

## 相对于 [[<parent_name>]] 的差异

| # | 差异项 | [[<parent_name>]] 原版 | 本版 |
|---|--------|------------------------|------|
| 1 | <差异类别> | <原版值/逻辑> | <本版值/逻辑> |
| 2 | ... | ... | ... |

## 关键参数

| 参数 | 值 | 相对于 parent |
|------|-----|:---:|
| <参数名> | <值> | 🆕 / ✏️ / ✅ |

> 🆕 新增 | ✏️ 修改 | ✅ 保持

## 回测结果

| 指标 | 值 |
|------|-----|
| Sharpe | — |
| 年化收益 | — |
| 最大回撤 | — |
| IC/Rank IC | — |

## 子版本

_暂无衍生版本_
```

**Claude 必须**：
1. 使用 `diff` 命令获取新脚本与 parent 的实际差异
2. 从 diff 中提取实质性修改（忽略空白、注释变化）
3. 将差异归纳为表格，用简洁语言描述，不要逐行罗列代码

**笔记命名**：`vault/策略/<脚本名(无.py)>.md`

**写入笔记后**，更新 parent 笔记的"子版本"章节：
```markdown
## 子版本
- [[<本版名称>]] — <一句话描述>
```

### Step B5：更新总览

更新 `VAULT_DIR/00-总览.md` 的"演进树"章节：

**若为初版**（树为空）：
```markdown
## 演进树
- 🟢 **[[<脚本名>]]** ← 初版
    - _暂无衍生版本_
```

**若为衍生版本**（追加到 parent 下方）：
```markdown
## 演进树
- 🟡 **[[<parent>]]** ← 初版
    - 🟢 **[[<新脚本>]]** — <一句话描述>
    - 🟡 **[[<已有衍生>]]** — <已有描述>
```

**节点颜色规则**：

| 状态标记 | 颜色 | 条件 |
|----------|------|------|
| 🟢 活跃 | 绿 | 无子版本（当前最新） |
| 🟡 有衍生 | 黄 | 有子版本，但自身仍可用 |
| ⚪ 已替代 | 灰 | 所有逻辑已被衍生版本覆盖 |
| 🔴 失败分支 | 红 | 回测结果差，已废弃 |

> 节点 `color`/`status` 的**唯一真源是 `.vault-manifest.json`**；总览演进树与 Canvas 均由 manifest 派生渲染，不各自独立评估。"重新评估"指的是**更新 manifest 里的 color/status**，再据其重绘总览与 canvas（三者保持一致）。

**若无法确定父级**→ 追加到"未归类脚本"：
```markdown
## 未归类脚本
- ⚠️ [[<脚本名>]] — 无法推断父级，等待手动归类
```

### Step B6：重绘 Canvas

读取 `VAULT_DIR/00-总览.md` 的演进树，生成 Canvas JSON。

**Canvas 节点布局算法**（左→右树形）：

```
Root (x=0, y=0)
  ├── Child1 (x=500, y=parent_y - sibling_offset)
  ├── Child2 (x=500, y=parent_y)
  └── Child3 (x=500, y=parent_y + sibling_offset)
```

- 节点宽度：`400px`，高度：`300px`
- 水平间距：`500px`（x 增量）
- 垂直间距：`350px`（y 增量）
- 同级子节点以父节点 y 为中心均匀分布

**节点颜色映射**（Canvas `color` 字段为字符串；**与 build_canvas 图例共用同一张表**）：

| 状态 | color | 含义 |
|------|:-----:|------|
| 🔴 失败/废弃 | `"1"` 红 | 回测差已废弃 |
| 🟠 独立分支 | `"2"` 橙 | 独立主题分支 |
| 🟡 有衍生 | `"3"` 黄 | 有子版本，自身仍可用 |
| 🟢 活跃/生产 | `"4"` 绿 | 当前最新/生产版 |
| 🔧 工具 | `"5"` 青 | 工具脚本 |
| 🧪 实验 | `"6"` 紫 | 实验/被放弃试验 |
| ⚪ 已替代 | `"0"` 灰 | 逻辑已被衍生完全覆盖 |

**Canvas JSON 结构**：

```json
{
  "nodes": [
    {
      "id": "<生成的UUID>",
      "type": "file",
      "file": "策略/<脚本名(无.py)>.md",
      "x": <x坐标>,
      "y": <y坐标>,
      "width": 400,
      "height": 300,
      "color": "<颜色代码>"
    }
  ],
  "edges": [
    {
      "id": "<生成的UUID>",
      "fromNode": "<parent节点ID>",
      "fromSide": "right",
      "toNode": "<child节点ID>",
      "toSide": "left"
    }
  ]
}
```

节点 ID 生成规则：使用脚本名的 hash 前缀（8 位），确保稳定可复现。

**未归类脚本节点**：放在 Canvas 右下方（`x=800, y=1000` 起始），颜色 `"6"`（紫色），与其他节点无连线。

### Step B6.5：追加开发日志

在 `$VAULT_DIR/开发日志.md` **文末追加**一条记录(append-only),内容包括:
- 日期
- 本次改动(新脚本名、相对 parent 的核心差异一句话)
- 回测结果:按《回测结果自动吸收》先查 `output_*/`；查不到则**询问用户**填入(绝不留空)

> 开发日志是 append-only 的:**只在末尾加,绝不修改历史条目**。这是本 Vault 的"过程"记录（结构记录在演进树）。

### Step B6.8：更新 manifest（单一真源，必做）

把本次新增/变更写回 `$VAULT_DIR/.vault-manifest.json` 的 `scripts[]`（name/parent/type/status/color/note/backtest/pending_fields）并刷新 `updated`。**演进树、Canvas、frontmatter 必须与 manifest 保持一致**（下一步校验）。

### Step B7：一致性校验（替代"锁定"）

v2 默认**不锁**。写入后跑一致性校验（不一致即 bug，须修正）：
1. `00-总览.md` 每个 `[[wikilink]]` 都有对应 `策略/*.md`（无断链）；
2. Canvas 每个 `node.file` 都存在（无缺失引用）；
3. manifest `scripts[]` 与演进树节点、Canvas 节点一一对应。

> 可选归档锁（仅用户要求时）：`find "$VAULT_DIR" -type f -name "*.md" -not -path "*/.obsidian/*" -exec chmod 444 {} \;`。**永不锁 .canvas / .obsidian / manifest。**

### Step B8：告知用户

```
✅ 策略笔记已追加：

| 项目 | 内容 |
|------|------|
| 新笔记 | vault/策略/<script>.md |
| 父级 | [[<parent>]] |
| 总览 | vault/00-总览.md 已更新 |
| 开发日志 | vault/开发日志.md 已追加一条 |
| Canvas | vault/画布-策略演进.canvas 已重绘 |
| 状态 | 🟢 活跃 / ⚠️ 未归类 |

> 在 Obsidian 里打开这个 vault(若未注册:Open folder as vault → 选 vault/ 路径)即可查看图谱和 Canvas。
```

---

## Phase C：会话内增量追加

**触发条件**（本会话中自动判断）：
- 本次会话已执行过 Phase A（Vault 初始化），且
- Claude 新建了一个 `.py` 文件（不在模板清单中）

**Claude 动作**：
1. 自动执行 Step B3（推断父级）
2. 比较新文件与模板清单：**新脚本如果 import 了模板，diff 了模板，parent 指向模板** — 但模板不纳入 Obsidian，所以 parent 设为 `None`（初版）
3. 执行 Step B4-B7（创建笔记 → 更新总览 → 重绘 Canvas → 锁定）
4. 简洁告知用户（与 Step B8 格式相同）

**⚠️ 模板衍生检测**：

如果新脚本与某个模板脚本的 diff 相似度 > 70%（即改动不大），Claude 应提醒用户：

> ⚠️ `new_script.py` 与模板 `template.py` 高度相似（相似度 ~XX%）。按设定，模板不纳入追踪，因此 `new_script.py` 将被标记为初版策略。如果这不符合预期，请告知。

---

## Phase D：多脚本 / 多库批量重构

**触发**：一个项目目录下已有**大量** `.py` 脚本（十几到几十个）需一次性建库；或需把**多个**项目目录同时"作为库重构"。

**核心原则**：并行提取 + 中央组装 + 并行落盘 + 自动画布 + 统一校验。**回测数字缺失一律留"待补录",绝不杜撰;lineage 存疑处显式标注;读代码发现的疑点(如基准代码 bug)记入对应笔记待修。**

### Step D1：完整 `.obsidian` 配置（Obsidian 标准 31 键，勿用精简版）

每个 vault 的 `.obsidian/core-plugins.json` 用下面这份**完整**配置（与用户主库一致；精简版会导致 Canvas/图谱插件缺失）。`app.json`/`appearance.json` 写 `{}`。**不锁 `.obsidian`**。

```json
{
  "file-explorer": true, "global-search": true, "switcher": true, "graph": true,
  "backlink": true, "canvas": true, "outgoing-link": true, "tag-pane": true,
  "footnotes": false, "properties": true, "page-preview": true, "daily-notes": true,
  "templates": true, "note-composer": true, "command-palette": true, "slash-command": false,
  "editor-status": true, "bookmarks": true, "markdown-importer": false, "zk-prefixer": false,
  "random-note": false, "outline": true, "word-count": true, "slides": false,
  "audio-recorder": false, "workspaces": false, "file-recovery": true, "publish": false,
  "sync": true, "bases": true, "webviewer": false
}
```

### Step D2：并行提取脚本信息（子 agent 分组读代码）

把脚本按演进簇分 3-5 组，每组派一个 `general-purpose` 子 agent（model=sonnet），**只 Read 代码返回结构化摘要**（定位/选股逻辑/关键参数/数据表/相对前版差异），数值逐字取自代码。子 agent **不写文件**，只回传数据。

### Step D3：中央写 `00-总览.md` + `开发日志.md`

汇总各组摘要，**由主 Claude 集中**推断演进树（L1 import > L2 命名 > L3 diff）、写总览（含入口导航、演进树、颜色图例、回测汇总占位、废弃分支）和开发日志（按日期回填时间线）。这两个文件是后续并行写笔记的"父子映射"依据,必须先定稿。

### Step D4：并行写笔记（子 agent 用已提取数据落盘，不重读代码）

按同样分组派子 agent，**把 Step D2 提取的数据 + 笔记模板 + 每篇的 parent/子版本映射**塞进 prompt，让它们直接 Write 到 `vault/策略/`。子 agent 不再读 `.py`（数据已给），保证准确、省时。回测结果：有 `output_*/results.csv` 的直接填 + 溯源；没有的**收集成清单待 Step D7 一次性问用户**（批量场景的"缺失即问"）。**默认不 chmod**（v2 可编辑）。

### Step D5：自动生成 Canvas（树形布局脚本）

用下面的脚本从 `{name, parent, color}` 列表生成 canvas（x=深度×460，y=叶子顺序槽位、父节点取子女均值），**不要手工摆坐标**：

```python
import hashlib, json
def nid(n): return hashlib.md5(n.encode()).hexdigest()[:8]
def build_canvas(nodes, strat_dir="策略"):
    children={}; roots=[]
    for n in nodes:
        (roots.append(n['name']) if n['parent'] is None
         else children.setdefault(n['parent'],[]).append(n['name']))
    depth={}
    def setd(nm,d):
        depth[nm]=d
        for c in children.get(nm,[]): setd(c,d+1)
    for r in roots: setd(r,0)
    y={}; slot=[0]
    def assign(nm):
        ch=children.get(nm,[])
        if not ch: y[nm]=slot[0]*340; slot[0]+=1
        else:
            for c in ch: assign(c)
            y[nm]=sum(y[c] for c in ch)/len(ch)
    for r in roots: assign(r)
    cn=[{"id":nid(n['name']),"type":"file","file":f"{strat_dir}/{n['name']}.md",
         "x":depth[n['name']]*460,"y":int(round(y[n['name']])),
         "width":400,"height":300,"color":n['color']} for n in nodes]
    ce=[{"id":nid(n['parent']+"->"+n['name']),"fromNode":nid(n['parent']),
         "fromSide":"right","toNode":nid(n['name']),"toSide":"left"}
        for n in nodes if n['parent'] is not None]
    return {"nodes":cn,"edges":ce}
```

Canvas 颜色（字符串，**与 Step B6 颜色表同一张**）：`"0"`灰(已替代) `"1"`红(废弃/失败) `"2"`橙(独立分支) `"3"`黄(有衍生) `"4"`绿(活跃/生产) `"5"`青(工具) `"6"`紫(实验)。多根/独立脚本 `parent=None`，自动各占一行。

### Step D6：统一校验（+ 写 manifest）

一段 Python 校验（**必做,不可省**）：
1. `00-总览.md` 每个 `[[wikilink]]` 是否都有对应 `策略/*.md`（断链清单）
2. 反向：有无未被总览引用的孤儿笔记
3. canvas 每个 `node.file` 是否都存在（引用缺失清单）
4. `.obsidian` 三配置齐全、core-plugins 键数=31
5. **写 `.vault-manifest.json`**（scripts[] 覆盖全部脚本），并校验 manifest ↔ 演进树 ↔ canvas 一致

> v2 **默认不锁**。可选归档锁（仅用户要求）：`find "$VAULT_DIR" -type f -name "*.md" -not -path "*/.obsidian/*" -exec chmod 444 {} \;`。**永不锁 .canvas/.obsidian/manifest。**

### Step D7：告知用户 + 缺失即问 + 注册指引

给出每个库的完整路径，提示用 Obsidian「Open folder as vault」逐个打开（勿脚本改全局 `obsidian.json`）。**把批量过程中收集的缺失字段（回测数据缺失、lineage 存疑、代码疑点）汇成一次清单问用户**（批量场景的"缺失即问"），据反馈回填 + 溯源。

---

## 辅助功能

### 更新回测结果

触发：跑完回测（会话内主动），或 `/sync`，或用户口头告知。

Claude 动作：
0. **（仅归档锁定场景）先解锁**：`find "$VAULT_DIR" -type f -name "*.md" -not -path "*/.obsidian/*" -exec chmod u+w {} \;`（v2 默认可写则跳过此步）；
1. **取数**：优先 QuantStats HTML 文件名 → 其次 `output_<script>/results.csv` → 再 MCP → 都没有则**询问用户**（绝不留空）；
2. 更新该笔记"回测结果"表 + 溯源脚注（`来源: qs_html @ 日期` 或 `来源: 用户反馈 @ 日期`）；
3. 更新 `00-总览.md` 的"回测结果汇总"表；
4. `开发日志.md` 文末追加一条（所有结果都记，含不理想的，注明原因避免重复测试）；
5. 更新 `.vault-manifest.json` 该脚本的 `backtest.filled/source/as_of`（`source` 取枚举 `qs_html|results.csv|user|mcp`）；
6. **（仅归档锁定场景）写完后重锁**：`... -exec chmod 444 {} \;`（**永不锁 canvas/.obsidian/manifest**）。

> ⚠️ 顺序铁律：若 vault 归档锁定（`.md` 为 444），**解锁（步 0）必须在所有写操作之前**，重锁（步 6）在之后——否则步 2-5 会因 EACCES 写失败。

### 标记废弃/失败分支

用户口头告知："`script.py` 回测结果差，放弃这个方向"

Claude 动作：
1. 笔记 frontmatter `status: abandoned`，加标签 `failed-branch`；
2. 总览中节点标 🔴/⚪，Canvas 节点颜色改红/灰；
3. **manifest** 该脚本 `status: abandoned`、`color` 同步更新；
4. 开发日志追加一条（含废弃原因，据用户原话）；
5. 三者与 manifest 校验一致。

### 更新策略笔记内容

用户口头告知需补充的内容（策略逻辑说明、新增参数等），Claude 直接改（默认可写）；涉及演进/回测/状态的，同步更新 manifest 并校验一致。

---

## 文件路径速查

| 用途 | 路径 |
|------|------|
| Vault 根 | `<PROJ_DIR>/vault/` |
| Hub 总览 | `<PROJ_DIR>/vault/00-总览.md` |
| 开发日志 | `<PROJ_DIR>/vault/开发日志.md` |
| Canvas 画布 | `<PROJ_DIR>/vault/画布-策略演进.canvas` |
| 策略笔记 | `<PROJ_DIR>/vault/策略/<script_name>.md` |
| **单一真源 manifest** | `<PROJ_DIR>/vault/.vault-manifest.json`（**不加锁**） |
| Obsidian 配置 | `<PROJ_DIR>/vault/.obsidian/`（使 vault 可独立打开;**不加锁**） |
| 回测数据源 | `<PROJ_DIR>/<输出目录>/【…总收益：X%…最大回撤：Y%…】.html`（QS 文件名，优先）；部分目录另有 `results.csv`/`nav_series.csv` |

---

## 禁止行为

- ❌ 将模板清单中的脚本纳入追踪
- ❌ 修改用户 `.py` 源代码文件（只读，除非用户明确要求）
- ❌ 在未确认时覆盖已有 Vault
- ❌ 对多家族策略静默合并（必须警告用户）
- ❌ 删除任何策略笔记（标记为废弃即可）
- ❌ 口头描述 Canvas 但不实际重绘（必须生成/更新 JSON 文件）
- ❌ **默认给任何文件加 chmod 444**（v2 默认可编辑；只有用户明确要求"归档锁"时才锁 `.md`）
- ❌ **字段缺失就留空 / 待补录**（v2：缺失即**询问用户**填写；仅用户授权才占位）
- ❌ **编造任何值**（回测数字、参数、lineage —— 缺则问，绝不猜）
- ❌ **回测指标来自非 QuantStats 报告的渠道**（记忆/估计/别的工具）—— QS 报告是唯一权威，缺则问用户
- ❌ 演进树 / Canvas / frontmatter 与 `.vault-manifest.json` 不一致而不修正
- ❌ **建 vault 却不建 `.obsidian/` 配置**（会导致 vault 埋在总库深层、无法独立打开、用户看不到 —— 曾经的头号缺陷）
- ❌ 给 `.obsidian/` 目录加 chmod 444（Obsidian 需读写自身配置）
- ❌ **给 `.canvas` 文件加 chmod 444**（Obsidian Canvas 打开即写视口/节点状态,只读会报 `EACCES: permission denied` 并渲染空白）
- ❌ Obsidian 打开着某库时重写其 Canvas 而不先提示用户关闭（会被空白内存态覆盖 —— 见 **关键约束 5 · Canvas 安全**）
- ❌ 用脚本直接改全局 `obsidian.json` 注册 vault（Obsidian 运行时会覆盖;改用 UI「Open folder as vault」）

## 关键约束

1. **默认可编辑**：v2 起 vault 文件默认**不加锁**（供用户批注）。仅用户明确要求"归档锁"时才 `chmod 444` **仅 `.md`**；`.canvas` / `.obsidian` / `.vault-manifest.json` **永不加锁**。
2. **缺失即问,绝不留空/编造**：字段无来源 → 询问用户 → 按反馈填 + 溯源标记；仅用户授权才占位。
3. **单一真源**：`.vault-manifest.json` 是唯一真源，演进树/Canvas/frontmatter 由它派生，每次更新后校验一致。
4. **vault 可独立打开**：每个 `vault/` 必须含 `.obsidian/`（app/appearance/core-plugins.json 31 键），使其可被「Open folder as vault」直接打开。
5. **Canvas 安全**：永不锁；用 build_canvas 确定性重画（hash id + 稳定布局，幂等）；**重写前若 Obsidian 正打开该库，先提示用户关标签/退出**，否则空白内存态会覆盖磁盘。
6. **父级推断**：L1(import) > L2(命名) > L3(diff)，无法确定则**询问用户**（不再默认进"未归类"）。
7. **模板隔离**：模板脚本不进入追踪，记录在 manifest.templates。
8. **开发日志 append-only**：只在文末追加，绝不改历史。
9. **幂等性**：重复触发同一脚本应检测笔记/manifest 已存在，跳过或询问是否覆盖。
