# -*- coding: utf-8 -*-
"""
因子与候选池集成模块
===================

根据Alpha因子模块集成方案设计，实现：
- 候选池 → 因子筛选 → 策略信号 的完整流程
- 因子信号与主线选股信号的融合
- 综合评分系统

流程设计：
1. 从候选池模块获取股票池
2. 计算多因子评分
3. 融合主线评分和因子评分
4. 输出最终选股信号
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any, Union, Tuple
from datetime import datetime
from dataclasses import dataclass, field
import logging

from .factor_manager import FactorManager
from .factor_evaluator import FactorEvaluator
from .factor_storage import FactorStorage

logger = logging.getLogger(__name__)


@dataclass
class StockSignal:
    """股票信号"""
    code: str                           # 股票代码
    name: str = ""                      # 股票名称
    
    # 评分
    factor_score: float = 0.0           # 因子综合评分
    mainline_score: float = 0.0         # 主线评分
    combined_score: float = 0.0         # 综合评分
    
    # 因子明细
    factor_details: Dict[str, float] = field(default_factory=dict)
    
    # 分类
    period: str = "medium"              # 短/中/长期
    sector: str = ""                    # 板块
    mainline: str = ""                  # 所属主线
    
    # 信号强度
    signal_strength: str = "medium"     # strong/medium/weak
    entry_reason: str = ""              # 入选理由
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'code': self.code,
            'name': self.name,
            'factor_score': self.factor_score,
            'mainline_score': self.mainline_score,
            'combined_score': self.combined_score,
            'factor_details': self.factor_details,
            'period': self.period,
            'sector': self.sector,
            'mainline': self.mainline,
            'signal_strength': self.signal_strength,
            'entry_reason': self.entry_reason
        }


class FactorPoolIntegration:
    """
    因子与候选池集成
    
    将因子模块与现有候选池模块对接，
    实现从候选股票池到最终选股信号的完整流程
    """
    
    # 默认因子权重配置
    DEFAULT_FACTOR_WEIGHTS = {
        'short': {
            'PriceMomentum': 0.3,
            'Reversal': 0.2,
            'CompositeFlow': 0.3,
            'RelativeStrength': 0.2
        },
        'medium': {
            'CompositeValue': 0.25,
            'CompositeGrowth': 0.25,
            'CompositeMomentum': 0.25,
            'CompositeQuality': 0.25
        },
        'long': {
            'CompositeValue': 0.35,
            'CompositeGrowth': 0.30,
            'CompositeQuality': 0.25,
            'PriceMomentum': 0.10
        }
    }
    
    def __init__(
        self,
        jq_client=None,
        factor_manager: Optional[FactorManager] = None,
        factor_storage: Optional[FactorStorage] = None,
        mainline_weight: float = 0.4,
        factor_weight: float = 0.6
    ):
        """
        初始化
        
        Args:
            jq_client: JQData客户端
            factor_manager: 因子管理器（可选，自动创建）
            factor_storage: 因子存储（可选，自动创建）
            mainline_weight: 主线评分权重
            factor_weight: 因子评分权重
        """
        self.jq_client = jq_client
        
        # 因子管理器
        if factor_manager:
            self.factor_manager = factor_manager
        else:
            self.factor_manager = FactorManager(jq_client=jq_client)
        
        # 因子存储
        if factor_storage:
            self.factor_storage = factor_storage
        else:
            self.factor_storage = FactorStorage()
        
        # 权重配置
        self.mainline_weight = mainline_weight
        self.factor_weight = factor_weight
    
    def set_jq_client(self, jq_client):
        """设置JQData客户端"""
        self.jq_client = jq_client
        self.factor_manager.set_jq_client(jq_client)
    
    def process_candidate_pool(
        self,
        stocks: List[str],
        date: Union[str, datetime],
        period: str = "medium",
        mainline_scores: Optional[Dict[str, float]] = None,
        factor_weights: Optional[Dict[str, float]] = None,
        top_n: int = 30
    ) -> List[StockSignal]:
        """
        处理候选池，生成选股信号
        
        Args:
            stocks: 候选股票列表
            date: 计算日期
            period: 投资周期 ('short', 'medium', 'long')
            mainline_scores: 主线评分（可选）
            factor_weights: 因子权重（可选，使用默认配置）
            top_n: 选择前N只股票
        
        Returns:
            List[StockSignal]: 选股信号列表
        """
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d')
        
        logger.info(f"处理候选池: {len(stocks)}只股票, 日期: {date}, 周期: {period}")
        
        # 获取因子权重
        if factor_weights is None:
            factor_weights = self.DEFAULT_FACTOR_WEIGHTS.get(period, self.DEFAULT_FACTOR_WEIGHTS['medium'])
        
        # 计算因子评分
        factor_scores, factor_details = self._calculate_factor_scores(
            stocks, date, factor_weights
        )
        
        # 融合主线评分
        combined_scores = self._combine_scores(
            stocks, factor_scores, mainline_scores
        )
        
        # 生成信号
        signals = self._generate_signals(
            stocks, date, period, factor_scores, combined_scores, 
            factor_details, mainline_scores, top_n
        )
        
        # 保存因子值到存储
        self._save_factor_values(date, factor_details)
        
        return signals
    
    def _calculate_factor_scores(
        self,
        stocks: List[str],
        date: datetime,
        factor_weights: Dict[str, float]
    ) -> Tuple[pd.Series, Dict[str, pd.Series]]:
        """
        计算因子综合评分
        
        Returns:
            Tuple[综合评分, 因子明细]
        """
        factor_details = {}
        
        # 计算各因子
        for factor_name in factor_weights.keys():
            try:
                result = self.factor_manager.calculate_factor(
                    factor_name, stocks, date,
                    winsorize=True, standardize=True
                )
                
                if result and not result.values.isna().all():
                    factor_details[factor_name] = result.values
                    logger.debug(f"因子计算完成: {factor_name}, 有效: {result.valid_count}")
                else:
                    logger.warning(f"因子无有效值: {factor_name}")
                    
            except Exception as e:
                logger.warning(f"因子计算失败 {factor_name}: {e}")
        
        if not factor_details:
            logger.warning("所有因子计算失败，返回空评分")
            return pd.Series(index=stocks, dtype=float), {}
        
        # 加权组合
        combined = self.factor_manager.combine_factors(
            {name: type('Result', (), {'values': values})() 
             for name, values in factor_details.items()},
            weights=factor_weights
        )
        
        # 标准化到0-100分
        if combined.std() > 0:
            combined = (combined - combined.min()) / (combined.max() - combined.min()) * 100
        
        return combined, factor_details
    
    def _combine_scores(
        self,
        stocks: List[str],
        factor_scores: pd.Series,
        mainline_scores: Optional[Dict[str, float]]
    ) -> pd.Series:
        """融合因子评分和主线评分"""
        combined = pd.Series(index=stocks, dtype=float)
        
        for stock in stocks:
            factor_score = factor_scores.get(stock, 0) if stock in factor_scores.index else 0
            mainline_score = mainline_scores.get(stock, 0) if mainline_scores else 0
            
            # 加权融合
            combined[stock] = (
                self.factor_weight * factor_score +
                self.mainline_weight * mainline_score
            )
        
        return combined
    
    def _generate_signals(
        self,
        stocks: List[str],
        date: datetime,
        period: str,
        factor_scores: pd.Series,
        combined_scores: pd.Series,
        factor_details: Dict[str, pd.Series],
        mainline_scores: Optional[Dict[str, float]],
        top_n: int
    ) -> List[StockSignal]:
        """生成选股信号"""
        signals = []
        
        # 获取股票名称
        stock_names = self._get_stock_names(stocks, date)
        
        # 按综合评分排序
        sorted_stocks = combined_scores.sort_values(ascending=False).head(top_n)
        
        for rank, (stock, combined_score) in enumerate(sorted_stocks.items(), 1):
            # 因子明细
            details = {}
            for factor_name, values in factor_details.items():
                if stock in values.index:
                    details[factor_name] = float(values[stock])
            
            # 信号强度
            if combined_score >= 80:
                strength = "strong"
            elif combined_score >= 60:
                strength = "medium"
            else:
                strength = "weak"
            
            # 入选理由
            top_factors = sorted(details.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
            reason_parts = [f"{name}={val:.2f}" for name, val in top_factors]
            entry_reason = f"综合排名#{rank}, " + ", ".join(reason_parts)
            
            signal = StockSignal(
                code=stock,
                name=stock_names.get(stock, stock),
                factor_score=float(factor_scores.get(stock, 0)),
                mainline_score=float(mainline_scores.get(stock, 0)) if mainline_scores else 0,
                combined_score=float(combined_score),
                factor_details=details,
                period=period,
                signal_strength=strength,
                entry_reason=entry_reason
            )
            
            signals.append(signal)
        
        logger.info(f"生成信号: {len(signals)}只股票")
        return signals
    
    def _get_stock_names(
        self,
        stocks: List[str],
        date: datetime
    ) -> Dict[str, str]:
        """获取股票名称"""
        names = {}
        
        if self.jq_client:
            try:
                import jqdatasdk as jq
                securities = jq.get_all_securities(types=['stock'], date=date)
                for stock in stocks:
                    if stock in securities.index:
                        names[stock] = securities.loc[stock, 'display_name']
            except Exception as e:
                logger.warning(f"获取股票名称失败: {e}")
        
        return names
    
    def _save_factor_values(
        self,
        date: datetime,
        factor_details: Dict[str, pd.Series]
    ):
        """保存因子值"""
        for factor_name, values in factor_details.items():
            try:
                self.factor_storage.save_factor_values(factor_name, date, values)
            except Exception as e:
                logger.warning(f"保存因子值失败 {factor_name}: {e}")
    
    def get_factor_radar_data(
        self,
        stock: str,
        date: Union[str, datetime],
        factor_names: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """
        获取股票因子雷达图数据
        
        Args:
            stock: 股票代码
            date: 日期
            factor_names: 因子名称列表
        
        Returns:
            Dict[因子名, 标准化分数]
        """
        if factor_names is None:
            factor_names = ['CompositeValue', 'CompositeGrowth', 'CompositeQuality', 
                          'CompositeMomentum', 'CompositeFlow']
        
        radar_data = {}
        
        for factor_name in factor_names:
            values = self.factor_storage.load_factor_values(factor_name, date, [stock])
            if values is not None and stock in values.index:
                # 转换为0-100分（假设已标准化）
                radar_data[factor_name] = float(min(100, max(0, 50 + values[stock] * 20)))
            else:
                radar_data[factor_name] = 50  # 默认中性
        
        return radar_data
    
    def get_factor_heatmap_data(
        self,
        stocks: List[str],
        date: Union[str, datetime],
        factor_names: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        获取因子热力图数据
        
        Args:
            stocks: 股票列表
            date: 日期
            factor_names: 因子名称列表
        
        Returns:
            pd.DataFrame: 热力图数据（股票×因子）
        """
        if factor_names is None:
            factor_names = list(self.DEFAULT_FACTOR_WEIGHTS['medium'].keys())
        
        data = {}
        
        for factor_name in factor_names:
            values = self.factor_storage.load_factor_values(factor_name, date, stocks)
            if values is not None:
                data[factor_name] = values
        
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()


# 便捷函数
def create_factor_pool_integration(jq_client=None) -> FactorPoolIntegration:
    """创建因子候选池集成模块"""
    return FactorPoolIntegration(jq_client=jq_client)

