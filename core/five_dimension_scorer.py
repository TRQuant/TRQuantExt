# -*- coding: utf-8 -*-
"""
投资主线五维评分系统
==================

五个评分维度（每维度满分20分，总分100分）：
1. 基本面维度 (Fundamentals): 盈利增长、财务健康、估值水平
2. 技术面维度 (Technical): 市场表现、趋势强度
3. 资金面维度 (Capital): 资金流入、机构持仓
4. 消息面维度 (News): 政策扶持、新闻热度
5. 行业地位维度 (Position): 产业周期、竞争格局

数据来源：JQData, AKShare
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DimensionScore:
    """单维度评分"""
    dimension: str
    score: float  # 0-20
    details: Dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class FiveDimensionScore:
    """五维评分结果"""
    theme_name: str
    theme_code: str
    analysis_date: str
    
    # 五维分数
    fundamental: DimensionScore = None
    technical: DimensionScore = None
    capital: DimensionScore = None
    news: DimensionScore = None
    position: DimensionScore = None
    
    # 综合得分
    total_score: float = 0.0
    rank: int = 0
    
    # 龙头股
    leaders: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'theme_name': self.theme_name,
            'theme_code': self.theme_code,
            'analysis_date': self.analysis_date,
            'total_score': self.total_score,
            'rank': self.rank,
            'fundamental': self.fundamental.score if self.fundamental else 0,
            'technical': self.technical.score if self.technical else 0,
            'capital': self.capital.score if self.capital else 0,
            'news': self.news.score if self.news else 0,
            'position': self.position.score if self.position else 0,
            'leaders': self.leaders
        }
    
    def get_radar_data(self) -> Dict[str, float]:
        """获取雷达图数据"""
        return {
            '基本面': self.fundamental.score if self.fundamental else 0,
            '技术面': self.technical.score if self.technical else 0,
            '资金面': self.capital.score if self.capital else 0,
            '消息面': self.news.score if self.news else 0,
            '行业地位': self.position.score if self.position else 0
        }


class FiveDimensionScorer:
    """
    五维评分器
    
    对投资主线进行全方位评分
    """
    
    def __init__(self):
        self._jq_client = None
        self._init_jq_client()
    
    def _init_jq_client(self):
        """初始化JQData客户端"""
        try:
            from jqdata.client import JQDataClient
            from config.config_manager import get_config_manager
            
            config = get_config_manager()
            jq_config = config.get_config('jqdata')
            
            if jq_config and jq_config.get('username') and jq_config.get('password'):
                self._jq_client = JQDataClient()
                self._jq_client.authenticate(jq_config['username'], jq_config['password'])
                
        except Exception as e:
            logger.warning(f"JQData初始化失败: {e}")
    
    def score_theme(self, theme_name: str, theme_code: str, stocks: List[str]) -> FiveDimensionScore:
        """
        对单个主题进行五维评分
        
        Args:
            theme_name: 主题名称
            theme_code: 主题代码
            stocks: 成分股列表
        """
        logger.info(f"📊 开始五维评分: {theme_name}")
        
        result = FiveDimensionScore(
            theme_name=theme_name,
            theme_code=theme_code,
            analysis_date=date.today().strftime('%Y-%m-%d')
        )
        
        # 1. 基本面评分
        result.fundamental = self._score_fundamental(stocks)
        
        # 2. 技术面评分
        result.technical = self._score_technical(theme_code, stocks)
        
        # 3. 资金面评分
        result.capital = self._score_capital(stocks)
        
        # 4. 消息面评分
        result.news = self._score_news(theme_name)
        
        # 5. 行业地位评分
        result.position = self._score_position(theme_name, stocks)
        
        # 计算总分
        dimensions = [result.fundamental, result.technical, result.capital, result.news, result.position]
        result.total_score = sum(d.score for d in dimensions if d)
        
        # 提取龙头股
        result.leaders = self._extract_leaders(stocks)
        
        logger.info(f"📊 {theme_name} 五维评分完成: {result.total_score:.1f}分")
        
        return result
    
    def _score_fundamental(self, stocks: List[str]) -> DimensionScore:
        """
        基本面评分
        
        评分因素:
        - 盈利增长（近3年净利润复合增速）
        - 财务健康（ROE、资产负债率）
        - 估值水平（PE相对市场）
        """
        score = 10.0  # 默认中性分
        details = {}
        
        try:
            if self._jq_client and stocks:
                # 获取财务数据
                fundamentals = self._get_fundamentals(stocks[:20])  # 限制数量
                
                if fundamentals:
                    # 1. 盈利增长（0-7分）
                    avg_growth = fundamentals.get('avg_profit_growth', 0)
                    if avg_growth > 30:
                        growth_score = 7
                    elif avg_growth > 20:
                        growth_score = 5
                    elif avg_growth > 10:
                        growth_score = 3
                    elif avg_growth > 0:
                        growth_score = 2
                    else:
                        growth_score = 0
                    
                    details['profit_growth'] = avg_growth
                    
                    # 2. ROE质量（0-6分）
                    avg_roe = fundamentals.get('avg_roe', 0)
                    if avg_roe > 20:
                        roe_score = 6
                    elif avg_roe > 15:
                        roe_score = 4
                    elif avg_roe > 10:
                        roe_score = 2
                    else:
                        roe_score = 1
                    
                    details['avg_roe'] = avg_roe
                    
                    # 3. 估值合理性（0-7分）
                    avg_pe = fundamentals.get('avg_pe', 30)
                    if 10 < avg_pe < 25:
                        pe_score = 7
                    elif 25 <= avg_pe < 40:
                        pe_score = 5
                    elif avg_pe >= 40:
                        pe_score = 2
                    else:
                        pe_score = 3
                    
                    details['avg_pe'] = avg_pe
                    
                    score = growth_score + roe_score + pe_score
            
        except Exception as e:
            logger.warning(f"基本面评分失败: {e}")
        
        desc = f"盈利增速{details.get('profit_growth', 0):.1f}%，ROE {details.get('avg_roe', 0):.1f}%"
        
        return DimensionScore(
            dimension="fundamental",
            score=min(20, max(0, score)),
            details=details,
            description=desc
        )
    
    def _score_technical(self, theme_code: str, stocks: List[str]) -> DimensionScore:
        """
        技术面评分
        
        评分因素:
        - 近期涨跌幅（相对基准）
        - 趋势强度（均线系统）
        - 涨停股数量
        """
        score = 10.0
        details = {}
        
        try:
            import akshare as ak
            
            # 获取板块涨跌幅
            try:
                df = ak.stock_board_concept_name_em()
                if df is not None and not df.empty:
                    # 查找该板块
                    theme_row = df[df['板块名称'].str.contains(theme_code[:4], na=False)]
                    if not theme_row.empty:
                        change = float(theme_row.iloc[0].get('涨跌幅', 0))
                        details['change_pct'] = change
                        
                        # 涨跌幅评分（0-10分）
                        if change > 5:
                            trend_score = 10
                        elif change > 2:
                            trend_score = 8
                        elif change > 0:
                            trend_score = 6
                        elif change > -2:
                            trend_score = 4
                        else:
                            trend_score = 2
                        
                        score = trend_score
            except:
                pass
            
            # 相对强弱评分（0-10分）
            # 这里简化处理，实际应该计算相对于大盘的强度
            relative_score = 5  # 默认
            
            score = min(20, score + relative_score)
            
        except Exception as e:
            logger.warning(f"技术面评分失败: {e}")
        
        desc = f"近期涨幅{details.get('change_pct', 0):.1f}%"
        
        return DimensionScore(
            dimension="technical",
            score=min(20, max(0, score)),
            details=details,
            description=desc
        )
    
    def _score_capital(self, stocks: List[str]) -> DimensionScore:
        """
        资金面评分
        
        评分因素:
        - 主力资金净流入
        - 北向资金持仓变化
        - 成交量变化
        """
        score = 10.0
        details = {}
        
        try:
            import akshare as ak
            
            # 获取资金流向
            try:
                df = ak.stock_individual_fund_flow_rank(indicator="今日")
                if df is not None and not df.empty:
                    # 查找成分股的资金流向
                    inflow_count = 0
                    total_inflow = 0
                    
                    for stock in stocks[:10]:
                        pure_code = stock.split('.')[0] if '.' in stock else stock
                        stock_row = df[df['代码'].astype(str).str.contains(pure_code, na=False)]
                        if not stock_row.empty:
                            try:
                                inflow = float(stock_row.iloc[0].get('主力净流入-净额', 0))
                                if inflow > 0:
                                    inflow_count += 1
                                total_inflow += inflow
                            except:
                                pass
                    
                    details['inflow_count'] = inflow_count
                    details['total_inflow'] = total_inflow / 100000000  # 转为亿
                    
                    # 资金流入评分
                    if total_inflow > 1e9:  # >10亿
                        score = 18
                    elif total_inflow > 5e8:
                        score = 15
                    elif total_inflow > 0:
                        score = 12
                    elif total_inflow > -5e8:
                        score = 8
                    else:
                        score = 4
                        
            except:
                pass
            
        except Exception as e:
            logger.warning(f"资金面评分失败: {e}")
        
        desc = f"主力净流入{details.get('total_inflow', 0):.2f}亿"
        
        return DimensionScore(
            dimension="capital",
            score=min(20, max(0, score)),
            details=details,
            description=desc
        )
    
    def _score_news(self, theme_name: str) -> DimensionScore:
        """
        消息面评分
        
        评分因素:
        - 政策利好程度
        - 新闻热度
        - 舆情倾向
        """
        score = 10.0
        details = {}
        
        try:
            import akshare as ak
            
            # 获取新闻热度
            try:
                df = ak.stock_news_em()
                if df is not None and not df.empty:
                    # 统计相关新闻数量
                    related_news = df[df['新闻标题'].str.contains(theme_name[:2], na=False)]
                    news_count = len(related_news)
                    details['news_count'] = news_count
                    
                    # 新闻数量评分
                    if news_count > 10:
                        score = 15
                    elif news_count > 5:
                        score = 12
                    elif news_count > 0:
                        score = 10
                    else:
                        score = 8
                    
                    # 简单情绪分析
                    positive_keywords = ['利好', '上涨', '突破', '政策支持', '增长']
                    negative_keywords = ['利空', '下跌', '风险', '监管']
                    
                    positive_count = 0
                    negative_count = 0
                    
                    for _, row in related_news.head(10).iterrows():
                        title = str(row.get('新闻标题', ''))
                        if any(kw in title for kw in positive_keywords):
                            positive_count += 1
                        if any(kw in title for kw in negative_keywords):
                            negative_count += 1
                    
                    details['positive_news'] = positive_count
                    details['negative_news'] = negative_count
                    
                    # 情绪调整
                    if positive_count > negative_count * 2:
                        score += 3
                    elif negative_count > positive_count * 2:
                        score -= 3
                        
            except:
                pass
            
        except Exception as e:
            logger.warning(f"消息面评分失败: {e}")
        
        desc = f"相关新闻{details.get('news_count', 0)}条"
        
        return DimensionScore(
            dimension="news",
            score=min(20, max(0, score)),
            details=details,
            description=desc
        )
    
    def _score_position(self, theme_name: str, stocks: List[str]) -> DimensionScore:
        """
        行业地位评分
        
        评分因素:
        - 产业周期阶段
        - 市场集中度
        - 进入壁垒
        """
        score = 10.0
        details = {}
        
        # 热门朝阳行业关键词
        HOT_INDUSTRIES = [
            '人工智能', '芯片', '半导体', '新能源', '光伏', '储能',
            '机器人', '自动驾驶', '云计算', '数据中心', '消费电子',
            '生物医药', '创新药', '医疗器械', 'AI', '算力'
        ]
        
        # 传统/夕阳行业关键词
        DECLINING_INDUSTRIES = [
            '煤炭', '钢铁', '水泥', '房地产', '纺织', '造纸'
        ]
        
        # 行业周期判断
        is_hot = any(kw in theme_name for kw in HOT_INDUSTRIES)
        is_declining = any(kw in theme_name for kw in DECLINING_INDUSTRIES)
        
        if is_hot:
            cycle_score = 8
            details['industry_cycle'] = '朝阳产业'
        elif is_declining:
            cycle_score = 3
            details['industry_cycle'] = '传统产业'
        else:
            cycle_score = 5
            details['industry_cycle'] = '成熟产业'
        
        # 市场规模评分（基于成分股数量）
        stock_count = len(stocks)
        if stock_count > 50:
            size_score = 6
            details['market_size'] = '大型赛道'
        elif stock_count > 20:
            size_score = 5
            details['market_size'] = '中型赛道'
        else:
            size_score = 4
            details['market_size'] = '细分赛道'
        
        # 竞争格局评分（简化）
        competition_score = 5
        details['competition'] = '竞争正常'
        
        score = cycle_score + size_score + competition_score
        
        desc = f"{details.get('industry_cycle', '')}，{details.get('market_size', '')}"
        
        return DimensionScore(
            dimension="position",
            score=min(20, max(0, score)),
            details=details,
            description=desc
        )
    
    def _get_fundamentals(self, stocks: List[str]) -> Dict:
        """获取财务数据"""
        result = {
            'avg_profit_growth': 0,
            'avg_roe': 0,
            'avg_pe': 30
        }
        
        try:
            if self._jq_client:
                import jqdatasdk as jq
                
                # 获取可用日期
                available_date = self._jq_client.get_available_end_date()
                
                # 获取财务数据
                q = jq.query(
                    jq.valuation.code,
                    jq.valuation.pe_ratio,
                    jq.indicator.roe,
                    jq.indicator.inc_net_profit_year_on_year
                ).filter(
                    jq.valuation.code.in_(stocks)
                )
                
                df = jq.get_fundamentals(q, date=available_date)
                
                if df is not None and not df.empty:
                    result['avg_pe'] = df['pe_ratio'].mean() or 30
                    result['avg_roe'] = df['roe'].mean() or 10
                    result['avg_profit_growth'] = df['inc_net_profit_year_on_year'].mean() or 0
                    
        except Exception as e:
            logger.debug(f"获取财务数据失败: {e}")
        
        return result
    
    def _extract_leaders(self, stocks: List[str]) -> List[Dict]:
        """提取龙头股"""
        leaders = []
        
        try:
            import akshare as ak
            
            # 获取涨幅排行
            for stock in stocks[:5]:  # 只取前5个
                pure_code = stock.split('.')[0] if '.' in stock else stock
                
                try:
                    # 获取股票信息
                    df = ak.stock_individual_info_em(symbol=pure_code)
                    if df is not None and not df.empty:
                        name = str(df[df['item'] == '股票简称']['value'].values[0]) if len(df[df['item'] == '股票简称']) > 0 else pure_code
                        
                        leaders.append({
                            'code': stock,
                            'name': name,
                            'reason': '主要成分股'
                        })
                except:
                    leaders.append({
                        'code': stock,
                        'name': pure_code,
                        'reason': '成分股'
                    })
                    
        except Exception as e:
            logger.debug(f"提取龙头股失败: {e}")
        
        return leaders[:3]  # 返回前3个


def get_five_dimension_scorer() -> FiveDimensionScorer:
    """获取五维评分器"""
    return FiveDimensionScorer()

