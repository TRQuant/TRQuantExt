# -*- coding: utf-8 -*-
"""
通达信数据读取器
==================

支持读取通达信本地数据文件，包括：
1. 日线数据 (.day)
2. 分钟线数据 (1min/5min/15min/30min/60min)
3. 除权数据

通达信数据格式参考：
- 日线：每条记录32字节
- 分钟线：每条记录32字节
- 数据存储为小端序二进制格式
"""

import os
import struct
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Union
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)


class TDXDataReader:
    """
    通达信数据读取器
    
    支持的数据类型：
    - 日线 (vipdoc/sh/lday/, vipdoc/sz/lday/)
    - 1分钟线 (vipdoc/sh/fzline/, vipdoc/sz/fzline/)
    - 5分钟线 (vipdoc/sh/minline/, vipdoc/sz/minline/)
    """
    
    # 通达信数据目录结构
    DATA_PATHS = {
        'sh': {
            'day': 'vipdoc/sh/lday',
            '1min': 'vipdoc/sh/fzline',
            '5min': 'vipdoc/sh/minline',
        },
        'sz': {
            'day': 'vipdoc/sz/lday',
            '1min': 'vipdoc/sz/fzline',
            '5min': 'vipdoc/sz/minline',
        }
    }
    
    # 日线数据结构 (32字节)
    DAY_STRUCT = struct.Struct('<IIIIIfII')
    # date(4), open(4), high(4), low(4), close(4), amount(4), volume(4), reserved(4)
    
    # 分钟线数据结构 (32字节)
    MIN_STRUCT = struct.Struct('<HHfffffII')
    # date(2), time(2), open(4), high(4), low(4), close(4), amount(4), volume(4)
    
    def __init__(self, tdx_root: Optional[str] = None):
        """
        初始化
        
        Args:
            tdx_root: 通达信安装目录，如 '/home/user/通达信'
                      如果为None，将尝试自动检测
        """
        self.tdx_root = tdx_root
        if self.tdx_root:
            self.tdx_root = Path(self.tdx_root)
        else:
            self.tdx_root = self._detect_tdx_path()
        
        self._initialized = self.tdx_root is not None and self.tdx_root.exists()
        
        if self._initialized:
            logger.info(f"✅ 通达信数据目录: {self.tdx_root}")
        else:
            logger.warning("⚠️ 未找到通达信数据目录")
    
    def _detect_tdx_path(self) -> Optional[Path]:
        """自动检测通达信安装路径"""
        common_paths = [
            Path.home() / '通达信',
            Path.home() / 'TDX',
            Path.home() / 'new_tdx',
            Path('/opt/tdx'),
            Path('/opt/通达信'),
            Path('C:/new_tdx'),
            Path('D:/new_tdx'),
            Path('C:/通达信'),
        ]
        
        for p in common_paths:
            if p.exists() and (p / 'vipdoc').exists():
                return p
        
        return None
    
    def is_available(self) -> bool:
        """检查是否可用"""
        return self._initialized
    
    def set_tdx_path(self, path: str) -> bool:
        """设置通达信路径"""
        p = Path(path)
        if p.exists() and (p / 'vipdoc').exists():
            self.tdx_root = p
            self._initialized = True
            logger.info(f"✅ 通达信路径已更新: {self.tdx_root}")
            return True
        else:
            logger.warning(f"⚠️ 无效的通达信路径: {path}")
            return False
    
    def get_stock_list(self) -> List[Dict]:
        """获取可用的股票列表"""
        if not self._initialized:
            return []
        
        stocks = []
        
        for market in ['sh', 'sz']:
            day_path = self.tdx_root / self.DATA_PATHS[market]['day']
            if not day_path.exists():
                continue
            
            for f in day_path.glob('*.day'):
                code = f.stem
                # 过滤指数和非股票
                if market == 'sh':
                    if code.startswith('6'):
                        stocks.append({
                            'code': f'{code}.XSHG',
                            'market': 'sh',
                            'name': code
                        })
                else:
                    if code.startswith('0') or code.startswith('3'):
                        stocks.append({
                            'code': f'{code}.XSHE',
                            'market': 'sz',
                            'name': code
                        })
        
        logger.info(f"📊 通达信数据: 共 {len(stocks)} 只股票")
        return stocks
    
    def read_day_data(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        读取日线数据
        
        Args:
            code: 股票代码，如 '000001.XSHE' 或 '000001'
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
        
        Returns:
            DataFrame with columns: date, open, high, low, close, volume, amount
        """
        if not self._initialized:
            logger.warning("通达信数据读取器未初始化")
            return None
        
        # 解析股票代码
        pure_code, market = self._parse_code(code)
        if not market:
            logger.warning(f"无法解析股票代码: {code}")
            return None
        
        # 构建文件路径
        file_path = self.tdx_root / self.DATA_PATHS[market]['day'] / f'{pure_code}.day'
        
        if not file_path.exists():
            logger.warning(f"日线数据文件不存在: {file_path}")
            return None
        
        try:
            data = self._read_day_file(file_path)
            
            if data.empty:
                return None
            
            # 日期过滤
            if start_date:
                data = data[data['date'] >= start_date]
            if end_date:
                data = data[data['date'] <= end_date]
            
            return data
            
        except Exception as e:
            logger.error(f"读取日线数据失败: {e}")
            return None
    
    def read_minute_data(
        self,
        code: str,
        frequency: str = '5min',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        读取分钟线数据
        
        Args:
            code: 股票代码
            frequency: '1min' 或 '5min'
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            DataFrame with columns: datetime, open, high, low, close, volume, amount
        """
        if not self._initialized:
            logger.warning("通达信数据读取器未初始化")
            return None
        
        # 解析股票代码
        pure_code, market = self._parse_code(code)
        if not market:
            logger.warning(f"无法解析股票代码: {code}")
            return None
        
        # 获取数据路径
        freq_key = '1min' if frequency in ['1min', '1m'] else '5min'
        file_ext = '.lc1' if freq_key == '1min' else '.lc5'
        
        data_dir = self.tdx_root / self.DATA_PATHS[market][freq_key]
        file_path = data_dir / f'{pure_code}{file_ext}'
        
        if not file_path.exists():
            logger.warning(f"分钟线数据文件不存在: {file_path}")
            return None
        
        try:
            data = self._read_minute_file(file_path)
            
            if data.empty:
                return None
            
            # 日期过滤
            if start_date:
                data = data[data['date'] >= start_date]
            if end_date:
                data = data[data['date'] <= end_date]
            
            return data
            
        except Exception as e:
            logger.error(f"读取分钟线数据失败: {e}")
            return None
    
    def _parse_code(self, code: str) -> tuple:
        """解析股票代码，返回 (纯代码, 市场)"""
        if '.' in code:
            parts = code.split('.')
            pure_code = parts[0]
            suffix = parts[1].upper()
            if suffix in ['XSHG', 'SH']:
                return pure_code, 'sh'
            elif suffix in ['XSHE', 'SZ']:
                return pure_code, 'sz'
        else:
            pure_code = code
            # 根据代码前缀判断市场
            if pure_code.startswith('6'):
                return pure_code, 'sh'
            elif pure_code.startswith(('0', '3')):
                return pure_code, 'sz'
        
        return None, None
    
    def _read_day_file(self, file_path: Path) -> pd.DataFrame:
        """读取日线文件"""
        records = []
        record_size = 32
        
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(record_size)
                if len(data) < record_size:
                    break
                
                try:
                    # 解析数据
                    # 日期格式: YYYYMMDD (整数)
                    date_int = struct.unpack('<I', data[0:4])[0]
                    open_price = struct.unpack('<I', data[4:8])[0] / 100.0
                    high_price = struct.unpack('<I', data[8:12])[0] / 100.0
                    low_price = struct.unpack('<I', data[12:16])[0] / 100.0
                    close_price = struct.unpack('<I', data[16:20])[0] / 100.0
                    amount = struct.unpack('<f', data[20:24])[0]
                    volume = struct.unpack('<I', data[24:28])[0]
                    
                    # 转换日期
                    year = date_int // 10000
                    month = (date_int % 10000) // 100
                    day = date_int % 100
                    date_str = f'{year:04d}-{month:02d}-{day:02d}'
                    
                    records.append({
                        'date': date_str,
                        'open': open_price,
                        'high': high_price,
                        'low': low_price,
                        'close': close_price,
                        'volume': volume,
                        'amount': amount
                    })
                    
                except Exception as e:
                    logger.debug(f"解析记录失败: {e}")
                    continue
        
        if records:
            df = pd.DataFrame(records)
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            return df
        
        return pd.DataFrame()
    
    def _read_minute_file(self, file_path: Path) -> pd.DataFrame:
        """读取分钟线文件"""
        records = []
        record_size = 32
        
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(record_size)
                if len(data) < record_size:
                    break
                
                try:
                    # 解析数据
                    date_int = struct.unpack('<H', data[0:2])[0]
                    time_int = struct.unpack('<H', data[2:4])[0]
                    open_price = struct.unpack('<f', data[4:8])[0]
                    high_price = struct.unpack('<f', data[8:12])[0]
                    low_price = struct.unpack('<f', data[12:16])[0]
                    close_price = struct.unpack('<f', data[16:20])[0]
                    amount = struct.unpack('<f', data[20:24])[0]
                    volume = struct.unpack('<I', data[24:28])[0]
                    
                    # 转换日期时间
                    # 日期格式: (year-2004)*2048 + month*100 + day
                    year = (date_int // 2048) + 2004
                    month = (date_int % 2048) // 100
                    day = (date_int % 2048) % 100
                    
                    # 时间格式: hour*60 + minute
                    hour = time_int // 60
                    minute = time_int % 60
                    
                    date_str = f'{year:04d}-{month:02d}-{day:02d}'
                    time_str = f'{hour:02d}:{minute:02d}'
                    datetime_str = f'{date_str} {time_str}'
                    
                    records.append({
                        'datetime': datetime_str,
                        'date': date_str,
                        'time': time_str,
                        'open': open_price,
                        'high': high_price,
                        'low': low_price,
                        'close': close_price,
                        'volume': volume,
                        'amount': amount
                    })
                    
                except Exception as e:
                    logger.debug(f"解析分钟记录失败: {e}")
                    continue
        
        if records:
            df = pd.DataFrame(records)
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.set_index('datetime')
            return df
        
        return pd.DataFrame()
    
    def import_to_mongodb(
        self,
        code: str,
        data_type: str = 'day',
        overwrite: bool = False
    ) -> int:
        """
        将通达信数据导入MongoDB
        
        Args:
            code: 股票代码
            data_type: 'day' 或 '5min'
            overwrite: 是否覆盖已有数据
        
        Returns:
            导入的记录数
        """
        try:
            from pymongo import MongoClient
            
            if data_type == 'day':
                data = self.read_day_data(code)
                collection_name = 'market_data'
            else:
                data = self.read_minute_data(code, frequency=data_type)
                collection_name = f'market_data_{data_type}'
            
            if data is None or data.empty:
                return 0
            
            client = MongoClient('mongodb://localhost:27017')
            db = client.jqquant
            collection = db[collection_name]
            
            # 重置索引
            df = data.reset_index()
            records = df.to_dict('records')
            
            # 添加代码字段
            for record in records:
                record['code'] = code
                # 转换datetime
                for key in ['date', 'datetime']:
                    if key in record and hasattr(record[key], 'strftime'):
                        record[key] = record[key].strftime('%Y-%m-%d' if key == 'date' else '%Y-%m-%d %H:%M:%S')
            
            count = 0
            for record in records:
                if overwrite:
                    key = {'code': code, 'date': record.get('date', record.get('datetime'))}
                    collection.update_one(key, {'$set': record}, upsert=True)
                    count += 1
                else:
                    try:
                        collection.insert_one(record)
                        count += 1
                    except:
                        pass  # 忽略重复
            
            logger.info(f"✅ 已导入 {count} 条 {data_type} 数据: {code}")
            return count
            
        except Exception as e:
            logger.error(f"导入MongoDB失败: {e}")
            return 0


def get_tdx_reader(tdx_path: str = None) -> TDXDataReader:
    """获取通达信数据读取器"""
    return TDXDataReader(tdx_path)

