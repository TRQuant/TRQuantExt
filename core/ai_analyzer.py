# -*- coding: utf-8 -*-
"""
AI智能分析器
============

基于大模型的智能选股分析：
1. 整合主线、因子、宏观信息
2. 构建分析提示
3. 调用大模型进行智能分析
4. 返回结构化建议

支持的模型：
- OpenAI GPT (需配置API Key)
- 本地大模型 (通过Ollama)
- Cursor内置模型 (通过API)
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
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


def create_ai_analyzer(model_type: str = "local") -> AIAnalyzer:
    """创建AI分析器"""
    return AIAnalyzer(model_type=model_type)

