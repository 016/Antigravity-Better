---
trigger: always_on
---

# Project basic rule

## 基本信息
这是一个 **HTML 注入脚本项目**，核心目标是**自定义 VS Code AI 聊天窗口的 iframe 界面**（如修改 AI 回复颜色、添加复制按钮等）。
项目采用 **HTML 直接覆盖** 模式，用户只需将修改后的 HTML 文件替换原始文件即可生效。

## Rules
- **单文件原则**: 所有自定义 JS、CSS 和新增 HTML 代码都必须内联写入 `workbench.html` 文件中。
- **零依赖**: 不依赖任何外部库或构建工具，保持纯原生 HTML/CSS/JS。
- **KISS 原则**: 保持实现简单，方便用户复制替换文件。
- **零基础友好**: 代码和注释需清晰，方便用户理解和二次修改。

## 技术架构 (Architecture)
1. **CSS 层**: 内联 `<style>` 标签，定义所有样式覆盖和自定义主题。
2. **JS 层**: 内联 `<script>` 标签，实现 DOM 监听、样式注入、功能增强（如复制按钮）。
3. **HTML 层**: 在原有结构基础上添加必要的容器或元素。

## 开发环境
- **运行环境**: Mac OS (宿主)
- **项目根目录**: `/Volumes/eeBox/eeProject/lm802.4.14.6.25`
- **应用目录**: `./app_root`
- **核心文件**: `./app_root/workbench.html`

## 设计要求
- 主题上要求简洁、精致、专业、好看、大气
- 功能需高度可配置，通过 JS 变量控制特性开关（如颜色、按钮）

## 工作流程自动匹配
- 本项目涉及两个类型的工作, 根据收到的任务类型自动匹配下面的工作流程
    - html页面核心修改/设计工作匹配 html-worker(.agent/workflows/html-worker.md)
    - workbench.html 功能开发工作匹配 anti-better-worker(.agent/workflows/anti-better-worker.md)
    - 其他未匹配工作则使用默认流程

## 核心项目文件
- `app_root/workbench.html`: AI 侧边栏的 HTML 文件，所有针对 V0.2 的自定义代码都写在这里。

## 用户使用方式
用户将修改后的 `workbench.html` 文件复制替换到 IDE 对应位置即可生效。