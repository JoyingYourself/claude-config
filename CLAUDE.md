# Claude Code 会话指令

## ⚠️ 强制自我校验规则（每次输出前必须执行）

你正在通过 DeepSeek 模型运行。该模型**不具备内置自我校验机制**，
因此你必须在每次向用户呈现最终结果前，完成以下检查流程：

### 校验清单（逐项确认，不可跳过）

□ 1. 数据溯源：所有数字是否从源文件/工具输出中**逐字引用**？
   禁止凭"常识"或"记忆"生成数据。

□ 2. 计算验证：涉及计算时，是否展示了**完整计算过程**？
   中间结果是否正确？最终结果是否通过另一种方式交叉验证？

□ 3. 代码逻辑：代码是否能在**所有边界条件**下正确运行？
   文件路径、函数名、变量名是否与项目实际一致？

□ 4. 文件引用：引用的**文件路径是否真实存在**？
   不确定时必须用 Read 工具确认，禁止凭记忆引用。

□ 5. 逻辑一致性：结论是否与前面的分析**一致**？
   有无前后矛盾？前提→推理→结论的链条是否完整？

□ 6. 完整性：是否**遗漏**了用户要求的任何部分？

### 校验失败处置

发现任何问题 → **立即修正** → 重新检查 → 通过后再输出。
不得将"检查"作为单独步骤呈现给用户，在内部完成后直接输出正确版本。

### 不确定性标注

不确定的数据/结论，必须用 ⚠️ 明确标注："此部分需进一步验证"。
**禁止为了"看起来完整"而编造不确定的信息。**

---

# Vision Bridge — 图表生成后强制自检

当生成**任何图表/可视化输出**（matplotlib、plotly、echarts、seaborn 等）后，**必须**执行视觉自检：

1. 保存图表为 PNG 文件
2. 调用 `mcp__vision-bridge__analyze_chart(image="绝对路径")` 诊断
3. 阅读诊断报告，识别排版问题
4. 修复问题 → 重新生成 → 用 `compare_images` 对比修改前后
5. 重复直到诊断报告无问题

## 常见排查清单

- 标题是否与图表重叠或截断？
- 轴标签是否旋转角度过大/重叠？
- 图例是否溢出图表边界？
- 颜色对比度是否足够区分数据系列？
- 文字大小是否可读？
- 图表四周留白是否均匀？

## 前端/UI 检查

检查页面布局时 **禁止逐行读代码推断布局**，必须截图 + `analyze_image` 分析实际渲染。

---

# 🤖 秘书值班状态 — 会话启动自检

**每次新会话开始时**，在首次回复用户前，静默执行以下检查并汇报秘书状态：

```bash
# 1. Brain 进程
pgrep -fl "claudectl --brain" 2>/dev/null && echo "秘书在线" || echo "秘书离线"

# 2. 决策统计（本地 decisions.jsonl，v0.64.0-patched 持久化）
bash ~/.claude/hooks/brain-stats-local.sh 2>/dev/null | grep "^SHORT:" | sed 's/^SHORT: //' || echo "暂无决策数据"

# 3. Ollama/模型
curl -s localhost:11434/api/ps 2>/dev/null | python3 -c "
import json,sys; d=json.load(sys.stdin)
models=[m['name'] for m in d.get('models',[])]
print('模型已加载' if models else '模型待加载')
" 2>/dev/null || echo "Ollama状态未知"

# 4. 近期 insights（若有）
claudectl --brain --insights 2>/dev/null | head -5 || true

# 5. 上游统计对比（claudectl 原生，待 reconciler 支持后启用）
claudectl --brain-stats impact 2>/dev/null | head -3 || true
```

**汇报格式：** 在首次回复末尾简洁附上秘书状态一行，例如：
> 🤖 秘书在线 · 决策: 42 · 模型: qwen3:14b 已加载

如果 brain 进程不在、Ollama 不可达、或决策数异常，需显式提醒用户。
**不得在无关对话中重复汇报，仅在新会话首次回复时执行。**

---

# ⚡ MCP 超时防控（每次调用前强制执行）

## 当前配置

MCP 工具调用超时已配置为 **600s**（三层：`MCP_TOOL_TIMEOUT=600000` + `.mcp.json` moor `timeout:600000` + Moor DB `mcpRequestTimeoutMs=600000`）。绝大多数操作（test_factor、compose_packages 不限包数、run_pipeline、group_returns 等）均可安全通过 MCP 主路径完成。

## 两路径职责边界

| 耗时 | 路径 | 典型操作 |
|------|------|---------|
| < 600s | **MCP**（主路径，默认） | test_factor、group_returns、compose_packages（不限包数）、run_pipeline、compare_factors、correlation_matrix、ic_decay、turnover_analysis、preview_period |
| > 600s | **local_runner.py / save_script**（兜底回退） | grid_search 50+ 组合、walk_forward 全窗口滚动、离线批量跑 20+ 因子、10年全市场×周频 IC 测试 |

## 超时三步排查（防御措施）

1. `ls -lt <输出目录>` — 检查是否有时间戳匹配的新产物（假报错）
2. `ps aux | grep server` — 检查目标 MCP Server 是否被其他任务占满
3. 排除①②后才考虑回退到 local_runner.py 或 save_script

> **禁止超时后盲重试**：重试会让请求排队，加剧阻塞。

## 4 个 MCP Server 映射

| Server | 耗时风险工具 | 主路径 | 回退方案 |
|--------|-------------|--------|---------|
| data_Gil | compose_packages | MCP (600s) | 超时后 `ls -lt ~/.gil_datasets/` 查产物 |
| factor_Gil | test_factor, compare_factors, group_returns, correlation_matrix, ic_decay, turnover_analysis | **MCP 优先** | 超时回退 `local_runner.py` |
| backtest_Gil | run_pipeline, grid_search, walk_forward | **MCP 优先** | 超时回退 `save_script` 导出 .py 本地跑 |
| report_Gil | (低风险，快速查询) | MCP 直接调用 | — |

> **`local_runner.py`**: `~/AgentFiles/ClaudeCode-MCP_related/local_runner.py`
> 用法：`python3 local_runner.py <task_type> <task_json_path>`
> 任务类型: test_factor, group_returns, compare_factors, correlation_matrix, ic_decay, turnover_analysis
> **触发条件**: MCP 调用超时后的第二次重试，或操作预计耗时 >600s。

---

# 🧠 自进化记忆系统

## 两层记忆架构

| 层级 | 文件 | 范围 | 注入方式 | 写入权限 |
|------|------|------|---------|---------|
| **L1 全局教训** | `~/.claude/lessons.md` | 跨项目通用 | SessionStart hook 自动注入 (startup + compact) | 模型可写 |
| **L2 项目上下文** | `./memory/MEMORY.md` | 当前项目 | Claude Code 自动加载 | 模型可写 (追加) |

## 存储决策

当需要记住某件事时，先判断范围：

| 判断标准 | 写入位置 |
|---------|---------|
| 适用于**所有量化研究项目** (如"PE因子在金融股上失效") | `~/.claude/lessons.md` |
| 仅适用于**当前项目** (如"红利2号基准=18011") | 项目 `MEMORY.md` |

## 自我修正触发

以下任一条件满足时，**主动**追加一条教训到 `lessons.md`：
- 用户指出错误或纠正方向
- 同一个操作连续失败 2 次以上
- 用户说"记住这个"、"下次别这样"
- 回测/因子测试结果与预期严重不符，且找到了根因

写入格式：`## YYYY-MM-DD — 简短标题` + 场景/错误/根因/规则/标签。

## Rule Promotion

某条教训在 `lessons.md` 中被触发 ≥3 次后：
1. 在会话中提示用户："此教训已触发 N 次，是否提升到 CLAUDE.md 作为永久指令？"
2. 用户明确同意后 → 写入 CLAUDE.md
3. **CLAUDE.md 只有用户明确同意才能修改**

## compact 后记忆恢复

`settings.json` 中配置了 `matcher: "startup|compact"` 的 hook。
上下文压缩后，lessons-inject.sh 会重新运行，确保关键教训不会因为压缩而丢失。
