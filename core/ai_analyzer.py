# -*- coding: utf-8 -*-
"""
AI智能分析器
============

基于大模型的智能选股分析与因子推荐：
1. 整合主线、因子、宏观信息
2. 构建分析提示
3. 调用大模型进行智能分析
4. 返回结构化建议

支持的模型：
- OpenAI GPT (需配置API Key)
- 本地大模型 (通过Ollama)
- Cursor内置模型 (通过API)

功能：
- 智能选股分析
- 因子推荐引擎
- 市场环境研判
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
import os

logger = logging.getLogger(__name__)


@dataclass
class AIAnalysisResult:
    """AI分析结果"""
    summary: str  # 分析摘要
    recommendations: List[Dict]  # 推荐股票列表
    risk_assessment: str  # 风险评估
    market_view: str  # 市场观点
    confidence: float  # 置信度 0-1
    reasoning: str  # 推理过程
    timestamp: str  # 分析时间


@dataclass
class FactorRecommendationResult:
    """因子推荐结果"""
    market_environment: str  # 市场环境描述
    recommended_factors: List[Dict]  # 推荐因子列表 [{name, weight, reason}]
    avoid_factors: List[str]  # 应避免的因子
    development_needs: List[str]  # 需要开发的因子
    period_adjustment: Dict  # 周期调整建议
    confidence: float  # 置信度 0-1
    reasoning: str  # 推理过程
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class AIAnalyzer:
    """AI智能分析器"""
    
    def __init__(self, model_type: str = "local"):
        """
        初始化分析器
        
        Args:
            model_type: 模型类型 - "openai", "local", "cursor"
        """
        self.model_type = model_type
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        
    def analyze_stocks(
        self,
        mainlines: List[Dict],
        factor_scores: List[Dict],
        market_context: Optional[Dict] = None,
        period: str = "medium"
    ) -> AIAnalysisResult:
        """
        智能分析股票
        
        Args:
            mainlines: 主线数据列表
            factor_scores: 因子评分列表
            market_context: 市场环境数据
            period: 投资周期 short/medium/long
        
        Returns:
            AIAnalysisResult: 分析结果
        """
        # 构建分析提示
        prompt = self._build_analysis_prompt(mainlines, factor_scores, market_context, period)
        
        # 调用模型
        try:
            if self.model_type == "openai" and self.api_key:
                response = self._call_openai(prompt)
            elif self.model_type == "local":
                response = self._call_local_model(prompt)
            else:
                # 使用规则引擎作为备选
                response = self._rule_based_analysis(mainlines, factor_scores, period)
        except Exception as e:
            logger.warning(f"AI分析失败，使用规则引擎: {e}")
            response = self._rule_based_analysis(mainlines, factor_scores, period)
        
        return response
    
    def _build_analysis_prompt(
        self,
        mainlines: List[Dict],
        factor_scores: List[Dict],
        market_context: Optional[Dict],
        period: str
    ) -> str:
        """构建分析提示"""
        
        period_desc = {"short": "短期(1-5天)", "medium": "中期(1-4周)", "long": "长期(1月+)"}
        
        prompt = f"""你是一位专业的量化投资分析师，请基于以下数据进行{period_desc.get(period, '中期')}投资分析：

## 当前投资主线（按综合评分排序）
"""
        for i, ml in enumerate(mainlines[:10], 1):
            name = ml.get('name') or ml.get('mainline', '')
            score = ml.get('total_score') or ml.get('mainline_score', 0)
            prompt += f"{i}. {name} - 综合评分: {score:.1f}\n"
        
        if factor_scores:
            prompt += "\n## 候选股票因子评分（Top 10）\n"
            for i, stock in enumerate(factor_scores[:10], 1):
                code = stock.get('code', '')
                name = stock.get('name', code)
                factor = stock.get('factor_score', 0)
                mainline = stock.get('mainline', '')
                prompt += f"{i}. {code} {name} - 因子得分: {factor:.1f}, 所属主线: {mainline}\n"
        
        if market_context:
            prompt += f"\n## 市场环境\n"
            prompt += f"- 大盘趋势: {market_context.get('trend', '震荡')}\n"
            prompt += f"- 成交量: {market_context.get('volume', '正常')}\n"
            prompt += f"- 北向资金: {market_context.get('northbound', '净流入')}\n"
        
        prompt += f"""
## 分析要求
1. 基于{period_desc.get(period, '中期')}投资视角
2. 结合主线强度和个股因子评分
3. 给出3-5只重点推荐股票及理由
4. 评估主要风险点
5. 给出仓位建议（满仓/半仓/轻仓）

请以JSON格式返回分析结果：
{{
    "summary": "一句话总结",
    "recommendations": [
        {{"code": "股票代码", "name": "股票名称", "reason": "推荐理由", "target_weight": "建议权重%"}}
    ],
    "risk_assessment": "风险评估",
    "market_view": "市场观点",
    "position_advice": "仓位建议",
    "confidence": 0.0-1.0
}}
"""
        return prompt
    
    def _call_openai(self, prompt: str) -> AIAnalysisResult:
        """调用OpenAI API"""
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "你是专业的量化投资分析师，擅长A股市场分析。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            return self._parse_ai_response(content)
            
        except Exception as e:
            logger.error(f"OpenAI调用失败: {e}")
            raise
    
    def _call_local_model(self, prompt: str) -> AIAnalysisResult:
        """调用本地Ollama模型"""
        try:
            import requests
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2.5:7b",  # 或其他本地模型
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                content = response.json().get("response", "")
                return self._parse_ai_response(content)
            else:
                raise Exception(f"Ollama返回错误: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"本地模型调用失败: {e}")
            raise
    
    def _parse_ai_response(self, content: str) -> AIAnalysisResult:
        """解析AI响应"""
        try:
            # 尝试提取JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                return AIAnalysisResult(
                    summary=data.get("summary", ""),
                    recommendations=data.get("recommendations", []),
                    risk_assessment=data.get("risk_assessment", ""),
                    market_view=data.get("market_view", ""),
                    confidence=data.get("confidence", 0.5),
                    reasoning=content,
                    timestamp=datetime.now().isoformat()
                )
        except Exception as e:
            logger.warning(f"解析AI响应失败: {e}")
        
        # 返回原始内容
        return AIAnalysisResult(
            summary="AI分析完成",
            recommendations=[],
            risk_assessment="需要人工审核",
            market_view=content[:500],
            confidence=0.3,
            reasoning=content,
            timestamp=datetime.now().isoformat()
        )
    
    def _rule_based_analysis(
        self,
        mainlines: List[Dict],
        factor_scores: List[Dict],
        period: str
    ) -> AIAnalysisResult:
        """基于规则的分析（备选方案）"""
        
        # 分析主线
        top_mainlines = mainlines[:5] if mainlines else []
        mainline_names = [m.get('name') or m.get('mainline', '') for m in top_mainlines]
        
        # 分析因子得分
        top_stocks = sorted(factor_scores, key=lambda x: x.get('factor_score', 0), reverse=True)[:5]
        
        # 构建推荐
        recommendations = []
        for stock in top_stocks:
            recommendations.append({
                "code": stock.get('code', ''),
                "name": stock.get('name', ''),
                "reason": f"因子得分: {stock.get('factor_score', 0):.1f}, 主线: {stock.get('mainline', '')}",
                "target_weight": f"{20 / len(top_stocks):.0f}%"
            })
        
        # 根据周期调整建议
        period_advice = {
            "short": ("短线机会，快进快出", "轻仓试探"),
            "medium": ("中线布局，逢低介入", "半仓配置"),
            "long": ("长线价值，耐心持有", "分批建仓")
        }
        
        market_view, position = period_advice.get(period, ("均衡配置", "半仓"))
        
        summary = f"当前主线: {', '.join(mainline_names[:3])}。建议{position}，关注{recommendations[0]['name'] if recommendations else '优质标的'}。"
        
        return AIAnalysisResult(
            summary=summary,
            recommendations=recommendations,
            risk_assessment="注意市场波动风险，设置好止损位",
            market_view=market_view,
            confidence=0.6,
            reasoning=f"基于规则分析：主线评分排序 + 因子综合评分。{period}策略侧重{'动量资金' if period == 'short' else '价值成长' if period == 'long' else '均衡配置'}。",
            timestamp=datetime.now().isoformat()
        )


    def recommend_factors(
        self,
        market_trend: str,
        pool_characteristics: Dict,
        period: str = "medium",
        current_factors: List[str] = None
    ) -> FactorRecommendationResult:
        """
        智能推荐因子组合
        
        Args:
            market_trend: 市场趋势 (bull/bear/oscillation/recovery)
            pool_characteristics: 候选池特征
            period: 投资周期 short/medium/long
            current_factors: 当前已有的因子列表
        
        Returns:
            FactorRecommendationResult: 因子推荐结果
        """
        # 构建因子推荐提示
        prompt = self._build_factor_recommendation_prompt(
            market_trend, pool_characteristics, period, current_factors
        )
        
        try:
            if self.model_type == "openai" and self.api_key:
                response_text = self._call_openai_raw(prompt)
                return self._parse_factor_recommendation(response_text)
            elif self.model_type == "local":
                response_text = self._call_local_model_raw(prompt)
                return self._parse_factor_recommendation(response_text)
            else:
                return self._rule_based_factor_recommendation(
                    market_trend, pool_characteristics, period
                )
        except Exception as e:
            logger.warning(f"AI因子推荐失败，使用规则引擎: {e}")
            return self._rule_based_factor_recommendation(
                market_trend, pool_characteristics, period
            )
    
    def _build_factor_recommendation_prompt(
        self,
        market_trend: str,
        pool_characteristics: Dict,
        period: str,
        current_factors: List[str] = None
    ) -> str:
        """构建因子推荐提示"""
        
        period_desc = {"short": "短期(1-5天)", "medium": "中期(1-4周)", "long": "长期(1月+)"}
        trend_desc = {
            "bull": "牛市上涨行情", 
            "bear": "熊市下跌行情",
            "oscillation": "震荡盘整行情",
            "recovery": "触底反弹行情"
        }
        
        prompt = f"""你是一位资深量化投资研究员，请基于以下市场环境和候选池特征，推荐最适合的因子组合：

## 当前市场环境
- 市场趋势: {trend_desc.get(market_trend, '震荡')}
- 投资周期: {period_desc.get(period, '中期')}

## 候选池特征
- 股票数量: {pool_characteristics.get('stock_count', 0)}
- 主导行业: {pool_characteristics.get('main_industry_type', '综合')}
- 行业分布: {pool_characteristics.get('industry_distribution', {})}
- 平均市值: {pool_characteristics.get('avg_market_cap', 'N/A')}
"""
        
        if current_factors:
            prompt += f"\n## 当前已配置因子\n{', '.join(current_factors)}\n"
        
        prompt += f"""
## 可选因子类别
- 价值因子: PE、PB、股息率、自由现金流收益率等
- 成长因子: 营收增长、利润增长、EPS增长、ROE变化等
- 质量因子: ROE、毛利率、资产周转率、负债率等
- 动量因子: 价格动量(5/20/60日)、相对强度、52周新高等
- 反转因子: 短期反转(5/10/20日)、超跌反弹等
- 波动因子: 波动率、Beta、下行风险等
- 流动性因子: 换手率、成交额、Amihud非流动性等
- 规模因子: 市值、流通市值等
- 资金流因子: 北向资金、主力资金、融资余额等
- 情绪因子: 分析师评级、新闻情绪等

## 推荐要求
1. 根据市场环境选择最适合的5-7个因子
2. 给出每个因子的建议权重(总和=100%)
3. 说明每个因子的推荐理由
4. 指出当前环境下应避免的因子
5. 建议需要额外开发的因子

请以JSON格式返回：
{{
    "market_environment": "市场环境描述",
    "recommended_factors": [
        {{"name": "因子名称", "weight": 0.25, "reason": "推荐理由"}}
    ],
    "avoid_factors": ["应避免因子1", "应避免因子2"],
    "development_needs": ["建议开发因子1", "建议开发因子2"],
    "period_adjustment": {{"short_weight": 0.3, "long_weight": 0.1}},
    "confidence": 0.8
}}
"""
        return prompt
    
    def _call_openai_raw(self, prompt: str) -> str:
        """调用OpenAI API返回原始文本"""
        import openai
        client = openai.OpenAI(api_key=self.api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是专业的量化因子研究员，擅长因子挖掘和组合优化。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
    
    def _call_local_model_raw(self, prompt: str) -> str:
        """调用本地模型返回原始文本"""
        import requests
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5:7b",
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json().get("response", "")
        raise Exception(f"Ollama返回错误: {response.status_code}")
    
    def _parse_factor_recommendation(self, content: str) -> FactorRecommendationResult:
        """解析因子推荐响应"""
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                return FactorRecommendationResult(
                    market_environment=data.get("market_environment", ""),
                    recommended_factors=data.get("recommended_factors", []),
                    avoid_factors=data.get("avoid_factors", []),
                    development_needs=data.get("development_needs", []),
                    period_adjustment=data.get("period_adjustment", {}),
                    confidence=data.get("confidence", 0.5),
                    reasoning=content
                )
        except Exception as e:
            logger.warning(f"解析因子推荐响应失败: {e}")
        
        return FactorRecommendationResult(
            market_environment="无法解析",
            recommended_factors=[],
            avoid_factors=[],
            development_needs=[],
            period_adjustment={},
            confidence=0.3,
            reasoning=content
        )
    
    def _rule_based_factor_recommendation(
        self,
        market_trend: str,
        pool_characteristics: Dict,
        period: str
    ) -> FactorRecommendationResult:
        """基于规则的因子推荐"""
        
        # 市场趋势对应的因子偏好
        TREND_FACTORS = {
            "bull": {
                "factors": [
                    {"name": "动量因子", "weight": 0.25, "reason": "牛市趋势延续，强者恒强"},
                    {"name": "成长因子", "weight": 0.25, "reason": "估值扩张期成长股弹性大"},
                    {"name": "资金流因子", "weight": 0.20, "reason": "跟随聪明钱方向"},
                    {"name": "质量因子", "weight": 0.15, "reason": "基本面支撑持续性"},
                    {"name": "规模因子", "weight": 0.15, "reason": "中小盘弹性更大"},
                ],
                "avoid": ["反转因子", "低波动因子"],
                "develop": ["情绪因子", "资金集中度因子"]
            },
            "bear": {
                "factors": [
                    {"name": "价值因子", "weight": 0.30, "reason": "熊市安全边际保护"},
                    {"name": "质量因子", "weight": 0.25, "reason": "高质量公司抗跌"},
                    {"name": "低波动因子", "weight": 0.20, "reason": "防御属性降低回撤"},
                    {"name": "股息因子", "weight": 0.15, "reason": "稳定现金回报"},
                    {"name": "反转因子", "weight": 0.10, "reason": "超跌反弹机会"},
                ],
                "avoid": ["动量因子", "规模因子(小盘)"],
                "develop": ["宏观避险因子", "现金流稳健因子"]
            },
            "oscillation": {
                "factors": [
                    {"name": "反转因子", "weight": 0.25, "reason": "震荡市均值回归效应强"},
                    {"name": "质量因子", "weight": 0.20, "reason": "穿越周期的核心"},
                    {"name": "价值因子", "weight": 0.20, "reason": "估值锚定"},
                    {"name": "流动性因子", "weight": 0.15, "reason": "捕捉换手率异动"},
                    {"name": "情绪因子", "weight": 0.20, "reason": "板块轮动驱动"},
                ],
                "avoid": ["长周期动量因子"],
                "develop": ["板块轮动因子", "事件驱动因子"]
            },
            "recovery": {
                "factors": [
                    {"name": "动量因子(短期)", "weight": 0.25, "reason": "捕捉反弹先锋"},
                    {"name": "成长因子", "weight": 0.25, "reason": "弹性标的优先"},
                    {"name": "资金流因子", "weight": 0.20, "reason": "增量资金方向"},
                    {"name": "规模因子", "weight": 0.15, "reason": "中小盘弹性"},
                    {"name": "质量因子", "weight": 0.15, "reason": "基本面支撑"},
                ],
                "avoid": ["高股息因子", "低波动因子"],
                "develop": ["领先指标因子", "机构调研因子"]
            }
        }
        
        trend_config = TREND_FACTORS.get(market_trend, TREND_FACTORS["oscillation"])
        
        # 根据周期调整权重
        factors = trend_config["factors"].copy()
        if period == "short":
            # 短期增加动量和反转权重
            for f in factors:
                if "动量" in f["name"] or "反转" in f["name"] or "资金" in f["name"]:
                    f["weight"] = min(f["weight"] * 1.3, 0.35)
        elif period == "long":
            # 长期增加价值和质量权重
            for f in factors:
                if "价值" in f["name"] or "质量" in f["name"] or "成长" in f["name"]:
                    f["weight"] = min(f["weight"] * 1.3, 0.35)
        
        # 归一化权重
        total = sum(f["weight"] for f in factors)
        for f in factors:
            f["weight"] = round(f["weight"] / total, 2)
        
        trend_desc = {
            "bull": "牛市上涨行情",
            "bear": "熊市下跌行情", 
            "oscillation": "震荡盘整行情",
            "recovery": "触底反弹行情"
        }
        
        return FactorRecommendationResult(
            market_environment=f"当前市场处于{trend_desc.get(market_trend, '震荡')}",
            recommended_factors=factors,
            avoid_factors=trend_config["avoid"],
            development_needs=trend_config["develop"],
            period_adjustment={"period": period, "adjustment": "已根据投资周期调整权重"},
            confidence=0.7,
            reasoning=f"基于规则引擎分析：市场趋势={market_trend}, 投资周期={period}"
        )


def create_ai_analyzer(model_type: str = "local") -> AIAnalyzer:
    """创建AI分析器"""
    return AIAnalyzer(model_type=model_type)

