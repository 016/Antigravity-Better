# Antigravity Bridge Extension

## 🌉 What is this?
This is a companion local bridge extension for **Antigravity Better**. It runs a local server to enable capabilities that are restricted in the web-based chat panel, such as:
1.  **Secure API Requests** (Crossing CORS boundaries)
2.  **Secure Storage** (Retaining API keys in VS Code's Secret Storage)
3.  **Local System Integration** (Future capabilities)

## 🚀 Features
- **Local API Proxy**: Relays requests to OpenRouter/DeepSeek APIs.
- **Port Conflict Detection**: Automatically detects if Port 54321 is in use and warns you.
- **Secure Key Storage**: Encrypts and stores your OpenRouter API key using VS Code's native Secret Storage API.
- **Zero Configuration**: Just install and it runs automatically in the background.

## 📦 Installation
1.  Download the `.vsix` file from releases.
2.  In VS Code/Antigravity:
    - Go to **Extensions** view (`Ctrl+Shift+X`).
    - Click the `...` menu (Views and More Actions).
    - Select **Install from VSIX...**
    - Choose the `antigravity-bridge-x.x.x.vsix` file.
3.  The extension will start automatically (Check the blue status bar item).

## 🔧 Technical Details
- **Server Port**: `54321` (localhost)
- **Endpoints**:
    - `POST /translate`: Handles AI translation requests.
    - `POST /save-key`: Securely saves API keys.
    - `GET /status`: Checks server health and key existence.

## 📝 Troubleshooting
**"Bridge Port Conflict" Error?**
If you see this error, another application is using port 54321. Please close other instances of VS Code or applications using this port, then reload the window.

---
*Built for Antigravity Better*
