# -*- coding: utf-8 -*-
"""
因子筛选标签页
==============

集成到因子构建面板，从MongoDB读取候选池数据，
使用FactorPoolIntegration进行因子筛选
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QComboBox, QDoubleSpinBox,
    QGroupBox, QFormLayout, QProgressBar, QMessageBox, QCheckBox,
    QScrollArea, QFrame, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
import logging
from datetime import datetime
from typing import List, Optional, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

# 尝试导入核心模块
try:
    from core.factors import FactorPoolIntegration, StockSignal, create_factor_pool_integration
    FACTOR_INTEGRATION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"FactorPoolIntegration导入失败: {e}")
    FACTOR_INTEGRATION_AVAILABLE = False

try:
    from pymongo import MongoClient
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False


def get_colors():
    """获取颜色配置"""
    try:
        from gui.styles.theme import Colors
        return Colors
    except:
        class DefaultColors:
            PRIMARY = "#4fc3f7"
            ACCENT = "#29b6f6"
            SUCCESS = "#66bb6a"
            WARNING = "#ffa726"
            ERROR = "#ef5350"
            BG_PRIMARY = "#1a1a2e"
            BG_SECONDARY = "#16213e"
            BG_TERTIARY = "#0f3460"
            TEXT_PRIMARY = "#e8e8e8"
            TEXT_SECONDARY = "#a0a0a0"
            TEXT_MUTED = "#666666"
            BORDER_PRIMARY = "#333355"
        return DefaultColors


Colors = get_colors()


class CandidatePoolLoader:
    """候选池数据加载器 - 从MongoDB读取"""
    
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017/", db_name: str = "jqquant"):
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.client = None
        self.db = None
        self._connected = False
        self._connect()
    
    def _connect(self):
        """连接MongoDB"""
        if not MONGO_AVAILABLE:
            return
        try:
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=3000)
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            self._connected = True
            logger.info("候选池加载器：MongoDB连接成功")
        except Exception as e:
            logger.warning(f"MongoDB连接失败: {e}")
    
    def is_connected(self) -> bool:
        return self._connected
    
    def load_candidate_stocks(self) -> List[Dict]:
        """从MongoDB加载候选池股票"""
        if not self._connected:
            return []
        
        try:
            # 从mainline_mapped集合获取最新的主线映射数据
            latest = self.db.mainline_mapped.find_one(sort=[("timestamp", -1)])
            
            if not latest:
                logger.warning("MongoDB中没有主线映射数据")
                return []
            
            mainlines = latest.get("mainlines", [])
            
            if not mainlines:
                logger.warning("MongoDB中没有映射的主线数据")
                return []
            
            # 获取记录的元信息
            period = latest.get("period", "中期")
            record_date = latest.get("date", "")
            
            logger.info(f"读取主线映射记录: 日期={record_date}, 周期={period}, 主线数={len(mainlines)}")
            
            # 收集所有主线信息（稍后获取成分股）
            stocks = []
            for ml in mainlines:
                mainline_name = ml.get("name", "")
                # composite_tab保存的字段是jqdata_code
                jq_code = ml.get("jqdata_code")
                jq_type = ml.get("jqdata_type", "concept")  # concept 或 industry
                score = ml.get("total_score", 0) or ml.get("composite_score", 0)
                
                if not ml.get("jqdata_mapped"):
                    logger.debug(f"跳过未映射主线: {mainline_name}")
                    continue
                
                # 记录主线信息，需要通过JQData获取成分股
                stocks.append({
                    "mainline": mainline_name,
                    "mainline_score": score,
                    "jq_code": jq_code,
                    "jq_type": jq_type,  # concept 或 industry
                    "need_fetch_stocks": True,
                    "record_date": record_date,
                    "period": period
                })
            
            logger.info(f"从MongoDB加载候选池: {len(stocks)}条记录, {len(mainlines)}个主线")
            return stocks
            
        except Exception as e:
            logger.error(f"加载候选池失败: {e}")
            return []
    
    def get_mainline_count(self) -> int:
        """获取主线数量"""
        if not self._connected:
            return 0
        try:
            # 检查mainline_mapped集合中最新记录的主线数量
            latest = self.db.mainline_mapped.find_one(sort=[("timestamp", -1)])
            if latest:
                return len(latest.get("mainlines", []))
            return 0
        except:
            return 0


class FactorFilterWorker(QThread):
    """因子筛选工作线程"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list)  # List[StockSignal or dict]
    error = pyqtSignal(str)
    mainline_info = pyqtSignal(str)  # 主线信息
    
    def __init__(self, jq_client, mainlines: List[Dict], period: str = "medium", top_n: int = 30):
        super().__init__()
        self.jq_client = jq_client
        self.mainlines = mainlines
        self.period = period
        self.top_n = top_n
    
    def run(self):
        try:
            import jqdatasdk as jq
            
            self.progress.emit(5, "读取主线数据...")
            
            # 统计主线信息
            mainline_names = list(set(m.get("mainline", "") for m in self.mainlines if m.get("mainline")))
            self.mainline_info.emit(f"已加载 {len(mainline_names)} 个主线: {', '.join(mainline_names[:5])}...")
            
            self.progress.emit(10, "获取JQData权限范围...")
            
            # 获取JQData权限范围内的可用日期（关键修复！）
            available_date = None
            try:
                if hasattr(self.jq_client, 'get_permission'):
                    perm = self.jq_client.get_permission()
                    if perm and hasattr(perm, 'end_date'):
                        available_date = perm.end_date
                        self.progress.emit(12, f"JQData权限范围: {perm.start_date} 至 {perm.end_date}")
                elif hasattr(self.jq_client, 'get_available_date'):
                    available_date = self.jq_client.get_available_date()
            except Exception as e:
                logger.warning(f"获取JQData权限失败: {e}")
            
            # 如果仍然无法获取，使用JQData试用账户的已知范围
            if not available_date:
                # JQData试用账户通常是3个月前一年的数据
                available_date = "2025-08-29"  # 已知的试用账户截止日期
                self.progress.emit(12, f"使用默认日期: {available_date}")
            
            logger.info(f"使用日期获取成分股: {available_date}")
            
            # 收集所有股票
            all_stocks = []
            jq_codes = set()
            
            for ml in self.mainlines:
                jq_code = ml.get("jq_code")
                if jq_code and jq_code not in jq_codes:
                    jq_codes.add(jq_code)
            
            # 批量获取成分股
            self.progress.emit(20, f"获取 {len(jq_codes)} 个主线的成分股...")
            
            # 构建code -> type映射
            code_type_map = {}
            for ml in self.mainlines:
                jq_code = ml.get("jq_code")
                jq_type = ml.get("jq_type", "concept")
                if jq_code:
                    code_type_map[jq_code] = jq_type
            
            stocks_by_mainline = {}
            for i, jq_code in enumerate(jq_codes):
                try:
                    jq_type = code_type_map.get(jq_code, "concept")
                    if jq_type == "industry" or not jq_code.startswith('SC'):
                        # 行业
                        stocks = jq.get_industry_stocks(jq_code, date=available_date)
                    else:
                        # 概念
                        stocks = jq.get_concept_stocks(jq_code, date=available_date)
                    
                    if stocks:
                        stocks_by_mainline[jq_code] = stocks[:20]  # 每个主线最多20只
                        logger.info(f"✅ 获取成分股成功: {jq_code} ({jq_type}), 共{len(stocks)}只")
                except Exception as e:
                    logger.warning(f"获取成分股失败 {jq_code}: {e}")
                
                self.progress.emit(20 + int(i / len(jq_codes) * 30), f"获取成分股 {i+1}/{len(jq_codes)}")
            
            # 合并所有股票
            all_stock_codes = []
            stock_mainline_map = {}  # 股票 -> 主线信息
            
            for ml in self.mainlines:
                jq_code = ml.get("jq_code")
                mainline_name = ml.get("mainline", "")
                mainline_score = ml.get("mainline_score", 0)
                
                if jq_code in stocks_by_mainline:
                    for code in stocks_by_mainline[jq_code]:
                        if code not in stock_mainline_map:
                            stock_mainline_map[code] = {
                                "mainline": mainline_name,
                                "mainline_score": mainline_score,
                                "jq_code": jq_code
                            }
                            all_stock_codes.append(code)
            
            if not all_stock_codes:
                self.error.emit("未获取到任何股票")
                return
            
            self.progress.emit(50, f"获取到 {len(all_stock_codes)} 只股票，开始因子计算...")
            
            # 因子计算
            if FACTOR_INTEGRATION_AVAILABLE:
                integration = create_factor_pool_integration(jq_client=self.jq_client)
                
                # 构建主线评分字典
                mainline_scores = {code: info["mainline_score"] for code, info in stock_mainline_map.items()}
                
                self.progress.emit(60, "计算因子评分...")
                
                signals = integration.process_candidate_pool(
                    stocks=all_stock_codes[:100],  # 限制数量
                    date=available_date,
                    period=self.period,
                    mainline_scores=mainline_scores,
                    top_n=self.top_n
                )
                
                # 添加主线信息
                for signal in signals:
                    if signal.code in stock_mainline_map:
                        signal.mainline = stock_mainline_map[signal.code].get("mainline", "")
                
                self.progress.emit(100, "完成")
                self.finished.emit(signals)
            else:
                # 简化版：直接返回股票列表
                results = []
                for code in all_stock_codes[:self.top_n]:
                    info = stock_mainline_map.get(code, {})
                    results.append({
                        "code": code,
                        "mainline": info.get("mainline", ""),
                        "mainline_score": info.get("mainline_score", 0)
                    })
                self.progress.emit(100, "完成（简化模式）")
                self.finished.emit(results)
            
        except Exception as e:
            logger.error(f"因子筛选失败: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))


class FactorFilterTab(QWidget):
    """因子筛选标签页 - 集成到因子构建面板"""
    
    def __init__(self, jq_client=None, parent=None):
        super().__init__(parent)
        self.jq_client = jq_client
        self.integration = None
        self.pool_loader = CandidatePoolLoader()
        self.current_signals = []
        self.worker = None
        self._init_ui()
        self._check_data_status()
        
        # 立即加载缓存
        self._load_cached_results()
    
    def set_jq_client(self, jq_client):
        """设置JQData客户端"""
        self.jq_client = jq_client
        if FACTOR_INTEGRATION_AVAILABLE:
            try:
                self.integration = create_factor_pool_integration(jq_client=jq_client)
            except Exception as e:
                logger.error(f"初始化因子集成失败: {e}")
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 整页滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: {Colors.BG_SECONDARY};
            }}
            QScrollBar:vertical {{
                background-color: {Colors.BG_SECONDARY};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {Colors.BORDER_PRIMARY};
                border-radius: 5px;
                min-height: 40px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {Colors.PRIMARY};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(16)
        
        # === 工具说明 ===
        intro_frame = self._create_intro_section()
        content_layout.addWidget(intro_frame)
        
        # === 数据状态 ===
        status_frame = self._create_status_section()
        content_layout.addWidget(status_frame)
        
        # === 筛选参数 ===
        params_frame = self._create_params_section()
        content_layout.addWidget(params_frame)
        
        # === 操作区 ===
        action_frame = self._create_action_section()
        content_layout.addWidget(action_frame)
        
        # === 结果表格 ===
        self.result_frame = self._create_result_section()
        content_layout.addWidget(self.result_frame)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
    
    def _create_intro_section(self) -> QFrame:
        """创建工具说明部分"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 12px;
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # 标题
        title = QLabel("🤖 AI智能因子选择")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {Colors.PRIMARY};")
        layout.addWidget(title)
        
        # 原理说明
        intro_text = """
<p style="color: #a0a0a0; line-height: 1.6;">
<b style="color: #4fc3f7;">📌 工作原理：</b><br>
本工具基于AI智能分析，根据投资主线和候选池股票特征，<b style="color: #ffa726;">自动选择和构建最优因子组合</b>：
</p>

<ol style="color: #a0a0a0; line-height: 1.8;">
<li><b style="color: #66bb6a;">读取数据</b> - 从MongoDB读取投资主线+候选池股票</li>
<li><b style="color: #66bb6a;">AI分析</b> - 大模型分析当前市场环境，推荐最适合的因子组合</li>
<li><b style="color: #66bb6a;">因子选择</b> - 根据投资周期（短/中/长）动态调整因子权重</li>
<li><b style="color: #66bb6a;">可视化</b> - 展示因子分布、相关性、有效性分析</li>
<li><b style="color: #66bb6a;">输出Top50</b> - 输出综合得分前50的候选列表，供策略开发使用</li>
</ol>

<p style="color: #888; font-size: 12px; margin-top: 10px;">
<b>💡 工作流程：</b> 投资主线识别 → 候选池构建 → <b>因子选择(当前)</b> → 因子计算 → 策略开发
</p>
"""
        intro_label = QLabel(intro_text)
        intro_label.setTextFormat(Qt.TextFormat.RichText)
        intro_label.setWordWrap(True)
        layout.addWidget(intro_label)
        
        return frame
    
    def _create_status_section(self) -> QFrame:
        """创建数据状态部分"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
            }}
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        
        # MongoDB状态
        mongo_status = "✅ 已连接" if self.pool_loader.is_connected() else "❌ 未连接"
        self.mongo_label = QLabel(f"MongoDB: {mongo_status}")
        self.mongo_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        layout.addWidget(self.mongo_label)
        
        layout.addSpacing(20)
        
        # 候选池状态
        mainline_count = self.pool_loader.get_mainline_count()
        self.pool_label = QLabel(f"候选池主线: {mainline_count} 个")
        self.pool_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        layout.addWidget(self.pool_label)
        
        layout.addStretch()
        
        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Colors.PRIMARY};
                border: none;
                padding: 4px 8px;
            }}
            QPushButton:hover {{ color: {Colors.ACCENT}; }}
        """)
        refresh_btn.clicked.connect(self._check_data_status)
        layout.addWidget(refresh_btn)
        
        return frame
    
    def _create_params_section(self) -> QFrame:
        """创建参数设置部分"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
            }}
        """)
        
        layout = QFormLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        
        # 投资周期
        self.period_combo = QComboBox()
        self.period_combo.addItems(["短期 (动量+资金流)", "中期 (均衡配置)", "长期 (价值+成长)"])
        self.period_combo.setCurrentIndex(1)
        self.period_combo.setStyleSheet(self._get_combo_style())
        layout.addRow("投资周期:", self.period_combo)
        
        # 选择数量
        self.top_n_spin = QSpinBox()
        self.top_n_spin.setRange(10, 100)
        self.top_n_spin.setValue(30)
        self.top_n_spin.setStyleSheet(self._get_spin_style())
        layout.addRow("选择数量:", self.top_n_spin)
        
        # 最低得分
        self.min_score_spin = QDoubleSpinBox()
        self.min_score_spin.setRange(0, 100)
        self.min_score_spin.setValue(50)
        self.min_score_spin.setStyleSheet(self._get_spin_style())
        layout.addRow("最低得分:", self.min_score_spin)
        
        return frame
    
    def _create_action_section(self) -> QFrame:
        """创建操作区"""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 按钮行
        btn_layout = QHBoxLayout()
        
        self.filter_btn = QPushButton("🚀 开始因子筛选")
        self.filter_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {Colors.ACCENT}; }}
            QPushButton:disabled {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_MUTED};
            }}
        """)
        self.filter_btn.clicked.connect(self._start_filter)
        btn_layout.addWidget(self.filter_btn)
        
        # AI智能分析按钮
        self.ai_btn = QPushButton("🤖 AI智能分析")
        self.ai_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: #45a049; }}
            QPushButton:disabled {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_MUTED};
            }}
        """)
        self.ai_btn.clicked.connect(self._start_ai_analysis)
        self.ai_btn.setEnabled(False)  # 初始禁用，筛选完成后启用
        btn_layout.addWidget(self.ai_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 进度条
        self.progress = QProgressBar()
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                height: 20px;
                text-align: center;
                color: {Colors.TEXT_PRIMARY};
            }}
            QProgressBar::chunk {{
                background-color: {Colors.PRIMARY};
                border-radius: 5px;
            }}
        """)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        layout.addWidget(self.status_label)
        
        # 主线信息
        self.mainline_info_label = QLabel("")
        self.mainline_info_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        self.mainline_info_label.setWordWrap(True)
        layout.addWidget(self.mainline_info_label)
        
        return frame
    
    def _create_result_section(self) -> QFrame:
        """创建结果表格部分 - 显示25项"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 表格 - 固定高度显示25行（每行约35px + 表头40px）
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "排名", "代码", "名称", "综合得分", "因子得分", "所属主线", "信号强度"
        ])
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.BG_PRIMARY};
                border: none;
                color: {Colors.TEXT_PRIMARY};
                gridline-color: {Colors.BORDER_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                padding: 10px;
                border: none;
                font-weight: 600;
            }}
            QTableWidget::item {{
                padding: 8px;
            }}
            QTableWidget::item:selected {{
                background-color: {Colors.PRIMARY}30;
            }}
        """)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        # 固定高度显示25行 (35px/行 * 25 + 40px表头 = 915px)
        self.table.setMinimumHeight(915)
        self.table.setMaximumHeight(915)
        # 禁用表格内部滚动，让整页滚动
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.table)
        
        return frame
    
    def _get_combo_style(self) -> str:
        return f"""
            QComboBox {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 8px 12px;
                color: {Colors.TEXT_PRIMARY};
                min-width: 200px;
            }}
            QComboBox:hover {{ border-color: {Colors.PRIMARY}; }}
            QComboBox::drop-down {{ border: none; width: 30px; }}
        """
    
    def _get_spin_style(self) -> str:
        return f"""
            QSpinBox, QDoubleSpinBox {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 8px 12px;
                color: {Colors.TEXT_PRIMARY};
                min-width: 100px;
            }}
            QSpinBox:hover, QDoubleSpinBox:hover {{ border-color: {Colors.PRIMARY}; }}
        """
    
    def _check_data_status(self):
        """检查数据状态"""
        mongo_connected = self.pool_loader.is_connected()
        mainline_count = self.pool_loader.get_mainline_count()
        
        mongo_status = "✅ 已连接" if mongo_connected else "❌ 未连接"
        self.mongo_label.setText(f"MongoDB: {mongo_status}")
        
        if mainline_count > 0:
            self.pool_label.setText(f"候选池主线: {mainline_count} 个")
            self.pool_label.setStyleSheet(f"color: {Colors.SUCCESS};")
        else:
            self.pool_label.setText("候选池: ⚠️ 无数据")
            self.pool_label.setStyleSheet(f"color: {Colors.WARNING};")
    
    def _load_cached_results(self):
        """加载缓存的因子筛选结果"""
        try:
            from core.cache_manager import get_cache_manager
            
            cache_mgr = get_cache_manager()
            
            # 检查因子筛选缓存
            if cache_mgr.is_cache_valid('factor_filter'):
                cached = cache_mgr.load_cache('factor_filter')
                if cached:
                    signals = cached.get('signals', [])
                    if signals:
                        self.current_signals = signals
                        self._update_table(signals)
                        
                        timestamp = cached.get('timestamp', '')[:16]
                        period = cached.get('period', '')
                        self.status_label.setText(f"📂 已加载缓存 ({timestamp})")
                        self.ai_btn.setEnabled(len(signals) > 0)
                        
                        logger.info(f"✅ 因子筛选加载缓存: {len(signals)}只股票")
                        return
            
            logger.debug("因子筛选无有效缓存")
            
        except Exception as e:
            logger.debug(f"加载因子筛选缓存失败: {e}")
    
    def _save_filter_results(self, signals: list, period: str = "medium"):
        """保存因子筛选结果到缓存"""
        logger.info(f"💾 正在保存因子筛选缓存: {len(signals)} 条结果")
        try:
            from core.cache_manager import get_cache_manager
            
            # 转换信号为可序列化格式
            serializable = []
            for s in signals:
                if hasattr(s, '__dict__'):
                    serializable.append({
                        'code': getattr(s, 'code', ''),
                        'name': getattr(s, 'name', ''),
                        'combined_score': getattr(s, 'combined_score', 0),
                        'factor_score': getattr(s, 'factor_score', 0),
                        'mainline': getattr(s, 'mainline', ''),
                        'signal_strength': getattr(s, 'signal_strength', 'medium'),
                    })
                else:
                    serializable.append(s)
            
            # 确保基本类型
            import json
            def make_serializable(obj):
                if hasattr(obj, 'item'):  # numpy types
                    return obj.item()
                if isinstance(obj, dict):
                    return {k: make_serializable(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [make_serializable(v) for v in obj]
                return obj
            
            clean_signals = make_serializable(serializable)
            
            cache_mgr = get_cache_manager()
            cache_mgr.save_cache('factor_filter', {
                'signals': clean_signals,
                'count': len(clean_signals),
            }, {'period': period})
            
        except Exception as e:
            logger.error(f"❌ 保存因子筛选缓存失败: {e}", exc_info=True)
    
    def _start_filter(self):
        """开始因子筛选"""
        # 检查JQData
        if self.jq_client is None:
            QMessageBox.warning(self, "错误", "JQData未连接，请检查配置")
            return
        
        # 加载候选池
        candidates = self.pool_loader.load_candidate_stocks()
        
        if not candidates:
            reply = QMessageBox.question(
                self, "候选池为空",
                "MongoDB中没有候选池数据。\n\n"
                "请先到「投资主线 → 综合评分」计算并保存主线评分。\n\n"
                "是否使用默认主线进行测试？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 使用默认测试主线
                candidates = [
                    {"mainline": "人工智能", "jq_code": "SC0363", "mainline_score": 85},
                    {"mainline": "新能源", "jq_code": "SC0066", "mainline_score": 80},
                    {"mainline": "半导体", "jq_code": "SC0353", "mainline_score": 78},
                ]
            else:
                return
        
        # 获取参数
        period_map = {0: "short", 1: "medium", 2: "long"}
        period = period_map.get(self.period_combo.currentIndex(), "medium")
        top_n = self.top_n_spin.value()
        
        # 启动工作线程
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
        
        self.worker = FactorFilterWorker(
            jq_client=self.jq_client,
            mainlines=candidates,
            period=period,
            top_n=top_n
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.mainline_info.connect(self._on_mainline_info)
        
        self.filter_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.status_label.setText("正在筛选...")
        
        self.worker.start()
    
    def _on_progress(self, value: int, message: str):
        """进度更新"""
        self.progress.setValue(value)
        self.status_label.setText(message)
    
    def _on_mainline_info(self, info: str):
        """主线信息更新"""
        self.mainline_info_label.setText(info)
    
    def _on_finished(self, signals):
        """筛选完成"""
        self.current_signals = signals
        self._update_table(signals)
        
        self.filter_btn.setEnabled(True)
        self.ai_btn.setEnabled(len(signals) > 0)  # 有结果时启用AI分析
        self.progress.setVisible(False)
        self.status_label.setText(f"✅ 筛选完成，共 {len(signals)} 只股票")
        
        # 保存到缓存
        period_map = {0: "short", 1: "medium", 2: "long"}
        period = period_map.get(self.period_combo.currentIndex(), "medium")
        self._save_filter_results(signals, period)
    
    def _on_error(self, error: str):
        """错误处理"""
        self.filter_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.status_label.setText(f"❌ 筛选失败: {error}")
        QMessageBox.critical(self, "错误", f"因子筛选失败:\n{error}")
    
    def _update_table(self, signals):
        """更新表格"""
        # 应用最低得分筛选
        min_score = self.min_score_spin.value()
        
        # 处理不同类型的信号
        if signals and hasattr(signals[0], 'combined_score'):
            # StockSignal类型
            filtered = [s for s in signals if s.combined_score >= min_score]
        else:
            # 字典类型
            filtered = [s for s in signals if s.get('mainline_score', 0) >= min_score]
        
        self.table.setRowCount(len(filtered))
        
        for row, signal in enumerate(filtered):
            if hasattr(signal, 'code'):
                # StockSignal类型
                self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
                self.table.setItem(row, 1, QTableWidgetItem(signal.code))
                self.table.setItem(row, 2, QTableWidgetItem(signal.name or signal.code))
                
                score_item = QTableWidgetItem(f"{signal.combined_score:.1f}")
                if signal.combined_score >= 80:
                    score_item.setForeground(QColor(Colors.SUCCESS))
                self.table.setItem(row, 3, score_item)
                
                self.table.setItem(row, 4, QTableWidgetItem(f"{signal.factor_score:.1f}"))
                self.table.setItem(row, 5, QTableWidgetItem(signal.mainline or ""))
                
                strength_item = QTableWidgetItem(signal.signal_strength)
                if signal.signal_strength == "strong":
                    strength_item.setForeground(QColor(Colors.SUCCESS))
                self.table.setItem(row, 6, strength_item)
            else:
                # 字典类型
                self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
                self.table.setItem(row, 1, QTableWidgetItem(signal.get('code', '')))
                self.table.setItem(row, 2, QTableWidgetItem(signal.get('name', '')))
                self.table.setItem(row, 3, QTableWidgetItem(f"{signal.get('mainline_score', 0):.1f}"))
                self.table.setItem(row, 4, QTableWidgetItem("-"))
                self.table.setItem(row, 5, QTableWidgetItem(signal.get('mainline', '')))
                self.table.setItem(row, 6, QTableWidgetItem("-"))
        
        self.table.resizeColumnsToContents()
    
    def _start_ai_analysis(self):
        """启动AI智能分析"""
        if not self.current_signals:
            QMessageBox.warning(self, "提示", "请先进行因子筛选")
            return
        
        try:
            from core.ai_analyzer import create_ai_analyzer
            
            # 获取主线数据
            mainlines = self.pool_loader.load_candidate_stocks()
            
            # 准备因子评分数据
            factor_scores = []
            for signal in self.current_signals:
                if hasattr(signal, 'code'):
                    factor_scores.append({
                        'code': signal.code,
                        'name': signal.name or signal.code,
                        'factor_score': signal.factor_score if hasattr(signal, 'factor_score') else 0,
                        'mainline': signal.mainline if hasattr(signal, 'mainline') else ''
                    })
                else:
                    factor_scores.append(signal)
            
            # 获取投资周期
            period_map = {0: "short", 1: "medium", 2: "long"}
            period = period_map.get(self.period_combo.currentIndex(), "medium")
            
            self.status_label.setText("🤖 正在进行AI智能分析...")
            self.ai_btn.setEnabled(False)
            
            # 创建分析器并执行分析
            analyzer = create_ai_analyzer(model_type="local")
            result = analyzer.analyze_stocks(
                mainlines=mainlines,
                factor_scores=factor_scores,
                period=period
            )
            
            # 显示分析结果
            self._show_ai_result(result)
            
            self.ai_btn.setEnabled(True)
            self.status_label.setText("✅ AI分析完成")
            
        except Exception as e:
            logger.error(f"AI分析失败: {e}")
            import traceback
            traceback.print_exc()
            self.ai_btn.setEnabled(True)
            self.status_label.setText(f"❌ AI分析失败: {e}")
            QMessageBox.warning(self, "AI分析失败", str(e))
    
    def _show_ai_result(self, result):
        """显示AI分析结果"""
        from PyQt6.QtWidgets import QDialog, QTextEdit
        
        dialog = QDialog(self)
        dialog.setWindowTitle("🤖 AI智能分析结果")
        dialog.setMinimumSize(600, 500)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_PRIMARY};
            }}
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 摘要
        summary_label = QLabel(f"📌 {result.summary}")
        summary_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {Colors.PRIMARY};")
        summary_label.setWordWrap(True)
        layout.addWidget(summary_label)
        
        # 置信度
        confidence_label = QLabel(f"置信度: {result.confidence:.0%}")
        confidence_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        layout.addWidget(confidence_label)
        
        # 推荐股票
        if result.recommendations:
            rec_label = QLabel("🎯 推荐股票:")
            rec_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {Colors.SUCCESS}; margin-top: 10px;")
            layout.addWidget(rec_label)
            
            for rec in result.recommendations:
                rec_text = f"  • {rec.get('code', '')} {rec.get('name', '')} - {rec.get('reason', '')}"
                rec_item = QLabel(rec_text)
                rec_item.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
                rec_item.setWordWrap(True)
                layout.addWidget(rec_item)
        
        # 市场观点
        view_label = QLabel(f"\n📊 市场观点: {result.market_view}")
        view_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        view_label.setWordWrap(True)
        layout.addWidget(view_label)
        
        # 风险评估
        risk_label = QLabel(f"\n⚠️ 风险评估: {result.risk_assessment}")
        risk_label.setStyleSheet(f"color: {Colors.WARNING};")
        risk_label.setWordWrap(True)
        layout.addWidget(risk_label)
        
        # 详细推理
        reasoning_label = QLabel("\n📝 分析过程:")
        reasoning_label.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_MUTED};")
        layout.addWidget(reasoning_label)
        
        reasoning_text = QTextEdit()
        reasoning_text.setPlainText(result.reasoning)
        reasoning_text.setReadOnly(True)
        reasoning_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                color: {Colors.TEXT_SECONDARY};
                font-size: 12px;
            }}
        """)
        reasoning_text.setMaximumHeight(150)
        layout.addWidget(reasoning_text)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                padding: 10px 20px;
                border-radius: 6px;
            }}
            QPushButton:hover {{ background-color: {Colors.PRIMARY}; }}
        """)
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        
        dialog.exec()
