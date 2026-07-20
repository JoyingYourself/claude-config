---
name: EngineeringCoding_Audit
description: 对抗式多代理代码审查 — 自动识别回测/通用代码，匹配专属维度，通过 Loop 发现 + 对抗验证 + 法官裁决消除自审盲区
---

# /EngineeringCoding_Audit — 对抗式多代理代码审查

## 概述

对**用户指定的单个代码文件**进行**对抗式多代理审查**。

**一次只审查一个文件。** 不扩展范围、不追溯依赖、不遍历目录。

通过 Workflow 工具调度多个 sub-agent，从不同维度并行审查。**核心理念：同一 agent 无法可靠审查自己的代码。** 通过独立审查 agent + 对抗立场 + 交叉验证，消除单 agent 自审盲区。

**自动识别领域**：检测到回测代码库特征（路径含 `MCP_moor`、引用 DuckDB/PIT 模式）时，在通用 6 维度的基础上叠加 4 个回测专属维度。

### 审查模式

| 模式 | 命令 | 内容 | 预估耗时 |
|------|------|------|:--------:|
| **quick** | `/EngineeringCoding_Audit --mode=quick <path>` | Adversarial Verify（4 维度证伪） | ~5 min |
| **full** (默认) | `/EngineeringCoding_Audit <path>` | 并行发现 + Adversarial Verify | ~10 min |
| **deep** | `/EngineeringCoding_Audit --mode=deep <path>` | full + Judge Panel 修复方案竞赛 | ~20 min |

### 适用场景

- 写完代码后用独立 agent 验证遗漏问题（消除自审盲区）
- 修改核心模块后审查逻辑漏洞或边界塌陷
- 重构前全面审计风险点
- CR 前预审查，减少人工 review 负担
- 回测代码的 PIT 时序/财务公式/多板处理专项审查

---

## 核心原则：只读审查，不修改代码

**绝不修改被审查的脚本。** 唯一产出是审查报告。

- ✅ 读取文件 → 调度 Agent 分析 → 生成报告（终端 + 文件）
- ❌ 不 Edit/Write 源代码 · 不自动修复 · Judge Panel 只建议不执行

## 与传统审查的关键区别

| 维度 | 传统 code-review | 本 skill |
|------|:---:|:---:|
| 审查者 | 同一个 agent | 多个独立 agent |
| 立场 | 确认正确 | 试图证伪（默认：这不是 bug） |
| 发现方式 | 一次性扫描 | 多维度并行 + 去重 |
| 验证 | 无 | 4 agent 对抗投票（≥3/4 才保留） |
| 领域感知 | 无 | 自动识别回测代码 → 叠加专属维度 |

---

## 路由

- `Read` — 读取目标代码文件
- `Workflow` — 调度多 Agent 并行审查（核心工具）
- `Write` — 保存审查报告（仅报告文件）

---

## 文件路径约定

输出：`<脚本同目录>/.audit_reports/{filename}_{YYYY-MM-DD}.md` + `.html`

---

# Part A: 通用审查维度（始终启用）

## A1. 逻辑正确性 (Logic)

代码在所有分支下是否产生正确结果？

- [ ] 算法逻辑覆盖所有分支？循环边界（off-by-one、空集合）？
- [ ] 条件判断遗漏 else/fallback？短路求值优先级？
- [ ] 类型转换安全性？比较器传递性？
- [ ] 异步逻辑：Promise/async 错误捕获？竞态条件？

## A2. 边界与容错 (Boundary)

极端/异常输入下是优雅降级还是崩溃？

- [ ] null/undefined/空集合检查？除零保护？索引越界？
- [ ] 数值溢出？递归终止条件？ReDoS？
- [ ] 外部输入格式不符时行为？try-catch 是否吞关键错误？

## A3. 性能与资源 (Performance)

正常和峰值负载下资源消耗是否可控？

- [ ] 时间复杂度？循环内查询（N+1）？内存泄漏（闭包/大对象）？
- [ ] 连接管理：DB/文件/网络 socket 是否有关闭机制？
- [ ] 缓存：过期策略？穿透/击穿/雪崩？不必要的深拷贝？

## A4. 安全性 (Security)

恶意输入能否导致数据泄漏或系统破坏？

- [ ] 注入风险（SQL 拼接、命令注入、eval）？路径遍历？
- [ ] 密钥/Token 硬编码？不安全反序列化（pickle）？
- [ ] 权限检查完备？日志泄漏敏感信息？已知漏洞依赖？

## A5. 可维护性 (Maintainability)

6 个月后另一个开发者能否快速理解并安全修改？

- [ ] 命名准确？函数 >50 行？魔法数字？耦合度？
- [ ] 错误信息包含上下文？注释解释"为什么"？测试覆盖？
- [ ] 硬编码配置值提取？

## A6. 并发与状态 (Concurrency)

多线程/并发访问时状态是否一致？（不涉及则跳过）

- [ ] 共享状态读写竞争？幂等性？事务一致性？
- [ ] 事件监听器移除？定时器清理？

---

# Part B: 回测领域叠加（自动识别触发）

## B0. 触发条件

**以下任一条件满足时**，在通用 6 维度的基础上叠加回测专属维度：

1. 文件路径包含 `MCP_moor`、`backtest_Gil`、`data_Gil`、`factor_Gil`、`report_Gil`
2. 代码内容包含 DuckDB / PIT 模式（`fin_date`/`mkt_date`、`infopubldate`/`tradingday`、STIB 配对）
3. 代码引用 Gildata 聚源数据库表名（`secumain`、`lc_mainindexnew`、`qt_dailyquote` 等）

**叠加逻辑**：通用 6 维度 + 回测 4 维度 = 10 维度并行审查。回测专用的数值稳定性检查合并到"边界与容错"维度中。

## B1. 时序正确性 (Temporal)

**核心问题：未来信息是否泄漏到历史决策？**

- [ ] `fin_date`（财务 PIT 截止日）与 `mkt_date`（行情日）正确分离？
- [ ] 财务表用 `<= fin_date` 过滤（非 `=`），行情表用 `= mkt_date`？
- [ ] 调仓日生成的持仓是否在调仓日之后才使用价格计算收益？
- [ ] 交易日校验：非交易日顺延？停牌股票被错误赋收益？
- [ ] 行业分类 `standard` 字段与日期匹配（≤2013=9, 2014-2020=24, 2021+=38）？
- [ ] `prev_trading_day` 回退不跨越财报发布日期？

## B2. 财务计算正确性 (Financial)

**核心问题：财务公式在所有边界条件下是否成立？**

- [ ] TTM 公式：`current_cumulative + prior_annual - same_period_prior_year`？
  - Q1 时 `current_cumulative = Q1累计`，公式仍成立？
  - Q4 时 `current_cumulative = prior_annual`，TTM 应等于 `current_cumulative`
- [ ] 单季度拆解：Q1=累计，Q2/Q3/Q4=当期累计-上期累计
- [ ] ROE = 净利润/平均净资产，平均 = (期初+期末)/2
- [ ] FCFY = (经营现金流-资本开支)/EV，EV=0 处理？
- [ ] 金融行业 FCFY 豁免？股息率主板/科创板归一化？
- [ ] 跨年边界日期匹配是否严格？

## B3. 多板处理正确性 (Multi-Board)

**核心问题：主板+科创板 UNION ALL 是否正确？**

- [ ] SELECT 列数量/顺序/类型一致？STIB 缺失字段 `NULL AS fieldname`？
- [ ] 单位转换（万元→元 ×10000）？同义异名字段映射？
- [ ] 行业/行情数据同时查询主板+科创板？
- [ ] STIB 去重用 STIB 自己的主键？

## B4. 交易逻辑真实性 (Market Realism)

**核心问题：模拟交易是否反映真实市场约束？**

- [ ] 换手摩擦：`cost_bps` 仅换仓时扣除（首次建仓不扣）？
- [ ] 停牌处理：被跳过？备选有效？退市后价值归零？
- [ ] 换手率限制首次豁免？行业上限迭代收敛？权重漂移归一化？
- [ ] 涨跌停/最小交易单位（100股）处理？

## B5. 回测领域知识（审查 Agent 必须了解）

以下知识在回测模式下注入审查 Agent 的 prompt，确保 SQL/数据引用判断准确。

### 数据环境

- 数据库：Gildata 聚源 DuckDB（~43 表，11 个 .duckdb 文件），路径 `/Users/junye_shi/Scholarship is a new sexy/Gildata_SecuCategory1&41_DuckDB/`
- 证券主表 `secumain`：`innercode, companycode, secucode, listeddate, listedsector, secucategory`（SecuCategory 1=主板 41=科创板；ListedSector 1=主板 6=创业板 7=科创板 8=北交所）
- PIT 列约定：`infopubldate <= fin_date`（财务），`enddate <= fin_date`（报告期），`tradingday = mkt_date`（行情）
- 关键字段：`netprofit, netoperatecashflow, capex, totalshareholderequity, totalmv, closeprice/ClosePrice, pe/pb, dividendratio, firstindustrycode`

### STIB 科创板配对（16 对）

| 主板表 | 科创板表 | 要点 |
|--------|----------|------|
| `lc_mainindexnew` | `lc_stibmaindata` | 核心财务（手动补充） |
| `lc_dindicesforvaluation` | `lc_stibdindiforvalue` | 估值指标 |
| `lc_balancesheetall` | `lc_stibbalancesheet` | 资产负债表 |
| `lc_incomestatementall` | `lc_stibincomestate` | 利润表 |
| `lc_cashflowstatementall` | `lc_stibcashflowstate` | 现金流量表 |
| `qt_dailyquote` | `lc_stibdailyquote` | 日线行情 |
| `qt_performance` | `lc_stibperformance` | 绩效（含单位转换） |
| `lc_exgindustry` | `lc_stibexgindustry` | 行业分类 |
| `lc_sharestru` | `lc_stibsharestru` | 股本结构 |
| Others | `lc_dividend`/`lc_ashareipo`/`lc_suspendresumption`/`lc_mainshlistnew` 等 | — |

### 回测高频 bug 清单（审查时重点对照）

1. `except Exception: pass` 静默吞错
2. `df.iterrows()` 逐行性能陷阱
3. `df.eval()` 列名特殊字符风险
4. 占位符替换后未检查残留（`{fin_date}`/`{mkt_date}`）
5. MAD=0 退化（所有值相同时）
6. 跨时期行业代码不一致（金融 44→48）
7. STIB NULL 填充未在下游检查
8. DuckDB 连接无 close 机制
9. 首期建仓摩擦豁免逻辑脆弱
10. 去重逻辑假设数据按日期有序

---

# Part C: 交互协议

## Step 1: 接收路径并分析

```
/EngineeringCoding_Audit <path> [--mode=quick|full|deep]
```

1. 解析路径 → 2. Read 全文 → 3. 识别领域（回测/通用）→ 4. 匹配维度 → 5. 展示确认

**通用文件展示**：

```
已加载: /path/to/file.ts (420 行) | 语言: TypeScript
领域: 通用 | 审查模式: full | 预计: ~10 min

审查维度 (6):
  ✅ 逻辑正确性  ✅ 边界与容错  ✅ 性能与资源
  ✅ 安全性      ✅ 可维护性    ⬜ 并发与状态 (跳过)

确认开始？
```

**回测代码展示**：

```
已加载: /path/to/executor.py (695 行) | 语言: Python
领域: 🔬 回测代码 | 审查模式: full | 预计: ~15 min

审查维度 (10):
  通用: ✅逻辑 ✅边界 ✅性能 ✅安全 ✅维护 ⬜并发
  回测: ✅时序 ✅财务 ✅多板 ✅交易

确认开始？
```

## Step 2: Phase 1 — 并行发现（full/deep）

所有匹配维度并行审查，一轮完成，去重合并。

## Step 3: Phase 2 — Adversarial Verify（所有模式）

- CRITICAL + HIGH 问题（最多 8 个），每个 4 Agent 证伪
- 默认立场：**"这不是 bug，请证明它是"**
- ≥3/4 确认保留；MEDIUM/LOW 直接通过
- 回测模式下，4 个证伪 Agent 至少 1 个使用回测领域 lens

## Step 4: Phase 3 — Judge Panel（仅 deep）

Top-3 问题 × 5 视角竞赛 + 独立评委打分 + 嫁接建议

## Step 5: 输出报告 + 5 项校验 → open HTML

报告校验：
1. MD/HTML 存在 2. 含严重度标记 3. 含必要章节 4. HTML 结构完整 5. 行号 ≤ 源文件行数

---

# Part D: Workflow 脚本模板

**⚠️ 所有子 Agent 硬约束（注入每个 agent prompt）：**

> 你的唯一产出是 StructuredOutput JSON。禁止使用 Edit/Write 修改任何源文件。
> 即使修复看起来很简单，也只能在 suggested_fix/code_changes 字段中描述方案，不得实际执行。
> 审查报告是只读产物，代码修改由用户事后自主决定。

## 模板 1: Phase 1 — 并行发现

```javascript
export const meta = {
  name: 'audit-discover',
  description: '所有审查维度并行执行，一轮完成发现',
  phases: [{ title: 'Discover', detail: '多维度并行审查' }],
};

phase('Discover');

const FILE_PATH = '${FILE_PATH}';
const FILE_CONTENT = `${FILE_CONTENT}`;
const DIMENSIONS = ${DIMENSIONS}; // [{key, label, checklist}]
const DOMAIN_KNOWLEDGE = `${DOMAIN_KNOWLEDGE}`; // 回测领域知识（通用文件为空字符串）

const ISSUE_SCHEMA = {
  type: 'object',
  properties: {
    issues: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          line_range: { type: 'string' },
          category: { type: 'string', enum: ['BUG', 'SMELL', 'PERF', 'SECURITY'] },
          severity: { type: 'string', enum: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] },
          dimension: { type: 'string' },
          title: { type: 'string' },
          description: { type: 'string' },
          reproducible_scenario: { type: 'string' },
          suggested_fix: { type: 'string' },
        },
        required: ['line_range', 'category', 'severity', 'dimension', 'title', 'description'],
      },
    },
  },
  required: ['issues'],
};

const allResults = await parallel(
  DIMENSIONS.map(dim => () =>
    agent(
      `你是代码审查专家。\n\n审查文件: ${FILE_PATH}\n审查维度: ${dim.label}\n\n` +
      `检查清单:\n${dim.checklist}\n\n` +
      (DOMAIN_KNOWLEDGE ? `领域知识:\n${DOMAIN_KNOWLEDGE}\n\n` : '') +
      `代码全文:\n\`\`\`\n${FILE_CONTENT}\n\`\`\`\n\n` +
      `从【${dim.label}】维度审查。只报告你确信的问题（不需要凑数），宁缺毋滥。\n\n` +
      `⚠️ 严格约束: 你的唯一产出是 StructuredOutput JSON。禁止使用 Edit/Write 修改源文件。`,
      { label: dim.key, schema: ISSUE_SCHEMA }
    )
  )
);

// 去重合并
const seenKeys = new Set();
const allFindings = [];
for (const result of allResults) {
  if (!result?.issues?.length) continue;
  for (const issue of result.issues) {
    const key = `${issue.line_range}|${issue.dimension}|${issue.title}`;
    if (!seenKeys.has(key)) { seenKeys.add(key); allFindings.push(issue); }
  }
}
allFindings.sort((a, b) => ({CRITICAL:0,HIGH:1,MEDIUM:2,LOW:3}[a.severity] - {CRITICAL:0,HIGH:1,MEDIUM:2,LOW:3}[b.severity]));

log(`Phase 1: ${DIMENSIONS.length} 维度 → ${allFindings.length} 候选`);
DIMENSIONS.forEach(d => log(`  ${d.label}: ${allFindings.filter(f => f.dimension === d.key).length}`));
return { findings: allFindings, dimensions_covered: DIMENSIONS.map(d => d.key) };
```

## 模板 2: Phase 2 — Adversarial Verify

```javascript
export const meta = {
  name: 'audit-verify',
  description: '对 HIGH+ 问题做 4 维度对抗验证，过滤假阳性',
  phases: [{ title: 'Verify', detail: 'HIGH+ 问题各 4 Agent 证伪' }],
};

phase('Verify');

const FINDINGS = ${FINDINGS};
const FILE_PATH = '${FILE_PATH}';
const FILE_CONTENT = `${FILE_CONTENT}`;
const IS_BACKTEST = ${IS_BACKTEST}; // boolean

const HIGH_PLUS = FINDINGS.filter(f => ['CRITICAL', 'HIGH'].includes(f.severity)).slice(0, 8);
const LOW_RISK = FINDINGS.filter(f => !['CRITICAL', 'HIGH'].includes(f.severity));

log(`对抗验证: ${HIGH_PLUS.length} HIGH+ (各4 Agent), ${LOW_RISK.length} MEDIUM/LOW 直接通过`);

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    vote: { type: 'string', enum: ['CONFIRMED_BUG', 'FALSE_ALARM', 'NEEDS_INVESTIGATION'] },
    confidence: { type: 'number', minimum: 0, maximum: 1 },
    reasoning: { type: 'string' },
    alternative_explanation: { type: 'string' },
  },
  required: ['vote', 'confidence', 'reasoning'],
};

// 通用 lenses + 回测专属（条件叠加）
const BASE_LENSES = [
  { key: 'logic', label: '逻辑正确性', prompt: '默认立场：这段代码在所有正常输入下是正确的。请构造能证明它错误的具体输入。' },
  { key: 'boundary', label: '边界与容错', prompt: '默认立场：这段代码在正常数据范围内不会出错。请构造极端/异常输入证明它确实会崩溃。' },
  { key: 'security', label: '安全/资源', prompt: '默认立场：这段代码没有安全漏洞和资源泄漏。请证明在恶意输入或高负载下它会出问题。' },
  { key: 'maintainability', label: '可维护性', prompt: '默认立场：这段代码的可维护性是及格的。请证明它在实际演进中会导致问题。' },
];

const BT_LENSES = [
  { key: 'temporal', label: '时序正确性', prompt: '你是 PIT 专家。默认立场：这不是时序泄漏。请用证据证明未来信息确实污染了历史决策。' },
  { key: 'financial', label: '财务逻辑', prompt: '你是财务分析专家。默认立场：这个公式在标准会计准则下正确。请找出什么边界情况下失效。' },
];

const LENSES = IS_BACKTEST
  ? [BASE_LENSES[0], BASE_LENSES[1], BT_LENSES[0], BT_LENSES[1]]  // 混合: 逻辑+边界+时序+财务
  : BASE_LENSES;

const verified = await pipeline(
  HIGH_PLUS,
  async (finding) => {
    const votes = await parallel(
      LENSES.map(lens => () =>
        agent(
          `审查以下发现，从【${lens.label}】角度判断真伪:\n\n` +
          `文件: ${FILE_PATH}\n位置: ${finding.line_range}\n描述: ${finding.title}\n详情: ${finding.description}\n\n` +
          `${lens.prompt}\n\n相关代码:\n\`\`\`\n${FILE_CONTENT}\n\`\`\`\n\n` +
          `⚠️ 严格约束: 你的唯一产出是 StructuredOutput JSON。禁止使用 Edit/Write 修改源文件。`,
          { label: `${finding.title.slice(0,15)}|${lens.key}`, schema: VERDICT_SCHEMA }
        )
      )
    );
    const confirmedCount = votes.filter(Boolean).filter(v => v.vote === 'CONFIRMED_BUG').length;
    return { ...finding, confirmed_votes: confirmedCount, total_votes: votes.length,
      verdict_details: votes.filter(Boolean).map((v, i) => ({ lens: LENSES[i].label, vote: v.vote, confidence: v.confidence, reasoning: v.reasoning })),
      kept: confirmedCount >= 3 };
  },
  (vf) => { log(vf.kept ? `✅ ${vf.title} (${vf.confirmed_votes}/4)` : `❌ ${vf.title} (${vf.confirmed_votes}/4)`); }
);

const confirmed = verified.filter(Boolean).filter(f => f.kept);
const lowRiskConfirmed = LOW_RISK.map(f => ({ ...f, confirmed_votes: 'N/A', total_votes: 'N/A', kept: true }));
const allConfirmed = [...confirmed, ...lowRiskConfirmed];
allConfirmed.sort((a, b) => ({CRITICAL:0,HIGH:1,MEDIUM:2,LOW:3}[a.severity] - {CRITICAL:0,HIGH:1,MEDIUM:2,LOW:3}[b.severity]));

log(`验证完成: ${FINDINGS.length} 候选 → ${allConfirmed.length} 确认 (${confirmed.length} 验证 + ${lowRiskConfirmed.length} 直接通过)`);
return { confirmed: allConfirmed, filtered: verified.filter(Boolean).filter(f => !f.kept) };
```

## 模板 3: Phase 3 — Judge Panel（仅 deep 模式）

```javascript
export const meta = {
  name: 'audit-design',
  description: '5 视角修复方案竞赛 + 评委打分',
  phases: [{ title: 'Propose', detail: '5 Agent 设计方案' }, { title: 'Judge', detail: '评委打分' }],
};

phase('Propose');

const TOP_ISSUES = ${TOP_ISSUES};
const FILE_PATH = '${FILE_PATH}';
const FILE_CONTENT = `${FILE_CONTENT}`;

const DESIGN_SCHEMA = {
  type: 'object',
  properties: {
    approach_name: { type: 'string' }, philosophy: { type: 'string' },
    description: { type: 'string' }, code_changes: { type: 'string' },
    pros: { type: 'array', items: { type: 'string' } },
    cons: { type: 'array', items: { type: 'string' } },
    estimated_effort: { type: 'string' },
    risk_level: { type: 'string', enum: ['LOW', 'MEDIUM', 'HIGH'] },
  },
  required: ['approach_name', 'description', 'code_changes', 'pros', 'cons'],
};

const PERSPECTIVES = [
  { key: 'perf', label: '性能优先', prompt: '最小化计算/内存开销。优先高效算法、缓存、惰性求值。' },
  { key: 'correctness', label: '正确性优先', prompt: '确保所有边界下结果正确。添加断言、校验、防御性编程。' },
  { key: 'maintainability', label: '可维护性优先', prompt: '最小化认知负担。优先可读性、可测试性、职责分离。' },
  { key: 'extensibility', label: '可扩展性优先', prompt: '让未来改动更简单。优先接口抽象、配置化、插件化。' },
  { key: 'production', label: '生产就绪优先', prompt: '让系统更健壮。优先日志、监控、容错、可观测性。' },
];

const allDesigns = [];
for (const issue of TOP_ISSUES) {
  const designs = await parallel(
    PERSPECTIVES.map(p => () =>
      agent(
        `设计修复方案:\n\n问题: ${issue.title}\n文件: ${FILE_PATH}:${issue.line_range}\n严重度: ${issue.severity}\n\n` +
        `视角: ${p.label}\n${p.prompt}\n\n相关代码:\n\`\`\`\n${FILE_CONTENT}\n\`\`\`\n\n` +
        `⚠️ 严格约束: 你的唯一产出是 StructuredOutput JSON。禁止使用 Edit/Write 修改源文件。`,
        { label: `${issue.title.slice(0,15)}|${p.key}`, schema: DESIGN_SCHEMA }
      )
    )
  );
  allDesigns.push({ issue, designs: designs.filter(Boolean) });
}

phase('Judge');

const SCORE_CARD_SCHEMA = {
  type: 'object',
  properties: {
    scores: {
      type: 'object',
      properties: {
        problem_solved: { type: 'number', minimum: 1, maximum: 10 },
        feasibility: { type: 'number', minimum: 1, maximum: 10 },
        side_benefits: { type: 'number', minimum: 1, maximum: 10 },
        no_harm: { type: 'number', minimum: 1, maximum: 10 },
        reversibility: { type: 'number', minimum: 1, maximum: 10 },
      },
      required: ['problem_solved', 'feasibility', 'side_benefits', 'no_harm', 'reversibility'],
    },
    comment: { type: 'string' },
  },
  required: ['scores', 'comment'],
};

for (const entry of allDesigns) {
  const scored = await parallel(
    entry.designs.map(d => () =>
      agent(
        `评估修复方案 "${d.approach_name}":\n${d.description}\n优点: ${d.pros.join(', ')}\n缺点: ${d.cons.join(', ')}\n` +
        `从以下维度打分(1-10): 问题解决度/实施可行性/边际收益/不伤害原则/可逆性。\n\n` +
        `⚠️ 严格约束: 你的唯一产出是 StructuredOutput JSON。禁止使用 Edit/Write 修改源文件。`,
        { label: `judge:${d.approach_name}`, schema: SCORE_CARD_SCHEMA }
      )
    )
  );
  const withScores = entry.designs.map((d, i) => {
    const s = scored[i];
    if (!s) return { ...d, totalScore: 0 };
    const total = s.scores.problem_solved * 0.30 + s.scores.feasibility * 0.25 +
                  s.scores.side_benefits * 0.20 + s.scores.no_harm * 0.15 + s.scores.reversibility * 0.10;
    return { ...d, scores: s.scores, totalScore: Math.round(total * 10) / 10, judgeComment: s.comment };
  });
  withScores.sort((a, b) => b.totalScore - a.totalScore);
  const best = withScores[0];
  log(`🏆 ${entry.issue.title}: ${best.approach_name} (${best.totalScore}/10)`);
  if (withScores.length > 1) {
    const graftIdeas = withScores.slice(1).flatMap(r => r.pros.filter(p => !best.pros.includes(p))).slice(0, 3);
    if (graftIdeas.length > 0) log(`  📝 嫁接: ${graftIdeas.join('; ')}`);
  }
}

return { allDesigns };
```

---

# Part E: 输出格式

### 终端输出

```
╔═══════════════════════════════════════════════════════╗
║           代码审查报告                                   ║
║  文件: executor.py | 领域: 回测 | 模式: full              ║
╚═══════════════════════════════════════════════════════╝

📊 概览
  候选: 12  →  确认: 7  →  过滤(假阳性): 5
  🔴 CRITICAL: 1   🟠 HIGH: 3   🟡 MEDIUM: 2   🟢 LOW: 1

🔴 CRITICAL
  1. executor.py:519 — NAV 累乘中除零被静默替换
     维度: 边界与容错 | 确认: 4/4
  ...

📄 报告: .audit_reports/executor_2026-07-10.md + .html
💡 deep 模式: /EngineeringCoding_Audit --mode=deep executor.py
```

### 保存文件

- 目录：`<脚本同目录>/.audit_reports/`
- HTML：深色主题（`#0d1117`，GitHub Dark），按严重度颜色编码

### 报告校验（5 项）

1. MD/HTML 存在 2. 含严重度标记 3. 含概览+分类 4. HTML 结构完整 5. 行号合法

---

## 禁止行为

- ❌ 跳过领域识别，回测代码不用回测维度
- ❌ 通用文件强行套用回测维度
- ❌ full/deep 跳过 Phase 1 并行发现
- ❌ Adversarial Verify 少于 4 Agent，阈值低于 3/4
- ❌ 审查报告不保存文件
- ❌ 未读取文件就审查 · 擅自修改路径 · 路径不存在继续执行
- ❌ 通用文件维度少于 4 个（<30 行除外）
- ❌ 调用业务 MCP 工具（data_Gil/factor_Gil/backtest_Gil）
- ❌ 跳过报告校验 · 行号越界不修正
- ❌ 修改被审查的源代码
