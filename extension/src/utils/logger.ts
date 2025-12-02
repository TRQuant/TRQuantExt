/**
 * 日志工具模块
 * 
 * 提供统一的日志记录接口，支持多级别日志和输出渠道
 * 遵循单一职责原则
 */

import * as vscode from 'vscode';

export enum LogLevel {
    DEBUG = 0,
    INFO = 1,
    WARN = 2,
    ERROR = 3
}

export interface LogEntry {
    level: LogLevel;
    message: string;
    timestamp: Date;
    module?: string;
    data?: any;
}

/**
 * TRQuant 日志管理器
 */
export class Logger {
    private static instance: Logger;
    private outputChannel: vscode.OutputChannel;
    private minLevel: LogLevel = LogLevel.INFO;
    private logs: LogEntry[] = [];
    private maxLogs: number = 1000;

    private constructor() {
        this.outputChannel = vscode.window.createOutputChannel('TRQuant');
    }

    /**
     * 获取Logger单例
     */
    static getInstance(): Logger {
        if (!Logger.instance) {
            Logger.instance = new Logger();
        }
        return Logger.instance;
    }

    /**
     * 设置最小日志级别
     */
    setLevel(level: LogLevel): void {
        this.minLevel = level;
    }

    /**
     * 显示输出面板
     */
    show(): void {
        this.outputChannel.show();
    }

    /**
     * 记录DEBUG级别日志
     */
    debug(message: string, module?: string, data?: any): void {
        this.log(LogLevel.DEBUG, message, module, data);
    }

    /**
     * 记录INFO级别日志
     */
    info(message: string, module?: string, data?: any): void {
        this.log(LogLevel.INFO, message, module, data);
    }

    /**
     * 记录WARN级别日志
     */
    warn(message: string, module?: string, data?: any): void {
        this.log(LogLevel.WARN, message, module, data);
    }

    /**
     * 记录ERROR级别日志
     */
    error(message: string, module?: string, data?: any): void {
        this.log(LogLevel.ERROR, message, module, data);
    }

    /**
     * 核心日志方法
     */
    private log(level: LogLevel, message: string, module?: string, data?: any): void {
        if (level < this.minLevel) {
            return;
        }

        const entry: LogEntry = {
            level,
            message,
            timestamp: new Date(),
            module,
            data
        };

        // 存储日志
        this.logs.push(entry);
        if (this.logs.length > this.maxLogs) {
            this.logs.shift();
        }

        // 格式化输出
        const levelStr = LogLevel[level].padEnd(5);
        const timeStr = entry.timestamp.toISOString().substring(11, 23);
        const moduleStr = module ? `[${module}]` : '';
        const dataStr = data ? ` | ${JSON.stringify(data)}` : '';

        const output = `${timeStr} ${levelStr} ${moduleStr} ${message}${dataStr}`;
        
        this.outputChannel.appendLine(output);

        // ERROR级别同时显示通知
        if (level === LogLevel.ERROR) {
            vscode.window.showErrorMessage(`TRQuant: ${message}`);
        }
    }

    /**
     * 获取最近的日志
     */
    getRecentLogs(count: number = 100): LogEntry[] {
        return this.logs.slice(-count);
    }

    /**
     * 清空日志
     */
    clear(): void {
        this.logs = [];
        this.outputChannel.clear();
    }

    /**
     * 释放资源
     */
    dispose(): void {
        this.outputChannel.dispose();
    }
}

// 导出便捷方法
export const logger = Logger.getInstance();

