# -*- coding: utf-8 -*-
"""
因子验证与评估模块
==================

根据Alpha因子模块集成方案设计，提供：
- IC信息系数计算
- IR信息比率计算
- 分组回测
- 多空组合回测
- 因子有效性检验

评估维度：
1. IC信息系数：因子与下一期股票收益的秩相关系数
2. 分组绩效：按因子值分组，观察各组收益是否单调
3. 多空组合：买入最高组、做空最低组，计算超额收益
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from scipy import stats
import logging

logger = logging.getLogger(__name__)


@dataclass
class ICResult:
    """IC计算结果"""
    factor_name: str
    date: datetime
    ic: float                    # 信息系数
    rank_ic: float               # 秩相关IC
    p_value: float               # 显著性检验p值
    n_stocks: int                # 股票数量
    
    @property
    def is_significant(self) -> bool:
        """是否显著（p<0.05）"""
        return self.p_value < 0.05
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'factor_name': self.factor_name,
            'date': self.date.isoformat() if isinstance(self.date, datetime) else str(self.date),
            'ic': self.ic,
            'rank_ic': self.rank_ic,
            'p_value': self.p_value,
            'n_stocks': self.n_stocks,
            'is_significant': self.is_significant
        }


@dataclass
class GroupBacktestResult:
    """分组回测结果"""
    factor_name: str
    start_date: datetime
    end_date: datetime
    n_groups: int
    group_returns: Dict[int, float]      # 各组平均收益
    group_sharpe: Dict[int, float]       # 各组夏普比
    long_short_return: float             # 多空收益
    is_monotonic: bool                   # 是否单调
    ic_mean: float                       # 平均IC
    ic_ir: float                         # IC信息比
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'factor_name': self.factor_name,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'n_groups': self.n_groups,
            'group_returns': self.group_returns,
            'group_sharpe': self.group_sharpe,
            'long_short_return': self.long_short_return,
            'is_monotonic': self.is_monotonic,
            'ic_mean': self.ic_mean,
            'ic_ir': self.ic_ir
        }


@dataclass
class FactorPerformance:
    """因子绩效汇总"""
    factor_name: str
    category: str
    description: str
    evaluation_date: datetime
    
    # IC指标
    ic_mean: float
    ic_std: float
    ic_ir: float                         # IC均值/IC标准差
    ic_positive_ratio: float             # IC为正的比例
    
    # 收益指标
    long_short_return: float             # 多空年化收益
    long_short_sharpe: float             # 多空夏普比
    top_group_excess_return: float       # 最高组超额收益
    
    # 稳定性指标
    turnover: float                      # 换手率
    max_drawdown: float                  # 最大回撤
    is_monotonic: bool                   # 分组收益是否单调
    
    # 状态
    status: str = "active"               # active, warning, inactive
    warning_msg: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'factor_name': self.factor_name,
            'category': self.category,
            'description': self.description,
            'evaluation_date': self.evaluation_date.isoformat(),
            'ic_mean': self.ic_mean,
            'ic_std': self.ic_std,
            'ic_ir': self.ic_ir,
            'ic_positive_ratio': self.ic_positive_ratio,
            'long_short_return': self.long_short_return,
            'long_short_sharpe': self.long_short_sharpe,
            'top_group_excess_return': self.top_group_excess_return,
            'turnover': self.turnover,
            'max_drawdown': self.max_drawdown,
            'is_monotonic': self.is_monotonic,
            'status': self.status,
            'warning_msg': self.warning_msg
        }


class FactorEvaluator:
    """
    因子评估器
    
    提供因子有效性检验和回测评估功能
    """
    
    def __init__(self, jq_client=None):
        """
        初始化评估器
        
        Args:
            jq_client: JQData客户端
        """
        self.jq_client = jq_client
    
    def calculate_ic(
        self,
        factor_values: pd.Series,
        forward_returns: pd.Series,
        method: str = 'spearman'
    ) -> ICResult:
        """
        计算信息系数(IC)
        
        Args:
            factor_values: 因子值
            forward_returns: 未来收益率
            method: 相关系数方法 ('spearman' or 'pearson')
        
        Returns:
            ICResult: IC计算结果
        """
        # 对齐数据
        common_idx = factor_values.dropna().index.intersection(forward_returns.dropna().index)
        
        if len(common_idx) < 10:
            logger.warning(f"有效样本不足: {len(common_idx)}")
            return ICResult(
                factor_name="",
                date=datetime.now(),
                ic=np.nan,
                rank_ic=np.nan,
                p_value=1.0,
                n_stocks=len(common_idx)
            )
        
        factor = factor_values.loc[common_idx]
        returns = forward_returns.loc[common_idx]
        
        # 计算秩相关IC（Spearman）
        rank_ic, p_value = stats.spearmanr(factor, returns)
        
        # 计算Pearson IC
        pearson_ic, _ = stats.pearsonr(factor, returns)
        
        return ICResult(
            factor_name=getattr(factor_values, 'name', ''),
            date=datetime.now(),
            ic=pearson_ic,
            rank_ic=rank_ic,
            p_value=p_value,
            n_stocks=len(common_idx)
        )
    
    def calculate_ic_series(
        self,
        factor_calculator,
        stocks: List[str],
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        forward_period: int = 20,
        freq: str = 'M'
    ) -> pd.DataFrame:
        """
        计算IC时间序列
        
        Args:
            factor_calculator: 因子计算函数或因子对象
            stocks: 股票列表
            start_date: 开始日期
            end_date: 结束日期
            forward_period: 未来收益计算周期（交易日）
            freq: 计算频率 ('D'=日, 'W'=周, 'M'=月)
        
        Returns:
            pd.DataFrame: IC时间序列
        """
        if self.jq_client is None:
            raise ValueError("需要JQData客户端")
        
        import jqdatasdk as jq
        
        # 生成日期序列
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        # 获取交易日
        trade_dates = jq.get_trade_days(start_date, end_date)
        
        if freq == 'M':
            # 月末日期
            dates_df = pd.DataFrame({'date': trade_dates})
            dates_df['month'] = dates_df['date'].apply(lambda x: x.strftime('%Y-%m'))
            eval_dates = dates_df.groupby('month')['date'].last().values
        elif freq == 'W':
            # 周末日期
            dates_df = pd.DataFrame({'date': trade_dates})
            dates_df['week'] = dates_df['date'].apply(lambda x: x.strftime('%Y-%W'))
            eval_dates = dates_df.groupby('week')['date'].last().values
        else:
            eval_dates = trade_dates
        
        ic_records = []
        
        for eval_date in eval_dates:
            try:
                # 计算因子值
                if hasattr(factor_calculator, 'calculate'):
                    factor_result = factor_calculator.calculate(stocks, eval_date)
                    factor_values = factor_result.values
                else:
                    factor_values = factor_calculator(stocks, eval_date)
                
                # 计算未来收益
                future_date_idx = np.searchsorted(trade_dates, eval_date) + forward_period
                if future_date_idx >= len(trade_dates):
                    continue
                
                future_date = trade_dates[future_date_idx]
                
                # 获取收益率
                returns = self._get_returns(stocks, eval_date, future_date)
                
                if returns is None or returns.empty:
                    continue
                
                # 计算IC
                ic_result = self.calculate_ic(factor_values, returns)
                
                ic_records.append({
                    'date': eval_date,
                    'ic': ic_result.ic,
                    'rank_ic': ic_result.rank_ic,
                    'p_value': ic_result.p_value,
                    'n_stocks': ic_result.n_stocks
                })
                
            except Exception as e:
                logger.warning(f"计算IC失败 {eval_date}: {e}")
                continue
        
        if not ic_records:
            return pd.DataFrame()
        
        return pd.DataFrame(ic_records).set_index('date')
    
    def _get_returns(
        self,
        stocks: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> Optional[pd.Series]:
        """获取区间收益率"""
        try:
            import jqdatasdk as jq
            
            # 获取起始和结束价格
            start_prices = jq.get_price(
                stocks, end_date=start_date, count=1, fields=['close'], panel=False
            )
            end_prices = jq.get_price(
                stocks, end_date=end_date, count=1, fields=['close'], panel=False
            )
            
            if start_prices.empty or end_prices.empty:
                return None
            
            start_dict = dict(zip(start_prices['code'], start_prices['close']))
            end_dict = dict(zip(end_prices['code'], end_prices['close']))
            
            returns = {}
            for stock in stocks:
                if stock in start_dict and stock in end_dict:
                    start_price = start_dict[stock]
                    end_price = end_dict[stock]
                    if start_price > 0:
                        returns[stock] = (end_price - start_price) / start_price
            
            return pd.Series(returns)
            
        except Exception as e:
            logger.error(f"获取收益率失败: {e}")
            return None
    
    def group_backtest(
        self,
        factor_calculator,
        stocks: List[str],
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        n_groups: int = 5,
        rebalance_freq: str = 'M'
    ) -> GroupBacktestResult:
        """
        分组回测
        
        将股票按因子值分组，计算各组收益表现
        
        Args:
            factor_calculator: 因子计算函数或因子对象
            stocks: 股票列表
            start_date: 开始日期
            end_date: 结束日期
            n_groups: 分组数量
            rebalance_freq: 调仓频率
        
        Returns:
            GroupBacktestResult: 分组回测结果
        """
        if self.jq_client is None:
            raise ValueError("需要JQData客户端")
        
        import jqdatasdk as jq
        
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        # 获取交易日
        trade_dates = jq.get_trade_days(start_date, end_date)
        
        # 生成调仓日期
        if rebalance_freq == 'M':
            dates_df = pd.DataFrame({'date': trade_dates})
            dates_df['month'] = dates_df['date'].apply(lambda x: x.strftime('%Y-%m'))
            rebalance_dates = dates_df.groupby('month')['date'].first().values
        else:
            rebalance_dates = trade_dates[::20]  # 约月度
        
        # 各组累积收益
        group_cum_returns = {i: [1.0] for i in range(1, n_groups + 1)}
        ic_list = []
        
        for i, rebal_date in enumerate(rebalance_dates[:-1]):
            next_rebal = rebalance_dates[i + 1]
            
            try:
                # 计算因子值
                if hasattr(factor_calculator, 'calculate'):
                    factor_result = factor_calculator.calculate(stocks, rebal_date)
                    factor_values = factor_result.values
                else:
                    factor_values = factor_calculator(stocks, rebal_date)
                
                # 分组
                factor_values = factor_values.dropna()
                if len(factor_values) < n_groups * 2:
                    continue
                
                # 按分位数分组
                factor_values = factor_values.rank(pct=True)
                groups = pd.cut(factor_values, bins=n_groups, labels=range(1, n_groups + 1))
                
                # 获取区间收益
                returns = self._get_returns(factor_values.index.tolist(), rebal_date, next_rebal)
                if returns is None:
                    continue
                
                # 计算各组收益
                for g in range(1, n_groups + 1):
                    group_stocks = groups[groups == g].index.tolist()
                    if group_stocks:
                        group_ret = returns.loc[returns.index.isin(group_stocks)].mean()
                        if not np.isnan(group_ret):
                            group_cum_returns[g].append(group_cum_returns[g][-1] * (1 + group_ret))
                
                # 计算IC
                ic_result = self.calculate_ic(factor_values, returns)
                if not np.isnan(ic_result.rank_ic):
                    ic_list.append(ic_result.rank_ic)
                
            except Exception as e:
                logger.warning(f"分组回测失败 {rebal_date}: {e}")
                continue
        
        # 计算结果指标
        group_returns = {}
        group_sharpe = {}
        
        for g in range(1, n_groups + 1):
            cum_ret_series = np.array(group_cum_returns[g])
            if len(cum_ret_series) > 1:
                period_returns = np.diff(cum_ret_series) / cum_ret_series[:-1]
                group_returns[g] = float((cum_ret_series[-1] / cum_ret_series[0]) ** (12 / len(period_returns)) - 1)
                if period_returns.std() > 0:
                    group_sharpe[g] = float(period_returns.mean() / period_returns.std() * np.sqrt(12))
                else:
                    group_sharpe[g] = 0.0
            else:
                group_returns[g] = 0.0
                group_sharpe[g] = 0.0
        
        # 多空收益
        long_short_return = group_returns.get(n_groups, 0) - group_returns.get(1, 0)
        
        # 检验单调性
        returns_list = [group_returns.get(g, 0) for g in range(1, n_groups + 1)]
        is_monotonic = all(x <= y for x, y in zip(returns_list[:-1], returns_list[1:])) or \
                       all(x >= y for x, y in zip(returns_list[:-1], returns_list[1:]))
        
        # IC统计
        ic_mean = float(np.mean(ic_list)) if ic_list else 0.0
        ic_std = float(np.std(ic_list)) if ic_list else 0.0
        ic_ir = ic_mean / ic_std if ic_std > 0 else 0.0
        
        return GroupBacktestResult(
            factor_name=getattr(factor_calculator, 'name', 'Unknown'),
            start_date=start_date,
            end_date=end_date,
            n_groups=n_groups,
            group_returns=group_returns,
            group_sharpe=group_sharpe,
            long_short_return=long_short_return,
            is_monotonic=is_monotonic,
            ic_mean=ic_mean,
            ic_ir=ic_ir
        )
    
    def evaluate_factor(
        self,
        factor,
        stocks: List[str],
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        n_groups: int = 5
    ) -> FactorPerformance:
        """
        综合评估因子
        
        Args:
            factor: 因子对象
            stocks: 股票列表
            start_date: 开始日期
            end_date: 结束日期
            n_groups: 分组数量
        
        Returns:
            FactorPerformance: 因子绩效
        """
        # IC时间序列
        ic_series = self.calculate_ic_series(
            factor, stocks, start_date, end_date, freq='M'
        )
        
        # 分组回测
        group_result = self.group_backtest(
            factor, stocks, start_date, end_date, n_groups=n_groups
        )
        
        # IC统计
        if not ic_series.empty:
            ic_mean = float(ic_series['rank_ic'].mean())
            ic_std = float(ic_series['rank_ic'].std())
            ic_ir = ic_mean / ic_std if ic_std > 0 else 0.0
            ic_positive_ratio = float((ic_series['rank_ic'] > 0).mean())
        else:
            ic_mean = ic_std = ic_ir = ic_positive_ratio = 0.0
        
        # 判断状态
        status = "active"
        warning_msg = None
        
        if ic_mean < 0.02:
            status = "warning"
            warning_msg = "IC均值过低"
        elif not group_result.is_monotonic:
            status = "warning"
            warning_msg = "分组收益不单调"
        elif ic_ir < 0.3:
            status = "warning"
            warning_msg = "IC稳定性不足"
        
        if ic_mean < 0:
            status = "inactive"
            warning_msg = "因子方向可能相反"
        
        return FactorPerformance(
            factor_name=factor.name,
            category=factor.category,
            description=factor.description,
            evaluation_date=datetime.now(),
            ic_mean=ic_mean,
            ic_std=ic_std,
            ic_ir=ic_ir,
            ic_positive_ratio=ic_positive_ratio,
            long_short_return=group_result.long_short_return,
            long_short_sharpe=group_result.group_sharpe.get(n_groups, 0) - group_result.group_sharpe.get(1, 0),
            top_group_excess_return=group_result.group_returns.get(n_groups, 0),
            turnover=0.0,  # 需要额外计算
            max_drawdown=0.0,  # 需要额外计算
            is_monotonic=group_result.is_monotonic,
            status=status,
            warning_msg=warning_msg
        )


# 便捷函数
def create_factor_evaluator(jq_client=None) -> FactorEvaluator:
    """创建因子评估器"""
    return FactorEvaluator(jq_client=jq_client)

