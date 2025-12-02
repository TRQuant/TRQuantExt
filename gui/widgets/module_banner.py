# -*- coding: utf-8 -*-
"""
统一模块Banner组件
==================

为所有模块提供一致的Banner样式，每个模块有独特的渐变色主题。
"""

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from gui.styles.theme import Colors


class ModuleBanner(QFrame):
    """
    统一的模块Banner组件
    
    每个模块使用不同的渐变色主题：
    - 工作台：紫蓝渐变 (#667eea → #764ba2)
    - 信息获取：青蓝渐变 (#0891b2 → #0ea5e9)
    - 市场趋势：翠绿渐变 (#059669 → #10b981)
    - 投资主线：橙红渐变 (#ea580c → #f97316)
    - 候选池：紫粉渐变 (#9333ea → #a855f7)
    - 因子构建：蓝绿渐变 (#0284c7 → #06b6d4)
    - 策略开发：金黄渐变 (#ca8a04 → #eab308)
    - 回测验证：靛蓝渐变 (#4f46e5 → #6366f1)
    - 实盘交易：红橙渐变 (#dc2626 → #ef4444)
    """
    
    # 预定义的模块主题
    THEMES = {
        "home": (Colors.MODULE_HOME_START, Colors.MODULE_HOME_END),
        "data": (Colors.MODULE_DATA_START, Colors.MODULE_DATA_END),
        "trend": (Colors.MODULE_TREND_START, Colors.MODULE_TREND_END),
        "mainline": (Colors.MODULE_MAINLINE_START, Colors.MODULE_MAINLINE_END),
        "pool": (Colors.MODULE_POOL_START, Colors.MODULE_POOL_END),
        "factor": (Colors.MODULE_FACTOR_START, Colors.MODULE_FACTOR_END),
        "strategy": (Colors.MODULE_STRATEGY_START, Colors.MODULE_STRATEGY_END),
        "backtest": (Colors.MODULE_BACKTEST_START, Colors.MODULE_BACKTEST_END),
        "trading": (Colors.MODULE_TRADING_START, Colors.MODULE_TRADING_END),
    }
    
    def __init__(self, icon: str, title: str, subtitle: str, 
                 theme: str = "home", parent=None):
        """
        初始化模块Banner
        
        Args:
            icon: 模块图标 (emoji)
            title: 模块标题
            subtitle: 模块副标题/描述
            theme: 主题名称 (home/data/trend/mainline/pool/factor/strategy/backtest/trading)
            parent: 父组件
        """
        super().__init__(parent)
        
        # 获取主题颜色
        if theme in self.THEMES:
            gradient_start, gradient_end = self.THEMES[theme]
        else:
            gradient_start, gradient_end = Colors.MODULE_HOME_START, Colors.MODULE_HOME_END
        
        self.setMinimumHeight(100)
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {gradient_start}, stop:1 {gradient_end});
                border-radius: 16px;
                border: none;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)
        
        # 图标
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("""
            font-size: 48px;
            background: rgba(255,255,255,0.2);
            border-radius: 16px;
            padding: 12px;
        """)
        icon_label.setFixedSize(80, 80)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # 文字区域
        text_layout = QVBoxLayout()
        text_layout.setSpacing(8)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 28px;
            font-weight: 800;
            color: white;
            letter-spacing: 1px;
        """)
        text_layout.addWidget(title_label)
        
        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet("""
            font-size: 14px;
            color: rgba(255,255,255,0.85);
            font-weight: 500;
        """)
        subtitle_label.setWordWrap(True)
        text_layout.addWidget(subtitle_label)
        
        layout.addLayout(text_layout)
        layout.addStretch()


# 便捷创建函数
def create_home_banner() -> ModuleBanner:
    return ModuleBanner("🎯", "策略开发工作台", 
                       "从数据分析到实盘交易的一站式量化策略开发平台", "home")

def create_data_banner() -> ModuleBanner:
    return ModuleBanner("📡", "信息获取", 
                       "多源数据接入 · 知识库管理 · 财经资讯监控", "data")

def create_trend_banner() -> ModuleBanner:
    return ModuleBanner("📈", "市场趋势识别", 
                       "综合技术分析 · 量化公司模型 · 大V观点 → 构建韬睿独有趋势判断系统", "trend")

def create_mainline_banner() -> ModuleBanner:
    return ModuleBanner("🔥", "投资主线识别", 
                       "五维量化评分 · 板块轮动分析 · 主线热点挖掘", "mainline")

def create_pool_banner() -> ModuleBanner:
    return ModuleBanner("📦", "候选池构建", 
                       "股票筛选 · ETF精选 · 多渠道数据融合 → 构建优质标的池", "pool")

def create_factor_banner() -> ModuleBanner:
    return ModuleBanner("📊", "因子构建", 
                       "经典因子库 · AI因子推荐 · 因子计算与评估", "factor")

def create_strategy_banner() -> ModuleBanner:
    return ModuleBanner("🛠️", "策略开发", 
                       "PTrade/QMT策略生成 · 参数优化 · 风险管理", "strategy")

def create_backtest_banner() -> ModuleBanner:
    return ModuleBanner("🔄", "回测验证", 
                       "历史回测 · 策略分析 · 收益归因 · 风险评估", "backtest")

def create_trading_banner() -> ModuleBanner:
    return ModuleBanner("🚀", "实盘交易", 
                       "PTrade/QMT对接 · 风控执行 · 实时监控", "trading")

