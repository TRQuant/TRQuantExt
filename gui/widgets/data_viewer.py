# -*- coding: utf-8 -*-
"""
通用数据查看器
==============

功能:
1. 弹出式全屏数据查看
2. 支持表格、文本、JSON格式
3. 搜索、筛选、导出功能
4. 可复用于系统各处
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QTextEdit, QLineEdit,
    QTabWidget, QWidget, QHeaderView, QFrame, QFileDialog,
    QComboBox, QSplitter, QApplication, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QClipboard
import json
import pandas as pd
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from gui.styles.theme import Colors


class DataViewerDialog(QDialog):
    """
    通用数据查看器对话框
    
    支持多种数据格式:
    - 表格数据 (List[Dict] 或 DataFrame)
    - 文本数据 (str)
    - JSON数据 (dict)
    """
    
    def __init__(
        self,
        parent=None,
        title: str = "数据查看器",
        data: Any = None,
        data_type: str = "auto"
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)
        
        # 设置模态
        self.setModal(False)
        
        self.data = data
        self.data_type = data_type
        self.filtered_data = data
        
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        """设置UI"""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_PRIMARY};
            }}
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
            }}
            QPushButton {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY}20;
                border-color: {Colors.PRIMARY};
            }}
            QLineEdit {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 8px 12px;
            }}
            QTableWidget {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                gridline-color: {Colors.BORDER_PRIMARY};
            }}
            QTableWidget::item {{
                padding: 8px;
            }}
            QTableWidget::item:selected {{
                background-color: {Colors.PRIMARY}40;
            }}
            QHeaderView::section {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                padding: 10px;
                border: none;
                border-bottom: 1px solid {Colors.BORDER_PRIMARY};
                font-weight: 600;
            }}
            QTextEdit {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 13px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        
        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索...")
        self.search_input.setMaximumWidth(300)
        self.search_input.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_input)
        
        # 统计信息
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        toolbar.addWidget(self.stats_label)
        
        toolbar.addStretch()
        
        # 按钮组
        copy_btn = QPushButton("📋 复制")
        copy_btn.clicked.connect(self._copy_to_clipboard)
        toolbar.addWidget(copy_btn)
        
        export_btn = QPushButton("💾 导出")
        export_btn.clicked.connect(self._export_data)
        toolbar.addWidget(export_btn)
        
        fullscreen_btn = QPushButton("⛶ 最大化")
        fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        toolbar.addWidget(fullscreen_btn)
        
        close_btn = QPushButton("✕ 关闭")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ERROR}20;
                color: {Colors.ERROR};
                border: 1px solid {Colors.ERROR}40;
            }}
            QPushButton:hover {{
                background-color: {Colors.ERROR}40;
            }}
        """)
        close_btn.clicked.connect(self.close)
        toolbar.addWidget(close_btn)
        
        layout.addLayout(toolbar)
        
        # 内容区域
        self.content_stack = QTabWidget()
        self.content_stack.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {Colors.BG_SECONDARY};
            }}
            QTabBar::tab {{
                background-color: {Colors.BG_PRIMARY};
                color: {Colors.TEXT_MUTED};
                border: none;
                padding: 10px 20px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.PRIMARY};
                border-bottom: 2px solid {Colors.PRIMARY};
            }}
        """)
        
        # 表格视图
        self.table_tab = QWidget()
        table_layout = QVBoxLayout(self.table_tab)
        table_layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table_layout.addWidget(self.table)
        
        self.content_stack.addTab(self.table_tab, "📊 表格视图")
        
        # 文本视图
        self.text_tab = QWidget()
        text_layout = QVBoxLayout(self.text_tab)
        text_layout.setContentsMargins(0, 0, 0, 0)
        
        self.text_view = QTextEdit()
        self.text_view.setReadOnly(True)
        text_layout.addWidget(self.text_view)
        
        self.content_stack.addTab(self.text_tab, "📝 文本视图")
        
        # JSON视图
        self.json_tab = QWidget()
        json_layout = QVBoxLayout(self.json_tab)
        json_layout.setContentsMargins(0, 0, 0, 0)
        
        self.json_view = QTextEdit()
        self.json_view.setReadOnly(True)
        json_layout.addWidget(self.json_view)
        
        self.content_stack.addTab(self.json_tab, "🔤 JSON视图")
        
        layout.addWidget(self.content_stack)
    
    def _load_data(self):
        """加载数据到各视图"""
        if self.data is None:
            self.stats_label.setText("无数据")
            return
        
        # 自动检测数据类型
        if self.data_type == "auto":
            if isinstance(self.data, pd.DataFrame):
                self.data_type = "dataframe"
            elif isinstance(self.data, list) and self.data and isinstance(self.data[0], dict):
                self.data_type = "list_dict"
            elif isinstance(self.data, dict):
                self.data_type = "dict"
            elif isinstance(self.data, str):
                self.data_type = "text"
            else:
                self.data_type = "text"
        
        # 加载到表格
        self._load_table()
        
        # 加载到文本
        self._load_text()
        
        # 加载到JSON
        self._load_json()
        
        # 更新统计
        self._update_stats()
    
    def _load_table(self):
        """加载表格数据"""
        try:
            if isinstance(self.data, pd.DataFrame):
                df = self.data
            elif isinstance(self.data, list) and self.data and isinstance(self.data[0], dict):
                df = pd.DataFrame(self.data)
            else:
                # 无法转为表格
                self.table.setRowCount(0)
                return
            
            self.table.setRowCount(len(df))
            self.table.setColumnCount(len(df.columns))
            self.table.setHorizontalHeaderLabels([str(c) for c in df.columns])
            
            for i, (_, row) in enumerate(df.iterrows()):
                for j, value in enumerate(row):
                    item = QTableWidgetItem(str(value) if pd.notna(value) else "")
                    
                    # 数字列右对齐
                    if isinstance(value, (int, float)):
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                        # 涨跌幅着色
                        col_name = str(df.columns[j]).lower()
                        if '涨' in col_name or 'change' in col_name or 'pct' in col_name:
                            if value > 0:
                                item.setForeground(QColor("#10B981"))
                            elif value < 0:
                                item.setForeground(QColor("#EF4444"))
                    
                    self.table.setItem(i, j, item)
            
            # 调整列宽
            self.table.resizeColumnsToContents()
            
        except Exception as e:
            self.table.setRowCount(1)
            self.table.setColumnCount(1)
            self.table.setItem(0, 0, QTableWidgetItem(f"加载失败: {e}"))
    
    def _load_text(self):
        """加载文本数据"""
        try:
            if isinstance(self.data, str):
                self.text_view.setText(self.data)
            elif isinstance(self.data, pd.DataFrame):
                self.text_view.setText(self.data.to_string())
            elif isinstance(self.data, list):
                lines = []
                for i, item in enumerate(self.data):
                    if isinstance(item, dict):
                        lines.append(f"[{i}] " + " | ".join(f"{k}: {v}" for k, v in item.items()))
                    else:
                        lines.append(f"[{i}] {item}")
                self.text_view.setText("\n".join(lines))
            else:
                self.text_view.setText(str(self.data))
        except Exception as e:
            self.text_view.setText(f"加载失败: {e}")
    
    def _load_json(self):
        """加载JSON数据"""
        try:
            if isinstance(self.data, pd.DataFrame):
                json_str = self.data.to_json(orient='records', force_ascii=False, indent=2)
            elif isinstance(self.data, (dict, list)):
                json_str = json.dumps(self.data, ensure_ascii=False, indent=2, default=str)
            else:
                json_str = json.dumps({"data": str(self.data)}, ensure_ascii=False, indent=2)
            
            self.json_view.setText(json_str)
        except Exception as e:
            self.json_view.setText(f'{{"error": "{e}"}}')
    
    def _update_stats(self):
        """更新统计信息"""
        if isinstance(self.data, pd.DataFrame):
            rows, cols = self.data.shape
            self.stats_label.setText(f"共 {rows} 行 × {cols} 列")
        elif isinstance(self.data, list):
            self.stats_label.setText(f"共 {len(self.data)} 条记录")
        elif isinstance(self.data, dict):
            self.stats_label.setText(f"共 {len(self.data)} 个字段")
        elif isinstance(self.data, str):
            lines = self.data.count('\n') + 1
            self.stats_label.setText(f"共 {lines} 行, {len(self.data)} 字符")
    
    def _on_search(self, text: str):
        """搜索过滤"""
        if not text:
            self._load_data()
            return
        
        text = text.lower()
        
        # 表格过滤
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)
        
        # 统计可见行
        visible = sum(1 for row in range(self.table.rowCount()) if not self.table.isRowHidden(row))
        self.stats_label.setText(f"显示 {visible}/{self.table.rowCount()} 行")
    
    def _copy_to_clipboard(self):
        """复制到剪贴板"""
        current_tab = self.content_stack.currentIndex()
        
        clipboard = QApplication.clipboard()
        
        if current_tab == 0:  # 表格
            # 复制选中行或全部
            selected = self.table.selectedItems()
            if selected:
                rows = set(item.row() for item in selected)
                text_lines = []
                for row in sorted(rows):
                    row_data = []
                    for col in range(self.table.columnCount()):
                        item = self.table.item(row, col)
                        row_data.append(item.text() if item else "")
                    text_lines.append("\t".join(row_data))
                clipboard.setText("\n".join(text_lines))
            else:
                clipboard.setText(self.text_view.toPlainText())
        elif current_tab == 1:  # 文本
            clipboard.setText(self.text_view.toPlainText())
        else:  # JSON
            clipboard.setText(self.json_view.toPlainText())
        
        QMessageBox.information(self, "复制成功", "数据已复制到剪贴板")
    
    def _export_data(self):
        """导出数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出数据",
            f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "Excel文件 (*.xlsx);;CSV文件 (*.csv);;JSON文件 (*.json);;文本文件 (*.txt)"
        )
        
        if not file_path:
            return
        
        try:
            if file_path.endswith('.xlsx'):
                if isinstance(self.data, pd.DataFrame):
                    self.data.to_excel(file_path, index=False)
                elif isinstance(self.data, list):
                    pd.DataFrame(self.data).to_excel(file_path, index=False)
                else:
                    pd.DataFrame([{"data": str(self.data)}]).to_excel(file_path, index=False)
            elif file_path.endswith('.csv'):
                if isinstance(self.data, pd.DataFrame):
                    self.data.to_csv(file_path, index=False)
                elif isinstance(self.data, list):
                    pd.DataFrame(self.data).to_csv(file_path, index=False)
                else:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(str(self.data))
            elif file_path.endswith('.json'):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.json_view.toPlainText())
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.text_view.toPlainText())
            
            QMessageBox.information(self, "导出成功", f"数据已导出到:\n{file_path}")
            
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"错误: {e}")
    
    def _toggle_fullscreen(self):
        """切换全屏"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()


def show_data_viewer(
    parent=None,
    title: str = "数据查看器",
    data: Any = None,
    data_type: str = "auto"
) -> DataViewerDialog:
    """
    便捷函数：显示数据查看器
    
    Args:
        parent: 父窗口
        title: 窗口标题
        data: 要显示的数据
        data_type: 数据类型 ("auto", "dataframe", "list_dict", "dict", "text")
    
    Returns:
        DataViewerDialog 实例
    
    Example:
        >>> from gui.widgets.data_viewer import show_data_viewer
        >>> show_data_viewer(self, "扫描结果", stocks_list)
    """
    dialog = DataViewerDialog(parent, title, data, data_type)
    dialog.show()
    return dialog

