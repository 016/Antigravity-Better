# 未文档化 API 逆向探测方法论

> **版本**: v1.0
> **日期**: 2026-02-17
> **适用范围**: 任何闭源应用的 API 发现与文档化
> **前置条件**: 无需源码、无需官方文档
> **案例来源**: 本方法论从 Cascade AI Chat Panel 逆向实践中提炼而来（详见 `cascade-interception-devguide.md`）

---

## 目录

1. [引言与适用范围](#1-引言与适用范围)
2. [核心原则](#2-核心原则)
3. [总流程图](#3-总流程图)
4. [Phase 0: 目标侦察](#4-phase-0-目标侦察)
5. [Phase 1: 标准接口检查](#5-phase-1-标准接口检查)
6. [Phase 2: 通道发现](#6-phase-2-通道发现)
7. [Phase 3: 流量拦截](#7-phase-3-流量拦截)
8. [Phase 4: 协议解码](#8-phase-4-协议解码)
9. [Phase 5: 内部状态访问](#9-phase-5-内部状态访问)
10. [Phase 6: 生产化封装](#10-phase-6-生产化封装)
11. [横切关注点](#11-横切关注点)
12. [经验教训](#12-经验教训)
13. [附录 A: 目标环境档案模板](#13-附录-a-目标环境档案模板)
14. [附录 B: 端点清单模板](#14-附录-b-端点清单模板)
15. [附录 C: API 表面模板](#15-附录-c-api-表面模板)
16. [附录 D: 探测决策记录模板](#16-附录-d-探测决策记录模板)
17. [附录 E: 全流程检查单](#17-附录-e-全流程检查单)

---

## 1. 引言与适用范围

### 1.1 本文档是什么

一套系统化的操作手册（Playbook），用于在**没有官方 API 文档**的情况下，发现、理解并文档化闭源应用的内部接口。

### 1.2 本文档不是什么

- 不是攻击指南或漏洞利用手册
- 不是绕过付费/授权的方法
- 所有技术仅用于合法的集成开发、扩展开发、互操作性研究

### 1.3 适用目标类型

| 目标类型 | 典型场景 | 覆盖程度 |
|:--|:--|:--|
| 浏览器 / Electron 应用 | VS Code 扩展、Electron IDE、SPA、iframe 嵌入页 | 完整（详见 `electron-webview-probing-methodology.md`） |
| 桌面原生应用 | Windows/macOS/Linux 原生应用（Qt, .NET, Cocoa, GTK） | 完整 |
| 移动端应用 | iOS/Android 原生或混合应用 | 完整 |
| CLI 工具 | 命令行工具、守护进程 | 完整 |
| 服务端服务 | 无文档的内部 API、微服务 | 完整（仅网络层） |
| 硬件/固件 | 嵌入式设备、IoT | 部分（仅网络层） |

### 1.4 目标读者

需要为闭源软件构建集成、扩展、Bridge 或自动化工具的开发者。

---

## 2. 核心原则

| # | 原则 | 说明 |
|:--|:--|:--|
| 1 | **递进式排除** | 从最标准/最简单的机制开始，逐层深入。每层的结果决定下一层的方向。不要跳级。 |
| 2 | **最小侵入** | 每一步只做最小验证。保留所有被替换的原始引用。永远不破坏目标的正常运行。 |
| 3 | **结构匹配优于名称匹配** | 在混淆/压缩环境中，匹配数据结构和行为签名，而非变量名或函数名。这是版本韧性的基础。 |
| 4 | **探测与生产分离** | 探测阶段可以用广撒网式的 monkey-patching/hooking。生产阶段只保留最稳定的单一路径。 |
| 5 | **边探测边记录** | 每个发现立即记录。维护一份持续更新的日志：尝试了什么、发现了什么、排除了什么。 |
| 6 | **合法与可逆** | 所有探测必须非破坏性且可逆。遵守所在司法管辖区的法律框架。 |

---

## 3. 总流程图

```
Phase 0: 目标侦察 (Reconnaissance)
  │  确定目标类型、运行环境、注入/观察可行性
  ▼
Phase 1: 标准接口检查 (Standard Interface Check)
  │  目标有公开/标准 API 吗？
  ├─ 有 → 使用标准 API，按需跳到 Phase 5 增强
  └─ 没有 →
  ▼
Phase 2: 通道发现 (Channel Discovery)
  │  扫描目标暴露的通信通道、配置、全局状态
  ▼
Phase 3: 流量拦截 (Traffic Interception)
  │  安装拦截器，捕获实际通信数据
  ▼
Phase 4: 协议解码 (Protocol Decoding)
  │  解析请求/响应编码，建立端点-功能映射
  ▼
Phase 5: 内部状态访问 (Internal State Access)
  │  绕过通信层，直接读写目标内部数据结构
  ▼
Phase 6: 生产化封装 (Production Bridge)
     封装稳定 API，添加缓存/容错/降级
```

**重要说明**：

- 不是所有目标都需要完整 7 个阶段。REST JSON API 可能在 Phase 4 结束。深度 UI 集成才需要 Phase 5-6。
- 每个阶段都可能发现足够信息而提前结束，也可能需要回退到前一阶段重新探测。
- 每个阶段结束时应填写对应的附录模板，形成完整文档。

---

## 4. Phase 0: 目标侦察

### 4.1 目标

确定目标是什么、运行在哪里、有哪些观察和注入途径。

### 4.2 目标分类决策树

```
目标运行在浏览器中？
  ├─ 是 → 浏览器环境 (SPA / iframe / Web Worker)
  │        是 Electron 应用？
  │        ├─ 是 → Electron（额外：IPC、Node.js 上下文、CDP）
  │        └─ 否 → 纯浏览器
  └─ 否 → 非浏览器
           桌面原生应用？
           ├─ 是 → Desktop Native (Windows/macOS/Linux)
           └─ 否 → 移动端应用？
                    ├─ 是 → Mobile (iOS/Android)
                    └─ 否 → CLI / 服务端？
                             ├─ CLI → CLI 环境
                             └─ Server → 仅网络层观察
```

### 4.3 各环境信息收集清单

#### Browser / Electron

| 信息项 | 如何获取 |
|:--|:--|
| iframe 还是顶层页面？同源还是跨域？ | `window.parent === window`，`parent.location.origin` |
| 页面协议 | `location.protocol`（http / https / file / vscode-file / chrome-extension） |
| Electron 版本、Node.js 集成状态 | `process.versions.electron`，`typeof require` |
| DevTools / CDP 可用？ | `--remote-debugging-port` 启动参数 |
| Content Security Policy | 检查 HTTP 响应头或 `<meta>` 标签 |
| 前端框架 | DOM 属性扫描（`__reactContainer$`、`__vue__`、`ng-version`） |

#### Desktop Native

| 信息项 | 如何获取 |
|:--|:--|
| 操作系统与架构 | `uname -a` / System Information |
| 编程语言 / 框架 | `file` 命令、`ldd` / `otool -L` / Dependency Walker |
| 动态库清单 | `ldd binary`（Linux）、`otool -L binary`（macOS）、Dependency Walker（Windows） |
| 进程隔离模型 | `ps aux`、进程树 |
| IPC 机制 | `lsof -U`（Unix socket）、`pipelist.exe`（Named pipe） |

#### Mobile

| 信息项 | 如何获取 |
|:--|:--|
| iOS 还是 Android？原生还是混合？ | App 包结构分析 |
| Root / Jailbreak 可用？ | 设备状态检查 |
| 应用签名与完整性检查 | 运行时检测绕过测试 |
| 网络安全配置（Certificate Pinning, ATS） | `AndroidManifest.xml` / `Info.plist` |

#### CLI

| 信息项 | 如何获取 |
|:--|:--|
| 实现语言 | `file` 命令、`strings` 输出分析 |
| 配置文件位置 | `strace -e openat`（Linux）、`fs_usage`（macOS） |
| 网络通信 | `ss -tlnp`、`netstat`、`lsof -i` |
| 环境变量依赖 | `strings binary | grep -i env`，逐一测试 |

#### Server-side

| 信息项 | 如何获取 |
|:--|:--|
| TLS 使用情况 | 连接测试、证书检查 |
| 可否 MITM | mitmproxy 代理测试 |
| 客户端 SDK 可用 | 搜索官方/非官方 SDK |

### 4.4 产出物

- **目标环境档案**（填写附录 A 模板）
- 可行观察/注入途径清单
- 风险评估

### 4.5 进入下一阶段的条件

- 目标类型已分类
- 至少确认一条观察途径
- 完成合法性与伦理审查

---

## 5. Phase 1: 标准接口检查

### 5.1 目标

在开始逆向之前，先检查目标是否提供了任何已文档化、标准或半文档化的 API。如果有，直接使用。

### 5.2 各环境标准 API 清单

| 环境 | API | 检查方法 |
|:--|:--|:--|
| VS Code Webview | `acquireVsCodeApi` | `typeof window.acquireVsCodeApi` |
| VS Code 主页面 | `window.vscode.ipcRenderer` | `typeof window.vscode?.ipcRenderer` |
| Electron 渲染进程 | `require('electron')` | `typeof require` |
| Chrome Extension | `chrome.runtime` | `typeof chrome?.runtime?.sendMessage` |
| Browser (通用) | `window.opener` | `typeof window.opener?.postMessage` |
| Android | Intent、Content Provider | `adb shell dumpsys activity` |
| iOS | URL Scheme、Universal Links | `Info.plist` 检查 |
| Windows | COM 接口、Named Pipe | 注册表、`oleview.exe` |
| macOS | XPC、AppleScript | `sdef`、`launchctl` |
| CLI | `--help`、`--version`、man page | 直接调用 |
| Server | OpenAPI / Swagger | `/.well-known/`、`/api-docs`、`/swagger.json` |

### 5.3 API 探测通用模式

核心思路：**用包装函数替换目标 API 入口，观察是否有调用**。

```
1. 保存原始函数引用 → orig = target.apiFunction
2. 替换为探测版本 → target.apiFunction = function(...) {
     记录调用栈、参数、返回值
     return orig.apply(this, arguments)
   }
3. 设置超时检查 → 如果一段时间内未被调用，尝试主动调用
4. 分析结果 → API 存在且可用？部分可用？不存在？
```

这个模式可以适配到各种环境：
- **Browser**: 直接替换 `window` 上的函数
- **Desktop (Linux)**: `LD_PRELOAD` 替换动态库函数
- **Desktop (macOS)**: `DYLD_INSERT_LIBRARIES`
- **Desktop (Windows)**: DLL injection + Detours / MinHook
- **Mobile**: Frida 替换目标方法

### 5.4 决策分支

```
标准 API 存在且功能完整？
  ├─ 是 → 直接使用，记录 API 表面，按需进入 Phase 5 增强
  ├─ 部分可用 → 记录可用部分，继续 Phase 2 发现缺失部分
  └─ 不存在 → 进入 Phase 2
```

### 5.5 产出物

- 标准 API 可用性报告
- 如果找到：API 表面文档初稿

---

## 6. Phase 2: 通道发现

### 6.1 目标

在没有标准 API 的情况下，发现目标实际使用的通信通道。扫描配置、全局状态、消息传递机制。

### 6.2 Browser / Electron 技术目录

| 技术 | 发现内容 | 适用场景 |
|:--|:--|:--|
| Window 属性扫描 | 配置对象、Token、自定义 API（如 `chatParams`） | 所有 Web 目标 |
| 配置对象解码 | Base64/JSON/URL 编码的认证信息、服务器地址 | 发现可疑全局变量后 |
| postMessage 拦截 | iframe/窗口间的消息通信 | 存在 iframe 或 popup 时 |
| 前端框架属性扫描 | React Fiber suffix、Vue 实例、Angular DI | 确认前端框架后 |
| Storage 检查 | localStorage、sessionStorage、IndexedDB、Cookie | 所有 Web 目标 |
| Service Worker 检查 | 缓存策略、push 订阅、fetch 拦截 | PWA 类应用 |

> 详细代码实现请参考 `electron-webview-probing-methodology.md` Phase 2。

### 6.3 Desktop Native 技术目录

| 技术 | 发现内容 | 工具 |
|:--|:--|:--|
| 文件句柄枚举 | 正在访问的配置文件、日志、数据库 | `lsof`（Linux/macOS）、`handle.exe`（Windows） |
| 注册表检查（Windows） | 配置、COM 注册、近期路径 | `regedit`、`reg query` |
| 环境变量转储 | 通过环境变量传递的配置 | `env`、`printenv`、Process Explorer |
| Named Pipe / Unix Socket 扫描 | IPC 通道 | `lsof -U`、`ls /tmp/*.sock`、`pipelist.exe` |
| 共享内存检查 | 进程间共享状态 | `ipcs`、`/dev/shm/` |
| 动态库导出分析 | 可用函数接口 | `nm`、`objdump`、`otool -L`、Dependency Walker |
| 字符串提取 | 嵌入的 URL、API Key、格式字符串、错误消息 | `strings` 命令 |

### 6.4 Mobile 技术目录

| 技术 | 发现内容 | 工具 |
|:--|:--|:--|
| App Manifest 分析 | 组件声明、权限、Intent Filter | `aapt dump`（Android）、`Info.plist`（iOS） |
| 类/方法转储 | 可用类及其方法 | `class-dump`（iOS）、`jadx`（Android） |
| SharedPreferences / UserDefaults | 配置值、Token、Feature Flag | 文件系统访问（需 Root/Jailbreak） |
| URL Scheme 探测 | Deep Link 处理器 | `adb shell am start`、`xcrun simctl openurl` |
| 广播/通知监控 | 内部事件总线 | `adb shell dumpsys activity broadcasts` |
| Keychain / Keystore 检查 | 存储的凭证 | Frida 脚本、`security`（macOS） |

### 6.5 CLI / Server 技术目录

| 技术 | 发现内容 | 工具 |
|:--|:--|:--|
| 配置文件发现 | 配置格式与选项 | `strace -e openat`、`fs_usage`（macOS） |
| 环境变量探测 | 接受的环境变量 | 逐一设置变量，观察行为变化 |
| 端口/Socket 监听 | 工具启动的网络服务 | `ss -tlnp`、`netstat`、`lsof -i` |
| DNS/HTTP 观察 | 联系的外部服务 | `tcpdump`、Wireshark、`dnsmon` |

### 6.6 通道发现决策树

```
发现了配置/认证数据？
  ├─ 是 → 记录服务器地址、Token、数据格式 → Phase 3
  └─ 否 → 继续扫描其他通道类型

发现了消息传递通道？
  ├─ 是，且携带业务数据 → 这可能是主通道 → Phase 3
  ├─ 是，但仅框架/系统消息 → 非主通道，继续搜索
  └─ 否 → 通道可能是网络级的 → Phase 3

发现了前端框架？
  ├─ 是 → 记录框架类型，为 Phase 5 做准备
  └─ 否 → Phase 5 可能需要内存/调试器方式
```

### 6.7 产出物

- 通道清单（存在哪些通道、哪些携带业务数据）
- 解码后的配置数据
- 认证信息清单
- 框架识别报告

---

## 7. Phase 3: 流量拦截

### 7.1 目标

在所有已发现的通信通道上同时安装拦截器。触发目标的关键操作。观察哪些通道承载实际业务数据。

### 7.2 Browser / Electron: Monkey-Patching

三层同时拦截：

| 层 | 目标 | 关键要点 |
|:--|:--|:--|
| fetch | HTTP/HTTPS 请求（包括 gRPC-Web） | `resp.clone()` 后再读取 body，不影响原始流 |
| XMLHttpRequest | 传统 AJAX 请求 | 需要同时 patch `open` 和 `send` |
| WebSocket | 持久化双向通信 | **必须保持原型链**：`WebSocket.prototype = OrigWS.prototype` |

> 完整 JavaScript 代码模板请参考 `electron-webview-probing-methodology.md` Phase 3 和 `cascade-interception-devguide.md` 第 5-6 节。

### 7.3 Desktop Native: 系统级 Hook

| 技术 | 操作系统 | 工具 | 捕获内容 |
|:--|:--|:--|:--|
| strace / ltrace | Linux | `strace -e network -p PID` | 所有网络相关系统调用 |
| dtrace / dtruss | macOS | `sudo dtruss -p PID` | 所有系统调用 |
| API Monitor | Windows | API Monitor 工具 | Win32 API 调用 |
| Detours / MinHook | Windows | DLL 注入 | 指定函数 Hook |
| LD_PRELOAD | Linux | 自定义 .so | 指定 libc 函数替换 |
| DYLD_INSERT_LIBRARIES | macOS | 自定义 .dylib | 指定函数替换 |
| 调试器断点 | 全平台 | gdb / lldb / x64dbg | 任意函数入口/出口 |

### 7.4 Mobile: 运行时 Hook

| 技术 | 平台 | 工具 | 捕获内容 |
|:--|:--|:--|:--|
| Frida 函数 Hook | 双平台 | Frida | 任意函数调用 + 参数 + 返回值 |
| mitmproxy / Charles | 双平台 | 代理工具 | 全部 HTTP/HTTPS 流量 |
| Objection | 双平台 | Objection（Frida 封装） | 常见模式的快速 Hook |
| Xposed Framework | Android | Xposed / LSPosed | Java 方法 Hook |
| Cydia Substrate | iOS (越狱) | Substrate | Objective-C 方法 Hook |

### 7.5 Network 层: 协议捕获

| 技术 | 捕获内容 | 工具 | 适用场景 |
|:--|:--|:--|:--|
| Wireshark | 完整数据包 + 协议解析 | Wireshark | 需要协议级细节 |
| tcpdump | 原始数据包 | tcpdump | 无 GUI 环境 |
| mitmproxy | HTTP/HTTPS（TLS 终结） | mitmproxy | 需要解密 HTTPS |
| ngrep | 网络流量中的模式匹配 | ngrep | 快速 grep 实时流量 |
| Fiddler | HTTP/HTTPS（Windows） | Fiddler | Windows 优先的工作流 |

### 7.6 协议识别指纹表

| 观察到的特征 | 协议 | 下一步 |
|:--|:--|:--|
| `application/grpc-web+proto` + 二进制 body | gRPC-Web | Phase 4: Protobuf 解码 |
| `application/json` | REST/JSON | Phase 4: JSON 解析 |
| `application/graphql` 或 body 包含 `query {` | GraphQL | Phase 4: Query 分析 |
| `text/event-stream` | SSE | Phase 4: 事件流解析 |
| WebSocket + JSON `{"type":"..."}` | 自定义 WS 协议 | Phase 4: 消息格式分析 |
| WebSocket + 二进制 | 自定义二进制 / Protobuf over WS | Phase 4: 二进制解码 |
| `application/x-protobuf` | gRPC (原生) | Phase 4: Protobuf 解码 |
| `application/msgpack` | MessagePack | Phase 4: MsgPack 解码 |
| Raw TCP + TLS | 自定义 TLS 协议 | Phase 4: TLS MITM + 模式分析 |
| Raw TCP 无 TLS | 自定义明文协议 | Phase 4: 直接模式分析 |
| Unix Socket / Named Pipe | 本地 IPC | Phase 4: 捕获并分析格式 |

### 7.7 关键注意事项

1. **保留原始引用**：Browser 中保存 `origFetch`；Native 中保存原始函数指针
2. **不消费目标需要的数据**：Browser 中用 `resp.clone()`；Native 中不修改传输中的 buffer
3. **流式响应可能显示 Content-Length=0**：gRPC、SSE、chunked transfer 都是如此
4. **二进制 body 不能直接转字符串**：需要用 ArrayBuffer / Uint8Array 处理
5. **异步时序**：拦截器日志可能滞后于实际 UI 变化

### 7.8 产出物

- 流量日志（原始捕获）
- 通信通道确认（哪些通道承载业务数据）
- 初步端点清单
- 协议指纹识别结果

---

## 8. Phase 4: 协议解码

### 8.1 目标

解析拦截到的请求/响应内容。构建完整的端点→功能映射表。

### 8.2 按协议选择解码策略

| 协议 | 解码策略 | 关键工具 |
|:--|:--|:--|
| JSON / REST | `JSON.parse` 直接解析 | Browser DevTools、jq |
| gRPC-Web / Protobuf（无 .proto） | 字符串提取 + UUID 提取 | 自定义 `extractStrings()` |
| gRPC-Web / Protobuf（有 .proto） | 完整 Protobuf 反序列化 | `protoc`、`grpcurl`、`buf` |
| GraphQL | 解析 query/mutation 结构 | Introspection query（如果启用） |
| MessagePack | MsgPack 解码器 | `msgpack-lite`、Python `msgpack` |
| 自定义二进制 | 模式识别、字段边界检测 | Hex Editor、自定义脚本 |
| XML / SOAP | XML 解析器 | `xmllint`、SOAP UI |

### 8.3 无 Schema 二进制解码技巧

当没有 .proto 或其他 Schema 文件时，可用以下技巧：

| 技巧 | 方法 | 适用场景 |
|:--|:--|:--|
| ASCII 字符串提取 | 扫描连续 3+ 个可打印字符（字节值 32-126） | 几乎所有二进制协议 |
| 模式匹配 | 用正则提取 UUID、URL、Email、时间戳 | 包含结构化标识符的协议 |
| 字段边界检测 | 不可打印字节作为天然分隔符 | Protobuf 等 TLV 格式 |
| 长度前缀检测 | Varint（Protobuf）、4 字节长度（自定义） | 有长度前缀的协议 |
| 差异分析 | 发送两个相似请求，比较二进制差异 | 需要定位特定字段时 |

**案例**：Cascade 探测中的 `extractStrings()` 和 `extractUUIDs()` 函数就是用技巧 1+2 从 Protobuf 二进制数据中提取出会话 ID 和消息文本。详见 `cascade-interception-devguide.md` 第 6 节。

### 8.4 端点功能映射方法

1. **单操作触发**：每次只执行目标的一个用户操作
2. **记录调用**：观察该操作触发了哪些端点调用
3. **标注端点**：为每个端点记录触发动作、请求参数、响应格式、是否流式
4. **调用序列图**：绘制复合操作的调用顺序

通用调用模式示例：

```
用户发送消息:
  → SendMessage (POST, body 含消息文本 + 会话 ID)
  ← 流式响应: AI 回复内容分块传输

用户切换上下文:
  → UpdateState (POST, body 含新上下文 ID)
  ← 确认响应
  → StreamUpdates (POST, body 含上下文 ID)
  ← 流式: 上下文历史内容

页面加载:
  → GetUserStatus
  → GetProfile
  → ListResources
  → StreamReactiveUpdates (长连接)
```

### 8.5 产出物

- **完整端点清单**（填写附录 B 模板）
- 协议规范文档
- 关键操作的调用序列图
- 解码后的数据样本

---

## 9. Phase 5: 内部状态访问

### 9.1 目标

绕过通信层，直接访问目标的内部数据结构，获得最稳定的读写能力。

### 9.2 适用性判断

```
能注入代码或附加调试器？
  ├─ 能 → 继续本阶段
  └─ 不能 → 留在 Phase 4 网络级 API，跳到 Phase 6

目标内部结构足够稳定？
  ├─ 是 → 构建直接状态访问
  └─ 否 → 优先使用 Phase 4 网络 API（跨版本更稳定）
```

### 9.3 Browser / Electron: 框架内部结构

#### React Fiber (React 16+)

| 步骤 | 技术 | 注意事项 |
|:--|:--|:--|
| 找到 Fiber Root | `element['__reactContainer$' + suffix]` | suffix 是运行时随机字符串，必须动态扫描 |
| 发现 suffix | 遍历 DOM 元素的 `Object.keys()`，匹配 `__reactContainer$` 前缀 | 每次页面刷新都变 |
| 遍历 Fiber 树 | BFS：`fiber.child` → `fiber.sibling` | 用 `WeakSet` 防止循环 |
| 定位 Context Provider | 检查 `fiber.memoizedProps.value` 的结构 | **用 shape matching，不用组件名** |
| 读取 hooks 状态 | 遍历 `fiber.memoizedState → .next` 链 | 状态链顺序可能变化 |

#### Vue 2/3

| 步骤 | Vue 2 | Vue 3 |
|:--|:--|:--|
| 找到实例 | `element.__vue__` | `element.__vue_app__` 或 `__vue_*` |
| 访问数据 | `instance.$data`、`instance.$props` | `instance.setupState`、`instance.props` |
| 访问 Store | `instance.$store`（Vuex） | `instance.appContext.config.globalProperties.$store` |

#### Angular

- `ng.getComponent(element)` 通过 debug 工具
- Dependency Injection 容器可遍历获取 Service 实例

> 详细代码请参考 `electron-webview-probing-methodology.md` Phase 5 和 `cascade-interception-devguide.md` 第 7 节。

### 9.4 Desktop Native: 调试器与内存访问

| 技术 | 用途 | 工具 |
|:--|:--|:--|
| 调试器附加 | 设断点、检查变量 | gdb、lldb、x64dbg、WinDbg |
| 内存扫描 | 在进程内存中查找特定值 | Cheat Engine、scanmem |
| DLL 注入 + Hook | 拦截内部函数调用 | Detours、MinHook、frida-gum |
| 逆向工程 | 理解代码流程（无源码） | IDA Pro、Ghidra、Binary Ninja |
| 符号分析 | 查找函数名（如果有符号） | `nm`、`objdump`、`dumpbin` |

### 9.5 Mobile: 运行时操纵

| 技术 | 平台 | 工具 |
|:--|:--|:--|
| Frida Runtime Hook | 双平台 | Frida |
| ObjC Runtime 反射 | iOS | `class-dump`、Frida ObjC Bridge |
| Java/ART 反射 | Android | Frida Java Bridge、Xposed |
| Swift Metadata 访问 | iOS | Frida Swift Bridge |
| SQLite 数据库检查 | 双平台 | Root/Jailbreak 后直接文件访问 |

### 9.6 Shape Matching 通用设计原则

**核心原则：匹配行为签名，不匹配标签。**

| 环境 | 不可靠标识 | 可靠标识 |
|:--|:--|:--|
| Browser（压缩后） | 组件名（`k3r`） | Props 结构（`Array.isArray(props.items)`） |
| Browser（压缩后） | CSS 类名（`.a3f`） | DOM 结构、`data-*` 属性 |
| Desktop（strip 后） | 函数名（mangled） | 函数签名（参数数量、返回类型） |
| Mobile（混淆后） | 类名（`a.b.c`） | 方法签名、字段类型 |
| Network | 端点路径（可能变） | 请求/响应结构、JSON 字段名 |

**稳定性排序**（从高到低）：

1. 数据结构 / 结构签名
2. 行为签名（做什么，而非叫什么）
3. 语义标识符（业务逻辑字段名）
4. 框架注入标识符（DOM 属性、运行时元数据）
5. 源码级标识符（函数名/类名/变量名）← 最不可靠

### 9.7 产出物

- **内部 API 表面文档**（填写附录 C 模板）
- 状态访问代码/脚本
- 组件/对象发现报告

---

## 10. Phase 6: 生产化封装

### 10.1 目标

将探测成果转化为稳定、可维护的集成 API。移除所有探测专用代码。

### 10.2 Bridge 设计要素

| 要素 | 说明 |
|:--|:--|
| 私有状态 + 缓存 | 维护 `_lastKnownGood` 缓存，带 TTL |
| 就绪检测 | Polling 或 MutationObserver，等待目标就绪 |
| 重试机制 | 指数退避，适应不同加载速度 |
| 干净的公共 API | 暴露最小必要接口，隐藏内部实现 |
| 失败降级 | 无法访问时返回缓存数据，附带降级标记 |

### 10.3 容错设计清单

| 失败场景 | 策略 |
|:--|:--|
| 目标未就绪（框架未挂载、服务未启动） | Polling + 指数退避 |
| 目标组件未渲染 / 进程暂停 | 返回缓存的 last-known-good 数据 |
| 内部结构变化（版本更新） | Shape matching 松弛 + 降级通知 |
| 运行时标识符变化（Fiber suffix、内存布局） | 每次访问前重新扫描 |
| 并发访问冲突 | Lock/Queue 串行化关键操作 |
| 缓存过期 | TTL 机制 + 主动失效 |
| 网络端点变化 | 降级到内部状态访问（反之亦然） |
| Bridge 完全失败 | 优雅降级 + 用户通知 |

### 10.4 探测代码清理原则

```
生产环境中移除:
  ✗ 所有广撒网式拦截（fetch/XHR/WS monkey-patching、strace、Frida 探测脚本）
  ✗ 所有调试面板和 verbose 日志
  ✗ 所有 window/内存扫描代码

生产环境中保留:
  ✓ 有针对性的内部状态访问（Fiber 遍历、特定 Hook）
  ✓ Bridge API 及干净接口
  ✓ 缓存 + 错误处理 + 降级逻辑
  ✓ 配置解码（如运行时需要）
```

### 10.5 版本韧性策略

1. **永远不硬编码构建时或运行时生成的标识符**（压缩后的名称、随机 suffix、内存地址）
2. **使用结构/行为匹配**（见 Phase 5.6）
3. **支持多种数据格式**（如同时处理 `ms.summaries` 和直接 UUID-keyed map）
4. **特征检测而非版本检测**（检查能力是否存在，不检查版本号）
5. **自动化回归测试**（新版本发布时自动运行探测脚本检测兼容性）

### 10.6 产出物

- 生产 Bridge 代码
- Bridge 消费者 API 文档
- 健康监控/告警机制
- 回归测试套件

---

## 11. 横切关注点

### 11.1 伦理与法律

- **服务条款**：检查逆向工程是否违反 ToS。在很多司法管辖区，ToS 不能覆盖互操作性逆向工程的法定权利
- **法律框架**：
  - 美国：DMCA Section 1201 豁免（互操作性用途）
  - 欧盟：Computer Programs Directive Article 6（互操作性例外）
  - 中国：根据《计算机软件保护条例》相关规定
- **负责任披露**：如果在探测过程中发现安全漏洞，应负责任地向厂商披露
- **范围限制**：只探测需要的部分。不窃取用户数据。不探测不属于你的生产系统
- **非破坏性原则**：所有探测必须可逆，永远不永久修改目标

### 11.2 可逆性

| 环境 | 如何确保可逆 |
|:--|:--|
| Browser | 保存 `origFetch`、`origXHR`、`OrigWS`，可随时还原 |
| Desktop | 使用非持久化 Hook（可卸载的 DLL 注入） |
| Mobile | Frida 脚本分离后干净恢复 |
| Network | 代理拦截移除后透明恢复 |

### 11.3 缓存与降级

- 在每一层缓存 last-known-good 结果
- 定义与数据波动性匹配的 TTL
- 级联降级：内部状态 → 网络 API → 缓存数据 → 带解释的错误
- 永远不静默失败

### 11.4 边探测边记录

- 维护探测日志：做了什么、发现了什么、排除了什么、时间戳
- 全程使用附录模板（A-D）
- 截图/录制关键发现
- 探测脚本提交版本控制，每阶段一个 commit，描述清楚

---

## 12. 经验教训

### 12.1 常见陷阱与对策

| 陷阱 | 根本原因 | 解决方案 |
|:--|:--|:--|
| 压缩/混淆的标识符每次构建都变 | 构建工具重命名符号 | 使用结构/行为匹配 |
| 内部数据格式跨版本变化 | 持续开发、重构 | 同时支持多种格式，使用宽松匹配 |
| 目标组件不总是存在 | 条件渲染、懒加载、进程生命周期 | 缓存 last-known-good，轮询可用性 |
| 缓存破坏式刷新导致集成失败 | 框架丢失对注入/修改对象的引用 | 使用正确的刷新机制（完整 reload） |
| 全局对象访问被模块作用域阻止 | 现代打包器创建隔离闭包 | `Object.defineProperty`、框架内部 API、调试器访问 |
| 流式响应显示空 body | 流式协议设 Content-Length=0 | 用流读取器（`clone().arrayBuffer()`、ReadableStream API） |
| 运行时标识符每次会话都变 | 框架的防冲突设计 | 每次访问前动态发现 |
| 构造函数替换后原型链断裂 | JavaScript 原型语义 | 显式恢复 `.prototype` 和静态属性 |

### 12.2 技术选型决策矩阵

| 方案 | 最适合 | 风险等级 | 稳定性 |
|:--|:--|:--|:--|
| 标准 API | 有可用标准接口时 | 低 | 高 |
| 网络拦截（只读） | 观察行为、协议分析 | 低 | 中 |
| 网络拦截（修改） | 测试、Fuzzing | 中 | 中 |
| 框架内部访问（React Fiber 等） | UI 应用的深度集成 | 中 | 中（依赖版本） |
| 运行时 Hook（Frida、DLL 注入） | 移动端、桌面原生 | 中高 | 低（OS/App 更新敏感） |
| 内存操纵 | 最后手段，无其他途径时 | 高 | 低 |

### 12.3 探测与生产的分界线

| 属性 | 探测阶段 | 生产阶段 |
|:--|:--|:--|
| 拦截范围 | 广撒网（所有 fetch/XHR/WS） | 精确制导（特定状态访问） |
| 日志 | 详细，含原始数据 | 最小化，仅错误 |
| 代码存活时间 | 临时，用完即删 | 长期维护 |
| 容错要求 | 低（手动观察即可） | 高（自动缓存 + 降级） |
| 对目标的影响 | 可能有性能开销 | 零可感知影响 |

---

## 13. 附录 A: 目标环境档案模板

```markdown
## 目标环境档案

| 字段 | 值 |
|:--|:--|
| 目标名称 | |
| 目标类型 | [ ] Browser/Electron [ ] Desktop Native [ ] Mobile [ ] CLI [ ] Server |
| 操作系统/平台 | |
| 框架/运行时 | |
| 注入途径 | |
| 标准 API 可用 | [ ] 是 [ ] 否 [ ] 部分 |
| 可行观察途径 | |
| 法律审查状态 | |
| 日期 | |
| 分析人 | |
```

---

## 14. 附录 B: 端点清单模板

```markdown
## 端点清单

| # | 端点 | 方法 | 功能 | 请求格式 | 响应格式 | 流式 | 需认证 | 备注 |
|:--|:--|:--|:--|:--|:--|:--|:--|:--|
| 1 | | | | | | | | |
| 2 | | | | | | | | |
```

---

## 15. 附录 C: API 表面模板

```markdown
## API 表面文档

### 内部状态访问点

| # | 访问路径 | 数据类型 | 读/写 | 稳定性 | 备注 |
|:--|:--|:--|:--|:--|:--|
| 1 | | | | | |

### 可用函数/方法

| # | 函数 | 参数 | 返回值 | 副作用 | 备注 |
|:--|:--|:--|:--|:--|:--|
| 1 | | | | | |
```

---

## 16. 附录 D: 探测决策记录模板

```markdown
## 探测决策记录

| 阶段 | 日期 | 尝试内容 | 结果 | 决策 | 下一步 |
|:--|:--|:--|:--|:--|:--|
| Phase 0 | | | | | |
| Phase 1 | | | | | |
| Phase 2 | | | | | |
| Phase 3 | | | | | |
| Phase 4 | | | | | |
| Phase 5 | | | | | |
| Phase 6 | | | | | |
```

---

## 17. 附录 E: 全流程检查单

```
Phase 0: 目标侦察
  □ 确认目标类型 (Browser / Desktop / Mobile / CLI / Server)
  □ 确认运行环境 (OS、框架、协议)
  □ 确认注入/观察可行性
  □ 完成法律与伦理审查
  □ 填写目标环境档案 (附录 A)

Phase 1: 标准接口检查
  □ 检查所有已知标准 API
  □ 尝试文档化接口
  □ 记录结果与决策

Phase 2: 通道发现
  □ 扫描全局对象/属性/配置
  □ 拦截消息通道
  □ 识别前端框架/运行时
  □ 解码发现的配置数据
  □ 记录认证信息和服务器地址

Phase 3: 流量拦截
  □ 安装所有适用拦截器
  □ 触发目标关键操作
  □ 分析流量日志
  □ 识别通信协议
  □ 建立初步端点清单

Phase 4: 协议解码
  □ 选择解码策略
  □ 解码请求/响应体
  □ 建立端点-功能映射
  □ 绘制调用序列图
  □ 填写端点清单 (附录 B)

Phase 5: 内部状态访问
  □ 评估是否需要此阶段
  □ 选择访问技术
  □ 实现 shape matching
  □ 构建状态访问代码
  □ 填写 API 表面文档 (附录 C)

Phase 6: 生产化封装
  □ 设计 Bridge API
  □ 实现缓存与容错
  □ 移除所有探测代码
  □ 添加版本韧性策略
  □ 编写回归测试
  □ 完成 API 文档

全程:
  □ 每阶段结束时填写探测决策记录 (附录 D)
  □ 探测脚本提交版本控制
  □ 关键发现截图/录制
```

---

> **文档关联**:
> - 案例来源: `cascade-interception-devguide.md`（Cascade Panel 完整探测实录）
> - Web 环境详细实现: `electron-webview-probing-methodology.md`（含 JavaScript 代码模板）
> - 经验分析: `cascade-interview-questions.md`（10 个关键架构问题）
