/**
 * Phase 1 scaffold — not published to the marketplace.
 * Opens the local panel server (ide/multi-agent-panel/server.py) in a webview.
 */
import * as vscode from "vscode";

const DEFAULT_PANEL_URL = "http://127.0.0.1:9876/";

export function activate(context: vscode.ExtensionContext): void {
  const disposable = vscode.commands.registerCommand("multiAgent.openPanel", () => {
    const panel = vscode.window.createWebviewPanel(
      "multiAgentPanel",
      "Multi-Agent Panel",
      vscode.ViewColumn.One,
      { enableScripts: true }
    );
    panel.webview.html = `<!DOCTYPE html><html><body style="margin:0;padding:0;height:100vh;">
      <iframe src="${DEFAULT_PANEL_URL}" style="border:0;width:100%;height:100%;"></iframe>
      <p style="font-family:sans-serif;padding:8px;">Start panel: python3 ide/multi-agent-panel/server.py --port 9876</p>
    </body></html>`;
  });
  context.subscriptions.push(disposable);
}

export function deactivate(): void {}
