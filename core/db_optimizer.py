# -*- coding: utf-8 -*-
"""
MongoDB数据库优化工具
====================

功能:
1. 集合索引优化
2. 数据清理
3. 统计分析
4. 备份恢复
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)

try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
    from pymongo.errors import OperationFailure
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False


class MongoDBOptimizer:
    """MongoDB优化器"""
    
    # 推荐的索引配置
    RECOMMENDED_INDEXES = {
        'mainline_scores': [
            [('date', DESCENDING), ('period', ASCENDING)],
            [('mainline_name', ASCENDING)],
            [('total_score', DESCENDING)],
        ],
        'candidate_pool': [
            [('date', DESCENDING), ('period', ASCENDING)],
            [('stock_code', ASCENDING)],
            [('mainline', ASCENDING)],
            [('priority', DESCENDING)],
        ],
        'factor_data': [
            [('stock_code', ASCENDING), ('date', DESCENDING)],
            [('factor_name', ASCENDING)],
            [('factor_value', DESCENDING)],
        ],
        'trade_logs': [
            [('timestamp', DESCENDING)],
            [('account_id', ASCENDING), ('log_type', ASCENDING)],
            [('stock_code', ASCENDING), ('timestamp', DESCENDING)],
        ],
        'cache_data': [
            [('cache_key', ASCENDING)],
            [('created_at', DESCENDING)],
            [('expires_at', ASCENDING)],
        ],
        'market_trend': [
            [('date', DESCENDING)],
            [('trend_type', ASCENDING)],
        ],
        'mainline_snapshots': [
            [('date', DESCENDING), ('period', ASCENDING)],
        ],
        'candidate_pool_snapshots': [
            [('date', DESCENDING), ('period', ASCENDING)],
        ],
    }
    
    def __init__(self, uri: str = "mongodb://localhost:27017", db_name: str = "jqquant"):
        """
        初始化
        
        Args:
            uri: MongoDB连接URI
            db_name: 数据库名称
        """
        self.uri = uri
        self.db_name = db_name
        self.client = None
        self.db = None
        
        if MONGO_AVAILABLE:
            try:
                self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
                self.client.server_info()
                self.db = self.client[db_name]
                logger.info(f"✅ MongoDB连接成功: {db_name}")
            except Exception as e:
                logger.error(f"MongoDB连接失败: {e}")
    
    def get_collections_info(self) -> List[Dict]:
        """获取所有集合信息"""
        if self.db is None:
            return []
        
        result = []
        
        for name in self.db.list_collection_names():
            coll = self.db[name]
            stats = self.db.command('collStats', name)
            
            result.append({
                'name': name,
                'count': coll.count_documents({}),
                'size_mb': stats.get('size', 0) / (1024 * 1024),
                'storage_mb': stats.get('storageSize', 0) / (1024 * 1024),
                'index_count': len(list(coll.list_indexes())),
                'avg_doc_size': stats.get('avgObjSize', 0)
            })
        
        return sorted(result, key=lambda x: x['size_mb'], reverse=True)
    
    def get_index_info(self, collection_name: str) -> List[Dict]:
        """获取集合索引信息"""
        if self.db is None:
            return []
        
        coll = self.db[collection_name]
        indexes = []
        
        for idx in coll.list_indexes():
            indexes.append({
                'name': idx.get('name'),
                'keys': list(idx.get('key', {}).items()),
                'unique': idx.get('unique', False),
                'sparse': idx.get('sparse', False)
            })
        
        return indexes
    
    def create_recommended_indexes(self) -> Dict[str, List[str]]:
        """创建推荐的索引"""
        if self.db is None:
            return {}
        
        result = {}
        
        for coll_name, indexes in self.RECOMMENDED_INDEXES.items():
            if coll_name not in self.db.list_collection_names():
                continue
            
            coll = self.db[coll_name]
            created = []
            
            for index_keys in indexes:
                try:
                    # 生成索引名
                    idx_name = '_'.join([f"{k}_{d}" for k, d in index_keys])
                    
                    # 检查索引是否存在
                    existing = [i['name'] for i in coll.list_indexes()]
                    if idx_name in existing:
                        continue
                    
                    # 创建索引
                    coll.create_index(index_keys, name=idx_name, background=True)
                    created.append(idx_name)
                    logger.info(f"创建索引: {coll_name}.{idx_name}")
                    
                except Exception as e:
                    logger.warning(f"创建索引失败 {coll_name}: {e}")
            
            if created:
                result[coll_name] = created
        
        return result
    
    def analyze_slow_queries(self) -> List[Dict]:
        """分析慢查询（需要开启profiling）"""
        if self.db is None:
            return []
        
        try:
            # 检查system.profile集合
            if 'system.profile' not in self.db.list_collection_names():
                return [{'message': 'Profiling未开启，运行 db.setProfilingLevel(1) 开启'}]
            
            profile = self.db['system.profile']
            slow_queries = list(profile.find({
                'millis': {'$gt': 100}  # 超过100ms
            }).sort('millis', DESCENDING).limit(10))
            
            result = []
            for q in slow_queries:
                result.append({
                    'ns': q.get('ns'),
                    'op': q.get('op'),
                    'millis': q.get('millis'),
                    'query': str(q.get('command', {}))[:200]
                })
            
            return result
            
        except Exception as e:
            logger.error(f"分析慢查询失败: {e}")
            return []
    
    def cleanup_old_data(self, collection_name: str, 
                        days: int = 30, 
                        date_field: str = 'date',
                        dry_run: bool = True) -> int:
        """
        清理旧数据
        
        Args:
            collection_name: 集合名称
            days: 保留天数
            date_field: 日期字段名
            dry_run: 是否模拟运行
        
        Returns:
            删除的文档数量
        """
        if self.db is None:
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        coll = self.db[collection_name]
        
        # 查询旧数据数量
        query = {date_field: {'$lt': cutoff_date.isoformat()}}
        count = coll.count_documents(query)
        
        if dry_run:
            logger.info(f"[模拟] 将删除 {collection_name} 中 {count} 条旧数据")
            return count
        
        # 实际删除
        result = coll.delete_many(query)
        logger.info(f"已删除 {collection_name} 中 {result.deleted_count} 条旧数据")
        
        return result.deleted_count
    
    def cleanup_cache(self, max_age_hours: int = 24) -> int:
        """清理过期缓存"""
        if self.db is None:
            return 0
        
        if 'cache' not in self.db.list_collection_names():
            return 0
        
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        result = self.db['cache'].delete_many({
            'created_at': {'$lt': cutoff.isoformat()}
        })
        
        logger.info(f"清理过期缓存: {result.deleted_count} 条")
        return result.deleted_count
    
    def compact_collection(self, collection_name: str) -> bool:
        """压缩集合"""
        if self.db is None:
            return False
        
        try:
            self.db.command('compact', collection_name)
            logger.info(f"压缩集合成功: {collection_name}")
            return True
        except OperationFailure as e:
            logger.error(f"压缩集合失败: {e}")
            return False
    
    def get_database_stats(self) -> Dict:
        """获取数据库统计信息"""
        if self.db is None:
            return {}
        
        try:
            stats = self.db.command('dbStats')
            
            return {
                'database': self.db_name,
                'collections': stats.get('collections', 0),
                'objects': stats.get('objects', 0),
                'data_size_mb': stats.get('dataSize', 0) / (1024 * 1024),
                'storage_size_mb': stats.get('storageSize', 0) / (1024 * 1024),
                'index_size_mb': stats.get('indexSize', 0) / (1024 * 1024),
                'total_size_mb': stats.get('totalSize', 0) / (1024 * 1024)
            }
            
        except Exception as e:
            logger.error(f"获取数据库统计失败: {e}")
            return {}
    
    def backup_collection(self, collection_name: str, filepath: str) -> bool:
        """备份集合到JSON文件"""
        if self.db is None:
            return False
        
        try:
            coll = self.db[collection_name]
            docs = list(coll.find({}))
            
            # 移除ObjectId
            for doc in docs:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(docs, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"备份成功: {collection_name} -> {filepath}, 共{len(docs)}条")
            return True
            
        except Exception as e:
            logger.error(f"备份失败: {e}")
            return False
    
    def generate_optimization_report(self) -> str:
        """生成优化报告"""
        report = []
        report.append("=" * 60)
        report.append("        MongoDB数据库优化报告")
        report.append("=" * 60)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 数据库统计
        stats = self.get_database_stats()
        report.append("【数据库概况】")
        report.append(f"  数据库名称: {stats.get('database', 'N/A')}")
        report.append(f"  集合数量: {stats.get('collections', 0)}")
        report.append(f"  文档总数: {stats.get('objects', 0)}")
        report.append(f"  数据大小: {stats.get('data_size_mb', 0):.2f} MB")
        report.append(f"  索引大小: {stats.get('index_size_mb', 0):.2f} MB")
        report.append("")
        
        # 集合详情
        collections = self.get_collections_info()
        report.append("【集合详情】")
        for coll in collections:
            report.append(f"  {coll['name']}: {coll['count']}条, {coll['size_mb']:.2f}MB, {coll['index_count']}个索引")
        report.append("")
        
        # 索引建议
        report.append("【索引建议】")
        for coll_name, indexes in self.RECOMMENDED_INDEXES.items():
            if coll_name in [c['name'] for c in collections]:
                existing = self.get_index_info(coll_name)
                existing_names = [i['name'] for i in existing]
                
                for idx_keys in indexes:
                    idx_name = '_'.join([f"{k}_{d}" for k, d in idx_keys])
                    if idx_name not in existing_names:
                        report.append(f"  建议为 {coll_name} 创建索引: {idx_keys}")
        report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)


def optimize_database() -> str:
    """执行数据库优化并返回报告"""
    optimizer = MongoDBOptimizer()
    
    # 创建索引
    optimizer.create_recommended_indexes()
    
    # 清理过期缓存
    optimizer.cleanup_cache(max_age_hours=48)
    
    # 生成报告
    return optimizer.generate_optimization_report()


def get_db_optimizer() -> MongoDBOptimizer:
    """获取数据库优化器实例"""
    return MongoDBOptimizer()

