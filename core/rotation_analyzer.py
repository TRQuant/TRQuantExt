# -*- coding: utf-8 -*-
"""
板块轮动分析器
==============

从多个外部数据源获取板块轮动数据：
1. AKShare - 板块资金流、涨跌幅排名
2. 东方财富 - 概念板块热度
3. 历史快照对比

遵循时间维度设计原则
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import pandas as pd

logger = logging.getLogger(__name__)

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.warning("AKShare未安装，部分轮动分析功能受限")


@dataclass
class SectorRotationSignal:
    """板块轮动信号"""
    sector_name: str
    current_rank: int
    prev_rank: int
    rank_change: int
    current_change_pct: float   # 当前涨跌幅
    avg_change_pct: float       # 平均涨跌幅
    momentum: str               # 升温/降温/稳定
    capital_flow: float         # 资金流向（亿）
    heat_score: float           # 热度评分


@dataclass
class RotationAnalysisResult:
    """轮动分析结果"""
    analysis_date: str
    rising_sectors: List[SectorRotationSignal]    # 升温板块
    falling_sectors: List[SectorRotationSignal]   # 降温板块
    stable_sectors: List[SectorRotationSignal]    # 稳定板块
    rotation_summary: str                          # 轮动总结
    data_source: str                               # 数据来源
    raw_data: Dict                                 # 原始数据


class RotationAnalyzer:
    """板块轮动分析器"""
    
    def __init__(self):
        self._cache = {}
        self._cache_time = {}
    
    def analyze_rotation(self, days: int = 5) -> Optional[RotationAnalysisResult]:
        """
        分析板块轮动
        
        Args:
            days: 分析天数
            
        Returns:
            轮动分析结果
        """
        # 优先使用AKShare获取实时数据
        if AKSHARE_AVAILABLE:
            result = self._analyze_with_akshare(days)
            if result:
                return result
        
        # 备用：使用历史快照
        result = self._analyze_with_snapshots(days)
        return result
    
    def _analyze_with_akshare(self, days: int) -> Optional[RotationAnalysisResult]:
        """使用AKShare分析轮动"""
        import time
        
        try:
            # 检查缓存
            cache_key = f"rotation_{days}"
            if cache_key in self._cache:
                cache_age = (datetime.now() - self._cache_time.get(cache_key, datetime.min)).seconds
                if cache_age < 300:  # 5分钟缓存
                    logger.info("使用缓存的轮动分析结果")
                    return self._cache[cache_key]
            
            rising = []
            falling = []
            stable = []
            raw_data = {}
            
            # 1. 优先使用资金流向数据（更可靠）
            df_flow = None
            for attempt in range(3):
                try:
                    df_flow = ak.stock_fund_flow_concept(symbol="即时")
                    if df_flow is not None and not df_flow.empty:
                        logger.info(f"成功获取资金流向数据: {len(df_flow)} 个行业")
                        break
                except Exception as e:
                    logger.warning(f"获取资金流向失败(尝试{attempt+1}/3): {e}")
                    if attempt < 2:
                        time.sleep(2)
            
            if df_flow is not None and not df_flow.empty:
                raw_data['fund_flow'] = df_flow.head(50).to_dict('records')
                
                for i, row in df_flow.head(40).iterrows():
                    name = row.get('行业', '')
                    change_pct = float(row.get('行业-涨跌幅', 0) or 0)
                    net_flow = float(row.get('净额', 0) or 0)  # 净额单位：亿
                    
                    signal = SectorRotationSignal(
                        sector_name=name,
                        current_rank=int(row.get('序号', i + 1)),
                        prev_rank=int(row.get('序号', i + 1)),
                        rank_change=0,
                        current_change_pct=change_pct,
                        avg_change_pct=change_pct,  # 资金流向没有5日数据
                        momentum="升温" if change_pct > 2 else ("降温" if change_pct < -2 else "稳定"),
                        capital_flow=net_flow,
                        heat_score=max(0, min(100, 50 + change_pct * 10 + net_flow * 2))
                    )
                    
                    if change_pct > 2:
                        rising.append(signal)
                    elif change_pct < -2:
                        falling.append(signal)
                    else:
                        stable.append(signal)
            
            # 2. 备用：获取概念板块涨跌幅排名
            if not rising and not falling:
                df_concept = None
                for attempt in range(2):
                    try:
                        df_concept = ak.stock_board_concept_name_em()
                        if df_concept is not None and not df_concept.empty:
                            break
                    except Exception as e:
                        logger.warning(f"获取概念板块失败(尝试{attempt+1}/2): {e}")
                        if attempt < 1:
                            time.sleep(1)
                
                if df_concept is not None and not df_concept.empty:
                    raw_data['concept_ranking'] = df_concept.head(50).to_dict('records')
                    
                    for i, row in df_concept.head(30).iterrows():
                        name = row.get('板块名称', '')
                        change_pct = float(row.get('涨跌幅', 0) or 0)
                        avg_5d = float(row.get('5日涨跌幅', change_pct) or change_pct)
                        
                        signal = SectorRotationSignal(
                            sector_name=name,
                            current_rank=i + 1,
                            prev_rank=i + 1,
                            rank_change=0,
                            current_change_pct=change_pct,
                            avg_change_pct=avg_5d,
                            momentum="持续升温" if avg_5d > 5 else ("升温" if change_pct > 2 else ("持续降温" if avg_5d < -5 else ("降温" if change_pct < -2 else "稳定"))),
                            capital_flow=0,
                            heat_score=max(0, min(100, 50 + change_pct * 10))
                        )
                        
                        if change_pct > 2:
                            rising.append(signal)
                        elif change_pct < -2:
                            falling.append(signal)
                        else:
                            stable.append(signal)
            
            if not rising and not falling:
                logger.warning("无法获取板块数据，尝试使用历史快照")
                return None
            
            # 按热度排序
            rising.sort(key=lambda x: x.heat_score, reverse=True)
            falling.sort(key=lambda x: x.heat_score)
            
            # 生成总结
            summary = self._generate_rotation_summary(rising, falling, stable)
            
            result = RotationAnalysisResult(
                analysis_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
                rising_sectors=rising[:10],
                falling_sectors=falling[:10],
                stable_sectors=stable[:5],
                rotation_summary=summary,
                data_source="AKShare",
                raw_data=raw_data
            )
            
            # 缓存
            self._cache[cache_key] = result
            self._cache_time[cache_key] = datetime.now()
            
            logger.info(f"板块轮动分析完成: 升温{len(rising)}个, 降温{len(falling)}个")
            return result
            
        except Exception as e:
            logger.error(f"AKShare轮动分析失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _analyze_with_snapshots(self, days: int) -> Optional[RotationAnalysisResult]:
        """使用历史快照分析轮动"""
        try:
            from core.time_dimension_manager import create_time_dimension_manager, Period
            
            tdm = create_time_dimension_manager()
            rotation = tdm.analyze_rotation(days=days, period=Period.MEDIUM)
            
            if 'error' in rotation:
                logger.warning(f"快照轮动分析: {rotation['error']}")
                return None
            
            rising = []
            falling = []
            
            for r in rotation.get('rising_mainlines', []):
                signal = SectorRotationSignal(
                    sector_name=r.get('mainline', ''),
                    current_rank=0,
                    prev_rank=0,
                    rank_change=0,
                    current_change_pct=r.get('change', 0),
                    avg_change_pct=r.get('change', 0),
                    momentum="升温",
                    capital_flow=0,
                    heat_score=r.get('latest_score', 50)
                )
                rising.append(signal)
            
            for f in rotation.get('falling_mainlines', []):
                signal = SectorRotationSignal(
                    sector_name=f.get('mainline', ''),
                    current_rank=0,
                    prev_rank=0,
                    rank_change=0,
                    current_change_pct=f.get('change', 0),
                    avg_change_pct=f.get('change', 0),
                    momentum="降温",
                    capital_flow=0,
                    heat_score=f.get('latest_score', 50)
                )
                falling.append(signal)
            
            return RotationAnalysisResult(
                analysis_date=rotation.get('analyzed_at', '')[:16],
                rising_sectors=rising,
                falling_sectors=falling,
                stable_sectors=[],
                rotation_summary=f"基于{rotation.get('snapshots_count', 0)}个历史快照分析",
                data_source="历史快照",
                raw_data=rotation
            )
            
        except Exception as e:
            logger.error(f"快照轮动分析失败: {e}")
            return None
    
    def _generate_rotation_summary(
        self,
        rising: List[SectorRotationSignal],
        falling: List[SectorRotationSignal],
        stable: List[SectorRotationSignal]
    ) -> str:
        """生成轮动总结"""
        summary_parts = []
        
        if rising:
            top_rising = [s.sector_name for s in rising[:3]]
            summary_parts.append(f"🔥 升温板块: {', '.join(top_rising)}")
        
        if falling:
            top_falling = [s.sector_name for s in falling[:3]]
            summary_parts.append(f"❄️ 降温板块: {', '.join(top_falling)}")
        
        # 判断市场风格
        avg_rising_heat = sum(s.heat_score for s in rising) / len(rising) if rising else 50
        avg_falling_heat = sum(s.heat_score for s in falling) / len(falling) if falling else 50
        
        if avg_rising_heat > 70:
            summary_parts.append("📈 市场情绪偏热，轮动活跃")
        elif avg_falling_heat < 30:
            summary_parts.append("📉 市场情绪偏冷，防御为主")
        else:
            summary_parts.append("📊 市场情绪中性，结构性行情")
        
        return " | ".join(summary_parts)
    
    def get_sector_history(self, sector_name: str, days: int = 20) -> Optional[pd.DataFrame]:
        """获取单个板块的历史数据"""
        if not AKSHARE_AVAILABLE:
            return None
        
        try:
            # 获取概念板块历史
            df = ak.stock_board_concept_hist_em(
                symbol=sector_name,
                period="日k",
                start_date=(datetime.now() - timedelta(days=days)).strftime("%Y%m%d"),
                end_date=datetime.now().strftime("%Y%m%d")
            )
            return df
        except Exception as e:
            logger.warning(f"获取板块历史失败 {sector_name}: {e}")
            return None


def create_rotation_analyzer() -> RotationAnalyzer:
    """创建轮动分析器"""
    return RotationAnalyzer()

