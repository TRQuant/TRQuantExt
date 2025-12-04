/**
 * 策略优化器面板
 * ===============
 * 
 * 显示策略分析结果和优化建议
 */

import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { OptimizationReport } from '../services/strategyOptimizer/analyzer/optimizationAdvisor';
import { logger } from '../utils/logger';

// 直接导入策略优化器服务
let strategyOptimizerInstance: any = null;

async function getStrategyOptimizer() {
    if (!strategyOptimizerInstance) {
        const module = await import('../services/strategyOptimizer');
        // 尝试获取导出的实例
        strategyOptimizerInstance = (module as any).strategyOptimizer || 
                                   (module as any).StrategyOptimizerService?.getInstance();
    }
    return strategyOptimizerInstance;
}

const MODULE = 'StrategyOptimizerPanel';

export class StrategyOptimizerPanel {
    public static currentPanel: StrategyOptimizerPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private _disposables: vscode.Disposable[] = [];
    private _report: OptimizationReport | null = null;

    private constructor(
        panel: vscode.WebviewPanel,
        extensionUri: vscode.Uri
    ) {
        this._panel = panel;
        this._extensionUri = extensionUri;

        this._panel.webview.onDidReceiveMessage(
            message => this.handleMessage(message),
            null,
            this._disposables
        );

        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
    }

    public static createOrShow(
        extensionUri: vscode.Uri,
        code?: string,
        fileName?: string
    ): StrategyOptimizerPanel {
        const column = vscode.ViewColumn.One;

        if (StrategyOptimizerPanel.currentPanel) {
            StrategyOptimizerPanel.currentPanel._panel.reveal(column);
            if (code) {
                StrategyOptimizerPanel.currentPanel.analyzeStrategy(code, fileName);
            }
            return StrategyOptimizerPanel.currentPanel;
        }

        const panel = vscode.window.createWebviewPanel(
            'strategyOptimizer',
            '🔍 策略优化器',
            column,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [extensionUri]
            }
        );

        StrategyOptimizerPanel.currentPanel = new StrategyOptimizerPanel(panel, extensionUri);
        
        if (code) {
            StrategyOptimizerPanel.currentPanel.analyzeStrategy(code, fileName);
        } else {
            StrategyOptimizerPanel.currentPanel.updateContent();
        }
        
        return StrategyOptimizerPanel.currentPanel;
    }

    private async handleMessage(message: any): Promise<void> {
        switch (message.command) {
            case 'analyzeFile':
                await this.analyzeFromFile();
                break;
            case 'analyzeEditor':
                await this.analyzeFromEditor();
                break;
            case 'exportReport':
                await this.exportReport();
                break;
        }
    }

    /**
     * 从文件分析策略
     */
    private async analyzeFromFile(): Promise<void> {
        const fileUri = await vscode.window.showOpenDialog({
            canSelectFiles: true,
            canSelectFolders: false,
            canSelectMany: false,
            filters: {
                'Python文件': ['py'],
                '所有文件': ['*']
            }
        });

        if (fileUri && fileUri[0]) {
            try {
                const code = fs.readFileSync(fileUri[0].fsPath, 'utf-8');
                const fileName = path.basename(fileUri[0].fsPath);
                this.analyzeStrategy(code, fileName);
            } catch (error) {
                vscode.window.showErrorMessage(`读取文件失败: ${error}`);
            }
        }
    }

    /**
     * 从编辑器分析策略
     */
    private async analyzeFromEditor(): Promise<void> {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('请先打开一个策略文件');
            return;
        }

        const code = editor.document.getText();
        const fileName = path.basename(editor.document.fileName);
        this.analyzeStrategy(code, fileName);
    }

    /**
     * 分析策略
     */
    private async analyzeStrategy(code: string, fileName?: string): Promise<void> {
        try {
            this._panel.webview.postMessage({ command: 'analyzing' });
            
            const optimizer = await getStrategyOptimizer();
            const report = optimizer.generateOptimizationReport(code, fileName);
            this._report = report;
            
            this._panel.webview.postMessage({
                command: 'reportReady',
                report: report
            });
            
            this.updateContent();
        } catch (error) {
            logger.error(`策略分析失败: ${error}`, MODULE);
            vscode.window.showErrorMessage(`策略分析失败: ${error}`);
            this._panel.webview.postMessage({
                command: 'error',
                message: String(error)
            });
        }
    }

    /**
     * 导出报告
     */
    private async exportReport(): Promise<void> {
        if (!this._report) {
            vscode.window.showWarningMessage('没有可导出的报告');
            return;
        }

        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            vscode.window.showErrorMessage('请先打开工作区');
            return;
        }

        const reportsDir = path.join(workspaceFolder.uri.fsPath, 'Reports');
        if (!fs.existsSync(reportsDir)) {
            fs.mkdirSync(reportsDir, { recursive: true });
        }

        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        const reportPath = path.join(reportsDir, `optimization_${timestamp}.md`);

        const markdown = this.generateMarkdownReport(this._report);
        fs.writeFileSync(reportPath, markdown, 'utf-8');

        vscode.window.showInformationMessage(
            `报告已导出: ${path.basename(reportPath)}`,
            '打开文件'
        ).then(selection => {
            if (selection === '打开文件') {
                vscode.commands.executeCommand('vscode.open', vscode.Uri.file(reportPath));
            }
        });
    }

    /**
     * 生成Markdown报告
     */
    private generateMarkdownReport(report: OptimizationReport): string {
        let md = `# 策略优化报告\n\n`;
        md += `**策略名称**: ${report.strategyName}\n\n`;
        md += `**平台**: ${report.platform}\n\n`;
        md += `**分析时间**: ${new Date(report.analysisTime).toLocaleString('zh-CN')}\n\n`;
        md += `---\n\n`;
        
        md += `## 📊 策略评分\n\n`;
        md += `| 维度 | 评分 |\n`;
        md += `|------|------|\n`;
        md += `| 整体评分 | **${report.overallScore}/100** |\n`;
        md += `| 风险控制 | ${report.scoreBreakdown.risk}/100 |\n`;
        md += `| 因子构建 | ${report.scoreBreakdown.factor}/100 |\n`;
        md += `| 选股逻辑 | ${report.scoreBreakdown.selection}/100 |\n`;
        md += `| 代码质量 | ${report.scoreBreakdown.code}/100 |\n\n`;
        
        md += `## 📝 优化摘要\n\n`;
        md += `${report.summary}\n\n`;
        
        md += `## 💡 优化建议\n\n`;
        for (const advice of report.advices) {
            const priorityEmoji = advice.priority === 'high' ? '🔴' : advice.priority === 'medium' ? '🟡' : '🟢';
            md += `### ${priorityEmoji} ${advice.title}\n\n`;
            md += `**类别**: ${advice.category}\n\n`;
            md += `**描述**: ${advice.description}\n\n`;
            if (advice.currentState) {
                md += `**当前状态**: ${advice.currentState}\n\n`;
            }
            if (advice.suggestedState) {
                md += `**建议状态**: ${advice.suggestedState}\n\n`;
            }
            if (advice.codeExample) {
                md += `**代码示例**:\n\n\`\`\`python\n${advice.codeExample}\n\`\`\`\n\n`;
            }
            if (advice.impact) {
                md += `**预期影响**: ${advice.impact}\n\n`;
            }
            md += `---\n\n`;
        }
        
        return md;
    }

    public updateContent(): void {
        this._panel.webview.html = this.generateHtml();
    }

    private generateHtml(): string {
        const report = this._report;
        
        return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>策略优化器</title>
    <style>
        :root {
            --bg-dark: #0a0e14;
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-card: #1c2128;
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --text-muted: #6e7681;
            --accent-gold: #f0b429;
            --accent-green: #3fb950;
            --accent-blue: #58a6ff;
            --accent-red: #f85149;
            --border-color: #30363d;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg-dark);
            color: var(--text-primary);
            padding: 24px;
        }
        
        .header {
            margin-bottom: 24px;
        }
        
        .header h1 {
            font-size: 24px;
            margin-bottom: 8px;
        }
        
        .actions {
            display: flex;
            gap: 12px;
            margin-top: 16px;
        }
        
        .btn {
            padding: 10px 20px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: var(--text-secondary);
            cursor: pointer;
            font-size: 14px;
        }
        
        .btn:hover {
            background: var(--bg-secondary);
            border-color: var(--accent-blue);
            color: var(--text-primary);
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            color: #fff;
        }
        
        .score-section {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }
        
        .score-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }
        
        .score-label {
            font-size: 12px;
            color: var(--text-muted);
            margin-bottom: 8px;
        }
        
        .score-value {
            font-size: 32px;
            font-weight: 700;
            color: var(--accent-gold);
        }
        
        .summary {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
            white-space: pre-wrap;
            line-height: 1.6;
        }
        
        .advices {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        
        .advice-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
        }
        
        .advice-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
        }
        
        .priority-badge {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .priority-high {
            background: rgba(248, 81, 73, 0.2);
            color: var(--accent-red);
        }
        
        .priority-medium {
            background: rgba(240, 180, 41, 0.2);
            color: var(--accent-gold);
        }
        
        .priority-low {
            background: rgba(88, 166, 255, 0.2);
            color: var(--accent-blue);
        }
        
        .advice-title {
            font-size: 18px;
            font-weight: 600;
        }
        
        .advice-body {
            margin-top: 12px;
            color: var(--text-secondary);
            line-height: 1.6;
        }
        
        .code-example {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px;
            margin-top: 12px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            overflow-x: auto;
        }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: var(--text-muted);
        }
        
        .empty-state .icon {
            font-size: 64px;
            margin-bottom: 16px;
            opacity: 0.5;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 策略优化器</h1>
        <p style="color: var(--text-muted);">分析策略代码，生成优化建议</p>
        <div class="actions">
            <button class="btn btn-primary" onclick="vscode.postMessage({command: 'analyzeEditor'})">
                📝 分析当前编辑器
            </button>
            <button class="btn" onclick="vscode.postMessage({command: 'analyzeFile'})">
                📁 选择文件分析
            </button>
            ${report ? `<button class="btn" onclick="vscode.postMessage({command: 'exportReport'})">💾 导出报告</button>` : ''}
        </div>
    </div>
    
    ${report ? `
        <div class="score-section">
            <div class="score-card">
                <div class="score-label">整体评分</div>
                <div class="score-value">${report.overallScore}</div>
            </div>
            <div class="score-card">
                <div class="score-label">风险控制</div>
                <div class="score-value">${report.scoreBreakdown.risk}</div>
            </div>
            <div class="score-card">
                <div class="score-label">因子构建</div>
                <div class="score-value">${report.scoreBreakdown.factor}</div>
            </div>
            <div class="score-card">
                <div class="score-label">选股逻辑</div>
                <div class="score-value">${report.scoreBreakdown.selection}</div>
            </div>
            <div class="score-card">
                <div class="score-label">代码质量</div>
                <div class="score-value">${report.scoreBreakdown.code}</div>
            </div>
        </div>
        
        <div class="summary">
            <strong>📝 优化摘要</strong><br><br>
            ${report.summary}
        </div>
        
        <div class="advices">
            ${report.advices.map((advice: any) => `
                <div class="advice-card">
                    <div class="advice-header">
                        <span class="priority-badge priority-${advice.priority}">
                            ${advice.priority === 'high' ? '🔴 高优先级' : advice.priority === 'medium' ? '🟡 中优先级' : '🟢 低优先级'}
                        </span>
                        <span class="advice-title">${advice.title}</span>
                    </div>
                    <div class="advice-body">
                        <p>${advice.description}</p>
                        ${advice.currentState ? `<p><strong>当前状态:</strong> ${advice.currentState}</p>` : ''}
                        ${advice.suggestedState ? `<p><strong>建议状态:</strong> ${advice.suggestedState}</p>` : ''}
                        ${advice.codeExample ? `
                            <div class="code-example">
                                <pre>${advice.codeExample}</pre>
                            </div>
                        ` : ''}
                        ${advice.impact ? `<p><strong>预期影响:</strong> ${advice.impact}</p>` : ''}
                    </div>
                </div>
            `).join('')}
        </div>
    ` : `
        <div class="empty-state">
            <div class="icon">🔍</div>
            <h2>开始分析策略</h2>
            <p>点击上方按钮分析策略代码</p>
        </div>
    `}
    
    <script>
        const vscode = acquireVsCodeApi();
        
        window.addEventListener('message', event => {
            const message = event.data;
            
            switch (message.command) {
                case 'analyzing':
                    document.body.innerHTML = '<div class="empty-state"><div class="icon">⏳</div><h2>正在分析策略...</h2></div>';
                    break;
                case 'reportReady':
                    location.reload();
                    break;
                case 'error':
                    alert('分析失败: ' + message.message);
                    break;
            }
        });
    </script>
</body>
</html>`;
    }

    public dispose(): void {
        StrategyOptimizerPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const d = this._disposables.pop();
            if (d) d.dispose();
        }
    }
}

/**
 * 注册策略优化器命令
 */
export function registerStrategyOptimizerPanel(context: vscode.ExtensionContext): void {
    context.subscriptions.push(
        vscode.commands.registerCommand('trquant.optimizeStrategy', async () => {
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                const code = editor.document.getText();
                const fileName = path.basename(editor.document.fileName);
                StrategyOptimizerPanel.createOrShow(context.extensionUri, code, fileName);
            } else {
                StrategyOptimizerPanel.createOrShow(context.extensionUri);
            }
        })
    );
    
    logger.info('策略优化器面板已注册', MODULE);
}
