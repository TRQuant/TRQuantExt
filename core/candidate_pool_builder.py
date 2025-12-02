#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
候选池构建模块

基于主线识别结果，构建个股候选池：
1. 主线 → 成分股（概念/行业）
2. 技术突破筛选（涨停、放量、均线突破等）
3. 财务因子筛选（ROE、净利润增速等）
4. 结果缓存和存储
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
import pandas as pd
import numpy as np
from pathlib import Path
import json

logger = logging.getLogger(__name__)


def _convert_numpy_types(obj: Any) -> Any:
    """递归转换numpy类型为Python原生类型（MongoDB兼容）"""
    if isinstance(obj, dict):
        return {k: _convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_numpy_types(item) for item in obj]
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj

# 尝试导入JQData
try:
    from jqdata.client import JQDataClient
    from jqdatasdk import query, valuation, indicator
    JQDATA_AVAILABLE = True
except ImportError:
    JQDATA_AVAILABLE = False
    logger.warning("⚠️ JQData未安装，候选池功能将受限")

# 尝试导入MongoDB
try:
    from pymongo import MongoClient
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    logger.warning("⚠️ PyMongo未安装，将使用文件缓存")


@dataclass
class CandidateStock:
    """候选股票信息"""
    code: str                    # 股票代码（JQData格式，如 '000001.XSHE'）
    name: str                    # 股票名称
    sector: str                  # 所属主线（概念/行业）
    sector_type: str             # 主线类型：'concept' 或 'industry'
    
    # 技术指标
    is_limit_up: bool = False    # 是否涨停
    is_volume_breakout: bool = False  # 是否放量突破
    is_ma_breakthrough: bool = False   # 是否站上均线
    consecutive_up_days: int = 0  # 连续上涨天数
    change_pct: float = 0.0      # 涨跌幅
    
    # 财务指标
    roe: Optional[float] = None  # ROE
    net_profit_growth: Optional[float] = None  # 净利润同比增长率
    revenue_growth: Optional[float] = None     # 营收同比增长率
    
    # 综合评分
    technical_score: float = 0.0  # 技术面得分
    fundamental_score: float = 0.0  # 基本面得分
    composite_score: float = 0.0    # 综合得分
    
    # 元数据
    update_time: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: List[str] = field(default_factory=list)  # 标签，如 ['新能源', '涨停', '高ROE']


@dataclass
class CandidatePool:
    """候选池"""
    pool_id: str                 # 池ID（如 'mainline_2025-11-29'）
    mainline_name: str           # 主线名称
    mainline_type: str          # 主线类型
    create_time: str            # 创建时间
    stocks: List[CandidateStock] = field(default_factory=list)  # 候选股票列表
    total_count: int = 0        # 总数量
    filtered_count: int = 0     # 筛选后数量
    data_mode: str = 'unknown'  # 数据模式：'historical' 或 'realtime'
    data_date: str = ''         # 数据日期（用于历史模式）
    
    def to_dict(self) -> Dict:
        """转换为字典（MongoDB兼容，自动转换numpy类型）"""
        data = {
            'pool_id': self.pool_id,
            'mainline_name': self.mainline_name,
            'mainline_type': self.mainline_type,
            'create_time': self.create_time,
            'total_count': self.total_count,
            'filtered_count': self.filtered_count,
            'data_mode': self.data_mode,
            'data_date': self.data_date,
            'stocks': [asdict(stock) for stock in self.stocks]
        }
        return _convert_numpy_types(data)


class CandidatePoolBuilder:
    """
    候选池构建器
    
    功能：
    1. 从主线获取成分股
    2. 技术突破筛选
    3. 财务因子筛选
    4. 结果缓存
    
    支持两种数据模式：
    - 历史模式（免费版）：使用历史数据进行策略验证
    - 实时模式（付费版）：使用实时数据进行实盘选股
    """
    
    def __init__(
        self,
        jq_client: Optional[JQDataClient] = None,
        mongo_uri: str = "mongodb://localhost:27017",
        cache_dir: Optional[Path] = None
    ):
        """
        初始化构建器
        
        Args:
            jq_client: JQData客户端（如果为None，会尝试从配置创建）
            mongo_uri: MongoDB连接URI
            cache_dir: 缓存目录
        """
        self.jq_client = jq_client
        self.mongo_uri = mongo_uri
        self.cache_dir = cache_dir or Path.home() / ".local/share/trquant/cache/candidate_pools"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化MongoDB
        self.db = None
        if MONGODB_AVAILABLE:
            try:
                client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=2000)
                client.server_info()
                self.db = client.jqquant
                logger.info("✅ MongoDB连接成功")
            except Exception as e:
                logger.warning(f"⚠️ MongoDB连接失败: {e}")
        
        # 如果没有提供JQData客户端，尝试从配置创建
        if self.jq_client is None and JQDATA_AVAILABLE:
            self._init_jq_client()
    
    def get_data_mode_info(self) -> Dict[str, Any]:
        """
        获取当前数据模式信息
        
        Returns:
            Dict: 包含数据模式、权限范围等信息
        """
        if not self.jq_client or not self.jq_client.is_authenticated():
            return {
                'authenticated': False,
                'mode': 'unknown',
                'message': '未认证'
            }
        
        perm = self.jq_client.get_permission()
        return {
            'authenticated': True,
            'mode': 'realtime' if perm.is_realtime else 'historical',
            'start_date': perm.start_date,
            'end_date': perm.end_date,
            'detected': perm.detected,
            'message': str(perm)
        }
    
    def _init_jq_client(self):
        """从配置初始化JQData客户端"""
        try:
            from config.config_manager import get_config_manager
            config_manager = get_config_manager()
            config = config_manager.get_jqdata_config()
            
            if config.get('username') and config.get('password'):
                self.jq_client = JQDataClient()
                if self.jq_client.authenticate(config['username'], config['password']):
                    logger.info("✅ JQData客户端初始化成功")
                else:
                    logger.warning("⚠️ JQData认证失败")
                    self.jq_client = None
            else:
                logger.warning("⚠️ 未找到JQData配置")
        except Exception as e:
            logger.warning(f"⚠️ 初始化JQData客户端失败: {e}")
    
    def build_from_mainline(
        self,
        mainline_name: str,
        mainline_type: str = 'concept',
        date: Optional[str] = None,
        use_cache: bool = True
    ) -> CandidatePool:
        """
        从主线构建候选池
        
        Args:
            mainline_name: 主线名称（概念或行业名称）
            mainline_type: 主线类型：'concept' 或 'industry'
            date: 日期（用于获取成分股，默认使用权限范围内的最新日期）
            use_cache: 是否使用缓存
        
        Returns:
            CandidatePool: 候选池对象
        """
        if not self.jq_client or not self.jq_client.is_authenticated():
            raise Exception("JQData客户端未认证，无法构建候选池")
        
        # 如果未指定日期，使用权限范围内的最新可用日期
        if date is None:
            date = self.jq_client.get_available_end_date()
            logger.info(f"使用权限范围内的最新日期: {date}")
        
        # 检查缓存（缓存key包含日期）
        cache_key = f"{mainline_name}_{mainline_type}_{date}"
        if use_cache:
            cached_pool = self._load_from_cache(mainline_name, mainline_type, date)
            if cached_pool:
                logger.info(f"✅ 使用缓存数据: {mainline_name} ({date})")
                return cached_pool
        
        # 创建候选池
        pool_id = f"mainline_{mainline_name}_{date.replace('-', '')}"
        pool = CandidatePool(
            pool_id=pool_id,
            mainline_name=mainline_name,
            mainline_type=mainline_type,
            create_time=datetime.now().isoformat()
        )
        
        # 添加数据模式信息
        mode_info = self.get_data_mode_info()
        pool.data_mode = mode_info.get('mode', 'unknown')
        pool.data_date = date
        
        # 1. 获取成分股
        logger.info(f"获取{mainline_type}成分股: {mainline_name} (日期: {date})")
        stocks = self._get_sector_stocks(mainline_name, mainline_type, date)
        pool.total_count = len(stocks)
        logger.info(f"获取到 {len(stocks)} 只成分股")
        
        if not stocks:
            logger.warning(f"未获取到成分股: {mainline_name}")
            return pool
        
        # 2. 技术突破筛选
        logger.info("进行技术突破筛选...")
        candidate_stocks = self._filter_technical_breakthrough(stocks, date)
        logger.info(f"技术筛选后剩余 {len(candidate_stocks)} 只股票")
        
        # 3. 财务因子筛选
        logger.info("进行财务因子筛选...")
        candidate_stocks = self._filter_fundamental(candidate_stocks, date)
        logger.info(f"财务筛选后剩余 {len(candidate_stocks)} 只股票")
        
        # 4. 计算综合得分
        candidate_stocks = self._calculate_scores(candidate_stocks)
        
        # 5. 设置板块信息
        for stock in candidate_stocks:
            stock.sector = mainline_name
            stock.sector_type = mainline_type
        
        # 6. 排序并保存
        candidate_stocks.sort(key=lambda x: x.composite_score, reverse=True)
        pool.stocks = candidate_stocks
        pool.filtered_count = len(candidate_stocks)
        
        # 保存到缓存
        if use_cache:
            self._save_to_cache(pool)
        
        return pool
    
    def _get_sector_stocks(
        self,
        sector_name: str,
        sector_type: str,
        date: Optional[str] = None
    ) -> List[str]:
        """
        获取板块成分股
        
        Args:
            sector_name: 板块名称
            sector_type: 'concept' 或 'industry'
            date: 日期
        
        Returns:
            List[str]: 股票代码列表
        """
        try:
            if sector_type == 'concept':
                # 首先尝试通过名称查找概念代码
                # 注意：JQData的概念代码通常是 'SC0001' 这样的格式
                # 这里简化处理，假设可以直接使用名称或需要先查找代码
                stocks = self.jq_client.get_concept_stocks(sector_name, date=date)
            elif sector_type == 'industry':
                stocks = self.jq_client.get_industry_stocks(sector_name, date=date)
            else:
                logger.error(f"未知的板块类型: {sector_type}")
                return []
            
            return stocks
        except Exception as e:
            logger.error(f"获取板块成分股失败: {e}")
            return []
    
    def _filter_technical_breakthrough(
        self,
        stocks: List[str],
        date: Optional[str] = None
    ) -> List[CandidateStock]:
        """
        技术突破筛选
        
        筛选条件：
        - 涨停
        - 放量突破（成交量放大）
        - 站上均线（如60日均线）
        - 连续上涨
        
        Args:
            stocks: 股票代码列表
            date: 日期（应该已经是权限范围内的日期）
        
        Returns:
            List[CandidateStock]: 筛选后的候选股票
        """
        candidates = []
        
        # 使用传入的日期（已经是权限范围内的日期）
        if date is None:
            date = self.jq_client.get_available_end_date()
        
        # 计算开始日期（向前推120天，约4个月）
        end_dt = datetime.strptime(date, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=120)
        
        # 确保开始日期在权限范围内
        perm = self.jq_client.get_permission()
        if perm.detected and perm.start_date:
            perm_start = datetime.strptime(perm.start_date, '%Y-%m-%d')
            if start_dt < perm_start:
                start_dt = perm_start
                logger.debug(f"开始日期调整到权限范围: {start_dt.strftime('%Y-%m-%d')}")
        
        start_date = start_dt.strftime('%Y-%m-%d')
        
        # 预先获取所有股票信息（减少API调用）
        all_securities = None
        try:
            all_securities = self.jq_client.get_all_securities(types=['stock'], date=date)
        except Exception as e:
            logger.warning(f"获取证券列表失败: {e}")
        
        processed = 0
        total = len(stocks)
        
        for stock_code in stocks:
            processed += 1
            if processed % 10 == 0:
                logger.info(f"技术筛选进度: {processed}/{total}")
            
            try:
                # 使用 get_price 获取指定日期范围的数据
                # auto_adjust_date=True 会自动调整到权限范围内
                price_data = self.jq_client.get_price(
                    securities=stock_code,
                    start_date=start_date,
                    end_date=date,
                    frequency='daily',
                    auto_adjust_date=True
                )
                
                if price_data.empty or len(price_data) < 20:
                    continue
                
                # 获取股票名称
                if all_securities is not None and stock_code in all_securities.index:
                    stock_name = all_securities.loc[stock_code, 'display_name']
                else:
                    stock_name = stock_code
                
                # 计算技术指标
                latest = price_data.iloc[-1]
                prev = price_data.iloc[-2] if len(price_data) > 1 else latest
                
                # 涨跌幅
                change_pct = ((latest['close'] - prev['close']) / prev['close']) * 100 if prev['close'] > 0 else 0
                
                # 是否涨停（假设涨跌幅 >= 9.5% 为涨停）
                is_limit_up = change_pct >= 9.5
                
                # 是否放量（成交量较前一日放大50%以上）
                volume_ratio = latest['volume'] / prev['volume'] if prev['volume'] > 0 else 1
                is_volume_breakout = volume_ratio >= 1.5
                
                # 是否站上均线
                data_len = len(price_data)
                if data_len >= 60:
                    ma60 = price_data['close'].tail(60).mean()
                    is_ma_breakthrough = latest['close'] > ma60
                elif data_len >= 30:
                    ma30 = price_data['close'].tail(30).mean()
                    is_ma_breakthrough = latest['close'] > ma30
                else:
                    ma_avg = price_data['close'].mean()
                    is_ma_breakthrough = latest['close'] > ma_avg
                
                # 连续上涨天数
                consecutive_up = 0
                for i in range(len(price_data) - 1, 0, -1):
                    if price_data.iloc[i]['close'] > price_data.iloc[i-1]['close']:
                        consecutive_up += 1
                    else:
                        break
                
                # 创建候选股票对象
                candidate = CandidateStock(
                    code=stock_code,
                    name=stock_name,
                    sector="",  # 将在外部设置
                    sector_type="",
                    is_limit_up=is_limit_up,
                    is_volume_breakout=is_volume_breakout,
                    is_ma_breakthrough=is_ma_breakthrough,
                    consecutive_up_days=consecutive_up,
                    change_pct=round(change_pct, 2)
                )
                
                # 技术面筛选：至少满足一个条件
                if is_limit_up or is_volume_breakout or is_ma_breakthrough or consecutive_up >= 3:
                    candidates.append(candidate)
                    
            except Exception as e:
                logger.debug(f"处理股票 {stock_code} 时出错: {e}")
                continue
        
        return candidates
    
    def _filter_fundamental(
        self,
        candidates: List[CandidateStock],
        date: Optional[str] = None
    ) -> List[CandidateStock]:
        """
        财务因子筛选
        
        筛选条件：
        - ROE > 10%
        - 净利润同比增长 > 30%
        - 营收同比增长 > 20%
        
        Args:
            candidates: 候选股票列表
            date: 日期
        
        Returns:
            List[CandidateStock]: 筛选后的候选股票
        """
        if not candidates:
            return []
        
        try:
            # 获取股票代码列表
            stock_codes = [c.code for c in candidates]
            
            # 批量获取财务数据（免费版限制每次最多4000条，需要分批）
            batch_size = 1000
            fundamental_data = {}
            
            for i in range(0, len(stock_codes), batch_size):
                batch = stock_codes[i:i+batch_size]
                try:
                    # 查询财务指标 (使用正确的JQData字段名)
                    q = query(
                        valuation.code,
                        indicator.roe,  # ROE
                        indicator.inc_net_profit_year_on_year,  # 净利润同比增长率
                        indicator.inc_revenue_year_on_year  # 营收同比增长率
                    ).filter(
                        valuation.code.in_(batch)
                    )
                    
                    df = self.jq_client.get_fundamentals(q, date=date)
                    
                    if not df.empty:
                        for _, row in df.iterrows():
                            code = row['code']
                            fundamental_data[code] = {
                                'roe': row.get('roe', 0),
                                'net_profit_growth': row.get('inc_net_profit_year_on_year', 0),
                                'revenue_growth': row.get('inc_revenue_year_on_year', 0)
                            }
                except Exception as e:
                    logger.warning(f"获取财务数据失败（批次 {i//batch_size + 1}）: {e}")
                    continue
            
            # 更新候选股票的财务数据
            filtered = []
            for candidate in candidates:
                if candidate.code in fundamental_data:
                    data = fundamental_data[candidate.code]
                    candidate.roe = data.get('roe', 0)
                    candidate.net_profit_growth = data.get('net_profit_growth', 0)
                    candidate.revenue_growth = data.get('revenue_growth', 0)
                    
                    # 财务筛选：至少满足一个条件
                    if (candidate.roe and candidate.roe > 10) or \
                       (candidate.net_profit_growth and candidate.net_profit_growth > 30) or \
                       (candidate.revenue_growth and candidate.revenue_growth > 20):
                        filtered.append(candidate)
                else:
                    # 如果没有财务数据，保留（可能是新股或数据缺失）
                    filtered.append(candidate)
            
            return filtered
            
        except Exception as e:
            logger.error(f"财务因子筛选失败: {e}")
            # 如果财务筛选失败，返回原列表
            return candidates
    
    def _calculate_scores(self, candidates: List[CandidateStock]) -> List[CandidateStock]:
        """
        计算综合得分
        
        技术面得分（0-100）：
        - 涨停：30分
        - 放量突破：20分
        - 站上均线：20分
        - 连续上涨：每1天10分，最高30分
        
        基本面得分（0-100）：
        - ROE > 20%：40分，> 10%：20分
        - 净利润增长 > 50%：30分，> 30%：20分
        - 营收增长 > 30%：30分，> 20%：20分
        
        综合得分 = 技术面得分 * 0.6 + 基本面得分 * 0.4
        """
        for candidate in candidates:
            # 技术面得分
            tech_score = 0
            if candidate.is_limit_up:
                tech_score += 30
            if candidate.is_volume_breakout:
                tech_score += 20
            if candidate.is_ma_breakthrough:
                tech_score += 20
            tech_score += min(candidate.consecutive_up_days * 10, 30)
            candidate.technical_score = min(tech_score, 100)
            
            # 基本面得分
            fund_score = 0
            if candidate.roe:
                if candidate.roe > 20:
                    fund_score += 40
                elif candidate.roe > 10:
                    fund_score += 20
            if candidate.net_profit_growth:
                if candidate.net_profit_growth > 50:
                    fund_score += 30
                elif candidate.net_profit_growth > 30:
                    fund_score += 20
            if candidate.revenue_growth:
                if candidate.revenue_growth > 30:
                    fund_score += 30
                elif candidate.revenue_growth > 20:
                    fund_score += 20
            candidate.fundamental_score = min(fund_score, 100)
            
            # 综合得分
            candidate.composite_score = candidate.technical_score * 0.6 + candidate.fundamental_score * 0.4
            
            # 生成标签
            tags = []
            if candidate.is_limit_up:
                tags.append('涨停')
            if candidate.is_volume_breakout:
                tags.append('放量')
            if candidate.is_ma_breakthrough:
                tags.append('均线突破')
            if candidate.roe and candidate.roe > 15:
                tags.append('高ROE')
            if candidate.net_profit_growth and candidate.net_profit_growth > 30:
                tags.append('高增长')
            candidate.tags = tags
        
        return candidates
    
    def _save_to_cache(self, pool: CandidatePool):
        """保存到缓存（MongoDB和文件）"""
        try:
            # 保存到MongoDB
            if self.db is not None:
                collection = self.db.candidate_pools
                collection.replace_one(
                    {'pool_id': pool.pool_id},
                    pool.to_dict(),
                    upsert=True
                )
                logger.debug(f"已保存到MongoDB: {pool.pool_id}")
            
            # 保存到文件
            cache_file = self.cache_dir / f"{pool.pool_id}.json"
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(pool.to_dict(), f, ensure_ascii=False, indent=2)
            logger.debug(f"已保存到文件: {cache_file}")
            
        except Exception as e:
            logger.warning(f"保存缓存失败: {e}")
    
    def _load_from_cache(
        self,
        mainline_name: str,
        mainline_type: str,
        date: Optional[str] = None
    ) -> Optional[CandidatePool]:
        """从缓存加载"""
        try:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
            date_str = date.replace('-', '')
            pool_id = f"mainline_{mainline_name}_{date_str}"
            
            # 从MongoDB加载
            if self.db is not None:
                collection = self.db.candidate_pools
                doc = collection.find_one({'pool_id': pool_id})
                if doc:
                    return self._dict_to_pool(doc)
            
            # 从文件加载
            cache_file = self.cache_dir / f"{pool_id}.json"
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return self._dict_to_pool(data)
            
        except Exception as e:
            logger.debug(f"加载缓存失败: {e}")
        
        return None
    
    def _dict_to_pool(self, data: Dict) -> CandidatePool:
        """字典转CandidatePool对象"""
        stocks = [CandidateStock(**stock_data) for stock_data in data.get('stocks', [])]
        pool = CandidatePool(
            pool_id=data['pool_id'],
            mainline_name=data['mainline_name'],
            mainline_type=data['mainline_type'],
            create_time=data['create_time'],
            stocks=stocks,
            total_count=data.get('total_count', 0),
            filtered_count=data.get('filtered_count', 0),
            data_mode=data.get('data_mode', 'unknown'),
            data_date=data.get('data_date', '')
        )
        return pool
    
    def list_available_concepts(self) -> List[Dict[str, str]]:
        """
        列出所有可用的概念板块
        
        Returns:
            List[Dict]: 概念列表，每个元素包含 code 和 name
        """
        if not self.jq_client or not self.jq_client.is_authenticated():
            return []
        
        try:
            concepts = self.jq_client.get_all_concepts()
            if concepts.empty:
                return []
            
            result = []
            for code, row in concepts.iterrows():
                result.append({
                    'code': code,
                    'name': row['name']
                })
            return result
        except Exception as e:
            logger.error(f"获取概念列表失败: {e}")
            return []
    
    def list_available_industries(self) -> List[Dict[str, str]]:
        """
        列出所有可用的行业板块
        
        Returns:
            List[Dict]: 行业列表，每个元素包含 code 和 name
        """
        if not self.jq_client or not self.jq_client.is_authenticated():
            return []
        
        try:
            industries = self.jq_client.get_all_industries()
            if industries.empty:
                return []
            
            result = []
            for code, row in industries.iterrows():
                result.append({
                    'code': code,
                    'name': row.get('name', code)
                })
            return result
        except Exception as e:
            logger.error(f"获取行业列表失败: {e}")
            return []


