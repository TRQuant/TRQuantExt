/**
 * TRQuant Client
 * ==============
 * 
 * 与Python后端通信的客户端服务
 * 
 * 职责:
 * - 封装与bridge.py的通信
 * - 提供类型安全的API方法
 * - 处理超时和错误
 * 
 * 遵循:
 * - 单一职责原则
 * - 依赖注入
 * - 接口隔离
 */

import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as path from 'path';
import * as os from 'os';

import { logger } from '../utils/logger';
import { config, ConfigManager } from '../utils/config';
import { 
    TRQuantError, 
    ErrorCode, 
    PythonError, 
    ErrorHandler 
} from '../utils/errors';
import {
    ApiResponse,
    MarketStatus,
    Mainline,
    Factor,
    Strategy,
    BacktestResult,
    RiskAssessment,
    GetMarketStatusParams,
    GetMainlinesParams,
    RecommendFactorsParams,
    GenerateStrategyParams,
    AnalyzeBacktestParams,
    RiskAssessmentParams
} from '../types';

/**
 * Bridge请求接口
 */
interface BridgeRequest {
    action: string;
    params: Record<string, any>;
}

/**
 * TRQuant客户端类
 */
export class TRQuantClient {
    private readonly MODULE = 'TRQuantClient';
    private extensionPath: string;
    private configManager: ConfigManager;

    constructor(context: vscode.ExtensionContext) {
        this.extensionPath = context.extensionPath;
        this.configManager = ConfigManager.getInstance();
        logger.info('TRQuantClient初始化完成', this.MODULE);
    }

    // ==================== 公共API方法 ====================

    /**
     * 获取市场状态
     */
    async getMarketStatus(
        params?: GetMarketStatusParams
    ): Promise<ApiResponse<MarketStatus>> {
        return this.callBridge<MarketStatus>('get_market_status', {
            universe: params?.universe || 'CN_EQ',
            as_of: params?.as_of || this.getTodayDate(),
            lookback_days: params?.lookback_days || 60
        });
    }

    /**
     * 获取投资主线
     */
    async getMainlines(
        params?: GetMainlinesParams
    ): Promise<ApiResponse<Mainline[]>> {
        return this.callBridge<Mainline[]>('get_mainlines', {
            top_n: params?.top_n || 20,
            time_horizon: params?.time_horizon || 'short'
        });
    }

    /**
     * 推荐因子
     */
    async recommendFactors(
        params?: RecommendFactorsParams
    ): Promise<ApiResponse<Factor[]>> {
        return this.callBridge<Factor[]>('recommend_factors', {
            market_regime: params?.market_regime,
            mainlines: params?.mainlines,
            top_n: params?.top_n || 10
        });
    }

    /**
     * 生成策略代码
     */
    async generateStrategy(
        params: GenerateStrategyParams
    ): Promise<ApiResponse<Strategy>> {
        // 验证必需参数
        ErrorHandler.validateRequired(params, ['factors']);
        
        const riskParams = {
            max_position: params.risk_params?.max_position || 
                this.configManager.get('defaultRiskParams').maxPosition,
            stop_loss: params.risk_params?.stop_loss || 
                this.configManager.get('defaultRiskParams').stopLoss,
            take_profit: params.risk_params?.take_profit || 
                this.configManager.get('defaultRiskParams').takeProfit
        };

        return this.callBridge<Strategy>('generate_strategy', {
            factors: params.factors,
            style: params.style || this.configManager.get('defaultStyle'),
            platform: params.platform || this.configManager.get('defaultPlatform'),
            risk_params: riskParams
        });
    }

    /**
     * 分析回测结果
     */
    async analyzeBacktest(
        params: AnalyzeBacktestParams
    ): Promise<ApiResponse<BacktestResult>> {
        return this.callBridge<BacktestResult>('analyze_backtest', params);
    }

    /**
     * 风险评估
     */
    async assessRisk(
        params: RiskAssessmentParams
    ): Promise<ApiResponse<RiskAssessment>> {
        ErrorHandler.validateRequired(params, ['portfolio']);
        return this.callBridge<RiskAssessment>('risk_assessment', params);
    }

    /**
     * 健康检查
     */
    async healthCheck(): Promise<boolean> {
        try {
            const result = await this.callBridge('health_check', {});
            return result.ok;
        } catch {
            return false;
        }
    }

    // ==================== 私有方法 ====================

    /**
     * 调用Python Bridge
     */
    private async callBridge<T>(
        action: string,
        params: Record<string, any>
    ): Promise<ApiResponse<T>> {
        const startTime = Date.now();
        
        logger.debug(`调用Bridge: ${action}`, this.MODULE, { params });

        try {
            const response = await this.executeSubprocess(action, params);
            const duration = Date.now() - startTime;
            
            logger.info(
                `Bridge调用完成: ${action}`,
                this.MODULE,
                { duration: `${duration}ms`, ok: response.ok }
            );

            return response;
        } catch (error) {
            const duration = Date.now() - startTime;
            logger.error(
                `Bridge调用失败: ${action}`,
                this.MODULE,
                { duration: `${duration}ms`, error: error instanceof Error ? error.message : String(error) }
            );
            throw error;
        }
    }

    /**
     * 通过子进程执行Bridge
     */
    private executeSubprocess<T>(
        action: string,
        params: Record<string, any>
    ): Promise<ApiResponse<T>> {
        return new Promise((resolve, reject) => {
            const pythonPath = this.configManager.getPythonPath(this.extensionPath);
            const bridgePath = path.join(this.extensionPath, 'python', 'bridge.py');
            const timeout = this.configManager.get('timeout');

            const request: BridgeRequest = { action, params };
            const requestStr = JSON.stringify(request);

            logger.debug(`执行Python: ${pythonPath}`, this.MODULE, { bridgePath });

            // 设置环境变量
            const env = {
                ...process.env,
                PYTHONIOENCODING: 'utf-8',
                TRQUANT_ROOT: path.dirname(this.extensionPath),
                PYTHONPATH: path.join(this.extensionPath, 'python')
            };

            const proc = cp.spawn(pythonPath, [bridgePath], {
                cwd: path.join(this.extensionPath, 'python'),
                env,
                stdio: ['pipe', 'pipe', 'pipe']
            });

            let stdout = '';
            let stderr = '';

            proc.stdout?.on('data', (data: Buffer) => {
                stdout += data.toString();
            });

            proc.stderr?.on('data', (data: Buffer) => {
                stderr += data.toString();
            });

            // 超时处理
            const timeoutId = setTimeout(() => {
                proc.kill('SIGTERM');
                reject(new TRQuantError(
                    ErrorCode.TIMEOUT,
                    `操作超时 (${timeout}ms)`,
                    { action }
                ));
            }, timeout);

            proc.on('close', (code: number | null) => {
                clearTimeout(timeoutId);

                if (code !== 0) {
                    logger.error(`Python进程退出: ${code}`, this.MODULE, { stderr });
                    reject(new PythonError(
                        stderr || `进程退出码: ${code}`,
                        { action, code, stderr }
                    ));
                    return;
                }

                try {
                    // 尝试解析JSON响应
                    const response = JSON.parse(stdout.trim());
                    resolve(response);
                } catch (parseError) {
                    logger.error('响应解析失败', this.MODULE, { stdout });
                    reject(new TRQuantError(
                        ErrorCode.BRIDGE_RESPONSE_PARSE_ERROR,
                        '无法解析后端响应',
                        { stdout, parseError: parseError instanceof Error ? parseError.message : String(parseError) }
                    ));
                }
            });

            proc.on('error', (error: Error) => {
                clearTimeout(timeoutId);
                logger.error('进程启动失败', this.MODULE, { error: error.message });
                
                if (error.message.includes('ENOENT')) {
                    reject(new TRQuantError(
                        ErrorCode.PYTHON_NOT_FOUND,
                        `Python解释器未找到: ${pythonPath}`,
                        { pythonPath }
                    ));
                } else {
                    reject(new PythonError(error.message, { error }));
                }
            });

            // 发送请求
            proc.stdin?.write(requestStr);
            proc.stdin?.end();
        });
    }

    /**
     * 获取今日日期
     */
    private getTodayDate(): string {
        return new Date().toISOString().split('T')[0];
    }

    /**
     * 释放资源
     */
    dispose(): void {
        logger.info('TRQuantClient已释放', this.MODULE);
    }
}
