---
name: EngineeringFrame_Audit
description: 框架/架构级代码审计 — 通过 Moor 网关的 CodeGraph_Gil 真 AST(tree-sitter 语义图)对整个项目做依赖拓扑/循环依赖/耦合(Ca/Ce/I)/分层违规/克隆检测,产出架构审计报告。触发词:架构审计、架构分析、依赖拓扑、循环依赖、耦合分析、分层违规、frame audit、架构体检。
---

# /EngineeringFrame_Audit — 框架级架构审计

## 角色定位

对**整个项目**做架构级审计:借助 Moor 网关后的 **CodeGraph_Gil 真 AST**(tree-sitter 语义图 + SQLite 图存储)分析模块划分、依赖拓扑、循环依赖、耦合度(Ca/Ce/I 不稳定度)、分层违规、克隆/重复、未用导出与热点,产出可执行的架构审计报告。

它补上 `EngineeringCoding_Audit`(单文件对抗式审计)缺失的"架构广度 + 语义级依赖分析"那一层:**Coding 审单文件的逻辑/边界正确性,Frame 审整个项目的结构健康**。

## 路由

**主用(真 AST,经 Moor 网关)** — CodeGraph_Gil MCP,以下工具经 Moor 暴露(命名空间 `mcp__moor__codegraph_gil__...`,首次运行按当前会话实际可用名调用):

| 工具 | 用途 |
|------|------|
| `index_project` | 扫描并建/刷新项目语义图(→ 被审项目 `.codegraph-skills/codegraph/index.db`) |
| `diagnose_graph` | 索引健康检查(文件数/符号数/provider/框架路由) |
| `analyze_architecture` | 架构总览:模块、依赖边界、循环、耦合、框架面、top 风险 |
| `audit_workspace` | 未用导出、维护热点、克隆分组 |
| `trace_paths` | 沿 calls/imports/type 边追踪,定位分层违规 |
| `find_references` / `find_implementations` / `inspect_symbol` | 符号级下钻、爆炸半径 |
| `api_impact` | 路由/接口/契约影响面 |

**回退(CodeGraph_Gil 不可用/未索引/语言不支持时)** — 内置 `Read / Grep / Glob / Bash`(grep 构建 import 图、DFS 查环),**并在报告首行显式标注"未使用 AST,降级为文本分析"**。

> CodeGraph_Gil 经 Moor 合规注册(server=`CodeGraph_Gil`,经 `conda run -n node24` 隔离,不碰 base node),配置规范见 `EngineeringMCP_Scaffold`。支持语言:JS/TS/Python/C#/PHP。

## 输入格式

用户直接调用,可带**目标项目根路径**(默认当前工作目录)。无上游 Skill 数据输入。
调用示例:`/EngineeringFrame_Audit /path/to/project`,或在项目目录内直接 `/EngineeringFrame_Audit`。

---

## 交互协议

### Step 1: 前置检查(preflight)

1. 确认目标项目路径(默认 cwd),确认是可识别代码库(有 `package.json`/`pyproject.toml`/`go.mod`/`*.csproj` 等清单)。
2. **确认 CodeGraph_Gil 工具经 Moor 可用**:在当前会话可用工具里定位 CodeGraph_Gil 的 `analyze_architecture` 等(名字形如 `mcp__moor__codegraph_gil__analyze_architecture`,以实际为准)。
   - 找不到 → 走回退路线,并在最终报告首行标注 `⚠️ 架构分析降级:CodeGraph_Gil 不可达`。
3. 项目主语言不在 CodeGraph_Gil 支持范围(JS/TS/Python/C#/PHP)→ 提示用户,走回退。

### Step 2: 建立语义图(必须先索引)

1. 调 `index_project(path=项目根)`,默认 honoring Git excludes,含 precise/framework overlays。
2. 调 `diagnose_graph(path)` 确认索引健康:文件数、符号数、**provider 状态**、框架路由。
   - 符号数为 0 或明显异常 → 报告索引失败原因,**不硬凑架构结论**。
   - **provider 显示 `unavailable`(如 Python 的 `precise_py` / `scip-python` / `basedpyright`)→ 先调 `install_graph_providers(mode="install")` 补装,再 `index_project` 重新索引让 provider 生效。**
3. **禁止跳过索引直接分析** —— 未索引的 `analyze_architecture` 无意义。
4. **指标降级声明**:若补装 provider 后 `analyze_architecture` 的模块耦合/不稳定度仍为 `?`(实测:Python 项目即使装了 scip-python,缺 basedpyright 时 Ca/Ce/I 仍不可得),**必须在报告中声明"模块耦合指标不可用"**,转而依据 `audit_workspace`(克隆/未用/热点,这些在纯 tree-sitter 层即可得)+ `trace_paths`(文件级依赖)给结论,**不得输出臆造的耦合数字**。

### Step 3: 架构总览

调 `analyze_architecture(path, verbosity="full")`,提取并解读:
- **模块划分**与依赖边界
- **循环依赖**(cycles):逐个列出环路成员 + file 位置
- **耦合指标**(coupling):Ca(传入)/Ce(传出)/I=Ce/(Ca+Ce) 不稳定度;标记"高传入 + 高不稳定"的危险模块
- **框架面**(routes/DI/中间件等)
- **top 风险**热点

> CodeGraph_Gil 的循环/耦合是**工作区-模块级**;单包仓库可能塌缩为一个模块 → 此时退到 `trace_paths` 做符号/文件级依赖分析,不输出误导性"零循环"。

### Step 4: 违规下钻(按需)

对总览暴露的高风险项:
- **分层违规**:`trace_paths(path_kind="imports")` 验证是否有"下层反向依赖上层"(如 domain→infrastructure、entity→controller)。
- **重复/克隆 + 未用导出**:`audit_workspace(verbosity="full")`。
- **接口契约**:改动敏感路由前 `api_impact`。
- **具体符号爆炸半径**:`inspect_symbol` / `find_references`。
每条发现必须带 **file:line**(来自工具返回),禁止无证据断言。

### Step 5: 产出架构审计报告

写 `ARCHITECTURE_AUDIT.md`(被审项目根,或用户指定目录),结构:
1. **执行摘要**(≤10 条,按架构风险排序)+ **首行标注是否使用了 AST**
2. **架构心智模型**(模块图/分层意图;若与 README 矛盾 → 本身作为一条发现)
3. **依赖拓扑**:模块依赖摘要 + 循环依赖清单(带成员 file:line)
4. **耦合与稳定度**:Ca/Ce/I 表,危险模块标注
5. **分层违规**:违规依赖边 + 证据
6. **重复/未用/热点**:克隆组、未用导出、维护热点
7. **修复建议**(分优先级,标注 effort/风险)+ 一节 **"看着像问题其实没问题"**(反浅层:列出考虑过但判定无需改的项)
8. **衔接建议**:列出 top-N 高风险文件,建议交给 `EngineeringCoding_Audit` 做单文件对抗深审

每条发现标严重度(🔴 CRITICAL / 🟠 HIGH / 🟡 MEDIUM / 🟢 LOW),带 file:line。

---

## 与其他 Skill 的勾稽关系

| 上游/下游 | Skill | 数据流 |
|-----------|-------|--------|
| 下游 | `EngineeringCoding_Audit` | Frame 审出的 top-N 高风险文件 → 交给 Coding 做单文件 4-agent 对抗证伪(架构定位 → 代码深审) |
| 同级 | `EngineeringCoding_Audit` | 边界:Frame = 整个项目架构/依赖拓扑;Coding = 单文件逻辑/边界正确性。互补不重叠 |
| 依赖 | `EngineeringMCP_Scaffold` | 依赖 CodeGraph_Gil MCP 经 Moor 合规注册(server=CodeGraph_Gil,conda run node24)。MCP 掉线时本 Skill 走 grep 回退 |

## 禁止行为

- ❌ **不索引就分析**:必须先 `index_project` + `diagnose_graph`,未索引的架构结论无效
- ❌ **修改被审项目源码**:只读审计,唯一产出是 `ARCHITECTURE_AUDIT.md`
- ❌ **凭空断言架构问题**:每条发现必须有工具返回的 file:line 或明确证据,禁止"我觉得耦合高"
- ❌ **降级不声明**:CodeGraph_Gil 不可用而走 grep 时,必须在报告首行标注"未使用 AST",不得假装用了真 AST
- ❌ **把 `.codegraph-skills/` 当产物或提交 git**:它是可重建缓存,提醒用户加入 `.gitignore`
- ❌ **单包仓库硬套模块级指标**:cycles/coupling 塌缩为一个模块时退到符号/文件级,不输出误导性"零循环"
- ❌ **绕过 Moor 直连 CodeGraph_Gil**:必须经 Moor 网关调用(命名空间 `mcp__moor__`),遵守 MCP 注册规范
