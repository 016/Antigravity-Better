<div align="center">
  <h1>🚀 Antigravity Better</h1>
  <p><strong>自定义你的 Antigravity AI 聊天面板。你的 IDE，你做主。</strong></p>
  <p><strong>Customize your Antigravity AI chat panel. Your IDE, your rules.</strong></p>
  <br>
  <p>
    <a href="./README.md">English</a> •
    <strong>中文</strong>
  </p>
  <p>
    <img src="https://img.shields.io/badge/version-0.2.13-brightgreen" alt="Version">
    <img src="https://img.shields.io/badge/dependencies-zero-green" alt="Zero Dependencies">
    <img src="https://img.shields.io/badge/file-single%20HTML-blue" alt="Single File">
    <img src="https://img.shields.io/badge/target-Antigravity-purple" alt="Antigravity">
    <img src="https://img.shields.io/github/license/016/Antigravity-Better" alt="License">
    <br><br>
    <a href="https://github.com/016/Antigravity-Better/releases"><img src="https://img.shields.io/badge/⬇️_下载-最新版本-brightgreen?style=for-the-badge" alt="Download"></a>
  </p>
</div>

---

## 📸 截图预览

<p align="center">
  <img src="./screenshots/zh_tab_appearance.png" width="400" alt="外观设置">
  <img src="./screenshots/zh_tab_feature.png" width="400" alt="功能设置">
</p>

---

## ✨ 什么是 Antigravity Better？

**Antigravity Better** 是一个轻量级、零依赖的工具包，用于自定义 **Antigravity**（Google 推出的 AI IDE）的聊天面板。

我们提供一个 **单一 HTML 文件**，只需替换即可解锁强大的自定义功能 - 无需修改源码或安装扩展。

你可以在我们提供的 HTML 文件上自由定制，开发属于你自己的功能。遵循我们预设的框架进行修改非常简单 - 只需添加你的 CSS 规则和 JS 逻辑即可！

> 💡 **理念**：我们铺好高速公路，你想开什么车都行。

### 兼容性说明

- ✅ **主要目标**：Antigravity（Google AI IDE）
  - **v0.2.x**: 支持 IDE v1.18.3+ 系列（全新 `workbench.html` 架构）
  - **v0.1.x**: 支持旧版 IDE(<1.18.3)（基于 `cascade-panel.html` 架构）
- ⚠️ **可能兼容**：其他基于 VS Code 的 AI IDE（如 Cursor、Windsurf 等）可能需要适配，我们无法保证兼容性。

---

## 🚀 功能特性

### 版本发布列表（不完全）

- **v0.2.13**：全面加固高危命令防护、重构 LaTeX 公式渲染引擎与交互体验升级：
  - **高危命令防护加固**：重构高危命令检测引擎，引入通用命令执行前缀匹配（`DANGER_CMD_PREFIX`），覆盖命令行行首、管道、分号、逻辑与、IDE 标签格式（`CommandLine:` / `"CommandLine":`）、引号包装、`sudo`/`xargs`/`bash -c` 与绝对路径；重构 DOM 上下文回溯算法，剔除 Tailwind 通用样式类导致的深度早断，精准提取代码块与终端指令；在作用域权限弹窗中引入双重高危审计，未开启高危开关时精准自动点击 `Skip` 并触发 5 秒安全熔断，实现高危命令 100% 拦截与常用开发指令 0 误杀。
  - **LaTeX 渲染引擎增强**：支持公式内部 `<br>` 换行智能清洗与相邻文本节点无缝缝合（`elem.normalize()`），彻底根治带前置说明文字的多行复杂公式渲染失败问题；新增 HTML 实体自动反转义（`&gt;`, `&lt;`, `&quot;`, `&#39;`, `&nbsp;`），消除不等式语法导致的 KaTeX 解析报错；引入环境感知对齐符处理（`aligned`/`cases`/`matrix` 等环境内保留对齐符 `&`，环境外自动转义为 `\&` 杜绝语法崩溃）；自动修复 Markdown 吞噬行间距反斜杠（`\[...pt]` 自动恢复为 `\\[...pt]`）与行尾单反斜杠；全面支持在 `$$...$$` 块级与 `\[...\]` 公式中自动解包由下划线转换而来的 `<em>`/`<strong>` 格式标签。
  - **交互体验与安全确认升级**：新增高危命令执行独立开关与二次确认弹窗（明确提醒工作范围、规范操作行为与 Git 备份）；设置面板功能菜单默认收起折叠且置顶“自动操作”；操作反馈引入双色分流 Toast（绿色跳过/红色警示放行）与浮层统计实时同步。
- **v0.2.11**：新增 `Submit` 自动点击支持，并增加了问卷弹窗保护；新增 `Submit`、`Tool Permissions` 独立开关，支持一键放行常规工具权限申请；修复了高危命令过滤在同级容器内的检测盲区。
- **v0.2.10**：修复对话中 Undo 图标未正确渲染的问题，原因是 CSP 未放行所需的 Google 相关资源；本次通过补充相关策略完成修复，方案来自 hanliangwei。
- **v0.2.9**：修复新建对话时误点历史会话标题的问题；当按钮同时带有 `title` 且包含 `grow` 类名时，跳过自动点击。
- **v0.2.8**：修复程序内版本号仍显示为 `0.2.2` 的问题，并同步整理文档版本信息。
- **v0.2.7**：增强更新检测（GitHub API + 备用 API 回退），支持显示当前/远端版本对比，新增“下载更新”入口和系统工具“自动关闭安装损坏提示”。
- **v0.2.6**：为 diff 确认与权限提示增加自动接受规则，更安全处理 `accept all`、`always allow`、`allow this conversation` 操作。
- **v0.2.5**：优化 workbench UI，emoji 图标替换为内联 SVG，改进 Tab 对齐、悬浮设置按钮、检测更新按钮和关闭按钮点击区域。
- **v0.2.4**：修复 LaTeX 行内公式渲染问题（#23）。
- **v0.2.3**：新增 `workbench.html` 部署工具。
- **v0.2.2**：修复复制按钮显示错位与自动操作点击问题，增加最大点击次数限制与清零功能。
- **v0.2.1**：迁移到 IDE v1.18.3+ 的 `workbench.html` 新架构，实现对 v0.1.7 功能平移。
- **v0.1.7**：旧架构稳定版本（`cascade-panel.html`）。
- **v0.1.6**：将自动重试能力合并到自动操作。
- **v0.1.5**：新增 LaTeX 公式渲染能力。
- **v0.1.4**：新增字体大小控制与版本检测。
- **v0.1.3**：新增安全规则，阻止危险命令自动执行。
- **v0.1.2**：新增自动重试机制。
- **v0.1.1**：首批核心能力：自定义颜色、快捷键覆盖与中英文支持。

### 开发者友好

- **单文件架构**：所有 CSS/JS/HTML 集成在一个文件
- **零构建工具**：无需 npm、无需打包 - 直接编辑替换
- **性能优先**：禁用的功能 = 零运行时开销
- **注释清晰**：代码结构明确，易于理解
- **易于扩展**：按照简单模式添加你自己的功能

---

## 📦 安装方法

### 快速开始

1. **找到目标文件**
   ```
   macOS: /Applications/Antigravity.app/Contents/Resources/app/out/vs/code/electron-browser/workbench/workbench.html
   Windows: [应用安装目录]/Antigravity/resources/app/out/vs/code/electron-browser/workbench/workbench.html
   ```

2. **备份并替换**
   ```bash
   # 进入安装目录
   ## Mac os
   cd /Applications/Antigravity.app/Contents/Resources/app/out/vs/code/electron-browser/workbench/
   ## Windows
   cd [应用安装目录]/Antigravity/resources/app/out/vs/code/electron-browser/workbench/

   # 备份原文件
   cp workbench.html workbench.html.bak
   
   # 替换为 Antigravity Better
   cp /path/to/antigravity-better/app_root/workbench.html ./
   ```

3. **重启 Antigravity** - 完成！🎉

> ⚠️ **注意**：每次 Antigravity 版本升级时，都会覆盖这个 HTML 文件。升级后需要重新执行一次替换操作。

### 🛠️ 常见问题处理 (Mac OS)

如果你在 Mac OS 上（特别是 **v1.20.5** 版本）遇到 **“文件已损坏，应移至废纸篓”** 的提示，请按照以下步骤操作：

1. 选择 **取消** 以保留文件。
2. 进入 **“系统设置”** -> **“隐私与安全性”** -> **“安全性”** 部分。
3. 你会看到对应的 Antigravity 被阻拦的信息，点击 **“仍要打开”**。
4. 再次尝试打开 Antigravity。在弹出的选项中选择 **“打开”**（可能需要**鼠标右键点击**应用并选择 **“打开”**，而不是直接双击）。
5. 只需要这样操作一次，给予运行权限后就不会再出问题。

*注：目前仅在 macOS 平台上进行了测试，其他平台可能会遇到类似问题，请自行寻找对应的系统权限解决方案。*

---

## 🛠️ 自定义配置

### 使用设置面板

点击聊天面板右侧的 **⚙️ 悬浮按钮** 打开设置。

- 在 **外观** 和 **功能** 选项卡之间切换
- 展开/折叠各个功能区块
- 点击右上角按钮切换 中文/English

### 添加自己的功能

Antigravity Better 专为扩展设计：

```html
<style>
  /* 1. 添加 CSS - 仅在功能启用时生效 */
  #react-app.your-feature .target { color: red; }
</style>

<script>
  // 2. 添加功能配置
  const YOUR_CONFIGS = [{ id: 'my-feature', ... }];
  
  // 3. 实现逻辑（遵循开关状态）
  function applyYourFeature() {
    if (!currentSettings.yourFeatureEnabled) return;
    // 你的代码
  }
</script>
```

---

## 🤝 参与贡献

欢迎各种形式的贡献：

- 🐛 Bug 反馈
- 💡 功能建议
- 🔧 Pull Request
- 📖 文档完善

### 🌟 贡献者

感谢所有优秀的贡献者！你们太棒了！💖

| 贡献者 | 贡献内容 | 日期 |
|--------|----------|------|
| [@moshouhot](https://github.com/moshouhot) | 🤖 自动操作 + 🛡️ 安全规则 - 可配置按钮自动点击，支持危险命令过滤 | 2026-01-24 |
| [@chengcodex](https://github.com/chengcodex) | 🔄 自动重试 - 智能错误检测与自动重试，采用 XPath 优化性能（v0.1.6 已合并到自动操作） | 2026-01-23 |

---

## 📜 开源协议

MIT License - 自由使用、修改、分享。

---

## 🔗 链接

- 🌐 官网：[dpit.lib00.com](https://dpit.lib00.com)
- 🐛 问题反馈：[GitHub Issues](https://github.com/016/Antigravity-Better/issues)

---

<div align="center">
  <sub>Built with ❤️ by the Antigravity Better Team</sub>
</div>
