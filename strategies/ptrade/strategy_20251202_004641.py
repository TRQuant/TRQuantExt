# -*- coding: utf-8 -*-
"""
韬睿量化 - 多因子选股策略
========================
自动生成时间: 2025-12-02 00:46:41
市场环境: 牛市
调仓频率: 5个交易日
持仓数量: 20只
主线题材: ["太赫兹", "海峡两岸", "军工信息化"]

策略说明：
本策略基于韬睿量化系统的市场趋势分析、投资主线识别、因子组合推荐
自动生成。策略采用多因子打分方法，综合考虑动量、价值、成长、质量
等因子，选取综合得分最高的股票构建投资组合。
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def init(context):
    """初始化策略"""
    # 设置基准
    set_benchmark('000300.SH')
    
    # 设置交易参数
    set_slippage(PriceRelatedSlippage(0.002))
    set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0013, min_cost=5))
    
    # 策略参数
    context.rebalance_days = 5  # 调仓周期
    context.day_count = 0
    context.max_stocks = 20  # 最大持仓数
    
    # 因子权重（基于市场环境: 牛市）
    context.factor_weights = {
        "momentum": 0.35,
        "growth": 0.3,
        "quality": 0.2,
        "size": 0.15
}
    
    # 主线题材（用于筛选股票池）
    context.mainlines = ["太赫兹", "海峡两岸", "军工信息化"]
    
    # 风控参数
    context.stop_loss = 0.08  # 止损比例
    context.take_profit = 0.20  # 止盈比例
    
    log.info("策略初始化完成")
    log.info(f"调仓周期: {context.rebalance_days}天")
    log.info(f"因子权重: {context.factor_weights}")

def before_trading(context):
    """盘前处理"""
    context.day_count += 1

def handle_bar(context, bar_dict):
    """每日交易逻辑"""
    # 检查是否调仓日
    if context.day_count % context.rebalance_days != 0:
        # 非调仓日只做风控
        check_risk_control(context, bar_dict)
        return
    
    log.info(f"=== 第{context.day_count}天，开始调仓 ===")
    
    # 获取候选股票池
    stocks = get_candidate_pool(context)
    if not stocks:
        log.warn("候选池为空，跳过调仓")
        return
    
    log.info(f"候选池股票数: {len(stocks)}")
    
    # 计算因子得分
    scores = calculate_factor_scores(context, stocks, bar_dict)
    if scores.empty:
        log.warn("因子计算失败，跳过调仓")
        return
    
    # 选取Top N股票
    selected = scores.nlargest(context.max_stocks, 'composite_score')
    target_stocks = selected.index.tolist()
    
    log.info(f"选中股票: {len(target_stocks)}只")
    
    # 调整仓位
    rebalance_portfolio(context, target_stocks, bar_dict)

def get_candidate_pool(context):
    """获取候选股票池"""
    # 获取沪深300成分股作为基础池
    stocks = get_index_stocks('000300.SH')
    
    # 过滤ST和停牌股票
    stocks = filter_stocks(stocks)
    
    return stocks

def filter_stocks(stocks):
    """过滤股票"""
    filtered = []
    for stock in stocks:
        # 过滤ST
        info = get_security_info(stock)
        if info and 'ST' not in info.display_name:
            # 过滤停牌
            if is_trading(stock):
                filtered.append(stock)
    return filtered

def calculate_factor_scores(context, stocks, bar_dict):
    """计算因子综合得分"""
    scores = pd.DataFrame(index=stocks)
    weights = context.factor_weights
    
    try:
        # 动量因子（20日涨幅）
        if 'momentum' in weights:
            momentum = get_price_change(stocks, 20)
            scores['momentum'] = zscore(momentum)
        
        # 价值因子（EP: 净利润/市值）
        if 'value' in weights:
            ep = get_fundamentals(query(
                valuation.pe_ratio
            ).filter(
                valuation.code.in_(stocks)
            ))
            if not ep.empty:
                scores['value'] = zscore(1 / ep['pe_ratio'])
        
        # 成长因子（营收增长率）
        if 'growth' in weights:
            growth = get_fundamentals(query(
                indicator.inc_revenue_year_on_year
            ).filter(
                indicator.code.in_(stocks)
            ))
            if not growth.empty:
                scores['growth'] = zscore(growth['inc_revenue_year_on_year'])
        
        # 质量因子（ROE）
        if 'quality' in weights:
            roe = get_fundamentals(query(
                indicator.roe
            ).filter(
                indicator.code.in_(stocks)
            ))
            if not roe.empty:
                scores['quality'] = zscore(roe['roe'])
        
        # 规模因子（市值，取负表示偏好小盘）
        if 'size' in weights:
            cap = get_fundamentals(query(
                valuation.market_cap
            ).filter(
                valuation.code.in_(stocks)
            ))
            if not cap.empty:
                scores['size'] = zscore(-cap['market_cap'])
        
        # 填充缺失值
        scores = scores.fillna(0)
        
        # 计算综合得分
        scores['composite_score'] = 0
        for factor, weight in weights.items():
            if factor in scores.columns:
                scores['composite_score'] += scores[factor] * weight
        
    except Exception as e:
        log.error(f"因子计算错误: {e}")
        return pd.DataFrame()
    
    return scores

def zscore(series):
    """Z-score标准化"""
    mean = series.mean()
    std = series.std()
    if std == 0:
        return series * 0
    return (series - mean) / std

def get_price_change(stocks, days):
    """获取价格变动"""
    changes = {}
    for stock in stocks:
        try:
            prices = history(stock, ['close'], days + 1, '1d')
            if len(prices) > days:
                changes[stock] = (prices.iloc[-1]['close'] - prices.iloc[0]['close']) / prices.iloc[0]['close']
        except:
            changes[stock] = 0
    return pd.Series(changes)

def rebalance_portfolio(context, target_stocks, bar_dict):
    """调整投资组合"""
    current_positions = set(context.portfolio.positions.keys())
    target_set = set(target_stocks)
    
    # 卖出不在目标中的股票
    for stock in current_positions - target_set:
        order_target_percent(stock, 0)
        log.info(f"卖出: {stock}")
    
    # 等权买入目标股票
    if target_stocks:
        weight = 0.95 / len(target_stocks)  # 留5%现金
        for stock in target_stocks:
            order_target_percent(stock, weight)
            log.info(f"买入: {stock}, 权重: {weight:.2%}")

def check_risk_control(context, bar_dict):
    """风险控制检查"""
    for stock, position in context.portfolio.positions.items():
        if position.quantity <= 0:
            continue
        
        current_price = bar_dict[stock].close
        avg_cost = position.avg_cost
        
        # 计算收益率
        pnl_ratio = (current_price - avg_cost) / avg_cost
        
        # 止损
        if pnl_ratio < -context.stop_loss:
            order_target_percent(stock, 0)
            log.warn(f"止损卖出: {stock}, 亏损: {pnl_ratio:.2%}")
        
        # 止盈
        elif pnl_ratio > context.take_profit:
            order_target_percent(stock, 0)
            log.info(f"止盈卖出: {stock}, 盈利: {pnl_ratio:.2%}")

def is_trading(stock):
    """检查是否可交易"""
    try:
        current_data = get_current_data()
        return not current_data[stock].paused
    except:
        return True
