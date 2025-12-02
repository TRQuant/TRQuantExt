# -*- coding: utf-8 -*-
"""
强势股扫描器 - 非主线强势股扫描
================================

功能:
1. 涨幅榜扫描 - 今日/近5日涨幅前列
2. 创新高扫描 - 60日/120日/250日新高
3. 连续上涨扫描 - 连续N天上涨
4. 量价齐升扫描 - 放量上涨
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from enum import Enum
import pandas as pd

logger = logging.getLogger(__name__)


class ScanType(Enum):
    """扫描类型"""
    TOP_GAINERS = "top_gainers"       # 涨幅榜
    NEW_HIGH = "new_high"             # 创新高
    CONSECUTIVE_UP = "consecutive_up"  # 连续上涨
    VOLUME_BREAKOUT = "volume_breakout"  # 放量上涨


@dataclass
class StrongStock:
    """强势股票"""
    code: str
    name: str
    price: float
    change_pct: float
    scan_type: ScanType
    
    # 可选字段
    volume: float = 0
    turnover: float = 0  # 成交额（亿）
    high_days: int = 0   # 新高周期（60/120/250）
    up_days: int = 0     # 连续上涨天数
    volume_ratio: float = 0  # 量比
    industry: str = ""
    score: float = 0     # 综合评分
    
    def to_dict(self) -> dict:
        return {
            'code': self.code,
            'name': self.name,
            'price': self.price,
            'change_pct': self.change_pct,
            'scan_type': self.scan_type.value,
            'volume': self.volume,
            'turnover': self.turnover,
            'high_days': self.high_days,
            'up_days': self.up_days,
            'volume_ratio': self.volume_ratio,
            'industry': self.industry,
            'score': self.score
        }


@dataclass
class ScanResult:
    """扫描结果"""
    scan_date: str
    scan_type: ScanType
    stocks: List[StrongStock]
    total_count: int
    scan_time: float = 0
    
    def to_dict(self) -> dict:
        return {
            'scan_date': self.scan_date,
            'scan_type': self.scan_type.value,
            'stocks': [s.to_dict() for s in self.stocks],
            'total_count': self.total_count,
            'scan_time': self.scan_time
        }


class StrongStockScanner:
    """强势股扫描器"""
    
    def __init__(self):
        self._cache: Dict[str, ScanResult] = {}
        self._max_retries = 3
        self._retry_delay = 2
    
    def _fetch_with_retry(self, fetch_func, description: str):
        """带重试的数据获取"""
        import time
        
        for attempt in range(self._max_retries):
            try:
                return fetch_func()
            except Exception as e:
                if attempt < self._max_retries - 1:
                    logger.warning(f"{description} 第{attempt+1}次失败: {e}，重试中...")
                    time.sleep(self._retry_delay)
                else:
                    logger.error(f"{description} 失败: {e}")
                    raise
    
    def scan_top_gainers(self, top_n: int = 50) -> ScanResult:
        """
        扫描涨幅榜
        
        Args:
            top_n: 返回前N只股票
        
        Returns:
            ScanResult
        """
        logger.info(f"🔍 扫描涨幅榜 TOP {top_n}")
        start_time = datetime.now()
        stocks = []
        
        try:
            import akshare as ak
            
            # 尝试主API
            df = None
            try:
                df = self._fetch_with_retry(
                    lambda: ak.stock_zh_a_spot_em(),
                    "获取涨幅榜"
                )
            except Exception as e:
                logger.warning(f"主API失败，尝试备用API: {e}")
                # 备用方案：使用概念板块资金流获取活跃股
                try:
                    concept_df = ak.stock_fund_flow_concept(symbol="即时")
                    if concept_df is not None and not concept_df.empty:
                        # 获取涨幅最大的概念中的领涨股
                        top_concepts = concept_df.nlargest(top_n, '行业-涨跌幅')
                        
                        for _, concept in top_concepts.iterrows():
                            try:
                                leader_stock = concept.get('领涨股', '')
                                leader_change = float(concept.get('领涨股-涨跌幅', 0) or 0)
                                leader_price = float(concept.get('当前价', 0) or 0)
                                industry = concept.get('行业', '')
                                
                                if leader_stock:
                                    # 构造股票代码（领涨股只有名称，需要查询代码）
                                    stock = StrongStock(
                                        code='',  # 没有代码
                                        name=leader_stock,
                                        price=leader_price,
                                        change_pct=leader_change,
                                        scan_type=ScanType.TOP_GAINERS,
                                        industry=industry
                                    )
                                    stock.score = self._calculate_score(stock)
                                    stocks.append(stock)
                            except:
                                continue
                except Exception as e2:
                    logger.error(f"备用API也失败: {e2}")
            
            if df is not None and not df.empty:
                # 过滤ST股和涨跌停
                df = df[~df['名称'].str.contains('ST|退', na=False)]
                df = df[df['涨跌幅'].notna() & (df['涨跌幅'] < 20)]  # 排除涨停
                
                # 按涨幅排序
                df = df.sort_values('涨跌幅', ascending=False).head(top_n)
                
                for _, row in df.iterrows():
                    try:
                        stock = StrongStock(
                            code=row['代码'],
                            name=row['名称'],
                            price=float(row.get('最新价', 0) or 0),
                            change_pct=float(row.get('涨跌幅', 0) or 0),
                            scan_type=ScanType.TOP_GAINERS,
                            turnover=float(row.get('成交额', 0) or 0) / 1e8,
                            volume_ratio=float(row.get('量比', 1) or 1)
                        )
                        stock.score = self._calculate_score(stock)
                        stocks.append(stock)
                    except Exception as e:
                        continue
                        
        except Exception as e:
            logger.error(f"扫描涨幅榜失败: {e}")
        
        scan_time = (datetime.now() - start_time).total_seconds()
        result = ScanResult(
            scan_date=date.today().strftime('%Y-%m-%d'),
            scan_type=ScanType.TOP_GAINERS,
            stocks=stocks,
            total_count=len(stocks),
            scan_time=scan_time
        )
        
        logger.info(f"✅ 涨幅榜扫描完成: {len(stocks)} 只股票, 耗时 {scan_time:.1f}秒")
        return result
    
    def scan_new_highs(self, period: int = 60, top_n: int = 50) -> ScanResult:
        """
        扫描创新高股票
        
        Args:
            period: 新高周期（60/120/250日）
            top_n: 返回前N只
        
        Returns:
            ScanResult
        """
        logger.info(f"🔍 扫描 {period}日创新高")
        start_time = datetime.now()
        stocks = []
        
        try:
            import akshare as ak
            
            # 获取实时行情（带重试）
            df = self._fetch_with_retry(
                lambda: ak.stock_zh_a_spot_em(),
                "获取创新高数据"
            )
            
            if df is not None and not df.empty:
                # 过滤
                df = df[~df['名称'].str.contains('ST|退', na=False)]
                
                # 获取52周最高
                if '52周最高' in df.columns:
                    df['near_high'] = df['最新价'].astype(float) / df['52周最高'].astype(float)
                    
                    # 筛选接近新高的（95%以上）
                    df = df[df['near_high'] >= 0.95]
                    df = df.sort_values('near_high', ascending=False).head(top_n)
                    
                    for _, row in df.iterrows():
                        try:
                            stock = StrongStock(
                                code=row['代码'],
                                name=row['名称'],
                                price=float(row.get('最新价', 0) or 0),
                                change_pct=float(row.get('涨跌幅', 0) or 0),
                                scan_type=ScanType.NEW_HIGH,
                                high_days=period,
                                turnover=float(row.get('成交额', 0) or 0) / 1e8
                            )
                            stock.score = self._calculate_score(stock)
                            stocks.append(stock)
                        except:
                            continue
                            
        except Exception as e:
            logger.error(f"扫描创新高失败: {e}")
        
        scan_time = (datetime.now() - start_time).total_seconds()
        result = ScanResult(
            scan_date=date.today().strftime('%Y-%m-%d'),
            scan_type=ScanType.NEW_HIGH,
            stocks=stocks,
            total_count=len(stocks),
            scan_time=scan_time
        )
        
        logger.info(f"✅ 创新高扫描完成: {len(stocks)} 只股票")
        return result
    
    def scan_consecutive_up(self, min_days: int = 3, top_n: int = 50) -> ScanResult:
        """
        扫描连续上涨股票
        
        Args:
            min_days: 最少连续上涨天数
            top_n: 返回前N只
        
        Returns:
            ScanResult
        """
        logger.info(f"🔍 扫描连续上涨 >= {min_days}天")
        start_time = datetime.now()
        stocks = []
        
        try:
            import akshare as ak
            
            # 获取连涨连跌数据（带重试）
            df = self._fetch_with_retry(
                lambda: ak.stock_rank_lxsz_ths(),
                "获取连涨数据"
            )
            
            if df is not None and not df.empty:
                # 筛选连涨
                df = df[df['连涨天数'] >= min_days]
                df = df[~df['名称'].str.contains('ST|退', na=False)]
                df = df.sort_values('连涨天数', ascending=False).head(top_n)
                
                for _, row in df.iterrows():
                    try:
                        stock = StrongStock(
                            code=str(row.get('代码', '')),
                            name=str(row.get('名称', '')),
                            price=float(row.get('最新价', 0) or 0),
                            change_pct=float(row.get('涨跌幅', 0) or 0),
                            scan_type=ScanType.CONSECUTIVE_UP,
                            up_days=int(row.get('连涨天数', 0) or 0)
                        )
                        stock.score = self._calculate_score(stock)
                        stocks.append(stock)
                    except:
                        continue
                        
        except Exception as e:
            logger.error(f"扫描连续上涨失败: {e}")
        
        scan_time = (datetime.now() - start_time).total_seconds()
        return ScanResult(
            scan_date=date.today().strftime('%Y-%m-%d'),
            scan_type=ScanType.CONSECUTIVE_UP,
            stocks=stocks,
            total_count=len(stocks),
            scan_time=scan_time
        )
    
    def scan_volume_breakout(self, volume_ratio_min: float = 2.0, top_n: int = 50) -> ScanResult:
        """
        扫描放量上涨股票
        
        Args:
            volume_ratio_min: 最小量比
            top_n: 返回前N只
        
        Returns:
            ScanResult
        """
        logger.info(f"🔍 扫描放量上涨 (量比 >= {volume_ratio_min})")
        start_time = datetime.now()
        stocks = []
        
        try:
            import akshare as ak
            
            df = self._fetch_with_retry(
                lambda: ak.stock_zh_a_spot_em(),
                "获取放量上涨数据"
            )
            
            if df is not None and not df.empty:
                df = df[~df['名称'].str.contains('ST|退', na=False)]
                df = df[df['涨跌幅'].astype(float) > 0]  # 上涨
                df = df[df['量比'].astype(float) >= volume_ratio_min]  # 放量
                
                df = df.sort_values('量比', ascending=False).head(top_n)
                
                for _, row in df.iterrows():
                    try:
                        stock = StrongStock(
                            code=row['代码'],
                            name=row['名称'],
                            price=float(row.get('最新价', 0) or 0),
                            change_pct=float(row.get('涨跌幅', 0) or 0),
                            scan_type=ScanType.VOLUME_BREAKOUT,
                            volume_ratio=float(row.get('量比', 0) or 0),
                            turnover=float(row.get('成交额', 0) or 0) / 1e8
                        )
                        stock.score = self._calculate_score(stock)
                        stocks.append(stock)
                    except:
                        continue
                        
        except Exception as e:
            logger.error(f"扫描放量上涨失败: {e}")
        
        scan_time = (datetime.now() - start_time).total_seconds()
        return ScanResult(
            scan_date=date.today().strftime('%Y-%m-%d'),
            scan_type=ScanType.VOLUME_BREAKOUT,
            stocks=stocks,
            total_count=len(stocks),
            scan_time=scan_time
        )
    
    def scan_all(self, top_n: int = 30) -> Dict[str, ScanResult]:
        """
        执行全部扫描
        
        Returns:
            Dict[scan_type, ScanResult]
        """
        logger.info("🚀 开始全市场强势股扫描...")
        
        results = {}
        
        # 涨幅榜
        results['top_gainers'] = self.scan_top_gainers(top_n)
        
        # 创新高
        results['new_high'] = self.scan_new_highs(60, top_n)
        
        # 连续上涨
        results['consecutive_up'] = self.scan_consecutive_up(3, top_n)
        
        # 放量上涨
        results['volume_breakout'] = self.scan_volume_breakout(2.0, top_n)
        
        total = sum(r.total_count for r in results.values())
        logger.info(f"✅ 全市场扫描完成，共找到 {total} 只强势股")
        
        return results
    
    def _calculate_score(self, stock: StrongStock) -> float:
        """计算综合评分"""
        score = 50.0
        
        # 涨幅得分 (0-30分)
        if stock.change_pct > 0:
            score += min(stock.change_pct * 3, 30)
        
        # 量比得分 (0-20分)
        if stock.volume_ratio > 1:
            score += min((stock.volume_ratio - 1) * 5, 20)
        
        # 连涨天数 (0-15分)
        if stock.up_days > 0:
            score += min(stock.up_days * 3, 15)
        
        # 新高周期 (0-15分)
        if stock.high_days > 0:
            score += min(stock.high_days / 20, 15)
        
        # 成交额加分 (0-10分)
        if stock.turnover > 1:
            score += min(stock.turnover * 2, 10)
        
        return min(score, 100)


# 单例
_scanner = None

def get_strong_stock_scanner() -> StrongStockScanner:
    global _scanner
    if _scanner is None:
        _scanner = StrongStockScanner()
    return _scanner

