---
name: ExploreScholar_Scan
description: 多源学术论文扫描 — 四源（arXiv q-fin + NBER + SSRN + 金融期刊）并行抓取、去重合并，产出 300-500 篇待选论文池。触发词：论文扫描、学术扫描、arxiv扫描、nber扫描。
---

# /ExploreScholar_Scan — 多源学术论文扫描

## 角色定位

零 token 论文扫描管道。负责从四个学术来源并行抓取最新论文、去重合并，产出统一格式的候选论文池（300-500 篇）。**全程 Python 脚本执行，不消耗 LLM token。**

## 与其他 Skill 的勾稽关系

```
ExploreScholar_Scan（本 Skill）
    ↓ merged_all.json
ExploreScholar_Digest（下游：关键词过滤 + LLM 三问审核）
    ↓ classified_papers.json
Agent pipeline 深度分析
    ↓
ResearchGil_Paper_Implement（下游：因子提取 + Gildata 复现）
    ↓
ExploreScholar_Report（下游：研究报告生成）
```

> 本 Skill 由 `PersonalResearch_PaperDigestWeekly` Workflow 的 Phase 1 调用。

## 四源配置

| 信源 | 抓取方式 | 更新频率 | 预计产出 |
|------|---------|:---:|:---:|
| **arXiv q-fin** | `export.arxiv.org/api/query` (Atom XML → feedparser) | 日更 | 150-250 篇 |
| **NBER** | `nber.org/rss/new.xml` → program 过滤 (AP/CF/EF/ME) | 周更 | 20-40 篇 |
| **SSRN** | RSS feed + WebFetch (FEN + ERN 网络) | 日更 | 80-150 篇 |
| **金融期刊** | 各期刊 RSS/WebFetch 目录页 (JF/JFE/RFS/JFQA/JPM) | 双月 | 10-30 篇 |

配置定义在 `config/sources.yaml`。

## 执行流程

### Step 1: 四源并行抓取

```bash
# 四个脚本并发执行
python3 scripts/fetch_arxiv.py --cats q-fin.PM,q-fin.ST,q-fin.PR,q-fin.RM,q-fin.GN,q-fin.TR,q-fin.MF,q-fin.CP,q-fin.EC --days 7
python3 scripts/fetch_nber.py --programs AP,CF,EF,ME
python3 scripts/fetch_ssrn.py --networks FEN,ERN
python3 scripts/fetch_journals.py --journals JF,JFE,RFS,JFQA,JPM
```

每个脚本输出标准 JSON 格式到 `/tmp/`：
- `/tmp/arxiv_raw.json`
- `/tmp/nber_raw.json`
- `/tmp/ssrn_raw.json`
- `/tmp/journals_raw.json`

### Step 2: 去重合并

```bash
python3 scripts/merge_dedup.py \
  --inputs /tmp/arxiv_raw.json,/tmp/nber_raw.json,/tmp/ssrn_raw.json,/tmp/journals_raw.json \
  --output /tmp/all_papers.json
```

去重策略（三级）：
1. DOI 精确匹配
2. 标题相似度 > 0.90（Levenshtein 比率）
3. arXiv ID 匹配

### Step 3: 归档原始数据

将原始抓取结果归档到中间文件目录：
```
Weekly_ResearchReport/中间文件/YYYY-MM-DD/scan_raw/
├── arxiv_raw.json
├── nber_raw.json
├── ssrn_raw.json
├── journals_raw.json
└── merged_all.json
```

## 统一输出格式

每篇论文的标准 JSON 字段：

```json
{
  "paper_id": "arxiv:2506.12345",
  "title": "Cross-Sectional Stock Return Predictability Using...",
  "authors": ["Author A", "Author B"],
  "year": 2026,
  "source": "arxiv",
  "source_category": "q-fin.PM",
  "abstract": "...",
  "url": "https://arxiv.org/abs/2506.12345",
  "doi": "10.xxx/...",
  "language": "en",
  "fetched_at": "2026-07-01T08:00:00Z"
}
```

## 交互协议

本 Skill 由 Workflow 自动调用，无需用户交互。

当用户直接调用 `/ExploreScholar_Scan` 时：
1. 执行四源并行抓取
2. 执行去重合并
3. 汇报：各源论文数、去重后总数、去重率
4. 将 merged_all.json 路径返回给用户

## 禁止行为

- ❌ 不要修改原始抓取脚本的核心逻辑（来源标注）
- ❌ 不要跳过去重步骤直接输出
- ❌ 不要在抓取阶段消耗 LLM token（抓取是纯 Python）
- ❌ 不要硬编码日期范围，使用 `--days` 参数控制
