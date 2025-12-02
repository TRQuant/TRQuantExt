#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动量和成长潜力扫描器

基于JQData和AKShare，筛选出动量和成长潜力的股票
支持短中长三个期限
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# 尝试导入JQData
JQDataClient = None
try:
    from jqdata.client import JQDataClient
    from jqdatasdk import query, valuation, indicator
    JQDATA_AVAILABLE = True
except ImportError:
    JQDATA_AVAILABLE = False
    logger.warning("⚠️ JQData未安装")

# 尝试导入AKShare
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    ak = None
    logger.warning("⚠️ AKShare未安装")


@dataclass
class MomentumGrowthStock:
    """动量和成长潜力股票"""
    code: str                    # 股票代码
    name: str                    # 股票名称
    period: str                  # 期限：short/medium/long
    
    # 动量指标
    momentum_score: float = 0.0  # 动量得分（0-100）
    price_change_1m: float = 0.0  # 1个月涨跌幅
    price_change_3m: float = 0.0  # 3个月涨跌幅
    price_change_6m: float = 0.0  # 6个月涨跌幅
    rsi: float = 0.0             # RSI指标
    macd_signal: str = ""        # MACD信号
    
    # 成长潜力指标
    growth_score: float = 0.0    # 成长得分（0-100）
    roe: Optional[float] = None  # ROE
    net_profit_growth: Optional[float] = None  # 净利润增长率
    revenue_growth: Optional[float] = None     # 营收增长率
    eps_growth: Optional[float] = None         # EPS增长率
    
    # 综合评分
    composite_score: float = 0.0  # 综合得分 = 动量得分 * 0.5 + 成长得分 * 0.5
    
    # 元数据
    update_time: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: List[str] = field(default_factory=list)


class MomentumGrowthScanner:
    """
    动量和成长潜力扫描器
    
    数据源优先级：JQData > AKShare
    期限分类：
    - 短期（short）：1-3个月动量
    - 中期（medium）：3-6个月动量
    - 长期（long）：6-12个月动量
    """
    
    def __init__(
        self,
        jq_client: Optional[JQDataClient] = None,
        use_akshare: bool = True
    ):
        """
        初始化扫描器
        
        Args:
            jq_client: JQData客户端
            use_akshare: 是否使用AKShare作为辅助数据源
        """
        self.jq_client = jq_client
        self.use_akshare = use_akshare and AKSHARE_AVAILABLE
        
        # 期限配置
        self.period_configs = {
            'short': {
                'lookback_days': 30,      # 1个月
                'momentum_weight': 0.7,   # 动量权重更高
                'growth_weight': 0.3
            },
            'medium': {
                'lookback_days': 90,      # 3个月
                'momentum_weight': 0.5,
                'growth_weight': 0.5
            },
            'long': {
                'lookback_days': 180,     # 6个月
                'momentum_weight': 0.3,   # 成长权重更高
                'growth_weight': 0.7
            }
        }
    
    def scan_all_markets(
        self,
        period: str = 'medium',
        min_score: float = 60.0,
        max_stocks: int = 100
    ) -> Dict[str, List[MomentumGrowthStock]]:
        """
        扫描全市场，筛选动量和成长潜力股票
        
        Args:
            period: 期限（short/medium/long）
            min_score: 最小综合得分
            max_stocks: 每个期限最多返回的股票数
        
        Returns:
            Dict: {period: [MomentumGrowthStock, ...]}
        """
        results = {}
        
        # 获取股票列表
        stock_list = self._get_stock_list()
        if not stock_list:
            logger.warning("未获取到股票列表")
            return results
        
        logger.info(f"开始扫描全市场，共 {len(stock_list)} 只股票")
        
        # 对每个期限进行扫描
        for period_key in ['short', 'medium', 'long']:
            logger.info(f"扫描 {period_key} 期限...")
            stocks = self._scan_period(
                stock_list=stock_list,
                period=period_key,
                min_score=min_score,
                max_stocks=max_stocks
            )
            results[period_key] = stocks
            logger.info(f"{period_key} 期限：找到 {len(stocks)} 只股票")
        
        return results
    
    def _get_stock_list(self) -> List[str]:
        """获取股票列表（优先JQData，备选AKShare）"""
        stock_list = []
        
        # 优先使用JQData
        if self.jq_client and self.jq_client.is_authenticated():
            try:
                securities = self.jq_client.get_all_securities(types=['stock'], date=None)
                if not securities.empty:
                    stock_list = securities.index.tolist()
                    logger.info(f"✅ JQData获取股票列表: {len(stock_list)} 只")
                    return stock_list
            except Exception as e:
                logger.warning(f"JQData获取股票列表失败: {e}")
        
        # 备选AKShare
        if self.use_akshare:
            try:
                import socket
                socket.setdefaulttimeout(30)
                # 使用AKShare获取A股代码列表
                df = ak.stock_info_a_code_name()
                if df is not None and not df.empty:
                    # 转换为JQData格式
                    for _, row in df.iterrows():
                        code = str(row.get('code', ''))
                        # 确保代码是6位数字
                        if len(code) == 6 and (code.startswith('0') or code.startswith('3') or code.startswith('6')):
                            # 转换为JQData格式：000001.XSHE 或 600000.XSHG
                            if code.startswith('6'):
                                jq_code = f"{code}.XSHG"
                            else:
                                jq_code = f"{code}.XSHE"
                            stock_list.append(jq_code)
                    logger.info(f"✅ AKShare获取股票列表: {len(stock_list)} 只")
                    return stock_list
            except Exception as e:
                logger.warning(f"AKShare获取股票列表失败: {e}")
        
        logger.warning("⚠️ 无法获取股票列表")
        return []
    
    def _scan_period(
        self,
        stock_list: List[str],
        period: str,
        min_score: float,
        max_stocks: int
    ) -> List[MomentumGrowthStock]:
        """
        扫描指定期限的股票
        
        Args:
            stock_list: 股票代码列表
            period: 期限（short/medium/long）
            min_score: 最小综合得分
            max_stocks: 最多返回的股票数
        
        Returns:
            List[MomentumGrowthStock]: 筛选后的股票列表
        """
        config = self.period_configs.get(period, self.period_configs['medium'])
        lookback_days = config['lookback_days']
        
        results = []
        processed = 0
        total = len(stock_list)
        
        # 获取可用日期
        if self.jq_client and self.jq_client.is_authenticated():
            end_date = self.jq_client.get_available_end_date()
            perm = self.jq_client.get_permission()
            start_date = perm.start_date if perm.detected else None
        else:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        
        for stock_code in stock_list:
            processed += 1
            if processed % 100 == 0:
                logger.info(f"扫描进度: {processed}/{total} ({processed*100//total}%)")
            
            try:
                stock = self._analyze_stock(
                    stock_code=stock_code,
                    period=period,
                    lookback_days=lookback_days,
                    end_date=end_date,
                    start_date=start_date
                )
                
                if stock and stock.composite_score >= min_score:
                    results.append(stock)
                    
            except Exception as e:
                logger.debug(f"分析股票 {stock_code} 失败: {e}")
                continue
        
        # 按综合得分排序
        results.sort(key=lambda x: x.composite_score, reverse=True)
        
        # 返回前max_stocks只
        return results[:max_stocks]
    
    def _analyze_stock(
        self,
        stock_code: str,
        period: str,
        lookback_days: int,
        end_date: str,
        start_date: Optional[str] = None
    ) -> Optional[MomentumGrowthStock]:
        """
        分析单只股票的动量和成长潜力
        
        Args:
            stock_code: 股票代码
            period: 期限
            lookback_days: 回看天数
            end_date: 结束日期
            start_date: 开始日期
        
        Returns:
            MomentumGrowthStock: 分析结果
        """
        # 计算开始日期
        if start_date is None:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            start_dt = end_dt - timedelta(days=lookback_days)
            start_date = start_dt.strftime('%Y-%m-%d')
        
        # 获取价格数据
        price_data = self._get_price_data(stock_code, start_date, end_date)
        if price_data is None or price_data.empty or len(price_data) < 20:
            return None
        
        # 获取股票名称
        stock_name = self._get_stock_name(stock_code)
        
        # 计算动量指标
        momentum_score, momentum_indicators = self._calculate_momentum(
            price_data, period
        )
        
        # 计算成长潜力
        growth_score, growth_indicators = self._calculate_growth(
            stock_code, end_date
        )
        
        # 计算综合得分
        config = self.period_configs.get(period, self.period_configs['medium'])
        composite_score = (
            momentum_score * config['momentum_weight'] +
            growth_score * config['growth_weight']
        )
        
        # 生成标签
        tags = []
        if momentum_score >= 70:
            tags.append('强动量')
        if growth_score >= 70:
            tags.append('高成长')
        if composite_score >= 80:
            tags.append('优质')
        
        # 创建股票对象
        stock = MomentumGrowthStock(
            code=stock_code,
            name=stock_name,
            period=period,
            momentum_score=momentum_score,
            price_change_1m=momentum_indicators.get('change_1m', 0),
            price_change_3m=momentum_indicators.get('change_3m', 0),
            price_change_6m=momentum_indicators.get('change_6m', 0),
            rsi=momentum_indicators.get('rsi', 0),
            macd_signal=momentum_indicators.get('macd_signal', ''),
            growth_score=growth_score,
            roe=growth_indicators.get('roe'),
            net_profit_growth=growth_indicators.get('net_profit_growth'),
            revenue_growth=growth_indicators.get('revenue_growth'),
            eps_growth=growth_indicators.get('eps_growth'),
            composite_score=composite_score,
            tags=tags
        )
        
        return stock
    
    def _get_price_data(
        self,
        stock_code: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """获取价格数据（优先JQData，备选AKShare）"""
        # 优先JQData
        if self.jq_client and self.jq_client.is_authenticated():
            try:
                price_data = self.jq_client.get_price(
                    securities=stock_code,
                    start_date=start_date,
                    end_date=end_date,
                    frequency='daily',
                    auto_adjust_date=True
                )
                if not price_data.empty:
                    return price_data
            except Exception as e:
                logger.debug(f"JQData获取价格数据失败 {stock_code}: {e}")
        
        # 备选AKShare（需要转换代码格式）
        if self.use_akshare:
            try:
                # 转换代码格式：000001.XSHE -> 000001
                code = stock_code.replace('.XSHE', '').replace('.XSHG', '')
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date=start_date.replace('-', ''),
                    end_date=end_date.replace('-', ''),
                    adjust="qfq"  # 前复权
                )
                if df is not None and not df.empty:
                    # 转换为JQData格式
                    df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'turnover', 'amplitude', 'change_pct', 'change_amount', 'turnover_rate']
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                    return df[['open', 'close', 'high', 'low', 'volume']]
            except Exception as e:
                logger.debug(f"AKShare获取价格数据失败 {stock_code}: {e}")
        
        return None
    
    def _get_stock_name(self, stock_code: str) -> str:
        """获取股票名称"""
        # 优先JQData
        if self.jq_client and self.jq_client.is_authenticated():
            try:
                securities = self.jq_client.get_all_securities(types=['stock'], date=None)
                if not securities.empty and stock_code in securities.index:
                    return securities.loc[stock_code, 'display_name']
            except:
                pass
        
        # 备选AKShare
        if self.use_akshare:
            try:
                code = stock_code.replace('.XSHE', '').replace('.XSHG', '')
                df = ak.stock_info_a_code_name()
                if df is not None and not df.empty:
                    # 确保code是字符串格式，且匹配
                    match = df[df['code'].astype(str) == code]
                    if not match.empty:
                        return str(match.iloc[0]['name'])
            except Exception as e:
                logger.debug(f"AKShare获取股票名称失败 {stock_code}: {e}")
        
        return stock_code
    
    def _calculate_momentum(
        self,
        price_data: pd.DataFrame,
        period: str
    ) -> Tuple[float, Dict]:
        """
        计算动量得分
        
        Args:
            price_data: 价格数据
            period: 期限
        
        Returns:
            Tuple[得分, 指标字典]
        """
        if price_data.empty or len(price_data) < 20:
            return 0.0, {}
        
        closes = price_data['close'].values
        volumes = price_data['volume'].values if 'volume' in price_data.columns else None
        
        # 计算不同期限的涨跌幅
        data_len = len(closes)
        
        # 1个月涨跌幅
        change_1m = 0.0
        if data_len >= 20:
            change_1m = ((closes[-1] - closes[-20]) / closes[-20]) * 100
        
        # 3个月涨跌幅
        change_3m = 0.0
        if data_len >= 60:
            change_3m = ((closes[-1] - closes[-60]) / closes[-60]) * 100
        
        # 6个月涨跌幅
        change_6m = 0.0
        if data_len >= 120:
            change_6m = ((closes[-1] - closes[-120]) / closes[-120]) * 100
        
        # 计算RSI
        rsi = self._calculate_rsi(closes, period=14)
        
        # 计算MACD信号
        macd_signal = self._calculate_macd_signal(closes)
        
        # 根据期限选择主要指标
        if period == 'short':
            # 短期：主要看1个月涨跌幅和RSI
            momentum_score = min(abs(change_1m) * 2, 50)  # 涨跌幅贡献最多50分
            if rsi > 70:
                momentum_score += 20  # 超买区域
            elif rsi < 30:
                momentum_score += 10  # 超卖区域
            if macd_signal == 'bullish':
                momentum_score += 30
        elif period == 'medium':
            # 中期：主要看3个月涨跌幅
            momentum_score = min(abs(change_3m) * 1.5, 60)
            if change_3m > 0:
                momentum_score += 20  # 上涨趋势
            if macd_signal == 'bullish':
                momentum_score += 20
        else:  # long
            # 长期：主要看6个月涨跌幅
            momentum_score = min(abs(change_6m) * 1.2, 70)
            if change_6m > 0:
                momentum_score += 20  # 长期上涨趋势
            if change_6m > 30:  # 6个月涨幅超过30%
                momentum_score += 10
        
        momentum_score = min(momentum_score, 100)
        
        indicators = {
            'change_1m': change_1m,
            'change_3m': change_3m,
            'change_6m': change_6m,
            'rsi': rsi,
            'macd_signal': macd_signal
        }
        
        return momentum_score, indicators
    
    def _calculate_rsi(self, closes: np.ndarray, period: int = 14) -> float:
        """计算RSI指标"""
        if len(closes) < period + 1:
            return 50.0
        
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd_signal(self, closes: np.ndarray) -> str:
        """计算MACD信号"""
        if len(closes) < 26:
            return 'neutral'
        
        # 简化的MACD计算
        ema12 = pd.Series(closes).ewm(span=12, adjust=False).mean().iloc[-1]
        ema26 = pd.Series(closes).ewm(span=26, adjust=False).mean().iloc[-1]
        macd = ema12 - ema26
        
        if macd > 0:
            return 'bullish'
        elif macd < 0:
            return 'bearish'
        else:
            return 'neutral'
    
    def _calculate_growth(
        self,
        stock_code: str,
        date: str
    ) -> Tuple[float, Dict]:
        """
        计算成长潜力得分
        
        Args:
            stock_code: 股票代码
            date: 日期
        
        Returns:
            Tuple[得分, 指标字典]
        """
        if not self.jq_client or not self.jq_client.is_authenticated():
            return 0.0, {}
        
        try:
            # 查询财务指标 (使用正确的JQData字段名)
            q = query(
                valuation.code,
                indicator.roe,
                indicator.inc_net_profit_year_on_year,  # 净利润同比增长率
                indicator.inc_revenue_year_on_year,  # 营收同比增长率
                indicator.eps  # 每股收益（替代eps_growth_rate）
            ).filter(
                valuation.code == stock_code
            )
            
            df = self.jq_client.get_fundamentals(q, date=date)
            
            if df.empty:
                return 0.0, {}
            
            row = df.iloc[0]
            roe = row.get('roe', 0) or 0
            net_profit_growth = row.get('inc_net_profit_year_on_year', 0) or 0
            revenue_growth = row.get('inc_revenue_year_on_year', 0) or 0
            eps_growth = net_profit_growth  # 用净利润增长率近似EPS增长率
            
            # 计算成长得分
            growth_score = 0.0
            
            # ROE贡献（最高30分）
            if roe > 20:
                growth_score += 30
            elif roe > 15:
                growth_score += 20
            elif roe > 10:
                growth_score += 10
            
            # 净利润增长率贡献（最高30分）
            if net_profit_growth > 50:
                growth_score += 30
            elif net_profit_growth > 30:
                growth_score += 20
            elif net_profit_growth > 20:
                growth_score += 10
            
            # 营收增长率贡献（最高20分）
            if revenue_growth > 30:
                growth_score += 20
            elif revenue_growth > 20:
                growth_score += 15
            elif revenue_growth > 10:
                growth_score += 10
            
            # EPS增长率贡献（最高20分）
            if eps_growth > 30:
                growth_score += 20
            elif eps_growth > 20:
                growth_score += 15
            elif eps_growth > 10:
                growth_score += 10
            
            growth_score = min(growth_score, 100)
            
            indicators = {
                'roe': roe,
                'net_profit_growth': net_profit_growth,
                'revenue_growth': revenue_growth,
                'eps_growth': eps_growth
            }
            
            return growth_score, indicators
            
        except Exception as e:
            logger.debug(f"计算成长潜力失败 {stock_code}: {e}")
            return 0.0, {}

