# -*- coding: utf-8 -*-
"""
历史查询Tab
============

提供时间维度的历史数据查询功能：
1. 主线历史查询
2. 候选池历史快照
3. 板块轮动分析
4. 变更记录追踪
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QGroupBox, QComboBox,
    QScrollArea, QFrame, QGridLayout, QDateEdit, QSpinBox,
    QTabWidget, QTextEdit, QHeaderView, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from gui.styles.theme import Colors, ButtonStyles

logger = logging.getLogger(__name__)


class RealtimeRotationWorker(QThread):
    """实时轮动分析工作线程"""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, days: int = 5):
        super().__init__()
        self.days = days
    
    def run(self):
        try:
            from core.rotation_analyzer import create_rotation_analyzer
            analyzer = create_rotation_analyzer()
            result = analyzer.analyze_rotation(days=self.days)
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"实时轮动分析失败: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))


class HistoryQueryWorker(QThread):
    """历史查询工作线程"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, query_type: str, params: dict):
        super().__init__()
        self.query_type = query_type
        self.params = params
    
    def run(self):
        try:
            from core.time_dimension_manager import create_time_dimension_manager, Period
            
            tdm = create_time_dimension_manager()
            result = {}
            
            if self.query_type == "mainline_snapshot":
                date = self.params.get("date")
                period = self.params.get("period", Period.MEDIUM)
                snapshot = tdm.get_mainline_snapshot(date, period)
                result = {"type": "mainline_snapshot", "snapshot": snapshot}
                
            elif self.query_type == "mainline_history":
                start = self.params.get("start_date")
                end = self.params.get("end_date")
                period = self.params.get("period")
                history = tdm.get_mainline_history(start, end, period)
                result = {"type": "mainline_history", "history": history}
                
            elif self.query_type == "pool_snapshot":
                date = self.params.get("date")
                period = self.params.get("period", Period.MEDIUM)
                snapshot = tdm.get_candidate_pool_snapshot(date, period)
                result = {"type": "pool_snapshot", "snapshot": snapshot}
                
            elif self.query_type == "pool_history":
                start = self.params.get("start_date")
                end = self.params.get("end_date")
                period = self.params.get("period")
                history = tdm.get_candidate_pool_history(start, end, period)
                result = {"type": "pool_history", "history": history}
                
            elif self.query_type == "rotation_analysis":
                days = self.params.get("days", 30)
                period = self.params.get("period", Period.MEDIUM)
                analysis = tdm.analyze_rotation(days, period)
                result = {"type": "rotation", "analysis": analysis}
                
            elif self.query_type == "change_history":
                stock_code = self.params.get("stock_code")
                limit = self.params.get("limit", 100)
                if stock_code:
                    changes = tdm.get_stock_history(stock_code, limit)
                else:
                    changes = tdm.get_recent_changes(limit)
                result = {"type": "changes", "changes": changes}
            
            self.finished.emit(result)
            
        except Exception as e:
            logger.error(f"历史查询失败: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))


class HistoryViewerTab(QWidget):
    """历史查询Tab"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tab控件
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(self._get_tab_style())
        
        self.tab_widget.addTab(self._create_mainline_history_tab(), "📊 主线历史")
        self.tab_widget.addTab(self._create_pool_history_tab(), "📦 候选池历史")
        self.tab_widget.addTab(self._create_rotation_tab(), "🔄 板块轮动")
        self.tab_widget.addTab(self._create_changes_tab(), "📝 变更记录")
        
        layout.addWidget(self.tab_widget)
    
    def _get_tab_style(self) -> str:
        return f"""
            QTabWidget::pane {{
                border: none;
                background-color: {Colors.BG_SECONDARY};
            }}
            QTabBar::tab {{
                background-color: {Colors.BG_PRIMARY};
                color: {Colors.TEXT_MUTED};
                border: none;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.PRIMARY};
                border-bottom: 2px solid {Colors.PRIMARY};
            }}
        """
    
    # ========== 主线历史Tab ==========
    def _create_mainline_history_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # 查询参数
        params_frame = QFrame()
        params_frame.setStyleSheet(f"background-color: {Colors.BG_TERTIARY}; border-radius: 8px; padding: 12px;")
        params_layout = QHBoxLayout(params_frame)
        params_layout.setSpacing(16)
        
        params_layout.addWidget(QLabel("查询日期:"))
        self.mainline_date = QDateEdit()
        self.mainline_date.setDate(QDate.currentDate())
        self.mainline_date.setCalendarPopup(True)
        self.mainline_date.setStyleSheet(self._get_input_style())
        params_layout.addWidget(self.mainline_date)
        
        params_layout.addWidget(QLabel("投资周期:"))
        self.mainline_period = QComboBox()
        self.mainline_period.addItems(["短期 (1-5天)", "中期 (1-4周)", "长期 (1月+)"])
        self.mainline_period.setCurrentIndex(1)
        self.mainline_period.setStyleSheet(self._get_combo_style())
        params_layout.addWidget(self.mainline_period)
        
        self.query_mainline_btn = QPushButton("🔍 查询")
        self.query_mainline_btn.setStyleSheet(ButtonStyles.PRIMARY)
        self.query_mainline_btn.clicked.connect(self._query_mainline_snapshot)
        params_layout.addWidget(self.query_mainline_btn)
        
        params_layout.addStretch()
        layout.addWidget(params_frame)
        
        # 结果表格
        self.mainline_table = QTableWidget()
        self.mainline_table.setColumnCount(5)
        self.mainline_table.setHorizontalHeaderLabels(["排名", "主线名称", "综合得分", "JQ映射", "状态"])
        self.mainline_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.mainline_table.setStyleSheet(self._get_table_style())
        layout.addWidget(self.mainline_table)
        
        # 状态标签
        self.mainline_status = QLabel("")
        self.mainline_status.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        layout.addWidget(self.mainline_status)
        
        return widget
    
    def _query_mainline_snapshot(self):
        """查询主线快照"""
        from core.time_dimension_manager import Period
        
        date = self.mainline_date.date().toString("yyyy-MM-dd")
        period_idx = self.mainline_period.currentIndex()
        period = [Period.SHORT, Period.MEDIUM, Period.LONG][period_idx]
        
        self.query_mainline_btn.setEnabled(False)
        self.mainline_status.setText("正在查询...")
        
        self.worker = HistoryQueryWorker("mainline_snapshot", {"date": date, "period": period})
        self.worker.finished.connect(self._on_mainline_result)
        self.worker.error.connect(lambda e: self._on_error(e, "mainline"))
        self.worker.start()
    
    def _on_mainline_result(self, result: dict):
        self.query_mainline_btn.setEnabled(True)
        
        snapshot = result.get("snapshot")
        if not snapshot:
            self.mainline_status.setText("❌ 未找到该日期的主线数据")
            self.mainline_table.setRowCount(0)
            return
        
        mainlines = snapshot.mainlines
        self.mainline_table.setRowCount(len(mainlines))
        
        for i, ml in enumerate(mainlines):
            self.mainline_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.mainline_table.setItem(i, 1, QTableWidgetItem(ml.get("name", "")))
            
            score = ml.get("score", ml.get("total_score", 0))
            score_item = QTableWidgetItem(f"{score:.1f}")
            if score > 70:
                score_item.setForeground(QColor(Colors.SUCCESS))
            elif score < 50:
                score_item.setForeground(QColor(Colors.ERROR))
            self.mainline_table.setItem(i, 2, score_item)
            
            self.mainline_table.setItem(i, 3, QTableWidgetItem(ml.get("jqdata_code", "-")))
            self.mainline_table.setItem(i, 4, QTableWidgetItem(ml.get("status", "active")))
        
        meta = snapshot.meta
        self.mainline_status.setText(
            f"✅ 快照日期: {meta.snapshot_date} | 周期: {meta.period} | "
            f"创建时间: {meta.created_at[:19]} | 共 {len(mainlines)} 条主线"
        )
    
    # ========== 候选池历史Tab ==========
    def _create_pool_history_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # 查询参数
        params_frame = QFrame()
        params_frame.setStyleSheet(f"background-color: {Colors.BG_TERTIARY}; border-radius: 8px; padding: 12px;")
        params_layout = QHBoxLayout(params_frame)
        params_layout.setSpacing(16)
        
        params_layout.addWidget(QLabel("查询日期:"))
        self.pool_date = QDateEdit()
        self.pool_date.setDate(QDate.currentDate())
        self.pool_date.setCalendarPopup(True)
        self.pool_date.setStyleSheet(self._get_input_style())
        params_layout.addWidget(self.pool_date)
        
        params_layout.addWidget(QLabel("投资周期:"))
        self.pool_period = QComboBox()
        self.pool_period.addItems(["短期", "中期", "长期"])
        self.pool_period.setCurrentIndex(1)
        self.pool_period.setStyleSheet(self._get_combo_style())
        params_layout.addWidget(self.pool_period)
        
        self.query_pool_btn = QPushButton("🔍 查询")
        self.query_pool_btn.setStyleSheet(ButtonStyles.PRIMARY)
        self.query_pool_btn.clicked.connect(self._query_pool_snapshot)
        params_layout.addWidget(self.query_pool_btn)
        
        params_layout.addStretch()
        layout.addWidget(params_frame)
        
        # 统计信息
        self.pool_stats = QLabel("")
        self.pool_stats.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px; padding: 8px;")
        layout.addWidget(self.pool_stats)
        
        # 结果表格
        self.pool_table = QTableWidget()
        self.pool_table.setColumnCount(6)
        self.pool_table.setHorizontalHeaderLabels(["序号", "代码", "名称", "所属主线", "评分", "入池原因"])
        self.pool_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.pool_table.setStyleSheet(self._get_table_style())
        layout.addWidget(self.pool_table)
        
        # 状态
        self.pool_status = QLabel("")
        self.pool_status.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        layout.addWidget(self.pool_status)
        
        return widget
    
    def _query_pool_snapshot(self):
        """查询候选池快照"""
        from core.time_dimension_manager import Period
        
        date = self.pool_date.date().toString("yyyy-MM-dd")
        period_idx = self.pool_period.currentIndex()
        period = [Period.SHORT, Period.MEDIUM, Period.LONG][period_idx]
        
        self.query_pool_btn.setEnabled(False)
        self.pool_status.setText("正在查询...")
        
        self.worker = HistoryQueryWorker("pool_snapshot", {"date": date, "period": period})
        self.worker.finished.connect(self._on_pool_result)
        self.worker.error.connect(lambda e: self._on_error(e, "pool"))
        self.worker.start()
    
    def _on_pool_result(self, result: dict):
        self.query_pool_btn.setEnabled(True)
        
        snapshot = result.get("snapshot")
        if not snapshot:
            self.pool_status.setText("❌ 未找到该日期的候选池数据")
            self.pool_table.setRowCount(0)
            self.pool_stats.setText("")
            return
        
        stocks = snapshot.stocks
        stats = snapshot.statistics
        
        # 显示统计信息
        stats_text = f"📊 股票数量: {stats.get('count', len(stocks))} | 平均评分: {stats.get('avg_score', 0):.1f}"
        if 'mainline_distribution' in stats:
            dist = stats['mainline_distribution']
            top_ml = sorted(dist.items(), key=lambda x: x[1], reverse=True)[:3]
            stats_text += f" | 主要主线: {', '.join([f'{k}({v})' for k, v in top_ml])}"
        self.pool_stats.setText(stats_text)
        
        # 填充表格
        self.pool_table.setRowCount(len(stocks))
        for i, stock in enumerate(stocks):
            self.pool_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.pool_table.setItem(i, 1, QTableWidgetItem(stock.get("code", "")))
            self.pool_table.setItem(i, 2, QTableWidgetItem(stock.get("name", "")))
            self.pool_table.setItem(i, 3, QTableWidgetItem(stock.get("mainline", "-")))
            
            score = stock.get("score", stock.get("mainline_score", 0))
            score_item = QTableWidgetItem(f"{score:.1f}" if score else "-")
            self.pool_table.setItem(i, 4, score_item)
            
            reason = stock.get("entry_reason", "")
            self.pool_table.setItem(i, 5, QTableWidgetItem(reason[:30] + "..." if len(reason) > 30 else reason))
        
        meta = snapshot.meta
        self.pool_status.setText(
            f"✅ 快照日期: {meta.snapshot_date} | 周期: {meta.period} | "
            f"数据源: {meta.source} | 共 {len(stocks)} 只股票"
        )
    
    # ========== 板块轮动Tab ==========
    def _create_rotation_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # 说明
        intro = QLabel(
            "📈 <b>板块轮动分析</b><br>"
            "支持两种数据源：1) AKShare实时数据（推荐）2) 历史快照对比<br>"
            "分析板块热度变化趋势，发现轮动信号，指导投资决策"
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px; padding: 8px; background-color: {Colors.BG_TERTIARY}; border-radius: 8px;")
        layout.addWidget(intro)
        
        # 参数
        params_frame = QFrame()
        params_frame.setStyleSheet(f"background-color: {Colors.BG_TERTIARY}; border-radius: 8px; padding: 12px;")
        params_layout = QHBoxLayout(params_frame)
        
        params_layout.addWidget(QLabel("分析天数:"))
        self.rotation_days = QSpinBox()
        self.rotation_days.setRange(1, 90)
        self.rotation_days.setValue(5)
        self.rotation_days.setStyleSheet(self._get_input_style())
        params_layout.addWidget(self.rotation_days)
        
        params_layout.addWidget(QLabel("投资周期:"))
        self.rotation_period = QComboBox()
        self.rotation_period.addItems(["短期", "中期", "长期"])
        self.rotation_period.setCurrentIndex(1)
        self.rotation_period.setStyleSheet(self._get_combo_style())
        params_layout.addWidget(self.rotation_period)
        
        # 实时分析按钮（使用AKShare）
        self.analyze_realtime_btn = QPushButton("🌐 实时轮动分析")
        self.analyze_realtime_btn.setStyleSheet(ButtonStyles.PRIMARY)
        self.analyze_realtime_btn.clicked.connect(self._analyze_rotation_realtime)
        params_layout.addWidget(self.analyze_realtime_btn)
        
        # 历史对比按钮
        self.analyze_rotation_btn = QPushButton("📊 历史快照对比")
        self.analyze_rotation_btn.setStyleSheet(ButtonStyles.SECONDARY)
        self.analyze_rotation_btn.clicked.connect(self._analyze_rotation)
        params_layout.addWidget(self.analyze_rotation_btn)
        
        params_layout.addStretch()
        layout.addWidget(params_frame)
        
        # 总结区域
        self.rotation_summary = QLabel("")
        self.rotation_summary.setWordWrap(True)
        self.rotation_summary.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY}; 
            font-size: 14px; 
            font-weight: bold;
            padding: 12px; 
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                stop:0 {Colors.BG_TERTIARY}, stop:1 {Colors.BG_SECONDARY});
            border-radius: 8px;
            border-left: 4px solid {Colors.PRIMARY};
        """)
        layout.addWidget(self.rotation_summary)
        
        # 结果区域
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 升温板块
        rising_frame = QGroupBox("🔥 升温板块 (Top 10)")
        rising_frame.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {Colors.SUCCESS}; }}")
        rising_layout = QVBoxLayout(rising_frame)
        self.rising_table = QTableWidget()
        self.rising_table.setColumnCount(5)
        self.rising_table.setHorizontalHeaderLabels(["板块", "涨跌幅%", "5日涨幅%", "热度", "资金流(亿)"])
        self.rising_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.rising_table.setStyleSheet(self._get_table_style())
        rising_layout.addWidget(self.rising_table)
        splitter.addWidget(rising_frame)
        
        # 降温板块
        falling_frame = QGroupBox("❄️ 降温板块 (Top 10)")
        falling_frame.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {Colors.ERROR}; }}")
        falling_layout = QVBoxLayout(falling_frame)
        self.falling_table = QTableWidget()
        self.falling_table.setColumnCount(5)
        self.falling_table.setHorizontalHeaderLabels(["板块", "涨跌幅%", "5日涨幅%", "热度", "资金流(亿)"])
        self.falling_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.falling_table.setStyleSheet(self._get_table_style())
        falling_layout.addWidget(self.falling_table)
        splitter.addWidget(falling_frame)
        
        layout.addWidget(splitter)
        
        # 状态
        self.rotation_status = QLabel("")
        self.rotation_status.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        layout.addWidget(self.rotation_status)
        
        return widget
    
    def _analyze_rotation_realtime(self):
        """使用AKShare实时分析板块轮动"""
        self.analyze_realtime_btn.setEnabled(False)
        self.rotation_status.setText("正在从AKShare获取实时数据...")
        
        # 使用工作线程
        self.worker = RealtimeRotationWorker(self.rotation_days.value())
        self.worker.finished.connect(self._on_realtime_rotation_result)
        self.worker.error.connect(lambda e: self._on_error(e, "rotation"))
        self.worker.start()
    
    def _on_realtime_rotation_result(self, result):
        """处理实时轮动分析结果"""
        self.analyze_realtime_btn.setEnabled(True)
        
        if result is None:
            self.rotation_status.setText("❌ 分析失败，无法获取数据")
            self.rotation_summary.setText("")
            return
        
        # 更新总结
        self.rotation_summary.setText(f"📊 {result.rotation_summary}")
        
        # 升温板块
        rising = result.rising_sectors
        self.rising_table.setRowCount(len(rising))
        for i, s in enumerate(rising):
            self.rising_table.setItem(i, 0, QTableWidgetItem(s.sector_name))
            
            change_item = QTableWidgetItem(f"+{s.current_change_pct:.2f}")
            change_item.setForeground(QColor(Colors.SUCCESS))
            self.rising_table.setItem(i, 1, change_item)
            
            avg_item = QTableWidgetItem(f"+{s.avg_change_pct:.2f}" if s.avg_change_pct > 0 else f"{s.avg_change_pct:.2f}")
            avg_item.setForeground(QColor(Colors.SUCCESS if s.avg_change_pct > 0 else Colors.ERROR))
            self.rising_table.setItem(i, 2, avg_item)
            
            self.rising_table.setItem(i, 3, QTableWidgetItem(f"{s.heat_score:.0f}"))
            self.rising_table.setItem(i, 4, QTableWidgetItem(f"{s.capital_flow:+.2f}" if s.capital_flow else "-"))
        
        # 降温板块
        falling = result.falling_sectors
        self.falling_table.setRowCount(len(falling))
        for i, s in enumerate(falling):
            self.falling_table.setItem(i, 0, QTableWidgetItem(s.sector_name))
            
            change_item = QTableWidgetItem(f"{s.current_change_pct:.2f}")
            change_item.setForeground(QColor(Colors.ERROR))
            self.falling_table.setItem(i, 1, change_item)
            
            avg_item = QTableWidgetItem(f"{s.avg_change_pct:.2f}")
            avg_item.setForeground(QColor(Colors.SUCCESS if s.avg_change_pct > 0 else Colors.ERROR))
            self.falling_table.setItem(i, 2, avg_item)
            
            self.falling_table.setItem(i, 3, QTableWidgetItem(f"{s.heat_score:.0f}"))
            self.falling_table.setItem(i, 4, QTableWidgetItem(f"{s.capital_flow:+.2f}" if s.capital_flow else "-"))
        
        self.rotation_status.setText(
            f"✅ 分析完成 | 数据来源: {result.data_source} | "
            f"升温: {len(rising)}个 | 降温: {len(falling)}个 | "
            f"时间: {result.analysis_date}"
        )
    
    def _analyze_rotation(self):
        """分析板块轮动（历史快照对比）"""
        from core.time_dimension_manager import Period
        
        days = self.rotation_days.value()
        period_idx = self.rotation_period.currentIndex()
        period = [Period.SHORT, Period.MEDIUM, Period.LONG][period_idx]
        
        self.analyze_rotation_btn.setEnabled(False)
        self.rotation_status.setText("正在分析历史快照...")
        
        self.worker = HistoryQueryWorker("rotation_analysis", {"days": days, "period": period})
        self.worker.finished.connect(self._on_rotation_result)
        self.worker.error.connect(lambda e: self._on_error(e, "rotation"))
        self.worker.start()
    
    def _on_rotation_result(self, result: dict):
        self.analyze_rotation_btn.setEnabled(True)
        
        analysis = result.get("analysis", {})
        
        if "error" in analysis:
            self.rotation_status.setText(f"❌ {analysis['error']}")
            return
        
        # 升温板块
        rising = analysis.get("rising_mainlines", [])
        self.rising_table.setRowCount(len(rising))
        for i, r in enumerate(rising):
            self.rising_table.setItem(i, 0, QTableWidgetItem(r.get("mainline", "")))
            self.rising_table.setItem(i, 1, QTableWidgetItem(f"{r.get('latest_score', 0):.1f}"))
            
            change_item = QTableWidgetItem(f"+{r.get('change', 0):.1f}")
            change_item.setForeground(QColor(Colors.SUCCESS))
            self.rising_table.setItem(i, 2, change_item)
        
        # 降温板块
        falling = analysis.get("falling_mainlines", [])
        self.falling_table.setRowCount(len(falling))
        for i, f in enumerate(falling):
            self.falling_table.setItem(i, 0, QTableWidgetItem(f.get("mainline", "")))
            self.falling_table.setItem(i, 1, QTableWidgetItem(f"{f.get('latest_score', 0):.1f}"))
            
            change_item = QTableWidgetItem(f"{f.get('change', 0):.1f}")
            change_item.setForeground(QColor(Colors.ERROR))
            self.falling_table.setItem(i, 2, change_item)
        
        self.rotation_status.setText(
            f"✅ 分析完成 | 分析天数: {analysis.get('days_analyzed')} | "
            f"快照数: {analysis.get('snapshots_count')} | "
            f"时间: {analysis.get('analyzed_at', '')[:19]}"
        )
    
    # ========== 变更记录Tab ==========
    def _create_changes_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # 说明
        intro = QLabel(
            "📝 <b>变更记录追踪</b><br>"
            "记录股票进入/退出候选池的历史，支持追溯单只股票的完整轨迹"
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px; padding: 8px; background-color: {Colors.BG_TERTIARY}; border-radius: 8px;")
        layout.addWidget(intro)
        
        # 查询
        params_frame = QFrame()
        params_frame.setStyleSheet(f"background-color: {Colors.BG_TERTIARY}; border-radius: 8px; padding: 12px;")
        params_layout = QHBoxLayout(params_frame)
        
        params_layout.addWidget(QLabel("股票代码 (可选):"))
        self.change_stock_code = QComboBox()
        self.change_stock_code.setEditable(True)
        self.change_stock_code.setPlaceholderText("留空查询全部")
        self.change_stock_code.setStyleSheet(self._get_combo_style())
        self.change_stock_code.setMinimumWidth(150)
        params_layout.addWidget(self.change_stock_code)
        
        self.query_changes_btn = QPushButton("🔍 查询变更")
        self.query_changes_btn.setStyleSheet(ButtonStyles.PRIMARY)
        self.query_changes_btn.clicked.connect(self._query_changes)
        params_layout.addWidget(self.query_changes_btn)
        
        params_layout.addStretch()
        layout.addWidget(params_frame)
        
        # 变更表格
        self.changes_table = QTableWidget()
        self.changes_table.setColumnCount(6)
        self.changes_table.setHorizontalHeaderLabels(["时间", "类型", "代码", "名称", "主线", "详情"])
        self.changes_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.changes_table.setStyleSheet(self._get_table_style())
        layout.addWidget(self.changes_table)
        
        # 状态
        self.changes_status = QLabel("")
        self.changes_status.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        layout.addWidget(self.changes_status)
        
        return widget
    
    def _query_changes(self):
        """查询变更记录"""
        stock_code = self.change_stock_code.currentText().strip() or None
        
        self.query_changes_btn.setEnabled(False)
        self.changes_status.setText("正在查询...")
        
        self.worker = HistoryQueryWorker("change_history", {"stock_code": stock_code, "limit": 100})
        self.worker.finished.connect(self._on_changes_result)
        self.worker.error.connect(lambda e: self._on_error(e, "changes"))
        self.worker.start()
    
    def _on_changes_result(self, result: dict):
        self.query_changes_btn.setEnabled(True)
        
        changes = result.get("changes", [])
        
        if not changes:
            self.changes_status.setText("❌ 未找到变更记录")
            self.changes_table.setRowCount(0)
            return
        
        self.changes_table.setRowCount(len(changes))
        for i, c in enumerate(changes):
            # 时间
            ts = c.get("timestamp", "")[:19]
            self.changes_table.setItem(i, 0, QTableWidgetItem(ts))
            
            # 类型
            change_type = c.get("change_type", "")
            type_item = QTableWidgetItem({"add": "➕ 加入", "remove": "➖ 移出", "update": "🔄 更新"}.get(change_type, change_type))
            if change_type == "add":
                type_item.setForeground(QColor(Colors.SUCCESS))
            elif change_type == "remove":
                type_item.setForeground(QColor(Colors.ERROR))
            self.changes_table.setItem(i, 1, type_item)
            
            self.changes_table.setItem(i, 2, QTableWidgetItem(c.get("item_id", "")))
            self.changes_table.setItem(i, 3, QTableWidgetItem(c.get("item_name", "")))
            
            details = c.get("details", {})
            self.changes_table.setItem(i, 4, QTableWidgetItem(details.get("mainline", "-")))
            self.changes_table.setItem(i, 5, QTableWidgetItem(f"周期: {details.get('period', '-')}"))
        
        self.changes_status.setText(f"✅ 共 {len(changes)} 条变更记录")
    
    def _on_error(self, error: str, source: str):
        """处理错误"""
        if source == "mainline":
            self.query_mainline_btn.setEnabled(True)
            self.mainline_status.setText(f"❌ 查询失败: {error}")
        elif source == "pool":
            self.query_pool_btn.setEnabled(True)
            self.pool_status.setText(f"❌ 查询失败: {error}")
        elif source == "rotation":
            self.analyze_rotation_btn.setEnabled(True)
            self.analyze_realtime_btn.setEnabled(True)
            self.rotation_status.setText(f"❌ 分析失败: {error}")
        elif source == "changes":
            self.query_changes_btn.setEnabled(True)
            self.changes_status.setText(f"❌ 查询失败: {error}")
    
    def _get_input_style(self) -> str:
        return f"""
            QDateEdit, QSpinBox {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 6px 10px;
            }}
        """
    
    def _get_combo_style(self) -> str:
        return f"""
            QComboBox {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 6px 10px;
                min-width: 100px;
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                selection-background-color: {Colors.PRIMARY};
            }}
        """
    
    def _get_table_style(self) -> str:
        return f"""
            QTableWidget {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                gridline-color: {Colors.BORDER_PRIMARY};
            }}
            QTableWidget::item {{
                padding: 6px;
                color: {Colors.TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_MUTED};
                padding: 8px;
                border: none;
                font-weight: 600;
            }}
        """

