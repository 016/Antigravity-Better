<div align="center">
  <h1>🚀 Antigravity Better</h1>
  <p><strong>自定义你的 Antigravity AI 聊天面板。你的 IDE，你做主。</strong></p>
  <p><strong>Customize your Antigravity AI chat panel. Your IDE, your rules.</strong></p>
  <br>
  <p>
    <strong>English</strong> •
    <a href="./README_ZH.md">中文</a>
  </p>
  <p>
    <img src="https://img.shields.io/badge/version-0.2.10-brightgreen" alt="Version">
    <img src="https://img.shields.io/badge/dependencies-zero-green" alt="Zero Dependencies">
    <img src="https://img.shields.io/badge/file-single%20HTML-blue" alt="Single File">
    <img src="https://img.shields.io/badge/target-Antigravity-purple" alt="Antigravity">
    <img src="https://img.shields.io/github/license/016/Antigravity-Better" alt="License">
    <br><br>
    <a href="https://github.com/016/Antigravity-Better/releases"><img src="https://img.shields.io/badge/⬇️_Download-Latest_Release-brightgreen?style=for-the-badge" alt="Download"></a>
  </p>
</div>

---

## 📸 Screenshots

<p align="center">
  <img src="./screenshots/en_tab_appearance.png" width="400" alt="Appearance Settings">
  <img src="./screenshots/en_tab_feature.png" width="400" alt="Feature Settings">
</p>

---

## ✨ What is Antigravity Better?

**Antigravity Better** is a lightweight, zero-dependency toolkit for customizing the AI chat panel in **Antigravity** - Google's new AI-powered IDE.

We provide a **single HTML file** that you can drop into your IDE to unlock powerful customizations - without touching any source code or installing extensions.

You can freely customize this HTML file to build your own features. Following our pre-built framework makes modifications incredibly easy - just add your CSS rules and JS logic, and you're good to go!

> 💡 **Philosophy**: We build the highway; you drive whatever car you want.

### Compatibility Note

- ✅ **Primary Target**: Antigravity (Google's AI IDE)
  - **v0.2.x**: Supports IDE v1.18.3+ (New `workbench.html` architecture)
  - **v0.1.x**: Supports older IDE versions(<1.18.3) (Legacy `cascade-panel.html` architecture)
- ⚠️ **Potentially Compatible**: Other VS Code-based AI IDEs (Cursor, Windsurf, etc.) may work with modifications, but we cannot guarantee compatibility.

---

## 🚀 Features

### Release Timeline (Partial)

- **v0.2.11**: Adds `Submit` auto-accept support with questionnaire modal protection, introduces `Submit`and`Tool Permissions` independent toggle to bypass normal tool permission prompts, and fixes a blind spot in the high-risk command filter for elements within the same container.
- **v0.2.10**: Fixes the Undo icon rendering issue in conversations by allowing the required Google resources in the Content Security Policy. The fix proposal came from hanliangwei.
- **v0.2.9**: Fixes accidental auto-clicks on conversation titles when creating a new conversation by skipping title buttons that carry both `title` and `grow`.
- **v0.2.8**: Fixes the app version string that was still shown as `0.2.2`, and aligns documentation version info.
- **v0.2.7**: Enhances update checks with dual-source fallback (GitHub API + backup API), shows current/remote version comparison, adds a download entry, and introduces an auto-dismiss system tool for corrupted-install warnings.
- **v0.2.6**: Adds auto-accept rules for diff confirmations and permission prompts, with safer handling for `accept all`, `always allow`, and `allow this conversation`.
- **v0.2.5**: Improves workbench UI, replaces emoji icons with inline SVG, and refines tab alignment, floating settings button, update-check button style, and close-button hit area.
- **v0.2.4**: Fixes LaTeX inline formula rendering issue (#23).
- **v0.2.3**: Adds a deployment tool for `workbench.html`.
- **v0.2.2**: Fixes copy button misalignment and auto-accept click issues, and adds max-click limit with reset.
- **v0.2.1**: Migrates to IDE v1.18.3+ `workbench.html` architecture with v0.1.7 feature parity.
- **v0.1.7**: Stable legacy-architecture release (`cascade-panel.html`).
- **v0.1.6**: Merges auto-retry capability into auto-accept.
- **v0.1.5**: Adds LaTeX formula rendering.
- **v0.1.4**: Adds font-size control and version check.
- **v0.1.3**: Adds safety rules to block dangerous auto-executed commands.
- **v0.1.2**: Adds auto-retry mechanism.
- **v0.1.1**: First core feature set: custom colors, hotkey override, and i18n support.

### For Developers

- **Single-file architecture**: All CSS/JS/HTML in one file
- **Zero build tools**: No npm, no bundler - just edit and replace
- **Performance-first**: Disabled features = zero runtime cost
- **Well-documented**: Clear code structure with comments
- **Extensible**: Add your own features following simple patterns

---

## 📦 Installation

### Quick Start

1. **Locate the target file**
   ```
   macOS: /Applications/Antigravity.app/Contents/Resources/app/out/vs/code/electron-browser/workbench/workbench.html
   Windows: [PathToAppFolder]/Antigravity/resources/app/out/vs/code/electron-browser/workbench/workbench.html
   ```

2. **Backup & Replace**
   ```bash
   # Navigate to the installation directory
   ## Mac os
   cd /Applications/Antigravity.app/Contents/Resources/app/out/vs/code/electron-browser/workbench/
   ## Windows
   cd [PathToAppFolder]/Antigravity/resources/app/out/vs/code/electron-browser/workbench/

   # Backup original
   cp workbench.html workbench.html.bak
   
   # Replace with Antigravity Better
   cp /path/to/antigravity-better/app_root/workbench.html ./
   ```

3. **Restart Antigravity** - Done! 🎉

> ⚠️ **Note**: Every time Antigravity updates, it will overwrite the HTML file. You'll need to re-apply this replacement after each update.

### 🛠️ Troubleshooting (Mac OS)

If you encounter a **"File is damaged and should be moved to the Trash"** warning on Mac OS (especially in **v1.20.5**), follow these steps:

1. Click **Cancel** to keep the file.
2. Go to **System Settings** -> **Privacy & Security** -> **Security**.
3. You should see a message saying "Antigravity was blocked...". Click **Allow Anyway** or **Open Anyway**.
4. Open Antigravity again. When the dialog appears, select **Open** (you may need to **right-click** the app and select **Open** instead of using double-click).
5. This only needs to be done once to grant permission.

*Note: We have only tested this on macOS. Other platforms might encounter similar issues; please look for system-specific security permission solutions.*

---

## 🛠️ Customization

### Using the Settings Panel

Click the **⚙️ floating button** on the right side of your chat panel to open settings.

- Switch between **Appearance** and **Features** tabs
- Expand/collapse each feature section
- Toggle language between English/中文

### Adding Your Own Features

Antigravity Better is designed to be extended:

```html
<style>
  /* 1. Add your CSS - only active when feature class is present */
  #react-app.your-feature .target { color: red; }
</style>

<script>
  // 2. Add your feature config
  const YOUR_CONFIGS = [{ id: 'my-feature', ... }];
  
  // 3. Implement your logic (respecting on/off state)
  function applyYourFeature() {
    if (!currentSettings.yourFeatureEnabled) return;
    // Your code here
  }
</script>
```

---

## 🤝 Contributing

We welcome contributions! Whether it's:

- 🐛 Bug reports
- 💡 Feature ideas
- 🔧 Pull requests
- 📖 Documentation

### 🌟 Contributors

A huge thank you to all our amazing contributors! 💖

| Contributor | Contribution | Date |
|-------------|--------------|------|
| [@moshouhot](https://github.com/moshouhot) | 🤖 Auto Accept + 🛡️ Safety Rules - Configurable button auto-click with dangerous command filtering | 2026-01-24 |
| [@chengcodex](https://github.com/chengcodex) | 🔄 Auto Retry - Smart error detection and auto-retry with XPath optimization (merged into Auto Accept in v0.1.6) | 2026-01-23 |

---

## 📜 License

MIT License - Use it, modify it, share it.

---

## 🔗 Links

- 🌐 Website: [dpit.lib00.com](https://dpit.lib00.com)
- 🐛 Issues: [GitHub Issues](https://github.com/016/Antigravity-Better/issues)

---

<div align="center">
  <sub>Built with ❤️ by the Antigravity Better Team</sub>
</div>
