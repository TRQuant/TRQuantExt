"""
股票池构建面板

核心逻辑：
1. 读取五维综合评分结果 → 获取高评分主线
2. 对每个主线：
   - 龙头股自动入选
   - JQData获取成分股 → TuShare Pro获取行情 → 筛选强势股
3. 技术突破：TuShare Pro全市场扫描 → 筛选涨停/放量/突破
4. ETF轮动：AKShare获取ETF行情

数据源优先级：
- 成分股：JQData > 缓存
- 行情：TuShare Pro > AKShare > 模拟
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path
import json

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QProgressBar, QComboBox, QSpinBox, QTextEdit,
    QHeaderView, QMessageBox, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from ..styles.theme import Colors

logger = logging.getLogger(__name__)


# ============================================================
# 模拟数据（当所有真实数据源都不可用时的最后备选）
# ============================================================

def get_mock_mainline_stocks():
    return [
        {"code": "002230", "name": "科大讯飞", "source": "mainline", "data_source": "模拟", "period": "medium", 
         "priority": 1, "mainline_score": 88.5, "change_pct": 5.2, "entry_reason": "🏆 主线龙头：人工智能", "sector": "人工智能"},
        {"code": "300750", "name": "宁德时代", "source": "mainline", "data_source": "模拟", "period": "medium",
         "priority": 1, "mainline_score": 85.3, "change_pct": 3.8, "entry_reason": "🏆 主线龙头：新能源", "sector": "新能源"},
        {"code": "688981", "name": "中芯国际", "source": "mainline", "data_source": "模拟", "period": "medium",
         "priority": 1, "mainline_score": 82.1, "change_pct": 4.5, "entry_reason": "🏆 主线龙头：半导体", "sector": "半导体"},
        {"code": "600760", "name": "中航沈飞", "source": "mainline", "data_source": "模拟", "period": "medium",
         "priority": 1, "mainline_score": 80.7, "change_pct": 6.1, "entry_reason": "🏆 主线龙头：军工", "sector": "军工"},
        {"code": "601012", "name": "隆基绿能", "source": "mainline", "data_source": "模拟", "period": "medium",
         "priority": 1, "mainline_score": 78.9, "change_pct": 2.9, "entry_reason": "🏆 主线龙头：光伏", "sector": "光伏"},
    ]

def get_mock_tech_stocks():
    return [
        {"code": "300750", "name": "宁德时代", "source": "tech_breakout", "data_source": "模拟", "period": "short",
         "priority": 2, "mainline_score": 0, "change_pct": 9.98, "entry_reason": "📈 技术突破：涨停, 放量3倍+", "sector": ""},
        {"code": "002594", "name": "比亚迪", "source": "tech_breakout", "data_source": "模拟", "period": "short",
         "priority": 2, "mainline_score": 0, "change_pct": 9.95, "entry_reason": "📈 技术突破：涨停, 放量2倍+", "sector": ""},
    ]

def get_mock_etfs():
    return [
        {"code": "159915", "name": "创业板ETF", "type": "宽基ETF", "price": 2.35, "change_5d": 8.5, "amount": 125.6, "index": "创业板指"},
        {"code": "512480", "name": "半导体ETF", "type": "主题ETF", "price": 1.28, "change_5d": 12.5, "amount": 85.2, "index": "半导体"},
    ]

def get_mock_external_stocks():
    return [
        {"code": "600519", "name": "贵州茅台", "source": "broker", "data_source": "示例", "period": "medium", 
         "priority": 3, "mainline_score": 0, "change_pct": 0, "entry_reason": "中信证券月度金股", "sector": ""},
    ]


# ============================================================
# 主线强势股扫描Worker
# ============================================================

class MainlineScanWorker(QThread):
    """
    主线强势股扫描（基于MongoDB已映射主线 + JQData）
    
    数据流（已优化）：
    1. 从MongoDB读取已映射的主线（综合评分时已完成AKShare→JQData映射）
    2. 直接使用JQData获取成分股（无需重新映射，速度快）
    3. 对成分股进行筛选
    4. 合并去重输出
    
    数据源：MongoDB + JQData（统一使用聚宽账户）
    """
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list, str)
    
    def __init__(self, period: str = "medium", max_mainlines: int = 10, max_stocks_per_mainline: int = 5):
        super().__init__()
        self.period = period
        self.max_mainlines = max_mainlines
        self.max_stocks_per_mainline = max_stocks_per_mainline
        self._stop = False
        
        # 数据源
        self.jq_client = None
        self.db = None
    
    def stop(self):
        self._stop = True
    
    def run(self):
        all_stocks = []
        data_sources_used = set()
        
        try:
            # Step 1: 初始化JQData
            self.progress.emit(5, "🔐 初始化JQData...")
            if not self._init_jqdata():
                self.progress.emit(100, "❌ JQData初始化失败")
                self.finished.emit(get_mock_mainline_stocks(), "模拟数据（JQData不可用）")
                return
            
            data_sources_used.add("JQData")
            
            # Step 2: 从MongoDB读取已映射的主线
            self.progress.emit(10, "📂 从MongoDB读取已映射的主线...")
            mapped_mainlines = self._load_mapped_mainlines()
            
            if not mapped_mainlines:
                self.progress.emit(15, "⚠️ MongoDB中未找到已映射主线，尝试从文件读取...")
                # 备选：从文件读取并实时映射
                mainlines = self._load_mainline_from_file()
                if mainlines:
                    self.progress.emit(20, "📊 从文件读取主线，进行JQData映射...")
                    mapped_mainlines = self._map_mainlines_to_jqdata(mainlines)
                
            if not mapped_mainlines:
                self.progress.emit(50, "⚠️ 未找到主线数据，请先运行综合评分")
                self.finished.emit(get_mock_mainline_stocks(), "模拟数据")
                return
            
            # 过滤出已成功映射的主线
            jqdata_mapped = [m for m in mapped_mainlines if m.get('jqdata_mapped') or m.get('jqdata_code')]
            self.progress.emit(15, f"✅ 找到 {len(jqdata_mapped)} 个已映射到JQData的主线")
            
            if not jqdata_mapped:
                self.progress.emit(50, "⚠️ 所有主线都未能映射到JQData")
                self.finished.emit(get_mock_mainline_stocks(), "模拟数据")
                return
            
            # Step 3: 对每个主线使用JQData获取成分股并筛选
            total = min(len(jqdata_mapped), self.max_mainlines)
            for i, mainline in enumerate(jqdata_mapped[:total]):
                if self._stop:
                    break
                
                name = mainline.get("name", "")
                jqdata_code = mainline.get("jqdata_code", "")
                jqdata_name = mainline.get("jqdata_name", "")
                jqdata_type = mainline.get("jqdata_type", "concept")
                score = mainline.get("total_score", 0)
                leader = mainline.get("leader_stock", "")
                leader_change = mainline.get("leader_change", 0)
                
                progress_pct = 20 + int(65 * (i + 1) / total)
                self.progress.emit(progress_pct, f"🔍 [{i+1}/{total}] {name} → {jqdata_name} (JQData)")
                
                mainline_stocks = []
                
                # 3.1 添加龙头股（必选）
                if leader:
                    leader_stock = self._create_leader_stock(leader, name, score, leader_change)
                    if leader_stock:
                        mainline_stocks.append(leader_stock)
                
                # 3.2 使用JQData获取成分股
                if jqdata_code and score >= 60:
                    concept_stocks = self._get_stocks_from_jqdata(jqdata_code, jqdata_type)
                    if concept_stocks:
                        logger.info(f"  → JQData获取成分股: {len(concept_stocks)} 只")
                        
                        # 筛选强势股
                        strong_stocks = self._filter_strong_stocks_jqdata(
                            concept_stocks, score, name
                        )
                        # 去掉龙头股（避免重复）
                        strong_stocks = [s for s in strong_stocks if s.get("name") != leader]
                        mainline_stocks.extend(strong_stocks[:self.max_stocks_per_mainline])
                
                all_stocks.extend(mainline_stocks)
            
            # Step 4: 去重和排序
            self.progress.emit(90, "📋 整理结果...")
            unique_stocks = self._deduplicate_and_sort(all_stocks)
            
            source_desc = "MongoDB主线 + JQData成分股"
            
            self.progress.emit(100, f"✅ 完成！找到 {len(unique_stocks)} 只主线强势股（数据源: JQData）")
            self.finished.emit(unique_stocks, source_desc)
            
        except Exception as e:
            logger.error(f"主线扫描失败: {e}", exc_info=True)
            self.progress.emit(100, f"❌ 扫描失败: {str(e)[:30]}，使用模拟数据")
            self.finished.emit(get_mock_mainline_stocks(), "模拟数据（异常）")
    
    def _init_jqdata(self) -> bool:
        """初始化JQData"""
        try:
            from jqdata.client import JQDataClient
            from config.config_manager import get_config_manager
            
            config_manager = get_config_manager()
            config = config_manager.get_jqdata_config()
            
            if not config.get('username') or not config.get('password'):
                logger.warning("⚠️ 未找到JQData配置")
                return False
            
            self.jq_client = JQDataClient()
            if not self.jq_client.authenticate(config['username'], config['password']):
                logger.warning("⚠️ JQData认证失败")
                return False
            
            # 显示数据权限
            perm = self.jq_client.get_permission()
            mode = "实时模式" if perm.is_realtime else "历史模式"
            logger.info(f"✅ JQData认证成功 - {mode} ({perm.start_date} 至 {perm.end_date})")
            
            return True
            
        except Exception as e:
            logger.error(f"JQData初始化失败: {e}")
            return False
    
    def _init_mongodb(self):
        """初始化MongoDB"""
        try:
            from pymongo import MongoClient
            client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
            client.server_info()
            self.db = client.jqquant
            return True
        except Exception as e:
            logger.warning(f"MongoDB连接失败: {e}")
            return False
    
    def _load_mapped_mainlines(self) -> List[Dict]:
        """从MongoDB读取已映射的主线"""
        if not self._init_mongodb():
            return []
        
        try:
            collection = self.db.mainline_mapped
            latest = collection.find_one(sort=[("timestamp", -1)])
            if latest:
                mainlines = latest.get('mainlines', [])
                logger.info(f"✅ 从MongoDB读取: {len(mainlines)} 个主线")
                return mainlines
        except Exception as e:
            logger.warning(f"从MongoDB读取失败: {e}")
        
        return []
    
    def _load_mainline_from_file(self) -> List[Dict]:
        """从文件读取主线数据（备选）"""
        composite_file = Path.home() / '.local/share/trquant/reports/mainline/latest_composite_scores.json'
        if composite_file.exists():
            try:
                with open(composite_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # 优先使用top20
                top20 = data.get("top20", [])
                if top20:
                    return top20
                # 否则使用scores
                scores = data.get("scores", [])
                return scores[:20]
            except Exception as e:
                logger.warning(f"读取文件失败: {e}")
        return []
    
    def _map_mainlines_to_jqdata(self, mainlines: List[Dict]) -> List[Dict]:
        """将主线映射到JQData（实时映射）"""
        if not self.jq_client:
            return []
        
        try:
            from core.mainline_mapper import MainlineMapper
            mapper = MainlineMapper(jq_client=self.jq_client)
            
            mapped = []
            for mainline in mainlines:
                name = mainline.get('name', '')
                if not name:
                    continue
                
                mapping = mapper.map_mainline(name, prefer_type='auto')
                mapped_data = {
                    **mainline,
                    "jqdata_mapped": mapping is not None,
                    "jqdata_code": mapping.jqdata_code if mapping else None,
                    "jqdata_name": mapping.jqdata_name if mapping else None,
                    "jqdata_type": mapping.mapping_type if mapping else None,
                }
                mapped.append(mapped_data)
                
                if mapping:
                    logger.info(f"  ✅ {name} → {mapping.jqdata_name}")
            
            return mapped
            
        except Exception as e:
            logger.error(f"映射失败: {e}")
            return []
    
    def _get_stocks_from_jqdata(self, jqdata_code: str, jqdata_type: str) -> List[Dict]:
        """使用JQData获取成分股"""
        if not self.jq_client:
            return []
        
        try:
            if jqdata_type == 'concept':
                stocks = self.jq_client.get_concept_stocks(jqdata_code)
            elif jqdata_type == 'industry':
                stocks = self.jq_client.get_industry_stocks(jqdata_code)
            else:
                return []
            
            # 转换为标准格式
            result = []
            for stock in stocks[:50]:  # 限制数量
                code = stock.replace('.XSHE', '').replace('.XSHG', '') if isinstance(stock, str) else str(stock)
                result.append({
                    "code": code,
                    "jqdata_code": stock,
                    "source": "JQData"
                })
            
            return result
            
        except Exception as e:
            logger.warning(f"JQData获取成分股失败: {e}")
            return []
    
    def _create_leader_stock(self, leader_name: str, mainline_name: str, score: float, change: float) -> Optional[Dict]:
        """创建龙头股记录"""
        return {
            "code": "",
            "name": leader_name,
            "source": "mainline",
            "data_source": "龙头股",
            "period": self.period,
            "priority": 1,
            "mainline_score": score,
            "change_pct": change,
            "entry_reason": f"🏆 主线龙头：{mainline_name}",
            "sector": mainline_name,
        }
    
    def _filter_strong_stocks_jqdata(self, stocks: List[Dict], score: float, sector_name: str) -> List[Dict]:
        """从JQData成分股中筛选强势股，结合AKShare实时涨跌幅"""
        result = []
        
        # 先获取AKShare实时行情（批量获取，提高效率）
        realtime_data = self._get_akshare_realtime_data()
        
        for stock in stocks:
            code = stock.get("code", "")
            jqdata_code = stock.get("jqdata_code", "")
            
            # 获取股票名称（从JQData）
            name = code
            try:
                if self.jq_client:
                    end_date = self.jq_client.get_available_end_date()
                    securities = self.jq_client.get_all_securities(types=['stock'], date=end_date)
                    if jqdata_code in securities.index:
                        name = securities.loc[jqdata_code, 'display_name']
            except:
                pass
            
            # 优先使用AKShare实时涨跌幅
            change_pct = 0.0
            if realtime_data is not None and code in realtime_data:
                change_pct = realtime_data[code].get('change_pct', 0)
            else:
                # 备选：从JQData获取历史涨跌幅
                price_data = self._get_stock_price_jqdata(jqdata_code)
                if price_data:
                    change_pct = price_data.get('change_pct', 0)
                    name = price_data.get('name', name)
            
            # 筛选条件：涨幅 > 0 或 主线评分高
            if change_pct > -5 or score >= 70:  # 放宽条件
                result.append({
                    "code": code,
                    "name": name,
                    "source": "mainline",
                    "data_source": "JQData+AKShare",
                    "period": self.period,
                    "priority": 2,
                    "mainline_score": score,
                    "change_pct": change_pct,
                    "entry_reason": f"📈 主线成分股：{sector_name}",
                    "sector": sector_name,
                })
        
        # 按涨幅排序
        result.sort(key=lambda x: x.get("change_pct", 0), reverse=True)
        return result
    
    def _get_akshare_realtime_data(self) -> Optional[Dict]:
        """获取AKShare实时行情数据"""
        try:
            import akshare as ak
            import socket
            socket.setdefaulttimeout(15)
            
            df = ak.stock_zh_a_spot_em()
            if df is None or df.empty:
                return None
            
            # 转换为字典格式，方便查询
            result = {}
            for _, row in df.iterrows():
                code = str(row.get('代码', ''))
                result[code] = {
                    'name': row.get('名称', ''),
                    'change_pct': float(row.get('涨跌幅', 0) or 0),
                    'price': float(row.get('最新价', 0) or 0),
                    'volume_ratio': float(row.get('量比', 1) or 1),
                    'turnover': float(row.get('换手率', 0) or 0),
                }
            
            logger.info(f"✅ AKShare获取实时行情: {len(result)} 只股票")
            return result
            
        except Exception as e:
            logger.warning(f"AKShare获取实时行情失败: {e}")
            return None
    
    def _get_stock_price_jqdata(self, jqdata_code: str) -> Optional[Dict]:
        """从JQData获取股票价格"""
        if not self.jq_client:
            return None
        
        try:
            # 获取最近的价格数据
            end_date = self.jq_client.get_available_end_date()
            price_df = self.jq_client.get_price(
                securities=jqdata_code,
                start_date=end_date,
                end_date=end_date,
                frequency='daily',
                auto_adjust_date=True
            )
            
            if price_df.empty:
                return None
            
            # 获取股票名称
            name = jqdata_code
            try:
                securities = self.jq_client.get_all_securities(types=['stock'], date=end_date)
                if jqdata_code in securities.index:
                    name = securities.loc[jqdata_code, 'display_name']
            except:
                pass
            
            latest = price_df.iloc[-1]
            
            # 计算涨跌幅（如果有昨收价）
            change_pct = 0.0
            if 'pre_close' in price_df.columns and latest.get('pre_close', 0) > 0:
                change_pct = ((latest['close'] - latest['pre_close']) / latest['pre_close']) * 100
            
            return {
                'name': name,
                'close': latest.get('close', 0),
                'change_pct': change_pct
            }
            
        except Exception as e:
            logger.debug(f"获取价格失败 {jqdata_code}: {e}")
            return None
    
    def _deduplicate_and_sort(self, stocks: List[Dict]) -> List[Dict]:
        """去重和排序"""
        seen = set()
        unique = []
        for stock in stocks:
            code = stock.get("code", "")
            if code and code not in seen:
                seen.add(code)
                unique.append(stock)
        
        # 按优先级和评分排序
        unique.sort(key=lambda x: (x.get("priority", 5), -x.get("mainline_score", 0), -x.get("change_pct", 0)))
        return unique[:30]


# ============================================================
# 技术突破扫描Worker
# ============================================================

class TechScanWorker(QThread):
    """
    技术突破扫描
    
    数据源：AKShare实时行情（优先）
    
    筛选条件：
    - 涨停（涨幅>=9.9%）：优先级最高
    - 大涨（涨幅>=7%）
    - 放量（量比>=2）
    - 活跃换手（5-15%）
    - 市值30-5000亿
    """
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list, str)
    
    def __init__(self, period: str = "short"):
        super().__init__()
        self.period = period
    
    def run(self):
        data_source_desc = ""
        df = None
        
        try:
            # 优先使用 AKShare 实时行情
            self.progress.emit(10, "📊 获取全市场实时行情（AKShare）...")
            
            try:
                import akshare as ak
                import socket
                socket.setdefaulttimeout(30)
                df = ak.stock_zh_a_spot_em()
                if df is not None and not df.empty:
                    data_source_desc = "AKShare实时行情"
                    self.progress.emit(35, f"✅ AKShare获取到 {len(df)} 只股票")
            except Exception as e:
                logger.warning(f"AKShare获取失败: {e}")
                df = None
            
            if df is None or df.empty:
                self.progress.emit(100, "⚠️ 行情获取失败，使用模拟数据")
                self.finished.emit(get_mock_tech_stocks(), "模拟数据")
                return
            
            self.progress.emit(45, "🔍 开始筛选技术突破股...")
            
            # 技术突破筛选
            stocks = []
            for _, row in df.iterrows():
                try:
                    name = str(row.get("名称", ""))
                    code = str(row.get("代码", ""))
                except:
                    continue
                
                if not name or not code:
                    continue
                if "ST" in name:
                    continue
                
                change_pct = float(row.get("涨跌幅", 0) or 0)
                volume_ratio = float(row.get("量比", 1) or 1)
                turnover = float(row.get("换手率", 0) or 0)
                market_cap = float(row.get("总市值", 0) or 0) / 100000000
                
                # 市值过滤
                if market_cap < 30 or market_cap > 5000:
                    continue
                
                # 计算技术信号得分
                signals = []
                score = 0
                
                if change_pct >= 9.9:
                    signals.append("涨停")
                    score += 40
                elif change_pct >= 7:
                    signals.append(f"大涨{change_pct:.1f}%")
                    score += 25
                elif change_pct >= 5:
                    signals.append(f"涨{change_pct:.1f}%")
                    score += 15
                
                if volume_ratio >= 3:
                    signals.append("放量3倍+")
                    score += 25
                elif volume_ratio >= 2:
                    signals.append("放量2倍+")
                    score += 15
                
                if 5 <= turnover <= 15:
                    signals.append("活跃换手")
                    score += 10
                
                # 只保留有明显信号的股票
                if signals and score >= 25:
                    stocks.append({
                        "code": code,
                        "name": name,
                        "source": "tech_breakout",
                        "data_source": data_source_desc,
                        "period": self.period,
                        "priority": 2 if score >= 50 else 3,
                        "mainline_score": 0,
                        "change_pct": change_pct,
                        "entry_reason": f"📈 技术突破：{', '.join(signals)}",
                        "sector": "",
                        "_score": score,
                    })
            
            # 按技术信号得分排序
            stocks.sort(key=lambda x: x.get("_score", 0), reverse=True)
            stocks = stocks[:20]
            
            self.progress.emit(100, f"✅ 找到 {len(stocks)} 只技术突破股")
            self.finished.emit(stocks, data_source_desc)
            
        except Exception as e:
            logger.error(f"技术扫描失败: {e}", exc_info=True)
            self.progress.emit(100, f"❌ 扫描失败，使用模拟数据")
            self.finished.emit(get_mock_tech_stocks(), "模拟数据")


# ============================================================
# ETF扫描Worker
# ============================================================

class ETFScanWorker(QThread):
    """ETF轮动扫描"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list, str)
    
    def run(self):
        try:
            self.progress.emit(20, "📊 获取ETF数据...")
            
            import akshare as ak
            df = ak.fund_etf_spot_em()
            
            if df is None or df.empty:
                self.progress.emit(100, "⚠️ ETF数据获取失败，使用模拟数据")
                self.finished.emit(get_mock_etfs(), "模拟数据")
                return
            
            self.progress.emit(60, f"✅ 获取到 {len(df)} 只ETF，开始筛选...")
            
            # 筛选活跃ETF
            df_sorted = df.sort_values('涨跌幅', ascending=False)
            
            etfs = []
            for _, row in df_sorted.head(30).iterrows():
                amount = float(row.get('成交额', 0) or 0) / 100000000
                if amount < 1:  # 成交额太小的排除
                    continue
                
                etfs.append({
                    "code": str(row.get('代码', '')),
                    "name": str(row.get('名称', '')),
                    "type": "ETF",
                    "price": float(row.get('最新价', 0) or 0),
                    "change_5d": float(row.get('涨跌幅', 0) or 0),
                    "amount": amount,
                    "index": str(row.get('市场', '-')),
                })
            
            self.progress.emit(100, f"✅ 筛选出 {len(etfs)} 只活跃ETF")
            self.finished.emit(etfs[:20], "AKShare ETF数据")
            
        except Exception as e:
            logger.error(f"ETF扫描失败: {e}")
            self.finished.emit(get_mock_etfs(), "模拟数据")


# ============================================================
# 外部数据解析Worker
# ============================================================

class ExternalParseWorker(QThread):
    """外部数据解析"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list, str)
    
    def run(self):
        self.progress.emit(30, "📂 扫描外部数据文件...")
        
        try:
            from markets.ashare.stock_pool.selectors.external_parser import ExternalDataParser
            parser = ExternalDataParser()
            pool = parser.parse_all()
            
            if pool and pool.stocks:
                stocks = []
                for stock in pool.stocks:
                    stocks.append({
                        "code": stock.code,
                        "name": stock.name,
                        "source": stock.source,
                        "data_source": "外部文件",
                        "period": stock.period,
                        "priority": stock.priority,
                        "mainline_score": 0,
                        "change_pct": 0,
                        "entry_reason": stock.entry_reason,
                        "sector": "",
                    })
                self.progress.emit(100, f"✅ 解析完成，{len(stocks)} 只股票")
                self.finished.emit(stocks, "外部数据文件")
                return
        except Exception as e:
            logger.debug(f"外部数据解析: {e}")
        
        self.progress.emit(100, "ℹ️ 无外部数据，使用示例")
        self.finished.emit(get_mock_external_stocks(), "示例数据")


# ============================================================
# 主面板
# ============================================================

class StockPoolPanel(QWidget):
    """股票池构建面板"""
    
    # 来源背景色
    SOURCE_COLORS = {
        "mainline": "#1E4976",      # 蓝色 - 主线强势
        "tech_breakout": "#1A5C3E", # 绿色 - 技术突破
        "etf": "#6B4423",           # 橙色 - ETF
        "broker": "#5C3D6E",        # 紫色 - 券商推荐
        "gurufocus": "#5C3D6E",     # 紫色 - GuruFocus
        "external": "#5C3D6E",      # 紫色 - 外部推荐
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.workers = {}
        self._all_stocks = []
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background: {Colors.BG_PRIMARY}; }}
            QTabBar::tab {{ background: {Colors.BG_SECONDARY}; color: {Colors.TEXT_SECONDARY}; padding: 10px 20px; border: none; border-bottom: 2px solid transparent; }}
            QTabBar::tab:selected {{ background: {Colors.BG_PRIMARY}; color: {Colors.TEXT_PRIMARY}; border-bottom: 2px solid {Colors.PRIMARY}; }}
            QTabBar::tab:hover {{ color: {Colors.TEXT_PRIMARY}; }}
        """)
        
        self.tab_widget.addTab(self._create_overview_tab(), "📊 综合总览")
        self.tab_widget.addTab(self._create_mainline_tab(), "🔥 主线强势")
        self.tab_widget.addTab(self._create_tech_tab(), "📈 技术突破")
        self.tab_widget.addTab(self._create_etf_tab(), "💹 ETF轮动")
        self.tab_widget.addTab(self._create_external_tab(), "📋 外部推荐")
        self.tab_widget.addTab(self._create_factor_filter_tab(), "🔍 因子筛选")
        self.tab_widget.addTab(self._create_signal_tab(), "📤 信号输出")
        
        layout.addWidget(self.tab_widget)
    
    def _create_stock_table(self, columns: List[str] = None) -> QTableWidget:
        if columns is None:
            columns = ["#", "代码", "名称", "数据源", "来源", "评分", "涨跌幅", "入池原因"]
        
        table = QTableWidget()
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(0, 40)
        table.setStyleSheet(f"""
            QTableWidget {{ background: {Colors.BG_TERTIARY}; border: 1px solid {Colors.BORDER_PRIMARY}; border-radius: 8px; gridline-color: {Colors.BORDER_PRIMARY}; }}
            QTableWidget::item {{ padding: 6px; color: {Colors.TEXT_PRIMARY}; }}
            QHeaderView::section {{ background: {Colors.BG_SECONDARY}; color: {Colors.TEXT_MUTED}; padding: 8px; border: none; font-weight: 600; }}
        """)
        return table
    
    def _fill_stock_table(self, table: QTableWidget, stocks: list, use_color: bool = True):
        """填充股票表格"""
        table.setRowCount(len(stocks))
        
        for i, stock in enumerate(stocks):
            source = str(stock.get('source', ''))
            bg_color = self.SOURCE_COLORS.get(source) if use_color else None
            
            items = [
                (str(i + 1), None),
                (str(stock.get('code', '')), None),
                (str(stock.get('name', '')), None),
                (str(stock.get('data_source', '')), None),
                (source, None),
                (f"{stock.get('mainline_score', 0):.1f}" if stock.get('mainline_score') else "-", None),
            ]
            
            change = stock.get('change_pct', 0)
            change_color = "#10B981" if change > 0 else ("#EF4444" if change < 0 else None)
            items.append((f"{change:+.2f}%", change_color))
            
            reason = str(stock.get('entry_reason', ''))
            items.append((reason[:40] + "..." if len(reason) > 40 else reason, None))
            
            for col, (text, fg_color) in enumerate(items):
                item = QTableWidgetItem(text)
                if bg_color:
                    item.setBackground(QColor(bg_color))
                if fg_color:
                    item.setForeground(QColor(fg_color))
                table.setItem(i, col, item)
    
    def _check_mainline_data(self) -> tuple:
        """检查五维综合评分数据是否存在"""
        composite_file = Path.home() / '.local/share/trquant/reports/mainline/latest_composite_scores.json'
        
        if composite_file.exists():
            try:
                import os
                file_mtime = os.path.getmtime(composite_file)
                age_hours = (datetime.now().timestamp() - file_mtime) / 3600
                
                with open(composite_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                mainline_count = len(data.get("scores", []))
                
                return True, age_hours, mainline_count, str(composite_file)
            except Exception as e:
                logger.warning(f"检查综合评分数据失败: {e}")
        
        heatmap_file = Path.home() / '.local/share/trquant/reports/heatmap/latest_heatmap_scores.json'
        
        if heatmap_file.exists():
            try:
                import os
                file_mtime = os.path.getmtime(heatmap_file)
                age_hours = (datetime.now().timestamp() - file_mtime) / 3600
                
                with open(heatmap_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                mainline_count = len(data.get("scores", []))
                
                return True, age_hours, mainline_count, str(heatmap_file)
            except Exception as e:
                logger.warning(f"检查热度评分数据失败: {e}")
        
        return False, 0, 0, ""
    
    # ============================================================
    # Tab 1: 综合总览
    # ============================================================
    
    def _create_overview_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # 说明
        intro = QLabel(
            "📊 <b>股票池综合总览</b> - 汇总各来源的筛选结果<br>"
            f"<span style='color: {Colors.TEXT_SECONDARY};'>"
            "数据流：投资主线(五维评分) → 【候选池构建】→ 因子开发 → 策略生成<br>"
            "数据源：JQData成分股 + TuShare Pro行情 + AKShare备选</span>"
        )
        intro.setStyleSheet(f"font-size: 14px; color: {Colors.TEXT_PRIMARY};")
        intro.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(intro)
        
        # 统计卡片
        stats_layout = QHBoxLayout()
        self.stat_mainline = self._create_stat_card("🔵 主线强势", "0")
        self.stat_tech = self._create_stat_card("🟢 技术突破", "0")
        self.stat_etf = self._create_stat_card("🟠 ETF轮动", "0")
        self.stat_external = self._create_stat_card("🟣 外部推荐", "0")
        stats_layout.addWidget(self.stat_mainline)
        stats_layout.addWidget(self.stat_tech)
        stats_layout.addWidget(self.stat_etf)
        stats_layout.addWidget(self.stat_external)
        layout.addLayout(stats_layout)
        
        # 按钮
        btn_layout = QHBoxLayout()
        self.scan_all_btn = QPushButton("🚀 一键扫描全部")
        self.scan_all_btn.setStyleSheet(f"""
            QPushButton {{ background: {Colors.PRIMARY}; color: white; border: none; border-radius: 8px; padding: 12px 24px; font-size: 14px; font-weight: 600; }}
            QPushButton:hover {{ background: {Colors.PRIMARY_LIGHT}; }}
            QPushButton:disabled {{ background: {Colors.BG_TERTIARY}; color: {Colors.TEXT_MUTED}; }}
        """)
        self.scan_all_btn.clicked.connect(self._scan_all)
        btn_layout.addWidget(self.scan_all_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 进度
        self.overview_progress = QProgressBar()
        self.overview_progress.setVisible(False)
        self.overview_progress.setStyleSheet(f"""
            QProgressBar {{ border: none; background: {Colors.BG_TERTIARY}; border-radius: 4px; height: 8px; }}
            QProgressBar::chunk {{ background: {Colors.PRIMARY}; border-radius: 4px; }}
        """)
        layout.addWidget(self.overview_progress)
        
        self.overview_status = QLabel("")
        self.overview_status.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; padding: 4px;")
        self.overview_status.setWordWrap(True)
        layout.addWidget(self.overview_status)
        
        self.overview_source = QLabel("")
        self.overview_source.setStyleSheet(f"color: {Colors.PRIMARY}; font-size: 12px; font-weight: 600;")
        layout.addWidget(self.overview_source)
        
        # 图例
        legend_layout = QHBoxLayout()
        for text, color in [("🔵 主线强势", "#1E4976"), ("🟢 技术突破", "#1A5C3E"), ("🟠 ETF", "#6B4423"), ("🟣 外部推荐", "#5C3D6E")]:
            lbl = QLabel(text)
            lbl.setStyleSheet(f"background: {color}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px;")
            legend_layout.addWidget(lbl)
        legend_layout.addStretch()
        layout.addLayout(legend_layout)
        
        # 表格
        self.overview_table = self._create_stock_table()
        layout.addWidget(self.overview_table)
        
        return widget
    
    def _create_stat_card(self, label: str, value: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background: {Colors.BG_TERTIARY}; border: 1px solid {Colors.BORDER_PRIMARY}; border-radius: 8px; }}")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        value_label = QLabel(value)
        value_label.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {Colors.PRIMARY};")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setObjectName("value")
        layout.addWidget(value_label)
        
        text_label = QLabel(label)
        text_label.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_SECONDARY};")
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(text_label)
        
        return card
    
    def _update_stat(self, card: QFrame, value: int):
        try:
            value_label = card.findChild(QLabel, "value")
            if value_label:
                value_label.setText(str(value))
        except:
            pass
    
    def _scan_all(self):
        """一键扫描全部"""
        exists, age_hours, count, filepath = self._check_mainline_data()
        
        if not exists:
            reply = QMessageBox.question(
                self, 
                "主线数据缺失",
                "⚠️ 未找到五维综合评分结果！\n\n"
                "主线强势股筛选需要先运行「投资主线 → 综合评分」。\n\n"
                "是否自动运行主线识别？（约需30秒）",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._run_mainline_identification()
                return
            else:
                self.overview_status.setText("⚠️ 跳过主线识别，仅扫描技术突破、ETF、外部推荐")
        elif age_hours > 24:
            self.overview_status.setText(f"⚠️ 主线数据已有 {age_hours:.1f} 小时未更新")
        else:
            source_type = "综合评分" if "composite" in filepath else "热度评分"
            self.overview_status.setText(f"✅ 检测到{source_type}：{count} 个主线，{age_hours:.1f} 小时前更新")
        
        self._do_scan_all()
    
    def _do_scan_all(self):
        """执行扫描"""
        self.overview_table.setRowCount(0)
        self._all_stocks = []
        self.overview_progress.setVisible(True)
        self.overview_progress.setValue(0)
        self.scan_all_btn.setEnabled(False)
        self.overview_source.setText("")
        
        self._start_mainline_scan()
    
    def _run_mainline_identification(self):
        """自动运行主线识别"""
        self.overview_status.setText("🔄 正在运行五维综合评分...")
        self.overview_progress.setVisible(True)
        self.overview_progress.setValue(0)
        self.scan_all_btn.setEnabled(False)
        
        from gui.widgets.dimension_tabs.composite_tab import CompositeWorker
        
        self.mainline_worker = CompositeWorker(period="medium", data_source="akshare")
        self.mainline_worker.progress.connect(
            lambda m: self.overview_status.setText(f"🔄 主线识别：{m}")
        )
        self.mainline_worker.finished.connect(self._on_mainline_identification_done)
        self.mainline_worker.error.connect(self._on_mainline_identification_error)
        self.mainline_worker.start()
    
    def _on_mainline_identification_done(self, results: list):
        """主线识别完成"""
        self._save_mainline_results(results)
        self.overview_status.setText(f"✅ 主线识别完成！{len(results)} 个主线，继续扫描候选池...")
        self._do_scan_all()
    
    def _save_mainline_results(self, results: list):
        """保存主线识别结果"""
        try:
            output_dir = Path.home() / ".local/share/trquant/reports/mainline"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            scores_data = []
            for r in results:
                scores_data.append({
                    "name": r.name,
                    "total_score": r.total_score,
                    "funds_score": r.funds_score,
                    "heat_score": r.heat_score,
                    "momentum_score": r.momentum_score,
                    "policy_score": r.policy_score,
                    "leader_score": r.leader_score,
                    "leader_stock": r.leader_stock,
                    "leader_change": r.leader_change,
                    "signal": r.signal,
                    "mainline_type": r.mainline_type,
                })
            
            data = {
                "timestamp": datetime.now().isoformat(),
                "period": "medium",
                "count": len(results),
                "scores": scores_data,
            }
            
            json_path = output_dir / "latest_composite_scores.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 主线识别结果已保存到: {json_path}")
            
        except Exception as e:
            logger.error(f"保存主线识别结果失败: {e}")
    
    def _on_mainline_identification_error(self, error: str):
        """主线识别失败"""
        self.overview_status.setText(f"❌ 主线识别失败: {error}，继续扫描其他来源...")
        self.scan_all_btn.setEnabled(True)
        self.overview_progress.setVisible(False)
        self._do_scan_all()
    
    def _start_mainline_scan(self):
        self.overview_status.setText("🔵 正在扫描主线强势股...")
        self.workers['overview_mainline'] = MainlineScanWorker()
        self.workers['overview_mainline'].progress.connect(
            lambda p, m: (self.overview_progress.setValue(int(p * 0.4)), self.overview_status.setText(m))
        )
        self.workers['overview_mainline'].finished.connect(self._on_overview_mainline_done)
        self.workers['overview_mainline'].start()
    
    def _on_overview_mainline_done(self, stocks: list, source: str):
        logger.info(f"📊 主线扫描完成: {len(stocks)} 只股票, 数据源: {source}")
        if stocks:
            logger.info(f"   示例: {stocks[0] if stocks else 'N/A'}")
        self._all_stocks.extend(stocks)
        self._update_stat(self.stat_mainline, len(stocks))
        self.overview_source.setText(f"主线强势：{source}")
        self._start_tech_scan()
    
    def _start_tech_scan(self):
        self.overview_status.setText("🟢 正在扫描技术突破股...")
        self.workers['overview_tech'] = TechScanWorker()
        self.workers['overview_tech'].progress.connect(
            lambda p, m: (self.overview_progress.setValue(40 + int(p * 0.25)), self.overview_status.setText(m))
        )
        self.workers['overview_tech'].finished.connect(self._on_overview_tech_done)
        self.workers['overview_tech'].start()
    
    def _on_overview_tech_done(self, stocks: list, source: str):
        self._all_stocks.extend(stocks)
        self._update_stat(self.stat_tech, len(stocks))
        src = self.overview_source.text()
        self.overview_source.setText(f"{src} | 技术突破：{source}")
        self._start_etf_scan()
    
    def _start_etf_scan(self):
        self.overview_status.setText("🟠 正在扫描ETF...")
        self.workers['overview_etf'] = ETFScanWorker()
        self.workers['overview_etf'].progress.connect(
            lambda p, m: (self.overview_progress.setValue(65 + int(p * 0.2)), self.overview_status.setText(m))
        )
        self.workers['overview_etf'].finished.connect(self._on_overview_etf_done)
        self.workers['overview_etf'].start()
    
    def _on_overview_etf_done(self, etfs: list, source: str):
        for etf in etfs:
            self._all_stocks.append({
                "code": etf.get("code", ""),
                "name": etf.get("name", ""),
                "source": "etf",
                "data_source": source,
                "period": "medium",
                "priority": 3,
                "mainline_score": 0,
                "change_pct": etf.get("change_5d", 0),
                "entry_reason": f"💹 ETF轮动：成交{etf.get('amount', 0):.1f}亿",
                "sector": "",
            })
        self._update_stat(self.stat_etf, len(etfs))
        src = self.overview_source.text()
        self.overview_source.setText(f"{src} | ETF：{source}")
        self._start_external_scan()
    
    def _start_external_scan(self):
        self.overview_status.setText("🟣 正在解析外部推荐...")
        self.workers['overview_external'] = ExternalParseWorker()
        self.workers['overview_external'].progress.connect(
            lambda p, m: (self.overview_progress.setValue(85 + int(p * 0.15)), self.overview_status.setText(m))
        )
        self.workers['overview_external'].finished.connect(self._on_overview_external_done)
        self.workers['overview_external'].start()
    
    def _on_overview_external_done(self, stocks: list, source: str):
        self._all_stocks.extend(stocks)
        self._update_stat(self.stat_external, len(stocks))
        
        logger.info(f"📊 扫描汇总: 总共 {len(self._all_stocks)} 只股票")
        
        # 去重
        seen = set()
        unique = []
        for s in self._all_stocks:
            code = s.get("code", "")
            name = s.get("name", "")
            # 如果没有code但有name，也保留
            key = code if code else name
            if key and key not in seen:
                seen.add(key)
                unique.append(s)
        
        unique.sort(key=lambda x: (x.get("priority", 5), -x.get("mainline_score", 0)))
        
        logger.info(f"📊 去重后: {len(unique)} 只股票")
        if unique:
            logger.info(f"   前3只: {[s.get('name', 'N/A') for s in unique[:3]]}")
        
        self._fill_stock_table(self.overview_table, unique[:50], use_color=True)
        
        self.overview_progress.setVisible(False)
        self.scan_all_btn.setEnabled(True)
        self.overview_status.setText(f"✅ 扫描完成！共 {len(unique)} 只股票（去重后）")
        src = self.overview_source.text()
        self.overview_source.setText(f"{src} | 外部：{source}")
    
    # ============================================================
    # Tab 2-6: 其他Tab
    # ============================================================
    
    def _create_mainline_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        layout.addWidget(QLabel("<b>🔥 主线强势股</b> - 从投资主线识别结果中筛选强势股"))
        
        dep_label = QLabel(f"📌 <b>前置依赖：</b>需要先运行「投资主线 → 综合评分」生成主线数据")
        dep_label.setStyleSheet(f"color: #F59E0B; font-size: 12px;")
        layout.addWidget(dep_label)
        
        btn = QPushButton("🔍 开始扫描")
        btn.setStyleSheet(f"background: {Colors.PRIMARY}; color: white; border: none; border-radius: 6px; padding: 10px 20px; font-weight: 600;")
        btn.clicked.connect(lambda: self._scan_single("mainline"))
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignLeft)
        
        self.mainline_progress = QProgressBar()
        self.mainline_progress.setVisible(False)
        layout.addWidget(self.mainline_progress)
        
        self.mainline_status = QLabel("")
        self.mainline_status.setWordWrap(True)
        layout.addWidget(self.mainline_status)
        
        self.mainline_table = self._create_stock_table()
        layout.addWidget(self.mainline_table)
        
        return widget
    
    def _create_tech_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        layout.addWidget(QLabel("<b>📈 技术突破</b> - 全市场扫描涨停、放量、突破信号"))
        layout.addWidget(QLabel(f"<span style='color: {Colors.TEXT_SECONDARY};'>数据源：TuShare Pro（优先）→ AKShare（备选）</span>"))
        
        btn = QPushButton("🔍 开始扫描")
        btn.setStyleSheet(f"background: {Colors.PRIMARY}; color: white; border: none; border-radius: 6px; padding: 10px 20px; font-weight: 600;")
        btn.clicked.connect(lambda: self._scan_single("tech"))
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignLeft)
        
        self.tech_progress = QProgressBar()
        self.tech_progress.setVisible(False)
        layout.addWidget(self.tech_progress)
        
        self.tech_status = QLabel("")
        self.tech_status.setWordWrap(True)
        layout.addWidget(self.tech_status)
        
        self.tech_table = self._create_stock_table()
        layout.addWidget(self.tech_table)
        
        return widget
    
    def _create_etf_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        layout.addWidget(QLabel("<b>💹 ETF轮动</b> - 筛选强势行业/主题ETF"))
        
        btn = QPushButton("🔍 开始扫描")
        btn.setStyleSheet(f"background: {Colors.PRIMARY}; color: white; border: none; border-radius: 6px; padding: 10px 20px; font-weight: 600;")
        btn.clicked.connect(lambda: self._scan_single("etf"))
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignLeft)
        
        self.etf_progress = QProgressBar()
        self.etf_progress.setVisible(False)
        layout.addWidget(self.etf_progress)
        
        self.etf_status = QLabel("")
        layout.addWidget(self.etf_status)
        
        self.etf_table = self._create_stock_table(["#", "代码", "名称", "类型", "最新价", "涨跌幅", "成交额(亿)", "市场"])
        layout.addWidget(self.etf_table)
        
        return widget
    
    def _create_external_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        layout.addWidget(QLabel("<b>📋 外部推荐</b> - 整合券商金股、GuruFocus等"))
        
        data_path = Path.home() / ".local/share/trquant/data/stock_pool/external"
        layout.addWidget(QLabel(f"📁 数据目录：{data_path}"))
        
        btn = QPushButton("🔍 解析数据")
        btn.setStyleSheet(f"background: {Colors.PRIMARY}; color: white; border: none; border-radius: 6px; padding: 10px 20px; font-weight: 600;")
        btn.clicked.connect(lambda: self._scan_single("external"))
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignLeft)
        
        self.external_progress = QProgressBar()
        self.external_progress.setVisible(False)
        layout.addWidget(self.external_progress)
        
        self.external_status = QLabel("")
        layout.addWidget(self.external_status)
        
        self.external_table = self._create_stock_table()
        layout.addWidget(self.external_table)
        
        return widget
    
    def _create_signal_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        layout.addWidget(QLabel("<b>📤 信号输出</b> - 生成PTrade/QMT策略代码"))
        
        btn = QPushButton("📄 生成PTrade代码")
        btn.setStyleSheet(f"background: #10B981; color: white; border: none; border-radius: 6px; padding: 10px 20px; font-weight: 600;")
        btn.clicked.connect(self._generate_code)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignLeft)
        
        self.code_preview = QTextEdit()
        self.code_preview.setReadOnly(True)
        self.code_preview.setStyleSheet(f"background: {Colors.BG_TERTIARY}; color: {Colors.TEXT_PRIMARY}; border: 1px solid {Colors.BORDER_PRIMARY}; border-radius: 8px; font-family: monospace;")
        self.code_preview.setPlaceholderText("先在其他Tab扫描股票，然后点击生成代码...")
        layout.addWidget(self.code_preview)
        
        return widget
    
    def _scan_single(self, scan_type: str):
        """单独扫描"""
        if scan_type == "mainline":
            exists, age_hours, count, filepath = self._check_mainline_data()
            
            if not exists:
                QMessageBox.warning(
                    self,
                    "主线数据缺失",
                    "⚠️ 未找到五维综合评分结果！\n\n"
                    "请先运行「投资主线 → 综合评分」生成主线数据。"
                )
                return
            
            self.mainline_table.setRowCount(0)
            self.mainline_progress.setVisible(True)
            self.mainline_progress.setValue(0)
            self.mainline_status.setText("正在扫描...")
            
            self.workers['mainline'] = MainlineScanWorker()
            self.workers['mainline'].progress.connect(
                lambda p, m: (self.mainline_progress.setValue(p), self.mainline_status.setText(m))
            )
            self.workers['mainline'].finished.connect(
                lambda stocks, src: (
                    self.mainline_progress.setVisible(False),
                    self.mainline_status.setText(f"✅ 完成 [{src}]"),
                    self._fill_stock_table(self.mainline_table, stocks, use_color=False)
                )
            )
            self.workers['mainline'].start()
            
        elif scan_type == "tech":
            self.tech_table.setRowCount(0)
            self.tech_progress.setVisible(True)
            self.tech_progress.setValue(0)
            
            self.workers['tech'] = TechScanWorker()
            self.workers['tech'].progress.connect(
                lambda p, m: (self.tech_progress.setValue(p), self.tech_status.setText(m))
            )
            self.workers['tech'].finished.connect(
                lambda stocks, src: (
                    self.tech_progress.setVisible(False),
                    self.tech_status.setText(f"✅ 完成 [{src}]"),
                    self._fill_stock_table(self.tech_table, stocks, use_color=False)
                )
            )
            self.workers['tech'].start()
            
        elif scan_type == "etf":
            self.etf_table.setRowCount(0)
            self.etf_progress.setVisible(True)
            self.etf_progress.setValue(0)
            
            self.workers['etf'] = ETFScanWorker()
            self.workers['etf'].progress.connect(
                lambda p, m: (self.etf_progress.setValue(p), self.etf_status.setText(m))
            )
            self.workers['etf'].finished.connect(self._on_etf_single_done)
            self.workers['etf'].start()
            
        elif scan_type == "external":
            self.external_table.setRowCount(0)
            self.external_progress.setVisible(True)
            self.external_progress.setValue(0)
            
            self.workers['external'] = ExternalParseWorker()
            self.workers['external'].progress.connect(
                lambda p, m: (self.external_progress.setValue(p), self.external_status.setText(m))
            )
            self.workers['external'].finished.connect(
                lambda stocks, src: (
                    self.external_progress.setVisible(False),
                    self.external_status.setText(f"✅ 完成 [{src}]"),
                    self._fill_stock_table(self.external_table, stocks, use_color=False)
                )
            )
            self.workers['external'].start()
    
    def _on_etf_single_done(self, etfs: list, source: str):
        self.etf_progress.setVisible(False)
        self.etf_status.setText(f"✅ 完成 [{source}]")
        
        self.etf_table.setRowCount(len(etfs))
        for i, etf in enumerate(etfs):
            self.etf_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.etf_table.setItem(i, 1, QTableWidgetItem(str(etf.get('code', ''))))
            self.etf_table.setItem(i, 2, QTableWidgetItem(str(etf.get('name', ''))))
            self.etf_table.setItem(i, 3, QTableWidgetItem(str(etf.get('type', ''))))
            self.etf_table.setItem(i, 4, QTableWidgetItem(f"{etf.get('price', 0):.3f}"))
            
            change = etf.get('change_5d', 0)
            change_item = QTableWidgetItem(f"{change:+.2f}%")
            change_item.setForeground(QColor("#10B981" if change > 0 else "#EF4444"))
            self.etf_table.setItem(i, 5, change_item)
            
            self.etf_table.setItem(i, 6, QTableWidgetItem(f"{etf.get('amount', 0):.2f}"))
            self.etf_table.setItem(i, 7, QTableWidgetItem(str(etf.get('index', '-'))))
    
    def _generate_code(self):
        codes = set()
        for table in [self.mainline_table, self.tech_table, self.external_table]:
            for row in range(table.rowCount()):
                item = table.item(row, 1)
                if item:
                    codes.add(item.text())
        
        if not codes:
            QMessageBox.warning(self, "提示", "请先扫描股票")
            return
        
        code_list = list(codes)[:20]
        
        code = f'''# -*- coding: utf-8 -*-
"""
韬睿量化 - 股票池策略
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
股票数量: {len(code_list)}
"""

STOCK_POOL = {code_list}

def initialize(context):
    set_benchmark('000300.XSHG')
    run_monthly(rebalance, 1, time='open')

def rebalance(context):
    stocks = STOCK_POOL
    for stock in list(context.portfolio.positions.keys()):
        if stock not in stocks:
            order_target(stock, 0)
    
    if len(stocks) > 0:
        weight = 1.0 / len(stocks)
        for stock in stocks:
            order_target_value(stock, context.portfolio.total_value * weight)
'''
        self.code_preview.setText(code)
        
        save_dir = Path.home() / ".local/share/trquant/strategies/ptrade"
        save_dir.mkdir(parents=True, exist_ok=True)
        filepath = save_dir / f"pool_strategy_{datetime.now().strftime('%Y%m%d')}.py"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        
        QMessageBox.information(self, "完成", f"代码已保存: {filepath}")
    
    def _create_factor_filter_tab(self) -> QWidget:
        """创建因子筛选标签页"""
        try:
            from gui.widgets.factor_filter_tab import FactorFilterTab
            tab = FactorFilterTab()
            
            # 尝试获取JQData客户端
            try:
                from jqdata.client import JQDataClient
                jq_client = JQDataClient()
                if jq_client.authenticate():
                    tab.set_jq_client(jq_client)
                    logger.info("✅ 因子筛选标签页已初始化JQData")
            except Exception as e:
                logger.warning(f"因子筛选标签页JQData初始化失败: {e}")
            
            return tab
        except Exception as e:
            logger.error(f"因子筛选标签页加载失败: {e}")
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(20, 20, 20, 20)
            error_label = QLabel(f"因子筛选功能加载失败: {e}")
            error_label.setStyleSheet(f"color: {Colors.ERROR};")
            layout.addWidget(error_label)
            return widget
