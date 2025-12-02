#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MCP Server测试
==============

运行方式：
    python test_mcp.py

测试内容：
    - MCP工具列表
    - 各工具调用
"""

import sys
import json
import asyncio
from pathlib import Path

# 添加当前目录
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server import MCPServer


async def test_mcp():
    """测试MCP Server"""
    print("=" * 60)
    print("TRQuant MCP Server 测试")
    print("=" * 60)
    print()
    
    server = MCPServer()
    passed = 0
    failed = 0
    
    # 测试工具列表
    print("1. 测试工具列表")
    tools = server.list_tools()
    print(f"   ✅ 共 {len(tools)} 个工具:")
    for tool in tools:
        print(f"      - {tool['name']}: {tool['description'][:40]}...")
    print()
    passed += 1
    
    # 测试市场状态
    print("2. 测试获取市场状态 (trquant_market_status)")
    result = await server.call_tool("trquant_market_status", {})
    if "error" in result:
        print(f"   ❌ 失败: {result['error']}")
        failed += 1
    else:
        content = json.loads(result['content'][0]['text'])
        print(f"   ✅ 市场Regime: {content.get('regime', 'N/A')}")
        passed += 1
    print()
    
    # 测试投资主线
    print("3. 测试获取投资主线 (trquant_mainlines)")
    result = await server.call_tool("trquant_mainlines", {"top_n": 5})
    if "error" in result:
        print(f"   ❌ 失败: {result['error']}")
        failed += 1
    else:
        content = json.loads(result['content'][0]['text'])
        print(f"   ✅ 获取 {len(content)} 条主线:")
        for ml in content[:3]:
            print(f"      - {ml['name']} (评分: {ml['score']:.2f})")
        passed += 1
    print()
    
    # 测试因子推荐
    print("4. 测试因子推荐 (trquant_recommend_factors)")
    result = await server.call_tool("trquant_recommend_factors", {
        "market_regime": "risk_on",
        "top_n": 5
    })
    if "error" in result:
        print(f"   ❌ 失败: {result['error']}")
        failed += 1
    else:
        content = json.loads(result['content'][0]['text'])
        print(f"   ✅ 推荐 {len(content)} 个因子:")
        for f in content[:3]:
            print(f"      - {f['name']} ({f['category']}, 权重: {f['weight']:.0%})")
        passed += 1
    print()
    
    # 测试策略生成
    print("5. 测试策略生成 (trquant_generate_strategy)")
    result = await server.call_tool("trquant_generate_strategy", {
        "platform": "ptrade",
        "style": "multi_factor",
        "factors": ["ROE_ttm", "momentum_20d", "PE_ttm"]
    })
    if "error" in result:
        print(f"   ❌ 失败: {result['error']}")
        failed += 1
    else:
        content = json.loads(result['content'][0]['text'])
        code_len = len(content.get('code', ''))
        print(f"   ✅ 生成策略: {content.get('name', 'N/A')}")
        print(f"      代码长度: {code_len} 字符")
        passed += 1
    print()
    
    # 测试回测分析
    print("6. 测试回测分析 (trquant_analyze_backtest)")
    result = await server.call_tool("trquant_analyze_backtest", {
        "metrics": {
            "total_return": 0.25,
            "sharpe_ratio": 1.5,
            "max_drawdown": 0.15,
            "win_rate": 0.55
        }
    })
    if "error" in result:
        print(f"   ❌ 失败: {result['error']}")
        failed += 1
    else:
        content = json.loads(result['content'][0]['text'])
        print(f"   ✅ 分析结果:")
        for diag in content.get('diagnosis', []):
            print(f"      - {diag}")
        passed += 1
    print()
    
    # 总结
    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(test_mcp())
    sys.exit(0 if success else 1)

