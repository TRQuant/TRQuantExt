# -*- coding: utf-8 -*-
"""
动量因子模块
============

包含以下因子：
- PriceMomentum: 价格动量（中期）
- Reversal: 短期反转
- RelativeStrength: 相对强弱

A股特点：
- 短期反转效应显著（1周）
- 中期动量（3-6个月）有效
- 长期动量（12个月）效果较弱
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Union
from datetime import datetime, timedelta
import logging

from .base_factor import BaseFactor

logger = logging.getLogger(__name__)


class PriceMomentumFactor(BaseFactor):
    """
    价格动量因子
    
    公式: 动量 = (P_t - P_t-N) / P_t-N
    
    经济学逻辑：
    - 价格趋势具有延续性
    - 反映市场对公司的认可
    
    A股实证：
    - 3-6个月动量效果较好
    - 需要剔除最近1个月（短期反转）
    """
    
    name = "PriceMomentum"
    category = "momentum"
    description = "价格动量因子"
    direction = 1
    
    def __init__(self, jq_client=None, lookback_days: int = 120, skip_days: int = 20, **kwargs):
        """
        初始化
        
        Args:
            lookback_days: 回看天数（默认120天，约6个月）
            skip_days: 跳过最近天数（默认20天，约1个月）
        """
        super().__init__(jq_client=jq_client, **kwargs)
        self.lookback_days = lookback_days
        self.skip_days = skip_days
    
    def calculate_raw(
        self,
        stocks: List[str],
        date: Union[str, datetime],
        **kwargs
    ) -> pd.Series:
        """计算价格动量因子"""
        if self.jq_client is None:
            raise ValueError("需要JQData客户端来计算价格动量因子")
        
        try:
            import jqdatasdk as jq
            
            if isinstance(date, str):
                date = datetime.strptime(date, '%Y-%m-%d')
            
            # 【支持动态调整lookback_days以适应试用账户】
            lookback_days = kwargs.get('lookback_days', self.lookback_days)
            skip_days = kwargs.get('skip_days', self.skip_days)
            
            # 获取历史价格
            # 需要lookback_days + skip_days的数据
            total_days = lookback_days + skip_days + 10  # 多取一些以防节假日
            
            prices = jq.get_price(
                stocks,
                end_date=date,
                count=total_days,
                fields=['close'],
                panel=False
            )
            
            if prices.empty:
                return pd.Series(index=stocks, dtype=float)
            
            # 计算每只股票的动量
            momentum_dict = {}
            
            for stock in stocks:
                stock_prices = prices[prices['code'] == stock]['close']
                
                if len(stock_prices) < lookback_days:
                    momentum_dict[stock] = np.nan
                    continue
                
                # 跳过最近skip_days天
                if skip_days > 0:
                    current_price = stock_prices.iloc[-(skip_days + 1)]
                else:
                    current_price = stock_prices.iloc[-1]
                
                # lookback_days之前的价格
                past_price = stock_prices.iloc[-(lookback_days + skip_days)]
                
                if past_price > 0:
                    momentum_dict[stock] = (current_price - past_price) / past_price
                else:
                    momentum_dict[stock] = np.nan
            
            result = pd.Series(momentum_dict)
            
            # 处理极端值
            result = result.clip(-2, 5)  # 限制在-200%到500%
            
            logger.info(f"价格动量因子计算完成(lookback={lookback_days}): 有效值 {result.notna().sum()}/{len(stocks)}")
            return result
            
        except Exception as e:
            logger.error(f"价格动量因子计算失败: {e}")
            return pd.Series(index=stocks, dtype=float)
    
    def get_ptrade_code(self) -> str:
        return f'''
# 价格动量因子
def calculate_price_momentum_factor(stocks, date, lookback_days={self.lookback_days}, skip_days={self.skip_days}):
    """
    计算价格动量因子
    
    Args:
        stocks: 股票列表
        date: 计算日期
        lookback_days: 回看天数
        skip_days: 跳过最近天数
    """
    from jqdatasdk import get_price
    import numpy as np
    
    total_days = lookback_days + skip_days + 10
    
    prices = get_price(
        stocks,
        end_date=date,
        count=total_days,
        fields=['close'],
        panel=False
    )
    
    momentum_dict = {{}}
    
    for stock in stocks:
        stock_prices = prices[prices['code'] == stock]['close']
        
        if len(stock_prices) < lookback_days:
            momentum_dict[stock] = np.nan
            continue
        
        if skip_days > 0:
            current_price = stock_prices.iloc[-(skip_days + 1)]
        else:
            current_price = stock_prices.iloc[-1]
        
        past_price = stock_prices.iloc[-(lookback_days + skip_days)]
        
        if past_price > 0:
            momentum_dict[stock] = (current_price - past_price) / past_price
        else:
            momentum_dict[stock] = np.nan
    
    import pandas as pd
    return pd.Series(momentum_dict).clip(-2, 5)
'''


class ReversalFactor(BaseFactor):
    """
    短期反转因子
    
    公式: 反转 = -(P_t - P_t-5) / P_t-5
    
    经济学逻辑：
    - 短期价格过度反应会修正
    - 反映市场情绪的过度波动
    
    A股实证：
    - 1周反转效应非常显著
    - IC可达0.04以上
    - 是A股最有效的因子之一
    """
    
    name = "Reversal"
    category = "momentum"
    description = "短期反转因子"
    direction = 1  # 取负后，下跌越多越好（反弹预期）
    
    def __init__(self, jq_client=None, lookback_days: int = 5, **kwargs):
        """
        初始化
        
        Args:
            lookback_days: 回看天数（默认5天，1周）
        """
        super().__init__(jq_client=jq_client, **kwargs)
        self.lookback_days = lookback_days
    
    def calculate_raw(
        self,
        stocks: List[str],
        date: Union[str, datetime],
        **kwargs
    ) -> pd.Series:
        """计算反转因子"""
        if self.jq_client is None:
            raise ValueError("需要JQData客户端来计算反转因子")
        
        try:
            import jqdatasdk as jq
            
            if isinstance(date, str):
                date = datetime.strptime(date, '%Y-%m-%d')
            
            # 支持动态调整lookback_days
            lookback_days = kwargs.get('lookback_days', self.lookback_days)
            
            # 获取历史价格
            prices = jq.get_price(
                stocks,
                end_date=date,
                count=lookback_days + 5,
                fields=['close'],
                panel=False
            )
            
            if prices.empty:
                return pd.Series(index=stocks, dtype=float)
            
            # 计算每只股票的反转
            reversal_dict = {}
            
            for stock in stocks:
                stock_prices = prices[prices['code'] == stock]['close']
                
                if len(stock_prices) < lookback_days + 1:
                    reversal_dict[stock] = np.nan
                    continue
                
                current_price = stock_prices.iloc[-1]
                past_price = stock_prices.iloc[-(lookback_days + 1)]
                
                if past_price > 0:
                    # 取负值：下跌越多，反转因子越大
                    reversal_dict[stock] = -(current_price - past_price) / past_price
                else:
                    reversal_dict[stock] = np.nan
            
            result = pd.Series(reversal_dict)
            
            # 处理极端值
            result = result.clip(-0.5, 0.5)
            
            logger.info(f"反转因子计算完成(lookback={lookback_days}): 有效值 {result.notna().sum()}/{len(stocks)}")
            return result
            
        except Exception as e:
            logger.error(f"反转因子计算失败: {e}")
            return pd.Series(index=stocks, dtype=float)
    
    def get_ptrade_code(self) -> str:
        return f'''
# 短期反转因子
def calculate_reversal_factor(stocks, date, lookback_days={self.lookback_days}):
    """
    计算短期反转因子
    
    短期下跌越多，反弹预期越强
    """
    from jqdatasdk import get_price
    import numpy as np
    import pandas as pd
    
    prices = get_price(
        stocks,
        end_date=date,
        count=lookback_days + 5,
        fields=['close'],
        panel=False
    )
    
    reversal_dict = {{}}
    
    for stock in stocks:
        stock_prices = prices[prices['code'] == stock]['close']
        
        if len(stock_prices) < lookback_days + 1:
            reversal_dict[stock] = np.nan
            continue
        
        current_price = stock_prices.iloc[-1]
        past_price = stock_prices.iloc[-(lookback_days + 1)]
        
        if past_price > 0:
            # 取负值：下跌越多，反转因子越大
            reversal_dict[stock] = -(current_price - past_price) / past_price
        else:
            reversal_dict[stock] = np.nan
    
    return pd.Series(reversal_dict).clip(-0.5, 0.5)
'''


class RelativeStrengthFactor(BaseFactor):
    """
    相对强弱因子
    
    公式: RS = 股票收益 - 基准收益
    
    经济学逻辑：
    - 相对表现反映个股的超额收益能力
    - 剔除了市场整体涨跌的影响
    
    A股实证：
    - 相对沪深300的超额收益是有效信号
    - 结合行业相对强弱效果更好
    """
    
    name = "RelativeStrength"
    category = "momentum"
    description = "相对强弱因子"
    direction = 1
    
    def __init__(
        self,
        jq_client=None,
        lookback_days: int = 60,
        benchmark: str = '000300.XSHG',
        **kwargs
    ):
        """
        初始化
        
        Args:
            lookback_days: 回看天数
            benchmark: 基准指数
        """
        super().__init__(jq_client=jq_client, **kwargs)
        self.lookback_days = lookback_days
        self.benchmark = benchmark
    
    def calculate_raw(
        self,
        stocks: List[str],
        date: Union[str, datetime],
        **kwargs
    ) -> pd.Series:
        """计算相对强弱因子"""
        if self.jq_client is None:
            raise ValueError("需要JQData客户端来计算相对强弱因子")
        
        try:
            import jqdatasdk as jq
            
            if isinstance(date, str):
                date = datetime.strptime(date, '%Y-%m-%d')
            
            # 支持动态调整lookback_days
            lookback_days = kwargs.get('lookback_days', self.lookback_days)
            
            # 获取股票价格
            stock_prices = jq.get_price(
                stocks,
                end_date=date,
                count=lookback_days + 5,
                fields=['close'],
                panel=False
            )
            
            # 获取基准价格
            benchmark_prices = jq.get_price(
                self.benchmark,
                end_date=date,
                count=lookback_days + 5,
                fields=['close']
            )
            
            if stock_prices.empty or benchmark_prices.empty:
                return pd.Series(index=stocks, dtype=float)
            
            # 计算基准收益
            benchmark_return = (
                benchmark_prices['close'].iloc[-1] / 
                benchmark_prices['close'].iloc[0] - 1
            )
            
            # 计算每只股票的相对强弱
            rs_dict = {}
            
            for stock in stocks:
                sp = stock_prices[stock_prices['code'] == stock]['close']
                
                if len(sp) < lookback_days:
                    rs_dict[stock] = np.nan
                    continue
                
                stock_return = sp.iloc[-1] / sp.iloc[0] - 1
                rs_dict[stock] = stock_return - benchmark_return
            
            result = pd.Series(rs_dict)
            
            # 处理极端值
            result = result.clip(-1, 2)
            
            logger.info(f"相对强弱因子计算完成(lookback={lookback_days}): 有效值 {result.notna().sum()}/{len(stocks)}")
            return result
            
        except Exception as e:
            logger.error(f"相对强弱因子计算失败: {e}")
            return pd.Series(index=stocks, dtype=float)
    
    def get_ptrade_code(self) -> str:
        return f'''
# 相对强弱因子
def calculate_relative_strength_factor(stocks, date, lookback_days={self.lookback_days}, benchmark='{self.benchmark}'):
    """
    计算相对强弱因子
    
    相对基准的超额收益
    """
    from jqdatasdk import get_price
    import numpy as np
    import pandas as pd
    
    # 股票价格
    stock_prices = get_price(
        stocks,
        end_date=date,
        count=lookback_days + 5,
        fields=['close'],
        panel=False
    )
    
    # 基准价格
    benchmark_prices = get_price(
        benchmark,
        end_date=date,
        count=lookback_days + 5,
        fields=['close']
    )
    
    # 基准收益
    benchmark_return = benchmark_prices['close'].iloc[-1] / benchmark_prices['close'].iloc[0] - 1
    
    rs_dict = {{}}
    
    for stock in stocks:
        sp = stock_prices[stock_prices['code'] == stock]['close']
        
        if len(sp) < lookback_days:
            rs_dict[stock] = np.nan
            continue
        
        stock_return = sp.iloc[-1] / sp.iloc[0] - 1
        rs_dict[stock] = stock_return - benchmark_return
    
    return pd.Series(rs_dict).clip(-1, 2)
'''


class CompositeMomentumFactor(BaseFactor):
    """
    复合动量因子
    
    综合价格动量、反转、相对强弱三个因子。
    """
    
    name = "CompositeMomentum"
    category = "momentum"
    description = "复合动量因子"
    direction = 1
    
    def __init__(self, jq_client=None, weights: Optional[dict] = None, **kwargs):
        """
        初始化
        
        Args:
            weights: 因子权重
        """
        super().__init__(jq_client=jq_client, **kwargs)
        self.weights = weights or {
            'PriceMomentum': 0.3,
            'Reversal': 0.4,  # 反转在A股效果最好
            'RelativeStrength': 0.3
        }
        
        self.momentum_factor = PriceMomentumFactor(jq_client=jq_client, **kwargs)
        self.reversal_factor = ReversalFactor(jq_client=jq_client, **kwargs)
        self.rs_factor = RelativeStrengthFactor(jq_client=jq_client, **kwargs)
    
    def calculate_raw(
        self,
        stocks: List[str],
        date: Union[str, datetime],
        **kwargs
    ) -> pd.Series:
        """计算复合动量因子"""
        factors = {}
        
        if self.weights.get('PriceMomentum', 0) > 0:
            factors['PriceMomentum'] = self.momentum_factor.calculate(stocks, date, **kwargs).values
        
        if self.weights.get('Reversal', 0) > 0:
            factors['Reversal'] = self.reversal_factor.calculate(stocks, date, **kwargs).values
        
        if self.weights.get('RelativeStrength', 0) > 0:
            factors['RelativeStrength'] = self.rs_factor.calculate(stocks, date, **kwargs).values
        
        df = pd.DataFrame(factors)
        
        # 加权平均
        composite = pd.Series(0, index=df.index)
        total_weight = 0
        
        for name, weight in self.weights.items():
            if name in df.columns:
                factor_values = df[name].fillna(0)
                composite += factor_values * weight
                total_weight += weight
        
        if total_weight > 0:
            composite /= total_weight
        
        composite.index = stocks
        
        logger.info(f"复合动量因子计算完成: 有效值 {composite.notna().sum()}/{len(stocks)}")
        return composite
    
    def get_ptrade_code(self) -> str:
        return '''
# 复合动量因子
def calculate_composite_momentum_factor(stocks, date, weights=None):
    """计算复合动量因子"""
    if weights is None:
        weights = {'PriceMomentum': 0.3, 'Reversal': 0.4, 'RelativeStrength': 0.3}
    
    momentum = calculate_price_momentum_factor(stocks, date)
    reversal = calculate_reversal_factor(stocks, date)
    rs = calculate_relative_strength_factor(stocks, date)
    
    def zscore(s):
        return (s - s.mean()) / s.std() if s.std() > 0 else s - s.mean()
    
    composite = (
        zscore(momentum.fillna(0)) * weights['PriceMomentum'] +
        zscore(reversal.fillna(0)) * weights['Reversal'] +
        zscore(rs.fillna(0)) * weights['RelativeStrength']
    )
    
    return zscore(composite)
'''

