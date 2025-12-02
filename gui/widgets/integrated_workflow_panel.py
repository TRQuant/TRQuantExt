# -*- coding: utf-8 -*-
"""
集成工作流程面板
================

调用 WorkflowOrchestrator 统一编排工作流程
不重复实现逻辑，仅负责UI展示
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSplitter, QTextBrowser, QProgressBar,
    QMessageBox, QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QUrl, QTimer
from PyQt6.QtGui import QDesktopServices
from datetime import datetime
from pathlib import Path
import logging
import json

from gui.styles.theme import Colors, ButtonStyles

logger = logging.getLogger(__name__)


# ============================================================
# 工作流程步骤定义
# ============================================================

WORKFLOW_STEPS = [
    {"id": "data_source", "name": "信息获取", "icon": "📡", "color": Colors.INFO},
    {"id": "market_trend", "name": "市场趋势", "icon": "📈", "color": Colors.PRIMARY},
    {"id": "mainline", "name": "投资主线", "icon": "🔥", "color": "#F59E0B"},
    {"id": "candidate_pool", "name": "候选池构建", "icon": "📦", "color": Colors.ACCENT},
    {"id": "factor", "name": "因子构建", "icon": "🧮", "color": Colors.SUCCESS},
    {"id": "strategy", "name": "策略生成", "icon": "💻", "color": Colors.WARNING},
]


# ============================================================
# 工作流程执行线程
# ============================================================

class WorkflowWorker(QThread):
    """工作流程执行线程 - 调用WorkflowOrchestrator"""
    progress = pyqtSignal(str, int, str)  # step_id, progress, message
    step_finished = pyqtSignal(str, dict)  # step_id, result
    all_finished = pyqtSignal(dict)  # full_result
    error = pyqtSignal(str, str)  # step_id, error
    
    def __init__(self, step_id: str = None, run_all: bool = False, parent=None):
        super().__init__(parent)
        self.step_id = step_id
        self.run_all = run_all
        self._is_cancelled = False
    
    def cancel(self):
        self._is_cancelled = True
    
    def run(self):
        try:
            from core.workflow_orchestrator import get_workflow_orchestrator
            
            orchestrator = get_workflow_orchestrator()
            
            if self.run_all:
                # 执行全部步骤
                def callback(step_name, result):
                    step_id = self._name_to_id(step_name)
                    self.step_finished.emit(step_id, {
                        "success": result.success,
                        "summary": result.summary,
                        "details": result.details
                    })
                
                full_result = orchestrator.run_full_workflow(callback=callback)
                
                self.all_finished.emit({
                    "success": full_result.success,
                    "strategy_file": full_result.strategy_file,
                    "total_time": full_result.total_time
                })
            else:
                # 执行单个步骤
                self.progress.emit(self.step_id, 10, "开始执行...")
                
                step_map = {
                    "data_source": orchestrator.check_data_sources,
                    "market_trend": orchestrator.analyze_market_trend,
                    "mainline": orchestrator.identify_mainlines,
                    "candidate_pool": orchestrator.build_candidate_pool,
                    "factor": orchestrator.recommend_factors,
                    "strategy": orchestrator.generate_strategy,
                }
                
                if self.step_id in step_map:
                    self.progress.emit(self.step_id, 50, "执行中...")
                    result = step_map[self.step_id]()
                    self.progress.emit(self.step_id, 100, "完成")
                    
                    self.step_finished.emit(self.step_id, {
                        "success": result.success,
                        "summary": result.summary,
                        "details": result.details
                    })
                else:
                    self.error.emit(self.step_id, f"未知步骤: {self.step_id}")
                    
        except Exception as e:
            import traceback
            logger.error(traceback.format_exc())
            self.error.emit(self.step_id or "unknown", str(e))
    
    def _name_to_id(self, name: str) -> str:
        """步骤名称转ID"""
        name_map = {
            "数据源": "data_source",
            "数据源检测": "data_source",
            "市场趋势": "market_trend",
            "投资主线": "mainline",
            "候选池": "candidate_pool",
            "候选池构建": "candidate_pool",
            "因子推荐": "factor",
            "策略生成": "strategy",
        }
        return name_map.get(name, name)


# ============================================================
# 步骤卡片
# ============================================================

class StepCard(QFrame):
    """步骤卡片"""
    clicked = pyqtSignal(str)
    
    def __init__(self, step: dict, parent=None):
        super().__init__(parent)
        self.step = step
        self._running = False
        self._completed = False
        self._init_ui()
    
    def _init_ui(self):
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(72)
        self._update_style()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)
        
        # 图标
        icon = QLabel(self.step["icon"])
        icon.setStyleSheet("font-size: 26px;")
        icon.setFixedWidth(36)
        layout.addWidget(icon)
        
        # 名称
        name = QLabel(self.step["name"])
        name.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(name, 1)
        
        # 状态
        self.status = QLabel("▶️")
        self.status.setStyleSheet("font-size: 16px;")
        layout.addWidget(self.status)
    
    def _update_style(self):
        border = Colors.WARNING if self._running else (Colors.SUCCESS if self._completed else Colors.BORDER_PRIMARY)
        self.setStyleSheet(f"""
            QFrame {{
                background: {Colors.BG_TERTIARY};
                border: 2px solid {border};
                border-left: 4px solid {self.step['color']};
                border-radius: 10px;
            }}
            QFrame:hover {{ background: {Colors.BG_HOVER}; }}
        """)
    
    def set_running(self, running: bool):
        self._running = running
        self.status.setText("⏳" if running else ("✅" if self._completed else "▶️"))
        self._update_style()
    
    def set_completed(self, completed: bool):
        self._completed = completed
        self.status.setText("✅" if completed else "▶️")
        self._update_style()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.step["id"])
        super().mousePressEvent(event)


# ============================================================
# 结果面板
# ============================================================

class ResultPanel(QFrame):
    """结果展示面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_step = None
        self._init_ui()
    
    def _init_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)
        
        # 标题
        self.title = QLabel("📋 执行结果")
        self.title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(self.title)
        
        # 摘要
        self.summary = QLabel("点击左侧步骤开始执行...")
        self.summary.setStyleSheet(f"""
            font-size: 14px;
            color: {Colors.TEXT_SECONDARY};
            background: {Colors.BG_SECONDARY};
            padding: 12px;
            border-radius: 8px;
        """)
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        
        # 进度条
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setStyleSheet(f"""
            QProgressBar {{ border: none; background: {Colors.BG_SECONDARY}; border-radius: 4px; height: 6px; }}
            QProgressBar::chunk {{ background: {Colors.PRIMARY}; border-radius: 4px; }}
        """)
        layout.addWidget(self.progress)
        
        # 详情
        self.details = QTextBrowser()
        self.details.setStyleSheet(f"""
            QTextBrowser {{
                background: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                color: {Colors.TEXT_PRIMARY};
                font-size: 12px;
            }}
        """)
        self.details.setMinimumHeight(180)
        layout.addWidget(self.details, 1)
        
        # 文件列表
        self.files = QTreeWidget()
        self.files.setHeaderLabels(["📁 文件", "时间"])
        self.files.setMaximumHeight(120)
        self.files.setStyleSheet(f"""
            QTreeWidget {{
                background: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        self.files.itemDoubleClicked.connect(self._open_file)
        layout.addWidget(self.files)
    
    def set_step(self, step_id: str):
        self.current_step = step_id
        name = next((s["name"] for s in WORKFLOW_STEPS if s["id"] == step_id), step_id)
        self.title.setText(f"📋 {name} - 执行结果")
    
    def show_progress(self, value: int, message: str):
        self.progress.setVisible(True)
        self.progress.setValue(value)
        self.summary.setText(message)
    
    def show_result(self, result: dict):
        self.progress.setVisible(False)
        self.summary.setText(result.get("summary", "完成"))
        
        # 详情 - 使用更友好的HTML格式
        details = result.get("details", {})
        html = self._format_details_html(details)
        self.details.setHtml(html)
        
        self._update_files()
    
    def _format_details_html(self, details: dict) -> str:
        """格式化详情为HTML"""
        html = f"<div style='color:{Colors.TEXT_PRIMARY}; font-family: Microsoft YaHei;'>"
        
        # 如果有报告链接，优先显示
        report_file = details.get("report_file")
        if report_file:
            html += f"""
            <div style='background:{Colors.BG_TERTIARY}; padding:12px; border-radius:8px; margin-bottom:12px;'>
                <strong style='color:{Colors.SUCCESS};'>📄 详细报告</strong><br/>
                <a href='file://{report_file}' style='color:{Colors.INFO};'>点击查看完整HTML报告 →</a>
            </div>
            """
        
        # 显示主要数据
        if "top_mainlines" in details:
            mainlines = details["top_mainlines"]
            html += f"<div style='margin-bottom:12px;'><strong style='color:{Colors.WARNING};'>🔥 投资主线 TOP{len(mainlines)}</strong></div>"
            html += "<table style='width:100%; border-collapse:collapse;'>"
            html += f"<tr style='background:{Colors.BG_TERTIARY};'><th style='padding:6px; text-align:left;'>排名</th><th style='padding:6px; text-align:left;'>名称</th><th style='padding:6px;'>评分</th></tr>"
            for ml in mainlines[:10]:  # 显示TOP10
                rank = ml.get('rank', '-')
                name = ml.get('name', '-')
                score = ml.get('composite_score', 0)
                html += f"<tr><td style='padding:4px;'>#{rank}</td><td style='padding:4px;'>{name}</td><td style='padding:4px; color:{Colors.SUCCESS};'>{score:.1f}</td></tr>"
            if len(mainlines) > 10:
                html += f"<tr><td colspan='3' style='padding:4px; color:{Colors.TEXT_SECONDARY};'>... 共{len(mainlines)}个主线，详见报告</td></tr>"
            html += "</table>"
        
        elif "stocks" in details:
            stocks = details["stocks"]
            html += f"<div style='margin-bottom:12px;'><strong style='color:{Colors.ACCENT};'>📦 候选池股票 ({len(stocks)}只)</strong></div>"
            html += "<table style='width:100%; border-collapse:collapse;'>"
            html += f"<tr style='background:{Colors.BG_TERTIARY};'><th style='padding:6px;'>代码</th><th style='padding:6px;'>名称</th><th style='padding:6px;'>来源</th><th style='padding:6px;'>评分</th></tr>"
            for stock in stocks[:15]:
                code = stock.get('code', '-')
                name = stock.get('name', '-')
                source = stock.get('source', '-')
                score = stock.get('score', 0)
                html += f"<tr><td style='padding:4px;'>{code}</td><td style='padding:4px;'>{name}</td><td style='padding:4px; color:{Colors.TEXT_SECONDARY};'>{source}</td><td style='padding:4px; color:{Colors.SUCCESS};'>{score:.1f}</td></tr>"
            html += "</table>"
        
        elif "recommended_factors" in details:
            factors = details["recommended_factors"]
            html += f"<div style='margin-bottom:12px;'><strong style='color:{Colors.SUCCESS};'>🧮 推荐因子</strong></div>"
            html += "<ul style='margin:0; padding-left:20px;'>"
            for f in factors:
                name = f.get('name', '-')
                weight = f.get('weight', 0) * 100
                reason = f.get('reason', '')
                html += f"<li style='margin:6px 0;'><strong>{name}</strong> (权重{weight:.0f}%) - {reason}</li>"
            html += "</ul>"
            if details.get("reasoning"):
                html += f"<div style='margin-top:12px; color:{Colors.TEXT_SECONDARY};'>策略说明: {details['reasoning']}</div>"
        
        else:
            # 其他详情用JSON显示
            html += f"<pre style='font-size:11px;'>{json.dumps(details, ensure_ascii=False, indent=2, default=str)}</pre>"
        
        html += "</div>"
        return html
    
    def _update_files(self):
        self.files.clear()
        
        base_dir = Path(__file__).parent.parent.parent
        
        # 报告文件
        report_dir = base_dir / "reports"
        if report_dir.exists():
            for f in sorted(report_dir.glob("*.html"), reverse=True)[:5]:
                mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime('%m-%d %H:%M')
                # 根据文件名判断类型
                icon = "📈" if "trend" in f.name else "🔥" if "mainline" in f.name else "📄"
                item = QTreeWidgetItem([f"{icon} {f.name}", mtime])
                item.setData(0, Qt.ItemDataRole.UserRole, str(f))
                self.files.addTopLevelItem(item)
        
        # 策略文件
        strategy_dir = base_dir / "strategies" / "ptrade"
        if strategy_dir.exists():
            for f in sorted(strategy_dir.glob("*.py"), reverse=True)[:3]:
                mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime('%m-%d %H:%M')
                item = QTreeWidgetItem([f"🐍 {f.name}", mtime])
                item.setData(0, Qt.ItemDataRole.UserRole, str(f))
                self.files.addTopLevelItem(item)
    
    def _open_file(self, item, col):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path and Path(path).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))


# ============================================================
# 集成工作流程面板
# ============================================================

class IntegratedWorkflowPanel(QWidget):
    """集成工作流程面板"""
    switch_page = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(14)
        
        # 标题栏
        header = QHBoxLayout()
        
        title = QLabel("🔄 集成工作流程")
        title.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
        header.addWidget(title)
        
        run_all = QPushButton("▶️ 一键执行全部")
        run_all.setStyleSheet(ButtonStyles.PRIMARY)
        run_all.setFixedHeight(36)
        run_all.clicked.connect(self._run_all)
        header.addWidget(run_all)
        
        header.addStretch()
        layout.addLayout(header)
        
        # 主内容
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧步骤
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(8)
        
        self.cards = {}
        for step in WORKFLOW_STEPS:
            card = StepCard(step)
            card.clicked.connect(self._on_step_click)
            left_layout.addWidget(card)
            self.cards[step["id"]] = card
        
        left_layout.addStretch()
        
        # 右侧结果
        self.result_panel = ResultPanel()
        
        splitter.addWidget(left)
        splitter.addWidget(self.result_panel)
        splitter.setSizes([260, 540])
        
        layout.addWidget(splitter, 1)
    
    def _on_step_click(self, step_id: str):
        """单步执行"""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(500)
        
        for sid, card in self.cards.items():
            card.set_running(sid == step_id)
        
        self.result_panel.set_step(step_id)
        
        self._worker = WorkflowWorker(step_id=step_id)
        self._worker.progress.connect(self._on_progress)
        self._worker.step_finished.connect(self._on_step_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()
    
    def _run_all(self):
        """执行全部"""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(500)
        
        # 重置所有卡片
        for card in self.cards.values():
            card.set_completed(False)
            card.set_running(False)
        
        self._worker = WorkflowWorker(run_all=True)
        self._worker.step_finished.connect(self._on_step_done)
        self._worker.all_finished.connect(self._on_all_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()
    
    def _on_progress(self, step_id: str, value: int, message: str):
        self.result_panel.show_progress(value, message)
    
    def _on_step_done(self, step_id: str, result: dict):
        card = self.cards.get(step_id)
        if card:
            card.set_running(False)
            card.set_completed(result.get("success", False))
        
        self.result_panel.set_step(step_id)
        self.result_panel.show_result(result)
    
    def _on_all_done(self, result: dict):
        msg = f"✅ 工作流执行完成！\n\n耗时: {result.get('total_time', 0):.1f}秒"
        if result.get("strategy_file"):
            msg += f"\n策略文件: {Path(result['strategy_file']).name}"
        QMessageBox.information(self, "完成", msg)
    
    def _on_error(self, step_id: str, error: str):
        card = self.cards.get(step_id)
        if card:
            card.set_running(False)
        
        self.result_panel.show_result({
            "success": False,
            "summary": f"❌ 失败: {error}",
            "details": {}
        })
