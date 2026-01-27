const vscode = require('vscode');
const http = require('http');
const https = require('https');

const SERVER_PORT = 54321;
let server;

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
    console.log('Antigravity Bridge is now active!');
    vscode.window.showInformationMessage('Antigravity Bridge: EXTENSION LOADED');

    // Register Manual Command
    context.subscriptions.push(vscode.commands.registerCommand('antigravityBridge.forceStart', () => {
        vscode.window.showInformationMessage('Antigravity Bridge Force Started!');
        checkServer();
    }));

    // Auto-Start Check
    checkServer();

    function checkServer() {
        if (!server) { startServer(); }
    }

    function startServer() {
        // Debug: Visual Proof of Activation
        const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
        statusBar.text = "$(broadcast) Antigravity Bridge";
        statusBar.tooltip = "Bridge Server Running on Port 54321";
        statusBar.show();
        context.subscriptions.push(statusBar);

        // Create a local HTTP server
        server = http.createServer(async (req, res) => {
            // Handle CORS
            res.setHeader('Access-Control-Allow-Origin', '*');
            res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
            res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

            if (req.method === 'OPTIONS') {
                res.writeHead(204);
                res.end();
                return;
            }

            // Parse JSON body
            let body = '';
            req.on('data', chunk => { body += chunk.toString(); });
            req.on('end', async () => {
                try {
                    const data = body ? JSON.parse(body) : {};

                    // --- Routes ---

                    // 1. Health Check
                    if (req.url === '/status' && req.method === 'GET') {
                        const apiKey = await context.secrets.get('openrouter_key');
                        res.writeHead(200, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify({
                            status: 'ok',
                            version: '0.1.0',
                            hasKey: !!apiKey
                        }));
                        return;
                    }

                    // 2. Save API Key (Securely)
                    if (req.url === '/save-key' && req.method === 'POST') {
                        const { apiKey } = data;
                        if (!apiKey) throw new Error('Missing apiKey');

                        await context.secrets.store('openrouter_key', apiKey);

                        res.writeHead(200, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify({ success: true }));
                        return;
                    }

                    // 3. Translate (Call OpenRouter)
                    if (req.url === '/translate' && req.method === 'POST') {
                        const { text, targetLang, model = 'tngtech/deepseek-r1t2-chimera:free', sourceLang } = data;
                        if (!text) throw new Error('Missing text');

                        // Retrieve Key
                        const apiKey = await context.secrets.get('openrouter_key');
                        if (!apiKey) {
                            res.writeHead(401, { 'Content-Type': 'application/json' });
                            res.end(JSON.stringify({ error: 'API Key not found. Please set it in settings.' }));
                            return;
                        }

                        // Improved translation prompt - STRICT no-preamble output
                        const systemPrompt = `You are a translation engine. Your ONLY job is to output the translated text.

ABSOLUTE RULES:
- Output ONLY the translation, nothing else
- NEVER include phrases like "Here is the translation", "Translation:", "Sure!", "Of course", or any introduction
- NEVER add explanations, notes, or commentary
- NEVER wrap the output in quotes or markdown
- NEVER mention the languages involved
- Just output the raw translated text, as if you ARE the translation itself

Translate from ${sourceLang || 'auto-detect'} to ${targetLang || 'English'}.`;

                        const payload = {
                            model: model,
                            messages: [
                                { role: 'system', content: systemPrompt },
                                { role: 'user', content: text }
                            ],
                            temperature: 0.2, // Even lower for more deterministic output
                            max_tokens: 4096
                        };

                        console.log(`[Bridge] Translating with model: ${model}`);
                        console.log(`[Bridge] ${sourceLang || 'auto'} -> ${targetLang || 'English'}`);

                        try {
                            const openRouterResponse = await doRequest('https://openrouter.ai/api/v1/chat/completions', {
                                method: 'POST',
                                headers: {
                                    'Authorization': `Bearer ${apiKey}`,
                                    'Content-Type': 'application/json',
                                    'HTTP-Referer': 'https://github.com/016/Antigravity-Better',
                                    'X-Title': 'Antigravity Better'
                                },
                                body: JSON.stringify(payload)
                            });

                            // Parse OpenRouter Response
                            const result = JSON.parse(openRouterResponse);

                            // Handle API errors with detailed messages
                            if (result.error) {
                                console.error('[Bridge] OpenRouter Error:', result.error);
                                const errorMsg = result.error.message || result.error.code || 'Unknown OpenRouter Error';
                                res.writeHead(400, { 'Content-Type': 'application/json' });
                                res.end(JSON.stringify({
                                    error: errorMsg,
                                    code: result.error.code,
                                    model: model
                                }));
                                return;
                            }

                            const translatedText = result.choices?.[0]?.message?.content?.trim();
                            if (!translatedText) {
                                console.error('[Bridge] Empty response from model');
                                throw new Error('No translation returned from model');
                            }

                            console.log(`[Bridge] Translation successful (${translatedText.length} chars)`);

                            res.writeHead(200, { 'Content-Type': 'application/json' });
                            res.end(JSON.stringify({
                                translation: translatedText,
                                model: model,
                                usage: result.usage // Include token usage info
                            }));
                            return;

                        } catch (apiError) {
                            console.error('[Bridge] API Request Failed:', apiError.message);
                            res.writeHead(500, { 'Content-Type': 'application/json' });
                            res.end(JSON.stringify({
                                error: `API Error: ${apiError.message}`,
                                model: model
                            }));
                            return;
                        }
                    }

                    // 404 Not Found
                    res.writeHead(404);
                    res.end(JSON.stringify({ error: 'Not Found' }));

                } catch (err) {
                    console.error('Bridge Error:', err);
                    res.writeHead(500, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: err.message }));
                }
            });
        });

        server.listen(SERVER_PORT, '127.0.0.1', () => {
            console.log(`Bridge Server running on http://127.0.0.1:${SERVER_PORT}`);
        });

        // Port conflict detection
        server.on('error', (err) => {
            if (err.code === 'EADDRINUSE') {
                vscode.window.showErrorMessage(
                    `Antigravity Bridge: Port ${SERVER_PORT} is in use. Please close the conflicting application.`
                );
                statusBar.text = "$(error) Bridge Port Conflict";
                statusBar.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
            } else {
                console.error('Bridge Server Error:', err);
            }
        });
    }
}

/**
 * Helper to make HTTPS requests
 */
function doRequest(url, options) {
    return new Promise((resolve, reject) => {
        const req = https.request(url, options, (res) => {
            let data = '';
            res.on('data', (chunk) => { data += chunk; });
            res.on('end', () => { resolve(data); });
        });
        req.on('error', (e) => { reject(e); });
        if (options.body) req.write(options.body);
        req.end();
    });
}

function deactivate() {
    if (server) {
        server.close();
    }
}

module.exports = {
    activate,
    deactivate
};
