---
name: ResearchGil_Factor_Validate
description: 因子统计验证 — Deflated Sharpe Ratio + 三闸门（DSR/Correlation/PCA）防过拟合体系，纯 numpy/scipy 实现，不依赖任何框架
---

> ⚠️ **@deprecated (2026-07-07)**: 此 Skill 的因子验证逻辑已合并到 `ResearchGil_Factor_Test`。因子测试完成后，PASS/REVISE/RESCORE/REJECT 评判在 Factor_Test 中一步完成。请使用 `/ResearchGil_Factor_Test`。
> 此文件保留至 2026-10-07 过渡期结束后删除。

# /ResearchGil_Factor_Validate — 因子统计验证

## 角色定位

对 `ResearchGil_Factor_Test` 检测出的因子做统计严格性验证，回答核心问题：**这个因子的表现是真实 alpha 还是多重检验噪音？**

核心能力：
- **Deflated Sharpe Ratio** — Bailey & López de Prado (2014) 公式，惩罚多重测试
- **Honest Trial Counter** — SQLite 试错计数器，每次 factor test 自动 +1，无法清零
- **三闸门** — DSR p<0.05 → Correlation |corr|<0.6 → PCA concentration<0.5，AND 逻辑
- **诊断工具** — Degradation Ratio、Fold Stability、Regime Breakdown

## 路由

本 Skill 不绑定特定 MCP Server。

- 核心算法在 `scripts/` 目录，纯 numpy/scipy/pandas，零框架依赖
- 试错计数器使用 SQLite（`~/.gil_factors/trials.db`）
- 上游数据来自 `factor_Gil` 的 `test_factor` 输出（需要包含 `raw_returns` 字段）

## 输入格式

上游 `factor_Gil.test_factor()` 输出 JSON，需包含：

```json
{
  "ic_stats": {"mean": 0.035, "ir": 0.62, "series": [0.03, ...]},
  "layer_returns": {
    "long_short": {"ann_return": 0.08, "sharpe": 0.65, "max_drawdown": -0.15}
  },
  "raw_returns": {
    "long_short": [0.008, -0.003, 0.012, ...],
    "q1": [...],
    "q5": [...]
  },
  "factor": {"expression": "rank(1/pe)", "dataset": "my_dataset.json"},
  "test_config": {"start": "2020-01-01", "end": "2024-12-31", "freq": "monthly"},
  "periods": [{"date": "2020-01-31", "n": 300, "ic": 0.035}, ...]
}
```

## 与其他 Skill 的勾稽关系

| 上游/下游 | Skill | 数据流 |
|-----------|-------|--------|
| 上游 | `ResearchGil_Factor_Test` | test_factor 输出（IC stats + raw_returns）→ 本 Skill |
| 下游 | `ResearchGil_Strategy_Backtest` | 仅通过三闸门的因子（accepted=1）进入策略回测 |
| 下游 | `ResearchGil_Factor_Combine` | 通过验证的因子可参与多因子合成（等权/IC加权/PCA） |
| 同级 | `ResearchGil_Data_Validate` | Data_Validate 校验数据质量，Factor_Validate 校验因子统计显著性 |

## 文件路径约定

| 角色 | 约定路径 | 说明 |
|------|----------|------|
| **输出** | `~/.gil_factors/trials.db` | SQLite 试错计数器，记录 n_trials + 每个因子的 DSR/Corr/PCA 闸门结果 + accepted 状态 |
| 输入 | `~/.gil_factors/test_results/{name}.json` | Factor_Test 产出的 test_factor 原始输出（需含 raw_returns） |

> 路径索引：`/Users/junye_shi/AgentFiles/SkillsRelationship_output/01_Research_Pipeline/04_Trials/index.html`

---

## 交互协议

### Step 0: 环境引导（首次使用必须执行）

1. 执行 `mkdir -p ~/.gil_factors/test_results` 确保上游输出目录存在
2. 执行 `python3 -c "from trials_db import TrialsDB; db = TrialsDB(); print(f'trials.db OK: {db.count()} trials'); db.close()"` 引导 trials.db
   - 工作目录：`~/.claude/skills/ResearchGil_Factor_Validate/scripts/`
   - 如 ImportError → 引导用户安装依赖：`pip install pandas numpy scipy`
   - trials.db 不存在时自动创建（TrialsDB.__init__ 内置 CREATE TABLE IF NOT EXISTS）
3. 若上游 `~/.gil_factors/test_results/` 为空 → 提示用户先运行 `/ResearchGil_Factor_Test`

### Step 1: 接收因子检测结果

用户提供 `factor_Gil.test_factor()` 的完整 JSON 输出或直接粘贴结果。

1. **检查 raw_returns 是否可用**：
   - 若 JSON 包含 `raw_returns.long_short` → 直接进入 Step 2
   - 若 JSON 不包含 `raw_returns` → 告知用户需要重新运行 `test_factor`（factor_Gil 需支持 raw_returns 输出）
   - 若 IC 序列不足 30 期 → 告知数据量不足，Deflated Sharpe 至少需要 30 个观测

2. **加载 trials.db**：
   ```python
   from scripts.trials_db import TrialsDB
   db = TrialsDB()
   n_trials = db.count()  # 当前已记录的试错次数
   ```

3. **展示当前试错状态**：
   - 累计试错次数 n_trials
   - 已通过验证的因子列表（accepted）
   - 最近 5 次拒绝原因

### Step 2: 执行 Deflated Sharpe Ratio（Gate 1 — 硬闸门）

```python
from scripts.deflated_sharpe import deflated_sharpe
import pandas as pd

returns = pd.Series(raw_returns["long_short"])
result = deflated_sharpe(returns, n_trials=n_trials)
```

1. **展示核心结果**：

| 指标 | 含义 | 展示 |
|------|------|------|
| `sharpe_ratio` | 观测年化 Sharpe | 如 0.72 |
| `expected_max_sharpe` | 归因于多重检验的期望最大 Sharpe | 如 n_trials=50 时为 1.03 |
| `deflated_sharpe_ratio` | 消胀后 Sharpe | 如 -0.31（负值意味着不如随机） |
| `pvalue` | 统计显著性 | **< 0.05 通过** |
| `n_trials` | 诚实试错次数 | 就是答案的保真度 |

2. **DSR 闸门判定**：
   - `pvalue < 0.05` → ✅ PASS → 进入 Step 3
   - `pvalue >= 0.05` → ❌ REJECT → 记录 trials.db，给出具体原因：
     - "测了 {n_trials} 个因子，观测 Sharpe {sr} 不敌多重检验期望最大 Sharpe {em}"
     - "需要更高的 Sharpe 或更少的试错次数"

3. **若用户提供 `n_trials_override`（手动声明的额外试错次数）→ 使用 `n_trials + override`**

### Step 3: 相关性闸门（Gate 2 — 多样性检查）

```python
from scripts.gates import correlation_gate
passed, max_corr = correlation_gate(new_returns, accepted_returns, max_correlation=0.6)
```

1. **加载已通过因子**：从 trials.db 读取 `accepted=1` 的 returns_json
2. **计算与每个已通过因子的 pairwise |correlation|**
3. **展示相关性矩阵**（新因子 vs 每个已通过因子）

4. **相关性闸门判定**：
   - `max_corr < 0.6` → ✅ PASS → 进入 Step 4
   - `max_corr >= 0.6` → ❌ REJECT，给出具体原因：
     - "与因子 '{name}' 的 |corr|={corr:.2f}，超过上限 0.6"
     - "建议：修改因子构造方式以降低相关性，或接受冗余"

### Step 4: PCA 集中度（Gate 3 — 隐形冗余检测）

```python
from scripts.factor_attribution import factor_concentration_score
pca_score = factor_concentration_score(new_returns, accepted_returns)
```

1. **解释 PCA 闸门的意义**：10 个因子可以 pairwise |corr| 都 < 0.6，但全部加载在同一个主成分上 → 市场风格一转就集体回撤

2. **PCA 闸门判定**：
   - `pca_score < 0.5` → ✅ PASS
   - `pca_score >= 0.5` → ❌ REJECT："因子与已通过因子池的 PC1 的 R²={score:.2f}，虽然 pairwise 相关性没问题，但存在隐形共线性"

### Step 5: 综合裁决 + 诊断

1. **三闸门 AND 结果**：仅当三个闸门全部 PASS 时，因子通过验证

2. **附加诊断**（不影响裁决，供参考）：
   ```python
   from scripts.diagnostics import fold_stability, degradation_ratio
   # 如果有训练集/测试集分离的 Sharpe
   deg = degradation_ratio(is_sharpe, oos_sharpe)
   # 退化率 > 0.5 为健康，< 0 为过拟合
   ```

3. **记录到 trials.db**：
   ```python
   from scripts.trials_db import TrialRecord
   db.record(TrialRecord(
       factor_name=name,
       expression=expression,
       dataset_path=dataset_path,
       ic_mean=ic_mean,
       ic_ir=ic_ir,
       sharpe=sharpe,
       accepted=gate_result.passes,
       rejection_reason=gate_result.reason,
       returns_json=json.dumps(raw_returns) if gate_result.passes else "",
   ))
   ```

4. **展示最终裁决**：

```
🔬 因子验证: {factor_name}

  Gate 1 - Deflated Sharpe Ratio: ✅ p={pvalue:.4f} < 0.05
  Gate 2 - Correlation:            ✅ max|corr|={max_corr:.2f} < 0.6
  Gate 3 - PCA Concentration:       ✅ R²={pca_score:.2f} < 0.5

  🔢 n_trials: {n_trials} → {n_trials+1}

  🟢 通过 — 因子可进入策略回测
```

或

```
  Gate 1 - Deflated Sharpe Ratio: ❌ p={pvalue:.3f} >= 0.05
  Gate 2 - Correlation:            (未执行)
  Gate 3 - PCA Concentration:      (未执行)

  🔴 拒绝 — 因子未通过统计验证，不会进入回测
```

### Step 6: 查看因子库状态

```python
from scripts.trials_db import TrialsDB
db = TrialsDB()
summary = db.summary()
```

展示：
- 总试错次数
- 通过率
- 通过因子的表达式和 Sharpe
- 最近 10 次拒绝原因分布

---

## 禁止行为

- ❌ 在 raw_returns 不可用时强行运行 Deflated Sharpe（不得用 IC 序列代替收益率序列）
- ❌ 在 trials.db 初始化失败时跳过 n_trials 参数（不得传 n_trials=1 蒙混过关）
- ❌ 用户要求覆盖 DSR p-value 阈值时妥协（DSR 是硬闸门，无 overrides）
- ❌ 跳过相关性闸门直接裁决（即使只有一个已通过因子也要检查）
- ❌ 在 Gate 1 失败后仍然执行 Gate 2/3（按成本排序，一票否决，立即终止）
- ❌ 替用户声明 n_trials_override（用户可能在前面的手动测试中测了额外因子但未记录）
- ❌ 未经用户确认就修改 trials.db 中的记录

## 典型对话

```
用户: /ResearchGil_Factor_Validate
      [粘贴 test_factor 输出 JSON]

Claude: [解析 JSON，加载 trials.db]
        当前试错次数: 47，已通过: 3 个因子
        n_trials=47 时，期望最大 Sharpe=1.02

        Gate 1 - Deflated Sharpe:
        ┌────────────────────────────────────┐
        │ 观测 Sharpe:     0.72              │
        │ 期望最大 Sharpe: 1.02 (47 trials) │
        │ Deflated Sharpe: -0.30             │
        │ p-value:          0.62             │
        │                    ❌ REJECT       │
        └────────────────────────────────────┘

        测了 47 个因子后，纯噪声的期望最大 Sharpe 已经涨到 1.02。
        你的 0.72 不敌这个门槛。建议：减少试错次数（聚焦高质量假设）
        或寻找 Sharpe > 1.5 的强因子。

用户: 这个因子是第一个测试的，之前的 46 个是另一个项目

Claude: 理解。如果你声明的 n_trials_override 为 1（仅此因子），
        DSR p-value = 0.03，Gate 1 通过。
        但请注意：声明的试错次数决定了 DSR 的诚实性。
        确认 n_trials = 1 + 47 = 48，还是 n_trials = 1（仅此因子）？

用户: 仅此因子，n_trials=1

Claude: [重新计算] p=0.03 → ✅ PASS
        Gate 2: 与已通过的 3 个因子的 max|corr|=0.42 → ✅ PASS
        Gate 3: PCA R²=0.18 → ✅ PASS

        🟢 通过！因子已记录到 trials.db (id=48, accepted=1)
        可进入 ResearchGil_Strategy_Backtest
```
