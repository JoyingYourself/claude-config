# 量化研究教训库（压缩版）

> 完整原文备份：`lessons.md.bak-*`。本压缩版用于快速注入和关键词匹配。
> 写入规则、Rule Promotion 机制见 CLAUDE.md § 自进化记忆系统。

## KEYWORDS INDEX

| 关键词 | 匹配教训（domain/date） |
|--------|----------------------|
| MCP, timeout, 超时, server, 服务器 | MCP/2026-07-19a, MCP/2026-07-19b, MCP/2026-07-12, MCP/2026-07-20 |
| Moor, 重启, 自启, 服务器挂, disabled | MCP/2026-07-20 |
| 交付, 自检, 完成, done, 报告 | Delivery/2026-07-27, Delivery/2026-07-27b, Delivery/2026-07-22, Delivery/2026-07-20, Delivery/2026-07-24 |
| 图表, chart, 净值曲线, 渲染, 可视化, 长度 | Delivery/2026-07-27b |
| 架构, design, 设计, 重构, refactor | Arch/2026-07-24a, Arch/2026-07-10a, Arch/2026-07-10b, Arch/2026-07-22 |
| 数据, data, 验证, validate, innercode, 路径, dedup, 去重, concat, 批跑, batch | Data/2026-07-24a, Data/2026-07-24b, Data/2026-07-24c, Data/2026-07-10, Data/2026-07-13a, Data/2026-07-18, Data/2026-07-10, Data/2026-08-09, Data/2026-07-27 |
| 用户, user, 交互, 确认, 猜测, ask | UX/2026-07-19, UX/2026-07-13, UX/2026-07-21 |
| skill, 阶段, stage, gate, 跳过 | Delivery/2026-07-24 |
| 因子, factor, 回测, backtest, 测试, test | Arch/2026-07-11b, Data/2026-07-10, Arch/2026-07-10a, Factor/2026-08-16 |
| NaN, IC异常, winsorize, 缩尾, 零膨胀, 因子测试 | Factor/2026-08-16 |
| write, edit, 修改, 覆盖, overwrite, 文件, file | Data/2026-07-24a, Data/2026-07-24b, Arch/2026-07-24a |
| 指数, index, benchmark, 基准, duckdb | Data/2026-07-13a |
| 模板, template, variant | Data/2026-07-24c |
| 离线, 部署, wheel, 依赖闭包, offline_packages, 打包 | Delivery/2026-08-19 |
| 文档, 文档同步, README, 配置同步, 维护, 同步引用 | Delivery/2026-08-20 |
| cron, 定时, 删除 | UX/2026-07-19 |
| 重构, refactor, 删除, 引用, grep, ReferenceError, is not defined, head 截断 | Tech/2026-08-26 |
| obsidian, vault, 笔记 | Obsidian/2026-07-10a, Obsidian/2026-07-10b |
| 代理, proxy, 网络, Connection refused, getproxies, no_proxy, 数据源全挂 | Net/2026-08-20 |
| Electron, notion, 白屏, 转圈, 打不开, Cookies, token_v2, state.json, 重登 | Tech/2026-09-06 |

---

# MCP/Timeout

## [MCP] 2026-07-19a — MCP_TIMEOUT ≠ MCP_TOOL_TIMEOUT

trigger_patterns:
  tool_keywords: []
  file_patterns: []
  mcp_servers: ["data_Gil", "factor_Gil", "backtest_Gil", "report_Gil"]

> WHEN: MCP 工具调用超时
> RULE: 先 `echo $MCP_TOOL_TIMEOUT` 确认当前值；怀疑超时→第一步 curl 直连服务端验证，区分客户端 vs 服务端超时。三层配置（env + .mcp.json + Moor DB）需全部调到位且重启 Claude Code。
> TAGS: #MCP #超时 #调试

## [MCP] 2026-07-19b — compose_packages 超时 → 先查产物

trigger_patterns:
  tool_keywords: []
  file_patterns: []
  mcp_servers: ["data_Gil"]

> WHEN: 任何会产生文件产物的 MCP 调用超时
> RULE: 第一步 `ls -lt ~/.gil_datasets/`（或对应输出目录）检查最新文件时间戳。匹配调用时间 → 可能已成功，直接用。产物不存在 → 再考虑重试。禁止盲重试。
> TAGS: #MCP #超时 #调试

## [MCP] 2026-07-12 — MCP 超时三步排查

trigger_patterns:
  tool_keywords: []
  file_patterns: []
  mcp_servers: ["data_Gil", "factor_Gil", "backtest_Gil", "report_Gil"]

> WHEN: MCP 工具调用超时
> RULE: ① `ls -lt` 输出目录查产物（假报错）→ ② `ps aux | grep server` 查 CPU/进程（资源竞争）→ ③ 排除①②后才考虑简化参数。禁止跳过①②直接缩范围。
> TAGS: #MCP #超时 #诊断流程

## [MCP] 2026-07-20 — Moor 重启后 Server 不自动拉起（2026-08-16 更新：已根治）

trigger_patterns:
  tool_keywords: ["pkill", "Moor", "restart", "重启"]
  file_patterns: []
  mcp_servers: []

> WHEN: 需要重启 Moor 或其子 MCP Server；或 Moor 工具报 "Tool not found or disabled"
> RULE: 1) 子 Server 是 Moor 的 stdio 子进程，杀掉后 Moor 标记 status='error' 且不自动拉起——先用 sqlite 重置该行（status='stopped', error_message=NULL）再重启 Moor。2) 重启 Moor：`kill $(cat "~/Library/Application Support/com.snowautumn.moor/pid")` + `open -a Moor`（2026-08-16 两次实测，WAL/DB 无损）。3) 根治已落地：settings 表 `general.autoStartServersOnLaunch=true`（2026-08-16 设置），Moor 启动即拉起全部 auto_start=1 服务器，无需 GUI 操作。4) Moor 的 /api/servers REST 需内部认证、UI 为 WebView（AX 树不可达）→ 运维路径 = sqlite 写库 + 重启，勿尝试 UI 自动化。
> TAGS: #Moor #MCP #运维 #自启

---

# Data/Validation

## [Data] 2026-07-24a — 修改共享数据源前追溯所有下游消费者

trigger_patterns:
  tool_keywords: []
  file_patterns: ["*.csv", "*.json", "*.parquet", "*.duckdb", "*.png"]
  mcp_servers: []

> WHEN: 修改任何会落盘的数据源（CSV、PNG、模板）
> RULE: ① `grep -r <路径>` 所有引用 → ② 备份原文件或输出到临时目录 → ③ 改完立即跑端到端验证。不等到后续步骤才发现覆盖。
> TAGS: #数据源 #下游消费者 #覆盖风险

## [Data] 2026-07-24b — innercode/secucode 必须查源表验证

trigger_patterns:
  tool_keywords: ["innercode", "secucode", "指数代码", "LC_", "IndexCode"]
  file_patterns: []
  mcp_servers: []

> WHEN: 使用任何 innercode、secucode、指数代码
> RULE: 从 secumain/数据库查询确认，不凭记忆。配置文件中每个代码旁注释对应的 secucode 和中文名（自文档）。同一指数多处使用→确认查的是同一张源表。
> TAGS: #innercode #数据验证 #secumain

## [Data] 2026-07-24c — 多 variant 模板逐元素检查

trigger_patterns:
  tool_keywords: ["variant", "template", "模板"]
  file_patterns: ["*.html"]
  mcp_servers: []

> WHEN: 从 base 模板创建 variant
> RULE: 列出所有与 base 不同的元素（不只图和 AUTO 标记）→ 逐项修改 + 逐项验证 → 打开两个 variant 报告并排对比确认。不做"批量替换"。
> TAGS: #模板 #variant #逐项检查

## [Data] 2026-07-10 — 数据源路径写前核对真实产物

trigger_patterns:
  tool_keywords: ["find", "ls", "数据源"]
  file_patterns: ["*.json", "*.csv", "*.parquet"]
  mcp_servers: []

> WHEN: 在 skill/文档里写任何"数据源路径/文件名约定"
> RULE: 先 `find`/`ls` 核对真实文件，以实测产物为准。不同工具链的输出 schema 不能互相假设。写完用真实文件跑解析器验证。
> TAGS: #数据 #Skill #文档

## [Data] 2026-08-09 — pd.concat 后 dedup 必须验证 SELECT 包含排序列

trigger_patterns:
  tool_keywords: ["concat", "dedup", "drop_duplicates", "pd.concat"]
  file_patterns: ["*.py"]
  mcp_servers: []

> WHEN: 写 `pd.concat([df_main, df_stib]).sort_values('infopubldate').drop_duplicates(...)` 去重代码
> RULE: ① 验证 SQL SELECT 中包含了 sort/dedup 所需的列（EndDate, InfoPublDate）→ ② 禁止用 `if 'column' in df.columns` 做静默跳过守卫（列缺失应报错而非跳过 dedup）→ ③ 优先封装 `safe_concat_main_stib()` 到 shared utils，从源头消除遗漏。形式上写了 dedup ≠ 实际上执行了 dedup。触发了 README 2026-08-06 踩坑记录但未从根本上防范——缺少列导致整行被静默跳过。
> TAGS: #数据 #dedup #concat #静默跳过 #shared_utils

## [Data] 2026-08-09b — 一司一期多行: 业务粒度 partition + 时间列 DESC 去重

trigger_patterns:
  tool_keywords: ["partition", "PIT", "去重", "一司一期", "ProposalSN"]
  file_patterns: []
  mcp_servers: []

> WHEN: 处理聚源财务/行情表一司一期多行数据
> RULE: ① 按字典主键派生业务粒度 partition (财务 CompanyCode,EndDate; 行情 InnerCode,TradingDay) → ② 按业务时间列 DESC (InfoPublDate/TradingDay) → ③ ①②仍区分不了 → 维护时间 DESC。特例：分红同键多 ProposalSN → SUM；无唯一索引表照①②③。维护时间只能进③级。
> TAGS: #数据 #PIT #去重

## [Data] 2026-07-13a — 本地 DuckDB 指数库优先

trigger_patterns:
  tool_keywords: ["DuckDB", "IndexMarket", "LC_INDEXBASICINFO"]
  file_patterns: ["*.duckdb"]
  mcp_servers: []

> WHEN: 需要获取指数行情数据
> RULE: 优先查本地 DuckDB `~/Scholarship is a new sexy/指数数据/IndexMarket.duckdb`。找不到再走外部 API。匹配：中文名→`LC_INDEXBASICINFO.INDEXABSTRACT` 模糊搜索→筛选 PTYPE=2 AND DESIGNDTYPE=2（真全收益）→ 排除港股版。交叉验证：全收益累计 > 价格累计。
> TAGS: #指数数据 #DuckDB #本地数据库

## [Data] 2026-07-18 — chinapostamc 两套 MCP 系统数据范围不同

trigger_patterns:
  tool_keywords: []
  file_patterns: []
  mcp_servers: ["chinapostamc_strategy_actual", "chinapostamc_strategy_callback"]

> WHEN: 使用 chinapostamc 的 actual 或 callback MCP 系统
> RULE: actual 系统 → 先 `list_available_dates` 确认策略有估值表。callback 系统 → 先 `list_strategies` 确认策略在回测数据库中。不要假设"路演讲的是 X 策略，系统里就有 X 策略的数据"。
> TAGS: #MCP #数据源 #chinapostamc

---

## [Data] 2026-07-27 — 批跑脚本不擅自修改，遇问题先汇报

trigger_patterns:
  tool_keywords: ["python", "batch", "run", "批跑"]
  file_patterns: ["*.py"]
  mcp_servers: []

> WHEN: 执行批跑任务时脚本报错
> RULE: ① 遇 rc≠0 → 收集错误信息 → 汇报用户 → 等待指示 ② 不改用户的工作区脚本逻辑（数据加载/策略参数/输出路径），仅允许改日期和通用路径 ③ 在用户明确授权前，不修改任何【定稿】或 TEMPLATE 脚本
> TAGS: #批跑 #脚本修改 #用户确认

---

# Delivery/SelfCheck

## [Delivery] 2026-07-27 — 交付 = 原始需求逐条核对，不是"没报错"

trigger_patterns:
  tool_keywords: []
  file_patterns: []
  mcp_servers: []

> WHEN: 任何任务交付给用户前
> RULE: ① 接收多步骤需求 → 先用自己的话复述每个步骤产出，确认理解一致再执行 ② 遇到阻塞 → 换方案或向用户说明，不允许标记"待补"跳过 ③ 交付前自检清单 = 原始需求逐条对照（不是只看断链/数字/文件存在）。违反次数已达多次，这是最核心的行为规则。
> TAGS: #交付规范 #自检 #需求理解
> ⚠️ trigger_patterns 待补(全空, Hook 无法触发)

## [Delivery] 2026-07-27b — 图表/可视化 bug 修复后必须提取渲染数据逐点验证

trigger_patterns:
  tool_keywords: []
  file_patterns: ["*.html", "*.png"]
  mcp_servers: []

> WHEN: 用户反馈图表/曲线/可视化有视觉问题（长度不对、缺线、错位等）
> RULE: 修复后不要只跑脚本看有无报错就汇报完成。必须从生成的 HTML/CSV 中提取实际渲染数据（ECharts navData/bmNavData 等），逐点对比产品线和基准线的日期/数值/点数，确认完全一致后再交付。修表面症状不验证渲染产物 → 漏掉深层不一致。
> TAGS: #图表 #净值曲线 #端到端验证 #逐点对比

## [Delivery] 2026-07-22 — 分级 DONE 框架

trigger_patterns:
  tool_keywords: []
  file_patterns: []
  mcp_servers: []

> WHEN: 任何任务启动时
> RULE: 锁定目标级别 — L1 语法级（可运行）→ L2 测试级（+测试通过）→ L3 行为级（+端到端真实验证）→ L4 交付级（+自检清单 PASS）→ L5 分析级（+量化推导支撑）。不可越级宣布完成，不可降级交差。
> TAGS: #工程规范 #完成标准 #DONE
> ⚠️ trigger_patterns 待补(全空, Hook 无法触发)

## [Delivery] 2026-07-20 — 报告类交付物交付前必须自检

trigger_patterns:
  tool_keywords: []
  file_patterns: ["*report*.html", "*报告*.html"]
  mcp_servers: []

> WHEN: 生成报告类交付物（HTML/PDF/图表）后
> RULE: 数据层自检（正则解析 HTML — 行数/日期/一致性）每次必做。视觉层（Chrome 截图 + vision bridge — 排版/重叠/可读性）涉及图表修改或首次生成时必做。未全部 PASS → 修复后重新生成，不得跳过直接交付。
> TAGS: #交付 #自检 #报告

## [Delivery] 2026-07-24 — Skill 阶段不可跳过

trigger_patterns:
  tool_keywords: ["Skill", "SKILL.md"]
  file_patterns: []
  mcp_servers: []

> WHEN: 执行 Skill（/ 命令），尤其是看到任务规模大时
> RULE: 按阶段顺序执行，每阶段完成后对照 Gate checklist 自查。不能被规模吓到走捷径。时间/Token 不够 → 告知用户当前进度，请求决策（继续/缩减范围/分批），而非静默降级质量。
> TAGS: #Skill执行 #阶段门禁 #流程遵守

## [Delivery] 2026-08-20 — 改共享配置必须同步文档引用：README 是下游消费者

trigger_patterns:
  tool_keywords: ["同步文档", "更新配置", "文档同步", "README", "维护说明"]
  file_patterns: ["common.py", "README.md", "*配置*.py", "*维护说明*", "*.md"]
  mcp_servers: []

> WHEN: 修改 common.py 中的共享配置（EXTRAPOLATE_SOURCES / PRODUCT_CONFIGS / BENCHMARK_CONFIGS 等）后 / 交付"文档已维护/README 维护好了"类声明前
> RULE: 修改共享配置后，必须 grep README 及所有 .md 文档中引用该配置的代码块/表格并逐项核对一致；交付文档维护声明前，逐条核对文档代码块与实际实现（禁止凭印象声明"已维护"）。本次教训：外推配置 2→6 指数时 README 代码块未同步，若用户未追问将长期残留。区别于 [[Data/2026-07-24a]]（数据源下游消费者）——本教训是文档-实现一致性。
> TAGS: #交付 #文档同步 #配置同步 #审计盲区

---

# Architecture/Design

## [Arch] 2026-07-24a — 改架构前先理解为什么是现在这样

trigger_patterns:
  tool_keywords: []
  file_patterns: ["*.py", "*.sh", "*.json"]
  mcp_servers: []

> WHEN: 看到 Bug 或"不够好"的设计，想动手改
> RULE: 先问：这个模块为什么设计成现在这样？谁做的、什么时候、什么原因。答案不清楚 → 先问用户，不猜。改动范围 = 问题的影响范围，不扩展到"顺带优化"。
> TAGS: #架构理解 #改动范围 #先问为什么

## [Arch] 2026-07-24b — 一改一验，不攒到最后

trigger_patterns:
  tool_keywords: []
  file_patterns: ["*.py", "*.sh", "*.json", "*.md"]
  mcp_servers: []

> WHEN: 连续做多个代码改动
> RULE: 一个逻辑改动 = 一次 run + 一次验证（至少看关键指标变化）。不通过 → 修好再改下一个。不要因为"跑一次要 2 分钟"就跳过（2 分钟 < 2 小时排查）。改完一个模块先 commit 作为回退点。
> TAGS: #一改一验 #独立验证 #bug遮蔽

## [Arch] 2026-07-22 — 实施前 6 轴扫描

trigger_patterns:
  tool_keywords: []
  file_patterns: []
  mcp_servers: []

> WHEN: 非平凡实现任务（预计 >3 文件或 >1 小时），写代码前
> RULE: 内部分析 6 轴：① 假设审计（依赖了哪些未验证假设？）② 范围边界（用户真正要求了什么？）③ 已有方案（能不能复用？）④ 极简路径（删掉一步还能完成吗？）⑤ 不确定性（哪步不可预测？预案？）⑥ 连锁影响（改完 hook/cron/MCP Server 还正常吗？）。≥2 轴有问题 → 先和用户对齐。
> TAGS: #工程规范 #计划 #审查 #防盲区
> ⚠️ trigger_patterns 待补(全空, Hook 无法触发)

## [Arch] 2026-07-10a — 穿行测试不能用现成正确产物当输入

trigger_patterns:
  tool_keywords: ["test", "测试", "穿行"]
  file_patterns: ["*.py"]
  mcp_servers: []

> WHEN: 做端到端测试验证
> RULE: 判据 = 被测系统自产的终值 == 黄金基线（不是"下游能读入中间产物"）。穿行测试的中途输入禁止用外部已知正确产物喂入。有平行忠实副本时更要警惕——副本能跑会制造"已复现"假象并供养伪验证。
> TAGS: #测试 #穿行测试 #验证

## [Arch] 2026-07-10b — 别让审计报告的叙事框架框定任务目标

trigger_patterns:
  tool_keywords: ["audit", "审计"]
  file_patterns: []
  mcp_servers: []

> WHEN: 接手一个任务，手里有一份审计/缺陷报告
> RULE: 先分清"任务目标"与"手头文档的叙事框架"——用一句话向用户确认"我们要的是 X 通用能力，还是复刻 Y 具体成品"。通用框架的验收判据 = 自产合理（数据全 loaded、因子非空、筛选真生效），绝不锚定某具体策略的精确数字。
> TAGS: #架构 #方向 #通用框架

## [Arch] 2026-07-11a — 新建 Skill/MCP 必须先调工程类 Skill

trigger_patterns:
  tool_keywords: ["skill", "mcp", "SKILL.md", "moor.db"]
  file_patterns: ["SKILL.md"]
  mcp_servers: []

> WHEN: 新建或修改 Skill/MCP 文件
> RULE: MCP → 先 `EngineeringMCP_Scaffold`（读规范→关 Moor→写 moor.db+Profile→重启验证）。Skill → 先 `EngineeringSkill_Scaffold`（命名公式+查重→6 步含穿行测试）。禁止 `claude mcp add` 和手写 SKILL.md。识别信号：涉及 `~/.claude/skills/`、`moor.db`、SKILL.md → 先想"有没有对应 scaffold skill"。
> TAGS: #Skill #MCP #Moor #scaffold

## [Arch] 2026-07-11b — 组合因子缺口修共享派生层一次

trigger_patterns:
  tool_keywords: ["factor", "因子", "enrich"]
  file_patterns: ["*.py"]
  mcp_servers: ["factor_Gil", "backtest_Gil"]

> WHEN: 发现多个平行引擎（test_factor、run_pipeline）各有同样缺口
> RULE: 修共享派生层一次（enrich），在每个引擎"取数后、求值前"接钩子。两个数据源列名可能不同 → 富集层做角色→前缀解析，不硬编码前缀。组合因子、TTM、单季派生都走 enrichment layer，不逐引擎打补丁。
> TAGS: #架构 #因子 #单一事实源

---

# Factor/因子测试

## [Factor] 2026-08-16 — NaN IC 是 bug 信号：下钻中间量，禁止聚合掩盖

trigger_patterns:
  tool_keywords: ["compare_factors", "test_factor", "ic_mean", "winsorize", "缩尾", "nan", "因子异常", "股息率"]
  file_patterns: ["factor_Gil/server.py", "factor_monitor.py"]
  mcp_servers: ["factor_Gil"]

> WHEN: 因子 IC 测试/监控出现 NaN、全零截面或"数据异常"
> RULE: 1) NaN 是 bug 信号不是数据噪声——禁止用 nanmean/跳过聚合掩盖，必须定位到退化期。2) 排查顺序：逐期 IC 序列（找 NaN 期）→ 该期截面分布（零值占比/唯一值/std）→ winsorize/中性化中间量（med/mad/clip 区间）。3) 零膨胀因子（股息率类，零值占比>50%）MAD 缩尾退化：med=0→mad=0→clip(0,0) 压成常数→spearman=NaN；修复=缩尾加 mad>0 守卫，不改聚合。4) 定位方法：用原始数据一比一复刻服务端管线（SQL→dropna→winsorize→merge→corr）逐步比对中间量。
> TAGS: #因子 #IC #NaN #winsorize #零膨胀 #factor_Gil

---

# Obsidian/Vault

## [Obsidian] 2026-07-10a — 所有回测结果必须记录到 Obsidian Vault

trigger_patterns:
  tool_keywords: ["backtest", "回测", "output"]
  file_patterns: []
  mcp_servers: ["backtest_Gil"]

> WHEN: 回测完成（任何策略/因子）
> RULE: 立即将结果写入对应策略笔记的"回测结果"表格。所有结果都记录（包括表现差的，标注原因避免重蹈覆辙）。总览文件维护"回测结果汇总"表。废弃分支不删除，标记 🟡/🔴 并说明原因。
> TAGS: #回测 #Obsidian #Vault

## [Obsidian] 2026-07-10b — Obsidian vault 必须含 .obsidian 配置

trigger_patterns:
  tool_keywords: ["vault", "obsidian", ".obsidian"]
  file_patterns: []
  mcp_servers: []

> WHEN: 创建新的 Obsidian vault
> RULE: 每个 `vault/` 建 `.obsidian/`（core-plugins 至少含 canvas/graph/file-explorer）使其可独立打开。`.obsidian/` 和 `.canvas` 绝不 chmod 444（Obsidian 运行时需写入）。只锁 `.md`。注册用 UI「Open folder as vault」，不脚本改 obsidian.json。
> TAGS: #Obsidian #Vault #Canvas

---

# UserInteraction

## [UX] 2026-07-19 — 用户未明确授权不得删除/修改 cron

trigger_patterns:
  tool_keywords: ["cron", "CronCreate", "CronDelete"]
  file_patterns: []
  mcp_servers: []

> WHEN: 考虑删除或修改 cron 任务时
> RULE: 必须等用户明确说"删"/"删掉"/"取消"/"停掉"。用户表达疑惑 ≠ 授权删除。先告知用户并明确询问"要删吗？"，等肯定回复后再动手。
> TAGS: #cron #用户交互 #权限

## [UX] 2026-07-13 — 用户没给的信息直接问，禁止猜测

trigger_patterns:
  tool_keywords: []
  file_patterns: []
  mcp_servers: []

> WHEN: 数据找不到或输入信息不完整
> RULE: 精确匹配失败 → 诚实告知，列出搜到的相近项（名称、代码、起止日期），让用户选择。禁止自行选替代。所需输入不完整 → 停止，逐项提问。禁止猜测路径、假设指数列表、用"默认"时间区间。
> TAGS: #用户交互 #数据准确性
> ⚠️ trigger_patterns 待补(全空, Hook 无法触发)

## [UX] 2026-07-21 — 不要先贴标签再找理由（盲目标⭐）

trigger_patterns:
  tool_keywords: []
  file_patterns: []
  mcp_servers: []

> WHEN: 需要做判断/推荐/标注时
> RULE: 用户没要求的结论不要加。有量化依据 → 先展示推导再标注，标注附带推导链接。绝不允许"先标⭐，被问到了再找理由"。"五个取中间"不是分析——选最优需要定义目标函数，没定义就不要选。
> TAGS: #分析边界 #过度输出
> ⚠️ trigger_patterns 待补(全空, Hook 无法触发)

---

# macOS/通知（技术备忘）

## [Tech] 2026-07-21 — macOS 脚本通知方案

trigger_patterns:
  tool_keywords: ["notification", "notify", "通知"]
  file_patterns: ["*.sh", "*.swift"]
  mcp_servers: []

> WHEN: 需要从脚本发 macOS 通知
> RULE: 使用 Swift 原生 app + UNUserNotificationCenter（`swiftc` 编译 ARM64 `.app` bundle，Info.plist 配置 CFBundleIdentifier + LSUIElement）。点击回调 = UNUserNotificationCenterDelegate。消息持久化 = 先写 `.last_notification.txt`。launchd 调 Binary 比 `open -a` 更可靠。
> TAGS: #macOS #通知 #Swift

---

# Delivery/部署交付

## [Delivery] 2026-08-19 — 能跑的代码 ≠ 能部署的包: 验证必须走目标环境依赖闭包

trigger_patterns:
  tool_keywords: ["离线", "offline_packages", "wheel", "依赖闭包", "dry-run", "部署", "打包"]
  file_patterns: ["offline_packages/*", "requirements.txt", "*部署*.md", "*安装*.md"]
  mcp_servers: []

> WHEN: 离线交付打包前 / offline_packages 或 requirements 变更后 / 部署前验证
> RULE: 任何离线交付必须做交叉平台依赖闭包验证: `pip install --dry-run --ignore-installed --platform win_amd64 --python-version 3.13 --only-binary=:all: --no-index --find-links=offline_packages <依赖>` 确认 Would install 完整列表无缺失。开发机预装包(Anaconda)会掩盖离线包缺失——能跑不等于能装。审计/验证必须包含交付维度(目标环境可安装性), 不能只验证开发环境运行行为。
> TAGS: #交付 #离线部署 #依赖闭包 #审计盲区

---

# Net/网络

## [Net] 2026-08-20 — 数据源全挂:先 curl 直测区分"源挂 vs 代理/网络层"

trigger_patterns:
  tool_keywords: ["getproxies", "no_proxy", "7890"]
  file_patterns: ["*benchmark.py", "*ticker_daemon.py", "*nav_estimator.py", "*providers.py", "*deepseek_client.py", "*github_weekly.py", "*gov_weekly.py", "*discover.py"]
  mcp_servers: []

> WHEN: Python 脚本/报告全部外部数据源(指数/行情/API)拉取失败,且浏览器/curl 正常
> RULE: ① 先 curl 直测同一 URL——通 = 问题在 Python 网络层(优先查 macOS 系统代理残留),不通 = 数据源真挂。② 定位: `python3 -c "import urllib.request; print(urllib.request.getproxies())"` + `nc -z 127.0.0.1 7890` 探测残留代理端口。③ 修复: 代理健康自适应(socket 探测端口,死→ os.environ['no_proxy']='*',活→不动);探测端口已支持 `PROXY_PORT` 环境变量覆盖(默认 7890,2026-08-20 起 8 处补丁均为此版本,端口变更无需改代码)。urllib/requests/httpx 三库均读系统代理,no_proxy='*' 对三者生效(实测)。④ 常驻进程(daemon/server)启动时固化代理,补丁后必须重启;localhost 请求不受代理影响。⑤ 已带自适应补丁的文件: 定稿报告 common.py、看板 benchmark.py、market-data 双 daemon、vision-bridge providers.py、新闻周报 5 脚本 — 修改这些文件时勿破坏双态逻辑。
> TAGS: #网络 #代理 #macOS #排查流程



## [Data] 2026-08-20b — 归档多个同名文件前必须检查目标冲突:mv 同名覆盖不可逆

trigger_patterns:
  tool_keywords: ["mv ", "归档"]
  file_patterns: ["*_archive*", "*归档*", "*.bak*"]
  mcp_servers: []

> WHEN: 移动/归档多个文件到同一目录(批量 mv/cp)
> RULE: ① 执行前先 `ls` 目标目录 + `ls` 全部源文件,检查同名冲突;多个同名源文件 → 分目录放或加来源后缀(如 `update_factsheet_DividendQuality.py`)。② 批量移动前先 `cp` 备份到临时目录,再 mv。③ mv 同名覆盖静默发生、不可逆(无 Time Machine 用户快照时无法恢复,实测 2026-08-20:3 个同名 update_factsheet.py 归档 → 2 个被覆盖永久丢失);一次 ls 的成本 << 不可逆丢失的代价。
> TAGS: #文件操作 #归档 #mv覆盖 #备份

---

## [Data] 2026-08-25 — 树形科目求和必须只累加末级:startswith 前缀累加会重复计数 5 倍

trigger_patterns:
  tool_keywords: ["get_cash_position", "get_summary", "闲置资金", "total_cash", "货币资金", "估值表", "科目", "重复计数", "现金"]
  file_patterns: ["*Strategy_Actual*", "*估值表*", "*valuation*", "*parser*.py"]
  mcp_servers: ["chinapostamc_strategy_actual"]

> WHEN: 解析估值表(或任何树形科目编码)计算现金/资产金额 / 新增估值表字段或工具
> RULE: ① 科目为多级树(1002→1002.01→…→1002.01.01.01.086.ZGYZCXYH),父级金额=子级汇总,
    用 startswith 前缀匹配后逐层累加必重复计数(实测 2026-08-25:红利质量现金 153,787.52
    被算成 771,869.69,误差 5 倍)——必须只累加末级科目(不存在 `code + "."` 前缀子科目的行)。
    ② 金额结果必须交叉验证:估值表恒等式 资产合计 − 股票市值 = 现金
    (105,276,884.52 − 105,123,097.00 = 153,787.52 精确吻合)。
    ③ 股票持仓解析需同样注意叶子过滤(层级深度 count(".") 约束),父级行如
    1101.01.01.01.001 上交所 不可计入。
> TAGS: #MCP #估值表 #树形科目 #重复计数 #交叉验证

---

## [Tech] 2026-08-26 — 删除定义前 grep 引用禁止截断:head 漏尾部引用致运行时 ReferenceError

trigger_patterns:
  tool_keywords: ["grep", "删除", "重构", "ReferenceError", "is not defined", "引用", "head", "截断"]
  file_patterns: ["*.js", "reproduce-batch.js", "*.py"]
  mcp_servers: []

> WHEN: 删除/重命名函数/变量/常量定义或整段代码 / 重构后运行报 ReferenceError: xxx is not defined
> RULE: ① 删除任何定义前, grep 全部引用——禁止带 head/tail 截断(截断即漏检:
    2026-08-26 R38 删除 Phase 1 组级代码连带删 gDefs, 删除前 grep -n "gDefs" | head -10
    只显示 Phase 1 段引用, 漏了 Phase 4 发布段 L618/L620 → Workflow 跑 59 agents/3.3M token
    后在 Publish 段崩溃 ReferenceError: gDefs is not defined)。
    ② 删除后立即 grep -c <符号名> 确认代码引用归零(注释残留可接受, 须区分)。
    ③ 删除/重命名符号后, 除 node --check/包裹法外, 加"符号存在性"检查:
    grep -n <符号名> 输出定义处 1 次 + 引用处逐一核对——语法检查查不出运行时符号缺失。
    ④ 查引用用 grep -c 看总数 + grep -n 全量核对, 不要用 head 先看几条就动手。
> TAGS: #重构 #grep检查 #引用漏检 #ReferenceError #R40 #删除代码

---

## [Tech] 2026-09-06 — Electron桌面App(Notion)白屏/转圈:先验登录会话,再查缓存网络

trigger_patterns:
  tool_keywords: ["notion", "Cookies", "token_v2", "state.json", "--enable-logging", "Partitions/", "Logs/Notion"]
  file_patterns: ["*Notion/state.json", "*Notion/Partitions/*", "*Notion/notion.db*", "*Logs/Notion*"]
  mcp_servers: ["notion"]

> WHEN: Electron 桌面 App(Notion 等)白屏/错误页/无限转圈, 网页版正常
> RULE: 排查顺序固定: ① 登录会话 — 升级后旧会话失效是高频主因, 删
>      ~/Library/Application Support/<App>/Partitions/<app>/Cookies 强制重登(最快见效)
>      → ② 网络/代理分流(系统代理把 App 流量送慢节点) → ③ 缓存/Service Worker。
>      旁证: 网页未登录访问私人页返回 400 restricted 是正常现象, ≠ 页面损坏;
>      MCP/API 能读 ≠ 用户会话能读。抓 renderer 真相用 --enable-logging=stderr
>      启动读 console (BootDataError / missingSpacePointer = 会话问题)。
> TAGS: #Tech #Electron #Notion #白屏 #登录会话 #重登

---
## 写入规则

### 何时写入
- 用户指出错误或纠正方向
- 同一个操作连续失败 2 次以上
- 用户说"记住这个"、"下次别这样"
- 回测/因子测试结果与预期严重不符，且找到了根因

### 写入格式（压缩版）
```markdown
## [DOMAIN] YYYY-MM-DD — 标题
> WHEN: 触发场景
> RULE: 一条可执行规则
> TAGS: #tag1 #tag2
```

### 存储决策
所有教训统一存储在 `~/.claude/lessons.md`（全局唯一池），通过 trigger_patterns 自动筛选适用范围。

### Rule Promotion
某条教训被触发 ≥3 次后 → 提示用户是否提升到 CLAUDE.md 作为永久指令。CLAUDE.md 只有用户明确同意才能修改。
