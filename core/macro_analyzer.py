# -*- coding: utf-8 -*-
"""
宏观经济指标分析器
==================

分析宏观经济数据对市场的影响：
1. GDP增速分析
2. CPI/PPI通胀分析
3. PMI制造业指数
4. 社融/M2货币供应
5. 利率与债券收益率
6. 汇率变化

数据来源：AKShare
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import pandas as pd

logger = logging.getLogger(__name__)


class MacroTrend(Enum):
    """宏观趋势"""
    EXPANSION = "expansion"  # 扩张
    STABLE = "stable"        # 稳定
    CONTRACTION = "contraction"  # 收缩
    TRANSITION = "transition"  # 转型期


class MacroSignal(Enum):
    """宏观信号"""
    BULLISH = "bullish"      # 利好
    NEUTRAL = "neutral"      # 中性
    BEARISH = "bearish"      # 利空


@dataclass
class MacroIndicator:
    """宏观指标"""
    name: str
    value: float
    prev_value: Optional[float] = None
    yoy_change: Optional[float] = None  # 同比变化
    mom_change: Optional[float] = None  # 环比变化
    trend: MacroTrend = MacroTrend.STABLE
    signal: MacroSignal = MacroSignal.NEUTRAL
    updated_at: Optional[str] = None
    description: str = ""


@dataclass
class MacroAnalysisResult:
    """宏观分析结果"""
    analysis_date: str
    gdp: Optional[MacroIndicator] = None
    cpi: Optional[MacroIndicator] = None
    ppi: Optional[MacroIndicator] = None
    pmi: Optional[MacroIndicator] = None
    m2: Optional[MacroIndicator] = None
    social_financing: Optional[MacroIndicator] = None
    interest_rate: Optional[MacroIndicator] = None
    exchange_rate: Optional[MacroIndicator] = None
    
    overall_signal: MacroSignal = MacroSignal.NEUTRAL
    overall_score: float = 0.0  # -100 到 100
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            'analysis_date': self.analysis_date,
            'overall_signal': self.overall_signal.value,
            'overall_score': self.overall_score,
            'summary': self.summary,
            'recommendations': self.recommendations,
            'indicators': {}
        }
        
        for attr in ['gdp', 'cpi', 'ppi', 'pmi', 'm2', 'social_financing', 'interest_rate', 'exchange_rate']:
            indicator = getattr(self, attr)
            if indicator:
                result['indicators'][attr] = {
                    'name': indicator.name,
                    'value': indicator.value,
                    'prev_value': indicator.prev_value,
                    'yoy_change': indicator.yoy_change,
                    'trend': indicator.trend.value,
                    'signal': indicator.signal.value,
                    'description': indicator.description
                }
        
        return result


class MacroAnalyzer:
    """
    宏观经济分析器
    
    功能：
    1. 获取并分析主要宏观经济指标
    2. 判断经济周期位置
    3. 评估对股市的影响
    4. 生成投资建议
    """
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_duration = timedelta(hours=24)  # 缓存24小时
    
    def analyze(self) -> MacroAnalysisResult:
        """
        执行宏观经济分析
        
        Returns:
            MacroAnalysisResult: 分析结果
        """
        logger.info("🌍 开始宏观经济分析...")
        
        result = MacroAnalysisResult(
            analysis_date=date.today().strftime('%Y-%m-%d')
        )
        
        try:
            # 获取各项指标
            result.gdp = self._analyze_gdp()
            result.cpi = self._analyze_cpi()
            result.ppi = self._analyze_ppi()
            result.pmi = self._analyze_pmi()
            result.m2 = self._analyze_m2()
            result.interest_rate = self._analyze_interest_rate()
            result.exchange_rate = self._analyze_exchange_rate()
            
            # 综合评估
            self._evaluate_overall(result)
            
            logger.info(f"🌍 宏观分析完成: {result.overall_signal.value} (得分: {result.overall_score:.1f})")
            
        except Exception as e:
            logger.error(f"宏观分析失败: {e}")
            result.summary = f"分析过程出错: {e}"
        
        return result
    
    def _analyze_gdp(self) -> Optional[MacroIndicator]:
        """分析GDP数据"""
        try:
            import akshare as ak
            
            # 获取GDP数据
            df = ak.macro_china_gdp()
            
            if df is not None and not df.empty:
                # 取最新数据
                latest = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else None
                
                # 尝试解析数值
                value = self._parse_value(latest.get('今值', latest.get('国内生产总值-绝对值', 0)))
                prev_value = self._parse_value(prev.get('今值', prev.get('国内生产总值-绝对值', 0))) if prev is not None else None
                
                # 计算变化
                yoy = None
                if '今值' in df.columns:
                    yoy = value  # GDP增速本身就是同比
                
                # 判断趋势和信号
                trend = MacroTrend.STABLE
                signal = MacroSignal.NEUTRAL
                
                if yoy is not None:
                    if yoy > 6:
                        trend = MacroTrend.EXPANSION
                        signal = MacroSignal.BULLISH
                    elif yoy > 4:
                        trend = MacroTrend.STABLE
                        signal = MacroSignal.NEUTRAL
                    elif yoy > 0:
                        trend = MacroTrend.CONTRACTION
                        signal = MacroSignal.BEARISH
                    else:
                        trend = MacroTrend.CONTRACTION
                        signal = MacroSignal.BEARISH
                
                return MacroIndicator(
                    name="GDP增速",
                    value=value,
                    prev_value=prev_value,
                    yoy_change=yoy,
                    trend=trend,
                    signal=signal,
                    updated_at=str(latest.get('时间', '')),
                    description=f"GDP同比增长{value:.1f}%，{'经济稳健增长' if signal == MacroSignal.BULLISH else '增速放缓需关注'}"
                )
                
        except Exception as e:
            logger.warning(f"GDP数据获取失败: {e}")
        
        return None
    
    def _analyze_cpi(self) -> Optional[MacroIndicator]:
        """分析CPI数据"""
        try:
            import akshare as ak
            
            df = ak.macro_china_cpi_yearly()
            
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else None
                
                value = self._parse_value(latest.get('今值', 0))
                prev_value = self._parse_value(prev.get('今值', 0)) if prev is not None else None
                
                # CPI判断：2-3%是健康区间
                trend = MacroTrend.STABLE
                signal = MacroSignal.NEUTRAL
                
                if value < 0:
                    trend = MacroTrend.CONTRACTION
                    signal = MacroSignal.BEARISH
                    desc = "通缩风险"
                elif value < 2:
                    trend = MacroTrend.STABLE
                    signal = MacroSignal.NEUTRAL
                    desc = "温和通胀，有利增长"
                elif value < 3:
                    trend = MacroTrend.STABLE
                    signal = MacroSignal.BULLISH
                    desc = "健康通胀区间"
                elif value < 5:
                    trend = MacroTrend.EXPANSION
                    signal = MacroSignal.NEUTRAL
                    desc = "通胀偏高，关注政策"
                else:
                    trend = MacroTrend.EXPANSION
                    signal = MacroSignal.BEARISH
                    desc = "通胀过高，利空股市"
                
                return MacroIndicator(
                    name="CPI",
                    value=value,
                    prev_value=prev_value,
                    yoy_change=value,
                    trend=trend,
                    signal=signal,
                    updated_at=str(latest.get('时间', '')),
                    description=f"CPI同比{value:.1f}%，{desc}"
                )
                
        except Exception as e:
            logger.warning(f"CPI数据获取失败: {e}")
        
        return None
    
    def _analyze_ppi(self) -> Optional[MacroIndicator]:
        """分析PPI数据"""
        try:
            import akshare as ak
            
            df = ak.macro_china_ppi_yearly()
            
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else None
                
                value = self._parse_value(latest.get('今值', 0))
                prev_value = self._parse_value(prev.get('今值', 0)) if prev is not None else None
                
                # PPI判断
                trend = MacroTrend.STABLE
                signal = MacroSignal.NEUTRAL
                
                if value < -3:
                    trend = MacroTrend.CONTRACTION
                    signal = MacroSignal.BEARISH
                    desc = "严重通缩，工业萎缩"
                elif value < 0:
                    trend = MacroTrend.CONTRACTION
                    signal = MacroSignal.NEUTRAL
                    desc = "工业品价格下跌"
                elif value < 3:
                    trend = MacroTrend.STABLE
                    signal = MacroSignal.BULLISH
                    desc = "温和上涨，企业盈利改善"
                else:
                    trend = MacroTrend.EXPANSION
                    signal = MacroSignal.NEUTRAL
                    desc = "成本压力上升"
                
                return MacroIndicator(
                    name="PPI",
                    value=value,
                    prev_value=prev_value,
                    yoy_change=value,
                    trend=trend,
                    signal=signal,
                    updated_at=str(latest.get('时间', '')),
                    description=f"PPI同比{value:.1f}%，{desc}"
                )
                
        except Exception as e:
            logger.warning(f"PPI数据获取失败: {e}")
        
        return None
    
    def _analyze_pmi(self) -> Optional[MacroIndicator]:
        """分析PMI数据"""
        try:
            import akshare as ak
            
            df = ak.macro_china_pmi_yearly()
            
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else None
                
                value = self._parse_value(latest.get('今值', 50))
                prev_value = self._parse_value(prev.get('今值', 50)) if prev is not None else None
                
                # PMI判断：50为荣枯线
                trend = MacroTrend.STABLE
                signal = MacroSignal.NEUTRAL
                
                if value >= 52:
                    trend = MacroTrend.EXPANSION
                    signal = MacroSignal.BULLISH
                    desc = "制造业强劲扩张"
                elif value >= 50:
                    trend = MacroTrend.STABLE
                    signal = MacroSignal.NEUTRAL
                    desc = "制造业温和扩张"
                elif value >= 48:
                    trend = MacroTrend.CONTRACTION
                    signal = MacroSignal.NEUTRAL
                    desc = "制造业轻微收缩"
                else:
                    trend = MacroTrend.CONTRACTION
                    signal = MacroSignal.BEARISH
                    desc = "制造业明显收缩"
                
                # 考虑趋势变化
                if prev_value is not None:
                    mom = value - prev_value
                    if mom > 1:
                        desc += "，环比改善"
                        if signal == MacroSignal.NEUTRAL:
                            signal = MacroSignal.BULLISH
                    elif mom < -1:
                        desc += "，环比恶化"
                        if signal == MacroSignal.NEUTRAL:
                            signal = MacroSignal.BEARISH
                
                return MacroIndicator(
                    name="PMI",
                    value=value,
                    prev_value=prev_value,
                    mom_change=value - prev_value if prev_value else None,
                    trend=trend,
                    signal=signal,
                    updated_at=str(latest.get('时间', '')),
                    description=f"PMI {value:.1f}，{desc}"
                )
                
        except Exception as e:
            logger.warning(f"PMI数据获取失败: {e}")
        
        return None
    
    def _analyze_m2(self) -> Optional[MacroIndicator]:
        """分析M2货币供应"""
        try:
            import akshare as ak
            
            df = ak.macro_china_money_supply()
            
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else None
                
                # 尝试获取M2同比增速
                value = self._parse_value(latest.get('M2-同比增长', latest.get('M2同比', 0)))
                prev_value = self._parse_value(prev.get('M2-同比增长', prev.get('M2同比', 0))) if prev is not None else None
                
                # M2判断
                trend = MacroTrend.STABLE
                signal = MacroSignal.NEUTRAL
                
                if value > 12:
                    trend = MacroTrend.EXPANSION
                    signal = MacroSignal.BULLISH
                    desc = "货币宽松，利好股市"
                elif value > 8:
                    trend = MacroTrend.STABLE
                    signal = MacroSignal.NEUTRAL
                    desc = "货币政策中性"
                else:
                    trend = MacroTrend.CONTRACTION
                    signal = MacroSignal.BEARISH
                    desc = "货币收紧，流动性趋紧"
                
                return MacroIndicator(
                    name="M2增速",
                    value=value,
                    prev_value=prev_value,
                    yoy_change=value,
                    trend=trend,
                    signal=signal,
                    updated_at=str(latest.get('月份', '')),
                    description=f"M2同比{value:.1f}%，{desc}"
                )
                
        except Exception as e:
            logger.warning(f"M2数据获取失败: {e}")
        
        return None
    
    def _analyze_interest_rate(self) -> Optional[MacroIndicator]:
        """分析利率数据"""
        try:
            import akshare as ak
            
            # 获取LPR利率
            df = ak.macro_china_lpr()
            
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                prev = df.iloc[-5] if len(df) > 5 else None  # 对比5个月前
                
                value = self._parse_value(latest.get('1年期LPR', 3.45))
                prev_value = self._parse_value(prev.get('1年期LPR', value)) if prev is not None else None
                
                # 利率判断
                trend = MacroTrend.STABLE
                signal = MacroSignal.NEUTRAL
                
                if prev_value:
                    change = value - prev_value
                    if change < -0.1:
                        trend = MacroTrend.EXPANSION
                        signal = MacroSignal.BULLISH
                        desc = "降息周期，利好股市"
                    elif change > 0.1:
                        trend = MacroTrend.CONTRACTION
                        signal = MacroSignal.BEARISH
                        desc = "加息周期，估值承压"
                    else:
                        desc = "利率稳定"
                else:
                    desc = "利率水平正常"
                
                return MacroIndicator(
                    name="LPR利率",
                    value=value,
                    prev_value=prev_value,
                    trend=trend,
                    signal=signal,
                    updated_at=str(latest.get('日期', '')),
                    description=f"1年期LPR {value:.2f}%，{desc}"
                )
                
        except Exception as e:
            logger.warning(f"利率数据获取失败: {e}")
        
        return None
    
    def _analyze_exchange_rate(self) -> Optional[MacroIndicator]:
        """分析汇率数据"""
        try:
            import akshare as ak
            
            # 获取人民币汇率
            df = ak.currency_boc_sina(symbol="美元")
            
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                prev_month = df.iloc[-22] if len(df) > 22 else None  # 对比1个月前
                
                value = self._parse_value(latest.get('中行汇买价', latest.get('卖出价', 7.2)))
                prev_value = self._parse_value(prev_month.get('中行汇买价', prev_month.get('卖出价', value))) if prev_month is not None else None
                
                # 汇率判断
                trend = MacroTrend.STABLE
                signal = MacroSignal.NEUTRAL
                
                if prev_value:
                    change_pct = (value - prev_value) / prev_value * 100
                    if change_pct > 2:
                        trend = MacroTrend.CONTRACTION
                        signal = MacroSignal.BEARISH
                        desc = "人民币贬值，外资流出压力"
                    elif change_pct < -2:
                        trend = MacroTrend.EXPANSION
                        signal = MacroSignal.BULLISH
                        desc = "人民币升值，外资流入"
                    else:
                        desc = "汇率基本稳定"
                else:
                    desc = "汇率运行正常"
                
                return MacroIndicator(
                    name="美元/人民币",
                    value=value,
                    prev_value=prev_value,
                    trend=trend,
                    signal=signal,
                    updated_at=str(latest.get('日期', '')),
                    description=f"美元/人民币 {value:.4f}，{desc}"
                )
                
        except Exception as e:
            logger.warning(f"汇率数据获取失败: {e}")
        
        return None
    
    def _evaluate_overall(self, result: MacroAnalysisResult):
        """综合评估宏观环境"""
        scores = []
        signals = []
        
        # 收集所有指标
        indicators = [
            ('gdp', 2.0),      # GDP权重最高
            ('pmi', 1.5),      # PMI次高
            ('cpi', 1.0),
            ('ppi', 1.0),
            ('m2', 1.2),
            ('interest_rate', 1.3),
            ('exchange_rate', 0.8),
        ]
        
        for attr, weight in indicators:
            indicator = getattr(result, attr)
            if indicator:
                signals.append(indicator.signal)
                
                # 信号转分数
                if indicator.signal == MacroSignal.BULLISH:
                    scores.append(30 * weight)
                elif indicator.signal == MacroSignal.BEARISH:
                    scores.append(-30 * weight)
                else:
                    scores.append(0)
        
        # 计算综合得分
        if scores:
            result.overall_score = sum(scores) / len(scores)
        
        # 判断综合信号
        bullish_count = signals.count(MacroSignal.BULLISH)
        bearish_count = signals.count(MacroSignal.BEARISH)
        
        if bullish_count >= 4:
            result.overall_signal = MacroSignal.BULLISH
        elif bearish_count >= 4:
            result.overall_signal = MacroSignal.BEARISH
        elif bullish_count > bearish_count + 1:
            result.overall_signal = MacroSignal.BULLISH
        elif bearish_count > bullish_count + 1:
            result.overall_signal = MacroSignal.BEARISH
        else:
            result.overall_signal = MacroSignal.NEUTRAL
        
        # 生成摘要
        result.summary = self._generate_summary(result)
        result.recommendations = self._generate_recommendations(result)
    
    def _generate_summary(self, result: MacroAnalysisResult) -> str:
        """生成分析摘要"""
        signal_text = {
            MacroSignal.BULLISH: "利好",
            MacroSignal.NEUTRAL: "中性",
            MacroSignal.BEARISH: "利空"
        }
        
        parts = [f"当前宏观经济环境整体{signal_text[result.overall_signal]}股市。"]
        
        # 添加关键指标描述
        if result.pmi:
            parts.append(result.pmi.description)
        if result.m2:
            parts.append(result.m2.description)
        
        return " ".join(parts)
    
    def _generate_recommendations(self, result: MacroAnalysisResult) -> List[str]:
        """生成投资建议"""
        recommendations = []
        
        if result.overall_signal == MacroSignal.BULLISH:
            recommendations.append("宏观环境支持，可适度增加权益配置")
            recommendations.append("关注顺周期板块机会")
        elif result.overall_signal == MacroSignal.BEARISH:
            recommendations.append("宏观承压，建议降低仓位或转向防御")
            recommendations.append("关注抗周期板块如消费、医药")
        else:
            recommendations.append("宏观环境中性，保持均衡配置")
            recommendations.append("精选个股，关注结构性机会")
        
        # 基于具体指标的建议
        if result.m2 and result.m2.signal == MacroSignal.BULLISH:
            recommendations.append("流动性宽松，利好成长股")
        
        if result.interest_rate and result.interest_rate.signal == MacroSignal.BULLISH:
            recommendations.append("降息周期利好利率敏感行业（地产、银行）")
        
        return recommendations
    
    def _parse_value(self, value: Any) -> float:
        """解析数值"""
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                # 移除百分号等
                clean = value.replace('%', '').replace(',', '').strip()
                return float(clean)
            except:
                return 0.0
        return 0.0


def get_macro_analyzer() -> MacroAnalyzer:
    """获取宏观分析器"""
    return MacroAnalyzer()

