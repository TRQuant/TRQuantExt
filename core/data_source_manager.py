# -*- coding: utf-8 -*-
"""
数据源统一管理器
==================

根据账户类型智能切换数据源，提供统一的数据访问接口。

账户类型:
1. TRIAL (试用版): JQData试用账户，数据范围受限
2. STANDARD (标准版): JQData正式账户，完整历史数据
3. PREMIUM (高级版): JQData正式账户 + 实时数据

数据源优先级:
1. JQData (主数据源)
2. AKShare (备用数据源)
3. Baostock (历史数据补充)
4. 本地缓存

遵循时间维度设计原则
"""

import logging
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Callable
import pandas as pd

logger = logging.getLogger(__name__)


class AccountType(Enum):
    """账户类型"""
    TRIAL = "trial"           # 试用版：历史数据受限（通常12-15个月前的1年数据）
    STANDARD = "standard"     # 标准版：完整历史数据，无实时
    PREMIUM = "premium"       # 高级版：完整历史 + 实时数据
    UNKNOWN = "unknown"       # 未知


class DataSourceType(Enum):
    """数据源类型"""
    JQDATA = "jqdata"
    AKSHARE = "akshare"
    BAOSTOCK = "baostock"
    TUSHARE = "tushare"
    LOCAL_CACHE = "local_cache"


@dataclass
class DataSourceStatus:
    """数据源状态"""
    source_type: DataSourceType
    is_available: bool = False
    account_type: AccountType = AccountType.UNKNOWN
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_realtime: bool = False
    daily_quota: int = 0
    used_quota: int = 0
    last_check: Optional[datetime] = None
    error_message: str = ""
    
    @property
    def remaining_quota(self) -> int:
        return max(0, self.daily_quota - self.used_quota)
    
    @property
    def quota_percent(self) -> float:
        if self.daily_quota <= 0:
            return 0
        return self.used_quota / self.daily_quota * 100


@dataclass
class DataFetchResult:
    """数据获取结果"""
    success: bool
    data: Optional[pd.DataFrame] = None
    source: DataSourceType = DataSourceType.JQDATA
    from_cache: bool = False
    error: str = ""
    fetch_time: datetime = field(default_factory=datetime.now)


class DataSourceManager:
    """
    数据源统一管理器
    
    功能:
    1. 自动检测账户类型和权限
    2. 智能选择最优数据源
    3. 自动降级到备用数据源
    4. 统一数据格式
    5. 缓存管理
    """
    
    def __init__(self):
        self._sources: Dict[DataSourceType, DataSourceStatus] = {}
        self._jq_client = None
        self._initialized = False
        self._priority = [
            DataSourceType.JQDATA,
            DataSourceType.AKSHARE,
            DataSourceType.BAOSTOCK,
            DataSourceType.LOCAL_CACHE
        ]
        
    def initialize(self) -> bool:
        """初始化所有数据源"""
        logger.info("🚀 正在初始化数据源管理器...")
        
        # 初始化JQData
        self._init_jqdata()
        
        # 初始化AKShare
        self._init_akshare()
        
        # 初始化Baostock
        self._init_baostock()
        
        # 初始化本地缓存
        self._init_local_cache()
        
        self._initialized = True
        self._log_status()
        return True
    
    def _init_jqdata(self):
        """初始化JQData数据源"""
        status = DataSourceStatus(
            source_type=DataSourceType.JQDATA,
            daily_quota=1000000  # 试用版每日100万条
        )
        
        try:
            from jqdata.client import JQDataClient
            from config.config_manager import get_config_manager
            
            config = get_config_manager()
            jq_config = config.get_config('jqdata')
            
            if jq_config and jq_config.get('username') and jq_config.get('password'):
                self._jq_client = JQDataClient()
                if self._jq_client.authenticate(jq_config['username'], jq_config['password']):
                    perm = self._jq_client.get_permission()
                    
                    status.is_available = True
                    status.start_date = perm.start_date
                    status.end_date = perm.end_date
                    status.is_realtime = perm.is_realtime
                    status.last_check = datetime.now()
                    
                    # 判断账户类型
                    if perm.is_realtime:
                        status.account_type = AccountType.PREMIUM
                        status.daily_quota = 200000000  # 高级版2亿条
                    elif perm.detected:
                        # 通过数据范围判断是否是正式账户
                        if perm.start_date and perm.end_date:
                            start = datetime.strptime(perm.start_date, '%Y-%m-%d')
                            end = datetime.strptime(perm.end_date, '%Y-%m-%d')
                            days_range = (end - start).days
                            
                            if days_range > 400:  # 超过400天，可能是正式账户
                                status.account_type = AccountType.STANDARD
                                status.daily_quota = 200000000
                            else:
                                status.account_type = AccountType.TRIAL
                                status.daily_quota = 1000000
                        else:
                            status.account_type = AccountType.TRIAL
                    
                    logger.info(f"✅ JQData已连接: {status.account_type.value} ({status.start_date} ~ {status.end_date})")
                else:
                    status.error_message = "认证失败"
                    logger.warning("⚠️ JQData认证失败")
            else:
                status.error_message = "未配置账号"
                logger.warning("⚠️ JQData未配置")
                
        except ImportError:
            status.error_message = "jqdatasdk未安装"
            logger.warning("⚠️ jqdatasdk未安装")
        except Exception as e:
            status.error_message = str(e)
            logger.error(f"❌ JQData初始化失败: {e}")
        
        self._sources[DataSourceType.JQDATA] = status
    
    def _init_akshare(self):
        """初始化AKShare数据源"""
        status = DataSourceStatus(
            source_type=DataSourceType.AKSHARE,
            account_type=AccountType.STANDARD,  # AKShare免费无限制
            daily_quota=999999999
        )
        
        try:
            import akshare as ak
            # 测试是否可用
            status.is_available = True
            status.start_date = "2010-01-01"
            status.end_date = date.today().strftime('%Y-%m-%d')
            status.is_realtime = True
            status.last_check = datetime.now()
            logger.info("✅ AKShare可用")
        except ImportError:
            status.error_message = "akshare未安装"
            logger.warning("⚠️ akshare未安装")
        except Exception as e:
            status.error_message = str(e)
            logger.warning(f"⚠️ AKShare初始化失败: {e}")
        
        self._sources[DataSourceType.AKSHARE] = status
    
    def _init_baostock(self):
        """初始化Baostock数据源"""
        status = DataSourceStatus(
            source_type=DataSourceType.BAOSTOCK,
            account_type=AccountType.STANDARD,
            daily_quota=999999999
        )
        
        try:
            import baostock as bs
            # 登录测试
            lg = bs.login()
            if lg.error_code == '0':
                status.is_available = True
                status.start_date = "1990-01-01"  # Baostock有很长的历史数据
                status.end_date = date.today().strftime('%Y-%m-%d')
                status.is_realtime = False  # Baostock不支持实时
                status.last_check = datetime.now()
                bs.logout()
                logger.info("✅ Baostock可用")
            else:
                status.error_message = f"登录失败: {lg.error_msg}"
                logger.warning(f"⚠️ Baostock登录失败: {lg.error_msg}")
        except ImportError:
            status.error_message = "baostock未安装"
            logger.info("ℹ️ baostock未安装（可选）")
        except Exception as e:
            status.error_message = str(e)
            logger.warning(f"⚠️ Baostock初始化失败: {e}")
        
        self._sources[DataSourceType.BAOSTOCK] = status
    
    def _init_local_cache(self):
        """初始化本地缓存"""
        status = DataSourceStatus(
            source_type=DataSourceType.LOCAL_CACHE,
            is_available=True,
            account_type=AccountType.STANDARD,
            daily_quota=999999999,
            last_check=datetime.now()
        )
        
        try:
            from pymongo import MongoClient
            client = MongoClient('mongodb://localhost:27017', serverSelectionTimeoutMS=2000)
            client.admin.command('ping')
            status.is_available = True
            logger.info("✅ 本地缓存(MongoDB)可用")
        except Exception as e:
            status.error_message = str(e)
            status.is_available = False
            logger.warning(f"⚠️ MongoDB不可用: {e}")
        
        self._sources[DataSourceType.LOCAL_CACHE] = status
    
    def _log_status(self):
        """记录数据源状态"""
        logger.info("=" * 50)
        logger.info("📊 数据源状态汇总:")
        for source_type, status in self._sources.items():
            icon = "✅" if status.is_available else "❌"
            logger.info(f"   {icon} {source_type.value}: {status.account_type.value if status.is_available else status.error_message}")
        logger.info("=" * 50)
    
    def get_source_status(self, source: DataSourceType) -> Optional[DataSourceStatus]:
        """获取指定数据源状态"""
        return self._sources.get(source)
    
    def get_all_status(self) -> Dict[DataSourceType, DataSourceStatus]:
        """获取所有数据源状态"""
        return self._sources.copy()
    
    def get_jqdata_account_type(self) -> AccountType:
        """获取JQData账户类型"""
        status = self._sources.get(DataSourceType.JQDATA)
        if status:
            return status.account_type
        return AccountType.UNKNOWN
    
    def get_available_date_range(self, source: DataSourceType = None) -> tuple:
        """
        获取可用的日期范围
        
        Args:
            source: 指定数据源，为None时返回所有可用源的最大范围
        """
        if source:
            status = self._sources.get(source)
            if status and status.is_available:
                return status.start_date, status.end_date
            return None, None
        
        # 合并所有可用源的日期范围
        all_starts = []
        all_ends = []
        
        for status in self._sources.values():
            if status.is_available and status.start_date and status.end_date:
                all_starts.append(status.start_date)
                all_ends.append(status.end_date)
        
        if all_starts and all_ends:
            return min(all_starts), max(all_ends)
        return None, None
    
    def get_price(
        self,
        code: str,
        start_date: str,
        end_date: str,
        frequency: str = 'daily',
        fields: List[str] = None,
        prefer_source: DataSourceType = None
    ) -> DataFetchResult:
        """
        统一获取价格数据接口
        
        按优先级尝试不同数据源，自动降级
        """
        if fields is None:
            fields = ['open', 'close', 'high', 'low', 'volume']
        
        # 确定数据源优先级
        sources_to_try = [prefer_source] if prefer_source else self._priority
        
        for source in sources_to_try:
            if source is None:
                continue
                
            status = self._sources.get(source)
            if not status or not status.is_available:
                continue
            
            try:
                result = self._fetch_from_source(source, code, start_date, end_date, frequency, fields)
                if result.success and result.data is not None and not result.data.empty:
                    return result
            except Exception as e:
                logger.warning(f"{source.value} 获取数据失败: {e}")
                continue
        
        return DataFetchResult(
            success=False,
            error="所有数据源均无法获取数据"
        )
    
    def _fetch_from_source(
        self,
        source: DataSourceType,
        code: str,
        start_date: str,
        end_date: str,
        frequency: str,
        fields: List[str]
    ) -> DataFetchResult:
        """从指定数据源获取数据"""
        
        if source == DataSourceType.JQDATA:
            return self._fetch_from_jqdata(code, start_date, end_date, frequency, fields)
        elif source == DataSourceType.AKSHARE:
            return self._fetch_from_akshare(code, start_date, end_date, frequency, fields)
        elif source == DataSourceType.BAOSTOCK:
            return self._fetch_from_baostock(code, start_date, end_date, frequency, fields)
        elif source == DataSourceType.LOCAL_CACHE:
            return self._fetch_from_cache(code, start_date, end_date, frequency, fields)
        
        return DataFetchResult(success=False, error=f"未知数据源: {source}")
    
    def _fetch_from_jqdata(
        self,
        code: str,
        start_date: str,
        end_date: str,
        frequency: str,
        fields: List[str]
    ) -> DataFetchResult:
        """从JQData获取数据"""
        if not self._jq_client:
            return DataFetchResult(success=False, error="JQData未初始化")
        
        try:
            df = self._jq_client.get_price(
                code,
                start_date=start_date,
                end_date=end_date,
                frequency=frequency,
                fields=fields
            )
            
            if df is not None and not df.empty:
                return DataFetchResult(
                    success=True,
                    data=df,
                    source=DataSourceType.JQDATA
                )
            
            return DataFetchResult(success=False, error="无数据返回")
            
        except Exception as e:
            return DataFetchResult(success=False, error=str(e))
    
    def _fetch_from_akshare(
        self,
        code: str,
        start_date: str,
        end_date: str,
        frequency: str,
        fields: List[str]
    ) -> DataFetchResult:
        """从AKShare获取数据"""
        try:
            import akshare as ak
            
            # 转换股票代码格式 (000001.XSHE -> 000001)
            pure_code = code.split('.')[0] if '.' in code else code
            
            # AKShare主要提供日线数据
            if frequency != 'daily':
                return DataFetchResult(success=False, error="AKShare仅支持日线数据")
            
            # 尝试获取个股数据
            try:
                df = ak.stock_zh_a_hist(
                    symbol=pure_code,
                    start_date=start_date.replace('-', ''),
                    end_date=end_date.replace('-', ''),
                    adjust="qfq"
                )
                
                if df is not None and not df.empty:
                    # 重命名列
                    column_map = {
                        '日期': 'date',
                        '开盘': 'open',
                        '收盘': 'close',
                        '最高': 'high',
                        '最低': 'low',
                        '成交量': 'volume'
                    }
                    df = df.rename(columns=column_map)
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.set_index('date')
                    
                    # 只保留需要的字段
                    available_fields = [f for f in fields if f in df.columns]
                    if available_fields:
                        df = df[available_fields]
                    
                    return DataFetchResult(
                        success=True,
                        data=df,
                        source=DataSourceType.AKSHARE
                    )
                    
            except Exception as e:
                logger.debug(f"AKShare个股数据获取失败: {e}")
            
            return DataFetchResult(success=False, error="无数据")
            
        except Exception as e:
            return DataFetchResult(success=False, error=str(e))
    
    def _fetch_from_baostock(
        self,
        code: str,
        start_date: str,
        end_date: str,
        frequency: str,
        fields: List[str]
    ) -> DataFetchResult:
        """从Baostock获取数据"""
        try:
            import baostock as bs
            
            # 转换股票代码格式 (000001.XSHE -> sz.000001)
            if '.XSHE' in code:
                bs_code = 'sz.' + code.split('.')[0]
            elif '.XSHG' in code:
                bs_code = 'sh.' + code.split('.')[0]
            else:
                bs_code = code
            
            # 登录
            lg = bs.login()
            if lg.error_code != '0':
                return DataFetchResult(success=False, error=f"登录失败: {lg.error_msg}")
            
            try:
                # 字段映射
                bs_fields = "date,open,high,low,close,volume"
                
                rs = bs.query_history_k_data_plus(
                    bs_code,
                    bs_fields,
                    start_date=start_date,
                    end_date=end_date,
                    frequency="d",  # 日线
                    adjustflag="2"  # 前复权
                )
                
                data_list = []
                while rs.next():
                    data_list.append(rs.get_row_data())
                
                if data_list:
                    df = pd.DataFrame(data_list, columns=rs.fields)
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.set_index('date')
                    
                    # 转换数值类型
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    return DataFetchResult(
                        success=True,
                        data=df,
                        source=DataSourceType.BAOSTOCK
                    )
                
                return DataFetchResult(success=False, error="无数据")
                
            finally:
                bs.logout()
                
        except ImportError:
            return DataFetchResult(success=False, error="baostock未安装")
        except Exception as e:
            return DataFetchResult(success=False, error=str(e))
    
    def _fetch_from_cache(
        self,
        code: str,
        start_date: str,
        end_date: str,
        frequency: str,
        fields: List[str]
    ) -> DataFetchResult:
        """从本地缓存获取数据"""
        try:
            from pymongo import MongoClient
            
            client = MongoClient('mongodb://localhost:27017')
            db = client.jqquant
            collection = db.market_data
            
            # 查询缓存
            query = {
                'code': code,
                'date': {
                    '$gte': start_date,
                    '$lte': end_date
                }
            }
            
            cursor = collection.find(query).sort('date', 1)
            data_list = list(cursor)
            
            if data_list:
                df = pd.DataFrame(data_list)
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
                
                # 只保留需要的字段
                available_fields = [f for f in fields if f in df.columns]
                if available_fields:
                    df = df[available_fields]
                
                return DataFetchResult(
                    success=True,
                    data=df,
                    source=DataSourceType.LOCAL_CACHE,
                    from_cache=True
                )
            
            return DataFetchResult(success=False, error="缓存中无数据")
            
        except Exception as e:
            return DataFetchResult(success=False, error=str(e))
    
    def save_to_cache(self, code: str, data: pd.DataFrame) -> bool:
        """保存数据到本地缓存"""
        try:
            from pymongo import MongoClient
            
            client = MongoClient('mongodb://localhost:27017')
            db = client.jqquant
            collection = db.market_data
            
            # 重置索引
            df = data.reset_index()
            
            # 转换为字典列表
            records = df.to_dict('records')
            
            # 添加代码字段
            for record in records:
                record['code'] = code
                if 'date' in record:
                    record['date'] = record['date'].strftime('%Y-%m-%d') if hasattr(record['date'], 'strftime') else str(record['date'])
            
            # 批量更新或插入
            for record in records:
                collection.update_one(
                    {'code': code, 'date': record['date']},
                    {'$set': record},
                    upsert=True
                )
            
            logger.debug(f"已缓存 {len(records)} 条数据: {code}")
            return True
            
        except Exception as e:
            logger.warning(f"保存缓存失败: {e}")
            return False
    
    def get_jq_client(self):
        """获取JQData客户端实例"""
        return self._jq_client
    
    def is_realtime_available(self) -> bool:
        """检查是否有实时数据权限"""
        jq_status = self._sources.get(DataSourceType.JQDATA)
        if jq_status and jq_status.is_available and jq_status.is_realtime:
            return True
        
        ak_status = self._sources.get(DataSourceType.AKSHARE)
        if ak_status and ak_status.is_available:
            return True
        
        return False


# 全局单例
_manager_instance: Optional[DataSourceManager] = None


def get_data_source_manager() -> DataSourceManager:
    """获取数据源管理器单例"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = DataSourceManager()
        _manager_instance.initialize()
    return _manager_instance

