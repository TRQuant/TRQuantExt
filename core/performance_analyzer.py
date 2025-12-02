# -*- coding: utf-8 -*-
"""
绩效分析模块
"""

import logging
from dataclasses import dataclass
from typing import List, Dict
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class MonthlyPerformance:
    """月度绩效"""
    year: int
    month: int
    return_rate: float
    benchmark_return: float
    excess_return: float
    volatility: float
    max_drawdown: float


@dataclass
class RiskMetrics:
    """风险指标"""
    var_95: float
    var_99: float
    cvar_95: float
    beta: float
    alpha: float
    tracking_error: float
    information_ratio: float


class PerformanceAnalyzer:
    """绩效分析器"""
    
    def __init__(self, equity_curve: pd.DataFrame, benchmark_curve: pd.DataFrame):
        self.equity = equity_curve
        self.benchmark = benchmark_curve
        
        if 'returns' not in self.equity.columns:
            self.equity['returns'] = self.equity['equity'].pct_change()
        
        if not benchmark_curve.empty and 'returns' not in self.benchmark.columns:
            self.benchmark['returns'] = self.benchmark['close'].pct_change()
    
    def calculate_risk_metrics(self, risk_free_rate: float = 0.02) -> RiskMetrics:
        """计算风险指标"""
        returns = self.equity['returns'].dropna()
        
        var_95 = np.percentile(returns, 5)
        var_99 = np.percentile(returns, 1)
        cvar_95 = returns[returns <= var_95].mean() if len(returns[returns <= var_95]) > 0 else var_95
        
        if not self.benchmark.empty:
            bench_returns = self.benchmark['returns'].dropna()
            aligned = pd.concat([returns, bench_returns], axis=1).dropna()
            
            if len(aligned) > 10:
                cov = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])
                beta = cov[0, 1] / cov[1, 1] if cov[1, 1] != 0 else 1.0
                
                strategy_annual = returns.mean() * 252
                bench_annual = bench_returns.mean() * 252
                alpha = strategy_annual - risk_free_rate - beta * (bench_annual - risk_free_rate)
                
                excess = aligned.iloc[:, 0] - aligned.iloc[:, 1]
                tracking_error = excess.std() * np.sqrt(252)
                information_ratio = excess.mean() * 252 / tracking_error if tracking_error > 0 else 0
            else:
                beta, alpha, tracking_error, information_ratio = 1.0, 0.0, 0.0, 0.0
        else:
            beta, alpha, tracking_error, information_ratio = 1.0, 0.0, 0.0, 0.0
        
        return RiskMetrics(
            var_95=var_95, var_99=var_99, cvar_95=cvar_95,
            beta=beta, alpha=alpha, tracking_error=tracking_error,
            information_ratio=information_ratio
        )
    
    def generate_equity_chart_data(self) -> Dict:
        """生成净值曲线数据"""
        equity = self.equity.copy()
        equity['normalized'] = equity['equity'] / equity['equity'].iloc[0]
        
        benchmark_normalized = None
        if not self.benchmark.empty:
            benchmark = self.benchmark.copy()
            benchmark['normalized'] = benchmark['close'] / benchmark['close'].iloc[0]
            benchmark_normalized = benchmark['normalized'].tolist()
        
        return {
            'dates': [str(d) for d in equity.index],
            'equity': equity['normalized'].tolist(),
            'benchmark': benchmark_normalized
        }


def analyze_performance(equity_curve: pd.DataFrame, benchmark_curve: pd.DataFrame = None) -> Dict:
    """分析绩效"""
    if benchmark_curve is None:
        benchmark_curve = pd.DataFrame()
    
    analyzer = PerformanceAnalyzer(equity_curve, benchmark_curve)
    
    return {
        'risk': analyzer.calculate_risk_metrics(),
        'chart_data': analyzer.generate_equity_chart_data()
    }

