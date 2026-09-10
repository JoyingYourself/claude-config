# claude-config — Claude Code 全局配置仓库(README · 全量)

> 2026-09-08 重建(历史 README_claudeconfig.md 与 setup.sh 已删除,内容并入本文)。本文件 + HANDOFF.md + ATTENTION.md 为三文档体系。
> ⭐ **本仓库总览特有(其他项目总览 = 普通 README)**:顶端附运行位实况,见下节。

## ⚡ 运行位实况(~/.claude · 快照 2026-09-08)

> 配置"生效位" = `~/.claude`(Claude Code 启动实际读取处)。以下为当前实况,**直观核对用,无需跳访达**;快照由维护会话更新。

| 生效项 | 实况 | 与仓库关系 |
|---|---|---|
| CLAUDE.md / lessons.md | 存在(lessons 31.5KB) | ✅ 同步(变更随会话收尾即推) |
| settings.json | 存在 | ✅ 同步(私有仓库可入库,0908 拍板) |
| settings.local.json | 存在(本机私有) | 不入库,每机独立 |
| hooks/ | 12 个生效脚本 | ✅ 同步 |
| skills/ | **28 项 = 全部直写归仓库**(2026-09-10 起;lark-* 28 已下沉至 feishu 项目级) | 仓库管直写;2026-09-08 清理 14 个工作区/废弃残留 |
| workflows/ | 空 | 业务工作流归业务工作区,全局不驻留 |
| commands/ | 空(已废弃) | — |
| plugins/ projects/ sessions/ 等 | Claude Code 运行时数据 | 不入库 |

## 项目定位

**Claude Code 全局层配置的唯一管理者**。凡 `~/.claude` 下生效的配置文件,不论产物物理位置,配置归属均在本仓库;Mac/Windows 双机经 git 同步。本仓库**不含**各工作区配置(工作区自己的 `.claude/` 各自独立仓库,见 AccumulatingWisdom 工程维护体系)。

## 布局地图(仓库 ↔ 运行位)

```
~/claude-config/                ← 本仓库(配置源,唯一真源)
    ├── CLAUDE.md               全局会话指令(个人规则)
    ├── lessons.md              全局教训库
    ├── settings.json           全局设置(含 env 模型路由)
    ├── hooks/                  生命周期钩子(12)
    ├── skills/                 全局技能(28 直写实体;lark 已下沉 feishu)
    ├── README.md / HANDOFF.md / ATTENTION.md   三文档(本文含运行位实况)
    └── (settings.local.json 每机独立,不入库)

~/.claude/                      ← Claude Code 运行位(生效副本)
    ├── CLAUDE.md / lessons.md / settings.json / hooks/
    ├── skills/  = 仓库 skills 28(全部直写;lark 归 feishu 项目级)
    ├── settings.local.json     本机独立(不入库)
    └── plugins/ projects/ sessions/ 等  运行时数据(不入库)
```

## 模块细分(每模块维护位)

| 模块 | 数量 | 说明 |
|---|---|---|
| skills/ | 25 实体 | 全局技能全家:Engineering_*(审计/验证/脚手架/长任务)13、DocumentJournal_* 2、ResearchGil_Data_* 2、external-apps、frontend-design、obsidian-markdown、baoyu-design、cli-anything、engineering 内嵌组 |
| ~~skills/lark-*~~ | **已下沉(2026-09-10)** | 28 个 lark skill 迁至 `AgentFiles/feishu/.claude/skills/`(项目级);全局不再挂载 |
| hooks/ | 11 | 教训纪律 3(lesson-guard/verify-reminder/config-change-reminder)、项目纪律 1(project-type-prompt)、状态栏 2(market-ticker¹/statusline-combined)、自动化 5(autopilot-* 3 + auto-validate + register-process);¹market-ticker 未挂 settings,下游为中邮资管 market-data 守护文档引用(手动工具,勿删) |
| commands/ | 0 | 已废弃(运行位无此机制) |
| workflows/ | 0 | ⚠️ 曾含 ChinapostAMC_StrategyOrder(全局旧版 8/3);2026-09-08 双版本收敛:正版 = 中邮资管/.claude/workflows 项目级 9/2 场景化版,全局已删(commit 8a41fd6)。业务工作流归业务工作区,全局不驻留 |
| CLAUDE.md / lessons.md | 2 | 高频变更,随会话纪律收尾即推 |

## 部署与同步(现状与纪律)

- **现状**:符号链接部署模式已废弃(2026-07 后运行位改为直写,曾致仓库停滞失去定义,2026-09-08 补推恢复同步 commit `81eee9b`)。
- **纪律(仓库为准)**:①任何全局配置变更 → 编辑 `~/claude-config` → commit + push ②运行位同步 = 将变更文件复制到 `~/.claude` 对应路径(setup.sh 符号链接部署已废弃删除,2026-09-08)③重大变更即推,禁止裸改运行位 ④新增全局 skill/配置先过归属判定(全局→本仓库;工作区→各区 .claude 仓库)⑤lark 系技能 = feishu 项目级(2026-09-10 下沉;此前挂全局链接),本仓库不复制。
- **双机**:git clone 到每台机器 → 复制部署;`settings.local.json` 每机独立,内容不入库。

## 安全

- `settings.json` 含 ANTHROPIC_AUTH_TOKEN(DeepSeek 路由)。**已确认仓库为私有,可入库(2026-09-08 用户拍板)**;若未来仓库公开/暴露 → 立即轮换 token 并迁移至 settings.local.json。
- `lessons.md` 可能含路径等内部信息,仓库同样保持私有。

## 快速上手

1. 改配置:编辑仓库文件 → `cp` 到 `~/.claude`(hooks/skills 变更后需重开会话生效)
2. 新增 skill:`mkdir skills/<name>/SKILL.md` → 复制到运行位 → 测试
3. 新增 hook:同上,hooks 触发点见 Obsidian 侧三文档规范
4. 收尾纪律:CLAUDE.md/lessons.md/hooks/skills 有变更 → 会话结束前 commit+push
