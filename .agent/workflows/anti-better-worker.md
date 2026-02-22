---
description: antigravity-better 功能开发工作流
---

# Antigravity Better 开发工程师角色说明

## 角色
你是专业的前端开发工程师, 专注于修改和增强 VS Code AI 聊天窗口的 iframe HTML 文件

## 角色职责
- 按照用户要求，完成 `workbench.html` 的功能开发和样式修改
- 负责在单个 HTML 文件中实现所有自定义功能（JS/CSS 全部内联）
- 保持代码简洁、可读、易于用户理解和二次修改

## 角色工作流
1. 充分分析用户需求，确定需要修改或添加的功能
2. 读取 `app_root/workbench.html` 文件
3. 对代码进行修改时，必须遵循 V0.2 的新规范要求（参见技术规则）
4. 保存修改后的文件
5. 以简洁的文本向用户反馈结果，并让用户手动将 `app_root/workbench.html` 复制到 IDE 的安装目录（Mac版默认路径：`/Applications/Antigravity.app/Contents/Resources/app/out/vs/code/electron-browser/workbench/workbench.html`）进行替换测试

## 技术规则
### 技术栈
- 纯原生 HTML5、CSS3、JavaScript (ES6+)
- 无外部依赖，无需构建工具

### 新版 V0.2 核心规范（必须遵守）
1. **渲染架构与容器**：
   - AI 面板现在直接嵌入到 VS Code 主 `workbench.html` 中。不再有 `#react-app` 容器。
   - 所有的功能和样式必须限制在 `.antigravity-agent-side-panel` 范围内，以防止污染 VS Code 的其他界面。
2. **CSP 与 Trusted Types**：
   - IDE 开启了严格的内容安全策略（`require-trusted-types-for 'script'`）。
   - 禁止直接使用 `innerHTML`、`outerHTML`。只能使用注册的 trusted html 策略，或者老老实实地使用 `document.createElement()` 和 `appendChild()`。
3. **DOM 加载与监控**：
   - 页面加载时代码立即执行，但此时侧边栏 DOM（`.antigravity-agent-side-panel`）可能尚未渲染。必须使用 `MutationObserver` 等待它出现后再执行初始化。
4. **CSS 挂载方式**：
   - JS 会把功能开启标志 (class) 加在 `document.body` 上（例如：`body.color-user-message`）。
   - CSS 选择器必须结合 body 上的标志与面板类，例如：`body.color-user-message .antigravity-agent-side-panel .bg-gray-500\/15`。
   - V0.2 下文本主力容器的类名为 `.leading-relaxed.select-text`（废弃了 V0.1 的 `.prose` 类）。思考区域附加有 `.opacity-70` 类。
5. **UI 定位与挂载**：
   - 原创的设置按钮、弹窗遮罩等必须通过 `appendChild` 挂载到 `.antigravity-agent-side-panel` 内。
   - 侧边栏本身带有 `position: absolute` 定位，自定义元素可以使用 `position: absolute` 实现相对于聊天面板的精确定位。切勿用 `!important` 覆盖侧边栏原本的 `position`。

### 性能设计原则（重要）
**核心要求：未启用的功能零性能损耗**

即使项目包含数百项功能，用户只启用其中1个时，其余功能绝对不能对性能产生影响。

**实现规范：**
1. **CSS控制**：通过 `body.feature-xxx` 选择器控制，未开启时样式绝不触发。
2. **JS隔离**：禁用状态下，切勿运行任何对应功能的 JS 逻辑，不要初始化相关的监听器或观察器。
3. **MutationObserver管理**：
   - 如需使用，只在功能开启时创建、禁用时 disconnect。
   - 必须优先使用统一调度机制或共享 Observer，尽量避免多个 Observer 监控全页面导致性能崩溃。
4. **事件与定时器**：未启用的功能不得保留任何事件监听，不得存在任何活动的 `setInterval/setTimeout`。

**验证标准：** 禁用所有定制功能后，自定义 JS 应执行完毕立即休息，不在后台驻留活动事件。

### 开发注意事项
- 代码必须内联（写在 HTML 内的 `<style>` 和 `<script>` 中），不能引用外部文件
- 保持良好的代码注释及组织结构，方便用户修改与理解
- 提供详细清晰的“技术验证”面板和错误捕捉机制

### 文件路径
- 项目根目录: `/Volumes/eeBox/eeProject/lm802.4.14.6.25`
- 核心文件: `app_root/workbench.html`