# claude-config — HANDOFF(交接给下一个维护者)

> 读者:任何需要维护本仓库的 Agent/会话(无上下文)。按本节顺序即可恢复全部状态。

## 0. 一句话

全局 Claude 配置源仓库;`~/.claude` 运行位 = 部署副本;**仓库为准,变更走仓库,收尾即推**。

## 1. 快速状态

- git:`main` → `origin/main`(github.com:JoyingYourself/claude-config.git),最近提交 81eee9b(2026-09-08 补推)。
- 三文档:README(全量,含运行位实况)/本文件/ATTENTION(坑),2026-09-08 重建。
- 历史:2026-07-20 前为"符号链接部署"(setup.sh),后废弃改直写 → 停滞 7 周 → 补推;**setup.sh 已确认废弃删除(2026-09-08)**;同步 = 仓库为准 + 复制。

## 2. 模块维护位(改什么去哪里)

| 要改的东西 | 编辑位置 | 运行位生效位置 | 备注 |
|---|---|---|---|
| 全局会话指令 | `CLAUDE.md` | `~/.claude/CLAUDE.md` | 高频;收尾即推 |
| 教训库 | `lessons.md` | `~/.claude/lessons.md` | 高频;收尾即推 |
| 全局设置 | `settings.json` | `~/.claude/settings.json` | 含 token,见安全 |
| 本机私有设置 | 不入库 | `~/.claude/settings.local.json` | 每机独立 |
| hooks | `hooks/*.sh|*.py` | `~/.claude/hooks/` | 新增 hook 需在 settings.json hooks 段登记触发点 |
| 全局 skills | `skills/<name>/` | `~/.claude/skills/<name>/` | 新增/修改后重开会话加载 |
| lark-* 28 系 | **不在此仓库** | `~/.claude/skills/lark-*`(链接) | 上游 `AgentFiles/feishu/core/vendor/larksuite-cli/`;feishu 侧升级 |
| workflows | (全局无) | — | 业务工作流归业务工作区(如 ChinapostAMC → 中邮资管/.claude/workflows);全局不驻留业务流 |
| commands | (已废弃) | — | 历史件已删,勿重建 |

## 3. 变更流程(会话纪律)

1. 编辑仓库文件(不裸改运行位;若已裸改运行位 → 复制回仓库)
2. `cp` 或脚本同步到 `~/.claude` 对应位
3. commit(消息注明日期与变更面,如"hooks:新增 xxx 规则")
4. push(防积压;重开会话或新会话生效)
5. 收尾:检查 `git status` 干净再结束会话

## 4. 归属判定(新增配置先答)

问:这个配置/技能是**全局通用**还是**某工作区专用**?
- 全局 → 本仓库(skills/ 实体或 hooks)
- 工作区专用 → 该工作区自己的 `.claude/` 仓库(如 AccumulatingWisdom 的 vault/工作区体系,独立 git 独立推)
- 第三方 vendor 产物(lark 等)→ 留在上游,本仓库登记依赖,不复制实体

## 5. 安全红线

- settings.json 含 ANTHROPIC_AUTH_TOKEN → **已确认私有仓库可入库(0908 拍板)**;若仓库暴露风险 → 轮换并迁 settings.local.json
- 不把任何凭据/密钥写入 lessons.md/CLAUDE.md
- backups/ 为历史部署备份,清理前确认无恢复需求

## 6. 已知待办

- ~/.claude 下 lessons.md 历史 .bak ×4 清理(确认无恢复需求后)
- PersonalResearch_PaperDigestWeekly workflow 已删(运行位无)——若 PaperDigest 主会话需要,从其项目侧恢复,勿在本仓库重建
- (已完成)setup.sh 废弃删除 / token 入库确认(0908)
