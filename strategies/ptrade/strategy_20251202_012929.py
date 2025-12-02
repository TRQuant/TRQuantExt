# -*- coding: utf-8 -*-
"""
韬睿量化策略_20251202
=============
基于突破在即环境自动生成

生成时间: 2025-12-02 01:29:29
生成工具: 韬睿量化策略生成器
"""

# ======== 初始化 ========
def initialize(context):
    """策略初始化"""
    # 设置基准
    set_benchmark("000300.XSHG")
    
    # 设置佣金和滑点
    set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0013))
    set_slippage(FixedSlippage(0.001))
    
    # 策略参数
    context.position_limit = 20
    context.single_stock_limit = 0.1
    context.stop_loss_threshold = 0.06
    context.take_profit_threshold = 0.18
    
    # 设置调仓频率
    run_weekly(rebalance, weekday=0, time='14:30')  # 每两周调仓需手动控制

# ======== 因子计算 ========
def calculate_factor_score(stock, context):
    """计算因子综合得分"""
    score = 0.0

    # 1月动量 (权重: 0.25)
    try:
        momentum_1m_value = get_momentum_1m(stock)
        score += 0.25 * 1 * normalize(momentum_1m_value)
    except:
        pass

    # 市盈率倒数 (权重: 0.25)
    try:
        ep_value = get_ep(stock)
        score += 0.25 * 1 * normalize(ep_value)
    except:
        pass

    # 净利润增长率 (权重: 0.25)
    try:
        profit_growth_value = get_profit_growth(stock)
        score += 0.25 * 1 * normalize(profit_growth_value)
    except:
        pass

    # 净资产收益率 (权重: 0.25)
    try:
        roe_value = get_roe(stock)
        score += 0.25 * 1 * normalize(roe_value)
    except:
        pass

    return score

def normalize(value):
    """标准化到0-1"""
    # 简单的Min-Max标准化，实际应使用历史数据
    return max(0, min(1, value))

# ======== 选股逻辑 ========
def select_stocks(context):
    """选股逻辑"""
    # 获取股票池
    stocks = get_index_stocks("000300.XSHG")
    
    # 计算综合因子得分
    scores = {}
    for stock in stocks:
        try:
            score = calculate_factor_score(stock, context)
            scores[stock] = score
        except:
            continue
    
    # 按得分排序
    sorted_stocks = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    # 取前N只
    selected = [s[0] for s in sorted_stocks[:context.position_limit]]
    
    return selected

# ======== 调仓逻辑 ========
def rebalance(context):
    """调仓函数"""
    # 获取目标股票
    target_stocks = select_stocks(context)
    
    # 计算每只股票的目标仓位
    weight = 1.0 / len(target_stocks) if target_stocks else 0
    weight = min(weight, context.single_stock_limit)
    
    # 获取当前持仓
    current_holdings = set(context.portfolio.positions.keys())
    target_set = set(target_stocks)
    
    # 卖出不在目标中的股票
    for stock in current_holdings - target_set:
        order_target_value(stock, 0)
    
    # 买入目标股票
    for stock in target_stocks:
        order_target_percent(stock, weight)
    
    log.info(f"调仓完成: 持有{len(target_stocks)}只股票")

# ======== 风险控制 ========
def check_stop_loss_take_profit(context):
    """检查止损止盈"""
    for stock, position in context.portfolio.positions.items():
        if position.amount <= 0:
            continue
        
        # 计算收益率
        cost = position.avg_cost
        current = position.price
        pnl_rate = (current - cost) / cost if cost > 0 else 0
        
        # 止损检查
        if pnl_rate < -0.06:
            order_target_value(stock, 0)
            log.info(f"止损卖出 {stock}: 收益率 {pnl_rate:.2%}")
            continue
        
        # 止盈检查
        if pnl_rate > 0.18:
            order_target_value(stock, 0)
            log.info(f"止盈卖出 {stock}: 收益率 {pnl_rate:.2%}")


# ======== 每日运行 ========
def handle_data(context, data):
    """每日运行"""
    # 检查止损止盈
    check_stop_loss_take_profit(context)
