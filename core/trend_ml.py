# -*- coding: utf-8 -*-
"""
趋势识别机器学习模型
====================

包含：
1. 隐马尔可夫模型(HMM) - 识别市场隐藏状态
2. 简易趋势分类器 - 基于技术指标的分类
3. 市场状态预测

注：使用简化版HMM，避免复杂依赖
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MarketState(Enum):
    """市场隐藏状态"""
    BULL = "牛市"
    BEAR = "熊市"
    SIDEWAYS = "震荡"


@dataclass
class HMMResult:
    """HMM分析结果"""
    current_state: MarketState
    state_probability: Dict[str, float]  # 各状态概率
    transition_prob: Dict[str, float]    # 下一状态转移概率
    confidence: float
    history_states: List[str]            # 历史状态序列


class SimpleHMM:
    """
    简化版隐马尔可夫模型
    
    用于识别市场的三种隐藏状态：牛市、熊市、震荡
    
    观测变量：
    - 价格变化率
    - 成交量变化率
    - 波动率
    """
    
    # 状态转移概率矩阵 (基于经验)
    # 从 [Bull, Bear, Sideways] 转移到 [Bull, Bear, Sideways]
    TRANSITION_MATRIX = np.array([
        [0.85, 0.05, 0.10],  # Bull -> Bull/Bear/Sideways
        [0.05, 0.80, 0.15],  # Bear -> Bull/Bear/Sideways
        [0.20, 0.20, 0.60],  # Sideways -> Bull/Bear/Sideways
    ])
    
    # 初始状态概率
    INITIAL_PROB = np.array([0.33, 0.33, 0.34])
    
    # 观测概率参数 (均值, 标准差)
    # 基于 [price_change, volume_change, volatility]
    EMISSION_PARAMS = {
        MarketState.BULL: {
            'price_change': (0.5, 1.5),      # 正收益
            'volume_change': (0.2, 0.5),     # 放量
            'volatility': (15, 8)            # 适中波动
        },
        MarketState.BEAR: {
            'price_change': (-0.5, 1.5),     # 负收益
            'volume_change': (0.3, 0.6),     # 恐慌放量
            'volatility': (25, 10)           # 高波动
        },
        MarketState.SIDEWAYS: {
            'price_change': (0, 0.8),        # 小幅波动
            'volume_change': (-0.1, 0.3),    # 缩量
            'volatility': (12, 5)            # 低波动
        }
    }
    
    def __init__(self):
        self.states = [MarketState.BULL, MarketState.BEAR, MarketState.SIDEWAYS]
        self.n_states = len(self.states)
    
    def analyze(self, df: pd.DataFrame) -> Optional[HMMResult]:
        """
        分析市场状态
        
        Args:
            df: 包含 open, high, low, close, volume 的DataFrame
            
        Returns:
            HMM分析结果
        """
        try:
            if df is None or len(df) < 20:
                logger.warning("数据不足，无法进行HMM分析")
                return None
            
            # 计算观测变量
            observations = self._calculate_observations(df)
            
            if len(observations) == 0:
                return None
            
            # 使用Viterbi算法找最可能的状态序列
            state_sequence = self._viterbi(observations)
            
            # 计算当前状态概率
            current_probs = self._calculate_state_probabilities(observations[-1])
            
            # 计算转移概率
            current_state_idx = self.states.index(state_sequence[-1])
            transition_probs = {
                state.value: self.TRANSITION_MATRIX[current_state_idx][i]
                for i, state in enumerate(self.states)
            }
            
            # 计算置信度
            confidence = max(current_probs.values())
            
            return HMMResult(
                current_state=state_sequence[-1],
                state_probability=current_probs,
                transition_prob=transition_probs,
                confidence=confidence,
                history_states=[s.value for s in state_sequence[-20:]]
            )
            
        except Exception as e:
            logger.error(f"HMM分析失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _calculate_observations(self, df: pd.DataFrame) -> List[Dict[str, float]]:
        """计算观测变量序列"""
        observations = []
        
        # 计算收益率
        df['returns'] = df['close'].pct_change() * 100
        
        # 计算成交量变化率
        df['vol_change'] = df['volume'].pct_change()
        
        # 计算波动率 (20日)
        df['volatility'] = df['returns'].rolling(20).std() * np.sqrt(252)
        
        # 从第20天开始
        for i in range(20, len(df)):
            obs = {
                'price_change': df['returns'].iloc[i] if not pd.isna(df['returns'].iloc[i]) else 0,
                'volume_change': df['vol_change'].iloc[i] if not pd.isna(df['vol_change'].iloc[i]) else 0,
                'volatility': df['volatility'].iloc[i] if not pd.isna(df['volatility'].iloc[i]) else 15
            }
            observations.append(obs)
        
        return observations
    
    def _emission_probability(self, observation: Dict[str, float], state: MarketState) -> float:
        """计算观测概率 P(observation | state)"""
        params = self.EMISSION_PARAMS[state]
        prob = 1.0
        
        for key in ['price_change', 'volume_change', 'volatility']:
            mean, std = params[key]
            value = observation.get(key, mean)
            
            # 使用高斯分布计算概率
            z = (value - mean) / std
            p = np.exp(-0.5 * z**2) / (std * np.sqrt(2 * np.pi))
            prob *= max(p, 1e-10)  # 避免零概率
        
        return prob
    
    def _viterbi(self, observations: List[Dict[str, float]]) -> List[MarketState]:
        """Viterbi算法找最可能的状态序列"""
        T = len(observations)
        if T == 0:
            return [MarketState.SIDEWAYS]
        
        # 初始化
        V = np.zeros((T, self.n_states))
        path = np.zeros((T, self.n_states), dtype=int)
        
        # 初始状态
        for i, state in enumerate(self.states):
            V[0, i] = np.log(self.INITIAL_PROB[i] + 1e-10) + \
                      np.log(self._emission_probability(observations[0], state) + 1e-10)
        
        # 递推
        for t in range(1, T):
            for j in range(self.n_states):
                probs = V[t-1] + np.log(self.TRANSITION_MATRIX[:, j] + 1e-10)
                path[t, j] = np.argmax(probs)
                V[t, j] = probs[path[t, j]] + \
                          np.log(self._emission_probability(observations[t], self.states[j]) + 1e-10)
        
        # 回溯
        best_path = np.zeros(T, dtype=int)
        best_path[T-1] = np.argmax(V[T-1])
        
        for t in range(T-2, -1, -1):
            best_path[t] = path[t+1, best_path[t+1]]
        
        return [self.states[i] for i in best_path]
    
    def _calculate_state_probabilities(self, observation: Dict[str, float]) -> Dict[str, float]:
        """计算当前观测下各状态的后验概率"""
        probs = {}
        total = 0
        
        for state in self.states:
            p = self._emission_probability(observation, state)
            probs[state.value] = p
            total += p
        
        # 归一化
        if total > 0:
            for key in probs:
                probs[key] /= total
        
        return probs


class TrendClassifier:
    """
    趋势分类器
    
    基于技术指标的简易分类模型
    使用规则+权重的方式，无需训练
    """
    
    def __init__(self):
        # 特征权重
        self.weights = {
            'ma_cross': 0.20,        # 均线交叉
            'macd_signal': 0.18,     # MACD信号
            'rsi_level': 0.12,       # RSI水平
            'price_position': 0.15,  # 价格位置
            'volume_trend': 0.12,    # 成交量趋势
            'volatility': 0.10,      # 波动率
            'momentum': 0.13         # 动量
        }
    
    def classify(self, df: pd.DataFrame) -> Dict:
        """
        分类当前市场趋势
        
        Returns:
            包含分类结果、置信度和特征得分的字典
        """
        try:
            if df is None or len(df) < 50:
                return self._default_result()
            
            features = self._extract_features(df)
            scores = self._calculate_scores(features)
            
            # 综合得分
            total_score = sum(scores[k] * self.weights[k] for k in self.weights)
            
            # 分类
            if total_score > 60:
                trend_class = "强势上涨"
                confidence = min(total_score / 100, 0.95)
            elif total_score > 30:
                trend_class = "上涨趋势"
                confidence = 0.6 + (total_score - 30) / 100
            elif total_score > 0:
                trend_class = "弱势震荡偏多"
                confidence = 0.5 + total_score / 100
            elif total_score > -30:
                trend_class = "弱势震荡偏空"
                confidence = 0.5 - total_score / 100
            elif total_score > -60:
                trend_class = "下跌趋势"
                confidence = 0.6 + abs(total_score + 30) / 100
            else:
                trend_class = "强势下跌"
                confidence = min(abs(total_score) / 100, 0.95)
            
            return {
                'trend_class': trend_class,
                'total_score': total_score,
                'confidence': confidence,
                'feature_scores': scores,
                'features': features
            }
            
        except Exception as e:
            logger.error(f"趋势分类失败: {e}")
            return self._default_result()
    
    def _extract_features(self, df: pd.DataFrame) -> Dict:
        """提取特征"""
        close = df['close']
        volume = df['volume']
        
        # 均线
        ma5 = close.rolling(5).mean()
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()
        
        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9).mean()
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta).where(delta < 0, 0).rolling(14).mean()
        rsi = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))
        
        # 动量
        momentum = (close.iloc[-1] / close.iloc[-20] - 1) * 100
        
        # 波动率
        volatility = close.pct_change().rolling(20).std() * np.sqrt(252) * 100
        
        return {
            'ma5': ma5.iloc[-1],
            'ma20': ma20.iloc[-1],
            'ma60': ma60.iloc[-1],
            'close': close.iloc[-1],
            'macd': macd.iloc[-1],
            'macd_signal': signal.iloc[-1],
            'macd_hist': macd.iloc[-1] - signal.iloc[-1],
            'rsi': rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50,
            'momentum': momentum,
            'volatility': volatility.iloc[-1] if not pd.isna(volatility.iloc[-1]) else 20,
            'volume_ratio': volume.iloc[-1] / volume.rolling(20).mean().iloc[-1]
        }
    
    def _calculate_scores(self, features: Dict) -> Dict:
        """计算各特征得分"""
        scores = {}
        
        # 均线交叉
        if features['close'] > features['ma5'] > features['ma20'] > features['ma60']:
            scores['ma_cross'] = 100
        elif features['close'] > features['ma5'] > features['ma20']:
            scores['ma_cross'] = 60
        elif features['close'] > features['ma20']:
            scores['ma_cross'] = 30
        elif features['close'] < features['ma5'] < features['ma20'] < features['ma60']:
            scores['ma_cross'] = -100
        elif features['close'] < features['ma5'] < features['ma20']:
            scores['ma_cross'] = -60
        else:
            scores['ma_cross'] = 0
        
        # MACD信号
        if features['macd_hist'] > 0 and features['macd'] > 0:
            scores['macd_signal'] = 80
        elif features['macd_hist'] > 0:
            scores['macd_signal'] = 40
        elif features['macd_hist'] < 0 and features['macd'] < 0:
            scores['macd_signal'] = -80
        elif features['macd_hist'] < 0:
            scores['macd_signal'] = -40
        else:
            scores['macd_signal'] = 0
        
        # RSI水平
        rsi = features['rsi']
        if rsi > 70:
            scores['rsi_level'] = 50  # 超买但仍强势
        elif rsi > 50:
            scores['rsi_level'] = (rsi - 50) * 2
        elif rsi > 30:
            scores['rsi_level'] = (rsi - 50) * 2
        else:
            scores['rsi_level'] = -50  # 超卖
        
        # 价格位置
        price_pos = (features['close'] - features['ma60']) / features['ma60'] * 100
        scores['price_position'] = np.clip(price_pos * 5, -100, 100)
        
        # 成交量趋势
        vol_ratio = features['volume_ratio']
        if vol_ratio > 1.5:
            scores['volume_trend'] = 50 if features['momentum'] > 0 else -50
        elif vol_ratio > 1:
            scores['volume_trend'] = 20 if features['momentum'] > 0 else -20
        else:
            scores['volume_trend'] = -20 if features['momentum'] > 0 else 20
        
        # 波动率
        vol = features['volatility']
        if vol > 30:
            scores['volatility'] = -30  # 高波动不稳定
        elif vol < 15:
            scores['volatility'] = 30   # 低波动稳定
        else:
            scores['volatility'] = 0
        
        # 动量
        scores['momentum'] = np.clip(features['momentum'] * 5, -100, 100)
        
        return scores
    
    def _default_result(self) -> Dict:
        """默认结果"""
        return {
            'trend_class': "数据不足",
            'total_score': 0,
            'confidence': 0,
            'feature_scores': {},
            'features': {}
        }


def create_hmm_analyzer() -> SimpleHMM:
    """创建HMM分析器"""
    return SimpleHMM()


def create_trend_classifier() -> TrendClassifier:
    """创建趋势分类器"""
    return TrendClassifier()

