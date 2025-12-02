# -*- coding: utf-8 -*-
"""
时间维度数据管理器
==================

核心设计原则：
所有模块数据都按时间维度存储和检索，支持：
1. 按日期查询历史状态
2. 按周期(短/中/长期)分类
3. 数据变更追踪
4. 快照与增量更新

遵循优秀软件工程原则：
- 单一职责：每个类只负责一个功能
- 开闭原则：对扩展开放，对修改关闭
- 依赖倒置：依赖抽象而非具体实现
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, TypeVar, Generic
from dataclasses import dataclass, field, asdict
from enum import Enum
from abc import ABC, abstractmethod
import json

logger = logging.getLogger(__name__)

# MongoDB连接
try:
    from pymongo import MongoClient, DESCENDING, ASCENDING
    from pymongo.errors import ConnectionFailure
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    logger.warning("pymongo未安装，时间维度管理功能受限")


class Period(Enum):
    """投资周期枚举"""
    SHORT = "short"      # 短期: 1-5天
    MEDIUM = "medium"    # 中期: 1-4周
    LONG = "long"        # 长期: 1月+
    
    @property
    def days(self) -> int:
        """周期对应的天数"""
        return {"short": 5, "medium": 20, "long": 60}[self.value]
    
    @property
    def label(self) -> str:
        """中文标签"""
        return {"short": "短期", "medium": "中期", "long": "长期"}[self.value]


@dataclass
class SnapshotMeta:
    """快照元数据"""
    snapshot_id: str
    snapshot_date: str              # YYYY-MM-DD
    period: str                     # short/medium/long
    created_at: str                 # ISO格式时间戳
    source: str                     # 数据来源
    version: str = "1.0"
    checksum: Optional[str] = None  # 数据校验和
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CandidatePoolSnapshot:
    """候选池快照"""
    meta: SnapshotMeta
    mainlines_used: List[Dict]      # 使用的主线列表
    stocks: List[Dict]              # 候选股票列表
    statistics: Dict                # 统计信息
    data_permission: Dict           # 数据权限快照
    
    def to_dict(self) -> Dict:
        return {
            "meta": self.meta.to_dict(),
            "mainlines_used": self.mainlines_used,
            "stocks": self.stocks,
            "statistics": self.statistics,
            "data_permission": self.data_permission
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CandidatePoolSnapshot':
        return cls(
            meta=SnapshotMeta(**data.get("meta", {})),
            mainlines_used=data.get("mainlines_used", []),
            stocks=data.get("stocks", []),
            statistics=data.get("statistics", {}),
            data_permission=data.get("data_permission", {})
        )


@dataclass
class MainlineSnapshot:
    """主线快照"""
    meta: SnapshotMeta
    mainlines: List[Dict]           # 主线列表
    rotation_signal: Optional[str]  # 轮动信号
    market_context: Dict            # 市场背景
    
    def to_dict(self) -> Dict:
        return {
            "meta": self.meta.to_dict(),
            "mainlines": self.mainlines,
            "rotation_signal": self.rotation_signal,
            "market_context": self.market_context
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MainlineSnapshot':
        return cls(
            meta=SnapshotMeta(**data.get("meta", {})),
            mainlines=data.get("mainlines", []),
            rotation_signal=data.get("rotation_signal"),
            market_context=data.get("market_context", {})
        )


@dataclass
class ChangeRecord:
    """变更记录"""
    timestamp: str
    change_type: str    # add/remove/update
    item_type: str      # stock/mainline
    item_id: str
    item_name: str
    details: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return asdict(self)


class TimeDimensionRepository(ABC):
    """时间维度数据仓库抽象类"""
    
    @abstractmethod
    def save_snapshot(self, collection: str, snapshot: Dict) -> bool:
        """保存快照"""
        pass
    
    @abstractmethod
    def get_snapshot(self, collection: str, date: str, period: str) -> Optional[Dict]:
        """获取指定日期和周期的快照"""
        pass
    
    @abstractmethod
    def get_latest_snapshot(self, collection: str, period: str = None) -> Optional[Dict]:
        """获取最新快照"""
        pass
    
    @abstractmethod
    def get_snapshots_range(self, collection: str, start_date: str, end_date: str, 
                            period: str = None) -> List[Dict]:
        """获取日期范围内的快照"""
        pass
    
    @abstractmethod
    def save_change_record(self, collection: str, record: Dict) -> bool:
        """保存变更记录"""
        pass
    
    @abstractmethod
    def get_change_history(self, collection: str, item_id: str = None, 
                           limit: int = 100) -> List[Dict]:
        """获取变更历史"""
        pass


class MongoDBRepository(TimeDimensionRepository):
    """MongoDB时间维度数据仓库"""
    
    def __init__(self, uri: str = "mongodb://localhost:27017", db_name: str = "jqquant"):
        self.uri = uri
        self.db_name = db_name
        self.client = None
        self.db = None
        self._connect()
    
    def _connect(self):
        """连接MongoDB"""
        if not MONGODB_AVAILABLE:
            logger.warning("MongoDB不可用")
            return
        
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=3000)
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            self._ensure_indexes()
            logger.info(f"MongoDB连接成功: {self.db_name}")
        except Exception as e:
            logger.error(f"MongoDB连接失败: {e}")
            self.db = None
    
    def _ensure_indexes(self):
        """确保索引存在"""
        if self.db is None:
            return
        
        try:
            # 候选池快照索引
            self.db.candidate_pool_snapshots.create_index(
                [("meta.snapshot_date", DESCENDING), ("meta.period", ASCENDING)],
                unique=True
            )
            self.db.candidate_pool_snapshots.create_index([("meta.created_at", DESCENDING)])
            
            # 主线快照索引
            self.db.mainline_snapshots.create_index(
                [("meta.snapshot_date", DESCENDING), ("meta.period", ASCENDING)],
                unique=True
            )
            self.db.mainline_snapshots.create_index([("meta.created_at", DESCENDING)])
            
            # 变更记录索引
            self.db.change_records.create_index([("timestamp", DESCENDING)])
            self.db.change_records.create_index([("item_id", ASCENDING)])
            
            logger.debug("MongoDB索引已创建")
        except Exception as e:
            logger.warning(f"创建索引失败: {e}")
    
    def save_snapshot(self, collection: str, snapshot: Dict) -> bool:
        """保存快照（使用upsert）"""
        if self.db is None:
            return False
        
        try:
            meta = snapshot.get("meta", {})
            filter_key = {
                "meta.snapshot_date": meta.get("snapshot_date"),
                "meta.period": meta.get("period")
            }
            
            result = self.db[collection].replace_one(filter_key, snapshot, upsert=True)
            logger.info(f"保存快照成功: {collection}, date={meta.get('snapshot_date')}, period={meta.get('period')}")
            return True
        except Exception as e:
            logger.error(f"保存快照失败: {e}")
            return False
    
    def get_snapshot(self, collection: str, date: str, period: str) -> Optional[Dict]:
        """获取指定日期和周期的快照"""
        if self.db is None:
            return None
        
        try:
            result = self.db[collection].find_one({
                "meta.snapshot_date": date,
                "meta.period": period
            })
            if result:
                result.pop('_id', None)
            return result
        except Exception as e:
            logger.error(f"获取快照失败: {e}")
            return None
    
    def get_latest_snapshot(self, collection: str, period: str = None) -> Optional[Dict]:
        """获取最新快照"""
        if self.db is None:
            return None
        
        try:
            query = {}
            if period:
                query["meta.period"] = period
            
            result = self.db[collection].find_one(
                query,
                sort=[("meta.created_at", DESCENDING)]
            )
            if result:
                result.pop('_id', None)
            return result
        except Exception as e:
            logger.error(f"获取最新快照失败: {e}")
            return None
    
    def get_snapshots_range(self, collection: str, start_date: str, end_date: str,
                            period: str = None) -> List[Dict]:
        """获取日期范围内的快照"""
        if self.db is None:
            return []
        
        try:
            query = {
                "meta.snapshot_date": {"$gte": start_date, "$lte": end_date}
            }
            if period:
                query["meta.period"] = period
            
            results = list(self.db[collection].find(
                query,
                sort=[("meta.snapshot_date", DESCENDING)]
            ))
            
            for r in results:
                r.pop('_id', None)
            
            return results
        except Exception as e:
            logger.error(f"获取快照范围失败: {e}")
            return []
    
    def save_change_record(self, collection: str, record: Dict) -> bool:
        """保存变更记录"""
        if self.db is None:
            return False
        
        try:
            self.db[collection].insert_one(record)
            return True
        except Exception as e:
            logger.error(f"保存变更记录失败: {e}")
            return False
    
    def get_change_history(self, collection: str, item_id: str = None,
                           limit: int = 100) -> List[Dict]:
        """获取变更历史"""
        if self.db is None:
            return []
        
        try:
            query = {}
            if item_id:
                query["item_id"] = item_id
            
            results = list(self.db[collection].find(
                query,
                sort=[("timestamp", DESCENDING)],
                limit=limit
            ))
            
            for r in results:
                r.pop('_id', None)
            
            return results
        except Exception as e:
            logger.error(f"获取变更历史失败: {e}")
            return []


class TimeDimensionManager:
    """
    时间维度管理器
    
    统一管理所有模块的时间维度数据，包括：
    - 候选池快照
    - 主线快照
    - 变更记录
    - 历史查询
    """
    
    def __init__(self, repository: TimeDimensionRepository = None):
        self.repo = repository or MongoDBRepository()
        self._change_callbacks = []
    
    def register_change_callback(self, callback):
        """注册变更回调"""
        self._change_callbacks.append(callback)
    
    # ========== 候选池管理 ==========
    
    def save_candidate_pool_snapshot(
        self,
        stocks: List[Dict],
        mainlines_used: List[Dict],
        period: Period = Period.MEDIUM,
        date: str = None,
        data_permission: Dict = None,
        source: str = "jqdata"
    ) -> bool:
        """
        保存候选池快照
        
        Args:
            stocks: 候选股票列表
            mainlines_used: 使用的主线
            period: 投资周期
            date: 快照日期（默认今天）
            data_permission: 数据权限信息
            source: 数据来源
        """
        date = date or datetime.now().strftime("%Y-%m-%d")
        
        # 创建元数据
        meta = SnapshotMeta(
            snapshot_id=f"pool_{date}_{period.value}",
            snapshot_date=date,
            period=period.value,
            created_at=datetime.now().isoformat(),
            source=source
        )
        
        # 计算统计信息
        statistics = self._calculate_pool_statistics(stocks)
        
        # 创建快照
        snapshot = CandidatePoolSnapshot(
            meta=meta,
            mainlines_used=mainlines_used,
            stocks=stocks,
            statistics=statistics,
            data_permission=data_permission or {}
        )
        
        # 保存
        success = self.repo.save_snapshot("candidate_pool_snapshots", snapshot.to_dict())
        
        if success:
            # 记录变更
            self._record_pool_changes(date, period, stocks)
        
        return success
    
    def get_candidate_pool_snapshot(
        self,
        date: str = None,
        period: Period = Period.MEDIUM
    ) -> Optional[CandidatePoolSnapshot]:
        """获取候选池快照"""
        date = date or datetime.now().strftime("%Y-%m-%d")
        
        data = self.repo.get_snapshot("candidate_pool_snapshots", date, period.value)
        if data:
            return CandidatePoolSnapshot.from_dict(data)
        return None
    
    def get_latest_candidate_pool(
        self,
        period: Period = None
    ) -> Optional[CandidatePoolSnapshot]:
        """获取最新候选池"""
        period_value = period.value if period else None
        data = self.repo.get_latest_snapshot("candidate_pool_snapshots", period_value)
        if data:
            return CandidatePoolSnapshot.from_dict(data)
        return None
    
    def get_candidate_pool_history(
        self,
        start_date: str,
        end_date: str,
        period: Period = None
    ) -> List[CandidatePoolSnapshot]:
        """获取候选池历史"""
        period_value = period.value if period else None
        data_list = self.repo.get_snapshots_range(
            "candidate_pool_snapshots", start_date, end_date, period_value
        )
        return [CandidatePoolSnapshot.from_dict(d) for d in data_list]
    
    def _calculate_pool_statistics(self, stocks: List[Dict]) -> Dict:
        """计算候选池统计信息"""
        if not stocks:
            return {"count": 0}
        
        # 按主线分组
        mainline_dist = {}
        for s in stocks:
            ml = s.get("mainline", "未分类")
            mainline_dist[ml] = mainline_dist.get(ml, 0) + 1
        
        return {
            "count": len(stocks),
            "mainline_distribution": mainline_dist,
            "avg_score": sum(s.get("score", 0) for s in stocks) / len(stocks) if stocks else 0
        }
    
    def _record_pool_changes(self, date: str, period: Period, current_stocks: List[Dict]):
        """记录候选池变更"""
        # 获取前一个快照
        prev_date = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        prev_snapshot = self.get_candidate_pool_snapshot(prev_date, period)
        
        if not prev_snapshot:
            return
        
        prev_codes = {s.get("code") for s in prev_snapshot.stocks}
        curr_codes = {s.get("code") for s in current_stocks}
        
        # 新增
        added = curr_codes - prev_codes
        for code in added:
            stock = next((s for s in current_stocks if s.get("code") == code), {})
            record = ChangeRecord(
                timestamp=datetime.now().isoformat(),
                change_type="add",
                item_type="stock",
                item_id=code,
                item_name=stock.get("name", ""),
                details={"mainline": stock.get("mainline"), "date": date, "period": period.value}
            )
            self.repo.save_change_record("change_records", record.to_dict())
        
        # 移除
        removed = prev_codes - curr_codes
        for code in removed:
            stock = next((s for s in prev_snapshot.stocks if s.get("code") == code), {})
            record = ChangeRecord(
                timestamp=datetime.now().isoformat(),
                change_type="remove",
                item_type="stock",
                item_id=code,
                item_name=stock.get("name", ""),
                details={"date": date, "period": period.value}
            )
            self.repo.save_change_record("change_records", record.to_dict())
    
    # ========== 主线管理 ==========
    
    def save_mainline_snapshot(
        self,
        mainlines: List[Dict],
        period: Period = Period.MEDIUM,
        date: str = None,
        rotation_signal: str = None,
        market_context: Dict = None,
        source: str = "akshare"
    ) -> bool:
        """保存主线快照"""
        date = date or datetime.now().strftime("%Y-%m-%d")
        
        meta = SnapshotMeta(
            snapshot_id=f"mainline_{date}_{period.value}",
            snapshot_date=date,
            period=period.value,
            created_at=datetime.now().isoformat(),
            source=source
        )
        
        snapshot = MainlineSnapshot(
            meta=meta,
            mainlines=mainlines,
            rotation_signal=rotation_signal,
            market_context=market_context or {}
        )
        
        return self.repo.save_snapshot("mainline_snapshots", snapshot.to_dict())
    
    def get_mainline_snapshot(
        self,
        date: str = None,
        period: Period = Period.MEDIUM
    ) -> Optional[MainlineSnapshot]:
        """获取主线快照"""
        date = date or datetime.now().strftime("%Y-%m-%d")
        
        data = self.repo.get_snapshot("mainline_snapshots", date, period.value)
        if data:
            return MainlineSnapshot.from_dict(data)
        return None
    
    def get_latest_mainline(
        self,
        period: Period = None
    ) -> Optional[MainlineSnapshot]:
        """获取最新主线"""
        period_value = period.value if period else None
        data = self.repo.get_latest_snapshot("mainline_snapshots", period_value)
        if data:
            return MainlineSnapshot.from_dict(data)
        return None
    
    def get_mainline_history(
        self,
        start_date: str,
        end_date: str,
        period: Period = None
    ) -> List[MainlineSnapshot]:
        """获取主线历史"""
        period_value = period.value if period else None
        data_list = self.repo.get_snapshots_range(
            "mainline_snapshots", start_date, end_date, period_value
        )
        return [MainlineSnapshot.from_dict(d) for d in data_list]
    
    # ========== 变更历史 ==========
    
    def get_stock_history(self, stock_code: str, limit: int = 50) -> List[Dict]:
        """获取单只股票的进出候选池历史"""
        return self.repo.get_change_history("change_records", stock_code, limit)
    
    def get_recent_changes(self, limit: int = 100) -> List[Dict]:
        """获取最近的变更记录"""
        return self.repo.get_change_history("change_records", None, limit)
    
    # ========== 板块轮动分析 ==========
    
    def analyze_rotation(
        self,
        days: int = 30,
        period: Period = Period.MEDIUM
    ) -> Dict:
        """
        分析板块轮动
        
        Returns:
            轮动分析结果，包括：
            - 热门板块变化
            - 轮动信号
            - 周期特征
        """
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # 获取历史主线
        history = self.get_mainline_history(start_date, end_date, period)
        
        if len(history) < 2:
            return {"error": "历史数据不足", "days": days}
        
        # 分析板块热度变化
        mainline_scores = {}  # {mainline_name: [scores]}
        
        for snapshot in history:
            for ml in snapshot.mainlines:
                name = ml.get("name", "")
                score = ml.get("score", ml.get("total_score", 0))
                if name not in mainline_scores:
                    mainline_scores[name] = []
                mainline_scores[name].append({
                    "date": snapshot.meta.snapshot_date,
                    "score": score
                })
        
        # 计算趋势
        rotation_signals = []
        for name, scores in mainline_scores.items():
            if len(scores) >= 2:
                latest = scores[-1]["score"]
                earliest = scores[0]["score"]
                change = latest - earliest
                
                if change > 10:
                    signal = "升温"
                elif change < -10:
                    signal = "降温"
                else:
                    signal = "稳定"
                
                rotation_signals.append({
                    "mainline": name,
                    "latest_score": latest,
                    "change": change,
                    "signal": signal,
                    "data_points": len(scores)
                })
        
        # 按变化幅度排序
        rotation_signals.sort(key=lambda x: x["change"], reverse=True)
        
        return {
            "period": period.value,
            "days_analyzed": days,
            "snapshots_count": len(history),
            "rising_mainlines": [r for r in rotation_signals if r["signal"] == "升温"][:5],
            "falling_mainlines": [r for r in rotation_signals if r["signal"] == "降温"][:5],
            "all_signals": rotation_signals,
            "analyzed_at": datetime.now().isoformat()
        }


def create_time_dimension_manager() -> TimeDimensionManager:
    """创建时间维度管理器"""
    return TimeDimensionManager()

