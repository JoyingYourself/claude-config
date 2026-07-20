export const meta = {
  name: 'PersonalResearch_PaperDigestWeekly',
  description: '量化研究周度论文文摘：多源扫描→分类筛选→深度分析→因子提取→回测验证→研究报告→知识沉淀',
  phases: [
    { title: '多源论文扫描', detail: 'ExploreScholar_Scan: arXiv+NBER+SSRN+期刊 四源抓取去重 → 300-500篇' },
    { title: '分类筛选与摘要', detail: 'ExploreScholar_Digest: 关键词过滤+LLM三问→按配额精选35篇(20+10+5)' },
    { title: '批量深度分析', detail: 'Agent pipeline 并发分析 35 篇论文' },
    { title: '因子提取与复现评估', detail: 'ResearchGil_Paper_Implement: 公式提取→Gildata映射→可用性评估' },
    { title: '回测验证', detail: 'Factor_Test → Factor_Validate → Strategy_Backtest → Report_Performance' },
    { title: '研究报告生成', detail: 'ExploreScholar_Report: 四部分递进报告 → HTML+MD 双格式' },
    { title: '知识沉淀与清理', detail: 'DocumentObsidian_Vault + DocumentJournal_Daily + 临时文件清理' },
  ],
}

// ============================================================
// PersonalResearch_PaperDigestWeekly — 量化研究周度论文文摘
// ============================================================
// 调用方式: /PersonalResearch_PaperDigestWeekly [YYYY-MM-DD] [YYYY-Www]
//   不传参数时: Agent 从系统获取当天日期（bash date 命令）
//   传参时: args.today = "YYYY-MM-DD", args.week = "YYYY-Www"
//
// 产出路径:
//   最终报告: /Users/junye_shi/AgentFiles/Multi-toolIntegrationAgent/Weekly_ResearchReport/YYYY-MM-DD/
//   中间文件: /Users/junye_shi/AgentFiles/Multi-toolIntegrationAgent/Weekly_ResearchReport/中间文件/YYYY-MM-DD/
//   临时文件: /tmp/ (Phase 7 主动清理)
// ============================================================

const SKILLS = '/Users/junye_shi/.claude/skills'
const REPORT_ROOT = '/Users/junye_shi/AgentFiles/Multi-toolIntegrationAgent/Weekly_ResearchReport'

// ⚠️ Workflow 脚本禁止使用 new Date() / Date.now()（会抛异常）。
// 日期通过 args 传入，或由 Phase 1 的 bash date 命令获取。

// 从 args 获取日期，未提供时留空（Phase 1 执行后从系统获取）
const TODAY = args.today || ''
const WEEK = args.week || ''

// FINAL_DIR / MID_DIR 在 Phase 1 Step 1.0 中计算（依赖 TODAY_RESOLVED）

// Temp files
const TEMP = {
  arxiv: '/tmp/arxiv_raw.json',
  nber: '/tmp/nber_raw.json',
  ssrn: '/tmp/ssrn_raw.json',
  journals: '/tmp/journals_raw.json',
  all: '/tmp/all_papers.json',
  keyword: '/tmp/keyword_filtered.json',
  classified: '/tmp/classified_papers.json',
  weeklyReport: '/tmp/weekly_report.json',
}

// ============================================================
// Phase 1: 多源论文扫描（Python 零 token）
// ============================================================
phase('多源论文扫描')

// Step 1.0: 若 args 未提供日期，从系统获取（Workflow 禁止 new Date()）
let TODAY_RESOLVED = TODAY
let WEEK_RESOLVED = WEEK
if (!TODAY_RESOLVED || !WEEK_RESOLVED) {
  const dateResult = await bash(
    `echo $(date +%Y-%m-%d) $(date +%Y-W%V)`,
    { label: '获取系统日期' }
  )
  const parts = dateResult?.stdout?.trim().split(/\s+/) || []
  if (!TODAY_RESOLVED) TODAY_RESOLVED = parts[0] || 'unknown-date'
  if (!WEEK_RESOLVED) WEEK_RESOLVED = parts[1] || 'unknown-week'
  log(`系统日期: ${TODAY_RESOLVED} | 周次: ${WEEK_RESOLVED}`)
}

const FINAL_DIR = `${REPORT_ROOT}/${TODAY_RESOLVED}`
const MID_DIR = `${REPORT_ROOT}/中间文件/${TODAY_RESOLVED}`

// Step 1.1: 创建输出目录
await bash(`mkdir -p "${FINAL_DIR}" "${MID_DIR}/scan_raw" "${MID_DIR}/filtered" "${MID_DIR}/analysis" "${MID_DIR}/factors" "${MID_DIR}/backtests"`)
log(`输出目录已创建: ${FINAL_DIR} | ${MID_DIR}`)

// Step 1.2: 四源并行抓取
const scanResults = await parallel([
  () => bash(
    `python3 ${SKILLS}/ExploreScholar_Scan/scripts/fetch_arxiv.py --output ${TEMP.arxiv}`,
    { label: '抓取 arXiv q-fin', description: 'arXiv 9个 q-fin 类别 + cs.LG/stat.ML 关键词过滤' }
  ),
  () => bash(
    `python3 ${SKILLS}/ExploreScholar_Scan/scripts/fetch_nber.py --output ${TEMP.nber}`,
    { label: '抓取 NBER', description: 'NBER RSS → AP/CF/EF/ME 程序过滤' }
  ),
  () => bash(
    `python3 ${SKILLS}/ExploreScholar_Scan/scripts/fetch_ssrn.py --output ${TEMP.ssrn}`,
    { label: '抓取 SSRN', description: 'SSRN FEN/ERN 网络 RSS' }
  ),
  () => bash(
    `python3 ${SKILLS}/ExploreScholar_Scan/scripts/fetch_journals.py --output ${TEMP.journals}`,
    { label: '抓取金融期刊', description: 'JF/JFE/RFS/JFQA/JPM TOC' }
  ),
])

// Parse scan results
let arxivCount = 0, nberCount = 0, ssrnCount = 0, journalCount = 0
try { arxivCount = JSON.parse(scanResults[0]?.stdout || '{}').count || 0 } catch(e) {}
try { nberCount = JSON.parse(scanResults[1]?.stdout || '{}').count || 0 } catch(e) {}
try { ssrnCount = JSON.parse(scanResults[2]?.stdout || '{}').count || 0 } catch(e) {}
try { journalCount = JSON.parse(scanResults[3]?.stdout || '{}').count || 0 } catch(e) {}
log(`扫描结果: arXiv ${arxivCount} | NBER ${nberCount} | SSRN ${ssrnCount} | 期刊 ${journalCount} = 共 ${arxivCount + nberCount + ssrnCount + journalCount} 篇`)

// Step 1.3: 去重合并
const mergeResult = await bash(
  `python3 ${SKILLS}/ExploreScholar_Scan/scripts/merge_dedup.py --inputs ${TEMP.arxiv},${TEMP.nber},${TEMP.ssrn},${TEMP.journals} --output ${TEMP.all}`,
  { label: '四源去重合并', description: 'DOI→标题相似度→arXiv ID 三级去重' }
)

let mergeStats = { total_after: 0, total_before: 0, removed: 0 }
try { mergeStats = JSON.parse(mergeResult?.stdout || '{}') } catch(e) {}
log(`去重合并: ${mergeStats.total_before} → ${mergeStats.total_after} 篇 (去除 ${mergeStats.removed} 篇重复)`)

// Step 1.4: 归档原始数据
await bash(`cp ${TEMP.arxiv} "${MID_DIR}/scan_raw/arxiv_raw.json"`)
await bash(`cp ${TEMP.nber} "${MID_DIR}/scan_raw/nber_raw.json"`)
await bash(`cp ${TEMP.ssrn} "${MID_DIR}/scan_raw/ssrn_raw.json"`)
await bash(`cp ${TEMP.journals} "${MID_DIR}/scan_raw/journals_raw.json"`)
await bash(`cp ${TEMP.all} "${MID_DIR}/scan_raw/merged_all.json"`)
log(`原始数据已归档至 ${MID_DIR}/scan_raw/`)

// ============================================================
// Phase 2: 分类筛选（关键词 + LLM 三问审核）
// ============================================================
phase('分类筛选与摘要')

// Step 2.1: 关键词白名单+黑名单过滤（零 token）
const kwResult = await bash(
  `python3 ${SKILLS}/ExploreScholar_Digest/scripts/filter_keywords.py \
    --input ${TEMP.all} \
    --config ${SKILLS}/ExploreScholar_Digest/config/scope_filter.yaml \
    --output ${TEMP.keyword}`,
  { label: '关键词过滤', description: '白名单~80词 + 黑名单~60词 → 80-120篇' }
)

let kwStats = { total_after: 0, total_before: 0, total_excluded: 0, stats: {} }
try { kwStats = JSON.parse(kwResult?.stdout || '{}') } catch(e) {}
log(`关键词过滤: ${kwStats.total_before} → ${kwStats.total_after} 篇 (排除 ${kwStats.total_excluded} 篇)`)

// Step 2.2: 准备 LLM 分类输入
await bash(
  `python3 ${SKILLS}/ExploreScholar_Digest/scripts/classify_papers.py \
    --input ${TEMP.keyword} \
    --prompt ${SKILLS}/ExploreScholar_Digest/prompts/classify_filter.md \
    --quotas ${SKILLS}/ExploreScholar_Digest/config/quotas.yaml \
    --output ${TEMP.classified}`,
  { label: '准备分类输入' }
)

// Step 2.3: LLM 三问审核 + 按配额精选 35 篇
const classifyResult = await agent(
  `你是一个量化选股因子研究专家。请对候选论文执行三问审核和分类筛选。

## 输入数据
- 分类数据文件: ${TEMP.classified}
- 分类 Prompt: ${SKILLS}/ExploreScholar_Digest/prompts/classify_filter.md
- 配额配置: ${SKILLS}/ExploreScholar_Digest/config/quotas.yaml

## 任务

### Step 1: 读取分类数据
Read ${TEMP.classified}，获取 candidates 列表。

### Step 2: 对每篇论文执行三问审核
按照 ${SKILLS}/ExploreScholar_Digest/prompts/classify_filter.md 中的标准，对每篇候选论文回答:

1. **Q1: 涉及权益市场横截面收益预测？** (yes/no) + 理由
2. **Q2: 可用财报/行情数据构建？** (yes/no) + 理由
3. **Q3: 在中国A股有复现价值？** (yes/no) + 理由

### Step 3: 因子大类分类
将每篇论文归入: fundamental / momentum / alternative

### Step 4: 优先级评分（1-10）
- novelty_score (40%): 新颖性
- replicability_score (35%): 可复现性
- significance_score (25%): 成果显著性

### Step 5: 按配额精选 35 篇
配额:
- 基本面因子: 20篇 (EN 12 + ZH 8)
- 动量因子: 10篇 (EN 6 + ZH 4)
- 另类数据: 5篇 (EN 3 + ZH 2)

仅选 3 个 Q 均为 YES 的论文。在每类配额内按综合评分降序排列。

### Step 6: 写入结果
将完整的分类结果写回 ${TEMP.classified}，填充:
- classified_papers: 每篇的完整审核结果
- selected: 按类别分组的精选 35 篇
- excluded: 排除的论文及原因
- stats: { total_candidates, passed_three_q, selected_by_category, ... }

### Step 7: 汇报
\`\`\`
=== 三问审核结果 ===
候选论文: N 篇
三问全部通过: N 篇
精选入选: 35 篇
  ├── 基本面因子: N 篇 (EN N / ZH N)
  ├── 动量因子: N 篇 (EN N / ZH N)
  └── 另类数据: N 篇 (EN N / ZH N)
排除: N 篇 (Q1不通过 N / Q2不通过 N / Q3不通过 N / 配额不足 N)
\`\`\`

## 关键约束
- 仅 3 个 YES 才能进入精选
- 宁缺毋滥: 如果某类候选不足，标记不足数，不要强行凑
- 每篇必须给出三问的具体理由，不能只写 yes/no`,
  { label: 'LLM三问审核+分类精选', phase: '分类筛选与摘要', model: 'sonnet' }
)

log(`LLM分类完成: ${classifyResult ? classifyResult.slice(0, 300) + '...' : '见 agent 输出'}`)

// Step 2.4: 归档过滤结果
await bash(`cp ${TEMP.keyword} "${MID_DIR}/filtered/keyword_filtered.json"`)
await bash(`cp ${TEMP.classified} "${MID_DIR}/filtered/classified_papers.json"`)

// ============================================================
// Phase 3: Agent pipeline 并发深度分析 35 篇
// ============================================================
phase('批量深度分析')

// Load classified papers to get the 35 selected
const classifiedData = await bash(`python3 -c "
import json
with open('${TEMP.classified}') as f:
    data = json.load(f)
selected = data.get('selected', {})
all_papers = []
for cat in ['fundamental', 'momentum', 'alternative']:
    for p in selected.get(cat, {}).get('all', []):
        all_papers.append(p)
print(json.dumps({'total': len(all_papers), 'papers': all_papers}))
"`, { label: '加载精选论文列表' })

let selectedPapers = []
try {
  const parsed = JSON.parse(classifiedData?.stdout || '{}')
  selectedPapers = parsed.papers || []
} catch(e) {
  log(`⚠️ 无法解析精选论文列表，将尝试从文件直接读取`)
}

const TOTAL_SELECTED = selectedPapers.length || 35
log(`入选论文: ${TOTAL_SELECTED} 篇，启动 pipeline 并发深度分析`)

// Step 3: Pipeline 并发深度分析每篇论文
const paperAnalyses = await pipeline(
  selectedPapers.length > 0 ? selectedPapers : Array.from({length: TOTAL_SELECTED}, (_, i) => ({ index: i })),
  async (paper) => {
    const idx = paper.index !== undefined ? paper.index : selectedPapers.indexOf(paper)
    const paperTitle = paper.title || `论文 #${idx + 1}`
    const paperId = paper.paper_id || `paper_${String(idx + 1).padStart(3, '0')}`

    const analysis = await agent(
      `你是一个量化金融研究专家。请对以下论文进行结构化深度分析。

## 论文信息
- Paper ID: ${paperId}
- 标题: ${paperTitle}
- 作者: ${Array.isArray(paper.authors) ? paper.authors.join(', ') : paper.authors || '未知'}
- 年份: ${paper.year || '未知'}
- 来源: ${paper.source || '未知'}
- 分类: ${paper.category || '未知'}
- 摘要: ${paper.abstract || '(无摘要)'}
- URL: ${paper.url || ''}

## 分析要求
按照 ${SKILLS}/ResearchGil_Paper_Implement/prompts/paper_analysis.md 中的完整框架进行分析。

## 输出
1. 将结构化分析结果写为: ${MID_DIR}/analysis/${paperId.replace(/[:\/]/g, '_')}.json
2. 同时生成可读的 Markdown 分析笔记: ${MID_DIR}/analysis/${paperId.replace(/[:\/]/g, '_')}.md
3. 返回核心发现摘要（≤100字）

## 关键约束
- 保留完整公式（LaTeX）
- 每个变量标注定义、单位、频率
- 评估 A 股复现价值（高/中/低）+ 理由
- 不做主观取舍，完整记录`,
      {
        label: `分析:${paperTitle.slice(0, 40)}`,
        schema: {
          type: 'object',
          properties: {
            paper_id: { type: 'string' },
            core_finding: { type: 'string' },
            factors_found: { type: 'number' },
            a_share_replication_value: { type: 'string', enum: ['high', 'medium', 'low'] },
            main_contribution: { type: 'string' },
          },
          required: ['paper_id', 'core_finding', 'a_share_replication_value'],
        },
      }
    )
    return { index: idx, paperId, title: paperTitle, analysis }
  }
)

const validAnalyses = paperAnalyses.filter(Boolean)
log(`深度分析完成: ${validAnalyses.length}/${TOTAL_SELECTED} 篇成功`)

// ============================================================
// Phase 4: 因子提取与复现评估
// ============================================================
phase('因子提取与复现评估')

const factorExtraction = await agent(
  `你是一个量化因子工程师。请从深度分析结果中提取可复现的量化因子。

## 输入
- 论文分析目录: ${MID_DIR}/analysis/
- 分类论文数据: ${MID_DIR}/filtered/classified_papers.json
- 因子提取 Prompt: ${SKILLS}/ResearchGil_Paper_Implement/prompts/factor_extraction.md

## 任务

### Step 1: 提取因子公式
Read 所有 paper_*.json 分析文件，按照 ${SKILLS}/ResearchGil_Paper_Implement/prompts/factor_extraction.md 中的规范提取因子。

### Step 2: Gildata 字段映射
对每个因子的每个变量，查找对应的 Gildata 数据库字段（参考 prompt 中的字段映射表）。

### Step 3: 可复现性评估
按三个级别分类:
- ✅ 可直接复现: 所有字段在 Gil 中可直接使用
- ⚠️ 需近似替代: 部分变量需要近似替代
- ❌ 无法复现: 关键字段缺失且无替代方案

### Step 4: 复现优先级排序
综合评分 = 字段可用性(40%) × 方法创新性(30%) × 预期IC(30%)
按评分降序排列，取前 8-15 个因子。

### Step 5: 写入输出
- ${MID_DIR}/factors/extracted_factors.json — 所有提取的因子
- ${MID_DIR}/factors/replicable_factors.json — 可复现因子（✅ + ⚠️）
- ${MID_DIR}/factors/field_mapping.json — 因子→Gil字段映射

### Step 6: 汇报
\`\`\`
=== 因子提取结果 ===
提取因子总数: N
可直接复现 (✅): N
需近似替代 (⚠️): N
无法复现 (❌): N
建议进入回测: N 个 (Top 8-15)
\`\`\`

## 关键约束
- 不要跳过 Gildata 字段验证
- 缺少关键字段时不要标记为"可直接复现"
- 因子表达式必须可在 Factor_Test 中直接使用`,
  { label: '因子提取+Gildata映射+优先级排序', phase: '因子提取与复现评估' }
)

log(`因子提取完成: ${factorExtraction ? factorExtraction.slice(0, 200) + '...' : '见 agent 输出'}`)

// ============================================================
// Phase 5: 回测验证（串联已有 ResearchGil_* Skill 链）
// ============================================================
phase('回测验证')

const backtestResult = await agent(
  `对 Phase 4 产出的可复现因子执行回测验证。

## 输入
- 可复现因子: ${MID_DIR}/factors/replicable_factors.json
- 字段映射: ${MID_DIR}/factors/field_mapping.json

## 执行流程

对每个可复现因子（按优先级降序，最多 8-15 个）执行:

### Step 1: ResearchGil_Data_Discover
验证因子所需的 Gildata 字段是否可用。
调用方式: 使用 Skill 工具调用 ResearchGil_Data_Discover，参数为因子的字段列表。

### Step 2: ResearchGil_Factor_Test
对字段可用的因子执行单因子检测:
- 计算 IC 均值 / ICIR / IC 衰减
- 分组收益 (5分位/10分位)
- 多空组合收益

### Step 3: ResearchGil_Factor_Validate
对通过初步检测的因子执行统计验证:
- Deflated Sharpe Ratio (DSR)
- 三闸门: DSR + Correlation + PCA
- 诚实试错计数器 (Honest Trial Counter)

仅通过三闸门验证的因子进入下一步。

### Step 4: ResearchGil_Strategy_Backtest
对通过验证的因子执行策略组装与回测。

### Step 5: ResearchGil_Report_Performance
生成绩效归因报告。

### Step 6: 汇总结果
将所有回测结果保存至 ${MID_DIR}/backtests/。
生成汇总表: 因子名 | IC | ICIR | 分层收益 | DSR | 状态

## 关键约束
- 必须按顺序执行，不可跳过步骤
- 不通过三闸门验证的因子不要进入 Strategy_Backtest
- 每个因子的回测结果单独保存`,
  { label: '执行回测验证链', phase: '回测验证' }
)

log(`回测验证完成: ${backtestResult ? backtestResult.slice(0, 200) + '...' : '见 agent 输出'}`)

// ============================================================
// Phase 6: 研究报告生成（四部分递进，不限篇幅）
// ============================================================
phase('研究报告生成')

const reportResult = await agent(
  `你是一个资深量化研究总监。请综合本周全量研究数据，生成完整的量化研究周度论文报告。

## 输入数据
- 全量扫描: ${MID_DIR}/scan_raw/merged_all.json
- 关键词过滤后: ${MID_DIR}/filtered/keyword_filtered.json
- 分类精选: ${MID_DIR}/filtered/classified_papers.json
- 深度分析: ${MID_DIR}/analysis/ (35 篇)
- 因子提取: ${MID_DIR}/factors/extracted_factors.json
- 回测结果: ${MID_DIR}/backtests/

## 报告 Prompt
按照 ${SKILLS}/ExploreScholar_Report/prompts/weekly_report.md 的完整要求生成。

## 报告结构（四部分 + 附录，不限篇幅）

### 第一部分：近期研究方向全景总结（≥2000字）
### 第二部分：35 篇论文核心成果精要（每篇 150-300字）
### 第三部分：重点论文深度汇报（5-8 篇，每篇 1500-3000字）
### 第四部分：复现执行结果
### 附录 A/B/C

## 输出

1. 生成报告 JSON 写入: ${TEMP.weeklyReport}
   Schema 参考 ${SKILLS}/ExploreScholar_Report/scripts/render_report.py 中的 render_html() 函数期望的字段结构。

2. 调用渲染脚本生成双格式:
   python3 ${SKILLS}/ExploreScholar_Report/scripts/render_report.py \
     --input ${TEMP.weeklyReport} \
     --output-dir "${FINAL_DIR}" \
     --week "${WEEK_RESOLVED}"

3. 验证输出文件存在:
   - ${FINAL_DIR}/weekly_report.html
   - ${FINAL_DIR}/weekly_report.md

## 关键约束
- 不限篇幅，宁可详尽不可遗漏
- 所有 35 篇论文必须全部出现在第二部分
- 深度汇报的公式必须保留完整 LaTeX
- HTML 包含所有图表和数据表格
- 报告必须标注生成时间: ${TODAY_RESOLVED}`,
  { label: '生成四部分递进研究报告', phase: '研究报告生成', model: 'sonnet' }
)

log(`报告生成完成: ${reportResult ? reportResult.slice(0, 200) + '...' : '见 agent 输出'}`)

// Verify output files exist
await bash(`ls -lh "${FINAL_DIR}/weekly_report.html" "${FINAL_DIR}/weekly_report.md"`)

// ============================================================
// Phase 7: 知识沉淀 + 临时文件清理
// ============================================================
phase('知识沉淀与清理')

// Step 7.1: 归档中间数据
await bash(`cp ${TEMP.weeklyReport} "${MID_DIR}/weekly_report.json"`)

// Step 7.2: DocumentObsidian_Vault（知识沉淀）
const obsidianResult = await agent(
  `将本周量化研究周报的核心发现沉淀到 Obsidian 知识库。

## 输入
- 周报: ${FINAL_DIR}/weekly_report.md
- 深度分析: ${MID_DIR}/analysis/
- 因子提取: ${MID_DIR}/factors/extracted_factors.json
- 回测结果: ${MID_DIR}/backtests/

## 任务
1. 调用 DocumentObsidian_Vault Skill，将本周新发现的因子和研究发现归入知识库
2. 为每个通过回测的因子创建或更新 Obsidian 笔记
3. 更新因子知识图谱（Canvas 可视化）
4. 标注来源论文和回测结果`,
  { label: 'Obsidian知识沉淀', phase: '知识沉淀与清理' }
)

// Step 7.3: DocumentJournal_Daily（工作日志）
const journalResult = await agent(
  `生成本次 PersonalResearch_PaperDigestWeekly 工作流执行的工作日志。

## 输入
- 工作流名称: PersonalResearch_PaperDigestWeekly
- 执行日期: ${TODAY_RESOLVED}
- 周次: ${WEEK_RESOLVED}
- 各 Phase 执行状态

## 任务
调用 DocumentJournal_Daily Skill，追加以下内容:
1. 执行摘要: 本周论文扫描/筛选/分析/回测概况
2. 关键发现: 最有价值的 3-5 个因子
3. 回测结果: 通过 DSR 的因子数量
4. 产出路径: ${FINAL_DIR}/
5. 分类归属: ScholarshipEarning`,
  { label: '工作日志追加', phase: '知识沉淀与清理' }
)

// Step 7.4: 清理临时文件
await bash(`rm -f ${TEMP.arxiv} ${TEMP.nber} ${TEMP.ssrn} ${TEMP.journals} ${TEMP.all} ${TEMP.keyword} ${TEMP.classified} ${TEMP.weeklyReport}`)
log('临时文件已清理: /tmp/*.json')

// Step 7.5: 清理超过 4 期的旧中间数据（保留 backtests/）
await bash(`
ls -d "${REPORT_ROOT}/中间文件/"*/ 2>/dev/null | sort | head -n -4 | while read dir; do
  rm -rf "$dir/scan_raw" "$dir/filtered" "$dir/analysis" "$dir/factors" 2>/dev/null
  echo "清理旧中间数据: $dir"
done
echo "中间数据清理完成（保留最近 4 期 + 全部 backtests）"
`)
log('旧中间数据清理完成（保留最近4期，backtests长期保留）')

// ============================================================
// 最终汇总
// ============================================================
log(`
╔══════════════════════════════════════════════════════════╗
║  PersonalResearch_PaperDigestWeekly 工作流执行完成              ║
╠══════════════════════════════════════════════════════════╣
║  日期: ${TODAY_RESOLVED}  |  周次: ${WEEK_RESOLVED}                          ║
╠══════════════════════════════════════════════════════════╣
║  ✅ Phase 1: 多源论文扫描 — ${mergeStats.total_after || '?'} 篇去重后            ║
║  ✅ Phase 2: 分类筛选 — 35 篇精选 (20+10+5)                ║
║  ✅ Phase 3: 批量深度分析 — ${validAnalyses.length} 篇完成              ║
║  ✅ Phase 4: 因子提取与复现评估                             ║
║  ✅ Phase 5: 回测验证                                      ║
║  ✅ Phase 6: 研究报告生成                                   ║
║  ✅ Phase 7: 知识沉淀 + 临时文件清理                        ║
╠══════════════════════════════════════════════════════════╣
║  🎯 最终报告:                                              ║
║    ${FINAL_DIR}/weekly_report.html                         ║
║    ${FINAL_DIR}/weekly_report.md                           ║
║                                                             ║
║  ⚙️ 中间数据:                                              ║
║    ${MID_DIR}/                                              ║
║      ├── scan_raw/     (${mergeStats.total_after || '?'} 篇原始数据)              ║
║      ├── filtered/     (分类筛选结果)                       ║
║      ├── analysis/     (${validAnalyses.length} 篇深度分析)                    ║
║      ├── factors/      (因子提取+映射)                      ║
║      └── backtests/    (回测结果，长期保留)                  ║
╚══════════════════════════════════════════════════════════╝
`)
