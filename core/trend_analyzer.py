# -*- coding: utf-8 -*-
"""
市场趋势识别引擎
================

综合技术分析与机器学习手段，识别市场短期、中期、长期趋势状态。

功能：
1. 技术指标融合（均线、MACD、KDJ、ADX、布林带）
2. 多周期趋势分析（短期1-8周、中期9-24周、长期25-48周）
3. 趋势强度评分（-100至+100）
4. 与策略系统联动

参考：IBD Market Pulse、贝莱德宏观分析框架
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TrendDirection(Enum):
    """趋势方向"""
    STRONG_UP = "强势上涨"
    UP = "上涨趋势"
    WEAK_UP = "弱势上涨"
    SIDEWAYS = "震荡盘整"
    WEAK_DOWN = "弱势下跌"
    DOWN = "下跌趋势"
    STRONG_DOWN = "强势下跌"


class TrendPeriod(Enum):
    """趋势周期"""
    SHORT = "short"      # 1-8周
    MEDIUM = "medium"    # 9-24周
    LONG = "long"        # 25-48周


@dataclass
class TrendSignal:
    """趋势信号"""
    period: TrendPeriod
    direction: TrendDirection
    score: float          # -100 到 +100
    confidence: float     # 0 到 1
    indicators: Dict[str, float] = field(default_factory=dict)
    description: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def color(self) -> str:
        """根据趋势方向返回颜色"""
        if self.score > 50:
            return "#00C853"  # 强势上涨 - 绿色
        elif self.score > 20:
            return "#4CAF50"  # 上涨趋势 - 浅绿
        elif self.score > 0:
            return "#8BC34A"  # 弱势上涨 - 黄绿
        elif self.score > -20:
            return "#FFC107"  # 震荡 - 黄色
        elif self.score > -50:
            return "#FF9800"  # 弱势下跌 - 橙色
        else:
            return "#F44336"  # 下跌趋势 - 红色
    
    @property
    def position_suggestion(self) -> str:
        """仓位建议"""
        if self.score > 60:
            return "80-100%"
        elif self.score > 30:
            return "50-80%"
        elif self.score > 0:
            return "30-50%"
        elif self.score > -30:
            return "10-30%"
        else:
            return "0-10%"


@dataclass
class MarketTrendResult:
    """市场趋势分析结果"""
    short_term: TrendSignal
    medium_term: TrendSignal
    long_term: TrendSignal
    composite_score: float
    market_phase: str  # 牛市/熊市/震荡/复苏
    analysis_date: datetime
    index_code: str = "000001.XSHG"
    resonance: Dict = field(default_factory=dict)  # 多周期共振信息
    
    @property
    def overall_direction(self) -> TrendDirection:
        """综合趋势方向"""
        avg_score = (self.short_term.score * 0.2 + 
                     self.medium_term.score * 0.3 + 
                     self.long_term.score * 0.5)
        
        if avg_score > 50:
            return TrendDirection.STRONG_UP
        elif avg_score > 20:
            return TrendDirection.UP
        elif avg_score > 0:
            return TrendDirection.WEAK_UP
        elif avg_score > -20:
            return TrendDirection.SIDEWAYS
        elif avg_score > -50:
            return TrendDirection.WEAK_DOWN
        else:
            return TrendDirection.DOWN
    
    def to_dict(self) -> Dict:
        """转换为字典（包含完整指标详情）"""
        return {
            "short_term": {
                "direction": self.short_term.direction.value,
                "score": self.short_term.score,
                "confidence": self.short_term.confidence,
                "color": self.short_term.color,
                "position": self.short_term.position_suggestion,
                "indicators": self.short_term.indicators,
                "description": self.short_term.description
            },
            "medium_term": {
                "direction": self.medium_term.direction.value,
                "score": self.medium_term.score,
                "confidence": self.medium_term.confidence,
                "color": self.medium_term.color,
                "position": self.medium_term.position_suggestion,
                "indicators": self.medium_term.indicators,
                "description": self.medium_term.description
            },
            "long_term": {
                "direction": self.long_term.direction.value,
                "score": self.long_term.score,
                "confidence": self.long_term.confidence,
                "color": self.long_term.color,
                "position": self.long_term.position_suggestion,
                "indicators": self.long_term.indicators,
                "description": self.long_term.description
            },
            "composite_score": self.composite_score,
            "market_phase": self.market_phase,
            "overall_direction": self.overall_direction.value,
            "analysis_date": self.analysis_date.isoformat(),
            "resonance": self.resonance
        }


class TrendAnalyzer:
    """
    市场趋势分析引擎
    
    融合技术指标和机器学习方法识别市场趋势
    """
    
    # 周期配置（交易日）
    PERIOD_CONFIG = {
        TrendPeriod.SHORT: {
            "name": "短期趋势(1-8周)",
            "days": 40,      # 约8周交易日
            "ma_fast": 5,
            "ma_slow": 20,
            "macd_fast": 8,
            "macd_slow": 17,
            "macd_signal": 9,
            "rsi_period": 6,
            "weight": 0.2
        },
        TrendPeriod.MEDIUM: {
            "name": "中期趋势(9-24周)",
            "days": 120,     # 约24周交易日
            "ma_fast": 20,
            "ma_slow": 60,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "rsi_period": 14,
            "weight": 0.3
        },
        TrendPeriod.LONG: {
            "name": "长期趋势(25-48周)",
            "days": 240,     # 约48周交易日
            "ma_fast": 60,
            "ma_slow": 250,
            "macd_fast": 26,
            "macd_slow": 52,
            "macd_signal": 9,
            "rsi_period": 21,
            "weight": 0.5
        }
    }
    
    def __init__(self, jq_client=None):
        """
        初始化
        
        Args:
            jq_client: JQData客户端
        """
        self.jq_client = jq_client
        self._cache = {}
    
    def analyze_market(
        self,
        index_code: str = "000001.XSHG",
        date: Optional[str] = None
    ) -> Optional[MarketTrendResult]:
        """
        分析市场趋势
        
        Args:
            index_code: 指数代码（默认上证指数）
            date: 分析日期
            
        Returns:
            MarketTrendResult: 趋势分析结果
        """
        try:
            # 获取价格数据
            df = self._get_price_data(index_code, date, days=300)
            if df is None or df.empty:
                logger.warning(f"无法获取{index_code}的价格数据")
                return None
            
            # 分析各周期趋势
            short_signal = self._analyze_period(df, TrendPeriod.SHORT)
            medium_signal = self._analyze_period(df, TrendPeriod.MEDIUM)
            long_signal = self._analyze_period(df, TrendPeriod.LONG)
            
            # 计算综合得分
            composite = (
                short_signal.score * self.PERIOD_CONFIG[TrendPeriod.SHORT]["weight"] +
                medium_signal.score * self.PERIOD_CONFIG[TrendPeriod.MEDIUM]["weight"] +
                long_signal.score * self.PERIOD_CONFIG[TrendPeriod.LONG]["weight"]
            )
            
            # 计算共振信息
            resonance = self._calculate_resonance(short_signal, medium_signal, long_signal)
            
            # 判断市场阶段
            market_phase = self._determine_market_phase(short_signal, medium_signal, long_signal)
            
            result = MarketTrendResult(
                short_term=short_signal,
                medium_term=medium_signal,
                long_term=long_signal,
                composite_score=composite,
                market_phase=market_phase,
                analysis_date=datetime.now(),
                index_code=index_code,
                resonance=resonance
            )
            
            logger.info(f"市场趋势分析完成: {index_code}, 综合得分={composite:.1f}, 阶段={market_phase}")
            return result
            
        except Exception as e:
            logger.error(f"市场趋势分析失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_price_data(
        self,
        code: str,
        date: Optional[str],
        days: int = 300
    ) -> Optional[pd.DataFrame]:
        """获取价格数据"""
        try:
            import jqdatasdk as jq
            
            # 确保已认证
            if not jq.is_auth():
                self._auto_auth_jq()
            
            # 确定结束日期
            if date:
                end_date = date
            elif self.jq_client:
                perm = self.jq_client.get_permission()
                end_date = perm.end_date if perm else "2025-08-29"
            else:
                end_date = "2025-08-29"
            
            # 获取数据
            df = jq.get_price(
                code,
                end_date=end_date,
                count=days,
                frequency='daily',
                fields=['open', 'high', 'low', 'close', 'volume']
            )
            
            if df is not None and not df.empty:
                df = df.reset_index()
                if 'index' in df.columns:
                    df = df.rename(columns={'index': 'date'})
                return df
            
            return None
            
        except Exception as e:
            logger.error(f"获取价格数据失败: {e}")
            return None
    
    def _auto_auth_jq(self):
        """自动认证JQData"""
        try:
            import jqdatasdk as jq
            from config.config_manager import get_config_manager
            
            config = get_config_manager()
            # get_config('jqdata') -> jqdata_config.json
            jq_config = config.get_config('jqdata')
            if jq_config:
                jq.auth(jq_config.get('username'), jq_config.get('password'))
                logger.info("TrendAnalyzer: JQData自动认证成功")
        except Exception as e:
            logger.warning(f"JQData自动认证失败: {e}")
    
    def _analyze_period(self, df: pd.DataFrame, period: TrendPeriod) -> TrendSignal:
        """分析特定周期的趋势"""
        config = self.PERIOD_CONFIG[period]
        
        # 只取该周期需要的数据
        period_df = df.tail(config["days"]).copy()
        
        # 计算技术指标
        indicators = {}
        
        # 1. 均线系统
        ma_score, ma_indicators = self._calc_ma_score(period_df, config)
        indicators.update(ma_indicators)
        
        # 2. MACD
        macd_score, macd_indicators = self._calc_macd_score(period_df, config)
        indicators.update(macd_indicators)
        
        # 3. RSI
        rsi_score, rsi_indicators = self._calc_rsi_score(period_df, config)
        indicators.update(rsi_indicators)
        
        # 4. 布林带
        bb_score, bb_indicators = self._calc_bollinger_score(period_df)
        indicators.update(bb_indicators)
        
        # 5. 成交量趋势
        vol_score, vol_indicators = self._calc_volume_score(period_df)
        indicators.update(vol_indicators)
        
        # 6. KDJ指标
        kdj_score, kdj_indicators = self._calc_kdj_score(period_df, config)
        indicators.update(kdj_indicators)
        
        # 7. ADX趋势强度
        adx_score, adx_indicators = self._calc_adx_score(period_df)
        indicators.update(adx_indicators)
        
        # 8. 资金流向（北向资金等）
        flow_score, flow_indicators = self._calc_capital_flow_score(period_df)
        indicators.update(flow_indicators)
        
        # 综合评分（加权平均）- 8指标体系
        weights = {
            "ma": 0.20,      # 均线系统
            "macd": 0.18,    # MACD动能
            "rsi": 0.10,     # RSI超买超卖
            "bb": 0.10,      # 布林带
            "vol": 0.12,     # 成交量
            "kdj": 0.10,     # KDJ随机指标
            "adx": 0.10,     # ADX趋势强度
            "flow": 0.10     # 资金流向
        }
        total_score = (
            ma_score * weights["ma"] +
            macd_score * weights["macd"] +
            rsi_score * weights["rsi"] +
            bb_score * weights["bb"] +
            vol_score * weights["vol"] +
            kdj_score * weights["kdj"] +
            adx_score * weights["adx"] +
            flow_score * weights["flow"]
        )
        
        # 计算置信度（指标一致性）
        scores = [ma_score, macd_score, rsi_score, bb_score, vol_score, kdj_score, adx_score, flow_score]
        confidence = 1 - (np.std(scores) / 100)
        confidence = max(0, min(1, confidence))
        
        # 确定趋势方向
        direction = self._score_to_direction(total_score)
        
        # 生成描述
        description = self._generate_description(period, indicators, total_score)
        
        return TrendSignal(
            period=period,
            direction=direction,
            score=total_score,
            confidence=confidence,
            indicators=indicators,
            description=description
        )
    
    def _calc_ma_score(self, df: pd.DataFrame, config: Dict) -> Tuple[float, Dict]:
        """计算均线系统得分"""
        close = df['close']
        
        ma_fast = close.rolling(config["ma_fast"]).mean()
        ma_slow = close.rolling(config["ma_slow"]).mean()
        
        # 当前价格位置
        current_close = close.iloc[-1]
        current_ma_fast = ma_fast.iloc[-1]
        current_ma_slow = ma_slow.iloc[-1]
        
        score = 0
        
        # 价格在均线上方
        if current_close > current_ma_fast:
            score += 25
        else:
            score -= 25
            
        if current_close > current_ma_slow:
            score += 25
        else:
            score -= 25
        
        # 均线多头排列
        if current_ma_fast > current_ma_slow:
            score += 30
        else:
            score -= 30
        
        # 均线趋势（斜率）
        ma_fast_slope = (ma_fast.iloc[-1] - ma_fast.iloc[-5]) / ma_fast.iloc[-5] * 100 if ma_fast.iloc[-5] > 0 else 0
        ma_slow_slope = (ma_slow.iloc[-1] - ma_slow.iloc[-10]) / ma_slow.iloc[-10] * 100 if ma_slow.iloc[-10] > 0 else 0
        
        score += np.clip(ma_fast_slope * 5, -20, 20)
        
        indicators = {
            "ma_fast": current_ma_fast,
            "ma_slow": current_ma_slow,
            "ma_fast_slope": ma_fast_slope,
            "price_vs_ma_fast": (current_close / current_ma_fast - 1) * 100 if current_ma_fast > 0 else 0,
            "price_vs_ma_slow": (current_close / current_ma_slow - 1) * 100 if current_ma_slow > 0 else 0
        }
        
        return np.clip(score, -100, 100), indicators
    
    def _calc_macd_score(self, df: pd.DataFrame, config: Dict) -> Tuple[float, Dict]:
        """计算MACD得分"""
        close = df['close']
        
        # 计算MACD
        ema_fast = close.ewm(span=config["macd_fast"], adjust=False).mean()
        ema_slow = close.ewm(span=config["macd_slow"], adjust=False).mean()
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=config["macd_signal"], adjust=False).mean()
        histogram = macd - signal
        
        current_macd = macd.iloc[-1]
        current_signal = signal.iloc[-1]
        current_hist = histogram.iloc[-1]
        prev_hist = histogram.iloc[-2]
        
        score = 0
        
        # MACD柱状图方向
        if current_hist > 0:
            score += 30
        else:
            score -= 30
        
        # 柱状图趋势
        if current_hist > prev_hist:
            score += 20
        else:
            score -= 20
        
        # 金叉/死叉
        if current_macd > current_signal:
            score += 25
        else:
            score -= 25
        
        # MACD零轴位置
        if current_macd > 0:
            score += 25
        else:
            score -= 25
        
        indicators = {
            "macd": current_macd,
            "macd_signal": current_signal,
            "macd_histogram": current_hist,
            "macd_hist_change": current_hist - prev_hist
        }
        
        return np.clip(score, -100, 100), indicators
    
    def _calc_rsi_score(self, df: pd.DataFrame, config: Dict) -> Tuple[float, Dict]:
        """计算RSI得分"""
        close = df['close']
        delta = close.diff()
        
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = gain.rolling(config["rsi_period"]).mean()
        avg_loss = loss.rolling(config["rsi_period"]).mean()
        
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        
        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-5]
        
        score = 0
        
        # RSI位置
        if current_rsi > 70:
            score += 10  # 超买但仍强势
        elif current_rsi > 50:
            score += 30
        elif current_rsi > 30:
            score -= 30
        else:
            score -= 10  # 超卖可能反弹
        
        # RSI趋势
        if current_rsi > prev_rsi:
            score += 20
        else:
            score -= 20
        
        # 极端值调整
        if current_rsi > 80:
            score -= 20  # 过热警告
        elif current_rsi < 20:
            score += 20  # 超跌反弹预期
        
        indicators = {
            "rsi": current_rsi,
            "rsi_change": current_rsi - prev_rsi
        }
        
        return np.clip(score, -100, 100), indicators
    
    def _calc_bollinger_score(self, df: pd.DataFrame, period: int = 20) -> Tuple[float, Dict]:
        """计算布林带得分"""
        close = df['close']
        
        ma = close.rolling(period).mean()
        std = close.rolling(period).std()
        
        upper = ma + 2 * std
        lower = ma - 2 * std
        
        current_close = close.iloc[-1]
        current_upper = upper.iloc[-1]
        current_lower = lower.iloc[-1]
        current_ma = ma.iloc[-1]
        
        # 计算位置百分比 (0-100)
        bb_position = (current_close - current_lower) / (current_upper - current_lower) * 100 if (current_upper - current_lower) > 0 else 50
        
        score = 0
        
        # 位置评分
        if bb_position > 80:
            score += 40  # 强势上轨
        elif bb_position > 50:
            score += 20  # 中上
        elif bb_position > 20:
            score -= 20  # 中下
        else:
            score -= 40  # 弱势下轨
        
        # 带宽变化（趋势强度）
        bb_width = (current_upper - current_lower) / current_ma * 100 if current_ma > 0 else 0
        prev_width = ((upper.iloc[-5] - lower.iloc[-5]) / ma.iloc[-5] * 100) if ma.iloc[-5] > 0 else 0
        
        if bb_width > prev_width:
            score += 10  # 波动扩大，趋势加强
        else:
            score -= 10  # 波动收窄
        
        indicators = {
            "bb_upper": current_upper,
            "bb_lower": current_lower,
            "bb_middle": current_ma,
            "bb_position": bb_position,
            "bb_width": bb_width
        }
        
        return np.clip(score, -100, 100), indicators
    
    def _calc_volume_score(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """计算成交量趋势得分"""
        volume = df['volume']
        close = df['close']
        
        # 量能均线
        vol_ma5 = volume.rolling(5).mean()
        vol_ma20 = volume.rolling(20).mean()
        
        current_vol = volume.iloc[-1]
        current_vol_ma5 = vol_ma5.iloc[-1]
        current_vol_ma20 = vol_ma20.iloc[-1]
        
        # 价格变化
        price_change = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] * 100 if close.iloc[-5] > 0 else 0
        
        score = 0
        
        # 量价配合
        if price_change > 0 and current_vol > current_vol_ma5:
            score += 40  # 放量上涨
        elif price_change > 0 and current_vol < current_vol_ma5:
            score += 10  # 缩量上涨
        elif price_change < 0 and current_vol > current_vol_ma5:
            score -= 40  # 放量下跌
        else:
            score -= 10  # 缩量下跌
        
        # 量能趋势
        if current_vol_ma5 > current_vol_ma20:
            score += 20
        else:
            score -= 20
        
        indicators = {
            "volume": current_vol,
            "volume_ma5": current_vol_ma5,
            "volume_ma20": current_vol_ma20,
            "volume_ratio": current_vol / current_vol_ma5 if current_vol_ma5 > 0 else 1
        }
        
        return np.clip(score, -100, 100), indicators
    
    def _calc_kdj_score(self, df: pd.DataFrame, config: Dict) -> Tuple[float, Dict]:
        """
        计算KDJ随机指标得分
        
        KDJ指标用于捕捉短线拐点和超买超卖状态
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # KDJ参数
        n = 9  # RSV周期
        m1 = 3  # K平滑
        m2 = 3  # D平滑
        
        # 计算RSV
        lowest_low = low.rolling(n).min()
        highest_high = high.rolling(n).max()
        rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
        rsv = rsv.fillna(50)
        
        # 计算K、D、J
        k = rsv.ewm(span=m1, adjust=False).mean()
        d = k.ewm(span=m2, adjust=False).mean()
        j = 3 * k - 2 * d
        
        current_k = k.iloc[-1]
        current_d = d.iloc[-1]
        current_j = j.iloc[-1]
        prev_k = k.iloc[-2]
        prev_d = d.iloc[-2]
        
        score = 0
        
        # K、D位置评分
        if current_k > 80:
            score -= 20  # 超买区
        elif current_k > 50:
            score += 30  # 强势区
        elif current_k > 20:
            score -= 30  # 弱势区
        else:
            score += 20  # 超卖区（可能反弹）
        
        # 金叉/死叉
        if current_k > current_d and prev_k <= prev_d:
            score += 30  # K上穿D，金叉
        elif current_k < current_d and prev_k >= prev_d:
            score -= 30  # K下穿D，死叉
        elif current_k > current_d:
            score += 15  # K在D上方
        else:
            score -= 15  # K在D下方
        
        # J值极端预警
        if current_j > 100:
            score -= 10  # J超买
        elif current_j < 0:
            score += 10  # J超卖
        
        indicators = {
            "kdj_k": current_k,
            "kdj_d": current_d,
            "kdj_j": current_j,
            "kdj_golden_cross": current_k > current_d and prev_k <= prev_d,
            "kdj_death_cross": current_k < current_d and prev_k >= prev_d
        }
        
        return np.clip(score, -100, 100), indicators
    
    def _calc_adx_score(self, df: pd.DataFrame, period: int = 14) -> Tuple[float, Dict]:
        """
        计算ADX趋势强度得分
        
        ADX用于量化趋势强度，不判断方向
        +DI/-DI用于判断方向
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # 计算True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        # 计算+DM和-DM
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        
        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0)
        
        # 计算+DI和-DI
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
        
        # 计算DX和ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(period).mean()
        
        current_adx = adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 20
        current_plus_di = plus_di.iloc[-1] if not pd.isna(plus_di.iloc[-1]) else 25
        current_minus_di = minus_di.iloc[-1] if not pd.isna(minus_di.iloc[-1]) else 25
        prev_adx = adx.iloc[-5] if not pd.isna(adx.iloc[-5]) else 20
        
        score = 0
        
        # ADX趋势强度
        if current_adx > 40:
            # 强趋势
            if current_plus_di > current_minus_di:
                score += 40  # 强上涨趋势
            else:
                score -= 40  # 强下跌趋势
        elif current_adx > 25:
            # 中等趋势
            if current_plus_di > current_minus_di:
                score += 25
            else:
                score -= 25
        else:
            # 弱趋势/震荡
            score += 0  # 无明确方向
        
        # ADX趋势变化
        if current_adx > prev_adx:
            score += 10  # 趋势加强
        else:
            score -= 10  # 趋势减弱
        
        # +DI/-DI方向
        if current_plus_di > current_minus_di:
            score += 20
        else:
            score -= 20
        
        indicators = {
            "adx": current_adx,
            "plus_di": current_plus_di,
            "minus_di": current_minus_di,
            "adx_trend": "强趋势" if current_adx > 40 else ("中等趋势" if current_adx > 25 else "震荡"),
            "adx_direction": "多头" if current_plus_di > current_minus_di else "空头"
        }
        
        return np.clip(score, -100, 100), indicators
    
    def _calc_capital_flow_score(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """
        计算资金流向得分
        
        包括：
        1. 北向资金流向（通过AKShare获取）
        2. 主力资金流向
        3. 大单资金流
        
        注：当前使用价量替代，后续可接入实际资金流数据
        """
        close = df['close']
        volume = df['volume']
        high = df['high']
        low = df['low']
        
        # 使用OBV替代（能量潮）
        obv = (volume * np.sign(close.diff())).cumsum()
        obv_ma5 = obv.rolling(5).mean()
        obv_ma20 = obv.rolling(20).mean()
        
        # 资金流量指标MFI
        typical_price = (high + low + close) / 3
        money_flow = typical_price * volume
        
        positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
        negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)
        
        positive_mf = positive_flow.rolling(14).sum()
        negative_mf = negative_flow.rolling(14).sum()
        
        mfi = 100 - (100 / (1 + positive_mf / negative_mf.replace(0, np.nan)))
        current_mfi = mfi.iloc[-1] if not pd.isna(mfi.iloc[-1]) else 50
        
        score = 0
        
        # OBV趋势
        if obv_ma5.iloc[-1] > obv_ma20.iloc[-1]:
            score += 30  # 资金流入趋势
        else:
            score -= 30  # 资金流出趋势
        
        # MFI超买超卖
        if current_mfi > 80:
            score += 10  # 资金过热
        elif current_mfi > 50:
            score += 25  # 资金流入
        elif current_mfi > 20:
            score -= 25  # 资金流出
        else:
            score -= 10  # 资金枯竭
        
        # 大单资金模拟（高量能日）
        vol_ratio = volume / volume.rolling(20).mean()
        big_volume_days = (vol_ratio > 2).rolling(5).sum().iloc[-1]
        
        if big_volume_days >= 2 and close.iloc[-1] > close.iloc[-5]:
            score += 20  # 放量上涨，主力介入
        elif big_volume_days >= 2 and close.iloc[-1] < close.iloc[-5]:
            score -= 20  # 放量下跌，主力出货
        
        indicators = {
            "obv": obv.iloc[-1],
            "obv_ma5": obv_ma5.iloc[-1],
            "obv_ma20": obv_ma20.iloc[-1],
            "mfi": current_mfi,
            "big_volume_days": big_volume_days,
            "flow_trend": "流入" if obv_ma5.iloc[-1] > obv_ma20.iloc[-1] else "流出"
        }
        
        return np.clip(score, -100, 100), indicators
    
    def _score_to_direction(self, score: float) -> TrendDirection:
        """分数转换为趋势方向"""
        if score > 60:
            return TrendDirection.STRONG_UP
        elif score > 30:
            return TrendDirection.UP
        elif score > 10:
            return TrendDirection.WEAK_UP
        elif score > -10:
            return TrendDirection.SIDEWAYS
        elif score > -30:
            return TrendDirection.WEAK_DOWN
        elif score > -60:
            return TrendDirection.DOWN
        else:
            return TrendDirection.STRONG_DOWN
    
    def _determine_market_phase(
        self,
        short: TrendSignal,
        medium: TrendSignal,
        long: TrendSignal
    ) -> str:
        """
        判断市场阶段（增强版多周期共振分析）
        
        参考IBD Market Pulse和威廉·欧奈尔的市场分析方法
        """
        # 计算共振得分
        resonance = self._calculate_resonance(short, medium, long)
        
        # 基于长期趋势判断大方向
        if long.score > 30:
            if resonance["all_bullish"]:
                return "牛市确认(全周期共振)"
            elif medium.score > 20 and short.score > 0:
                return "牛市确认"
            elif medium.score > 0:
                return "牛市震荡"
            elif short.score < -20:
                return "牛市短期调整"
            else:
                return "牛市中期调整"
        elif long.score < -30:
            if resonance["all_bearish"]:
                return "熊市确认(全周期共振)"
            elif medium.score < -20 and short.score < 0:
                return "熊市确认"
            elif medium.score < 0:
                return "熊市反弹"
            elif short.score > 20:
                return "熊市技术反弹"
            else:
                return "熊市筑底"
        else:
            # 震荡市场中的细分
            if resonance["all_bullish"]:
                return "突破在即"
            elif resonance["all_bearish"]:
                return "破位风险"
            elif short.score > 20 and medium.score > 0:
                return "复苏初期"
            elif short.score < -20 and medium.score < 0:
                return "见顶回落"
            elif abs(short.score) < 15 and abs(medium.score) < 15:
                return "窄幅震荡"
            else:
                return "宽幅震荡"
    
    def _calculate_resonance(
        self,
        short: TrendSignal,
        medium: TrendSignal,
        long: TrendSignal
    ) -> Dict:
        """
        计算多周期共振情况
        
        共振越强，趋势越可靠
        """
        scores = [short.score, medium.score, long.score]
        
        # 全周期多头共振
        all_bullish = all(s > 10 for s in scores)
        
        # 全周期空头共振
        all_bearish = all(s < -10 for s in scores)
        
        # 共振强度（标准差越小共振越强）
        std = np.std(scores)
        resonance_strength = max(0, 100 - std * 2)
        
        # 方向一致性
        signs = [np.sign(s) if abs(s) > 5 else 0 for s in scores]
        direction_consistency = abs(sum(signs)) / 3
        
        # 趋势加速/减速
        if short.score > medium.score > long.score:
            acceleration = "加速上涨"
        elif short.score < medium.score < long.score:
            acceleration = "加速下跌"
        elif long.score > medium.score > short.score > 0:
            acceleration = "上涨动能减弱"
        elif long.score < medium.score < short.score < 0:
            acceleration = "下跌动能减弱"
        else:
            acceleration = "趋势分化"
        
        return {
            "all_bullish": all_bullish,
            "all_bearish": all_bearish,
            "resonance_strength": resonance_strength,
            "direction_consistency": direction_consistency,
            "acceleration": acceleration,
            "scores": {"short": short.score, "medium": medium.score, "long": long.score}
        }
    
    def _generate_description(self, period: TrendPeriod, indicators: Dict, score: float) -> str:
        """生成趋势描述（8指标体系）"""
        period_name = self.PERIOD_CONFIG[period]["name"]
        
        parts = []
        
        # 均线描述
        if indicators.get("price_vs_ma_fast", 0) > 0:
            parts.append(f"价格在短均线上方{indicators.get('price_vs_ma_fast', 0):.1f}%")
        else:
            parts.append(f"价格在短均线下方{abs(indicators.get('price_vs_ma_fast', 0)):.1f}%")
        
        # MACD描述
        if indicators.get("macd_histogram", 0) > 0:
            parts.append("MACD柱线为正")
        else:
            parts.append("MACD柱线为负")
        
        # RSI描述
        rsi = indicators.get("rsi", 50)
        if rsi > 70:
            parts.append(f"RSI={rsi:.0f}(超买)")
        elif rsi < 30:
            parts.append(f"RSI={rsi:.0f}(超卖)")
        else:
            parts.append(f"RSI={rsi:.0f}")
        
        # KDJ描述
        kdj_k = indicators.get("kdj_k", 50)
        if indicators.get("kdj_golden_cross"):
            parts.append("KDJ金叉")
        elif indicators.get("kdj_death_cross"):
            parts.append("KDJ死叉")
        elif kdj_k > 80:
            parts.append(f"KDJ超买({kdj_k:.0f})")
        elif kdj_k < 20:
            parts.append(f"KDJ超卖({kdj_k:.0f})")
        
        # ADX描述
        adx = indicators.get("adx", 20)
        adx_trend = indicators.get("adx_trend", "")
        adx_dir = indicators.get("adx_direction", "")
        if adx > 25:
            parts.append(f"ADX={adx:.0f}({adx_trend}{adx_dir})")
        
        # 资金流描述
        flow_trend = indicators.get("flow_trend", "")
        if flow_trend:
            parts.append(f"资金{flow_trend}")
        
        return f"{period_name}: " + ", ".join(parts)
    
    def get_position_advice(self, result: MarketTrendResult) -> Dict:
        """获取仓位建议"""
        score = result.composite_score
        phase = result.market_phase
        
        if score > 60:
            position = "80-100%"
            strategy = "积极进攻，追强势股"
            factors = ["动量因子", "成长因子", "资金流因子"]
        elif score > 30:
            position = "50-80%"
            strategy = "稳健持仓，跟随趋势"
            factors = ["动量因子", "质量因子", "成长因子"]
        elif score > 0:
            position = "30-50%"
            strategy = "谨慎操作，控制仓位"
            factors = ["质量因子", "价值因子", "低波动因子"]
        elif score > -30:
            position = "10-30%"
            strategy = "防御为主，等待机会"
            factors = ["价值因子", "低波动因子", "股息因子"]
        else:
            position = "0-10%"
            strategy = "空仓观望，保护本金"
            factors = ["现金", "逆向因子"]
        
        return {
            "position": position,
            "strategy": strategy,
            "recommended_factors": factors,
            "phase": phase,
            "score": score
        }


def create_trend_analyzer(jq_client=None) -> TrendAnalyzer:
    """创建趋势分析器"""
    return TrendAnalyzer(jq_client=jq_client)

