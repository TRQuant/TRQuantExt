# -*- coding: utf-8 -*-
"""
趋势-因子联动模块
==================

根据市场趋势动态调整因子权重：
1. 牛市：提高动量、成长因子权重
2. 熊市：提高价值、低波动因子权重
3. 震荡市：均衡配置

遵循TIME_DIMENSION_PRINCIPLES.md的设计原则
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """市场状态"""
    STRONG_BULL = "strong_bull"     # 强势牛市
    BULL = "bull"                   # 牛市
    WEAK_BULL = "weak_bull"         # 弱势上涨
    SIDEWAYS = "sideways"           # 震荡
    WEAK_BEAR = "weak_bear"         # 弱势下跌
    BEAR = "bear"                   # 熊市
    STRONG_BEAR = "strong_bear"     # 强势熊市
    RECOVERY = "recovery"           # 复苏
    
    @classmethod
    def from_score(cls, score: float) -> 'MarketRegime':
        """根据趋势得分判断市场状态"""
        if score >= 60:
            return cls.STRONG_BULL
        elif score >= 30:
            return cls.BULL
        elif score >= 10:
            return cls.WEAK_BULL
        elif score >= -10:
            return cls.SIDEWAYS
        elif score >= -30:
            return cls.WEAK_BEAR
        elif score >= -60:
            return cls.BEAR
        else:
            return cls.STRONG_BEAR


@dataclass
class FactorWeightProfile:
    """因子权重配置"""
    momentum: float = 0.15
    growth: float = 0.15
    value: float = 0.15
    quality: float = 0.15
    flow: float = 0.10
    volatility: float = 0.10
    size: float = 0.10
    liquidity: float = 0.10
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "momentum": self.momentum,
            "growth": self.growth,
            "value": self.value,
            "quality": self.quality,
            "flow": self.flow,
            "volatility": self.volatility,
            "size": self.size,
            "liquidity": self.liquidity
        }
    
    def normalize(self) -> 'FactorWeightProfile':
        """归一化权重"""
        total = sum(self.to_dict().values())
        if total == 0:
            return self
        
        return FactorWeightProfile(
            momentum=self.momentum / total,
            growth=self.growth / total,
            value=self.value / total,
            quality=self.quality / total,
            flow=self.flow / total,
            volatility=self.volatility / total,
            size=self.size / total,
            liquidity=self.liquidity / total
        )


# 预定义的权重配置
WEIGHT_PROFILES: Dict[MarketRegime, FactorWeightProfile] = {
    MarketRegime.STRONG_BULL: FactorWeightProfile(
        momentum=0.30, growth=0.25, value=0.05, quality=0.10,
        flow=0.15, volatility=0.05, size=0.05, liquidity=0.05
    ),
    MarketRegime.BULL: FactorWeightProfile(
        momentum=0.25, growth=0.20, value=0.10, quality=0.15,
        flow=0.15, volatility=0.05, size=0.05, liquidity=0.05
    ),
    MarketRegime.WEAK_BULL: FactorWeightProfile(
        momentum=0.20, growth=0.15, value=0.15, quality=0.15,
        flow=0.15, volatility=0.10, size=0.05, liquidity=0.05
    ),
    MarketRegime.SIDEWAYS: FactorWeightProfile(
        momentum=0.10, growth=0.15, value=0.20, quality=0.20,
        flow=0.10, volatility=0.10, size=0.05, liquidity=0.10
    ),
    MarketRegime.WEAK_BEAR: FactorWeightProfile(
        momentum=0.05, growth=0.10, value=0.25, quality=0.20,
        flow=0.10, volatility=0.15, size=0.05, liquidity=0.10
    ),
    MarketRegime.BEAR: FactorWeightProfile(
        momentum=0.05, growth=0.05, value=0.30, quality=0.25,
        flow=0.05, volatility=0.15, size=0.05, liquidity=0.10
    ),
    MarketRegime.STRONG_BEAR: FactorWeightProfile(
        momentum=0.00, growth=0.05, value=0.35, quality=0.25,
        flow=0.05, volatility=0.20, size=0.00, liquidity=0.10
    ),
    MarketRegime.RECOVERY: FactorWeightProfile(
        momentum=0.20, growth=0.20, value=0.15, quality=0.15,
        flow=0.15, volatility=0.05, size=0.05, liquidity=0.05
    ),
}

# 投资周期对应的基础权重调整
PERIOD_ADJUSTMENTS = {
    "short": {  # 短期侧重动量和资金流
        "momentum": 1.5,
        "flow": 1.3,
        "growth": 0.7,
        "value": 0.5,
    },
    "medium": {  # 中期均衡
        "momentum": 1.0,
        "flow": 1.0,
        "growth": 1.0,
        "value": 1.0,
    },
    "long": {  # 长期侧重价值和成长
        "momentum": 0.5,
        "flow": 0.7,
        "growth": 1.5,
        "value": 1.5,
        "quality": 1.3,
    }
}


class TrendFactorLinker:
    """趋势-因子联动器"""
    
    def __init__(self):
        self._current_regime: Optional[MarketRegime] = None
        self._current_weights: Optional[FactorWeightProfile] = None
        self._trend_score: float = 0
        self._callbacks = []
    
    def register_weight_change_callback(self, callback):
        """注册权重变更回调"""
        self._callbacks.append(callback)
    
    def update_from_trend(self, trend_result: Dict) -> FactorWeightProfile:
        """
        根据趋势分析结果更新因子权重
        
        Args:
            trend_result: 趋势分析结果（来自TrendAnalyzer）
            
        Returns:
            更新后的因子权重配置
        """
        try:
            # 提取综合得分
            composite_score = trend_result.get('composite_score', 0)
            market_phase = trend_result.get('market_phase', '')
            
            self._trend_score = composite_score
            
            # 判断市场状态
            regime = self._determine_regime(composite_score, market_phase)
            
            if regime != self._current_regime:
                logger.info(f"市场状态变化: {self._current_regime} -> {regime}")
                self._current_regime = regime
            
            # 获取对应的权重配置
            weights = WEIGHT_PROFILES.get(regime, FactorWeightProfile())
            self._current_weights = weights.normalize()
            
            # 触发回调
            for callback in self._callbacks:
                try:
                    callback(self._current_weights, regime)
                except Exception as e:
                    logger.error(f"权重变更回调失败: {e}")
            
            logger.info(f"因子权重已更新: 市场状态={regime.value}, 动量={weights.momentum:.2f}, 价值={weights.value:.2f}")
            
            return self._current_weights
            
        except Exception as e:
            logger.error(f"趋势-因子联动失败: {e}")
            return FactorWeightProfile()
    
    def get_adjusted_weights(
        self,
        period: str = "medium",
        custom_adjustments: Dict[str, float] = None
    ) -> Dict[str, float]:
        """
        获取经过周期和自定义调整后的权重
        
        Args:
            period: 投资周期 (short/medium/long)
            custom_adjustments: 自定义调整系数
            
        Returns:
            调整后的权重字典
        """
        if self._current_weights is None:
            # 使用默认权重
            weights = FactorWeightProfile()
        else:
            weights = self._current_weights
        
        weights_dict = weights.to_dict()
        
        # 应用周期调整
        period_adj = PERIOD_ADJUSTMENTS.get(period, {})
        for factor, adj in period_adj.items():
            if factor in weights_dict:
                weights_dict[factor] *= adj
        
        # 应用自定义调整
        if custom_adjustments:
            for factor, adj in custom_adjustments.items():
                if factor in weights_dict:
                    weights_dict[factor] *= adj
        
        # 归一化
        total = sum(weights_dict.values())
        if total > 0:
            weights_dict = {k: v / total for k, v in weights_dict.items()}
        
        return weights_dict
    
    def get_recommended_factors(self, top_n: int = 5) -> List[Tuple[str, float]]:
        """
        获取当前市场状态下推荐的因子
        
        Returns:
            (因子名, 权重) 列表，按权重降序排列
        """
        if self._current_weights is None:
            return []
        
        weights = self._current_weights.to_dict()
        sorted_factors = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        
        return sorted_factors[:top_n]
    
    def get_avoided_factors(self, threshold: float = 0.08) -> List[str]:
        """
        获取当前市场状态下应避免的因子
        
        Returns:
            权重低于阈值的因子列表
        """
        if self._current_weights is None:
            return []
        
        weights = self._current_weights.to_dict()
        return [k for k, v in weights.items() if v < threshold]
    
    def _determine_regime(self, score: float, phase: str) -> MarketRegime:
        """确定市场状态"""
        # 首先根据得分判断
        regime = MarketRegime.from_score(score)
        
        # 根据阶段进行调整
        if "复苏" in phase or "反弹" in phase:
            regime = MarketRegime.RECOVERY
        elif "牛市加速" in phase:
            regime = MarketRegime.STRONG_BULL
        elif "熊市加速" in phase:
            regime = MarketRegime.STRONG_BEAR
        
        return regime
    
    @property
    def current_regime(self) -> Optional[MarketRegime]:
        return self._current_regime
    
    @property
    def trend_score(self) -> float:
        return self._trend_score
    
    def get_regime_description(self) -> str:
        """获取当前市场状态描述"""
        if self._current_regime is None:
            return "未知"
        
        descriptions = {
            MarketRegime.STRONG_BULL: "强势牛市 - 积极进攻，侧重动量和成长",
            MarketRegime.BULL: "牛市 - 稳健持仓，动量为主",
            MarketRegime.WEAK_BULL: "弱势上涨 - 谨慎操作，均衡配置",
            MarketRegime.SIDEWAYS: "震荡盘整 - 防御为主，价值+质量",
            MarketRegime.WEAK_BEAR: "弱势下跌 - 控制仓位，避免动量",
            MarketRegime.BEAR: "熊市 - 低仓观望，价值+低波动",
            MarketRegime.STRONG_BEAR: "强势熊市 - 空仓保护，现金为王",
            MarketRegime.RECOVERY: "复苏期 - 逐步加仓，布局成长"
        }
        
        return descriptions.get(self._current_regime, "未知状态")


# 全局单例
_linker_instance: Optional[TrendFactorLinker] = None


def get_trend_factor_linker() -> TrendFactorLinker:
    """获取趋势-因子联动器单例"""
    global _linker_instance
    if _linker_instance is None:
        _linker_instance = TrendFactorLinker()
    return _linker_instance


def create_trend_factor_linker() -> TrendFactorLinker:
    """创建新的趋势-因子联动器"""
    return TrendFactorLinker()

