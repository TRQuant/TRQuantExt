# -*- coding: utf-8 -*-
"""
因子数据存储模块
================

根据Alpha因子模块集成方案设计，提供MongoDB存储：
- FactorData: 因子值存储
- FactorInfo: 因子元信息
- FactorPerformance: 因子绩效监控
- FactorWeights: 组合权重记录

表结构设计：
1. factor_data: {date, stock_id, factor_name, value}
2. factor_info: {factor_name, category, description, definition, evidence, status, ...}
3. factor_performance: {factor_name, date, ic, ir, group_returns, ...}
4. factor_weights: {date, factor_weights, method}
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)

# 尝试导入pymongo
try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
    from pymongo.errors import ConnectionFailure
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    logger.warning("pymongo未安装，MongoDB存储功能不可用")


class FactorStorage:
    """
    因子数据存储
    
    使用MongoDB存储因子数据、元信息和绩效记录
    """
    
    def __init__(
        self,
        mongo_uri: str = "mongodb://localhost:27017/",
        db_name: str = "trquant_factors",
        use_file_fallback: bool = True
    ):
        """
        初始化存储
        
        Args:
            mongo_uri: MongoDB连接URI
            db_name: 数据库名称
            use_file_fallback: 当MongoDB不可用时使用文件存储
        """
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.use_file_fallback = use_file_fallback
        
        self.client = None
        self.db = None
        self._connected = False
        
        # 文件存储路径
        self.file_storage_dir = Path.home() / '.local/share/trquant/factors'
        self.file_storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 尝试连接MongoDB
        self._connect()
    
    def _connect(self):
        """连接MongoDB"""
        if not PYMONGO_AVAILABLE:
            logger.warning("pymongo不可用，使用文件存储")
            return
        
        try:
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=3000)
            # 测试连接
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            self._connected = True
            
            # 创建索引
            self._create_indexes()
            
            logger.info(f"MongoDB连接成功: {self.db_name}")
            
        except Exception as e:
            logger.warning(f"MongoDB连接失败: {e}，使用文件存储")
            self._connected = False
    
    def _create_indexes(self):
        """创建索引"""
        if not self._connected:
            return
        
        try:
            # factor_data索引
            self.db.factor_data.create_index([
                ("date", DESCENDING),
                ("factor_name", ASCENDING),
                ("stock_id", ASCENDING)
            ])
            
            # factor_info索引
            self.db.factor_info.create_index([("factor_name", ASCENDING)], unique=True)
            
            # factor_performance索引
            self.db.factor_performance.create_index([
                ("factor_name", ASCENDING),
                ("date", DESCENDING)
            ])
            
            # factor_weights索引
            self.db.factor_weights.create_index([("date", DESCENDING)])
            
        except Exception as e:
            logger.warning(f"创建索引失败: {e}")
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected
    
    # ====================== 因子值存储 ======================
    
    def save_factor_values(
        self,
        factor_name: str,
        date: Union[str, datetime],
        values: pd.Series,
        overwrite: bool = True
    ) -> bool:
        """
        保存因子值
        
        Args:
            factor_name: 因子名称
            date: 日期
            values: 因子值（index为股票代码）
            overwrite: 是否覆盖已有数据
        
        Returns:
            bool: 是否成功
        """
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d')
        
        date_str = date.strftime('%Y-%m-%d')
        
        if self._connected:
            return self._save_factor_values_mongo(factor_name, date, values, overwrite)
        elif self.use_file_fallback:
            return self._save_factor_values_file(factor_name, date_str, values)
        
        return False
    
    def _save_factor_values_mongo(
        self,
        factor_name: str,
        date: datetime,
        values: pd.Series,
        overwrite: bool
    ) -> bool:
        """MongoDB存储因子值"""
        try:
            collection = self.db.factor_data
            
            # 删除旧数据
            if overwrite:
                collection.delete_many({
                    "factor_name": factor_name,
                    "date": date
                })
            
            # 插入新数据
            documents = []
            for stock_id, value in values.items():
                if pd.notna(value):
                    documents.append({
                        "factor_name": factor_name,
                        "date": date,
                        "stock_id": stock_id,
                        "value": float(value),
                        "updated_at": datetime.now()
                    })
            
            if documents:
                collection.insert_many(documents)
            
            logger.debug(f"保存因子值: {factor_name} @ {date}, {len(documents)}条")
            return True
            
        except Exception as e:
            logger.error(f"保存因子值失败: {e}")
            return False
    
    def _save_factor_values_file(
        self,
        factor_name: str,
        date_str: str,
        values: pd.Series
    ) -> bool:
        """文件存储因子值"""
        try:
            factor_dir = self.file_storage_dir / "data" / factor_name
            factor_dir.mkdir(parents=True, exist_ok=True)
            
            filepath = factor_dir / f"{date_str}.json"
            
            data = {
                "factor_name": factor_name,
                "date": date_str,
                "values": {k: float(v) for k, v in values.items() if pd.notna(v)},
                "updated_at": datetime.now().isoformat()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            logger.error(f"文件存储因子值失败: {e}")
            return False
    
    def load_factor_values(
        self,
        factor_name: str,
        date: Union[str, datetime],
        stocks: Optional[List[str]] = None
    ) -> Optional[pd.Series]:
        """
        加载因子值
        
        Args:
            factor_name: 因子名称
            date: 日期
            stocks: 股票列表（可选，用于过滤）
        
        Returns:
            pd.Series: 因子值
        """
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d')
        
        if self._connected:
            return self._load_factor_values_mongo(factor_name, date, stocks)
        elif self.use_file_fallback:
            return self._load_factor_values_file(factor_name, date.strftime('%Y-%m-%d'), stocks)
        
        return None
    
    def _load_factor_values_mongo(
        self,
        factor_name: str,
        date: datetime,
        stocks: Optional[List[str]]
    ) -> Optional[pd.Series]:
        """从MongoDB加载因子值"""
        try:
            query = {"factor_name": factor_name, "date": date}
            if stocks:
                query["stock_id"] = {"$in": stocks}
            
            cursor = self.db.factor_data.find(query)
            
            data = {}
            for doc in cursor:
                data[doc["stock_id"]] = doc["value"]
            
            if data:
                return pd.Series(data)
            return None
            
        except Exception as e:
            logger.error(f"加载因子值失败: {e}")
            return None
    
    def _load_factor_values_file(
        self,
        factor_name: str,
        date_str: str,
        stocks: Optional[List[str]]
    ) -> Optional[pd.Series]:
        """从文件加载因子值"""
        try:
            filepath = self.file_storage_dir / "data" / factor_name / f"{date_str}.json"
            
            if not filepath.exists():
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            values = pd.Series(data.get("values", {}))
            
            if stocks:
                values = values.loc[values.index.isin(stocks)]
            
            return values
            
        except Exception as e:
            logger.error(f"文件加载因子值失败: {e}")
            return None
    
    # ====================== 因子元信息 ======================
    
    def save_factor_info(
        self,
        factor_name: str,
        category: str,
        description: str,
        definition: str = "",
        evidence: str = "",
        frequency: str = "daily",
        direction: int = 1,
        status: str = "active",
        **extra_info
    ) -> bool:
        """
        保存因子元信息
        
        Args:
            factor_name: 因子名称
            category: 类别（value, growth, quality, momentum, flow）
            description: 描述
            definition: 计算公式说明
            evidence: 实证研究来源
            frequency: 更新频率
            direction: 因子方向（1=正向，-1=负向）
            status: 状态（active, warning, inactive）
        """
        doc = {
            "factor_name": factor_name,
            "category": category,
            "description": description,
            "definition": definition,
            "evidence": evidence,
            "frequency": frequency,
            "direction": direction,
            "status": status,
            "updated_at": datetime.now(),
            **extra_info
        }
        
        if self._connected:
            try:
                self.db.factor_info.update_one(
                    {"factor_name": factor_name},
                    {"$set": doc},
                    upsert=True
                )
                return True
            except Exception as e:
                logger.error(f"保存因子信息失败: {e}")
        
        # 文件存储
        try:
            filepath = self.file_storage_dir / "info" / f"{factor_name}.json"
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            doc['updated_at'] = doc['updated_at'].isoformat()
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            return True
            
        except Exception as e:
            logger.error(f"保存因子信息失败: {e}")
            return False
    
    def load_factor_info(self, factor_name: str) -> Optional[Dict[str, Any]]:
        """加载因子元信息"""
        if self._connected:
            try:
                doc = self.db.factor_info.find_one({"factor_name": factor_name})
                if doc:
                    doc.pop('_id', None)
                    return doc
            except Exception as e:
                logger.error(f"加载因子信息失败: {e}")
        
        # 文件加载
        try:
            filepath = self.file_storage_dir / "info" / f"{factor_name}.json"
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        
        return None
    
    def list_factors(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有因子"""
        factors = []
        
        if self._connected:
            try:
                query = {}
                if category:
                    query["category"] = category
                
                for doc in self.db.factor_info.find(query):
                    doc.pop('_id', None)
                    factors.append(doc)
                
                return factors
                
            except Exception as e:
                logger.error(f"列出因子失败: {e}")
        
        # 文件列表
        try:
            info_dir = self.file_storage_dir / "info"
            if info_dir.exists():
                for filepath in info_dir.glob("*.json"):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        doc = json.load(f)
                        if category is None or doc.get("category") == category:
                            factors.append(doc)
        except:
            pass
        
        return factors
    
    # ====================== 因子绩效记录 ======================
    
    def save_factor_performance(
        self,
        factor_name: str,
        date: Union[str, datetime],
        ic: float,
        ic_ir: float,
        group_returns: Dict[int, float],
        long_short_return: float,
        status: str = "active",
        **extra_metrics
    ) -> bool:
        """
        保存因子绩效记录
        
        Args:
            factor_name: 因子名称
            date: 评估日期
            ic: 信息系数
            ic_ir: IC信息比
            group_returns: 分组收益
            long_short_return: 多空收益
            status: 状态
        """
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d')
        
        doc = {
            "factor_name": factor_name,
            "date": date,
            "ic": ic,
            "ic_ir": ic_ir,
            "group_returns": group_returns,
            "long_short_return": long_short_return,
            "status": status,
            "updated_at": datetime.now(),
            **extra_metrics
        }
        
        if self._connected:
            try:
                self.db.factor_performance.update_one(
                    {"factor_name": factor_name, "date": date},
                    {"$set": doc},
                    upsert=True
                )
                return True
            except Exception as e:
                logger.error(f"保存因子绩效失败: {e}")
        
        # 文件存储
        try:
            filepath = self.file_storage_dir / "performance" / factor_name / f"{date.strftime('%Y-%m')}.json"
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            doc['date'] = doc['date'].isoformat()
            doc['updated_at'] = doc['updated_at'].isoformat()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            return True
            
        except Exception as e:
            logger.error(f"保存因子绩效失败: {e}")
            return False
    
    def load_factor_performance_history(
        self,
        factor_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """加载因子绩效历史"""
        records = []
        
        if self._connected:
            try:
                query = {"factor_name": factor_name}
                if start_date:
                    query["date"] = {"$gte": start_date}
                if end_date:
                    query.setdefault("date", {})["$lte"] = end_date
                
                for doc in self.db.factor_performance.find(query).sort("date", DESCENDING):
                    doc.pop('_id', None)
                    records.append(doc)
                
            except Exception as e:
                logger.error(f"加载因子绩效历史失败: {e}")
        
        # 文件加载
        if not records:
            try:
                perf_dir = self.file_storage_dir / "performance" / factor_name
                if perf_dir.exists():
                    for filepath in sorted(perf_dir.glob("*.json"), reverse=True):
                        with open(filepath, 'r', encoding='utf-8') as f:
                            doc = json.load(f)
                            records.append(doc)
            except:
                pass
        
        if records:
            return pd.DataFrame(records)
        return pd.DataFrame()
    
    # ====================== 因子权重记录 ======================
    
    def save_factor_weights(
        self,
        date: Union[str, datetime],
        weights: Dict[str, float],
        method: str = "equal",
        metadata: Optional[Dict] = None
    ) -> bool:
        """保存因子组合权重"""
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d')
        
        doc = {
            "date": date,
            "weights": weights,
            "method": method,
            "metadata": metadata or {},
            "updated_at": datetime.now()
        }
        
        if self._connected:
            try:
                self.db.factor_weights.update_one(
                    {"date": date},
                    {"$set": doc},
                    upsert=True
                )
                return True
            except Exception as e:
                logger.error(f"保存因子权重失败: {e}")
        
        # 文件存储
        try:
            filepath = self.file_storage_dir / "weights" / f"{date.strftime('%Y-%m-%d')}.json"
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            doc['date'] = doc['date'].isoformat()
            doc['updated_at'] = doc['updated_at'].isoformat()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            return True
            
        except Exception as e:
            logger.error(f"保存因子权重失败: {e}")
            return False
    
    def load_latest_weights(self) -> Optional[Dict[str, Any]]:
        """加载最新权重"""
        if self._connected:
            try:
                doc = self.db.factor_weights.find_one(sort=[("date", DESCENDING)])
                if doc:
                    doc.pop('_id', None)
                    return doc
            except Exception as e:
                logger.error(f"加载因子权重失败: {e}")
        
        # 文件加载
        try:
            weights_dir = self.file_storage_dir / "weights"
            if weights_dir.exists():
                files = sorted(weights_dir.glob("*.json"), reverse=True)
                if files:
                    with open(files[0], 'r', encoding='utf-8') as f:
                        return json.load(f)
        except:
            pass
        
        return None
    
    def close(self):
        """关闭连接"""
        if self.client:
            self.client.close()
            self._connected = False


# 便捷函数
def create_factor_storage(
    mongo_uri: str = "mongodb://localhost:27017/",
    db_name: str = "trquant_factors"
) -> FactorStorage:
    """创建因子存储实例"""
    return FactorStorage(mongo_uri=mongo_uri, db_name=db_name)

