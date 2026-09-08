# PITFALLS — 部署坑库(SSH 连接 + 初次部署 + 增量部署/运维)

> 仅收录**部署过程**相关坑(SSH 连接/初次部署/增量部署/运维)。
> **代码开发过程中的坑不收录于此**(见项目 ATTENTION.md / 本地踩坑记录)。
> 规则: 遇到新坑并解决后, 立即回写本文件(症状→根因→方案→状态) +
> 项目 ATTENTION.md(只增不删), 并在对话中告知用户。
> 状态: ✅ 已修复已验证 / 🟡 已修复未验证 / 🔴 未修复

## 一、网络 / 连接

| # | 症状 | 根因 | 方案 | 状态 |
|---|------|------|------|:---:|
| N1 | 操作机 ping/22 不通目标机 | 两台设备不同网段(如 192.168.43.x 热点 vs 192.168.102.x 公司 Wi-Fi) | 操作机切目标机同一网络; 排查顺序: 网段→防火墙→sshd | ✅ |
| N2 | `Add-WindowsCapability` 报 0x80240438 / **0x8024401c**(HTTP 状态类变体) | 域环境 WU 端点不可达/异常(WSUS/组策略接管; 与 pip 联网不冲突) | 预检→路径: ①已预装? ②直接 GitHub 手动安装(OpenSSH-Win64.zip → 重命名 OpenSSH → install-sshd.ps1), 不试 dism(同端点必然失败) | ✅ |
| N3 | **跨网段但 TCP 通**: ping 100% 丢包(ICMP 被过滤), 但 `nc -z <IP> 22` 成功 | 公司网络跨 VLAN 有路由, 仅禁 ICMP | 以 **TCP 端口实测为准**(nc -z), 不以 ping 判断连通性; 预检直接 nc 22 | ✅ |
| N4 | 公用机网段与预演机不同(192.168.200.x 有线 vs 192.168.102.x Wi-Fi) | 接入方式不同 → 不同 VLAN | 部署前探测目标机实际 IP(ipconfig), 不要假设与预演同网段 | ✅ |
| N5 | **远程机反复断连**: ARP 有 MAC(在线)但 ping/SSH 超时, 屏幕黑 | **Windows 自动睡眠**(空闲 10-30min, 网络断开; 非 sshd 问题) | 先分两层: 睡眠(唤醒 + `powercfg /change standby-timeout-ac 0` + `hibernate-timeout-ac 0`) vs sshd 服务(Get-Service sshd); 长任务/远程操作前先设不休眠 | ✅ |
| N6 | **SSH 22 不通但 SMB 445 通 = 机器在线 + 服务问题**(2026-09-07): 重启后 sshd 未自启/服务注册丢失(S10), QueryServer 8543 也不通 | 重启后: sshd 服务可能停(或注册丢失), SYSTEM 计划任务 `/sc once` **不自动触发**(R11) | 判别法: 445 通 → 机器在线+路由通, 问题在服务层; 现场恢复(操作手册 阶段 5: 诊断→S10 重建→Start-Service→schtasks /run) | ✅ |

## 二、SSH / 远程执行

| # | 症状 | 根因 | 方案 | 状态 |
|---|------|------|------|:---:|
| S1 | SSH 断开后服务进程消失 | OpenSSH 会话终止清理子进程树 | SYSTEM 计划任务(`schtasks /ru SYSTEM`), 独立会话无密码 | ✅ |
| S2 | `ssh localhost` Connection refused | install-sshd.ps1 只注册服务不启动 | `Start-Service sshd` 后再验证 | ✅ |
| S3 | `ssh localhost` Permission denied | 无密码账户(仅面部/指纹/PIN)或密码错误 | 创建本地管理员账户专用 SSH(deployuser); 密码区分大小写 | ✅ |
| S4 | ssh/scp 非交互密码认证 | sshpass 不可用(Mac 无 brew) | expect 脚本包装: `expect { "password:" { send "<pwd>\r"; exp_continue } }`; 首次连接加 `-o StrictHostKeyChecking=no` | ✅ |
| S5 | SSH 会话 python 命令不存在 | deployuser PATH 无 python | 全路径调用(注意: 公用机 python 在 `C:\Users\<用户>\anaconda3\python.exe`, 非 D:\Ana_Py — 部署前必须探测实际路径) | ✅ |
| S6 | **expect 的 expect 块单行书写导致永久超时**: 密码提示后无任何输出, `expect -d` 显示整个块被当作单个字面模式 | Tcl 中 `{...}` 是字面量, `expect { "a" {b} "c" {d} eof }` 单行时整个串被解析为一个模式(变量也不展开) | **expect 块必须多行书写**(每模式一行), 或改用 base64 EncodedCommand 完全避开 expect 匹配内容 | ✅ |
| S7 | **expect 双引号内反斜杠被 Tcl 吃掉**: `-File C:\qs.ps1` 变 `-File C:qs.ps1` | Tcl 对 `\q` 等未知转义丢弃反斜杠 | expect 脚本内 Windows 路径写 `C:\\qs.ps1`; 或路径放 base64 内(EncodedCommand)彻底避开 | ✅ |
| S8 | **bash 单引号字符串内嵌 PowerShell 单引号被破坏**: `$py = '"C:\..."'` 传到目标机引号丢失 | bash 单引号内不能含单引号, 字符串被截断 | 远程命令一律用 base64 EncodedCommand(UTF-16LE), 或 ps1 脚本文件 scp 后 `-File` 执行, 不在 bash 里拼 PowerShell 引号 | ✅ |
| S9 | **PowerShell 中 `\"` 不是转义**: `$py = "\"C:\path\""` 报语法错误 | PowerShell 转义符是反引号 `, 非反斜杠 | PowerShell 内嵌双引号用单引号字符串 `'"C:\path"'` 或 `` `" `` | ✅ |
| S10 | **sshd 服务注册项丢失**: 文件在(C:\Windows\System32\OpenSSH\sshd.exe + sshd_config + host keys 全齐)但 `Get-Service sshd` 不存在(仅剩 ssh-agent) — 8-24 系统变动后发生 | 系统更新/还原导致服务注册丢失(非 OpenSSH 卸载, **勿重装**) | 管理员 PowerShell 重建(**必须标准服务模式, 不带 `-d`** — 调试模式注册是反复崩的根源, 见 S13): `sc.exe create sshd type= own start= auto binPath= "C:\Windows\System32\OpenSSH\sshd.exe"`(优先 `C:\Program Files\OpenSSH\sshd.exe` 完整安装版) → 确认 22 端口空闲 → `Start-Service sshd` → 按 **操作手册.md 阶段 1G 做 SSH 加固**(电源不休眠+失败重启) | ✅ |
| S11 | **前台 `sshd.exe -d` 调试模式 Connection reset**: 监听正常但客户端连接被 RST | 前台进程非 SYSTEM 身份 → `get_user_token - unable to generate user token ... as i am not running as system` → 无法认证任何用户(ga_init unable to resolve user) | **前台调试模式仅用于诊断**(打印认证全流程), 不可当服务用; 正式连接必须走服务模式(LocalSystem, 认证正常) | ✅ |
| S12 | **sshd 服务反复停止(退出码 1067)**: 启动后运行一段时间 STOPPED, 7034 事件 | 1067=服务特定错误; 常见: ① 22 端口被前台 sshd/其他进程占用(绑定失败) ② 偶发未复现; **连接/断开不会触发崩溃**(受控验证: 连接+断开后 RUNNING, 无新增 7034) | 排查链: sc query sshd(退出码) → System 事件 7034/7045 时间线 → 端口占用(netstat :22); 兜底: `sc.exe failure sshd reset= 86400 actions= restart/1000/restart/1000/restart/1000`(崩溃 1 秒自愈); 确认服务模式稳定后即可用 | ✅ |
| S13 | **sshd 以 `-d` 调试模式注册成服务 → 反复断连/重启后连接异常**(2026-08-27 测试机): 服务 RUNNING 但 SSH connect timeout; 部署机(同一 OpenSSH)从未崩过 | S10 早期修复命令用 `-d` 注册 — 调试模式(前台/诊断)注册成服务 = 行为不稳定根源; 部署机模板 = `C:\Program Files\OpenSSH\sshd.exe` 标准服务模式 + LocalSystem + AUTO_START + 交流电源永不睡眠 | **SSH 加固 = 照部署机模板三件套**(操作手册.md 阶段 1G, 可复制): ① 标准服务模式重建(不带 -d) ② `powercfg /change standby-timeout-ac 0` + `hibernate-timeout-ac 0`(防自动睡眠断连) ③ `sc.exe failure sshd ... actions= restart/1000/...`(失败 1 秒自愈); 新机部署/复用 Skill 时**先加固再长任务** | ✅ |

## 三、依赖 / 环境(目标机安装)

| # | 症状 | 根因 | 方案 | 状态 |
|---|------|------|------|:---:|
| D1 | 离线安装当场失败缺包 | 开发机 Anaconda 预装掩盖缺失 | 闭包自检: `pip install --dry-run --ignore-installed --platform win_amd64 --python-version 3.13 --only-binary=:all: --no-index --find-links=offline_packages ...` | ✅ |
| D2 | pydantic 导入失败 | pydantic_core 版本不匹配(须精确 2.46.4) | 用 `pip download <pkg>` 让 pip 解析正确版本 | ✅ |
| D3 | **探测不到目标机 Python**: 常见路径(D:\Ana_Py/C:\Python313/ProgramData\Anaconda3)全 False | 各机 python 安装位置不同(公用机在 `C:\Users\Zhang Ruixiao\anaconda3`) | 探测要覆盖: 注册表(HKLM/HKCU PythonCore) + `where python` + `C:\Users\*\anaconda3` + `C:\Program Files(x86)` + 全盘 `-Filter python.exe -Recurse -Depth 3`(conda 缓存 E:\test\pkgs 也可能有) | ✅ |
| D4 | 依赖在线安装只补缺包(anaconda 自带 duckdb/pandas 等) | 目标机预装环境版本不同(pandas 2.3.3 vs 开发机 3.0.3) | 安装后必须 `import` 验证全部关键包版本; executor 已做 NAType 兜底兼容 pandas 2/3 | ✅ |

## 四、服务运行(部署/运维)

| # | 症状 | 根因 | 方案 | 状态 |
|---|------|------|------|:---:|
| R1 | 启动后连接丢失/health degraded + 0 库 | GBK 控制台无法编码 `•`/`←` 等 print 崩溃 | 服务打印仅用 ASCII; `python -u` 无缓冲看日志 | ✅ |
| R2 | 服务日志无挂载输出 | stdout 块缓冲 | `python -u` 无缓冲; 排查以 server_err.log 为准 | ✅ |
| R3 | health degraded | 数据目录文件缺失/被占用 | 重启服务; 查 DUCKDB_DATA_DIRS 与文件 | ✅ |
| R4 | 查询全超时 | 慢查询/大表 | 调大 QUERY_TIMEOUT_MS 或限并发 | ✅ |
| R5 | 前端白屏 | static/ 不完整 | 重新拷贝前端产物(index.html + assets/) | ✅ |
| R6 | 部署后用户看到旧界面 | 浏览器缓存旧 index.html | 验证时 `?v=日期` 参数或 Ctrl+Shift+R | ✅ |
| R7 | setx 环境变量不生效 | setx 后当前窗口不更新 | 新开命令行窗口生效(分号分隔多目录) | ✅ |
| R8 | 升级部署丢用户/权限/审计 | 覆盖旧版本时 data/ 被替换 | 升级前备份 `data/users.db`, 部署后恢复 | ✅ |
| R9 | **schtasks 创建的任务不运行/找不到**: 用 `$action` 字符串拼命令时引号在多层传递中丢失 | bash/expect/PowerShell 三层引号转义 | 改用 `Register-ScheduledTask`(New-ScheduledTaskAction -Argument 单引号字符串)替代 schtasks /tr; 创建后立即 `schtasks /query /xml` 验证 `<Command>/<Arguments>` | ✅ |
| R10 | **admin 首启密码与实际不符**(文件写 Deploy@2026 但登录 1026 失败) | 首次启动发生在手动测试进程(环境变量上下文不同); 密码文件与库内哈希不一致 | 用项目自带 `security.py` 重置: `python -c "import sqlite3; from security import hash_password; ..."`(操作手册 3A 同款); 重置后立即登录验证 | ✅ |
| R11 | **机器重启后 QueryServer 8543 不通**: 计划任务存在但未运行 | 任务为 `/sc once /st 00:00` 形态, **重启后不自动触发**(SCHEDULER 只在指定时刻触发一次; SSH 会话断开场景靠 /run 手动, 重启场景无人 /run) | 现场 `schtasks /run /tn "QueryServer"`(操作手册 阶段 5); 根治: 触发器改 ONSTART(`schtasks /create ... /sc onstart`)或 Register-ScheduledTask -Trigger AtStartup, 重启自启 | ✅ |

## 五、增量部署 / 数据同步(运维)

| # | 症状 | 根因 | 方案 | 状态 |
|---|------|------|------|:---:|
| I1 | 增量表"均不可用" | PRAGMA table_info 返回 tuple, 字符串索引 TypeError | `r[1]` 索引取列名(代码侧已修, 配置核对时留意) | ✅ |
| I2 | 增量 merge 报错 | 本地表无 UNIQUE 约束, INSERT OR REPLACE 失败 | 两步法: DELETE pk 冲突 + INSERT | ✅ |
| I3 | 配置表名查询极慢(43 倍) | 引号小写 vs 实际大写表名 | duckdb_tables() 取真实表名执行 | ✅ |
| I4 | 同步工具读状态文件报错 | PowerShell 写文件带 BOM | utf-8-sig 容错读取 | ✅ |
| I5 | 大表导出阻塞所有请求 | 单 worker 事件循环被 COPY 占满 | 导出走 asyncio.to_thread + 独立只读连接 | ✅ |
| I6 | 同事下载到旧数据 | 服务器数据未更新(硬盘新/服务器旧) | 下载验收含"数据源版本"检查; 数据更新后再开放 | 🟡 |
| I7 | 数据目录残留副本/STAGING 表 | 历史误拷/中断任务 | 定期清理: 重复 .duckdb 副本 + QT_*_STAGING(数据在正式表) | 🟡 |
| I8 | 新增表无增量配置(只能全量) | download_config.json 未配时间列 | 新表配置: 时间列 XGRQ 优先, 其次 UPDATETIME/业务列; 无时间列只能全量 | ✅ |
| I9 | **数据目录多日期版本并存**(E:\0413/0609/0625 + D:\空目录) | 公用机历史备份/同步多次留存 | 部署前探测全部候选目录的 .duckdb 文件数与 LastWriteTime, 选最新完整版本; 空目录(有目录无 .duckdb)不可用 | ✅ |
| I10 | **同步工具报 "--local-dir required" 但用 --local-db**: 旧版脚本无 diff 模式参数 | 测试机/旧部署的 gildata_sync.py 早于 8-24 diff 功能(usage 无 --local-db) | 从开发机上传最新版 gildata_sync.py 覆盖(工具部署后代码演进需同步) | ✅ |
| I11 | **--local-db 提示"检测到多库, 需逐库指定"退出** | 脚本设计: local-db 模式匹配单库(服务器 15 库时无法推断文件对应库) | **配合 `--db <库名>` 指定**(过滤后单库即执行); 端到端已验证(6-18 旧库 → 8-24 增量 418 行, 行数/水位线与生产机完全一致) | ✅ |

## 六、权限 / 账号(部署/运维)

| # | 症状 | 根因 | 方案 | 状态 |
|---|------|------|------|:---:|
| P1 | 权限分类器拦截远程命令/批量脚本 | 对跨机/破坏性操作保守判定 | 用户切换模式(bypass); 高危操作逐项执行+用户确认, 不做批量盲执行 | ✅ |
| P2 | 登录提示"账号已锁定 15 分钟" | 连续登录失败触发锁定(安全机制) | 等锁定到期或管理员重置密码(自动清除锁定); 同事使用说明需提示 | ✅ |
| P3 | 普通用户看到管理后台 | 前端菜单未按权限隐藏 | 菜单+路由+后端三重隔离(已实测仅 admin 可见); 验证清单含此检查 | ✅ |
| P4 | 首启 admin 密码泄露风险 | admin_initial_password.txt 明文留存 | 首次登录后立即改密并删除该文件 | ✅ |

## 六B、SMB 共享(数据共享通道, 2026-08-24 新增)

| # | 症状 | 根因 | 方案 | 状态 |
|---|------|------|------|:---:|
| SB1 | SMB 挂载 Permission denied, 但 smbutil view 认证成功(能列共享) | **Windows UAC 远程限制**(LocalAccountTokenFilterPolicy 默认 0): 远程 SMB 会话的管理员令牌被过滤, **Administrators 组授权无效** | 共享权限 + NTFS **显式授权具体账号**(如 `Grant-SmbShareAccess -AccountName deployuser -AccessRight Read`), 不经 Administrators 组; Mac 挂载 URL 密码含 `@` 须转义 `%40` | ✅ |
| SB2 | Grant-SmbShareAccess 报"用户名与安全标识间无任何映射" | 账号名非本地账户(如 Microsoft 账户用户目录名 Zhang Ruixiao, 实际本地账户是 Wang Zw 等) | 先 `Get-LocalUser` 查真实本地账户名再授权 | ✅ |

## 七、验证方法论(Claude 操作阶段)

| # | 症状 | 根因 | 方案 | 状态 |
|---|------|------|------|:---:|
| V1 | 脚本判定 PASS 但操作未执行 | 以 UI 反馈为准误判 | **以审计日志落库为证据链** | ✅ |
| V2 | CDP evaluate 返回空/异常 | 表达式是函数定义未调用/{{}}转义 | IIFE `(() => {...})()`; json.dumps 传参 | ✅ |
| V3 | CDP location.href 后 evaluate 失败 | 跳转销毁执行上下文 | 分两步: 先跳转, 再 evaluate 操作 | ✅ |
| V4 | 确认框检测不到 | Element Plus MessageBox 是 .el-message-box 非 .el-dialog | 选择器同时匹配两者 | ✅ |
| V5 | Chrome MCP 操作漂移到别的标签 | 用户活跃标签重排 selected 状态 | 每次 evaluate 前 select_page + URL 守卫; 用户忙时改用 CDP 直连 | ✅ |
| V6 | 后台标签页弹窗"卡住" | 非活跃窗口动画被浏览器节流 | bringToFront 后操作 | ✅ |
| V7 | API 正常但部署验证 UI 不可用 | 前端独立层问题(拦截器/解包/过滤) | 部署验证必须走真实浏览器交互, 不依赖 API 通过 | ✅ |
| V8 | 验证环境截图保存失败 | Chrome MCP workspace roots 白名单 | macOS `screencapture -x` + vision_bridge 分析 | ✅ |

---

## 坑检查时机(铁律)

- **用户操作阶段**: 不检查坑(用户按操作手册执行, 出现问题用户会反馈)
- **Claude 操作阶段**: 每步执行遇到异常, **立即对照本坑库逐条匹配**——
  命中 → 按方案处理并继续; 未命中 → 排查根因 → 解决 → **立即回写**
  (本文件 + 项目 ATTENTION.md + 部署指南/05 三处同步) → 对话中告知用户
