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

// 核心服务
import { TRQuantClient } from './services/trquantClient';
import { MCPRegistrar } from './services/mcpRegistrar';

// 命令
import { getMarketStatus } from './commands/getMarketStatus';
import { getMainlines } from './commands/getMainlines';
import { recommendFactors } from './commands/recommendFactors';
import { generateStrategy } from './commands/generateStrategy';
import { analyzeBacktest } from './commands/analyzeBacktest';

// 视图
import { MarketPanel } from './views/marketPanel';

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
    logger.info('TRQuant Extension 正在激活...', MODULE);
    
    const startTime = Date.now();

    try {
        // 初始化配置
        const configManager = ConfigManager.getInstance();
        context.subscriptions.push({ dispose: () => configManager.dispose() });

        // 初始化客户端
        client = new TRQuantClient(context);
        context.subscriptions.push({ dispose: () => client.dispose() });

        // 创建状态栏
        statusBarItem = createStatusBar();
        context.subscriptions.push(statusBarItem);

        // 注册命令
        registerCommands(context);

        // 注册MCP（如果启用）
        if (config.get('mcpEnabled')) {
            await registerMCP(context);
        }

        // 初始化完成后更新状态栏
        updateStatusBar();

        const duration = Date.now() - startTime;
        logger.info(`TRQuant Extension 激活完成 (${duration}ms)`, MODULE);

        // 显示欢迎消息（仅首次）
        showWelcomeMessage(context);

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
