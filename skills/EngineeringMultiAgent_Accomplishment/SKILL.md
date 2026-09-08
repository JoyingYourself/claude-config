---
name: EngineeringMultiAgent_Accomplishment
description: 多Agent并行任务通用模板 — 基于 CrewAI 框架动态拆解任务、分配角色、编排执行。触发词：多Agent、multiagent、并行Agent、多角色协作、CrewAI、Agent流水线
---

# /EngineeringMultiAgent_Accomplishment — 多Agent并行任务通用模板

## 角色定位

本 Skill 封装 CrewAI 多 Agent 编排框架，作为**通用化多 Agent 任务执行模板**。用户只需描述任务目标，Skill 自动完成：任务拆解 → Agent 角色定义 → 工具分配 → 串行/层级编排 → 执行监控 → 结果汇总。

不预置任何场景模板，不限定 Agent 数量或角色——一切由任务描述驱动，LLM 动态决策。

## 路由

- **CrewAI 框架**：`/Users/junye_shi/AgentFiles/MultiAgent/CrewAI/`（本地仓库，pip install -e 安装）
- **LLM**：DeepSeek API（OpenAI 兼容端点 `https://api.deepseek.com`，模型 `deepseek-chat`）。注意：CrewAI 使用 OpenAI SDK，不能走 Anthropic 兼容端点
- **MCP 工具**：所有已注册 MCP 工具均可用（backtest_Gil / factor_Gil / data_Gil / report_Gil / chinapostamc_* / chrome_devtools 等）——Agent 通过 Skill 层桥接调用，不直接持有
- **API Key**：从环境变量 `DEEPSEEK_API_KEY` 读取，Skill 执行时注入脚本进程

## 输入格式

用户通过自然语言触发，无需结构化输入：

```
/multiagent <任务描述>
```

示例：
- `/multiagent 分析过去5年A股价值因子的有效性，输出回测报告`
- `/multiagent 扫描GitHub上本周最火的3个量化开源项目，逐个分析架构并对比`
- `/multiagent 对当前项目做全面的代码审计，包括安全、性能、可维护性三个维度`

---

## 交互协议

### Step 1：任务拆解（Claude Code 侧）

收到用户任务描述后，执行以下分析（不生成代码，仅产出拆解方案供内部使用）：

1. **理解任务**：用一句话复述任务目标，确认理解正确
2. **拆解子任务**：将任务分解为 2-5 个独立或依赖的子任务，每个子任务需明确：
   - 做什么（一句话）
   - 需要什么工具/MCP（从所有可用 MCP 中匹配）
   - 产出什么（结构化描述）
   - 是否关键路径（critical: true/false）
3. **设计 Agent 角色**：为每个子任务设计 Agent 的 role/goal/backstory
4. **判断 Process**：
   - 子任务间强依赖（A 产出 → B 消费 → C 汇总）→ sequential
   - 3+ 子任务需要动态协调（Manager 分配）→ hierarchical
5. **判断 Memory**：
   - 是否跨 session 迭代型任务（如"长期因子研究"）？→ 启用 Memory
   - 一次性任务 → 关闭

### Step 2：生成并执行 CrewAI 脚本

根据 Step 1 的拆解方案，动态生成一个 Python 脚本，包含：

1. **Agent 定义**：每个 Agent 绑定 role/goal/backstory，不绑定工具（`tools=[]`）
2. **Task 定义**：每个 Task 绑定 description/expected_output/agent，通过 `context` 建立依赖链
3. **Crew 配置**：
   - `process=Process.sequential` 或 `Process.hierarchical`
   - `memory=True/False`
   - `verbose=True`（始终开启，便于调试）
   - `max_rpm=60`（DeepSeek 限流保护）
4. **LLM 配置**：
   ```python
   LLM(
       model="deepseek-chat",
       base_url="https://api.deepseek.com",
       api_key=os.environ["DEEPSEEK_API_KEY"],
       temperature=0.1,
   )
   ```
5. **资源限制**：
   - 单 Task 最大重试 5 次
   - 单 Task 超时 20 分钟（`timeout=1200`）
   - 总超时 60 分钟

**执行方式**：
```bash
DEEPSEEK_API_KEY="$API_KEY" python3 /tmp/crewai_task_<uuid>.py
```
Claude Code 通过 Bash 工具后台执行，轮询等待完成。超时或失败时读取 checkpoint 日志。

### Step 3：MCP 工具桥接（中间结果处理）

CrewAI Agent 不直接持有 MCP 工具。当 Agent 的 Task 产出包含工具需求时，Claude Code 侧解析并执行：

1. **识别工具需求**：检查 Task 的 `CrewOutput.raw` 中是否包含 `<tool_request>` 标记块：
   ```json
   {
     "tool": "mcp__moor__backtest_gil__run_pipeline",
     "params": { "config": "{...}" },
     "reason": "执行价值因子回测"
   }
   ```
2. **执行 MCP 调用**：Claude Code 直接调用对应的 MCP 工具
3. **注入结果**：将 MCP 返回结果格式化，作为下一 Task 的 `context` 注入。Task 的 prompt 中追加：
   ```
   --- 工具执行结果（run_pipeline）---
   {精简的 MCP 返回}
   --- 请基于以上结果继续 ---
   ```

**注意**：若 Agent 以自然语言描述工具需求（非 JSON 格式），Claude Code 侧需自行识别语义并匹配 MCP 工具。JSON 格式为首选，自然语言为回退。

### Step 4：结果汇总与呈现

CrewAI 执行完成后：

1. 检查 `CrewOutput` 的最终结果
2. 若有 `output_file` 配置，读取并呈现文件内容或路径
3. 若执行失败（全部重试耗尽）：
   - 列出已完成 Task 的产出
   - 列出失败 Task 的错误诊断
   - 提示 checkpoint 位置（`~/.crewai/checkpoints/`）
   - 询问用户下一步操作（从 checkpoint 恢复 / 修改参数重试 / 放弃）
4. 成功时：汇总关键发现，标注执行统计（Task 数、工具调用次数、耗时、token 消耗）

---

## 与其他 Skill 的勾稽关系

| 上游/下游 | Skill | 数据流 |
|-----------|-------|--------|
| 下游 | 所有 MCP 工具（backtest_Gil / factor_Gil / data_Gil / report_Gil / chinapostamc_* 等） | 本 Skill 通过桥接层调用 MCP 工具，将结果注入 Agent 执行流 |
| 同级 | `EngineeringCoding_Audit` | 当任务描述含"审计/审查"时，可委托给 Audit Skill 进行对抗式审查 |
| 同级 | `EngineeringFrame_Audit` | 当任务描述含"架构分析"时，可委托给 Frame Audit Skill |

> 本 Skill 是执行层的通用入口，根据任务内容按需路由到具体 MCP 工具或其他 Skill。

## 禁止行为

- ❌ 预置固定的 Agent 数量或角色模板——必须从任务描述动态生成
- ❌ 限制可用的 MCP 工具范围——所有已注册 MCP 工具均可被 Agent 请求
- ❌ 在 Agent 的 Python 脚本中硬编码 API key——必须从环境变量读取
- ❌ 单 Task 失败后立即放弃——必须重试 5 次后再判断
- ❌ 跳过任务拆解步骤直接生成脚本——必须先拆解、用户确认后再执行
- ❌ MCP 调用失败时静默吞下错误——必须将完整错误信息注入 Agent context
- ❌ checkpoint 丢失时不做提示——执行失败必须告知用户 checkpoint 位置和恢复方式
