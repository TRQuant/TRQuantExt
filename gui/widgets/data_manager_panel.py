# -*- coding: utf-8 -*-
"""
数据管理面板
============

管理系统生成的所有数据：
- 报告文件（HTML）
- 策略文件（Python）
- 数据库数据（MongoDB）
- 缓存数据
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QTextBrowser, QSplitter, QMessageBox, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices
from pathlib import Path
from datetime import datetime
import json
import shutil
import logging

from gui.styles.theme import Colors, ButtonStyles
from gui.widgets.module_banner import ModuleBanner

logger = logging.getLogger(__name__)


class DataManagerPanel(QWidget):
    """数据管理面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._load_data()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Banner
        banner = ModuleBanner(
            title="📁 数据管理中心",
            subtitle="统一管理报告、策略、数据库和缓存",
            gradient_colors=(Colors.INFO, Colors.PRIMARY)
        )
        layout.addWidget(banner)
        
        # 内容区域
        content = QWidget()
        content.setStyleSheet(f"background: {Colors.BG_PRIMARY};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(16)
        
        # 统计卡片
        stats_layout = QHBoxLayout()
        self.report_count = self._create_stat_card("📄", "报告文件", "0")
        self.strategy_count = self._create_stat_card("🐍", "策略文件", "0")
        self.db_count = self._create_stat_card("🗄️", "数据集合", "0")
        self.cache_size = self._create_stat_card("💾", "缓存大小", "0 MB")
        
        stats_layout.addWidget(self.report_count)
        stats_layout.addWidget(self.strategy_count)
        stats_layout.addWidget(self.db_count)
        stats_layout.addWidget(self.cache_size)
        content_layout.addLayout(stats_layout)
        
        # Tab页
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                background: {Colors.BG_SECONDARY};
            }}
            QTabBar::tab {{
                background: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_SECONDARY};
                padding: 10px 20px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        
        # 报告管理Tab
        tabs.addTab(self._create_reports_tab(), "📄 报告文件")
        
        # 策略管理Tab
        tabs.addTab(self._create_strategies_tab(), "🐍 策略文件")
        
        # 数据库管理Tab
        tabs.addTab(self._create_database_tab(), "🗄️ 数据库")
        
        # 缓存管理Tab
        tabs.addTab(self._create_cache_tab(), "💾 缓存")
        
        content_layout.addWidget(tabs, 1)
        layout.addWidget(content, 1)
    
    def _create_stat_card(self, icon: str, label: str, value: str) -> QFrame:
        """创建统计卡片"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(8)
        
        # 图标和标签
        header = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 24px;")
        header.addWidget(icon_label)
        
        title = QLabel(label)
        title.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)
        
        # 数值
        value_label = QLabel(value)
        value_label.setObjectName("value")
        value_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 28px; font-weight: bold;")
        layout.addWidget(value_label)
        
        return card
    
    def _create_reports_tab(self) -> QWidget:
        """报告管理Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setStyleSheet(ButtonStyles.SECONDARY)
        refresh_btn.clicked.connect(self._refresh_reports)
        toolbar.addWidget(refresh_btn)
        
        open_folder_btn = QPushButton("📂 打开目录")
        open_folder_btn.setStyleSheet(ButtonStyles.SECONDARY)
        open_folder_btn.clicked.connect(self._open_reports_folder)
        toolbar.addWidget(open_folder_btn)
        
        clean_btn = QPushButton("🗑️ 清理旧报告")
        clean_btn.setStyleSheet(ButtonStyles.DANGER)
        clean_btn.clicked.connect(self._clean_old_reports)
        toolbar.addWidget(clean_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # 报告列表
        self.reports_tree = QTreeWidget()
        self.reports_tree.setHeaderLabels(["文件名", "类型", "大小", "修改时间"])
        self.reports_tree.setStyleSheet(f"""
            QTreeWidget {{
                background: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                color: {Colors.TEXT_PRIMARY};
            }}
            QTreeWidget::item:hover {{ background: {Colors.BG_HOVER}; }}
            QTreeWidget::item:selected {{ background: {Colors.PRIMARY}; }}
            QHeaderView::section {{
                background: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_SECONDARY};
                padding: 8px;
                border: none;
            }}
        """)
        self.reports_tree.itemDoubleClicked.connect(self._open_report)
        layout.addWidget(self.reports_tree, 1)
        
        return widget
    
    def _create_strategies_tab(self) -> QWidget:
        """策略管理Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setStyleSheet(ButtonStyles.SECONDARY)
        refresh_btn.clicked.connect(self._refresh_strategies)
        toolbar.addWidget(refresh_btn)
        
        open_folder_btn = QPushButton("📂 打开目录")
        open_folder_btn.setStyleSheet(ButtonStyles.SECONDARY)
        open_folder_btn.clicked.connect(self._open_strategies_folder)
        toolbar.addWidget(open_folder_btn)
        
        export_btn = QPushButton("📤 导出策略")
        export_btn.setStyleSheet(ButtonStyles.PRIMARY)
        export_btn.clicked.connect(self._export_strategy)
        toolbar.addWidget(export_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 策略列表
        self.strategies_tree = QTreeWidget()
        self.strategies_tree.setHeaderLabels(["文件名", "大小", "修改时间"])
        self.strategies_tree.setStyleSheet(f"""
            QTreeWidget {{
                background: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        self.strategies_tree.itemClicked.connect(self._preview_strategy)
        splitter.addWidget(self.strategies_tree)
        
        # 预览区域
        self.strategy_preview = QTextBrowser()
        self.strategy_preview.setStyleSheet(f"""
            QTextBrowser {{
                background: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                color: {Colors.TEXT_PRIMARY};
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }}
        """)
        splitter.addWidget(self.strategy_preview)
        
        splitter.setSizes([300, 500])
        layout.addWidget(splitter, 1)
        
        return widget
    
    def _create_database_tab(self) -> QWidget:
        """数据库管理Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setStyleSheet(ButtonStyles.SECONDARY)
        refresh_btn.clicked.connect(self._refresh_database)
        toolbar.addWidget(refresh_btn)
        
        export_btn = QPushButton("📤 导出数据")
        export_btn.setStyleSheet(ButtonStyles.PRIMARY)
        export_btn.clicked.connect(self._export_database)
        toolbar.addWidget(export_btn)
        
        clean_btn = QPushButton("🗑️ 清理数据")
        clean_btn.setStyleSheet(ButtonStyles.DANGER)
        clean_btn.clicked.connect(self._clean_database)
        toolbar.addWidget(clean_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # 数据库集合表格
        self.db_table = QTableWidget()
        self.db_table.setColumnCount(4)
        self.db_table.setHorizontalHeaderLabels(["集合名称", "文档数", "大小", "最后更新"])
        self.db_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.db_table.setStyleSheet(f"""
            QTableWidget {{
                background: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                color: {Colors.TEXT_PRIMARY};
                gridline-color: {Colors.BORDER_PRIMARY};
            }}
            QHeaderView::section {{
                background: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_SECONDARY};
                padding: 10px;
                border: none;
            }}
        """)
        layout.addWidget(self.db_table, 1)
        
        return widget
    
    def _create_cache_tab(self) -> QWidget:
        """缓存管理Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 缓存信息
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{
                background: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 12px;
                padding: 20px;
            }}
        """)
        info_layout = QVBoxLayout(info_frame)
        
        self.cache_info = QLabel("正在加载缓存信息...")
        self.cache_info.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 14px;")
        self.cache_info.setWordWrap(True)
        info_layout.addWidget(self.cache_info)
        
        layout.addWidget(info_frame)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        clear_cache_btn = QPushButton("🗑️ 清除全部缓存")
        clear_cache_btn.setStyleSheet(ButtonStyles.DANGER)
        clear_cache_btn.setFixedHeight(44)
        clear_cache_btn.clicked.connect(self._clear_cache)
        btn_layout.addWidget(clear_cache_btn)
        
        clear_old_btn = QPushButton("🧹 清除7天前缓存")
        clear_old_btn.setStyleSheet(ButtonStyles.WARNING)
        clear_old_btn.setFixedHeight(44)
        clear_old_btn.clicked.connect(self._clear_old_cache)
        btn_layout.addWidget(clear_old_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        layout.addStretch()
        
        return widget
    
    def _load_data(self):
        """加载数据"""
        self._refresh_reports()
        self._refresh_strategies()
        self._refresh_database()
        self._refresh_cache()
    
    def _refresh_reports(self):
        """刷新报告列表"""
        self.reports_tree.clear()
        
        base_dir = Path(__file__).parent.parent.parent
        reports_dir = base_dir / "reports"
        
        if not reports_dir.exists():
            return
        
        count = 0
        
        # 按日期分组
        for item in sorted(reports_dir.iterdir(), reverse=True):
            if item.is_dir():
                # 日期文件夹
                date_item = QTreeWidgetItem([item.name, "📁 文件夹", "", ""])
                self.reports_tree.addTopLevelItem(date_item)
                
                for f in sorted(item.glob("*.html"), reverse=True):
                    size = f"{f.stat().st_size / 1024:.1f} KB"
                    mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime('%H:%M:%S')
                    child = QTreeWidgetItem([f.name, "HTML", size, mtime])
                    child.setData(0, Qt.ItemDataRole.UserRole, str(f))
                    date_item.addChild(child)
                    count += 1
                
                date_item.setExpanded(True)
            
            elif item.suffix == ".html":
                size = f"{item.stat().st_size / 1024:.1f} KB"
                mtime = datetime.fromtimestamp(item.stat().st_mtime).strftime('%m-%d %H:%M')
                
                # 判断类型
                report_type = "趋势报告" if "trend" in item.name else "主线报告" if "mainline" in item.name else "报告"
                
                file_item = QTreeWidgetItem([item.name, report_type, size, mtime])
                file_item.setData(0, Qt.ItemDataRole.UserRole, str(item))
                self.reports_tree.addTopLevelItem(file_item)
                count += 1
        
        # 更新统计
        self.report_count.findChild(QLabel, "value").setText(str(count))
    
    def _refresh_strategies(self):
        """刷新策略列表"""
        self.strategies_tree.clear()
        
        base_dir = Path(__file__).parent.parent.parent
        strategies_dir = base_dir / "strategies" / "ptrade"
        
        if not strategies_dir.exists():
            return
        
        count = 0
        for f in sorted(strategies_dir.glob("*.py"), reverse=True):
            size = f"{f.stat().st_size / 1024:.1f} KB"
            mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime('%m-%d %H:%M')
            
            item = QTreeWidgetItem([f.name, size, mtime])
            item.setData(0, Qt.ItemDataRole.UserRole, str(f))
            self.strategies_tree.addTopLevelItem(item)
            count += 1
        
        # 更新统计
        self.strategy_count.findChild(QLabel, "value").setText(str(count))
    
    def _refresh_database(self):
        """刷新数据库信息"""
        self.db_table.setRowCount(0)
        
        try:
            from pymongo import MongoClient
            client = MongoClient('localhost', 27017, serverSelectionTimeoutMS=3000)
            db = client['trquant']
            
            collections = db.list_collection_names()
            self.db_table.setRowCount(len(collections))
            
            for i, coll_name in enumerate(sorted(collections)):
                coll = db[coll_name]
                doc_count = coll.count_documents({})
                
                # 获取最后更新时间
                last_doc = coll.find_one(sort=[("timestamp", -1)]) or coll.find_one(sort=[("_id", -1)])
                if last_doc:
                    if "timestamp" in last_doc:
                        last_update = last_doc["timestamp"].strftime('%m-%d %H:%M') if hasattr(last_doc["timestamp"], 'strftime') else str(last_doc["timestamp"])[:16]
                    else:
                        last_update = "-"
                else:
                    last_update = "-"
                
                # 估算大小
                stats = db.command("collstats", coll_name)
                size = f"{stats.get('size', 0) / 1024:.1f} KB"
                
                self.db_table.setItem(i, 0, QTableWidgetItem(coll_name))
                self.db_table.setItem(i, 1, QTableWidgetItem(str(doc_count)))
                self.db_table.setItem(i, 2, QTableWidgetItem(size))
                self.db_table.setItem(i, 3, QTableWidgetItem(last_update))
            
            # 更新统计
            self.db_count.findChild(QLabel, "value").setText(str(len(collections)))
            
        except Exception as e:
            logger.warning(f"刷新数据库失败: {e}")
            self.db_count.findChild(QLabel, "value").setText("N/A")
    
    def _refresh_cache(self):
        """刷新缓存信息"""
        cache_dir = Path.home() / ".cache" / "trquant"
        local_dir = Path.home() / ".local" / "share" / "trquant"
        
        total_size = 0
        file_count = 0
        
        for d in [cache_dir, local_dir]:
            if d.exists():
                for f in d.rglob("*"):
                    if f.is_file():
                        total_size += f.stat().st_size
                        file_count += 1
        
        size_mb = total_size / (1024 * 1024)
        
        self.cache_info.setText(f"""
<b>缓存目录：</b><br/>
• {cache_dir}<br/>
• {local_dir}<br/><br/>
<b>统计：</b><br/>
• 文件数：{file_count} 个<br/>
• 总大小：{size_mb:.2f} MB
        """)
        
        # 更新统计
        self.cache_size.findChild(QLabel, "value").setText(f"{size_mb:.1f} MB")
    
    def _open_report(self, item, col):
        """打开报告文件"""
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path and Path(path).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
    
    def _preview_strategy(self, item, col):
        """预览策略代码"""
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path and Path(path).exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    code = f.read()
                self.strategy_preview.setPlainText(code)
            except Exception as e:
                self.strategy_preview.setPlainText(f"读取失败: {e}")
    
    def _open_reports_folder(self):
        """打开报告目录"""
        reports_dir = Path(__file__).parent.parent.parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(reports_dir)))
    
    def _open_strategies_folder(self):
        """打开策略目录"""
        strategies_dir = Path(__file__).parent.parent.parent / "strategies" / "ptrade"
        strategies_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(strategies_dir)))
    
    def _clean_old_reports(self):
        """清理旧报告"""
        reply = QMessageBox.question(
            self, "确认", "确定要删除7天前的报告吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            import time
            threshold = time.time() - 7 * 24 * 3600
            
            reports_dir = Path(__file__).parent.parent.parent / "reports"
            deleted = 0
            
            for f in reports_dir.rglob("*.html"):
                if f.stat().st_mtime < threshold:
                    f.unlink()
                    deleted += 1
            
            QMessageBox.information(self, "完成", f"已删除 {deleted} 个旧报告")
            self._refresh_reports()
    
    def _export_strategy(self):
        """导出策略"""
        selected = self.strategies_tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "提示", "请先选择要导出的策略")
            return
        
        path = selected.data(0, Qt.ItemDataRole.UserRole)
        if not path:
            return
        
        dest, _ = QFileDialog.getSaveFileName(
            self, "导出策略", selected.text(0), "Python文件 (*.py)"
        )
        
        if dest:
            shutil.copy(path, dest)
            QMessageBox.information(self, "完成", f"策略已导出到:\n{dest}")
    
    def _export_database(self):
        """导出数据库"""
        dest_dir = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if not dest_dir:
            return
        
        try:
            from pymongo import MongoClient
            client = MongoClient('localhost', 27017)
            db = client['trquant']
            
            dest_path = Path(dest_dir) / f"trquant_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            export_data = {}
            for coll_name in db.list_collection_names():
                docs = list(db[coll_name].find())
                # 转换ObjectId
                for doc in docs:
                    doc['_id'] = str(doc['_id'])
                    for k, v in doc.items():
                        if hasattr(v, 'isoformat'):
                            doc[k] = v.isoformat()
                export_data[coll_name] = docs
            
            with open(dest_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            QMessageBox.information(self, "完成", f"数据已导出到:\n{dest_path}")
            
        except Exception as e:
            QMessageBox.warning(self, "导出失败", str(e))
    
    def _clean_database(self):
        """清理数据库"""
        reply = QMessageBox.question(
            self, "确认", "确定要清理所有数据库数据吗？\n此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from pymongo import MongoClient
                client = MongoClient('localhost', 27017)
                client.drop_database('trquant')
                QMessageBox.information(self, "完成", "数据库已清理")
                self._refresh_database()
            except Exception as e:
                QMessageBox.warning(self, "失败", str(e))
    
    def _clear_cache(self):
        """清除全部缓存"""
        reply = QMessageBox.question(
            self, "确认", "确定要清除全部缓存吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            cache_dir = Path.home() / ".cache" / "trquant"
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            QMessageBox.information(self, "完成", "缓存已清除")
            self._refresh_cache()
    
    def _clear_old_cache(self):
        """清除7天前缓存"""
        import time
        threshold = time.time() - 7 * 24 * 3600
        
        cache_dir = Path.home() / ".cache" / "trquant"
        deleted = 0
        
        if cache_dir.exists():
            for f in cache_dir.rglob("*"):
                if f.is_file() and f.stat().st_mtime < threshold:
                    f.unlink()
                    deleted += 1
        
        QMessageBox.information(self, "完成", f"已清除 {deleted} 个旧缓存文件")
        self._refresh_cache()

