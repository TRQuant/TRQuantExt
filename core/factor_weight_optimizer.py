# -*- coding: utf-8 -*-
"""
因子权重优化器
==============

功能:
1. 网格搜索优化因子权重
2. 情景因子权重库（牛市/熊市/震荡）
3. IC加权优化
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple, Callable
from enum import Enum
import numpy as np
import pandas as pd
from itertools import product

logger = logging.getLogger(__name__)


class MarketScenario(Enum):
    """市场情景"""
    BULL = "bull"        # 牛市
    BEAR = "bear"        # 熊市
    SIDEWAYS = "sideways" # 震荡
    UNKNOWN = "unknown"  # 未知


@dataclass
class WeightConfig:
    """权重配置"""
    factor_weights: Dict[str, float]
    scenario: MarketScenario = MarketScenario.UNKNOWN
    description: str = ""
    performance: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            'factor_weights': self.factor_weights,
            'scenario': self.scenario.value,
            'description': self.description,
            'performance': self.performance
        }


@dataclass
class OptimizationResult:
    """优化结果"""
    best_weights: Dict[str, float]
    best_performance: float
    all_results: List[Tuple[Dict[str, float], float]]
    optimization_method: str
    iterations: int
    time_cost: float
    
    def to_dict(self) -> dict:
        return {
            'best_weights': self.best_weights,
            'best_performance': self.best_performance,
            'optimization_method': self.optimization_method,
            'iterations': self.iterations,
            'time_cost': self.time_cost
        }


# 预设情景权重库
SCENARIO_WEIGHT_LIBRARY = {
    MarketScenario.BULL: {
        "name": "牛市配置",
        "description": "趋势向上，侧重动量和成长因子",
        "weights": {
            "value": 0.10,      # 价值因子权重降低
            "growth": 0.25,     # 成长因子权重增加
            "quality": 0.15,    # 质量因子
            "momentum": 0.30,   # 动量因子权重最高
            "volatility": 0.10, # 波动因子
            "size": 0.10,       # 市值因子
        },
        "rebalance_freq": "weekly",  # 调仓频率
        "stop_loss": 0.08,           # 止损线
    },
    MarketScenario.BEAR: {
        "name": "熊市配置",
        "description": "趋势向下，侧重价值和低波动因子",
        "weights": {
            "value": 0.30,      # 价值因子权重增加
            "growth": 0.10,     # 成长因子权重降低
            "quality": 0.25,    # 质量因子权重增加
            "momentum": 0.05,   # 动量因子权重降低
            "volatility": 0.20, # 低波动因子权重增加
            "size": 0.10,       # 市值因子
        },
        "rebalance_freq": "monthly",
        "stop_loss": 0.05,
    },
    MarketScenario.SIDEWAYS: {
        "name": "震荡市配置",
        "description": "无明确趋势，侧重价值和反转因子",
        "weights": {
            "value": 0.25,      # 价值因子
            "growth": 0.15,     # 成长因子
            "quality": 0.20,    # 质量因子
            "momentum": 0.10,   # 动量因子权重降低
            "volatility": 0.15, # 波动因子
            "size": 0.15,       # 市值因子
        },
        "rebalance_freq": "biweekly",
        "stop_loss": 0.06,
    },
}


class FactorWeightOptimizer:
    """因子权重优化器"""
    
    def __init__(self):
        self._scenario_library = SCENARIO_WEIGHT_LIBRARY
    
    def grid_search(
        self,
        factor_names: List[str],
        eval_func: Callable[[Dict[str, float]], float],
        weight_range: Tuple[float, float] = (0.0, 0.5),
        step: float = 0.1,
        constraint_sum: float = 1.0
    ) -> OptimizationResult:
        """
        网格搜索优化因子权重
        
        Args:
            factor_names: 因子名称列表
            eval_func: 评估函数，输入权重字典，返回得分
            weight_range: 权重范围
            step: 步长
            constraint_sum: 权重和约束（通常为1.0）
        
        Returns:
            OptimizationResult
        """
        logger.info(f"🔍 开始网格搜索优化, {len(factor_names)} 个因子")
        start_time = datetime.now()
        
        # 生成候选权重
        min_w, max_w = weight_range
        weight_candidates = np.arange(min_w, max_w + step, step)
        
        best_weights = None
        best_score = float('-inf')
        all_results = []
        iterations = 0
        
        # 生成所有权重组合
        for weights_tuple in product(weight_candidates, repeat=len(factor_names)):
            weights = list(weights_tuple)
            
            # 归一化到约束和
            total = sum(weights)
            if total == 0:
                continue
            weights = [w / total * constraint_sum for w in weights]
            
            # 构建权重字典
            weight_dict = dict(zip(factor_names, weights))
            
            # 评估
            try:
                score = eval_func(weight_dict)
                iterations += 1
                
                all_results.append((weight_dict.copy(), score))
                
                if score > best_score:
                    best_score = score
                    best_weights = weight_dict.copy()
                    
            except Exception as e:
                logger.warning(f"评估失败: {e}")
                continue
        
        time_cost = (datetime.now() - start_time).total_seconds()
        
        result = OptimizationResult(
            best_weights=best_weights or {},
            best_performance=best_score,
            all_results=sorted(all_results, key=lambda x: x[1], reverse=True)[:20],
            optimization_method="grid_search",
            iterations=iterations,
            time_cost=time_cost
        )
        
        logger.info(f"✅ 网格搜索完成: {iterations}次迭代, 最优得分: {best_score:.4f}")
        return result
    
    def ic_weighted(
        self,
        factor_ic_dict: Dict[str, float],
        min_weight: float = 0.05,
        max_weight: float = 0.40
    ) -> Dict[str, float]:
        """
        IC加权法确定因子权重
        
        Args:
            factor_ic_dict: 因子IC字典 {因子名: IC值}
            min_weight: 最小权重
            max_weight: 最大权重
        
        Returns:
            权重字典
        """
        if not factor_ic_dict:
            return {}
        
        # 取绝对值（IC正负都有效）
        abs_ic = {k: abs(v) for k, v in factor_ic_dict.items()}
        total_ic = sum(abs_ic.values())
        
        if total_ic == 0:
            # 等权
            n = len(factor_ic_dict)
            return {k: 1.0 / n for k in factor_ic_dict}
        
        # IC加权
        weights = {}
        for factor, ic in abs_ic.items():
            w = ic / total_ic
            # 应用约束
            w = max(min_weight, min(max_weight, w))
            weights[factor] = w
        
        # 重新归一化
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}
        
        return weights
    
    def get_scenario_weights(self, scenario: MarketScenario) -> WeightConfig:
        """
        获取情景权重配置
        
        Args:
            scenario: 市场情景
        
        Returns:
            WeightConfig
        """
        config = self._scenario_library.get(scenario, self._scenario_library[MarketScenario.SIDEWAYS])
        
        return WeightConfig(
            factor_weights=config['weights'],
            scenario=scenario,
            description=config['description']
        )
    
    def get_all_scenarios(self) -> List[Dict]:
        """获取所有情景配置"""
        return [
            {
                'scenario': s.value,
                'name': config['name'],
                'description': config['description'],
                'weights': config['weights'],
                'rebalance_freq': config['rebalance_freq'],
                'stop_loss': config['stop_loss']
            }
            for s, config in self._scenario_library.items()
        ]
    
    def auto_detect_scenario(self, market_data: pd.DataFrame = None) -> MarketScenario:
        """
        自动检测当前市场情景
        
        Args:
            market_data: 市场数据（可选）
        
        Returns:
            MarketScenario
        """
        try:
            from core.trend_analyzer import get_trend_analyzer
            
            analyzer = get_trend_analyzer()
            result = analyzer.analyze()
            
            # 根据趋势信号判断情景
            signal = result.overall_signal.value
            
            if signal in ['strong_up', 'up']:
                return MarketScenario.BULL
            elif signal in ['strong_down', 'down']:
                return MarketScenario.BEAR
            else:
                return MarketScenario.SIDEWAYS
                
        except Exception as e:
            logger.warning(f"自动检测情景失败: {e}")
            return MarketScenario.UNKNOWN
    
    def recommend_weights(self) -> WeightConfig:
        """
        根据当前市场自动推荐权重
        
        Returns:
            WeightConfig
        """
        scenario = self.auto_detect_scenario()
        
        if scenario == MarketScenario.UNKNOWN:
            # 使用均衡配置
            scenario = MarketScenario.SIDEWAYS
        
        config = self.get_scenario_weights(scenario)
        logger.info(f"📊 当前市场情景: {scenario.value}, 推荐配置: {config.description}")
        
        return config


# 单例
_optimizer = None

def get_factor_weight_optimizer() -> FactorWeightOptimizer:
    global _optimizer
    if _optimizer is None:
        _optimizer = FactorWeightOptimizer()
    return _optimizer

