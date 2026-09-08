export const meta = {
  name: 'ChinapostAMC_StrategyOrder',
  description: '中邮资管策略订单工作流：原始脚本→发单脚本改造→选股执行→调仓/复投创建→池比对剔除→在池核对→下单模板生成',
  phases: [
    { title: '改造发单脚本', detail: 'Agent 语义分析原始脚本，删除回测，保留选股，增加资金分配' },
    { title: '执行选股', detail: '创建策略目录，运行发单脚本，产出 _former.csv 等' },
    { title: '创建调仓复投', detail: '参考已有策略模板生成调仓和复投脚本（与选股并行）' },
    { title: '池比对递补', detail: '禁投/关联池比对，剔除+备选递补，权重重算' },
    { title: '在池核对', detail: '核对在池状态，生成不在可投池 CSV，拷贝 _former.csv' },
    { title: '下单模板', detail: '拷贝下单模板，填写50只代码/市场/权重' },
    { title: '执行报告', detail: '生成 HTML 执行报告，含交叉校验' },
  ],
}

// ============================================================
// ChinapostAMC_StrategyOrder — 中邮资管策略订单工作流
// ============================================================
// 调用方式: /ChinapostAMC_StrategyOrder <原始脚本路径> <策略名称> <初始资金>
//
// 输入参数 (通过 args 传入):
//   args.scriptPath  — 原始策略脚本路径 (只读，不允许改动)
//   args.strategyName — 策略名称 (用于命名脚本、文件夹)
//   args.capital      — 初始资金 (如 100000000)
//
// 项目根目录:
//   TARGET_ROOT = /Users/junye_shi/中邮资管/中邮金市/target_list
// ============================================================

const TARGET_ROOT = '/Users/junye_shi/中邮资管/中邮金市/target_list'
const STEP1_ROOT = `${TARGET_ROOT}/【step1】下单交易指令`
const STEP2_ROOT = `${TARGET_ROOT}/【step2】批量入池`
const POOL_DIR = `${STEP2_ROOT}/股票池文件`
const ORDER_TEMPLATE = `${STEP1_ROOT}/批量下单测试.xlsx`

// ============================================================
// Phase 1: Agent 改造发单脚本
// ============================================================
phase('改造发单脚本')

const transformPlan = await agent(
  `你是一个策略脚本改造专家。用户提供了一个策略的原始 Python 脚本，你需要直接改造出一个「发单脚本」。

## 用户输入
- 原始脚本路径: ${args.scriptPath}
- 策略名称: ${args.strategyName}
- 初始资金: ${args.capital}

## 改造规则（严格执行，不要征求意见，直接产出文件）

### 第一步：Read 原始脚本全文，然后用 AST / grep 精确定位以下代码块

**🗑 必须删除（回测 & 画图）：**
- \`import matplotlib.pyplot as plt\`
- \`import glob, platform\` → 改为 \`import glob\`
- \`def setup_chinese_font():\` 整个函数
- \`def patch_quantstats_font():\` 整个函数
- \`setup_chinese_font()\` 顶层调用
- \`START_DATE =\`, \`END_DATE =\`, \`RISK_FREE_RATE =\`, \`COST_BPS =\`, \`BENCHMARK_CODE =\` 常量
- \`def calculate_turnover_and_friction():\` 整个函数
- \`def run_backtest_segment():\` 整个函数
- \`def run_full_backtest():\` 整个函数
- \`def main():\` 旧的 main 函数（替换为新的）
- BASE_OUTPUT 路径改为: ${STEP1_ROOT}/${args.strategyName}

**✅ 必须保留（选股管线）：**
- DuckDB 引擎 / SQL_TPL_* / get_base_universe / filter_* / calc_* / winsorize_mad
- StrategyComponents class / run_strategy_pipeline() / THRESHOLD / FIRST_WEIGHT_TARGET
- 金融行业特殊指标库挂载

**➕ 必须新增（资金分配）：**
- 在 \`warnings.filterwarnings('ignore')\` 之后插入:
  START_DATE = "2012-12-31"
  END_DATE = "2026-06-27"
  TOTAL_CAPITAL = ${args.capital}
  TRADE_LOT_SIZE = 100
  STRATEGY_NAME = "${args.strategyName}"
- 修改 run_strategy_pipeline 签名: 加参数 output_dir=None
- 在 run_strategy_pipeline 的 return 之前加 output_dir 分支（写 CSV）
- ⚠️ **必须在 output_dir 分支末尾生成 _former.csv**: 将最终 50 只成分股（含 target_weight、因子得分、secucode）与前 20 只备选股（按排名取 pool4 中未被选入成分股的 top 20，权重列留空，类型标记为"备选股"）合并为一份 70 行 CSV，命名为 \`{STRATEGY_NAME}_Orders_{YYYYMMDD}_former.csv\`。列至少包含: secucode, 简称, 类型(成分股/备选股), target_weight, dy, ep, fcfy, roe_ttm_mean, 排名
- 替换 main() 为建仓模式：行情观测日=today, 财务观测日=前月末, 直接调 pipeline; 去掉 START_DATE/END_DATE/get_rebalance_dates 调用

### 第二步：写入文件
- 用 Write 工具写入: ${STEP1_ROOT}/${args.strategyName}/${args.strategyName}_发单脚本.py
- 原始脚本绝对不允许修改

### 第三步：语法校验
- Bash: python3 -c "import py_compile; py_compile.compile('${STEP1_ROOT}/${args.strategyName}/${args.strategyName}_发单脚本.py', doraise=True)"
- 若语法错误: 分析并修复（最多 2 次）

### 第四步：汇报
- 发单脚本路径 + 行数
- 删除/保留/新增的代码块清单

## 关键约束
- ❌ 原始脚本不允许任何改动
- ❌ 不要输出改造计划然后等待确认，直接改造并写入文件
- ❌ 不要删除选股赋权的核心逻辑
- ⚠️ 若某段代码无法确定归属，宁可保留

	### 第五步：中间态抽样交叉校验
	1. 分别在原始脚本和发单脚本的 pool_2 / pool_4 生成后插入临时 CSV 输出
	2. 抽取 pool_2 和 pool_4 中共有的 3 只股票，对比所有指标列
	3. 全部一致 → ✅ 选股规则未被误删；有差异 → ❌ 报告差异列和数值
	4. 校验完成后删除临时 CSV`,
  {
    label: '改造发单脚本（直接执行，不等待确认）',
    phase: '改造发单脚本',
    model: 'sonnet',
  }
)

log(`发单脚本改造结果: ${transformPlan ? transformPlan.slice(0, 200) + '...' : '见 agent 输出'}`)

// ============================================================
// Phase 2 & 3: 执行选股 + 创建调仓复投（并行 — Phase 3 不依赖 Phase 2 输出）
// ============================================================
phase('执行选股')

const [runResult, auxScriptsResult] = await parallel([
  // Phase 2: 执行选股
  () => agent(
    `执行以下任务：

## 策略信息
- 策略名称: ${args.strategyName}
- 初始资金: ${args.capital}
- 发单脚本路径: ${STEP1_ROOT}/${args.strategyName}/${args.strategyName}_发单脚本.py

## 任务（硬断言链，逐项通过才继续）
1. **硬断言 [ENTRY]**: Bash: find ${STEP1_ROOT}/${args.strategyName}/ -name "*发单脚本*" 确认文件存在 → 若不存在则 **ABORT**
2. 检查发单脚本中的 TOTAL_CAPITAL 是否已设为 ${args.capital}
3. 执行发单脚本: cd ${STEP1_ROOT}/${args.strategyName} && python ${args.strategyName}_发单脚本.py
4. **硬断言 [EXIT] — _former.csv 必须存在**:
   - Bash: find ${STEP1_ROOT}/${args.strategyName}/ -name "*_former*.csv" MUST return a file
   - 若不存在 → 说明 Phase 1 改造未正确嵌入 _former.csv 生成逻辑 → 分析发单脚本缺失了什么 → 用 Edit 工具修复脚本 → 重新执行（最多 2 次）→ 若仍缺失则 **ABORT 并报告缺失原因**
   - 存在后: wc -l 确认 ≥ 50 行（成分股），检查是否有备选股行（目标权重为空/NaN，标记为"备选股"）
5. 验证入选组合明细*.csv 或策略指标明细 CSV 存在
6. 汇报:
   - 实际输出目录路径
   - _former.csv 的准确行数（成分股/备选股各多少）
   - 所有产出文件的完整列表

如果执行报错，分析错误并尝试修复（最多 2 次）。`,
    {
      label: '执行发单选股',
      phase: '执行选股',
    }
  ),
  // Phase 3: 创建调仓复投（不依赖选股输出，仅需 Phase 1 的发单脚本即可并行执行）
  () => agent(
    `在发单脚本同路径下创建调仓脚本和复投脚本。

## 输入信息
- 策略名称: ${args.strategyName}
- 发单脚本: ${STEP1_ROOT}/${args.strategyName}/${args.strategyName}_发单脚本.py
- 参考模板1: ${STEP1_ROOT}/价值1号/中邮价值1号_调仓脚本.py
- 参考模板2: ${STEP1_ROOT}/价值1号/中邮价值1号_分红复投脚本.py
- 参考模板3: ${STEP1_ROOT}/红利质量/红利质量_调仓脚本.py
- 参考模板4: ${STEP1_ROOT}/红利质量/红利质量_复投脚本.py

## 任务一：创建调仓脚本
文件路径: ${STEP1_ROOT}/${args.strategyName}/${args.strategyName}_调仓脚本.py

要求:
1. 读取参考模板（1-4）的结构和逻辑模式
2. 调仓脚本核心逻辑:
   - 读取 _former.csv（70行: 50成分股+20备选股）
   - 用户配置区: INPUT_FILE / STOCKS_TO_REMOVE / REBAL_DATE / OUTPUT_DIR / 策略参数
   - 分离成分股（目标权重>0）与备选股（权重为空）
   - 剔除 STOCKS_TO_REMOVE 中指定的股票
   - 从备选股中按排名依次递补至 50 只
   - 按发单脚本的权重算法重算 50 只权重（与发单脚本保持完全一致）
   - 注意: **STOCKS_TO_REMOVE 初始为空列表**，注释说明其值应由池比对结果动态填入
   - 输出 _rebalanced.csv

## 任务二：创建复投脚本（v4 估值表直读版）
文件路径: ${STEP1_ROOT}/${args.strategyName}/${args.strategyName}_复投脚本.py

要求:
1. 读取参考模板: ${STEP1_ROOT}/dividend_reinvest.py（通用复投脚本 v4）
2. 复投脚本核心逻辑（两个数据源各司其职）:
   - **目标权重+排名**: 通过 importlib 导入发单脚本的 run_strategy_pipeline()（策略逻辑一致性，不变）
   - **精确持仓+闲置资金**: 导入 nav_estimator.load_product() + products_config 读取估值表（替代 O32 XLS 手工导出）
   - 交叉比对: delta = total_capital × target_w - current_mv(来自估值表精确市值)
   - **资金阶梯**: 闲置资金 > 3000 元才触发, 可部署资金 = max(0, non_trading_mv - 3000) × cash_ratio(默认0.5)
   - 差额>0 且 ≥100股 → 按排名补仓；差额≤0 → 跳过（只加仓不减仓）
   - 输出 _分红复投_YYYYMMDD.csv
3. 脚本支持 CLI 参数: --product, --date, --cash-ratio, --min-cash(默认3000), --fin-obs, --mkt-obs

## 关键约束
- ❌ 调仓脚本的 STOCKS_TO_REMOVE 初始值为空列表 []，不要硬编码任何历史股票代码
- ❌ 权重算法必须 import 发单脚本的参数常量（DECAY_LAMBDA / FIRST_WEIGHT_TARGET 或 DY 加权），不要重复硬编码
- ❌ 复投脚本必须 import 发单脚本的选股管线函数，不要复制粘贴选股逻辑
- ❌ 持仓数据源必须是估值表 (load_product)，不得读取 O32 XLS 文件
- ❌ 闲置资金 = non_trading_mv（估值表自动提取），不得要求用户手工填写 DIVIDEND_CASH`,
    {
      label: '创建调仓复投脚本',
      phase: '创建调仓复投',
    }
  ),
])

log(`选股执行结果: ${runResult ? runResult.slice(0, 200) + '...' : '见 agent 输出'}`)
log(`调仓/复投脚本创建: ${auxScriptsResult ? auxScriptsResult.slice(0, 200) + '...' : '见 agent 输出'}`)

// ============================================================
// Phase 4: 池比对 & 剔除 → 备选递补（并行读取池文件 → 合并比对）
// ============================================================
phase('池比对递补')

// Step 4a: 并行读取禁投池和关联交易池（互不依赖）
const [banPoolReport, relatedPoolReport] = await parallel([
  () => agent(
    `读取禁投池文件，提取 6 位 A 股代码。

## 输入
- 禁投池: ${POOL_DIR}/股票禁投池-*.xlsx（取最新日期，用 Bash: ls -t 取最新）

## 任务
1. Python + openpyxl 读取禁投池 Excel，打印列名和前 5 行数据
2. **先判断「证券代码」列的格式**:
   - 若值为 6 位数字（如 000002）→ 直接作为 secucode 使用，无需 DuckDB
   - 若值为非 6 位数字（如 6, 12345 等）→ 才需通过 DuckDB SecuMain 映射
3. 去重后汇报：文件名、总记录数、有效代码数、代码列表
4. **禁止直接假设代码列为 InnerCode 而全量走 DuckDB 映射**

## 输出格式
\`\`\`
=== 禁投池读取结果 ===
文件: xxx.xlsx
代码列格式: [6位代码 / InnerCode]
总记录数: N → 去重后: M
代码列表(前20): [000001, ...]
\`\`\``,
    { label: '禁投池读取映射', phase: '池比对递补' }
  ),
  () => agent(
    `读取关联交易池文件，提取 6 位证券代码。

## 输入
- 关联交易池1: ${POOL_DIR}/中邮资管关联交易证券池*.xlsx（取最新日期）
- 关联交易池2: ${POOL_DIR}/中邮保险关联交易证券池*.xlsx（取最新日期）

## 任务
1. Python + openpyxl 读取两个 Excel 文件
2. 从「证券代码」列直接提取 6 位代码（标准 A 股代码，直接字符串匹配，无需 DuckDB 映射）
3. 合并去重，标注来源（中邮资管 / 中邮保险）
4. 汇报: 每个文件的代码数、合并去重后总数、代码列表（含来源标注）

## 输出格式
\`\`\`
=== 关联交易池读取结果 ===
中邮资管: 文件=xxx, 代码数=N
中邮保险: 文件=xxx, 代码数=M
合并去重后: K 个代码
代码列表(含来源): [000001(中邮资管), 000002(中邮保险), ...]
\`\`\`

注意: 关联交易池代码是标准 6 位 A 股，直接字符串提取，不要走 DuckDB。`,
    { label: '关联交易池读取', phase: '池比对递补' }
  ),
])

log(`禁投池: ${banPoolReport ? banPoolReport.slice(0, 150) + '...' : '见 agent 输出'}`)
log(`关联交易池: ${relatedPoolReport ? relatedPoolReport.slice(0, 150) + '...' : '见 agent 输出'}`)

// Step 4b-4e: 汇总比对 → 剔除 → 递补 → 权重重算
const poolCheckResult = await agent(
  `基于已读取的池文件结果，执行比对、剔除、递补和权重重算。

## 硬断言 [ENTRY] — _former.csv 不存在则 ABORT（不降级、不 fallback）
1. Bash: find ${STEP1_ROOT}/${args.strategyName}/ -name "*_former*.csv" → **必须找到文件**
2. 若不存在 → **ABORT 并报告**: 「上游 Phase 2 未产出 _former.csv，请检查发单脚本的 _former.csv 生成逻辑，修复后重新运行完整工作流」
3. 存在后: Read _former.csv，确认总行数 ≥ 50 行，逐行打印所有代码+名称+类型

## 已读取的池数据
### 禁投池（InnerCode 已映射为 6 位代码）
${banPoolReport || '（见上方 agent 输出）'}

### 关联交易池（标准 6 位代码 + 来源标注）
${relatedPoolReport || '（见上方 agent 输出）'}

## 任务

### Step 4b: 全量逐行比对
1. 读入 _former.csv，提取**全部行**代码（成分股+备选股，共约70行），不可只检成分股
2. 逐行打印: 代码 + 名称 + 类型(成分股/备选股) + 是否命中禁投池 + 是否命中关联交易池

### Step 4c: 剔除
1. 成分股/备选股 ∩ 禁投池 → **直接剔除**
2. 任意股票 ∩ 关联交易池 → **标记警告，不自动剔除**，单独成节「关联交易池命中（待用户决策）」

### Step 4d: 备选递补（仅当有备选股时；无则跳过）
1. 剔除后不足 50 只且有备选股 → 从备选股按排名依次递补至 50 只
2. 若无备选股可用（仅 50 成分股模式）→ 剔除 N 只后以 (50-N) 只继续，标注「无备选股可递补」
3. 递补后 = 拟投成分股

### Step 4e: 权重重算
1. 使用调仓脚本中与发单脚本一致的权重算法，对新的 50 只股票重算权重
2. 约束: 个股权重上限、行业权重上限=20%

### Step 4f: 更新 _former.csv
1. 删除被剔除股票的行
2. 递补进来的备选股更新类型为「成分股」并填入重算权重

### 汇报格式
\`\`\`
=== 池比对结果 ===
原始: 成分股 50 + 备选股 ~20 = 共约70行
禁投池命中(剔除): N 只 (代码+名称+类型)
关联交易池命中(警告,未剔除): M 只 (代码+名称+类型+来源，**待用户决策**)
剔除后剩余: X 只成分股
从备选递补: Y 只 (代码+名称+原排名)
最终拟投成分股: 50 只
备选股剩余: Z 只
\`\`\`

## 禁止行为
- 不要只检查成分股而跳过备选股
- 不要创建 .py 脚本文件, 用 python3 -c 内联执行
- 不要凭记忆/猜测报告命中, 必须逐行打印比对过程
- 关联交易池代码是标准6位A股, 不要绕道DuckDB映射`,
  {
    label: '池比对剔除递补（全量70行逐行比对）',
    phase: '池比对递补',
    model: 'sonnet',
  }
)

log(`池比对结果: ${poolCheckResult ? poolCheckResult.slice(0, 200) + '...' : '见 agent 输出'}`)

// ============================================================
// Phase 5: 核对在池状态 & 不在池清单
// ============================================================
phase('在池核对')

const inPoolResult = await agent(
  `将 Step 4 确定的全部股票（50成分股 + 备选股）与在池查询文件核对，生成不在可投池 CSV，并拷贝选股结果。

**硬断言 [ENTRY]**: find \`*_former*.csv\` → 必须存在。若不存在 → **ABORT**，报告「上游 Phase 2/4 未产出 _former.csv，请修复上游后重新运行完整工作流」。不降级、不 fallback。

## 输入
- 最终 50 只拟投成分股 + 备选股代码（来自 Step 4 池比对后的 _former.csv 全部行）
- 在池查询文件: ${POOL_DIR}/股票在池查询_*.xlsx（取最新日期）
- 选股结果 CSV: _former.csv（Step 4 更新后的版本，路径在 Step 2 输出目录）

## 任务

### Step 5a: 核对在池状态
1. 用 Python 读入最新「股票在池查询」Excel（注意: 该文件第一行为表头描述，实际表头在第二行）
2. 从「股票」列提取所有 6 位代码（格式: 股票名(代码.交易所)）
3. 将 _former.csv **全部行**（成分股+备选股）逐一与在池代码比对，分开报告：成分股不在池 X 只 + 备选股不在池 Y 只

### Step 5b: 创建 step2 输出目录 & 生成不在池 CSV
1. 先检查 ${STEP2_ROOT}/${args.strategyName}/ 下是否已有以当天日期命名的文件夹
2. 若已存在 → **向用户提示已有文件，询问：覆盖/跳过/使用新日期命名**
3. 若不存在 → 创建该文件夹
4. 在最终路径下创建 CSV 文件，储存**不在可投池的股票**:
   - 列: 证券代码, 证券简称, 行业代码
   - 仅包含不在基础池且不在核心池的股票

### Step 5c: 拷贝选股结果
1. 将 _former.csv（Step 4 更新后的版本）**拷贝一份**保存至 step2 输出目录同路径下
2. 一并拷贝入选组合明细 CSV

### 汇报格式
\`\`\`
=== 在池核对结果 ===
step2 输出目录: ${STEP2_ROOT}/${args.strategyName}/{日期}/
不在可投池: N 只 (列出代码+名称)
_former.csv 已拷贝至 step2
入选组合明细.csv 已拷贝至 step2
\`\`\``,
  {
    label: '在池核对与清单生成（全量成分+备选）',
    phase: '在池核对',
  }
)

log(`在池核对结果: ${inPoolResult ? inPoolResult.slice(0, 200) + '...' : '见 agent 输出'}`)

// ============================================================
// Phase 6: 生成下单模板
// ============================================================
phase('下单模板')

const orderResult = await agent(
  `生成最终的下单模板 Excel 文件。

## 硬断言 [ENTRY]
1. Bash: find \`*_former*.csv\` → 必须存在（来自 Phase 4/5），不存在则 **ABORT**
2. 存在后: Read 提取 50 只成分股（代码+名称+权重），数量不对则 ABORT

## 输入
- 最终 50 只拟投成分股（代码、名称、重算后的权重 — 来自 Step 4 池比对递补后的结果）
- 下单模板: ${ORDER_TEMPLATE}

## 任务

### Step 6a: 拷贝模板
1. 拷贝 ${ORDER_TEMPLATE} 到 Step 2 输出目录（同步骤 5 创建的 ${STEP2_ROOT}/${args.strategyName}/{日期}/ 路径下）
2. 也拷贝一份到 Step 1 发单输出目录（${STEP1_ROOT}/${args.strategyName}/{日期}/ 下）

### Step 6b: 填写下单信息
用 Python + openpyxl 操作拷贝后的 xlsx 文件。模板结构: Sheet1, 第1行为表头。
1. 将 50 只拟投成分股股票代码**依次**填写至「证券代码」列（第 A 列 / col 1）
2. 逐一查询成分股交易市场，填入「交易市场内部编号」列（第 F 列 / col 6）:
   - 60xxxx / 68xxxx → 上交所 → 填入 **1**
   - 00xxxx / 30xxxx → 深交所 → 填入 **2**
3. 将重算后的理想权重（百分比形式，如 5.0 表示 5%）写入「指令金额」列（第 O 列 / col 15）
4. 注意：模板第 1 行为表头，数据从第 2 行开始填写，共填 50 行

### Step 6c: 验证
1. 确认「证券代码」列恰好填写了 **50 只，不多不少**
2. 确认交易市场内部编号全部正确填写
3. 确认指令金额项对应关系正确

### 汇报格式
\`\`\`
=== 下单模板生成 ===
模板已拷贝至: (两个路径)
证券代码列: 50 只 ✓
上交所: X 只 (代码 60xxxx / 68xxxx)
深交所: Y 只 (代码 00xxxx / 30xxxx)
权重已填入指令金额项
\`\`\``,
  {
    label: '生成下单模板',
    phase: '下单模板',
  }
)

log(`下单模板: ${orderResult ? orderResult.slice(0, 200) + '...' : '见 agent 输出'}`)

// ============================================================
// Phase 7: 生成执行报告
// ============================================================
phase('执行报告')

const reportResult = await agent(
  `生成工作流执行报告 HTML 文件。

## 报告输出路径
${STEP2_ROOT}/${args.strategyName}/{YYYY-MM-DD}/执行报告_YYYYMMDD.html
（日期目录与 Phase 5/6 相同）

## 报告内容（必须逐项填写）

### 执行摘要
策略名称、初始资金、执行时间、行情观测日、财务观测日、6 Phase 状态汇总表

### Phase 1: 改造发单脚本
- 原始脚本路径、发单脚本路径 + 行数
- 删除/保留/新增代码块清单
- 语法校验结果
- 回测残留检查（matplotlib/quantstats/backtest 是否残留）
- ⭐ 中间态抽样交叉校验：Pool 2 和 Pool 4 各抽 3 只，列出指标比对表（原始值 vs 发单值 vs 差异）

### Phase 2: 执行选股
- 输出目录路径
- Pool 0→1→2→4→5 各级数量
- 成分股/备选股数量
- 权重和、个股权重范围、行业权重 max
- 输出文件清单

### Phase 3: 创建调仓复投
- 调仓/复投脚本路径 + 行数
- STOCKS_TO_REMOVE 初始值确认（空列表）
- 发单脚本 import 可用性

### Phase 4: 池比对
- 禁投池文件 + 代码数；关联交易池文件 + 代码数
- 全量逐行比对表（70 行，每行有命中状态）
- 禁投命中清单（直接剔除）；关联交易命中清单（标记警告）
- 剔除后剩余 + 递补清单

### Phase 5: 在池核对
- 在池查询文件 + 池总代码数
- 不在可投池全量清单（成分股 + 备选股，含名称/行业）
- step2 拷贝确认

### Phase 6: 下单模板
- 模板路径（step1 + step2）
- 证券代码数=50、上交所/深交所数量
- 市场编码全对确认
- 代码顺序 vs _former.csv 一致性
- 权重 vs _former.csv 一致性

### 交叉校验
- 下单模板代码 ⊆ _former.csv 成分股
- 下单模板权重 = _former.csv 权重
- 不在池清单 = 全量 70 行 vs 在池查询
- 池比对命中清单 ⊆ _former.csv
- 禁投/关联三联核对（former 中状态、Phase 4 命中清单、模板最终态）
- Pool 2/4 抽样指标原始 vs 发单一致性

## 样式要求
- 深色主题（#0d1117 背景）
- 表格上方标注 ✅/❌/⚠️
- 异常项用红色或橙色高亮
- HTML 自包含，无需外部 CSS`,
  {
    label: '生成执行报告',
    phase: '执行报告',
  }
)

log(`执行报告: ${reportResult ? reportResult.slice(0, 200) + '...' : '见 agent 输出'}`)

log(`
╔══════════════════════════════════════════════╗
║  ChinapostAMC_StrategyOrder 工作流完成        ║
╠══════════════════════════════════════════════╣
║  策略: ${args.strategyName}                          ║
║  初始资金: ${args.capital}                      ║
╠══════════════════════════════════════════════╣
║  ✅ Phase 1: 发单脚本改造                      ║
║  ✅ Phase 2: 执行选股 (⇄ Phase 3 并行)         ║
║  ✅ Phase 3: 调仓 & 复投脚本                   ║
║  ✅ Phase 4: 池比对 & 递补 & 权重重算          ║
║  ✅ Phase 5: 在池核对 & 不在池清单             ║
║  ✅ Phase 6: 下单模板生成                      ║
║  ✅ Phase 7: 执行报告                          ║
╠══════════════════════════════════════════════╣
║  输出文件:                                     ║
║    step1/${args.strategyName}/                    ║
║      ├── ${args.strategyName}_发单脚本.py           ║
║      ├── ${args.strategyName}_调仓脚本.py           ║
║      ├── ${args.strategyName}_复投脚本.py           ║
║      └── {YYYYMMDD}/                          ║
║           ├── _former.csv                     ║
║           ├── 下单模板.xlsx                    ║
║           └── ...                             ║
║    step2/${args.strategyName}/{YYYYMMDD}/         ║
║           ├── _former.csv (拷贝)              ║
║           ├── 不在可投池.csv                   ║
║           └── 下单模板.xlsx                    ║
╚══════════════════════════════════════════════╝
`)