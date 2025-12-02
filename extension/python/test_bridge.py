#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bridge模块测试
==============

运行方式：
    python test_bridge.py

测试内容：
    - health_check
    - get_market_status
    - get_mainlines
    - recommend_factors
    - generate_strategy (PTrade & QMT)
"""

import sys
import json
import subprocess
from pathlib import Path

# 测试用例
TEST_CASES = [
    {
        "name": "健康检查",
        "action": "health_check",
        "params": {}
    },
    {
        "name": "获取市场状态",
        "action": "get_market_status",
        "params": {"universe": "CN_EQ"}
    },
    {
        "name": "获取投资主线",
        "action": "get_mainlines",
        "params": {"top_n": 5}
    },
    {
        "name": "推荐因子",
        "action": "recommend_factors",
        "params": {"market_regime": "risk_on"}
    },
    {
        "name": "生成PTrade策略",
        "action": "generate_strategy",
        "params": {
            "platform": "ptrade",
            "style": "multi_factor",
            "factors": ["ROE_ttm", "momentum_20d"],
            "risk_params": {
                "max_position": 0.1,
                "stop_loss": 0.08,
                "take_profit": 0.2
            }
        }
    },
    {
        "name": "生成QMT策略",
        "action": "generate_strategy",
        "params": {
            "platform": "qmt",
            "style": "momentum_growth",
            "factors": ["revenue_growth", "momentum_20d"],
            "risk_params": {
                "max_position": 0.1,
                "stop_loss": 0.08,
                "take_profit": 0.2
            }
        }
    }
]


def run_test(test_case: dict) -> tuple:
    """运行单个测试"""
    request = json.dumps({
        "action": test_case["action"],
        "params": test_case["params"]
    })
    
    try:
        # 直接导入并调用
        from bridge import ACTIONS
        
        action = test_case["action"]
        params = test_case["params"]
        
        if action not in ACTIONS:
            return False, f"未知动作: {action}"
        
        result = ACTIONS[action](params)
        
        if not result.get("ok"):
            return False, result.get("error", "未知错误")
        
        return True, result.get("data")
        
    except Exception as e:
        return False, str(e)


def main():
    """主函数"""
    print("=" * 60)
    print("TRQuant Bridge 测试")
    print("=" * 60)
    print()
    
    passed = 0
    failed = 0
    
    for test in TEST_CASES:
        print(f"测试: {test['name']}")
        print(f"  动作: {test['action']}")
        
        success, result = run_test(test)
        
        if success:
            print(f"  ✅ 通过")
            if isinstance(result, dict):
                # 只显示关键信息
                if 'code' in result:
                    print(f"     代码长度: {len(result['code'])} 字符")
                elif 'regime' in result:
                    print(f"     市场Regime: {result['regime']}")
                elif 'status' in result:
                    print(f"     状态: {result['status']}")
            elif isinstance(result, list):
                print(f"     返回 {len(result)} 条记录")
            passed += 1
        else:
            print(f"  ❌ 失败: {result}")
            failed += 1
        
        print()
    
    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

