# -*- coding: utf-8 -*-
"""
因子构建面板 - 完整的量化因子库与构建工具
==========================================

整合：
- 完整因子分类库（价值、成长、质量、动量、波动、流动性、情绪、技术）
- 经典因子库参考（101 Alphas、191 Alphas、WorldQuant等）
- 因子计算与组合
- PTrade/QMT策略代码生成
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit,
    QComboBox, QSpinBox, QDoubleSpinBox, QGroupBox, QFormLayout,
    QListWidget, QListWidgetItem, QSplitter, QMessageBox,
    QProgressBar, QCheckBox, QScrollArea, QFrame, QTreeWidget,
    QTreeWidgetItem, QHeaderView, QLineEdit, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QUrl
from PyQt6.QtGui import QFont, QColor, QDesktopServices
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd

from gui.styles.theme import Colors, ButtonStyles

logger = logging.getLogger(__name__)


# ============================================================
# 完整因子数据库
# ============================================================

FACTOR_DATABASE = {
    "value": {
        "name": "💰 价值因子",
        "icon": "💰",
        "description": "衡量股票估值水平，低估值股票通常具有更高的预期收益",
        "effectiveness": "★★★☆☆",
        "factors": [
            {"id": "pe_ttm", "name": "市盈率(PE_TTM)", "formula": "股价 / 近12个月EPS", "direction": "negative", "interpretation": "PE<20为低估值，适合价值投资"},
            {"id": "pe_forward", "name": "预期市盈率", "formula": "股价 / 预测EPS", "direction": "negative", "interpretation": "基于分析师预测的估值"},
            {"id": "pb", "name": "市净率(PB)", "formula": "股价 / 每股净资产", "direction": "negative", "interpretation": "PB<1为破净股，安全边际高"},
            {"id": "pb_tangible", "name": "有形资产市净率", "formula": "市值 / (总资产-无形资产-商誉)", "direction": "negative", "interpretation": "剔除无形资产的估值"},
            {"id": "ps_ttm", "name": "市销率(PS_TTM)", "formula": "市值 / 近12个月营收", "direction": "negative", "interpretation": "适用于亏损但有收入的公司"},
            {"id": "pcf_ocf", "name": "市现率(经营)", "formula": "市值 / 经营现金流", "direction": "negative", "interpretation": "经营现金流估值"},
            {"id": "pcf_fcf", "name": "市现率(自由)", "formula": "市值 / 自由现金流", "direction": "negative", "interpretation": "自由现金流估值"},
            {"id": "ev_ebitda", "name": "EV/EBITDA", "formula": "企业价值 / EBITDA", "direction": "negative", "interpretation": "排除资本结构影响"},
            {"id": "ev_ebit", "name": "EV/EBIT", "formula": "企业价值 / EBIT", "direction": "negative", "interpretation": "考虑折旧的估值"},
            {"id": "ev_sales", "name": "EV/Sales", "formula": "企业价值 / 营收", "direction": "negative", "interpretation": "企业价值角度的市销率"},
            {"id": "ep", "name": "盈利收益率(EP)", "formula": "EPS / 股价 = 1/PE", "direction": "positive", "interpretation": "EP越高越便宜，Fama-French因子"},
            {"id": "bp", "name": "账面市值比(BP)", "formula": "每股净资产 / 股价 = 1/PB", "direction": "positive", "interpretation": "Fama-French三因子之一"},
            {"id": "sp", "name": "销售市值比(SP)", "formula": "每股营收 / 股价 = 1/PS", "direction": "positive", "interpretation": "营收角度的价值因子"},
            {"id": "cfp", "name": "现金流市值比(CFP)", "formula": "每股现金流 / 股价", "direction": "positive", "interpretation": "现金流角度的价值因子"},
            {"id": "dividend_yield", "name": "股息率", "formula": "每股股息 / 股价", "direction": "positive", "interpretation": "高股息提供安全边际"},
            {"id": "dividend_payout", "name": "股息支付率", "formula": "每股股息 / EPS", "direction": "positive", "interpretation": "分红慷慨程度"},
            {"id": "fcf_yield", "name": "自由现金流收益率", "formula": "自由现金流 / 市值", "direction": "positive", "interpretation": "巴菲特最看重的指标"},
            {"id": "earnings_yield_gap", "name": "盈利收益率差", "formula": "EP - 10年期国债收益率", "direction": "positive", "interpretation": "股票相对债券的吸引力"},
        ]
    },
    "growth": {
        "name": "📈 成长因子",
        "icon": "📈",
        "description": "衡量公司业绩增长能力，高成长股票享有估值溢价",
        "effectiveness": "★★★☆☆",
        "factors": [
            {"id": "revenue_growth_yoy", "name": "营收同比增长率", "formula": "(本期营收-去年同期) / 去年同期", "direction": "positive", "interpretation": ">20%为高增长"},
            {"id": "revenue_growth_qoq", "name": "营收环比增长率", "formula": "(本季营收-上季营收) / 上季营收", "direction": "positive", "interpretation": "季度增长趋势"},
            {"id": "revenue_growth_3y", "name": "营收3年复合增长", "formula": "(当前营收/3年前营收)^(1/3)-1", "direction": "positive", "interpretation": "长期营收增长"},
            {"id": "profit_growth_yoy", "name": "净利润同比增长率", "formula": "(本期净利润-去年同期) / 去年同期", "direction": "positive", "interpretation": ">30%为高增长"},
            {"id": "profit_growth_qoq", "name": "净利润环比增长率", "formula": "(本季净利润-上季净利润) / 上季净利润", "direction": "positive", "interpretation": "季度盈利趋势"},
            {"id": "profit_growth_3y", "name": "净利润3年复合增长", "formula": "(当前净利润/3年前净利润)^(1/3)-1", "direction": "positive", "interpretation": "长期盈利增长"},
            {"id": "eps_growth_yoy", "name": "EPS同比增长率", "formula": "(本期EPS-去年同期EPS) / 去年同期EPS", "direction": "positive", "interpretation": "每股盈利增长"},
            {"id": "eps_growth_3y", "name": "EPS三年复合增长", "formula": "(当前EPS/3年前EPS)^(1/3)-1", "direction": "positive", "interpretation": "长期EPS增长能力"},
            {"id": "operating_profit_growth", "name": "营业利润增长率", "formula": "(本期营业利润-去年同期) / 去年同期", "direction": "positive", "interpretation": "主营业务盈利增长"},
            {"id": "roe_change", "name": "ROE变化", "formula": "本期ROE - 去年同期ROE", "direction": "positive", "interpretation": "盈利能力提升信号"},
            {"id": "roa_change", "name": "ROA变化", "formula": "本期ROA - 去年同期ROA", "direction": "positive", "interpretation": "资产效率提升"},
            {"id": "margin_change", "name": "毛利率变化", "formula": "本期毛利率 - 去年同期毛利率", "direction": "positive", "interpretation": "盈利能力改善"},
            {"id": "sustainable_growth", "name": "可持续增长率", "formula": "ROE × (1-分红率)", "direction": "positive", "interpretation": "内生增长能力"},
            {"id": "peg", "name": "PEG比率", "formula": "PE / 盈利增长率", "direction": "negative", "interpretation": "<1为成长股低估"},
        ]
    },
    "quality": {
        "name": "⭐ 质量因子",
        "icon": "⭐",
        "description": "衡量公司财务健康度和盈利质量，A股最有效因子之一",
        "effectiveness": "★★★★☆",
        "factors": [
            {"id": "roe", "name": "净资产收益率(ROE)", "formula": "净利润 / 平均股东权益", "direction": "positive", "interpretation": ">15%为优秀，巴菲特核心指标"},
            {"id": "roe_diluted", "name": "摊薄ROE", "formula": "净利润 / 期末股东权益", "direction": "positive", "interpretation": "更保守的ROE计算"},
            {"id": "roa", "name": "总资产收益率(ROA)", "formula": "净利润 / 平均总资产", "direction": "positive", "interpretation": ">5%为良好"},
            {"id": "roic", "name": "投入资本回报率(ROIC)", "formula": "NOPAT / 投入资本", "direction": "positive", "interpretation": ">WACC创造价值"},
            {"id": "roce", "name": "资本使用回报率(ROCE)", "formula": "EBIT / (总资产-流动负债)", "direction": "positive", "interpretation": "资本效率"},
            {"id": "gross_margin", "name": "毛利率", "formula": "(营收-成本) / 营收", "direction": "positive", "interpretation": ">30%具有定价权"},
            {"id": "operating_margin", "name": "营业利润率", "formula": "营业利润 / 营收", "direction": "positive", "interpretation": "主营盈利能力"},
            {"id": "net_margin", "name": "净利率", "formula": "净利润 / 营收", "direction": "positive", "interpretation": ">10%为良好"},
            {"id": "ebitda_margin", "name": "EBITDA利润率", "formula": "EBITDA / 营收", "direction": "positive", "interpretation": "现金盈利能力"},
            {"id": "asset_turnover", "name": "资产周转率", "formula": "营收 / 平均总资产", "direction": "positive", "interpretation": "资产运营效率"},
            {"id": "inventory_turnover", "name": "存货周转率", "formula": "营业成本 / 平均存货", "direction": "positive", "interpretation": "存货管理效率"},
            {"id": "receivable_turnover", "name": "应收账款周转率", "formula": "营收 / 平均应收账款", "direction": "positive", "interpretation": "回款效率"},
            {"id": "current_ratio", "name": "流动比率", "formula": "流动资产 / 流动负债", "direction": "positive", "interpretation": "1.5-2.0为健康"},
            {"id": "quick_ratio", "name": "速动比率", "formula": "(流动资产-存货) / 流动负债", "direction": "positive", "interpretation": ">1为良好"},
            {"id": "cash_ratio", "name": "现金比率", "formula": "现金及等价物 / 流动负债", "direction": "positive", "interpretation": "即时偿债能力"},
            {"id": "debt_to_equity", "name": "资产负债率", "formula": "总负债 / 总资产", "direction": "negative", "interpretation": "<60%较安全"},
            {"id": "debt_to_ebitda", "name": "负债/EBITDA", "formula": "总负债 / EBITDA", "direction": "negative", "interpretation": "<3为健康"},
            {"id": "interest_coverage", "name": "利息保障倍数", "formula": "EBIT / 利息费用", "direction": "positive", "interpretation": ">3为安全"},
            {"id": "accruals", "name": "应计项目", "formula": "(净利润-经营现金流) / 总资产", "direction": "negative", "interpretation": "越低盈利质量越高"},
            {"id": "accruals_bs", "name": "资产负债表应计", "formula": "ΔNOA / 平均总资产", "direction": "negative", "interpretation": "Sloan应计异象"},
            {"id": "cash_flow_quality", "name": "现金流质量", "formula": "经营现金流 / 净利润", "direction": "positive", "interpretation": ">1为优质盈利"},
            {"id": "earnings_quality", "name": "盈利质量", "formula": "经营现金流 / 总资产", "direction": "positive", "interpretation": "现金盈利能力"},
            {"id": "capex_intensity", "name": "资本支出强度", "formula": "资本支出 / 营收", "direction": "negative", "interpretation": "资本密集度"},
            {"id": "rd_intensity", "name": "研发强度", "formula": "研发费用 / 营收", "direction": "positive", "interpretation": "创新投入"},
        ]
    },
    "momentum": {
        "name": "🚀 动量因子",
        "icon": "🚀",
        "description": "基于价格趋势，捕捉市场动能效应",
        "effectiveness": "★★★☆☆",
        "factors": [
            {"id": "momentum_5d", "name": "5日动量", "formula": "(当前价-5日前价) / 5日前价", "direction": "positive", "interpretation": "超短期趋势"},
            {"id": "momentum_10d", "name": "10日动量", "formula": "(当前价-10日前价) / 10日前价", "direction": "positive", "interpretation": "短期趋势"},
            {"id": "momentum_20d", "name": "20日动量", "formula": "(当前价-20日前价) / 20日前价", "direction": "positive", "interpretation": "月度趋势"},
            {"id": "momentum_60d", "name": "60日动量", "formula": "(当前价-60日前价) / 60日前价", "direction": "positive", "interpretation": "季度趋势"},
            {"id": "momentum_120d", "name": "120日动量", "formula": "(当前价-120日前价) / 120日前价", "direction": "positive", "interpretation": "半年趋势"},
            {"id": "momentum_250d", "name": "250日动量", "formula": "(当前价-250日前价) / 250日前价", "direction": "positive", "interpretation": "年度趋势"},
            {"id": "momentum_12_1", "name": "12-1月动量", "formula": "过去12个月收益(剔除最近1个月)", "direction": "positive", "interpretation": "经典动量因子，避免短期反转"},
            {"id": "momentum_6_1", "name": "6-1月动量", "formula": "过去6个月收益(剔除最近1个月)", "direction": "positive", "interpretation": "中期动量"},
            {"id": "relative_strength", "name": "相对强度(RS)", "formula": "个股涨幅 / 指数涨幅", "direction": "positive", "interpretation": "相对市场超额表现"},
            {"id": "industry_momentum", "name": "行业动量", "formula": "行业指数近期收益", "direction": "positive", "interpretation": "行业轮动信号"},
            {"id": "52w_high", "name": "52周新高距离", "formula": "当前价 / 52周最高价", "direction": "positive", "interpretation": "接近新高强势"},
            {"id": "price_to_ma50", "name": "价格/MA50", "formula": "当前价 / 50日均线", "direction": "positive", "interpretation": ">1为中期强势"},
            {"id": "price_to_ma200", "name": "价格/MA200", "formula": "当前价 / 200日均线", "direction": "positive", "interpretation": ">1为长期强势"},
        ]
    },
    "reversal": {
        "name": "🔄 反转因子",
        "icon": "🔄",
        "description": "短期反转效应，A股市场非常显著",
        "effectiveness": "★★★★★",
        "factors": [
            {"id": "reversal_1d", "name": "1日反转", "formula": "-昨日收益率", "direction": "positive", "interpretation": "日内反转"},
            {"id": "reversal_5d", "name": "5日反转", "formula": "-(当前价-5日前价) / 5日前价", "direction": "positive", "interpretation": "超短期反转，A股最强因子"},
            {"id": "reversal_10d", "name": "10日反转", "formula": "-(当前价-10日前价) / 10日前价", "direction": "positive", "interpretation": "短期反转"},
            {"id": "reversal_20d", "name": "20日反转", "formula": "-(当前价-20日前价) / 20日前价", "direction": "positive", "interpretation": "月度反转"},
            {"id": "reversal_60d", "name": "60日反转", "formula": "-(当前价-60日前价) / 60日前价", "direction": "positive", "interpretation": "季度反转"},
            {"id": "max_return_5d", "name": "5日最大涨幅", "formula": "-max(近5日涨幅)", "direction": "positive", "interpretation": "避免短期追高"},
            {"id": "max_return_20d", "name": "20日最大涨幅", "formula": "-max(近20日涨幅)", "direction": "positive", "interpretation": "避免追高"},
            {"id": "min_return_20d", "name": "20日最大跌幅", "formula": "-min(近20日涨幅)", "direction": "negative", "interpretation": "抄底信号"},
            {"id": "overnight_return", "name": "隔夜收益反转", "formula": "-隔夜收益率", "direction": "positive", "interpretation": "隔夜反转效应"},
            {"id": "intraday_return", "name": "日内收益反转", "formula": "-日内收益率", "direction": "positive", "interpretation": "日内反转效应"},
        ]
    },
    "volatility": {
        "name": "📉 波动因子",
        "icon": "📉",
        "description": "衡量价格波动风险，低波动异象",
        "effectiveness": "★★★☆☆",
        "factors": [
            {"id": "volatility_5d", "name": "5日波动率", "formula": "5日收益率标准差×√252", "direction": "negative", "interpretation": "超短期波动"},
            {"id": "volatility_20d", "name": "20日波动率", "formula": "20日收益率标准差×√252", "direction": "negative", "interpretation": "短期波动风险"},
            {"id": "volatility_60d", "name": "60日波动率", "formula": "60日收益率标准差×√252", "direction": "negative", "interpretation": "中期波动风险"},
            {"id": "volatility_120d", "name": "120日波动率", "formula": "120日收益率标准差×√252", "direction": "negative", "interpretation": "长期波动风险"},
            {"id": "beta", "name": "Beta系数", "formula": "Cov(ri,rm) / Var(rm)", "direction": "negative", "interpretation": "<1为防御型"},
            {"id": "beta_down", "name": "下行Beta", "formula": "市场下跌时的Beta", "direction": "negative", "interpretation": "下跌风险敞口"},
            {"id": "idio_volatility", "name": "特质波动率", "formula": "残差收益率标准差", "direction": "negative", "interpretation": "非系统性风险"},
            {"id": "realized_volatility", "name": "已实现波动率", "formula": "高频收益率计算的波动率", "direction": "negative", "interpretation": "更准确的波动估计"},
            {"id": "max_drawdown", "name": "最大回撤", "formula": "(峰值-谷值) / 峰值", "direction": "negative", "interpretation": "历史最大亏损"},
            {"id": "downside_volatility", "name": "下行波动率", "formula": "负收益日的标准差", "direction": "negative", "interpretation": "下跌风险"},
            {"id": "var_95", "name": "VaR(95%)", "formula": "95%置信度的最大损失", "direction": "negative", "interpretation": "风险价值"},
            {"id": "skewness", "name": "收益率偏度", "formula": "收益率分布偏度", "direction": "positive", "interpretation": "正偏度更好"},
            {"id": "kurtosis", "name": "收益率峰度", "formula": "收益率分布峰度", "direction": "negative", "interpretation": "低峰度更稳定"},
        ]
    },
    "liquidity": {
        "name": "💧 流动性因子",
        "icon": "💧",
        "description": "衡量股票交易活跃度和流动性",
        "effectiveness": "★★☆☆☆",
        "factors": [
            {"id": "turnover_rate_1d", "name": "日换手率", "formula": "成交量 / 流通股本", "direction": "negative", "interpretation": "低换手率有超额收益"},
            {"id": "turnover_rate_20d", "name": "20日平均换手率", "formula": "近20日换手率均值", "direction": "negative", "interpretation": "中期换手水平"},
            {"id": "turnover_rate_60d", "name": "60日平均换手率", "formula": "近60日换手率均值", "direction": "negative", "interpretation": "长期换手水平"},
            {"id": "turnover_volatility", "name": "换手率波动", "formula": "换手率标准差", "direction": "negative", "interpretation": "交易稳定性"},
            {"id": "avg_volume_5d", "name": "5日平均成交额", "formula": "近5日成交额均值", "direction": "positive", "interpretation": "短期流动性"},
            {"id": "avg_volume_20d", "name": "20日平均成交额", "formula": "近20日成交额均值", "direction": "positive", "interpretation": "流动性水平"},
            {"id": "volume_ratio", "name": "量比", "formula": "当日成交量 / 5日均量", "direction": "neutral", "interpretation": ">1表示放量"},
            {"id": "volume_change", "name": "成交量变化", "formula": "(当日成交量-5日均量) / 5日均量", "direction": "neutral", "interpretation": "成交量异动"},
            {"id": "amihud", "name": "Amihud非流动性", "formula": "|收益率| / 成交额", "direction": "negative", "interpretation": "价格冲击成本"},
            {"id": "bid_ask_spread", "name": "买卖价差", "formula": "(卖一价-买一价) / 中间价", "direction": "negative", "interpretation": "交易成本"},
            {"id": "market_cap", "name": "市值", "formula": "股价 × 总股本", "direction": "negative", "interpretation": "小市值效应"},
            {"id": "float_market_cap", "name": "流通市值", "formula": "股价 × 流通股本", "direction": "negative", "interpretation": "流通盘大小"},
        ]
    },
    "sentiment": {
        "name": "💭 情绪/资金因子",
        "icon": "💭",
        "description": "衡量市场情绪和资金流向",
        "effectiveness": "★★★☆☆",
        "factors": [
            {"id": "north_flow_1d", "name": "北向资金日流入", "formula": "北向资金当日净买入", "direction": "positive", "interpretation": "外资当日动向"},
            {"id": "north_flow_5d", "name": "北向资金5日流入", "formula": "北向资金近5日净买入", "direction": "positive", "interpretation": "外资短期偏好"},
            {"id": "north_flow_20d", "name": "北向资金20日流入", "formula": "北向资金近20日净买入", "direction": "positive", "interpretation": "外资中期偏好"},
            {"id": "north_holding", "name": "北向持股比例", "formula": "北向持股数 / 流通股本", "direction": "positive", "interpretation": "外资持仓水平"},
            {"id": "main_force_flow", "name": "主力资金流入", "formula": "大单净买入额", "direction": "positive", "interpretation": "机构动向"},
            {"id": "retail_flow", "name": "散户资金流入", "formula": "小单净买入额", "direction": "negative", "interpretation": "散户动向（反向指标）"},
            {"id": "margin_balance", "name": "融资余额", "formula": "融资余额金额", "direction": "positive", "interpretation": "杠杆资金规模"},
            {"id": "margin_change", "name": "融资余额变化", "formula": "融资余额变化率", "direction": "positive", "interpretation": "杠杆资金动向"},
            {"id": "short_interest", "name": "融券余额", "formula": "融券余额金额", "direction": "negative", "interpretation": "做空压力"},
            {"id": "analyst_rating", "name": "分析师评级", "formula": "买入评级占比", "direction": "positive", "interpretation": "卖方一致预期"},
            {"id": "analyst_coverage", "name": "分析师覆盖", "formula": "覆盖分析师数量", "direction": "positive", "interpretation": "市场关注度"},
            {"id": "forecast_revision", "name": "盈利预测修正", "formula": "EPS预测变化率", "direction": "positive", "interpretation": "预期边际变化"},
            {"id": "target_price_ratio", "name": "目标价/现价", "formula": "分析师目标价 / 当前价", "direction": "positive", "interpretation": "上涨空间"},
            {"id": "insider_trading", "name": "内部人交易", "formula": "高管增持净额", "direction": "positive", "interpretation": "内部人信心"},
        ]
    },
    "technical": {
        "name": "📊 技术因子",
        "icon": "📊",
        "description": "基于技术分析的量化因子",
        "effectiveness": "★★☆☆☆",
        "factors": [
            {"id": "rsi_6", "name": "RSI(6)", "formula": "6日相对强弱指标", "direction": "neutral", "interpretation": "<20超卖，>80超买"},
            {"id": "rsi_14", "name": "RSI(14)", "formula": "14日相对强弱指标", "direction": "neutral", "interpretation": "<30超卖，>70超买"},
            {"id": "rsi_24", "name": "RSI(24)", "formula": "24日相对强弱指标", "direction": "neutral", "interpretation": "中期RSI"},
            {"id": "macd", "name": "MACD", "formula": "DIF - DEA", "direction": "positive", "interpretation": "趋势跟踪指标"},
            {"id": "macd_signal", "name": "MACD信号", "formula": "MACD金叉/死叉", "direction": "positive", "interpretation": "交易信号"},
            {"id": "kdj_k", "name": "KDJ-K值", "formula": "随机指标K值", "direction": "neutral", "interpretation": "超买超卖判断"},
            {"id": "kdj_d", "name": "KDJ-D值", "formula": "随机指标D值", "direction": "neutral", "interpretation": "K值平滑"},
            {"id": "kdj_j", "name": "KDJ-J值", "formula": "3K - 2D", "direction": "neutral", "interpretation": "超买超卖敏感指标"},
            {"id": "bollinger_upper", "name": "布林带上轨距离", "formula": "(上轨-价格) / 价格", "direction": "positive", "interpretation": "距上轨空间"},
            {"id": "bollinger_lower", "name": "布林带下轨距离", "formula": "(价格-下轨) / 价格", "direction": "positive", "interpretation": "距下轨空间"},
            {"id": "bollinger_width", "name": "布林带宽度", "formula": "(上轨-下轨) / 中轨", "direction": "negative", "interpretation": "波动收窄"},
            {"id": "ma_cross_5_10", "name": "MA5/MA10交叉", "formula": "MA5 > MA10", "direction": "positive", "interpretation": "短期金叉"},
            {"id": "ma_cross_5_20", "name": "MA5/MA20交叉", "formula": "MA5 > MA20", "direction": "positive", "interpretation": "中期金叉"},
            {"id": "ma_deviation_5", "name": "MA5偏离度", "formula": "(价格-MA5) / MA5", "direction": "neutral", "interpretation": "短期偏离"},
            {"id": "ma_deviation_20", "name": "MA20偏离度", "formula": "(价格-MA20) / MA20", "direction": "neutral", "interpretation": "中期偏离"},
            {"id": "obv", "name": "OBV能量潮", "formula": "累计成交量（涨加跌减）", "direction": "positive", "interpretation": "量价配合"},
            {"id": "cci", "name": "CCI顺势指标", "formula": "(TP-MA) / (0.015×MD)", "direction": "neutral", "interpretation": "趋势强度"},
            {"id": "atr", "name": "ATR真实波幅", "formula": "真实波幅的移动平均", "direction": "negative", "interpretation": "波动幅度"},
            {"id": "williams_r", "name": "威廉指标%R", "formula": "(最高价-收盘价) / (最高价-最低价)", "direction": "neutral", "interpretation": "超买超卖"},
            {"id": "dmi_plus", "name": "DMI+DI", "formula": "正向指标", "direction": "positive", "interpretation": "上涨动能"},
            {"id": "dmi_minus", "name": "DMI-DI", "formula": "负向指标", "direction": "negative", "interpretation": "下跌动能"},
            {"id": "adx", "name": "ADX趋势强度", "formula": "平均趋向指数", "direction": "positive", "interpretation": "趋势强度"},
        ]
    },
    "alpha101": {
        "name": "🔬 Alpha101因子",
        "icon": "🔬",
        "description": "WorldQuant 101 Alphas中的经典因子",
        "effectiveness": "★★★★☆",
        "factors": [
            {"id": "alpha001", "name": "Alpha#001", "formula": "rank(Ts_ArgMax(SignedPower(returns<0?stddev:close,2),5))-0.5", "direction": "positive", "interpretation": "波动率调整收益"},
            {"id": "alpha002", "name": "Alpha#002", "formula": "-1*correlation(rank(delta(log(volume),2)),rank((close-open)/open),6)", "direction": "positive", "interpretation": "量价背离"},
            {"id": "alpha003", "name": "Alpha#003", "formula": "-1*correlation(rank(open),rank(volume),10)", "direction": "positive", "interpretation": "开盘价量相关"},
            {"id": "alpha004", "name": "Alpha#004", "formula": "-1*Ts_Rank(rank(low),9)", "direction": "positive", "interpretation": "低价排名"},
            {"id": "alpha005", "name": "Alpha#005", "formula": "rank(open-(sum(vwap,10)/10))*(-1*abs(rank(close-vwap)))", "direction": "positive", "interpretation": "VWAP偏离"},
            {"id": "alpha006", "name": "Alpha#006", "formula": "-1*correlation(open,volume,10)", "direction": "positive", "interpretation": "开盘量价相关"},
            {"id": "alpha007", "name": "Alpha#007", "formula": "adv20<volume?-1*ts_rank(abs(delta(close,7)),60)*sign(delta(close,7)):(-1)", "direction": "positive", "interpretation": "放量反转"},
            {"id": "alpha008", "name": "Alpha#008", "formula": "-1*rank(sum(open,5)*sum(returns,5)-delay(sum(open,5)*sum(returns,5),10))", "direction": "positive", "interpretation": "开盘动量"},
            {"id": "alpha009", "name": "Alpha#009", "formula": "0<ts_min(delta(close,1),5)?delta(close,1):ts_max(delta(close,1),5)<0?delta(close,1):(-1*delta(close,1))", "direction": "positive", "interpretation": "价格变化"},
            {"id": "alpha010", "name": "Alpha#010", "formula": "rank(0<ts_min(delta(close,1),4)?delta(close,1):ts_max(delta(close,1),4)<0?delta(close,1):-1*delta(close,1))", "direction": "positive", "interpretation": "价格动量排名"},
            {"id": "alpha012", "name": "Alpha#012", "formula": "sign(delta(volume,1))*(-1*delta(close,1))", "direction": "positive", "interpretation": "量价背离"},
            {"id": "alpha013", "name": "Alpha#013", "formula": "-1*rank(covariance(rank(close),rank(volume),5))", "direction": "positive", "interpretation": "量价协方差"},
            {"id": "alpha014", "name": "Alpha#014", "formula": "-1*rank(delta(returns,3))*correlation(open,volume,10)", "direction": "positive", "interpretation": "收益变化"},
            {"id": "alpha015", "name": "Alpha#015", "formula": "-1*sum(rank(correlation(rank(high),rank(volume),3)),3)", "direction": "positive", "interpretation": "高价量相关"},
            {"id": "alpha016", "name": "Alpha#016", "formula": "-1*rank(covariance(rank(high),rank(volume),5))", "direction": "positive", "interpretation": "高价量协方差"},
            {"id": "alpha017", "name": "Alpha#017", "formula": "-1*rank(ts_rank(close,10))*rank(delta(delta(close,1),1))*rank(ts_rank(volume/adv20,5))", "direction": "positive", "interpretation": "综合动量"},
            {"id": "alpha018", "name": "Alpha#018", "formula": "-1*rank(stddev(abs(close-open),5)+close-open+correlation(close,open,10))", "direction": "positive", "interpretation": "波动开收价"},
            {"id": "alpha019", "name": "Alpha#019", "formula": "-1*sign(close-delay(close,7)+delta(close,7))*1+rank(1+sum(returns,250))", "direction": "positive", "interpretation": "长期动量"},
            {"id": "alpha020", "name": "Alpha#020", "formula": "-1*rank(open-delay(high,1))*rank(open-delay(close,1))*rank(open-delay(low,1))", "direction": "positive", "interpretation": "缺口因子"},
        ]
    },
    "size": {
        "name": "📐 规模因子",
        "icon": "📐",
        "description": "市值相关因子，小市值效应",
        "effectiveness": "★★★☆☆",
        "factors": [
            {"id": "ln_market_cap", "name": "对数市值", "formula": "ln(总市值)", "direction": "negative", "interpretation": "小市值效应"},
            {"id": "ln_float_cap", "name": "对数流通市值", "formula": "ln(流通市值)", "direction": "negative", "interpretation": "小盘股效应"},
            {"id": "market_cap_rank", "name": "市值排名", "formula": "市值在全市场的排名", "direction": "negative", "interpretation": "相对规模"},
            {"id": "mid_cap", "name": "中盘因子", "formula": "ln(市值)^2", "direction": "negative", "interpretation": "非线性规模效应"},
            {"id": "relative_size", "name": "相对规模", "formula": "个股市值 / 行业平均市值", "direction": "negative", "interpretation": "行业内相对规模"},
        ]
    },
}

# 经典因子库参考
CLASSIC_FACTOR_LIBRARIES = [
    {
        "name": "WorldQuant 101 Alphas",
        "description": "WorldQuant发布的101个Alpha因子公式，涵盖价量、技术、基本面等多种类型",
        "url": "https://arxiv.org/abs/1601.00991",
        "paper": "101 Formulaic Alphas (Kakushadze, 2016)",
        "factors_count": 101,
        "tags": ["学术论文", "公式化因子", "高频"],
        "example": "Alpha#1: (rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns, 20) : close), 2.), 5)) - 0.5)",
        "application": "适合量化选股和高频交易策略，需要分钟级数据支持"
    },
    {
        "name": "WorldQuant 191 Alphas", 
        "description": "WorldQuant扩展版191个Alpha因子，更全面的因子覆盖",
        "url": "https://platform.worldquant.com/",
        "paper": "Extended Alpha Factors",
        "factors_count": 191,
        "tags": ["扩展版", "全面覆盖", "实战"],
        "example": "包含更多基本面因子和行业中性化处理",
        "application": "WorldQuant Brain平台可直接测试，适合机构级量化研究"
    },
    {
        "name": "Zura Alpha因子库",
        "description": "开源量化因子库，包含A股适配的因子实现",
        "url": "https://github.com/yli188/WorldQuant_alpha101_code",
        "paper": "开源实现",
        "factors_count": 101,
        "tags": ["开源", "Python实现", "A股适配"],
        "example": "提供完整的Python代码实现，可直接用于A股回测",
        "application": "适合学习因子构建方法，可直接复用代码"
    },
    {
        "name": "Barra风险模型因子",
        "description": "MSCI Barra多因子风险模型，机构标准",
        "url": "https://www.msci.com/our-solutions/factor-investing",
        "paper": "Barra Risk Model Handbook",
        "factors_count": 10,
        "tags": ["风险模型", "机构标准", "因子投资"],
        "example": "Size, Value, Momentum, Quality, Volatility, Growth等",
        "application": "用于组合风险归因和因子暴露分析"
    },
    {
        "name": "Fama-French因子",
        "description": "学术界最经典的因子模型，诺贝尔奖级别研究",
        "url": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html",
        "paper": "Common Risk Factors (Fama & French, 1993)",
        "factors_count": 5,
        "tags": ["学术经典", "三因子/五因子", "诺贝尔奖"],
        "example": "SMB(规模)、HML(价值)、RMW(盈利)、CMA(投资)、MOM(动量)",
        "application": "因子研究的理论基础，用于学术研究和因子有效性验证"
    },
    {
        "name": "AQR因子库",
        "description": "AQR Capital发布的因子数据和研究",
        "url": "https://www.aqr.com/Insights/Datasets",
        "paper": "AQR Factor Research",
        "factors_count": 20,
        "tags": ["对冲基金", "因子数据", "全球市场"],
        "example": "Quality Minus Junk (QMJ), Betting Against Beta (BAB)",
        "application": "提供免费因子数据下载，适合因子研究和回测验证"
    },
    {
        "name": "聚宽因子库",
        "description": "JoinQuant平台内置因子库，A股本土化",
        "url": "https://www.joinquant.com/help/api/help#factor_values",
        "paper": "JQData因子文档",
        "factors_count": 100,
        "tags": ["A股", "本土化", "API接口"],
        "example": "提供预计算因子值，直接调用get_factor_values",
        "application": "本平台核心数据源，可直接在策略中使用"
    },
    {
        "name": "优矿因子库",
        "description": "通联数据优矿平台因子库",
        "url": "https://uqer.datayes.com/",
        "paper": "优矿因子文档",
        "factors_count": 80,
        "tags": ["A股", "机构级", "数据平台"],
        "example": "包含技术因子、基本面因子、另类因子等",
        "application": "机构级数据平台，适合专业量化研究"
    },
]

# 因子应用案例
FACTOR_APPLICATION_EXAMPLES = [
    {
        "name": "价值+质量组合策略",
        "description": "结合低估值和高质量，巴菲特风格",
        "factors": ["ep", "roe", "gross_margin"],
        "weights": [0.4, 0.4, 0.2],
        "stock_pool": "沪深300",
        "rebalance": "月度",
        "backtest_return": "年化15-20%",
        "max_drawdown": "20-25%",
        "code_example": '''
# 价值+质量组合策略
factors = {
    'ep': 0.4,      # 盈利收益率，越高越便宜
    'roe': 0.4,     # ROE，越高质量越好
    'gross_margin': 0.2  # 毛利率，定价权
}
stock_pool = get_index_stocks('000300.XSHG')
'''
    },
    {
        "name": "动量+反转混合策略",
        "description": "中期动量+短期反转，捕捉趋势与回调",
        "factors": ["momentum_12_1", "reversal_5d"],
        "weights": [0.6, 0.4],
        "stock_pool": "中证500",
        "rebalance": "周度",
        "backtest_return": "年化20-30%",
        "max_drawdown": "30-35%",
        "code_example": '''
# 动量+反转混合策略
factors = {
    'momentum_12_1': 0.6,  # 12-1月动量
    'reversal_5d': 0.4     # 5日反转（A股最强因子）
}
# 周度调仓，中证500股票池
'''
    },
    {
        "name": "低波动+高股息策略",
        "description": "防御型策略，适合震荡市",
        "factors": ["volatility_60d", "dividend_yield"],
        "weights": [0.5, 0.5],
        "stock_pool": "全A股",
        "rebalance": "季度",
        "backtest_return": "年化10-15%",
        "max_drawdown": "15-20%",
        "code_example": '''
# 低波动+高股息策略
factors = {
    'volatility_60d': -0.5,  # 负权重=选低波动
    'dividend_yield': 0.5    # 高股息
}
# 季度调仓，适合长期持有
'''
    },
    {
        "name": "成长+动量策略",
        "description": "追逐高成长趋势股，牛市表现好",
        "factors": ["profit_growth_yoy", "momentum_6m", "roe_change"],
        "weights": [0.4, 0.3, 0.3],
        "stock_pool": "创业板",
        "rebalance": "月度",
        "backtest_return": "年化25-40%",
        "max_drawdown": "40-50%",
        "code_example": '''
# 成长+动量策略（高波动高收益）
factors = {
    'profit_growth_yoy': 0.4,  # 净利润增速
    'momentum_6m': 0.3,        # 6个月动量
    'roe_change': 0.3          # ROE提升
}
# 适合牛市，熊市回撤大
'''
    },
    {
        "name": "多因子综合策略",
        "description": "均衡配置多类因子，稳健型",
        "factors": ["ep", "roe", "reversal_20d", "volatility_60d"],
        "weights": [0.3, 0.3, 0.2, 0.2],
        "stock_pool": "沪深300",
        "rebalance": "月度",
        "backtest_return": "年化12-18%",
        "max_drawdown": "18-22%",
        "code_example": '''
# 多因子综合策略
factors = {
    'ep': 0.3,           # 价值
    'roe': 0.3,          # 质量
    'reversal_20d': 0.2, # 反转
    'volatility_60d': -0.2  # 低波动
}
# 因子分散化，降低单因子风险
'''
    },
]


class FactorCalculationThread(QThread):
    """因子计算线程"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, factor_manager, factor_names, stocks, date):
        super().__init__()
        self.factor_manager = factor_manager
        self.factor_names = factor_names
        self.stocks = stocks
        self.date = date
    
    def run(self):
        try:
            results = {}
            total = len(self.factor_names)
            
            for i, name in enumerate(self.factor_names):
                self.progress.emit(
                    int((i + 1) / total * 100),
                    f"计算因子: {name}"
                )
                result = self.factor_manager.calculate_factor(name, self.stocks, self.date)
                if result:
                    results[name] = result
            
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class FactorBuilderPanel(QWidget):
    """因子构建面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.factor_manager = None
        self.jq_client = None
        self.current_results = {}
        self._init_jq_client()
        self.init_ui()
    
    def _init_jq_client(self):
        """初始化JQData客户端"""
        try:
            from jqdata.client import JQDataClient
            self.jq_client = JQDataClient()
            if self.jq_client.authenticate():
                from core.factors import FactorManager
                self.factor_manager = FactorManager(jq_client=self.jq_client)
                logger.info("✅ 因子管理器初始化成功")
        except Exception as e:
            logger.warning(f"因子管理器初始化失败: {e}")
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: {Colors.BG_SECONDARY};
            }}
            QTabBar::tab {{
                background: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_SECONDARY};
                padding: 12px 24px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 13px;
                font-weight: 500;
            }}
            QTabBar::tab:selected {{
                background: {Colors.PRIMARY};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        
        # 添加选项卡
        self.tab_widget.addTab(self._create_alpha_intro_tab(), "🎓 Alpha工程")
        self.tab_widget.addTab(self._create_factor_library_tab(), "📚 因子库")
        self.tab_widget.addTab(self._create_classic_factors_tab(), "🏆 经典因子库")
        self.tab_widget.addTab(self._create_quant_companies_tab(), "🏢 量化公司")
        self.tab_widget.addTab(self._create_examples_tab(), "💡 应用案例")
        self.tab_widget.addTab(self._create_factor_calc_tab(), "🔧 因子计算")
        # 策略生成功能已整合到"策略开发"模块
        
        layout.addWidget(self.tab_widget)
    
    def _create_alpha_intro_tab(self) -> QWidget:
        """创建Alpha工程介绍选项卡 - 卡片式布局 + 动态流程图"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {Colors.BG_SECONDARY};
            }}
            QScrollBar:vertical {{
                background-color: {Colors.BG_SECONDARY};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {Colors.BORDER_PRIMARY};
                border-radius: 4px;
                min-height: 40px;
            }}
        """)
        
        content = QWidget()
        content.setStyleSheet(f"background-color: {Colors.BG_SECONDARY};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 24, 32, 24)
        content_layout.setSpacing(20)
        
        # === 顶部Hero区域 ===
        hero = self._create_hero_section()
        content_layout.addWidget(hero)
        
        # === 什么是Alpha - 详细介绍 ===
        alpha_intro = self._create_alpha_intro_section()
        content_layout.addWidget(alpha_intro)
        
        # === 核心概念卡片组 (3列) ===
        concepts_title = QLabel("🧠 核心概念")
        concepts_title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {Colors.TEXT_PRIMARY}; margin-top: 8px;")
        content_layout.addWidget(concepts_title)
        
        concepts_row = self._create_concepts_cards()
        content_layout.addWidget(concepts_row)
        
        # === Alpha工程流程图 ===
        flow_title = QLabel("⚙️ Alpha工程流程")
        flow_title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {Colors.TEXT_PRIMARY}; margin-top: 8px;")
        content_layout.addWidget(flow_title)
        
        flow_intro = QLabel(
            "Alpha工程是一个系统性、可重复的因子研究和策略开发流程。"
            "从提出因子假设开始，经过严格的构建、检验、组合，最终实现策略的实盘运行和持续迭代优化。"
        )
        flow_intro.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_SECONDARY}; margin-bottom: 8px;")
        flow_intro.setWordWrap(True)
        content_layout.addWidget(flow_intro)
        
        flow_chart = self._create_flow_chart()
        content_layout.addWidget(flow_chart)
        
        # === 流程详解 ===
        flow_detail = self._create_flow_detail_section()
        content_layout.addWidget(flow_detail)
        
        # === 因子来源卡片组 (4列) ===
        sources_title = QLabel("🔬 Alpha因子的来源与本质")
        sources_title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {Colors.TEXT_PRIMARY}; margin-top: 8px;")
        content_layout.addWidget(sources_title)
        
        sources_intro = QLabel(
            "Alpha因子是能够预测股票未来收益的量化指标。有效的因子必须有合理的经济学解释，"
            "否则可能只是数据挖掘的结果，在样本外会失效。因子的来源主要有以下四类："
        )
        sources_intro.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_SECONDARY}; margin-bottom: 8px;")
        sources_intro.setWordWrap(True)
        content_layout.addWidget(sources_intro)
        
        sources_row = self._create_factor_sources_cards()
        content_layout.addWidget(sources_row)
        
        # === 因子检验方法 ===
        testing_section = self._create_testing_section()
        content_layout.addWidget(testing_section)
        
        # === A股因子有效性 ===
        ashare_title = QLabel("🇨🇳 A股市场的Alpha特点")
        ashare_title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {Colors.TEXT_PRIMARY}; margin-top: 8px;")
        content_layout.addWidget(ashare_title)
        
        ashare_intro = QLabel(
            "A股市场与成熟市场存在显著差异：散户占比高、涨跌停限制、T+1交易制度等。"
            "这些特点导致某些因子在A股表现特别突出（如短期反转），而另一些因子效果减弱。"
        )
        ashare_intro.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_SECONDARY}; margin-bottom: 8px;")
        ashare_intro.setWordWrap(True)
        content_layout.addWidget(ashare_intro)
        
        ashare_cards = self._create_ashare_factor_cards()
        content_layout.addWidget(ashare_cards)
        
        # === A股策略建议 ===
        ashare_tips = self._create_ashare_tips_section()
        content_layout.addWidget(ashare_tips)
        
        # === 经典案例卡片 ===
        cases_title = QLabel("📚 经典Alpha策略案例")
        cases_title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {Colors.TEXT_PRIMARY}; margin-top: 8px;")
        content_layout.addWidget(cases_title)
        
        cases_intro = QLabel(
            "以下是经过学术研究和实战验证的经典Alpha策略，它们代表了因子投资的不同流派和方法论，"
            "可以作为构建自己策略的参考和起点。"
        )
        cases_intro.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_SECONDARY}; margin-bottom: 8px;")
        cases_intro.setWordWrap(True)
        content_layout.addWidget(cases_intro)
        
        cases_row = self._create_case_cards()
        content_layout.addWidget(cases_row)
        
        # === 案例详解 ===
        cases_detail = self._create_cases_detail_section()
        content_layout.addWidget(cases_detail)
        
        # === 平台工具对照 ===
        tools_section = self._create_tools_section()
        content_layout.addWidget(tools_section)
        
        # === 底部CTA ===
        cta = self._create_cta_section()
        content_layout.addWidget(cta)
        
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return widget
    
    def _create_hero_section(self) -> QFrame:
        """创建顶部Hero区域"""
        hero = QFrame()
        hero.setFixedHeight(180)
        hero.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a3e, stop:0.5 #2d1f4e, stop:1 #1a2a4e);
                border-radius: 16px;
                border: 1px solid {Colors.PRIMARY}40;
            }}
        """)
        
        layout = QHBoxLayout(hero)
        layout.setContentsMargins(40, 30, 40, 30)
        
        # 左侧文字
        left = QVBoxLayout()
        left.setSpacing(12)
        
        title = QLabel("🎓 Alpha工程")
        title.setStyleSheet(f"""
            font-size: 32px;
            font-weight: 800;
            color: {Colors.TEXT_PRIMARY};
            letter-spacing: 2px;
        """)
        left.addWidget(title)
        
        subtitle = QLabel("Systematic Alpha Generation & Factor Investing")
        subtitle.setStyleSheet(f"font-size: 14px; color: {Colors.TEXT_MUTED}; font-style: italic;")
        left.addWidget(subtitle)
        
        desc = QLabel("通过系统性地挖掘、验证和组合Alpha因子，构建能够持续战胜市场的投资策略")
        desc.setStyleSheet(f"font-size: 14px; color: {Colors.TEXT_SECONDARY}; margin-top: 8px;")
        desc.setWordWrap(True)
        left.addWidget(desc)
        
        left.addStretch()
        layout.addLayout(left, 3)
        
        # 右侧公式卡片
        formula_card = QFrame()
        formula_card.setFixedSize(300, 140)
        formula_card.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(0, 0, 0, 0.25);
                border-radius: 12px;
                border: 1px solid {Colors.PRIMARY}60;
            }}
        """)
        formula_layout = QVBoxLayout(formula_card)
        formula_layout.setContentsMargins(20, 18, 20, 18)
        formula_layout.setSpacing(10)
        
        formula_title = QLabel("📐 核心公式")
        formula_title.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_MUTED}; font-weight: 500;")
        formula_layout.addWidget(formula_title, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 主公式 - 使用HTML格式支持更好的数学符号
        formula = QLabel()
        formula.setText(
            '<div style="text-align: center;">'
            '<span style="font-size: 28px; font-weight: 700; color: ' + Colors.PRIMARY + '; font-family: \'Times New Roman\', serif;">'
            'R = α + β × R<sub style="font-size: 20px;">m</sub> + ε'
            '</span>'
            '</div>'
        )
        formula.setAlignment(Qt.AlignmentFlag.AlignCenter)
        formula.setTextFormat(Qt.TextFormat.RichText)
        formula_layout.addWidget(formula)
        
        # 公式说明 - 分行显示更清晰
        formula_desc = QLabel()
        formula_desc.setText(
            '<div style="text-align: center; line-height: 1.6;">'
            '<span style="color: ' + Colors.TEXT_MUTED + '; font-size: 11px;">'
            '<b>α</b> = 超额收益<br>'
            '<b>β</b> = 市场敞口<br>'
            '<b>ε</b> = 随机误差'
            '</span>'
            '</div>'
        )
        formula_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        formula_desc.setTextFormat(Qt.TextFormat.RichText)
        formula_layout.addWidget(formula_desc)
        
        layout.addWidget(formula_card, 1)
        
        return hero
    
    def _create_concepts_cards(self) -> QFrame:
        """创建核心概念卡片组"""
        container = QFrame()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        concepts = [
            {
                "icon": "α",
                "title": "Alpha",
                "color": "#10B981",
                "desc": "超额收益",
                "detail": "投资组合相对于基准的超额回报，代表主动管理能力"
            },
            {
                "icon": "β",
                "title": "Beta",
                "color": "#3B82F6",
                "desc": "市场敞口",
                "detail": "投资组合对市场系统性风险的暴露程度"
            },
            {
                "icon": "γ",
                "title": "Smart Beta",
                "color": "#F59E0B",
                "desc": "因子溢价",
                "detail": "通过系统性暴露于特定因子获取的风险溢价"
            }
        ]
        
        for c in concepts:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.BG_PRIMARY};
                    border-radius: 12px;
                    border: 1px solid {Colors.BORDER_PRIMARY};
                }}
                QFrame:hover {{
                    border-color: {c['color']}80;
                    background-color: {c['color']}08;
                }}
            """)
            
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(20, 20, 20, 20)
            card_layout.setSpacing(12)
            
            # 图标 - 使用实心彩色背景配深色文字
            icon = QLabel(c["icon"])
            icon.setFixedSize(50, 50)
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setStyleSheet(f"""
                background-color: {c['color']};
                border-radius: 25px;
                font-size: 24px;
                font-weight: 800;
                color: #0d0d14;
                font-family: 'Times New Roman', serif;
            """)
            card_layout.addWidget(icon)
            
            # 标题
            title = QLabel(c["title"])
            title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {c['color']};")
            card_layout.addWidget(title)
            
            # 副标题
            sub = QLabel(c["desc"])
            sub.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_SECONDARY};")
            card_layout.addWidget(sub)
            
            # 详情
            detail = QLabel(c["detail"])
            detail.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_MUTED};")
            detail.setWordWrap(True)
            card_layout.addWidget(detail)
            
            card_layout.addStretch()
            layout.addWidget(card)
        
        return container
    
    def _create_flow_chart(self) -> QFrame:
        """创建动态流程图"""
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border-radius: 16px;
                border: 1px solid {Colors.BORDER_PRIMARY};
            }}
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(0)
        
        # 流程步骤
        steps = [
            {"num": "1", "title": "因子假设", "en": "Hypothesis", "color": Colors.PRIMARY,
             "desc": "基于经济学理论提出因子假设", "icon": "💡"},
            {"num": "2", "title": "因子构建", "en": "Construction", "color": "#10B981",
             "desc": "定义计算公式，处理数据质量", "icon": "🔧"},
            {"num": "3", "title": "因子检验", "en": "Testing", "color": "#3B82F6",
             "desc": "IC分析、分层回测、显著性检验", "icon": "📊"},
            {"num": "4", "title": "因子组合", "en": "Combination", "color": "#F59E0B",
             "desc": "多因子加权、风险模型优化", "icon": "🎯"},
            {"num": "5", "title": "策略实盘", "en": "Implementation", "color": "#EC4899",
             "desc": "交易成本控制、风控系统", "icon": "🚀"},
            {"num": "6", "title": "监控迭代", "en": "Monitoring", "color": "#8B5CF6",
             "desc": "因子衰减监控、持续优化", "icon": "🔄"},
        ]
        
        # 横向流程图
        flow_row = QHBoxLayout()
        flow_row.setSpacing(0)
        
        for i, step in enumerate(steps):
            # 步骤卡片
            step_widget = QFrame()
            step_widget.setFixedWidth(140)
            step_widget.setStyleSheet(f"""
                QFrame {{
                    background: transparent;
                }}
            """)
            
            step_layout = QVBoxLayout(step_widget)
            step_layout.setContentsMargins(8, 8, 8, 8)
            step_layout.setSpacing(8)
            step_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # 圆形图标
            circle = QLabel(step["icon"])
            circle.setFixedSize(56, 56)
            circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            circle.setStyleSheet(f"""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {step['color']}, stop:1 {step['color']}CC);
                border-radius: 28px;
                font-size: 24px;
                color: white;
            """)
            step_layout.addWidget(circle, alignment=Qt.AlignmentFlag.AlignCenter)
            
            # 标题
            title = QLabel(step["title"])
            title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {step['color']};")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            step_layout.addWidget(title)
            
            # 英文
            en = QLabel(step["en"])
            en.setStyleSheet(f"font-size: 10px; color: {Colors.TEXT_MUTED};")
            en.setAlignment(Qt.AlignmentFlag.AlignCenter)
            step_layout.addWidget(en)
            
            # 描述
            desc = QLabel(step["desc"])
            desc.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_SECONDARY};")
            desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
            desc.setWordWrap(True)
            desc.setFixedHeight(36)
            step_layout.addWidget(desc)
            
            flow_row.addWidget(step_widget)
            
            # 箭头（除了最后一个）
            if i < len(steps) - 1:
                arrow = QLabel("→")
                arrow.setFixedWidth(30)
                arrow.setStyleSheet(f"""
                    font-size: 24px;
                    color: {Colors.BORDER_PRIMARY};
                    font-weight: bold;
                """)
                arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
                flow_row.addWidget(arrow)
        
        layout.addLayout(flow_row)
        
        # 循环箭头提示
        cycle_hint = QLabel("↻ 持续迭代优化")
        cycle_hint.setStyleSheet(f"""
            font-size: 12px;
            color: {Colors.TEXT_MUTED};
            margin-top: 16px;
        """)
        cycle_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(cycle_hint)
        
        return container
    
    def _create_alpha_intro_section(self) -> QFrame:
        """创建Alpha详细介绍区域"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border-radius: 12px;
                border: 1px solid {Colors.BORDER_PRIMARY};
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # 标题
        title = QLabel("📈 什么是Alpha？")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)
        
        # 正文内容
        content = QLabel(
            "在投资领域，<b>Alpha (α)</b> 是衡量投资组合相对于基准指数的超额收益的指标。"
            "它代表了投资经理通过主动管理所创造的价值，是区分优秀投资者和普通投资者的关键。\n\n"
            
            "<b>理解投资收益的分解：</b>\n"
            "任何投资组合的收益都可以分解为三个部分：\n"
            "• <span style='color: #10B981;'><b>Alpha (α)</b></span> - 超额收益，来自选股能力和择时能力\n"
            "• <span style='color: #3B82F6;'><b>Beta (β)</b></span> - 市场风险敞口，被动持有市场获得的收益\n"
            "• <span style='color: #F59E0B;'><b>Epsilon (ε)</b></span> - 随机误差，不可预测的波动\n\n"
            
            "<b>为什么Alpha如此重要？</b>\n"
            "在有效市场假说下，市场价格已经反映了所有公开信息，因此获取Alpha是极其困难的。"
            "然而，行为金融学研究表明，由于投资者的非理性行为和市场结构的不完善，"
            "Alpha机会确实存在。量化投资的核心目标就是通过系统性的方法发现和捕获这些Alpha机会。\n\n"
            
            "<b>Alpha的来源：</b>\n"
            "• 信息优势 - 更快或更准确地处理信息\n"
            "• 分析优势 - 更好的模型和方法论\n"
            "• 行为优势 - 利用他人的非理性行为\n"
            "• 结构优势 - 利用市场结构性缺陷"
        )
        content.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;")
        content.setWordWrap(True)
        content.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(content)
        
        return frame
    
    def _create_flow_detail_section(self) -> QFrame:
        """创建流程详解区域"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border-radius: 12px;
                border: 1px solid {Colors.BORDER_PRIMARY};
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        
        title = QLabel("📋 流程详解")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)
        
        steps_detail = [
            (Colors.PRIMARY, "1. 因子假设", 
             "一切始于假设。基于经济学理论、行为金融学或市场观察，提出可能预测股票收益的因子假设。"
             "例如：'低估值股票长期跑赢高估值股票'（价值因子假设）。好的假设必须有逻辑支撑，而非纯粹的数据挖掘。"),
            ("#10B981", "2. 因子构建",
             "将假设转化为可计算的量化指标。包括：定义因子计算公式、处理数据质量问题（缺失值、异常值）、"
             "进行标准化处理（Z-score、排名）、行业中性化等。构建阶段的质量直接影响后续检验的有效性。"),
            ("#3B82F6", "3. 因子检验",
             "严格的统计检验是避免过拟合的关键。主要方法包括：IC分析（因子与收益的相关性）、"
             "分层回测（按因子值分组比较收益）、t检验（统计显著性）、样本外验证、多市场验证等。"),
            ("#F59E0B", "4. 因子组合",
             "单因子往往不够稳定，需要多因子组合。方法包括：等权加权、IC加权、最优化加权、"
             "因子正交化（去除因子间相关性）、风险模型约束等。目标是构建稳健的综合因子。"),
            ("#EC4899", "5. 策略实盘",
             "从因子到策略的转化。需要考虑：交易成本控制、滑点管理、策略容量评估、风控系统设计、"
             "调仓频率优化、资金管理等。实盘表现往往低于回测，需要预留足够的安全边际。"),
            ("#8B5CF6", "6. 监控迭代",
             "策略上线后的持续监控和优化。包括：因子衰减监控（因子是否失效）、策略归因分析、"
             "参数动态调整、新因子研发等。量化投资是一个持续进化的过程，需要不断适应市场变化。"),
        ]
        
        for color, step_title, detail in steps_detail:
            step_frame = QFrame()
            step_layout = QHBoxLayout(step_frame)
            step_layout.setContentsMargins(0, 8, 0, 8)
            step_layout.setSpacing(12)
            
            # 左侧色条
            bar = QFrame()
            bar.setFixedWidth(4)
            bar.setStyleSheet(f"background-color: {color}; border-radius: 2px;")
            step_layout.addWidget(bar)
            
            # 内容
            content_layout = QVBoxLayout()
            content_layout.setSpacing(4)
            
            step_title_label = QLabel(step_title)
            step_title_label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {color};")
            content_layout.addWidget(step_title_label)
            
            detail_label = QLabel(detail)
            detail_label.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_SECONDARY}; line-height: 1.6;")
            detail_label.setWordWrap(True)
            content_layout.addWidget(detail_label)
            
            step_layout.addLayout(content_layout)
            layout.addWidget(step_frame)
        
        return frame
    
    def _create_testing_section(self) -> QFrame:
        """创建因子检验方法区域"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border-radius: 12px;
                border: 1px solid {Colors.BORDER_PRIMARY};
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        title = QLabel("📊 因子检验核心方法")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)
        
        intro = QLabel(
            "严格的因子检验是避免过拟合、确保策略稳健性的关键。以下是量化投资中最常用的因子检验方法："
        )
        intro.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_SECONDARY};")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        
        # 检验方法卡片
        methods_row = QHBoxLayout()
        methods_row.setSpacing(12)
        
        methods = [
            {"name": "IC分析", "color": "#10B981", "formula": "IC = corr(因子, 收益)",
             "standard": "|IC| > 0.03", "desc": "因子值与下期收益的相关系数，衡量因子的预测能力"},
            {"name": "IR分析", "color": "#3B82F6", "formula": "IR = mean(IC) / std(IC)",
             "standard": "IR > 0.5", "desc": "信息比率，衡量因子预测能力的稳定性"},
            {"name": "分层回测", "color": "#F59E0B", "formula": "分5/10组比较收益",
             "standard": "单调递增/递减", "desc": "按因子值分组，验证因子的选股能力"},
            {"name": "t检验", "color": "#EC4899", "formula": "t = IC均值 / (IC标准差/√n)",
             "standard": "|t| > 2", "desc": "统计显著性检验，判断因子是否显著有效"},
        ]
        
        for m in methods:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.BG_SECONDARY};
                    border-radius: 8px;
                    border-top: 3px solid {m['color']};
                }}
            """)
            
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 14, 16, 14)
            card_layout.setSpacing(8)
            
            name = QLabel(m["name"])
            name.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {m['color']};")
            card_layout.addWidget(name)
            
            formula = QLabel(m["formula"])
            formula.setStyleSheet(f"""
                font-size: 11px;
                font-family: 'Consolas', monospace;
                color: {Colors.TEXT_PRIMARY};
                background-color: rgba(0,0,0,0.2);
                padding: 6px;
                border-radius: 4px;
            """)
            card_layout.addWidget(formula)
            
            standard = QLabel(f"标准: {m['standard']}")
            standard.setStyleSheet(f"font-size: 12px; color: {m['color']}; font-weight: 600;")
            card_layout.addWidget(standard)
            
            desc = QLabel(m["desc"])
            desc.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED};")
            desc.setWordWrap(True)
            card_layout.addWidget(desc)
            
            methods_row.addWidget(card)
        
        layout.addLayout(methods_row)
        
        # 避免过拟合提示
        warning = QFrame()
        warning.setStyleSheet(f"""
            QFrame {{
                background-color: #F59E0B15;
                border-radius: 8px;
                border-left: 4px solid #F59E0B;
            }}
        """)
        warning_layout = QVBoxLayout(warning)
        warning_layout.setContentsMargins(16, 12, 16, 12)
        
        warning_title = QLabel("⚠️ 避免过拟合的关键")
        warning_title.setStyleSheet(f"font-size: 14px; font-weight: 600; color: #F59E0B;")
        warning_layout.addWidget(warning_title)
        
        warning_content = QLabel(
            "• 使用样本外测试，而非仅依赖历史回测\n"
            "• 因子必须有经济学逻辑支撑，不能纯粹数据挖掘\n"
            "• 警惕数据窥探（Data Snooping）偏差\n"
            "• 考虑交易成本后的净收益\n"
            "• 进行多市场、多时期验证"
        )
        warning_content.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_SECONDARY}; line-height: 1.6;")
        warning_layout.addWidget(warning_content)
        
        layout.addWidget(warning)
        
        return frame
    
    def _create_ashare_tips_section(self) -> QFrame:
        """创建A股策略建议区域"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10B98115, stop:1 #3B82F615);
                border-radius: 12px;
                border: 1px solid #10B98140;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        
        title = QLabel("💡 A股Alpha策略建议")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: #10B981;")
        layout.addWidget(title)
        
        tips = [
            ("🔄 反转为主", "充分利用A股的短期反转效应，这是A股最强的Alpha来源。5日反转因子在A股年化超额收益可达15-25%。"),
            ("⭐ 质量筛选", "用ROE、现金流质量、盈利稳定性等指标过滤垃圾股，避免踩雷。质量因子是长期有效的防御性因子。"),
            ("💰 控制换手", "A股交易成本较高（印花税、佣金、冲击成本），高换手策略容易被成本侵蚀。建议月换手率控制在30%以内。"),
            ("🏢 行业中性", "A股行业轮动剧烈，单一行业暴露风险大。建议做行业中性化处理，避免行业集中风险。"),
            ("📐 规模适中", "避免过小市值股票的流动性问题和退市风险。建议股票池市值下限设为50亿以上。"),
        ]
        
        tips_layout = QHBoxLayout()
        tips_layout.setSpacing(16)
        
        for icon_title, desc in tips:
            tip_card = QFrame()
            tip_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.BG_PRIMARY};
                    border-radius: 8px;
                    border: 1px solid {Colors.BORDER_PRIMARY};
                }}
            """)
            
            tip_layout = QVBoxLayout(tip_card)
            tip_layout.setContentsMargins(14, 12, 14, 12)
            tip_layout.setSpacing(6)
            
            tip_title = QLabel(icon_title)
            tip_title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
            tip_layout.addWidget(tip_title)
            
            tip_desc = QLabel(desc)
            tip_desc.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED}; line-height: 1.5;")
            tip_desc.setWordWrap(True)
            tip_layout.addWidget(tip_desc)
            
            tips_layout.addWidget(tip_card)
        
        layout.addLayout(tips_layout)
        
        return frame
    
    def _create_cases_detail_section(self) -> QFrame:
        """创建案例详解区域"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border-radius: 12px;
                border: 1px solid {Colors.BORDER_PRIMARY};
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        title = QLabel("📖 案例深度解析")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)
        
        # 案例1: Fama-French
        case1 = QFrame()
        case1.setStyleSheet(f"background-color: {Colors.BG_SECONDARY}; border-radius: 8px;")
        case1_layout = QVBoxLayout(case1)
        case1_layout.setContentsMargins(16, 14, 16, 14)
        case1_layout.setSpacing(8)
        
        case1_title = QLabel("📘 Fama-French三因子模型")
        case1_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: #3B82F6;")
        case1_layout.addWidget(case1_title)
        
        case1_content = QLabel(
            "<b>历史背景：</b>1992年，诺贝尔经济学奖得主Eugene Fama和Kenneth French发表了开创性论文，"
            "证明除了市场风险外，规模因子（SMB）和价值因子（HML）也能解释股票收益的横截面差异。\n\n"
            
            "<b>核心发现：</b>\n"
            "• 小市值股票长期跑赢大市值股票（规模效应）\n"
            "• 低估值股票长期跑赢高估值股票（价值效应）\n"
            "• 这两个效应在全球多个市场都存在\n\n"
            
            "<b>实践意义：</b>三因子模型是现代因子投资的理论基石，后来扩展为五因子模型（加入盈利和投资因子）。"
            "Smart Beta ETF大多基于这一理论框架。"
        )
        case1_content.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_SECONDARY}; line-height: 1.7;")
        case1_content.setWordWrap(True)
        case1_content.setTextFormat(Qt.TextFormat.RichText)
        case1_layout.addWidget(case1_content)
        layout.addWidget(case1)
        
        # 案例2: AQR QMJ
        case2 = QFrame()
        case2.setStyleSheet(f"background-color: {Colors.BG_SECONDARY}; border-radius: 8px;")
        case2_layout = QVBoxLayout(case2)
        case2_layout.setContentsMargins(16, 14, 16, 14)
        case2_layout.setSpacing(8)
        
        case2_title = QLabel("📗 AQR Quality Minus Junk")
        case2_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: #10B981;")
        case2_layout.addWidget(case2_title)
        
        case2_content = QLabel(
            "<b>策略来源：</b>AQR Capital Management是全球最大的量化对冲基金之一，由Cliff Asness创立。"
            "QMJ策略是其公开发表的经典质量因子策略。\n\n"
            
            "<b>质量定义：</b>\n"
            "• 盈利能力：ROE、ROA、毛利率、现金流收益率\n"
            "• 成长性：盈利增长、资产增长、利润率提升\n"
            "• 安全性：低杠杆、低波动、高流动性\n\n"
            
            "<b>策略逻辑：</b>做多高质量股票（Quality），做空低质量股票（Junk）。"
            "研究表明，高质量股票不仅收益更高，而且在市场下跌时更抗跌。\n\n"
            
            "<b>历史表现：</b>1957-2012年美股年化超额收益约4%，夏普比率0.5以上，在多个国家市场都有效。"
        )
        case2_content.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_SECONDARY}; line-height: 1.7;")
        case2_content.setWordWrap(True)
        case2_content.setTextFormat(Qt.TextFormat.RichText)
        case2_layout.addWidget(case2_content)
        layout.addWidget(case2)
        
        # 案例3: A股反转
        case3 = QFrame()
        case3.setStyleSheet(f"background-color: {Colors.BG_SECONDARY}; border-radius: 8px;")
        case3_layout = QVBoxLayout(case3)
        case3_layout.setContentsMargins(16, 14, 16, 14)
        case3_layout.setSpacing(8)
        
        case3_title = QLabel("📙 A股短期反转策略")
        case3_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: #F59E0B;")
        case3_layout.addWidget(case3_title)
        
        case3_content = QLabel(
            "<b>A股特色：</b>与美股的动量效应不同，A股市场短期反转效应非常显著。"
            "这与A股散户占比高、情绪波动大、涨跌停限制等特点密切相关。\n\n"
            
            "<b>策略逻辑：</b>\n"
            "• 买入近期下跌的股票（被过度抛售）\n"
            "• 卖出近期上涨的股票（被过度追捧）\n"
            "• 利用散户的过度反应获取收益\n\n"
            
            "<b>实施要点：</b>\n"
            "• 反转周期：5日效果最佳，20日次之\n"
            "• 调仓频率：周度调仓，平衡收益和成本\n"
            "• 风控措施：排除ST股、新股、停牌股\n\n"
            
            "<b>历史表现：</b>2010-2020年A股年化超额收益15-25%，但需要严格控制交易成本，"
            "高换手率可能侵蚀大部分收益。"
        )
        case3_content.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_SECONDARY}; line-height: 1.7;")
        case3_content.setWordWrap(True)
        case3_content.setTextFormat(Qt.TextFormat.RichText)
        case3_layout.addWidget(case3_content)
        layout.addWidget(case3)
        
        return frame
    
    def _create_tools_section(self) -> QFrame:
        """创建平台工具对照区域"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border-radius: 12px;
                border: 1px solid {Colors.BORDER_PRIMARY};
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        title = QLabel("🛠️ 本平台提供的Alpha工程工具")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)
        
        intro = QLabel(
            "韬睿量化平台为Alpha工程的每个环节提供专业工具支持，帮助您从因子研究到策略实盘的全流程："
        )
        intro.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_SECONDARY};")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        
        # 工具卡片
        tools_row = QHBoxLayout()
        tools_row.setSpacing(12)
        
        tools = [
            {"icon": "📚", "name": "因子库", "desc": "164个因子定义、公式、解读", "color": Colors.PRIMARY},
            {"icon": "🏆", "name": "经典因子库", "desc": "WorldQuant、Fama-French参考", "color": "#10B981"},
            {"icon": "💡", "name": "应用案例", "desc": "经过验证的多因子组合策略", "color": "#F59E0B"},
            {"icon": "🔧", "name": "因子计算", "desc": "连接JQData实时计算因子", "color": "#3B82F6"},
            {"icon": "🛠️", "name": "策略开发", "desc": "→ 进入策略开发模块", "color": "#EC4899"},
        ]
        
        for tool in tools:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.BG_SECONDARY};
                    border-radius: 8px;
                    border: 1px solid {Colors.BORDER_PRIMARY};
                }}
                QFrame:hover {{
                    border-color: {tool['color']}80;
                }}
            """)
            
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 14, 16, 14)
            card_layout.setSpacing(8)
            card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            icon = QLabel(tool["icon"])
            icon.setStyleSheet("font-size: 28px;")
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(icon)
            
            name = QLabel(tool["name"])
            name.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {tool['color']};")
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(name)
            
            desc = QLabel(tool["desc"])
            desc.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED};")
            desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
            desc.setWordWrap(True)
            card_layout.addWidget(desc)
            
            tools_row.addWidget(card)
        
        layout.addLayout(tools_row)
        
        return frame
    
    def _create_factor_sources_cards(self) -> QFrame:
        """创建因子来源卡片组"""
        container = QFrame()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        sources = [
            {"icon": "📊", "title": "风险溢价", "color": "#10B981",
             "examples": ["价值因子", "规模因子"], "theory": "承担风险获得补偿"},
            {"icon": "🧠", "title": "行为偏差", "color": "#3B82F6",
             "examples": ["动量因子", "反转因子"], "theory": "投资者非理性行为"},
            {"icon": "🏛️", "title": "结构因素", "color": "#F59E0B",
             "examples": ["流动性溢价", "低波动"], "theory": "市场结构性机会"},
            {"icon": "📰", "title": "信息优势", "color": "#EC4899",
             "examples": ["盈利修正", "另类数据"], "theory": "更快处理信息"},
        ]
        
        for s in sources:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.BG_PRIMARY};
                    border-radius: 12px;
                    border-left: 4px solid {s['color']};
                    border-top: 1px solid {Colors.BORDER_PRIMARY};
                    border-right: 1px solid {Colors.BORDER_PRIMARY};
                    border-bottom: 1px solid {Colors.BORDER_PRIMARY};
                }}
                QFrame:hover {{
                    background-color: {s['color']}08;
                }}
            """)
            
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 16, 16, 16)
            card_layout.setSpacing(8)
            
            # 头部
            header = QHBoxLayout()
            icon = QLabel(s["icon"])
            icon.setStyleSheet(f"font-size: 24px;")
            header.addWidget(icon)
            
            title = QLabel(s["title"])
            title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {s['color']};")
            header.addWidget(title)
            header.addStretch()
            card_layout.addLayout(header)
            
            # 理论
            theory = QLabel(s["theory"])
            theory.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_SECONDARY};")
            card_layout.addWidget(theory)
            
            # 示例
            examples = QLabel("例: " + "、".join(s["examples"]))
            examples.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED};")
            card_layout.addWidget(examples)
            
            layout.addWidget(card)
        
        return container
    
    def _create_ashare_factor_cards(self) -> QFrame:
        """创建A股因子有效性卡片"""
        container = QFrame()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        factors = [
            {"name": "短期反转", "icon": "🔄", "stars": 5, "color": "#10B981",
             "note": "A股最强因子！"},
            {"name": "质量因子", "icon": "⭐", "stars": 4, "color": "#3B82F6",
             "note": "ROE长期有效"},
            {"name": "小市值", "icon": "📐", "stars": 4, "color": "#F59E0B",
             "note": "注册制后减弱"},
            {"name": "价值因子", "icon": "💰", "stars": 3, "color": "#EC4899",
             "note": "需配合质量"},
            {"name": "动量因子", "icon": "🚀", "stars": 3, "color": "#8B5CF6",
             "note": "中期有效"},
            {"name": "北向资金", "icon": "💹", "stars": 3, "color": "#06B6D4",
             "note": "聪明钱效应"},
        ]
        
        for f in factors:
            card = QFrame()
            card.setFixedHeight(100)
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.BG_PRIMARY};
                    border-radius: 10px;
                    border: 1px solid {Colors.BORDER_PRIMARY};
                }}
                QFrame:hover {{
                    border-color: {f['color']}80;
                }}
            """)
            
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)
            card_layout.setSpacing(4)
            
            # 头部
            header = QHBoxLayout()
            icon = QLabel(f["icon"])
            icon.setStyleSheet("font-size: 18px;")
            header.addWidget(icon)
            
            name = QLabel(f["name"])
            name.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
            header.addWidget(name)
            header.addStretch()
            card_layout.addLayout(header)
            
            # 星级
            stars = QLabel("★" * f["stars"] + "☆" * (5 - f["stars"]))
            stars.setStyleSheet(f"font-size: 14px; color: {f['color']};")
            card_layout.addWidget(stars)
            
            # 备注
            note = QLabel(f["note"])
            note.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED};")
            card_layout.addWidget(note)
            
            layout.addWidget(card)
        
        return container
    
    def _create_case_cards(self) -> QFrame:
        """创建经典案例卡片"""
        container = QFrame()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        cases = [
            {
                "title": "Fama-French 三因子",
                "color": "#3B82F6",
                "formula": "R = α + β₁MKT + β₂SMB + β₃HML",
                "return": "年化超额 3-5%",
                "desc": "市场+规模+价值，因子投资理论基石"
            },
            {
                "title": "AQR Quality Minus Junk",
                "color": "#10B981",
                "formula": "Quality = 盈利 + 成长 + 安全",
                "return": "年化超额 4%+",
                "desc": "做多高质量，做空低质量股票"
            },
            {
                "title": "A股短期反转策略",
                "color": "#F59E0B",
                "formula": "反转 = -1 × 过去5日收益",
                "return": "年化超额 15-25%",
                "desc": "利用散户情绪过度反应获利"
            },
        ]
        
        for case in cases:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {case['color']}15, stop:1 {Colors.BG_PRIMARY});
                    border-radius: 12px;
                    border: 1px solid {case['color']}40;
                }}
                QFrame:hover {{
                    border-color: {case['color']}80;
                }}
            """)
            
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(20, 18, 20, 18)
            card_layout.setSpacing(10)
            
            # 标题
            title = QLabel(case["title"])
            title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {case['color']};")
            card_layout.addWidget(title)
            
            # 公式
            formula = QLabel(case["formula"])
            formula.setStyleSheet(f"""
                font-size: 12px;
                font-family: 'Consolas', monospace;
                color: {Colors.TEXT_PRIMARY};
                background-color: rgba(0,0,0,0.2);
                padding: 8px;
                border-radius: 6px;
            """)
            card_layout.addWidget(formula)
            
            # 收益
            ret = QLabel(f"📈 {case['return']}")
            ret.setStyleSheet(f"font-size: 13px; color: {case['color']}; font-weight: 600;")
            card_layout.addWidget(ret)
            
            # 描述
            desc = QLabel(case["desc"])
            desc.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_MUTED};")
            desc.setWordWrap(True)
            card_layout.addWidget(desc)
            
            card_layout.addStretch()
            layout.addWidget(card)
        
        return container
    
    def _create_cta_section(self) -> QFrame:
        """创建底部行动召唤区域"""
        cta = QFrame()
        cta.setFixedHeight(100)
        cta.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.PRIMARY}30, stop:1 {Colors.ACCENT}30);
                border-radius: 16px;
                border: 1px solid {Colors.PRIMARY}40;
            }}
        """)
        
        layout = QHBoxLayout(cta)
        layout.setContentsMargins(32, 0, 32, 0)
        
        # 左侧文字
        left = QVBoxLayout()
        title = QLabel("🎯 开始您的Alpha工程之旅")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        left.addWidget(title)
        
        desc = QLabel("探索164个量化因子，构建属于您的多因子策略")
        desc.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_SECONDARY};")
        left.addWidget(desc)
        
        layout.addLayout(left)
        layout.addStretch()
        
        # 右侧按钮
        btn = QPushButton("📚 进入因子库 →")
        btn.setFixedSize(160, 44)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY}DD;
            }}
        """)
        btn.clicked.connect(lambda: self.tab_widget.setCurrentIndex(1))
        layout.addWidget(btn)
        
        return cta
    
    def _create_factor_library_tab(self) -> QWidget:
        """创建因子库选项卡"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 左侧：因子分类
        left_panel = QFrame()
        left_panel.setFixedWidth(280)
        left_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border-right: 1px solid {Colors.BORDER_PRIMARY};
            }}
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # 标题
        header = QFrame()
        header.setFixedHeight(70)
        header.setStyleSheet(f"background-color: {Colors.BG_SECONDARY}; border-bottom: 1px solid {Colors.BORDER_PRIMARY};")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        
        title = QLabel("📊 因子构建")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        header_layout.addWidget(title)
        
        subtitle = QLabel(f"共 {sum(len(cat['factors']) for cat in FACTOR_DATABASE.values())} 个因子")
        subtitle.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_MUTED};")
        header_layout.addWidget(subtitle)
        
        left_layout.addWidget(header)
        
        # 搜索框
        search_frame = QFrame()
        search_frame.setStyleSheet(f"background-color: {Colors.BG_PRIMARY}; border-bottom: 1px solid {Colors.BORDER_PRIMARY};")
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(12, 8, 12, 8)
        
        self.factor_search = QLineEdit()
        self.factor_search.setPlaceholderText("🔍 搜索因子...")
        self.factor_search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 8px 12px;
                color: {Colors.TEXT_PRIMARY};
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {Colors.PRIMARY};
            }}
        """)
        self.factor_search.textChanged.connect(self._on_factor_search)
        search_layout.addWidget(self.factor_search)
        
        left_layout.addWidget(search_frame)
        
        # 分类列表
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderHidden(True)
        self.category_tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {Colors.BG_PRIMARY};
                border: none;
                color: {Colors.TEXT_PRIMARY};
                font-size: 13px;
            }}
            QTreeWidget::item {{
                padding: 8px 4px;
                border-radius: 4px;
            }}
            QTreeWidget::item:selected {{
                background-color: {Colors.PRIMARY}30;
                color: {Colors.PRIMARY};
            }}
            QTreeWidget::item:hover:!selected {{
                background-color: {Colors.BG_SECONDARY};
            }}
        """)
        self.category_tree.itemClicked.connect(self._on_category_selected)
        
        # 填充分类
        for cat_id, cat_data in FACTOR_DATABASE.items():
            cat_item = QTreeWidgetItem([f"{cat_data['icon']} {cat_data['name'].replace(cat_data['icon'], '').strip()} ({len(cat_data['factors'])})"])
            cat_item.setData(0, Qt.ItemDataRole.UserRole, cat_id)
            
            for factor in cat_data['factors']:
                factor_item = QTreeWidgetItem([f"  {factor['name']}"])
                factor_item.setData(0, Qt.ItemDataRole.UserRole, factor)
                cat_item.addChild(factor_item)
            
            self.category_tree.addTopLevelItem(cat_item)
        
        self.category_tree.expandAll()
        left_layout.addWidget(self.category_tree)
        
        layout.addWidget(left_panel)
        
        # 右侧：因子详情
        right_panel = QFrame()
        right_panel.setStyleSheet(f"background-color: {Colors.BG_SECONDARY};")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(24, 20, 24, 20)
        right_layout.setSpacing(16)
        
        # 因子详情区域
        self.factor_detail = QTextEdit()
        self.factor_detail.setReadOnly(True)
        self.factor_detail.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                padding: 16px;
                color: {Colors.TEXT_PRIMARY};
                font-size: 14px;
            }}
        """)
        self.factor_detail.setHtml(self._get_welcome_html())
        
        right_layout.addWidget(self.factor_detail)
        
        layout.addWidget(right_panel)
        
        return widget
    
    def _create_classic_factors_tab(self) -> QWidget:
        """创建经典因子库选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # 标题
        title = QLabel("🏆 经典量化因子库参考")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)
        
        desc = QLabel("全球顶级量化机构和学术界的因子研究成果，可作为开发新因子组合的参考")
        desc.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_MUTED};")
        layout.addWidget(desc)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {Colors.BG_SECONDARY};
            }}
        """)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)
        
        for lib in CLASSIC_FACTOR_LIBRARIES:
            card = self._create_library_card(lib)
            content_layout.addWidget(card)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return widget
    
    def _create_library_card(self, lib: dict) -> QFrame:
        """创建因子库卡片"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 12px;
            }}
            QFrame:hover {{
                border-color: {Colors.PRIMARY};
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        
        # 标题行
        title_layout = QHBoxLayout()
        
        name = QLabel(lib["name"])
        name.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        title_layout.addWidget(name)
        
        count_badge = QLabel(f"{lib['factors_count']} 因子")
        count_badge.setStyleSheet(f"""
            font-size: 11px;
            font-weight: 600;
            color: {Colors.PRIMARY};
            background-color: {Colors.PRIMARY}20;
            padding: 4px 10px;
            border-radius: 10px;
        """)
        title_layout.addWidget(count_badge)
        
        title_layout.addStretch()
        
        # 打开链接按钮
        open_btn = QPushButton("🔗 打开")
        open_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_LIGHT};
            }}
        """)
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(lib["url"])))
        title_layout.addWidget(open_btn)
        
        layout.addLayout(title_layout)
        
        # 描述
        desc = QLabel(lib["description"])
        desc.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_SECONDARY};")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # 标签
        tags_layout = QHBoxLayout()
        tags_layout.setSpacing(6)
        for tag in lib["tags"]:
            tag_label = QLabel(tag)
            tag_label.setStyleSheet(f"""
                font-size: 11px;
                color: {Colors.TEXT_MUTED};
                background-color: {Colors.BG_SECONDARY};
                padding: 3px 8px;
                border-radius: 4px;
            """)
            tags_layout.addWidget(tag_label)
        tags_layout.addStretch()
        layout.addLayout(tags_layout)
        
        # 示例
        example_frame = QFrame()
        example_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border-radius: 6px;
                padding: 2px;
            }}
        """)
        example_layout = QVBoxLayout(example_frame)
        example_layout.setContentsMargins(12, 10, 12, 10)
        example_layout.setSpacing(4)
        
        example_title = QLabel("📝 示例")
        example_title.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {Colors.TEXT_MUTED};")
        example_layout.addWidget(example_title)
        
        example_text = QLabel(lib["example"])
        example_text.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_SECONDARY};")
        example_text.setWordWrap(True)
        example_layout.addWidget(example_text)
        
        layout.addWidget(example_frame)
        
        # 应用说明
        app_label = QLabel(f"💡 应用: {lib['application']}")
        app_label.setStyleSheet(f"font-size: 12px; color: {Colors.SUCCESS};")
        app_label.setWordWrap(True)
        layout.addWidget(app_label)
        
        return card
    
    def _create_quant_companies_tab(self) -> QWidget:
        """创建量化公司选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # 标题
        title = QLabel("🏢 全球知名量化公司")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)
        
        desc = QLabel("全球顶级量化投资公司的方法论、成功案例及A股参与情况")
        desc.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_MUTED};")
        layout.addWidget(desc)
        
        # 分类标签
        category_frame = QFrame()
        category_layout = QHBoxLayout(category_frame)
        category_layout.setContentsMargins(0, 0, 0, 0)
        category_layout.setSpacing(12)
        
        self.company_category_btns = {}
        categories = [
            ("全部", "all", Colors.PRIMARY),
            ("国际顶级", "international", "#3B82F6"),
            ("中国头部", "china_top", "#10B981"),
            ("A股参与", "ashare", "#F59E0B"),
        ]
        
        for name, key, color in categories:
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setChecked(key == "all")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.BG_SECONDARY};
                    color: {Colors.TEXT_PRIMARY};
                    border: 2px solid {Colors.BORDER_PRIMARY};
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: 500;
                }}
                QPushButton:checked {{
                    background-color: {color};
                    color: white;
                    border-color: {color};
                }}
                QPushButton:hover:!checked {{
                    border-color: {color}80;
                }}
            """)
            btn.clicked.connect(lambda checked, k=key: self._filter_companies(k))
            category_layout.addWidget(btn)
            self.company_category_btns[key] = btn
        
        category_layout.addStretch()
        layout.addWidget(category_frame)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {Colors.BG_SECONDARY};
            }}
        """)
        
        self.companies_content = QWidget()
        self.companies_layout = QVBoxLayout(self.companies_content)
        self.companies_layout.setSpacing(16)
        
        # 加载公司数据
        self.quant_companies = self._load_quant_companies()
        self.current_filter = "all"
        self._display_companies()
        
        scroll.setWidget(self.companies_content)
        layout.addWidget(scroll)
        
        return widget
    
    def _load_quant_companies(self) -> list:
        """加载量化公司数据"""
        return [
            {
                "name": "Renaissance Technologies",
                "name_cn": "文艺复兴科技",
                "country": "美国",
                "category": "international",
                "founded": 1982,
                "aum": "$1300亿+",
                "founder": "James Simons",
                "ashare": False,
                "status": "success",
                "methodology": "统计套利、信号处理、机器学习",
                "description": "全球最成功的量化对冲基金之一，Medallion基金年化收益35%+（扣除费用前）。"
                               "以严格的保密性和数学建模著称，大量使用信号处理和机器学习技术。",
                "key_strategies": [
                    "统计套利：利用短期价格偏差",
                    "信号处理：从噪声中提取信号",
                    "机器学习：非线性模式识别",
                    "高频交易：微秒级交易执行"
                ],
                "success_metrics": "Medallion基金1988-2018年扣除费用后年化收益39%，"
                                  "被誉为'量化投资界的圣杯'",
                "ashare_info": "未公开参与A股市场",
                "website": "https://www.rentec.com"
            },
            {
                "name": "Two Sigma",
                "name_cn": "双西格玛",
                "country": "美国",
                "category": "international",
                "founded": 2001,
                "aum": "$600亿+",
                "founder": "David Siegel, John Overdeck",
                "ashare": False,
                "status": "success",
                "methodology": "大数据、机器学习、分布式计算",
                "description": "以技术驱动著称的量化对冲基金，大量使用大数据和机器学习技术。"
                               "拥有超过2000名员工，其中大部分是工程师和数据科学家。",
                "key_strategies": [
                    "大数据分析：处理PB级数据",
                    "机器学习：深度学习、强化学习",
                    "分布式系统：大规模并行计算",
                    "另类数据：卫星图像、社交媒体"
                ],
                "success_metrics": "管理规模快速增长，多只基金长期跑赢市场",
                "ashare_info": "未公开参与A股市场",
                "website": "https://www.twosigma.com"
            },
            {
                "name": "AQR Capital Management",
                "name_cn": "AQR资本管理",
                "country": "美国",
                "category": "international",
                "founded": 1998,
                "aum": "$1000亿+",
                "founder": "Cliff Asness",
                "ashare": False,
                "status": "success",
                "methodology": "因子投资、系统化策略、学术研究",
                "description": "以因子投资和学术研究著称，公开发表大量研究论文。"
                               "创始人Cliff Asness是Fama-French三因子模型的共同开发者之一。",
                "key_strategies": [
                    "因子投资：价值、动量、质量、低波动",
                    "系统化策略：规则化、可重复",
                    "多资产配置：股票、债券、商品",
                    "学术研究：公开发表研究成果"
                ],
                "success_metrics": "多只Smart Beta策略基金长期有效，"
                                  "Quality Minus Junk因子年化超额4%+",
                "ashare_info": "未公开参与A股市场",
                "website": "https://www.aqr.com"
            },
            {
                "name": "D.E. Shaw & Co.",
                "name_cn": "德劭",
                "country": "美国",
                "category": "international",
                "founded": 1988,
                "aum": "$500亿+",
                "founder": "David E. Shaw",
                "ashare": False,
                "status": "success",
                "methodology": "量化交易、计算金融、算法优化",
                "description": "以计算金融和算法交易著称，创始人David Shaw是计算机科学家。"
                               "在量化交易、统计套利等领域有深厚积累。",
                "key_strategies": [
                    "统计套利：配对交易、均值回归",
                    "算法交易：最优执行算法",
                    "计算金融：高性能计算",
                    "多策略组合：分散风险"
                ],
                "success_metrics": "长期稳定收益，多只基金年化收益15%+",
                "ashare_info": "未公开参与A股市场",
                "website": "https://www.deshaw.com"
            },
            {
                "name": "Citadel",
                "name_cn": "城堡投资",
                "country": "美国",
                "category": "international",
                "founded": 1990,
                "aum": "$500亿+",
                "founder": "Kenneth Griffin",
                "ashare": False,
                "status": "success",
                "methodology": "多策略、高频交易、做市",
                "description": "全球最大的对冲基金之一，业务涵盖量化交易、做市、私募股权等。"
                               "在高频交易和做市业务方面处于领先地位。",
                "key_strategies": [
                    "高频交易：微秒级交易",
                    "做市业务：提供流动性",
                    "多策略：股票、债券、商品、外汇",
                    "另类投资：私募股权、房地产"
                ],
                "success_metrics": "Wellington基金长期年化收益20%+，"
                                  "做市业务全球领先",
                "ashare_info": "未公开参与A股市场",
                "website": "https://www.citadel.com"
            },
            {
                "name": "九坤投资",
                "name_cn": "九坤投资",
                "country": "中国",
                "category": "china_top",
                "founded": 2012,
                "aum": "600亿+",
                "founder": "王琛、姚齐聪",
                "ashare": True,
                "status": "success",
                "methodology": "机器学习、高频交易、多因子模型",
                "description": "中国头部量化私募，以机器学习和高频交易见长。"
                               "在A股市场有深厚积累，管理规模长期位居行业前列。",
                "key_strategies": [
                    "机器学习：深度学习、强化学习",
                    "高频交易：毫秒级交易执行",
                    "多因子模型：价值、动量、质量、反转",
                    "另类数据：新闻情绪、资金流向"
                ],
                "success_metrics": "多只产品年化收益20%+，"
                                  "2020-2021年规模快速增长",
                "ashare_info": "深度参与A股，主要策略包括：\n"
                              "• 中高频量化选股\n"
                              "• 统计套利\n"
                              "• 事件驱动策略",
                "website": "https://www.jiukun.com"
            },
            {
                "name": "幻方量化",
                "name_cn": "幻方量化",
                "country": "中国",
                "category": "china_top",
                "founded": 2015,
                "aum": "500亿+",
                "founder": "梁文锋",
                "ashare": True,
                "status": "success",
                "methodology": "深度学习、强化学习、超算集群",
                "description": "以深度学习技术著称，自建超算集群进行模型训练。"
                               "在AI量化领域处于国内领先地位。",
                "key_strategies": [
                    "深度学习：神经网络、CNN、RNN",
                    "强化学习：DQN、PPO等算法",
                    "超算集群：自建算力基础设施",
                    "高频策略：微秒级交易"
                ],
                "success_metrics": "2020-2021年业绩突出，"
                                  "多只产品年化收益30%+",
                "ashare_info": "专注A股市场，主要策略：\n"
                              "• AI量化选股\n"
                              "• 高频交易\n"
                              "• 机器学习策略",
                "website": "https://www.hfquant.com"
            },
            {
                "name": "明汯投资",
                "name_cn": "明汯投资",
                "country": "中国",
                "category": "china_top",
                "founded": 2014,
                "aum": "500亿+",
                "founder": "裘慧明",
                "ashare": True,
                "status": "success",
                "methodology": "多因子模型、统计套利、机器学习",
                "description": "中国量化私募头部机构，以多因子模型和统计套利见长。"
                               "在A股市场有长期稳定表现。",
                "key_strategies": [
                    "多因子模型：价值、成长、质量、动量",
                    "统计套利：配对交易、均值回归",
                    "机器学习：特征工程、模型优化",
                    "风险控制：动态对冲、组合优化"
                ],
                "success_metrics": "长期年化收益15-20%，"
                                  "回撤控制较好",
                "ashare_info": "深度参与A股，策略包括：\n"
                              "• 量化选股\n"
                              "• 统计套利\n"
                              "• 市场中性策略",
                "website": "https://www.mhfund.com"
            },
            {
                "name": "灵均投资",
                "name_cn": "灵均投资",
                "country": "中国",
                "category": "china_top",
                "founded": 2014,
                "aum": "400亿+",
                "founder": "马志宇",
                "ashare": True,
                "status": "success",
                "methodology": "多因子、机器学习、高频交易",
                "description": "中国头部量化私募，以多因子模型和机器学习技术见长。"
                               "在A股市场有稳定表现。",
                "key_strategies": [
                    "多因子模型：基本面+技术面",
                    "机器学习：XGBoost、LightGBM",
                    "高频交易：日内交易策略",
                    "风险模型：Barra风险模型"
                ],
                "success_metrics": "多只产品年化收益15-25%",
                "ashare_info": "专注A股市场，主要策略：\n"
                              "• 量化选股\n"
                              "• 市场中性\n"
                              "• 指数增强",
                "website": "https://www.lingjun.com"
            },
            {
                "name": "启林投资",
                "name_cn": "启林投资",
                "country": "中国",
                "category": "china_top",
                "founded": 2015,
                "aum": "300亿+",
                "founder": "王鸿勇",
                "ashare": True,
                "status": "success",
                "methodology": "多因子、机器学习、另类数据",
                "description": "中国量化私募头部机构，以多因子模型和另类数据应用见长。",
                "key_strategies": [
                    "多因子模型：基本面+技术面+另类数据",
                    "机器学习：特征选择、模型融合",
                    "另类数据：新闻情绪、资金流向",
                    "风险控制：动态调整、组合优化"
                ],
                "success_metrics": "长期年化收益15-20%",
                "ashare_info": "深度参与A股，策略包括：\n"
                              "• 量化选股\n"
                              "• 市场中性\n"
                              "• 指数增强",
                "website": "https://www.qilin.com"
            },
            {
                "name": "因诺资产",
                "name_cn": "因诺资产",
                "country": "中国",
                "category": "china_top",
                "founded": 2014,
                "aum": "200亿+",
                "founder": "徐书楠",
                "ashare": True,
                "status": "success",
                "methodology": "CTA、量化选股、套利",
                "description": "中国量化私募，以CTA策略和量化选股见长。"
                               "在商品期货和股票市场都有布局。",
                "key_strategies": [
                    "CTA策略：趋势跟踪、均值回归",
                    "量化选股：多因子模型",
                    "套利策略：期现套利、跨期套利",
                    "多策略组合：分散风险"
                ],
                "success_metrics": "CTA策略表现突出，"
                                  "多只产品年化收益20%+",
                "ashare_info": "参与A股，主要策略：\n"
                              "• 量化选股\n"
                              "• 市场中性\n"
                              "• 指数增强",
                "website": "https://www.innofund.com"
            },
            {
                "name": "Two Sigma Asia Pacific",
                "name_cn": "双西格玛亚太",
                "country": "美国（亚太）",
                "category": "international",
                "founded": 2012,
                "aum": "未公开",
                "founder": "Two Sigma",
                "ashare": True,
                "status": "success",
                "methodology": "大数据、机器学习、量化交易",
                "description": "Two Sigma的亚太分支机构，参与包括A股在内的亚太市场。"
                               "使用与总部相同的技术平台和方法论。",
                "key_strategies": [
                    "机器学习：深度学习、强化学习",
                    "大数据分析：处理海量数据",
                    "量化交易：多策略组合",
                    "另类数据：本地化数据源"
                ],
                "success_metrics": "在亚太市场有稳定表现",
                "ashare_info": "通过QFII/RQFII等渠道参与A股，"
                              "主要策略包括量化选股和统计套利",
                "website": "https://www.twosigma.com"
            },
            {
                "name": "Winton Capital",
                "name_cn": "温顿资本",
                "country": "英国",
                "category": "international",
                "founded": 1997,
                "aum": "$200亿+",
                "founder": "David Harding",
                "ashare": False,
                "status": "success",
                "methodology": "系统化交易、趋势跟踪、机器学习",
                "description": "英国最大的量化对冲基金之一，以系统化交易和趋势跟踪见长。"
                               "在商品期货和股票市场都有布局。",
                "key_strategies": [
                    "趋势跟踪：CTA策略",
                    "系统化交易：规则化执行",
                    "机器学习：模式识别",
                    "多资产：股票、债券、商品"
                ],
                "success_metrics": "长期年化收益15%+，"
                                  "CTA策略表现突出",
                "ashare_info": "未公开参与A股市场",
                "website": "https://www.winton.com"
            },
            {
                "name": "WorldQuant",
                "name_cn": "世坤投资",
                "country": "美国",
                "category": "international",
                "founded": 2007,
                "aum": "$50亿+",
                "founder": "Igor Tulchinsky",
                "ashare": False,
                "status": "success",
                "methodology": "Alpha研究、因子挖掘、系统化交易",
                "description": "以Alpha研究和因子挖掘著称，公开发表101 Alpha和191 Alpha因子库。"
                               "通过众包模式让全球研究员参与因子开发。",
                "key_strategies": [
                    "Alpha研究：因子挖掘",
                    "系统化交易：规则化执行",
                    "众包研究：全球研究员网络",
                    "因子组合：多因子模型"
                ],
                "success_metrics": "公开发表101/191 Alpha因子库，"
                                  "成为量化研究的重要参考",
                "ashare_info": "未公开参与A股市场",
                "website": "https://www.worldquant.com"
            },
            {
                "name": "Optiver",
                "name_cn": "奥普提弗",
                "country": "荷兰",
                "category": "international",
                "founded": 1986,
                "aum": "未公开",
                "founder": "Johann Kaemingk",
                "ashare": True,
                "status": "success",
                "methodology": "做市、高频交易、期权交易",
                "description": "全球领先的做市商和高频交易公司，在期权和股票做市方面处于领先地位。"
                               "在中国设有分支机构，参与A股市场。",
                "key_strategies": [
                    "做市业务：提供流动性",
                    "高频交易：微秒级交易",
                    "期权交易：波动率交易",
                    "统计套利：配对交易"
                ],
                "success_metrics": "做市业务全球领先，"
                                  "在多个交易所提供流动性",
                "ashare_info": "通过QFII等渠道参与A股，"
                              "主要业务包括做市和高频交易",
                "website": "https://www.optiver.com"
            },
            {
                "name": "Jane Street",
                "name_cn": "简街资本",
                "country": "美国",
                "category": "international",
                "founded": 2000,
                "aum": "未公开",
                "founder": "Tim Reynolds, Michael Jenkins",
                "ashare": False,
                "status": "success",
                "methodology": "做市、高频交易、套利",
                "description": "全球领先的做市商，在ETF、股票、期权等市场提供流动性。"
                               "以技术驱动和工程师文化著称。",
                "key_strategies": [
                    "做市业务：ETF、股票、期权",
                    "高频交易：微秒级执行",
                    "套利策略：跨市场套利",
                    "风险管理：实时风控系统"
                ],
                "success_metrics": "做市业务全球领先，"
                                  "日交易量巨大",
                "ashare_info": "未公开参与A股市场",
                "website": "https://www.janestreet.com"
            },
            {
                "name": "Virtu Financial",
                "name_cn": "Virtu金融",
                "country": "美国",
                "category": "international",
                "founded": 2008,
                "aum": "未公开",
                "founder": "Vincent Viola",
                "ashare": False,
                "status": "success",
                "methodology": "做市、高频交易、算法交易",
                "description": "全球领先的做市商，在多个交易所提供流动性。"
                               "2015年上市，成为首家上市的做市商。",
                "key_strategies": [
                    "做市业务：股票、期权、ETF",
                    "高频交易：微秒级交易",
                    "算法交易：最优执行",
                    "风险管理：实时监控"
                ],
                "success_metrics": "2015年上市，"
                                  "做市业务稳定盈利",
                "ashare_info": "未公开参与A股市场",
                "website": "https://www.virtu.com"
            },
            {
                "name": "Millennium Management",
                "name_cn": "千禧管理",
                "country": "美国",
                "category": "international",
                "founded": 1989,
                "aum": "$600亿+",
                "founder": "Israel Englander",
                "ashare": False,
                "status": "success",
                "methodology": "多策略、量化交易、相对价值",
                "description": "全球最大的对冲基金之一，采用多策略平台模式。"
                               "旗下有多个量化交易团队。",
                "key_strategies": [
                    "多策略平台：分散风险",
                    "量化交易：统计套利、因子投资",
                    "相对价值：配对交易",
                    "事件驱动：并购套利"
                ],
                "success_metrics": "长期年化收益15%+，"
                                  "多策略平台模式成功",
                "ashare_info": "未公开参与A股市场",
                "website": "https://www.mlp.com"
            },
            {
                "name": "Point72",
                "name_cn": "Point72",
                "country": "美国",
                "category": "international",
                "founded": 2014,
                "aum": "$200亿+",
                "founder": "Steven Cohen",
                "ashare": False,
                "status": "success",
                "methodology": "多策略、量化交易、基本面研究",
                "description": "前SAC Capital，由Steven Cohen创立。"
                               "采用多策略模式，包括量化交易和基本面研究。",
                "key_strategies": [
                    "多策略：量化+基本面",
                    "量化交易：统计套利",
                    "基本面研究：深度研究",
                    "另类数据：卫星图像、社交媒体"
                ],
                "success_metrics": "长期稳定收益",
                "ashare_info": "未公开参与A股市场",
                "website": "https://www.point72.com"
            },
            {
                "name": "Balyasny Asset Management",
                "name_cn": "Balyasny资产管理",
                "country": "美国",
                "category": "international",
                "founded": 2001,
                "aum": "$200亿+",
                "founder": "Dmitry Balyasny",
                "ashare": False,
                "status": "success",
                "methodology": "多策略、量化交易、基本面研究",
                "description": "多策略对冲基金，采用平台模式。"
                               "旗下有多个量化交易团队。",
                "key_strategies": [
                    "多策略平台：分散风险",
                    "量化交易：统计套利、因子投资",
                    "基本面研究：深度研究",
                    "风险管理：严格风控"
                ],
                "success_metrics": "长期稳定收益",
                "ashare_info": "未公开参与A股市场",
                "website": "https://www.bamfunds.com"
            },
            {
                "name": "宽德投资",
                "name_cn": "宽德投资",
                "country": "中国",
                "category": "china_top",
                "founded": 2014,
                "aum": "200亿+",
                "founder": "徐御之",
                "ashare": True,
                "status": "success",
                "methodology": "高频交易、量化选股、统计套利",
                "description": "中国量化私募，以高频交易和量化选股见长。"
                               "在A股市场有稳定表现。",
                "key_strategies": [
                    "高频交易：日内交易",
                    "量化选股：多因子模型",
                    "统计套利：配对交易",
                    "风险控制：动态对冲"
                ],
                "success_metrics": "多只产品年化收益15-20%",
                "ashare_info": "专注A股市场，主要策略：\n"
                              "• 高频交易\n"
                              "• 量化选股\n"
                              "• 市场中性",
                "website": "https://www.kuande.com"
            },
            {
                "name": "衍复投资",
                "name_cn": "衍复投资",
                "country": "中国",
                "category": "china_top",
                "founded": 2019,
                "aum": "300亿+",
                "founder": "高亢",
                "ashare": True,
                "status": "success",
                "methodology": "多因子模型、机器学习、高频交易",
                "description": "中国量化私募新锐，以多因子模型和机器学习见长。"
                               "规模快速增长。",
                "key_strategies": [
                    "多因子模型：基本面+技术面",
                    "机器学习：特征工程、模型优化",
                    "高频交易：日内交易",
                    "风险模型：Barra风险模型"
                ],
                "success_metrics": "2020-2021年业绩突出，"
                                  "规模快速增长",
                "ashare_info": "专注A股市场，主要策略：\n"
                              "• 量化选股\n"
                              "• 市场中性\n"
                              "• 指数增强",
                "website": "https://www.yanfu.com"
            },
            {
                "name": "佳期投资",
                "name_cn": "佳期投资",
                "country": "中国",
                "category": "china_top",
                "founded": 2014,
                "aum": "200亿+",
                "founder": "季强",
                "ashare": True,
                "status": "success",
                "methodology": "高频交易、机器学习、量化选股",
                "description": "中国头部量化私募，以高频交易和机器学习见长。"
                               "在A股市场有稳定表现，管理规模位居行业前列。",
                "key_strategies": [
                    "高频交易：毫秒级交易执行",
                    "机器学习：深度学习、强化学习",
                    "量化选股：多因子模型",
                    "统计套利：配对交易、均值回归"
                ],
                "success_metrics": "多只产品年化收益20%+，"
                                  "高频策略表现突出",
                "ashare_info": "深度参与A股市场，主要策略：\n"
                              "• 高频交易\n"
                              "• 量化选股\n"
                              "• 市场中性\n"
                              "• 统计套利",
                "website": "https://www.jiaqi.com"
            },
            {
                "name": "白鹭资管",
                "name_cn": "白鹭资管",
                "country": "中国",
                "category": "china_top",
                "founded": 2013,
                "aum": "150亿+",
                "founder": "章寅",
                "ashare": True,
                "status": "success",
                "methodology": "多策略、量化选股、CTA",
                "description": "中国量化私募，以多策略组合见长。"
                               "在股票和商品期货市场都有布局。",
                "key_strategies": [
                    "量化选股：多因子模型",
                    "CTA策略：趋势跟踪、均值回归",
                    "市场中性：对冲策略",
                    "多策略组合：分散风险"
                ],
                "success_metrics": "长期年化收益15-20%",
                "ashare_info": "参与A股市场，主要策略：\n"
                              "• 量化选股\n"
                              "• 市场中性\n"
                              "• 指数增强",
                "website": "https://www.bailu.com"
            },
            {
                "name": "金锝资产",
                "name_cn": "金锝资产",
                "country": "中国",
                "category": "china_top",
                "founded": 2012,
                "aum": "100亿+",
                "founder": "任思泓",
                "ashare": True,
                "status": "success",
                "methodology": "量化选股、市场中性、多因子模型",
                "description": "中国量化私募，以量化选股和市场中性策略见长。"
                               "在A股市场有长期稳定表现。",
                "key_strategies": [
                    "量化选股：多因子模型",
                    "市场中性：对冲策略",
                    "风险控制：动态调整",
                    "组合优化：风险模型约束"
                ],
                "success_metrics": "长期年化收益15-18%",
                "ashare_info": "专注A股市场，主要策略：\n"
                              "• 量化选股\n"
                              "• 市场中性\n"
                              "• 指数增强",
                "website": "https://www.jinde.com"
            },
            {
                "name": "进化论资产",
                "name_cn": "进化论资产",
                "country": "中国",
                "category": "china_top",
                "founded": 2014,
                "aum": "200亿+",
                "founder": "王一平",
                "ashare": True,
                "status": "success",
                "methodology": "量化选股、机器学习、多策略",
                "description": "中国量化私募，以量化选股和机器学习技术见长。"
                               "在A股市场有稳定表现。",
                "key_strategies": [
                    "量化选股：多因子模型",
                    "机器学习：特征工程、模型优化",
                    "市场中性：对冲策略",
                    "多策略组合：分散风险"
                ],
                "success_metrics": "多只产品年化收益15-25%",
                "ashare_info": "深度参与A股市场，主要策略：\n"
                              "• 量化选股\n"
                              "• 市场中性\n"
                              "• 指数增强",
                "website": "https://www.evolution.com"
            },
            {
                "name": "天演资本",
                "name_cn": "天演资本",
                "country": "中国",
                "category": "china_top",
                "founded": 2014,
                "aum": "150亿+",
                "founder": "谢晓阳",
                "ashare": True,
                "status": "success",
                "methodology": "量化选股、高频交易、机器学习",
                "description": "中国量化私募，以量化选股和高频交易见长。"
                               "在A股市场有稳定表现。",
                "key_strategies": [
                    "量化选股：多因子模型",
                    "高频交易：日内交易",
                    "机器学习：模型优化",
                    "风险控制：动态调整"
                ],
                "success_metrics": "长期年化收益15-20%",
                "ashare_info": "专注A股市场，主要策略：\n"
                              "• 量化选股\n"
                              "• 高频交易\n"
                              "• 市场中性",
                "website": "https://www.tianyan.com"
            },
            {
                "name": "鸣石投资",
                "name_cn": "鸣石投资",
                "country": "中国",
                "category": "china_top",
                "founded": 2010,
                "aum": "100亿+",
                "founder": "袁宇",
                "ashare": True,
                "status": "success",
                "methodology": "量化选股、多因子模型、机器学习",
                "description": "中国量化私募，以量化选股和多因子模型见长。"
                               "在A股市场有长期稳定表现。",
                "key_strategies": [
                    "量化选股：多因子模型",
                    "机器学习：特征选择、模型融合",
                    "市场中性：对冲策略",
                    "风险控制：组合优化"
                ],
                "success_metrics": "长期年化收益15-18%",
                "ashare_info": "深度参与A股市场，主要策略：\n"
                              "• 量化选股\n"
                              "• 市场中性\n"
                              "• 指数增强",
                "website": "https://www.mingshi.com"
            },
            {
                "name": "诚奇资产",
                "name_cn": "诚奇资产",
                "country": "中国",
                "category": "china_top",
                "founded": 2013,
                "aum": "100亿+",
                "founder": "何文奇",
                "ashare": True,
                "status": "success",
                "methodology": "量化选股、多因子模型、机器学习",
                "description": "中国量化私募，以量化选股和机器学习技术见长。"
                               "在A股市场有稳定表现。",
                "key_strategies": [
                    "量化选股：多因子模型",
                    "机器学习：XGBoost、LightGBM",
                    "市场中性：对冲策略",
                    "风险控制：动态调整"
                ],
                "success_metrics": "长期年化收益15-20%",
                "ashare_info": "专注A股市场，主要策略：\n"
                              "• 量化选股\n"
                              "• 市场中性\n"
                              "• 指数增强",
                "website": "https://www.chengqi.com"
            },
            {
                "name": "赫富投资",
                "name_cn": "赫富投资",
                "country": "中国",
                "category": "china_top",
                "founded": 2016,
                "aum": "80亿+",
                "founder": "蔡觉逸",
                "ashare": True,
                "status": "success",
                "methodology": "量化选股、机器学习、高频交易",
                "description": "中国量化私募新锐，以量化选股和机器学习见长。"
                               "规模快速增长。",
                "key_strategies": [
                    "量化选股：多因子模型",
                    "机器学习：深度学习、强化学习",
                    "高频交易：日内交易",
                    "风险控制：组合优化"
                ],
                "success_metrics": "2020-2021年业绩突出，"
                                  "规模快速增长",
                "ashare_info": "专注A股市场，主要策略：\n"
                              "• 量化选股\n"
                              "• 市场中性\n"
                              "• 指数增强",
                "website": "https://www.hefu.com"
            },
            {
                "name": "黑翼资产",
                "name_cn": "黑翼资产",
                "country": "中国",
                "category": "china_top",
                "founded": 2014,
                "aum": "100亿+",
                "founder": "陈泽浩、邹倚天",
                "ashare": True,
                "status": "success",
                "methodology": "CTA、量化选股、多策略",
                "description": "中国量化私募，以CTA策略和量化选股见长。"
                               "在商品期货和股票市场都有布局。",
                "key_strategies": [
                    "CTA策略：趋势跟踪、均值回归",
                    "量化选股：多因子模型",
                    "市场中性：对冲策略",
                    "多策略组合：分散风险"
                ],
                "success_metrics": "CTA策略表现突出，"
                                  "多只产品年化收益20%+",
                "ashare_info": "参与A股市场，主要策略：\n"
                              "• 量化选股\n"
                              "• 市场中性\n"
                              "• 指数增强",
                "website": "https://www.heiyi.com"
            },
            {
                "name": "思勰投资",
                "name_cn": "思勰投资",
                "country": "中国",
                "category": "china_top",
                "founded": 2016,
                "aum": "80亿+",
                "founder": "吴家麒、陈磐颖",
                "ashare": True,
                "status": "success",
                "methodology": "CTA、量化选股、高频交易",
                "description": "中国量化私募，以CTA策略和高频交易见长。"
                               "在商品期货和股票市场都有布局。",
                "key_strategies": [
                    "CTA策略：趋势跟踪、均值回归",
                    "量化选股：多因子模型",
                    "高频交易：日内交易",
                    "多策略组合：分散风险"
                ],
                "success_metrics": "CTA策略表现突出，"
                                  "多只产品年化收益20%+",
                "ashare_info": "参与A股市场，主要策略：\n"
                              "• 量化选股\n"
                              "• CTA策略\n"
                              "• 市场中性",
                "website": "https://www.sixie.com"
            },
        ]
    
    def _filter_companies(self, category: str):
        """筛选公司"""
        # 更新按钮状态
        for key, btn in self.company_category_btns.items():
            btn.setChecked(key == category)
        
        self.current_filter = category
        self._display_companies()
    
    def _display_companies(self):
        """显示公司列表"""
        # 清空现有内容
        while self.companies_layout.count():
            item = self.companies_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 筛选公司
        filtered = []
        for company in self.quant_companies:
            if self.current_filter == "all":
                filtered.append(company)
            elif self.current_filter == "international":
                if company["category"] == "international":
                    filtered.append(company)
            elif self.current_filter == "china_top":
                if company["category"] == "china_top":
                    filtered.append(company)
            elif self.current_filter == "ashare":
                if company.get("ashare", False):
                    filtered.append(company)
        
        # 显示公司卡片
        for company in filtered:
            card = self._create_company_card(company)
            self.companies_layout.addWidget(card)
        
        self.companies_layout.addStretch()
    
    def _create_company_card(self, company: dict) -> QFrame:
        """创建公司卡片"""
        card = QFrame()
        
        # 根据状态设置颜色
        status_color = "#10B981" if company["status"] == "success" else "#F59E0B"
        border_color = status_color if company.get("ashare", False) else Colors.BORDER_PRIMARY
        
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 2px solid {border_color};
                border-radius: 12px;
            }}
            QFrame:hover {{
                border-color: {Colors.PRIMARY};
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # 头部：公司名称和标签
        header = QHBoxLayout()
        
        name_layout = QVBoxLayout()
        name_layout.setSpacing(4)
        
        name = QLabel(company["name"])
        name.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        name_layout.addWidget(name)
        
        if company.get("name_cn"):
            name_cn = QLabel(company["name_cn"])
            name_cn.setStyleSheet(f"font-size: 14px; color: {Colors.TEXT_MUTED};")
            name_layout.addWidget(name_cn)
        
        header.addLayout(name_layout)
        header.addStretch()
        
        # 标签组
        tags_layout = QHBoxLayout()
        tags_layout.setSpacing(8)
        
        # 国家标签
        country_tag = QLabel(f"🌍 {company['country']}")
        country_tag.setStyleSheet(f"""
            font-size: 11px;
            color: {Colors.TEXT_SECONDARY};
            background-color: {Colors.BG_SECONDARY};
            padding: 4px 10px;
            border-radius: 10px;
        """)
        tags_layout.addWidget(country_tag)
        
        # 状态标签
        status_text = "✅ 成功" if company["status"] == "success" else "⚠️ 待观察"
        status_tag = QLabel(status_text)
        status_tag.setStyleSheet(f"""
            font-size: 11px;
            font-weight: 600;
            color: white;
            background-color: {status_color};
            padding: 4px 10px;
            border-radius: 10px;
        """)
        tags_layout.addWidget(status_tag)
        
        # A股标签
        if company.get("ashare"):
            ashare_tag = QLabel("🇨🇳 A股参与")
            ashare_tag.setStyleSheet(f"""
                font-size: 11px;
                font-weight: 600;
                color: white;
                background-color: #F59E0B;
                padding: 4px 10px;
                border-radius: 10px;
            """)
            tags_layout.addWidget(ashare_tag)
        
        header.addLayout(tags_layout)
        layout.addLayout(header)
        
        # 基本信息
        info_frame = QFrame()
        info_frame.setStyleSheet(f"background-color: {Colors.BG_SECONDARY}; border-radius: 8px;")
        info_layout = QGridLayout(info_frame)
        info_layout.setContentsMargins(16, 12, 16, 12)
        info_layout.setSpacing(12)
        
        info_items = [
            ("📅 成立", f"{company['founded']}年"),
            ("💰 管理规模", company.get("aum", "未公开")),
            ("👤 创始人", company.get("founder", "未公开")),
        ]
        
        for i, (label, value) in enumerate(info_items):
            label_widget = QLabel(label)
            label_widget.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_MUTED};")
            info_layout.addWidget(label_widget, i, 0)
            
            value_widget = QLabel(value)
            value_widget.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
            info_layout.addWidget(value_widget, i, 1)
        
        layout.addWidget(info_frame)
        
        # 方法论
        method_label = QLabel("🔬 核心方法论")
        method_label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {Colors.PRIMARY};")
        layout.addWidget(method_label)
        
        method_text = QLabel(company["methodology"])
        method_text.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_SECONDARY};")
        method_text.setWordWrap(True)
        layout.addWidget(method_text)
        
        # 描述
        desc = QLabel(company["description"])
        desc.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_SECONDARY}; line-height: 1.6;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # 核心策略
        strategies_label = QLabel("📋 核心策略")
        strategies_label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {Colors.PRIMARY};")
        layout.addWidget(strategies_label)
        
        strategies_frame = QFrame()
        strategies_frame.setStyleSheet(f"background-color: {Colors.BG_SECONDARY}; border-radius: 8px;")
        strategies_layout = QVBoxLayout(strategies_frame)
        strategies_layout.setContentsMargins(14, 10, 14, 10)
        strategies_layout.setSpacing(6)
        
        for strategy in company["key_strategies"]:
            strategy_item = QLabel(f"• {strategy}")
            strategy_item.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_SECONDARY};")
            strategy_item.setWordWrap(True)
            strategies_layout.addWidget(strategy_item)
        
        layout.addWidget(strategies_frame)
        
        # 成功指标
        success_label = QLabel("📈 成功指标")
        success_label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: #10B981;")
        layout.addWidget(success_label)
        
        success_text = QLabel(company["success_metrics"])
        success_text.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_SECONDARY}; line-height: 1.6;")
        success_text.setWordWrap(True)
        layout.addWidget(success_text)
        
        # A股参与信息
        if company.get("ashare"):
            ashare_label = QLabel("🇨🇳 A股参与情况")
            ashare_label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: #F59E0B;")
            layout.addWidget(ashare_label)
            
            ashare_frame = QFrame()
            ashare_frame.setStyleSheet(f"""
                background-color: #F59E0B15;
                border-left: 4px solid #F59E0B;
                border-radius: 6px;
            """)
            ashare_layout = QVBoxLayout(ashare_frame)
            ashare_layout.setContentsMargins(14, 10, 14, 10)
            
            ashare_text = QLabel(company["ashare_info"])
            ashare_text.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_SECONDARY}; line-height: 1.6;")
            ashare_text.setWordWrap(True)
            ashare_layout.addWidget(ashare_text)
            
            layout.addWidget(ashare_frame)
        
        # 网站链接
        if company.get("website"):
            website_btn = QPushButton(f"🌐 访问官网")
            website_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            website_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.PRIMARY};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 12px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {Colors.PRIMARY_LIGHT};
                }}
            """)
            website_btn.clicked.connect(lambda checked, url=company["website"]: 
                                       QDesktopServices.openUrl(QUrl(url)))
            layout.addWidget(website_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        return card
    
    def _create_examples_tab(self) -> QWidget:
        """创建应用案例选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # 标题
        title = QLabel("💡 因子组合应用案例")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)
        
        desc = QLabel("经过回测验证的因子组合策略，可直接复用或作为参考")
        desc.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_MUTED};")
        layout.addWidget(desc)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {Colors.BG_SECONDARY}; }}")
        
        content = QWidget()
        content_layout = QGridLayout(content)
        content_layout.setSpacing(16)
        
        for i, example in enumerate(FACTOR_APPLICATION_EXAMPLES):
            card = self._create_example_card(example)
            content_layout.addWidget(card, i // 2, i % 2)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return widget
    
    def _create_example_card(self, example: dict) -> QFrame:
        """创建应用案例卡片"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        
        # 标题
        name = QLabel(example["name"])
        name.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(name)
        
        # 描述
        desc = QLabel(example["description"])
        desc.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_MUTED};")
        layout.addWidget(desc)
        
        # 因子配置
        factors_text = " + ".join([f"{f}({w})" for f, w in zip(example["factors"], example["weights"])])
        factors_label = QLabel(f"📊 因子: {factors_text}")
        factors_label.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_SECONDARY};")
        factors_label.setWordWrap(True)
        layout.addWidget(factors_label)
        
        # 参数
        params = QLabel(f"📈 股票池: {example['stock_pool']} | 调仓: {example['rebalance']}")
        params.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED};")
        layout.addWidget(params)
        
        # 回测结果
        results_layout = QHBoxLayout()
        
        ret_label = QLabel(f"收益: {example['backtest_return']}")
        ret_label.setStyleSheet(f"font-size: 12px; color: {Colors.SUCCESS}; font-weight: 600;")
        results_layout.addWidget(ret_label)
        
        dd_label = QLabel(f"回撤: {example['max_drawdown']}")
        dd_label.setStyleSheet(f"font-size: 12px; color: {Colors.ERROR}; font-weight: 600;")
        results_layout.addWidget(dd_label)
        
        results_layout.addStretch()
        layout.addLayout(results_layout)
        
        # 代码示例
        code_btn = QPushButton("📋 查看代码")
        code_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        code_btn.clicked.connect(lambda: self._show_code_example(example))
        layout.addWidget(code_btn)
        
        return card
    
    def _create_factor_calc_tab(self) -> QWidget:
        """创建因子计算选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # 标题
        title = QLabel("🔧 因子计算")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)
        
        # 配置区域
        config_frame = QFrame()
        config_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
            }}
        """)
        config_layout = QFormLayout(config_frame)
        config_layout.setContentsMargins(16, 16, 16, 16)
        config_layout.setSpacing(12)
        
        # 股票池选择
        self.stock_pool_combo = QComboBox()
        self.stock_pool_combo.addItems(["沪深300", "中证500", "中证1000", "全A股"])
        self.stock_pool_combo.setStyleSheet(self._get_combo_style())
        config_layout.addRow("股票池:", self.stock_pool_combo)
        
        # 因子选择
        self.factor_list = QListWidget()
        self.factor_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.factor_list.setMaximumHeight(150)
        self.factor_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                color: {Colors.TEXT_PRIMARY};
            }}
            QListWidget::item:selected {{
                background-color: {Colors.PRIMARY}30;
                color: {Colors.PRIMARY};
            }}
        """)
        
        for cat_data in FACTOR_DATABASE.values():
            for factor in cat_data['factors']:
                item = QListWidgetItem(f"{cat_data['icon']} {factor['name']}")
                item.setData(Qt.ItemDataRole.UserRole, factor['id'])
                self.factor_list.addItem(item)
        
        config_layout.addRow("选择因子:", self.factor_list)
        
        layout.addWidget(config_frame)
        
        # 计算按钮
        calc_btn = QPushButton("🚀 开始计算")
        calc_btn.setStyleSheet(ButtonStyles.PRIMARY)
        calc_btn.setFixedHeight(44)
        calc_btn.clicked.connect(self._on_calculate_factors)
        layout.addWidget(calc_btn)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                height: 20px;
                text-align: center;
                color: {Colors.TEXT_PRIMARY};
            }}
            QProgressBar::chunk {{
                background-color: {Colors.PRIMARY};
                border-radius: 5px;
            }}
        """)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 结果区域
        self.result_table = QTableWidget()
        self.result_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                color: {Colors.TEXT_PRIMARY};
                gridline-color: {Colors.BORDER_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                padding: 8px;
                border: none;
                font-weight: 600;
            }}
        """)
        layout.addWidget(self.result_table)
        
        return widget
    
    def _create_strategy_gen_tab(self) -> QWidget:
        """创建策略生成选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # 标题
        title = QLabel("🚀 PTrade策略代码生成")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)
        
        desc = QLabel("根据因子配置自动生成可在PTrade/QMT平台运行的策略代码")
        desc.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_MUTED};")
        layout.addWidget(desc)
        
        # 配置区域
        config_frame = QFrame()
        config_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
            }}
        """)
        config_layout = QFormLayout(config_frame)
        config_layout.setContentsMargins(16, 16, 16, 16)
        config_layout.setSpacing(12)
        
        # 策略名称
        self.strategy_name_input = QLineEdit()
        self.strategy_name_input.setPlaceholderText("my_factor_strategy")
        self.strategy_name_input.setStyleSheet(self._get_input_style())
        config_layout.addRow("策略名称:", self.strategy_name_input)
        
        # 持仓数量
        self.hold_num_spin = QSpinBox()
        self.hold_num_spin.setRange(5, 100)
        self.hold_num_spin.setValue(30)
        self.hold_num_spin.setStyleSheet(self._get_spin_style())
        config_layout.addRow("持仓数量:", self.hold_num_spin)
        
        # 调仓周期
        self.rebalance_combo = QComboBox()
        self.rebalance_combo.addItems(["每日", "每周", "每月", "每季度"])
        self.rebalance_combo.setCurrentIndex(2)
        self.rebalance_combo.setStyleSheet(self._get_combo_style())
        config_layout.addRow("调仓周期:", self.rebalance_combo)
        
        layout.addWidget(config_frame)
        
        # 生成按钮
        gen_btn = QPushButton("⚡ 生成策略代码")
        gen_btn.setStyleSheet(ButtonStyles.PRIMARY)
        gen_btn.setFixedHeight(44)
        gen_btn.clicked.connect(self._on_generate_strategy)
        layout.addWidget(gen_btn)
        
        # 代码预览
        self.code_preview = QTextEdit()
        self.code_preview.setStyleSheet(f"""
            QTextEdit {{
                background-color: #1e1e1e;
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                padding: 12px;
                color: #d4d4d4;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 13px;
            }}
        """)
        self.code_preview.setPlaceholderText("生成的策略代码将显示在这里...")
        layout.addWidget(self.code_preview)
        
        return widget
    
    def _get_welcome_html(self) -> str:
        """获取欢迎页HTML"""
        return f"""
        <div style="color: {Colors.TEXT_PRIMARY}; font-family: 'Microsoft YaHei', sans-serif; padding: 20px;">
            <h2 style="color: {Colors.PRIMARY};">👈 选择左侧因子查看详情</h2>
            <p style="color: {Colors.TEXT_MUTED};">
                本因子库包含 {sum(len(cat['factors']) for cat in FACTOR_DATABASE.values())} 个量化因子，
                涵盖价值、成长、质量、动量、反转、波动、流动性、情绪、技术等多个维度。
            </p>
            <hr style="border-color: {Colors.BORDER_PRIMARY};">
            <h3 style="color: {Colors.SUCCESS};">📊 因子分类</h3>
            <ul style="color: {Colors.TEXT_SECONDARY};">
                <li><b>价值因子</b> - PE、PB、股息率等估值指标</li>
                <li><b>成长因子</b> - 营收增速、利润增速等</li>
                <li><b>质量因子</b> - ROE、毛利率、现金流质量 (A股最有效)</li>
                <li><b>动量因子</b> - 价格动量、相对强度</li>
                <li><b>反转因子</b> - 短期反转 (A股最强因子)</li>
                <li><b>波动因子</b> - 波动率、Beta、最大回撤</li>
                <li><b>流动性因子</b> - 换手率、成交额</li>
                <li><b>情绪因子</b> - 北向资金、主力资金、分析师预期</li>
                <li><b>技术因子</b> - RSI、MACD、布林带等</li>
            </ul>
        </div>
        """
    
    def _on_category_selected(self, item: QTreeWidgetItem, column: int):
        """选择因子分类或因子"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if isinstance(data, str):
            # 选择了分类
            cat_data = FACTOR_DATABASE.get(data)
            if cat_data:
                self._show_category_detail(cat_data)
        elif isinstance(data, dict):
            # 选择了具体因子
            self._show_factor_detail(data)
    
    def _show_category_detail(self, cat_data: dict):
        """显示分类详情"""
        factors_html = ""
        for f in cat_data['factors']:
            direction = "↑越高越好" if f['direction'] == 'positive' else ("↓越低越好" if f['direction'] == 'negative' else "—中性")
            factors_html += f"""
            <tr style="border-bottom: 1px solid {Colors.BORDER_PRIMARY};">
                <td style="padding: 8px;">{f['name']}</td>
                <td style="padding: 8px; color: {Colors.TEXT_MUTED};">{f['formula']}</td>
                <td style="padding: 8px; color: {'#10B981' if f['direction'] == 'positive' else '#EF4444' if f['direction'] == 'negative' else Colors.TEXT_MUTED};">{direction}</td>
            </tr>
            """
        
        html = f"""
        <div style="color: {Colors.TEXT_PRIMARY}; font-family: 'Microsoft YaHei', sans-serif;">
            <h2 style="color: {Colors.PRIMARY};">{cat_data['name']}</h2>
            <p style="color: {Colors.TEXT_MUTED};">{cat_data['description']}</p>
            <p style="color: {Colors.WARNING};">A股有效性: {cat_data['effectiveness']}</p>
            <hr style="border-color: {Colors.BORDER_PRIMARY};">
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background: {Colors.BG_TERTIARY};">
                    <th style="padding: 10px; text-align: left;">因子名称</th>
                    <th style="padding: 10px; text-align: left;">计算公式</th>
                    <th style="padding: 10px; text-align: left;">方向</th>
                </tr>
                {factors_html}
            </table>
        </div>
        """
        self.factor_detail.setHtml(html)
    
    def _show_factor_detail(self, factor: dict):
        """显示因子详情"""
        direction = "越高越好 ↑" if factor['direction'] == 'positive' else ("越低越好 ↓" if factor['direction'] == 'negative' else "中性 —")
        direction_color = Colors.SUCCESS if factor['direction'] == 'positive' else (Colors.ERROR if factor['direction'] == 'negative' else Colors.TEXT_MUTED)
        
        html = f"""
        <div style="color: {Colors.TEXT_PRIMARY}; font-family: 'Microsoft YaHei', sans-serif; padding: 10px;">
            <h2 style="color: {Colors.PRIMARY};">{factor['name']}</h2>
            
            <div style="background: {Colors.BG_TERTIARY}; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <h4 style="color: {Colors.TEXT_MUTED}; margin: 0 0 8px 0;">📐 计算公式</h4>
                <p style="color: {Colors.TEXT_PRIMARY}; font-size: 16px; margin: 0;">{factor['formula']}</p>
            </div>
            
            <div style="background: {Colors.BG_TERTIARY}; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <h4 style="color: {Colors.TEXT_MUTED}; margin: 0 0 8px 0;">📊 因子方向</h4>
                <p style="color: {direction_color}; font-size: 16px; font-weight: bold; margin: 0;">{direction}</p>
            </div>
            
            <div style="background: {Colors.BG_TERTIARY}; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <h4 style="color: {Colors.TEXT_MUTED}; margin: 0 0 8px 0;">💡 解读</h4>
                <p style="color: {Colors.TEXT_SECONDARY}; margin: 0;">{factor['interpretation']}</p>
            </div>
            
            <hr style="border-color: {Colors.BORDER_PRIMARY};">
            
            <h4 style="color: {Colors.SUCCESS};">🔧 使用示例</h4>
            <pre style="background: #1e1e1e; padding: 15px; border-radius: 8px; color: #d4d4d4; font-family: Consolas, monospace;">
# 在PTrade策略中使用 {factor['name']}
factor_value = get_factor_values(
    securities=stocks,
    factors=['{factor['id']}'],
    end_date=context.current_dt
)

# 根据因子值排序选股
sorted_stocks = factor_value.sort_values(
    by='{factor['id']}',
    ascending={'True' if factor['direction'] == 'negative' else 'False'}
)
            </pre>
        </div>
        """
        self.factor_detail.setHtml(html)
    
    def _on_factor_search(self, text: str):
        """搜索因子"""
        search_text = text.lower()
        
        for i in range(self.category_tree.topLevelItemCount()):
            cat_item = self.category_tree.topLevelItem(i)
            cat_visible = False
            
            for j in range(cat_item.childCount()):
                factor_item = cat_item.child(j)
                factor_data = factor_item.data(0, Qt.ItemDataRole.UserRole)
                
                if isinstance(factor_data, dict):
                    visible = (search_text in factor_data['name'].lower() or
                              search_text in factor_data.get('formula', '').lower() or
                              search_text in factor_data.get('interpretation', '').lower())
                    factor_item.setHidden(not visible)
                    if visible:
                        cat_visible = True
            
            cat_item.setHidden(not cat_visible and bool(search_text))
    
    def _show_code_example(self, example: dict):
        """显示代码示例"""
        QMessageBox.information(
            self,
            f"📋 {example['name']} 代码示例",
            example['code_example'],
            QMessageBox.StandardButton.Ok
        )
    
    def _on_calculate_factors(self):
        """计算因子"""
        if self.factor_manager is None:
            QMessageBox.warning(self, "错误", "因子管理器未初始化，请先连接JQData")
            return
        
        selected_items = self.factor_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请至少选择一个因子")
            return
        
        # 获取股票池
        pool_map = {"沪深300": "000300.XSHG", "中证500": "000905.XSHG", 
                   "中证1000": "000852.XSHG", "全A股": "all_a"}
        pool_name = self.stock_pool_combo.currentText()
        
        try:
            import jqdatasdk as jq
            if pool_name == "全A股":
                stocks = jq.get_all_securities(types=['stock']).index.tolist()[:500]  # 限制数量
            else:
                stocks = jq.get_index_stocks(pool_map[pool_name])
            
            # 获取可用日期
            date = self.jq_client.get_available_date() if self.jq_client else datetime.now().strftime('%Y-%m-%d')
            
            # 因子名称映射（从FACTOR_DATABASE到实际因子名）
            factor_map = {
                'ep': 'EP', 'bp': 'BP', 'sp': 'SP', 'dividend_yield': 'DividendYield',
                'roe': 'ROE', 'gross_margin': 'GrossMargin', 'asset_turnover': 'AssetTurnover',
                'revenue_growth_yoy': 'RevenueGrowth', 'profit_growth_yoy': 'ProfitGrowth',
                'price_momentum': 'PriceMomentum', 'reversal': 'Reversal',
                'size': 'Size', 'volatility': 'Volatility', 'turnover': 'Turnover'
            }
            
            # 计算因子
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            results = {}
            factor_names = []
            for item in selected_items:
                factor_id = item.data(Qt.ItemDataRole.UserRole)
                factor_name = factor_map.get(factor_id.lower(), factor_id)
                if factor_name in self.factor_manager.list_factors():
                    factor_names.append(factor_name)
            
            if not factor_names:
                QMessageBox.warning(self, "提示", "所选因子在当前因子库中不存在")
                return
            
            # 批量计算
            total = len(factor_names)
            for i, name in enumerate(factor_names):
                self.progress_bar.setValue(int((i + 1) / total * 100))
                try:
                    result = self.factor_manager.calculate_factor(name, stocks[:100], date)  # 限制股票数
                    if result:
                        results[name] = result
                except Exception as e:
                    logger.warning(f"因子计算失败 {name}: {e}")
            
            self.progress_bar.setVisible(False)
            
            # 显示结果
            self._display_factor_results(results)
            
        except Exception as e:
            logger.error(f"因子计算失败: {e}")
            QMessageBox.critical(self, "错误", f"因子计算失败:\n{e}")
    
    def _display_factor_results(self, results: dict):
        """显示因子计算结果"""
        if not results:
            return
        
        # 构建表格
        all_stocks = set()
        for result in results.values():
            all_stocks.update(result.values.index.tolist())
        
        self.result_table.setRowCount(len(all_stocks))
        self.result_table.setColumnCount(len(results) + 1)
        
        headers = ["股票代码"] + list(results.keys())
        self.result_table.setHorizontalHeaderLabels(headers)
        
        for row, stock in enumerate(sorted(all_stocks)):
            self.result_table.setItem(row, 0, QTableWidgetItem(stock))
            
            for col, (name, result) in enumerate(results.items(), 1):
                value = result.values.get(stock)
                if pd.notna(value):
                    item = QTableWidgetItem(f"{value:.4f}")
                    self.result_table.setItem(row, col, item)
                else:
                    self.result_table.setItem(row, col, QTableWidgetItem("-"))
        
        self.result_table.resizeColumnsToContents()
    
    def _on_generate_strategy(self):
        """生成策略代码"""
        strategy_name = self.strategy_name_input.text() or "my_factor_strategy"
        hold_num = self.hold_num_spin.value()
        rebalance = self.rebalance_combo.currentText()
        
        code = f'''# -*- coding: utf-8 -*-
"""
{strategy_name} - 多因子量化策略
生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
持仓数量: {hold_num}
调仓周期: {rebalance}
"""

def initialize(context):
    """策略初始化"""
    g.stock_pool = '000300.XSHG'  # 沪深300
    g.hold_num = {hold_num}
    g.factors = {{
        'ep': 0.3,      # 盈利收益率
        'roe': 0.3,     # ROE
        'reversal': 0.2, # 反转因子
        'volatility': -0.2  # 低波动（负权重）
    }}
    log.info("多因子策略初始化完成")

def before_trading_start(context):
    """每日开盘前"""
    g.stocks = get_index_stocks(g.stock_pool)

def handle_data(context, data):
    """策略主逻辑"""
    # 获取因子数据并计算综合得分
    # ... 因子计算逻辑 ...
    pass
'''
        
        self.code_preview.setPlainText(code)
    
    def _get_combo_style(self) -> str:
        return f"""
            QComboBox {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 8px 12px;
                color: {Colors.TEXT_PRIMARY};
                min-width: 200px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                selection-background-color: {Colors.PRIMARY};
            }}
        """
    
    def _get_input_style(self) -> str:
        return f"""
            QLineEdit {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 8px 12px;
                color: {Colors.TEXT_PRIMARY};
                min-width: 200px;
            }}
            QLineEdit:focus {{
                border-color: {Colors.PRIMARY};
            }}
        """
    
    def _get_spin_style(self) -> str:
        return f"""
            QSpinBox {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 8px 12px;
                color: {Colors.TEXT_PRIMARY};
                min-width: 200px;
            }}
        """

