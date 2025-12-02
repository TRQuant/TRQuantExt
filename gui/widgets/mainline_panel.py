# -*- coding: utf-8 -*-
"""
板块主线量化选股系统
====================

完整实现A股板块主线量化选股方法论，包含7大核心模块：
1. 方法论介绍 - 完整流程说明
2. 主线识别 - 市场扫描与板块发现
3. 热度评分 - 板块量化评分与轮动
4. 个股筛选 - 多维打分选股
5. 调研笔记 - 行业调研与社交信息记录
6. 回测验证 - 策略历史回测
7. 实时监控 - 风控与预警

数据源：AKShare（免费）+ JQData（主力）+ Wind（扩展）
回测平台：PTrade + QMT + 聚宽
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QScrollArea, QTabWidget, QLineEdit,
    QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QProgressBar, QGroupBox, QSlider, QDateEdit, QMessageBox,
    QFileDialog, QPlainTextEdit, QApplication
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QTimer, QDate, QThread
from PyQt6.QtGui import QFont, QDesktopServices, QColor
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging

from gui.styles.theme import Colors

logger = logging.getLogger(__name__)


class ForesightAnalysisWorker(QThread):
    """前瞻性分析工作线程 - 异步执行，不阻塞UI"""
    
    finished = pyqtSignal(dict)  # 分析完成信号
    progress = pyqtSignal(str)   # 进度更新信号
    error = pyqtSignal(str)      # 错误信号
    
    def run(self):
        """在后台线程中执行分析"""
        try:
            from markets.ashare.mainline.real_data_fetcher import real_data_fetcher
            from markets.ashare.mainline.cursor_analyzer import cursor_analyzer
            from datetime import datetime
            
            # 第一步：获取真实数据
            self.progress.emit("📡 正在获取真实市场数据...")
            all_data = real_data_fetcher.fetch_all_data()
            
            # 统计数据获取情况
            success_count = sum(1 for r in all_data.values() if r.success)
            total_count = len(all_data)
            
            # 第二步：生成Cursor分析Prompt
            self.progress.emit("🤖 正在生成分析Prompt...")
            analysis_result = cursor_analyzer.run_analysis()
            
            # 返回结果
            self.finished.emit({
                "success": True,
                "all_data": all_data,
                "success_count": success_count,
                "total_count": total_count,
                "analysis_result": analysis_result,
                "prompt": analysis_result["prompt"],
                "time": datetime.now().strftime('%H:%M:%S'),
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))


class MainlinePanel(QWidget):
    """板块主线量化选股面板"""
    
    # 信号
    generate_strategy = pyqtSignal(dict)  # 生成策略信号
    run_backtest = pyqtSignal(dict)  # 运行回测信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_manager = None
        self.research_notes = []  # 调研笔记
        self.watchlist = []  # 观察池
        self.setup_ui()
        self._init_data_manager()
    
    def _init_data_manager(self):
        """初始化数据源管理器"""
        try:
            from data_sources import DataSourceManager
            self.data_manager = DataSourceManager(use_cache=True)
            self.data_manager.connect_source('akshare')
            logger.info("主线面板数据源初始化成功")
        except Exception as e:
            logger.error(f"数据源初始化失败: {e}")
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tab控件直接在最上面
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {Colors.BG_SECONDARY};
            }}
            QTabBar::tab {{
                background-color: {Colors.BG_PRIMARY};
                color: {Colors.TEXT_MUTED};
                border: none;
                padding: 12px 20px;
                font-size: 13px;
                font-weight: 600;
                min-width: 80px;
            }}
            QTabBar::tab:selected {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.MODULE_MAINLINE_START};
                border-bottom: 3px solid {Colors.MODULE_MAINLINE_START};
            }}
            QTabBar {{
                background-color: {Colors.BG_PRIMARY};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        
        # 添加核心Tab - 基于五维评分系统设计方案
        self.tab_widget.addTab(self._create_methodology_tab(), "📖 方法论")
        self.tab_widget.addTab(self._create_identification_tab(), "🔍 主线识别")
        
        # 五维评分独立Tab
        self.tab_widget.addTab(self._create_funds_tab(), "💰 资金")
        self.tab_widget.addTab(self._create_heatmap_tab(), "🔥 热度")  # 复用现有热度面板
        self.tab_widget.addTab(self._create_momentum_tab(), "📈 动量")
        self.tab_widget.addTab(self._create_policy_tab(), "📜 政策")
        self.tab_widget.addTab(self._create_leader_tab(), "👑 龙头")
        self.tab_widget.addTab(self._create_composite_tab(), "🎯 综合评分")  # 专业投资主线
        self.tab_widget.addTab(self._create_history_tab(), "📅 历史查询")  # 时间维度历史
        # 候选池已在侧边栏独立模块，此处不再重复
        
        self.tab_widget.addTab(self._create_research_tab(), "📋 调研笔记")
        self.tab_widget.addTab(self._create_backtest_tab(), "📈 回测验证")
        self.tab_widget.addTab(self._create_monitoring_tab(), "⚡ 实时监控")
        
        layout.addWidget(self.tab_widget)
    
    # ================================================================
    # Tab 1: 方法论介绍
    # ================================================================
    def _create_methodology_tab(self) -> QWidget:
        """创建方法论介绍Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {Colors.BG_SECONDARY};
            }}
        """)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 24, 32, 24)
        content_layout.setSpacing(24)
        
        # Hero区域
        hero = self._create_methodology_hero()
        content_layout.addWidget(hero)
        
        # 流程图
        flow_chart = self._create_flow_chart()
        content_layout.addWidget(flow_chart)
        
        # 7大模块详细说明
        modules = self._create_modules_detail()
        content_layout.addWidget(modules)
        
        # 核心指标说明
        indicators = self._create_indicators_section()
        content_layout.addWidget(indicators)
        
        # 数据源说明
        datasources = self._create_datasource_section()
        content_layout.addWidget(datasources)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return widget
    
    def _create_methodology_hero(self) -> QFrame:
        """创建方法论Hero区域"""
        hero = QFrame()
        hero.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1E3A5F,
                    stop:1 #0F2744
                );
                border-radius: 16px;
                border: 1px solid {Colors.PRIMARY}40;
            }}
        """)
        
        layout = QHBoxLayout(hero)
        layout.setContentsMargins(32, 28, 32, 28)
        
        # 左侧文字
        text_layout = QVBoxLayout()
        text_layout.setSpacing(12)
        
        title = QLabel("📊 A股板块主线量化选股方法论")
        title.setStyleSheet(f"""
            font-size: 24px;
            font-weight: 800;
            color: {Colors.TEXT_PRIMARY};
        """)
        text_layout.addWidget(title)
        
        subtitle = QLabel(
            "从「板块识别」到「选股调研」再到「回测跟踪」的完整闭环方法\n"
            "系统性扫描市场板块，捕捉当前市场主线，量化衡量板块强度与资金集中度"
        )
        subtitle.setStyleSheet(f"""
            font-size: 13px;
            color: {Colors.TEXT_MUTED};
            line-height: 1.6;
        """)
        subtitle.setWordWrap(True)
        text_layout.addWidget(subtitle)
        
        # 特点标签
        tags_layout = QHBoxLayout()
        tags_layout.setSpacing(10)
        
        tags = [
            ("🎯", "可实战部署", "#10B981"),
            ("📊", "模型可解释", "#3B82F6"),
            ("🔄", "闭环验证", "#F59E0B"),
            ("⚡", "实时跟踪", "#EC4899"),
        ]
        
        for icon, text, color in tags:
            tag = QLabel(f"{icon} {text}")
            # 使用实心彩色背景 + 深色文字，确保高对比度
            tag.setStyleSheet(f"""
                font-size: 11px;
                font-weight: 600;
                color: #0d0d14;
                background-color: {color};
                padding: 6px 12px;
                border-radius: 14px;
            """)
            tags_layout.addWidget(tag)
        
        tags_layout.addStretch()
        text_layout.addLayout(tags_layout)
        
        layout.addLayout(text_layout, 3)
        
        # 右侧统计
        stats_frame = QFrame()
        stats_frame.setFixedWidth(200)
        stats_frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(0, 0, 0, 0.3);
                border-radius: 12px;
            }}
        """)
        stats_layout = QVBoxLayout(stats_frame)
        stats_layout.setContentsMargins(20, 16, 20, 16)
        stats_layout.setSpacing(12)
        
        stats = [
            ("7", "核心模块"),
            ("15+", "量化指标"),
            ("3", "数据源支持"),
            ("3", "回测平台"),
        ]
        
        for value, label in stats:
            stat_row = QHBoxLayout()
            val_label = QLabel(value)
            val_label.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {Colors.PRIMARY};")
            stat_row.addWidget(val_label)
            
            desc_label = QLabel(label)
            desc_label.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED};")
            stat_row.addWidget(desc_label)
            stat_row.addStretch()
            
            stats_layout.addLayout(stat_row)
        
        layout.addWidget(stats_frame, 1)
        
        return hero
    
    def _create_flow_chart(self) -> QFrame:
        """创建流程图"""
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
        
        title = QLabel("⚙️ 完整工作流程")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)
        
        # 流程图（横向）- 修正流程：五维量化→综合评分→主线→候选池→因子→策略
        flow_layout = QHBoxLayout()
        flow_layout.setSpacing(6)
        
        # 正确的工作流程
        steps = [
            ("1", "五维量化", "#3B82F6", "资金/热度/动量/政策/龙头"),
            ("2", "综合评分", "#10B981", "权重加权"),
            ("3", "主线识别", "#F59E0B", "输出主线"),
            ("4", "候选池", "#EC4899", "股票+ETF"),
            ("5", "因子开发", "#8B5CF6", "多因子评分"),
            ("6", "策略回测", "#06B6D4", "验证执行"),
        ]
        
        for i, (num, name, color, desc) in enumerate(steps):
            # 步骤卡片 - 增大尺寸确保文字不溢出
            step_frame = QFrame()
            step_frame.setFixedSize(120, 90)
            step_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.BG_PRIMARY};
                    border: 2px solid {color}50;
                    border-radius: 10px;
                }}
                QFrame:hover {{
                    border: 2px solid {color};
                    background-color: {color}15;
                }}
            """)
            step_frame.setCursor(Qt.CursorShape.PointingHandCursor)
            
            step_layout = QVBoxLayout(step_frame)
            step_layout.setContentsMargins(8, 8, 8, 8)
            step_layout.setSpacing(4)
            
            # 序号
            num_label = QLabel(num)
            num_label.setStyleSheet(f"""
                font-size: 11px;
                font-weight: 700;
                color: #0d0d14;
                background-color: {color};
                padding: 2px 6px;
                border-radius: 8px;
            """)
            num_label.setFixedSize(20, 20)
            num_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            step_layout.addWidget(num_label, alignment=Qt.AlignmentFlag.AlignLeft)
            
            # 名称 - 单行
            name_label = QLabel(name)
            name_label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: #ffffff;")
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            step_layout.addWidget(name_label)
            
            # 描述 - 单行
            desc_label = QLabel(desc)
            desc_label.setStyleSheet(f"font-size: 10px; color: #cdd6f4;")
            desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            step_layout.addWidget(desc_label)
            
            flow_layout.addWidget(step_frame)
            
            # 箭头
            if i < len(steps) - 1:
                arrow = QLabel("→")
                arrow.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {Colors.TEXT_SECONDARY};")
                flow_layout.addWidget(arrow)
        
        flow_layout.addStretch()
        layout.addLayout(flow_layout)
        
        return frame
    
    def _create_modules_detail(self) -> QFrame:
        """创建模块详细说明"""
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
        
        title = QLabel("📚 七大核心模块详解")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)
        
        modules = [
            {
                "name": "1. 市场主线识别",
                "icon": "🔍",
                "color": "#3B82F6",
                "desc": "定期扫描所有行业和主题板块表现，通过涨跌幅榜、成交占比、资金净流入、涨停热度等指标发现当下市场主线。",
                "indicators": ["阶段涨幅（5日/20日）", "成交额占比", "主力资金净流入", "涨停家数占比"]
            },
            {
                "name": "2. 板块热度评分",
                "icon": "📊",
                "color": "#10B981",
                "desc": "构建板块热度评分机制，综合资金维度(40%)、价格维度(30%)、情绪维度(30%)进行量化打分。",
                "indicators": ["成交额占比", "主力净流入", "超额收益", "换手率", "龙虎榜机构买入"]
            },
            {
                "name": "3. 个股多维打分",
                "icon": "🎯",
                "color": "#F59E0B",
                "desc": "从主线板块中筛选优质个股，通过技术面(30%)、资金面(30%)、基本面(40%)综合打分挑选龙头标的。",
                "indicators": ["均线强度", "量价配合", "主力净流入", "ROE", "营收增速", "估值分位"]
            },
            {
                "name": "4. 定性调研验证",
                "icon": "📋",
                "color": "#EC4899",
                "desc": "对候选股票进行深入定性研究，包括公告研读、券商研报、机构持仓变动、行业调研、社交信息等。",
                "indicators": ["公司公告", "券商研报", "基金持仓", "机构调研", "行业调研笔记", "社交信息线索"]
            },
            {
                "name": "5. 历史回测验证",
                "icon": "📈",
                "color": "#8B5CF6",
                "desc": "对策略进行历史数据回测，计算年化收益、最大回撤、夏普比率等指标，验证选股逻辑有效性。",
                "indicators": ["年化收益率", "最大回撤", "夏普比率", "胜率", "超额收益"]
            },
            {
                "name": "6. 实时跟踪风控",
                "icon": "⚡",
                "color": "#06B6D4",
                "desc": "建立实时监控系统，跟踪主线切换、个股表现、风险触发，实现及时调仓和风险控制。",
                "indicators": ["主线轮动信号", "止损预警", "仓位建议", "风险评估"]
            },
            {
                "name": "7. 数据源集成",
                "icon": "🔌",
                "color": "#F97316",
                "desc": "整合AKShare、JQData、Wind等数据源，实现板块数据、资金流向、行情数据、基本面数据的统一获取。",
                "indicators": ["AKShare（免费）", "JQData（主力）", "Wind（扩展）", "MongoDB缓存"]
            },
        ]
        
        grid = QGridLayout()
        grid.setSpacing(12)
        
        for i, module in enumerate(modules):
            card = self._create_module_card(module)
            grid.addWidget(card, i // 2, i % 2)
        
        layout.addLayout(grid)
        
        return frame
    
    def _create_module_card(self, module: dict) -> QFrame:
        """创建模块卡片"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-left: 4px solid {module['color']};
                border-radius: 8px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        
        # 标题
        title_layout = QHBoxLayout()
        icon = QLabel(module['icon'])
        icon.setStyleSheet("font-size: 18px;")
        title_layout.addWidget(icon)
        
        name = QLabel(module['name'])
        name.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        title_layout.addWidget(name)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # 描述
        desc = QLabel(module['desc'])
        desc.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED}; line-height: 1.4;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # 指标标签 - 使用深色背景配亮色文字确保可读性
        tags_layout = QHBoxLayout()
        tags_layout.setSpacing(4)
        for indicator in module['indicators'][:4]:
            tag = QLabel(indicator)
            tag.setStyleSheet(f"""
                font-size: 9px;
                color: {Colors.TEXT_SECONDARY};
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {module['color']}50;
                padding: 2px 6px;
                border-radius: 4px;
            """)
            tags_layout.addWidget(tag)
        tags_layout.addStretch()
        layout.addLayout(tags_layout)
        
        return card
    
    def _create_indicators_section(self) -> QFrame:
        """创建核心指标说明"""
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
        
        title = QLabel("📐 核心指标公式")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)
        
        # 指标表格
        indicators = [
            ("板块热度得分", "40%×资金指标 + 30%×价格指标 + 30%×情绪指标", "综合衡量板块强度"),
            ("成交占比", "板块成交额 / 全市场成交额", "资金集中度"),
            ("超额收益", "板块涨幅 - 沪深300涨幅", "相对强度"),
            ("个股综合分", "30%×技术分 + 30%×资金分 + 40%×基本面分", "选股排序依据"),
            ("均线强度", "(收盘价 - MA20) / MA20", "趋势强度"),
            ("估值分位", "当前PE / 历史PE分布", "估值水平"),
        ]
        
        table = QTableWidget()
        table.setRowCount(len(indicators))
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["指标名称", "计算公式", "说明"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                gridline-color: {Colors.BORDER_PRIMARY};
            }}
            QTableWidget::item {{
                padding: 8px;
                color: {Colors.TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_MUTED};
                padding: 8px;
                border: none;
                font-weight: 600;
            }}
        """)
        table.setFixedHeight(220)
        
        for i, (name, formula, desc) in enumerate(indicators):
            table.setItem(i, 0, QTableWidgetItem(name))
            table.setItem(i, 1, QTableWidgetItem(formula))
            table.setItem(i, 2, QTableWidgetItem(desc))
        
        layout.addWidget(table)
        
        return frame
    
    def _create_datasource_section(self) -> QFrame:
        """创建数据源说明"""
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
        
        title = QLabel("🔌 数据源与回测平台")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)
        
        # 数据源卡片
        sources_layout = QHBoxLayout()
        sources_layout.setSpacing(16)
        
        sources = [
            ("AKShare", "免费开源", "板块数据、资金流向、行情数据", "#10B981", "当前使用"),
            ("JQData", "专业数据", "全量A股数据、因子数据、Level2", "#3B82F6", "计划购买"),
            ("Wind", "机构级", "全球市场、另类数据、深度研报", "#F59E0B", "未来扩展"),
        ]
        
        for name, type_, features, color, status in sources:
            card = QFrame()
            card.setFixedWidth(200)
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.BG_PRIMARY};
                    border: 1px solid {color}40;
                    border-radius: 10px;
                }}
            """)
            
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_layout.setSpacing(6)
            
            header = QHBoxLayout()
            name_label = QLabel(name)
            name_label.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
            header.addWidget(name_label)
            
            status_label = QLabel(status)
            status_label.setStyleSheet(f"""
                font-size: 9px;
                color: {color};
                background-color: {color}20;
                padding: 2px 6px;
                border-radius: 8px;
            """)
            header.addWidget(status_label)
            header.addStretch()
            card_layout.addLayout(header)
            
            type_label = QLabel(type_)
            type_label.setStyleSheet(f"font-size: 11px; color: {color};")
            card_layout.addWidget(type_label)
            
            features_label = QLabel(features)
            features_label.setStyleSheet(f"font-size: 10px; color: {Colors.TEXT_MUTED};")
            features_label.setWordWrap(True)
            card_layout.addWidget(features_label)
            
            sources_layout.addWidget(card)
        
        sources_layout.addStretch()
        layout.addLayout(sources_layout)
        
        # 回测平台
        backtest_title = QLabel("📈 回测平台集成")
        backtest_title.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {Colors.TEXT_PRIMARY}; margin-top: 12px;")
        layout.addWidget(backtest_title)
        
        platforms_layout = QHBoxLayout()
        platforms = [
            ("PTrade", "国金证券", "实盘交易", "#EC4899"),
            ("QMT", "迅投QMT", "程序化交易", "#8B5CF6"),
            ("聚宽", "JoinQuant", "云端回测", "#06B6D4"),
        ]
        
        for name, provider, feature, color in platforms:
            badge = QLabel(f"{name} ({provider}) - {feature}")
            badge.setStyleSheet(f"""
                font-size: 11px;
                color: {color};
                background-color: {color}15;
                padding: 6px 12px;
                border-radius: 6px;
                border: 1px solid {color}30;
            """)
            platforms_layout.addWidget(badge)
        
        platforms_layout.addStretch()
        layout.addLayout(platforms_layout)
        
        return frame
    
    # ================================================================
    # Tab 2: 主线识别（前瞻性分析）
    # ================================================================
    def _create_identification_tab(self) -> QWidget:
        """创建主线识别Tab - 包含前瞻性分析"""
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {Colors.BG_SECONDARY}; }}")
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # 顶部说明 - 强调前瞻性
        intro_frame = QFrame()
        intro_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1E3A5F, stop:1 #0F2744);
                border-radius: 12px;
                border: 1px solid {Colors.PRIMARY}40;
            }}
        """)
        intro_layout = QVBoxLayout(intro_frame)
        intro_layout.setContentsMargins(20, 16, 20, 16)
        intro_layout.setSpacing(8)
        
        intro_title = QLabel("🔮 前瞻性主线识别")
        intro_title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: #ffffff;")
        intro_layout.addWidget(intro_title)
        
        intro_desc = QLabel(
            "三层分析框架：宏观前瞻（6-12月）→ 中观验证（1-3月）→ 微观确认（1-4周）\n"
            "不仅识别当下热点，更要预判未来趋势，提前布局而非追涨杀跌"
        )
        intro_desc.setStyleSheet(f"font-size: 12px; color: #cdd6f4; line-height: 1.5;")
        intro_layout.addWidget(intro_desc)
        
        layout.addWidget(intro_frame)
        
        # 操作区
        action_layout = QHBoxLayout()
        
        # 前瞻性分析按钮
        foresight_btn = QPushButton("🔮 前瞻性分析")
        foresight_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #8B5CF6;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: #7C3AED; }}
        """)
        foresight_btn.clicked.connect(self._run_foresight_analysis)
        action_layout.addWidget(foresight_btn)
        
        scan_btn = QPushButton("🔍 扫描板块")
        scan_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Colors.PRIMARY}DD; }}
        """)
        scan_btn.clicked.connect(self._scan_sectors)
        action_layout.addWidget(scan_btn)
        
        # 板块类型选择
        self.sector_type_combo = QComboBox()
        self.sector_type_combo.addItems(["申万行业", "同花顺概念", "东财板块"])
        self.sector_type_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 100px;
            }}
        """)
        action_layout.addWidget(self.sector_type_combo)
        
        action_layout.addStretch()
        
        self.update_time_label = QLabel("最后更新: --")
        self.update_time_label.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED};")
        action_layout.addWidget(self.update_time_label)
        
        layout.addLayout(action_layout)
        
        # ============ 前瞻性分析结果区 ============
        foresight_frame = QFrame()
        foresight_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid #8B5CF640;
                border-radius: 12px;
            }}
        """)
        foresight_layout = QVBoxLayout(foresight_frame)
        foresight_layout.setContentsMargins(20, 16, 20, 16)
        foresight_layout.setSpacing(12)
        
        foresight_title = QLabel("🔮 前瞻性分析结果")
        foresight_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: #ffffff;")
        foresight_layout.addWidget(foresight_title)
        
        # 三层分析展示
        layers_layout = QHBoxLayout()
        layers_layout.setSpacing(12)
        
        # 宏观前瞻
        macro_card = self._create_analysis_layer_card(
            "📋 宏观前瞻", "6-12个月", "#3B82F6",
            ["政策周期", "经济周期", "产业趋势"]
        )
        layers_layout.addWidget(macro_card)
        
        # 中观验证
        meso_card = self._create_analysis_layer_card(
            "📊 中观验证", "1-3个月", "#10B981",
            ["行业景气", "资金流向", "催化剂"]
        )
        layers_layout.addWidget(meso_card)
        
        # 微观确认
        micro_card = self._create_analysis_layer_card(
            "🎯 微观确认", "1-4周", "#F59E0B",
            ["技术形态", "龙头表现", "市场情绪"]
        )
        layers_layout.addWidget(micro_card)
        
        foresight_layout.addLayout(layers_layout)
        
        # 分析结果文本
        self.foresight_result = QLabel("点击「前瞻性分析」开始三层分析...")
        self.foresight_result.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_SECONDARY}; line-height: 1.6;")
        self.foresight_result.setWordWrap(True)
        foresight_layout.addWidget(self.foresight_result)
        
        layout.addWidget(foresight_frame)
        
        # ============ 发现的主线列表 ============
        mainline_title = QLabel("🔥 发现的投资主线")
        mainline_title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(mainline_title)
        
        self.mainline_cards_layout = QVBoxLayout()
        self.mainline_cards_layout.setSpacing(12)
        
        # 初始占位
        placeholder = QLabel("运行前瞻性分析后，这里将显示识别到的投资主线...")
        placeholder.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_MUTED}; padding: 20px;")
        self.mainline_cards_layout.addWidget(placeholder)
        
        layout.addLayout(self.mainline_cards_layout)
        
        # ============ 板块排名表格 ============
        table_title = QLabel("📈 板块排名")
        table_title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(table_title)
        
        self.sector_table = QTableWidget()
        self.sector_table.setColumnCount(8)
        self.sector_table.setHorizontalHeaderLabels([
            "排名", "板块名称", "涨跌幅", "成交占比", "资金净流入", "涨停数", "热度分", "操作"
        ])
        self.sector_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.sector_table.setMaximumHeight(300)
        self.sector_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                gridline-color: {Colors.BORDER_PRIMARY};
            }}
            QTableWidget::item {{
                padding: 8px;
                color: {Colors.TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {Colors.BG_PRIMARY};
                color: {Colors.TEXT_SECONDARY};
                padding: 10px;
                border: none;
                font-weight: 600;
            }}
        """)
        layout.addWidget(self.sector_table)
        
        layout.addStretch()
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        
        return widget
    
    def _create_analysis_layer_card(self, title: str, period: str, color: str, items: list) -> QFrame:
        """创建分析层级卡片"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {color}40;
                border-left: 4px solid {color};
                border-radius: 8px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 13px; font-weight: 700; color: #ffffff;")
        layout.addWidget(title_label)
        
        # 周期
        period_label = QLabel(period)
        period_label.setStyleSheet(f"font-size: 10px; color: {color};")
        layout.addWidget(period_label)
        
        # 分析项
        for item in items:
            item_label = QLabel(f"• {item}")
            item_label.setStyleSheet(f"font-size: 10px; color: {Colors.TEXT_SECONDARY};")
            layout.addWidget(item_label)
        
        return card
    
    def _run_foresight_analysis(self):
        """运行前瞻性分析 - 异步执行，不阻塞UI"""
        # 检查是否已有分析在运行
        if hasattr(self, '_foresight_worker') and self._foresight_worker and self._foresight_worker.isRunning():
            self.foresight_result.setText("⚠️ 分析正在进行中，请稍候...")
            return
        
        # 禁用按钮，显示进度
        self.foresight_result.setText("📡 正在获取真实市场数据...\n\n💡 提示：分析在后台运行，您可以继续使用其他功能")
        
        # 创建并启动工作线程
        self._foresight_worker = ForesightAnalysisWorker()
        self._foresight_worker.progress.connect(self._on_foresight_progress)
        self._foresight_worker.finished.connect(self._on_foresight_finished)
        self._foresight_worker.error.connect(self._on_foresight_error)
        self._foresight_worker.start()
    
    def _on_foresight_progress(self, message: str):
        """前瞻分析进度更新"""
        self.foresight_result.setText(f"{message}\n\n💡 提示：分析在后台运行，您可以继续使用其他功能")
    
    def _on_foresight_finished(self, result: dict):
        """前瞻分析完成"""
        from datetime import datetime
        
        all_data = result["all_data"]
        success_count = result["success_count"]
        total_count = result["total_count"]
        analysis_result = result["analysis_result"]
        prompt = result["prompt"]
        
        # 构建结果展示
        result_text = (
            f"<b>📊 真实数据获取完成</b><br>"
            f"• 数据源: {success_count}/{total_count} 成功<br>"
            f"• 数据时间: {result['time']}<br><br>"
            f"<b>📡 数据来源</b><br>"
        )
        
        for key, data_result in all_data.items():
            status = "✅" if data_result.success else "❌"
            source = data_result.source
            result_text += f"{status} {key}: {source}<br>"
        
        result_text += f"<br><b>🤖 Cursor分析Prompt已生成</b><br>"
        result_text += f"• 文件: {analysis_result['file_path']}<br>"
        result_text += f"• 点击下方按钮复制Prompt到Cursor进行AI分析<br>"
        
        self.foresight_result.setText(result_text)
        self.foresight_result.setTextFormat(Qt.TextFormat.RichText)
        
        # 保存prompt供后续使用
        self._current_prompt = prompt
        self._current_analysis_result = analysis_result
        
        # 清空并更新主线卡片区域 - 显示数据摘要
        while self.mainline_cards_layout.count():
            item = self.mainline_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 添加数据摘要卡片
        self._add_data_summary_cards(all_data)
        
        # 添加Cursor分析按钮
        self._add_cursor_action_buttons(prompt, analysis_result)
        
        # 更新时间
        self.update_time_label.setText(f"最后更新: {datetime.now().strftime('%H:%M:%S')}")
    
    def _on_foresight_error(self, error: str):
        """前瞻分析错误"""
        self.foresight_result.setText(f"❌ 分析失败: {error}\n\n请检查网络连接后重试")
    
    def _add_data_summary_cards(self, all_data):
        """添加数据摘要卡片"""
        # 板块资金流向卡片
        sector_flow = all_data.get("sector_flow")
        if sector_flow and sector_flow.success and sector_flow.data:
            card = self._create_data_card(
                "📈 板块资金流向",
                sector_flow.source,
                self._format_sector_flow(sector_flow.data[:5])
            )
            self.mainline_cards_layout.addWidget(card)
        
        # 市场情绪卡片
        sentiment = all_data.get("market_sentiment")
        if sentiment and sentiment.success and sentiment.data:
            card = self._create_data_card(
                "🎭 市场情绪",
                sentiment.source,
                f"涨停: {sentiment.data.get('up_limit_count', 0)} | "
                f"跌停: {sentiment.data.get('down_limit_count', 0)} | "
                f"情绪分: {sentiment.data.get('sentiment_score', 50)}"
            )
            self.mainline_cards_layout.addWidget(card)
        
        # 北向资金卡片
        north = all_data.get("northbound_flow")
        if north and north.success and north.data:
            card = self._create_data_card(
                "💰 北向资金",
                north.source,
                f"今日: {north.data.get('today_net', 0):.2f}亿 | "
                f"本周: {north.data.get('week_net', 0):.2f}亿 | "
                f"本月: {north.data.get('month_net', 0):.2f}亿"
            )
            self.mainline_cards_layout.addWidget(card)
    
    def _format_sector_flow(self, data) -> str:
        """格式化板块资金流向"""
        lines = []
        for item in data:
            lines.append(
                f"{item['sector_name']}: {item['change_pct']:.2f}%, "
                f"主力净流入 {item['main_net_inflow']:.2f}亿"
            )
        return "\n".join(lines)
    
    def _create_data_card(self, title: str, source: str, content: str) -> QFrame:
        """创建数据卡片"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 10px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title_label)
        
        # 数据来源
        source_label = QLabel(f"来源: {source}")
        source_label.setStyleSheet(f"font-size: 10px; color: {Colors.TEXT_MUTED};")
        layout.addWidget(source_label)
        
        # 内容
        content_label = QLabel(content)
        content_label.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_SECONDARY};")
        content_label.setWordWrap(True)
        layout.addWidget(content_label)
        
        return card
    
    def _add_cursor_action_buttons(self, prompt, analysis_result):
        """添加Cursor操作按钮"""
        button_frame = QFrame()
        button_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid #8B5CF640;
                border-radius: 10px;
            }}
        """)
        
        layout = QVBoxLayout(button_frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        
        # 标题
        title = QLabel("🤖 在Cursor中进行AI分析")
        title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: #8B5CF6;")
        layout.addWidget(title)
        
        # 说明
        desc = QLabel(
            "真实数据已准备完毕，点击下方按钮复制分析Prompt到Cursor Chat，\n"
            "使用Claude Opus 4或GPT-4o进行深度分析。"
        )
        desc.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_SECONDARY};")
        layout.addWidget(desc)
        
        # 按钮区
        btn_layout = QHBoxLayout()
        
        # 复制Prompt按钮
        copy_btn = QPushButton("📋 复制分析Prompt")
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #8B5CF6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: #7C3AED; }}
        """)
        copy_btn.clicked.connect(lambda: self._copy_prompt_to_clipboard(prompt))
        btn_layout.addWidget(copy_btn)
        
        # 打开Prompt文件按钮
        open_btn = QPushButton("📁 打开Prompt文件")
        open_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_PRIMARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {Colors.BG_TERTIARY}; }}
        """)
        open_btn.clicked.connect(lambda: self._open_prompt_file(analysis_result["file_path"]))
        btn_layout.addWidget(open_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 使用说明
        instructions = QLabel(
            "使用方法:\n"
            "1. 点击「复制分析Prompt」\n"
            "2. 打开Cursor Chat (Cmd+L)\n"
            "3. 粘贴并发送\n"
            "4. 选择模型: Claude Opus 4 (推荐)"
        )
        instructions.setStyleSheet(f"font-size: 10px; color: {Colors.TEXT_MUTED};")
        layout.addWidget(instructions)
        
        self.mainline_cards_layout.addWidget(button_frame)
    
    def _copy_prompt_to_clipboard(self, prompt):
        """复制Prompt到剪贴板"""
        from PyQt6.QtWidgets import QApplication, QMessageBox
        
        clipboard = QApplication.clipboard()
        clipboard.setText(prompt.prompt)
        
        QMessageBox.information(
            self, 
            "复制成功", 
            "分析Prompt已复制到剪贴板！\n\n"
            "请打开Cursor Chat (Cmd+L)，粘贴并发送。\n"
            "推荐使用Claude Opus 4模型进行分析。"
        )
    
    def _open_prompt_file(self, file_path):
        """打开Prompt文件"""
        import subprocess
        import platform
        
        try:
            if platform.system() == "Darwin":  # macOS
                subprocess.run(["open", file_path])
            elif platform.system() == "Linux":
                subprocess.run(["xdg-open", file_path])
            else:
                subprocess.run(["start", file_path], shell=True)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "打开失败", f"无法打开文件: {e}\n\n文件路径: {file_path}")
    
    def _create_mainline_card(self, mainline) -> QFrame:
        """创建主线卡片（简化版，兼容旧接口）"""
        return self._create_mainline_card_pro(mainline)
    
    def _create_mainline_card_pro(self, mainline) -> QFrame:
        """创建专业版主线卡片 - 展示完整分析过程"""
        # 根据阶段选择颜色
        stage_colors = {
            "emerging": "#8B5CF6",
            "growing": "#10B981",
            "mature": "#F59E0B",
            "declining": "#EF4444",
        }
        color = stage_colors.get(mainline.stage.value, "#3B82F6")
        
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {color}50;
                border-left: 4px solid {color};
                border-radius: 10px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        
        # ===== 标题行 =====
        header = QHBoxLayout()
        
        name = QLabel(f"🔥 {mainline.name}")
        name.setStyleSheet(f"font-size: 16px; font-weight: 700; color: #ffffff;")
        header.addWidget(name)
        
        # 阶段标签
        stage_names = {"emerging": "启动期", "growing": "成长期", "mature": "成熟期", "declining": "衰退期"}
        stage = QLabel(stage_names.get(mainline.stage.value, ""))
        stage.setStyleSheet(f"""
            font-size: 10px; font-weight: 600;
            color: #0d0d14;
            background-color: {color};
            padding: 3px 8px;
            border-radius: 8px;
        """)
        header.addWidget(stage)
        
        # 总分
        total_score = mainline.score.total_score
        score_color = "#10B981" if total_score >= 75 else ("#F59E0B" if total_score >= 60 else "#EF4444")
        score_label = QLabel(f"综合得分: {total_score:.0f}")
        score_label.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {score_color};")
        header.addWidget(score_label)
        
        header.addStretch()
        
        # 投资建议
        rec_text = mainline.score.recommendation[:10] if len(mainline.score.recommendation) > 10 else mainline.score.recommendation
        rec_color = "#10B981" if "推荐" in rec_text else ("#F59E0B" if "中性" in rec_text else "#EF4444")
        rec = QLabel(rec_text)
        rec.setStyleSheet(f"""
            font-size: 11px; font-weight: 600;
            color: #0d0d14;
            background-color: {rec_color};
            padding: 4px 12px;
            border-radius: 8px;
        """)
        header.addWidget(rec)
        
        layout.addLayout(header)
        
        # ===== 核心逻辑 =====
        logic_label = QLabel(f"💡 {mainline.core_logic}")
        logic_label.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_PRIMARY}; font-weight: 500;")
        logic_label.setWordWrap(True)
        layout.addWidget(logic_label)
        
        # ===== 六维评分详情 =====
        dim_frame = QFrame()
        dim_frame.setStyleSheet(f"background-color: {Colors.BG_PRIMARY}; border-radius: 8px;")
        dim_layout = QVBoxLayout(dim_frame)
        dim_layout.setContentsMargins(12, 10, 12, 10)
        dim_layout.setSpacing(6)
        
        dim_title = QLabel("📊 六维度评分详情")
        dim_title.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
        dim_layout.addWidget(dim_title)
        
        # 评分条
        for dim in mainline.score.dimensions:
            dim_row = QHBoxLayout()
            dim_row.setSpacing(8)
            
            # 维度名称
            dim_names = {
                "policy": "政策支持",
                "capital": "资金认可",
                "industry": "产业景气",
                "technical": "技术形态",
                "valuation": "估值合理",
                "foresight": "前瞻领先",
            }
            dim_name = QLabel(dim_names.get(dim.dimension, dim.dimension))
            dim_name.setFixedWidth(60)
            dim_name.setStyleSheet(f"font-size: 10px; color: {Colors.TEXT_SECONDARY};")
            dim_row.addWidget(dim_name)
            
            # 进度条
            progress_bg = QFrame()
            progress_bg.setFixedHeight(8)
            progress_bg.setStyleSheet(f"background-color: {Colors.BG_TERTIARY}; border-radius: 4px;")
            
            progress_fill = QFrame(progress_bg)
            fill_width = int(dim.total_score * 1.2)  # 120px max
            progress_fill.setGeometry(0, 0, fill_width, 8)
            score_bar_color = "#10B981" if dim.total_score >= 75 else ("#F59E0B" if dim.total_score >= 60 else "#EF4444")
            progress_fill.setStyleSheet(f"background-color: {score_bar_color}; border-radius: 4px;")
            
            dim_row.addWidget(progress_bg, 1)
            
            # 分数
            score_val = QLabel(f"{dim.total_score:.0f}")
            score_val.setFixedWidth(30)
            score_val.setStyleSheet(f"font-size: 10px; font-weight: 600; color: {score_bar_color};")
            dim_row.addWidget(score_val)
            
            # 数据源
            sources = ", ".join([f.data_source for f in dim.factors[:2]])
            source_label = QLabel(sources[:20])
            source_label.setFixedWidth(100)
            source_label.setStyleSheet(f"font-size: 9px; color: {Colors.TEXT_MUTED};")
            dim_row.addWidget(source_label)
            
            dim_layout.addLayout(dim_row)
        
        layout.addWidget(dim_frame)
        
        # ===== 相关板块和股票 =====
        info_layout = QHBoxLayout()
        
        sectors_label = QLabel(f"📁 板块: {', '.join(mainline.sectors[:4])}")
        sectors_label.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_SECONDARY};")
        info_layout.addWidget(sectors_label)
        
        stocks_label = QLabel(f"📈 龙头: {', '.join(mainline.stocks[:4])}")
        stocks_label.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_SECONDARY};")
        info_layout.addWidget(stocks_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # ===== 风险提示 =====
        risk_label = QLabel(mainline.score.risk_warning)
        risk_label.setStyleSheet(f"font-size: 10px; color: #F59E0B;")
        risk_label.setWordWrap(True)
        layout.addWidget(risk_label)
        
        # ===== LLM分析结论（如果有）=====
        if mainline.llm_analysis:
            llm_frame = QFrame()
            llm_frame.setStyleSheet(f"""
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid #8B5CF640;
                border-radius: 6px;
            """)
            llm_layout = QVBoxLayout(llm_frame)
            llm_layout.setContentsMargins(10, 8, 10, 8)
            llm_layout.setSpacing(4)
            
            llm_title = QLabel(f"🤖 LLM分析 ({mainline.llm_analysis.model_used})")
            llm_title.setStyleSheet(f"font-size: 10px; font-weight: 600; color: #8B5CF6;")
            llm_layout.addWidget(llm_title)
            
            llm_text = mainline.llm_analysis.reasoning[:150] + "..." if len(mainline.llm_analysis.reasoning) > 150 else mainline.llm_analysis.reasoning
            llm_content = QLabel(llm_text)
            llm_content.setStyleSheet(f"font-size: 10px; color: {Colors.TEXT_SECONDARY};")
            llm_content.setWordWrap(True)
            llm_layout.addWidget(llm_content)
            
            confidence = QLabel(f"置信度: {mainline.llm_analysis.confidence:.0%}")
            confidence.setStyleSheet(f"font-size: 9px; color: {Colors.TEXT_MUTED};")
            llm_layout.addWidget(confidence)
            
            layout.addWidget(llm_frame)
        
        # ===== 数据溯源按钮 =====
        trace_btn = QPushButton(f"📡 查看数据溯源 ({len(mainline.data_traces)}个数据源)")
        trace_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_MUTED};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_PRIMARY};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        trace_btn.clicked.connect(lambda: self._show_data_traces(mainline))
        layout.addWidget(trace_btn)
        
        return card
    
    def _show_data_traces(self, mainline):
        """显示数据溯源详情"""
        from PyQt6.QtWidgets import QMessageBox
        
        traces_text = f"📡 {mainline.name} 数据溯源\n\n"
        for trace in mainline.data_traces:
            traces_text += f"• {trace.source_name}\n"
            traces_text += f"  提供商: {trace.provider}\n"
            traces_text += f"  可靠性: {trace.reliability}\n"
            traces_text += f"  字段: {', '.join(trace.data_fields[:3])}\n\n"
        
        QMessageBox.information(self, "数据溯源", traces_text)
    
    # ================================================================
    # 五维评分独立Tab
    # ================================================================
    def _create_funds_tab(self) -> QWidget:
        """创建资金维度Tab"""
        try:
            from gui.widgets.dimension_tabs import FundsDimensionTab
            return FundsDimensionTab()
        except Exception as e:
            logger.error(f"加载资金维度面板失败: {e}")
            return self._create_error_widget(f"资金维度", e)
    
    def _create_momentum_tab(self) -> QWidget:
        """创建动量维度Tab"""
        try:
            from gui.widgets.dimension_tabs import MomentumDimensionTab
            return MomentumDimensionTab()
        except Exception as e:
            logger.error(f"加载动量维度面板失败: {e}")
            return self._create_error_widget(f"动量维度", e)
    
    def _create_policy_tab(self) -> QWidget:
        """创建政策维度Tab"""
        try:
            from gui.widgets.dimension_tabs import PolicyDimensionTab
            return PolicyDimensionTab()
        except Exception as e:
            logger.error(f"加载政策维度面板失败: {e}")
            return self._create_error_widget(f"政策维度", e)
    
    def _create_leader_tab(self) -> QWidget:
        """创建龙头维度Tab"""
        try:
            from gui.widgets.dimension_tabs import LeaderDimensionTab
            return LeaderDimensionTab()
        except Exception as e:
            logger.error(f"加载龙头维度面板失败: {e}")
            return self._create_error_widget(f"龙头维度", e)
    
    def _create_composite_tab(self) -> QWidget:
        """创建综合评分Tab（专业投资主线）"""
        try:
            from gui.widgets.dimension_tabs import CompositeDimensionTab
            return CompositeDimensionTab()
        except Exception as e:
            logger.error(f"加载综合评分面板失败: {e}")
            return self._create_error_widget(f"综合评分", e)
    
    def _create_error_widget(self, name: str, error: Exception) -> QWidget:
        """创建错误提示Widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        
        error_label = QLabel(f"⚠️ {name}面板加载失败\n\n错误: {error}")
        error_label.setStyleSheet(f"""
            color: {Colors.ERROR};
            font-size: 14px;
            padding: 20px;
            background-color: {Colors.BG_TERTIARY};
            border-radius: 8px;
        """)
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(error_label)
        layout.addStretch()
        return widget
    
    # ================================================================
    # Tab 4: 热度评分
    # ================================================================
    def _create_heatmap_tab(self) -> QWidget:
        """创建热度评分Tab - 使用新的7因子热度评分面板"""
        try:
            from gui.widgets.heatmap_panel import HeatmapPanel
            return HeatmapPanel()
        except Exception as e:
            logger.error(f"加载热度评分面板失败: {e}")
            # 回退到简单面板
            widget = QWidget()
            layout = QVBoxLayout(widget)
            error_label = QLabel(f"热度评分面板加载失败: {e}")
            error_label.setStyleSheet(f"color: {Colors.ERROR}; padding: 20px;")
            layout.addWidget(error_label)
            return widget
    
    # ================================================================
    # Tab 4: 个股筛选
    # ================================================================
    def _create_stock_selection_tab(self) -> QWidget:
        """
        创建股票池构建Tab
        
        使用新的StockPoolPanel，整合：
        - 主线强势股筛选
        - 技术突破扫描
        - 外部推荐整合
        - 短中长期分类
        - 信号输出（PTrade/QMT）
        """
        try:
            from gui.widgets.stock_pool_panel import StockPoolPanel
            panel = StockPoolPanel()
            logger.info("✅ 股票池面板加载成功")
            return panel
        except Exception as e:
            logger.error(f"❌ 股票池面板加载失败: {e}")
            # 回退到简单的提示界面
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(24, 20, 24, 20)
            
            error_label = QLabel(
                f"🔧 <b>股票池模块加载失败</b><br>"
                f"<span style='color: {Colors.TEXT_SECONDARY};'>{str(e)}</span>"
            )
            error_label.setStyleSheet(f"font-size: 14px; color: {Colors.TEXT_PRIMARY};")
            error_label.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(error_label)
            layout.addStretch()
            
            return widget
    
    # ================================================================
    # Tab 5: 调研笔记
    # ================================================================
    def _create_research_tab(self) -> QWidget:
        """创建调研笔记Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # 顶部说明
        intro = QLabel(
            "📋 <b>调研笔记</b> - 记录行业调研、社交信息、公告研报等定性研究内容<br>"
            f"<span style='color: {Colors.TEXT_SECONDARY};'>支持从校友圈、行业活动、实地调研等渠道获取的非公开信息整理</span>"
        )
        intro.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_PRIMARY};")
        intro.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(intro)
        
        # 分栏布局
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：笔记列表
        left_panel = QFrame()
        left_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 10px;
            }}
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        
        left_header = QHBoxLayout()
        left_title = QLabel("📝 笔记列表")
        left_title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        left_header.addWidget(left_title)
        
        new_note_btn = QPushButton("+ 新建")
        new_note_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
            }}
        """)
        new_note_btn.clicked.connect(self._new_research_note)
        left_header.addWidget(new_note_btn)
        left_layout.addLayout(left_header)
        
        self.notes_list = QTableWidget()
        self.notes_list.setColumnCount(3)
        self.notes_list.setHorizontalHeaderLabels(["日期", "类型", "标题"])
        self.notes_list.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.notes_list.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
            }}
            QTableWidget::item {{
                padding: 6px;
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        self.notes_list.itemClicked.connect(self._load_note)
        left_layout.addWidget(self.notes_list)
        
        splitter.addWidget(left_panel)
        
        # 右侧：笔记编辑
        right_panel = QFrame()
        right_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 10px;
            }}
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 14, 16, 14)
        right_layout.setSpacing(12)
        
        # 笔记类型
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("类型:"))
        self.note_type_combo = QComboBox()
        self.note_type_combo.addItems([
            "🏭 行业调研", "👥 校友信息", "📰 公告解读", "📊 研报摘要",
            "💬 社交线索", "🎤 会议纪要", "🔍 实地调研", "💡 投资灵感"
        ])
        self.note_type_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {Colors.BG_PRIMARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 6px 10px;
                min-width: 150px;
            }}
        """)
        type_layout.addWidget(self.note_type_combo)
        type_layout.addStretch()
        right_layout.addLayout(type_layout)
        
        # 标题
        self.note_title = QLineEdit()
        self.note_title.setPlaceholderText("笔记标题...")
        self.note_title.setStyleSheet(f"""
            QLineEdit {{
                background-color: {Colors.BG_PRIMARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
            }}
        """)
        right_layout.addWidget(self.note_title)
        
        # 关联股票
        stock_layout = QHBoxLayout()
        stock_layout.addWidget(QLabel("关联股票:"))
        self.note_stocks = QLineEdit()
        self.note_stocks.setPlaceholderText("输入股票代码，多个用逗号分隔，如: 000001, 600000")
        self.note_stocks.setStyleSheet(self.note_title.styleSheet())
        stock_layout.addWidget(self.note_stocks)
        right_layout.addLayout(stock_layout)
        
        # 内容
        self.note_content = QPlainTextEdit()
        self.note_content.setPlaceholderText(
            "记录调研内容...\n\n"
            "建议包含：\n"
            "- 信息来源（校友/行业会议/实地调研等）\n"
            "- 关键发现\n"
            "- 投资逻辑\n"
            "- 风险提示\n"
            "- 后续跟踪计划"
        )
        self.note_content.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {Colors.BG_PRIMARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 10px;
                font-size: 12px;
            }}
        """)
        right_layout.addWidget(self.note_content)
        
        # 保存按钮
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        
        save_btn = QPushButton("💾 保存笔记")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: 600;
            }}
        """)
        save_btn.clicked.connect(self._save_research_note)
        save_layout.addWidget(save_btn)
        
        add_stock_btn = QPushButton("📋 加入观察池")
        add_stock_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #10B981;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
            }}
        """)
        add_stock_btn.clicked.connect(self._add_note_stocks_to_watchlist)
        save_layout.addWidget(add_stock_btn)
        
        right_layout.addLayout(save_layout)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 500])
        
        layout.addWidget(splitter)
        
        return widget
    
    # ================================================================
    # Tab 6: 回测验证
    # ================================================================
    def _create_backtest_tab(self) -> QWidget:
        """创建回测验证Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # 顶部说明
        intro = QLabel(
            "📈 <b>历史回测验证</b> - 对主线选股策略进行历史数据回测，验证有效性<br>"
            f"<span style='color: {Colors.TEXT_SECONDARY};'>支持PTrade、QMT、聚宽三大平台回测</span>"
        )
        intro.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_PRIMARY};")
        intro.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(intro)
        
        # 回测参数
        param_frame = QFrame()
        param_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 10px;
            }}
        """)
        param_layout = QVBoxLayout(param_frame)
        param_layout.setContentsMargins(16, 14, 16, 14)
        param_layout.setSpacing(12)
        
        param_title = QLabel("⚙️ 回测参数")
        param_title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        param_layout.addWidget(param_title)
        
        # 参数行1
        row1 = QHBoxLayout()
        
        row1.addWidget(QLabel("回测平台:"))
        self.backtest_platform = QComboBox()
        self.backtest_platform.addItems(["PTrade", "QMT", "聚宽"])
        self.backtest_platform.setStyleSheet(f"""
            QComboBox {{
                background-color: {Colors.BG_PRIMARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 6px 10px;
                min-width: 100px;
            }}
        """)
        row1.addWidget(self.backtest_platform)
        
        row1.addWidget(QLabel("开始日期:"))
        self.backtest_start = QDateEdit()
        self.backtest_start.setDate(QDate.currentDate().addYears(-1))
        self.backtest_start.setCalendarPopup(True)
        self.backtest_start.setStyleSheet(self.backtest_platform.styleSheet())
        row1.addWidget(self.backtest_start)
        
        row1.addWidget(QLabel("结束日期:"))
        self.backtest_end = QDateEdit()
        self.backtest_end.setDate(QDate.currentDate())
        self.backtest_end.setCalendarPopup(True)
        self.backtest_end.setStyleSheet(self.backtest_platform.styleSheet())
        row1.addWidget(self.backtest_end)
        
        row1.addStretch()
        param_layout.addLayout(row1)
        
        # 参数行2
        row2 = QHBoxLayout()
        
        row2.addWidget(QLabel("初始资金:"))
        self.initial_capital = QSpinBox()
        self.initial_capital.setRange(10000, 100000000)
        self.initial_capital.setValue(1000000)
        self.initial_capital.setSuffix(" 元")
        self.initial_capital.setStyleSheet(self.backtest_platform.styleSheet())
        row2.addWidget(self.initial_capital)
        
        row2.addWidget(QLabel("调仓频率:"))
        self.rebalance_freq = QComboBox()
        self.rebalance_freq.addItems(["每日", "每周", "每月", "每季"])
        self.rebalance_freq.setCurrentIndex(2)
        self.rebalance_freq.setStyleSheet(self.backtest_platform.styleSheet())
        row2.addWidget(self.rebalance_freq)
        
        row2.addWidget(QLabel("持仓数量:"))
        self.hold_count = QSpinBox()
        self.hold_count.setRange(1, 50)
        self.hold_count.setValue(10)
        self.hold_count.setSuffix(" 只")
        self.hold_count.setStyleSheet(self.backtest_platform.styleSheet())
        row2.addWidget(self.hold_count)
        
        row2.addStretch()
        
        run_btn = QPushButton("🚀 运行回测")
        run_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 12px;
                font-weight: 600;
            }}
        """)
        run_btn.clicked.connect(self._run_backtest)
        row2.addWidget(run_btn)
        
        param_layout.addLayout(row2)
        layout.addWidget(param_frame)
        
        # 回测结果
        result_frame = QFrame()
        result_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 10px;
            }}
        """)
        result_layout = QVBoxLayout(result_frame)
        result_layout.setContentsMargins(16, 14, 16, 14)
        
        result_title = QLabel("📊 回测结果")
        result_title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        result_layout.addWidget(result_title)
        
        # 指标卡片
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(12)
        
        metrics = [
            ("年化收益", "--", "#10B981"),
            ("最大回撤", "--", "#EF4444"),
            ("夏普比率", "--", "#3B82F6"),
            ("胜率", "--", "#F59E0B"),
            ("超额收益", "--", "#8B5CF6"),
        ]
        
        self.backtest_metrics = {}
        for name, value, color in metrics:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.BG_PRIMARY};
                    border: 1px solid {color}30;
                    border-radius: 8px;
                    min-width: 100px;
                }}
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)
            
            name_label = QLabel(name)
            name_label.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED};")
            card_layout.addWidget(name_label)
            
            value_label = QLabel(value)
            value_label.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {color};")
            card_layout.addWidget(value_label)
            
            self.backtest_metrics[name] = value_label
            metrics_layout.addWidget(card)
        
        metrics_layout.addStretch()
        result_layout.addLayout(metrics_layout)
        
        # 回测日志
        self.backtest_log = QTextEdit()
        self.backtest_log.setReadOnly(True)
        self.backtest_log.setPlaceholderText("回测日志将显示在这里...")
        self.backtest_log.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_PRIMARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 10px;
                font-family: monospace;
                font-size: 11px;
            }}
        """)
        self.backtest_log.setFixedHeight(150)
        result_layout.addWidget(self.backtest_log)
        
        layout.addWidget(result_frame)
        
        return widget
    
    # ================================================================
    # Tab: 历史查询 (时间维度)
    # ================================================================
    def _create_history_tab(self) -> QWidget:
        """创建历史查询Tab - 时间维度功能"""
        try:
            from gui.widgets.history_viewer_tab import HistoryViewerTab
            return HistoryViewerTab(self)
        except Exception as e:
            logger.error(f"创建历史查询Tab失败: {e}")
            # 返回占位Widget
            widget = QWidget()
            layout = QVBoxLayout(widget)
            error_label = QLabel(f"历史查询功能加载失败: {e}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)
            return widget
    
    # ================================================================
    # Tab 7: 实时监控
    # ================================================================
    def _create_monitoring_tab(self) -> QWidget:
        """创建实时监控Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # 顶部说明
        intro = QLabel(
            "⚡ <b>实时监控与风控</b> - 跟踪主线切换、个股表现、风险触发，及时调仓<br>"
            f"<span style='color: {Colors.TEXT_SECONDARY};'>设置预警规则，自动生成调仓建议</span>"
        )
        intro.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_PRIMARY};")
        intro.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(intro)
        
        # 监控状态
        status_layout = QHBoxLayout()
        status_layout.setSpacing(16)
        
        # 主线状态
        mainline_card = self._create_monitor_card("🎯 当前主线", "未识别", "#3B82F6")
        status_layout.addWidget(mainline_card)
        
        # 持仓状态
        position_card = self._create_monitor_card("📊 持仓数量", "0 只", "#10B981")
        status_layout.addWidget(position_card)
        
        # 预警状态
        alert_card = self._create_monitor_card("⚠️ 预警数量", "0 个", "#F59E0B")
        status_layout.addWidget(alert_card)
        
        # 风险等级
        risk_card = self._create_monitor_card("🛡️ 风险等级", "低", "#8B5CF6")
        status_layout.addWidget(risk_card)
        
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # 预警规则设置
        rule_frame = QFrame()
        rule_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 10px;
            }}
        """)
        rule_layout = QVBoxLayout(rule_frame)
        rule_layout.setContentsMargins(16, 14, 16, 14)
        
        rule_title = QLabel("⚙️ 预警规则")
        rule_title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        rule_layout.addWidget(rule_title)
        
        rules_grid = QGridLayout()
        rules_grid.setSpacing(12)
        
        # 止损规则
        rules_grid.addWidget(QLabel("止损线:"), 0, 0)
        self.stop_loss = QDoubleSpinBox()
        self.stop_loss.setRange(-50, 0)
        self.stop_loss.setValue(-8)
        self.stop_loss.setSuffix("%")
        self.stop_loss.setStyleSheet(f"""
            QDoubleSpinBox {{
                background-color: {Colors.BG_PRIMARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 4px;
                padding: 4px;
            }}
        """)
        rules_grid.addWidget(self.stop_loss, 0, 1)
        
        # 止盈规则
        rules_grid.addWidget(QLabel("止盈线:"), 0, 2)
        self.take_profit = QDoubleSpinBox()
        self.take_profit.setRange(0, 100)
        self.take_profit.setValue(20)
        self.take_profit.setSuffix("%")
        self.take_profit.setStyleSheet(self.stop_loss.styleSheet())
        rules_grid.addWidget(self.take_profit, 0, 3)
        
        # 主线切换
        rules_grid.addWidget(QLabel("主线切换阈值:"), 1, 0)
        self.rotation_threshold = QSpinBox()
        self.rotation_threshold.setRange(1, 10)
        self.rotation_threshold.setValue(3)
        self.rotation_threshold.setSuffix(" 天")
        self.rotation_threshold.setStyleSheet(self.stop_loss.styleSheet())
        rules_grid.addWidget(self.rotation_threshold, 1, 1)
        
        # 仓位上限
        rules_grid.addWidget(QLabel("单股仓位上限:"), 1, 2)
        self.max_position = QDoubleSpinBox()
        self.max_position.setRange(0, 100)
        self.max_position.setValue(20)
        self.max_position.setSuffix("%")
        self.max_position.setStyleSheet(self.stop_loss.styleSheet())
        rules_grid.addWidget(self.max_position, 1, 3)
        
        rule_layout.addLayout(rules_grid)
        
        # 启动监控按钮
        monitor_btn_layout = QHBoxLayout()
        monitor_btn_layout.addStretch()
        
        start_monitor_btn = QPushButton("▶️ 启动监控")
        start_monitor_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #10B981;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 12px;
                font-weight: 600;
            }}
        """)
        start_monitor_btn.clicked.connect(self._start_monitoring)
        monitor_btn_layout.addWidget(start_monitor_btn)
        
        rule_layout.addLayout(monitor_btn_layout)
        layout.addWidget(rule_frame)
        
        # 预警列表
        alert_frame = QFrame()
        alert_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 10px;
            }}
        """)
        alert_layout = QVBoxLayout(alert_frame)
        alert_layout.setContentsMargins(16, 14, 16, 14)
        
        alert_title = QLabel("🔔 预警信息")
        alert_title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        alert_layout.addWidget(alert_title)
        
        self.alert_table = QTableWidget()
        self.alert_table.setColumnCount(5)
        self.alert_table.setHorizontalHeaderLabels(["时间", "类型", "标的", "内容", "建议"])
        self.alert_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.alert_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
            }}
        """)
        alert_layout.addWidget(self.alert_table)
        
        layout.addWidget(alert_frame)
        
        return widget
    
    def _create_monitor_card(self, title: str, value: str, color: str) -> QFrame:
        """创建监控状态卡片"""
        card = QFrame()
        card.setFixedSize(150, 80)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {color}40;
                border-radius: 10px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED};")
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {color};")
        layout.addWidget(value_label)
        
        return card
    
    # ================================================================
    # 事件处理方法
    # ================================================================
    def _scan_sectors(self):
        """扫描板块"""
        QMessageBox.information(self, "提示", "正在扫描板块数据...\n\n此功能将从AKShare获取实时板块数据。")
        # TODO: 实现板块扫描逻辑
        self.update_time_label.setText(f"最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def _calculate_heat_score(self):
        """计算热度评分"""
        total = self.weight_fund.value() + self.weight_price.value() + self.weight_sentiment.value()
        if total != 100:
            QMessageBox.warning(self, "警告", f"权重之和必须为100%，当前为{total}%")
            return
        QMessageBox.information(self, "提示", "正在计算板块热度评分...")
        # TODO: 实现热度评分计算
    
    def _screen_stocks(self):
        """筛选个股"""
        QMessageBox.information(self, "提示", "正在筛选个股...")
        # TODO: 实现个股筛选逻辑
    
    def _add_to_watchlist(self):
        """加入观察池"""
        QMessageBox.information(self, "提示", "已将选中股票加入观察池")
    
    def _generate_strategy(self):
        """生成策略"""
        QMessageBox.information(self, "提示", "正在生成策略代码...")
        self.generate_strategy.emit({})
    
    def _new_research_note(self):
        """新建调研笔记"""
        self.note_title.clear()
        self.note_stocks.clear()
        self.note_content.clear()
        self.note_type_combo.setCurrentIndex(0)
    
    def _save_research_note(self):
        """保存调研笔记"""
        note = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "type": self.note_type_combo.currentText(),
            "title": self.note_title.text(),
            "stocks": self.note_stocks.text(),
            "content": self.note_content.toPlainText(),
        }
        
        if not note["title"]:
            QMessageBox.warning(self, "警告", "请输入笔记标题")
            return
        
        self.research_notes.append(note)
        
        # 更新列表
        row = self.notes_list.rowCount()
        self.notes_list.insertRow(row)
        self.notes_list.setItem(row, 0, QTableWidgetItem(note["date"]))
        self.notes_list.setItem(row, 1, QTableWidgetItem(note["type"]))
        self.notes_list.setItem(row, 2, QTableWidgetItem(note["title"]))
        
        QMessageBox.information(self, "成功", "笔记已保存")
    
    def _load_note(self, item):
        """加载笔记"""
        row = item.row()
        if row < len(self.research_notes):
            note = self.research_notes[row]
            self.note_title.setText(note["title"])
            self.note_stocks.setText(note["stocks"])
            self.note_content.setPlainText(note["content"])
            # 设置类型
            index = self.note_type_combo.findText(note["type"])
            if index >= 0:
                self.note_type_combo.setCurrentIndex(index)
    
    def _add_note_stocks_to_watchlist(self):
        """将笔记中的股票加入观察池"""
        stocks = self.note_stocks.text()
        if stocks:
            QMessageBox.information(self, "成功", f"已将 {stocks} 加入观察池")
    
    def _run_backtest(self):
        """运行回测"""
        platform = self.backtest_platform.currentText()
        QMessageBox.information(self, "提示", f"正在通过{platform}运行回测...\n\n回测结果将显示在下方。")
        
        # 模拟回测结果
        self.backtest_metrics["年化收益"].setText("32.5%")
        self.backtest_metrics["最大回撤"].setText("-18.7%")
        self.backtest_metrics["夏普比率"].setText("1.85")
        self.backtest_metrics["胜率"].setText("62.3%")
        self.backtest_metrics["超额收益"].setText("+20.2%")
        
        self.backtest_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] 回测开始...")
        self.backtest_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] 平台: {platform}")
        self.backtest_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] 回测完成")
    
    def _start_monitoring(self):
        """启动监控"""
        QMessageBox.information(self, "提示", "实时监控已启动\n\n系统将持续跟踪主线变化和个股表现。")

