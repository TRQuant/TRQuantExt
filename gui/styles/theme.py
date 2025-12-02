# -*- coding: utf-8 -*-
"""
韬睿量化专业版 - 主题样式系统
机构级专业设计标准
"""

# 颜色系统 - 基于专业金融终端设计
class Colors:
    """颜色定义"""
    
    # 主色调 - 深蓝渐变
    PRIMARY = "#667eea"
    PRIMARY_LIGHT = "#7c93f0"
    PRIMARY_DARK = "#5568d6"
    
    # 强调色
    ACCENT = "#764ba2"
    ACCENT_LIGHT = "#8a5fb6"
    ACCENT_DARK = "#624090"
    
    # 背景色系
    BG_DARK = "#0a0a12"
    BG_PRIMARY = "#0d0d14"
    BG_SECONDARY = "#12121f"
    BG_TERTIARY = "#181825"
    BG_CARD = "#1e1e2e"
    BG_HOVER = "#252535"
    
    # 边框色
    BORDER_DARK = "#1a1a2e"
    BORDER_PRIMARY = "#2a2a4a"
    BORDER_LIGHT = "#3a3a6a"
    BORDER_ACTIVE = "#667eea"
    
    # 文字色
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#cdd6f4"
    TEXT_TERTIARY = "#a6adc8"
    TEXT_MUTED = "#9ca3af"     # 提高对比度: 从 #6c7086 改为更亮的灰色
    TEXT_DISABLED = "#6b7280"  # 提高对比度: 从 #45475a 改为更亮的灰色
    
    # 状态色
    SUCCESS = "#a6e3a1"
    SUCCESS_DARK = "#40a02b"
    WARNING = "#f9e2af"
    WARNING_DARK = "#df8e1d"
    ERROR = "#f38ba8"
    ERROR_DARK = "#d20f39"
    INFO = "#89b4fa"
    INFO_DARK = "#1e66f5"
    
    # 涨跌色
    UP = "#ef4444"      # 红涨
    DOWN = "#22c55e"    # 绿跌
    FLAT = "#6c7086"    # 平盘
    
    # 图表色
    CHART_1 = "#667eea"
    CHART_2 = "#a6e3a1"
    CHART_3 = "#f9e2af"
    CHART_4 = "#f38ba8"
    CHART_5 = "#89b4fa"
    CHART_6 = "#cba6f7"
    
    # ========== 模块主题色 ==========
    # 每个模块独特的渐变色，用于Banner区分
    
    # 工作台 - 紫蓝渐变（品牌色）
    MODULE_HOME_START = "#667eea"
    MODULE_HOME_END = "#764ba2"
    
    # 信息获取 - 青蓝渐变（信息/数据感）
    MODULE_DATA_START = "#0891b2"
    MODULE_DATA_END = "#0ea5e9"
    
    # 市场趋势 - 翠绿渐变（趋势/成长感）
    MODULE_TREND_START = "#059669"
    MODULE_TREND_END = "#10b981"
    
    # 投资主线 - 橙红渐变（热度/焦点感）
    MODULE_MAINLINE_START = "#ea580c"
    MODULE_MAINLINE_END = "#f97316"
    
    # 候选池 - 紫粉渐变（筛选/精选感）
    MODULE_POOL_START = "#9333ea"
    MODULE_POOL_END = "#a855f7"
    
    # 因子构建 - 蓝绿渐变（科技/量化感）
    MODULE_FACTOR_START = "#0284c7"
    MODULE_FACTOR_END = "#06b6d4"
    
    # 策略开发 - 金黄渐变（价值/策略感）
    MODULE_STRATEGY_START = "#ca8a04"
    MODULE_STRATEGY_END = "#eab308"
    
    # 回测验证 - 靛蓝渐变（验证/测试感）
    MODULE_BACKTEST_START = "#4f46e5"
    MODULE_BACKTEST_END = "#6366f1"
    
    # 实盘交易 - 红橙渐变（实战/交易感）
    MODULE_TRADING_START = "#dc2626"
    MODULE_TRADING_END = "#ef4444"


class Typography:
    """字体定义"""
    
    # 字体族
    FONT_FAMILY = "'SF Pro Display', 'PingFang SC', 'Microsoft YaHei', sans-serif"
    FONT_MONO = "'JetBrains Mono', 'Fira Code', 'Consolas', monospace"
    
    # 字号
    SIZE_XS = "10px"
    SIZE_SM = "12px"
    SIZE_BASE = "14px"
    SIZE_LG = "16px"
    SIZE_XL = "18px"
    SIZE_2XL = "24px"
    SIZE_3XL = "32px"
    SIZE_4XL = "48px"


class Spacing:
    """间距定义"""
    
    XS = "4px"
    SM = "8px"
    MD = "12px"
    LG = "16px"
    XL = "24px"
    XXL = "32px"
    XXXL = "48px"


class BorderRadius:
    """圆角定义"""
    
    SM = "4px"
    MD = "8px"
    LG = "12px"
    XL = "16px"
    FULL = "9999px"


# 全局样式表
GLOBAL_STYLE = f"""
/* 全局样式 */
QWidget {{
    font-family: {Typography.FONT_FAMILY};
    font-size: {Typography.SIZE_BASE};
    color: {Colors.TEXT_SECONDARY};
    background-color: transparent;
}}

QMainWindow {{
    background-color: {Colors.BG_PRIMARY};
}}

/* 滚动条 */
QScrollBar:vertical {{
    background-color: {Colors.BG_SECONDARY};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {Colors.BORDER_PRIMARY};
    border-radius: 4px;
    min-height: 40px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {Colors.BORDER_LIGHT};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {Colors.BG_SECONDARY};
    height: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal {{
    background-color: {Colors.BORDER_PRIMARY};
    border-radius: 4px;
    min-width: 40px;
}}

/* 工具提示 */
QToolTip {{
    background-color: {Colors.BG_CARD};
    color: {Colors.TEXT_SECONDARY};
    border: 1px solid {Colors.BORDER_PRIMARY};
    border-radius: {BorderRadius.MD};
    padding: 8px 12px;
}}

/* 菜单 */
QMenu {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER_PRIMARY};
    border-radius: {BorderRadius.MD};
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 24px;
    border-radius: {BorderRadius.SM};
}}

QMenu::item:selected {{
    background-color: {Colors.PRIMARY}33;
    color: {Colors.PRIMARY};
}}

/* 输入框 */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {Colors.BG_SECONDARY};
    border: 1px solid {Colors.BORDER_PRIMARY};
    border-radius: {BorderRadius.MD};
    padding: 10px 12px;
    color: {Colors.TEXT_SECONDARY};
    selection-background-color: {Colors.PRIMARY}55;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {Colors.PRIMARY};
}}

QLineEdit:disabled, QTextEdit:disabled {{
    background-color: {Colors.BG_DARK};
    color: {Colors.TEXT_DISABLED};
}}

/* 下拉框 */
QComboBox {{
    background-color: {Colors.BG_SECONDARY};
    border: 1px solid {Colors.BORDER_PRIMARY};
    border-radius: {BorderRadius.MD};
    padding: 8px 12px;
    color: {Colors.TEXT_SECONDARY};
    min-width: 100px;
}}

QComboBox:hover {{
    border-color: {Colors.BORDER_LIGHT};
}}

QComboBox:focus {{
    border-color: {Colors.PRIMARY};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {Colors.TEXT_MUTED};
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER_PRIMARY};
    border-radius: {BorderRadius.MD};
    selection-background-color: {Colors.PRIMARY}33;
    selection-color: {Colors.PRIMARY};
    padding: 4px;
}}

/* 数值输入框 */
QSpinBox, QDoubleSpinBox {{
    background-color: {Colors.BG_SECONDARY};
    border: 1px solid {Colors.BORDER_PRIMARY};
    border-radius: {BorderRadius.MD};
    padding: 8px 12px;
    color: {Colors.TEXT_SECONDARY};
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {Colors.PRIMARY};
}}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background-color: transparent;
    border: none;
    width: 16px;
}}

/* 日期选择器 */
QDateEdit {{
    background-color: {Colors.BG_SECONDARY};
    border: 1px solid {Colors.BORDER_PRIMARY};
    border-radius: {BorderRadius.MD};
    padding: 8px 12px;
    color: {Colors.TEXT_SECONDARY};
}}

QDateEdit:focus {{
    border-color: {Colors.PRIMARY};
}}

QCalendarWidget {{
    background-color: {Colors.BG_CARD};
}}

/* 复选框 */
QCheckBox {{
    spacing: 8px;
    color: {Colors.TEXT_SECONDARY};
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {Colors.BORDER_PRIMARY};
    border-radius: {BorderRadius.SM};
    background-color: {Colors.BG_SECONDARY};
}}

QCheckBox::indicator:hover {{
    border-color: {Colors.PRIMARY};
}}

QCheckBox::indicator:checked {{
    background-color: {Colors.PRIMARY};
    border-color: {Colors.PRIMARY};
}}

/* 单选按钮 */
QRadioButton {{
    spacing: 8px;
    color: {Colors.TEXT_SECONDARY};
}}

QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {Colors.BORDER_PRIMARY};
    border-radius: 9px;
    background-color: {Colors.BG_SECONDARY};
}}

QRadioButton::indicator:hover {{
    border-color: {Colors.PRIMARY};
}}

QRadioButton::indicator:checked {{
    background-color: {Colors.PRIMARY};
    border-color: {Colors.PRIMARY};
}}

/* 进度条 */
QProgressBar {{
    background-color: {Colors.BG_SECONDARY};
    border: none;
    border-radius: {BorderRadius.SM};
    text-align: center;
    color: {Colors.TEXT_SECONDARY};
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {Colors.PRIMARY}, stop:1 {Colors.ACCENT});
    border-radius: {BorderRadius.SM};
}}

/* 表格 */
QTableWidget, QTableView {{
    background-color: transparent;
    border: none;
    gridline-color: {Colors.BORDER_DARK};
    selection-background-color: {Colors.PRIMARY}22;
}}

QTableWidget::item, QTableView::item {{
    padding: 12px;
    border-bottom: 1px solid {Colors.BORDER_DARK};
}}

QTableWidget::item:selected, QTableView::item:selected {{
    background-color: {Colors.PRIMARY}33;
    color: {Colors.TEXT_PRIMARY};
}}

QHeaderView::section {{
    background-color: {Colors.BG_SECONDARY};
    color: {Colors.TEXT_MUTED};
    padding: 12px;
    border: none;
    border-bottom: 1px solid {Colors.BORDER_PRIMARY};
    font-weight: 600;
}}

/* 列表 */
QListWidget {{
    background-color: transparent;
    border: none;
    outline: none;
}}

QListWidget::item {{
    padding: 12px;
    border-radius: {BorderRadius.MD};
    margin: 2px 0;
}}

QListWidget::item:selected {{
    background-color: {Colors.PRIMARY}33;
    color: {Colors.PRIMARY};
}}

QListWidget::item:hover {{
    background-color: {Colors.BG_HOVER};
}}

/* 标签页 */
QTabWidget::pane {{
    background-color: {Colors.BG_TERTIARY};
    border: 1px solid {Colors.BORDER_PRIMARY};
    border-radius: {BorderRadius.LG};
    margin-top: -1px;
}}

QTabBar::tab {{
    background-color: transparent;
    color: {Colors.TEXT_MUTED};
    padding: 12px 24px;
    border: none;
    border-bottom: 2px solid transparent;
    font-weight: 500;
}}

QTabBar::tab:selected {{
    color: {Colors.PRIMARY};
    border-bottom-color: {Colors.PRIMARY};
}}

QTabBar::tab:hover:!selected {{
    color: {Colors.TEXT_SECONDARY};
}}

/* 分组框 */
QGroupBox {{
    background-color: {Colors.BG_TERTIARY};
    border: 1px solid {Colors.BORDER_PRIMARY};
    border-radius: {BorderRadius.LG};
    margin-top: 16px;
    padding-top: 16px;
    font-weight: 600;
    color: {Colors.TEXT_PRIMARY};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px;
    background-color: {Colors.BG_TERTIARY};
}}

/* 分割线 */
QSplitter::handle {{
    background-color: {Colors.BORDER_PRIMARY};
}}

QSplitter::handle:horizontal {{
    width: 1px;
}}

QSplitter::handle:vertical {{
    height: 1px;
}}
"""


# 按钮样式
class ButtonStyles:
    """按钮样式"""
    
    PRIMARY = f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {Colors.PRIMARY}, stop:1 {Colors.ACCENT});
            color: {Colors.TEXT_PRIMARY};
            border: none;
            border-radius: {BorderRadius.MD};
            padding: 12px 24px;
            font-weight: 600;
            font-size: {Typography.SIZE_BASE};
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {Colors.PRIMARY_LIGHT}, stop:1 {Colors.ACCENT_LIGHT});
        }}
        QPushButton:pressed {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {Colors.PRIMARY_DARK}, stop:1 {Colors.ACCENT_DARK});
        }}
        QPushButton:disabled {{
            background-color: {Colors.BORDER_PRIMARY};
            color: {Colors.TEXT_DISABLED};
        }}
    """
    
    SECONDARY = f"""
        QPushButton {{
            background-color: {Colors.BG_TERTIARY};
            color: {Colors.TEXT_SECONDARY};
            border: 1px solid {Colors.BORDER_PRIMARY};
            border-radius: {BorderRadius.MD};
            padding: 12px 24px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {Colors.BG_HOVER};
            border-color: {Colors.BORDER_LIGHT};
        }}
        QPushButton:pressed {{
            background-color: {Colors.BG_SECONDARY};
        }}
    """
    
    GHOST = f"""
        QPushButton {{
            background-color: transparent;
            color: {Colors.PRIMARY};
            border: 1px solid {Colors.PRIMARY};
            border-radius: {BorderRadius.MD};
            padding: 12px 24px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {Colors.PRIMARY}22;
        }}
        QPushButton:pressed {{
            background-color: {Colors.PRIMARY}33;
        }}
    """
    
    SUCCESS = f"""
        QPushButton {{
            background-color: {Colors.SUCCESS};
            color: {Colors.BG_DARK};
            border: none;
            border-radius: {BorderRadius.MD};
            padding: 12px 24px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {Colors.SUCCESS_DARK};
            color: {Colors.TEXT_PRIMARY};
        }}
    """
    
    DANGER = f"""
        QPushButton {{
            background-color: {Colors.ERROR};
            color: {Colors.TEXT_PRIMARY};
            border: none;
            border-radius: {BorderRadius.MD};
            padding: 12px 24px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {Colors.ERROR_DARK};
        }}
    """
    
    ICON = f"""
        QPushButton {{
            background-color: transparent;
            color: {Colors.TEXT_MUTED};
            border: none;
            border-radius: {BorderRadius.MD};
            padding: 8px;
        }}
        QPushButton:hover {{
            background-color: {Colors.BG_HOVER};
            color: {Colors.TEXT_SECONDARY};
        }}
    """


# 卡片样式
class CardStyles:
    """卡片样式"""
    
    DEFAULT = f"""
        QFrame {{
            background-color: {Colors.BG_TERTIARY};
            border: 1px solid {Colors.BORDER_PRIMARY};
            border-radius: {BorderRadius.LG};
        }}
    """
    
    ELEVATED = f"""
        QFrame {{
            background-color: {Colors.BG_CARD};
            border: 1px solid {Colors.BORDER_PRIMARY};
            border-radius: {BorderRadius.LG};
        }}
    """
    
    GRADIENT = f"""
        QFrame {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {Colors.BG_TERTIARY}, stop:1 {Colors.BG_SECONDARY});
            border: 1px solid {Colors.BORDER_PRIMARY};
            border-radius: {BorderRadius.LG};
        }}
    """
    
    HIGHLIGHT = f"""
        QFrame {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {Colors.PRIMARY}22, stop:1 {Colors.ACCENT}11);
            border: 1px solid {Colors.PRIMARY}55;
            border-radius: {BorderRadius.LG};
        }}
    """


# 标签样式
class LabelStyles:
    """标签样式"""
    
    TITLE = f"""
        QLabel {{
            font-size: {Typography.SIZE_2XL};
            font-weight: 700;
            color: {Colors.TEXT_PRIMARY};
        }}
    """
    
    SUBTITLE = f"""
        QLabel {{
            font-size: {Typography.SIZE_LG};
            font-weight: 600;
            color: {Colors.TEXT_PRIMARY};
        }}
    """
    
    BODY = f"""
        QLabel {{
            font-size: {Typography.SIZE_BASE};
            color: {Colors.TEXT_SECONDARY};
        }}
    """
    
    CAPTION = f"""
        QLabel {{
            font-size: {Typography.SIZE_SM};
            color: {Colors.TEXT_MUTED};
        }}
    """
    
    SUCCESS = f"""
        QLabel {{
            color: {Colors.SUCCESS};
            font-weight: 500;
        }}
    """
    
    ERROR = f"""
        QLabel {{
            color: {Colors.ERROR};
            font-weight: 500;
        }}
    """
    
    WARNING = f"""
        QLabel {{
            color: {Colors.WARNING};
            font-weight: 500;
        }}
    """


# 徽章样式
class BadgeStyles:
    """徽章样式"""
    
    @staticmethod
    def get_style(color: str, bg_alpha: str = "33") -> str:
        return f"""
            QLabel {{
                background-color: {color}{bg_alpha};
                color: {color};
                border-radius: {BorderRadius.FULL};
                padding: 4px 12px;
                font-size: {Typography.SIZE_SM};
                font-weight: 600;
            }}
        """
    
    PRIMARY = get_style.__func__(Colors.PRIMARY)
    SUCCESS = get_style.__func__(Colors.SUCCESS)
    WARNING = get_style.__func__(Colors.WARNING)
    ERROR = get_style.__func__(Colors.ERROR)
    INFO = get_style.__func__(Colors.INFO)


def apply_theme(app):
    """应用主题到应用程序"""
    app.setStyleSheet(GLOBAL_STYLE)
