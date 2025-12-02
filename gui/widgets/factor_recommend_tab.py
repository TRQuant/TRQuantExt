# -*- coding: utf-8 -*-
"""
因子推荐标签页
=============

基于投资环境和候选池特征，进行深度研究，推荐因子组合。

流程：
1. 分析当前投资环境（市场趋势、资金面、情绪面）
2. 获取候选池股票特征（行业分布、财务特征、技术形态）
3. 深度研究：AI分析 + 规则引擎
4. 输出：推荐因子组合、权重配置、具体因子、建模建议
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QTextEdit, QGroupBox,
    QComboBox, QProgressBar, QScrollArea, QFrame, QSplitter,
    QMessageBox, QGridLayout, QSpinBox, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QColor
import logging
from datetime import datetime
from typing import Dict, List, Optional
import json

from gui.styles.theme import Colors, ButtonStyles

logger = logging.getLogger(__name__)


# ============================================================
# 详细因子库（包含具体因子）
# ============================================================

DETAILED_FACTORS = {
    "动量因子": {
        "description": "捕捉价格趋势延续效应",
        "specific_factors": [
            {"id": "momentum_12_1", "name": "12-1月动量", "formula": "过去12个月收益(剔除最近1个月)", "weight": 0.35},
            {"id": "momentum_60d", "name": "60日动量", "formula": "(当前价-60日前价)/60日前价", "weight": 0.25},
            {"id": "relative_strength", "name": "相对强度RS", "formula": "个股涨幅/指数涨幅", "weight": 0.20},
            {"id": "52w_high", "name": "52周新高距离", "formula": "当前价/52周最高价", "weight": 0.20},
        ],
        "modeling_suggestion": "建议使用滚动窗口计算，剔除最近1个月避免短期反转效应。可考虑行业中性化处理。"
    },
    "成长因子": {
        "description": "衡量公司业绩增长能力",
        "specific_factors": [
            {"id": "revenue_growth_yoy", "name": "营收同比增长", "formula": "(本期营收-去年同期)/去年同期", "weight": 0.30},
            {"id": "profit_growth_yoy", "name": "净利润同比增长", "formula": "(本期净利润-去年同期)/去年同期", "weight": 0.30},
            {"id": "roe_change", "name": "ROE变化", "formula": "本期ROE-去年同期ROE", "weight": 0.20},
            {"id": "eps_growth_3y", "name": "EPS三年复合增长", "formula": "(当前EPS/3年前EPS)^(1/3)-1", "weight": 0.20},
        ],
        "modeling_suggestion": "使用TTM数据，注意财报发布时间滞后。建议对极端值做Winsorize处理(1%/99%)。"
    },
    "价值因子": {
        "description": "衡量股票估值水平",
        "specific_factors": [
            {"id": "ep", "name": "盈利收益率EP", "formula": "EPS/股价 = 1/PE", "weight": 0.30},
            {"id": "bp", "name": "账面市值比BP", "formula": "每股净资产/股价 = 1/PB", "weight": 0.25},
            {"id": "dividend_yield", "name": "股息率", "formula": "每股股息/股价", "weight": 0.25},
            {"id": "fcf_yield", "name": "自由现金流收益率", "formula": "自由现金流/市值", "weight": 0.20},
        ],
        "modeling_suggestion": "价值因子需行业中性化，不同行业估值水平差异大。PE为负时建议使用PB或PS替代。"
    },
    "质量因子": {
        "description": "衡量公司财务健康度",
        "specific_factors": [
            {"id": "roe", "name": "净资产收益率ROE", "formula": "净利润/平均股东权益", "weight": 0.35},
            {"id": "gross_margin", "name": "毛利率", "formula": "(营收-成本)/营收", "weight": 0.25},
            {"id": "asset_turnover", "name": "资产周转率", "formula": "营收/平均总资产", "weight": 0.20},
            {"id": "accruals", "name": "应计项目", "formula": "(净利润-经营现金流)/总资产", "weight": 0.20},
        ],
        "modeling_suggestion": "ROE使用杜邦分解更细致。应计项目为负向因子(越低越好)，反映盈利质量。"
    },
    "资金流因子": {
        "description": "跟踪聪明钱流向",
        "specific_factors": [
            {"id": "north_flow", "name": "北向资金净流入", "formula": "北向资金净买入/流通市值", "weight": 0.40},
            {"id": "main_force_flow", "name": "主力资金净流入", "formula": "大单净买入/成交额", "weight": 0.35},
            {"id": "margin_change", "name": "融资余额变化", "formula": "(今日融资余额-5日前)/5日前", "weight": 0.25},
        ],
        "modeling_suggestion": "资金流因子时效性强，建议使用近5-20日累计值。需注意数据延迟问题。"
    },
    "反转因子": {
        "description": "捕捉短期均值回归效应",
        "specific_factors": [
            {"id": "reversal_5d", "name": "5日反转", "formula": "-(当前价-5日前价)/5日前价", "weight": 0.40},
            {"id": "reversal_20d", "name": "20日反转", "formula": "-(当前价-20日前价)/20日前价", "weight": 0.35},
            {"id": "max_return_5d", "name": "5日最大涨幅反转", "formula": "-max(近5日涨幅)", "weight": 0.25},
        ],
        "modeling_suggestion": "A股短期反转效应显著，但需控制换手率成本。建议结合流动性因子筛选。"
    },
    "低波动因子": {
        "description": "低波动股票的防御属性",
        "specific_factors": [
            {"id": "volatility_20d", "name": "20日波动率", "formula": "20日收益率标准差×√252", "weight": 0.40},
            {"id": "beta", "name": "Beta系数", "formula": "Cov(ri,rm)/Var(rm)", "weight": 0.35},
            {"id": "max_drawdown", "name": "最大回撤", "formula": "(峰值-谷值)/峰值", "weight": 0.25},
        ],
        "modeling_suggestion": "低波动因子为负向因子。在熊市和震荡市更有效，牛市可能跑输。"
    },
    "流动性因子": {
        "description": "衡量交易活跃度",
        "specific_factors": [
            {"id": "turnover_20d", "name": "20日平均换手率", "formula": "近20日换手率均值", "weight": 0.40},
            {"id": "amihud", "name": "Amihud非流动性", "formula": "|收益率|/成交额", "weight": 0.35},
            {"id": "volume_ratio", "name": "量比", "formula": "当日成交量/5日均量", "weight": 0.25},
        ],
        "modeling_suggestion": "低换手率通常有超额收益。Amihud指标反映价格冲击成本。"
    },
    "规模因子": {
        "description": "小市值效应",
        "specific_factors": [
            {"id": "ln_market_cap", "name": "对数市值", "formula": "-ln(总市值)", "weight": 0.60},
            {"id": "float_cap", "name": "流通市值", "formula": "-ln(流通市值)", "weight": 0.40},
        ],
        "modeling_suggestion": "规模因子为负向因子(小市值更好)。A股壳价值效应明显，需注意ST股风险。"
    },
    "情绪因子": {
        "description": "市场情绪和预期",
        "specific_factors": [
            {"id": "analyst_upgrade", "name": "分析师评级变化", "formula": "评级上调次数-下调次数", "weight": 0.40},
            {"id": "forecast_revision", "name": "盈利预测修正", "formula": "(最新预测-上月预测)/上月预测", "weight": 0.35},
            {"id": "news_sentiment", "name": "新闻情绪得分", "formula": "NLP情感分析得分", "weight": 0.25},
        ],
        "modeling_suggestion": "情绪因子需要另类数据支持。建议使用公开的分析师预测数据作为替代。"
    },
    "股息因子": {
        "description": "稳定分红能力",
        "specific_factors": [
            {"id": "dividend_yield", "name": "股息率", "formula": "每股股息/股价", "weight": 0.50},
            {"id": "dividend_payout", "name": "分红率", "formula": "每股股息/EPS", "weight": 0.30},
            {"id": "dividend_growth", "name": "股息增长率", "formula": "(今年股息-去年股息)/去年股息", "weight": 0.20},
        ],
        "modeling_suggestion": "高股息策略在熊市和利率下行期更有效。需关注分红的可持续性。"
    },
}

MARKET_FACTOR_RULES = {
    "bull_market": {
        "name": "牛市/上涨行情",
        "description": "市场整体向上，成交活跃，北向持续流入",
        "recommended_categories": ["动量因子", "成长因子", "资金流因子", "质量因子", "规模因子"],
        "category_weights": {"动量因子": 0.30, "成长因子": 0.25, "资金流因子": 0.20, "质量因子": 0.15, "规模因子": 0.10},
        "avoid_factors": ["反转因子", "低波动因子"],
        "development_needs": ["情绪因子", "资金集中度因子"],
        "modeling_advice": """
【牛市建模建议】
1. 因子组合：动量+成长为核心，辅以资金流跟踪
2. 换仓频率：周频或双周频，捕捉趋势延续
3. 止损设置：个股-15%，组合-10%
4. 行业配置：超配先导板块(科技、消费)，低配防御板块
5. 风险控制：控制单行业暴露不超过30%
"""
    },
    "bear_market": {
        "name": "熊市/下跌行情",
        "description": "市场整体下行，成交萎缩，避险情绪浓厚",
        "recommended_categories": ["价值因子", "质量因子", "低波动因子", "股息因子", "反转因子"],
        "category_weights": {"价值因子": 0.30, "质量因子": 0.25, "低波动因子": 0.20, "股息因子": 0.15, "反转因子": 0.10},
        "avoid_factors": ["动量因子", "规模因子(小盘)"],
        "development_needs": ["宏观避险因子", "现金流稳健性因子"],
        "modeling_advice": """
【熊市建模建议】
1. 因子组合：价值+质量为核心，追求安全边际
2. 换仓频率：月频，降低交易成本
3. 止损设置：个股-20%，组合-15%（更宽松）
4. 行业配置：超配防御板块(银行、公用事业)，避免周期股
5. 风险控制：高现金比例(30%+)，等待反转信号
"""
    },
    "oscillation": {
        "name": "震荡/盘整行情",
        "description": "市场缺乏方向，板块轮动加快",
        "recommended_categories": ["反转因子", "质量因子", "价值因子", "流动性因子", "情绪因子"],
        "category_weights": {"反转因子": 0.25, "质量因子": 0.20, "价值因子": 0.20, "流动性因子": 0.15, "情绪因子": 0.20},
        "avoid_factors": ["长周期动量因子"],
        "development_needs": ["板块轮动因子", "事件驱动因子"],
        "modeling_advice": """
【震荡市建模建议】
1. 因子组合：反转+质量为核心，均值回归策略
2. 换仓频率：日频或隔日，快进快出
3. 止损设置：个股-8%，组合-5%（更严格）
4. 行业配置：关注板块轮动，跟随热点但不追高
5. 风险控制：控制仓位不超过60%，保持灵活性
"""
    },
    "recovery": {
        "name": "复苏/反弹行情",
        "description": "市场触底回升，先导板块启动",
        "recommended_categories": ["动量因子", "成长因子", "资金流因子", "规模因子", "质量因子"],
        "category_weights": {"动量因子": 0.25, "成长因子": 0.25, "资金流因子": 0.20, "规模因子": 0.15, "质量因子": 0.15},
        "avoid_factors": ["高股息因子", "低波动因子"],
        "development_needs": ["领先指标因子", "机构调研因子"],
        "modeling_advice": """
【复苏期建模建议】
1. 因子组合：短期动量+成长为核心，捕捉反弹先锋
2. 换仓频率：周频，跟随趋势形成
3. 止损设置：个股-12%，组合-8%
4. 行业配置：超配弹性板块(券商、科技)，左侧布局
5. 风险控制：确认趋势后逐步加仓，初期保持谨慎
"""
    }
}

PERIOD_FACTOR_WEIGHTS = {
    "short": {
        "name": "短期策略(1-5天)",
        "factor_weights": {"动量因子": 0.30, "资金流因子": 0.25, "反转因子": 0.20, "流动性因子": 0.15, "情绪因子": 0.10},
        "characteristics": "侧重技术面和资金面，快进快出"
    },
    "medium": {
        "name": "中期策略(1-4周)",
        "factor_weights": {"动量因子": 0.20, "成长因子": 0.20, "质量因子": 0.20, "价值因子": 0.15, "资金流因子": 0.15, "低波动因子": 0.10},
        "characteristics": "均衡配置，趋势与价值兼顾"
    },
    "long": {
        "name": "长期策略(1月+)",
        "factor_weights": {"价值因子": 0.25, "成长因子": 0.25, "质量因子": 0.25, "股息因子": 0.15, "低波动因子": 0.10},
        "characteristics": "侧重基本面，长期价值投资"
    }
}

INDUSTRY_FACTOR_MAPPING = {
    "科技": {"recommended": ["成长因子", "动量因子"], "avoid": ["股息因子"], "reason": "科技股重成长性"},
    "金融": {"recommended": ["价值因子", "股息因子"], "avoid": ["规模因子"], "reason": "金融股重估值分红"},
    "消费": {"recommended": ["质量因子", "成长因子"], "avoid": [], "reason": "消费股重品牌溢价"},
    "医药": {"recommended": ["成长因子", "质量因子"], "avoid": ["价值因子"], "reason": "医药股重研发成长"},
    "周期": {"recommended": ["动量因子", "价值因子"], "avoid": ["成长因子"], "reason": "周期股重趋势估值"},
    "新能源": {"recommended": ["成长因子", "动量因子"], "avoid": ["股息因子"], "reason": "新能源重增速政策"},
}


class EnvironmentAnalyzer:
    """投资环境分析器"""
    
    def __init__(self, jq_client=None):
        self.jq_client = jq_client
        
    def analyze_market_trend(self) -> Dict:
        """分析市场趋势"""
        try:
            if not self.jq_client:
                return self._default_market_analysis()
            
            import jqdatasdk as jq
            from datetime import datetime, timedelta
            
            perm = self.jq_client.get_permission()
            end_date = perm.end_date if perm else "2025-08-29"
            start_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=60)).strftime("%Y-%m-%d")
            
            df = jq.get_price(
                "000001.XSHG",
                start_date=start_date,
                end_date=end_date,
                frequency='daily',
                fields=['close', 'volume']
            )
            
            if df is None or df.empty:
                return self._default_market_analysis()
            
            latest_close = df['close'].iloc[-1]
            ma20 = df['close'].rolling(20).mean().iloc[-1]
            ma60 = df['close'].rolling(60).mean().iloc[-1] if len(df) >= 60 else ma20
            
            avg_volume = df['volume'].mean()
            recent_volume = df['volume'].iloc[-5:].mean()
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
            
            if latest_close > ma20 > ma60:
                trend = "bull_market"
                trend_desc = "上涨趋势"
            elif latest_close < ma20 < ma60:
                trend = "bear_market"
                trend_desc = "下跌趋势"
            elif latest_close > ma20 and ma20 < ma60:
                trend = "recovery"
                trend_desc = "触底反弹"
            else:
                trend = "oscillation"
                trend_desc = "震荡盘整"
            
            return {
                "trend_type": trend,
                "trend_desc": trend_desc,
                "index_level": f"{latest_close:.2f}",
                "vs_ma20": f"{(latest_close/ma20 - 1)*100:.1f}%",
                "vs_ma60": f"{(latest_close/ma60 - 1)*100:.1f}%",
                "volume_ratio": f"{volume_ratio:.2f}",
                "volume_status": "放量" if volume_ratio > 1.2 else "缩量" if volume_ratio < 0.8 else "正常",
                "analysis_date": end_date
            }
            
        except Exception as e:
            logger.warning(f"市场趋势分析失败: {e}")
            return self._default_market_analysis()
    
    def _default_market_analysis(self) -> Dict:
        return {
            "trend_type": "oscillation",
            "trend_desc": "震荡盘整",
            "index_level": "N/A",
            "vs_ma20": "N/A",
            "vs_ma60": "N/A",
            "volume_ratio": "1.00",
            "volume_status": "正常",
            "analysis_date": datetime.now().strftime("%Y-%m-%d")
        }
    
    def analyze_candidate_pool(self, stocks: List[Dict]) -> Dict:
        """分析候选池特征"""
        if not stocks:
            return {"stock_count": 0, "industry_distribution": {}, "main_industry_type": "综合", "characteristics": "无候选池数据"}
        
        industry_count = {}
        for stock in stocks:
            industry = stock.get("industry", stock.get("mainline", "未知"))
            industry_count[industry] = industry_count.get(industry, 0) + 1
        
        top_industries = sorted(industry_count.items(), key=lambda x: x[1], reverse=True)[:5]
        main_industry = top_industries[0][0] if top_industries else "综合"
        industry_type = self._map_to_industry_type(main_industry)
        
        return {
            "stock_count": len(stocks),
            "industry_distribution": dict(top_industries),
            "main_industry_type": industry_type,
            "characteristics": f"以{industry_type}为主导，共{len(stocks)}只候选股"
        }
    
    def _map_to_industry_type(self, industry: str) -> str:
        mapping = {
            "科技": ["人工智能", "芯片", "半导体", "软件", "云计算", "大数据", "5G", "物联网"],
            "金融": ["银行", "保险", "证券", "金融科技"],
            "消费": ["白酒", "食品", "饮料", "家电", "零售", "电商"],
            "医药": ["医药", "生物", "医疗", "疫苗", "创新药"],
            "周期": ["钢铁", "煤炭", "有色", "化工", "建材", "基建"],
            "新能源": ["新能源", "锂电", "光伏", "风电", "储能", "电动车"]
        }
        for category, keywords in mapping.items():
            for kw in keywords:
                if kw in industry:
                    return category
        return "综合"


class FactorRecommendWorker(QThread):
    """因子推荐工作线程"""
    
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, jq_client, period: str):
        super().__init__()
        self.jq_client = jq_client
        self.period = period
        
    def run(self):
        try:
            self.progress.emit("正在分析市场环境...")
            analyzer = EnvironmentAnalyzer(self.jq_client)
            market_analysis = analyzer.analyze_market_trend()
            self.progress.emit(f"市场趋势: {market_analysis['trend_desc']}")
            
            self.progress.emit("正在获取候选池...")
            candidate_stocks = self._load_candidate_pool()
            pool_analysis = analyzer.analyze_candidate_pool(candidate_stocks)
            self.progress.emit(f"候选池: {pool_analysis['stock_count']}只股票")
            
            self.progress.emit("正在生成详细因子推荐...")
            recommendation = self._generate_detailed_recommendation(market_analysis, pool_analysis, self.period)
            
            result = {
                "market_analysis": market_analysis,
                "pool_analysis": pool_analysis,
                "recommendation": recommendation,
                "timestamp": datetime.now().isoformat()
            }
            
            self.finished.emit(result)
            
        except Exception as e:
            logger.error(f"因子推荐失败: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
    
    def _load_candidate_pool(self) -> List[Dict]:
        try:
            from pymongo import MongoClient
            client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
            db = client.jqquant
            
            cache = db.candidate_pool_cache.find_one(sort=[("timestamp", -1)])
            if cache and cache.get("stocks"):
                return cache["stocks"]
            
            mainline = db.mainline_mapped.find_one(sort=[("timestamp", -1)])
            if mainline and mainline.get("mainlines"):
                return [{"code": ml.get("jqdata_code", ""), "mainline": ml.get("name", ""), "industry": ml.get("name", "")} for ml in mainline["mainlines"]]
            return []
        except Exception as e:
            logger.warning(f"加载候选池失败: {e}")
            return []
    
    def _generate_detailed_recommendation(self, market: Dict, pool: Dict, period: str) -> Dict:
        trend_type = market.get("trend_type", "oscillation")
        industry_type = pool.get("main_industry_type", "综合")
        
        market_rule = MARKET_FACTOR_RULES.get(trend_type, MARKET_FACTOR_RULES["oscillation"])
        period_rule = PERIOD_FACTOR_WEIGHTS.get(period, PERIOD_FACTOR_WEIGHTS["medium"])
        industry_rule = INDUSTRY_FACTOR_MAPPING.get(industry_type, {})
        
        # 生成推荐因子大类和权重
        recommended_categories = []
        category_weights = market_rule.get("category_weights", {})
        
        for cat in market_rule.get("recommended_categories", []):
            base_weight = category_weights.get(cat, 0.15)
            period_adjust = period_rule["factor_weights"].get(cat, 0.1)
            final_weight = (base_weight + period_adjust) / 2
            
            recommended_categories.append({
                "category": cat,
                "weight": round(final_weight, 2),
                "description": DETAILED_FACTORS.get(cat, {}).get("description", ""),
                "specific_factors": DETAILED_FACTORS.get(cat, {}).get("specific_factors", []),
                "modeling_suggestion": DETAILED_FACTORS.get(cat, {}).get("modeling_suggestion", ""),
            })
        
        # 归一化权重
        total_weight = sum(c["weight"] for c in recommended_categories)
        if total_weight > 0:
            for c in recommended_categories:
                c["weight"] = round(c["weight"] / total_weight, 2)
        
        recommended_categories.sort(key=lambda x: x["weight"], reverse=True)
        
        # 生成建模建议
        modeling_advice = market_rule.get("modeling_advice", "")
        
        return {
            "market_type": market_rule["name"],
            "market_desc": market_rule["description"],
            "period_type": period_rule["name"],
            "period_desc": period_rule["characteristics"],
            "industry_type": industry_type,
            "recommended_categories": recommended_categories,
            "avoid_factors": market_rule.get("avoid_factors", []),
            "development_needs": market_rule.get("development_needs", []),
            "modeling_advice": modeling_advice,
            "summary": self._generate_summary(market_rule, period_rule, industry_type, recommended_categories)
        }
    
    def _generate_summary(self, market_rule, period_rule, industry_type, categories) -> str:
        top_cats = [c["category"] for c in categories[:3]]
        return f"当前市场处于【{market_rule['name']}】阶段，候选池以【{industry_type}】为主。基于【{period_rule['name']}】策略，建议重点配置：{', '.join(top_cats)}。"


class FactorRecommendTab(QWidget):
    """因子推荐标签页"""
    
    recommendation_ready = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.jq_client = None
        self.worker = None
        self.current_recommendation = None
        
        self._init_jq_client()
        self._init_ui()
        self._load_cached_results()
        
    def _init_jq_client(self):
        """初始化JQData客户端"""
        try:
            from jqdata.client import JQDataClient
            from config.config_manager import get_config_manager
            
            config_manager = get_config_manager()
            config = config_manager.get_jqdata_config()
            username = config.get('username', '')
            password = config.get('password', '')
            
            if not username or not password:
                logger.warning("因子推荐Tab: 未找到JQData配置")
                return
            
            self.jq_client = JQDataClient()
            if self.jq_client.authenticate(username, password):
                logger.info("因子推荐Tab: JQData连接成功")
            else:
                self.jq_client = None
        except Exception as e:
            logger.warning(f"因子推荐Tab: JQData连接失败: {e}")
            self.jq_client = None
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {Colors.BG_SECONDARY}; }}")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)
        content_layout.setContentsMargins(20, 20, 20, 20)
        
        # 介绍区
        intro_frame = self._create_intro_section()
        content_layout.addWidget(intro_frame)
        
        # 操作区
        action_frame = self._create_action_section()
        content_layout.addWidget(action_frame)
        
        # 进度显示
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet(f"color: {Colors.PRIMARY}; font-size: 13px;")
        content_layout.addWidget(self.progress_label)
        
        # 摘要区
        self.summary_frame = self._create_summary_section()
        content_layout.addWidget(self.summary_frame)
        
        # 详细结果区
        result_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 因子大类推荐表格
        category_panel = self._create_category_panel()
        result_splitter.addWidget(category_panel)
        
        # 具体因子详情
        detail_panel = self._create_detail_panel()
        result_splitter.addWidget(detail_panel)
        
        result_splitter.setSizes([300, 400])
        content_layout.addWidget(result_splitter, 1)
        
        # 建模建议区
        modeling_frame = self._create_modeling_section()
        content_layout.addWidget(modeling_frame)
        
        # 注意事项
        warning_frame = self._create_warning_section()
        content_layout.addWidget(warning_frame)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
    
    def _create_intro_section(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.PRIMARY}22, stop:1 {Colors.BG_SECONDARY});
                border-radius: 12px;
                padding: 20px;
            }}
        """)
        layout = QVBoxLayout(frame)
        
        title = QLabel("🧠 因子推荐引擎")
        title.setFont(QFont("", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {Colors.PRIMARY};")
        layout.addWidget(title)
        
        desc = QLabel(
            "基于当前投资环境和候选池特征进行深度分析，智能推荐最适合的因子组合。\n"
            "输出：因子大类 → 具体因子 → 建模建议 → 策略参数"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px;")
        layout.addWidget(desc)
        
        return frame
    
    def _create_action_section(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"QFrame {{ background: {Colors.BG_TERTIARY}; border-radius: 8px; padding: 16px; }}")
        layout = QHBoxLayout(frame)
        
        layout.addWidget(QLabel("投资周期:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["短期(1-5天)", "中期(1-4周)", "长期(1月+)"])
        self.period_combo.setCurrentIndex(1)
        self.period_combo.setStyleSheet(self._get_combo_style())
        layout.addWidget(self.period_combo)
        
        layout.addSpacing(20)
        
        self.analyze_btn = QPushButton("🔬 深度分析并推荐因子")
        self.analyze_btn.setStyleSheet(ButtonStyles.PRIMARY)
        self.analyze_btn.setMinimumWidth(200)
        self.analyze_btn.clicked.connect(self._start_analysis)
        layout.addWidget(self.analyze_btn)
        
        self.reset_btn = QPushButton("🔄 重新开始")
        self.reset_btn.setStyleSheet(ButtonStyles.SECONDARY)
        self.reset_btn.clicked.connect(self._reset_analysis)
        layout.addWidget(self.reset_btn)
        
        layout.addStretch()
        
        self.apply_btn = QPushButton("✅ 应用到因子计算")
        self.apply_btn.setStyleSheet(ButtonStyles.SUCCESS)
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._apply_recommendation)
        layout.addWidget(self.apply_btn)
        
        return frame
    
    def _create_summary_section(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: {Colors.BG_TERTIARY};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        layout = QVBoxLayout(frame)
        
        self.summary_label = QLabel("请点击「深度分析并推荐因子」开始分析...")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-size: 14px;
            padding: 12px;
            background: {Colors.BG_SECONDARY};
            border-radius: 8px;
            border-left: 4px solid {Colors.PRIMARY};
        """)
        layout.addWidget(self.summary_label)
        
        # 市场信息行
        info_layout = QHBoxLayout()
        self.market_info = QLabel("市场环境: 待分析")
        self.market_info.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        info_layout.addWidget(self.market_info)
        
        self.pool_info = QLabel("候选池: 待分析")
        self.pool_info.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        info_layout.addWidget(self.pool_info)
        
        self.period_info = QLabel("投资周期: 待分析")
        self.period_info.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        info_layout.addWidget(self.period_info)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        return frame
    
    def _create_category_panel(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"QFrame {{ background: {Colors.BG_TERTIARY}; border-radius: 8px; }}")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        
        title = QLabel("📊 推荐因子大类及权重")
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)
        
        self.category_table = QTableWidget()
        self.category_table.setColumnCount(4)
        self.category_table.setHorizontalHeaderLabels(["因子大类", "建议权重", "说明", "包含因子数"])
        self.category_table.horizontalHeader().setStretchLastSection(True)
        self.category_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.category_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.category_table.setStyleSheet(self._get_table_style())
        self.category_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.category_table.itemSelectionChanged.connect(self._on_category_selected)
        layout.addWidget(self.category_table)
        
        return frame
    
    def _create_detail_panel(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"QFrame {{ background: {Colors.BG_TERTIARY}; border-radius: 8px; }}")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        
        title_layout = QHBoxLayout()
        self.detail_title = QLabel("📋 具体因子详情（请选择上方因子大类）")
        self.detail_title.setFont(QFont("", 14, QFont.Weight.Bold))
        self.detail_title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        title_layout.addWidget(self.detail_title)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(4)
        self.detail_table.setHorizontalHeaderLabels(["因子名称", "因子ID", "计算公式", "类内权重"])
        self.detail_table.horizontalHeader().setStretchLastSection(True)
        self.detail_table.setStyleSheet(self._get_table_style())
        layout.addWidget(self.detail_table)
        
        # 建模建议文本
        self.factor_modeling_label = QLabel("选择因子大类后，这里将显示该类因子的建模建议...")
        self.factor_modeling_label.setWordWrap(True)
        self.factor_modeling_label.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            padding: 12px;
            background: {Colors.BG_SECONDARY};
            border-radius: 6px;
            border-left: 3px solid {Colors.INFO};
        """)
        layout.addWidget(self.factor_modeling_label)
        
        return frame
    
    def _create_modeling_section(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"QFrame {{ background: {Colors.BG_TERTIARY}; border-radius: 8px; padding: 16px; }}")
        layout = QVBoxLayout(frame)
        
        title = QLabel("🔧 综合建模建议")
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)
        
        self.modeling_text = QTextEdit()
        self.modeling_text.setReadOnly(True)
        self.modeling_text.setMaximumHeight(200)
        self.modeling_text.setStyleSheet(f"""
            QTextEdit {{
                background: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                color: {Colors.TEXT_PRIMARY};
                padding: 12px;
                font-family: monospace;
            }}
        """)
        self.modeling_text.setPlainText("分析完成后，这里将显示综合建模建议...")
        layout.addWidget(self.modeling_text)
        
        return frame
    
    def _create_warning_section(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"QFrame {{ background: {Colors.BG_TERTIARY}; border-radius: 8px; padding: 16px; }}")
        layout = QHBoxLayout(frame)
        
        # 应避免的因子
        avoid_group = QGroupBox("⚠️ 当前环境应避免")
        avoid_group.setStyleSheet(self._get_group_style())
        avoid_layout = QVBoxLayout(avoid_group)
        self.avoid_label = QLabel("待分析...")
        self.avoid_label.setWordWrap(True)
        self.avoid_label.setStyleSheet(f"color: {Colors.WARNING};")
        avoid_layout.addWidget(self.avoid_label)
        layout.addWidget(avoid_group)
        
        # 建议开发的因子
        dev_group = QGroupBox("🔧 建议开发的因子")
        dev_group.setStyleSheet(self._get_group_style())
        dev_layout = QVBoxLayout(dev_group)
        self.dev_label = QLabel("待分析...")
        self.dev_label.setWordWrap(True)
        self.dev_label.setStyleSheet(f"color: {Colors.INFO};")
        dev_layout.addWidget(self.dev_label)
        layout.addWidget(dev_group)
        
        return frame
    
    def _load_cached_results(self):
        """加载缓存的结果"""
        try:
            from pymongo import MongoClient
            client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
            db = client.jqquant
            
            cache = db.factor_recommendation_cache.find_one(sort=[("timestamp", -1)])
            if cache:
                # 检查缓存是否过期（24小时）
                cache_time = datetime.fromisoformat(cache.get("timestamp", "2000-01-01"))
                if (datetime.now() - cache_time).total_seconds() < 86400:
                    self.current_recommendation = cache
                    self._display_results(cache)
                    self.progress_label.setText(f"✅ 已加载上次分析结果 ({cache_time.strftime('%Y-%m-%d %H:%M')})")
                    logger.info(f"因子推荐: 加载缓存成功")
                    return
            
            logger.debug("因子推荐: 无有效缓存")
        except Exception as e:
            logger.debug(f"加载因子推荐缓存失败: {e}")
    
    def _save_results_to_cache(self, result: dict):
        """保存结果到缓存"""
        try:
            from pymongo import MongoClient
            client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
            db = client.jqquant
            
            # 删除旧缓存
            db.factor_recommendation_cache.delete_many({})
            # 保存新结果
            db.factor_recommendation_cache.insert_one(result)
            logger.info("因子推荐: 结果已保存到缓存")
        except Exception as e:
            logger.warning(f"保存因子推荐缓存失败: {e}")
    
    def _start_analysis(self):
        """开始分析"""
        try:
            if self.worker and self.worker.isRunning():
                QMessageBox.warning(self, "提示", "分析正在进行中...")
                return
            
            period_map = {"短期(1-5天)": "short", "中期(1-4周)": "medium", "长期(1月+)": "long"}
            period = period_map.get(self.period_combo.currentText(), "medium")
            
            self.analyze_btn.setEnabled(False)
            self.progress_label.setText("正在启动分析...")
            
            self.worker = FactorRecommendWorker(self.jq_client, period)
            self.worker.progress.connect(self._on_progress)
            self.worker.finished.connect(self._on_finished)
            self.worker.error.connect(self._on_error)
            self.worker.start()
            
        except Exception as e:
            logger.error(f"启动因子分析失败: {e}")
            self.analyze_btn.setEnabled(True)
            self.progress_label.setText(f"❌ 启动失败: {e}")
    
    def _reset_analysis(self):
        """重新开始分析"""
        reply = QMessageBox.question(
            self, "确认", "确定要清空当前结果并重新开始吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.current_recommendation = None
            self.summary_label.setText("请点击「深度分析并推荐因子」开始分析...")
            self.market_info.setText("市场环境: 待分析")
            self.pool_info.setText("候选池: 待分析")
            self.period_info.setText("投资周期: 待分析")
            self.category_table.setRowCount(0)
            self.detail_table.setRowCount(0)
            self.modeling_text.setPlainText("分析完成后，这里将显示综合建模建议...")
            self.avoid_label.setText("待分析...")
            self.dev_label.setText("待分析...")
            self.apply_btn.setEnabled(False)
            self.progress_label.setText("")
    
    def _on_progress(self, msg: str):
        self.progress_label.setText(msg)
    
    def _on_finished(self, result: dict):
        try:
            self.analyze_btn.setEnabled(True)
            self.apply_btn.setEnabled(True)
            self.progress_label.setText("✅ 分析完成")
            
            self.current_recommendation = result
            self._display_results(result)
            self._save_results_to_cache(result)
            
        except Exception as e:
            logger.error(f"更新因子推荐结果失败: {e}")
            import traceback
            traceback.print_exc()
            self.progress_label.setText(f"⚠️ 结果显示异常: {e}")
    
    def _display_results(self, result: dict):
        """显示分析结果"""
        try:
            # 更新摘要
            rec = result.get("recommendation", {})
            self.summary_label.setText(rec.get("summary", "分析完成"))
            
            # 更新信息行
            market = result.get("market_analysis", {})
            pool = result.get("pool_analysis", {})
            self.market_info.setText(f"市场环境: {market.get('trend_desc', 'N/A')} ({market.get('analysis_date', '')})")
            self.pool_info.setText(f"候选池: {pool.get('stock_count', 0)}只股票, {pool.get('main_industry_type', '综合')}为主")
            self.period_info.setText(f"投资周期: {rec.get('period_type', 'N/A')}")
            
            # 更新因子大类表格
            categories = rec.get("recommended_categories", [])
            self.category_table.setRowCount(len(categories))
            for row, cat in enumerate(categories):
                self.category_table.setItem(row, 0, QTableWidgetItem(cat.get("category", "")))
                
                weight_item = QTableWidgetItem(f"{cat.get('weight', 0)*100:.0f}%")
                weight_item.setForeground(QColor(Colors.SUCCESS))
                self.category_table.setItem(row, 1, weight_item)
                
                self.category_table.setItem(row, 2, QTableWidgetItem(cat.get("description", "")))
                
                factor_count = len(cat.get("specific_factors", []))
                self.category_table.setItem(row, 3, QTableWidgetItem(str(factor_count)))
            
            self.category_table.resizeColumnsToContents()
            
            # 更新建模建议
            self.modeling_text.setPlainText(rec.get("modeling_advice", "暂无综合建模建议"))
            
            # 更新警告区
            avoid = rec.get("avoid_factors", [])
            if avoid:
                self.avoid_label.setText("• " + "\n• ".join(str(a) for a in avoid))
            else:
                self.avoid_label.setText("无特别需要避免的因子")
            
            dev = rec.get("development_needs", [])
            if dev:
                self.dev_label.setText("• " + "\n• ".join(str(d) for d in dev))
            else:
                self.dev_label.setText("当前因子库已满足需求")
            
            self.apply_btn.setEnabled(True)
            
        except Exception as e:
            logger.error(f"显示结果失败: {e}")
    
    def _on_category_selected(self):
        """当选择因子大类时，显示具体因子"""
        selected_rows = self.category_table.selectedItems()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        if not self.current_recommendation:
            return
        
        categories = self.current_recommendation.get("recommendation", {}).get("recommended_categories", [])
        if row >= len(categories):
            return
        
        cat = categories[row]
        self.detail_title.setText(f"📋 {cat.get('category', '')} - 具体因子详情")
        
        # 填充具体因子表格
        factors = cat.get("specific_factors", [])
        self.detail_table.setRowCount(len(factors))
        for i, f in enumerate(factors):
            self.detail_table.setItem(i, 0, QTableWidgetItem(f.get("name", "")))
            self.detail_table.setItem(i, 1, QTableWidgetItem(f.get("id", "")))
            self.detail_table.setItem(i, 2, QTableWidgetItem(f.get("formula", "")))
            
            weight_item = QTableWidgetItem(f"{f.get('weight', 0)*100:.0f}%")
            weight_item.setForeground(QColor(Colors.PRIMARY))
            self.detail_table.setItem(i, 3, weight_item)
        
        self.detail_table.resizeColumnsToContents()
        
        # 更新该类因子的建模建议
        self.factor_modeling_label.setText(cat.get("modeling_suggestion", "暂无该类因子的具体建模建议"))
    
    def _on_error(self, error: str):
        self.analyze_btn.setEnabled(True)
        self.progress_label.setText(f"❌ 分析失败: {error}")
        QMessageBox.critical(self, "错误", f"因子推荐失败:\n{error}")
    
    def _apply_recommendation(self):
        """应用推荐"""
        if not self.current_recommendation:
            QMessageBox.warning(self, "提示", "请先进行因子分析")
            return
        
        self.recommendation_ready.emit(self.current_recommendation)
        QMessageBox.information(self, "成功", "推荐因子已准备就绪，请切换到「因子计算」页面查看和使用")
    
    def _get_combo_style(self) -> str:
        return f"""
            QComboBox {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 8px 12px;
                color: {Colors.TEXT_PRIMARY};
                min-width: 150px;
            }}
            QComboBox::drop-down {{ border: none; width: 30px; }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                selection-background-color: {Colors.PRIMARY};
            }}
        """
    
    def _get_group_style(self) -> str:
        return f"""
            QGroupBox {{
                font-weight: bold;
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }}
        """
    
    def _get_table_style(self) -> str:
        return f"""
            QTableWidget {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                gridline-color: {Colors.BORDER_PRIMARY};
            }}
            QTableWidget::item {{
                padding: 8px;
                color: {Colors.TEXT_PRIMARY};
            }}
            QTableWidget::item:selected {{
                background-color: {Colors.PRIMARY}44;
            }}
            QHeaderView::section {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                padding: 8px;
                border: none;
                border-bottom: 1px solid {Colors.BORDER_PRIMARY};
            }}
        """
