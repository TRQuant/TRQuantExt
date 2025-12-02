# -*- coding: utf-8 -*-
"""
策略生成器
==========

功能:
1. 多因子选股策略模板生成
2. 调仓逻辑配置
3. 止损止盈规则
4. 交易成本设置
5. 生成PTrade/QMT可执行代码
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Optional, Any
from enum import Enum
import json

logger = logging.getLogger(__name__)


class RebalanceFreq(Enum):
    """调仓频率"""
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class StopLossType(Enum):
    """止损类型"""
    FIXED = "fixed"           # 固定比例止损
    TRAILING = "trailing"     # 移动止损
    ATR = "atr"              # ATR止损
    NONE = "none"            # 不止损


class TakeProfitType(Enum):
    """止盈类型"""
    FIXED = "fixed"           # 固定比例止盈
    TRAILING = "trailing"     # 移动止盈
    TARGET = "target"         # 目标价止盈
    NONE = "none"            # 不止盈


@dataclass
class FactorConfig:
    """因子配置"""
    factor_id: str
    factor_name: str
    weight: float
    direction: str = "positive"  # positive/negative
    neutralize: bool = False     # 是否中性化


@dataclass
class RebalanceConfig:
    """调仓配置"""
    frequency: RebalanceFreq = RebalanceFreq.MONTHLY
    rebalance_day: int = 1       # 月调仓日期
    rebalance_weekday: int = 0   # 周调仓日（0=周一）
    position_limit: int = 20     # 最大持仓数
    single_stock_limit: float = 0.10  # 单只股票最大仓位


@dataclass
class StopLossConfig:
    """止损配置"""
    type: StopLossType = StopLossType.FIXED
    threshold: float = 0.08     # 止损阈值
    trailing_step: float = 0.05 # 移动止损步长
    atr_multiplier: float = 2.0 # ATR倍数


@dataclass
class TakeProfitConfig:
    """止盈配置"""
    type: TakeProfitType = TakeProfitType.FIXED
    threshold: float = 0.20     # 止盈阈值
    trailing_step: float = 0.05 # 移动止盈步长


@dataclass
class CostConfig:
    """交易成本配置"""
    commission_rate: float = 0.0003  # 佣金率 (双边)
    stamp_tax_rate: float = 0.001    # 印花税 (卖出)
    slippage: float = 0.001          # 滑点


@dataclass
class StrategyConfig:
    """策略配置"""
    name: str
    description: str = ""
    factors: List[FactorConfig] = field(default_factory=list)
    rebalance: RebalanceConfig = field(default_factory=RebalanceConfig)
    stop_loss: StopLossConfig = field(default_factory=StopLossConfig)
    take_profit: TakeProfitConfig = field(default_factory=TakeProfitConfig)
    cost: CostConfig = field(default_factory=CostConfig)
    benchmark: str = "000300.XSHG"  # 基准指数
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'description': self.description,
            'factors': [
                {'id': f.factor_id, 'name': f.factor_name, 'weight': f.weight, 
                 'direction': f.direction, 'neutralize': f.neutralize}
                for f in self.factors
            ],
            'rebalance': {
                'frequency': self.rebalance.frequency.value,
                'position_limit': self.rebalance.position_limit,
                'single_stock_limit': self.rebalance.single_stock_limit
            },
            'stop_loss': {
                'type': self.stop_loss.type.value,
                'threshold': self.stop_loss.threshold
            },
            'take_profit': {
                'type': self.take_profit.type.value,
                'threshold': self.take_profit.threshold
            },
            'cost': {
                'commission': self.cost.commission_rate,
                'stamp_tax': self.cost.stamp_tax_rate,
                'slippage': self.cost.slippage
            },
            'benchmark': self.benchmark
        }


class StrategyGenerator:
    """策略生成器"""
    
    def __init__(self):
        self._templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, StrategyConfig]:
        """加载预设模板"""
        templates = {}
        
        # 价值成长策略
        templates['value_growth'] = StrategyConfig(
            name="价值成长策略",
            description="结合低估值和高成长选股，适合牛市",
            factors=[
                FactorConfig("ep", "市盈率倒数", 0.3, "positive"),
                FactorConfig("roe", "净资产收益率", 0.25, "positive"),
                FactorConfig("profit_growth", "净利润增长率", 0.25, "positive"),
                FactorConfig("momentum_1m", "1月动量", 0.2, "positive"),
            ],
            rebalance=RebalanceConfig(
                frequency=RebalanceFreq.MONTHLY,
                position_limit=20,
                single_stock_limit=0.10
            ),
            stop_loss=StopLossConfig(type=StopLossType.TRAILING, threshold=0.08),
            take_profit=TakeProfitConfig(type=TakeProfitType.TRAILING, threshold=0.30)
        )
        
        # 动量策略
        templates['momentum'] = StrategyConfig(
            name="动量策略",
            description="追涨强势股，适合趋势市",
            factors=[
                FactorConfig("momentum_1m", "1月动量", 0.4, "positive"),
                FactorConfig("momentum_3m", "3月动量", 0.3, "positive"),
                FactorConfig("volume_ratio", "量比", 0.15, "positive"),
                FactorConfig("rsi", "RSI", 0.15, "positive"),
            ],
            rebalance=RebalanceConfig(
                frequency=RebalanceFreq.WEEKLY,
                position_limit=15,
                single_stock_limit=0.08
            ),
            stop_loss=StopLossConfig(type=StopLossType.FIXED, threshold=0.05),
            take_profit=TakeProfitConfig(type=TakeProfitType.TRAILING, threshold=0.15)
        )
        
        # 低波动价值策略
        templates['low_vol_value'] = StrategyConfig(
            name="低波动价值策略",
            description="低波动+高股息，适合熊市防守",
            factors=[
                FactorConfig("volatility", "波动率", 0.3, "negative"),
                FactorConfig("dividend_yield", "股息率", 0.3, "positive"),
                FactorConfig("ep", "市盈率倒数", 0.25, "positive"),
                FactorConfig("roe", "净资产收益率", 0.15, "positive"),
            ],
            rebalance=RebalanceConfig(
                frequency=RebalanceFreq.QUARTERLY,
                position_limit=30,
                single_stock_limit=0.05
            ),
            stop_loss=StopLossConfig(type=StopLossType.FIXED, threshold=0.10),
            take_profit=TakeProfitConfig(type=TakeProfitType.FIXED, threshold=0.25)
        )
        
        # 质量成长策略
        templates['quality_growth'] = StrategyConfig(
            name="质量成长策略",
            description="高质量+高成长，适合震荡市",
            factors=[
                FactorConfig("roe", "净资产收益率", 0.3, "positive"),
                FactorConfig("profit_growth", "净利润增长率", 0.25, "positive"),
                FactorConfig("revenue_growth", "营收增长率", 0.2, "positive"),
                FactorConfig("gross_margin", "毛利率", 0.15, "positive"),
                FactorConfig("debt_ratio", "资产负债率", 0.1, "negative"),
            ],
            rebalance=RebalanceConfig(
                frequency=RebalanceFreq.MONTHLY,
                position_limit=25,
                single_stock_limit=0.08
            ),
            stop_loss=StopLossConfig(type=StopLossType.TRAILING, threshold=0.08),
            take_profit=TakeProfitConfig(type=TakeProfitType.TRAILING, threshold=0.25)
        )
        
        return templates
    
    def get_templates(self) -> List[Dict]:
        """获取所有模板列表"""
        return [
            {
                'id': tid,
                'name': t.name,
                'description': t.description,
                'factors_count': len(t.factors),
                'rebalance_freq': t.rebalance.frequency.value
            }
            for tid, t in self._templates.items()
        ]
    
    def get_template(self, template_id: str) -> Optional[StrategyConfig]:
        """获取指定模板"""
        return self._templates.get(template_id)
    
    def create_strategy(self, config: StrategyConfig) -> str:
        """
        生成策略代码
        
        Args:
            config: 策略配置
        
        Returns:
            PTrade格式策略代码
        """
        factors_code = self._generate_factors_code(config.factors)
        rebalance_code = self._generate_rebalance_code(config.rebalance)
        risk_code = self._generate_risk_code(config.stop_loss, config.take_profit)
        
        code = f'''# -*- coding: utf-8 -*-
"""
{config.name}
=============
{config.description}

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
生成工具: 韬睿量化策略生成器
"""

# ======== 初始化 ========
def initialize(context):
    """策略初始化"""
    # 设置基准
    set_benchmark("{config.benchmark}")
    
    # 设置佣金和滑点
    set_commission(PerTrade(buy_cost={config.cost.commission_rate}, sell_cost={config.cost.commission_rate + config.cost.stamp_tax_rate}))
    set_slippage(FixedSlippage({config.cost.slippage}))
    
    # 策略参数
    context.position_limit = {config.rebalance.position_limit}
    context.single_stock_limit = {config.rebalance.single_stock_limit}
    context.stop_loss_threshold = {config.stop_loss.threshold}
    context.take_profit_threshold = {config.take_profit.threshold}
    
    # 设置调仓频率
{rebalance_code}

# ======== 因子计算 ========
{factors_code}

# ======== 选股逻辑 ========
def select_stocks(context):
    """选股逻辑"""
    # 获取股票池
    stocks = get_index_stocks("{config.benchmark}")
    
    # 计算综合因子得分
    scores = {{}}
    for stock in stocks:
        try:
            score = calculate_factor_score(stock, context)
            scores[stock] = score
        except:
            continue
    
    # 按得分排序
    sorted_stocks = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    # 取前N只
    selected = [s[0] for s in sorted_stocks[:context.position_limit]]
    
    return selected

# ======== 调仓逻辑 ========
def rebalance(context):
    """调仓函数"""
    # 获取目标股票
    target_stocks = select_stocks(context)
    
    # 计算每只股票的目标仓位
    weight = 1.0 / len(target_stocks) if target_stocks else 0
    weight = min(weight, context.single_stock_limit)
    
    # 获取当前持仓
    current_holdings = set(context.portfolio.positions.keys())
    target_set = set(target_stocks)
    
    # 卖出不在目标中的股票
    for stock in current_holdings - target_set:
        order_target_value(stock, 0)
    
    # 买入目标股票
    for stock in target_stocks:
        order_target_percent(stock, weight)
    
    log.info(f"调仓完成: 持有{{len(target_stocks)}}只股票")

# ======== 风险控制 ========
{risk_code}

# ======== 每日运行 ========
def handle_data(context, data):
    """每日运行"""
    # 检查止损止盈
    check_stop_loss_take_profit(context)
'''
        
        return code
    
    def _generate_factors_code(self, factors: List[FactorConfig]) -> str:
        """生成因子计算代码"""
        code_lines = []
        code_lines.append("def calculate_factor_score(stock, context):")
        code_lines.append('    """计算因子综合得分"""')
        code_lines.append("    score = 0.0")
        code_lines.append("")
        
        for f in factors:
            direction = "1" if f.direction == "positive" else "-1"
            code_lines.append(f"    # {f.factor_name} (权重: {f.weight})")
            code_lines.append(f"    try:")
            code_lines.append(f"        {f.factor_id}_value = get_{f.factor_id}(stock)")
            code_lines.append(f"        score += {f.weight} * {direction} * normalize({f.factor_id}_value)")
            code_lines.append(f"    except:")
            code_lines.append(f"        pass")
            code_lines.append("")
        
        code_lines.append("    return score")
        code_lines.append("")
        code_lines.append("def normalize(value):")
        code_lines.append('    """标准化到0-1"""')
        code_lines.append("    # 简单的Min-Max标准化，实际应使用历史数据")
        code_lines.append("    return max(0, min(1, value))")
        
        return "\n".join(code_lines)
    
    def _generate_rebalance_code(self, config: RebalanceConfig) -> str:
        """生成调仓代码"""
        freq_map = {
            RebalanceFreq.DAILY: "run_daily(rebalance, time='14:30')",
            RebalanceFreq.WEEKLY: f"run_weekly(rebalance, weekday={config.rebalance_weekday}, time='14:30')",
            RebalanceFreq.BIWEEKLY: f"run_weekly(rebalance, weekday={config.rebalance_weekday}, time='14:30')  # 每两周调仓需手动控制",
            RebalanceFreq.MONTHLY: f"run_monthly(rebalance, tradingday={config.rebalance_day}, time='14:30')",
            RebalanceFreq.QUARTERLY: f"run_monthly(rebalance, tradingday={config.rebalance_day}, time='14:30')  # 季度调仓在handle_data中控制",
        }
        
        return f"    {freq_map.get(config.frequency, freq_map[RebalanceFreq.MONTHLY])}"
    
    def _generate_risk_code(self, stop_loss: StopLossConfig, take_profit: TakeProfitConfig) -> str:
        """生成风控代码"""
        code = '''def check_stop_loss_take_profit(context):
    """检查止损止盈"""
    for stock, position in context.portfolio.positions.items():
        if position.amount <= 0:
            continue
        
        # 计算收益率
        cost = position.avg_cost
        current = position.price
        pnl_rate = (current - cost) / cost if cost > 0 else 0
        
'''
        
        if stop_loss.type != StopLossType.NONE:
            code += f'''        # 止损检查
        if pnl_rate < -{stop_loss.threshold}:
            order_target_value(stock, 0)
            log.info(f"止损卖出 {{stock}}: 收益率 {{pnl_rate:.2%}}")
            continue
        
'''
        
        if take_profit.type != TakeProfitType.NONE:
            code += f'''        # 止盈检查
        if pnl_rate > {take_profit.threshold}:
            order_target_value(stock, 0)
            log.info(f"止盈卖出 {{stock}}: 收益率 {{pnl_rate:.2%}}")
'''
        
        return code
    
    def save_strategy(self, config: StrategyConfig, file_path: str) -> bool:
        """保存策略到文件"""
        try:
            code = self.create_strategy(config)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            logger.info(f"策略已保存: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存策略失败: {e}")
            return False


# 单例
_generator = None

def get_strategy_generator() -> StrategyGenerator:
    global _generator
    if _generator is None:
        _generator = StrategyGenerator()
    return _generator

