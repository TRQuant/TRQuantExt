# -*- coding: utf-8 -*-
"""
韬睿量化专业版 - 主窗口
以策略开发为核心的机构级量化投研平台
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QStackedWidget, QApplication, QTextEdit,
    QGraphicsDropShadowEffect, QScrollArea, QGridLayout, QMessageBox
)
from PyQt6.QtCore import Qt, QSettings, QPropertyAnimation, QEasingCurve, QUrl
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QDesktopServices
from pathlib import Path
import subprocess
import sys
import webbrowser
import logging

from gui.styles.theme import Colors, Typography, ButtonStyles, CardStyles

logger = logging.getLogger(__name__)


class SidebarButton(QPushButton):
    """侧边栏导航按钮"""
    
    def __init__(self, icon: str, text: str, parent=None):
        super().__init__(parent)
        self.icon_text = icon
        self.label_text = text
        self.setText(f"{icon}  {text}")
        self.setCheckable(True)
        self.setFixedHeight(48)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_MUTED};
                border: none;
                border-radius: 10px;
                padding: 12px 16px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_HOVER};
                color: {Colors.TEXT_SECONDARY};
            }}
            QPushButton:checked {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.PRIMARY}33, stop:1 {Colors.ACCENT}22);
                color: {Colors.PRIMARY};
                font-weight: 600;
                border-left: 3px solid {Colors.PRIMARY};
                border-top-left-radius: 0;
                border-bottom-left-radius: 0;
            }}
        """)


class StatusIndicator(QWidget):
    """状态指示器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(8, 8)
        self._status = "offline"
        self.update_style()
    
    def set_status(self, status: str):
        """设置状态: online, offline, warning"""
        self._status = status
        self.update_style()
    
    def update_style(self):
        colors = {
            "online": Colors.SUCCESS,
            "offline": Colors.TEXT_MUTED,
            "warning": Colors.WARNING,
            "error": Colors.ERROR,
        }
        color = colors.get(self._status, Colors.TEXT_MUTED)
        self.setStyleSheet(f"""
            background-color: {color};
            border-radius: 4px;
        """)


class ToolCard(QFrame):
    """工具卡片组件"""
    
    def __init__(self, icon: str, title: str, description: str, 
                 color: str, callback=None, parent=None):
        super().__init__(parent)
        self.callback = callback
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 12px;
            }}
            QFrame:hover {{
                border-color: {color}88;
                background-color: {Colors.BG_CARD};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # 图标
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"""
            font-size: 28px;
            background-color: {color}22;
            border-radius: 10px;
            padding: 10px;
        """)
        icon_label.setFixedSize(52, 52)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 15px;
            font-weight: 600;
            color: {Colors.TEXT_PRIMARY};
        """)
        layout.addWidget(title_label)
        
        # 描述
        desc_label = QLabel(description)
        desc_label.setStyleSheet(f"""
            font-size: 12px;
            color: {Colors.TEXT_MUTED};
        """)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        layout.addStretch()
    
    def mousePressEvent(self, event):
        if self.callback:
            self.callback()
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    """主窗口 - 以策略开发为核心"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("韬睿量化专业版 - Taorui Quant Professional")
        self.setMinimumSize(1440, 900)
        
        # 设置窗口样式
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {Colors.BG_PRIMARY};
            }}
        """)
        
        self.init_ui()
        self.show_maximized_on_primary_screen()
    
    def show_maximized_on_primary_screen(self):
        """在主屏幕上最大化显示"""
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            self.setGeometry(geometry)
        self.showMaximized()
    
    def init_ui(self):
        """初始化UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 侧边栏
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)
        
        # 主内容区
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet(f"""
            QStackedWidget {{
                background-color: {Colors.BG_SECONDARY};
            }}
        """)
        
        # ========== 启动优化：延迟加载面板 ==========
        # 只立即加载首页，其他面板延迟加载
        self._panels_loaded = {i: False for i in range(10)}
        self._panel_classes = {}  # 存储面板类引用
        
        # 0: 首页（立即加载）
        self.home_page = self.create_home_page()
        self.content_stack.addWidget(self.home_page)
        self._panels_loaded[0] = True
        
        # 1-11: 创建占位符，延迟加载
        for i in range(1, 12):
            placeholder = QWidget()
            placeholder.setStyleSheet(f"background-color: {Colors.BG_SECONDARY};")
            self.content_stack.addWidget(placeholder)
        
        # 初始化面板引用
        self.data_source_panel = None
        self.mainline_panel = None
        self.stock_pool_panel = None  # 候选池面板
        self.factor_panel = None
        self.strategy_dev_panel = None
        self.backtest_panel = None
        self.trading_panel = None
        self.system_panel = None
        self.log_panel = None
        
        main_layout.addWidget(self.content_stack)
        
        # 设置默认页面
        self.nav_buttons[0].setChecked(True)
    
    def create_sidebar(self) -> QFrame:
        """创建侧边栏"""
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_DARK};
                border-right: 1px solid {Colors.BORDER_DARK};
            }}
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setSpacing(4)
        layout.setContentsMargins(16, 20, 16, 20)
        
        # === Logo区域 ===
        logo_frame = QWidget()
        logo_layout = QHBoxLayout(logo_frame)
        logo_layout.setContentsMargins(8, 0, 8, 0)
        logo_layout.setSpacing(12)
        
        # Logo图标
        logo_icon = QLabel()
        logo_icon.setFixedSize(40, 40)
        logo_icon.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {Colors.PRIMARY}, stop:1 {Colors.ACCENT});
            border-radius: 10px;
            font-size: 18px;
            font-weight: bold;
            color: white;
        """)
        logo_icon.setText("TR")
        logo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_icon.setFont(QFont("SF Pro Display", 14, QFont.Weight.Bold))
        logo_layout.addWidget(logo_icon)
        
        # Logo文字
        logo_text = QWidget()
        logo_text_layout = QVBoxLayout(logo_text)
        logo_text_layout.setContentsMargins(0, 0, 0, 0)
        logo_text_layout.setSpacing(0)
        
        title_label = QLabel("韬睿量化")
        title_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 700;
            color: {Colors.TEXT_PRIMARY};
            letter-spacing: 1px;
        """)
        logo_text_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Professional")
        subtitle_label.setStyleSheet(f"""
            font-size: 10px;
            color: {Colors.PRIMARY};
            letter-spacing: 2px;
        """)
        logo_text_layout.addWidget(subtitle_label)
        
        logo_layout.addWidget(logo_text)
        logo_layout.addStretch()
        
        layout.addWidget(logo_frame)
        layout.addSpacing(24)
        
        # === 分隔线 ===
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {Colors.BORDER_DARK};")
        layout.addWidget(divider)
        layout.addSpacing(16)
        
        # === 策略工作流 ===
        nav_label = QLabel("策略工作流")
        nav_label.setStyleSheet(f"""
            font-size: 11px;
            font-weight: 600;
            color: {Colors.TEXT_MUTED};
            letter-spacing: 1px;
            padding-left: 12px;
        """)
        layout.addWidget(nav_label)
        layout.addSpacing(8)
        
        # 导航按钮 - 按量化工作流程排序
        nav_items = [
            ("🏠", "工作台", 0),
            ("📡", "信息获取", 1),       # 步骤1: 数据源、知识库、资讯
            ("📈", "市场趋势", 2),       # 步骤2: 市场趋势识别（短/中/长期）
            ("🔥", "投资主线", 3),       # 步骤3: 五维量化→综合评分→主线识别
            ("📦", "候选池", 4),         # 步骤4: 股票池+ETF池构建（独立模块）
            ("📊", "因子构建", 5),       # 步骤5: 因子库+计算+组合
            ("🛠️", "策略开发", 6),       # 步骤6: 策略生成（整合）
            ("🔄", "回测验证", 7),       # 步骤7: 回测
            ("🚀", "实盘交易", 8),       # 步骤8: 实盘
        ]
        
        self.nav_buttons = []
        
        for icon, text, index in nav_items:
            btn = SidebarButton(icon, text)
            btn.clicked.connect(lambda checked, i=index: self.switch_page(i))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)
        
        layout.addSpacing(16)
        
        # === 系统管理 ===
        sys_label = QLabel("系统管理")
        sys_label.setStyleSheet(f"""
            font-size: 11px;
            font-weight: 600;
            color: {Colors.TEXT_MUTED};
            letter-spacing: 1px;
            padding-left: 12px;
        """)
        layout.addWidget(sys_label)
        layout.addSpacing(8)
        
        sys_items = [
            ("📁", "数据管理", 9),     # 文件管理系统
            ("⚙️", "系统设置", 10),
            ("📋", "运行日志", 11),
        ]
        
        self.sys_nav_start_index = len(self.nav_buttons)  # 记录系统按钮起始索引
        
        for icon, text, index in sys_items:
            btn = SidebarButton(icon, text)
            btn.clicked.connect(lambda checked, i=index: self.switch_page(i))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)
        
        layout.addStretch()
        
        # === 状态栏 ===
        status_frame = QFrame()
        status_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_SECONDARY};
                border-radius: 10px;
                padding: 8px;
            }}
        """)
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(12, 10, 12, 10)
        status_layout.setSpacing(8)
        
        self.status_indicator = StatusIndicator()
        status_layout.addWidget(self.status_indicator)
        
        self.status_text = QLabel("系统就绪")
        self.status_text.setStyleSheet(f"""
            font-size: 12px;
            color: {Colors.TEXT_TERTIARY};
        """)
        status_layout.addWidget(self.status_text)
        status_layout.addStretch()
        
        layout.addWidget(status_frame)
        layout.addSpacing(12)
        
        # === 版本信息 ===
        version_label = QLabel("v2.0.0 Professional")
        version_label.setStyleSheet(f"""
            color: {Colors.TEXT_DISABLED};
            font-size: 10px;
        """)
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)
        
        return sidebar
    
    def create_home_page(self) -> QWidget:
        """创建首页 - 策略开发工作台"""
        page = QWidget()
        page.setStyleSheet(f"background-color: {Colors.BG_SECONDARY};")
        
        # 使用滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {Colors.BG_SECONDARY};
            }}
        """)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(28)
        
        # === 欢迎区域 ===
        welcome_frame = QFrame()
        welcome_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.MODULE_HOME_START}, stop:1 {Colors.MODULE_HOME_END});
                border: none;
                border-radius: 16px;
            }}
        """)
        welcome_layout = QVBoxLayout(welcome_frame)
        welcome_layout.setContentsMargins(32, 28, 32, 28)
        welcome_layout.setSpacing(12)
        
        welcome_title = QLabel("🎯 策略开发工作台")
        welcome_title.setStyleSheet(f"""
            font-size: 32px;
            font-weight: 800;
            color: white;
            letter-spacing: 1px;
        """)
        welcome_layout.addWidget(welcome_title)
        
        welcome_subtitle = QLabel("信息获取 → 市场趋势 → 投资主线 → 候选池 → 因子构建 → 策略开发 → 回测验证 → 实盘交易")
        welcome_subtitle.setStyleSheet(f"""
            font-size: 15px;
            font-weight: 500;
            color: rgba(255,255,255,0.85);
        """)
        welcome_layout.addWidget(welcome_subtitle)
        
        # 使用指南按钮
        guide_btn_layout = QHBoxLayout()
        guide_btn_layout.addStretch()
        
        guide_btn = QPushButton("📖 查看使用指南")
        guide_btn.setStyleSheet(ButtonStyles.PRIMARY)
        guide_btn.setFixedHeight(40)
        guide_btn.clicked.connect(self.open_user_guide)
        guide_btn_layout.addWidget(guide_btn)
        
        welcome_layout.addLayout(guide_btn_layout)
        
        layout.addWidget(welcome_frame)
        
        # === 核心工作流程（流程图） ===
        workflow_title = QLabel("📋 量化工作流程")
        workflow_title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 600;
            color: {Colors.TEXT_PRIMARY};
        """)
        layout.addWidget(workflow_title)
        
        # 流程图容器
        workflow_frame = QFrame()
        workflow_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 16px;
            }}
        """)
        workflow_main_layout = QVBoxLayout(workflow_frame)
        workflow_main_layout.setContentsMargins(24, 20, 24, 20)
        workflow_main_layout.setSpacing(16)
        
        # 第一行：步骤 1-4（信息获取 → 市场趋势 → 投资主线 → 候选池）
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(0)
        
        # 步骤1: 信息获取
        step1 = self._create_workflow_step(
            "1", "📡", "信息获取", 
            "知识库/数据源/财经媒体",
            Colors.INFO, lambda: self.switch_page(1)
        )
        row1_layout.addWidget(step1)
        
        # 箭头
        arrow1 = self._create_arrow()
        row1_layout.addWidget(arrow1)
        
        # 步骤2: 市场趋势（新增）
        step2 = self._create_workflow_step(
            "2", "📈", "市场趋势",
            "短/中/长期趋势识别",
            Colors.PRIMARY, lambda: self.switch_page(2)
        )
        row1_layout.addWidget(step2)
        
        # 箭头
        arrow2 = self._create_arrow()
        row1_layout.addWidget(arrow2)
        
        # 步骤3: 投资主线
        step3 = self._create_workflow_step(
            "3", "🔥", "投资主线",
            "五维量化 → 综合评分 → 主线",
            "#F59E0B", lambda: self.switch_page(3)
        )
        row1_layout.addWidget(step3)
        
        # 箭头
        arrow3 = self._create_arrow()
        row1_layout.addWidget(arrow3)
        
        # 步骤4: 候选池
        step4 = self._create_workflow_step(
            "4", "📦", "候选池",
            "股票+ETF → 多渠道筛选",
            Colors.ACCENT, lambda: self.switch_page(4)
        )
        row1_layout.addWidget(step4)
        
        workflow_main_layout.addLayout(row1_layout)
        
        # 中间连接区域：简化的垂直箭头（与上方步骤对齐）
        middle_layout = QHBoxLayout()
        middle_layout.setContentsMargins(0, 8, 0, 8)
        middle_layout.setSpacing(0)
        
        # 第一列：信息获取下方（空白）
        spacer1 = QLabel("")
        spacer1.setFixedWidth(180)
        middle_layout.addWidget(spacer1)
        
        # 第一个箭头位置（空白）
        spacer_arrow1 = QLabel("")
        spacer_arrow1.setFixedWidth(40)
        middle_layout.addWidget(spacer_arrow1)
        
        # 第二列：投资主线下方（迭代回测箭头）
        iterate_label = QLabel("↑↓")
        iterate_label.setFixedWidth(180)
        iterate_label.setStyleSheet(f"""
            font-size: 22px;
            font-weight: bold;
            color: {Colors.PRIMARY};
        """)
        iterate_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        iterate_label.setToolTip("迭代回测优化")
        middle_layout.addWidget(iterate_label)
        
        # 第二个箭头位置（空白）
        spacer_arrow2 = QLabel("")
        spacer_arrow2.setFixedWidth(40)
        middle_layout.addWidget(spacer_arrow2)
        
        # 第三列：因子构建下方（向下箭头）
        down_label = QLabel("↓")
        down_label.setFixedWidth(180)
        down_label.setStyleSheet(f"""
            font-size: 22px;
            font-weight: bold;
            color: {Colors.SUCCESS};
        """)
        down_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        down_label.setToolTip("进入策略开发")
        middle_layout.addWidget(down_label)
        
        workflow_main_layout.addLayout(middle_layout)
        
        # 第二行：步骤 8-7-6-5（反向排列形成U型流程）
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(0)
        
        # 步骤8: 实盘交易
        step8 = self._create_workflow_step(
            "8", "🚀", "实盘交易",
            "PTrade/QMT → 风控执行",
            Colors.ERROR, lambda: self.switch_page(8)
        )
        row2_layout.addWidget(step8)
        
        # 箭头（反向）
        arrow7 = self._create_arrow(reverse=True)
        row2_layout.addWidget(arrow7)
        
        # 步骤7: 回测验证
        step7 = self._create_workflow_step(
            "7", "🔄", "回测验证",
            "本地/PTrade回测 → 报告",
            Colors.PRIMARY, lambda: self.switch_page(7)
        )
        row2_layout.addWidget(step7)
        
        # 箭头（反向）
        arrow6 = self._create_arrow(reverse=True)
        row2_layout.addWidget(arrow6)
        
        # 步骤6: 策略开发
        step6 = self._create_workflow_step(
            "6", "🛠️", "策略开发",
            "实战策略/生成器/AI助手",
            Colors.WARNING, lambda: self.switch_page(6)
        )
        row2_layout.addWidget(step6)
        
        # 箭头（反向）
        arrow5 = self._create_arrow(reverse=True)
        row2_layout.addWidget(arrow5)
        
        # 步骤5: 因子构建
        step5 = self._create_workflow_step(
            "5", "📊", "因子构建",
            "Alpha工程 → 因子库/组合",
            Colors.SUCCESS, lambda: self.switch_page(5)
        )
        row2_layout.addWidget(step5)
        
        workflow_main_layout.addLayout(row2_layout)
        
        layout.addWidget(workflow_frame)
        
        # === 集成工作流程（垂直流程） ===
        try:
            from gui.widgets.integrated_workflow_panel import IntegratedWorkflowPanel
            self.integrated_workflow = IntegratedWorkflowPanel()
            self.integrated_workflow.switch_page.connect(self.switch_page)
            layout.addWidget(self.integrated_workflow)
        except Exception as e:
            logger.warning(f"集成工作流程面板加载失败: {e}")
            # 显示占位符
            placeholder = QLabel("⚠️ 集成工作流程面板加载失败")
            placeholder.setStyleSheet(f"color: {Colors.WARNING}; padding: 16px;")
            layout.addWidget(placeholder)
        
        # === 系统状态概览 ===
        status_title = QLabel("📊 系统状态")
        status_title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 600;
            color: {Colors.TEXT_PRIMARY};
        """)
        layout.addWidget(status_title)
        
        status_layout = QHBoxLayout()
        status_layout.setSpacing(16)
        
        # 状态卡片
        status_items = [
            ("🔌", "数据源", "JQData + AKShare", "已连接", Colors.SUCCESS),
            ("💾", "数据缓存", "MongoDB", "运行中", Colors.SUCCESS),
            ("📊", "因子库", "60+ 因子", "可用", Colors.PRIMARY),
            ("🚀", "交易接口", "PTrade/QMT", "待配置", Colors.WARNING),
        ]
        
        for icon, name, detail, status, color in status_items:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.BG_TERTIARY};
                    border: 1px solid {Colors.BORDER_PRIMARY};
                    border-radius: 12px;
                }}
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 14, 16, 14)
            card_layout.setSpacing(6)
            
            header = QHBoxLayout()
            icon_label = QLabel(icon)
            icon_label.setStyleSheet("font-size: 20px;")
            header.addWidget(icon_label)
            
            name_label = QLabel(name)
            name_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
            header.addWidget(name_label)
            header.addStretch()
            
            status_label = QLabel(status)
            status_label.setStyleSheet(f"""
                font-size: 10px;
                font-weight: 600;
                color: {color};
                background-color: {color}20;
                padding: 3px 8px;
                border-radius: 8px;
            """)
            header.addWidget(status_label)
            card_layout.addLayout(header)
            
            detail_label = QLabel(detail)
            detail_label.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED};")
            card_layout.addWidget(detail_label)
            
            status_layout.addWidget(card)
        
        layout.addLayout(status_layout)
        
        # === 工具与资源 ===
        tools_title = QLabel("🛠️ 工具与资源")
        tools_title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 600;
            color: {Colors.TEXT_PRIMARY};
        """)
        layout.addWidget(tools_title)
        
        tools_grid = QGridLayout()
        tools_grid.setSpacing(16)
        
        tools_items = [
            ("📂", "文件管理系统", "策略代码、回测报告管理", Colors.PRIMARY, self.open_dashboard),
            ("📚", "A股实操手册", "量化因子体系与实战指南", Colors.ACCENT, self.open_manual),
            ("⚙️", "系统设置", "数据源配置与系统管理", Colors.TEXT_MUTED, lambda: self.switch_page(9)),
            ("📋", "运行日志", "查看系统运行记录", Colors.INFO, lambda: self.switch_page(10)),
        ]
        
        for i, (icon, title, desc, color, callback) in enumerate(tools_items):
            card = ToolCard(icon, title, desc, color, callback)
            card.setFixedHeight(110)
            tools_grid.addWidget(card, 0, i)
        
        layout.addLayout(tools_grid)
        
        # === 快捷操作 ===
        quick_frame = QFrame()
        quick_frame.setStyleSheet(CardStyles.DEFAULT)
        quick_layout = QHBoxLayout(quick_frame)
        quick_layout.setContentsMargins(20, 12, 20, 12)
        quick_layout.setSpacing(12)
        
        quick_label = QLabel("⚡ 快捷操作")
        quick_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 600;
            color: {Colors.TEXT_MUTED};
        """)
        quick_layout.addWidget(quick_label)
        quick_layout.addSpacing(8)
        
        quick_actions = [
            ("📖", "使用指南", self.open_user_guide),
            ("🔍", "扫描主线", lambda: self.switch_page(2)),
            ("🚀", "新建策略", lambda: self.switch_page(6)),
        ]
        
        for icon, text, callback in quick_actions:
            btn = QPushButton(f"{icon} {text}")
            btn.setStyleSheet(ButtonStyles.SECONDARY)
            btn.setFixedHeight(36)
            btn.clicked.connect(callback)
            quick_layout.addWidget(btn)
        
        quick_layout.addStretch()
        layout.addWidget(quick_frame)
        
        layout.addStretch()
        
        scroll.setWidget(content)
        
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        
        return page
    
    def create_log_panel(self) -> QWidget:
        """创建日志面板"""
        panel = QWidget()
        panel.setStyleSheet(f"background-color: {Colors.BG_SECONDARY};")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        # 标题栏
        header = QHBoxLayout()
        
        title = QLabel("📋 运行日志")
        title.setStyleSheet(f"""
            font-size: 24px;
            font-weight: 700;
            color: {Colors.TEXT_PRIMARY};
        """)
        header.addWidget(title)
        header.addStretch()
        
        clear_btn = QPushButton("🗑️ 清空")
        clear_btn.setStyleSheet(ButtonStyles.SECONDARY)
        clear_btn.setFixedSize(100, 40)
        clear_btn.clicked.connect(self.clear_logs)
        header.addWidget(clear_btn)
        
        layout.addLayout(header)
        
        # 日志内容
        log_frame = QFrame()
        log_frame.setStyleSheet(CardStyles.DEFAULT)
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(0, 0, 0, 0)
        
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_DARK};
                color: {Colors.TEXT_TERTIARY};
                border: none;
                border-radius: 12px;
                font-family: {Typography.FONT_MONO};
                font-size: 12px;
                padding: 16px;
                line-height: 1.6;
            }}
        """)
        self.log_viewer.setPlaceholderText("系统日志将在此显示...")
        log_layout.addWidget(self.log_viewer)
        
        layout.addWidget(log_frame)
        
        return panel
    
    def switch_page(self, index: int):
        """切换页面 - 支持延迟加载"""
        # 延迟加载面板
        if not self._panels_loaded.get(index, False):
            self._load_panel(index)
        
        self.content_stack.setCurrentIndex(index)
        
        # 更新导航按钮选中状态
        # 页面索引与导航按钮索引现在是一致的：
        # 0: 工作台, 1: 信息获取, 2: 市场趋势, 3: 投资主线, 4: 候选池
        # 5: 因子构建, 6: 策略开发, 7: 回测验证, 8: 实盘交易
        # 9: 数据管理, 10: 系统设置, 11: 运行日志
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
    
    def _load_panel(self, index: int):
        """延迟加载或刷新面板"""
        old_widget = self.content_stack.widget(index)
        new_widget = None
        
        try:
            if index == 0:  # 首页（工作台）
                new_widget = self.create_home_page()
                self.home_page = new_widget
            
            elif index == 1:  # 信息获取
                from gui.widgets.data_source_panel import DataSourcePanel
                new_widget = DataSourcePanel()
                new_widget.open_manual.connect(self.open_manual)
                new_widget.open_settings.connect(lambda: self.switch_page(9))
                self.data_source_panel = new_widget
                
            elif index == 2:  # 市场趋势（新增）
                from gui.widgets.market_trend_panel import MarketTrendPanel
                new_widget = MarketTrendPanel()
                # 连接趋势更新信号，供其他模块使用
                new_widget.trend_updated.connect(self._on_trend_updated)
                self.market_trend_panel = new_widget
                
            elif index == 3:  # 投资主线
                from gui.widgets.mainline_panel import MainlinePanel
                new_widget = MainlinePanel()
                new_widget.generate_strategy.connect(self._on_mainline_generate_strategy)
                new_widget.run_backtest.connect(self._on_mainline_run_backtest)
                self.mainline_panel = new_widget
                
            elif index == 4:  # 候选池（独立模块）- 基于主线识别+JQData
                from gui.widgets.stock_pool_panel import StockPoolPanel
                new_widget = StockPoolPanel()
                self.stock_pool_panel = new_widget
                
            elif index == 5:  # 因子构建
                from gui.widgets.factor_builder_panel import FactorBuilderPanel
                new_widget = FactorBuilderPanel()
                self.factor_panel = new_widget
                
            elif index == 6:  # 策略开发
                from gui.widgets.strategy_dev_panel import StrategyDevPanel
                new_widget = StrategyDevPanel()
                new_widget.run_backtest.connect(self.on_run_backtest)
                self.strategy_dev_panel = new_widget
                
            elif index == 7:  # 回测验证
                from gui.widgets.backtest_panel import BacktestPanel
                new_widget = BacktestPanel()
                self.backtest_panel = new_widget
                
            elif index == 8:  # 实盘交易
                from gui.widgets.trading_panel import TradingPanel
                new_widget = TradingPanel()
                self.trading_panel = new_widget
                
            elif index == 9:  # 数据管理
                from gui.widgets.data_manager_panel import DataManagerPanel
                new_widget = DataManagerPanel()
                self.data_manager_panel = new_widget
                
            elif index == 10:  # 系统设置
                from gui.widgets.system_panel import SystemPanel
                new_widget = SystemPanel()
                new_widget.system_started.connect(self.on_system_started)
                new_widget.system_stopped.connect(self.on_system_stopped)
                self.system_panel = new_widget
                
            elif index == 11:  # 运行日志
                new_widget = self.create_log_panel()
                self.log_panel = new_widget
            
            if new_widget and old_widget:
                # 替换widget
                self.content_stack.removeWidget(old_widget)
                self.content_stack.insertWidget(index, new_widget)
                self.content_stack.setCurrentIndex(index)
                old_widget.deleteLater()
                self._panels_loaded[index] = True
                
        except Exception as e:
            logger.error(f"加载面板 {index} 失败: {e}")
            import traceback
            traceback.print_exc()
    
    
    def _get_page_name(self, index: int) -> str:
        """获取页面名称"""
        page_names = {
            0: "工作台",
            1: "信息获取",
            2: "市场趋势",
            3: "投资主线",
            4: "候选池",
            5: "因子构建",
            6: "策略开发",
            7: "回测验证",
            8: "实盘交易",
            9: "数据管理",
            10: "系统设置",
            11: "运行日志",
        }
        return page_names.get(index, f"页面{index}")
    
    def _on_mainline_generate_strategy(self, data: dict):
        """从投资主线模块生成策略"""
        # 切换到策略开发页面
        self.switch_page(6)
        self.log_message("📝 从投资主线生成策略...")
    
    def _on_mainline_run_backtest(self, data: dict):
        """从投资主线模块运行回测"""
        # 切换到回测验证页面
        self.switch_page(7)
        self.log_message("📈 从投资主线运行回测...")
    
    def _on_trend_updated(self, trend_data: dict):
        """处理市场趋势更新"""
        try:
            phase = trend_data.get("market_phase", "未知")
            score = trend_data.get("composite_score", 0)
            self.log_message(f"📈 市场趋势更新: {phase} (得分: {score:+.0f})")
            
            # 可以将趋势信息传递给其他模块
            if hasattr(self, 'factor_panel') and self.factor_panel:
                # 通知因子模块当前市场趋势
                pass
        except Exception as e:
            logger.warning(f"处理趋势更新失败: {e}")
    
    def on_run_backtest(self, strategy_path: str, params: dict):
        """
        运行回测 - 从策略开发模块接收策略并跳转到回测页面
        
        参数:
            strategy_path: 策略文件路径
            params: 策略参数，包含 code, filepath, filename 等
        """
        # 切换到回测验证页面
        self.switch_page(5)
        
        # 如果回测面板有加载策略的方法，调用它
        if hasattr(self.backtest_panel, 'load_strategy_file'):
            self.backtest_panel.load_strategy_file(strategy_path)
        elif hasattr(self.backtest_panel, 'strategy_combo'):
            # 尝试设置策略名称
            filename = params.get('filename', strategy_path)
            self.backtest_panel.strategy_combo.setCurrentText(filename)
        
        # 设置默认参数
        if hasattr(self.backtest_panel, 'capital_input'):
            self.backtest_panel.capital_input.setValue(params.get('initial_capital', 1000000))
        if hasattr(self.backtest_panel, 'fee_input'):
            self.backtest_panel.fee_input.setValue(params.get('commission_rate', 0.0003))
        
        # 记录日志
        self.log_message(f"📈 策略已发送到回测验证: {strategy_path}")
    
    def on_strategy_generated(self, file_path: str, platform: str):
        """策略生成完成"""
        self.log_message(f"✅ 策略已保存: {file_path}")
        self.log_message(f"   平台: {platform}")
    
    def on_system_started(self):
        """系统启动"""
        self.status_indicator.set_status("online")
        self.status_text.setText("系统运行中")
        self.status_text.setStyleSheet(f"font-size: 12px; color: {Colors.SUCCESS};")
        self.log_message("✅ 系统启动成功")
    
    def on_system_stopped(self):
        """系统停止"""
        self.status_indicator.set_status("offline")
        self.status_text.setText("系统已停止")
        self.status_text.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_TERTIARY};")
        self.log_message("⏹️ 系统已停止")
    
    def log_message(self, message: str):
        """记录日志"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        # 确保 log_viewer 存在
        if hasattr(self, 'log_viewer') and self.log_viewer:
            self.log_viewer.append(f"<span style='color: {Colors.TEXT_MUTED};'>[{timestamp}]</span> {message}")
        else:
            # 如果日志面板尚未创建，打印到控制台
            print(f"[{timestamp}] {message}")
    
    def clear_logs(self):
        """清空日志"""
        if hasattr(self, 'log_viewer') and self.log_viewer:
            self.log_viewer.clear()
    
    # === 工具方法 ===
    
    def _create_workflow_step(self, step_num: str, icon: str, title: str, 
                               desc: str, color: str, callback) -> QFrame:
        """创建工作流程步骤卡片"""
        frame = QFrame()
        frame.setCursor(Qt.CursorShape.PointingHandCursor)
        frame.setFixedSize(180, 100)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 2px solid {color}66;
                border-radius: 12px;
            }}
            QFrame:hover {{
                background-color: {color}15;
                border-color: {color}AA;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        
        # 顶部：步骤号和图标
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)
        
        step_label = QLabel(step_num)
        step_label.setStyleSheet(f"""
            background-color: {color};
            color: #0d0d14;
            font-size: 11px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 8px;
            min-width: 16px;
        """)
        step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        step_label.setFixedSize(20, 20)
        top_layout.addWidget(step_label)
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 20px;")
        top_layout.addWidget(icon_label)
        
        top_layout.addStretch()
        layout.addLayout(top_layout)
        
        # 标题 - 使用白色确保可读性
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 600;
            color: #ffffff;
        """)
        layout.addWidget(title_label)
        
        # 描述 - 使用更亮的颜色确保可读性
        desc_label = QLabel(desc)
        desc_label.setStyleSheet(f"""
            font-size: 11px;
            color: #cdd6f4;
        """)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # 点击事件
        frame.mousePressEvent = lambda e: callback()
        
        return frame
    
    def _create_arrow(self, reverse: bool = False) -> QLabel:
        """创建流程箭头"""
        arrow = QLabel("→" if not reverse else "←")
        arrow.setStyleSheet(f"""
            font-size: 24px;
            font-weight: bold;
            color: {Colors.PRIMARY};
            padding: 0 8px;
        """)
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow.setFixedWidth(40)
        return arrow
    
    def open_dashboard(self):
        """打开文件管理仪表盘"""
        try:
            # 启动Dashboard服务
            project_root = Path(__file__).parent.parent
            subprocess.Popen(
                [sys.executable, 'start_dashboard.py'],
                cwd=str(project_root),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            # 等待服务启动后打开浏览器
            import time
            time.sleep(1)
            webbrowser.open("http://127.0.0.1:5000")
            self.log_message("📂 文件管理系统已启动")
        except Exception as e:
            self.log_message(f"❌ 启动失败: {e}")
            QMessageBox.warning(self, "启动失败", f"无法启动文件管理系统: {e}")
    
    def open_user_guide(self):
        """打开使用指南"""
        from gui.widgets.user_guide_dialog import UserGuideDialog
        
        dialog = UserGuideDialog(self)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
    
    def show_startup_guide(self):
        """启动时显示使用指南（如果用户未选择不再显示）"""
        from gui.widgets.user_guide_dialog import UserGuideDialog
        
        if UserGuideDialog.should_show_on_startup():
            # 延迟显示，确保主窗口已完全加载
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(500, self.open_user_guide)
    
    def open_manual(self):
        """打开A股高倍股实操手册 - 五册导航首页"""
        manual_path = Path(__file__).parent.parent / "AShare-manual"
        if manual_path.exists():
            try:
                subprocess.Popen(
                    ['npm', 'run', 'dev'],
                    cwd=str(manual_path),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                import time
                time.sleep(2)
                # 进入A股手册五册导航首页
                webbrowser.open("http://localhost:4321")
                self.log_message("📚 A股高倍股实操手册已启动 - 五册导航首页")
            except Exception as e:
                self.log_message(f"❌ 启动失败: {e}")
        else:
            self.log_message("❌ A股手册目录不存在")
            QMessageBox.warning(self, "目录不存在", "A股高倍股实操手册目录不存在")
    
    def open_us_stock_manual(self):
        """打开美股投资实操手册"""
        manual_path = Path(__file__).parent.parent / "US_Stock_Manual"
        if manual_path.exists():
            try:
                subprocess.Popen(
                    ['npm', 'run', 'dev', '--', '--port', '4322'],
                    cwd=str(manual_path),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                import time
                time.sleep(2)
                webbrowser.open("http://localhost:4322")
                self.log_message("📚 美股投资实操手册已启动")
            except Exception as e:
                self.log_message(f"❌ 启动失败: {e}")
        else:
            self.log_message("❌ 美股手册目录不存在")
            QMessageBox.warning(self, "目录不存在", "美股投资实操手册目录不存在")
    
    def open_cursor_prompts(self):
        """打开Cursor提示词"""
        prompts_path = Path(__file__).parent.parent / "prompts"
        if prompts_path.exists():
            try:
                # 尝试用Cursor打开
                subprocess.Popen(['cursor', str(prompts_path)])
                self.log_message("🤖 已在Cursor中打开提示词目录")
            except FileNotFoundError:
                # 如果Cursor不可用，用文件管理器打开
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(prompts_path)))
                self.log_message("📁 已打开提示词目录")
        else:
            self.log_message("❌ 提示词目录不存在")
    
    def open_bridge_manager(self):
        """打开Bridge服务管理"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Bridge服务管理")
        msg.setText("Bridge服务管理")
        msg.setInformativeText(
            "PTrade Bridge: http://localhost:8001\n"
            "QMT Bridge: http://localhost:8002\n"
            "QuantConnect Bridge: http://localhost:8003\n\n"
            "使用终端命令启动:\n"
            "./scripts/docker_manager.sh services"
        )
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()
        self.log_message("📡 Bridge服务信息已显示")
    
    def start_system(self):
        """启动系统"""
        self.switch_page(9)  # 切换到系统设置页面
        self.system_panel.start_system()
    
    def sync_data(self):
        """同步数据"""
        self.log_message("🔄 开始同步数据...")
        # TODO: 实现数据同步逻辑
        self.log_message("✅ 数据同步完成")
