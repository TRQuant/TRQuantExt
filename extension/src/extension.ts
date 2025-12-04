/**
 * TRQuant Cursor Extension
 * ========================
 * 
 * 韬睿量化 - A股量化投资助手
 * 
 * 功能：
 * 1. 获取市场状态和投资主线
 * 2. 推荐因子和生成策略（PTrade/QMT）
 * 3. 通过MCP协议与Cursor AI集成
 * 
 * 架构：
 * - 遵循VS Code Extension最佳实践
 * - 使用依赖注入管理服务
 * - 统一的日志和错误处理
 */

import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import * as cp from 'child_process';

// 核心服务
import { TRQuantClient } from './services/trquantClient';
import { MCPRegistrar } from './services/mcpRegistrar';
import { registerConfigCommands } from './services/projectConfig';
import { registerBacktestManager } from './services/backtestManager';

// 命令
import { getMarketStatus } from './commands/getMarketStatus';
import { getMainlines } from './commands/getMainlines';
import { recommendFactors } from './commands/recommendFactors';
import { generateStrategy } from './commands/generateStrategy';
import { analyzeBacktest } from './commands/analyzeBacktest';
import { runBacktest } from './commands/runBacktest';

// 视图
import { MarketPanel } from './views/marketPanel';
import { DashboardPanel } from './views/dashboardPanel';
import { WelcomePanel } from './views/welcomePanel';
import { registerProjectExplorer } from './views/projectExplorer';
import { registerBacktestReportCommands } from './views/backtestReportPanel';
import { MainDashboard, registerMainDashboard } from './views/mainDashboard';
import { showBacktestConfigPanel } from './views/backtestConfigPanel';
import { registerDataSourcePanel } from './views/dataSourcePanel';
import { registerMarketTrendPanel } from './views/marketTrendPanel';
import { registerMainlinePanel } from './views/mainlinePanel';
import { registerCandidatePoolPanel } from './views/candidatePoolPanel';
import { registerFactorPanel } from './views/factorPanel';
import { registerStrategyOptimizerPanel } from './views/strategyOptimizerPanel';

// 工作流面板（独立GUI）- 现在在 registerCommands 中动态导入
// 快捷操作（侧边栏）
import { registerQuickActionsView } from './providers/quickActionsProvider';
// 项目创建命令
import { registerCreateProjectCommand } from './commands/createProject';
// 策略优化助手
import { registerStrategyOptimizer } from './services/strategyOptimizer';
import { registerStrategyDevPanel } from './views/strategyDevPanel';
import { registerTradingPanel } from './views/tradingPanel';
import { registerFileManagerPanel } from './views/fileManagerPanel';
import { registerKnowledgeBasePanel } from './views/knowledgeBasePanel';
import { registerSystemSettingsPanel } from './views/systemSettingsPanel';
// A股手册直接启动Astro服务器

// 提供者
import { registerStrategyCompletionProvider } from './providers/strategyCompletionProvider';
import { registerStrategyDiagnosticProvider } from './providers/strategyDiagnosticProvider';

// 工具
import { logger, LogLevel } from './utils/logger';
import { config, ConfigManager } from './utils/config';
import { ErrorHandler } from './utils/errors';

const MODULE = 'Extension';

// 全局实例
let client: TRQuantClient;
let statusBarItem: vscode.StatusBarItem;

/**
 * 扩展激活入口
 */
export async function activate(context: vscode.ExtensionContext): Promise<void> {
    console.log('[TRQuant] 🚀 扩展激活开始...');
    logger.info('TRQuant Extension 正在激活...', MODULE);
    
    const startTime = Date.now();

    try {
        // ========== 最优先：注册创建项目命令 ==========
        // 直接在这里注册，确保一定被执行
        console.log('[TRQuant] 📦 注册 createProject 命令...');
        const createProjectDisposable = vscode.commands.registerCommand('trquant.createProject', async () => {
            console.log('[TRQuant] ✅ createProject 命令被触发!');
            vscode.window.setStatusBarMessage('🐉 正在创建项目...', 2000);
            
            try {
                // 获取项目名生成器
                const { generateProjectName } = await import('./utils/projectNameGenerator');
                const defaultName = generateProjectName();
                console.log(`[TRQuant] 生成项目名: ${defaultName}`);
                
                // 确定项目目录
                const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
                let projectsRoot: string;
                
                if (workspaceFolder) {
                    projectsRoot = require('path').join(workspaceFolder.uri.fsPath, 'Projects');
                } else {
                    projectsRoot = require('path').join(context.extensionPath, 'data', 'Projects');
                }
                
                // 确保目录存在
                const fs = require('fs');
                if (!fs.existsSync(projectsRoot)) {
                    fs.mkdirSync(projectsRoot, { recursive: true });
                }
                
                // 弹出输入框
                const projectName = await vscode.window.showInputBox({
                    title: '🐉 创建量化项目',
                    prompt: `项目将创建在: ${projectsRoot}`,
                    value: defaultName,
                    valueSelection: [0, defaultName.length],
                    placeHolder: '输入项目名称（如：祥瑞碧霄凤凰）',
                    ignoreFocusOut: true,
                    validateInput: (value) => {
                        if (!value || value.trim().length === 0) {
                            return '项目名称不能为空';
                        }
                        if (/[<>:"/\\|?*]/.test(value)) {
                            return '项目名称不能包含特殊字符';
                        }
                        return null;
                    }
                });
                
                if (!projectName) {
                    console.log('[TRQuant] 用户取消');
                    return;
                }
                
                // 创建项目
                const finalName = projectName.trim();
                const projectPath = require('path').join(projectsRoot, finalName);
                
                if (!fs.existsSync(projectPath)) {
                    fs.mkdirSync(projectPath, { recursive: true });
                }
                
                // 创建策略文件 - 使用完整的外部模板
                const mainPyPath = require('path').join(projectPath, 'main.py');
                const now = new Date();
                const endDate = new Date(now);
                endDate.setMonth(endDate.getMonth() - 3);
                const startDate = new Date(endDate);
                startDate.setFullYear(startDate.getFullYear() - 1);
                
                const formatDate = (d: Date): string => {
                    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
                };
                
                // 尝试从工作流获取实时数据
                let marketRegime = 'neutral';
                let hotMainlines: Array<{name: string; industries: string[]}> = [];
                
                try {
                    // 获取市场状态
                    const marketResult = await client?.getMarketStatus();
                    if (marketResult?.ok && marketResult?.data?.regime) {
                        marketRegime = marketResult.data.regime;
                        console.log(`[TRQuant] 获取市场状态: ${marketRegime}`);
                    }
                    
                    // 获取投资主线
                    const mainlinesResult = await client?.getMainlines({ top_n: 5 });
                    if (mainlinesResult?.ok && mainlinesResult?.data) {
                        hotMainlines = mainlinesResult.data.slice(0, 5).map((m: any) => ({
                            name: m.name || '',
                            industries: m.industries || []
                        }));
                        console.log(`[TRQuant] 获取投资主线: ${hotMainlines.map(m => m.name).join(', ')}`);
                    }
                } catch (e) {
                    console.log('[TRQuant] 获取工作流数据失败，使用默认值');
                }
                
                // 读取外部模板文件
                const templatePath = require('path').join(context.extensionPath, 'templates', 'strategies', 'multi_factor_template.py');
                let strategyContent: string;
                
                if (fs.existsSync(templatePath)) {
                    strategyContent = fs.readFileSync(templatePath, 'utf-8');
                    console.log('[TRQuant] 使用完整外部模板');
                    
                    // 替换变量
                    strategyContent = strategyContent
                        .replace(/\{project_name\}/g, finalName)
                        .replace(/\{create_time\}/g, new Date().toLocaleString('zh-CN'))
                        .replace(/\{start_date\}/g, formatDate(startDate))
                        .replace(/\{end_date\}/g, formatDate(endDate));
                    
                    // 替换市场状态
                    strategyContent = strategyContent.replace(
                        /MARKET_REGIME = 'neutral'/,
                        `MARKET_REGIME = '${marketRegime}'`
                    );
                    
                    // 替换投资主线数据
                    if (hotMainlines.length > 0) {
                        const mainlinesStr = hotMainlines.map(m => 
                            `    ('${m.name}', ${JSON.stringify(m.industries)}),`
                        ).join('\n');
                        strategyContent = strategyContent.replace(
                            /HOT_MAINLINES = \[\n    \('人工智能'.*?\n    \('半导体'.*?\n\]/s,
                            `HOT_MAINLINES = [\n${mainlinesStr}\n]`
                        );
                    }
                    
                    // ⚠️ 关键：将模板中的 {{ 和 }} 转换为 { 和 }
                    // 模板文件使用 {{ }} 是为了避免被 Python .format() 方法替换
                    strategyContent = strategyContent
                        .replace(/\{\{/g, '{')
                        .replace(/\}\}/g, '}');
                } else {
                    // 回退到简化模板
                    console.log('[TRQuant] 模板文件不存在，使用简化模板');
                    strategyContent = `# -*- coding: utf-8 -*-
"""
${finalName} - 智能多因子量化策略
=====================================

创建时间: ${new Date().toLocaleString('zh-CN')}
回测区间: ${formatDate(startDate)} 至 ${formatDate(endDate)}
基准指数: 000300.XSHG (沪深300)

市场状态: ${marketRegime}
投资主线: ${hotMainlines.map(m => m.name).join(', ') || '沪深300成分股'}
"""

import numpy as np
import pandas as pd

MARKET_REGIME = '${marketRegime}'
HOT_MAINLINES = ${JSON.stringify(hotMainlines.map(m => [m.name, m.industries]))}

def initialize(context):
    set_benchmark('000300.XSHG')
    g.stock_num = 10
    g.market_regime = MARKET_REGIME
    log.info('策略初始化: ${finalName}')
    log.info(f'市场状态: {g.market_regime}')

def handle_data(context, data):
    pass
`;
                }
                
                fs.writeFileSync(mainPyPath, strategyContent, 'utf-8');
                
                // 打开文件
                const doc = await vscode.workspace.openTextDocument(mainPyPath);
                await vscode.window.showTextDocument(doc);
                
                // 刷新
                vscode.commands.executeCommand('workbench.files.action.refreshFilesExplorer');
                
                vscode.window.showInformationMessage(
                    `✅ 项目 "${finalName}" 创建成功！`,
                    '运行回测'
                ).then(selection => {
                    if (selection === '运行回测') {
                        vscode.commands.executeCommand('trquant.runBacktest');
                    }
                });
                
            } catch (err) {
                console.error('[TRQuant] createProject 错误:', err);
                vscode.window.showErrorMessage(`创建项目失败: ${err}`);
            }
        });
        context.subscriptions.push(createProjectDisposable);
        console.log('[TRQuant] ✅ createProject 命令注册成功');
        // ========== END 创建项目命令 ==========

        // 初始化配置
        const configManager = ConfigManager.getInstance();
        context.subscriptions.push({ dispose: () => configManager.dispose() });

        // 初始化客户端
        client = new TRQuantClient(context);
        context.subscriptions.push({ dispose: () => client.dispose() });

        // 创建状态栏
        statusBarItem = createStatusBar();
        context.subscriptions.push(statusBarItem);

        // 注册命令（包含工作流面板命令）
        registerCommands(context);
        console.log('[TRQuant] ✅ 所有命令注册完成');

        // 注册项目资源管理器
        registerProjectExplorer(context);

        // 注册配置管理命令
        registerConfigCommands(context);

        // 注册回测管理器
        registerBacktestManager(context, client);

        // 注册回测报告命令
        registerBacktestReportCommands(context);

        // 注册策略代码补全提供者
        registerStrategyCompletionProvider(context);

        // 注册策略代码诊断提供者
        registerStrategyDiagnosticProvider(context);

        // 注册主控制台
        registerMainDashboard(context, client);

        // 注册侧边栏快捷操作（显示viewsWelcome内容）
        registerQuickActionsView(context);

        // registerCreateProjectCommand 已在上面直接注册，跳过
        // registerCreateProjectCommand(context);

        // 注册引导命令：点击侧边栏 -> 打开命令面板并搜索创建命令
        context.subscriptions.push(
            vscode.commands.registerCommand('trquant.guide.createProject', async () => {
                // 呼出 Quick Open，输入命令前缀
                // 注意：这里输入的字符串必须匹配 package.json 中定义的 title
                await vscode.commands.executeCommand('workbench.action.quickOpen', '>TRQuant: 新建量化项目');
            })
        );

        // 注册策略优化助手
        registerStrategyOptimizer(context, client);

        // 注意：工作流面板已在上面立即注册，这里不再重复注册

        // 注册步骤面板
        registerDataSourcePanel(context, client);      // 步骤1: 信息获取
        registerMarketTrendPanel(context, client);     // 步骤2: 市场趋势
        registerMainlinePanel(context, client);        // 步骤3: 投资主线
        registerCandidatePoolPanel(context, client);   // 步骤4: 候选池
        registerFactorPanel(context, client);          // 步骤5: 因子构建
        registerStrategyDevPanel(context, client);     // 步骤6: 策略开发
        registerTradingPanel(context, client);         // 步骤8: 实盘交易
        
        // 注册系统管理面板
        registerFileManagerPanel(context, client);     // 文件管理
        registerKnowledgeBasePanel(context, client);   // 知识库
        registerSystemSettingsPanel(context, client);  // 系统设置
        
        // 注册策略优化器面板
        registerStrategyOptimizerPanel(context);
        
        // 注册A股实操手册命令 - 参考桌面软件实现，直接启动Astro服务器
        context.subscriptions.push(
            vscode.commands.registerCommand('trquant.openAShareManual', async () => {
                try {
                    logger.info('=== 开始启动A股实操手册 ===', MODULE);
                    
                    // 参考桌面软件：Path(__file__).parent.parent / "AShare-manual"
                    // 扩展中：context.extensionPath 对应 extension/ 目录
                    let manualPath = path.join(context.extensionPath, 'AShare-manual');
                    
                    // 如果扩展路径下不存在，尝试工作区路径（开发时使用）
                    if (!fs.existsSync(manualPath)) {
                        logger.info(`扩展路径不存在，尝试工作区路径: ${manualPath}`, MODULE);
                        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
                        if (workspaceFolder) {
                            const workspaceManualPath = path.join(workspaceFolder.uri.fsPath, 'extension', 'AShare-manual');
                            logger.info(`检查工作区路径: ${workspaceManualPath}`, MODULE);
                            if (fs.existsSync(workspaceManualPath)) {
                                manualPath = workspaceManualPath;
                                logger.info(`✓ 使用工作区路径: ${manualPath}`, MODULE);
                            } else {
                                logger.warn(`工作区路径也不存在: ${workspaceManualPath}`, MODULE);
                            }
                        }
                    } else {
                        logger.info(`✓ 使用扩展路径: ${manualPath}`, MODULE);
                    }
                    
                    // 检查目录是否存在
                    if (!fs.existsSync(manualPath)) {
                        const errorMsg = `手册目录不存在: ${manualPath}\n请确保A股手册已正确安装。`;
                        logger.error(errorMsg, MODULE);
                        vscode.window.showErrorMessage(errorMsg);
                        return;
                    }
                    
                    // 检查package.json是否存在
                    const packageJsonPath = path.join(manualPath, 'package.json');
                    if (!fs.existsSync(packageJsonPath)) {
                        const errorMsg = `手册配置不存在: ${packageJsonPath}`;
                        logger.error(errorMsg, MODULE);
                        vscode.window.showErrorMessage(errorMsg);
                        return;
                    }
                    logger.info(`✓ package.json存在: ${packageJsonPath}`, MODULE);
                    
                    // 检查node_modules是否存在，如果不存在则提示安装
                    const nodeModulesPath = path.join(manualPath, 'node_modules');
                    if (!fs.existsSync(nodeModulesPath)) {
                        logger.info('检测到node_modules不存在，需要安装依赖', MODULE);
                        const install = await vscode.window.showWarningMessage(
                            'A股手册需要安装依赖，是否现在安装？',
                            '安装',
                            '取消'
                        );
                        if (install === '安装') {
                            const installTerminal = vscode.window.createTerminal({
                                name: 'A股手册-安装',
                                cwd: manualPath
                            });
                            installTerminal.show();
                            installTerminal.sendText('npm install');
                            vscode.window.showInformationMessage('正在安装依赖，安装完成后请重新点击"📚 A股实操手册"');
                            return;
                        } else {
                            return;
                        }
                    }
                    logger.info(`✓ node_modules存在`, MODULE);
                    
                    // 参考桌面软件实现：使用 subprocess.Popen 启动服务器
                    logger.info(`启动npm run dev进程: ${manualPath}`, MODULE);
                    try {
                        // 使用子进程启动，类似桌面软件
                        const proc = cp.spawn('npm', ['run', 'dev'], {
                            cwd: manualPath,
                            stdio: 'ignore', // 类似桌面软件的 DEVNULL
                            detached: true,
                            shell: true
                        });
                        
                        proc.unref(); // 允许父进程退出而不等待子进程
                        
                        logger.info('✓ npm run dev进程已启动', MODULE);
                        vscode.window.showInformationMessage('正在启动A股手册服务器，请稍候...');
                        
                        // 参考桌面软件：等待2秒后打开浏览器
                        setTimeout(async () => {
                            logger.info('尝试打开浏览器到 http://localhost:4321', MODULE);
                            try {
                                await vscode.env.openExternal(vscode.Uri.parse('http://localhost:4321'));
                                logger.info('✅ A股手册已在浏览器中打开', MODULE);
                                vscode.window.showInformationMessage('✅ A股高倍股实操手册已启动 - 五册导航首页');
                            } catch (e) {
                                logger.warn(`打开浏览器失败: ${e}`, MODULE);
                                // 尝试其他端口
                                const ports = [4322, 4323, 4324];
                                for (const port of ports) {
                                    try {
                                        await vscode.env.openExternal(vscode.Uri.parse(`http://localhost:${port}`));
                                        logger.info(`✅ 已打开A股手册 (端口${port})`, MODULE);
                                        vscode.window.showInformationMessage(`✅ A股手册已打开 (端口${port})`);
                                        return;
                                    } catch (err) {
                                        // 继续尝试
                                    }
                                }
                                vscode.window.showWarningMessage('无法自动打开浏览器，请手动访问 http://localhost:4321');
                            }
                        }, 2000); // 参考桌面软件：等待2秒
                        
                    } catch (spawnError) {
                        logger.error(`启动进程失败: ${spawnError}`, MODULE);
                        vscode.window.showErrorMessage(`启动失败: ${spawnError instanceof Error ? spawnError.message : String(spawnError)}`);
                    }
                } catch (err) {
                    const errorMsg = err instanceof Error ? err.message : String(err);
                    logger.error(`启动A股手册失败: ${errorMsg}`, MODULE);
                    vscode.window.showErrorMessage(`启动A股手册失败: ${errorMsg}`);
                }
            })
        );
        logger.info('✓ A股实操手册命令已注册', MODULE);

        // 注册MCP（如果启用）
        if (config.get('mcpEnabled')) {
            await registerMCP(context);
        }

        // 初始化完成后更新状态栏
        updateStatusBar();

        const duration = Date.now() - startTime;
        logger.info(`TRQuant Extension 激活完成 (${duration}ms)`, MODULE);

        // 自动打开主控制台 GUI
        logger.info('准备打开主控制台...', MODULE);
        
        // 立即打开主控制台
        try {
            MainDashboard.createOrShow(context.extensionUri, client);
            logger.info('✅ 主控制台已自动打开', MODULE);
        } catch (err) {
            logger.error(`❌ 打开主控制台失败: ${err}`, MODULE);
            // 备用方案：显示通知让用户手动打开
            vscode.window.showErrorMessage(
                `主控制台打开失败: ${err}`,
                '重试'
            ).then(selection => {
                if (selection === '重试') {
                    vscode.commands.executeCommand('trquant.openDashboard');
                }
            });
        }
        
        // 显示启动成功通知
        vscode.window.showInformationMessage('🐉 韬睿量化已启动！');

    } catch (error) {
        ErrorHandler.handle(error, MODULE);
        throw error;
    }
}

/**
 * 创建状态栏项
 */
function createStatusBar(): vscode.StatusBarItem {
    const item = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right,
        100
    );
    
    item.text = '$(graph) TRQuant';
    item.tooltip = 'TRQuant 量化助手 - 点击打开控制面板';
    item.command = 'trquant.showPanel';
    item.show();

    return item;
}

/**
 * 注册所有命令
 */
function registerCommands(context: vscode.ExtensionContext): void {
    const commands: Array<{ id: string; handler: () => Promise<void> }> = [
        {
            id: 'trquant.getMarketStatus',
            handler: () => getMarketStatus(client, context)
        },
        {
            id: 'trquant.getMainlines',
            handler: () => getMainlines(client, context)
        },
        {
            id: 'trquant.recommendFactors',
            handler: () => recommendFactors(client, context)
        },
        {
            id: 'trquant.generateStrategy',
            handler: () => generateStrategy(client, context)
        },
        {
            id: 'trquant.analyzeBacktest',
            handler: () => analyzeBacktest(client, context)
        },
        // createProject 已通过 registerCreateProjectCommand 注册
        {
            id: 'trquant.runBacktest',
            handler: async () => {
                try {
                    console.log('[TRQuant] 运行回测命令触发');
                    showBacktestConfigPanel(context.extensionUri, client, context);
                    console.log('[TRQuant] 回测配置面板已打开');
                } catch (err) {
                    console.error('[TRQuant] 运行回测错误:', err);
                    vscode.window.showErrorMessage(`运行回测失败: ${err}`);
                }
            }
        },
        {
            id: 'trquant.openBacktestConfig',
            handler: async () => {
                showBacktestConfigPanel(context.extensionUri, client, context);
            }
        },
        {
            id: 'trquant.enableMCP',
            handler: async () => {
                await registerMCP(context);
                vscode.window.showInformationMessage('TRQuant MCP Server 已启用');
            }
        },
        {
            id: 'trquant.showPanel',
            handler: async () => {
                MarketPanel.createOrShow(context.extensionUri, client);
            }
        },
        {
            id: 'trquant.showDashboard',
            handler: async () => {
                DashboardPanel.createOrShow(context.extensionUri, client);
            }
        },
        {
            id: 'trquant.openDashboard',
            handler: async () => {
                MainDashboard.createOrShow(context.extensionUri, client);
            }
        },
        {
            id: 'trquant.showWelcome',
            handler: async () => {
                WelcomePanel.createOrShow(context.extensionUri, client);
            }
        },
        {
            id: 'trquant.showLogs',
            handler: async () => {
                logger.show();
            }
        },
        {
            id: 'trquant.refreshStatus',
            handler: async () => {
                await updateStatusBar();
                vscode.window.showInformationMessage('状态已刷新');
            }
        },
        {
            id: 'trquant.openWorkflowPanel',
            handler: async () => {
                // 打开工作流面板 = 启动桌面系统（与桌面系统保持一致）
                console.log('[TRQuant] 打开工作流面板 -> 启动桌面系统');
                logger.info('打开工作流面板（启动桌面系统）', MODULE);
                await launchDesktopSystem(context);
            }
        },
        {
            id: 'trquant.launchDesktopSystem',
            handler: async () => {
                console.log('[TRQuant] 启动桌面系统');
                logger.info('启动桌面系统', MODULE);
                await launchDesktopSystem(context);
            }
        },
        {
            id: 'trquant.openWorkflowPanelWebview',
            handler: async () => {
                // 在 VS Code 中打开简化版工作流面板（WebView）
                console.log('[TRQuant] 打开WebView工作流面板');
                logger.info('打开WebView工作流面板', MODULE);
                const { WorkflowPanel } = await import('./views/workflowPanel');
                WorkflowPanel.createOrShow(context.extensionUri, client);
            }
        }
    ];

    for (const { id, handler } of commands) {
        const disposable = vscode.commands.registerCommand(id, async () => {
            logger.debug(`执行命令: ${id}`, MODULE);
            await ErrorHandler.wrap(handler, id);
        });
        context.subscriptions.push(disposable);
    }

    logger.info(`已注册 ${commands.length} 个命令`, MODULE);
}

/**
 * 启动桌面系统（PyQt6 GUI）
 * 与桌面系统保持完全一致的工作流体验
 */
async function launchDesktopSystem(context: vscode.ExtensionContext): Promise<void> {
    const pythonPath = config.getPythonPath(context.extensionPath);
    
    // TRQuant 根目录
    const trquantRoot = path.dirname(context.extensionPath);
    const mainScript = path.join(trquantRoot, 'start_dashboard.py');
    
    // 检查启动脚本是否存在
    if (!fs.existsSync(mainScript)) {
        vscode.window.showErrorMessage(`桌面系统启动脚本不存在: ${mainScript}`);
        return;
    }
    
    logger.info(`启动桌面系统: ${mainScript}`, MODULE);
    
    try {
        // 使用子进程启动桌面系统
        const proc = cp.spawn(pythonPath, [mainScript], {
            cwd: trquantRoot,
            detached: true,
            stdio: 'ignore'
        });
        
        proc.unref();
        
        vscode.window.showInformationMessage('🖥️ 桌面系统已启动！');
        logger.info('桌面系统启动成功', MODULE);
    } catch (error) {
        const msg = error instanceof Error ? error.message : String(error);
        logger.error(`启动桌面系统失败: ${msg}`, MODULE);
        vscode.window.showErrorMessage(`启动桌面系统失败: ${msg}`);
    }
}

/**
 * 注册MCP Server
 */
async function registerMCP(context: vscode.ExtensionContext): Promise<void> {
    try {
        await MCPRegistrar.registerServer(context);
        logger.info('MCP Server 已注册', MODULE);
    } catch (error) {
        logger.warn(`MCP注册失败: ${error instanceof Error ? error.message : String(error)}`, MODULE);
    }
}

/**
 * 更新状态栏显示
 */
async function updateStatusBar(): Promise<void> {
    try {
        const result = await client.getMarketStatus();
        
        if (result.ok && result.data) {
            const regime = result.data.regime;
            const regimeIcons: Record<string, string> = {
                'risk_on': '📈',
                'risk_off': '📉',
                'neutral': '➡️'
            };
            
            const icon = regimeIcons[regime] || '📊';
            statusBarItem.text = `$(graph) ${icon} TRQuant`;
            statusBarItem.tooltip = `TRQuant | 市场: ${regime.toUpperCase()}\n点击打开控制面板`;
        }
    } catch (error) {
        // 静默处理错误，保持默认状态
        logger.debug('更新状态栏失败', MODULE, { error });
    }
}

/**
 * 显示欢迎消息
 */
function showWelcomeMessage(context: vscode.ExtensionContext): void {
    const WELCOME_SHOWN_KEY = 'trquant.welcomeShown';
    
    if (!context.globalState.get(WELCOME_SHOWN_KEY)) {
        vscode.window.showInformationMessage(
            '欢迎使用 TRQuant 量化助手！按 Ctrl+Shift+P 输入 "TRQuant" 查看可用命令。',
            '查看命令',
            '不再显示'
        ).then(selection => {
            if (selection === '查看命令') {
                vscode.commands.executeCommand('workbench.action.quickOpen', '>TRQuant');
            } else if (selection === '不再显示') {
                context.globalState.update(WELCOME_SHOWN_KEY, true);
            }
        });
    }
}

/**
 * 扩展停用
 */
export function deactivate(): void {
    logger.info('TRQuant Extension 正在停用...', MODULE);
    
    if (client) {
        client.dispose();
    }
    
    logger.dispose();
}
