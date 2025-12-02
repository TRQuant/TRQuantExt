# -*- coding: utf-8 -*-
"""
市场趋势识别面板
================

韬睿量化专业级市场趋势分析模块。
综合技术分析、量化公司模型和大V观点，构建独有的趋势判断系统。

Tab页结构：
1. 📖 方法论 - 理论基础与韬睿量化模型
2. 🏢 量化公司模型 - 头部量化公司的趋势判断工具
3. 🎤 大V观点 - 知名投资者的趋势判断方法
4. 📊 趋势分析 - 高级交互式趋势仪表盘
5. 📈 技术指标 - 详细指标说明与计算公式
6. 🔗 策略联动 - 如何与后续模块联动
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QGroupBox, QComboBox,
    QScrollArea, QFrame, QGridLayout, QProgressBar, QSplitter,
    QMessageBox, QTextEdit, QTabWidget, QSpinBox, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QPen, QRadialGradient, QLinearGradient
import logging
import math
from datetime import datetime
from typing import Dict, Optional

from gui.styles.theme import Colors, ButtonStyles

logger = logging.getLogger(__name__)


# ========== 模块Banner组件 ==========
class ModuleBanner(QFrame):
    """统一的模块Banner组件"""
    
    def __init__(self, icon: str, title: str, subtitle: str, 
                 gradient_start: str, gradient_end: str, parent=None):
        super().__init__(parent)
        self.gradient_start = gradient_start
        self.gradient_end = gradient_end
        
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
        text_layout.addWidget(subtitle_label)
        
        layout.addLayout(text_layout)
        layout.addStretch()


class AdvancedTrendGauge(QWidget):
    """高级趋势仪表盘组件 - 带动画和交互效果"""
    
    clicked = pyqtSignal(str)
    
    def __init__(self, title: str = "", period: str = "short", parent=None):
        super().__init__(parent)
        self.title = title
        self.period = period
        self.score = 0
        self.target_score = 0
        self.direction = "震荡"
        self.confidence = 0.5
        self.position = "50%"
        self._animation_progress = 0
        self._hover = False
        
        self.setMinimumSize(220, 260)
        self.setMaximumSize(280, 320)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._animate)
    
    def set_data(self, score: float, direction: str, confidence: float, position: str):
        self.target_score = score
        self.direction = direction
        self.confidence = confidence
        self.position = position
        self._animation_progress = 0
        self.animation_timer.start(16)
    
    def _animate(self):
        self._animation_progress += 0.05
        if self._animation_progress >= 1:
            self._animation_progress = 1
            self.animation_timer.stop()
            self.score = self.target_score
        else:
            t = self._animation_progress
            ease = t * t * (3 - 2 * t)
            self.score = ease * self.target_score
        self.update()
    
    def _get_color_for_score(self, score: float) -> QColor:
        if score > 60:
            return QColor("#22c55e")
        elif score > 30:
            return QColor("#84cc16")
        elif score > 0:
            return QColor("#eab308")
        elif score > -30:
            return QColor("#f97316")
        elif score > -60:
            return QColor("#ef4444")
        else:
            return QColor("#dc2626")
    
    def enterEvent(self, event):
        self._hover = True
        self.update()
    
    def leaveEvent(self, event):
        self._hover = False
        self.update()
    
    def mousePressEvent(self, event):
        self.clicked.emit(self.period)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        center_x = width // 2
        center_y = height // 2 - 10
        radius = min(width, height) // 2 - 40
        
        # 背景
        bg_color = QColor(Colors.BG_CARD if self._hover else Colors.BG_TERTIARY)
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(QColor(Colors.BORDER_LIGHT if self._hover else Colors.BORDER_PRIMARY), 2))
        painter.drawRoundedRect(2, 2, width - 4, height - 4, 16, 16)
        
        # 标题
        painter.setPen(QColor(Colors.TEXT_PRIMARY))
        font = QFont("", 13, QFont.Weight.Bold)
        painter.setFont(font)
        title_rect = painter.boundingRect(0, 0, width, 30, Qt.AlignmentFlag.AlignCenter, self.title)
        painter.drawText((width - title_rect.width()) // 2, 28, self.title)
        
        # 背景圆环
        arc_width = 16
        painter.setPen(QPen(QColor(Colors.BORDER_DARK), arc_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(center_x - radius, center_y - radius, radius * 2, radius * 2, -45 * 16, -270 * 16)
        
        # 趋势弧
        score_color = self._get_color_for_score(self.score)
        gradient = QLinearGradient(center_x - radius, center_y, center_x + radius, center_y)
        gradient.setColorAt(0, score_color.darker(120))
        gradient.setColorAt(1, score_color)
        
        pen = QPen(QBrush(gradient), arc_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        angle = int((self.score + 100) / 200 * 270)
        painter.drawArc(center_x - radius, center_y - radius, radius * 2, radius * 2, -45 * 16, -angle * 16)
        
        # 中心区域
        inner_radius = radius - 30
        center_gradient = QRadialGradient(center_x, center_y, inner_radius)
        center_gradient.setColorAt(0, QColor(Colors.BG_SECONDARY))
        center_gradient.setColorAt(1, QColor(Colors.BG_TERTIARY))
        painter.setBrush(QBrush(center_gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center_x - inner_radius, center_y - inner_radius, inner_radius * 2, inner_radius * 2)
        
        # 分数
        painter.setPen(score_color)
        font = QFont("", 28, QFont.Weight.Bold)
        painter.setFont(font)
        score_text = f"{self.score:+.0f}"
        score_rect = painter.boundingRect(0, 0, 100, 50, Qt.AlignmentFlag.AlignCenter, score_text)
        painter.drawText(center_x - score_rect.width() // 2, center_y + 10, score_text)
        
        # 方向
        font = QFont("", 11, QFont.Weight.Bold)
        painter.setFont(font)
        dir_rect = painter.boundingRect(0, 0, 100, 30, Qt.AlignmentFlag.AlignCenter, self.direction)
        painter.drawText(center_x - dir_rect.width() // 2, center_y + 35, self.direction)
        
        # 底部信息
        info_y = height - 50
        painter.setPen(QColor(Colors.TEXT_SECONDARY))
        font = QFont("", 10)
        painter.setFont(font)
        painter.drawText(20, info_y, f"置信度: {self.confidence * 100:.0f}%")
        
        pos_text = f"仓位: {self.position}"
        pos_rect = painter.boundingRect(0, 0, 100, 20, Qt.AlignmentFlag.AlignRight, pos_text)
        painter.drawText(width - pos_rect.width() - 20, info_y, pos_text)
        
        # 置信度条
        bar_y = info_y + 10
        bar_width = width - 40
        painter.setBrush(QBrush(QColor(Colors.BORDER_DARK)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(20, bar_y, bar_width, 4, 2, 2)
        painter.setBrush(QBrush(score_color))
        painter.drawRoundedRect(20, bar_y, int(bar_width * self.confidence), 4, 2, 2)


class TrendAnalysisWorker(QThread):
    """趋势分析工作线程"""
    
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, jq_client, index_code: str = "000001.XSHG"):
        super().__init__()
        self.jq_client = jq_client
        self.index_code = index_code
    
    def run(self):
        try:
            self.progress.emit("正在获取市场数据...")
            from core.trend_analyzer import TrendAnalyzer
            analyzer = TrendAnalyzer(jq_client=self.jq_client)
            self.progress.emit("正在计算技术指标...")
            result = analyzer.analyze_market(self.index_code)
            if result:
                self.progress.emit("分析完成")
                self.finished.emit(result.to_dict())
            else:
                self.error.emit("趋势分析失败")
        except Exception as e:
            logger.error(f"趋势分析失败: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))


class MarketTrendPanel(QWidget):
    """市场趋势面板 - 韬睿量化专业趋势分析"""
    
    trend_updated = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.jq_client = None
        self.worker = None
        self.current_result = None
        
        self._init_jq_client()
        self._init_ui()
        self._load_cached_result()
    
    def _init_jq_client(self):
        try:
            from jqdata.client import JQDataClient
            from config.config_manager import get_config_manager
            config_manager = get_config_manager()
            config = config_manager.get_jqdata_config()
            username = config.get('username', '')
            password = config.get('password', '')
            if username and password:
                self.jq_client = JQDataClient()
                if self.jq_client.authenticate(username, password):
                    logger.info("市场趋势Panel: JQData连接成功")
                else:
                    self.jq_client = None
        except Exception as e:
            logger.warning(f"市场趋势Panel: JQData连接失败: {e}")
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tab控件直接在最上面
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(self._get_tab_style())
        
        # 添加所有Tab
        self.tab_widget.addTab(self._create_methodology_tab(), "📖 方法论")
        self.tab_widget.addTab(self._create_quant_models_tab(), "🏢 量化公司模型")
        self.tab_widget.addTab(self._create_kol_views_tab(), "🎤 大V观点")
        self.tab_widget.addTab(self._create_analysis_tab(), "📊 趋势分析")
        self.tab_widget.addTab(self._create_indicators_tab(), "📈 技术指标")
        self.tab_widget.addTab(self._create_capital_flow_tab(), "💰 资金流向")
        self.tab_widget.addTab(self._create_history_chart_tab(), "📉 历史图表")
        self.tab_widget.addTab(self._create_hmm_analysis_tab(), "🧠 市场状态识别")
        self.tab_widget.addTab(self._create_strategy_tab(), "🔗 策略联动")
        
        layout.addWidget(self.tab_widget)
    
    def _get_tab_style(self) -> str:
        return f"""
            QTabWidget::pane {{
                border: none;
                background-color: {Colors.BG_SECONDARY};
            }}
            QTabBar {{
                background-color: {Colors.BG_PRIMARY};
            }}
            QTabBar::tab {{
                background-color: {Colors.BG_PRIMARY};
                color: {Colors.TEXT_MUTED};
                border: none;
                padding: 12px 20px;
                font-size: 13px;
                font-weight: 600;
                min-width: 100px;
            }}
            QTabBar::tab:selected {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.MODULE_TREND_START};
                border-bottom: 3px solid {Colors.MODULE_TREND_START};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
            }}
        """
    
    # ========== Tab 1: 方法论 ==========
    def _create_methodology_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {Colors.BG_SECONDARY}; }}")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 16, 24, 24)
        content_layout.setSpacing(20)
        
        # 模块Banner（在Tab内容顶部）
        banner = self._create_module_banner()
        content_layout.addWidget(banner)
        
        # 韬睿量化模型概述
        overview = self._create_section("🎯 韬睿量化趋势判断模型", f"""
<p style="font-size: 15px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
韬睿量化构建了一套<b style="color: {Colors.TEXT_PRIMARY};">多维度融合的市场趋势判断系统</b>，
综合以下三大信息来源：
</p>

<table border="0" cellpadding="12" style="width: 100%; margin-top: 16px;">
<tr>
    <td style="background: {Colors.MODULE_TREND_START}22; border-radius: 10px; width: 33%;">
        <b style="color: {Colors.MODULE_TREND_START}; font-size: 16px;">📊 技术分析</b><br/>
        <span style="color: {Colors.TEXT_SECONDARY};">MA/MACD/RSI/布林带等<br/>经典技术指标体系</span>
    </td>
    <td style="background: {Colors.MODULE_FACTOR_START}22; border-radius: 10px; width: 33%;">
        <b style="color: {Colors.MODULE_FACTOR_START}; font-size: 16px;">🏢 量化公司</b><br/>
        <span style="color: {Colors.TEXT_SECONDARY};">贝莱德/文艺复兴/桥水<br/>等头部机构的方法论</span>
    </td>
    <td style="background: {Colors.MODULE_MAINLINE_START}22; border-radius: 10px; width: 33%;">
        <b style="color: {Colors.MODULE_MAINLINE_START}; font-size: 16px;">🎤 大V观点</b><br/>
        <span style="color: {Colors.TEXT_SECONDARY};">知名投资者的趋势<br/>判断经验与方法</span>
    </td>
</tr>
</table>

<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8; margin-top: 20px;">
<b style="color: {Colors.TEXT_PRIMARY}; font-size: 15px;">韬睿综合模型特点：</b>
</p>
<ul style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 2;">
<li><b style="color: {Colors.SUCCESS};">多源融合</b> - 不依赖单一指标，综合多种方法论</li>
<li><b style="color: {Colors.SUCCESS};">动态权重</b> - 根据市场环境自动调整各指标权重</li>
<li><b style="color: {Colors.SUCCESS};">实战验证</b> - 所有模型经过历史回测和实盘验证</li>
<li><b style="color: {Colors.SUCCESS};">持续迭代</b> - 根据市场变化不断优化模型参数</li>
</ul>
""")
        content_layout.addWidget(overview)
        
        # 理论基础
        theory = self._create_section("📚 理论基础", f"""
<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
<b style="color: {Colors.TEXT_PRIMARY}; font-size: 15px;">道氏理论 (Dow Theory)</b><br/>
技术分析的基石，核心观点：
</p>
<ul style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
<li><b style="color: {Colors.TEXT_PRIMARY};">三种趋势</b>：主要趋势、次要趋势、短期波动</li>
<li><b style="color: {Colors.TEXT_PRIMARY};">三个阶段</b>：积累期、公众参与期、派发期</li>
<li><b style="color: {Colors.TEXT_PRIMARY};">趋势延续</b>：趋势持续直到明确反转信号出现</li>
</ul>

<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8; margin-top: 16px;">
<b style="color: {Colors.TEXT_PRIMARY}; font-size: 15px;">IBD Market Pulse 参考</b>
</p>
<table border="0" cellpadding="10" style="width: 100%; margin-top: 8px;">
<tr><td style="background: #22c55e33; border-radius: 8px; border-left: 4px solid #22c55e;">
    <b style="color: #22c55e;">Confirmed Uptrend</b> - 确认上涨，建议满仓
</td></tr>
<tr><td style="background: #eab30833; border-radius: 8px; border-left: 4px solid #eab308;">
    <b style="color: #eab308;">Uptrend Under Pressure</b> - 上涨受压，建议半仓
</td></tr>
<tr><td style="background: #ef444433; border-radius: 8px; border-left: 4px solid #ef4444;">
    <b style="color: #ef4444;">Market in Correction</b> - 市场修正，建议空仓
</td></tr>
</table>
""")
        content_layout.addWidget(theory)
        
        # 多周期分析
        multiperiod = self._create_section("⏱️ 多周期共振分析", f"""
<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
市场同时存在多个时间尺度的趋势：
</p>
<ul style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
<li><b style="color: {Colors.INFO};">长期趋势</b> (25-48周) → 决定整体仓位高低</li>
<li><b style="color: {Colors.PRIMARY};">中期趋势</b> (9-24周) → 决定何时加减仓</li>
<li><b style="color: {Colors.SUCCESS};">短期趋势</b> (1-8周) → 决定具体进出场点</li>
</ul>

<table border="1" cellpadding="10" style="border-collapse: collapse; width: 100%; margin-top: 16px; border-color: {Colors.BORDER_PRIMARY};">
<tr style="background: {Colors.BG_TERTIARY};">
    <th style="color: {Colors.TEXT_PRIMARY};">共振状态</th>
    <th style="color: {Colors.TEXT_PRIMARY};">短期</th>
    <th style="color: {Colors.TEXT_PRIMARY};">中期</th>
    <th style="color: {Colors.TEXT_PRIMARY};">长期</th>
    <th style="color: {Colors.TEXT_PRIMARY};">策略</th>
</tr>
<tr style="color: #22c55e;"><td>全面上涨</td><td>↑</td><td>↑</td><td>↑</td><td>满仓进攻</td></tr>
<tr style="color: {Colors.TEXT_SECONDARY};"><td>短期回调</td><td style="color: #ef4444;">↓</td><td style="color: #22c55e;">↑</td><td style="color: #22c55e;">↑</td><td>等待企稳加仓</td></tr>
<tr style="color: #eab308;"><td>震荡盘整</td><td>→</td><td>→</td><td>→</td><td>轻仓观望</td></tr>
<tr style="color: #ef4444;"><td>全面下跌</td><td>↓</td><td>↓</td><td>↓</td><td>空仓保护</td></tr>
</table>
""")
        content_layout.addWidget(multiperiod)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        return widget
    
    # ========== Tab 2: 量化公司模型 ==========
    def _create_quant_models_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {Colors.BG_SECONDARY}; }}")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 24, 32, 24)
        content_layout.setSpacing(24)
        
        # 概述
        intro = self._create_section("🏢 头部量化公司的趋势判断工具", f"""
<p style="font-size: 15px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
全球顶级量化对冲基金使用的市场趋势判断方法和工具，为韬睿量化模型提供参考。
</p>
""")
        content_layout.addWidget(intro)
        
        # 贝莱德
        blackrock = self._create_section("🔷 贝莱德 (BlackRock) - Aladdin系统", f"""
<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
<b style="color: {Colors.TEXT_PRIMARY};">管理规模：</b>10万亿美元+ | <b style="color: {Colors.TEXT_PRIMARY};">核心系统：</b>Aladdin风险管理平台
</p>

<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8; margin-top: 12px;">
<b style="color: {Colors.TEXT_PRIMARY};">趋势判断方法：</b>
</p>
<ul style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
<li><b style="color: {Colors.PRIMARY};">宏观经济周期模型</b> - 将经济划分为扩张、顶峰、收缩、复苏四阶段</li>
<li><b style="color: {Colors.PRIMARY};">风险因子分析</b> - 分析利率、信用、股权、通胀等风险因子暴露</li>
<li><b style="color: {Colors.PRIMARY};">情绪指标</b> - 监控VIX、信用利差、资金流向等市场情绪</li>
<li><b style="color: {Colors.PRIMARY};">跨资产相关性</b> - 分析股债商品间的联动关系</li>
</ul>

<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8; margin-top: 12px;">
<b style="color: {Colors.TEXT_PRIMARY};">韬睿借鉴：</b>
使用宏观经济周期判断长期趋势方向，结合风险因子调整仓位。
</p>
""")
        content_layout.addWidget(blackrock)
        
        # 文艺复兴科技
        renaissance = self._create_section("🔶 文艺复兴科技 (Renaissance) - 大奖章基金", f"""
<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
<b style="color: {Colors.TEXT_PRIMARY};">年化收益：</b>66%（1988-2018） | <b style="color: {Colors.TEXT_PRIMARY};">策略类型：</b>纯量化短期交易
</p>

<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8; margin-top: 12px;">
<b style="color: {Colors.TEXT_PRIMARY};">趋势判断方法：</b>
</p>
<ul style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
<li><b style="color: {Colors.PRIMARY};">隐马尔可夫模型(HMM)</b> - 识别市场隐藏状态转换</li>
<li><b style="color: {Colors.PRIMARY};">模式识别</b> - 从海量历史数据中提取价格模式</li>
<li><b style="color: {Colors.PRIMARY};">统计套利</b> - 利用价格偏离均值的回归特性</li>
<li><b style="color: {Colors.PRIMARY};">机器学习</b> - 使用神经网络预测短期价格走势</li>
</ul>

<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8; margin-top: 12px;">
<b style="color: {Colors.TEXT_PRIMARY};">韬睿借鉴：</b>
使用HMM识别市场状态（牛市/熊市/震荡），辅助趋势判断。
</p>
""")
        content_layout.addWidget(renaissance)
        
        # 桥水
        bridgewater = self._create_section("🟢 桥水基金 (Bridgewater) - 全天候策略", f"""
<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
<b style="color: {Colors.TEXT_PRIMARY};">管理规模：</b>1500亿美元 | <b style="color: {Colors.TEXT_PRIMARY};">核心策略：</b>风险平价、全天候
</p>

<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8; margin-top: 12px;">
<b style="color: {Colors.TEXT_PRIMARY};">经济周期象限模型：</b>
</p>
<table border="1" cellpadding="10" style="border-collapse: collapse; width: 100%; margin-top: 8px; border-color: {Colors.BORDER_PRIMARY};">
<tr style="background: {Colors.BG_TERTIARY};">
    <th style="color: {Colors.TEXT_PRIMARY};">象限</th>
    <th style="color: {Colors.TEXT_PRIMARY};">增长</th>
    <th style="color: {Colors.TEXT_PRIMARY};">通胀</th>
    <th style="color: {Colors.TEXT_PRIMARY};">利好资产</th>
</tr>
<tr style="color: {Colors.TEXT_SECONDARY};">
    <td style="color: #22c55e;">I - 繁荣期</td><td>↑</td><td>↑</td><td>股票、商品</td>
</tr>
<tr style="color: {Colors.TEXT_SECONDARY};">
    <td style="color: #eab308;">II - 滞胀期</td><td>↓</td><td>↑</td><td>商品、通胀债券</td>
</tr>
<tr style="color: {Colors.TEXT_SECONDARY};">
    <td style="color: #ef4444;">III - 衰退期</td><td>↓</td><td>↓</td><td>国债、现金</td>
</tr>
<tr style="color: {Colors.TEXT_SECONDARY};">
    <td style="color: #0ea5e9;">IV - 复苏期</td><td>↑</td><td>↓</td><td>股票、信用债</td>
</tr>
</table>

<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8; margin-top: 12px;">
<b style="color: {Colors.TEXT_PRIMARY};">韬睿借鉴：</b>
根据经济周期象限调整股债配比和因子权重。
</p>
""")
        content_layout.addWidget(bridgewater)
        
        # 双西格玛
        twosigma = self._create_section("🔵 Two Sigma - 机器学习驱动", f"""
<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
<b style="color: {Colors.TEXT_PRIMARY};">管理规模：</b>600亿美元 | <b style="color: {Colors.TEXT_PRIMARY};">策略类型：</b>AI/ML量化
</p>

<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8; margin-top: 12px;">
<b style="color: {Colors.TEXT_PRIMARY};">趋势判断工具：</b>
</p>
<ul style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
<li><b style="color: {Colors.PRIMARY};">NLP情绪分析</b> - 分析新闻、社交媒体情绪</li>
<li><b style="color: {Colors.PRIMARY};">另类数据</b> - 卫星图像、信用卡数据等</li>
<li><b style="color: {Colors.PRIMARY};">深度学习</b> - LSTM预测时间序列趋势</li>
<li><b style="color: {Colors.PRIMARY};">强化学习</b> - 动态优化交易策略</li>
</ul>

<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8; margin-top: 12px;">
<b style="color: {Colors.TEXT_PRIMARY};">韬睿借鉴：</b>
整合舆情分析和AI预测作为趋势判断的辅助信号。
</p>
""")
        content_layout.addWidget(twosigma)
        
        # IBD实时分析按钮
        ibd_section = self._create_ibd_analysis_section()
        content_layout.addWidget(ibd_section)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        return widget
    
    def _create_ibd_analysis_section(self) -> QFrame:
        """创建IBD实时分析区域"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.MODULE_TREND_START}40;
                border-radius: 12px;
                padding: 20px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(16)
        
        # 标题
        title = QLabel("🔍 IBD风格实时分析")
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        desc = QLabel("使用IBD的跟踪日/分布日方法分析当前市场状态")
        desc.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px;")
        layout.addWidget(desc)
        
        # 按钮行
        btn_layout = QHBoxLayout()
        
        # 分析按钮
        self.ibd_btn = QPushButton("▶ 开始IBD分析")
        self.ibd_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.MODULE_TREND_START};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.MODULE_TREND_END};
            }}
        """)
        self.ibd_btn.clicked.connect(self._run_ibd_analysis)
        btn_layout.addWidget(self.ibd_btn)
        
        # 查看详情按钮
        view_btn = QPushButton("📊 查看详情")
        view_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY}20;
            }}
        """)
        view_btn.clicked.connect(self._view_ibd_full)
        btn_layout.addWidget(view_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        # 结果显示区
        self.ibd_result = QTextEdit()
        self.ibd_result.setReadOnly(True)
        self.ibd_result.setMinimumHeight(200)
        self.ibd_result.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_PRIMARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                padding: 12px;
                font-family: monospace;
                font-size: 13px;
            }}
        """)
        self.ibd_result.setPlaceholderText("点击上方按钮开始分析...")
        layout.addWidget(self.ibd_result)
        
        return frame
    
    def _run_ibd_analysis(self):
        """执行IBD分析"""
        self.ibd_btn.setEnabled(False)
        self.ibd_btn.setText("分析中...")
        self.ibd_result.setText("正在执行IBD风格分析，请稍候...")
        
        try:
            from core.ibd_style_analyzer import get_ibd_analyzer
            
            analyzer = get_ibd_analyzer()
            result = analyzer.analyze('000001.XSHG', lookback_days=60)
            
            status_text = {
                'confirmed_uptrend': '✅ 确认上涨趋势',
                'uptrend_pressure': '⚠️ 上涨趋势承压',
                'correction': '🔴 市场调整中',
                'rally_attempt': '🟡 反弹尝试中'
            }.get(result.market_status.value, result.market_status.value)
            
            output = f"""
📊 IBD风格市场分析结果
{'='*40}

📅 分析日期: {result.analysis_date}
📈 市场状态: {status_text}

📉 技术指标:
  • 分布日数量: {result.distribution_count}个（近25日）
  • 跟踪日数量: {len(result.follow_through_days)}个
  • 价格vs50日均线: {result.price_vs_50ma:+.2f}%
  • 价格vs200日均线: {result.price_vs_200ma:+.2f}%

💡 投资建议:
{result.recommendation}

📋 详细说明:
"""
            for detail in result.details:
                output += f"  • {detail}\n"
            
            self.ibd_result.setText(output)
            
            # 存储结果供查看
            self._ibd_result_data = {
                'analysis_date': result.analysis_date,
                'market_status': status_text,
                'distribution_count': result.distribution_count,
                'follow_through_days': len(result.follow_through_days),
                'price_vs_50ma': f"{result.price_vs_50ma:+.2f}%",
                'price_vs_200ma': f"{result.price_vs_200ma:+.2f}%",
                'recommendation': result.recommendation,
                'details': result.details
            }
            
        except Exception as e:
            self.ibd_result.setText(f"❌ 分析失败: {e}")
            self._ibd_result_data = None
        finally:
            self.ibd_btn.setEnabled(True)
            self.ibd_btn.setText("▶ 开始IBD分析")
    
    def _view_ibd_full(self):
        """在弹出窗口中查看IBD分析详情"""
        if not hasattr(self, '_ibd_result_data') or not self._ibd_result_data:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "提示", "请先执行IBD分析获取数据")
            return
        
        from gui.widgets.data_viewer import show_data_viewer
        show_data_viewer(
            parent=self,
            title="IBD风格市场分析详情",
            data=self.ibd_result.toPlainText()
        )
    
    # ========== Tab 3: 大V观点 ==========
    def _create_kol_views_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {Colors.BG_SECONDARY}; }}")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 24, 32, 24)
        content_layout.setSpacing(24)
        
        # 概述
        intro = self._create_section("🎤 知名投资者的趋势判断方法", f"""
<p style="font-size: 15px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
投资大师和知名分析师的趋势判断经验与方法，是韬睿量化模型的重要参考来源。
</p>
""")
        content_layout.addWidget(intro)
        
        # 威廉·欧奈尔
        oneil = self._create_section("📈 威廉·欧奈尔 (William O'Neil) - CANSLIM系统", f"""
<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
<b style="color: {Colors.TEXT_PRIMARY};">身份：</b>IBD创始人，成长股投资大师
</p>

<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8; margin-top: 12px;">
<b style="color: {Colors.TEXT_PRIMARY};">Market Pulse 趋势判断法：</b>
</p>
<ul style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
<li><b style="color: {Colors.SUCCESS};">跟踪日</b> - 大盘放量上涨2%以上，确认趋势反转</li>
<li><b style="color: {Colors.ERROR};">派发日</b> - 大盘放量下跌0.2%以上，累计4-5天触发警报</li>
<li><b style="color: {Colors.PRIMARY};">领涨股</b> - 观察龙头股表现判断市场健康度</li>
<li><b style="color: {Colors.WARNING};">宽度指标</b> - 新高股票数量与新低数量对比</li>
</ul>

<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8; margin-top: 12px;">
<b style="color: {Colors.TEXT_PRIMARY};">韬睿应用：</b>
集成跟踪日/派发日计数器，作为趋势转折信号。
</p>
""")
        content_layout.addWidget(oneil)
        
        # 斯坦·温斯坦
        weinstein = self._create_section("📊 斯坦·温斯坦 (Stan Weinstein) - 阶段分析法", f"""
<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
<b style="color: {Colors.TEXT_PRIMARY};">著作：</b>《股票买卖时机》(Secrets for Profiting in Bull and Bear Markets)
</p>

<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8; margin-top: 12px;">
<b style="color: {Colors.TEXT_PRIMARY};">四阶段模型：</b>
</p>
<table border="1" cellpadding="10" style="border-collapse: collapse; width: 100%; margin-top: 8px; border-color: {Colors.BORDER_PRIMARY};">
<tr style="background: {Colors.BG_TERTIARY};">
    <th style="color: {Colors.TEXT_PRIMARY};">阶段</th>
    <th style="color: {Colors.TEXT_PRIMARY};">特征</th>
    <th style="color: {Colors.TEXT_PRIMARY};">操作</th>
</tr>
<tr style="color: {Colors.TEXT_SECONDARY};">
    <td style="color: #eab308;">1 - 底部积累</td>
    <td>价格横盘，成交萎缩，30周均线走平</td>
    <td>观察，准备建仓</td>
</tr>
<tr style="color: {Colors.TEXT_SECONDARY};">
    <td style="color: #22c55e;">2 - 上升趋势</td>
    <td>价格突破，成交放大，30周均线上行</td>
    <td><b>买入并持有</b></td>
</tr>
<tr style="color: {Colors.TEXT_SECONDARY};">
    <td style="color: #f97316;">3 - 顶部派发</td>
    <td>价格震荡，成交异常，30周均线走平</td>
    <td>减仓，准备离场</td>
</tr>
<tr style="color: {Colors.TEXT_SECONDARY};">
    <td style="color: #ef4444;">4 - 下降趋势</td>
    <td>价格下跌，偶有反弹，30周均线下行</td>
    <td><b>空仓观望</b></td>
</tr>
</table>

<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8; margin-top: 12px;">
<b style="color: {Colors.TEXT_PRIMARY};">韬睿应用：</b>
使用30周均线判断市场所处阶段，指导仓位决策。
</p>
""")
        content_layout.addWidget(weinstein)
        
        # 马克·米内尔维尼
        minervini = self._create_section("🏆 马克·米内尔维尼 (Mark Minervini) - VCP形态", f"""
<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
<b style="color: {Colors.TEXT_PRIMARY};">成就：</b>5年复合收益率220%，美国投资冠军
</p>

<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8; margin-top: 12px;">
<b style="color: {Colors.TEXT_PRIMARY};">趋势模板(Trend Template)：</b>
</p>
<ul style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
<li>价格 > 150日均线 且 150日均线 > 200日均线</li>
<li>200日均线至少上行1个月</li>
<li>50日均线 > 150日均线 > 200日均线</li>
<li>价格在52周高点的25%范围内</li>
<li>相对强度评级 ≥ 70</li>
</ul>

<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8; margin-top: 12px;">
<b style="color: {Colors.TEXT_PRIMARY};">韬睿应用：</b>
将趋势模板作为个股筛选条件，确保选股符合上升趋势。
</p>
""")
        content_layout.addWidget(minervini)
        
        # 林奇/巴菲特风格
        value_masters = self._create_section("💎 价值投资大师的趋势观", f"""
<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
<b style="color: {Colors.TEXT_PRIMARY};">彼得·林奇：</b>"不要预测市场，专注个股研究"
</p>
<ul style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
<li>关注企业基本面而非市场趋势</li>
<li>使用PEG判断估值合理性</li>
<li>在恐慌时贪婪，在贪婪时恐惧</li>
</ul>

<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8; margin-top: 16px;">
<b style="color: {Colors.TEXT_PRIMARY};">霍华德·马克斯：</b>"钟摆理论"
</p>
<ul style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
<li>市场情绪在极度乐观与极度悲观之间摆动</li>
<li>关注信用周期判断市场位置</li>
<li>在别人恐惧时买入优质资产</li>
</ul>

<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8; margin-top: 12px;">
<b style="color: {Colors.TEXT_PRIMARY};">韬睿应用：</b>
结合情绪指标判断市场极端位置，提供逆向操作信号。
</p>
""")
        content_layout.addWidget(value_masters)
        
        # 情绪分析功能区
        sentiment_section = self._create_sentiment_analysis_section()
        content_layout.addWidget(sentiment_section)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        return widget
    
    def _create_sentiment_analysis_section(self) -> QFrame:
        """创建情绪分析区域"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.MODULE_TREND_START}40;
                border-radius: 12px;
                padding: 20px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(16)
        
        # 标题
        title = QLabel("😊 市场情绪实时分析")
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        desc = QLabel("分析市场情绪指数、恐惧贪婪指数、大V观点等综合情绪信号")
        desc.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px;")
        layout.addWidget(desc)
        
        # 按钮行
        btn_layout = QHBoxLayout()
        
        # 分析按钮
        self.sentiment_btn = QPushButton("▶ 开始情绪分析")
        self.sentiment_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.MODULE_TREND_START};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.MODULE_TREND_END};
            }}
        """)
        self.sentiment_btn.clicked.connect(self._run_sentiment_analysis)
        btn_layout.addWidget(self.sentiment_btn)
        
        # 查看详情按钮
        view_btn = QPushButton("📊 查看详情")
        view_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY}20;
            }}
        """)
        view_btn.clicked.connect(self._view_sentiment_full)
        btn_layout.addWidget(view_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        # 结果显示区
        self.sentiment_result = QTextEdit()
        self.sentiment_result.setReadOnly(True)
        self.sentiment_result.setMinimumHeight(200)
        self.sentiment_result.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_PRIMARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                padding: 12px;
                font-family: monospace;
                font-size: 13px;
            }}
        """)
        self.sentiment_result.setPlaceholderText("点击上方按钮开始分析...")
        layout.addWidget(self.sentiment_result)
        
        return frame
    
    def _run_sentiment_analysis(self):
        """执行情绪分析"""
        self.sentiment_btn.setEnabled(False)
        self.sentiment_btn.setText("分析中...")
        self.sentiment_result.setText("正在执行情绪分析，请稍候...")
        
        try:
            from core.sentiment_analyzer import get_sentiment_analyzer
            
            analyzer = get_sentiment_analyzer()
            result = analyzer.analyze()
            
            sentiment_text = {
                'very_bullish': '📈 极度乐观',
                'bullish': '🟢 乐观',
                'neutral': '🟡 中性',
                'bearish': '🔴 悲观',
                'very_bearish': '📉 极度悲观'
            }.get(result.overall_sentiment.value, result.overall_sentiment.value)
            
            fg_color = '🟢' if result.fear_greed_index > 60 else '🔴' if result.fear_greed_index < 40 else '🟡'
            
            output = f"""
😊 市场情绪分析结果
{'='*40}

📅 分析日期: {result.analysis_date}
🎯 整体情绪: {sentiment_text}
📊 情绪评分: {result.overall_score:.1f}/100

🌡️ 恐惧贪婪指数: {fg_color} {result.fear_greed_index:.0f}
  • 0-20: 极度恐惧（逆向买入信号）
  • 20-40: 恐惧
  • 40-60: 中性
  • 60-80: 贪婪
  • 80-100: 极度贪婪（逆向卖出信号）

📈 看多/看空比例:
  • 看多: {result.bullish_ratio:.0%}
  • 看空: {(1 - result.bullish_ratio):.0%}

📝 摘要:
{result.summary}

💡 投资建议:
"""
            for rec in result.recommendations:
                output += f"  • {rec}\n"
            
            self.sentiment_result.setText(output)
            
        except Exception as e:
            self.sentiment_result.setText(f"❌ 分析失败: {e}")
        finally:
            self.sentiment_btn.setEnabled(True)
            self.sentiment_btn.setText("▶ 开始情绪分析")
    
    def _view_sentiment_full(self):
        """在弹出窗口中查看情绪分析详情"""
        text = self.sentiment_result.toPlainText()
        if not text or "点击" in text:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "提示", "请先执行情绪分析获取数据")
            return
        
        from gui.widgets.data_viewer import show_data_viewer
        show_data_viewer(
            parent=self,
            title="市场情绪分析详情",
            data=text
        )
    
    # ========== Tab 4: 趋势分析 ==========
    def _create_analysis_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {Colors.BG_SECONDARY}; }}")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 24, 32, 24)
        content_layout.setSpacing(20)
        
        # 操作区
        action_frame = self._create_action_section()
        content_layout.addWidget(action_frame)
        
        # 状态
        self.status_frame = QFrame()
        self.status_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 10px;
            }}
        """)
        status_layout = QHBoxLayout(self.status_frame)
        status_layout.setContentsMargins(16, 8, 16, 8)
        
        self.progress_label = QLabel("等待分析...")
        self.progress_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px;")
        status_layout.addWidget(self.progress_label)
        status_layout.addStretch()
        
        self.time_label = QLabel("")
        self.time_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        status_layout.addWidget(self.time_label)
        
        content_layout.addWidget(self.status_frame)
        
        # 仪表盘
        gauge_frame = self._create_gauge_section()
        content_layout.addWidget(gauge_frame)
        
        # 市场阶段和建议
        advice_frame = self._create_advice_section()
        content_layout.addWidget(advice_frame)
        
        # 多周期共振分析
        resonance_frame = self._create_resonance_section()
        content_layout.addWidget(resonance_frame)
        
        # 宏观经济分析
        macro_frame = self._create_macro_analysis_section()
        content_layout.addWidget(macro_frame)
        
        # 8指标详情
        indicators_frame = self._create_indicators_detail_section()
        content_layout.addWidget(indicators_frame)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        return widget
    
    def _create_resonance_section(self) -> QFrame:
        """创建多周期共振分析区域"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # 标题
        title_layout = QHBoxLayout()
        title = QLabel("🔗 多周期共振分析")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        title_layout.addWidget(title)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # 共振信息网格
        grid = QGridLayout()
        grid.setSpacing(16)
        
        # 共振强度
        strength_card = self._create_resonance_card("共振强度", "resonance_strength")
        grid.addWidget(strength_card, 0, 0)
        
        # 趋势加速
        accel_card = self._create_resonance_card("趋势动能", "acceleration")
        grid.addWidget(accel_card, 0, 1)
        
        # 方向一致性
        dir_card = self._create_resonance_card("方向一致", "direction")
        grid.addWidget(dir_card, 0, 2)
        
        # 策略建议
        strategy_card = self._create_resonance_card("共振策略", "strategy")
        grid.addWidget(strategy_card, 0, 3)
        
        layout.addLayout(grid)
        
        # 共振表格
        self.resonance_table = QTableWidget()
        self.resonance_table.setColumnCount(4)
        self.resonance_table.setRowCount(3)
        self.resonance_table.setHorizontalHeaderLabels(["周期", "趋势方向", "得分", "状态"])
        self.resonance_table.verticalHeader().setVisible(False)
        self.resonance_table.setMaximumHeight(120)
        self.resonance_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.resonance_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_DARK};
                border-radius: 8px;
                gridline-color: {Colors.BORDER_DARK};
            }}
            QTableWidget::item {{
                padding: 8px;
                color: {Colors.TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_SECONDARY};
                padding: 8px;
                border: none;
                font-weight: 600;
            }}
        """)
        
        # 初始化表格
        for i, period in enumerate(["短期(1-8周)", "中期(9-24周)", "长期(25-48周)"]):
            self.resonance_table.setItem(i, 0, QTableWidgetItem(period))
            self.resonance_table.setItem(i, 1, QTableWidgetItem("--"))
            self.resonance_table.setItem(i, 2, QTableWidgetItem("--"))
            self.resonance_table.setItem(i, 3, QTableWidgetItem("--"))
        
        layout.addWidget(self.resonance_table)
        
        return frame
    
    def _create_macro_analysis_section(self) -> QFrame:
        """创建宏观经济分析区域"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.MODULE_TREND_START}40;
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # 标题
        title_layout = QHBoxLayout()
        title = QLabel("🌐 宏观经济环境分析")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        # 分析按钮
        self.macro_btn = QPushButton("▶ 获取宏观数据")
        self.macro_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.MODULE_TREND_START};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.MODULE_TREND_END};
            }}
        """)
        self.macro_btn.clicked.connect(self._run_macro_analysis)
        title_layout.addWidget(self.macro_btn)
        layout.addLayout(title_layout)
        
        # 结果表格
        self.macro_table = QTableWidget(7, 4)
        self.macro_table.setHorizontalHeaderLabels(["指标", "当前值", "趋势", "信号"])
        self.macro_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.macro_table.verticalHeader().setVisible(False)
        self.macro_table.setMinimumHeight(220)
        self.macro_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                gridline-color: {Colors.BORDER_PRIMARY};
            }}
            QTableWidget::item {{
                padding: 8px;
                color: {Colors.TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_SECONDARY};
                padding: 8px;
                border: none;
                font-weight: 600;
            }}
        """)
        
        # 初始化表格
        indicators = ["GDP增速", "CPI", "PPI", "PMI", "M2增速", "利率", "汇率"]
        for i, name in enumerate(indicators):
            self.macro_table.setItem(i, 0, QTableWidgetItem(name))
            self.macro_table.setItem(i, 1, QTableWidgetItem("--"))
            self.macro_table.setItem(i, 2, QTableWidgetItem("--"))
            self.macro_table.setItem(i, 3, QTableWidgetItem("--"))
        
        layout.addWidget(self.macro_table)
        
        # 综合评价
        self.macro_summary = QLabel('点击"获取宏观数据"按钮获取最新宏观经济分析')
        self.macro_summary.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY}; 
            font-size: 13px;
            padding: 12px;
            background-color: {Colors.BG_PRIMARY};
            border-radius: 8px;
        """)
        self.macro_summary.setWordWrap(True)
        layout.addWidget(self.macro_summary)
        
        return frame
    
    def _run_macro_analysis(self):
        """执行宏观经济分析"""
        self.macro_btn.setEnabled(False)
        self.macro_btn.setText("分析中...")
        
        try:
            from core.macro_analyzer import get_macro_analyzer
            
            analyzer = get_macro_analyzer()
            result = analyzer.analyze()
            
            # 更新表格
            indicators = [
                ('gdp', 'GDP增速'),
                ('cpi', 'CPI'),
                ('ppi', 'PPI'),
                ('pmi', 'PMI'),
                ('m2', 'M2增速'),
                ('interest_rate', '利率'),
                ('exchange_rate', '汇率')
            ]
            
            for i, (key, name) in enumerate(indicators):
                indicator = getattr(result, key, None)
                if indicator:
                    value_item = QTableWidgetItem(f"{indicator.value:.2f}")
                    trend_text = {'up': '↑上升', 'down': '↓下降', 'stable': '→稳定'}.get(indicator.trend.value, '--')
                    trend_item = QTableWidgetItem(trend_text)
                    
                    signal_text = {
                        'very_bullish': '📈强看多',
                        'bullish': '🟢看多',
                        'neutral': '🟡中性',
                        'bearish': '🔴看空',
                        'very_bearish': '📉强看空'
                    }.get(indicator.signal.value, '--')
                    signal_item = QTableWidgetItem(signal_text)
                    
                    self.macro_table.setItem(i, 1, value_item)
                    self.macro_table.setItem(i, 2, trend_item)
                    self.macro_table.setItem(i, 3, signal_item)
            
            # 更新综合评价
            signal_text = {
                'very_bullish': '📈 强势看多',
                'bullish': '🟢 偏多',
                'neutral': '🟡 中性',
                'bearish': '🔴 偏空',
                'very_bearish': '📉 强势看空'
            }.get(result.overall_signal.value, result.overall_signal.value)
            
            summary = f"""
📊 宏观经济综合评价 ({result.analysis_date})

🎯 整体信号: {signal_text}  |  📊 综合得分: {result.overall_score:.1f}/100

📝 {result.summary}

💡 建议: {'; '.join(result.recommendations[:2]) if result.recommendations else '暂无'}
"""
            self.macro_summary.setText(summary.strip())
            
        except Exception as e:
            self.macro_summary.setText(f"❌ 分析失败: {e}")
        finally:
            self.macro_btn.setEnabled(True)
            self.macro_btn.setText("▶ 获取宏观数据")
    
    def _create_resonance_card(self, title: str, key: str) -> QFrame:
        """创建共振信息卡片"""
        card = QFrame()
        card.setObjectName(f"resonance_{key}")
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_DARK};
                border-radius: 10px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(title_label)
        
        value_label = QLabel("--")
        value_label.setObjectName("value")
        value_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(value_label)
        
        return card
    
    def _update_resonance_display(self, result: dict):
        """更新共振分析显示"""
        resonance = result.get("resonance", {})
        
        # 更新共振卡片
        # 共振强度
        strength = resonance.get("resonance_strength", 0)
        strength_card = self.findChild(QFrame, "resonance_resonance_strength")
        if strength_card:
            value_label = strength_card.findChild(QLabel, "value")
            if value_label:
                value_label.setText(f"{strength:.0f}%")
                if strength > 70:
                    value_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {Colors.SUCCESS};")
                elif strength > 40:
                    value_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {Colors.WARNING};")
                else:
                    value_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {Colors.TEXT_MUTED};")
        
        # 趋势加速
        accel = resonance.get("acceleration", "--")
        accel_card = self.findChild(QFrame, "resonance_acceleration")
        if accel_card:
            value_label = accel_card.findChild(QLabel, "value")
            if value_label:
                value_label.setText(accel)
        
        # 方向一致
        consistency = resonance.get("direction_consistency", 0)
        dir_card = self.findChild(QFrame, "resonance_direction")
        if dir_card:
            value_label = dir_card.findChild(QLabel, "value")
            if value_label:
                if consistency > 0.8:
                    value_label.setText("高度一致")
                    value_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {Colors.SUCCESS};")
                elif consistency > 0.5:
                    value_label.setText("部分一致")
                    value_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {Colors.WARNING};")
                else:
                    value_label.setText("方向分化")
                    value_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {Colors.TEXT_MUTED};")
        
        # 策略建议
        strategy_card = self.findChild(QFrame, "resonance_strategy")
        if strategy_card:
            value_label = strategy_card.findChild(QLabel, "value")
            if value_label:
                if resonance.get("all_bullish"):
                    value_label.setText("积极做多")
                    value_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {Colors.SUCCESS};")
                elif resonance.get("all_bearish"):
                    value_label.setText("防御观望")
                    value_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {Colors.ERROR};")
                else:
                    value_label.setText("灵活应对")
                    value_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {Colors.WARNING};")
        
        # 更新共振表格
        scores = resonance.get("scores", {})
        term_data = [
            ("short_term", "短期", scores.get("short", 0)),
            ("medium_term", "中期", scores.get("medium", 0)),
            ("long_term", "长期", scores.get("long", 0))
        ]
        
        for i, (key, name, score) in enumerate(term_data):
            data = result.get(key, {})
            direction = data.get("direction", "--")
            
            self.resonance_table.setItem(i, 1, QTableWidgetItem(direction))
            
            score_item = QTableWidgetItem(f"{score:+.0f}")
            if score > 20:
                score_item.setForeground(QColor(Colors.SUCCESS))
            elif score < -20:
                score_item.setForeground(QColor(Colors.ERROR))
            else:
                score_item.setForeground(QColor(Colors.WARNING))
            self.resonance_table.setItem(i, 2, score_item)
            
            if score > 30:
                status = "✅ 强势"
            elif score > 0:
                status = "📈 偏强"
            elif score > -30:
                status = "📉 偏弱"
            else:
                status = "❌ 弱势"
            self.resonance_table.setItem(i, 3, QTableWidgetItem(status))
    
    def _create_indicators_detail_section(self) -> QFrame:
        """创建8指标详情展示区域"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # 标题
        title_layout = QHBoxLayout()
        title = QLabel("📊 8指标体系详情")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        hint = QLabel("综合MA/MACD/RSI/布林带/成交量/KDJ/ADX/资金流")
        hint.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        title_layout.addWidget(hint)
        layout.addLayout(title_layout)
        
        # 指标网格
        grid = QGridLayout()
        grid.setSpacing(12)
        
        # 创建8个指标卡片
        self.indicator_cards = {}
        indicators_info = [
            ("ma", "📈 均线系统", "MA", "20%"),
            ("macd", "📉 MACD动能", "MACD", "18%"),
            ("rsi", "💪 RSI强弱", "RSI", "10%"),
            ("bb", "📊 布林带", "BB", "10%"),
            ("vol", "📦 成交量", "VOL", "12%"),
            ("kdj", "🔄 KDJ随机", "KDJ", "10%"),
            ("adx", "💥 ADX趋势", "ADX", "10%"),
            ("flow", "💰 资金流", "FLOW", "10%"),
        ]
        
        for i, (key, name, abbr, weight) in enumerate(indicators_info):
            row, col = divmod(i, 4)
            card = self._create_indicator_card(name, abbr, weight)
            self.indicator_cards[key] = card
            grid.addWidget(card, row, col)
        
        layout.addLayout(grid)
        
        return frame
    
    def _create_indicator_card(self, name: str, abbr: str, weight: str) -> QFrame:
        """创建单个指标卡片"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_DARK};
                border-radius: 10px;
            }}
        """)
        card.setMinimumHeight(80)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        
        # 标题行
        title_layout = QHBoxLayout()
        title = QLabel(name)
        title.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        title_layout.addWidget(title)
        
        weight_label = QLabel(weight)
        weight_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10px;")
        title_layout.addWidget(weight_label)
        layout.addLayout(title_layout)
        
        # 分数
        score_label = QLabel("--")
        score_label.setObjectName("score")
        score_label.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(score_label)
        
        # 状态
        status_label = QLabel("等待分析")
        status_label.setObjectName("status")
        status_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10px;")
        layout.addWidget(status_label)
        
        return card
    
    def _update_indicator_cards(self, result: dict):
        """更新指标卡片显示"""
        # 使用中期趋势的指标作为主要显示
        medium_data = result.get("medium_term", {})
        indicators = medium_data.get("indicators", {})
        
        if not indicators:
            return
        
        # 更新各卡片
        self._update_card("ma", indicators)
        self._update_card("macd", indicators)
        self._update_card("rsi", indicators)
        self._update_card("bb", indicators)
        self._update_card("vol", indicators)
        self._update_card("kdj", indicators)
        self._update_card("adx", indicators)
        self._update_card("flow", indicators)
    
    def _update_card(self, key: str, indicators: dict):
        """更新单个卡片"""
        if key not in self.indicator_cards:
            return
        
        card = self.indicator_cards[key]
        score_label = card.findChild(QLabel, "score")
        status_label = card.findChild(QLabel, "status")
        
        if not score_label or not status_label:
            return
        
        # 根据指标类型提取数据
        if key == "ma":
            value = indicators.get("price_vs_ma_fast", 0)
            score_label.setText(f"{value:+.1f}%")
            status_label.setText("高于均线" if value > 0 else "低于均线")
        elif key == "macd":
            value = indicators.get("macd_histogram", 0)
            score_label.setText("正" if value > 0 else "负")
            status_label.setText(f"柱值: {value:.2f}")
        elif key == "rsi":
            value = indicators.get("rsi", 50)
            score_label.setText(f"{value:.0f}")
            if value > 70:
                status_label.setText("超买区")
            elif value < 30:
                status_label.setText("超卖区")
            else:
                status_label.setText("正常区间")
        elif key == "bb":
            value = indicators.get("bb_position", 50)
            score_label.setText(f"{value:.0f}%")
            status_label.setText("上轨附近" if value > 70 else ("下轨附近" if value < 30 else "中轨"))
        elif key == "vol":
            ratio = indicators.get("volume_ratio", 1)
            score_label.setText(f"{ratio:.1f}x")
            status_label.setText("放量" if ratio > 1.5 else ("缩量" if ratio < 0.7 else "正常"))
        elif key == "kdj":
            k = indicators.get("kdj_k", 50)
            score_label.setText(f"K={k:.0f}")
            if indicators.get("kdj_golden_cross"):
                status_label.setText("🔼 金叉")
            elif indicators.get("kdj_death_cross"):
                status_label.setText("🔽 死叉")
            else:
                status_label.setText("D=" + str(int(indicators.get("kdj_d", 50))))
        elif key == "adx":
            adx = indicators.get("adx", 20)
            score_label.setText(f"{adx:.0f}")
            status_label.setText(indicators.get("adx_trend", "") + indicators.get("adx_direction", ""))
        elif key == "flow":
            mfi = indicators.get("mfi", 50)
            score_label.setText(f"{mfi:.0f}")
            status_label.setText(indicators.get("flow_trend", ""))
    
    def _create_action_section(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 12px;
            }}
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)
        
        index_label = QLabel("分析指数:")
        index_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px;")
        layout.addWidget(index_label)
        
        self.index_combo = QComboBox()
        self.index_combo.addItems([
            "上证指数 (000001.XSHG)",
            "深证成指 (399001.XSHE)",
            "沪深300 (000300.XSHG)",
            "创业板指 (399006.XSHE)",
            "中证500 (000905.XSHG)"
        ])
        self.index_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                padding: 10px 16px;
                color: {Colors.TEXT_PRIMARY};
                min-width: 220px;
                font-size: 13px;
            }}
            QComboBox::drop-down {{ border: none; width: 30px; }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_CARD};
                color: {Colors.TEXT_PRIMARY};
                selection-background-color: {Colors.MODULE_TREND_START};
            }}
        """)
        layout.addWidget(self.index_combo)
        
        layout.addSpacing(20)
        
        self.analyze_btn = QPushButton("🔍 开始趋势分析")
        self.analyze_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.MODULE_TREND_START}, stop:1 {Colors.MODULE_TREND_END});
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: 600;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.MODULE_TREND_END}, stop:1 {Colors.MODULE_TREND_START});
            }}
        """)
        self.analyze_btn.setMinimumWidth(180)
        self.analyze_btn.clicked.connect(self._start_analysis)
        layout.addWidget(self.analyze_btn)
        
        layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.setStyleSheet(ButtonStyles.SECONDARY)
        self.refresh_btn.clicked.connect(self._start_analysis)
        layout.addWidget(self.refresh_btn)
        
        return frame
    
    def _create_gauge_section(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        title_layout = QHBoxLayout()
        title = QLabel("📊 趋势仪表盘")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        title_layout.addWidget(title)
        title_layout.addStretch()
        hint = QLabel("点击仪表盘查看详细分析")
        hint.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        title_layout.addWidget(hint)
        layout.addLayout(title_layout)
        
        gauge_layout = QHBoxLayout()
        gauge_layout.setSpacing(24)
        
        self.short_gauge = AdvancedTrendGauge("短期趋势 (1-8周)", "short")
        self.short_gauge.clicked.connect(self._on_gauge_clicked)
        self.medium_gauge = AdvancedTrendGauge("中期趋势 (9-24周)", "medium")
        self.medium_gauge.clicked.connect(self._on_gauge_clicked)
        self.long_gauge = AdvancedTrendGauge("长期趋势 (25-48周)", "long")
        self.long_gauge.clicked.connect(self._on_gauge_clicked)
        
        gauge_layout.addStretch()
        gauge_layout.addWidget(self.short_gauge)
        gauge_layout.addWidget(self.medium_gauge)
        gauge_layout.addWidget(self.long_gauge)
        gauge_layout.addStretch()
        
        layout.addLayout(gauge_layout)
        
        return frame
    
    def _create_advice_section(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # 市场阶段
        phase_layout = QHBoxLayout()
        
        phase_info = QVBoxLayout()
        phase_title = QLabel("🎯 市场阶段判断")
        phase_title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        phase_info.addWidget(phase_title)
        
        self.phase_label = QLabel("等待分析...")
        self.phase_label.setStyleSheet(f"""
            font-size: 28px;
            font-weight: 800;
            color: {Colors.WARNING};
            padding: 16px 24px;
            background-color: {Colors.BG_SECONDARY};
            border-radius: 12px;
            border-left: 4px solid {Colors.WARNING};
        """)
        phase_info.addWidget(self.phase_label)
        phase_layout.addLayout(phase_info, 2)
        
        score_info = QVBoxLayout()
        score_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_title = QLabel("综合得分")
        score_title.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_SECONDARY};")
        score_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_info.addWidget(score_title)
        
        self.composite_score = QLabel("--")
        self.composite_score.setStyleSheet(f"font-size: 48px; font-weight: 800; color: {Colors.TEXT_PRIMARY};")
        self.composite_score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_info.addWidget(self.composite_score)
        phase_layout.addLayout(score_info, 1)
        
        layout.addLayout(phase_layout)
        
        # 分隔线
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {Colors.BORDER_PRIMARY};")
        layout.addWidget(divider)
        
        # 策略建议
        advice_layout = QGridLayout()
        advice_layout.setSpacing(16)
        
        for i, (icon, title, attr) in enumerate([
            ("💰", "建议仓位", "position_label"),
            ("🎯", "策略方向", "strategy_label"),
            ("📊", "推荐因子", "factors_label"),
        ]):
            f = QFrame()
            f.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.BG_SECONDARY};
                    border: 1px solid {Colors.BORDER_DARK};
                    border-radius: 10px;
                }}
            """)
            fl = QVBoxLayout(f)
            fl.setContentsMargins(16, 12, 16, 12)
            fl.setSpacing(6)
            
            t = QLabel(f"{icon} {title}")
            t.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
            fl.addWidget(t)
            
            v = QLabel("--")
            v.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 14px; font-weight: 500;")
            if attr == "factors_label":
                v.setWordWrap(True)
            fl.addWidget(v)
            
            setattr(self, attr, v)
            advice_layout.addWidget(f, 0, i)
        
        layout.addLayout(advice_layout)
        
        # 因子联动详情区域
        linkage_frame = QFrame()
        linkage_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 12px;
            }}
        """)
        linkage_layout = QVBoxLayout(linkage_frame)
        linkage_layout.setContentsMargins(16, 12, 16, 12)
        linkage_layout.setSpacing(10)
        
        # 标题行
        title_row = QHBoxLayout()
        linkage_title = QLabel("🔗 趋势-因子联动")
        linkage_title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 14px; font-weight: bold;")
        title_row.addWidget(linkage_title)
        title_row.addStretch()
        
        self.linkage_btn = QPushButton("📊 查看联动详情")
        self.linkage_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.MODULE_TREND_START};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {Colors.MODULE_TREND_END};
            }}
            QPushButton:disabled {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_MUTED};
            }}
        """)
        self.linkage_btn.clicked.connect(self._show_factor_linkage_details)
        title_row.addWidget(self.linkage_btn)
        linkage_layout.addLayout(title_row)
        
        # 当前状态标签
        self.linkage_status = QLabel("请先进行趋势分析")
        self.linkage_status.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        linkage_layout.addWidget(self.linkage_status)
        
        # 因子权重详情（默认隐藏）
        self.linkage_details = QFrame()
        self.linkage_details.setVisible(False)
        details_layout = QVBoxLayout(self.linkage_details)
        details_layout.setContentsMargins(0, 8, 0, 0)
        details_layout.setSpacing(8)
        
        # 市场状态
        regime_row = QHBoxLayout()
        regime_row.addWidget(QLabel("市场状态:"))
        self.regime_label = QLabel("--")
        self.regime_label.setStyleSheet(f"color: {Colors.PRIMARY}; font-weight: bold;")
        regime_row.addWidget(self.regime_label)
        regime_row.addStretch()
        details_layout.addLayout(regime_row)
        
        # 推荐因子表格
        self.linkage_table = QTableWidget()
        self.linkage_table.setColumnCount(3)
        self.linkage_table.setHorizontalHeaderLabels(["因子类别", "权重", "建议"])
        self.linkage_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.linkage_table.setMaximumHeight(200)
        self.linkage_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_DARK};
                border-radius: 6px;
                color: {Colors.TEXT_PRIMARY};
                font-size: 12px;
            }}
            QHeaderView::section {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_SECONDARY};
                padding: 6px;
                border: none;
                font-weight: bold;
            }}
        """)
        details_layout.addWidget(self.linkage_table)
        
        # 避免因子
        avoid_row = QHBoxLayout()
        avoid_row.addWidget(QLabel("⚠️ 避免因子:"))
        self.avoid_label = QLabel("--")
        self.avoid_label.setStyleSheet(f"color: {Colors.ERROR}; font-size: 12px;")
        self.avoid_label.setWordWrap(True)
        avoid_row.addWidget(self.avoid_label, 1)
        details_layout.addLayout(avoid_row)
        
        linkage_layout.addWidget(self.linkage_details)
        layout.addWidget(linkage_frame)
        
        return frame
    
    # ========== Tab 5: 技术指标 ==========
    def _create_indicators_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {Colors.BG_SECONDARY}; }}")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 24, 32, 24)
        content_layout.setSpacing(20)
        
        # 各指标详解
        for title, weight, formula, rules in [
            ("📊 移动平均线系统", "30%", 
             "SMA(n) = (P₁ + P₂ + ... + Pₙ) / n\nEMA(t) = α × P(t) + (1-α) × EMA(t-1)",
             ["价格 > 快速均线：+25分", "价格 > 慢速均线：+25分", "多头排列：+30分", "均线斜率：±20分"]),
            ("📈 MACD指标", "25%",
             "DIF = EMA(12) - EMA(26)\nDEA = EMA(DIF, 9)\nMACD柱 = DIF - DEA",
             ["柱状图 > 0：+30分", "柱状图趋势向上：+20分", "金叉（DIF > DEA）：+25分", "零轴上方：+25分"]),
            ("💪 RSI指标", "15%",
             "RS = 平均涨幅 / 平均跌幅\nRSI = 100 - (100 / (1 + RS))",
             ["RSI > 70（超买）：-20分", "RSI 50-70：+30分", "RSI 30-50：-30分", "RSI < 30（超卖）：+20分"]),
        ]:
            section = self._create_section(f"{title} (权重: {weight})", f"""
<div style="background: {Colors.BG_SECONDARY}; padding: 12px 16px; border-radius: 8px; margin: 8px 0;">
<code style="color: {Colors.MODULE_TREND_START}; font-family: monospace; font-size: 13px;">
{formula}
</code>
</div>

<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8; margin-top: 12px;">
<b style="color: {Colors.TEXT_PRIMARY};">评分规则：</b>
</p>
<ul style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
{"".join(f"<li>{r}</li>" for r in rules)}
</ul>
""")
            content_layout.addWidget(section)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        return widget
    
    # ========== Tab 6: 策略联动 ==========
    def _create_strategy_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {Colors.BG_SECONDARY}; }}")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 24, 32, 24)
        content_layout.setSpacing(20)
        
        position = self._create_section("🔄 模块在工作流中的定位", f"""
<div style="background: {Colors.BG_SECONDARY}; padding: 16px 20px; border-radius: 10px; margin: 8px 0; text-align: center;">
<span style="color: {Colors.TEXT_SECONDARY};">信息获取 → </span>
<span style="color: {Colors.MODULE_TREND_START}; font-weight: bold;">📈 市场趋势</span>
<span style="color: {Colors.TEXT_SECONDARY};"> → 投资主线 → 候选池 → 因子构建 → 策略开发</span>
</div>

<p style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8; margin-top: 16px;">
<b style="color: {Colors.TEXT_PRIMARY};">趋势模块的核心价值：</b>
</p>
<ul style="font-size: 14px; color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
<li>为后续模块提供<b style="color: {Colors.MODULE_TREND_START};">市场环境判断</b></li>
<li>指导<b style="color: {Colors.MODULE_TREND_START};">仓位管理</b></li>
<li>影响<b style="color: {Colors.MODULE_TREND_START};">因子权重</b></li>
<li>决定<b style="color: {Colors.MODULE_TREND_START};">策略类型</b></li>
</ul>
""")
        content_layout.addWidget(position)
        
        factor_linkage = self._create_section("📊 动态因子权重联动", f"""
<table border="1" cellpadding="10" style="border-collapse: collapse; width: 100%; border-color: {Colors.BORDER_PRIMARY};">
<tr style="background: {Colors.BG_TERTIARY};">
    <th style="color: {Colors.TEXT_PRIMARY};">市场阶段</th>
    <th style="color: {Colors.TEXT_PRIMARY};">优势因子</th>
    <th style="color: {Colors.TEXT_PRIMARY};">权重调整</th>
</tr>
<tr style="color: #22c55e;"><td>牛市确认</td><td>动量、成长、资金流</td><td>动量↑35%, 成长↑30%</td></tr>
<tr style="color: #84cc16;"><td>牛市调整</td><td>质量、低波动</td><td>质量↑25%, 动量↓</td></tr>
<tr style="color: #eab308;"><td>震荡盘整</td><td>价值、质量</td><td>均衡配置</td></tr>
<tr style="color: #ef4444;"><td>熊市确认</td><td>现金、逆向</td><td>降低风险暴露</td></tr>
</table>
""")
        content_layout.addWidget(factor_linkage)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        return widget
    
    # ========== 辅助方法 ==========
    def _create_module_banner(self) -> QFrame:
        """创建模块Banner（与其他模块保持一致的渐变透明风格）"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0F3D3E,
                    stop:1 #1A5C5E
                );
                border-radius: 16px;
                border: 1px solid {Colors.MODULE_TREND_START}40;
            }}
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(32, 28, 32, 28)
        
        # 左侧文字
        text_layout = QVBoxLayout()
        text_layout.setSpacing(12)
        
        title = QLabel("📈 市场趋势识别")
        title.setStyleSheet(f"""
            font-size: 24px;
            font-weight: 800;
            color: {Colors.TEXT_PRIMARY};
        """)
        text_layout.addWidget(title)
        
        subtitle = QLabel(
            "综合技术分析 · 量化公司模型 · 大V观点 → 构建韬睿独有趋势判断系统\n"
            "多周期趋势识别，为策略开发提供市场环境判断依据"
        )
        subtitle.setStyleSheet(f"""
            font-size: 13px;
            color: {Colors.TEXT_MUTED};
            line-height: 1.6;
        """)
        subtitle.setWordWrap(True)
        text_layout.addWidget(subtitle)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        
        return frame
    
    def _create_section(self, title: str, content: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title_label)
        
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setTextFormat(Qt.TextFormat.RichText)
        content_label.setStyleSheet(f"font-size: 13px;")
        content_label.setOpenExternalLinks(True)
        layout.addWidget(content_label)
        
        return frame
    
    # ========== 新增Tab: 资金流向 ==========
    def _create_capital_flow_tab(self) -> QWidget:
        """资金流向Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {Colors.BG_SECONDARY}; }}")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 16, 24, 24)
        content_layout.setSpacing(20)
        
        # 标题
        title = QLabel("💰 资金流向分析")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        content_layout.addWidget(title)
        
        desc = QLabel("实时监控北向资金、两融余额等资金面数据，辅助判断市场趋势")
        desc.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_MUTED};")
        content_layout.addWidget(desc)
        
        # 操作区
        action_frame = QFrame()
        action_frame.setStyleSheet(f"background-color: {Colors.BG_TERTIARY}; border-radius: 12px;")
        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(16, 12, 16, 12)
        
        self.capital_refresh_btn = QPushButton("🔄 获取最新数据")
        self.capital_refresh_btn.setStyleSheet(ButtonStyles.PRIMARY)
        self.capital_refresh_btn.clicked.connect(self._refresh_capital_flow)
        action_layout.addWidget(self.capital_refresh_btn)
        
        self.capital_status_label = QLabel("")
        self.capital_status_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        action_layout.addWidget(self.capital_status_label)
        action_layout.addStretch()
        
        content_layout.addWidget(action_frame)
        
        # 北向资金卡片
        nb_frame = self._create_section("📈 北向资金", "")
        nb_layout = nb_frame.layout()
        
        self.nb_grid = QGridLayout()
        self.nb_grid.setSpacing(16)
        
        # 创建北向资金显示卡片
        self.nb_labels = {}
        card_configs = [
            ("today_net", "今日净流入", "亿元"),
            ("5d_net", "5日净流入", "亿元"),
            ("sh_net", "沪股通", "亿元"),
            ("sz_net", "深股通", "亿元"),
        ]
        
        for i, (key, label, unit) in enumerate(card_configs):
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.BG_SECONDARY};
                    border: 1px solid {Colors.BORDER_PRIMARY};
                    border-radius: 8px;
                    padding: 12px;
                }}
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 12, 12, 12)
            
            label_w = QLabel(label)
            label_w.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_MUTED};")
            card_layout.addWidget(label_w)
            
            value_label = QLabel("--")
            value_label.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
            card_layout.addWidget(value_label)
            
            unit_label = QLabel(unit)
            unit_label.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED};")
            card_layout.addWidget(unit_label)
            
            self.nb_labels[key] = value_label
            self.nb_grid.addWidget(card, i // 2, i % 2)
        
        nb_layout.addLayout(self.nb_grid)
        content_layout.addWidget(nb_frame)
        
        # 两融余额
        margin_frame = self._create_section("📊 两融数据", "")
        margin_layout = margin_frame.layout()
        
        self.margin_labels = {}
        margin_configs = [
            ("balance", "融资余额", "亿元"),
            ("change", "今日变化", "亿元"),
        ]
        
        margin_grid = QHBoxLayout()
        margin_grid.setSpacing(16)
        
        for key, label, unit in margin_configs:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.BG_SECONDARY};
                    border: 1px solid {Colors.BORDER_PRIMARY};
                    border-radius: 8px;
                    padding: 12px;
                }}
            """)
            card_layout = QVBoxLayout(card)
            
            label_w = QLabel(label)
            label_w.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_MUTED};")
            card_layout.addWidget(label_w)
            
            value_label = QLabel("--")
            value_label.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
            card_layout.addWidget(value_label)
            
            self.margin_labels[key] = value_label
            margin_grid.addWidget(card)
        
        margin_grid.addStretch()
        margin_layout.addLayout(margin_grid)
        content_layout.addWidget(margin_frame)
        
        # 资金流向综合评分
        score_frame = self._create_section("🎯 资金流向评分", "")
        score_layout = score_frame.layout()
        
        self.capital_score_label = QLabel("--")
        self.capital_score_label.setStyleSheet(f"font-size: 48px; font-weight: 800; color: {Colors.TEXT_PRIMARY};")
        self.capital_score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_layout.addWidget(self.capital_score_label)
        
        self.capital_signal_label = QLabel("--")
        self.capital_signal_label.setStyleSheet(f"font-size: 14px; color: {Colors.TEXT_SECONDARY}; text-align: center;")
        self.capital_signal_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_layout.addWidget(self.capital_signal_label)
        
        content_layout.addWidget(score_frame)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return widget
    
    def _refresh_capital_flow(self):
        """刷新资金流向数据"""
        try:
            from core.capital_flow import create_capital_flow_analyzer
            
            self.capital_status_label.setText("正在获取...")
            self.capital_refresh_btn.setEnabled(False)
            
            QTimer.singleShot(100, self._do_refresh_capital)
        except Exception as e:
            self.capital_status_label.setText(f"❌ 错误: {e}")
    
    def _do_refresh_capital(self):
        """执行资金流刷新"""
        try:
            from core.capital_flow import create_capital_flow_analyzer
            
            analyzer = create_capital_flow_analyzer()
            result = analyzer.analyze_capital_flow()
            
            # 更新北向资金
            if result.northbound:
                nb = result.northbound
                self.nb_labels["today_net"].setText(f"{nb.total_net:+.1f}")
                self.nb_labels["sh_net"].setText(f"{nb.sh_net:+.1f}")
                self.nb_labels["sz_net"].setText(f"{nb.sz_net:+.1f}")
                
                # 颜色
                color = Colors.SUCCESS if nb.total_net > 0 else Colors.ERROR
                self.nb_labels["today_net"].setStyleSheet(f"font-size: 24px; font-weight: 700; color: {color};")
            
            # 5日净流入
            if 'northbound_5d' in result.details:
                val = result.details['northbound_5d']
                self.nb_labels["5d_net"].setText(f"{val:+.1f}")
                color = Colors.SUCCESS if val > 0 else Colors.ERROR
                self.nb_labels["5d_net"].setStyleSheet(f"font-size: 24px; font-weight: 700; color: {color};")
            
            # 两融
            if result.margin:
                self.margin_labels["balance"].setText(f"{result.margin.margin_balance:.0f}")
                self.margin_labels["change"].setText(f"{result.margin.margin_change:+.1f}")
                
                color = Colors.SUCCESS if result.margin.margin_change > 0 else Colors.ERROR
                self.margin_labels["change"].setStyleSheet(f"font-size: 24px; font-weight: 700; color: {color};")
            
            # 综合评分
            score = result.flow_score
            self.capital_score_label.setText(f"{score:+.0f}")
            color = Colors.SUCCESS if score > 20 else (Colors.ERROR if score < -20 else Colors.WARNING)
            self.capital_score_label.setStyleSheet(f"font-size: 48px; font-weight: 800; color: {color};")
            
            self.capital_signal_label.setText(f"{result.flow_trend} | {result.signal}")
            
            self.capital_status_label.setText(f"✅ 更新时间: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            logger.error(f"刷新资金流向失败: {e}")
            self.capital_status_label.setText(f"❌ 获取失败: {e}")
        finally:
            self.capital_refresh_btn.setEnabled(True)
    
    # ========== 新增Tab: 历史图表 ==========
    def _create_history_chart_tab(self) -> QWidget:
        """历史趋势图表Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {Colors.BG_SECONDARY}; }}")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 16, 24, 24)
        content_layout.setSpacing(20)
        
        # 标题
        title = QLabel("📉 历史趋势图表")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        content_layout.addWidget(title)
        
        desc = QLabel("K线图 + 趋势状态背景着色，直观展示市场历史走势与趋势变化")
        desc.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_MUTED};")
        content_layout.addWidget(desc)
        
        # 参数控制区
        params_frame = QFrame()
        params_frame.setStyleSheet(f"background-color: {Colors.BG_TERTIARY}; border-radius: 12px;")
        params_layout = QHBoxLayout(params_frame)
        params_layout.setContentsMargins(16, 12, 16, 12)
        params_layout.setSpacing(16)
        
        # 指数选择
        params_layout.addWidget(QLabel("指数:"))
        self.chart_index_combo = QComboBox()
        self.chart_index_combo.addItems([
            "上证指数(000001.XSHG)",
            "深证成指(399001.XSHE)",
            "创业板指(399006.XSHE)",
            "沪深300(000300.XSHG)",
            "中证500(000905.XSHG)"
        ])
        self.chart_index_combo.setStyleSheet(self._get_combo_style())
        params_layout.addWidget(self.chart_index_combo)
        
        # 周期选择
        params_layout.addWidget(QLabel("周期:"))
        self.chart_period_combo = QComboBox()
        self.chart_period_combo.addItems(["短期(5/20日)", "中期(20/60日)", "长期(60/120日)"])
        self.chart_period_combo.setCurrentIndex(1)
        self.chart_period_combo.setStyleSheet(self._get_combo_style())
        params_layout.addWidget(self.chart_period_combo)
        
        # 天数选择
        params_layout.addWidget(QLabel("天数:"))
        self.chart_days_spin = QSpinBox()
        self.chart_days_spin.setRange(30, 250)
        self.chart_days_spin.setValue(120)
        self.chart_days_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 6px 10px;
            }}
        """)
        params_layout.addWidget(self.chart_days_spin)
        
        # 生成按钮
        self.generate_chart_btn = QPushButton("📊 生成图表")
        self.generate_chart_btn.setStyleSheet(ButtonStyles.PRIMARY)
        self.generate_chart_btn.clicked.connect(self._generate_trend_chart)
        params_layout.addWidget(self.generate_chart_btn)
        
        self.chart_status_label = QLabel("")
        self.chart_status_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        params_layout.addWidget(self.chart_status_label)
        
        params_layout.addStretch()
        content_layout.addWidget(params_frame)
        
        # 图表显示区
        chart_frame = QFrame()
        chart_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 12px;
            }}
        """)
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setContentsMargins(16, 16, 16, 16)
        
        self.chart_label = QLabel('点击"生成图表"按钮查看历史趋势')
        self.chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chart_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 14px; min-height: 500px;")
        self.chart_label.setMinimumHeight(550)
        chart_layout.addWidget(self.chart_label)
        
        content_layout.addWidget(chart_frame)
        
        # 图例说明
        legend_frame = self._create_section("📌 图表说明", f"""
        <p style="color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
        <b>背景色含义:</b><br>
        <span style="color: #22c55e;">■ 深绿色</span> = 强势上涨 (得分 > 60)<br>
        <span style="color: #84cc16;">■ 浅绿色</span> = 上涨趋势 (得分 30-60)<br>
        <span style="color: #a3e635;">■ 淡绿色</span> = 弱势上涨 (得分 0-30)<br>
        <span style="color: #94a3b8;">■ 灰色</span> = 震荡整理 (得分 约0)<br>
        <span style="color: #fbbf24;">■ 黄色</span> = 弱势下跌 (得分 -30-0)<br>
        <span style="color: #f97316;">■ 橙色</span> = 下跌趋势 (得分 -60--30)<br>
        <span style="color: #ef4444;">■ 红色</span> = 强势下跌 (得分 < -60)
        </p>
        """)
        content_layout.addWidget(legend_frame)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return widget
    
    def _generate_trend_chart(self):
        """生成趋势图表"""
        try:
            from core.trend_chart import create_trend_chart_generator
            from PyQt6.QtGui import QPixmap
            
            self.chart_status_label.setText("正在生成...")
            self.generate_chart_btn.setEnabled(False)
            
            # 获取参数
            index_text = self.chart_index_combo.currentText()
            index_code = index_text.split("(")[1].rstrip(")") if "(" in index_text else "000001.XSHG"
            
            period_text = self.chart_period_combo.currentText()
            if "短期" in period_text:
                period = "short"
            elif "长期" in period_text:
                period = "long"
            else:
                period = "medium"
            
            days = self.chart_days_spin.value()
            
            # 异步生成
            QTimer.singleShot(100, lambda: self._do_generate_chart(index_code, period, days))
            
        except Exception as e:
            self.chart_status_label.setText(f"❌ 错误: {e}")
            self.generate_chart_btn.setEnabled(True)
    
    def _do_generate_chart(self, index_code: str, period: str, days: int):
        """执行图表生成"""
        try:
            from core.trend_chart import create_trend_chart_generator
            from PyQt6.QtGui import QPixmap
            import base64
            
            generator = create_trend_chart_generator(self.jq_client)
            chart_base64 = generator.generate_trend_chart(
                index_code=index_code,
                days=days,
                period=period,
                show_ma=True,
                show_volume=True
            )
            
            if chart_base64:
                # 解码并显示
                image_data = base64.b64decode(chart_base64)
                pixmap = QPixmap()
                pixmap.loadFromData(image_data)
                
                # 缩放适应
                scaled = pixmap.scaledToWidth(
                    self.chart_label.width() - 20,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.chart_label.setPixmap(scaled)
                self.chart_status_label.setText(f"✅ 生成完成 ({datetime.now().strftime('%H:%M:%S')})")
            else:
                self.chart_label.setText("图表生成失败，请检查数据连接")
                self.chart_status_label.setText("❌ 生成失败")
                
        except Exception as e:
            logger.error(f"生成趋势图表失败: {e}")
            import traceback
            traceback.print_exc()
            self.chart_label.setText(f"生成失败: {e}")
            self.chart_status_label.setText("❌ 错误")
        finally:
            self.generate_chart_btn.setEnabled(True)
    
    # ========== 新增Tab: HMM市场状态识别 ==========
    def _create_hmm_analysis_tab(self) -> QWidget:
        """HMM市场状态识别Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {Colors.BG_SECONDARY}; }}")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 16, 24, 24)
        content_layout.setSpacing(20)
        
        # 标题
        title = QLabel("🧠 市场状态识别 (HMM)")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        content_layout.addWidget(title)
        
        desc = QLabel("使用隐马尔可夫模型(HMM)识别市场隐藏状态：牛市、熊市、震荡")
        desc.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_MUTED};")
        content_layout.addWidget(desc)
        
        # 方法说明
        method_frame = self._create_section("📚 模型原理", f"""
        <p style="color: {Colors.TEXT_SECONDARY}; line-height: 1.8;">
        <b>隐马尔可夫模型 (Hidden Markov Model)</b><br><br>
        HMM假设市场存在三种"隐藏状态"：<br>
        • <b style="color: #22c55e;">牛市状态</b>：收益率为正、成交量放大、波动率适中<br>
        • <b style="color: #ef4444;">熊市状态</b>：收益率为负、恐慌性放量、波动率升高<br>
        • <b style="color: #94a3b8;">震荡状态</b>：收益率接近零、成交量萎缩、波动率较低<br><br>
        
        <b>观测变量:</b><br>
        1. 每日收益率变化<br>
        2. 成交量变化率<br>
        3. 波动率水平<br><br>
        
        <b>算法:</b> Viterbi算法找最可能的状态序列
        </p>
        """)
        content_layout.addWidget(method_frame)
        
        # 操作区
        action_frame = QFrame()
        action_frame.setStyleSheet(f"background-color: {Colors.BG_TERTIARY}; border-radius: 12px;")
        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(16, 12, 16, 12)
        
        action_layout.addWidget(QLabel("指数:"))
        self.hmm_index_combo = QComboBox()
        self.hmm_index_combo.addItems([
            "上证指数(000001.XSHG)",
            "深证成指(399001.XSHE)",
            "沪深300(000300.XSHG)"
        ])
        self.hmm_index_combo.setStyleSheet(self._get_combo_style())
        action_layout.addWidget(self.hmm_index_combo)
        
        self.hmm_analyze_btn = QPushButton("🔬 运行HMM分析")
        self.hmm_analyze_btn.setStyleSheet(ButtonStyles.PRIMARY)
        self.hmm_analyze_btn.clicked.connect(self._run_hmm_analysis)
        action_layout.addWidget(self.hmm_analyze_btn)
        
        self.hmm_status_label = QLabel("")
        self.hmm_status_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        action_layout.addWidget(self.hmm_status_label)
        
        action_layout.addStretch()
        content_layout.addWidget(action_frame)
        
        # 结果显示区
        result_frame = QFrame()
        result_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 12px;
            }}
        """)
        result_layout = QVBoxLayout(result_frame)
        result_layout.setContentsMargins(24, 20, 24, 20)
        result_layout.setSpacing(16)
        
        # 当前状态
        self.hmm_current_state = QLabel("--")
        self.hmm_current_state.setStyleSheet(f"font-size: 36px; font-weight: 800; color: {Colors.TEXT_PRIMARY};")
        self.hmm_current_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        result_layout.addWidget(self.hmm_current_state)
        
        self.hmm_confidence = QLabel("置信度: --")
        self.hmm_confidence.setStyleSheet(f"font-size: 14px; color: {Colors.TEXT_MUTED};")
        self.hmm_confidence.setAlignment(Qt.AlignmentFlag.AlignCenter)
        result_layout.addWidget(self.hmm_confidence)
        
        # 状态概率
        prob_grid = QGridLayout()
        prob_grid.setSpacing(12)
        
        self.hmm_prob_labels = {}
        for i, (state, color) in enumerate([("牛市", Colors.SUCCESS), ("熊市", Colors.ERROR), ("震荡", Colors.WARNING)]):
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.BG_SECONDARY};
                    border: 2px solid {color};
                    border-radius: 8px;
                }}
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 12, 16, 12)
            
            state_label = QLabel(state)
            state_label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {color};")
            state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(state_label)
            
            prob_label = QLabel("--")
            prob_label.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
            prob_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(prob_label)
            
            self.hmm_prob_labels[state] = prob_label
            prob_grid.addWidget(card, 0, i)
        
        result_layout.addLayout(prob_grid)
        
        # 转移概率
        trans_title = QLabel("📊 下一状态转移概率")
        trans_title.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {Colors.TEXT_PRIMARY}; margin-top: 12px;")
        result_layout.addWidget(trans_title)
        
        self.hmm_transition_label = QLabel("--")
        self.hmm_transition_label.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_SECONDARY};")
        result_layout.addWidget(self.hmm_transition_label)
        
        content_layout.addWidget(result_frame)
        
        # 分类器结果
        classifier_frame = self._create_section("📈 趋势分类器", "")
        classifier_layout = classifier_frame.layout()
        
        self.classifier_result = QLabel("点击上方按钮运行分析")
        self.classifier_result.setStyleSheet(f"font-size: 14px; color: {Colors.TEXT_SECONDARY};")
        self.classifier_result.setWordWrap(True)
        classifier_layout.addWidget(self.classifier_result)
        
        content_layout.addWidget(classifier_frame)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return widget
    
    def _run_hmm_analysis(self):
        """运行HMM分析"""
        try:
            self.hmm_status_label.setText("正在分析...")
            self.hmm_analyze_btn.setEnabled(False)
            
            QTimer.singleShot(100, self._do_hmm_analysis)
        except Exception as e:
            self.hmm_status_label.setText(f"❌ 错误: {e}")
    
    def _do_hmm_analysis(self):
        """执行HMM分析"""
        try:
            import jqdatasdk as jq
            from core.trend_ml import create_hmm_analyzer, create_trend_classifier
            
            # 获取数据
            index_text = self.hmm_index_combo.currentText()
            index_code = index_text.split("(")[1].rstrip(")") if "(" in index_text else "000001.XSHG"
            
            if self.jq_client:
                perm = self.jq_client.get_permission()
                end_date = perm.end_date if perm else "2025-08-29"
            else:
                end_date = "2025-08-29"
            
            df = jq.get_price(index_code, end_date=end_date, count=150,
                             frequency='daily', fields=['open', 'high', 'low', 'close', 'volume'])
            
            if df is None or df.empty:
                self.hmm_status_label.setText("❌ 数据获取失败")
                return
            
            # HMM分析
            hmm = create_hmm_analyzer()
            result = hmm.analyze(df)
            
            if result:
                # 更新当前状态
                state = result.current_state.value
                self.hmm_current_state.setText(state)
                
                if state == "牛市":
                    color = Colors.SUCCESS
                elif state == "熊市":
                    color = Colors.ERROR
                else:
                    color = Colors.WARNING
                
                self.hmm_current_state.setStyleSheet(f"font-size: 36px; font-weight: 800; color: {color};")
                self.hmm_confidence.setText(f"置信度: {result.confidence * 100:.1f}%")
                
                # 状态概率
                for state_name, prob in result.state_probability.items():
                    if state_name in self.hmm_prob_labels:
                        self.hmm_prob_labels[state_name].setText(f"{prob * 100:.1f}%")
                
                # 转移概率
                trans_text = " | ".join([f"{s}: {p*100:.0f}%" for s, p in result.transition_prob.items()])
                self.hmm_transition_label.setText(trans_text)
            
            # 趋势分类器
            classifier = create_trend_classifier()
            cls_result = classifier.classify(df)
            
            if cls_result:
                text = f"""
                <b>趋势类别:</b> {cls_result['trend_class']}<br>
                <b>综合得分:</b> {cls_result['total_score']:.1f}<br>
                <b>置信度:</b> {cls_result['confidence']*100:.1f}%<br><br>
                <b>特征得分:</b><br>
                """
                for k, v in cls_result.get('feature_scores', {}).items():
                    text += f"• {k}: {v:.1f}<br>"
                
                self.classifier_result.setText(text)
            
            self.hmm_status_label.setText(f"✅ 分析完成 ({datetime.now().strftime('%H:%M:%S')})")
            
        except Exception as e:
            logger.error(f"HMM分析失败: {e}")
            import traceback
            traceback.print_exc()
            self.hmm_status_label.setText(f"❌ 分析失败: {e}")
        finally:
            self.hmm_analyze_btn.setEnabled(True)
    
    def _get_combo_style(self) -> str:
        """下拉框样式"""
        return f"""
            QComboBox {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 140px;
            }}
            QComboBox:hover {{
                border-color: {Colors.MODULE_TREND_START};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                selection-background-color: {Colors.MODULE_TREND_START};
            }}
        """
    
    def _on_gauge_clicked(self, period: str):
        period_names = {"short": "短期", "medium": "中期", "long": "长期"}
        if self.current_result:
            term_data = self.current_result.get(f"{period}_term", {})
            msg = f"""
{period_names.get(period, period)}趋势详情:

得分: {term_data.get('score', 0):+.0f}
方向: {term_data.get('direction', '未知')}
置信度: {term_data.get('confidence', 0) * 100:.0f}%
建议仓位: {term_data.get('position', '50%')}
"""
            QMessageBox.information(self, f"{period_names.get(period)}趋势详情", msg.strip())
    
    def _load_cached_result(self):
        try:
            from pymongo import MongoClient
            client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
            db = client.jqquant
            cache = db.market_trend_cache.find_one(sort=[("timestamp", -1)])
            if cache:
                cache_time = datetime.fromisoformat(cache.get("timestamp", "2000-01-01"))
                if (datetime.now() - cache_time).total_seconds() < 3600:
                    self.current_result = cache.get("result", {})
                    self._update_display(self.current_result)
                    self.progress_label.setText(f"✅ 已加载缓存结果")
                    self.time_label.setText(f"更新: {cache_time.strftime('%Y-%m-%d %H:%M')}")
                    logger.info("市场趋势: 加载缓存成功")
        except Exception as e:
            logger.debug(f"加载趋势缓存失败: {e}")
    
    def _save_result_to_cache(self, result: dict):
        try:
            from pymongo import MongoClient
            import numpy as np
            
            def make_serializable(obj):
                """递归转换numpy类型为Python原生类型"""
                if isinstance(obj, dict):
                    return {k: make_serializable(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [make_serializable(v) for v in obj]
                elif isinstance(obj, (np.integer, np.int64, np.int32)):
                    return int(obj)
                elif isinstance(obj, (np.floating, np.float64, np.float32)):
                    return float(obj) if not np.isnan(obj) else 0.0
                elif isinstance(obj, (np.bool_, np.bool)):
                    return bool(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                else:
                    return obj
            
            serializable_result = make_serializable(result)
            
            client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
            db = client.jqquant
            db.market_trend_cache.delete_many({})
            db.market_trend_cache.insert_one({"result": serializable_result, "timestamp": datetime.now().isoformat()})
            logger.info("市场趋势: 结果已保存到缓存")
        except Exception as e:
            logger.warning(f"保存趋势缓存失败: {e}")
    
    def _start_analysis(self):
        if self.worker and self.worker.isRunning():
            return
        
        index_text = self.index_combo.currentText()
        index_code = index_text.split("(")[1].rstrip(")") if "(" in index_text else "000001.XSHG"
        
        self.analyze_btn.setEnabled(False)
        self.progress_label.setText("正在分析...")
        self.progress_label.setStyleSheet(f"color: {Colors.MODULE_TREND_START}; font-size: 13px;")
        
        self.worker = TrendAnalysisWorker(self.jq_client, index_code)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()
    
    def _on_progress(self, msg: str):
        self.progress_label.setText(msg)
    
    def _on_finished(self, result: dict):
        self.analyze_btn.setEnabled(True)
        self.progress_label.setText("✅ 分析完成")
        self.progress_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 13px;")
        self.time_label.setText(f"更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        self.current_result = result
        self._update_display(result)
        self._save_result_to_cache(result)
        self.trend_updated.emit(result)
        
        # 趋势-因子联动：自动更新因子权重
        self._update_factor_weights(result)
    
    def _on_error(self, error: str):
        self.analyze_btn.setEnabled(True)
        self.progress_label.setText(f"❌ 分析失败: {error}")
        self.progress_label.setStyleSheet(f"color: {Colors.ERROR}; font-size: 13px;")
    
    def _update_display(self, result: dict):
        try:
            for period, gauge in [("short", self.short_gauge), ("medium", self.medium_gauge), ("long", self.long_gauge)]:
                data = result.get(f"{period}_term", {})
                gauge.set_data(
                    data.get("score", 0),
                    data.get("direction", "震荡"),
                    data.get("confidence", 0.5),
                    data.get("position", "50%")
                )
            
            phase = result.get("market_phase", "未知")
            composite = result.get("composite_score", 0)
            
            self.phase_label.setText(phase)
            
            if "牛市" in phase or composite > 30:
                color = Colors.SUCCESS
            elif "熊市" in phase or composite < -30:
                color = Colors.ERROR
            else:
                color = Colors.WARNING
            
            self.phase_label.setStyleSheet(f"""
                font-size: 28px; font-weight: 800; color: {color};
                padding: 16px 24px; background-color: {Colors.BG_SECONDARY};
                border-radius: 12px; border-left: 4px solid {color};
            """)
            
            self.composite_score.setText(f"{composite:+.0f}")
            self.composite_score.setStyleSheet(f"font-size: 48px; font-weight: 800; color: {color};")
            
            if composite > 60:
                position, strategy, factors = "80-100%", "积极进攻，追强势股", "动量, 成长, 资金流"
            elif composite > 30:
                position, strategy, factors = "50-80%", "稳健持仓，跟随趋势", "动量, 质量, 成长"
            elif composite > 0:
                position, strategy, factors = "30-50%", "谨慎操作，控制仓位", "质量, 价值, 低波动"
            elif composite > -30:
                position, strategy, factors = "10-30%", "防御为主，等待机会", "价值, 低波动, 股息"
            else:
                position, strategy, factors = "0-10%", "空仓观望，保护本金", "现金为王"
            
            self.position_label.setText(position)
            self.strategy_label.setText(strategy)
            self.factors_label.setText(factors)
            
            # 更新共振分析
            if hasattr(self, 'resonance_table'):
                self._update_resonance_display(result)
            
            # 更新8指标卡片
            if hasattr(self, 'indicator_cards'):
                self._update_indicator_cards(result)
            
        except Exception as e:
            logger.error(f"更新显示失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_factor_weights(self, result: dict):
        """根据趋势分析结果更新因子权重（趋势-因子联动）"""
        try:
            from core.trend_factor_linker import get_trend_factor_linker
            
            linker = get_trend_factor_linker()
            weights = linker.update_from_trend(result)
            
            # 获取推荐因子
            recommended = linker.get_recommended_factors(top_n=6)
            avoided = linker.get_avoided_factors()
            regime_desc = linker.get_regime_description()
            
            # 保存联动结果供UI使用
            self._linkage_result = {
                "weights": weights,
                "recommended": recommended,
                "avoided": avoided,
                "regime": regime_desc,
                "regime_enum": linker.current_regime
            }
            
            # 更新状态标签
            if hasattr(self, 'linkage_status'):
                self.linkage_status.setText(f"✅ 已联动: {regime_desc}")
                self.linkage_status.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 12px;")
            
            # 日志记录
            rec_str = ", ".join([f"{f}({w:.0%})" for f, w in recommended[:3]])
            logger.info(f"📊 趋势-因子联动: {regime_desc}")
            logger.info(f"   推荐因子: {rec_str}")
            if avoided:
                logger.info(f"   避免因子: {', '.join(avoided)}")
            
        except Exception as e:
            logger.warning(f"趋势-因子联动失败: {e}")
            if hasattr(self, 'linkage_status'):
                self.linkage_status.setText(f"❌ 联动失败: {e}")
                self.linkage_status.setStyleSheet(f"color: {Colors.ERROR}; font-size: 12px;")
    
    def _show_factor_linkage_details(self):
        """显示因子联动详情"""
        if not hasattr(self, '_linkage_result') or not self._linkage_result:
            QMessageBox.information(self, "提示", "请先进行趋势分析以生成因子联动数据")
            return
        
        result = self._linkage_result
        
        # 切换详情显示
        is_visible = self.linkage_details.isVisible()
        self.linkage_details.setVisible(not is_visible)
        
        if is_visible:
            self.linkage_btn.setText("📊 查看联动详情")
            return
        
        self.linkage_btn.setText("📊 收起详情")
        
        # 更新市场状态
        regime = result.get("regime", "未知")
        self.regime_label.setText(regime)
        
        # 根据市场状态设置颜色
        regime_enum = result.get("regime_enum")
        if regime_enum:
            regime_name = regime_enum.value if hasattr(regime_enum, 'value') else str(regime_enum)
            if "bull" in regime_name:
                self.regime_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-weight: bold;")
            elif "bear" in regime_name:
                self.regime_label.setStyleSheet(f"color: {Colors.ERROR}; font-weight: bold;")
            else:
                self.regime_label.setStyleSheet(f"color: {Colors.WARNING}; font-weight: bold;")
        
        # 更新因子权重表格
        recommended = result.get("recommended", [])
        self.linkage_table.setRowCount(len(recommended))
        
        # 因子中文名映射
        factor_names = {
            "momentum": "动量因子",
            "growth": "成长因子",
            "value": "价值因子",
            "quality": "质量因子",
            "flow": "资金流因子",
            "volatility": "波动率因子",
            "size": "市值因子",
            "liquidity": "流动性因子"
        }
        
        for i, (factor, weight) in enumerate(recommended):
            # 因子名称
            name = factor_names.get(factor, factor)
            name_item = QTableWidgetItem(name)
            self.linkage_table.setItem(i, 0, name_item)
            
            # 权重
            weight_item = QTableWidgetItem(f"{weight:.0%}")
            if weight >= 0.25:
                weight_item.setForeground(QColor(Colors.SUCCESS))
            elif weight >= 0.15:
                weight_item.setForeground(QColor(Colors.PRIMARY))
            else:
                weight_item.setForeground(QColor(Colors.TEXT_SECONDARY))
            self.linkage_table.setItem(i, 1, weight_item)
            
            # 建议
            if weight >= 0.25:
                advice = "重点配置"
            elif weight >= 0.15:
                advice = "适当配置"
            elif weight >= 0.10:
                advice = "少量配置"
            else:
                advice = "观望"
            advice_item = QTableWidgetItem(advice)
            self.linkage_table.setItem(i, 2, advice_item)
        
        # 更新避免因子
        avoided = result.get("avoided", [])
        if avoided:
            avoided_names = [factor_names.get(f, f) for f in avoided]
            self.avoid_label.setText(", ".join(avoided_names))
        else:
            self.avoid_label.setText("无")
    
    def get_current_trend(self) -> Optional[dict]:
        return self.current_result
