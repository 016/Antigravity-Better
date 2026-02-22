# Electron Webview 逆向探测通用方法论

> 从 Cascade Panel 探测实践中提炼的标准化流程
> 适用于任何 Electron 应用中嵌入的 Webview / iframe 的逆向分析与二次开发

---

## 核心原则

1. **递进式排除** — 从最标准的机制开始，逐层深入，每层根据上一层结果决定方向
2. **最小侵入** — 每一步只做最小验证，保留原始函数引用，不破坏目标正常运行
3. **结构匹配优于名称匹配** — 在混淆环境中，匹配数据结构而非变量名/函数名
4. **探测与生产分离** — 探测阶段用 monkey-patching 撒网，生产阶段用最稳定的方案

---

## 总流程图

```
Phase 0: 环境识别
  │  确认目标运行在哪里（iframe? 同源? Electron?）
  │
  ▼
Phase 1: 标准 API 探测
  │  目标有标准通信接口吗？
  │  ├─ 有 → 直接使用，流程结束
  │  └─ 没有 →
  ▼
Phase 2: 通信通道发现
  │  扫描 window 属性 + 拦截 postMessage
  │  找到认证信息、服务器地址、非标准 API
  │
  ▼
Phase 3: 全量网络拦截
  │  同时 monkey-patch fetch / XHR / WebSocket
  │  确认实际通信协议和端点清单
  │
  ▼
Phase 4: 协议解码
  │  解析请求/响应体的编码格式
  │  建立端点 → 功能的映射表
  │
  ▼
Phase 5: 内部状态访问
  │  通过框架内部结构（如 React Fiber）直接读写状态
  │  构建稳定的 Bridge API
  │
  ▼
Phase 6: 生产化封装
     移除探测代码，保留最稳定的访问路径
     添加容错、缓存、降级机制
```

---

## Phase 0: 环境识别

**目标**: 搞清楚注入代码运行在什么环境中，决定后续可用的技术手段。

### 检测清单

```javascript
// 1. 是否在 iframe 中？
const isIframe = window.parent !== window;

// 2. 与父页面是否同源？
let isSameOrigin = false;
try {
  isSameOrigin = !!window.parent.location.origin;
} catch(e) {
  isSameOrigin = false; // 跨域，抛 SecurityError
}

// 3. 是否在 Electron 中？
const isElectron = !!(window.process?.versions?.electron
  || navigator.userAgent.includes('Electron'));

// 4. 页面协议
const protocol = location.protocol;
// 'vscode-file:' → VS Code 系列
// 'file:'        → 本地文件
// 'http/https:'  → Web 应用
// 'chrome-extension:' → 浏览器扩展

// 5. 注入代码的执行时机
const domReady = document.readyState;
// 'loading'     → DOM 还在解析，最早时机
// 'interactive' → DOM 已解析，脚本可操作
// 'complete'    → 所有资源加载完毕
```

### 输出决策表

| 条件 | 含义 | 后续影响 |
|:--|:--|:--|
| iframe + 同源 | 可以直接访问父页面和 iframe 内部的所有 JS/DOM | 最大自由度 |
| iframe + 跨域 | 只能通过 postMessage 通信 | 只能等消息，不能主动读取 |
| 非 iframe | 代码在主页面上，直接操作 | 无需处理 iframe 穿透 |
| Electron | 可能有 IPC、Node.js API | 检查 `window.vscode`、`require` 等 |

### Cascade 实例

```
结果: iframe + 同源 + Electron + vscode-file: 协议
含义: 可以直接穿透 iframe 访问内部一切，但不在标准 VS Code webview 框架内
```

---

## Phase 1: 标准 API 探测

**目标**: 检查目标是否提供标准的、文档化的通信接口。如果有，直接用，不用逆向。

### 通用检测模板

```javascript
// 模板: 用函数包装拦截来探测 API 是否存在且被调用
function probeApi(apiName, windowObj) {
  windowObj = windowObj || window;

  if (typeof windowObj[apiName] !== 'function') {
    console.log(`[Probe] ${apiName} 不存在`);
    return 'NOT_FOUND';
  }

  const orig = windowObj[apiName];
  let called = false;

  windowObj[apiName] = function() {
    called = true;
    console.log(`[Probe] ${apiName} 被调用`, {
      stack: new Error().stack,
      args: Array.from(arguments).map(a =>
        typeof a === 'object' ? JSON.stringify(a).slice(0, 200) : String(a)
      )
    });
    const result = orig.apply(this, arguments);
    console.log(`[Probe] ${apiName} 返回`, Object.keys(result || {}));
    return result;
  };

  // 超时检查: 如果没被自动调用，尝试直接调用
  setTimeout(() => {
    if (!called) {
      console.log(`[Probe] ${apiName} 未被调用，尝试直接调用`);
      try {
        const result = orig.call(windowObj);
        console.log(`[Probe] 直接调用成功`, Object.keys(result || {}));
      } catch(e) {
        console.log(`[Probe] 直接调用失败: ${e.message}`);
        // "can only be invoked once" → 已被其他代码调用
      }
    }
  }, 5000);

  return 'WRAPPED';
}
```

### 常见标准 API 检查清单

| 平台 | API | 检查方式 |
|:--|:--|:--|
| VS Code Webview | `acquireVsCodeApi` | `typeof window.acquireVsCodeApi` |
| VS Code (主页面) | `window.vscode.ipcRenderer` | `typeof window.vscode?.ipcRenderer?.send` |
| Electron | `require('electron')` | `typeof require` |
| Chrome Extension | `chrome.runtime` | `typeof chrome?.runtime?.sendMessage` |
| 通用 Web | `window.opener` | `typeof window.opener?.postMessage` |

### 决策分支

```
标准 API 存在且正常？
  ├─ 是 → 使用标准 API，流程可结束（或跳到 Phase 5 做增强）
  └─ 否 → 进入 Phase 2
```

---

## Phase 2: 通信通道发现

**目标**: 在标准 API 不可用时，发现目标实际使用的通信机制。三管齐下：扫描全局对象、拦截消息通道、检查页面上下文。

### 2.1 Window 属性扫描

扫描 window 上所有非标准属性，寻找配置对象、认证信息、自定义 API。

```javascript
function scanWindowProps(windowObj) {
  windowObj = windowObj || window;
  const builtins = new Set([
    'location', 'navigator', 'document', 'console', 'performance',
    'localStorage', 'sessionStorage', 'history', 'screen',
    'innerWidth', 'innerHeight', 'scrollX', 'scrollY',
    'fetch', 'XMLHttpRequest', 'WebSocket', 'Promise',
    'Array', 'Object', 'String', 'Number', 'Boolean',
    'Math', 'Date', 'RegExp', 'JSON', 'Map', 'Set',
    'setTimeout', 'setInterval', 'requestAnimationFrame',
    'alert', 'confirm', 'prompt', 'open', 'close',
    'postMessage', 'addEventListener', 'removeEventListener',
    // ... 根据需要扩展
  ]);

  const findings = { functions: [], objects: [], strings: [], other: [] };

  for (const key in windowObj) {
    if (builtins.has(key)) continue;
    if (key.startsWith('on') || key.startsWith('webkit')) continue;
    if (key.startsWith('__')) continue; // 框架内部属性单独处理

    try {
      const val = windowObj[key];
      const type = typeof val;

      if (type === 'function') {
        findings.functions.push(key);
      } else if (type === 'object' && val !== null) {
        findings.objects.push({
          key,
          constructor: val.constructor?.name,
          keys: Object.keys(val).slice(0, 10)
        });
      } else if (type === 'string' && val.length > 10) {
        // 可能是 Base64 编码的配置
        findings.strings.push({
          key,
          length: val.length,
          preview: val.slice(0, 50),
          looksBase64: /^[A-Za-z0-9+/=]+$/.test(val) && val.length > 20
        });
      }
    } catch(e) { /* getter 可能抛异常 */ }
  }

  return findings;
}
```

**关注点**:
- 类似 `chatParams`、`config`、`__config__` 的配置对象
- Base64 编码的长字符串（可能包含 token、URL）
- 以 `_` 开头的自定义属性

### 2.2 配置对象解码

```javascript
// 通用的配置解码尝试
function tryDecodeConfig(value) {
  // 尝试 1: 直接 JSON
  try { return { format: 'json', data: JSON.parse(value) }; } catch(e) {}

  // 尝试 2: Base64 → JSON
  try { return { format: 'base64+json', data: JSON.parse(atob(value)) }; } catch(e) {}

  // 尝试 3: URL 编码
  try {
    const decoded = decodeURIComponent(value);
    if (decoded !== value) {
      return { format: 'urlencode', data: JSON.parse(decoded) };
    }
  } catch(e) {}

  // 尝试 4: URL 查询参数
  try {
    const params = new URLSearchParams(value);
    if (params.toString() === value) {
      return { format: 'query', data: Object.fromEntries(params) };
    }
  } catch(e) {}

  return null;
}
```

### 2.3 postMessage 拦截

```javascript
function interceptPostMessage() {
  const log = [];

  // 出站: 拦截向父页面发送的消息
  if (window.parent !== window) {
    const origPM = window.parent.postMessage.bind(window.parent);
    window.parent.postMessage = function(data, origin) {
      log.push({
        direction: 'OUT',
        timestamp: Date.now(),
        data: typeof data === 'object'
          ? JSON.stringify(data).slice(0, 500)
          : String(data).slice(0, 500),
        origin
      });
      return origPM(data, origin || '*');
    };
  }

  // 入站: 监听收到的消息
  window.addEventListener('message', function(e) {
    log.push({
      direction: 'IN',
      timestamp: Date.now(),
      data: typeof e.data === 'object'
        ? JSON.stringify(e.data).slice(0, 500)
        : String(e.data).slice(0, 500),
      origin: e.origin,
      source: e.source === window.parent ? 'parent' : 'other'
    });
  });

  return {
    getLog: () => log.slice(),
    clear: () => { log.length = 0; }
  };
}
```

### 2.4 框架内部属性扫描

```javascript
// 扫描 DOM 元素上的框架内部属性
function scanFrameworkProps() {
  const results = { react: null, vue: null, angular: null, svelte: null };

  const elements = document.querySelectorAll('*');
  for (let i = 0; i < Math.min(elements.length, 200); i++) {
    const keys = Object.keys(elements[i]);
    for (const key of keys) {
      if (key.startsWith('__reactContainer$') || key.startsWith('__reactFiber$')) {
        results.react = {
          suffix: key.replace(/^__react(Container|Fiber)\$/, ''),
          element: elements[i].tagName + '#' + elements[i].id,
          version: 'Fiber (16+)'
        };
      }
      if (key === '__vue__' || key.startsWith('__vue_')) {
        results.vue = { element: elements[i].tagName + '#' + elements[i].id };
      }
      if (key.startsWith('__ng_')) {
        results.angular = { element: elements[i].tagName + '#' + elements[i].id };
      }
    }
  }

  return results;
}
```

### Phase 2 输出

| 发现类型 | 示例 | 后续动作 |
|:--|:--|:--|
| 认证 token | OAuth, JWT, API key | 记录 → Phase 3 中验证使用方式 |
| 服务器地址 | `127.0.0.1:port`, API URL | 记录 → Phase 3 中确认通信协议 |
| 前端框架 | React Fiber, Vue | 记录 → Phase 5 中用于内部状态访问 |
| postMessage 内容 | 框架消息 vs 业务数据 | 判断是否为主要通信通道 |

---

## Phase 3: 全量网络拦截

**目标**: 同时拦截所有浏览器网络 API，确认目标使用哪种协议通信，建立端点清单。

### 3.1 统一拦截框架

```javascript
function installNetworkInterceptors() {
  const log = [];
  const MAX_ENTRIES = 500;

  function add(type, info) {
    if (log.length >= MAX_ENTRIES) log.shift();
    log.push({
      type,
      info,
      timestamp: Date.now()
    });
  }

  // ──────── fetch 拦截 ────────
  const origFetch = window.fetch;
  window.fetch = function(input, opts) {
    const url = typeof input === 'string'
      ? input
      : (input?.url || String(input));
    const method = opts?.method || 'GET';

    // 记录请求体类型和大小
    let bodyInfo = '';
    if (opts?.body) {
      if (opts.body instanceof Uint8Array || opts.body instanceof ArrayBuffer) {
        const size = opts.body.byteLength || opts.body.length;
        bodyInfo = ` body=binary(${size}B)`;
      } else {
        bodyInfo = ` body=${String(opts.body).slice(0, 200)}`;
      }
    }

    // 记录关键请求头
    const contentType = opts?.headers?.['Content-Type']
      || opts?.headers?.get?.('Content-Type')
      || '';

    add('FETCH-REQ', `${method} ${url.slice(0, 200)}${bodyInfo} ct=${contentType}`);

    return origFetch.apply(this, arguments).then(function(resp) {
      add('FETCH-RESP', `${resp.status} ${url.slice(0, 150)} ct=${resp.headers.get('content-type')}`);
      return resp;
    }).catch(function(err) {
      add('FETCH-ERR', `${url.slice(0, 150)} ${err.message}`);
      throw err;
    });
  };

  // ──────── XMLHttpRequest 拦截 ────────
  const origXhrOpen = XMLHttpRequest.prototype.open;
  const origXhrSend = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.open = function(method, url) {
    this._probe = { method, url: String(url).slice(0, 200) };
    return origXhrOpen.apply(this, arguments);
  };

  XMLHttpRequest.prototype.send = function(body) {
    const p = this._probe || {};
    add('XHR-REQ', `${p.method} ${p.url}`);
    this.addEventListener('load', () => {
      add('XHR-RESP', `${this.status} ${p.url}`);
    });
    return origXhrSend.apply(this, arguments);
  };

  // ──────── WebSocket 拦截 ────────
  const OrigWS = window.WebSocket;
  window.WebSocket = function(url, protocols) {
    add('WS-OPEN', String(url).slice(0, 200));
    const ws = protocols ? new OrigWS(url, protocols) : new OrigWS(url);

    const origWsSend = ws.send.bind(ws);
    ws.send = function(data) {
      const preview = typeof data === 'string'
        ? data.slice(0, 200)
        : `binary(${data.byteLength || data.length || '?'}B)`;
      add('WS-OUT', preview);
      return origWsSend(data);
    };

    ws.addEventListener('message', (e) => {
      const preview = typeof e.data === 'string'
        ? e.data.slice(0, 200)
        : `binary(${e.data.byteLength || e.data.size || '?'}B)`;
      add('WS-IN', preview);
    });

    ws.addEventListener('close', (e) => add('WS-CLOSE', `code=${e.code}`));
    ws.addEventListener('error', () => add('WS-ERR', 'connection error'));
    return ws;
  };
  // ★ 必须保持原型链，否则 instanceof 检查会失败
  window.WebSocket.prototype = OrigWS.prototype;
  window.WebSocket.CONNECTING = OrigWS.CONNECTING;
  window.WebSocket.OPEN = OrigWS.OPEN;
  window.WebSocket.CLOSING = OrigWS.CLOSING;
  window.WebSocket.CLOSED = OrigWS.CLOSED;

  return {
    getLog: () => log.slice(),
    getStats: () => {
      const stats = {};
      for (const entry of log) {
        stats[entry.type] = (stats[entry.type] || 0) + 1;
      }
      return stats;
    },
    clear: () => { log.length = 0; }
  };
}
```

### 3.2 协议识别决策表

拦截一段时间后（建议触发目标的关键操作，如发送消息、切换页面），分析日志：

| 观察到的特征 | 协议判断 | 下一步 |
|:--|:--|:--|
| `FETCH-REQ` + `ct=application/grpc-web+proto` + 二进制 body | **gRPC-Web** | Phase 4 用 protobuf 解码 |
| `FETCH-REQ` + `ct=application/json` | **REST / JSON API** | Phase 4 直接 JSON.parse |
| `FETCH-REQ` + `ct=application/graphql` | **GraphQL** | Phase 4 解析 query/mutation |
| `WS-OPEN` + `WS-IN/OUT` 有大量流量 | **WebSocket** | Phase 4 分析消息格式 |
| `WS-OPEN` + JSON 消息 | **JSON-RPC over WS** | Phase 4 解析 method/params |
| `XHR-REQ` 有流量 | **传统 AJAX** | Phase 4 分析请求/响应 |
| 以上都没有有意义的流量 | 通信不走浏览器网络 API | 检查 Electron IPC、SharedWorker、BroadcastChannel |

### 3.3 端点清单模板

对发现的所有 URL 进行分类：

```markdown
| 端点 URL / 名称 | HTTP 方法 | 功能推测 | 请求体格式 | 响应格式 | 是否流式 |
|:--|:--|:--|:--|:--|:--|
| /api/SendMessage | POST | 发送消息 | JSON | SSE | 是 |
| /api/GetHistory | GET | 获取历史 | - | JSON | 否 |
```

---

## Phase 4: 协议解码

**目标**: 解析请求和响应体的内容，建立端点 → 功能的映射。

### 4.1 按协议选择解码策略

#### JSON / REST

```javascript
// 最简单的情况: 直接拦截并解析 JSON
const origFetch = window.fetch;
window.fetch = function(input, opts) {
  return origFetch.apply(this, arguments).then(resp => {
    const clone = resp.clone(); // ★ 必须 clone
    clone.json().then(data => {
      console.log('[Decode]', input, data);
    }).catch(() => {}); // 非 JSON 响应忽略
    return resp;
  });
};
```

#### gRPC-Web / Protobuf

没有 .proto 文件时的暴力解码方法——提取二进制中的可读字符串和 UUID：

```javascript
function extractStrings(bytes) {
  const parts = [];
  let cur = '';
  for (let i = 0; i < bytes.length; i++) {
    const b = bytes[i];
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

function extractUUIDs(bytes) {
  const str = extractStrings(bytes).join('|');
  return str.match(
    /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/g
  ) || [];
}

// 增强版 fetch 拦截
const origFetch = window.fetch;
window.fetch = function(input, opts) {
  const url = typeof input === 'string' ? input : input?.url || String(input);

  // 解码请求体
  if (opts?.body) {
    try {
      const bytes = opts.body instanceof Uint8Array
        ? opts.body
        : new Uint8Array(opts.body);
      console.log('[REQ]', url, {
        strings: extractStrings(bytes),
        uuids: extractUUIDs(bytes)
      });
    } catch(e) {}
  }

  return origFetch.apply(this, arguments).then(resp => {
    // ★ clone() 后读取，不影响原始流
    const clone = resp.clone();
    clone.arrayBuffer().then(buf => {
      const bytes = new Uint8Array(buf);
      console.log('[RESP]', url, {
        status: resp.status,
        size: bytes.length,
        strings: extractStrings(bytes),
        uuids: extractUUIDs(bytes)
      });
    });
    return resp;
  });
};
```

#### WebSocket

```javascript
// WebSocket 消息通常是 JSON 或自定义二进制
// 在 Phase 3 的拦截基础上增加解码
ws.addEventListener('message', (e) => {
  if (typeof e.data === 'string') {
    try {
      const parsed = JSON.parse(e.data);
      console.log('[WS-JSON]', parsed);
    } catch {
      console.log('[WS-TEXT]', e.data.slice(0, 500));
    }
  } else {
    // Blob 或 ArrayBuffer
    const reader = new FileReader();
    reader.onload = () => {
      const bytes = new Uint8Array(reader.result);
      console.log('[WS-BIN]', {
        size: bytes.length,
        strings: extractStrings(bytes)
      });
    };
    reader.readAsArrayBuffer(e.data);
  }
});
```

### 4.2 关键注意事项

| 问题 | 说明 |
|:--|:--|
| **必须 `resp.clone()`** | 读取 Response body 会消费流，原始调用方将无法读取，导致目标应用崩溃 |
| **流式响应 Content-Length=0** | gRPC/SSE 等流式协议的 Content-Length 可能为 0，数据通过 ReadableStream 分块传输 |
| **二进制 body 不能 toString** | Uint8Array 直接 toString 会得到逗号分隔的数字，需要专门的解码逻辑 |
| **异步时序** | clone().arrayBuffer() 是异步的，日志输出会比实际 UI 渲染稍有延迟 |

---

## Phase 5: 内部状态访问

**目标**: 绕过网络层，直接访问前端框架的内部数据结构，获得最稳定的读写能力。

### 5.1 React Fiber 遍历（React 16+）

```javascript
// 步骤 1: 找到 Fiber 入口
function findFiberRoot(rootElementId) {
  const rootEl = document.getElementById(rootElementId);
  if (!rootEl) return null;

  // 动态发现 suffix（每次 React 挂载都不同）
  const keys = Object.keys(rootEl);
  const containerKey = keys.find(k => k.startsWith('__reactContainer$'));
  if (!containerKey) return null;

  return {
    fiber: rootEl[containerKey],
    suffix: containerKey.replace('__reactContainer$', '')
  };
}

// 步骤 2: BFS 遍历 Fiber 树，用条件函数匹配目标节点
function findFiberNode(rootFiber, matchFn) {
  const queue = [rootFiber];
  const visited = new WeakSet();

  while (queue.length > 0) {
    const fiber = queue.shift();
    if (!fiber || visited.has(fiber)) continue;
    visited.add(fiber);

    if (matchFn(fiber)) return fiber;

    if (fiber.child) queue.push(fiber.child);
    if (fiber.sibling) queue.push(fiber.sibling);
  }
  return null;
}

// 步骤 3: 用 prop 结构匹配（不用组件名！）
// 示例: 找到含有 events + state + layout 的 Context Provider
const contextNode = findFiberNode(root.fiber, fiber => {
  const val = fiber.memoizedProps?.value;
  return val && val.events && val.state && val.layout;
});
```

### 5.2 Vue 实例访问（Vue 2/3）

```javascript
// Vue 2
function findVueRoot(selector) {
  const el = document.querySelector(selector);
  return el?.__vue__;
}

// Vue 3
function findVue3Root(selector) {
  const el = document.querySelector(selector);
  const key = Object.keys(el).find(k => k.startsWith('__vue_'));
  return el?.[key];
}
```

### 5.3 Shape Matching 设计原则

minified / 混淆代码中，变量名和组件名不可靠。使用 **prop 结构匹配**：

```javascript
// ✗ 不要这样做 — 组件名每次构建都会变
fiber.type.name === 'ConversationList'  // 下次可能变成 'k3r'

// ✓ 应该这样做 — 匹配 props 的结构特征
Array.isArray(fiber.memoizedProps?.cascadeIds)  // 业务属性名不会被混淆
  && fiber.memoizedProps.cascadeIds.length > 0
```

**可靠的匹配条件** (从最稳定到最不稳定):

| 稳定性 | 匹配方式 | 示例 |
|:--|:--|:--|
| 高 | Props 键名 + 值类型 | `Array.isArray(props.items)` |
| 高 | Context value 的结构 | `value.events && value.state` |
| 中 | DOM 结构特征 | `fiber.stateNode?.id === 'chat-list'` |
| 低 | 组件 displayName | `fiber.type.displayName === 'ChatList'` |
| 不可靠 | Minified 组件名 | `fiber.type.name === 'k3r'` |

### 5.4 memoizedState 链遍历

React hooks 的状态存储在 Fiber 节点的 memoizedState 链表中：

```javascript
function walkHooksState(fiber) {
  const states = [];
  let hook = fiber.memoizedState;
  let index = 0;

  while (hook) {
    states.push({
      index,
      type: hook.queue ? 'useState/useReducer' : 'other',
      value: hook.memoizedState,
      // 对于 useState: memoizedState 就是当前值
      // 对于 useRef: memoizedState.current
      // 对于 useMemo: memoizedState[0] 是缓存值
    });
    hook = hook.next;
    index++;
  }

  return states;
}
```

---

## Phase 6: 生产化封装

**目标**: 将探测成果转化为稳定的、可维护的 Bridge API。

### 6.1 Bridge 设计模板

```javascript
window._bridge = (function() {
  // ─── 私有状态 ───
  let _cache = {
    context: null,
    contextTime: 0,
    lastData: null,
  };
  const CACHE_TTL = 5000; // 缓存 5 秒

  // ─── 基础设施 ───
  function findFiberSuffix() { /* Phase 5 的实现 */ }
  function findFiberNode(root, matchFn) { /* Phase 5 的实现 */ }

  // ─── 带缓存的查找 ───
  function getContext(forceRefresh) {
    const now = Date.now();
    if (!forceRefresh && _cache.context && now - _cache.contextTime < CACHE_TTL) {
      return _cache.context;
    }

    const root = findFiberRoot('root-element-id');
    if (!root) return _cache.context; // 降级: 返回缓存

    const node = findFiberNode(root.fiber, fiber => {
      // 你的 shape matching 条件
    });

    if (node) {
      _cache.context = node.memoizedProps.value;
      _cache.contextTime = now;
    }

    return _cache.context;
  }

  // ─── 带重试的就绪检测 ───
  function waitForReady(callback, maxRetries) {
    maxRetries = maxRetries || 30;
    let retries = 0;

    const check = () => {
      const ctx = getContext(true);
      if (ctx) {
        callback(null, ctx);
        return;
      }
      retries++;
      if (retries >= maxRetries) {
        callback(new Error('Bridge not ready after max retries'));
        return;
      }
      setTimeout(check, 500);
    };

    check();
  }

  // ─── 公共 API ───
  return {
    isReady: () => !!getContext(),
    waitForReady,

    // 具体的业务方法（根据你的需求实现）
    getData: () => {
      const ctx = getContext();
      if (!ctx) return _cache.lastData; // 降级
      const data = /* 从 ctx 提取数据 */;
      _cache.lastData = data; // 更新缓存
      return data;
    },

    doAction: (params) => {
      const ctx = getContext();
      if (!ctx) throw new Error('Bridge not ready');
      ctx.events.someAction(params);
    }
  };
})();
```

### 6.2 容错设计清单

| 失败场景 | 应对策略 |
|:--|:--|
| 框架尚未挂载 | Polling + 指数退避等待 |
| 目标组件未渲染 | 返回缓存的上一次成功结果 |
| 内部结构发生变化 | Shape matching 条件放宽 + 降级提示 |
| Fiber suffix 变化 | 每次查找前重新扫描 |
| 并发访问冲突 | 使用锁或队列串行化关键操作 |
| 缓存过期 | TTL 机制 + 主动失效 |

### 6.3 探测代码清理

生产部署前移除所有探测代码：

```
✗ 移除: fetch / XHR / WebSocket monkey-patching
✗ 移除: postMessage 拦截
✗ 移除: window 属性扫描
✗ 移除: 调试用的 DOM overlay

✓ 保留: Fiber 遍历 + Shape matching
✓ 保留: Bridge API
✓ 保留: 缓存 + 容错逻辑
✓ 保留: 配置解码（如 chatParams）
```

---

## 附录: 快速参考

### 全流程检查单

```
□ Phase 0: 确认 iframe/同源/Electron/协议
□ Phase 1: 检查标准 API (acquireVsCodeApi, chrome.runtime, etc.)
□ Phase 2: 扫描 window 属性 + postMessage + 框架检测
□ Phase 3: 安装 fetch/XHR/WS 拦截 → 触发关键操作 → 分析日志
□ Phase 4: 根据协议类型选择解码策略 → 建立端点清单
□ Phase 5: 通过框架内部结构直接访问状态 → Shape matching
□ Phase 6: 封装 Bridge API → 缓存 + 容错 → 移除探测代码
```

### 常见协议指纹

| 指纹 | 协议 |
|:--|:--|
| `application/grpc-web+proto` + 二进制 body | gRPC-Web |
| `application/json` + `{"jsonrpc":"2.0"}` | JSON-RPC |
| `text/event-stream` | Server-Sent Events (SSE) |
| `application/graphql` 或 body 含 `query {` | GraphQL |
| WebSocket + JSON `{"type":"...","payload":{}}` | 自定义 WS 协议 |
| WebSocket + 二进制 | 自定义二进制协议 / protobuf over WS |

### monkey-patching 安全要点

```
1. 始终保存原始函数引用: const orig = window.fetch
2. 用 orig.apply(this, arguments) 转发调用，保持 this 和参数完整
3. WebSocket 替换后必须恢复原型链: WebSocket.prototype = OrigWS.prototype
4. 读取 Response body 前必须 clone(): resp.clone().arrayBuffer()
5. 在生产环境中移除所有 monkey-patching，只保留框架内部访问
```
