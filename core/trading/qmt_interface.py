# -*- coding: utf-8 -*-
"""
QMT/xtquant 交易接口
====================

对接迅投QMT量化交易终端

功能:
1. 账户连接与认证
2. 获取持仓信息
3. 订单提交与管理
4. 交易信号处理
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Callable
from enum import Enum
import time
import threading

logger = logging.getLogger(__name__)

# 尝试导入xtquant
try:
    from xtquant import xttrader
    from xtquant import xtdata
    from xtquant.xttype import StockAccount
    XTQUANT_AVAILABLE = True
except ImportError:
    XTQUANT_AVAILABLE = False
    logger.warning("xtquant未安装，QMT交易功能不可用")


class OrderDirection(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"       # 待提交
    SUBMITTED = "submitted"   # 已提交
    PARTIAL = "partial"       # 部分成交
    FILLED = "filled"         # 完全成交
    CANCELLED = "cancelled"   # 已撤单
    REJECTED = "rejected"     # 已拒绝
    FAILED = "failed"         # 失败


@dataclass
class Position:
    """持仓信息"""
    stock_code: str
    stock_name: str
    quantity: int
    available_qty: int
    cost_price: float
    current_price: float
    market_value: float
    profit_loss: float
    profit_loss_pct: float
    
    @classmethod
    def from_xtquant(cls, data: dict) -> 'Position':
        """从xtquant数据构建"""
        return cls(
            stock_code=data.get('stock_code', ''),
            stock_name=data.get('stock_name', ''),
            quantity=int(data.get('volume', 0)),
            available_qty=int(data.get('can_use_volume', 0)),
            cost_price=float(data.get('open_price', 0)),
            current_price=float(data.get('last_price', 0)),
            market_value=float(data.get('market_value', 0)),
            profit_loss=float(data.get('float_profit_loss', 0)),
            profit_loss_pct=float(data.get('profit_rate', 0))
        )


@dataclass
class Order:
    """订单信息"""
    order_id: str
    stock_code: str
    stock_name: str
    direction: OrderDirection
    price: float
    quantity: int
    filled_qty: int = 0
    filled_price: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    create_time: str = ""
    update_time: str = ""
    error_msg: str = ""


@dataclass
class AccountInfo:
    """账户信息"""
    account_id: str
    account_type: str
    total_asset: float
    cash: float
    market_value: float
    frozen_cash: float
    profit_loss: float
    profit_loss_pct: float


class QMTTrader:
    """QMT交易接口"""
    
    def __init__(self, qmt_path: str = None, account_id: str = None):
        """
        初始化
        
        Args:
            qmt_path: QMT安装路径
            account_id: 交易账户ID
        """
        self.qmt_path = qmt_path or "C:/国金QMT/userdata_mini"
        self.account_id = account_id
        self.connected = False
        self.trader = None
        self.account = None
        
        self._order_callbacks: List[Callable] = []
        self._trade_callbacks: List[Callable] = []
    
    def connect(self) -> bool:
        """
        连接QMT
        
        Returns:
            是否连接成功
        """
        if not XTQUANT_AVAILABLE:
            logger.error("xtquant未安装，无法连接QMT")
            return False
        
        try:
            # 创建trader对象
            self.trader = xttrader.XtQuantTrader(self.qmt_path, "TRQuant")
            
            # 启动trader
            self.trader.start()
            
            # 建立连接
            connect_result = self.trader.connect()
            
            if connect_result != 0:
                logger.error(f"QMT连接失败: {connect_result}")
                return False
            
            # 订阅账户
            if self.account_id:
                self.account = StockAccount(self.account_id)
                subscribe_result = self.trader.subscribe(self.account)
                
                if subscribe_result != 0:
                    logger.error(f"账户订阅失败: {subscribe_result}")
                    return False
            
            self.connected = True
            logger.info("✅ QMT连接成功")
            return True
            
        except Exception as e:
            logger.error(f"QMT连接异常: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.trader:
            self.trader.stop()
            self.connected = False
            logger.info("QMT已断开连接")
    
    def get_account_info(self) -> Optional[AccountInfo]:
        """获取账户信息"""
        if not self.connected or not self.account:
            return None
        
        try:
            data = self.trader.query_stock_asset(self.account)
            
            if data:
                return AccountInfo(
                    account_id=self.account_id,
                    account_type="股票账户",
                    total_asset=float(data.get('total_asset', 0)),
                    cash=float(data.get('cash', 0)),
                    market_value=float(data.get('market_value', 0)),
                    frozen_cash=float(data.get('frozen_cash', 0)),
                    profit_loss=float(data.get('float_profit_loss', 0)),
                    profit_loss_pct=0.0
                )
                
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
        
        return None
    
    def get_positions(self) -> List[Position]:
        """获取持仓列表"""
        if not self.connected or not self.account:
            return []
        
        try:
            positions = self.trader.query_stock_positions(self.account)
            return [Position.from_xtquant(p.__dict__) for p in positions]
            
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return []
    
    def get_orders(self, include_cancelled: bool = False) -> List[Order]:
        """获取委托列表"""
        if not self.connected or not self.account:
            return []
        
        try:
            orders = self.trader.query_stock_orders(self.account)
            
            result = []
            for o in orders:
                status = self._parse_order_status(o.order_status)
                if not include_cancelled and status in [OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                    continue
                
                result.append(Order(
                    order_id=str(o.order_id),
                    stock_code=o.stock_code,
                    stock_name=getattr(o, 'stock_name', ''),
                    direction=OrderDirection.BUY if o.order_type == 23 else OrderDirection.SELL,
                    price=float(o.price),
                    quantity=int(o.order_volume),
                    filled_qty=int(o.traded_volume),
                    filled_price=float(o.traded_price),
                    status=status,
                    create_time=str(o.order_time),
                    update_time='',
                    error_msg=getattr(o, 'status_msg', '')
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"获取委托失败: {e}")
            return []
    
    def buy(self, stock_code: str, price: float, quantity: int) -> Optional[str]:
        """
        买入股票
        
        Args:
            stock_code: 股票代码
            price: 价格（0为市价）
            quantity: 数量
        
        Returns:
            订单ID，失败返回None
        """
        return self._place_order(stock_code, OrderDirection.BUY, price, quantity)
    
    def sell(self, stock_code: str, price: float, quantity: int) -> Optional[str]:
        """
        卖出股票
        
        Args:
            stock_code: 股票代码
            price: 价格（0为市价）
            quantity: 数量
        
        Returns:
            订单ID，失败返回None
        """
        return self._place_order(stock_code, OrderDirection.SELL, price, quantity)
    
    def _place_order(self, stock_code: str, direction: OrderDirection, 
                     price: float, quantity: int) -> Optional[str]:
        """下单"""
        if not self.connected or not self.account:
            logger.error("未连接或未设置账户")
            return None
        
        try:
            # 23=买入，24=卖出
            order_type = 23 if direction == OrderDirection.BUY else 24
            
            # 0=限价，5=最优五档即时成交
            price_type = 11 if price == 0 else 11  # 11=限价
            
            order_id = self.trader.order_stock(
                self.account,
                stock_code,
                order_type,
                quantity,
                price_type,
                price
            )
            
            if order_id > 0:
                logger.info(f"下单成功: {stock_code} {direction.value} {quantity}@{price}, ID={order_id}")
                return str(order_id)
            else:
                logger.error(f"下单失败: {order_id}")
                return None
                
        except Exception as e:
            logger.error(f"下单异常: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """
        撤单
        
        Args:
            order_id: 订单ID
        
        Returns:
            是否成功
        """
        if not self.connected or not self.account:
            return False
        
        try:
            result = self.trader.cancel_order_stock(self.account, int(order_id))
            return result == 0
            
        except Exception as e:
            logger.error(f"撤单失败: {e}")
            return False
    
    def _parse_order_status(self, status_code: int) -> OrderStatus:
        """解析订单状态"""
        status_map = {
            0: OrderStatus.PENDING,
            1: OrderStatus.SUBMITTED,
            2: OrderStatus.PARTIAL,
            3: OrderStatus.FILLED,
            4: OrderStatus.CANCELLED,
            5: OrderStatus.REJECTED,
        }
        return status_map.get(status_code, OrderStatus.PENDING)
    
    def register_order_callback(self, callback: Callable):
        """注册订单回调"""
        self._order_callbacks.append(callback)
    
    def register_trade_callback(self, callback: Callable):
        """注册成交回调"""
        self._trade_callbacks.append(callback)


class MockQMTTrader:
    """
    模拟QMT交易接口
    
    用于测试和开发，不需要实际QMT环境
    """
    
    def __init__(self):
        self.connected = False
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.cash = 1000000.0
        self.order_counter = 0
    
    def connect(self) -> bool:
        self.connected = True
        logger.info("✅ Mock QMT连接成功")
        return True
    
    def disconnect(self):
        self.connected = False
        logger.info("Mock QMT已断开")
    
    def get_account_info(self) -> AccountInfo:
        market_value = sum(p.market_value for p in self.positions.values())
        return AccountInfo(
            account_id="MOCK_ACCOUNT",
            account_type="模拟账户",
            total_asset=self.cash + market_value,
            cash=self.cash,
            market_value=market_value,
            frozen_cash=0.0,
            profit_loss=0.0,
            profit_loss_pct=0.0
        )
    
    def get_positions(self) -> List[Position]:
        return list(self.positions.values())
    
    def get_orders(self, include_cancelled: bool = False) -> List[Order]:
        orders = list(self.orders.values())
        if not include_cancelled:
            orders = [o for o in orders if o.status not in [OrderStatus.CANCELLED, OrderStatus.REJECTED]]
        return orders
    
    def buy(self, stock_code: str, price: float, quantity: int) -> Optional[str]:
        cost = price * quantity
        if cost > self.cash:
            logger.warning(f"资金不足: 需要{cost}, 可用{self.cash}")
            return None
        
        self.order_counter += 1
        order_id = f"MOCK_{self.order_counter}"
        
        # 模拟成交
        self.cash -= cost
        
        if stock_code in self.positions:
            pos = self.positions[stock_code]
            new_qty = pos.quantity + quantity
            pos.cost_price = (pos.cost_price * pos.quantity + price * quantity) / new_qty
            pos.quantity = new_qty
            pos.available_qty = new_qty
            pos.market_value = new_qty * price
        else:
            self.positions[stock_code] = Position(
                stock_code=stock_code,
                stock_name=stock_code,
                quantity=quantity,
                available_qty=quantity,
                cost_price=price,
                current_price=price,
                market_value=quantity * price,
                profit_loss=0,
                profit_loss_pct=0
            )
        
        self.orders[order_id] = Order(
            order_id=order_id,
            stock_code=stock_code,
            stock_name=stock_code,
            direction=OrderDirection.BUY,
            price=price,
            quantity=quantity,
            filled_qty=quantity,
            filled_price=price,
            status=OrderStatus.FILLED,
            create_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        logger.info(f"[MOCK] 买入成功: {stock_code} {quantity}@{price}")
        return order_id
    
    def sell(self, stock_code: str, price: float, quantity: int) -> Optional[str]:
        if stock_code not in self.positions:
            logger.warning(f"无持仓: {stock_code}")
            return None
        
        pos = self.positions[stock_code]
        if quantity > pos.available_qty:
            logger.warning(f"可用不足: 需要{quantity}, 可用{pos.available_qty}")
            return None
        
        self.order_counter += 1
        order_id = f"MOCK_{self.order_counter}"
        
        # 模拟成交
        proceeds = price * quantity
        self.cash += proceeds
        
        pos.quantity -= quantity
        pos.available_qty -= quantity
        pos.market_value = pos.quantity * price
        
        if pos.quantity <= 0:
            del self.positions[stock_code]
        
        self.orders[order_id] = Order(
            order_id=order_id,
            stock_code=stock_code,
            stock_name=stock_code,
            direction=OrderDirection.SELL,
            price=price,
            quantity=quantity,
            filled_qty=quantity,
            filled_price=price,
            status=OrderStatus.FILLED,
            create_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        logger.info(f"[MOCK] 卖出成功: {stock_code} {quantity}@{price}")
        return order_id
    
    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.CANCELLED
            return True
        return False


def create_trader(use_mock: bool = True, **kwargs) -> QMTTrader:
    """
    创建交易接口
    
    Args:
        use_mock: 是否使用模拟接口
        **kwargs: QMTTrader参数
    
    Returns:
        交易接口实例
    """
    if use_mock or not XTQUANT_AVAILABLE:
        return MockQMTTrader()
    return QMTTrader(**kwargs)

