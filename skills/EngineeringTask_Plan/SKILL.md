---
name: EngineeringTask_Plan
description: 项目任务规划工作流 — 接收项目路径，判断新/老项目，生成 README.md（agent间信息传递）和可编辑任务规划 HTML 报告（含"同意并执行"按钮）。触发词：任务规划、项目规划、task plan、新项目、规划报告。
---

# /EngineeringTask_Plan — 项目任务规划

## 角色定位

接收用户指定的项目路径，自动化项目初始化与任务规划流程：

- **路径下有 README.md** → 老项目新需求：读取 README 理解上下文 → 与用户沟通增量需求 → 生成可编辑的任务规划 HTML 报告
- **路径下无 README.md** → 新项目：创建项目文件夹 → 与用户沟通需求 → 生成 README.md（agent 间信息传递）→ 生成可编辑的任务规划 HTML 报告

**两份产出物**：

| 文件 | 受众 | 格式 | 用途 |
|------|------|------|------|
| `README.md` | Agent ↔ Agent | Markdown，结构化章节 | 信息传递：总需求、任务阶段、已有成果、踩坑记录。后续 agent 可通过读取此文件快速理解项目全貌 |
| `task-plan.html` | 人 ↔ Agent | 可编辑 HTML | 任务规划：分阶段任务清单、依赖关系、里程碑。可在浏览器中直接编辑文本，"同意并执行"按钮触发 agent 按规划实施 |

## 路由

本 Skill 不绑定特定 MCP Server。依赖文件系统读写和 WebFetch（如需读取远程 README）。

## 输入格式

用户直接调用，需提供：

```
/EngineeringTask_Plan <项目路径>
```

例：`/EngineeringTask_Plan /Users/junye_shi/AgentFiles/backtest_Gil/`

可选附加参数（在对话中提供）：
- `--name` 项目名称（新项目时必填）
- `--description` 项目简述（新项目时选填，不填则从对话中提取）

---

## 交互协议

### Step 1：路径检查与路由判断

1. 读取用户指定的项目路径
2. 检查路径是否存在：
   - 路径存在且含 `README.md` → **路由 A：老项目新需求** → 跳至 Step 2A
   - 路径存在但无 `README.md` → **路由 B：初始化已有目录** → 跳至 Step 2B
   - 路径不存在 → **路由 C：新建项目** → 跳至 Step 2C

```
                   用户提供路径
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
      路径存在       路径存在       路径不存在
      含README       无README
            │            │            │
        路由 A        路由 B        路由 C
      老项目新需求   已有目录初始化   新建项目
```

### Step 2A：老项目新需求（路由 A）

1. **读取 README.md**：全文阅读，提取关键信息：
   - 项目目标与背景
   - 已有成果（哪些阶段已完成）
   - 当前进度（正在进行中的阶段）
   - 踩坑记录（已知问题和解决方案）
   - 技术栈和依赖

2. **与用户沟通增量需求**：
   - 根据 README 已有信息，询问用户本次新增需求是什么
   - 确认增量需求是否与已有成果冲突
   - 确认是否需要在踩坑记录中追加新发现的问题

3. **更新 README.md**（如有变更）：
   - 在 README 中追加新的需求描述
   - 更新任务阶段状态（如某阶段从"进行中"→"已完成"）
   - 追加新的踩坑记录（如有）

4. **生成任务规划 HTML** → 跳至 Step 3

### Step 2B：已有目录初始化（路由 B）

1. 告知用户目录已存在但无 README.md
2. 询问用户：这是否为需要补建 README 的已有项目？
   - 是 → 按 Step 2C 的方式沟通需求，在该目录下生成 README.md
   - 否 → 询问正确的路径

### Step 2C：新建项目（路由 C）

1. **创建项目文件夹**：
   ```bash
   mkdir -p <项目路径>
   ```

2. **与用户沟通需求**（必须逐项确认，不可跳过）：
   - **Q1: 项目目标** — 这个项目要解决什么问题？
   - **Q2: 最终产出物** — 完成后交付什么？（代码/SQL/报告/数据集/策略脚本...）
   - **Q3: 技术约束** — 语言？框架？数据源？部署环境？
   - **Q4: 时间约束** — 有 deadline 吗？分几个阶段交付？
   - **Q5: 已有资源** — 是否有可复用的代码/数据/文档？

3. **生成 README.md** → 跳至 Step 3（先生成 README，再生成 HTML）

### Step 3：生成 README.md（仅路由 C 新项目）

生成结构化的 `README.md`，写入到 `<项目路径>/README.md`。

**README.md 必须包含以下章节**（agent 间信息传递的标准格式）：

```markdown
# <项目名称>

## 📋 总需求

<一句话描述项目目标 + 3-5 条核心需求>

## 🗺️ 任务阶段

| 阶段 | 状态 | 描述 | 产出物 | 完成时间 |
|------|------|------|--------|---------|
| Phase 1 | ⏳ 待开始 | <描述> | <产出> | — |
| Phase 2 | ⏳ 待开始 | <描述> | <产出> | — |
| ... | ... | ... | ... | ... |

状态标记: ✅ 已完成 / 🔄 进行中 / ⏳ 待开始 / ❌ 已放弃 / ⚠️ 阻塞

## 📦 已有成果

<如果是新项目，写"项目初始化阶段，暂无成果">
<如果是老项目，列出已完成的文件、代码、数据等>

## 🕳️ 踩坑记录

<格式: 日期 — 问题描述 — 根因 — 解决方案>
<新项目可写"暂无">

## 🔗 技术栈

| 组件 | 选型 | 备注 |
|------|------|------|
| 语言 | Python 3.13 | |
| 数据 | DuckDB / 聚源 | |
| ... | ... | ... |

## 📁 关键文件索引

| 文件/目录 | 用途 |
|-----------|------|
| `task-plan.html` | 本次任务规划报告 |
| ... | ... |
```

**写入约束**：
- 路径必须为 `<用户指定路径>/README.md`
- 若该路径已存在 README.md，更新而非覆盖（追加新阶段 + 更新状态）
- 写入前向用户展示完整内容，确认后再写入

### Step 4：生成任务规划 HTML 报告

生成 `<项目路径>/task-plan.html`。**HTML 报告必须包含以下特性**：

**4a. CSS 样式要求**：
- GitHub Dark 主题色系（`--bg: #0d1117; --surface: #161b22` 等）
- 响应式布局，适合在浏览器中阅读和编辑
- 任务卡片的视觉层次清晰

**4b. 内容结构**：

```
┌─────────────────────────────────────────┐
│ 📋 <项目名称> — 任务规划报告              │
│ 生成时间 / 项目路径 / README版本          │
├─────────────────────────────────────────┤
│                                         │
│ 📊 项目概览                              │
│  └ 目标 / 当前进度 / 关键里程碑           │
│                                         │
│ 🗺️ 任务阶段 (从 README.md 读取)          │
│  ┌ Phase 1: <阶段名> [⏳待开始]          │
│  │   ├ 任务 1.1: <描述>                  │
│  │   ├ 任务 1.2: <描述>                  │
│  │   ├ 依赖: 无                          │
│  │   └ 产出: <具体文件/结果>              │
│  ├ Phase 2: ...                         │
│  └ ...                                  │
│                                         │
│ ⚠️ 风险与注意事项 (从踩坑记录提取)         │
│                                         │
│ 📁 产出物清单                             │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ [✅ 同意并开始执行]  [✏️ 修改计划]    │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

**4c. 交互功能（必须实现）**：

1. **✏️ 编辑模式按钮**（右下角浮动）：
   - 点击后所有任务描述文本变为 `contenteditable="true"`
   - 编辑过的元素自动添加黄色高亮 `.edited`
   - 再次点击退出编辑模式

2. **📋 复制修改内容按钮**（编辑模式时显示）：
   - 收集所有 `.edited` 元素的修改内容
   - 复制到剪贴板，用户可粘贴给 agent

3. **✅ 同意并开始执行按钮**（报告末尾）：
   - 用户点击后，agent 开始按 Phase 顺序执行任务
   - 点击时触发 `alert("任务规划已确认，请切换回 Claude Code 会话，Agent 将按照 Phase 1 → Phase N 的顺序开始执行。")` 提示用户切回终端

4. **📊 进度追踪**：
   - 每个 Phase 卡片有状态标识
   - 可在编辑模式下修改状态（⏳ → 🔄 → ✅）

**4d. HTML 模板**：

参考附录中的完整 HTML 模板。核心要求：
- `<script>` 中实现 `toggleEdit()`、`copyChanges()`、`agreeAndStart()` 三个函数
- CSS 变量体系与 MCP 报告一致
- 所有任务描述文本包裹在 `.desc-new` 或 `.task-desc` 类中（以便编辑模式选中）

### Step 5：确认与交付

1. 展示生成的 README.md 摘要和 task-plan.html 路径
2. 提醒用户：
   - 可在浏览器中打开 `task-plan.html`，直接编辑任务描述
   - 修改后点"复制修改内容"粘贴给 agent
   - 确认无误后点"同意并开始执行"
3. **如果用户直接点击了"同意并开始执行"** → agent 按 Phase 顺序读取 README.md + task-plan.html，逐 Phase 实施

### Step 6：同步维护（强制执行，不可跳过）

**每次对任务做出修改或执行完成后，必须同步更新 README.md 和 task-plan.html。** 两份文件始终反映项目的最新状态。

**6a. 触发条件（以下任一发生时立即执行同步）：**

| 触发事件 | 更新内容 |
|---------|---------|
| Phase 状态变更（⏳→🔄→✅） | README 任务阶段表的状态列 + HTML 对应 Phase 卡片的 status class 和标签 |
| 新增/删除/修改任务 | README 任务阶段表中该 Phase 的任务列表 + HTML 对应 Phase 的 task-list |
| 踩坑记录新增 | README 踩坑记录章节追加 + HTML 风险卡片区追加 |
| 产出物完成 | README 已有成果章节更新 + HTML 产出物清单状态图标更新 |
| 用户通过 HTML 编辑模式修改了内容并粘贴回来 | 先更新 README（权威源），再根据 README 重新生成 HTML 中的对应部分 |
| Phase 全部完成 | README 已有成果章节汇总所有产出 + HTML 概览进度更新 |

**6b. 同步顺序（不可颠倒）：**

```
用户修改/任务执行完成
       │
       ▼
1. 更新 README.md（权威数据源）
       │
       ▼
2. 根据 README.md 更新 task-plan.html
   （Phase 状态 / 任务列表 / 产出物 / 风险 / 踩坑记录）
       │
       ▼
3. 向用户确认："README.md 和 task-plan.html 已同步更新"
```

**6c. README.md 更新规则：**

- **状态变更**：修改任务阶段表中对应 Phase 的状态标记（⏳→🔄→✅）
- **成果追加**：在「已有成果」章节追加新完成的产出物路径+简述
- **踩坑追加**：在「踩坑记录」章节按日期格式追加新记录
- **新增 Phase**：在任务阶段表末尾追加新行
- **修改已有内容**：直接修改对应行，不追加

**6d. task-plan.html 更新规则：**

- **状态变更**：修改 Phase 卡片 `<div class="card pending">` → `active` → `done`，对应 status 标签文字和 class
- **任务列表**：与 README 任务阶段表保持行级一致
- **产出物清单**：与 README 已有成果章节保持一一对应
- **风险卡片**：与 README 踩坑记录保持一一对应
- **概览数字**：总阶段数/当前进度/已产出文件数 随实际进展更新

**6e. 禁止的同步方式：**

- ❌ 只更新 README 不更新 HTML（或反之）
- ❌ 先更新 HTML 再更新 README（README 是权威源）
- ❌ 修改 HTML 后不把变更回写到 README
- ❌ Phase 完成后不更新状态（两份文件与实际进度不一致）
- ❌ 用"大致一样就行"的心态做同步（两份文件必须在任务级别精确一致）

---

## 与其他 Skill 的勾稽关系

| 上游/下游 | Skill | 数据流 |
|-----------|-------|--------|
| 下游 | 任意 Skill | task-plan.html 中的 Phase 可指定调用其他 Skill（如 ResearchGil_Factor_Test） |
| 同级 | 无 | 独立运行，不依赖其他 Skill |
| 联动 | `EngineeringSkill_Scaffold` | 若规划中涉及新建 Skill，可联动调用 |

## 禁止行为

- ❌ 跳过 Step 2A/2C 的用户需求确认步骤（路由 A 必须读取 README 后与用户确认增量需求；路由 C 必须逐项确认 Q1-Q5）
- ❌ README.md 章节不完整（禁止缺少"总需求""任务阶段""已有成果""踩坑记录"任一章节）
- ❌ HTML 报告缺少编辑模式或"同意并开始执行"按钮
- ❌ 在用户未点击"同意并开始执行"之前开始实施任务
- ❌ 覆盖已有 README.md 时不清算已有成果（必须追加而非覆盖）
- ❌ 生成 HTML 时使用外部 CDN 资源（必须完全自包含，离线可用）
- ❌ 忘记在 HTML 中嵌入 `toggleEdit()`、`copyChanges()`、`agreeAndStart()` 三个 JS 函数
- ❌ task-plan.html 中的 Phase 任务描述模糊（每个任务必须有具体的产出物文件路径）
- ❌ 任务修改或执行后不同步更新 README.md 和 task-plan.html（Step 6 强制执行）
- ❌ 只更新其中一份文件（README 和 HTML 必须同步，README 是权威源优先更新）
- ❌ Phase 完成后状态仍标记为 ⏳/🔄（两份文件的进度必须与实际一致）

---

## 附录：HTML 模板参考

完整的 task-plan.html 模板。生成时替换 `{{占位符}}`。

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{项目名称}} — 任务规划报告</title>
<style>
  :root {
    --bg: #0d1117; --surface: #161b22; --surface2: #1c2333; --border: #30363d;
    --text: #c9d1d9; --text2: #8b949e; --accent: #58a6ff; --green: #3fb950;
    --orange: #d2991d; --red: #f85149; --purple: #a371f7;
  }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; background:var(--bg); color:var(--text); line-height:1.6; padding:2rem; }
  .container { max-width:1100px; margin:0 auto; }
  h1 { font-size:1.6rem; border-bottom:2px solid var(--border); padding-bottom:0.5rem; color:#f0f6fc; }
  h2 { font-size:1.2rem; margin:2rem 0 0.75rem; color:#f0f6fc; border-bottom:1px solid var(--border); padding-bottom:0.3rem; }
  h3 { font-size:1rem; margin:1.2rem 0 0.5rem; color:var(--accent); }

  .meta { display:flex; gap:2rem; flex-wrap:wrap; color:var(--text2); font-size:0.8rem; margin-bottom:1.5rem; }
  .meta span { display:flex; align-items:center; gap:0.3rem; }

  .card { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:1.25rem; margin:1rem 0; }
  .card.phase-pending  { border-left:3px solid var(--text2); }
  .card.phase-active   { border-left:3px solid var(--orange); }
  .card.phase-done     { border-left:3px solid var(--green); }
  .card.phase-blocked  { border-left:3px solid var(--red); }

  .phase-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem; }
  .phase-status { font-size:0.8rem; padding:0.2rem 0.6rem; border-radius:1rem; font-weight:600; }
  .phase-status.pending  { background:rgba(139,148,158,0.15); color:var(--text2); }
  .phase-status.active   { background:rgba(210,153,29,0.15); color:var(--orange); }
  .phase-status.done     { background:rgba(63,185,80,0.15); color:var(--green); }
  .phase-status.blocked  { background:rgba(248,81,73,0.15); color:var(--red); }

  .task-list { list-style:none; }
  .task-item { padding:0.5rem 0; border-bottom:1px solid rgba(48,54,61,0.5); font-size:0.88rem; }
  .task-item:last-child { border-bottom:none; }
  .task-check { color:var(--text2); margin-right:0.5rem; }
  .task-dep  { font-size:0.78rem; color:var(--orange); margin-left:0.5rem; }
  .task-out  { font-size:0.78rem; color:var(--purple); margin-left:0.5rem; }

  .overview-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:0.75rem; margin:1rem 0; }
  .overview-item { background:var(--surface2); border-radius:6px; padding:0.75rem; text-align:center; }
  .overview-label { font-size:0.75rem; color:var(--text2); }
  .overview-value { font-size:1.1rem; font-weight:600; margin-top:0.2rem; }

  .risk-card { background:rgba(248,81,73,0.06); border:1px solid rgba(248,81,73,0.2); border-radius:6px; padding:0.75rem 1rem; margin:0.5rem 0; font-size:0.85rem; }

  .action-bar { display:flex; gap:1rem; justify-content:center; margin:2.5rem 0 1rem; }
  .btn { padding:12px 28px; border-radius:8px; font-size:1rem; font-weight:600; cursor:pointer; border:none; font-family:inherit; }
  .btn-agree { background:var(--green); color:#000; }
  .btn-agree:hover { opacity:0.9; }
  .btn-edit { background:var(--surface); color:var(--text); border:1px solid var(--border); }

  /* ── 编辑模式 ── */
  #edit-toolbar { position:fixed; bottom:20px; right:20px; z-index:9999; display:flex; gap:8px; }
  #edit-toolbar button { padding:8px 14px; border-radius:6px; border:1px solid var(--border); background:var(--surface); color:var(--text); cursor:pointer; font-size:0.82rem; font-family:inherit; }
  #edit-toolbar button:hover { border-color:var(--accent); color:var(--accent); }
  #edit-toolbar button.active { background:rgba(88,166,255,0.15); border-color:var(--accent); color:var(--accent); }
  [contenteditable="true"] { outline:2px dashed rgba(88,166,255,0.5); outline-offset:2px; border-radius:3px; }
  [contenteditable="true"]:hover { outline-color:var(--accent); background:rgba(88,166,255,0.04); }
  .edited { background:rgba(210,153,29,0.1) !important; outline-color:var(--orange) !important; }
  .copied-toast { position:fixed; top:20px; left:50%; transform:translateX(-50%); background:var(--green); color:#000; padding:10px 20px; border-radius:6px; font-size:0.85rem; z-index:9999; display:none; }

  footer { margin-top:3rem; padding-top:1.5rem; border-top:1px solid var(--border); color:var(--text2); font-size:0.78rem; text-align:center; }
</style>
<script>
let editMode = false;
function toggleEdit(){
  editMode = !editMode;
  document.querySelectorAll('.task-desc, .task-out-detail, .risk-desc, .overview-value, .card p, .card li').forEach(el => {
    el.contentEditable = editMode;
    if(!editMode) el.classList.remove('edited');
    if(editMode) el.addEventListener('input', ()=>el.classList.add('edited'), {once:true});
  });
  const btn = document.getElementById('btn-edit');
  btn.textContent = editMode ? '🔒 退出编辑' : '✏️ 编辑模式';
  btn.classList.toggle('active', editMode);
  document.getElementById('btn-copy').style.display = editMode ? '' : 'none';
  // 也可编辑状态标签
  document.querySelectorAll('.phase-status').forEach(el => {
    el.contentEditable = editMode;
  });
}
function copyChanges(){
  const edits = [];
  document.querySelectorAll('.edited').forEach((el,i) => {
    edits.push('=== 修改 '+(i+1)+' ===');
    edits.push('位置: ' + (el.closest('.card')?.querySelector('h3')?.innerText || el.className));
    edits.push('内容: ' + el.innerText);
    edits.push('');
  });
  const text = edits.length ? edits.join('\n') : '（未检测到修改。请先在编辑模式下点击文本修改内容。）';
  navigator.clipboard.writeText(text).then(()=>{
    const t = document.getElementById('toast');
    t.style.display='block'; setTimeout(()=>t.style.display='none',2000);
  });
}
function agreeAndStart(){
  alert('✅ 任务规划已确认\n\nAgent 将按照 Phase 1 → Phase N 的顺序开始执行。\n请切换回 Claude Code 会话。');
}
</script>
</head>
<body>
<div id="toast" class="copied-toast">✅ 已复制到剪贴板，粘贴给 Claude 即可</div>
<div id="edit-toolbar">
  <button id="btn-copy" style="display:none" onclick="copyChanges()">📋 复制修改内容</button>
  <button id="btn-edit" onclick="toggleEdit()">✏️ 编辑模式</button>
</div>
<div class="container">

<h1>📋 {{项目名称}} — 任务规划报告</h1>
<div class="meta">
  <span>📅 {{生成时间}}</span>
  <span>📁 {{项目路径}}</span>
  <span>📄 基于 README.md v{{版本}}</span>
</div>

<!-- 项目概览 -->
<h2>📊 项目概览</h2>
<div class="overview-grid">
  <div class="overview-item">
    <div class="overview-label">总阶段数</div>
    <div class="overview-value">{{阶段总数}}</div>
  </div>
  <div class="overview-item">
    <div class="overview-label">当前进度</div>
    <div class="overview-value">{{当前进度}}</div>
  </div>
  <div class="overview-item">
    <div class="overview-label">预计产出</div>
    <div class="overview-value">{{预计产出数}} 个文件</div>
  </div>
  <div class="overview-item">
    <div class="overview-label">风险项</div>
    <div class="overview-value" style="color:var(--orange);">{{风险数量}}</div>
  </div>
</div>

<!-- 任务阶段 -->
<h2>🗺️ 任务阶段</h2>
<p style="color:var(--text2); font-size:0.82rem;">每个 Phase 按顺序执行。可在编辑模式下修改任务描述和状态。</p>

<!-- Phase 卡片: 根据 README.md 的任务阶段表格动态生成 -->
{{#each phases}}
<div class="card phase-{{status_class}}">
  <div class="phase-header">
    <h3>{{phase_title}}</h3>
    <span class="phase-status {{status_class}}">{{status_label}}</span>
  </div>
  <ul class="task-list">
    {{#each tasks}}
    <li class="task-item">
      <span class="task-check">{{check_icon}}</span>
      <span class="task-desc">{{description}}</span>
      {{#if dependency}}<span class="task-dep">🔗 依赖: {{dependency}}</span>{{/if}}
      <span class="task-out">📦 产出: <span class="task-out-detail">{{output}}</span></span>
    </li>
    {{/each}}
  </ul>
  <p style="font-size:0.78rem; color:var(--text2); margin-top:0.5rem;">
    ⚡ 预估工时: {{estimated_hours}}
  </p>
</div>
{{/each}}

<!-- 风险 -->
<h2>⚠️ 风险与注意事项</h2>
{{#each risks}}
<div class="risk-card">
  <strong>⚠️ {{title}}</strong>
  <p class="risk-desc" style="margin-top:0.25rem;">{{description}}</p>
  <p style="font-size:0.78rem; color:var(--text2);">缓解措施: {{mitigation}}</p>
</div>
{{/each}}

<!-- 产出物清单 -->
<h2>📁 产出物清单</h2>
<div class="card">
  <ul style="list-style:none;">
    {{#each deliverables}}
    <li style="padding:0.3rem 0; font-size:0.88rem; font-family:'SF Mono','Fira Code',monospace;">
      {{status_icon}} <code>{{path}}</code> — {{description}}
    </li>
    {{/each}}
  </ul>
</div>

<!-- 操作按钮 -->
<div class="action-bar">
  <button class="btn btn-edit" onclick="toggleEdit()">✏️ 修改计划</button>
  <button class="btn btn-agree" onclick="agreeAndStart()">✅ 同意并开始执行</button>
</div>

<footer>
  由 EngineeringTask_Plan 生成 · {{生成时间}} · README.md 版本: {{版本}}
</footer>

</div>
</body>
</html>
```

**模板使用说明**：
- `{{占位符}}` 由 agent 在生成 HTML 时替换为实际内容
- `{{#each phases}}` 等块级占位符表示循环生成多个卡片
- Phase 的 `status_class` 映射: ⏳待开始→`pending`, 🔄进行中→`active`, ✅已完成→`done`, ⚠️阻塞→`blocked`
- 所有 `.task-desc`、`.risk-desc`、`.task-out-detail` 类的元素在编辑模式下自动变为可编辑
