# -*- coding: utf-8 -*-
"""
因子筛选标签页
==============

在候选池面板中添加因子筛选功能，使用FactorPoolIntegration
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QComboBox, QDoubleSpinBox,
    QGroupBox, QFormLayout, QProgressBar, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
import logging
from datetime import datetime
from typing import List, Optional

from ..styles.theme import Colors
from core.factors import FactorPoolIntegration, StockSignal

logger = logging.getLogger(__name__)


class FactorFilterWorker(QThread):
    """因子筛选工作线程"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list)  # List[StockSignal]
    error = pyqtSignal(str)
    
    def __init__(self, integration: FactorPoolIntegration, stocks: List[str], 
                 date: str, period: str = "medium", top_n: int = 30):
        super().__init__()
        self.integration = integration
        self.stocks = stocks
        self.date = date
        self.period = period
        self.top_n = top_n
    
    def run(self):
        try:
            self.progress.emit(10, "开始因子筛选...")
            
            # 获取主线评分（如果有）
            mainline_scores = None  # TODO: 从MongoDB读取主线评分
            
            self.progress.emit(30, "计算因子评分...")
            
            # 使用FactorPoolIntegration处理候选池
            signals = self.integration.process_candidate_pool(
                stocks=self.stocks,
                date=self.date,
                period=self.period,
                mainline_scores=mainline_scores,
                top_n=self.top_n
            )
            
            self.progress.emit(100, "完成")
            self.finished.emit(signals)
            
        except Exception as e:
            logger.error(f"因子筛选失败: {e}")
            self.error.emit(str(e))


class FactorFilterTab(QWidget):
    """因子筛选标签页"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.integration = None
        self.jq_client = None
        self.current_signals = []
        self.worker = None
        self._init_ui()
    
    def set_jq_client(self, jq_client):
        """设置JQData客户端"""
        self.jq_client = jq_client
        try:
            from core.factors import create_factor_pool_integration
            self.integration = create_factor_pool_integration(jq_client=jq_client)
        except Exception as e:
            logger.error(f"初始化因子集成失败: {e}")
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel("🔍 因子筛选")
        title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {Colors.PRIMARY};
            margin-bottom: 10px;
        """)
        layout.addWidget(title)
        
        # 参数设置
        params_group = QGroupBox("筛选参数")
        params_layout = QFormLayout()
        
        self.period_combo = QComboBox()
        self.period_combo.addItems(["短期", "中期", "长期"])
        self.period_combo.setCurrentText("中期")
        params_layout.addRow("投资周期:", self.period_combo)
        
        self.top_n_spin = QDoubleSpinBox()
        self.top_n_spin.setRange(10, 100)
        self.top_n_spin.setValue(30)
        self.top_n_spin.setDecimals(0)
        params_layout.addRow("选择数量:", self.top_n_spin)
        
        self.min_score_spin = QDoubleSpinBox()
        self.min_score_spin.setRange(0, 100)
        self.min_score_spin.setValue(60)
        params_layout.addRow("最低得分:", self.min_score_spin)
        
        self.neutralize_check = QCheckBox("行业/市值中性化")
        self.neutralize_check.setChecked(True)
        params_layout.addRow("", self.neutralize_check)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        self.filter_btn = QPushButton("🚀 开始因子筛选")
        self.filter_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.ACCENT};
            }}
            QPushButton:disabled {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_MUTED};
            }}
        """)
        self.filter_btn.clicked.connect(self._start_filter)
        btn_layout.addWidget(self.filter_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 进度条
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        layout.addWidget(self.status_label)
        
        # 结果表格
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "排名", "代码", "名称", "综合得分", "因子得分", "主线得分",
            "信号强度", "入选理由"
        ])
        self.table.horizontalHeader().setStyleSheet(f"""
            QHeaderView::section {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                padding: 8px;
                border: none;
                font-weight: bold;
            }}
        """)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
    
    def _start_filter(self):
        """开始因子筛选"""
        if self.integration is None:
            QMessageBox.warning(self, "错误", "因子模块未初始化，请先连接JQData")
            return
        
        # 获取候选股票（从父面板）
        parent = self.parent()
        while parent and not hasattr(parent, '_all_stocks'):
            parent = parent.parent()
        
        if not parent or not hasattr(parent, '_all_stocks') or not parent._all_stocks:
            QMessageBox.warning(self, "提示", "请先在"综合总览"标签页扫描股票")
            return
        
        # 提取股票代码
        stocks = []
        for s in parent._all_stocks:
            code = s.get("code", "")
            if code:
                # 转换为JQData格式
                if code.endswith(('.XSHG', '.XSHE')):
                    stocks.append(code)
                elif len(code) == 6:
                    # 判断市场
                    if code.startswith(('60', '68')):
                        stocks.append(f"{code}.XSHG")
                    else:
                        stocks.append(f"{code}.XSHE")
        
        if not stocks:
            QMessageBox.warning(self, "提示", "未找到有效的股票代码")
            return
        
        # 获取参数
        period_map = {"短期": "short", "中期": "medium", "长期": "long"}
        period = period_map.get(self.period_combo.currentText(), "medium")
        top_n = int(self.top_n_spin.value())
        date = datetime.now().strftime('%Y-%m-%d')
        
        # 启动工作线程
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
        
        self.worker = FactorFilterWorker(
            self.integration, stocks, date, period, top_n
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        
        self.filter_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.status_label.setText("正在筛选...")
        
        self.worker.start()
    
    def _on_progress(self, value: int, message: str):
        """进度更新"""
        self.progress.setValue(value)
        self.status_label.setText(message)
    
    def _on_finished(self, signals: List[StockSignal]):
        """筛选完成"""
        self.current_signals = signals
        self._update_table(signals)
        
        self.filter_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.status_label.setText(f"✅ 筛选完成，共 {len(signals)} 只股票")
    
    def _on_error(self, error: str):
        """错误处理"""
        self.filter_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.status_label.setText(f"❌ 筛选失败: {error}")
        QMessageBox.critical(self, "错误", f"因子筛选失败:\n{error}")
    
    def _update_table(self, signals: List[StockSignal]):
        """更新表格"""
        # 应用最低得分筛选
        min_score = self.min_score_spin.value()
        filtered = [s for s in signals if s.combined_score >= min_score]
        
        self.table.setRowCount(len(filtered))
        
        for row, signal in enumerate(filtered):
            # 排名
            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            
            # 代码
            code_item = QTableWidgetItem(signal.code)
            self.table.setItem(row, 1, code_item)
            
            # 名称
            self.table.setItem(row, 2, QTableWidgetItem(signal.name or signal.code))
            
            # 综合得分
            score_item = QTableWidgetItem(f"{signal.combined_score:.2f}")
            if signal.combined_score >= 80:
                score_item.setForeground(QColor(Colors.SUCCESS))
            elif signal.combined_score >= 60:
                score_item.setForeground(QColor(Colors.WARNING))
            self.table.setItem(row, 3, score_item)
            
            # 因子得分
            self.table.setItem(row, 4, QTableWidgetItem(f"{signal.factor_score:.2f}"))
            
            # 主线得分
            self.table.setItem(row, 5, QTableWidgetItem(f"{signal.mainline_score:.2f}"))
            
            # 信号强度
            strength_item = QTableWidgetItem(signal.signal_strength)
            if signal.signal_strength == "strong":
                strength_item.setForeground(QColor(Colors.SUCCESS))
            elif signal.signal_strength == "weak":
                strength_item.setForeground(QColor(Colors.ERROR))
            self.table.setItem(row, 6, strength_item)
            
            # 入选理由
            self.table.setItem(row, 7, QTableWidgetItem(signal.entry_reason))
        
        self.table.resizeColumnsToContents()

