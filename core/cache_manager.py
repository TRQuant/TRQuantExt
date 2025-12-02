# -*- coding: utf-8 -*-
"""
缓存管理器
=========

统一管理各模块的计算结果缓存，避免重复计算：
- 投资主线综合评分
- 候选池扫描结果
- 因子筛选结果

存储位置：MongoDB (jqquant数据库)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class CacheManager:
    """缓存管理器"""
    
    # 缓存集合名称
    COLLECTIONS = {
        'mainline': 'mainline_mapped',       # 投资主线综合评分
        'candidate_pool': 'candidate_pool_cache',  # 候选池扫描结果
        'factor_filter': 'factor_filter_cache',    # 因子筛选结果
    }
    
    # 缓存有效期（小时）
    CACHE_EXPIRY = {
        'mainline': 24,        # 主线评分24小时有效
        'candidate_pool': 12,  # 候选池12小时有效
        'factor_filter': 6,    # 因子筛选6小时有效
    }
    
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017", db_name: str = "jqquant"):
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.db = None
        self._connect()
    
    def _connect(self):
        """连接MongoDB"""
        try:
            from pymongo import MongoClient
            client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=2000)
            client.server_info()
            self.db = client[self.db_name]
            logger.debug("CacheManager: MongoDB连接成功")
        except Exception as e:
            logger.warning(f"CacheManager: MongoDB连接失败: {e}")
            self.db = None
    
    def is_cache_valid(self, cache_type: str, params: Dict = None) -> bool:
        """
        检查缓存是否有效
        
        Args:
            cache_type: 缓存类型 (mainline/candidate_pool/factor_filter)
            params: 参数字典，用于匹配特定缓存
        
        Returns:
            bool: 缓存是否有效
        """
        if self.db is None:
            return False
        
        try:
            collection_name = self.COLLECTIONS.get(cache_type)
            if not collection_name:
                return False
            
            collection = self.db[collection_name]
            
            # 构建查询条件
            query = {}
            if params:
                if 'period' in params:
                    query['period'] = params['period']
                if 'date' in params:
                    query['date'] = params['date']
            
            # 查找最新记录
            latest = collection.find_one(query, sort=[("timestamp", -1)])
            
            if not latest:
                return False
            
            # 检查是否过期
            timestamp_str = latest.get("timestamp", "")
            if timestamp_str:
                try:
                    cache_time = datetime.fromisoformat(timestamp_str)
                    expiry_hours = self.CACHE_EXPIRY.get(cache_type, 12)
                    if datetime.now() - cache_time < timedelta(hours=expiry_hours):
                        return True
                except:
                    pass
            
            return False
            
        except Exception as e:
            logger.debug(f"检查缓存有效性失败: {e}")
            return False
    
    def load_cache(self, cache_type: str, params: Dict = None) -> Optional[Dict]:
        """
        加载缓存数据
        
        Args:
            cache_type: 缓存类型
            params: 参数字典
        
        Returns:
            缓存数据或None
        """
        if self.db is None:
            return None
        
        try:
            collection_name = self.COLLECTIONS.get(cache_type)
            if not collection_name:
                return None
            
            collection = self.db[collection_name]
            
            # 构建查询条件
            query = {}
            if params:
                if 'period' in params:
                    query['period'] = params['period']
            
            # 查找最新记录
            latest = collection.find_one(query, sort=[("timestamp", -1)])
            
            if latest:
                # 移除MongoDB的_id字段
                latest.pop('_id', None)
                logger.info(f"✅ 加载缓存成功: {cache_type}, 时间={latest.get('timestamp', '')[:19]}")
                return latest
            
            return None
            
        except Exception as e:
            logger.warning(f"加载缓存失败: {e}")
            return None
    
    def save_cache(self, cache_type: str, data: Dict, params: Dict = None):
        """
        保存缓存数据
        
        Args:
            cache_type: 缓存类型
            data: 要缓存的数据
            params: 参数字典
        """
        if self.db is None:
            return
        
        try:
            collection_name = self.COLLECTIONS.get(cache_type)
            if not collection_name:
                return
            
            collection = self.db[collection_name]
            
            # 添加时间戳
            doc = {
                **data,
                "timestamp": datetime.now().isoformat(),
                "date": datetime.now().strftime('%Y-%m-%d'),
            }
            
            if params:
                doc.update(params)
            
            # 使用日期+周期作为唯一键
            filter_key = {"date": doc["date"]}
            if 'period' in doc:
                filter_key['period'] = doc['period']
            
            collection.replace_one(filter_key, doc, upsert=True)
            
            logger.info(f"✅ 保存缓存成功: {cache_type}")
            
        except Exception as e:
            logger.warning(f"保存缓存失败: {e}")
    
    def get_cache_info(self, cache_type: str) -> Optional[Dict]:
        """
        获取缓存信息（不加载完整数据）
        
        Returns:
            {'timestamp': '...', 'date': '...', 'period': '...', 'count': N}
        """
        if self.db is None:
            return None
        
        try:
            collection_name = self.COLLECTIONS.get(cache_type)
            if not collection_name:
                return None
            
            collection = self.db[collection_name]
            latest = collection.find_one(sort=[("timestamp", -1)])
            
            if latest:
                return {
                    'timestamp': latest.get('timestamp', ''),
                    'date': latest.get('date', ''),
                    'period': latest.get('period', ''),
                    'count': len(latest.get('mainlines', [])) or len(latest.get('stocks', [])) or 0
                }
            
            return None
            
        except Exception as e:
            return None


# 全局单例
_cache_manager = None

def get_cache_manager() -> CacheManager:
    """获取缓存管理器单例"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager

