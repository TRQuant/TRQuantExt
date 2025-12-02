# -*- coding: utf-8 -*-
"""
交易日志记录器
==============

记录所有交易活动，支持MongoDB存储和查询

功能:
1. 记录订单提交
2. 记录成交回报
3. 记录账户变动
4. 交易统计分析
"""

import logging
from dataclasses import dataclass, asdict
from datetime import datetime, date
from typing import List, Dict, Optional, Any
from enum import Enum
import json

logger = logging.getLogger(__name__)

# MongoDB连接
try:
    from pymongo import MongoClient
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False


class LogType(Enum):
    """日志类型"""
    ORDER = "order"           # 订单日志
    TRADE = "trade"           # 成交日志
    POSITION = "position"     # 持仓变动
    ACCOUNT = "account"       # 账户变动
    SIGNAL = "signal"         # 交易信号
    ERROR = "error"           # 错误日志


@dataclass
class TradeLog:
    """交易日志"""
    log_id: str
    log_type: str
    timestamp: str
    account_id: str
    stock_code: str = ""
    stock_name: str = ""
    direction: str = ""
    price: float = 0.0
    quantity: int = 0
    amount: float = 0.0
    order_id: str = ""
    status: str = ""
    message: str = ""
    extra_data: Dict = None
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['extra_data'] = d.get('extra_data') or {}
        return d


class TradeLogger:
    """交易日志记录器"""
    
    def __init__(self, account_id: str = "default", 
                 mongodb_uri: str = "mongodb://localhost:27017"):
        """
        初始化
        
        Args:
            account_id: 账户ID
            mongodb_uri: MongoDB连接URI
        """
        self.account_id = account_id
        self.db = None
        self.collection = None
        self.log_counter = 0
        
        if MONGO_AVAILABLE:
            try:
                client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=3000)
                client.server_info()
                self.db = client['trquant']
                self.collection = self.db['trade_logs']
                
                # 创建索引
                self.collection.create_index([
                    ("timestamp", -1),
                    ("log_type", 1),
                    ("account_id", 1)
                ])
                
                logger.info("✅ 交易日志MongoDB连接成功")
                
            except Exception as e:
                logger.warning(f"MongoDB连接失败，使用内存存储: {e}")
                self._logs = []
        else:
            self._logs = []
    
    def _generate_log_id(self) -> str:
        """生成日志ID"""
        self.log_counter += 1
        return f"LOG_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self.log_counter:04d}"
    
    def log_order(self, stock_code: str, direction: str, 
                  price: float, quantity: int, order_id: str,
                  status: str = "submitted", message: str = "",
                  **extra) -> str:
        """
        记录订单
        
        Returns:
            日志ID
        """
        log = TradeLog(
            log_id=self._generate_log_id(),
            log_type=LogType.ORDER.value,
            timestamp=datetime.now().isoformat(),
            account_id=self.account_id,
            stock_code=stock_code,
            direction=direction,
            price=price,
            quantity=quantity,
            amount=price * quantity,
            order_id=order_id,
            status=status,
            message=message,
            extra_data=extra
        )
        
        self._save_log(log)
        logger.info(f"📝 订单日志: {stock_code} {direction} {quantity}@{price}")
        return log.log_id
    
    def log_trade(self, stock_code: str, direction: str,
                  price: float, quantity: int, order_id: str,
                  message: str = "", **extra) -> str:
        """
        记录成交
        
        Returns:
            日志ID
        """
        log = TradeLog(
            log_id=self._generate_log_id(),
            log_type=LogType.TRADE.value,
            timestamp=datetime.now().isoformat(),
            account_id=self.account_id,
            stock_code=stock_code,
            direction=direction,
            price=price,
            quantity=quantity,
            amount=price * quantity,
            order_id=order_id,
            status="filled",
            message=message,
            extra_data=extra
        )
        
        self._save_log(log)
        logger.info(f"💰 成交日志: {stock_code} {direction} {quantity}@{price}")
        return log.log_id
    
    def log_signal(self, stock_code: str, direction: str,
                   signal_type: str, score: float = 0.0,
                   message: str = "", **extra) -> str:
        """
        记录交易信号
        
        Returns:
            日志ID
        """
        log = TradeLog(
            log_id=self._generate_log_id(),
            log_type=LogType.SIGNAL.value,
            timestamp=datetime.now().isoformat(),
            account_id=self.account_id,
            stock_code=stock_code,
            direction=direction,
            message=message,
            extra_data={
                'signal_type': signal_type,
                'score': score,
                **extra
            }
        )
        
        self._save_log(log)
        logger.info(f"📊 信号日志: {stock_code} {direction} {signal_type}")
        return log.log_id
    
    def log_error(self, message: str, stock_code: str = "",
                  order_id: str = "", **extra) -> str:
        """
        记录错误
        
        Returns:
            日志ID
        """
        log = TradeLog(
            log_id=self._generate_log_id(),
            log_type=LogType.ERROR.value,
            timestamp=datetime.now().isoformat(),
            account_id=self.account_id,
            stock_code=stock_code,
            order_id=order_id,
            message=message,
            extra_data=extra
        )
        
        self._save_log(log)
        logger.error(f"❌ 错误日志: {message}")
        return log.log_id
    
    def _save_log(self, log: TradeLog):
        """保存日志"""
        if self.collection is not None:
            try:
                self.collection.insert_one(log.to_dict())
            except Exception as e:
                logger.error(f"保存日志失败: {e}")
                self._logs.append(log.to_dict())
        else:
            self._logs.append(log.to_dict())
    
    def query_logs(self, 
                   log_type: str = None,
                   stock_code: str = None,
                   start_date: str = None,
                   end_date: str = None,
                   limit: int = 100) -> List[Dict]:
        """
        查询日志
        
        Args:
            log_type: 日志类型
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回数量限制
        
        Returns:
            日志列表
        """
        if self.collection is not None:
            query = {"account_id": self.account_id}
            
            if log_type:
                query["log_type"] = log_type
            if stock_code:
                query["stock_code"] = stock_code
            if start_date:
                query["timestamp"] = {"$gte": start_date}
            if end_date:
                if "timestamp" in query:
                    query["timestamp"]["$lte"] = end_date
                else:
                    query["timestamp"] = {"$lte": end_date}
            
            try:
                cursor = self.collection.find(query).sort("timestamp", -1).limit(limit)
                return list(cursor)
            except Exception as e:
                logger.error(f"查询日志失败: {e}")
                return []
        else:
            # 内存查询
            result = self._logs.copy()
            
            if log_type:
                result = [l for l in result if l.get('log_type') == log_type]
            if stock_code:
                result = [l for l in result if l.get('stock_code') == stock_code]
            
            return result[-limit:]
    
    def get_today_summary(self) -> Dict:
        """获取今日交易摘要"""
        today = date.today().isoformat()
        
        orders = self.query_logs(log_type=LogType.ORDER.value, start_date=today)
        trades = self.query_logs(log_type=LogType.TRADE.value, start_date=today)
        errors = self.query_logs(log_type=LogType.ERROR.value, start_date=today)
        
        buy_trades = [t for t in trades if t.get('direction') == 'buy']
        sell_trades = [t for t in trades if t.get('direction') == 'sell']
        
        return {
            'date': today,
            'order_count': len(orders),
            'trade_count': len(trades),
            'buy_count': len(buy_trades),
            'sell_count': len(sell_trades),
            'buy_amount': sum(t.get('amount', 0) for t in buy_trades),
            'sell_amount': sum(t.get('amount', 0) for t in sell_trades),
            'error_count': len(errors)
        }
    
    def export_logs(self, filepath: str, log_type: str = None,
                    start_date: str = None, end_date: str = None):
        """导出日志到文件"""
        logs = self.query_logs(
            log_type=log_type,
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )
        
        # 移除MongoDB的_id字段
        for log in logs:
            if '_id' in log:
                del log['_id']
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
        
        logger.info(f"日志已导出: {filepath}, 共{len(logs)}条")


def get_trade_logger(account_id: str = "default") -> TradeLogger:
    """
    获取交易日志记录器
    
    Args:
        account_id: 账户ID
    
    Returns:
        TradeLogger实例
    """
    return TradeLogger(account_id)

