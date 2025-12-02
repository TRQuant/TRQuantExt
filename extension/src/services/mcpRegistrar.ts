/**
 * MCP Server 注册服务
 * ====================
 * 
 * 将TRQuant注册为Cursor的MCP Server
 * 使得AI可以直接调用量化功能
 * 
 * 遵循：
 * - 单一职责原则
 * - 依赖注入
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import { logger } from '../utils/logger';
import { config } from '../utils/config';

const MODULE = 'MCPRegistrar';

/**
 * MCP配置接口
 */
interface MCPConfig {
    mcpServers: {
        [key: string]: {
            command: string;
            args: string[];
            env?: Record<string, string>;
        };
    };
}

/**
 * MCP注册器
 */
export class MCPRegistrar {
    
    /**
     * 注册MCP Server到Cursor
     */
    static async registerServer(context: vscode.ExtensionContext): Promise<void> {
        logger.info('开始注册MCP Server...', MODULE);

        try {
            // 获取MCP配置文件路径
            const configPath = this.getMCPConfigPath();
            logger.info(`MCP配置路径: ${configPath}`, MODULE);

            // 读取现有配置或创建新配置
            let mcpConfig = this.loadMCPConfig(configPath);

            // 添加TRQuant Server
            const pythonPath = config.getPythonPath(context.extensionPath);
            const mcpServerPath = path.join(context.extensionPath, 'python', 'mcp_server.py');

            mcpConfig.mcpServers['trquant'] = {
                command: pythonPath,
                args: [mcpServerPath],
                env: {
                    PYTHONIOENCODING: 'utf-8',
                    TRQUANT_ROOT: path.dirname(context.extensionPath)
                }
            };

            // 保存配置
            this.saveMCPConfig(configPath, mcpConfig);

            logger.info('MCP Server 注册成功', MODULE);

            // 提示用户
            vscode.window.showInformationMessage(
                'TRQuant MCP Server 已注册。重启Cursor后生效。',
                '查看配置',
                '了解更多'
            ).then(selection => {
                if (selection === '查看配置') {
                    this.openMCPConfig(configPath);
                } else if (selection === '了解更多') {
                    vscode.env.openExternal(vscode.Uri.parse('https://docs.cursor.com/context/model-context-protocol'));
                }
            });

        } catch (error) {
            logger.error(`MCP注册失败: ${error instanceof Error ? error.message : String(error)}`, MODULE);
            throw error;
        }
    }

    /**
     * 获取MCP配置文件路径
     */
    private static getMCPConfigPath(): string {
        const homeDir = os.homedir();
        
        // Cursor的MCP配置位置
        const configLocations = [
            // Linux
            path.join(homeDir, '.cursor', 'mcp.json'),
            // macOS
            path.join(homeDir, 'Library', 'Application Support', 'Cursor', 'mcp.json'),
            // Windows
            path.join(homeDir, 'AppData', 'Roaming', 'Cursor', 'mcp.json')
        ];

        // 检查已存在的配置
        for (const configPath of configLocations) {
            if (fs.existsSync(configPath)) {
                return configPath;
            }
        }

        // 返回默认路径
        switch (os.platform()) {
            case 'darwin':
                return configLocations[1];
            case 'win32':
                return configLocations[2];
            default:
                return configLocations[0];
        }
    }

    /**
     * 加载MCP配置
     */
    private static loadMCPConfig(configPath: string): MCPConfig {
        try {
            if (fs.existsSync(configPath)) {
                const content = fs.readFileSync(configPath, 'utf-8');
                return JSON.parse(content);
            }
        } catch (error) {
            logger.warn(`读取MCP配置失败: ${error}`, MODULE);
        }

        // 返回默认配置
        return { mcpServers: {} };
    }

    /**
     * 保存MCP配置
     */
    private static saveMCPConfig(configPath: string, config: MCPConfig): void {
        // 确保目录存在
        const dir = path.dirname(configPath);
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }

        // 写入配置
        const content = JSON.stringify(config, null, 2);
        fs.writeFileSync(configPath, content, 'utf-8');
        
        logger.info(`MCP配置已保存: ${configPath}`, MODULE);
    }

    /**
     * 打开MCP配置文件
     */
    private static async openMCPConfig(configPath: string): Promise<void> {
        const doc = await vscode.workspace.openTextDocument(configPath);
        await vscode.window.showTextDocument(doc);
    }

    /**
     * 检查MCP Server是否已注册
     */
    static isRegistered(): boolean {
        try {
            const configPath = this.getMCPConfigPath();
            const config = this.loadMCPConfig(configPath);
            return 'trquant' in config.mcpServers;
        } catch {
            return false;
        }
    }

    /**
     * 移除MCP Server注册
     */
    static async unregisterServer(): Promise<void> {
        logger.info('移除MCP Server注册...', MODULE);

        try {
            const configPath = this.getMCPConfigPath();
            let mcpConfig = this.loadMCPConfig(configPath);

            if ('trquant' in mcpConfig.mcpServers) {
                delete mcpConfig.mcpServers['trquant'];
                this.saveMCPConfig(configPath, mcpConfig);
                logger.info('MCP Server 已移除', MODULE);
            }

        } catch (error) {
            logger.error(`移除MCP注册失败: ${error instanceof Error ? error.message : String(error)}`, MODULE);
        }
    }
}
