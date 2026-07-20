---
name: EngineeringMCP_Scaffold
description: >
  MCP Server 配置操作指南 — 当创建新 MCP、迁移 MCP、MCP 连不上、或修改 MCP 配置时使用。
  触发词：新建MCP、添加MCP、MCP配置、MCP迁移、MCP连不上、Moor配置。
metadata:
  version: "2.0.0"
  category: engineering
compatibility: Claude Code + Moor MCP Gateway
---

# MCP Server 配置操作指南

## Iron Rules（违反将导致 MCP 不可用）

1. **所有 MCP Server 必须通过 Moor 网关管理。** Claude Code 只连 Moor 一个端点。禁止绕过 Moor 在 `~/.mcp.json` 中直连 MCP。

2. **创建/修改 MCP 后必须执行完整注册流程。** 只写代码不注册 = MCP 不可用。

3. **每次操作前必须先读取最新指南。** 配置流程可能更新，Read 以下文件获取最新版本：

   ```
   /Users/junye_shi/AgentFiles/ClaudeCode-MCP_related/README.md
   ```

4. **Moor 写入前必须关闭 Moor。** SQLite 直写时 Moor 必须处于关闭状态。运行时写入不会被引擎接管。

## 强制流程

### Step 0: 读取操作指南（不可跳过）

```
Read /Users/junye_shi/AgentFiles/ClaudeCode-MCP_related/README.md
```

### Step 1: 按 README.md 中的脚本执行注册

1. 创建 MCP 代码 → 放入 `ClaudeCode-MCP_related/<ServerName>/`
2. 关闭 Moor → 运行注册脚本 → 重启 Moor
3. 验证 `SELECT name, status FROM mcp_servers` 显示 `running`

### Step 2: 完成检查清单

- [ ] `~/.mcp.json` 仅包含 Moor 网关
- [ ] `~/.claude/.mcp.json` 为空
- [ ] 新 MCP 源码在统一目录下
- [ ] Moor 中 Server 状态为 `running`
- [ ] 所有 Profile 已添加并启用
- [ ] 网关 `tools/list` 验证通过
