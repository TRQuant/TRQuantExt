# -*- coding: utf-8 -*-
"""
数据更新调度器
==============

自动定时更新各类数据：
1. 每日收盘后更新行情数据 (15:30)
2. 每日更新板块轮动数据
3. 每周更新财务数据
4. 异常重试机制

遵循时间维度设计原则
"""

import logging
import threading
import time
from datetime import datetime, date, timedelta
from typing import Callable, List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import schedule
import json

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskFrequency(Enum):
    """任务频率"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    HOURLY = "hourly"
    ONCE = "once"


@dataclass
class ScheduledTask:
    """定时任务定义"""
    name: str
    func: Callable
    frequency: TaskFrequency
    time: str  # HH:MM 格式
    enabled: bool = True
    last_run: Optional[datetime] = None
    last_status: TaskStatus = TaskStatus.PENDING
    last_error: str = ""
    retry_count: int = 0
    max_retries: int = 3
    weekday: Optional[int] = None  # 0=Monday, 用于周任务
    day_of_month: Optional[int] = None  # 用于月任务
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)


class DataScheduler:
    """
    数据更新调度器
    
    功能:
    1. 定时执行数据更新任务
    2. 任务失败自动重试
    3. 任务执行状态记录
    4. 支持交易日判断
    """
    
    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._trading_calendar: set = set()
        
        # 注册默认任务
        self._register_default_tasks()
    
    def _register_default_tasks(self):
        """注册默认的数据更新任务"""
        
        # 1. 每日收盘后更新行情数据
        self.add_task(ScheduledTask(
            name="daily_market_data",
            func=self._update_market_data,
            frequency=TaskFrequency.DAILY,
            time="15:35",
            enabled=True
        ))
        
        # 2. 每日更新板块轮动数据
        self.add_task(ScheduledTask(
            name="daily_sector_rotation",
            func=self._update_sector_rotation,
            frequency=TaskFrequency.DAILY,
            time="15:45",
            enabled=True
        ))
        
        # 3. 每日更新北向资金数据
        self.add_task(ScheduledTask(
            name="daily_north_capital",
            func=self._update_north_capital,
            frequency=TaskFrequency.DAILY,
            time="16:00",
            enabled=True
        ))
        
        # 4. 每日更新市场趋势分析
        self.add_task(ScheduledTask(
            name="daily_trend_analysis",
            func=self._update_trend_analysis,
            frequency=TaskFrequency.DAILY,
            time="16:15",
            enabled=True
        ))
        
        # 5. 每周更新财务数据（周六早上）
        self.add_task(ScheduledTask(
            name="weekly_financial_data",
            func=self._update_financial_data,
            frequency=TaskFrequency.WEEKLY,
            time="08:00",
            weekday=5,  # 周六
            enabled=True
        ))
        
        # 6. 每月更新因子库
        self.add_task(ScheduledTask(
            name="monthly_factor_update",
            func=self._update_factor_library,
            frequency=TaskFrequency.MONTHLY,
            time="09:00",
            day_of_month=1,
            enabled=True
        ))
        
        logger.info(f"✅ 已注册 {len(self._tasks)} 个定时任务")
    
    def add_task(self, task: ScheduledTask):
        """添加定时任务"""
        with self._lock:
            self._tasks[task.name] = task
            logger.info(f"📋 注册任务: {task.name} ({task.frequency.value} @ {task.time})")
    
    def remove_task(self, name: str):
        """移除任务"""
        with self._lock:
            if name in self._tasks:
                del self._tasks[name]
                logger.info(f"🗑️ 移除任务: {name}")
    
    def enable_task(self, name: str):
        """启用任务"""
        with self._lock:
            if name in self._tasks:
                self._tasks[name].enabled = True
    
    def disable_task(self, name: str):
        """禁用任务"""
        with self._lock:
            if name in self._tasks:
                self._tasks[name].enabled = False
    
    def get_task_status(self, name: str) -> Optional[Dict]:
        """获取任务状态"""
        task = self._tasks.get(name)
        if task:
            return {
                'name': task.name,
                'enabled': task.enabled,
                'frequency': task.frequency.value,
                'time': task.time,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'last_status': task.last_status.value,
                'last_error': task.last_error,
                'retry_count': task.retry_count
            }
        return None
    
    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务状态"""
        return [self.get_task_status(name) for name in self._tasks]
    
    def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("调度器已在运行")
            return
        
        self._running = True
        self._setup_schedule()
        
        # 启动后台线程
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
        logger.info("🚀 数据调度器已启动")
    
    def stop(self):
        """停止调度器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        schedule.clear()
        logger.info("🛑 数据调度器已停止")
    
    def _setup_schedule(self):
        """设置调度计划"""
        schedule.clear()
        
        for name, task in self._tasks.items():
            if not task.enabled:
                continue
            
            if task.frequency == TaskFrequency.DAILY:
                schedule.every().day.at(task.time).do(self._execute_task, name)
            elif task.frequency == TaskFrequency.WEEKLY:
                weekday = task.weekday or 0
                weekday_name = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'][weekday]
                getattr(schedule.every(), weekday_name).at(task.time).do(self._execute_task, name)
            elif task.frequency == TaskFrequency.MONTHLY:
                # schedule库不直接支持月任务，使用每日检查
                schedule.every().day.at(task.time).do(self._check_monthly_task, name)
            elif task.frequency == TaskFrequency.HOURLY:
                schedule.every().hour.at(f":{task.time.split(':')[1]}").do(self._execute_task, name)
    
    def _run_loop(self):
        """后台运行循环"""
        while self._running:
            try:
                schedule.run_pending()
                time.sleep(30)  # 每30秒检查一次
            except Exception as e:
                logger.error(f"调度器错误: {e}")
                time.sleep(60)
    
    def _check_monthly_task(self, name: str):
        """检查月任务是否应该执行"""
        task = self._tasks.get(name)
        if task and task.day_of_month:
            today = date.today()
            if today.day == task.day_of_month:
                self._execute_task(name)
    
    def _execute_task(self, name: str):
        """执行任务"""
        task = self._tasks.get(name)
        if not task or not task.enabled:
            return
        
        # 检查是否是交易日（对于市场数据任务）
        if name.startswith('daily_') and not self._is_trading_day():
            task.last_status = TaskStatus.SKIPPED
            logger.info(f"⏭️ 跳过非交易日任务: {name}")
            return
        
        logger.info(f"▶️ 开始执行任务: {name}")
        task.last_status = TaskStatus.RUNNING
        task.last_run = datetime.now()
        
        try:
            task.func(*task.args, **task.kwargs)
            task.last_status = TaskStatus.SUCCESS
            task.last_error = ""
            task.retry_count = 0
            logger.info(f"✅ 任务完成: {name}")
            
            # 记录到数据库
            self._log_task_execution(task, success=True)
            
        except Exception as e:
            task.last_status = TaskStatus.FAILED
            task.last_error = str(e)
            task.retry_count += 1
            logger.error(f"❌ 任务失败: {name} - {e}")
            
            # 重试逻辑
            if task.retry_count < task.max_retries:
                logger.info(f"🔄 将在5分钟后重试 ({task.retry_count}/{task.max_retries})")
                schedule.every(5).minutes.do(self._retry_task, name).tag(f'retry_{name}')
            
            # 记录到数据库
            self._log_task_execution(task, success=False, error=str(e))
    
    def _retry_task(self, name: str):
        """重试任务"""
        # 移除重试调度
        schedule.clear(f'retry_{name}')
        self._execute_task(name)
    
    def _is_trading_day(self) -> bool:
        """判断今天是否是交易日"""
        today = date.today()
        
        # 周末不交易
        if today.weekday() >= 5:
            return False
        
        # 如果有交易日历，使用交易日历
        if self._trading_calendar:
            return today in self._trading_calendar
        
        # 默认周一到周五都是交易日（简化处理）
        return True
    
    def _log_task_execution(self, task: ScheduledTask, success: bool, error: str = ""):
        """记录任务执行日志到MongoDB"""
        try:
            from pymongo import MongoClient
            
            client = MongoClient('mongodb://localhost:27017')
            db = client.jqquant
            collection = db.task_logs
            
            log_entry = {
                'task_name': task.name,
                'executed_at': task.last_run.isoformat() if task.last_run else None,
                'status': 'success' if success else 'failed',
                'error': error,
                'retry_count': task.retry_count
            }
            
            collection.insert_one(log_entry)
            
        except Exception as e:
            logger.debug(f"记录任务日志失败: {e}")
    
    # ========== 具体的数据更新任务 ==========
    
    def _update_market_data(self):
        """更新市场行情数据"""
        logger.info("📈 开始更新市场行情数据...")
        
        try:
            from core.data_source_manager import get_data_source_manager
            
            manager = get_data_source_manager()
            today = date.today().strftime('%Y-%m-%d')
            
            # 获取主要指数数据
            indices = ['000001.XSHG', '399001.XSHE', '399006.XSHE', '000300.XSHG']
            for idx in indices:
                result = manager.get_price(idx, today, today)
                if result.success:
                    manager.save_to_cache(idx, result.data)
                    logger.info(f"   ✅ {idx} 已更新")
            
            logger.info("📈 市场行情数据更新完成")
            
        except Exception as e:
            logger.error(f"市场行情更新失败: {e}")
            raise
    
    def _update_sector_rotation(self):
        """更新板块轮动数据"""
        logger.info("🔄 开始更新板块轮动数据...")
        
        try:
            from core.rotation_analyzer import create_rotation_analyzer
            
            analyzer = create_rotation_analyzer()
            result = analyzer.analyze_rotation(days=5)
            
            if result:
                # 保存到MongoDB
                from pymongo import MongoClient
                client = MongoClient('mongodb://localhost:27017')
                db = client.jqquant
                
                doc = {
                    'date': result.analysis_date,
                    'rising_count': len(result.rising_sectors),
                    'falling_count': len(result.falling_sectors),
                    'summary': result.rotation_summary,
                    'data_source': result.data_source,
                    'rising_sectors': [
                        {'name': s.sector_name, 'change': s.current_change_pct, 'heat': s.heat_score}
                        for s in result.rising_sectors[:10]
                    ],
                    'falling_sectors': [
                        {'name': s.sector_name, 'change': s.current_change_pct, 'heat': s.heat_score}
                        for s in result.falling_sectors[:10]
                    ]
                }
                
                db.sector_rotation.update_one(
                    {'date': result.analysis_date[:10]},
                    {'$set': doc},
                    upsert=True
                )
                
                logger.info(f"🔄 板块轮动数据已更新: 升温{len(result.rising_sectors)}个")
            
        except Exception as e:
            logger.error(f"板块轮动更新失败: {e}")
            raise
    
    def _update_north_capital(self):
        """更新北向资金数据"""
        logger.info("💰 开始更新北向资金数据...")
        
        try:
            from core.capital_flow import CapitalFlowAnalyzer
            
            analyzer = CapitalFlowAnalyzer()
            result = analyzer.analyze_capital_flow()
            
            if result:
                from pymongo import MongoClient
                client = MongoClient('mongodb://localhost:27017')
                db = client.jqquant
                
                doc = {
                    'date': date.today().strftime('%Y-%m-%d'),
                    'flow_score': result.flow_score,
                    'flow_trend': result.flow_trend,
                    'signal': result.signal,
                    'details': result.details
                }
                
                db.capital_flow.update_one(
                    {'date': doc['date']},
                    {'$set': doc},
                    upsert=True
                )
                
                logger.info(f"💰 北向资金数据已更新: {result.flow_trend}")
            
        except Exception as e:
            logger.error(f"北向资金更新失败: {e}")
            raise
    
    def _update_trend_analysis(self):
        """更新市场趋势分析"""
        logger.info("📊 开始更新市场趋势分析...")
        
        try:
            from core.trend_analyzer import TrendAnalyzer
            
            analyzer = TrendAnalyzer()
            result = analyzer.analyze_market('000001.XSHG')
            
            if result:
                from pymongo import MongoClient
                client = MongoClient('mongodb://localhost:27017')
                db = client.jqquant
                
                doc = {
                    'date': date.today().strftime('%Y-%m-%d'),
                    'short_term': {
                        'score': result.short_term.score,
                        'direction': result.short_term.direction.value,
                        'confidence': result.short_term.confidence
                    },
                    'medium_term': {
                        'score': result.medium_term.score,
                        'direction': result.medium_term.direction.value,
                        'confidence': result.medium_term.confidence
                    },
                    'long_term': {
                        'score': result.long_term.score,
                        'direction': result.long_term.direction.value,
                        'confidence': result.long_term.confidence
                    },
                    'market_phase': result.market_phase,
                    'composite_score': result.composite_score
                }
                
                db.trend_analysis.update_one(
                    {'date': doc['date']},
                    {'$set': doc},
                    upsert=True
                )
                
                logger.info(f"📊 趋势分析已更新: {result.market_phase}")
            
        except Exception as e:
            logger.error(f"趋势分析更新失败: {e}")
            raise
    
    def _update_financial_data(self):
        """更新财务数据（周任务）"""
        logger.info("📑 开始更新财务数据...")
        
        try:
            # 财务数据更新逻辑
            # 由于JQData试用账户限制，这里使用AKShare获取基础财务数据
            import akshare as ak
            from pymongo import MongoClient
            
            client = MongoClient('mongodb://localhost:27017')
            db = client.jqquant
            
            # 获取A股公司基本信息
            try:
                df = ak.stock_info_a_code_name()
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        doc = {
                            'code': row.get('code', ''),
                            'name': row.get('name', ''),
                            'updated_at': datetime.now().isoformat()
                        }
                        db.stock_info.update_one(
                            {'code': doc['code']},
                            {'$set': doc},
                            upsert=True
                        )
                    
                    logger.info(f"📑 已更新 {len(df)} 只股票基本信息")
            except:
                pass
            
            logger.info("📑 财务数据更新完成")
            
        except Exception as e:
            logger.error(f"财务数据更新失败: {e}")
            raise
    
    def _update_factor_library(self):
        """更新因子库（月任务）"""
        logger.info("🧮 开始更新因子库...")
        
        try:
            from core.factors.factor_pipeline import FactorPipeline
            
            pipeline = FactorPipeline()
            # 运行月度评估
            pipeline.run_monthly_evaluation()
            
            logger.info("🧮 因子库更新完成")
            
        except Exception as e:
            logger.error(f"因子库更新失败: {e}")
            raise
    
    def run_task_now(self, name: str):
        """立即执行指定任务"""
        if name in self._tasks:
            self._execute_task(name)
        else:
            logger.warning(f"任务不存在: {name}")


# 全局调度器实例
_scheduler_instance: Optional[DataScheduler] = None


def get_data_scheduler() -> DataScheduler:
    """获取数据调度器单例"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = DataScheduler()
    return _scheduler_instance

