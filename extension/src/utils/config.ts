/**
 * 配置管理模块
 * 
 * 集中管理所有配置项，支持默认值和类型安全
 * 遵循开闭原则 - 对扩展开放，对修改关闭
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as os from 'os';

/**
 * 配置接口定义
 */
export interface TRQuantConfig {
    // Python配置
    pythonPath: string;
    
    // 服务器配置
    serverHost: string;
    serverPort: number;
    timeout: number;
    
    // MCP配置
    mcpEnabled: boolean;
    mcpPort: number;
    
    // 功能配置
    autoRefresh: boolean;
    refreshInterval: number;
    
    // 策略配置
    defaultPlatform: 'ptrade' | 'qmt';
    defaultStyle: string;
    
    // 风控默认参数
    defaultRiskParams: {
        maxPosition: number;
        stopLoss: number;
        takeProfit: number;
    };
}

/**
 * 默认配置
 */
const DEFAULT_CONFIG: TRQuantConfig = {
    pythonPath: os.platform() === 'win32' ? 'python' : 'python3',
    serverHost: '127.0.0.1',
    serverPort: 5000,
    timeout: 60000,
    mcpEnabled: true,
    mcpPort: 5001,
    autoRefresh: false,
    refreshInterval: 300000, // 5分钟
    defaultPlatform: 'ptrade',
    defaultStyle: 'multi_factor',
    defaultRiskParams: {
        maxPosition: 0.1,
        stopLoss: 0.08,
        takeProfit: 0.2
    }
};

/**
 * 配置管理器
 */
export class ConfigManager {
    private static instance: ConfigManager;
    private config: TRQuantConfig;
    private disposables: vscode.Disposable[] = [];

    private constructor() {
        this.config = this.loadConfig();
        
        // 监听配置变化
        this.disposables.push(
            vscode.workspace.onDidChangeConfiguration(e => {
                if (e.affectsConfiguration('trquant')) {
                    this.config = this.loadConfig();
                }
            })
        );
    }

    /**
     * 获取单例
     */
    static getInstance(): ConfigManager {
        if (!ConfigManager.instance) {
            ConfigManager.instance = new ConfigManager();
        }
        return ConfigManager.instance;
    }

    /**
     * 加载配置
     */
    private loadConfig(): TRQuantConfig {
        const wsConfig = vscode.workspace.getConfiguration('trquant');
        
        return {
            pythonPath: wsConfig.get<string>('pythonPath') || DEFAULT_CONFIG.pythonPath,
            serverHost: wsConfig.get<string>('serverHost') || DEFAULT_CONFIG.serverHost,
            serverPort: wsConfig.get<number>('serverPort') || DEFAULT_CONFIG.serverPort,
            timeout: wsConfig.get<number>('timeout') || DEFAULT_CONFIG.timeout,
            mcpEnabled: wsConfig.get<boolean>('mcpEnabled') ?? DEFAULT_CONFIG.mcpEnabled,
            mcpPort: wsConfig.get<number>('mcpPort') || DEFAULT_CONFIG.mcpPort,
            autoRefresh: wsConfig.get<boolean>('autoRefresh') ?? DEFAULT_CONFIG.autoRefresh,
            refreshInterval: wsConfig.get<number>('refreshInterval') || DEFAULT_CONFIG.refreshInterval,
            defaultPlatform: wsConfig.get<'ptrade' | 'qmt'>('defaultPlatform') || DEFAULT_CONFIG.defaultPlatform,
            defaultStyle: wsConfig.get<string>('defaultStyle') || DEFAULT_CONFIG.defaultStyle,
            defaultRiskParams: {
                maxPosition: wsConfig.get<number>('defaultMaxPosition') || DEFAULT_CONFIG.defaultRiskParams.maxPosition,
                stopLoss: wsConfig.get<number>('defaultStopLoss') || DEFAULT_CONFIG.defaultRiskParams.stopLoss,
                takeProfit: wsConfig.get<number>('defaultTakeProfit') || DEFAULT_CONFIG.defaultRiskParams.takeProfit
            }
        };
    }

    /**
     * 获取完整配置
     */
    getConfig(): Readonly<TRQuantConfig> {
        return { ...this.config };
    }

    /**
     * 获取单个配置项
     */
    get<K extends keyof TRQuantConfig>(key: K): TRQuantConfig[K] {
        return this.config[key];
    }

    /**
     * 更新配置项
     */
    async set<K extends keyof TRQuantConfig>(
        key: K, 
        value: TRQuantConfig[K],
        target: vscode.ConfigurationTarget = vscode.ConfigurationTarget.Global
    ): Promise<void> {
        const wsConfig = vscode.workspace.getConfiguration('trquant');
        await wsConfig.update(key, value, target);
    }

    /**
     * 获取Python解释器完整路径
     */
    getPythonPath(extensionPath: string): string {
        const configPath = this.config.pythonPath;
        
        // 如果是绝对路径，直接返回
        if (path.isAbsolute(configPath)) {
            return configPath;
        }
        
        // 检查是否在虚拟环境中
        const venvPath = path.join(extensionPath, '..', 'venv');
        const venvPython = os.platform() === 'win32'
            ? path.join(venvPath, 'Scripts', 'python.exe')
            : path.join(venvPath, 'bin', 'python');
        
        // 优先使用虚拟环境
        return venvPython;
    }

    /**
     * 释放资源
     */
    dispose(): void {
        this.disposables.forEach(d => d.dispose());
    }
}

// 导出便捷方法
export const config = ConfigManager.getInstance();

