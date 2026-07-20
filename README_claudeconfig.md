# claude-config

Claude Code 全局配置同步仓库。

## 项目定位

管理 Claude Code 的**全局层配置**——所有项目共用，Mac / Windows 双机同步。

```
~/claude-config/          ← 这个 Git 仓库（存配置源文件）
    ↓ 符号链接
~/.claude/                ← Claude Code 实际读取的位置
    ├── CLAUDE.md          → 链接到仓库
    ├── skills/            → 链接到仓库
    ├── commands/          → 链接到仓库
    ├── hooks/             → 链接到仓库
    ├── workflows/         → 链接到仓库
    ├── lessons.md         → 链接到仓库
    ├── settings.json      → 链接到仓库
    └── settings.local.json ← 不进仓库（每台机器独立）
```

### 两层体系

| 层 | 位置 | 作用范围 | 管理方式 |
|------|------|---------|---------|
| **全局层** | `~/.claude/` | 所有项目 | claude-config 仓库 |
| **项目层** | `<项目>/.claude/` | 单个项目 | 各项目的 Git 仓库 |

## 仓库地址

https://github.com/JoyingYourself/claude-config

## 新增配置 / 修改配置

### 改已有的（CLAUDE.md、skill、command 等）

正常编辑 `~/.claude/` 下的文件即可（符号链接自动写入仓库），然后：

```bash
cd ~/claude-config
git add -A
git commit -m "描述改动"
git push
```

另一台机器：

```bash
cd ~/claude-config && git pull    # 即刻生效，无需重启 Claude Code
```

### 新建 Skill

直接在 `~/.claude/skills/` 下创建目录和 SKILL.md（等于在仓库的 `skills/` 下创建），然后 commit + push。

注意：Skill 中不要写死平台路径（如 `/Users/xxx/`），用 `~` 或让 Claude 自行推断。

### 新增 MCP 权限

在仓库的 `settings.json` 中 `permissions.allow` 数组加条目，然后 commit + push。

MCP Server 的启动命令在各自机器的 `settings.local.json` 或项目 `.mcp.json` 中配置（不进仓库）。

### 新增 Hook 脚本

脚本文件放入仓库的 `hooks/` 目录。

Hook 的注册命令（settings.json 中的 hooks 字段）在各自机器的 `settings.local.json` 中配置（不进仓库）。

## 不进仓库的东西

- `settings.local.json` — 每台机器独立（hook 命令路径、MCP 启用列表）
- `history.jsonl` — 对话历史
- `sessions/`、`telemetry/`、`tasks/`、`plans/` — 运行时状态
- `plugins/` — 插件系统托管

## 敏感信息保护

- DeepSeek API Key 在 `settings.local.json` 的 `env` 块中，不进仓库
- `settings.json`（仓库中）不含任何 API 密钥或 Token
- 仓库设为 Private

## Windows 端部署

```bash
git clone git@github.com:JoyingYourself/claude-config.git ~/claude-config
cd ~/claude-config
bash setup.sh
```

然后手动配置 `settings.local.json`（hook 注册 + MCP 启用 + env），安装运行时依赖（Python / Ollama / claudectl，按需）。

## 回滚

setup.sh 部署前会自动备份原始文件到 `~/.claude/backups/<timestamp>/`。如需回滚：

```bash
# 删除符号链接，恢复备份
rm ~/.claude/CLAUDE.md
cp ~/.claude/backups/<timestamp>/CLAUDE.md ~/.claude/CLAUDE.md
# ... 其他文件同理
```
