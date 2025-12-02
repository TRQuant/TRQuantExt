# -*- coding: utf-8 -*-
"""
本地回测引擎
============

基于Backtrader的本地回测引擎

功能:
1. 多因子选股策略回测
2. 绩效指标计算（夏普、最大回撤、年化等）
3. 净值曲线生成
4. 回测报告生成
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# 尝试导入backtrader
try:
    import backtrader as bt
    BACKTRADER_AVAILABLE = True
except ImportError:
    BACKTRADER_AVAILABLE = False
    logger.warning("Backtrader未安装，使用简化回测引擎")


@dataclass
class BacktestConfig:
    """回测配置"""
    start_date: str
    end_date: str
    initial_capital: float = 1000000.0
    commission_rate: float = 0.0003     # 佣金率
    stamp_tax_rate: float = 0.001       # 印花税
    slippage: float = 0.001             # 滑点
    benchmark: str = "000300.XSHG"      # 基准
    position_limit: int = 20            # 最大持仓
    rebalance_freq: str = "monthly"     # 调仓频率
    

@dataclass
class TradeRecord:
    """交易记录"""
    date: str
    stock_code: str
    stock_name: str
    direction: str  # buy/sell
    price: float
    quantity: int
    amount: float
    pnl: float = 0.0
    pnl_pct: float = 0.0


@dataclass
class PerformanceMetrics:
    """绩效指标"""
    total_return: float          # 总收益率
    annual_return: float         # 年化收益率
    benchmark_return: float      # 基准收益率
    excess_return: float         # 超额收益
    sharpe_ratio: float          # 夏普比率
    max_drawdown: float          # 最大回撤
    max_drawdown_duration: int   # 最大回撤持续天数
    win_rate: float              # 胜率
    profit_loss_ratio: float     # 盈亏比
    volatility: float            # 波动率
    calmar_ratio: float          # 卡尔玛比率
    sortino_ratio: float         # 索提诺比率
    trade_count: int             # 交易次数
    avg_holding_days: float      # 平均持仓天数
    
    def to_dict(self) -> dict:
        return {
            'total_return': f"{self.total_return:.2%}",
            'annual_return': f"{self.annual_return:.2%}",
            'benchmark_return': f"{self.benchmark_return:.2%}",
            'excess_return': f"{self.excess_return:.2%}",
            'sharpe_ratio': f"{self.sharpe_ratio:.2f}",
            'max_drawdown': f"{self.max_drawdown:.2%}",
            'max_drawdown_duration': f"{self.max_drawdown_duration}天",
            'win_rate': f"{self.win_rate:.2%}",
            'profit_loss_ratio': f"{self.profit_loss_ratio:.2f}",
            'volatility': f"{self.volatility:.2%}",
            'calmar_ratio': f"{self.calmar_ratio:.2f}",
            'sortino_ratio': f"{self.sortino_ratio:.2f}",
            'trade_count': self.trade_count,
            'avg_holding_days': f"{self.avg_holding_days:.1f}天"
        }


@dataclass
class BacktestResult:
    """回测结果"""
    config: BacktestConfig
    metrics: PerformanceMetrics
    equity_curve: pd.DataFrame      # 净值曲线
    trades: List[TradeRecord]       # 交易记录
    daily_returns: pd.Series        # 日收益率
    positions: pd.DataFrame         # 持仓记录
    benchmark_curve: pd.DataFrame   # 基准曲线
    run_time: float = 0.0          # 运行时间(秒)
    
    def to_dict(self) -> dict:
        return {
            'config': {
                'start_date': self.config.start_date,
                'end_date': self.config.end_date,
                'initial_capital': self.config.initial_capital,
                'benchmark': self.config.benchmark
            },
            'metrics': self.metrics.to_dict(),
            'trade_count': len(self.trades),
            'run_time': f"{self.run_time:.1f}秒"
        }


class SimpleBacktestEngine:
    """
    简化回测引擎（不依赖Backtrader）
    
    用于快速验证策略逻辑
    """
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.trades: List[TradeRecord] = []
        self.equity_curve = []
        self.positions = {}
        self.cash = config.initial_capital
        self.current_value = config.initial_capital
    
    def run(self, stock_scores: Dict[str, pd.DataFrame]) -> BacktestResult:
        """
        执行回测
        
        Args:
            stock_scores: 股票评分数据 {stock_code: DataFrame with date, score columns}
        
        Returns:
            BacktestResult
        """
        logger.info(f"🚀 开始回测: {self.config.start_date} ~ {self.config.end_date}")
        start_time = datetime.now()
        
        # 获取价格数据
        price_data = self._get_price_data(list(stock_scores.keys()))
        benchmark_data = self._get_benchmark_data()
        
        # 生成交易日期序列
        dates = pd.date_range(self.config.start_date, self.config.end_date, freq='B')
        rebalance_dates = self._get_rebalance_dates(dates)
        
        equity_records = []
        
        for dt in dates:
            dt_str = dt.strftime('%Y-%m-%d')
            
            # 更新持仓市值
            self._update_positions_value(dt_str, price_data)
            
            # 调仓日
            if dt in rebalance_dates:
                target_stocks = self._select_stocks(dt_str, stock_scores)
                self._rebalance(dt_str, target_stocks, price_data)
            
            # 记录净值
            equity_records.append({
                'date': dt_str,
                'equity': self.current_value,
                'cash': self.cash,
                'positions_value': self.current_value - self.cash
            })
        
        # 构建结果
        equity_df = pd.DataFrame(equity_records)
        equity_df['date'] = pd.to_datetime(equity_df['date'])
        equity_df.set_index('date', inplace=True)
        
        # 计算日收益率
        equity_df['returns'] = equity_df['equity'].pct_change()
        
        # 计算绩效指标
        metrics = self._calculate_metrics(equity_df, benchmark_data)
        
        run_time = (datetime.now() - start_time).total_seconds()
        
        result = BacktestResult(
            config=self.config,
            metrics=metrics,
            equity_curve=equity_df,
            trades=self.trades,
            daily_returns=equity_df['returns'],
            positions=pd.DataFrame(),  # TODO: 持仓记录
            benchmark_curve=benchmark_data,
            run_time=run_time
        )
        
        logger.info(f"✅ 回测完成: 收益率={metrics.total_return:.2%}, 夏普={metrics.sharpe_ratio:.2f}")
        return result
    
    def _get_price_data(self, stocks: List[str]) -> Dict[str, pd.DataFrame]:
        """获取价格数据"""
        price_data = {}
        
        try:
            from core.data_source_manager import get_data_source_manager
            
            manager = get_data_source_manager()
            
            for stock in stocks[:50]:  # 限制数量
                result = manager.get_price(
                    stock, 
                    self.config.start_date, 
                    self.config.end_date
                )
                if result.success and result.data is not None:
                    price_data[stock] = result.data
                    
        except Exception as e:
            logger.warning(f"获取价格数据失败: {e}")
        
        return price_data
    
    def _get_benchmark_data(self) -> pd.DataFrame:
        """获取基准数据"""
        try:
            from core.data_source_manager import get_data_source_manager
            
            manager = get_data_source_manager()
            result = manager.get_price(
                self.config.benchmark,
                self.config.start_date,
                self.config.end_date
            )
            
            if result.success and result.data is not None:
                df = result.data.copy()
                df['returns'] = df['close'].pct_change()
                df['cumulative'] = (1 + df['returns']).cumprod()
                return df
                
        except Exception as e:
            logger.warning(f"获取基准数据失败: {e}")
        
        return pd.DataFrame()
    
    def _get_rebalance_dates(self, dates: pd.DatetimeIndex) -> set:
        """获取调仓日期"""
        freq = self.config.rebalance_freq
        
        if freq == 'daily':
            return set(dates)
        elif freq == 'weekly':
            # 每周一
            return set(dates[dates.dayofweek == 0])
        elif freq == 'biweekly':
            weekly = dates[dates.dayofweek == 0]
            return set(weekly[::2])
        elif freq == 'monthly':
            # 每月第一个交易日
            return set(dates.to_series().groupby(dates.to_period('M')).first())
        elif freq == 'quarterly':
            return set(dates.to_series().groupby(dates.to_period('Q')).first())
        
        return set(dates.to_series().groupby(dates.to_period('M')).first())
    
    def _select_stocks(self, date: str, stock_scores: Dict[str, pd.DataFrame]) -> List[str]:
        """选股"""
        scores = []
        
        for stock, df in stock_scores.items():
            if df is not None and not df.empty:
                # 获取最近的评分
                if 'date' in df.columns:
                    mask = df['date'] <= date
                    if mask.any():
                        latest = df[mask].iloc[-1]
                        if 'score' in latest:
                            scores.append((stock, float(latest['score'])))
                elif 'score' in df.columns:
                    scores.append((stock, float(df['score'].iloc[-1])))
        
        # 按评分排序
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前N只
        return [s[0] for s in scores[:self.config.position_limit]]
    
    def _update_positions_value(self, date: str, price_data: Dict[str, pd.DataFrame]):
        """更新持仓市值"""
        positions_value = 0
        
        for stock, qty in list(self.positions.items()):
            if stock in price_data:
                df = price_data[stock]
                if not df.empty:
                    # 获取当日收盘价
                    try:
                        if hasattr(df.index, 'strftime'):
                            mask = df.index.strftime('%Y-%m-%d') <= date
                        else:
                            mask = df.index <= date
                        
                        if mask.any():
                            price = df.loc[mask, 'close'].iloc[-1]
                            positions_value += qty * price
                        else:
                            # 使用首日价格
                            positions_value += qty * df['close'].iloc[0]
                    except:
                        positions_value += qty * df['close'].iloc[-1] if not df.empty else 0
        
        self.current_value = self.cash + positions_value
    
    def _rebalance(self, date: str, target_stocks: List[str], price_data: Dict[str, pd.DataFrame]):
        """调仓"""
        if not target_stocks:
            return
        
        # 计算目标仓位
        target_weight = 1.0 / len(target_stocks)
        target_value = self.current_value * target_weight * 0.95  # 留5%现金
        
        # 卖出不在目标中的股票
        for stock in list(self.positions.keys()):
            if stock not in target_stocks:
                self._sell(stock, date, price_data)
        
        # 买入目标股票
        for stock in target_stocks:
            if stock not in self.positions:
                self._buy(stock, target_value, date, price_data)
    
    def _buy(self, stock: str, target_value: float, date: str, price_data: Dict[str, pd.DataFrame]):
        """买入"""
        if stock not in price_data or price_data[stock].empty:
            return
        
        try:
            df = price_data[stock]
            if hasattr(df.index, 'strftime'):
                mask = df.index.strftime('%Y-%m-%d') <= date
            else:
                mask = df.index <= date
            
            if not mask.any():
                return
            
            price = df.loc[mask, 'close'].iloc[-1]
            
            # 计算可买数量（100股整数）
            quantity = int(target_value / price / 100) * 100
            
            if quantity <= 0:
                return
            
            cost = quantity * price * (1 + self.config.commission_rate + self.config.slippage)
            
            if cost > self.cash:
                quantity = int(self.cash / price / (1 + self.config.commission_rate + self.config.slippage) / 100) * 100
                cost = quantity * price * (1 + self.config.commission_rate + self.config.slippage)
            
            if quantity > 0 and cost <= self.cash:
                self.cash -= cost
                self.positions[stock] = self.positions.get(stock, 0) + quantity
                
                self.trades.append(TradeRecord(
                    date=date,
                    stock_code=stock,
                    stock_name='',
                    direction='buy',
                    price=price,
                    quantity=quantity,
                    amount=cost
                ))
                
        except Exception as e:
            logger.debug(f"买入失败 {stock}: {e}")
    
    def _sell(self, stock: str, date: str, price_data: Dict[str, pd.DataFrame]):
        """卖出"""
        if stock not in self.positions or self.positions[stock] <= 0:
            return
        
        if stock not in price_data or price_data[stock].empty:
            return
        
        try:
            df = price_data[stock]
            if hasattr(df.index, 'strftime'):
                mask = df.index.strftime('%Y-%m-%d') <= date
            else:
                mask = df.index <= date
            
            if not mask.any():
                return
            
            price = df.loc[mask, 'close'].iloc[-1]
            quantity = self.positions[stock]
            
            proceeds = quantity * price * (1 - self.config.commission_rate - self.config.stamp_tax_rate - self.config.slippage)
            
            self.cash += proceeds
            del self.positions[stock]
            
            self.trades.append(TradeRecord(
                date=date,
                stock_code=stock,
                stock_name='',
                direction='sell',
                price=price,
                quantity=quantity,
                amount=proceeds
            ))
            
        except Exception as e:
            logger.debug(f"卖出失败 {stock}: {e}")
    
    def _calculate_metrics(self, equity_df: pd.DataFrame, benchmark_df: pd.DataFrame) -> PerformanceMetrics:
        """计算绩效指标"""
        returns = equity_df['returns'].dropna()
        
        # 总收益率
        total_return = (equity_df['equity'].iloc[-1] / self.config.initial_capital) - 1
        
        # 年化收益率
        days = len(equity_df)
        annual_return = (1 + total_return) ** (252 / max(days, 1)) - 1
        
        # 基准收益率
        if not benchmark_df.empty and 'cumulative' in benchmark_df.columns:
            benchmark_return = benchmark_df['cumulative'].iloc[-1] - 1
        else:
            benchmark_return = 0.0
        
        # 超额收益
        excess_return = annual_return - benchmark_return
        
        # 波动率
        volatility = returns.std() * np.sqrt(252)
        
        # 夏普比率（假设无风险利率2%）
        rf = 0.02 / 252
        sharpe_ratio = (returns.mean() - rf) / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        
        # 最大回撤
        cummax = equity_df['equity'].cummax()
        drawdown = (equity_df['equity'] - cummax) / cummax
        max_drawdown = abs(drawdown.min())
        
        # 最大回撤持续期
        drawdown_duration = 0
        if max_drawdown > 0:
            peak_idx = drawdown.idxmin()
            recovery = equity_df.loc[peak_idx:, 'equity']
            if len(recovery) > 1:
                recovery_idx = recovery[recovery >= cummax[peak_idx]].index
                if len(recovery_idx) > 0:
                    drawdown_duration = (recovery_idx[0] - peak_idx).days
                else:
                    drawdown_duration = (equity_df.index[-1] - peak_idx).days
        
        # 胜率
        winning_trades = len([t for t in self.trades if t.direction == 'sell' and t.pnl > 0])
        total_trades = len([t for t in self.trades if t.direction == 'sell'])
        win_rate = winning_trades / max(total_trades, 1)
        
        # 盈亏比
        profits = sum([t.pnl for t in self.trades if t.pnl > 0])
        losses = abs(sum([t.pnl for t in self.trades if t.pnl < 0]))
        profit_loss_ratio = profits / max(losses, 1)
        
        # 卡尔玛比率
        calmar_ratio = annual_return / max(max_drawdown, 0.001)
        
        # 索提诺比率
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0.001
        sortino_ratio = (annual_return - 0.02) / max(downside_std, 0.001)
        
        return PerformanceMetrics(
            total_return=total_return,
            annual_return=annual_return,
            benchmark_return=benchmark_return,
            excess_return=excess_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_duration=drawdown_duration,
            win_rate=win_rate,
            profit_loss_ratio=profit_loss_ratio,
            volatility=volatility,
            calmar_ratio=calmar_ratio,
            sortino_ratio=sortino_ratio,
            trade_count=len(self.trades),
            avg_holding_days=days / max(total_trades, 1) * 2
        )


def create_backtest_engine(config: BacktestConfig) -> SimpleBacktestEngine:
    """创建回测引擎"""
    return SimpleBacktestEngine(config)


def run_quick_backtest(
    stocks: List[str],
    start_date: str,
    end_date: str,
    initial_capital: float = 1000000.0
) -> BacktestResult:
    """
    快速回测
    
    Args:
        stocks: 股票列表
        start_date: 开始日期
        end_date: 结束日期
        initial_capital: 初始资金
    
    Returns:
        BacktestResult
    """
    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital
    )
    
    # 创建等权评分
    stock_scores = {s: pd.DataFrame({'score': [1.0]}) for s in stocks}
    
    engine = create_backtest_engine(config)
    return engine.run(stock_scores)
