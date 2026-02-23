# Cascade Panel 深度拦截与二次开发指南

> **版本**: v1.0
> **作者**: AG-Better 开发团队
> **日期**: 2026-02-14
> **适用对象**: Antigravity IDE (Google VS Code Fork) 的 Cascade AI Chat Panel

---

## 目录

1. [架构概览](#1-架构概览)
2. [探测阶段总览 (T1.0 - T1.4)](#2-探测阶段总览)
3. [T1.0: acquireVsCodeApi 探测](#3-t10-acquirevscodapi-探测)
4. [T1.1C: 通信机制探测 (postMessage / Window 扫描)](#4-t11c-通信机制探测)
5. [T1.3: 网络拦截层 (fetch / XHR / WebSocket)](#5-t13-网络拦截层)
6. [T1.4: 深度 gRPC 响应体解码](#6-t14-深度-grpc-响应体解码)
7. [生产方案: React Fiber Bridge](#7-生产方案-react-fiber-bridge)
8. [gRPC-Web 协议与端点清单](#8-grpc-web-协议与端点清单)
9. [React Context API 完整表面](#9-react-context-api-完整表面)
10. [CDP 远程自动化](#10-cdp-远程自动化)
11. [Electron IPC 与 chatParams](#11-electron-ipc-与-chatparams)
12. [关键发现与经验教训](#12-关键发现与经验教训)
13. [附录: 完整探测脚本代码](#13-附录-完整探测脚本代码)

---

## 1. 架构概览

### 1.1 Cascade 运行环境

```
┌─────────────────────────────────────────────────────────┐
│  Antigravity IDE (Electron App)                         │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Main Workbench Page                               │ │
│  │  origin: vscode-file://vscode-app/...              │ │
│  │  ┌──────────────────────────────────────────────┐  │ │
│  │  │  Cascade Panel (iframe)                      │  │ │
│  │  │  origin: vscode-file://vscode-app/...        │  │ │
│  │  │  ★ SAME ORIGIN as parent                     │  │ │
│  │  │  ┌──────────────────────────────────────┐    │  │ │
│  │  │  │  React 18 App (#react-app)           │    │  │ │
│  │  │  │  └── Context Provider (events/state) │    │  │ │
│  │  │  │       └── Conversation Components    │    │  │ │
│  │  │  └──────────────────────────────────────┘    │  │ │
│  │  └──────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────┘ │
│                         │                               │
│                    gRPC-Web (fetch)                      │
│                         ↓                               │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Local Language Server                             │ │
│  │  https://127.0.0.1:{port}/                         │ │
│  │  Protobuf-encoded HTTP POST                        │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 1.2 关键特征

| 特征 | 值 |
|:---|:---|
| Cascade 所在位置 | iframe 内 |
| Origin | `vscode-file://vscode-app/...`（与父页面同源） |
| `acquireVsCodeApi` | **不存在**（Scenario C） |
| 通信协议 | gRPC-Web（HTTP POST + Protobuf） |
| 语言服务器地址 | `https://127.0.0.1:{port}/` （端口动态） |
| React 版本 | React 18（Fiber 架构） |
| 跨 iframe 访问 | 可以（同源） |
| 前端框架 | React 18 + Context Provider |

### 1.3 AG-Better 注入点

AG-Better 扩展通过修改 Cascade panel 的 HTML 文件注入代码：
- 文件位置：`app_root/cascade-panel.html`
- 注入方式：`<head>` 区域的 `<script>` 标签
- 执行时机：在 React 应用挂载之前（早期脚本执行）

---

## 2. 探测阶段总览

探测分为 4 个递进阶段，每个阶段基于上一阶段的结论决定下一步方向：

```
T1.0: acquireVsCodeApi 存在吗？
  └── 结果: 不存在 (Scenario C)
       └── T1.1C: 实际通信机制是什么？
            └── 结果: postMessage 存在但非主通道，发现 gRPC 特征
                 └── T1.3: 拦截全部网络流量 (fetch/XHR/WebSocket)
                      └── 结果: 发现 gRPC-Web over fetch，17+ 端点
                           └── T1.4: 解码 gRPC 二进制响应体
                                └── 结果: 成功提取 UUID/字符串，确认协议细节
                                     └── T2.0: 实现 React Fiber Bridge（生产方案）
```

| 阶段 | Git Commit | 目标 | 核心技术 |
|:---|:---|:---|:---|
| T1.0 | `991861d` | `acquireVsCodeApi` 是否可用 | 函数包装拦截 |
| T1.1C | `fbb001d` | 探测实际通信机制 | postMessage 拦截 + window 属性扫描 |
| T1.3 | `add08c7` | 拦截全部网络流量 | fetch/XHR/WebSocket monkey-patching |
| T1.4 | `896bb26` | 解码 gRPC 二进制数据 | Uint8Array 字符串/UUID 提取 |
| T2.0 | `b5e5464` | 生产实现 | React Fiber 遍历 + Context 直接调用 |
| T2.1 | `4d1ed4b` | 健壮性修复 | Prop shape matching + Summary nesting |

---

## 3. T1.0: acquireVsCodeApi 探测

### 3.1 目的

验证标准 VS Code Webview API 是否可用于 Cascade panel。

### 3.2 探测方式：函数包装拦截

```javascript
// 核心思路：用 wrapper 函数替换 window.acquireVsCodeApi
if (typeof window.acquireVsCodeApi === 'function') {
  const orig = window.acquireVsCodeApi;
  let intercepted = false;

  window.acquireVsCodeApi = function() {
    intercepted = true;
    console.log('[AG-Probe] intercepted! Stack:', new Error().stack);
    const api = orig.call(this);
    console.log('[AG-Probe] API keys:', Object.keys(api));
    console.log('[AG-Probe] getState():', JSON.stringify(api.getState?.()));
    window._agProbeApi = api;
    return api;
  };

  // 5 秒后检查：如果未被调用，尝试直接调用
  setTimeout(() => {
    if (!intercepted) {
      try {
        const api = orig.call(window);
        window._agProbeApi = api;
      } catch(e) {
        // "can only be invoked once" → API 已被其他代码调用
      }
    }
  }, 5000);
} else {
  // Scenario C: acquireVsCodeApi 不存在
}
```

### 3.3 决策树结果

| Scenario | 条件 | 后续路径 |
|:---|:---|:---|
| A | `intercepted = true`，API 正常 | → 使用标准 VS Code 消息通道 |
| B | `intercepted = false`，直接调用报 "already called" | → 需要更早的注入时机 |
| **C** ★ | **`acquireVsCodeApi` 不存在** | **→ 需要发现替代通信机制** |

**结论**: Cascade panel 不使用标准 VS Code Webview API。**`acquireVsCodeApi` 在 Cascade 的 window 对象上根本不存在。**

### 3.4 二次开发要点

- 如果在新版 IDE 中 `acquireVsCodeApi` 被添加，此探测能自动发现
- 5 秒超时机制可调整，用于应对不同加载速度的环境

---

## 4. T1.1C: 通信机制探测

### 4.1 目的

在 `acquireVsCodeApi` 不可用的情况下，探测 Cascade 使用的实际通信机制。

### 4.2 三重探测策略

#### 4.2.1 postMessage 拦截

```javascript
// 拦截 outbound 消息
var origPM = window.parent.postMessage.bind(window.parent);
window.parent.postMessage = function(data, origin) {
  var s = typeof data === 'object'
    ? JSON.stringify(data).substring(0, 200)
    : String(data).substring(0, 200);
  msgLog.push('OUT: ' + s);
  return origPM(data, origin || '*');
};

// 拦截 inbound 消息
window.addEventListener('message', function(e) {
  var s = typeof e.data === 'object'
    ? JSON.stringify(e.data).substring(0, 200)
    : String(e.data).substring(0, 200);
  msgLog.push('IN: ' + s);
});
```

**发现**: postMessage 存在但仅用于 VS Code 框架通信（主题变更等），不携带 AI 对话数据。

#### 4.2.2 Window 属性扫描

```javascript
// 扫描 window 上所有非标准属性
var custom = [];
for (var k in window) {
  if (!standardProps.has(k) && !k.startsWith('on') && !k.startsWith('webkit')) {
    try {
      var t = typeof window[k];
      if (t === 'function' || t === 'object') {
        custom.push(k + '(' + t + ')');
      }
    } catch(e) {}
  }
}
```

**发现**:
- `window.chatParams`：Base64 编码的 JSON，包含 OAuth token、CSRF token、语言服务器 URL
- 无 `vscode` 对象
- 无 `acquireVsCodeApi`

#### 4.2.3 页面位置与帧信息

```javascript
// 确认同源关系
console.log('href:', location.href);               // vscode-file://vscode-app/...
console.log('parent === window:', parent === window); // false (是 iframe)
console.log('parent.origin:', parent.location.origin); // 可访问（同源）
```

### 4.3 chatParams 解码

```javascript
// window.chatParams 是 Base64 编码的 JSON
var decoded = JSON.parse(atob(window.chatParams));
// 结构：
{
  "oauthToken": "ya29.xxx...",      // Google OAuth2 访问令牌
  "csrfToken": "xxx...",            // CSRF 防护令牌
  "languageServerUrl": "https://127.0.0.1:54854",  // 本地语言服务器
  "languageServerAuthToken": "xxx..." // 语言服务器认证令牌
}
```

### 4.4 二次开发要点

- `chatParams` 是获取语言服务器地址和认证信息的唯一来源
- 同源特性意味着可以直接访问 iframe 内部 DOM 和 JS 对象
- 从 CDP（Chrome DevTools Protocol）外部也可以通过遍历 iframe 来执行脚本

---

## 5. T1.3: 网络拦截层

### 5.1 目的

通过拦截所有网络 API 调用，发现 Cascade 与后端通信的完整协议。

### 5.2 三层 Monkey-Patching

#### 5.2.1 fetch 拦截

```javascript
var origFetch = window.fetch;
window.fetch = function(url, opts) {
  var u = typeof url === 'string' ? url : (url && url.url ? url.url : String(url));
  var method = (opts && opts.method) || 'GET';

  // 记录请求体片段
  var bodySnip = '';
  if (opts && opts.body) {
    try { bodySnip = ' body=' + String(opts.body).substring(0, 400); } catch(e) {}
  }

  log('FETCH', method + ' ' + u + bodySnip);

  return origFetch.apply(this, arguments).then(function(resp) {
    log('FETCH-RESP', resp.status + ' ' + u);
    return resp;
  });
};
```

#### 5.2.2 XMLHttpRequest 拦截

```javascript
var origOpen = XMLHttpRequest.prototype.open;
var origSend = XMLHttpRequest.prototype.send;

XMLHttpRequest.prototype.open = function(method, url) {
  this._agMethod = method;
  this._agUrl = String(url);
  return origOpen.apply(this, arguments);
};

XMLHttpRequest.prototype.send = function(body) {
  log('XHR', this._agMethod + ' ' + this._agUrl);
  this.addEventListener('load', function() {
    log('XHR-RESP', this.status + ' ' + this._agUrl);
  });
  return origSend.apply(this, arguments);
};
```

#### 5.2.3 WebSocket 拦截

```javascript
var OrigWS = window.WebSocket;
window.WebSocket = function(url, protocols) {
  log('WS-OPEN', url);
  var ws = protocols ? new OrigWS(url, protocols) : new OrigWS(url);

  // 拦截发送
  var origSend = ws.send.bind(ws);
  ws.send = function(data) {
    log('WS-OUT', String(data).substring(0, 400));
    return origSend(data);
  };

  // 拦截接收
  ws.addEventListener('message', function(e) {
    log('WS-IN', String(e.data).substring(0, 400));
  });

  ws.addEventListener('close', function(e) {
    log('WS-CLOSE', 'code=' + e.code);
  });

  return ws;
};

// 保持原型链和静态常量
window.WebSocket.prototype = OrigWS.prototype;
window.WebSocket.CONNECTING = OrigWS.CONNECTING;
window.WebSocket.OPEN = OrigWS.OPEN;
window.WebSocket.CLOSING = OrigWS.CLOSING;
window.WebSocket.CLOSED = OrigWS.CLOSED;
```

### 5.3 关键发现

1. **通信协议是 gRPC-Web over fetch**（非 XHR、非 WebSocket）
2. **所有请求发往 `https://127.0.0.1:{port}/`**（本地语言服务器）
3. **请求体是 Protobuf 编码的二进制数据**（Uint8Array）
4. **响应通过 ReadableStream 分块返回**（流式 gRPC）
5. **HTTP 状态码始终 200**，错误信息在 Protobuf 内部

### 5.4 二次开发要点

- fetch monkey-patching 是拦截 gRPC-Web 的唯一方式
- 注意 `opts.body` 可能是 Uint8Array（不能直接 toString）
- 响应体需要通过 `resp.clone().arrayBuffer()` 来读取，不能消费原始流
- WebSocket 拦截代码中**必须保持原型链**（`WebSocket.prototype = OrigWS.prototype`），否则 `instanceof` 检查会失败

---

## 6. T1.4: 深度 gRPC 响应体解码

### 6.1 目的

解码 gRPC 二进制请求/响应体，提取有意义的数据（UUID、字符串等）。

### 6.2 二进制数据解析工具函数

#### 6.2.1 字符串提取

```javascript
// 从 Uint8Array 中提取连续 3+ 个 ASCII 可打印字符的片段
function extractStrings(bytes) {
  var parts = [], cur = '';
  for (var i = 0; i < bytes.length; i++) {
    var b = bytes[i];
    if (b >= 32 && b < 127) {
      cur += String.fromCharCode(b);
    } else {
      if (cur.length >= 3) parts.push(cur);
      cur = '';
    }
  }
  if (cur.length >= 3) parts.push(cur);
  return parts;
}
```

#### 6.2.2 UUID 提取

```javascript
// 从提取的字符串中匹配标准 UUID 格式
function extractUUIDs(bytes) {
  var str = extractStrings(bytes).join('|');
  return str.match(
    /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/g
  ) || [];
}
```

### 6.3 增强版 fetch 拦截（含响应体解码）

```javascript
var origFetch = window.fetch;
window.fetch = function(input, opts) {
  var url = typeof input === 'string' ? input : (input && input.url || String(input));
  var ep = matchEndpoint(url); // 匹配已知 gRPC 端点名

  // 请求体解码
  if (opts && opts.body && ep) {
    try {
      var rb = opts.body instanceof Uint8Array
        ? opts.body
        : new Uint8Array(opts.body);
      var rs = extractStrings(rb);
      var ru = extractUUIDs(rb);
      log('REQ', ep + (ru.length ? ' uuid=' + ru[0] : '')
        + ' [' + rs.join('|') + ']');
    } catch(e) {
      log('REQ', ep + ' (body parse err)');
    }
  }

  return origFetch.apply(this, arguments).then(function(resp) {
    if (!ep) return resp;

    // ★ 关键: clone() 后读取 arrayBuffer，不影响原始流
    var clone = resp.clone();
    clone.arrayBuffer().then(function(buf) {
      var bytes = new Uint8Array(buf);
      var strs = extractStrings(bytes);
      var uuids = extractUUIDs(bytes);
      log('RESP', ep + ' status=' + resp.status
        + ' size=' + bytes.length + 'B'
        + ' uuids=[' + uuids.join(', ') + ']');
      if (strs.length > 0) {
        log('DATA', ep + ': ' + strs.join(' | '));
      }
    });

    return resp;
  });
};
```

### 6.4 重要注意事项

1. **`resp.clone()`**：gRPC-Web 使用流式响应，读取 body 会消费流。必须先 clone 再读取
2. **Protobuf 字段分隔符**：在二进制中表现为不可打印字符（< 32），所以 `extractStrings` 用它们做天然分隔
3. **响应大小**：有些 streaming 端点（如 `StreamCascadeReactiveUpdates`）的 `Content-Length` 显示为 0，但实际数据通过 ReadableStream 分块传输
4. **UUID 格式**：Cascade 会话 ID 使用标准 UUID v4 格式 `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

---

## 7. 生产方案: React Fiber Bridge

### 7.1 设计思路

经过 T1.0-T1.4 的探测，确定最可靠的方案是**直接访问 React Fiber 树**，从内部获取 Context Provider 中的 events 和 state。

```
React Fiber Tree
└── Root (FiberRootNode)
    └── App
        └── Context.Provider (value = {events, state, layout})
            ├── ConversationList (props: {cascadeIds: [...]})
            │   └── memoizedState chain → summaries map
            └── ChatView
                └── MessageList
```

### 7.2 完整 Bridge API

```javascript
window._agBridge = {
  findCascadeContext(),     // 返回 Context Provider 的 value
  findConversationList(),   // 返回会话列表 [{cascadeId, summary, ...}]
  getCurrentCascadeId(),    // 返回当前活跃会话 ID
  switchConversation(id),   // 切换到指定会话
  startNewConversation(),   // 创建新会话
  isReady()                 // Bridge 是否就绪
};
```

### 7.3 核心实现细节

#### 7.3.1 Fiber Suffix 发现

React 18 在 DOM 元素上添加 `__reactContainer$<random_suffix>` 属性。Suffix 是随机字符串，每次 React 挂载都不同。

```javascript
function findFiberSuffix() {
  const all = document.querySelectorAll('*');
  for (let i = 0; i < all.length; i++) {
    const keys = Object.keys(all[i]);
    for (let k = 0; k < keys.length; k++) {
      if (keys[k].startsWith('__reactContainer$')) {
        return keys[k].replace('__reactContainer$', '');
      }
    }
  }
  return null;
}
```

**关键点**: Suffix 在每次页面刷新后都会变化（例如 `iz359v3fbbm` → `ke373f03kc`），所以不能硬编码。

#### 7.3.2 Context Provider 发现（BFS 遍历）

```javascript
function findCascadeContext() {
  const container = document.getElementById('react-app')
    ['__reactContainer$' + suffix];

  const queue = [container];
  const visited = new WeakSet();

  while (queue.length > 0) {
    const fiber = queue.shift();
    if (!fiber || visited.has(fiber)) continue;
    visited.add(fiber);

    // ★ Shape matching: 检查 memoizedProps.value 的结构
    if (fiber.memoizedProps?.value) {
      const val = fiber.memoizedProps.value;
      if (val.events && val.state && val.layout
          && val.events.setCascadeConversationState) {
        return val; // 找到 Cascade Context！
      }
    }

    if (fiber.child) queue.push(fiber.child);
    if (fiber.sibling) queue.push(fiber.sibling);
  }
}
```

**匹配条件**:
- `value.events` 存在（包含 32 个事件函数）
- `value.state` 存在（包含 23 个状态属性）
- `value.layout` 存在
- `value.events.setCascadeConversationState` 存在（关键切换函数）

#### 7.3.3 会话列表发现（Prop Shape Matching）

```javascript
function findConversationList() {
  // BFS 遍历 Fiber 树
  // ★ 不用组件名（如 ILe/wLe），因为 minified 名每次构建都变
  // ★ 用 props 结构匹配: 寻找有 cascadeIds 数组 prop 的组件

  while (queue.length > 0) {
    const fiber = queue.shift();

    if (fiber.memoizedProps
        && Array.isArray(fiber.memoizedProps.cascadeIds)
        && fiber.memoizedProps.cascadeIds.length > 0) {
      listComponent = fiber;
      break;
    }
  }

  // 从组件的 memoizedState 链中提取 summaries
  let state = listComponent.memoizedState;
  while (state) {
    const ms = state.memoizedState;
    // ★ Summaries 可能嵌套在 .summaries 下，也可能直接是 UUID-keyed map
    if (ms?.summaries) { summaries = ms.summaries; break; }
    if (ms && /^[0-9a-f]{8}-/.test(Object.keys(ms)[0])) { summaries = ms; break; }
    state = state.next;
  }
}
```

**教训**:
1. **不要使用 minified 组件名**（如 `ILe`、`wLe`）— 这些名字在每次构建后都会变化
2. **使用 prop 结构匹配**（如 `cascadeIds` 数组）— 这些是业务逻辑属性，不会被混淆
3. **Summaries 嵌套结构不稳定** — 需要同时处理 `ms.summaries` 和直接 UUID-keyed 两种格式
4. **组件可能未挂载** — 当用户在对话视图时，ConversationList 组件不渲染，需要返回缓存数据

#### 7.3.4 会话切换

```javascript
// 切换到已有会话
function switchConversation(cascadeId) {
  const ctx = findCascadeContext();
  ctx.events.setCascadeConversationState({ cascadeId: cascadeId });
}

// 创建新会话
function startNewConversation() {
  const ctx = findCascadeContext();
  ctx.events.clearCascadeId();
}
```

**触发的后端调用**:
- `setCascadeConversationState` → 触发 `UpdateConversationAnnotations` + `StreamCascadeReactiveUpdates`
- `clearCascadeId` → 清除当前会话 ID，显示空白对话框

---

## 8. gRPC-Web 协议与端点清单

### 8.1 协议特征

| 属性 | 值 |
|:---|:---|
| 传输方式 | HTTP POST over `fetch` |
| 服务器地址 | `https://127.0.0.1:{port}/` |
| 端口 | 动态（从 `chatParams` 获取） |
| Content-Type | `application/grpc-web+proto` |
| 编码 | Protocol Buffers (protobuf) |
| 响应方式 | ReadableStream（流式） |
| 认证 | Bearer token（OAuth2 ya29...） |

### 8.2 已发现端点完整清单

| 端点名 | 功能 | 请求含 UUID | 流式响应 |
|:---|:---|:---|:---|
| `ListPages` | 列出打开的页面 | 否 | 是 |
| `SendUserCascadeMessage` | 发送用户消息 | 是 | 是 |
| `StreamCascadeReactiveUpdates` | 实时对话更新流 | 是 | 是 |
| `StreamCascadeSummariesReactiveUpdates` | 对话摘要更新流 | 否 | 是 |
| `StreamCascadePanelReactiveUpdates` | 面板状态更新流 | 否 | 是 |
| `UpdateConversationAnnotations` | 更新对话标注 | 是 | 否 |
| `StartChatClientRequestStream` | 开始聊天请求流 | 是 | 是 |
| `GetUserStatus` | 获取用户状态 | 否 | 否 |
| `GetWorkspaceInfos` | 获取工作区信息 | 否 | 否 |
| `GetAllRules` | 获取所有规则 | 否 | 否 |
| `GetAllWorkflows` | 获取所有工作流 | 否 | 否 |
| `GetMcpServerStates` | 获取 MCP 服务器状态 | 否 | 否 |
| `GetProfileData` | 获取用户 profile | 否 | 否 |
| `LogEvent` | 日志上报 | 否 | 否 |
| `GetStaticExperimentStatus` | A/B 实验状态 | 否 | 否 |
| `ShouldEnableUnleash` | Feature flag 查询 | 否 | 否 |

### 8.3 调用模式

```
用户发送消息:
  → SendUserCascadeMessage (POST, body含消息文本+cascadeId)
  ← 流式响应: AI 回复内容分块传输

切换对话:
  → UpdateConversationAnnotations (POST, body含新cascadeId)
  ← 确认响应 (204)
  → StreamCascadeReactiveUpdates (POST, body含cascadeId)
  ← 流式响应: 对话历史内容

页面加载:
  → GetUserStatus
  → GetProfileData
  → ListPages
  → StreamCascadeSummariesReactiveUpdates
  → StreamCascadePanelReactiveUpdates
  → GetMcpServerStates
  → GetAllRules
  → GetAllWorkflows
```

---

## 9. React Context API 完整表面

### 9.1 Context Provider Value 结构

```javascript
const contextValue = {
  events: { ... },   // 32 个事件函数
  state: { ... },    // 23 个状态属性
  layout: { ... },   // 布局相关
};
```

### 9.2 已确认可用的 events 函数

| 函数名 | 参数 | 功能 |
|:---|:---|:---|
| `setCascadeConversationState` | `{cascadeId: string}` | 切换到指定对话 |
| `clearCascadeId` | 无 | 清除当前对话（新建对话） |

其余 30 个函数在 T1.4 中观察到但未逐个验证，包括但不限于：
- 消息发送/编辑/删除相关
- UI 状态控制（展开/折叠等）
- 设置变更通知
- 代码块操作（运行/复制等）

### 9.3 State 结构

```javascript
state.cascadeState = {
  cascadeId: "uuid-string",    // 当前活跃对话 ID
  // ... 其他对话状态字段
};
```

### 9.4 Conversation List Component Props

```javascript
{
  cascadeIds: ["uuid-1", "uuid-2", ...],  // 所有对话 ID 列表
  // ... 其他 props
}
```

### 9.5 memoizedState 链中的 Summaries

```javascript
// 访问路径: component.memoizedState → (遍历 .next 链) → memoizedState
// 格式 1: 直接 UUID-keyed map
{
  "uuid-1": { summary: "...", lastModifiedTime: "...", status: "...", stepCount: N },
  "uuid-2": { ... }
}

// 格式 2: 嵌套在 .summaries 下
{
  summaries: {
    "uuid-1": { summary: "...", ... },
    "uuid-2": { ... }
  }
}
```

---

## 10. CDP 远程自动化

### 10.1 连接方式

```
CDP WebSocket: ws://localhost:9222/devtools/page/{PAGE_ID}
```

启用 CDP: 在 IDE 启动参数中添加 `--remote-debugging-port=9222`

### 10.2 跨 iframe 执行脚本

由于 Cascade iframe 与主页面同源，可以从主页面遍历 iframe 执行脚本：

```javascript
// CDP 执行的 JS wrapper
(function(){
    var iframes = document.querySelectorAll('iframe');
    for (var i = 0; i < iframes.length; i++) {
        try {
            if (iframes[i].contentWindow
                && iframes[i].contentWindow.location.href.indexOf('cascade') !== -1) {
                var win = iframes[i].contentWindow;
                // 在 Cascade iframe 内执行代码
                var result = (function(win) {
                    /* 实际要执行的代码 */
                })(win);
                return typeof result === 'string' ? result : JSON.stringify(result);
            }
        } catch(e) {
            return JSON.stringify({error: e.message});
        }
    }
    return JSON.stringify({error: 'cascade iframe not found'});
})()
```

### 10.3 CDP Helper 工具 (_cdp_helper.py)

```python
#!/usr/bin/env python3
"""CDP helper to execute JS in Cascade Webview."""
import asyncio, json, sys
import websockets

CDP_URI = 'ws://localhost:9222/devtools/page/{PAGE_ID}'

async def cdp_exec(js_expr, timeout=15):
    """Execute JS in cascade iframe via main frame cross-origin access."""
    wrapper = f"""
    (function(){{
        var iframes = document.querySelectorAll('iframe');
        for (var i = 0; i < iframes.length; i++) {{
            try {{
                if (iframes[i].contentWindow
                    && iframes[i].contentWindow.location.href.indexOf('cascade') !== -1) {{
                    var win = iframes[i].contentWindow;
                    var result = (function(win) {{ {js_expr} }})(win);
                    return typeof result === 'string' ? result : JSON.stringify(result);
                }}
            }} catch(e) {{ return JSON.stringify({{error: e.message}}); }}
        }}
        return JSON.stringify({{error: 'cascade iframe not found'}});
    }})()
    """
    async with websockets.connect(CDP_URI, max_size=10**7) as ws:
        await ws.send(json.dumps({
            'id': 1, 'method': 'Runtime.evaluate',
            'params': {'expression': wrapper, 'returnByValue': True}
        }))
        for _ in range(50):
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
            msg = json.loads(raw)
            if msg.get('id') == 1:
                return msg.get('result', {}).get('result', {}).get('value', '')
```

### 10.4 常用 CDP 操作

```python
# 获取 probe 日志
python3 _cdp_helper.py probe

# 分析 DOM 结构
python3 _cdp_helper.py dom

# 查看会话列表
python3 _cdp_helper.py conversations

# 完整状态快照
python3 _cdp_helper.py snapshot

# 全部日志
python3 _cdp_helper.py all
```

### 10.5 页面刷新

```javascript
// CDP 方式刷新 Cascade webview
// ★ 不要刷新 iframe，要刷新主 workbench 页面
// 否则 extension host 会丢失对 iframe 的引用
{ "id": 1, "method": "Page.reload", "params": { "ignoreCache": true } }
```

**注意**: 不要使用带 `?timestamp` 的 URL 刷新（cache-bust），这会导致 React 不重新挂载。

---

## 11. Electron IPC 与 chatParams

### 11.1 Electron IPC (仅主工作台页面可用)

```javascript
// 在主工作台页面（非 Cascade iframe 内）可用
window.vscode.ipcRenderer = {
  send(channel, ...args),     // 发送消息到主进程
  invoke(channel, ...args),   // 请求-响应模式
  on(channel, handler),       // 监听主进程消息
  once(channel, handler),     // 一次性监听
  removeListener(channel, handler)
};
```

**注意**: `window.vscode` 在 Cascade iframe 内**不可用**，只在主工作台页面上存在。

### 11.2 chatParams 结构

```javascript
// Cascade iframe 的 window 对象上
// window.chatParams = Base64EncodedJSON

var params = JSON.parse(atob(window.chatParams));
// {
//   oauthToken: "ya29.xxx...",           // Google OAuth2 访问令牌
//   csrfToken: "xxx...",                 // CSRF 防护令牌
//   languageServerUrl: "https://127.0.0.1:54854",
//   languageServerAuthToken: "xxx...",
//   // 可能还有其他字段
// }
```

### 11.3 用途

- **`languageServerUrl`**: 构造 gRPC-Web 请求的目标地址
- **`oauthToken`**: Bearer 认证
- **`csrfToken`**: CSRF 防护头部

---

## 12. 关键发现与经验教训

### 12.1 探测过程中的坑

| 问题 | 原因 | 解决方案 |
|:---|:---|:---|
| Minified 组件名每次构建都变 | Webpack/Rollup 混淆 | 使用 **prop shape matching** |
| Summaries 嵌套结构不固定 | React state 结构更新 | 同时检查 `.summaries` 和直接 UUID-keyed |
| ConversationList 不总是挂载 | 对话视图中不渲染列表 | 返回 `_lastConversations` 缓存 |
| iframe cache-bust 刷新破坏 React | Extension host 丢失 iframe 引用 | 使用 `Page.reload` 刷新主页面 |
| `_tabManager` 闭包作用域 | JS 模块化 | `Object.defineProperty(window, ...)` |
| gRPC 响应体显示 0B | 流式传输，Content-Length=0 | 通过 `clone().arrayBuffer()` 读取实际数据 |
| Fiber suffix 每次刷新都变 | React 18 内部随机生成 | 动态扫描 DOM 属性获取 |

### 12.2 拦截技术选型指南

| 技术 | 适用场景 | 风险 |
|:---|:---|:---|
| **React Fiber Bridge** ★ | 生产方案：读取/修改 UI 状态 | React 版本升级可能破坏 |
| fetch monkey-patching | 调试/探测网络流量 | 可能影响正常 gRPC 调用 |
| XHR monkey-patching | 调试（Cascade 不使用 XHR） | 低风险但也低价值 |
| WebSocket 拦截 | 调试（Cascade 不使用 WS） | 低风险但也低价值 |
| postMessage 拦截 | 调试 VS Code 框架消息 | 低风险，不含业务数据 |
| CDP 远程执行 | 自动化测试、远程调试 | 需要 `--remote-debugging-port` |
| chatParams 解码 | 获取认证信息、服务器地址 | Base64 编码，无加密 |
| Electron IPC | 扩展主工作台功能 | 仅主页面可用，非 Cascade iframe |

### 12.3 生产化建议

1. **不要在生产环境使用 fetch/XHR/WebSocket monkey-patching** — 仅用于探测和调试
2. **React Fiber Bridge 是当前唯一可靠的生产方案** — 但需要防御性编程
3. **始终处理 Fiber 不可用的情况** — React 可能未挂载、挂载延迟、或结构变化
4. **缓存上一次成功的查询结果** — 应对组件未挂载等暂时性失败
5. **使用 polling 而非一次性查询** — Bridge 需要等待 React 就绪后才能使用

---

## 13. 附录: 完整探测脚本代码

### 13.1 T1.0 完整脚本

```javascript
// === AG-Better: 前置假设验证（临时脚本，验证后移除） ===
(function() {
  console.log('[AG-Probe] acquireVsCodeApi exists?', typeof window.acquireVsCodeApi);
  console.log('[AG-Probe] acquireVsCodeApi already called?',
    window.acquireVsCodeApi?.toString?.().includes('can only be invoked once'));

  if (typeof window.acquireVsCodeApi === 'function') {
    const orig = window.acquireVsCodeApi;
    let intercepted = false;
    window.acquireVsCodeApi = function() {
      intercepted = true;
      console.log('[AG-Probe] acquireVsCodeApi intercepted! Call stack:', new Error().stack);
      const api = orig.call(this);
      console.log('[AG-Probe] API object keys:', Object.keys(api));
      console.log('[AG-Probe] getState():', JSON.stringify(api.getState?.()).substring(0, 500));
      window._agProbeApi = api;
      return api;
    };
    setTimeout(() => {
      console.log('[AG-Probe] Was intercepted within 5s?', intercepted);
      if (!intercepted) {
        console.warn('[AG-Probe] acquireVsCodeApi was NOT called.');
        try {
          const api = orig.call(window);
          console.log('[AG-Probe] Direct call succeeded?', !!api);
          window._agProbeApi = api;
        } catch(e) {
          console.error('[AG-Probe] Direct call failed:', e.message);
        }
      }
    }, 5000);
  } else {
    console.error('[AG-Probe] acquireVsCodeApi not found on window!');
  }
})();
```

### 13.2 T1.1C 完整脚本

```javascript
// === AG-Probe T1.1C: 探测实际通信机制 ===
(function() {
  var results = [];
  function log(msg) { results.push(msg); console.log('[AG-Probe] ' + msg); }

  // 1. 基础 API 检查
  log('--- 1. Basic API Check ---');
  log('acquireVsCodeApi: ' + (typeof window.acquireVsCodeApi));
  log('window.parent === window: ' + (window.parent === window));
  try { log('parent.origin: ' + window.parent.location.origin); }
  catch(e) { log('parent.origin: CROSS-ORIGIN'); }

  // 2. postMessage 拦截
  log('--- 2. postMessage Interception ---');
  var msgLog = [];
  var origPM = window.parent !== window
    ? window.parent.postMessage.bind(window.parent) : null;
  if (origPM) {
    window.parent.postMessage = function(data, origin) {
      var s = typeof data === 'object'
        ? JSON.stringify(data).substring(0, 200)
        : String(data).substring(0, 200);
      msgLog.push('OUT: ' + s);
      return origPM(data, origin || '*');
    };
  }
  window.addEventListener('message', function(e) {
    var s = typeof e.data === 'object'
      ? JSON.stringify(e.data).substring(0, 200)
      : String(e.data).substring(0, 200);
    msgLog.push('IN: ' + s);
  });

  // 3. Window 非标准属性扫描
  log('--- 3. Window Custom Props ---');
  var custom = [];
  for (var k in window) {
    if (!k.startsWith('on') && !k.startsWith('webkit') && k !== '__proto__') {
      try {
        var t = typeof window[k];
        if (t === 'function' || t === 'object') custom.push(k + '(' + t + ')');
      } catch(e) {}
    }
  }
  log(custom.length > 0 ? custom.join(', ') : 'NONE');

  // 4. 位置与帧信息
  log('--- 4. Location & Frame ---');
  log('href: ' + location.href.substring(0, 200));
  log('protocol: ' + location.protocol);

  // 5. 延迟汇总
  setTimeout(function() {
    log('--- 5. Messages after 8s ---');
    log('Total: ' + msgLog.length);
    msgLog.slice(0, 15).forEach(function(m, i) { log('  [' + i + '] ' + m); });
    showResults();
  }, 8000);

  setTimeout(showResults, 500);

  function showResults() {
    var el = document.getElementById('ag-probe-results');
    if (!el) {
      el = document.createElement('div');
      el.id = 'ag-probe-results';
      el.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:999999;'
        + 'background:#1a1a2e;color:#0f0;font:12px monospace;padding:12px;'
        + 'border-bottom:3px solid #0f0;max-height:50vh;overflow:auto;white-space:pre-wrap;';
      document.body ? document.body.prepend(el)
        : document.addEventListener('DOMContentLoaded', function() { document.body.prepend(el); });
    }
    el.textContent = '=== AG-Probe T1.1C ===\n' + results.join('\n');
  }
})();
```

### 13.3 T1.3 完整脚本

```javascript
// === AG-Probe T1.3: 网络通信拦截 (fetch/XHR/WebSocket) ===
(function() {
  var log = [];
  var MAX = 300;
  var TRIM = 400;

  function add(type, info) {
    if (log.length >= MAX) return;
    log.push('[' + type + '] ' + info);
  }

  // 1. 拦截 fetch
  var origFetch = window.fetch;
  window.fetch = function(url, opts) {
    var u = typeof url === 'string' ? url : (url && url.url ? url.url : String(url));
    var method = (opts && opts.method) || 'GET';
    var bodySnip = '';
    if (opts && opts.body) {
      try { bodySnip = ' body=' + String(opts.body).substring(0, TRIM); } catch(e) {}
    }
    add('FETCH', method + ' ' + u.substring(0, 200) + bodySnip);
    return origFetch.apply(this, arguments).then(function(resp) {
      add('FETCH-RESP', resp.status + ' ' + u.substring(0, 150));
      return resp;
    });
  };

  // 2. 拦截 XMLHttpRequest
  var origXHROpen = XMLHttpRequest.prototype.open;
  var origXHRSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function(method, url) {
    this._agMethod = method;
    this._agUrl = String(url).substring(0, 200);
    return origXHROpen.apply(this, arguments);
  };
  XMLHttpRequest.prototype.send = function(body) {
    var bodySnip = body ? ' body=' + String(body).substring(0, TRIM) : '';
    add('XHR', (this._agMethod || '?') + ' ' + (this._agUrl || '?') + bodySnip);
    var self = this;
    this.addEventListener('load', function() {
      add('XHR-RESP', self.status + ' ' + (self._agUrl || '?'));
    });
    return origXHRSend.apply(this, arguments);
  };

  // 3. 拦截 WebSocket
  var OrigWS = window.WebSocket;
  window.WebSocket = function(url, protocols) {
    add('WS-OPEN', String(url).substring(0, 200));
    var ws = protocols ? new OrigWS(url, protocols) : new OrigWS(url);
    var origSend = ws.send.bind(ws);
    ws.send = function(data) {
      add('WS-OUT', String(data).substring(0, TRIM));
      return origSend(data);
    };
    ws.addEventListener('message', function(e) {
      add('WS-IN', String(e.data).substring(0, TRIM));
    });
    ws.addEventListener('close', function(e) {
      add('WS-CLOSE', 'code=' + e.code);
    });
    return ws;
  };
  window.WebSocket.prototype = OrigWS.prototype;
  window.WebSocket.CONNECTING = OrigWS.CONNECTING;
  window.WebSocket.OPEN = OrigWS.OPEN;
  window.WebSocket.CLOSING = OrigWS.CLOSING;
  window.WebSocket.CLOSED = OrigWS.CLOSED;

  // 4. postMessage
  if (window.parent !== window) {
    var origPM = window.parent.postMessage.bind(window.parent);
    window.parent.postMessage = function(data, origin) {
      var s;
      try { s = typeof data === 'object' ? JSON.stringify(data).substring(0, 200) : String(data).substring(0, 200); }
      catch(e) { s = '?'; }
      add('PM-OUT', s);
      return origPM(data, origin || '*');
    };
  }
  window.addEventListener('message', function(e) {
    var s;
    try { s = typeof e.data === 'object' ? JSON.stringify(e.data).substring(0, 200) : String(e.data).substring(0, 200); }
    catch(e2) { s = '?'; }
    add('PM-IN', s);
  }, true);

  // 显示面板
  function render() {
    var el = document.getElementById('ag-probe-results');
    if (!el) {
      el = document.createElement('div');
      el.id = 'ag-probe-results';
      el.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:999999;'
        + 'background:#1a1a2e;color:#0f0;font:10px/1.3 monospace;padding:6px 10px;'
        + 'border-bottom:3px solid #0f0;max-height:55vh;overflow:auto;white-space:pre-wrap;';
      (document.body || document.documentElement).appendChild(el);
    }
    el.textContent = '=== AG-Probe T1.3: Network Traffic (' + log.length + ') ===\n'
      + 'Send a msg to AI, wait for reply, then copy this text.\n\n'
      + log.join('\n');
    window._agProbeText = text;
  }

  setInterval(render, 2000);
  setTimeout(render, 800);
})();
```

### 13.4 T1.4 完整脚本

```javascript
// === AG-Probe T1.4: 深度 gRPC 响应体解码 ===
(function() {
  var log = [];
  var MAX = 500;

  function add(tag, info) {
    if (log.length >= MAX) log.shift();
    log.push('[' + tag + '] ' + info);
  }

  function extractStrings(bytes) {
    var parts = [], cur = '';
    for (var i = 0; i < bytes.length; i++) {
      var b = bytes[i];
      if (b >= 32 && b < 127) cur += String.fromCharCode(b);
      else { if (cur.length >= 3) parts.push(cur); cur = ''; }
    }
    if (cur.length >= 3) parts.push(cur);
    return parts;
  }

  function extractUUIDs(bytes) {
    var str = extractStrings(bytes).join('|');
    return str.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/g) || [];
  }

  var DEEP = [
    'ListPages','SendUserCascadeMessage','StreamCascadeSummariesReactiveUpdates',
    'StreamCascadeReactiveUpdates','StreamCascadePanelReactiveUpdates',
    'UpdateConversationAnnotations','StartChatClientRequestStream',
    'GetUserStatus','GetWorkspaceInfos','GetAllRules','GetAllWorkflows',
    'GetMcpServerStates','GetProfileData','LogEvent','GetStaticExperimentStatus',
    'ShouldEnableUnleash'
  ];

  function matchEndpoint(url) {
    for (var i = 0; i < DEEP.length; i++) {
      if (url.indexOf(DEEP[i]) !== -1) return DEEP[i];
    }
    return null;
  }

  var origFetch = window.fetch;
  window.fetch = function(input, opts) {
    var url = typeof input === 'string' ? input : (input && input.url || String(input));
    var ep = matchEndpoint(url);
    var short = url.replace(/https:\/\/127\.0\.0\.1:\d+\//, '');

    if (opts && opts.body && ep) {
      try {
        var rb = opts.body instanceof Uint8Array ? opts.body : new Uint8Array(opts.body);
        var rs = extractStrings(rb);
        var ru = extractUUIDs(rb);
        add('REQ', ep + (ru.length ? ' uuid=' + ru[0] : '') + ' [' + rs.join('|') + ']');
      } catch(e) { add('REQ', ep + ' (body parse err)'); }
    } else {
      add('REQ', short);
    }

    return origFetch.apply(this, arguments).then(function(resp) {
      if (!ep) return resp;
      var clone = resp.clone();
      clone.arrayBuffer().then(function(buf) {
        var bytes = new Uint8Array(buf);
        var strs = extractStrings(bytes);
        var uuids = extractUUIDs(bytes);
        add('RESP', ep + ' status=' + resp.status + ' size=' + bytes.length + 'B'
          + ' uuids=[' + uuids.join(', ') + ']');
        if (strs.length > 0) {
          var joined = strs.join(' | ');
          if (joined.length > 2000) joined = joined.substring(0, 2000) + '...(truncated)';
          add('DATA', ep + ': ' + joined);
        }
      }).catch(function(e) { add('RESP-ERR', ep + ': ' + e.message); });
      return resp;
    });
  };

  if (window.parent !== window) {
    var origPM = window.parent.postMessage.bind(window.parent);
    window.parent.postMessage = function(data, origin) {
      add('PM-OUT', (typeof data === 'object'
        ? JSON.stringify(data).substring(0, 150)
        : String(data).substring(0, 150)));
      return origPM(data, origin || '*');
    };
  }
  window.addEventListener('message', function(e) {
    add('PM-IN', (typeof e.data === 'object'
      ? JSON.stringify(e.data).substring(0, 150)
      : String(e.data).substring(0, 150)));
  }, true);

  function render() {
    var el = document.getElementById('ag-probe-results');
    if (!el) {
      el = document.createElement('div');
      el.id = 'ag-probe-results';
      el.style.cssText = 'position:fixed;bottom:0;left:0;right:0;z-index:999999;'
        + 'background:#1a1a2e;color:#0f0;font:10px/1.3 monospace;padding:6px 10px;'
        + 'border-top:3px solid #0f0;max-height:40vh;overflow:auto;white-space:pre-wrap;user-select:text;';
      (document.body || document.documentElement).appendChild(el);
    }
    el.textContent = '=== AG-Probe T1.4: Deep gRPC (' + log.length + ') ===\n'
      + 'Do: 1) send msg  2) switch conversation  3) copy this\n\n'
      + log.join('\n');
    window._agProbeLog = log.slice();
  }

  setInterval(render, 2000);
  setTimeout(render, 800);
})();
```

### 13.5 生产 React Fiber Bridge

完整代码见 `app_root/cascade-panel.html` 第 6-198 行。

---

## 快速参考卡

```
┌──────────────────────────────────────────────────────────────┐
│  Cascade 开发快速参考                                         │
├──────────────────────────────────────────────────────────────┤
│  Window 对象:                                                │
│    window._agBridge          → Bridge API                    │
│    window._tabManager        → Tab Manager 实例              │
│    window.chatParams         → Base64(JSON) 认证信息          │
│                                                              │
│  React 入口:                                                  │
│    #react-app['__reactContainer$' + suffix]                  │
│    suffix 通过 findFiberSuffix() 动态获取                      │
│                                                              │
│  切换对话:                                                    │
│    _agBridge.switchConversation(cascadeId)                    │
│                                                              │
│  新建对话:                                                    │
│    _agBridge.startNewConversation()                           │
│                                                              │
│  获取对话列表:                                                 │
│    _agBridge.findConversationList()                           │
│    → [{cascadeId, summary, lastModifiedTime, status}]        │
│                                                              │
│  获取当前对话 ID:                                              │
│    _agBridge.getCurrentCascadeId()                            │
│                                                              │
│  gRPC 服务器:                                                 │
│    https://127.0.0.1:{port}/                                 │
│    port 从 chatParams.languageServerUrl 获取                  │
│                                                              │
│  CDP 调试:                                                    │
│    ws://localhost:9222/devtools/page/{PAGE_ID}                │
│    python3 _cdp_helper.py [probe|dom|snapshot|all]            │
│                                                              │
│  持久化:                                                      │
│    localStorage 'ag-better-tab-state' (tab 状态)              │
│    localStorage 'cascade-panel-settings' (扩展设置)           │
│    localStorage 'ag-better-bridge-enabled' (bridge 开关)      │
└──────────────────────────────────────────────────────────────┘
```
