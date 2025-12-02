/**
 * 错误处理模块
 * 
 * 定义自定义错误类型和错误处理工具
 * 遵循异常处理最佳实践
 */

import * as vscode from 'vscode';
import { logger } from './logger';

/**
 * 错误代码枚举
 */
export enum ErrorCode {
    // 通用错误 (1000-1999)
    UNKNOWN = 1000,
    TIMEOUT = 1001,
    CANCELLED = 1002,
    
    // Python后端错误 (2000-2999)
    PYTHON_NOT_FOUND = 2000,
    PYTHON_EXECUTION_ERROR = 2001,
    BRIDGE_CONNECTION_ERROR = 2002,
    BRIDGE_RESPONSE_PARSE_ERROR = 2003,
    
    // 数据错误 (3000-3999)
    DATA_NOT_AVAILABLE = 3000,
    DATA_PARSE_ERROR = 3001,
    DATA_VALIDATION_ERROR = 3002,
    
    // 配置错误 (4000-4999)
    CONFIG_INVALID = 4000,
    CONFIG_MISSING = 4001,
    
    // MCP错误 (5000-5999)
    MCP_CONNECTION_ERROR = 5000,
    MCP_TOOL_NOT_FOUND = 5001,
    MCP_EXECUTION_ERROR = 5002
}

/**
 * TRQuant基础错误类
 */
export class TRQuantError extends Error {
    public readonly code: ErrorCode;
    public readonly details?: any;
    public readonly timestamp: Date;

    constructor(code: ErrorCode, message: string, details?: any) {
        super(message);
        this.name = 'TRQuantError';
        this.code = code;
        this.details = details;
        this.timestamp = new Date();
        
        // 确保原型链正确
        Object.setPrototypeOf(this, TRQuantError.prototype);
    }

    /**
     * 转换为用户友好的消息
     */
    toUserMessage(): string {
        const codeMessages: Record<ErrorCode, string> = {
            [ErrorCode.UNKNOWN]: '发生未知错误',
            [ErrorCode.TIMEOUT]: '操作超时，请重试',
            [ErrorCode.CANCELLED]: '操作已取消',
            [ErrorCode.PYTHON_NOT_FOUND]: 'Python解释器未找到，请检查配置',
            [ErrorCode.PYTHON_EXECUTION_ERROR]: 'Python执行错误',
            [ErrorCode.BRIDGE_CONNECTION_ERROR]: '无法连接到后端服务',
            [ErrorCode.BRIDGE_RESPONSE_PARSE_ERROR]: '后端响应解析失败',
            [ErrorCode.DATA_NOT_AVAILABLE]: '数据不可用',
            [ErrorCode.DATA_PARSE_ERROR]: '数据解析失败',
            [ErrorCode.DATA_VALIDATION_ERROR]: '数据验证失败',
            [ErrorCode.CONFIG_INVALID]: '配置无效',
            [ErrorCode.CONFIG_MISSING]: '缺少必要配置',
            [ErrorCode.MCP_CONNECTION_ERROR]: 'MCP服务连接失败',
            [ErrorCode.MCP_TOOL_NOT_FOUND]: 'MCP工具未找到',
            [ErrorCode.MCP_EXECUTION_ERROR]: 'MCP工具执行失败'
        };

        return codeMessages[this.code] || this.message;
    }

    /**
     * 转换为日志格式
     */
    toLogString(): string {
        return `[${ErrorCode[this.code]}] ${this.message}${
            this.details ? ` | Details: ${JSON.stringify(this.details)}` : ''
        }`;
    }
}

/**
 * Python相关错误
 */
export class PythonError extends TRQuantError {
    constructor(message: string, details?: any) {
        super(ErrorCode.PYTHON_EXECUTION_ERROR, message, details);
        this.name = 'PythonError';
    }
}

/**
 * 数据相关错误
 */
export class DataError extends TRQuantError {
    constructor(code: ErrorCode, message: string, details?: any) {
        super(code, message, details);
        this.name = 'DataError';
    }
}

/**
 * 配置相关错误
 */
export class ConfigError extends TRQuantError {
    constructor(message: string, details?: any) {
        super(ErrorCode.CONFIG_INVALID, message, details);
        this.name = 'ConfigError';
    }
}

/**
 * 错误处理工具类
 */
export class ErrorHandler {
    /**
     * 处理错误并显示给用户
     */
    static handle(error: unknown, context?: string): void {
        const module = context || 'ErrorHandler';
        
        if (error instanceof TRQuantError) {
            logger.error(error.toLogString(), module);
            vscode.window.showErrorMessage(error.toUserMessage());
        } else if (error instanceof Error) {
            logger.error(error.message, module, { stack: error.stack });
            vscode.window.showErrorMessage(`TRQuant: ${error.message}`);
        } else {
            logger.error(String(error), module);
            vscode.window.showErrorMessage(`TRQuant: 发生未知错误`);
        }
    }

    /**
     * 包装异步函数，自动处理错误
     */
    static async wrap<T>(
        fn: () => Promise<T>,
        context?: string
    ): Promise<T | undefined> {
        try {
            return await fn();
        } catch (error) {
            ErrorHandler.handle(error, context);
            return undefined;
        }
    }

    /**
     * 创建带重试的异步函数
     */
    static async withRetry<T>(
        fn: () => Promise<T>,
        maxRetries: number = 3,
        delay: number = 1000,
        context?: string
    ): Promise<T> {
        let lastError: unknown;
        
        for (let i = 0; i < maxRetries; i++) {
            try {
                return await fn();
            } catch (error) {
                lastError = error;
                logger.warn(
                    `操作失败，第${i + 1}次重试...`,
                    context,
                    { error: error instanceof Error ? error.message : String(error) }
                );
                
                if (i < maxRetries - 1) {
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
            }
        }
        
        throw lastError;
    }

    /**
     * 验证必需参数
     */
    static validateRequired(params: Record<string, any>, required: string[]): void {
        const missing = required.filter(key => params[key] === undefined || params[key] === null);
        
        if (missing.length > 0) {
            throw new TRQuantError(
                ErrorCode.DATA_VALIDATION_ERROR,
                `缺少必需参数: ${missing.join(', ')}`,
                { missing, provided: Object.keys(params) }
            );
        }
    }
}

