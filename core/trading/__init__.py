# -*- coding: utf-8 -*-
"""
交易模块
========

实盘交易接口集成

支持:
- xtquant: 迅投QMT接口（国金/国盛/国信/海通等券商）
- 模拟交易: 本地模拟交易
"""

from .qmt_interface import (
    QMTTrader,
    MockQMTTrader,
    Position,
    Order,
    OrderDirection,
    OrderStatus,
    AccountInfo,
    create_trader,
    XTQUANT_AVAILABLE
)

from .xtquant_backtest import (
    XtBacktestConfig,
    XtBacktestEngine,
    XtBacktestResult,
    XtDataDownloader,
    XtLiveTrader,
    XtPosition,
    XtOrder,
    check_xtquant_status,
    create_xt_backtest_engine
)

from .trade_logger import (
    TradeLogger,
    TradeLog,
    LogType,
    get_trade_logger
)

__all__ = [
    # QMT接口
    'QMTTrader',
    'MockQMTTrader',
    'Position',
    'Order',
    'OrderDirection',
    'OrderStatus',
    'AccountInfo',
    'create_trader',
    'XTQUANT_AVAILABLE',
    
    # xtquant回测
    'XtBacktestConfig',
    'XtBacktestEngine',
    'XtBacktestResult',
    'XtDataDownloader',
    'XtLiveTrader',
    'XtPosition',
    'XtOrder',
    'check_xtquant_status',
    'create_xt_backtest_engine',
    
    # 交易日志
    'TradeLogger',
    'TradeLog',
    'LogType',
    'get_trade_logger'
]

