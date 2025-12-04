/**
 * TRQuant 投资工作流仪表盘
 * ==========================
 * 
 * 韬睿量化核心入口 - 完整投资流程系统
 * 区别于QuantConnect纯回测，这是8步骤投资工作流
 * 
 * 功能模块：
 * - 市场状态概览
 * - 投资主线TOP5
 * - 推荐因子展示
 * - 8步骤工作流快捷入口
 * - 最近项目/回测列表
 */

import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { TRQuantClient } from '../services/trquantClient';
import { logger } from '../utils/logger';
import { showQuantConnectStyleReport, BacktestResultData } from './quantconnectStylePanel';
import { MarketStatus, Mainline, Factor } from '../types';

const MODULE = 'MainDashboard';

export class MainDashboard {
    public static currentPanel: MainDashboard | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private readonly _client: TRQuantClient;
    private _disposables: vscode.Disposable[] = [];
    
    // 缓存数据
    private _marketStatus: MarketStatus | null = null;
    private _mainlines: Mainline[] = [];
    private _factors: Factor[] = [];

    private constructor(
        panel: vscode.WebviewPanel,
        extensionUri: vscode.Uri,
        client: TRQuantClient
    ) {
        this._panel = panel;
        this._extensionUri = extensionUri;
        this._client = client;

        this._panel.webview.onDidReceiveMessage(
            message => this.handleMessage(message),
            null,
            this._disposables
        );

        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
        
        // 初始加载
        this.updateContent();
        this.refreshAllData();
    }

    public static createOrShow(
        extensionUri: vscode.Uri,
        client: TRQuantClient
    ): MainDashboard {
        const column = vscode.ViewColumn.One;

        if (MainDashboard.currentPanel) {
            MainDashboard.currentPanel._panel.reveal(column);
            return MainDashboard.currentPanel;
        }

        const panel = vscode.window.createWebviewPanel(
            'trquantDashboard',
            '🐉 韬睿量化工作台',
            column,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [extensionUri]
            }
        );

        MainDashboard.currentPanel = new MainDashboard(panel, extensionUri, client);
        return MainDashboard.currentPanel;
    }

    private async handleMessage(message: any): Promise<void> {
        // 调试：记录所有收到的消息
        console.log('[MainDashboard] 收到消息:', message.command);
        
        switch (message.command) {
            // 工作流步骤
            case 'openStep':
                await this.openWorkflowStep(message.step);
                break;
            
            // 刷新数据
            case 'refreshAll':
                await this.refreshAllData();
                break;
            case 'refreshMarket':
                await this.refreshMarketStatus();
                break;
            case 'refreshMainlines':
                await this.refreshMainlines();
                break;
            case 'refreshFactors':
                await this.refreshFactors();
                break;
            
            // 项目管理
            case 'createProject':
                console.log('[MainDashboard] 执行 createProject 命令');
                await vscode.commands.executeCommand('trquant.createProject');
                break;
            case 'openProject':
                vscode.commands.executeCommand('trquant.openProject');
                break;
            
            // 快捷操作
            case 'openBacktestConfig':
                vscode.commands.executeCommand('trquant.openBacktestConfig');
                break;
            case 'generateStrategy':
                vscode.commands.executeCommand('trquant.generateStrategy');
                break;
            case 'showLogs':
                vscode.commands.executeCommand('trquant.showLogs');
                break;
            case 'openSettings':
                vscode.commands.executeCommand('trquant.openSettings');
                break;
            case 'openFileManager':
                vscode.commands.executeCommand('trquant.openFileManager');
                break;
            
            // 启动Web文件管理系统（Dashboard）
            case 'launchFileDashboard':
                await this.launchFileDashboard();
                break;
            case 'openKnowledgeBase':
                vscode.commands.executeCommand('trquant.openKnowledgeBase');
                break;
            case 'openAShareManual':
                vscode.commands.executeCommand('trquant.openAShareManual');
                break;
            
            // 新的A股手册启动方式 - 直接在面板中处理
            case 'launchAShareManual':
                await this.launchAShareManual();
                break;
            
            // 运行完整工作流
            case 'runFullWorkflow':
                await this.runFullWorkflow();
                break;
            
            // 打开工作流面板
            case 'openWorkflowPanel':
                console.log('[MainDashboard] 准备执行 openWorkflowPanel 命令');
                try {
                    await vscode.commands.executeCommand('trquant.openWorkflowPanel');
                    console.log('[MainDashboard] openWorkflowPanel 命令执行完成');
                } catch (error) {
                    console.error('[MainDashboard] openWorkflowPanel 命令执行失败:', error);
                    vscode.window.showErrorMessage(`打开工作流面板失败: ${error}`);
                }
                break;
            
            // 文件管理系统功能
            case 'generateInvestmentReport':
                await this.generateInvestmentReport();
                break;
            case 'syncFileChanges':
                await this.syncFileChanges();
                break;
            case 'exportDatabase':
                await this.exportDatabase();
                break;
            case 'openFile':
                await this.openFile(message.path);
                break;
        }
    }

    private async openWorkflowStep(step: number): Promise<void> {
        const stepMap: Record<number, { id: string; name: string }> = {
            1: { id: 'data_source', name: '信息获取' },
            2: { id: 'market_trend', name: '市场趋势' },
            3: { id: 'mainline', name: '投资主线' },
            4: { id: 'candidate_pool', name: '候选池构建' },
            5: { id: 'factor', name: '因子构建' },
            6: { id: 'strategy', name: '策略生成' },
            7: { id: 'backtest', name: '回测验证' },
            8: { id: 'trading', name: '实盘交易' }
        };
        
        const stepInfo = stepMap[step];
        if (!stepInfo) return;
        
        // 步骤7和8打开专门的配置页面
        if (step === 7) {
            vscode.commands.executeCommand('trquant.openBacktestConfig');
            return;
        }
        if (step === 8) {
            vscode.commands.executeCommand('trquant.openTrading');
            return;
        }
        
        // 其他步骤在当前页面执行并显示结果
        // 1. 更新UI状态 - 显示执行中
        this._panel.webview.postMessage({ 
            command: 'stepStarted', 
            step,
            stepId: stepInfo.id,
            stepName: stepInfo.name 
        });
        
        try {
            // 2. 调用Python后端执行步骤
            const result = await this._client.callBridge<any>('run_workflow_step', { step_id: stepInfo.id });
            
            // 3. 解析结果 - bridge返回: {ok, summary, data}
            const response = result as any;  // 扩展类型
            const summary = response.summary || (result.ok ? '执行成功' : '执行失败');
            const details = result.data || {};
            
            // 4. 发送结果到前端
            this._panel.webview.postMessage({
                command: 'stepResult',
                step,
                stepId: stepInfo.id,
                stepName: stepInfo.name,
                success: result.ok,
                summary: summary,
                details: details,
                error: result.error
            });
            
        } catch (err) {
            logger.error(`步骤${step}执行失败: ${err}`, MODULE);
            this._panel.webview.postMessage({
                command: 'stepResult',
                step,
                stepId: stepInfo.id,
                stepName: stepInfo.name,
                success: false,
                summary: `执行失败: ${err}`,
                details: {},
                error: String(err)
            });
        }
    }

    private async refreshAllData(): Promise<void> {
        this._panel.webview.postMessage({ command: 'loadingStart' });
        
        await Promise.all([
            this.refreshMarketStatus(),
            this.refreshMainlines(),
            this.refreshFactors()
        ]);
        
        this._panel.webview.postMessage({ command: 'loadingEnd' });
    }

    private async refreshMarketStatus(): Promise<void> {
        try {
            const result = await this._client.getMarketStatus();
            if (result.ok && result.data) {
                this._marketStatus = result.data;
                // 转换为前端需要的格式
                const displayData = {
                    regime: this._marketStatus.regime,
                    regime_cn: this.getRegimeCN(this._marketStatus.regime),
                    indices: this.formatIndices(this._marketStatus.index_trend),
                    style_rotation: this._marketStatus.style_rotation?.[0]?.style || '均衡'
                };
                this._panel.webview.postMessage({
                    command: 'marketStatusUpdated',
                    data: displayData
                });
            }
        } catch (error) {
            logger.error(`获取市场状态失败: ${error}`, MODULE);
        }
    }

    private getRegimeCN(regime: string): string {
        const map: Record<string, string> = {
            'risk_on': '风险偏好',
            'risk_off': '风险规避',
            'neutral': '中性'
        };
        return map[regime] || regime;
    }

    private formatIndices(indexTrend: Record<string, any>): Array<{name: string; value: number; change: number}> {
        const result: Array<{name: string; value: number; change: number}> = [];
        const nameMap: Record<string, string> = {
            'sh_index': '上证指数',
            'sz_index': '深证成指',
            'cy_index': '创业板指'
        };
        
        for (const [key, value] of Object.entries(indexTrend || {})) {
            result.push({
                name: nameMap[key] || key,
                value: value?.zscore || 0,
                change: value?.change_pct || 0
            });
        }
        return result;
    }

    private async refreshMainlines(): Promise<void> {
        try {
            const result = await this._client.getMainlines({ time_horizon: 'short', top_n: 5 });
            if (result.ok && result.data) {
                this._mainlines = result.data;
                this._panel.webview.postMessage({
                    command: 'mainlinesUpdated',
                    data: this._mainlines
                });
            }
        } catch (error) {
            logger.error(`获取投资主线失败: ${error}`, MODULE);
        }
    }

    private async refreshFactors(): Promise<void> {
        try {
            const regime = this._marketStatus?.regime || 'neutral';
            const result = await this._client.recommendFactors({ market_regime: regime, top_n: 5 });
            if (result.ok && result.data) {
                this._factors = result.data;
                this._panel.webview.postMessage({
                    command: 'factorsUpdated',
                    data: this._factors
                });
            }
        } catch (error) {
            logger.error(`获取推荐因子失败: ${error}`, MODULE);
        }
    }

    /**
     * 一键执行全部工作流
     * 按顺序执行8个步骤，实时更新进度
     */
    private async runFullWorkflow(): Promise<void> {
        logger.info('=== 一键执行完整投资工作流 ===', MODULE);
        
        const steps = [
            { id: 'step1', name: '📡 信息获取', action: 'check_data_sources' },
            { id: 'step2', name: '📈 市场趋势', action: 'analyze_market_trend' },
            { id: 'step3', name: '🔥 投资主线', action: 'identify_mainlines' },
            { id: 'step4', name: '📦 候选池构建', action: 'build_candidate_pool' },
            { id: 'step5', name: '📊 因子推荐', action: 'recommend_factors' },
            { id: 'step6', name: '🛠️ 策略生成', action: 'generate_strategy' },
            { id: 'step7', name: '🔄 回测验证', action: 'run_backtest' },
            { id: 'step8', name: '🚀 交易检查', action: 'check_broker' }
        ];
        
        // 显示进度
        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: '🐉 执行完整投资工作流',
            cancellable: true
        }, async (progress, token) => {
            const results: any[] = [];
            let hasError = false;
            
            for (let i = 0; i < steps.length; i++) {
                if (token.isCancellationRequested) {
                    vscode.window.showWarningMessage('工作流已取消');
                    break;
                }
                
                const step = steps[i];
                progress.report({ 
                    message: `(${i + 1}/${steps.length}) ${step.name}`,
                    increment: 100 / steps.length
                });
                
                try {
                    logger.info(`执行步骤: ${step.name}`, MODULE);
                    
                    // 通知前端更新状态
                    this._panel.webview.postMessage({
                        command: 'workflowProgress',
                        data: {
                            currentStep: step.id,
                            stepName: step.name,
                            progress: ((i + 1) / steps.length) * 100,
                            status: 'running'
                        }
                    });
                    
                    // 调用后端
                    const response = await this._client.callBridge('run_workflow_step', {
                        step_id: step.action
                    });
                    
                    if (response.ok) {
                        results.push({
                            step: step.name,
                            success: true,
                            data: response.data
                        });
                        
                        // 更新前端显示结果
                        this._panel.webview.postMessage({
                            command: 'workflowStepResult',
                            data: {
                                stepId: step.id,
                                stepName: step.name,
                                result: response.data,
                                success: true
                            }
                        });
                    } else {
                        hasError = true;
                        results.push({
                            step: step.name,
                            success: false,
                            error: response.error
                        });
                    }
                    
                    // 稍微延迟以便用户能看到进度
                    await new Promise(resolve => setTimeout(resolve, 500));
                    
                } catch (error) {
                    hasError = true;
                    const msg = error instanceof Error ? error.message : String(error);
                    logger.error(`步骤 ${step.name} 失败: ${msg}`, MODULE);
                    results.push({
                        step: step.name,
                        success: false,
                        error: msg
                    });
                }
            }
            
            // 完成通知
            this._panel.webview.postMessage({
                command: 'workflowComplete',
                data: {
                    results,
                    hasError
                }
            });
            
            if (hasError) {
                vscode.window.showWarningMessage('⚠️ 工作流完成，部分步骤有错误');
            } else {
                vscode.window.showInformationMessage('✅ 完整投资工作流执行完成！');
            }
            
            // 刷新数据
            await this.refreshAllData();
        });
    }

    /**
     * 启动A股实操手册 - Astro文档系统
     * 参考桌面软件gui/main_window.py中的open_manual方法
     */
    private async launchAShareManual(): Promise<void> {
        logger.info('=== 启动A股实操手册 ===', MODULE);
        
        try {
            // 确定手册路径 - 在工作区的extension/AShare-manual下
            const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
            if (!workspaceFolder) {
                vscode.window.showErrorMessage('请先打开TRQuant工作区');
                return;
            }
            
            const manualPath = path.join(workspaceFolder.uri.fsPath, 'extension', 'AShare-manual');
            logger.info(`手册路径: ${manualPath}`, MODULE);
            
            // 检查目录是否存在
            if (!fs.existsSync(manualPath)) {
                vscode.window.showErrorMessage(`A股手册目录不存在: ${manualPath}`);
                logger.error(`目录不存在: ${manualPath}`, MODULE);
                return;
            }
            
            // 检查package.json是否存在
            if (!fs.existsSync(path.join(manualPath, 'package.json'))) {
                vscode.window.showErrorMessage('A股手册配置文件缺失');
                return;
            }
            
            // 检查node_modules
            if (!fs.existsSync(path.join(manualPath, 'node_modules'))) {
                const result = await vscode.window.showWarningMessage(
                    'A股手册需要安装依赖，是否安装？',
                    '安装', '取消'
                );
                if (result === '安装') {
                    const terminal = vscode.window.createTerminal({
                        name: 'A股手册依赖安装',
                        cwd: manualPath
                    });
                    terminal.show();
                    terminal.sendText('npm install && echo "依赖安装完成，请重新点击A股实操手册"');
                }
                return;
            }
            
            // 使用终端启动Astro - 这是最可靠的方式
            // 先检查是否已有终端在运行
            const existingTerminal = vscode.window.terminals.find(t => t.name === 'A股手册服务');
            
            if (existingTerminal) {
                logger.info('发现已存在的手册服务终端', MODULE);
                existingTerminal.show();
                // 直接打开浏览器
                vscode.window.showInformationMessage('正在打开A股手册...');
                setTimeout(() => {
                    vscode.env.openExternal(vscode.Uri.parse('http://localhost:4321'));
                }, 500);
                return;
            }
            
            // 创建新终端启动服务
            logger.info('创建新终端启动Astro服务', MODULE);
            const terminal = vscode.window.createTerminal({
                name: 'A股手册服务',
                cwd: manualPath,
                env: {
                    ...process.env,
                    // 确保使用正确的node/npm路径
                }
            });
            terminal.show();
            
            // 发送启动命令
            terminal.sendText('npm run dev');
            
            vscode.window.showInformationMessage('📚 正在启动A股手册服务器...');
            
            // 等待服务器启动后打开浏览器
            setTimeout(() => {
                logger.info('尝试打开浏览器', MODULE);
                vscode.env.openExternal(vscode.Uri.parse('http://localhost:4321'));
                vscode.window.showInformationMessage('✅ A股高倍股实操手册已启动');
            }, 3000);
            
        } catch (error) {
            const msg = error instanceof Error ? error.message : String(error);
            logger.error(`启动失败: ${msg}`, MODULE);
            vscode.window.showErrorMessage(`启动A股手册失败: ${msg}`);
        }
    }

    /**
     * 启动Web文件管理系统（Dashboard）
     * 
     * 独立插件设计：
     * - Dashboard位于 extension/dashboard/ 目录
     * - 启动脚本: extension/start_dashboard.py
     * - 数据目录: extension/data/
     * - 支持跨平台（Linux/macOS/Windows）
     */
    private async launchFileDashboard(): Promise<void> {
        logger.info('=== 启动Extension Dashboard ===', MODULE);
        
        try {
            const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
            if (!workspaceFolder) {
                vscode.window.showErrorMessage('请先打开工作区');
                return;
            }
            
            // 检查是否已有终端在运行
            const existingTerminal = vscode.window.terminals.find(t => t.name === 'TRQuant Dashboard');
            if (existingTerminal) {
                logger.info('Dashboard服务已在运行', MODULE);
                existingTerminal.show();
                vscode.window.showInformationMessage('📁 正在打开文件管理系统...');
                setTimeout(() => {
                    vscode.env.openExternal(vscode.Uri.parse('http://localhost:5000'));
                }, 500);
                return;
            }
            
            // Dashboard位于extension目录内
            const extensionPath = path.join(workspaceFolder.uri.fsPath, 'extension');
            const dashboardScript = path.join(extensionPath, 'start_dashboard.py');
            
            // 检查启动脚本是否存在
            if (!fs.existsSync(dashboardScript)) {
                vscode.window.showErrorMessage(`Dashboard启动脚本不存在: ${dashboardScript}`);
                return;
            }
            
            logger.info(`Dashboard脚本: ${dashboardScript}`, MODULE);
            
            // 创建终端（工作目录为extension）
            const terminal = vscode.window.createTerminal({
                name: 'TRQuant Dashboard',
                cwd: extensionPath
            });
            terminal.show();
            
            // 跨平台命令
            const isWindows = process.platform === 'win32';
            
            // 检查extension内的虚拟环境
            const extVenvActivate = isWindows 
                ? path.join(extensionPath, 'venv', 'Scripts', 'activate.bat')
                : path.join(extensionPath, 'venv', 'bin', 'activate');
            
            // 也检查工作区根目录的虚拟环境
            const rootVenvActivate = isWindows
                ? path.join(workspaceFolder.uri.fsPath, 'venv', 'Scripts', 'activate.bat')
                : path.join(workspaceFolder.uri.fsPath, 'venv', 'bin', 'activate');
            
            let command = '';
            if (fs.existsSync(extVenvActivate)) {
                // 使用extension内的虚拟环境
                command = isWindows 
                    ? `"${extVenvActivate}" && python start_dashboard.py`
                    : `source "${extVenvActivate}" && python start_dashboard.py`;
                logger.info('使用extension venv', MODULE);
            } else if (fs.existsSync(rootVenvActivate)) {
                // 使用工作区根目录的虚拟环境
                command = isWindows
                    ? `"${rootVenvActivate}" && python start_dashboard.py`
                    : `source "${rootVenvActivate}" && python start_dashboard.py`;
                logger.info('使用工作区根目录venv', MODULE);
            } else {
                // 使用系统Python
                const pythonCmd = isWindows ? 'python' : 'python3';
                command = `${pythonCmd} start_dashboard.py`;
                logger.info('使用系统Python', MODULE);
            }
            
            terminal.sendText(command);
            vscode.window.showInformationMessage('📁 正在启动Extension Dashboard...');
            
            // 等待服务器启动后打开浏览器
            setTimeout(() => {
                vscode.env.openExternal(vscode.Uri.parse('http://localhost:5000'));
                vscode.window.showInformationMessage('✅ Extension Dashboard已启动 - http://localhost:5000');
            }, 3000);
            
        } catch (error) {
            const msg = error instanceof Error ? error.message : String(error);
            logger.error(`启动Dashboard失败: ${msg}`, MODULE);
            vscode.window.showErrorMessage(`启动文件管理系统失败: ${msg}`);
        }
    }

    /**
     * 生成专业投资报告
     * 综合所有工作流步骤的结果，由AI生成专业报告
     */
    private async generateInvestmentReport(): Promise<void> {
        logger.info('生成投资报告...', MODULE);
        
        try {
            vscode.window.showInformationMessage('📊 正在生成投资报告...');
            
            const response = await this._client.callBridge('generate_investment_report', {
                type: 'full'
            });
            
            if (response.ok && response.data) {
                const data = response.data as { path?: string; file?: string };
                const reportPath = data.path || data.file || '';
                vscode.window.showInformationMessage(
                    `✅ 报告已生成: ${path.basename(reportPath)}`,
                    '打开报告'
                ).then(selection => {
                    if (selection === '打开报告') {
                        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
                        if (workspaceFolder && reportPath) {
                            const fullPath = path.join(workspaceFolder.uri.fsPath, reportPath);
                            vscode.env.openExternal(vscode.Uri.file(fullPath));
                        }
                    }
                });
            } else {
                vscode.window.showErrorMessage(`生成报告失败: ${response.error || '未知错误'}`);
            }
        } catch (error) {
            const msg = error instanceof Error ? error.message : String(error);
            logger.error(`生成报告失败: ${msg}`, MODULE);
            vscode.window.showErrorMessage(`生成报告失败: ${msg}`);
        }
    }

    /**
     * 同步文件变化
     * 检测Cursor中操作产生的代码、回测等文件
     */
    private async syncFileChanges(): Promise<void> {
        logger.info('同步文件变化...', MODULE);
        
        try {
            const response = await this._client.callBridge('sync_file_changes', {});
            
            if (response.ok && response.data) {
                const data = response.data as { total_count?: number; recent_files?: Array<{ name: string }> };
                const count = data.total_count || 0;
                const recentFiles = data.recent_files || [];
                
                if (count > 0) {
                    const fileList = recentFiles.slice(0, 3).map(f => f.name).join(', ');
                    vscode.window.showInformationMessage(
                        `🔄 检测到 ${count} 个更新文件: ${fileList}${count > 3 ? '...' : ''}`
                    );
                } else {
                    vscode.window.showInformationMessage('✅ 文件已是最新状态');
                }
            }
        } catch (error) {
            const msg = error instanceof Error ? error.message : String(error);
            logger.error(`同步失败: ${msg}`, MODULE);
        }
    }

    /**
     * 导出数据库
     */
    private async exportDatabase(): Promise<void> {
        logger.info('导出数据库...', MODULE);
        
        try {
            vscode.window.showInformationMessage('🗄️ 正在导出数据库...');
            
            const response = await this._client.callBridge('export_database', {});
            
            if (response.ok && response.data) {
                const data = response.data as { collections?: number; total_docs?: number; file?: string };
                vscode.window.showInformationMessage(
                    `✅ 数据库已导出: ${data.collections || 0}个集合, ${data.total_docs || 0}条记录`,
                    '打开文件'
                ).then(selection => {
                    if (selection === '打开文件') {
                        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
                        if (workspaceFolder && data.file) {
                            vscode.env.openExternal(vscode.Uri.file(data.file));
                        }
                    }
                });
            } else {
                vscode.window.showErrorMessage(`导出失败: ${response.error || '请确保MongoDB已启动'}`);
            }
        } catch (error) {
            const msg = error instanceof Error ? error.message : String(error);
            logger.error(`导出数据库失败: ${msg}`, MODULE);
            vscode.window.showErrorMessage(`导出数据库失败: ${msg}`);
        }
    }

    /**
     * 打开文件
     * 支持代码文件在编辑器打开，其他文件用默认程序
     */
    private async openFile(filePath: string): Promise<void> {
        if (!filePath) return;
        
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) return;
        
        const fullPath = path.join(workspaceFolder.uri.fsPath, filePath);
        const ext = path.extname(filePath).toLowerCase();
        
        // 代码文件在编辑器中打开
        if (['.py', '.json', '.yaml', '.yml', '.md', '.txt'].includes(ext)) {
            const doc = await vscode.workspace.openTextDocument(fullPath);
            await vscode.window.showTextDocument(doc);
        } 
        // HTML/PDF等用外部程序
        else {
            vscode.env.openExternal(vscode.Uri.file(fullPath));
        }
    }

    public updateContent(): void {
        this._panel.webview.html = this.generateHtml();
    }

    private generateHtml(): string {
        return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>韬睿量化工作台</title>
    <style>
        :root {
            --bg-dark: #0a0e14;
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-card: #1c2128;
            --bg-hover: #262c36;
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --text-muted: #6e7681;
            --accent-gold: #f0b429;
            --accent-green: #3fb950;
            --accent-blue: #58a6ff;
            --accent-purple: #a371f7;
            --accent-red: #f85149;
            --accent-orange: #f0883e;
            --border-color: #30363d;
            --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --gradient-gold: linear-gradient(135deg, #f0b429 0%, #e85d04 100%);
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg-dark);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
        }
        
        /* 顶部标题栏 */
        .header {
            background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 100%);
            padding: 24px 32px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header-left {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        
        .logo {
            width: 48px;
            height: 48px;
            background: var(--gradient-gold);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            font-weight: bold;
            color: #fff;
            box-shadow: 0 4px 12px rgba(240, 180, 41, 0.3);
        }
        
        .header-title h1 {
            font-size: 24px;
            font-weight: 700;
            background: linear-gradient(90deg, var(--accent-gold), #fff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 1px;
        }
        
        .header-title .subtitle {
            font-size: 13px;
            color: var(--text-muted);
            margin-top: 4px;
        }
        
        .header-right {
            display: flex;
            gap: 12px;
        }
        
        .header-btn {
            padding: 10px 20px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: var(--text-secondary);
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .header-btn:hover {
            background: var(--bg-hover);
            border-color: var(--accent-blue);
            color: var(--text-primary);
        }
        
        .header-btn.primary {
            background: var(--gradient-primary);
            border: none;
            color: #fff;
        }
        
        .header-btn.primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        /* 主容器 */
        .main-container {
            padding: 24px 32px;
            max-width: 1600px;
            margin: 0 auto;
        }
        
        /* 市场状态卡片 */
        .market-section {
            margin-bottom: 24px;
        }
        
        .market-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 16px;
        }
        
        .market-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            transition: all 0.2s;
        }
        
        .market-card:hover {
            transform: translateY(-2px);
            border-color: var(--accent-blue);
        }
        
        .market-card.regime {
            background: linear-gradient(135deg, rgba(63, 185, 80, 0.1), rgba(88, 166, 255, 0.1));
            border-color: var(--accent-green);
        }
        
        .market-card .label {
            font-size: 12px;
            color: var(--text-muted);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .market-card .value {
            font-size: 24px;
            font-weight: 700;
        }
        
        .market-card .change {
            font-size: 14px;
            margin-top: 4px;
        }
        
        .market-card .change.up { color: var(--accent-red); }
        .market-card .change.down { color: var(--accent-green); }
        
        .market-card.regime .value {
            color: var(--accent-green);
        }
        
        /* 双栏布局 */
        .content-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 24px;
        }
        
        .card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
        }
        
        .card-header {
            padding: 16px 20px;
            background: rgba(0, 0, 0, 0.2);
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .card-header h3 {
            font-size: 15px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .card-header .actions {
            display: flex;
            gap: 8px;
        }
        
        .card-header .btn-small {
            padding: 6px 12px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            color: var(--text-secondary);
            font-size: 12px;
            cursor: pointer;
        }
        
        .card-header .btn-small:hover {
            background: var(--accent-blue);
            border-color: var(--accent-blue);
            color: #fff;
        }
        
        .card-body {
            padding: 20px;
        }
        
        /* 投资主线列表 */
        .mainline-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .mainline-item {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 14px 16px;
            background: var(--bg-card);
            border-radius: 8px;
            transition: all 0.2s;
            cursor: pointer;
        }
        
        .mainline-item:hover {
            background: var(--bg-hover);
            transform: translateX(4px);
        }
        
        .mainline-rank {
            width: 28px;
            height: 28px;
            background: var(--gradient-gold);
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            font-weight: 700;
            color: #fff;
        }
        
        .mainline-rank.silver { background: linear-gradient(135deg, #9ca3af, #6b7280); }
        .mainline-rank.bronze { background: linear-gradient(135deg, #d97706, #92400e); }
        
        .mainline-info {
            flex: 1;
        }
        
        .mainline-name {
            font-size: 15px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        
        .mainline-industries {
            font-size: 12px;
            color: var(--text-muted);
        }
        
        .mainline-score {
            font-size: 20px;
            font-weight: 700;
            color: var(--accent-gold);
        }
        
        /* 因子列表 */
        .factor-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .factor-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 14px 16px;
            background: var(--bg-card);
            border-radius: 8px;
        }
        
        .factor-icon {
            width: 36px;
            height: 36px;
            background: var(--gradient-primary);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
        }
        
        .factor-info {
            flex: 1;
        }
        
        .factor-name {
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 2px;
        }
        
        .factor-category {
            font-size: 11px;
            color: var(--text-muted);
        }
        
        .factor-weight {
            font-size: 16px;
            font-weight: 700;
            color: var(--accent-purple);
        }
        
        /* 8步骤工作流 */
        .workflow-section {
            margin-bottom: 24px;
        }
        
        .section-title {
            font-size: 13px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 16px;
            padding-left: 4px;
        }
        
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        
        .run-all-btn {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.3s;
        }
        .run-all-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
        }
        
        .workflow-container {
            display: flex;
            gap: 20px;
        }
        
        .workflow-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            flex: 1;
        }
        
        .workflow-step {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px 12px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            position: relative;
        }
        
        .workflow-step::after {
            display: none;
        }
        
        .workflow-step:last-child::after {
            display: none;
        }
        
        .workflow-step:hover {
            transform: translateY(-4px);
            border-color: var(--accent-blue);
            box-shadow: 0 8px 24px rgba(88, 166, 255, 0.15);
        }
        
        .workflow-step.active {
            background: linear-gradient(135deg, rgba(88, 166, 255, 0.15), rgba(163, 113, 247, 0.15));
            border-color: var(--accent-blue);
        }
        
        .step-number {
            width: 24px;
            height: 24px;
            background: var(--bg-card);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            font-weight: 600;
            color: var(--text-muted);
            margin: 0 auto 12px;
        }
        
        .workflow-step:hover .step-number {
            background: var(--accent-blue);
            color: #fff;
        }
        
        .step-icon {
            font-size: 28px;
            margin-bottom: 10px;
        }
        
        .step-name {
            font-size: 13px;
            font-weight: 600;
            color: var(--text-secondary);
        }
        
        .workflow-step:hover .step-name {
            color: var(--text-primary);
        }
        
        .step-status {
            position: absolute;
            top: 8px;
            right: 8px;
            font-size: 14px;
        }
        
        .workflow-step.running {
            border-color: #f59e0b;
            animation: pulse 1.5s infinite;
        }
        
        .workflow-step.completed {
            border-color: #10b981;
        }
        
        .workflow-step.failed {
            border-color: #ef4444;
        }
        
        @keyframes pulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4); }
            50% { box-shadow: 0 0 0 8px rgba(245, 158, 11, 0); }
        }
        
        /* 结果面板 */
        .result-panel {
            flex: 1;
            min-width: 400px;
            max-width: 500px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px;
            display: none;
        }
        
        .result-panel.visible {
            display: block;
        }
        
        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .result-title {
            font-size: 16px;
            font-weight: 600;
            color: var(--text-primary);
        }
        
        .close-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 16px;
            padding: 4px 8px;
            border-radius: 4px;
        }
        .close-btn:hover {
            background: var(--bg-hover);
            color: var(--text-primary);
        }
        
        .result-summary {
            background: var(--bg-card);
            padding: 12px;
            border-radius: 8px;
            color: var(--text-secondary);
            font-size: 14px;
            margin-bottom: 12px;
        }
        
        .result-progress {
            margin-bottom: 12px;
        }
        
        .progress-bar {
            height: 6px;
            background: var(--bg-card);
            border-radius: 3px;
            overflow: hidden;
            margin-bottom: 8px;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #6366f1, #8b5cf6);
            width: 0%;
            transition: width 0.3s;
        }
        
        .progress-text {
            font-size: 12px;
            color: var(--text-muted);
        }
        
        .result-details {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px;
            max-height: 300px;
            overflow-y: auto;
            font-size: 13px;
            margin-bottom: 12px;
        }
        
        .result-details table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .result-details th, .result-details td {
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }
        
        .result-details th {
            background: var(--bg-secondary);
            font-weight: 600;
            color: var(--text-secondary);
        }
        
        .result-files {
            max-height: 100px;
            overflow-y: auto;
        }
        
        .file-item {
            display: flex;
            justify-content: space-between;
            padding: 8px;
            background: var(--bg-card);
            border-radius: 6px;
            margin-bottom: 4px;
            cursor: pointer;
            font-size: 12px;
        }
        .file-item:hover {
            background: var(--bg-hover);
        }
        
        /* 快捷操作区 */
        .quick-section {
            margin-bottom: 24px;
        }
        
        .quick-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
        }
        
        .quick-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 16px;
        }
        
        .quick-card:hover {
            transform: translateY(-2px);
            border-color: var(--accent-blue);
        }
        
        .quick-card.highlight {
            background: linear-gradient(135deg, rgba(240, 180, 41, 0.1), rgba(232, 93, 4, 0.1));
            border-color: var(--accent-gold);
        }
        
        .quick-icon {
            width: 48px;
            height: 48px;
            background: var(--bg-card);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
        }
        
        .quick-card.highlight .quick-icon {
            background: var(--gradient-gold);
        }
        
        .quick-info h4 {
            font-size: 15px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        
        .quick-info p {
            font-size: 12px;
            color: var(--text-muted);
        }
        
        /* 底部双栏 */
        .bottom-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }
        
        .project-list, .backtest-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .project-item, .backtest-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            background: var(--bg-card);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .project-item:hover, .backtest-item:hover {
            background: var(--bg-hover);
        }
        
        .item-name {
            font-size: 14px;
            font-weight: 500;
        }
        
        .item-date {
            font-size: 12px;
            color: var(--text-muted);
        }
        
        .item-return {
            font-size: 14px;
            font-weight: 600;
        }
        
        .item-return.positive { color: var(--accent-red); }
        .item-return.negative { color: var(--accent-green); }
        
        /* 加载状态 */
        .loading-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(10, 14, 20, 0.8);
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        
        .loading-overlay.active {
            display: flex;
        }
        
        .loading-spinner {
            width: 48px;
            height: 48px;
            border: 3px solid var(--border-color);
            border-top-color: var(--accent-gold);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* 空状态 */
        .empty-state {
            text-align: center;
            padding: 32px;
            color: var(--text-muted);
        }
        
        .empty-state .icon {
            font-size: 48px;
            margin-bottom: 12px;
            opacity: 0.5;
        }
        
        /* 响应式 */
        @media (max-width: 1400px) {
            .workflow-grid {
                grid-template-columns: repeat(4, 1fr);
            }
            .workflow-step::after {
                display: none;
            }
        }
        
        @media (max-width: 1000px) {
            .content-grid, .bottom-grid {
                grid-template-columns: 1fr;
            }
            .market-grid {
                grid-template-columns: repeat(3, 1fr);
            }
            .quick-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
    </style>
</head>
<body>
    <!-- 顶部标题栏 -->
    <div class="header">
        <div class="header-left">
            <div class="logo">TR</div>
            <div class="header-title">
                <h1>韬睿量化工作台</h1>
                <div class="subtitle">TRQuant Professional - A股完整投资流程系统</div>
            </div>
        </div>
        <div class="header-right">
            <button class="header-btn" onclick="vscode.postMessage({command: 'refreshAll'})">
                🔄 刷新数据
            </button>
            <button class="header-btn" onclick="vscode.postMessage({command: 'openSettings'})">
                ⚙️ 设置
            </button>
            <button class="header-btn primary" onclick="openWorkflowPanel()">
                ▶️ 打开工作流面板
            </button>
        </div>
    </div>
    
    <div class="main-container">
        <!-- 快捷操作（置顶） -->
        <div class="quick-section">
            <div class="section-title">⚡ 快捷操作</div>
            <div class="quick-grid">
                <div class="quick-card highlight" onclick="console.log('点击新建项目'); vscode.postMessage({command: 'createProject'})">
                    <div class="quick-icon">📁</div>
                    <div class="quick-info">
                        <h4>新建项目</h4>
                        <p>一键生成中国风策略</p>
                    </div>
                </div>
                <div class="quick-card" onclick="vscode.postMessage({command: 'launchFileDashboard'})">
                    <div class="quick-icon">📂</div>
                    <div class="quick-info">
                        <h4>文件系统</h4>
                        <p>策略/报告/数据管理</p>
                    </div>
                </div>
                <div class="quick-card" onclick="openWorkflowPanel()">
                    <div class="quick-icon">🔄</div>
                    <div class="quick-info">
                        <h4>工作流面板</h4>
                        <p>查看完整投资流程</p>
                    </div>
                </div>
                <div class="quick-card" onclick="vscode.postMessage({command: 'runBacktest'})">
                    <div class="quick-icon">🧪</div>
                    <div class="quick-info">
                        <h4>运行回测</h4>
                        <p>配置并执行策略回测</p>
                    </div>
                </div>
                <div class="quick-card" onclick="vscode.postMessage({command: 'launchAShareManual'})">
                    <div class="quick-icon">📚</div>
                    <div class="quick-info">
                        <h4>实操手册</h4>
                        <p>A股投资指南</p>
                    </div>
                </div>
                <div class="quick-card" onclick="vscode.postMessage({command: 'generateInvestmentReport'})">
                    <div class="quick-icon">📊</div>
                    <div class="quick-info">
                        <h4>生成报告</h4>
                        <p>AI投资分析报告</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- 市场状态 -->
        <div class="market-section">
            <div class="market-grid" id="marketGrid">
                <div class="market-card regime">
                    <div class="label">市场状态</div>
                    <div class="value" id="marketRegime">加载中...</div>
                    <div class="change" id="marketStyle">-</div>
                </div>
                <div class="market-card">
                    <div class="label">上证指数</div>
                    <div class="value" id="shIndex">-</div>
                    <div class="change" id="shChange">-</div>
                </div>
                <div class="market-card">
                    <div class="label">深证成指</div>
                    <div class="value" id="szIndex">-</div>
                    <div class="change" id="szChange">-</div>
                </div>
                <div class="market-card">
                    <div class="label">创业板指</div>
                    <div class="value" id="cyIndex">-</div>
                    <div class="change" id="cyChange">-</div>
                </div>
                <div class="market-card">
                    <div class="label">北向资金</div>
                    <div class="value" id="northFlow">-</div>
                    <div class="change" id="northChange">-</div>
                </div>
            </div>
        </div>
        
        <!-- 投资主线 & 推荐因子 -->
        <div class="content-grid">
            <!-- 投资主线 -->
            <div class="card">
                <div class="card-header">
                    <h3>🔥 当前投资主线 TOP5</h3>
                    <div class="actions">
                        <button class="btn-small" onclick="vscode.postMessage({command: 'refreshMainlines'})">刷新</button>
                        <button class="btn-small" onclick="vscode.postMessage({command: 'openStep', step: 3})">查看全部</button>
                    </div>
                </div>
                <div class="card-body">
                    <div class="mainline-list" id="mainlineList">
                        <div class="empty-state">
                            <div class="icon">🔥</div>
                            <div>点击刷新获取投资主线</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 推荐因子 -->
            <div class="card">
                <div class="card-header">
                    <h3>📊 智能推荐因子</h3>
                    <div class="actions">
                        <button class="btn-small" onclick="vscode.postMessage({command: 'refreshFactors'})">刷新</button>
                        <button class="btn-small" onclick="vscode.postMessage({command: 'generateStrategy'})">生成策略</button>
                    </div>
                </div>
                <div class="card-body">
                    <div class="factor-list" id="factorList">
                        <div class="empty-state">
                            <div class="icon">📊</div>
                            <div>点击刷新获取因子推荐</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 8步骤工作流 -->
        <div class="workflow-section">
            <div class="section-header">
                <div class="section-title">📋 8步骤投资工作流</div>
                <button class="run-all-btn" onclick="vscode.postMessage({command: 'runFullWorkflow'})">
                    ▶️ 一键执行全部
                </button>
            </div>
            <div class="workflow-container">
                <div class="workflow-grid">
                    <div class="workflow-step" id="step-1" onclick="runStep(1)">
                        <div class="step-number">1</div>
                        <div class="step-icon">📡</div>
                        <div class="step-name">信息获取</div>
                        <div class="step-status" id="status-1">▶️</div>
                    </div>
                    <div class="workflow-step" id="step-2" onclick="runStep(2)">
                        <div class="step-number">2</div>
                        <div class="step-icon">📈</div>
                        <div class="step-name">市场趋势</div>
                        <div class="step-status" id="status-2">▶️</div>
                    </div>
                    <div class="workflow-step" id="step-3" onclick="runStep(3)">
                        <div class="step-number">3</div>
                        <div class="step-icon">🔥</div>
                        <div class="step-name">投资主线</div>
                        <div class="step-status" id="status-3">▶️</div>
                    </div>
                    <div class="workflow-step" id="step-4" onclick="runStep(4)">
                        <div class="step-number">4</div>
                        <div class="step-icon">📦</div>
                        <div class="step-name">候选池</div>
                        <div class="step-status" id="status-4">▶️</div>
                    </div>
                    <div class="workflow-step" id="step-5" onclick="runStep(5)">
                        <div class="step-number">5</div>
                        <div class="step-icon">📊</div>
                        <div class="step-name">因子构建</div>
                        <div class="step-status" id="status-5">▶️</div>
                    </div>
                    <div class="workflow-step" id="step-6" onclick="runStep(6)">
                        <div class="step-number">6</div>
                        <div class="step-icon">🛠️</div>
                        <div class="step-name">策略开发</div>
                        <div class="step-status" id="status-6">▶️</div>
                    </div>
                    <div class="workflow-step" id="step-7" onclick="runStep(7)">
                        <div class="step-number">7</div>
                        <div class="step-icon">🔄</div>
                        <div class="step-name">回测验证</div>
                        <div class="step-status" id="status-7">▶️</div>
                    </div>
                    <div class="workflow-step" id="step-8" onclick="runStep(8)">
                        <div class="step-number">8</div>
                        <div class="step-icon">🚀</div>
                        <div class="step-name">实盘交易</div>
                        <div class="step-status" id="status-8">▶️</div>
                    </div>
                </div>
                
                <!-- 执行结果区域 -->
                <div class="result-panel" id="result-panel">
                    <div class="result-header">
                        <span class="result-title" id="result-title">📋 执行结果</span>
                        <button class="close-btn" onclick="hideResultPanel()">✕</button>
                    </div>
                    <div class="result-summary" id="result-summary">
                        点击左侧步骤开始执行...
                    </div>
                    <div class="result-progress" id="result-progress" style="display:none;">
                        <div class="progress-bar"><div class="progress-fill" id="progress-fill"></div></div>
                        <span class="progress-text" id="progress-text">执行中...</span>
                    </div>
                    <div class="result-details" id="result-details"></div>
                    <div class="result-files" id="result-files"></div>
                </div>
            </div>
        </div>
        
        <!-- 快捷操作 -->
        <div class="quick-section">
            <div class="section-title">⚡ 快捷操作</div>
            <div class="quick-grid">
                <div class="quick-card highlight" onclick="vscode.postMessage({command: 'openBacktestConfig'})">
                    <div class="quick-icon">🧪</div>
                    <div class="quick-info">
                        <h4>回测配置</h4>
                        <p>配置并运行策略回测</p>
                    </div>
                </div>
                <div class="quick-card" onclick="vscode.postMessage({command: 'createProject'})">
                    <div class="quick-icon">📁</div>
                    <div class="quick-info">
                        <h4>新建项目</h4>
                        <p>创建新的量化项目</p>
                    </div>
                </div>
                <div class="quick-card" onclick="vscode.postMessage({command: 'generateStrategy'})">
                    <div class="quick-icon">🤖</div>
                    <div class="quick-info">
                        <h4>AI生成策略</h4>
                        <p>智能生成PTrade代码</p>
                    </div>
                </div>
                <div class="quick-card" onclick="vscode.postMessage({command: 'showLogs'})">
                    <div class="quick-icon">📋</div>
                    <div class="quick-info">
                        <h4>查看日志</h4>
                        <p>系统运行日志</p>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 系统管理 -->
        <div class="quick-section">
            <div class="section-title">🔧 系统管理与文件中心</div>
            <div class="quick-grid">
                <div class="quick-card highlight" onclick="vscode.postMessage({command: 'launchFileDashboard'})">
                    <div class="quick-icon">📁</div>
                    <div class="quick-info">
                        <h4>文件管理系统</h4>
                        <p>Web仪表盘(策略/报告/数据库)</p>
                    </div>
                </div>
                <div class="quick-card" onclick="vscode.postMessage({command: 'generateInvestmentReport'})">
                    <div class="quick-icon">📊</div>
                    <div class="quick-info">
                        <h4>生成投资报告</h4>
                        <p>AI综合分析报告</p>
                    </div>
                </div>
                <div class="quick-card" onclick="vscode.postMessage({command: 'syncFileChanges'})">
                    <div class="quick-icon">🔄</div>
                    <div class="quick-info">
                        <h4>智能同步</h4>
                        <p>检测更新的文件</p>
                    </div>
                </div>
                <div class="quick-card" onclick="vscode.postMessage({command: 'exportDatabase'})">
                    <div class="quick-icon">🗄️</div>
                    <div class="quick-info">
                        <h4>数据库管理</h4>
                        <p>导出/备份MongoDB</p>
                    </div>
                </div>
                <div class="quick-card" onclick="vscode.postMessage({command: 'openSettings'})">
                    <div class="quick-icon">⚙️</div>
                    <div class="quick-info">
                        <h4>系统设置</h4>
                        <p>配置参数管理</p>
                    </div>
                </div>
                <div class="quick-card" onclick="vscode.postMessage({command: 'showLogs'})">
                    <div class="quick-icon">📋</div>
                    <div class="quick-info">
                        <h4>运行日志</h4>
                        <p>系统运行日志</p>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 最近项目 & 回测 -->
        <div class="bottom-grid">
            <div class="card">
                <div class="card-header">
                    <h3>📁 最近项目</h3>
                    <div class="actions">
                        <button class="btn-small" onclick="vscode.postMessage({command: 'openProject'})">打开项目</button>
                    </div>
                </div>
                <div class="card-body">
                    <div class="project-list" id="projectList">
                        <div class="project-item">
                            <div>
                                <div class="item-name">🐉 睿智金龙</div>
                                <div class="item-date">2024-12-03</div>
                            </div>
                            <span style="color: var(--text-muted)">→</span>
                        </div>
                        <div class="project-item">
                            <div>
                                <div class="item-name">🦅 灵动碧鹤</div>
                                <div class="item-date">2024-12-02</div>
                            </div>
                            <span style="color: var(--text-muted)">→</span>
                        </div>
                        <div class="project-item">
                            <div>
                                <div class="item-name">🎋 飘逸紫竹</div>
                                <div class="item-date">2024-12-01</div>
                            </div>
                            <span style="color: var(--text-muted)">→</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <h3>📊 最近回测</h3>
                    <div class="actions">
                        <button class="btn-small" onclick="vscode.postMessage({command: 'openStep', step: 7})">查看全部</button>
                    </div>
                </div>
                <div class="card-body">
                    <div class="backtest-list" id="backtestList">
                        <div class="backtest-item">
                            <div>
                                <div class="item-name">test1 动量成长策略</div>
                                <div class="item-date">2024-12-03 15:30</div>
                            </div>
                            <div class="item-return positive">+15.2%</div>
                        </div>
                        <div class="backtest-item">
                            <div>
                                <div class="item-name">momentum 策略</div>
                                <div class="item-date">2024-12-02 10:15</div>
                            </div>
                            <div class="item-return positive">+8.5%</div>
                        </div>
                        <div class="backtest-item">
                            <div>
                                <div class="item-name">multi_factor 多因子</div>
                                <div class="item-date">2024-12-01 14:20</div>
                            </div>
                            <div class="item-return negative">-2.1%</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- 加载遮罩 -->
    <div class="loading-overlay" id="loadingOverlay">
        <div class="loading-spinner"></div>
    </div>
    
    <script>
        const vscode = acquireVsCodeApi();
        
        // 更新市场状态
        function updateMarketStatus(data) {
            if (!data) return;
            
            // 市场Regime
            document.getElementById('marketRegime').textContent = data.regime_cn || data.regime || '中性';
            document.getElementById('marketStyle').textContent = data.style_rotation || '均衡';
            
            // 指数数据
            if (data.indices && data.indices.length >= 3) {
                const [sh, sz, cy] = data.indices;
                
                document.getElementById('shIndex').textContent = sh.value?.toFixed(2) || '-';
                document.getElementById('shChange').textContent = (sh.change >= 0 ? '+' : '') + (sh.change * 100)?.toFixed(2) + '%';
                document.getElementById('shChange').className = 'change ' + (sh.change >= 0 ? 'up' : 'down');
                
                document.getElementById('szIndex').textContent = sz.value?.toFixed(2) || '-';
                document.getElementById('szChange').textContent = (sz.change >= 0 ? '+' : '') + (sz.change * 100)?.toFixed(2) + '%';
                document.getElementById('szChange').className = 'change ' + (sz.change >= 0 ? 'up' : 'down');
                
                document.getElementById('cyIndex').textContent = cy.value?.toFixed(2) || '-';
                document.getElementById('cyChange').textContent = (cy.change >= 0 ? '+' : '') + (cy.change * 100)?.toFixed(2) + '%';
                document.getElementById('cyChange').className = 'change ' + (cy.change >= 0 ? 'up' : 'down');
            }
        }
        
        // 更新投资主线
        function updateMainlines(data) {
            const container = document.getElementById('mainlineList');
            if (!data || data.length === 0) {
                container.innerHTML = '<div class="empty-state"><div class="icon">🔥</div><div>暂无投资主线数据</div></div>';
                return;
            }
            
            container.innerHTML = data.map((m, i) => {
                const rankClass = i === 0 ? '' : i === 1 ? 'silver' : i === 2 ? 'bronze' : '';
                return \`
                    <div class="mainline-item">
                        <div class="mainline-rank \${rankClass}">\${i + 1}</div>
                        <div class="mainline-info">
                            <div class="mainline-name">\${m.name}</div>
                            <div class="mainline-industries">\${m.industries?.slice(0, 3).join(' · ') || ''}</div>
                        </div>
                        <div class="mainline-score">⭐\${m.score}</div>
                    </div>
                \`;
            }).join('');
        }
        
        // 更新因子
        function updateFactors(data) {
            const container = document.getElementById('factorList');
            if (!data || data.length === 0) {
                container.innerHTML = '<div class="empty-state"><div class="icon">📊</div><div>暂无因子推荐</div></div>';
                return;
            }
            
            const icons = ['📈', '💹', '💰', '⚡', '🎯'];
            container.innerHTML = data.map((f, i) => \`
                <div class="factor-item">
                    <div class="factor-icon">\${icons[i % icons.length]}</div>
                    <div class="factor-info">
                        <div class="factor-name">\${f.name}</div>
                        <div class="factor-category">\${f.category || '量化因子'}</div>
                    </div>
                    <div class="factor-weight">\${(f.weight * 100).toFixed(0)}%</div>
                </div>
            \`).join('');
        }
        
        // =====================
        // 工作流步骤执行
        // =====================
        
        function runStep(step) {
            vscode.postMessage({command: 'openStep', step: step});
        }
        
        function showResultPanel() {
            document.getElementById('result-panel').classList.add('visible');
        }
        
        function hideResultPanel() {
            document.getElementById('result-panel').classList.remove('visible');
        }
        
        function setStepStatus(step, status) {
            const stepEl = document.getElementById('step-' + step);
            const statusEl = document.getElementById('status-' + step);
            
            // 移除所有状态类
            stepEl.classList.remove('running', 'completed', 'failed');
            
            switch(status) {
                case 'running':
                    stepEl.classList.add('running');
                    statusEl.textContent = '⏳';
                    break;
                case 'completed':
                    stepEl.classList.add('completed');
                    statusEl.textContent = '✅';
                    break;
                case 'failed':
                    stepEl.classList.add('failed');
                    statusEl.textContent = '❌';
                    break;
                default:
                    statusEl.textContent = '▶️';
            }
        }
        
        function showProgress(show, value, text) {
            const el = document.getElementById('result-progress');
            el.style.display = show ? 'block' : 'none';
            if (show) {
                document.getElementById('progress-fill').style.width = value + '%';
                document.getElementById('progress-text').textContent = text || '执行中...';
            }
        }
        
        function formatDetails(details) {
            if (!details || Object.keys(details).length === 0) {
                return '<div style="color:var(--text-muted);">无详细数据</div>';
            }
            
            let html = '';
            
            // 投资主线
            if (details.top_mainlines) {
                const mainlines = details.top_mainlines;
                html += '<div style="margin-bottom:12px;"><strong style="color:#f59e0b;">🔥 投资主线 TOP' + mainlines.length + '</strong></div>';
                html += '<table><tr><th>排名</th><th>名称</th><th>评分</th></tr>';
                mainlines.slice(0, 10).forEach(ml => {
                    html += '<tr><td>#' + (ml.rank || '-') + '</td><td>' + (ml.name || '-') + '</td><td style="color:#10b981;">' + ((ml.composite_score || ml.score || 0).toFixed?.(1) || ml.composite_score || ml.score || '-') + '</td></tr>';
                });
                if (mainlines.length > 10) {
                    html += '<tr><td colspan="3" style="color:var(--text-muted);">... 共' + mainlines.length + '个主线</td></tr>';
                }
                html += '</table>';
            }
            
            // 候选池股票
            else if (details.stocks) {
                const stocks = details.stocks;
                html += '<div style="margin-bottom:12px;"><strong style="color:#8b5cf6;">📦 候选池股票 (' + stocks.length + '只)</strong></div>';
                html += '<table><tr><th>代码</th><th>名称</th><th>来源</th><th>评分</th></tr>';
                stocks.slice(0, 15).forEach(s => {
                    html += '<tr><td>' + (s.code || '-') + '</td><td>' + (s.name || '-') + '</td><td style="color:var(--text-muted);">' + (s.source || '-') + '</td><td style="color:#10b981;">' + ((s.score || 0).toFixed?.(1) || '-') + '</td></tr>';
                });
                html += '</table>';
            }
            
            // 推荐因子
            else if (details.recommended_factors) {
                const factors = details.recommended_factors;
                html += '<div style="margin-bottom:12px;"><strong style="color:#10b981;">🧮 推荐因子</strong></div>';
                html += '<ul style="margin:0;padding-left:20px;">';
                factors.forEach(f => {
                    const weight = ((f.weight || 0) * 100).toFixed(0);
                    html += '<li style="margin:6px 0;"><strong>' + (f.name || '-') + '</strong> (权重' + weight + '%) - ' + (f.reason || '') + '</li>';
                });
                html += '</ul>';
            }
            
            // 数据源检测
            else if (details.jqdata !== undefined || details.akshare !== undefined) {
                html += '<div style="margin-bottom:12px;"><strong style="color:#6366f1;">📡 数据源状态</strong></div>';
                html += '<table><tr><th>数据源</th><th>状态</th></tr>';
                if (details.jqdata !== undefined) {
                    html += '<tr><td>JQData</td><td style="color:' + (details.jqdata ? '#10b981' : '#ef4444') + ';">' + (details.jqdata ? '✅ 可用' : '❌ 不可用') + '</td></tr>';
                }
                if (details.akshare !== undefined) {
                    html += '<tr><td>AKShare</td><td style="color:' + (details.akshare ? '#10b981' : '#ef4444') + ';">' + (details.akshare ? '✅ 可用' : '❌ 不可用') + '</td></tr>';
                }
                html += '</table>';
            }
            
            // 市场趋势
            else if (details.regime || details.trend_strength !== undefined) {
                html += '<div style="margin-bottom:12px;"><strong style="color:#6366f1;">📈 市场趋势分析</strong></div>';
                html += '<table><tr><th>指标</th><th>数值</th></tr>';
                if (details.regime) html += '<tr><td>市场Regime</td><td>' + details.regime + '</td></tr>';
                if (details.trend_strength !== undefined) html += '<tr><td>趋势强度</td><td>' + details.trend_strength + '</td></tr>';
                if (details.volatility !== undefined) html += '<tr><td>波动率</td><td>' + details.volatility + '</td></tr>';
                if (details.style_rotation) html += '<tr><td>风格轮动</td><td>' + details.style_rotation + '</td></tr>';
                html += '</table>';
            }
            
            // 策略文件
            else if (details.strategy_file) {
                html += '<div style="margin-bottom:12px;"><strong style="color:#10b981;">💻 策略生成完成</strong></div>';
                html += '<div style="background:var(--bg-card);padding:12px;border-radius:8px;">';
                html += '<div>📄 策略文件: <strong>' + details.strategy_file.split('/').pop() + '</strong></div>';
                if (details.platform) html += '<div>🎯 目标平台: ' + details.platform + '</div>';
                if (details.style) html += '<div>📊 策略风格: ' + details.style + '</div>';
                html += '</div>';
            }
            
            // 默认JSON显示
            else {
                html += '<pre style="font-size:11px;overflow-x:auto;">' + JSON.stringify(details, null, 2) + '</pre>';
            }
            
            return html;
        }
        
        // 处理消息
        window.addEventListener('message', event => {
            const message = event.data;
            
            switch (message.command) {
                case 'loadingStart':
                    document.getElementById('loadingOverlay').classList.add('active');
                    break;
                case 'loadingEnd':
                    document.getElementById('loadingOverlay').classList.remove('active');
                    break;
                case 'marketStatusUpdated':
                    updateMarketStatus(message.data);
                    break;
                case 'mainlinesUpdated':
                    updateMainlines(message.data);
                    break;
                case 'factorsUpdated':
                    updateFactors(message.data);
                    break;
                    
                // 工作流步骤执行
                case 'stepStarted':
                    setStepStatus(message.step, 'running');
                    showResultPanel();
                    document.getElementById('result-title').textContent = '📋 ' + message.stepName + ' - 执行中';
                    document.getElementById('result-summary').textContent = '正在执行 ' + message.stepName + '...';
                    document.getElementById('result-details').innerHTML = '';
                    showProgress(true, 30, '执行中...');
                    break;
                    
                case 'stepResult':
                    setStepStatus(message.step, message.success ? 'completed' : 'failed');
                    showProgress(false);
                    document.getElementById('result-title').textContent = '📋 ' + message.stepName + ' - ' + (message.success ? '✅ 完成' : '❌ 失败');
                    document.getElementById('result-summary').textContent = message.summary || (message.success ? '执行成功' : '执行失败');
                    document.getElementById('result-details').innerHTML = formatDetails(message.details);
                    break;
                
                // 一键执行全部工作流的消息处理
                case 'workflowProgress':
                    var data = message.data;
                    if (data.currentStep) {
                        setStepStatus(data.currentStep, 'running');
                    }
                    showResultPanel();
                    document.getElementById('result-title').textContent = '🔄 执行工作流 - ' + data.stepName;
                    document.getElementById('result-summary').textContent = '进度: ' + Math.round(data.progress) + '%';
                    showProgress(true, data.progress, data.stepName);
                    break;
                    
                case 'workflowStepResult':
                    var stepData = message.data;
                    if (stepData.stepId) {
                        setStepStatus(stepData.stepId, stepData.success ? 'completed' : 'failed');
                    }
                    // 累加显示结果
                    var detailsEl = document.getElementById('result-details');
                    var stepHtml = '<div style="margin:8px 0;padding:8px;background:var(--bg-card);border-radius:6px;border-left:3px solid ' + 
                        (stepData.success ? '#10b981' : '#ef4444') + ';">';
                    stepHtml += '<strong>' + stepData.stepName + '</strong>: ' + (stepData.success ? '✅' : '❌');
                    stepHtml += '</div>';
                    detailsEl.innerHTML += stepHtml;
                    break;
                    
                case 'workflowComplete':
                    var completeData = message.data;
                    showProgress(false);
                    document.getElementById('result-title').textContent = completeData.hasError ? '⚠️ 工作流完成（部分失败）' : '✅ 工作流执行完成';
                    document.getElementById('result-summary').textContent = '共执行 ' + completeData.results.length + ' 个步骤';
                    
                    // 显示汇总
                    var summaryHtml = '<div style="margin-top:16px;">';
                    summaryHtml += '<h4 style="color:var(--accent-gold);margin-bottom:8px;">执行结果汇总</h4>';
                    completeData.results.forEach(function(r) {
                        summaryHtml += '<div style="display:flex;align-items:center;gap:8px;margin:4px 0;">';
                        summaryHtml += '<span>' + (r.success ? '✅' : '❌') + '</span>';
                        summaryHtml += '<span>' + r.step + '</span>';
                        if (r.error) {
                            summaryHtml += '<span style="color:#ef4444;font-size:11px;">(' + r.error + ')</span>';
                        }
                        summaryHtml += '</div>';
                    });
                    summaryHtml += '</div>';
                    document.getElementById('result-details').innerHTML += summaryHtml;
                    break;
            }
        });
    </script>
</body>
</html>`;
    }

    public dispose(): void {
        MainDashboard.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const d = this._disposables.pop();
            if (d) d.dispose();
        }
    }
}

/**
 * 注册主控制台
 */
export function registerMainDashboard(
    context: vscode.ExtensionContext,
    client: TRQuantClient
): void {
    context.subscriptions.push(
        vscode.commands.registerCommand('trquant.openDashboard', () => {
            MainDashboard.createOrShow(context.extensionUri, client);
        })
    );

    logger.info('投资工作流仪表盘已注册', MODULE);
}

/**
 * 显示主控制台
 */
export function showMainDashboard(
    extensionUri: vscode.Uri,
    client: TRQuantClient
): void {
    MainDashboard.createOrShow(extensionUri, client);
}
