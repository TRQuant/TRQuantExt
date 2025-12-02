/**
 * 类型定义模块
 * 
 * 集中定义所有接口和类型，确保类型安全
 */

/**
 * 通用API响应
 */
export interface ApiResponse<T = any> {
    ok: boolean;
    data?: T;
    error?: string;
    timestamp?: string;
}

/**
 * 市场状态
 */
export interface MarketStatus {
    regime: MarketRegime;
    index_trend: Record<string, IndexTrend>;
    style_rotation: StyleScore[];
    summary: string;
    timestamp?: string;
}

export type MarketRegime = 'risk_on' | 'risk_off' | 'neutral';

export interface IndexTrend {
    zscore: number;
    trend: 'up' | 'down' | 'flat';
    change_pct?: number;
}

export interface StyleScore {
    style: string;
    score: number;
}

/**
 * 投资主线
 */
export interface Mainline {
    name: string;
    score: number;
    industries: string[];
    logic: string;
    time_horizon?: 'short' | 'medium' | 'long';
    confidence?: number;
}

/**
 * 量化因子
 */
export interface Factor {
    name: string;
    category: FactorCategory;
    weight: number;
    reason: string;
    ic?: number;
    ir?: number;
}

export type FactorCategory = 
    | '盈利能力'
    | '成长性'
    | '估值'
    | '动量'
    | '流动性'
    | '波动率'
    | '质量'
    | '其他';

/**
 * 策略
 */
export interface Strategy {
    code: string;
    name: string;
    platform: StrategyPlatform;
    style: StrategyStyle;
    description: string;
    factors: string[];
    risk_params: RiskParams;
    created_at?: string;
}

export type StrategyPlatform = 'ptrade' | 'qmt';

export type StrategyStyle = 
    | 'multi_factor'
    | 'momentum_growth'
    | 'value'
    | 'market_neutral';

export interface RiskParams {
    max_position: number;
    stop_loss: number;
    take_profit: number;
    max_drawdown?: number;
    rebalance_freq?: string;
}

/**
 * 回测结果
 */
export interface BacktestResult {
    metrics: BacktestMetrics;
    trades: Trade[];
    equity_curve?: number[];
    diagnosis: string[];
    suggestions: string[];
}

export interface BacktestMetrics {
    total_return: number;
    annual_return: number;
    sharpe_ratio: number;
    max_drawdown: number;
    win_rate: number;
    trade_count: number;
    profit_loss_ratio: number;
    volatility?: number;
    beta?: number;
    alpha?: number;
}

export interface Trade {
    date: string;
    stock: string;
    action: 'buy' | 'sell';
    price: number;
    volume: number;
    pnl?: number;
}

/**
 * 风险评估
 */
export interface RiskAssessment {
    overall_risk: 'low' | 'medium' | 'high';
    metrics: RiskMetrics;
    warnings: string[];
    suggestions: string[];
}

export interface RiskMetrics {
    var_95: number;
    var_99?: number;
    beta: number;
    tracking_error?: number;
    concentration?: number;
}

/**
 * MCP工具定义
 */
export interface MCPTool {
    name: string;
    description: string;
    inputSchema: {
        type: 'object';
        properties: Record<string, any>;
        required?: string[];
    };
}

/**
 * 请求参数类型
 */
export interface GetMarketStatusParams {
    universe?: string;
    as_of?: string;
    lookback_days?: number;
}

export interface GetMainlinesParams {
    top_n?: number;
    time_horizon?: 'short' | 'medium' | 'long';
}

export interface RecommendFactorsParams {
    market_regime?: MarketRegime;
    mainlines?: string[];
    top_n?: number;
}

export interface GenerateStrategyParams {
    factors: string[];
    style?: StrategyStyle;
    platform?: StrategyPlatform;
    risk_params?: Partial<RiskParams>;
}

export interface AnalyzeBacktestParams {
    backtest_file?: string;
    backtest_data?: any;
}

export interface RiskAssessmentParams {
    portfolio: Record<string, number>;
}

