# -*- coding: utf-8 -*-
"""
IBD风格市场趋势分析器
=====================

参考Investor's Business Daily (IBD)的市场分析方法：
1. 市场跟踪日 (Follow-Through Day)
2. 分布日统计 (Distribution Day Count)
3. 市场状态评估 (Market Pulse)
4. 领涨股分析

IBD方法论核心：
- 跟踪日：确认底部反转的强势上涨
- 分布日：机构抛售信号（大跌+放量）
- 市场状态：根据跟踪日和分布日判断
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class MarketStatus(Enum):
    """市场状态（IBD风格）"""
    CONFIRMED_UPTREND = "confirmed_uptrend"      # 确认上涨
    UPTREND_UNDER_PRESSURE = "uptrend_pressure"  # 上涨承压
    MARKET_IN_CORRECTION = "correction"           # 市场调整
    RALLY_ATTEMPT = "rally_attempt"               # 反弹尝试


@dataclass
class FollowThroughDay:
    """跟踪日信息"""
    date: str
    gain_pct: float      # 涨幅
    volume_ratio: float  # 相对平均成交量比例
    days_since_low: int  # 距离低点天数
    is_valid: bool = True


@dataclass
class DistributionDay:
    """分布日信息"""
    date: str
    loss_pct: float      # 跌幅
    volume_ratio: float  # 相对平均成交量比例
    expired: bool = False  # 是否过期（25日后过期）


@dataclass
class IBDAnalysisResult:
    """IBD风格分析结果"""
    analysis_date: str
    market_status: MarketStatus
    distribution_count: int
    follow_through_days: List[FollowThroughDay] = field(default_factory=list)
    distribution_days: List[DistributionDay] = field(default_factory=list)
    
    # 技术指标
    price_vs_50ma: float = 0.0   # 价格相对50日均线
    price_vs_200ma: float = 0.0  # 价格相对200日均线
    ma50_vs_ma200: float = 0.0   # 50日vs200日均线
    
    # 市场宽度
    stocks_above_50ma_pct: float = 0.0  # 在50日均线上方的股票比例
    new_highs: int = 0
    new_lows: int = 0
    
    recommendation: str = ""
    details: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'analysis_date': self.analysis_date,
            'market_status': self.market_status.value,
            'distribution_count': self.distribution_count,
            'follow_through_count': len(self.follow_through_days),
            'price_vs_50ma': self.price_vs_50ma,
            'price_vs_200ma': self.price_vs_200ma,
            'ma50_vs_ma200': self.ma50_vs_ma200,
            'stocks_above_50ma_pct': self.stocks_above_50ma_pct,
            'new_highs': self.new_highs,
            'new_lows': self.new_lows,
            'recommendation': self.recommendation,
            'details': self.details
        }


class IBDStyleAnalyzer:
    """
    IBD风格市场分析器
    
    分析方法：
    1. 识别跟踪日（底部反转确认）
    2. 统计分布日（机构抛售）
    3. 评估市场状态
    4. 生成交易建议
    """
    
    # 分布日标准
    DISTRIBUTION_THRESHOLD = -0.2    # 跌幅超过0.2%
    DISTRIBUTION_VOLUME_RATIO = 1.0  # 成交量高于平均
    DISTRIBUTION_LOOKBACK = 25       # 25日内有效
    MAX_DISTRIBUTION_DAYS = 5        # 超过5个分布日视为承压
    
    # 跟踪日标准
    FOLLOW_THROUGH_GAIN = 1.2        # 涨幅超过1.2%
    FOLLOW_THROUGH_VOLUME_RATIO = 1.0  # 成交量高于平均
    FOLLOW_THROUGH_MIN_DAYS = 4      # 至少在低点后第4天
    
    def __init__(self):
        self._data_cache: Dict[str, pd.DataFrame] = {}
    
    def analyze(self, index_code: str = '000001.XSHG', lookback_days: int = 60) -> IBDAnalysisResult:
        """
        执行IBD风格分析
        
        Args:
            index_code: 指数代码（默认上证指数）
            lookback_days: 回看天数
        
        Returns:
            IBDAnalysisResult
        """
        logger.info(f"🔍 开始IBD风格市场分析: {index_code}")
        
        result = IBDAnalysisResult(
            analysis_date=date.today().strftime('%Y-%m-%d'),
            market_status=MarketStatus.RALLY_ATTEMPT,
            distribution_count=0
        )
        
        try:
            # 获取数据
            df = self._get_index_data(index_code, lookback_days + 200)
            
            if df is None or len(df) < 50:
                result.recommendation = "数据不足，无法分析"
                return result
            
            # 计算技术指标
            df = self._calculate_indicators(df)
            
            # 识别分布日
            distribution_days = self._identify_distribution_days(df)
            result.distribution_days = distribution_days
            result.distribution_count = len([d for d in distribution_days if not d.expired])
            
            # 识别跟踪日
            follow_through_days = self._identify_follow_through_days(df)
            result.follow_through_days = follow_through_days
            
            # 计算均线位置
            latest = df.iloc[-1]
            result.price_vs_50ma = (latest['close'] / latest['ma50'] - 1) * 100 if latest['ma50'] > 0 else 0
            result.price_vs_200ma = (latest['close'] / latest['ma200'] - 1) * 100 if latest['ma200'] > 0 else 0
            result.ma50_vs_ma200 = (latest['ma50'] / latest['ma200'] - 1) * 100 if latest['ma200'] > 0 else 0
            
            # 获取市场宽度（如果有数据）
            breadth = self._get_market_breadth()
            if breadth:
                result.stocks_above_50ma_pct = breadth.get('above_50ma_pct', 0)
                result.new_highs = breadth.get('new_highs', 0)
                result.new_lows = breadth.get('new_lows', 0)
            
            # 判断市场状态
            result.market_status = self._determine_market_status(result, df)
            
            # 生成建议
            result.recommendation = self._generate_recommendation(result)
            result.details = self._generate_details(result, df)
            
            logger.info(f"🔍 IBD分析完成: {result.market_status.value}")
            
        except Exception as e:
            logger.error(f"IBD分析失败: {e}")
            result.recommendation = f"分析出错: {e}"
        
        return result
    
    def _get_index_data(self, code: str, days: int) -> Optional[pd.DataFrame]:
        """获取指数数据"""
        try:
            from core.data_source_manager import get_data_source_manager
            
            manager = get_data_source_manager()
            end_date = date.today().strftime('%Y-%m-%d')
            start_date = (date.today() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            result = manager.get_price(code, start_date, end_date)
            
            if result.success and result.data is not None:
                df = result.data.copy()
                df = df.reset_index()
                df.columns = [c.lower() for c in df.columns]
                
                # 处理索引列名称 (可能是 'index' 或 'date')
                if 'index' in df.columns and 'date' not in df.columns:
                    df = df.rename(columns={'index': 'date'})
                
                # 确保date列是datetime类型
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                
                return df
            
        except Exception as e:
            logger.warning(f"获取指数数据失败: {e}")
        
        return None
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        df = df.copy()
        
        # 均线
        df['ma50'] = df['close'].rolling(window=50).mean()
        df['ma200'] = df['close'].rolling(window=200).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        
        # 平均成交量
        df['avg_volume'] = df['volume'].rolling(window=50).mean()
        df['volume_ratio'] = df['volume'] / df['avg_volume']
        
        # 日涨跌幅
        df['pct_change'] = df['close'].pct_change() * 100
        
        # 距离低点天数
        df['rolling_min'] = df['close'].rolling(window=25).min()
        
        return df
    
    def _identify_distribution_days(self, df: pd.DataFrame) -> List[DistributionDay]:
        """识别分布日"""
        distribution_days = []
        recent_df = df.tail(self.DISTRIBUTION_LOOKBACK + 5)
        
        for i, row in recent_df.iterrows():
            if pd.isna(row['pct_change']) or pd.isna(row['volume_ratio']):
                continue
            
            # 分布日条件：跌幅 > 0.2% 且 成交量放大
            if (row['pct_change'] < self.DISTRIBUTION_THRESHOLD and 
                row['volume_ratio'] > self.DISTRIBUTION_VOLUME_RATIO):
                
                date_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
                
                distribution_days.append(DistributionDay(
                    date=date_str,
                    loss_pct=row['pct_change'],
                    volume_ratio=row['volume_ratio'],
                    expired=False  # 在lookback内都有效
                ))
        
        # 只保留最近25天的
        if len(distribution_days) > self.DISTRIBUTION_LOOKBACK:
            for dd in distribution_days[:-self.DISTRIBUTION_LOOKBACK]:
                dd.expired = True
        
        return distribution_days
    
    def _identify_follow_through_days(self, df: pd.DataFrame) -> List[FollowThroughDay]:
        """识别跟踪日"""
        follow_through_days = []
        
        # 找到近期低点
        recent_df = df.tail(60)
        if len(recent_df) < 20:
            return follow_through_days
        
        # 找最低收盘价位置
        low_idx = recent_df['close'].idxmin()
        low_date = recent_df.loc[low_idx, 'date']
        
        # 从低点后第4天开始寻找跟踪日
        low_pos = recent_df.index.get_loc(low_idx)
        
        for i in range(low_pos + self.FOLLOW_THROUGH_MIN_DAYS, len(recent_df)):
            row = recent_df.iloc[i]
            
            if pd.isna(row['pct_change']) or pd.isna(row['volume_ratio']):
                continue
            
            # 跟踪日条件：涨幅 > 1.2% 且 成交量放大
            if (row['pct_change'] > self.FOLLOW_THROUGH_GAIN and 
                row['volume_ratio'] > self.FOLLOW_THROUGH_VOLUME_RATIO):
                
                date_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
                
                follow_through_days.append(FollowThroughDay(
                    date=date_str,
                    gain_pct=row['pct_change'],
                    volume_ratio=row['volume_ratio'],
                    days_since_low=i - low_pos
                ))
        
        return follow_through_days
    
    def _determine_market_status(self, result: IBDAnalysisResult, df: pd.DataFrame) -> MarketStatus:
        """判断市场状态"""
        dist_count = result.distribution_count
        ftd_count = len(result.follow_through_days)
        
        # 价格位置
        latest = df.iloc[-1]
        price_above_50ma = latest['close'] > latest['ma50'] if not pd.isna(latest['ma50']) else True
        price_above_200ma = latest['close'] > latest['ma200'] if not pd.isna(latest['ma200']) else True
        
        # 市场状态判断逻辑
        if dist_count >= self.MAX_DISTRIBUTION_DAYS:
            # 分布日过多，市场调整
            return MarketStatus.MARKET_IN_CORRECTION
        
        if ftd_count > 0 and dist_count < 3 and price_above_50ma:
            # 有跟踪日且分布日少，确认上涨
            return MarketStatus.CONFIRMED_UPTREND
        
        if ftd_count > 0 and 3 <= dist_count < self.MAX_DISTRIBUTION_DAYS:
            # 有跟踪日但分布日偏多，上涨承压
            return MarketStatus.UPTREND_UNDER_PRESSURE
        
        if not price_above_50ma and not price_above_200ma:
            # 价格低于均线，市场调整
            return MarketStatus.MARKET_IN_CORRECTION
        
        # 默认反弹尝试
        return MarketStatus.RALLY_ATTEMPT
    
    def _get_market_breadth(self) -> Optional[Dict]:
        """获取市场宽度数据"""
        try:
            import akshare as ak
            
            # 尝试获取涨跌统计
            result = {}
            
            # 可以通过AKShare获取涨跌家数等数据
            # 这里简化处理
            
            return result
            
        except Exception as e:
            logger.debug(f"获取市场宽度失败: {e}")
            return None
    
    def _generate_recommendation(self, result: IBDAnalysisResult) -> str:
        """生成交易建议"""
        status = result.market_status
        
        recommendations = {
            MarketStatus.CONFIRMED_UPTREND: "市场上涨确认，可积极参与，关注领涨股突破买点",
            MarketStatus.UPTREND_UNDER_PRESSURE: "上涨趋势承压，谨慎操作，避免追高，关注止损",
            MarketStatus.MARKET_IN_CORRECTION: "市场处于调整，降低仓位或观望，等待新的跟踪日",
            MarketStatus.RALLY_ATTEMPT: "反弹尝试中，等待跟踪日确认，暂不大举买入"
        }
        
        return recommendations.get(status, "保持观望")
    
    def _generate_details(self, result: IBDAnalysisResult, df: pd.DataFrame) -> List[str]:
        """生成详细说明"""
        details = []
        
        # 市场状态描述
        status_desc = {
            MarketStatus.CONFIRMED_UPTREND: "市场已确认上涨趋势",
            MarketStatus.UPTREND_UNDER_PRESSURE: "上涨趋势面临压力",
            MarketStatus.MARKET_IN_CORRECTION: "市场处于调整阶段",
            MarketStatus.RALLY_ATTEMPT: "市场正在尝试反弹"
        }
        details.append(status_desc.get(result.market_status, ""))
        
        # 分布日信息
        active_dist = len([d for d in result.distribution_days if not d.expired])
        details.append(f"近25日有效分布日: {active_dist}个")
        
        # 跟踪日信息
        if result.follow_through_days:
            latest_ftd = result.follow_through_days[-1]
            details.append(f"最近跟踪日: {latest_ftd.date} (涨{latest_ftd.gain_pct:.1f}%)")
        else:
            details.append("近期无跟踪日")
        
        # 均线位置
        if result.price_vs_50ma > 0:
            details.append(f"价格高于50日均线 {result.price_vs_50ma:.1f}%")
        else:
            details.append(f"价格低于50日均线 {abs(result.price_vs_50ma):.1f}%")
        
        if result.price_vs_200ma > 0:
            details.append(f"价格高于200日均线 {result.price_vs_200ma:.1f}%")
        else:
            details.append(f"价格低于200日均线 {abs(result.price_vs_200ma):.1f}%")
        
        return details


def get_ibd_analyzer() -> IBDStyleAnalyzer:
    """获取IBD风格分析器"""
    return IBDStyleAnalyzer()

