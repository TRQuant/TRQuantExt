# -*- coding: utf-8 -*-
"""
XtQuant回测模块
===============

基于迅投xtquant的回测引擎，可对接国金/国盛/国信等券商QMT

功能:
1. 历史数据下载与缓存
2. 策略回测执行
3. 绩效分析
4. 实盘对接准备

支持的券商:
- 国金证券 (推荐)
- 国盛证券
- 国信证券
- 海通证券
- 华鑫证券

使用前提:
1. pip install xtquant
2. 本地运行miniQMT客户端（极简模式）
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any, Callable
from enum import Enum
import time
import os

logger = logging.getLogger(__name__)

# 尝试导入xtquant
XTQUANT_INSTALLED = False
XTQUANT_AVAILABLE = False
XTQUANT_DATA_AVAILABLE = False
XTQUANT_TRADE_AVAILABLE = False

try:
    import xtquant
    XTQUANT_INSTALLED = True
    logger.info(f"✅ xtquant已安装: {getattr(xtquant, '__version__', 'unknown')}")
except ImportError:
    logger.warning("xtquant未安装，请运行: pip install xtquant")

# 尝试导入数据模块
if XTQUANT_INSTALLED:
    try:
        from xtquant import xtdata
        XTQUANT_DATA_AVAILABLE = True
        logger.info("✅ xtdata数据模块可用")
    except Exception as e:
        logger.warning(f"xtdata不可用(需要miniQMT运行): {e}")

# 尝试导入交易模块
if XTQUANT_INSTALLED:
    try:
        from xtquant import xttrader
        from xtquant.xttype import StockAccount
        XTQUANT_TRADE_AVAILABLE = True
        logger.info("✅ xttrader交易模块可用")
    except Exception as e:
        logger.warning(f"xttrader不可用(需要miniQMT运行): {e}")

XTQUANT_AVAILABLE = XTQUANT_DATA_AVAILABLE or XTQUANT_TRADE_AVAILABLE


@dataclass
class XtBacktestConfig:
    """xtquant回测配置"""
    start_date: str                          # 开始日期 YYYYMMDD
    end_date: str                            # 结束日期 YYYYMMDD
    stock_list: List[str] = field(default_factory=list)  # 股票列表
    initial_capital: float = 1000000.0       # 初始资金
    commission_rate: float = 0.0003          # 佣金率
    stamp_tax: float = 0.001                 # 印花税
    slippage: float = 0.001                  # 滑点
    benchmark: str = "000300.SH"             # 基准指数
    data_period: str = "1d"                  # 数据周期: 1m/5m/15m/30m/60m/1d
    qmt_path: str = ""                       # miniQMT路径


@dataclass
class XtPosition:
    """持仓信息"""
    stock_code: str
    volume: int
    available: int
    cost_price: float
    market_value: float


@dataclass
class XtOrder:
    """订单信息"""
    order_id: int
    stock_code: str
    direction: str  # buy/sell
    price: float
    volume: int
    traded_volume: int
    status: str
    create_time: str


@dataclass
class XtBacktestResult:
    """回测结果"""
    total_return: float              # 总收益率
    annual_return: float             # 年化收益率
    max_drawdown: float              # 最大回撤
    sharpe_ratio: float              # 夏普比率
    win_rate: float                  # 胜率
    trade_count: int                 # 交易次数
    benchmark_return: float          # 基准收益率
    daily_returns: List[float] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    trades: List[Dict] = field(default_factory=list)


class XtDataDownloader:
    """
    xtquant数据下载器
    
    用于下载和缓存历史行情数据
    """
    
    def __init__(self, data_dir: str = None):
        """
        初始化
        
        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = data_dir or os.path.expanduser("~/.trquant/xtdata")
        os.makedirs(self.data_dir, exist_ok=True)
        
        if XTQUANT_AVAILABLE:
            # 设置数据目录
            xtdata.data_dir = self.data_dir
    
    def download_history(self, 
                        stock_list: List[str],
                        start_date: str,
                        end_date: str,
                        period: str = "1d",
                        callback: Callable = None) -> bool:
        """
        下载历史数据
        
        Args:
            stock_list: 股票代码列表
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            period: 周期 1m/5m/15m/30m/60m/1d
            callback: 进度回调函数
        
        Returns:
            是否成功
        """
        if not XTQUANT_AVAILABLE:
            logger.error("xtquant未安装")
            return False
        
        try:
            total = len(stock_list)
            for i, stock in enumerate(stock_list):
                if callback:
                    callback(i + 1, total, f"下载 {stock}")
                
                # 下载数据
                xtdata.download_history_data(
                    stock_code=stock,
                    period=period,
                    start_time=start_date,
                    end_time=end_date
                )
                
                logger.debug(f"下载完成: {stock}")
            
            logger.info(f"✅ 历史数据下载完成: {total}只股票")
            return True
            
        except Exception as e:
            logger.error(f"下载历史数据失败: {e}")
            return False
    
    def get_market_data(self,
                       stock_list: List[str],
                       period: str = "1d",
                       start_time: str = "",
                       end_time: str = "",
                       count: int = -1) -> Dict:
        """
        获取行情数据
        
        Args:
            stock_list: 股票代码列表
            period: 周期
            start_time: 开始时间
            end_time: 结束时间
            count: 数据条数（-1为全部）
        
        Returns:
            行情数据字典 {stock_code: DataFrame}
        """
        if not XTQUANT_AVAILABLE:
            return {}
        
        try:
            data = xtdata.get_market_data_ex(
                field_list=[],  # 空列表返回全部字段
                stock_list=stock_list,
                period=period,
                start_time=start_time,
                end_time=end_time,
                count=count,
                dividend_type='front',  # 前复权
                fill_data=True
            )
            return data
            
        except Exception as e:
            logger.error(f"获取行情数据失败: {e}")
            return {}
    
    def get_stock_list(self, market: str = "SH") -> List[str]:
        """
        获取股票列表
        
        Args:
            market: 市场 SH/SZ
        
        Returns:
            股票代码列表
        """
        if not XTQUANT_AVAILABLE:
            return []
        
        try:
            if market == "SH":
                return xtdata.get_stock_list_in_sector("沪深A股")
            elif market == "SZ":
                return xtdata.get_stock_list_in_sector("深证A股")
            else:
                return xtdata.get_stock_list_in_sector("沪深A股")
                
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return []


class XtBacktestEngine:
    """
    xtquant回测引擎
    
    基于xtquant进行策略回测
    """
    
    def __init__(self, config: XtBacktestConfig):
        """
        初始化
        
        Args:
            config: 回测配置
        """
        self.config = config
        self.downloader = XtDataDownloader()
        
        # 回测状态
        self.cash = config.initial_capital
        self.positions: Dict[str, XtPosition] = {}
        self.trades: List[Dict] = []
        self.equity_history: List[float] = []
        self.current_date = ""
    
    def run(self, 
            strategy_func: Callable,
            on_progress: Callable = None) -> XtBacktestResult:
        """
        运行回测
        
        Args:
            strategy_func: 策略函数，接收(date, data, positions, cash)参数
            on_progress: 进度回调
        
        Returns:
            回测结果
        """
        if not XTQUANT_AVAILABLE:
            logger.warning("xtquant未安装，使用模拟回测")
            return self._run_mock_backtest(strategy_func, on_progress)
        
        logger.info(f"🚀 开始xtquant回测: {self.config.start_date} ~ {self.config.end_date}")
        start_time = time.time()
        
        # 1. 下载历史数据
        if on_progress:
            on_progress(10, "下载历史数据...")
        
        self.downloader.download_history(
            self.config.stock_list,
            self.config.start_date,
            self.config.end_date,
            self.config.data_period
        )
        
        # 2. 获取行情数据
        if on_progress:
            on_progress(30, "加载行情数据...")
        
        market_data = self.downloader.get_market_data(
            self.config.stock_list,
            self.config.data_period,
            self.config.start_date,
            self.config.end_date
        )
        
        if not market_data:
            logger.error("无法获取行情数据")
            return self._empty_result()
        
        # 3. 获取交易日期序列
        sample_stock = list(market_data.keys())[0]
        dates = list(market_data[sample_stock].index)
        
        # 4. 逐日回测
        if on_progress:
            on_progress(50, "执行回测...")
        
        for i, dt in enumerate(dates):
            self.current_date = str(dt)
            
            # 获取当日数据
            daily_data = {
                stock: df.loc[dt] if dt in df.index else None
                for stock, df in market_data.items()
            }
            
            # 执行策略
            signals = strategy_func(
                self.current_date,
                daily_data,
                self.positions.copy(),
                self.cash
            )
            
            # 处理信号
            if signals:
                self._process_signals(signals, daily_data)
            
            # 更新持仓市值
            self._update_positions_value(daily_data)
            
            # 记录净值
            total_value = self.cash + sum(p.market_value for p in self.positions.values())
            self.equity_history.append(total_value)
            
            if on_progress and i % 50 == 0:
                progress = 50 + int(40 * i / len(dates))
                on_progress(progress, f"回测中... {self.current_date}")
        
        # 5. 计算绩效
        if on_progress:
            on_progress(95, "计算绩效...")
        
        result = self._calculate_performance()
        
        run_time = time.time() - start_time
        logger.info(f"✅ 回测完成: 收益={result.total_return:.2%}, 耗时={run_time:.1f}秒")
        
        return result
    
    def _process_signals(self, signals: List[Dict], daily_data: Dict):
        """处理交易信号"""
        for signal in signals:
            stock = signal.get('stock')
            action = signal.get('action')  # buy/sell
            volume = signal.get('volume', 0)
            price = signal.get('price', 0)
            
            if not stock or not action:
                continue
            
            # 获取当日收盘价
            if stock in daily_data and daily_data[stock] is not None:
                close_price = daily_data[stock].get('close', price)
                if price == 0:
                    price = close_price
            
            if action == 'buy':
                self._buy(stock, price, volume)
            elif action == 'sell':
                self._sell(stock, price, volume)
    
    def _buy(self, stock: str, price: float, volume: int):
        """买入"""
        # 计算实际成交价（含滑点）
        actual_price = price * (1 + self.config.slippage)
        cost = actual_price * volume * (1 + self.config.commission_rate)
        
        if cost > self.cash:
            # 资金不足，调整数量
            volume = int(self.cash / (actual_price * (1 + self.config.commission_rate)) / 100) * 100
            if volume <= 0:
                return
            cost = actual_price * volume * (1 + self.config.commission_rate)
        
        self.cash -= cost
        
        # 更新持仓
        if stock in self.positions:
            pos = self.positions[stock]
            new_volume = pos.volume + volume
            pos.cost_price = (pos.cost_price * pos.volume + actual_price * volume) / new_volume
            pos.volume = new_volume
            pos.available = new_volume
            pos.market_value = new_volume * price
        else:
            self.positions[stock] = XtPosition(
                stock_code=stock,
                volume=volume,
                available=volume,
                cost_price=actual_price,
                market_value=volume * price
            )
        
        self.trades.append({
            'date': self.current_date,
            'stock': stock,
            'action': 'buy',
            'price': actual_price,
            'volume': volume,
            'cost': cost
        })
    
    def _sell(self, stock: str, price: float, volume: int):
        """卖出"""
        if stock not in self.positions:
            return
        
        pos = self.positions[stock]
        if volume > pos.available:
            volume = pos.available
        
        if volume <= 0:
            return
        
        # 计算实际成交价（含滑点）
        actual_price = price * (1 - self.config.slippage)
        proceeds = actual_price * volume * (1 - self.config.commission_rate - self.config.stamp_tax)
        
        self.cash += proceeds
        
        # 更新持仓
        pos.volume -= volume
        pos.available -= volume
        pos.market_value = pos.volume * price
        
        if pos.volume <= 0:
            del self.positions[stock]
        
        self.trades.append({
            'date': self.current_date,
            'stock': stock,
            'action': 'sell',
            'price': actual_price,
            'volume': volume,
            'proceeds': proceeds
        })
    
    def _update_positions_value(self, daily_data: Dict):
        """更新持仓市值"""
        for stock, pos in self.positions.items():
            if stock in daily_data and daily_data[stock] is not None:
                close = daily_data[stock].get('close', pos.cost_price)
                pos.market_value = pos.volume * close
    
    def _calculate_performance(self) -> XtBacktestResult:
        """计算绩效指标"""
        import numpy as np
        
        if len(self.equity_history) < 2:
            return self._empty_result()
        
        equity = np.array(self.equity_history)
        initial = self.config.initial_capital
        
        # 总收益率
        total_return = (equity[-1] / initial) - 1
        
        # 日收益率
        daily_returns = np.diff(equity) / equity[:-1]
        
        # 年化收益率
        days = len(daily_returns)
        annual_return = (1 + total_return) ** (252 / max(days, 1)) - 1
        
        # 最大回撤
        cummax = np.maximum.accumulate(equity)
        drawdown = (equity - cummax) / cummax
        max_drawdown = abs(drawdown.min())
        
        # 夏普比率
        rf = 0.02 / 252  # 无风险利率
        sharpe_ratio = (daily_returns.mean() - rf) / (daily_returns.std() + 1e-8) * np.sqrt(252)
        
        # 胜率
        winning_trades = sum(1 for t in self.trades if t.get('action') == 'sell' and 
                           t.get('proceeds', 0) > t.get('cost', 0))
        total_sells = sum(1 for t in self.trades if t.get('action') == 'sell')
        win_rate = winning_trades / max(total_sells, 1)
        
        return XtBacktestResult(
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            trade_count=len(self.trades),
            benchmark_return=0.0,  # TODO: 计算基准收益
            daily_returns=daily_returns.tolist(),
            equity_curve=equity.tolist(),
            trades=self.trades
        )
    
    def _empty_result(self) -> XtBacktestResult:
        """返回空结果"""
        return XtBacktestResult(
            total_return=0, annual_return=0, max_drawdown=0,
            sharpe_ratio=0, win_rate=0, trade_count=0, benchmark_return=0
        )
    
    def _run_mock_backtest(self, strategy_func, on_progress) -> XtBacktestResult:
        """模拟回测（xtquant不可用时）"""
        logger.info("使用模拟回测模式...")
        
        # 生成模拟数据
        import random
        
        days = 252
        equity = [self.config.initial_capital]
        
        for i in range(days):
            # 随机波动
            change = random.gauss(0.0003, 0.015)
            equity.append(equity[-1] * (1 + change))
            
            if on_progress and i % 50 == 0:
                on_progress(50 + int(40 * i / days), f"模拟回测中...")
        
        self.equity_history = equity
        return self._calculate_performance()


class XtLiveTrader:
    """
    xtquant实盘交易接口
    
    连接miniQMT进行实盘交易
    """
    
    def __init__(self, qmt_path: str, account_id: str):
        """
        初始化
        
        Args:
            qmt_path: miniQMT路径
            account_id: 交易账户ID
        """
        self.qmt_path = qmt_path
        self.account_id = account_id
        self.trader = None
        self.account = None
        self.connected = False
    
    def connect(self) -> bool:
        """连接miniQMT"""
        if not XTQUANT_AVAILABLE:
            logger.error("xtquant未安装")
            return False
        
        try:
            # 创建trader
            self.trader = xttrader.XtQuantTrader(self.qmt_path, "TRQuant")
            
            # 启动
            self.trader.start()
            
            # 连接
            result = self.trader.connect()
            if result != 0:
                logger.error(f"连接失败: {result}")
                return False
            
            # 订阅账户
            self.account = StockAccount(self.account_id)
            sub_result = self.trader.subscribe(self.account)
            
            if sub_result != 0:
                logger.error(f"订阅账户失败: {sub_result}")
                return False
            
            self.connected = True
            logger.info(f"✅ 已连接miniQMT: {self.account_id}")
            return True
            
        except Exception as e:
            logger.error(f"连接异常: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.trader:
            self.trader.stop()
            self.connected = False
            logger.info("已断开miniQMT")
    
    def get_positions(self) -> List[XtPosition]:
        """获取持仓"""
        if not self.connected:
            return []
        
        try:
            positions = self.trader.query_stock_positions(self.account)
            return [
                XtPosition(
                    stock_code=p.stock_code,
                    volume=p.volume,
                    available=p.can_use_volume,
                    cost_price=p.open_price,
                    market_value=p.market_value
                )
                for p in positions
            ]
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return []
    
    def buy(self, stock: str, price: float, volume: int) -> Optional[int]:
        """买入"""
        if not self.connected:
            return None
        
        try:
            order_id = self.trader.order_stock(
                self.account,
                stock,
                xttrader.STOCK_BUY,  # 买入
                volume,
                xttrader.PRTP_FIX,   # 限价
                price
            )
            
            if order_id > 0:
                logger.info(f"买入委托成功: {stock} {volume}@{price}, ID={order_id}")
                return order_id
            else:
                logger.error(f"买入委托失败: {order_id}")
                return None
                
        except Exception as e:
            logger.error(f"买入异常: {e}")
            return None
    
    def sell(self, stock: str, price: float, volume: int) -> Optional[int]:
        """卖出"""
        if not self.connected:
            return None
        
        try:
            order_id = self.trader.order_stock(
                self.account,
                stock,
                xttrader.STOCK_SELL,  # 卖出
                volume,
                xttrader.PRTP_FIX,    # 限价
                price
            )
            
            if order_id > 0:
                logger.info(f"卖出委托成功: {stock} {volume}@{price}, ID={order_id}")
                return order_id
            else:
                logger.error(f"卖出委托失败: {order_id}")
                return None
                
        except Exception as e:
            logger.error(f"卖出异常: {e}")
            return None
    
    def cancel_order(self, order_id: int) -> bool:
        """撤单"""
        if not self.connected:
            return False
        
        try:
            result = self.trader.cancel_order_stock(self.account, order_id)
            return result == 0
        except Exception as e:
            logger.error(f"撤单失败: {e}")
            return False


def check_xtquant_status() -> Dict:
    """
    检查xtquant状态
    
    Returns:
        状态信息字典
    """
    status = {
        'installed': XTQUANT_INSTALLED if 'XTQUANT_INSTALLED' in dir() else False,
        'data_available': XTQUANT_DATA_AVAILABLE,
        'trade_available': XTQUANT_TRADE_AVAILABLE,
        'version': None,
        'data_dir': None,
        'can_backtest': False,
        'can_trade': False,
        'message': '',
        'requirements': []
    }
    
    try:
        import xtquant
        status['installed'] = True
        status['version'] = getattr(xtquant, '__version__', 'unknown')
    except ImportError:
        status['message'] = '请运行: pip install xtquant'
        status['requirements'].append('pip install xtquant')
        return status
    
    # 检查数据模块
    if XTQUANT_DATA_AVAILABLE:
        status['can_backtest'] = True
        try:
            status['data_dir'] = xtdata.data_dir
        except:
            pass
    else:
        status['requirements'].append('需要在Windows下运行miniQMT客户端')
    
    # 检查交易模块
    if XTQUANT_TRADE_AVAILABLE:
        status['can_trade'] = True
    else:
        status['requirements'].append('需要miniQMT客户端保持运行')
    
    # 生成状态消息
    if status['can_backtest'] and status['can_trade']:
        status['message'] = '✅ xtquant完全可用，支持回测和实盘交易'
    elif status['can_backtest']:
        status['message'] = '⚠️ xtquant部分可用，仅支持回测'
    elif status['installed']:
        status['message'] = '⚠️ xtquant已安装但需要miniQMT客户端'
        status['requirements'].extend([
            '1. 在券商官网下载QMT客户端',
            '2. 登录QMT时勾选"极简模式"或"独立交易"启动miniQMT',
            '3. 保持miniQMT运行状态',
            '4. 支持的券商：国金、国盛、国信、海通、华鑫等'
        ])
    else:
        status['message'] = '❌ xtquant未安装'
    
    return status


def create_xt_backtest_engine(config: XtBacktestConfig) -> XtBacktestEngine:
    """创建xtquant回测引擎"""
    return XtBacktestEngine(config)

