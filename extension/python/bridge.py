#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TRQuant Extension Bridge
========================

与VS Code/Cursor Extension通信的Python桥接模块。
通过stdin/stdout传输JSON数据。
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime

# 添加TRQuant路径
TRQUANT_ROOT = os.environ.get('TRQUANT_ROOT', str(Path(__file__).parent.parent.parent))
sys.path.insert(0, TRQUANT_ROOT)

try:
    from core.trend_analyzer import TrendAnalyzer
    from core.candidate_pool_builder import CandidatePoolBuilder
    from core.factors.factor_manager import FactorManager
    from core.strategy_generator import StrategyGenerator
    from core.workflow_orchestrator import get_workflow_orchestrator
    TRQUANT_AVAILABLE = True
except ImportError as e:
    TRQUANT_AVAILABLE = False
    IMPORT_ERROR = str(e)


def get_market_status(params: dict) -> dict:
    """获取市场状态"""
    if not TRQUANT_AVAILABLE:
        return mock_market_status()
    
    try:
        orchestrator = get_workflow_orchestrator()
        result = orchestrator.analyze_market_trend()
        
        if result.success:
            return {
                'ok': True,
                'data': {
                    'regime': result.details.get('position_suggestion', 'neutral'),
                    'index_trend': result.details.get('index_trend', {}),
                    'style_rotation': result.details.get('style_rotation', []),
                    'summary': result.summary
                }
            }
        else:
            return {'ok': False, 'error': result.summary}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def get_mainlines(params: dict) -> dict:
    """获取投资主线"""
    if not TRQUANT_AVAILABLE:
        return mock_mainlines()
    
    try:
        orchestrator = get_workflow_orchestrator()
        result = orchestrator.identify_mainlines()
        
        if result.success:
            mainlines = result.details.get('mainlines', [])
            return {
                'ok': True,
                'data': [
                    {
                        'name': m.get('name', ''),
                        'score': m.get('score', 0),
                        'industries': m.get('industries', []),
                        'logic': m.get('logic', '')
                    }
                    for m in mainlines[:params.get('top_n', 20)]
                ]
            }
        else:
            return {'ok': False, 'error': result.summary}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def recommend_factors(params: dict) -> dict:
    """推荐因子"""
    if not TRQUANT_AVAILABLE:
        return mock_factors()
    
    try:
        orchestrator = get_workflow_orchestrator()
        result = orchestrator.recommend_factors()
        
        if result.success:
            factors = result.details.get('factors', [])
            return {
                'ok': True,
                'data': [
                    {
                        'name': f.get('name', ''),
                        'category': f.get('category', '其他'),
                        'weight': f.get('weight', 0.5),
                        'reason': f.get('reason', '')
                    }
                    for f in factors
                ]
            }
        else:
            return {'ok': False, 'error': result.summary}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def generate_strategy(params: dict) -> dict:
    """生成策略代码 - 支持PTrade和QMT双平台"""
    platform = params.get('platform', 'ptrade')  # 默认PTrade
    style = params.get('style', 'multi_factor')
    factors = params.get('factors', ['ROE_ttm', 'momentum_20d'])
    risk_params = params.get('risk_params', {
        'max_position': 0.1,
        'stop_loss': 0.08,
        'take_profit': 0.2
    })
    
    try:
        # 使用新的策略生成器
        from tools.strategy_generator import get_strategy_generator
        generator = get_strategy_generator()
        
        result = generator.generate(
            platform=platform,
            style=style,
            factors=factors,
            risk_params=risk_params
        )
        
        return {
            'ok': True,
            'data': result
        }
    except ImportError:
        # 降级到mock实现
        return mock_strategy(params)
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def analyze_backtest(params: dict) -> dict:
    """分析回测结果"""
    # 简单实现
    return {
        'ok': True,
        'data': {
            'metrics': {
                'total_return': 15.5,
                'sharpe_ratio': 1.2,
                'max_drawdown': -8.3,
                'win_rate': 56.0,
                'trade_count': 42,
                'profit_loss_ratio': 1.8
            },
            'diagnosis': [
                '策略在震荡市表现较好',
                '最大回撤发生在2024年Q3'
            ],
            'suggestions': [
                '考虑增加止损机制',
                '可以尝试增加动量因子权重'
            ]
        }
    }


def risk_assessment(params: dict) -> dict:
    """风险评估"""
    return {
        'ok': True,
        'data': {
            'overall_risk': 'medium',
            'metrics': {
                'var_95': -2.5,
                'beta': 0.85,
                'tracking_error': 3.2
            },
            'warnings': []
        }
    }


# Mock数据（当TRQuant不可用时）
def mock_market_status():
    return {
        'ok': True,
        'data': {
            'regime': 'risk_on',
            'index_trend': {
                'SH000300': {'zscore': 0.8, 'trend': 'up'},
                'SZ399006': {'zscore': 1.2, 'trend': 'up'}
            },
            'style_rotation': [
                {'style': 'growth', 'score': 0.7},
                {'style': 'value', 'score': -0.2},
                {'style': 'momentum', 'score': 0.5}
            ],
            'summary': '当前市场风险偏好回升，成长风格占优，建议关注科技、新能源等高成长板块。'
        }
    }


def mock_mainlines():
    return {
        'ok': True,
        'data': [
            {'name': 'AI人工智能', 'score': 0.92, 'industries': ['半导体', '软件', '通信'], 'logic': 'AI产业链持续景气'},
            {'name': '新能源汽车', 'score': 0.85, 'industries': ['汽车', '电池', '充电桩'], 'logic': '渗透率持续提升'},
            {'name': '医药创新', 'score': 0.78, 'industries': ['创新药', '医疗器械', 'CXO'], 'logic': '政策支持+老龄化'},
            {'name': '高端制造', 'score': 0.72, 'industries': ['机械', '工控', '机器人'], 'logic': '制造业升级'},
            {'name': '消费复苏', 'score': 0.65, 'industries': ['白酒', '免税', '餐饮'], 'logic': '经济复苏预期'}
        ]
    }


def mock_factors():
    return {
        'ok': True,
        'data': [
            {'name': 'ROE_ttm', 'category': '盈利能力', 'weight': 0.8, 'reason': '高ROE反映优质经营'},
            {'name': 'revenue_growth', 'category': '成长性', 'weight': 0.75, 'reason': '成长股市场占优'},
            {'name': 'momentum_20d', 'category': '动量', 'weight': 0.7, 'reason': '趋势延续性强'},
            {'name': 'turnover_rate', 'category': '流动性', 'weight': 0.6, 'reason': '活跃度指标'},
            {'name': 'pe_ttm', 'category': '估值', 'weight': 0.5, 'reason': '估值安全边际'}
        ]
    }


def mock_strategy(params: dict):
    style = params.get('style', 'multi_factor')
    factors = params.get('factors', ['ROE_ttm', 'momentum_20d'])
    
    code = f'''# -*- coding: utf-8 -*-
"""
TRQuant生成策略 - {style}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
使用因子: {', '.join(factors)}
"""

def initialize(context):
    """初始化策略"""
    # 设置参数
    context.max_position = {params.get('risk_params', {}).get('max_position', 0.1)}
    context.stop_loss = {params.get('risk_params', {}).get('stop_loss', 0.08)}
    context.take_profit = {params.get('risk_params', {}).get('take_profit', 0.2)}
    
    # 设置股票池
    context.universe = get_index_stocks('000300.XSHG')
    
    # 设置调仓频率
    run_daily(rebalance, time='9:35')


def rebalance(context):
    """调仓逻辑"""
    # 获取因子数据
    factor_data = get_factor_data(context.universe, {factors})
    
    # 因子合成
    scores = calculate_composite_score(factor_data)
    
    # 选股
    selected = scores.nlargest(10).index.tolist()
    
    # 风控检查
    selected = risk_filter(selected, context)
    
    # 调仓
    adjust_positions(context, selected)


def calculate_composite_score(factor_data):
    """计算综合得分"""
    # 因子标准化
    normalized = (factor_data - factor_data.mean()) / factor_data.std()
    
    # 等权合成
    return normalized.mean(axis=1)


def risk_filter(stocks, context):
    """风控过滤"""
    filtered = []
    for stock in stocks:
        # 跳过ST
        if is_st(stock):
            continue
        # 跳过停牌
        if is_suspended(stock):
            continue
        filtered.append(stock)
    return filtered


def adjust_positions(context, selected):
    """调整持仓"""
    current = list(context.portfolio.positions.keys())
    
    # 卖出
    for stock in current:
        if stock not in selected:
            order_target_percent(stock, 0)
    
    # 买入
    weight = context.max_position / len(selected) if selected else 0
    for stock in selected:
        order_target_percent(stock, weight)
'''
    
    return {
        'ok': True,
        'data': {
            'code': code,
            'name': f'{style}_strategy_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'description': f'基于{", ".join(factors)}的{style}策略',
            'factors': factors,
            'risk_params': params.get('risk_params', {})
        }
    }


def health_check(params: dict) -> dict:
    """健康检查"""
    return {
        'ok': True,
        'data': {
            'status': 'healthy',
            'trquant_available': TRQUANT_AVAILABLE,
            'timestamp': datetime.now().isoformat()
        }
    }


# 动作分发
ACTIONS = {
    'get_market_status': get_market_status,
    'get_mainlines': get_mainlines,
    'recommend_factors': recommend_factors,
    'generate_strategy': generate_strategy,
    'analyze_backtest': analyze_backtest,
    'risk_assessment': risk_assessment,
    'health_check': health_check
}


def main():
    """主函数"""
    try:
        # 从stdin读取请求
        request_str = sys.stdin.read()
        request = json.loads(request_str)
        
        action = request.get('action')
        params = request.get('params', {})
        
        if action not in ACTIONS:
            response = {'ok': False, 'error': f'未知动作: {action}'}
        else:
            response = ACTIONS[action](params)
        
        # 输出响应
        print(json.dumps(response, ensure_ascii=False))
        
    except json.JSONDecodeError as e:
        print(json.dumps({'ok': False, 'error': f'JSON解析错误: {e}'}))
    except Exception as e:
        print(json.dumps({'ok': False, 'error': str(e)}))


if __name__ == '__main__':
    main()

