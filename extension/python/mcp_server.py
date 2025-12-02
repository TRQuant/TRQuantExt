#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TRQuant MCP Server
==================

Model Context Protocol (MCP) Server实现
允许Cursor AI直接调用TRQuant功能

运行方式：
    python mcp_server.py

遵循：
    - MCP协议规范
    - 单一职责原则
    - 依赖注入
"""

import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

# 添加项目路径
TRQUANT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(TRQUANT_ROOT))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger('MCP')

# 导入TRQuant核心模块
try:
    from core import get_workflow_orchestrator
    from core.trend_analyzer import TrendAnalyzer
    from core.five_dimension_scorer import FiveDimensionScorer
    TRQUANT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"TRQuant核心模块不可用: {e}")
    TRQUANT_AVAILABLE = False


@dataclass
class MCPTool:
    """MCP工具定义"""
    name: str
    description: str
    input_schema: dict


# 定义MCP工具
MCP_TOOLS: List[MCPTool] = [
    MCPTool(
        name="trquant_market_status",
        description="获取A股市场当前状态，包括市场Regime（risk_on/risk_off/neutral）、指数趋势和风格轮动",
        input_schema={
            "type": "object",
            "properties": {
                "universe": {
                    "type": "string",
                    "description": "市场，默认CN_EQ表示A股",
                    "default": "CN_EQ"
                }
            },
            "required": []
        }
    ),
    MCPTool(
        name="trquant_mainlines",
        description="获取当前A股市场的投资主线，包括主线名称、评分、相关行业和投资逻辑",
        input_schema={
            "type": "object",
            "properties": {
                "top_n": {
                    "type": "integer",
                    "description": "返回前N条主线，默认10",
                    "default": 10
                },
                "time_horizon": {
                    "type": "string",
                    "enum": ["short", "medium", "long"],
                    "description": "投资周期：short(1-5天)、medium(1-4周)、long(1月+)",
                    "default": "short"
                }
            },
            "required": []
        }
    ),
    MCPTool(
        name="trquant_recommend_factors",
        description="基于市场状态推荐量化因子，包括因子名称、类别、权重和推荐理由",
        input_schema={
            "type": "object",
            "properties": {
                "market_regime": {
                    "type": "string",
                    "enum": ["risk_on", "risk_off", "neutral"],
                    "description": "市场状态"
                },
                "top_n": {
                    "type": "integer",
                    "description": "返回前N个因子，默认10",
                    "default": 10
                }
            },
            "required": []
        }
    ),
    MCPTool(
        name="trquant_generate_strategy",
        description="生成PTrade或QMT量化策略代码，支持多因子、动量成长、价值、市场中性四种风格",
        input_schema={
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "enum": ["ptrade", "qmt"],
                    "description": "目标平台",
                    "default": "ptrade"
                },
                "style": {
                    "type": "string",
                    "enum": ["multi_factor", "momentum_growth", "value", "market_neutral"],
                    "description": "策略风格",
                    "default": "multi_factor"
                },
                "factors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "使用的因子列表"
                },
                "max_position": {
                    "type": "number",
                    "description": "单票最大仓位(0-1)，默认0.1",
                    "default": 0.1
                },
                "stop_loss": {
                    "type": "number",
                    "description": "止损线(0-1)，默认0.08",
                    "default": 0.08
                },
                "take_profit": {
                    "type": "number",
                    "description": "止盈线(0-1)，默认0.2",
                    "default": 0.2
                }
            },
            "required": ["factors"]
        }
    ),
    MCPTool(
        name="trquant_analyze_backtest",
        description="分析回测结果，提供诊断和优化建议",
        input_schema={
            "type": "object",
            "properties": {
                "metrics": {
                    "type": "object",
                    "description": "回测指标，包含total_return、sharpe_ratio、max_drawdown等"
                }
            },
            "required": ["metrics"]
        }
    )
]


class MCPServer:
    """MCP Server实现"""
    
    def __init__(self):
        self.orchestrator = get_workflow_orchestrator() if TRQUANT_AVAILABLE else None
        logger.info(f"MCP Server初始化, TRQuant可用: {TRQUANT_AVAILABLE}")
    
    def list_tools(self) -> List[dict]:
        """列出所有可用工具"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema
            }
            for tool in MCP_TOOLS
        ]
    
    async def call_tool(self, name: str, arguments: dict) -> dict:
        """调用工具"""
        logger.info(f"调用工具: {name}")
        
        handlers = {
            "trquant_market_status": self._get_market_status,
            "trquant_mainlines": self._get_mainlines,
            "trquant_recommend_factors": self._recommend_factors,
            "trquant_generate_strategy": self._generate_strategy,
            "trquant_analyze_backtest": self._analyze_backtest
        }
        
        handler = handlers.get(name)
        if not handler:
            return {"error": f"未知工具: {name}"}
        
        try:
            result = await handler(arguments)
            return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}
        except Exception as e:
            logger.error(f"工具执行失败: {e}")
            return {"error": str(e)}
    
    async def _get_market_status(self, args: dict) -> dict:
        """获取市场状态"""
        if not TRQUANT_AVAILABLE:
            return self._mock_market_status()
        
        try:
            analyzer = TrendAnalyzer()
            result = analyzer.analyze_market()
            return {
                "regime": result.regime.value if hasattr(result.regime, 'value') else str(result.regime),
                "index_trend": result.index_zscore,
                "style_rotation": result.style_rotation,
                "summary": result.summary if hasattr(result, 'summary') else self._generate_summary(result)
            }
        except Exception as e:
            logger.error(f"获取市场状态失败: {e}")
            return self._mock_market_status()
    
    async def _get_mainlines(self, args: dict) -> List[dict]:
        """获取投资主线"""
        if not TRQUANT_AVAILABLE:
            return self._mock_mainlines(args.get('top_n', 10))
        
        try:
            if self.orchestrator:
                result = self.orchestrator.identify_mainlines()
                if result.get('ok') and result.get('data'):
                    return result['data'][:args.get('top_n', 10)]
            return self._mock_mainlines(args.get('top_n', 10))
        except Exception as e:
            logger.error(f"获取投资主线失败: {e}")
            return self._mock_mainlines(args.get('top_n', 10))
    
    async def _recommend_factors(self, args: dict) -> List[dict]:
        """推荐因子"""
        regime = args.get('market_regime', 'neutral')
        top_n = args.get('top_n', 10)
        
        # 基于市场状态的因子推荐规则
        factor_pools = {
            'risk_on': [
                {"name": "momentum_20d", "category": "动量", "weight": 0.9, "reason": "风险偏好上升时动量因子表现优异"},
                {"name": "revenue_growth", "category": "成长性", "weight": 0.85, "reason": "成长股在牛市中领涨"},
                {"name": "ROE_ttm", "category": "盈利能力", "weight": 0.8, "reason": "高ROE公司具有竞争优势"},
                {"name": "net_profit_growth", "category": "成长性", "weight": 0.75, "reason": "利润增速是成长性核心指标"},
                {"name": "turnover_rate", "category": "流动性", "weight": 0.7, "reason": "高换手率表示市场关注度高"},
                {"name": "beta", "category": "波动率", "weight": 0.65, "reason": "高Beta股票在牛市中收益更高"},
                {"name": "relative_strength", "category": "动量", "weight": 0.6, "reason": "相对强度选出领涨股"},
                {"name": "analyst_revision", "category": "其他", "weight": 0.55, "reason": "分析师上调预期"},
                {"name": "price_volume", "category": "动量", "weight": 0.5, "reason": "量价配合验证趋势"},
                {"name": "industry_momentum", "category": "动量", "weight": 0.45, "reason": "行业轮动捕捉热点"}
            ],
            'risk_off': [
                {"name": "dividend_yield", "category": "估值", "weight": 0.9, "reason": "高分红提供安全边际"},
                {"name": "PE_ttm", "category": "估值", "weight": 0.85, "reason": "低估值防御性更强"},
                {"name": "volatility_60d", "category": "波动率", "weight": 0.8, "reason": "低波动股票更稳健"},
                {"name": "ROE_ttm", "category": "盈利能力", "weight": 0.75, "reason": "稳定盈利能力是基础"},
                {"name": "debt_to_equity", "category": "质量", "weight": 0.7, "reason": "低杠杆抗风险能力强"},
                {"name": "PB_lf", "category": "估值", "weight": 0.65, "reason": "低市净率安全边际高"},
                {"name": "cash_flow", "category": "质量", "weight": 0.6, "reason": "现金流健康是防御关键"},
                {"name": "market_cap", "category": "其他", "weight": 0.55, "reason": "大市值股票更稳定"},
                {"name": "quality_score", "category": "质量", "weight": 0.5, "reason": "综合质量评分"},
                {"name": "earning_stability", "category": "质量", "weight": 0.45, "reason": "盈利稳定性"}
            ],
            'neutral': [
                {"name": "ROE_ttm", "category": "盈利能力", "weight": 0.85, "reason": "盈利能力是选股基础"},
                {"name": "PE_ttm", "category": "估值", "weight": 0.8, "reason": "估值合理性评估"},
                {"name": "momentum_20d", "category": "动量", "weight": 0.75, "reason": "短期动量捕捉"},
                {"name": "revenue_growth", "category": "成长性", "weight": 0.7, "reason": "成长性评估"},
                {"name": "volatility_60d", "category": "波动率", "weight": 0.65, "reason": "波动率控制"},
                {"name": "turnover_rate", "category": "流动性", "weight": 0.6, "reason": "流动性保障"},
                {"name": "dividend_yield", "category": "估值", "weight": 0.55, "reason": "分红收益"},
                {"name": "debt_to_equity", "category": "质量", "weight": 0.5, "reason": "财务健康度"},
                {"name": "PB_lf", "category": "估值", "weight": 0.45, "reason": "资产价值"},
                {"name": "quality_score", "category": "质量", "weight": 0.4, "reason": "综合质量"}
            ]
        }
        
        factors = factor_pools.get(regime, factor_pools['neutral'])
        return factors[:top_n]
    
    async def _generate_strategy(self, args: dict) -> dict:
        """生成策略代码"""
        from tools.strategy_generator import StrategyGenerator
        
        generator = StrategyGenerator()
        result = generator.generate(
            platform=args.get('platform', 'ptrade'),
            style=args.get('style', 'multi_factor'),
            factors=args.get('factors', ['ROE_ttm', 'momentum_20d']),
            risk_params={
                'max_position': args.get('max_position', 0.1),
                'stop_loss': args.get('stop_loss', 0.08),
                'take_profit': args.get('take_profit', 0.2)
            }
        )
        
        return result
    
    async def _analyze_backtest(self, args: dict) -> dict:
        """分析回测结果"""
        metrics = args.get('metrics', {})
        
        diagnosis = []
        suggestions = []
        
        # 分析总收益
        total_return = metrics.get('total_return', 0)
        if total_return < 0:
            diagnosis.append("策略亏损，需要全面检视")
            suggestions.append("检查入场信号是否过于激进")
        elif total_return < 0.1:
            diagnosis.append("收益较低，可能存在优化空间")
            suggestions.append("考虑增加因子或调整权重")
        
        # 分析夏普比率
        sharpe = metrics.get('sharpe_ratio', 0)
        if sharpe < 0.5:
            diagnosis.append("夏普比率偏低，风险调整收益不佳")
            suggestions.append("增加止损条件或降低仓位")
        elif sharpe > 2:
            diagnosis.append("夏普比率较高，策略质量不错")
        
        # 分析最大回撤
        max_dd = metrics.get('max_drawdown', 0)
        if max_dd > 0.3:
            diagnosis.append("最大回撤过大，风控需要加强")
            suggestions.append("降低单票仓位或增加止损")
        
        # 分析胜率
        win_rate = metrics.get('win_rate', 0)
        if win_rate < 0.4:
            diagnosis.append("胜率偏低")
            suggestions.append("优化选股条件或增加确认信号")
        
        return {
            "metrics_analysis": {
                "total_return": f"{total_return*100:.2f}%" if total_return else "N/A",
                "sharpe_ratio": f"{sharpe:.2f}" if sharpe else "N/A",
                "max_drawdown": f"{max_dd*100:.2f}%" if max_dd else "N/A",
                "win_rate": f"{win_rate*100:.2f}%" if win_rate else "N/A"
            },
            "diagnosis": diagnosis or ["指标正常"],
            "suggestions": suggestions or ["继续观察，保持策略稳定性"]
        }
    
    def _generate_summary(self, result) -> str:
        """生成市场状态摘要"""
        regime = result.regime.value if hasattr(result.regime, 'value') else str(result.regime)
        if regime == 'risk_on':
            return "当前市场风险偏好上升，适合积极配置成长股和高Beta资产。"
        elif regime == 'risk_off':
            return "当前市场风险偏好下降，建议防御性配置，关注价值股。"
        else:
            return "当前市场处于震荡格局，建议均衡配置，控制风险敞口。"
    
    def _mock_market_status(self) -> dict:
        """模拟市场状态"""
        return {
            "regime": "neutral",
            "index_trend": {
                "SH000300": {"zscore": 0.5, "trend": "up"},
                "SZ399006": {"zscore": -0.3, "trend": "down"},
                "SH000016": {"zscore": 0.8, "trend": "up"}
            },
            "style_rotation": [
                {"style": "value", "score": 0.6},
                {"style": "growth", "score": 0.3},
                {"style": "momentum", "score": 0.1}
            ],
            "summary": "模拟数据：市场处于震荡格局，价值风格相对占优。"
        }
    
    def _mock_mainlines(self, top_n: int) -> List[dict]:
        """模拟投资主线"""
        mainlines = [
            {"name": "AI人工智能", "score": 0.95, "industries": ["计算机", "电子", "通信"], "logic": "AI技术突破带动产业链"},
            {"name": "新能源汽车", "score": 0.88, "industries": ["汽车", "电气设备"], "logic": "电动化智能化加速"},
            {"name": "半导体国产替代", "score": 0.85, "industries": ["电子", "计算机"], "logic": "自主可控需求迫切"},
            {"name": "医药创新", "score": 0.78, "industries": ["医药生物"], "logic": "创新药进入收获期"},
            {"name": "高端制造", "score": 0.75, "industries": ["机械设备", "国防军工"], "logic": "制造业升级"},
            {"name": "消费复苏", "score": 0.72, "industries": ["食品饮料", "商贸零售"], "logic": "消费信心恢复"},
            {"name": "数字经济", "score": 0.68, "industries": ["计算机", "传媒"], "logic": "数字化转型"},
            {"name": "新材料", "score": 0.65, "industries": ["化工", "有色金属"], "logic": "新兴产业需求"},
            {"name": "光伏储能", "score": 0.62, "industries": ["电气设备", "公用事业"], "logic": "清洁能源发展"},
            {"name": "国企改革", "score": 0.58, "industries": ["建筑装饰", "公用事业"], "logic": "估值修复"}
        ]
        return mainlines[:top_n]


async def handle_request(request: dict, server: MCPServer) -> dict:
    """处理MCP请求"""
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "trquant-mcp",
                    "version": "1.0.0"
                }
            }
        }
    
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": server.list_tools()
            }
        }
    
    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = await server.call_tool(tool_name, arguments)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": result
        }
    
    elif method == "notifications/initialized":
        return None  # 不需要响应
    
    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"未知方法: {method}"
            }
        }


async def main():
    """主函数 - 运行MCP Server"""
    logger.info("TRQuant MCP Server 启动...")
    server = MCPServer()
    
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
    
    writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout
    )
    writer = asyncio.StreamWriter(writer_transport, writer_protocol, reader, asyncio.get_event_loop())
    
    while True:
        try:
            line = await reader.readline()
            if not line:
                break
            
            request = json.loads(line.decode('utf-8'))
            response = await handle_request(request, server)
            
            if response:
                response_str = json.dumps(response, ensure_ascii=False) + '\n'
                writer.write(response_str.encode('utf-8'))
                await writer.drain()
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {e}")
        except Exception as e:
            logger.error(f"处理请求错误: {e}")


if __name__ == "__main__":
    asyncio.run(main())
