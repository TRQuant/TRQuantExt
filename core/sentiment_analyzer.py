# -*- coding: utf-8 -*-
"""
市场情绪分析器
==============

整合多渠道信息进行情绪分析：
1. 财经新闻情绪
2. 社交媒体情绪（微博、雪球等）
3. 搜索热度
4. 舆情监控

情绪来源：
- AKShare财经新闻
- 百度指数（通过AKShare）
- 雪球热帖（模拟）
- 自定义观点输入
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import re

logger = logging.getLogger(__name__)


class SentimentLevel(Enum):
    """情绪等级"""
    VERY_BULLISH = "very_bullish"    # 极度乐观
    BULLISH = "bullish"              # 乐观
    NEUTRAL = "neutral"              # 中性
    BEARISH = "bearish"              # 悲观
    VERY_BEARISH = "very_bearish"    # 极度悲观


class OpinionSource(Enum):
    """观点来源"""
    NEWS = "news"              # 财经新闻
    SOCIAL_MEDIA = "social"    # 社交媒体
    EXPERT = "expert"          # 专家观点
    RESEARCH = "research"      # 研报
    CUSTOM = "custom"          # 自定义


@dataclass
class Opinion:
    """观点记录"""
    source: OpinionSource
    author: str
    title: str
    content: str
    sentiment: SentimentLevel
    score: float  # -100 to 100
    timestamp: str
    url: str = ""
    keywords: List[str] = field(default_factory=list)


@dataclass
class SentimentResult:
    """情绪分析结果"""
    analysis_date: str
    overall_sentiment: SentimentLevel
    overall_score: float  # -100 to 100
    
    # 各渠道情绪
    news_sentiment: float = 0.0
    social_sentiment: float = 0.0
    expert_sentiment: float = 0.0
    
    # 情绪指标
    fear_greed_index: float = 50.0  # 0-100，50为中性
    bullish_ratio: float = 0.5       # 看多比例
    
    # 热门话题
    hot_topics: List[str] = field(default_factory=list)
    
    # 观点列表
    opinions: List[Opinion] = field(default_factory=list)
    
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'analysis_date': self.analysis_date,
            'overall_sentiment': self.overall_sentiment.value,
            'overall_score': self.overall_score,
            'news_sentiment': self.news_sentiment,
            'social_sentiment': self.social_sentiment,
            'expert_sentiment': self.expert_sentiment,
            'fear_greed_index': self.fear_greed_index,
            'bullish_ratio': self.bullish_ratio,
            'hot_topics': self.hot_topics,
            'opinions_count': len(self.opinions),
            'summary': self.summary,
            'recommendations': self.recommendations
        }


class SentimentAnalyzer:
    """
    市场情绪分析器
    
    功能：
    1. 财经新闻情绪分析
    2. 社交媒体情绪监测
    3. 综合情绪评分
    4. 逆向指标提示
    """
    
    # 情绪关键词
    BULLISH_KEYWORDS = [
        '利好', '上涨', '突破', '新高', '牛市', '加仓', '看多', '反弹',
        '放量', '涨停', '资金流入', '北向买入', '政策支持', '业绩增长',
        '低估', '机会', '布局', '底部', '启动', '爆发'
    ]
    
    BEARISH_KEYWORDS = [
        '利空', '下跌', '破位', '新低', '熊市', '减仓', '看空', '调整',
        '缩量', '跌停', '资金流出', '北向卖出', '政策收紧', '业绩下滑',
        '高估', '风险', '见顶', '顶部', '回调', '暴跌'
    ]
    
    def __init__(self):
        self._custom_opinions: List[Opinion] = []
    
    def analyze(self) -> SentimentResult:
        """执行情绪分析"""
        logger.info("😊 开始市场情绪分析...")
        
        result = SentimentResult(
            analysis_date=date.today().strftime('%Y-%m-%d'),
            overall_sentiment=SentimentLevel.NEUTRAL,
            overall_score=0.0
        )
        
        try:
            # 1. 分析财经新闻
            news_opinions = self._analyze_news()
            result.opinions.extend(news_opinions)
            result.news_sentiment = self._calculate_avg_score(news_opinions)
            
            # 2. 分析社交媒体（搜索热度等）
            social_data = self._analyze_social()
            result.social_sentiment = social_data.get('score', 0)
            result.hot_topics = social_data.get('topics', [])
            
            # 3. 添加自定义观点
            result.opinions.extend(self._custom_opinions)
            custom_score = self._calculate_avg_score(self._custom_opinions)
            result.expert_sentiment = custom_score
            
            # 4. 计算综合情绪
            self._calculate_overall(result)
            
            # 5. 计算恐惧贪婪指数
            result.fear_greed_index = self._calculate_fear_greed(result)
            
            # 6. 生成摘要和建议
            result.summary = self._generate_summary(result)
            result.recommendations = self._generate_recommendations(result)
            
            logger.info(f"😊 情绪分析完成: {result.overall_sentiment.value} ({result.overall_score:.1f})")
            
        except Exception as e:
            logger.error(f"情绪分析失败: {e}")
            result.summary = f"分析出错: {e}"
        
        return result
    
    def add_custom_opinion(
        self,
        author: str,
        title: str,
        content: str,
        is_bullish: bool = True,
        score: Optional[float] = None
    ):
        """
        添加自定义观点
        
        Args:
            author: 作者/来源
            title: 标题
            content: 内容
            is_bullish: 是否看多
            score: 自定义评分（-100到100）
        """
        if score is None:
            score = 50 if is_bullish else -50
        
        sentiment = (
            SentimentLevel.BULLISH if score > 30 else
            SentimentLevel.BEARISH if score < -30 else
            SentimentLevel.NEUTRAL
        )
        
        opinion = Opinion(
            source=OpinionSource.CUSTOM,
            author=author,
            title=title,
            content=content,
            sentiment=sentiment,
            score=score,
            timestamp=datetime.now().isoformat(),
            keywords=self._extract_keywords(content)
        )
        
        self._custom_opinions.append(opinion)
        logger.info(f"📝 已添加观点: {author} - {title}")
    
    def clear_custom_opinions(self):
        """清空自定义观点"""
        self._custom_opinions = []
    
    def _analyze_news(self) -> List[Opinion]:
        """分析财经新闻"""
        opinions = []
        
        try:
            import akshare as ak
            
            # 获取财经新闻
            try:
                df = ak.stock_news_em()
                
                if df is not None and not df.empty:
                    for _, row in df.head(20).iterrows():
                        title = str(row.get('新闻标题', row.get('title', '')))
                        content = str(row.get('新闻内容', title))
                        
                        # 分析情绪
                        score = self._analyze_text_sentiment(title + " " + content)
                        sentiment = self._score_to_level(score)
                        
                        opinions.append(Opinion(
                            source=OpinionSource.NEWS,
                            author="东方财富",
                            title=title[:50],
                            content=content[:200],
                            sentiment=sentiment,
                            score=score,
                            timestamp=str(row.get('发布时间', '')),
                            keywords=self._extract_keywords(title)
                        ))
                        
            except Exception as e:
                logger.debug(f"获取新闻失败: {e}")
                
        except ImportError:
            logger.warning("akshare未安装")
        
        return opinions
    
    def _analyze_social(self) -> Dict:
        """分析社交媒体情绪"""
        result = {
            'score': 0,
            'topics': []
        }
        
        try:
            import akshare as ak
            
            # 获取百度指数热搜（如果可用）
            try:
                # 获取热门股票搜索
                df = ak.stock_hot_rank_em()
                
                if df is not None and not df.empty:
                    # 提取热门话题
                    hot_stocks = df.head(10)['股票名称'].tolist() if '股票名称' in df.columns else []
                    result['topics'] = hot_stocks[:5]
                    
                    # 简单的热度评分
                    result['score'] = 20  # 有热度即为正向
                    
            except Exception as e:
                logger.debug(f"获取热搜失败: {e}")
                
        except ImportError:
            pass
        
        return result
    
    def _analyze_text_sentiment(self, text: str) -> float:
        """分析文本情绪"""
        if not text:
            return 0.0
        
        text = text.lower()
        
        bullish_count = sum(1 for kw in self.BULLISH_KEYWORDS if kw in text)
        bearish_count = sum(1 for kw in self.BEARISH_KEYWORDS if kw in text)
        
        total = bullish_count + bearish_count
        if total == 0:
            return 0.0
        
        # 计算分数：-100 到 100
        score = (bullish_count - bearish_count) / total * 100
        
        return score
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        keywords = []
        
        for kw in self.BULLISH_KEYWORDS + self.BEARISH_KEYWORDS:
            if kw in text:
                keywords.append(kw)
        
        return keywords[:5]  # 最多5个
    
    def _score_to_level(self, score: float) -> SentimentLevel:
        """分数转情绪等级"""
        if score >= 60:
            return SentimentLevel.VERY_BULLISH
        elif score >= 20:
            return SentimentLevel.BULLISH
        elif score <= -60:
            return SentimentLevel.VERY_BEARISH
        elif score <= -20:
            return SentimentLevel.BEARISH
        else:
            return SentimentLevel.NEUTRAL
    
    def _calculate_avg_score(self, opinions: List[Opinion]) -> float:
        """计算平均情绪分数"""
        if not opinions:
            return 0.0
        return sum(op.score for op in opinions) / len(opinions)
    
    def _calculate_overall(self, result: SentimentResult):
        """计算综合情绪"""
        # 加权平均（新闻权重0.4，社交0.3，专家0.3）
        weights = [0.4, 0.3, 0.3]
        scores = [result.news_sentiment, result.social_sentiment, result.expert_sentiment]
        
        total_weight = sum(w for w, s in zip(weights, scores) if s != 0)
        if total_weight > 0:
            result.overall_score = sum(w * s for w, s in zip(weights, scores) if s != 0) / total_weight
        else:
            result.overall_score = 0.0
        
        result.overall_sentiment = self._score_to_level(result.overall_score)
        
        # 计算看多比例
        bullish_count = sum(1 for op in result.opinions if op.score > 0)
        total_count = len(result.opinions)
        result.bullish_ratio = bullish_count / total_count if total_count > 0 else 0.5
    
    def _calculate_fear_greed(self, result: SentimentResult) -> float:
        """
        计算恐惧贪婪指数
        
        0 = 极度恐惧
        50 = 中性
        100 = 极度贪婪
        """
        # 将情绪分数(-100到100)转换为恐惧贪婪指数(0到100)
        fear_greed = (result.overall_score + 100) / 2
        return max(0, min(100, fear_greed))
    
    def _generate_summary(self, result: SentimentResult) -> str:
        """生成情绪摘要"""
        sentiment_text = {
            SentimentLevel.VERY_BULLISH: "极度乐观",
            SentimentLevel.BULLISH: "偏向乐观",
            SentimentLevel.NEUTRAL: "相对中性",
            SentimentLevel.BEARISH: "偏向悲观",
            SentimentLevel.VERY_BEARISH: "极度悲观"
        }
        
        fg_text = (
            "贪婪" if result.fear_greed_index > 70 else
            "乐观" if result.fear_greed_index > 55 else
            "中性" if result.fear_greed_index > 45 else
            "谨慎" if result.fear_greed_index > 30 else
            "恐惧"
        )
        
        return (
            f"当前市场情绪{sentiment_text[result.overall_sentiment]}，"
            f"恐惧贪婪指数{result.fear_greed_index:.0f}（{fg_text}），"
            f"看多比例{result.bullish_ratio:.0%}。"
        )
    
    def _generate_recommendations(self, result: SentimentResult) -> List[str]:
        """生成基于情绪的建议"""
        recommendations = []
        
        # 极端情绪时的逆向提示
        if result.fear_greed_index > 80:
            recommendations.append("⚠️ 市场极度贪婪，注意回调风险，考虑逐步减仓")
        elif result.fear_greed_index < 20:
            recommendations.append("💡 市场极度恐惧，可能是布局良机，考虑逢低吸纳")
        
        # 常规建议
        if result.overall_sentiment in [SentimentLevel.BULLISH, SentimentLevel.VERY_BULLISH]:
            recommendations.append("顺势而为，但注意止盈")
        elif result.overall_sentiment in [SentimentLevel.BEARISH, SentimentLevel.VERY_BEARISH]:
            recommendations.append("保守操作，降低仓位")
        else:
            recommendations.append("情绪中性，精选个股")
        
        # 热门话题相关建议
        if result.hot_topics:
            recommendations.append(f"热门关注: {', '.join(result.hot_topics[:3])}")
        
        return recommendations


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """获取情绪分析器"""
    return SentimentAnalyzer()

