---
name: ResearchGil_Factor_Combine
description: 多因子合成 — 将通过三闸门验证的因子组合为复合因子，支持等权/IC加权/PCA加权/最优化配置。触发词：因子合成、factor combine、多因子组合、composite factor。
---

# /ResearchGil_Factor_Combine — 多因子合成

## 角色定位

将 `ResearchGil_Factor_Validate` 通过三闸门验证的因子（trials.db 中 `accepted=1`），按指定方法合成为复合因子，产出可供 `ResearchGil_Strategy_Backtest` 直接使用的复合因子 JSON。

## 路由

- **数据源**: `~/.gil_factors/trials.db`（已通过验证的因子列表）
- **因子定义**: `~/.gil_factors/{name}.json`（因子表达式 + IC 统计）
- **输出**: `~/.gil_factors/{composite_name}.json`（复合因子 JSON）
- **Python**: `scripts/` 目录下的合成算法

## 与其他 Skill 的勾稽关系

| 上游/下游 | Skill | 数据流 |
|-----------|-------|--------|
| 上游 | `ResearchGil_Factor_Validate` | trials.db (accepted=1) → 可选因子池 |
| 上游 | `ResearchGil_Factor_Test` | `~/.gil_factors/{name}.json` → 因子定义 |
| 下游 | `ResearchGil_Strategy_Backtest` | 复合因子 JSON → 回测 config.factors |
| 同级 | `ResearchGil_Paper_Implement` | 论文复现时的多因子组合 |

## 文件路径约定

| 角色 | 约定路径 | 说明 |
|------|----------|------|
| **输出** | `~/.gil_factors/{composite_name}.json` | 复合因子定义（含子因子权重） |
| 输入 1 | `~/.gil_factors/trials.db` | Factor_Validate 产出的验证状态 |
| 输入 2 | `~/.gil_factors/{name}.json` | 各子因子的定义文件 |

---

## 交互协议

### Step 0: 环境检查

1. 检查 `trials.db` 中是否有 `accepted=1` 的因子：
   ```python
   cd ~/.claude/skills/ResearchGil_Factor_Validate/scripts
   python3 -c "from trials_db import TrialsDB; db = TrialsDB(); print(db.accepted_factors())"
   ```
2. 若 accepted=0 → 提示"无已通过验证的因子。请先运行 /ResearchGil_Factor_Validate 通过至少一个因子。"
3. 若只有 1 个 → 提示"单一因子无需合成，可直接用于 /ResearchGil_Strategy_Backtest"

### Step 1: 选择合成因子

1. 展示已通过验证的因子列表（名称、表达式、IC IR、Sharpe）
2. 用户选择参与合成的因子（至少 2 个）
3. 若用户想包含未验证因子 → 警告"未验证因子存在过度拟合风险"，需明确确认

### Step 2: 选择合成方法

| 方法 | 说明 | 适用场景 |
|------|------|---------|
| `equal_weight` | 各因子 rank 后等权加总 | 无先验信息时的稳健选择 |
| `ic_weighted` | 按历史 IC IR 加权 | 因子历史表现差异大时 |
| `score_weighted` | 按综合得分加权（IC IR × (1 - |pairwise corr|)）| 惩罚冗余因子 |
| `pca_first_pc` | PCA 第一主成分（自动降维） | 因子数量多且共线性高时 |
| `custom` | 用户指定各因子权重 | 有先验信念 |

### Step 3: 确认复合表达式

1. 根据合成方法生成复合因子表达式：
   - `equal_weight`: `w1 * rank(f1) + w2 * rank(f2) + ...`（w 均等）
   - `ic_weighted`: 同上，w 按 IC IR 比例
   - `score_weighted`: 同上，w 按综合得分
   - `pca_first_pc`: 输出 PCA 载荷作为权重
2. 展示权重分配表
3. 用户确认或调整

### Step 4: 保存复合因子

1. 生成复合因子 JSON（兼容 save_factor 格式）
2. 保存到 `~/.gil_factors/{composite_name}.json`
3. 告知下游使用方式：`/ResearchGil_Strategy_Backtest` 的 factors 参数

---

## 复合因子 JSON 结构

```json
{
  "name": "value_quality_composite",
  "label": "价值质量复合因子",
  "version": 1,
  "created_at": "2026-07-05T...",
  "created_by": "ResearchGil_Factor_Combine",
  "expression": "0.35 * rank(1/pe) + 0.35 * rank(roe_ttm) + 0.30 * rank(fcff_yield)",
  "composite_method": "score_weighted",
  "sub_factors": [
    {"name": "ep_factor", "weight": 0.35, "ic_ir": 0.62, "expression": "rank(1/pe)"},
    {"name": "roe_factor", "weight": 0.35, "ic_ir": 0.55, "expression": "rank(roettm)"},
    {"name": "fcff_yield", "weight": 0.30, "ic_ir": 0.42, "expression": "rank((netoperatecashflow_ttm - capex_ttm) / enterprisevaluen)"}
  ],
  "dataset_path": "/Users/junye_shi/.gil_datasets/{dataset_name}.json",
  "stats": {
    "ic_mean": 0.042,
    "ic_ir": 0.68,
    "n_factors": 3
  }
}
```

---

## 禁止行为

- ❌ 包含未通过三闸门验证的因子（accepted≠1）
- ❌ 子因子使用不同的 Dataset（必须同一 Dataset 以保证日期对齐）
- ❌ 合成权重未归一化（权重之和必须等于 1）
- ❌ 跳过权重展示直接保存
