/**
 * 工作流面板 - 复用桌面系统代码
 * 
 * 与桌面系统 gui/widgets/integrated_workflow_panel.py 保持一致
 * 通过Python Bridge调用 core/workflow_orchestrator.py
 * 
 * 功能：
 * - 6步骤工作流（数据源、市场趋势、投资主线、候选池、因子、策略）
 * - 单步执行和全部执行
 * - 实时显示执行结果
 */

import * as vscode from 'vscode';
import { TRQuantClient } from '../services/trquantClient';
import { logger } from '../utils/logger';

const MODULE = 'WorkflowPanel';

// 工作流步骤定义（与桌面系统一致）
const WORKFLOW_STEPS = [
    { id: 'data_source', name: '信息获取', icon: '📡', color: '#58a6ff' },
    { id: 'market_trend', name: '市场趋势', icon: '📈', color: '#667eea' },
    { id: 'mainline', name: '投资主线', icon: '🔥', color: '#F59E0B' },
    { id: 'candidate_pool', name: '候选池构建', icon: '📦', color: '#a371f7' },
    { id: 'factor', name: '因子构建', icon: '🧮', color: '#3fb950' },
    { id: 'strategy', name: '策略生成', icon: '💻', color: '#d29922' },
];

export class WorkflowPanel {
    public static currentPanel: WorkflowPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private readonly _client: TRQuantClient;
    private _disposables: vscode.Disposable[] = [];
    private _currentStep: string | null = null;
    private _isRunning = false;

    private constructor(
        panel: vscode.WebviewPanel,
        extensionUri: vscode.Uri,
        client: TRQuantClient
    ) {
        this._panel = panel;
        this._extensionUri = extensionUri;
        this._client = client;

        this._panel.webview.html = this._getHtmlContent();

        // 监听面板关闭
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        // 监听消息
        this._panel.webview.onDidReceiveMessage(
            message => this._handleMessage(message),
            null,
            this._disposables
        );
    }

    public static createOrShow(
        extensionUri: vscode.Uri,
        client: TRQuantClient
    ): WorkflowPanel {
        const column = vscode.ViewColumn.One;

        if (WorkflowPanel.currentPanel) {
            WorkflowPanel.currentPanel._panel.reveal(column);
            return WorkflowPanel.currentPanel;
        }

        const panel = vscode.window.createWebviewPanel(
            'trquantWorkflow',
            '🔄 集成工作流程',
            column,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [extensionUri]
            }
        );

        WorkflowPanel.currentPanel = new WorkflowPanel(panel, extensionUri, client);
        return WorkflowPanel.currentPanel;
    }

    public dispose(): void {
        WorkflowPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const d = this._disposables.pop();
            if (d) d.dispose();
        }
    }

    // ==================== 消息处理 ====================

    private async _handleMessage(message: any): Promise<void> {
        logger.info(`[WorkflowPanel] 收到消息: ${message.command}`, MODULE);

        switch (message.command) {
            case 'runStep':
                await this._runStep(message.stepId);
                break;
            case 'runAll':
                await this._runAll();
                break;
            case 'cancel':
                this._isRunning = false;
                this._postMessage({ command: 'cancelled' });
                break;
        }
    }

    // ==================== 工作流执行 ====================

    /**
     * 执行单个步骤
     * 复用桌面系统 core/workflow_orchestrator.py
     */
    private async _runStep(stepId: string): Promise<void> {
        if (this._isRunning) {
            vscode.window.showWarningMessage('工作流正在执行中，请等待完成');
            return;
        }

        this._isRunning = true;
        this._currentStep = stepId;

        // 更新UI状态
        this._postMessage({
            command: 'stepStarted',
            stepId,
            stepName: WORKFLOW_STEPS.find(s => s.id === stepId)?.name || stepId
        });

        try {
            // 通过Python Bridge调用workflow_orchestrator
            const response = await this._client.callBridge('run_workflow_step', {
                step_id: stepId
            });

            const resp = response as any;
            if (response.ok) {
                // 执行成功
                this._postMessage({
                    command: 'stepFinished',
                    stepId,
                    success: true,
                    summary: resp.summary || '执行成功',
                    details: resp.data || {},
                    stepName: resp.step_name || WORKFLOW_STEPS.find(s => s.id === stepId)?.name || stepId
                });
            } else {
                // 执行失败
                this._postMessage({
                    command: 'stepFinished',
                    stepId,
                    success: false,
                    summary: resp.error || '执行失败',
                    details: {},
                    stepName: WORKFLOW_STEPS.find(s => s.id === stepId)?.name || stepId
                });
            }
        } catch (error) {
            const msg = error instanceof Error ? error.message : String(error);
            logger.error(`步骤 ${stepId} 执行失败: ${msg}`, MODULE);
            this._postMessage({
                command: 'stepFinished',
                stepId,
                success: false,
                summary: `执行失败: ${msg}`,
                details: {},
                stepName: WORKFLOW_STEPS.find(s => s.id === stepId)?.name || stepId
            });
        } finally {
            this._isRunning = false;
            this._currentStep = null;
        }
    }

    /**
     * 执行全部步骤
     * 复用桌面系统 core/workflow_orchestrator.py 的 run_full_workflow
     */
    private async _runAll(): Promise<void> {
        if (this._isRunning) {
            vscode.window.showWarningMessage('工作流正在执行中，请等待完成');
            return;
        }

        this._isRunning = true;

        // 显示进度
        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: '🔄 执行完整工作流',
            cancellable: true
        }, async (progress, token) => {
            const results: any[] = [];
            let hasError = false;

            // 通知前端开始执行全部
            this._postMessage({ command: 'allStarted' });

            try {
                // 通过Python Bridge调用完整工作流
                const response = await this._client.callBridge('run_full_workflow', {});

                const resp = response as any;
                if (response.ok && resp.data) {
                    const data = resp.data as any;
                    const steps = data.steps || [];
                    
                    // 逐个通知步骤完成
                    for (const step of steps) {
                        const stepId = this._getStepIdFromName(step.step_name);
                        this._postMessage({
                            command: 'stepFinished',
                            stepId,
                            success: step.success,
                            summary: step.summary || '',
                            details: step.details || {},
                            stepName: step.step_name
                        });

                        results.push({
                            step: step.step_name,
                            success: step.success,
                            error: step.error
                        });

                        if (!step.success) {
                            hasError = true;
                        }

                        progress.report({
                            message: `${step.step_name}: ${step.success ? '✅' : '❌'}`,
                            increment: 100 / steps.length
                        });
                    }

                    // 通知全部完成
                    this._postMessage({
                        command: 'allFinished',
                        success: !hasError,
                        results,
                        strategyFile: data.strategy_file,
                        totalTime: data.total_time
                    });

                    if (hasError) {
                        vscode.window.showWarningMessage('⚠️ 工作流完成，部分步骤有错误');
                    } else {
                        vscode.window.showInformationMessage('✅ 完整工作流执行完成！');
                    }
                } else {
                    throw new Error(response.error || '执行失败');
                }
            } catch (error) {
                const msg = error instanceof Error ? error.message : String(error);
                logger.error(`完整工作流执行失败: ${msg}`, MODULE);
                this._postMessage({
                    command: 'allFinished',
                    success: false,
                    results: [],
                    error: msg
                });
                vscode.window.showErrorMessage(`工作流执行失败: ${msg}`);
            } finally {
                this._isRunning = false;
            }
        });
    }

    /**
     * 步骤名称转ID
     */
    private _getStepIdFromName(stepName: string): string {
        const nameMap: Record<string, string> = {
            '数据源': 'data_source',
            '数据源检测': 'data_source',
            '市场趋势': 'market_trend',
            '投资主线': 'mainline',
            '候选池': 'candidate_pool',
            '候选池构建': 'candidate_pool',
            '因子推荐': 'factor',
            '策略生成': 'strategy',
        };
        return nameMap[stepName] || stepName.toLowerCase().replace(/\s+/g, '_');
    }

    private _postMessage(message: any): void {
        this._panel.webview.postMessage(message);
    }

    // ==================== HTML内容 ====================

    private _getHtmlContent(): string {
        return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>集成工作流程</title>
    <style>
        :root {
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --border-color: #30363d;
            --text-primary: #c9d1d9;
            --text-secondary: #8b949e;
            --accent-blue: #58a6ff;
            --accent-green: #3fb950;
            --accent-yellow: #d29922;
            --accent-red: #f85149;
            --accent-purple: #a371f7;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            height: 100vh;
            overflow: hidden;
        }
        
        .container {
            display: flex;
            height: 100vh;
            gap: 0;
        }
        
        /* 左侧步骤区域 */
        .steps-panel {
            width: 280px;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border-color);
            padding: 16px;
            overflow-y: auto;
        }
        
        .header {
            margin-bottom: 20px;
        }
        
        .header h1 {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 12px;
        }
        
        .run-all-btn {
            width: 100%;
            padding: 10px;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.2s;
        }
        
        .run-all-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
        }
        
        .run-all-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .steps-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .step-card {
            background: var(--bg-tertiary);
            border: 2px solid var(--border-color);
            border-left: 4px solid var(--step-color);
            border-radius: 10px;
            padding: 14px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .step-card:hover {
            background: var(--bg-primary);
            border-color: var(--accent-blue);
        }
        
        .step-card.running {
            border-color: var(--accent-yellow);
            animation: pulse 1.5s infinite;
        }
        
        .step-card.completed {
            border-color: var(--accent-green);
        }
        
        .step-card.failed {
            border-color: var(--accent-red);
        }
        
        @keyframes pulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(217, 153, 34, 0.4); }
            50% { box-shadow: 0 0 0 8px rgba(217, 153, 34, 0); }
        }
        
        .step-icon {
            font-size: 26px;
            width: 36px;
            text-align: center;
        }
        
        .step-name {
            flex: 1;
            font-size: 15px;
            font-weight: 600;
        }
        
        .step-status {
            font-size: 16px;
        }
        
        /* 右侧结果区域 */
        .result-panel {
            flex: 1;
            background: var(--bg-primary);
            padding: 20px;
            overflow-y: auto;
        }
        
        .result-header {
            margin-bottom: 20px;
        }
        
        .result-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        .result-summary {
            background: var(--bg-secondary);
            padding: 16px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            margin-bottom: 20px;
        }
        
        .result-details {
            background: var(--bg-secondary);
            padding: 16px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            max-height: 400px;
            overflow-y: auto;
        }
        
        .result-details table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .result-details th,
        .result-details td {
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }
        
        .result-details th {
            background: var(--bg-tertiary);
            font-weight: 600;
        }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: var(--text-secondary);
        }
        
        .empty-icon {
            font-size: 48px;
            margin-bottom: 12px;
            opacity: 0.5;
        }
        
        .progress-bar {
            height: 6px;
            background: var(--bg-tertiary);
            border-radius: 3px;
            overflow: hidden;
            margin: 12px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #6366f1, #8b5cf6);
            width: 0%;
            transition: width 0.3s;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 左侧步骤 -->
        <div class="steps-panel">
            <div class="header">
                <h1>🔄 集成工作流程</h1>
                <button class="run-all-btn" id="runAllBtn" onclick="runAll()">
                    ▶️ 一键执行全部
                </button>
            </div>
            <div class="steps-list" id="stepsList">
                ${WORKFLOW_STEPS.map(step => `
                    <div class="step-card" id="step-${step.id}" 
                         style="--step-color: ${step.color}"
                         onclick="runStep('${step.id}')">
                        <div class="step-icon">${step.icon}</div>
                        <div class="step-name">${step.name}</div>
                        <div class="step-status" id="status-${step.id}">▶️</div>
                    </div>
                `).join('')}
            </div>
        </div>
        
        <!-- 右侧结果 -->
        <div class="result-panel">
            <div class="result-header">
                <div class="result-title" id="resultTitle">📋 执行结果</div>
            </div>
            <div class="result-summary" id="resultSummary">
                点击左侧步骤开始执行...
            </div>
            <div class="result-details" id="resultDetails"></div>
        </div>
    </div>
    
    <script>
        const vscode = acquireVsCodeApi();
        let isRunning = false;
        
        function runStep(stepId) {
            if (isRunning) {
                return;
            }
            vscode.postMessage({ command: 'runStep', stepId });
        }
        
        function runAll() {
            if (isRunning) {
                return;
            }
            vscode.postMessage({ command: 'runAll' });
        }
        
        function setStepStatus(stepId, status) {
            const card = document.getElementById('step-' + stepId);
            const statusEl = document.getElementById('status-' + stepId);
            
            card.classList.remove('running', 'completed', 'failed');
            
            switch(status) {
                case 'running':
                    card.classList.add('running');
                    statusEl.textContent = '⏳';
                    break;
                case 'completed':
                    card.classList.add('completed');
                    statusEl.textContent = '✅';
                    break;
                case 'failed':
                    card.classList.add('failed');
                    statusEl.textContent = '❌';
                    break;
                default:
                    statusEl.textContent = '▶️';
            }
        }
        
        function formatDetails(details) {
            if (!details || Object.keys(details).length === 0) {
                return '<div style="color:var(--text-secondary);">无详细数据</div>';
            }
            
            let html = '';
            
            // 投资主线
            if (details.top_mainlines) {
                const mainlines = details.top_mainlines;
                html += '<div style="margin-bottom:12px;"><strong>🔥 投资主线 TOP' + mainlines.length + '</strong></div>';
                html += '<table><tr><th>排名</th><th>名称</th><th>评分</th></tr>';
                mainlines.slice(0, 10).forEach(ml => {
                    html += '<tr><td>#' + (ml.rank || '-') + '</td><td>' + (ml.name || '-') + '</td><td>' + ((ml.composite_score || ml.score || 0).toFixed?.(1) || '-') + '</td></tr>';
                });
                html += '</table>';
            }
            
            // 候选池股票
            else if (details.stocks) {
                const stocks = details.stocks;
                html += '<div style="margin-bottom:12px;"><strong>📦 候选池股票 (' + stocks.length + '只)</strong></div>';
                html += '<table><tr><th>代码</th><th>名称</th><th>来源</th><th>评分</th></tr>';
                stocks.slice(0, 15).forEach(s => {
                    html += '<tr><td>' + (s.code || '-') + '</td><td>' + (s.name || '-') + '</td><td>' + (s.source || '-') + '</td><td>' + ((s.score || 0).toFixed?.(1) || '-') + '</td></tr>';
                });
                html += '</table>';
            }
            
            // 推荐因子
            else if (details.recommended_factors) {
                const factors = details.recommended_factors;
                html += '<div style="margin-bottom:12px;"><strong>🧮 推荐因子</strong></div>';
                html += '<ul style="margin:0;padding-left:20px;">';
                factors.forEach(f => {
                    const weight = ((f.weight || 0) * 100).toFixed(0);
                    html += '<li style="margin:6px 0;"><strong>' + (f.name || '-') + '</strong> (权重' + weight + '%) - ' + (f.reason || '') + '</li>';
                });
                html += '</ul>';
            }
            
            // 数据源检测
            else if (details.jqdata !== undefined || details.akshare !== undefined) {
                html += '<div style="margin-bottom:12px;"><strong>📡 数据源状态</strong></div>';
                html += '<table><tr><th>数据源</th><th>状态</th></tr>';
                if (details.jqdata !== undefined) {
                    html += '<tr><td>JQData</td><td style="color:' + (details.jqdata ? '#3fb950' : '#f85149') + ';">' + (details.jqdata ? '✅ 可用' : '❌ 不可用') + '</td></tr>';
                }
                if (details.akshare !== undefined) {
                    html += '<tr><td>AKShare</td><td style="color:' + (details.akshare ? '#3fb950' : '#f85149') + ';">' + (details.akshare ? '✅ 可用' : '❌ 不可用') + '</td></tr>';
                }
                html += '</table>';
            }
            
            // 默认JSON显示
            else {
                html += '<pre style="font-size:11px;overflow-x:auto;">' + JSON.stringify(details, null, 2) + '</pre>';
            }
            
            return html;
        }
        
        window.addEventListener('message', event => {
            const message = event.data;
            
            switch (message.command) {
                case 'stepStarted':
                    isRunning = true;
                    document.getElementById('runAllBtn').disabled = true;
                    setStepStatus(message.stepId, 'running');
                    document.getElementById('resultTitle').textContent = '📋 ' + message.stepName + ' - 执行中';
                    document.getElementById('resultSummary').textContent = '正在执行 ' + message.stepName + '...';
                    document.getElementById('resultDetails').innerHTML = '';
                    break;
                    
                case 'stepFinished':
                    isRunning = false;
                    document.getElementById('runAllBtn').disabled = false;
                    setStepStatus(message.stepId, message.success ? 'completed' : 'failed');
                    document.getElementById('resultTitle').textContent = '📋 ' + message.stepName + ' - ' + (message.success ? '✅ 完成' : '❌ 失败');
                    document.getElementById('resultSummary').textContent = message.summary || (message.success ? '执行成功' : '执行失败');
                    document.getElementById('resultDetails').innerHTML = formatDetails(message.details);
                    break;
                    
                case 'allStarted':
                    isRunning = true;
                    document.getElementById('runAllBtn').disabled = true;
                    document.getElementById('resultTitle').textContent = '🔄 执行完整工作流';
                    document.getElementById('resultSummary').textContent = '正在执行所有步骤...';
                    document.getElementById('resultDetails').innerHTML = '';
                    // 重置所有步骤状态
                    ${WORKFLOW_STEPS.map(s => `setStepStatus('${s.id}', 'default');`).join('')}
                    break;
                    
                case 'allFinished':
                    isRunning = false;
                    document.getElementById('runAllBtn').disabled = false;
                    document.getElementById('resultTitle').textContent = message.success ? '✅ 工作流执行完成' : '⚠️ 工作流完成（部分失败）';
                    document.getElementById('resultSummary').textContent = '共执行 ' + (message.results?.length || 0) + ' 个步骤';
                    
                    // 显示汇总
                    let summaryHtml = '<div style="margin-top:16px;">';
                    summaryHtml += '<h4 style="margin-bottom:8px;">执行结果汇总</h4>';
                    if (message.results) {
                        message.results.forEach(r => {
                            summaryHtml += '<div style="display:flex;align-items:center;gap:8px;margin:4px 0;">';
                            summaryHtml += '<span>' + (r.success ? '✅' : '❌') + '</span>';
                            summaryHtml += '<span>' + r.step + '</span>';
                            if (r.error) {
                                summaryHtml += '<span style="color:#f85149;font-size:11px;">(' + r.error + ')</span>';
                            }
                            summaryHtml += '</div>';
                        });
                    }
                    summaryHtml += '</div>';
                    document.getElementById('resultDetails').innerHTML = summaryHtml;
                    break;
                    
                case 'cancelled':
                    isRunning = false;
                    document.getElementById('runAllBtn').disabled = false;
                    break;
            }
        });
    </script>
</body>
</html>`;
    }
}

// ============================================================
// 注册函数
// ============================================================

export function registerWorkflowPanel(
    context: vscode.ExtensionContext,
    client: TRQuantClient
): void {
    context.subscriptions.push(
        vscode.commands.registerCommand('trquant.openWorkflowPanel', () => {
            WorkflowPanel.createOrShow(context.extensionUri, client);
        })
    );
    
    logger.info('工作流面板已注册（复用桌面系统代码）', MODULE);
}
