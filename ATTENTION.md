# claude-config — ATTENTION(踩坑台账)

> 只增不删。状态三档:🔴 未修复 / 🟡 已修复未验证 / 🟢 已修复已验证。

### 🟢 符号链接部署模式已废弃 — setup.sh 已删除(2026-09-08 定稿)
- setup.sh 原以符号链接部署(仓库 → ~/.claude);2026-07 起运行位改直写,链接全断。
- 处理:用户确认废弃 → setup.sh 与 README_claudeconfig.md 已 git rm(随三文档定稿 commit);同步 = 仓库为准 + 复制。
- 验证:2026-09-08 检查 ~/.claude 全目录无指向 claude-config 的链接(除 lark-* 指向 feishu)。

### 🟢 仓库曾停滞 7 周失去定义 — 补推 81eee9b(2026-09-08)
- 场景:最后提交 2026-07-20;期间运行位直写演化(skills +27、CLAUDE.md/lessons/settings 全变)未回灌;仓库 = 旧快照,与运行位 md5 全异。
- 修复:回灌运行位直写内容(skills 27 实体/hooks 13/CLAUDE.md/lessons.md/settings.json/workflows 1)+ 清理陈旧定义(brain-* hooks 11、commands 5、PaperDigestWeekly workflow)。
- 规则:**变更必须走仓库 + 收尾即推**;发现运行位与仓库不一致 → 立即回灌,勿等积压。

### 🟢 settings.json 含 ANTHROPIC_AUTH_TOKEN — 已确认私有仓库可入库(2026-09-08 用户拍板)
- token 属机密;已随 81eee9b 进入仓库历史。
- 状态:**用户确认仓库为私有,可入库,不做迁移**;若未来公开/暴露 → 立即轮换 token 并迁 settings.local.json。
- 规则:仓库保密等级 = 私有;勿推送至公开远端。

### 🟢 brain-* 大脑系统 hooks 已废弃删除(2026-09-08)
- 仓库曾有 brain-anomaly/brain-stats 等 11 件,运行位 hooks 无对应 → 废弃;已随补推删除。勿重建。

### 🟢 commands/ 模块整体废弃(2026-09-08)
- 运行位无 commands 机制(目录空);仓库 5 旧件(secretary/brain-stats 系)已删。勿重建。

### 🟢 lark-* 28 skills = 上游链接,勿在本仓库复制/修改
- ~/.claude/skills/lark-* 是指向 AgentFiles/feishu/core/vendor/larksuite-cli/skills 的符号链接。
- 规则:更新走 feishu 上游;本仓库只登记依赖。直接复制实体入库会造成双份漂移。

### 🟡 ~/.claude 根残留历史备份(清理候选)
- lessons.md.bak-* ×4(7/10、7/27、8/16、8/25)、CLAUDE.md.bak、.mcp.json.bak、hooks/verify-reminder.py.bak——确认无恢复需求后删除。
- 状态:🟡 待清理(需用户确认)。

### 2026-09-08 — PersonalResearch_PaperDigestWeekly.js 已从仓库删除
- 运行位 ~/.claude/workflows 无此文件(仓库独有)→ 判定陈旧删除。⚠️ 该工作流名属 PaperDigest 侧(红线项目):若其主会话需要,应从 PaperDigest 项目侧恢复,勿在本仓库重建。

### 🟢 ChinapostAMC_StrategyOrder 双版本漂移 → 收敛为项目级(2026-09-08,commit 8a41fd6)
- 场景:同名 workflow 两份——全局 ~/.claude/workflows 旧版(8/3,538 行单流程)+ 中邮资管/.claude/workflows 项目级新版(9/2,739 行场景化 A/B/C 切段),md5 不同,加载易混淆。
- 处理:用户裁定**项目级为正版,全局版删除**(含仓库同步)。业务工作流按归属原则驻留业务工作区,全局不驻留。
- 规则:同名资产出现双处时先比版本;工作流归业务区;全局 workflows 保持空或仅通用流。
