# -*- coding: utf-8 -*-
"""
数据源状态显示组件
==================

显示所有数据源的状态和账户信息
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QProgressBar, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont
import logging
from datetime import datetime
from typing import Dict

from gui.styles.theme import Colors, ButtonStyles

logger = logging.getLogger(__name__)


class DataSourceRefreshWorker(QThread):
    """数据源刷新工作线程"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def run(self):
        try:
            from core.data_source_manager import get_data_source_manager
            manager = get_data_source_manager()
            manager.initialize()
            
            result = {}
            for source_type, status in manager.get_all_status().items():
                result[source_type.value] = {
                    'is_available': status.is_available,
                    'account_type': status.account_type.value,
                    'start_date': status.start_date,
                    'end_date': status.end_date,
                    'is_realtime': status.is_realtime,
                    'error': status.error_message
                }
            
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))


class DataSourceStatusWidget(QWidget):
    """数据源状态显示组件"""
    
    status_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._load_status()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 标题行
        title_row = QHBoxLayout()
        title = QLabel("📡 数据源状态")
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; font-weight: bold;")
        title_row.addWidget(title)
        title_row.addStretch()
        
        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.PRIMARY};
                border: 1px solid {Colors.PRIMARY};
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY}20;
            }}
        """)
        self.refresh_btn.clicked.connect(self._refresh_status)
        title_row.addWidget(self.refresh_btn)
        
        layout.addLayout(title_row)
        
        # 数据源卡片容器
        self.cards_layout = QGridLayout()
        self.cards_layout.setSpacing(12)
        layout.addLayout(self.cards_layout)
        
        # 初始化卡片
        self.source_cards: Dict[str, QFrame] = {}
        self._create_source_cards()
        
        # 状态说明
        hint = QLabel("💡 试用账户数据范围有限，建议升级正式账户获取完整数据")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px; padding: 8px;")
        layout.addWidget(hint)
    
    def _create_source_cards(self):
        """创建数据源卡片"""
        sources = [
            ("jqdata", "聚宽JQData", "🔷", "主数据源"),
            ("akshare", "AKShare", "🟢", "备用数据源"),
            ("baostock", "Baostock", "🔵", "历史数据"),
            ("local_cache", "本地缓存", "💾", "MongoDB")
        ]
        
        for i, (key, name, icon, desc) in enumerate(sources):
            card = self._create_card(key, name, icon, desc)
            self.source_cards[key] = card
            self.cards_layout.addWidget(card, i // 2, i % 2)
    
    def _create_card(self, key: str, name: str, icon: str, desc: str) -> QFrame:
        """创建单个数据源卡片"""
        card = QFrame()
        card.setObjectName(key)
        card.setStyleSheet(f"""
            QFrame#{key} {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # 标题行
        header = QHBoxLayout()
        title = QLabel(f"{icon} {name}")
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 13px; font-weight: bold;")
        header.addWidget(title)
        
        status_label = QLabel("检测中...")
        status_label.setObjectName(f"{key}_status")
        status_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
        header.addWidget(status_label)
        header.addStretch()
        
        layout.addLayout(header)
        
        # 详情
        detail_label = QLabel(desc)
        detail_label.setObjectName(f"{key}_detail")
        detail_label.setWordWrap(True)
        detail_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(detail_label)
        
        # 日期范围
        date_label = QLabel("")
        date_label.setObjectName(f"{key}_date")
        date_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10px;")
        layout.addWidget(date_label)
        
        return card
    
    def _load_status(self):
        """加载数据源状态"""
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("加载中...")
        
        self.worker = DataSourceRefreshWorker()
        self.worker.finished.connect(self._on_status_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()
    
    def _refresh_status(self):
        """刷新状态"""
        self._load_status()
    
    def _on_status_loaded(self, result: dict):
        """状态加载完成"""
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 刷新")
        
        for key, info in result.items():
            if key in self.source_cards:
                self._update_card(key, info)
        
        self.status_changed.emit(result)
    
    def _update_card(self, key: str, info: dict):
        """更新卡片显示"""
        card = self.source_cards.get(key)
        if not card:
            return
        
        status_label = card.findChild(QLabel, f"{key}_status")
        detail_label = card.findChild(QLabel, f"{key}_detail")
        date_label = card.findChild(QLabel, f"{key}_date")
        
        is_available = info.get('is_available', False)
        account_type = info.get('account_type', 'unknown')
        
        if is_available:
            status_label.setText("✅ 已连接")
            status_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 11px;")
            
            # 账户类型详情
            type_text = {
                'trial': '试用版',
                'standard': '标准版',
                'premium': '高级版',
            }.get(account_type, account_type)
            
            if info.get('is_realtime'):
                type_text += " (实时)"
            
            detail_label.setText(type_text)
            detail_label.setStyleSheet(f"color: {Colors.PRIMARY}; font-size: 11px; font-weight: bold;")
            
            # 日期范围
            start = info.get('start_date', '')
            end = info.get('end_date', '')
            if start and end:
                date_label.setText(f"📅 {start} ~ {end}")
            else:
                date_label.setText("")
        else:
            status_label.setText("❌ 未连接")
            status_label.setStyleSheet(f"color: {Colors.ERROR}; font-size: 11px;")
            
            error = info.get('error', '未知错误')
            detail_label.setText(error[:30] + "..." if len(error) > 30 else error)
            detail_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
            date_label.setText("")
        
        # 更新卡片边框颜色
        border_color = Colors.SUCCESS if is_available else Colors.BORDER_PRIMARY
        card.setStyleSheet(f"""
            QFrame#{key} {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
    
    def _on_error(self, error: str):
        """错误处理"""
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 刷新")
        logger.error(f"数据源状态加载失败: {error}")


class DataSourceStatusBar(QFrame):
    """
    数据源状态栏（紧凑版，用于主窗口底部）
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._load_status()
    
    def _init_ui(self):
        """初始化UI"""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border-top: 1px solid {Colors.BORDER_PRIMARY};
                padding: 4px 12px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(16)
        
        # JQData状态
        self.jqdata_label = QLabel("🔷 JQData: 检测中...")
        self.jqdata_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(self.jqdata_label)
        
        # AKShare状态
        self.akshare_label = QLabel("🟢 AKShare: 检测中...")
        self.akshare_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(self.akshare_label)
        
        layout.addStretch()
        
        # 最后更新时间
        self.update_time_label = QLabel("")
        self.update_time_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10px;")
        layout.addWidget(self.update_time_label)
    
    def _load_status(self):
        """加载状态"""
        self.worker = DataSourceRefreshWorker()
        self.worker.finished.connect(self._on_status_loaded)
        self.worker.start()
    
    def _on_status_loaded(self, result: dict):
        """状态加载完成"""
        # JQData
        jq = result.get('jqdata', {})
        if jq.get('is_available'):
            account_type = {
                'trial': '试用',
                'standard': '标准',
                'premium': '高级'
            }.get(jq.get('account_type', ''), '')
            self.jqdata_label.setText(f"🔷 JQData: ✅ {account_type}")
            self.jqdata_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 11px;")
        else:
            self.jqdata_label.setText("🔷 JQData: ❌")
            self.jqdata_label.setStyleSheet(f"color: {Colors.ERROR}; font-size: 11px;")
        
        # AKShare
        ak = result.get('akshare', {})
        if ak.get('is_available'):
            self.akshare_label.setText("🟢 AKShare: ✅")
            self.akshare_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 11px;")
        else:
            self.akshare_label.setText("🟢 AKShare: ❌")
            self.akshare_label.setStyleSheet(f"color: {Colors.ERROR}; font-size: 11px;")
        
        # 更新时间
        self.update_time_label.setText(f"更新: {datetime.now().strftime('%H:%M')}")

