---
name: DepartmentServer_Deploy
description: "部门数据查询服务器(DuckDB_QueryServer)全生命周期管理: ①部署(经 SSH 直连 Windows 目标机自动执行完整部署: 传输/安装/配置/启动/验证); ②远程配置变更(日常修改: 代码/配置/前端→传输→重启→验证→记录配置变更表)。含互动式配置流程与内嵌坑库(PITFALLS.md), 新坑解决后立即回写。触发词: 部署服务器、SSH 部署、服务器上线、部署 DuckDB、远程配置、配置变更、远程修改、修改服务器配置、改服务器代码、更新服务器前端。"
---

# 部门服务器部署与远程配置 (DepartmentServer_Deploy)

## 定位

管理 DuckDB_QueryServer 数据查询平台在 Windows 目标机(部门公用外网机或测试机)的
**全生命周期**: 部署上线 + 部署后的一切远程配置变更。**互动式配置**: Skill 内嵌
核心流程与坑库(PITFALLS.md), 遇到已见过的坑直接回复解决方案, 新坑解决后立即回写。

- 阶段一 **部署**: 从零把平台装到目标机
- 阶段二 **远程配置变更**: 日常修改 → 传输 → 重启 → 验证 → 记录
- ⚠️ 新表引入的"功能扩充"(字典/增量配置/模板)是特殊需求, 按 README「项目后续方向」
  清单执行, 不入本 Skill 通用流程

## 文件结构

```
~/.claude/skills/DepartmentServer_Deploy/
├── SKILL.md       本文件: 互动式流程(自包含, 可独立执行)
└── PITFALLS.md    坑库: 症状→根因→方案→状态(7 类 37 条, 只增不删)

项目工作区 部门服务器部署/ (= 中邮资管/中邮金市/部门服务器部署/)
├── CLAUDE.md      项目执行原则(文档维护铁律)
├── README.md      项目信息 + 配置变更记录表(#1~10) + 项目后续方向
├── HANDOFF.md     上下文交接
├── ATTENTION.md   踩坑记录(只增不删, 与 PITFALLS.md 双向同步)
├── 操作手册.md    用户手动操作清单(SSH 开通等, 可复制执行)
├── 部署指南/01~05 详细参考(细节回退查; 核心流程已内嵌本 Skill)
└── offline_packages/ 53 wheel 离线依赖
```

源项目代码: `中邮资管/中邮金市/2026/DuckDB_QueryServer/`(git 维护)

---

## 互动式配置协议(每次任务开始执行)

```
1. 读 CLAUDE.md → README.md → ATTENTION.md + PITFALLS.md(恢复上下文, 防重蹈覆辙)
2. 预检(收集环境事实, 不做无效试错):
   - 操作机网段: ipconfig getifaddr en0(须与目标机同网段, 否则告知用户切网络)
   - 目标机连通: nc -z <IP> 22
   - SSH 通道状态: 已建/需用户按操作手册开通
   - **三机预检(常规, 自动执行)**: 测试机 192.168.102.109(deployuser) + 生产机 192.168.200.3(deployuser/Deploy@2026)
     → nc -z 各机 22 + 服务 health(http://<IP>:8543/api/v1/health);
     新功能/配置变更默认先上测试机验证, 再上生产机(三机流转)
3. 问用户一次性信息(如缺失): 目标机 IP / SSH 账户 / 密码 / 数据目录路径
4. 按"预检结论→确定路径"执行(不是逐条试错)
5. 每步执行后验证; 全部完成后文档回填(铁律)
```

---

# 阶段一: 部署

### 第 1 步: 连通与信息

- 预检网段/SSH(见交互协议); 用户一次性提供: IP / 账户 / 密码 / 数据目录
- SSH 未开通 → 按 操作手册.md 阶段 1 的预检→路径分支(见 PITFALLS N2/S2/S3):
  ① 是否已预装 `Get-WindowsCapability -Online -Name OpenSSH.Server*` → Installed 则启动
  ② 域环境 0x80240438 → GitHub 手动安装(OpenSSH-Win64.zip → 重命名 OpenSSH → install-sshd.ps1)
  ③ 无密码账户 → 创建本地管理员 deployuser 专用 SSH
  ④ 验证 `ssh localhost`

### 第 2 步: 传输代码

```bash
# 打包(排除运行时; 数据目录不传; 旧版本先备份 data/users.db)
cd <源项目父目录> && tar --exclude='data' --exclude='__pycache__' --exclude='.git' \
  --exclude='frontend' --exclude='node_modules' --exclude='.claude' \
  --exclude='.hex-skills' --exclude='.codegraph-skills' \
  --exclude='admin_initial_password.txt' -czf /tmp/queryserver_deploy.tar.gz DuckDB_QueryServer/
# expect 包装 scp(密码认证) → 目标机 C:\ → tar 解压
```

### 第 3 步: 安装依赖(在线优先)

```bash
# 全路径 python(SSH 会话 PATH 无 python, PITFALLS S5)
cd C:\DuckDB_QueryServer && D:\Ana_Py\python.exe -m pip install -r requirements.txt
# 离线: pip install --no-index --find-links=offline_packages ...
# 离线包变更后先闭包自检(PITFALLS D1): pip install --dry-run --ignore-installed \
#   --platform win_amd64 --python-version 3.13 --only-binary=:all: --no-index \
#   --find-links=offline_packages duckdb pandas ... 
```

### 第 4 步: 配置数据目录

- 与 config.py 默认 `D:\Gildata_*` 一致 → 跳过
- 不一致 → `setx DUCKDB_DATA_DIRS "路径1;路径2"`(分号分隔; setx 后须新开窗口)
- 无数据目录 → 跳过(服务可启动, health=degraded, 仅界面/认证可用)

### 第 5 步: 启动服务(持久后台)

⚠️ SSH 会话杀子进程(PITFALLS S1) → SYSTEM 计划任务:

```powershell
$action = 'cmd /c cd /d C:\DuckDB_QueryServer && D:\Ana_Py\python.exe -u -m uvicorn api_server:app --host 0.0.0.0 --port 8543 > C:\DuckDB_QueryServer\server.log 2>&1'
schtasks /create /tn "QueryServer" /tr "`"$action`"" /sc once /st 00:00 /ru SYSTEM /f
schtasks /run /tn "QueryServer"
```

防火墙(限局域网段): `New-NetFirewallRule -Name qs8543 ... -LocalPort 8543 -RemoteAddress 10.0.0.0/8,172.16.0.0/12,192.168.0.0/16`

### 第 6 步: 验证(8 项 + 浏览器级, 铁律)

**A. API 8 项**(快速通道):
1. `curl http://<IP>:8543/api/v1/health` → healthy + databases_attached ≥ 2
2. 前端登录页 HTTP 200 3. admin 登录(首启密码在 admin_initial_password.txt, 登录后改密删文件)
4. 注册→审批→授权→登录→查询 5. 未授权表 3012 拒绝 6. 代码映射/字典可用
7. 审计落库 8. SYSTEM 任务运行中(进程持久)

**B. 浏览器级验证(Chrome MCP, 必做 — API 通过 ≠ UI 可用)**
> 铁律来源: ATTENTION #14(API 正常但 4 个前端功能失效)/#22(控件级排查 5 假象)/
> 2026-08-24 正式部署实战(API 8 项全过但菜单缺"数据下载" = static/ 8-19 旧产物未重建)。

必验清单(逐项真实交互, 非仅页面打开):
| # | 验证项 | 方式 |
|---|--------|------|
| B1 | admin 登录 → 跳转首页 | fill_form 真实输入 + 原生 click |
| B2 | 菜单按权限渲染 | DOM 查询 `.el-menu-item`(admin 应含全部功能+管理后台) |
| B3 | 快捷查询: 模板列表渲染 + **真实执行一个模板**(无参数模板最快, 如交易日历) | 打开查询弹窗 → 原生 click 执行 → 结果表行数/列 |
| B4 | 高级 SQL: **真实输入 SQL + 执行** → 结果行数与 API 一致 | fill textarea(注意: 无预填, placeholder 非 value) → 执行 |
| B5 | 表浏览器: 选库选表 → 列信息 + 数据预览 | 下拉选择 + 结果确认 |
| B6 | 表浏览器搜索过滤(如输入 secu → 下拉只剩 secumain) | fill 搜索框 + 下拉选项断言 |
| B7 | 数据下载页渲染(14 库 + 全量按钮) | 菜单进入 + 表格行数 |
| B8 | 权限视图隔离: 普通用户登录 → 菜单仅授权模块(无管理后台) | 切换账号登录 + 菜单断言 |
| B9 | 模板按表权限过滤(无表授权用户 → 模板列表为空) | 普通用户看快捷查询页 |

方法要点(坑库 V5/V6/S6 + #22):
- 每次操作前 select_page + URL 守卫(标签漂移)
- 弹窗内按钮用**原生 click(uid)**, JS click 对 el-dialog 内按钮无效
- 先读源码确认触发方式(@input vs 按钮 vs 回车), 避免误判
- 用户浏览器忙 → 独立 Chrome + CDP 直连(9333)
- 证据: 审计日志落库 + a11y 快照; 逐项 ✅/❌(FUNCTION_AUDIT 风格)
- 危险操作(全量下载/删除/禁用)只验证到按钮可点+确认框, 不实际执行

**前端产物检查(2026-08-24 新增)**: 部署前确认源项目 static/ 与 frontend/src 同步
(`grep "数据下载" static/assets/*.js` 有命中 + 最新页面 hash), 否则前端修复未进产物。

---

# 阶段二: 远程配置变更

统一走 **改 → 传 → 启 → 验 → 记**。

### 场景识别

| 变更类型 | 传输方式 | 重启 | 验证重点 |
|---------|---------|:---:|---------|
| 后端代码(.py) | tar 全量 / scp 单文件 | ✅ SYSTEM 任务重启 | API + 审计落库 |
| 前端(static) | npm build → scp 覆盖 | ❌ 即改即生效 | 浏览器 + ?v= 绕过缓存 |
| 配置文件(JSON/env) | scp 单文件 | ✅ | API + 页面 |
| 数据字典 JSON | scp | ✅(有缓存则清) | 字典页搜索/详情 |
| 环境变量 | setx | ✅ | health/挂载 |

### 通用流程

1. **改**: 源项目 git 仓库; 每完成一个逻辑改动 `git commit` 做回退点; 一改一验
2. **传**: expect 包装 scp(密码认证)
3. **启**: `schtasks /end /tn "QueryServer"; schtasks /run /tn "QueryServer"` + health 确认
4. **验**: 双通道自适应(见下); 后端状态以**审计日志落库**为准(PITFALLS V1)
5. **记**: README 配置变更记录表追加一行; 对话中告知"已更新三份文档"

### 验证双通道(自适应)

| 通道 | 适用 | 要点 |
|------|------|------|
| Chrome MCP | 用户浏览器空闲 | select_page 后立即操作; URL 守卫; dialog 内原生 click(uid) |
| CDP 直连 | 用户浏览器忙 | 独立 Chrome `--user-data-dir=/tmp/chrome_audit_profile --remote-debugging-port=9333 --remote-allow-origins=*`; python websocket; 指定 targetId 无漂移 |
| API/curl | 后端状态/审计 | curl + jq; 审计日志核对 |

CDP 要点(PITFALLS V2/V3/V4): 表达式 IIFE; location.href 分两步; message-box JS click 优先。

### 回滚

后端=git 历史重传重启; 前端=旧 static 备份/重 build; 配置=改前备份原文件。

---

## 坑检查时机与回写规则(铁律)

**坑检查时机**:
- **用户操作阶段**: 不检查坑(用户按操作手册执行, 出现问题用户会反馈)
- **Claude 操作阶段**: 每步执行遇到异常, **立即对照 PITFALLS.md 逐条匹配**——
  命中 → 按方案处理并继续; 未命中 → 排查根因 → 解决 → 回写

**新坑回写(解决后立即, 三处同步)**:
1. **PITFALLS.md**(本 Skill 坑库): 追加一行(症状→根因→方案→状态), 分类归类
2. **项目 ATTENTION.md**(部门服务器部署/): 新增条目(只增不删, 状态三档)
3. **部署指南/05 故障排查.md**: 相关章节补一行(现象/原因/处置)

并在对话中明确告知用户"已回写坑库"。
**范围**: PITFALLS.md 只收部署过程坑(SSH 连接/初次部署/增量部署/运维);
代码开发坑不收录(见项目 ATTENTION.md / 本地踩坑记录)。

## 关键实现技巧(实战沉淀)

| 场景 | 方案 |
|------|------|
| ssh/scp 密码认证非交互 | expect 脚本包装 |
| PowerShell 引号地狱 | powershell -EncodedCommand <base64(UTF-16LE)> |
| 服务日志无挂载输出 | python -u 无缓冲 |
| GBK 控制台打印崩溃 | print 仅 ASCII(PITFALLS R1) |
| 权限分类器拦截 | 用户切换 bypass; 高危逐项确认(PITFALLS P1) |
| 用户浏览器被占用 | 独立 Chrome + CDP 直连(9333) |
| 浏览器缓存旧前端 | ?v= 参数(PITFALLS F1) |
| 登录失败锁定 | 等到期或重置密码清除(PITFALLS P2) |

## 约束

- 用户配合最小化: 一次性初始配置, 不在对话中逐步指挥
- 数据标识符(IP/路径/代码)查证不凭记忆
- 修改落盘数据源前查下游消费者; 一改一验
- 交付前对照原始需求逐条核对
- 高危操作(账号/权限/删除)逐项执行+用户确认, 不做批量盲执行
- 新表扩充(字典/增量配置/模板)按 README「项目后续方向」清单, 不属于常规流程
- **部署指南与 Skill 双向同步**: 部署指南有细节变更 → 同步内嵌流程; Skill 新增流程/坑 → 同步部署指南
