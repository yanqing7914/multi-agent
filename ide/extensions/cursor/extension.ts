/**
 * Cursor extension scaffold — same webview pattern as VS Code, Cursor-specific branding.
 */
import * as vscode from "vscode";

const PANEL_URL = process.env.MULTI_AGENT_PANEL_URL || "http://127.0.0.1:9876/";

export function activate(context: vscode.ExtensionContext): void {
  context.subscriptions.push(
    vscode.commands.registerCommand("multiAgentCursor.openPanel", () => {
      const panel = vscode.window.createWebviewPanel(
        "multiAgentCursorPanel",
        "Multi-Agent (Cursor)",
        vscode.ViewColumn.Beside,
        { enableScripts: true, retainContextWhenHidden: true }
      );
      panel.webview.html = `<!DOCTYPE html><html><body style="margin:0;height:100vh;">
        <iframe src="${PANEL_URL}" style="width:100%;height:100%;border:0;"></iframe>
      </body></html>`;
      vscode.window.showInformationMessage(
        "Panel expects: python3 ide/multi-agent-panel/server.py --port 9876"
      );
    })
  );
}

export function deactivate(): void {}
