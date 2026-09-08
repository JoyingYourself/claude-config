---
name: EngineeringDocGen_HTML_Artifact
description: "Generate beautiful, self-contained single-page HTML artifacts with impeccable, anti-slop design taste — documents, reports, specs, code-review explainers, research explainers, design explorations, and throwaway interactive editors. Shareable and openable in any browser. Optional PSD branding. Use when: making an HTML file or artifact or page, turning a spec/plan/report into readable HTML, building an interactive editor or prototype, or exploring multiple design directions side by side. Triggers on: html artifact, make html, beautiful html, html page, html report, html explainer, design in html, interactive html, html mockup, html one pager."
argument-hint: "[what to build]"
---

# /EngineeringDocGen_HTML_Artifact — HTML 报告生成

Produce a single, self-contained HTML file with impeccable taste. HTML beats Markdown
for specs, reports, reviews, and explorations: it is denser, more readable, more
shareable, and people actually read it. This skill makes HTML that does not look like
a machine made it.

## The one rule everything serves

> If someone could look at the output and say "AI made that" without a doubt, it failed.

Recognizability over default aesthetics. Every choice below exists to defeat the
"visual maximum common denominator" of AI training data (Inter + purple gradient +
beige/brass + eyebrow-on-every-section + ghost cards). Read `references/anti-slop-bans.md`
to know exactly what those tells are and how to refuse them.

## Workflow

Run these in order. Skip nothing in steps 1, 7, and 8.

### 1. Emit a design read (one line, before any code)

State your interpretation so the user can correct it cheaply:

> Reading this as: `<page kind>` for `<audience>`, with a `<vibe>` language, leaning toward `<direction>`.

Examples:
- "Reading this as: an internal engineering spec for the platform team, with a calm
  document language, leaning toward a two-column reading layout with a sticky TOC."
- "Reading this as: a consumer landing page for a coffee subscription, with a warm
  editorial language, leaning toward a split hero + one saturated accent."

Use `AskUserQuestion` ONLY if page-kind, audience, or output format is genuinely
ambiguous. Otherwise infer and proceed; the user can redirect after the design read.

### 2. Set three dials

Infer 1–10 values from the brief; they gate downstream choices:

- `DESIGN_VARIANCE` (1 = perfect symmetry, 10 = artsy chaos)
- `MOTION_INTENSITY` (1 = static, 10 = cinematic)
- `VISUAL_DENSITY` (1 = airy, 10 = packed data)

Signal presets: minimalist/calm/editorial → ~5 / 3 / 3 · data report/dashboard → ~5 / 3 / 7 ·
marketing/agency → ~8 / 7 / 4 · public-sector/trust-first → ~3 / 2 / 5. When `DESIGN_VARIANCE > 4`,
do not use a centered hero — go split-screen, asymmetric, or left-aligned.

### 3. Pick the register and load only what you need

Always read `references/taste-core.md` and `references/anti-slop-bans.md`. Then load the
matching register reference(s) — and nothing else:

| Register | When | Reference |
|----------|------|-----------|
| Document / report | spec, plan, PR/code-review explainer, research writeup, status/incident report | `references/document-patterns.md` |
| Design / marketing | landing page, portfolio, visual identity, hero design | (taste-core + anti-slop are enough) |
| Data / dashboard | dashboard, data-rich report, analysis, KPIs, charts, data-story landing | `references/data-viz.md` + `references/dashboard-patterns.md` |
| Interactive editor | tune values, reorder/triage, annotate, export-as-prompt | `references/interactive-patterns.md` |
| Multi-variant | "give me N directions to compare" | `references/multivariant.md` |

A single task may combine registers. Load the union: a charted report pulls document-patterns
+ data-viz; a data-story landing pulls dashboard-patterns + data-viz; a dashboard with filters
adds interactive-patterns. Add interactive/variant machinery only where the task needs it. The
`assets/chart-snippets.html` scaffold has data-driven inline-SVG charts and KPI cards to copy.

### 4. Decide branding (taste-first; PSD opt-in)

Default to distinctive, brief-appropriate taste with NO district branding. Apply PSD
branding only when the user asks, or the audience is clearly PSD/internal/district
(board, staff, families, school program). When branding: follow `references/psd-branding.md`
— read real colors/fonts/logos from the existing `psd-brand-guidelines` skill; never
AI-generate or CSS-silhouette a logo.

### 5. Gather context honestly

- **Facts first**: WebSearch-verify any product/version/spec/statistic before asserting
  it. Searching 10 seconds beats a confident wrong claim.
- **Real images, not fake divs**: use an image tool, real stock URLs (Unsplash/Pexels),
  or `https://picsum.photos/seed/<seed>/<w>/<h>`. A `<div>` mocked up as a fake dashboard
  or terminal is a tell. If you have no real asset, use an honest labeled placeholder.
- **No invented stats**: a fake-precise number (`92%`, `4.1×`) is banned unless it is
  real data or explicitly labeled as mock.

### 6. Build

Start from `assets/base-scaffold.html` (structural only — reset, a11y, reduced-motion,
print CSS, an embedded pre-flight comment). Keep everything self-contained: inline CSS,
inline vanilla JS, fonts via CDN `<link>`. The file must work opened directly via
`file://` (no build step, no bundler, no `<script src="local.js">`). Apply the taste
rules and the chosen aesthetic. For interactive editors, always end with an export
button ("copy as JSON / markdown / prompt") so the user can paste state back into Claude.

**Output location**: default to the current working directory. If the user named a path
or the context is clearly personal, write to `~/Downloads`. Use a short, descriptive,
kebab-case filename.

### 6.5 投屏/汇报类页面：交互模式与双版交付（用户拍板规范，强制）

适用于投屏汇报稿、培训材料、演示型报告。两类规范缺一不可：

**A. 交互模式：骨架 + 点击下钻（2026-08-26 用户拍板，普遍推广）**

- 先给"骨架"（公式 / 列表 / 结构图 / 卡片集），内容不直接平铺，而是**点击部件/条目就地展开详情**——展示层次逐层下钻，避免长页平铺割裂
- 展开规则：点开详情（同一时刻只开一个），再点收起；切换即关旧开新
- 键盘可操作：`tabindex="0"` + `role="button"` + Enter/空格展开收起；**空格不得触发全局翻页**（box 的 keydown 需 `preventDefault` + `stopPropagation`）
- 无障碍：`aria-expanded` 随状态更新
- 推广原则：所有模块/区块统一此交互，不设例外（信息密度已极低、无"详情"可下钻的对照型小组件除外，如四要素小卡、红绿对照）

**B. 双版交付：本机版 + 离线版（2026-08-26 用户拍板，缺一不可）**

最终交付的报告需做**两个版本**，单文件 + 版本切换实现（同一 HTML 内 `body` class 切换，选择可存 localStorage）：

| 版本 | 场景 | 呈现方式 |
|------|------|---------|
| **本机版**（默认） | 在自己的电脑上展示 | 展示内容**链接电脑实际配置**：`file://` 链接可直接跳转本地真实文件/目录（MCP 服务目录、skill 目录、CLAUDE.md、数据库目录等），点击即打开，现场演示真实配置 |
| **离线版** | 其他电脑展示（公司设备） | 规避 Mac 与展示设备不兼容：所有 `file://` 链接替换为**描述文字**（如"📄 MCP 配置目录"），不可点击、不依赖本机文件，显示效果与预期一致 |

- 页面顶部提供**版本切换控件**（本机版 / 离线版按钮，醒目可点）
- 链接统一标记 `.file-link`：本机版渲染为 `<a href="file://...">`（前缀 🔗），离线版降级（`pointer-events:none`、灰显、前缀 📄）
- 说明性文本中不得出现仅本机才成立的表述（如直接写路径），路径一律放链接内
- **汇报前自测（强制）**：每次阶段性成果汇报前，调用 chrome MCP 完成**模拟用户操作的完整测试**（翻页导航、各点击下钻组件的展开/收起/切换/键盘、版本切换与 localStorage 记忆、file 链接可点性），测试通过才允许汇报

**C. 公司品牌配色规范（2026-08-31 用户拍板：白 70% / 金 20% / 黑 5% / 灰 5%）**

中邮资管公司报告（路演材料/一页通）配色规范，任何公司相关 HTML 产物（投屏稿/报告/材料）强制遵守：

- **比例铁律**：白色 70%（页面底、卡片底）· 金色 20%（主强调，必须有"面"不能只有"线"）· 黑色 5%（标题/正文主文字）· 灰色 5%（次要文字/边框/层次底）。深蓝不得作主色（路演材料曾用深蓝，一页通系为金色主题——以金色为准）
- **金色分层**（玖泰1号一页通实测）：主金 `#b08f1c`（数据/图形/高亮/链接）· 深金 `#8a6f45`（文字型金：注释/坐标/次要金字）· 深金黄 `#96751a`（面板小标题/警示）· 亮金 `#d4b45c`（hover/装饰次亮）· 米金渐变 `#c8a53d→#d4b45c→#e3ce8f→#f0e6ce→transparent`（页眉装饰条、封面/标题页渐变底）
- **语义色**：红 `#c53030` / 绿 `#38a169`（仅语义：适合/不适合、风险，占比小）；人名强调深红棕 `#8c2f22`（一页通用法）
- **图形配色映射**（什么图形用什么色，一页通实测）：页眉装饰条→金色渐变；数据曲线/折线/柱形/数据点→主金 `#b08f1c`，曲线填充→主金降透明度渐变（28%→2%）；关键数据高亮→主金加粗（`#b08f1c` bold）；面板小标题→深金黄 `#96751a`；坐标轴/图注→深金 `#8a6f45`；网格虚线→米金 `#e8d9b6`；最新数据点→主金 + 米白描边 `#fdf6e8`；正文→深灰 `#595959`
- **落地要点**：①金色作主强调色时底色必配**深色文字**（如 `#2b2105`），禁止金底白字（对比度不足）；②投屏/大留白页面金色必须有大面积载体（封面/标题页米金渐变底、金色装饰线、金胶囊徽标、金边卡片），单靠文字变色凑不出 20% 视觉占比；③正文标题黑 `#1a1a1a`，正文灰 `#595959`，层次底米白 `#f7f4ec`；④终端/代码演示块（黑底）作为"内容黑盒"保留，其内部荧光绿 prompt 为真实终端颜色勿改，可加金色外边框融入主题

### 7. Run the pre-flight self-audit gate

Before delivering, run every check in `references/preflight-audit.md` against the file
you just wrote (grep it). Fix every failure. Then delete the pre-flight comment block
from the scaffold. Report a one-line pass summary, e.g.:
`Audit: 1 accent locked · 2 eyebrows / 7 sections · all buttons one-line · contrast ok · reduced-motion present.`

### 8. Open and hand off

Open it for the user: `bash scripts/open.sh <path>`. Give them the absolute path, and
note for sharing: upload to any static host / S3 / Drive for a link. Mention the one
real tradeoff if relevant: HTML diffs are noisier than Markdown in version control.

**Sharing inside PSD:** the `/psd-atrium` skill publishes this file into Atrium (AI
Studio's content workspace) as an interactive artifact with a real intranet URL —
`create-artifact --code-file <path>` then `publish --id <id>`. Offer it when the user
wants a link to send colleagues rather than a file to email. Two constraints worth
stating up front: pass the file with `--code-file` (an inline argument over 128 KiB
fails to spawn), and published artifacts run under `connect-src 'none'`, so anything
that fetches data at runtime will silently do nothing — inline the data instead.

## Hard "do not" list (full reasoning + fixes in references)

- Never `Inter`/`Roboto`/`Arial` by reflex; never `Fraunces`/`Instrument Serif` display serifs.
- Never AI-purple/violet glow gradients as a default accent.
- Never the beige/cream + brass/clay/oxblood "premium-craft" palette as a default.
- Never an eyebrow (tiny uppercase tracked label) above every section.
- Never a ghost card (`1px border` + big `box-shadow` together); never `border-radius: 32px+` on cards.
- Never em-dashes in visible copy; never marketing buzzword soup (seamless, leverage, supercharge…).
- Never serif "because it feels premium" — serif needs an explicit editorial/heritage reason.
- Never more than one accent color on a page; lock it and audit every component.
