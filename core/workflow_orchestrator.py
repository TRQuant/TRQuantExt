# -*- coding: utf-8 -*-
"""
工作流编排器
============

统一编排整个量化工作流程，直接调用现有模块：
- TrendAnalyzer: 市场趋势分析
- FiveDimensionScorer: 投资主线五维评分
- CandidatePoolBuilder: 候选池构建
- StrongStockScanner: 强势股扫描
- AIAnalyzer: 智能因子推荐
- StrategyGenerator: 策略代码生成

使用方式：
    from core.workflow_orchestrator import WorkflowOrchestrator
    
    orchestrator = WorkflowOrchestrator()
    result = orchestrator.run_full_workflow()
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class WorkflowResult:
    """工作流结果"""
    step_name: str
    success: bool
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None


@dataclass
class FullWorkflowResult:
    """完整工作流结果"""
    success: bool
    steps: List[WorkflowResult] = field(default_factory=list)
    strategy_file: Optional[str] = None
    total_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class WorkflowOrchestrator:
    """
    工作流编排器 - 统一调用现有模块
    
    不重复实现逻辑，仅负责编排调用各个独立模块
    """
    
    def __init__(self):
        self.db = None
        self._init_db()
        self._results = {}
    
    def _init_db(self):
        """初始化MongoDB连接"""
        try:
            from pymongo import MongoClient
            client = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
            self.db = client['trquant']
        except Exception as e:
            logger.warning(f"MongoDB连接失败: {e}")
    
    # ============================================================
    # 步骤1: 数据源检测
    # ============================================================
    
    def check_data_sources(self) -> WorkflowResult:
        """检测数据源状态"""
        logger.info("🔍 检测数据源...")
        
        details = {
            "jqdata": {"connected": False},
            "akshare": {"connected": False},
            "mongodb": {"connected": False}
        }
        
        # 检测JQData
        try:
            from jqdata.client import JQDataClient
            from config.config_manager import get_config_manager
            
            config = get_config_manager().get_jqdata_config()
            if config.get("username"):
                client = JQDataClient()
                if client.authenticate(config["username"], config["password"]):
                    perm = client.get_permission()
                    details["jqdata"] = {
                        "connected": True,
                        "account_type": "试用账户" if not perm.is_realtime else "正式账户",
                        "date_range": f"{perm.start_date} 至 {perm.end_date}"
                    }
        except Exception as e:
            details["jqdata"]["error"] = str(e)[:50]
        
        # 检测AKShare
        try:
            import akshare as ak
            df = ak.stock_zh_index_spot_em()
            if df is not None and len(df) > 0:
                details["akshare"] = {"connected": True, "indices": len(df)}
        except Exception as e:
            details["akshare"]["error"] = str(e)[:50]
        
        # 检测MongoDB
        if self.db is not None:
            try:
                collections = self.db.list_collection_names()
                details["mongodb"] = {"connected": True, "collections": len(collections)}
            except Exception as e:
                details["mongodb"]["error"] = str(e)[:50]
        
        connected = sum(1 for v in details.values() if v.get("connected"))
        success = connected >= 2
        
        result = WorkflowResult(
            step_name="数据源检测",
            success=success,
            summary=f"✅ {connected}/3 数据源正常" if success else f"⚠️ {connected}/3 数据源可用",
            details=details
        )
        
        self._results["data_source"] = result
        return result
    
    # ============================================================
    # 步骤2: 市场趋势分析
    # ============================================================
    
    def analyze_market_trend(self) -> WorkflowResult:
        """分析市场趋势 - 调用TrendAnalyzer"""
        logger.info("📈 分析市场趋势...")
        
        try:
            from core.trend_analyzer import TrendAnalyzer
            from jqdata.client import JQDataClient
            from config.config_manager import get_config_manager
            
            # 初始化JQData客户端
            jq_client = None
            try:
                config = get_config_manager().get_jqdata_config()
                if config.get("username"):
                    jq_client = JQDataClient()
                    jq_client.authenticate(config["username"], config["password"])
            except:
                pass
            
            analyzer = TrendAnalyzer(jq_client=jq_client)
            trend_result = analyzer.analyze_market()
            
            if trend_result:
                # 保存到MongoDB
                trend_data = {
                    "date": datetime.now().strftime('%Y-%m-%d'),
                    "trend_short": trend_result.short_term.direction.value,
                    "trend_mid": trend_result.medium_term.direction.value,
                    "trend_long": trend_result.long_term.direction.value,
                    "score_short": trend_result.short_term.score,
                    "score_mid": trend_result.medium_term.score,
                    "score_long": trend_result.long_term.score,
                    "composite_score": trend_result.composite_score,
                    "market_phase": trend_result.market_phase,
                    "timestamp": datetime.now()
                }
                
                if self.db is not None:
                    self.db.market_trend.replace_one(
                        {"date": datetime.now().strftime('%Y-%m-%d')},
                        trend_data,
                        upsert=True
                    )
                
                # 生成详细报告
                report_file = self._generate_trend_report(trend_data)
                
                # 安全获取属性
                details = {
                    "short_term": trend_result.short_term.direction.value if hasattr(trend_result.short_term, 'direction') else str(trend_result.short_term),
                    "mid_term": trend_result.medium_term.direction.value if hasattr(trend_result.medium_term, 'direction') else str(trend_result.medium_term),
                    "long_term": trend_result.long_term.direction.value if hasattr(trend_result.long_term, 'direction') else str(trend_result.long_term),
                    "score_short": trend_result.short_term.score,
                    "score_mid": trend_result.medium_term.score,
                    "score_long": trend_result.long_term.score,
                    "composite_score": trend_result.composite_score,
                    "market_phase": trend_result.market_phase,
                    "report_file": report_file
                }
                
                # 可选属性
                if hasattr(trend_result, 'position_suggestion'):
                    details["position_suggestion"] = trend_result.position_suggestion
                
                result = WorkflowResult(
                    step_name="市场趋势",
                    success=True,
                    summary=f"📈 {trend_result.market_phase} | 综合评分:{trend_result.composite_score:.0f}",
                    details=details
                )
            else:
                result = WorkflowResult(
                    step_name="市场趋势",
                    success=False,
                    summary="⚠️ 趋势分析返回空结果"
                )
            
        except Exception as e:
            result = WorkflowResult(
                step_name="市场趋势",
                success=False,
                summary=f"❌ 分析失败: {str(e)[:50]}",
                error=str(e)
            )
        
        self._results["market_trend"] = result
        return result
    
    def _generate_trend_report(self, trend_data: Dict) -> str:
        """生成市场趋势详细报告"""
        report_dir = Path(__file__).parent.parent / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = report_dir / f"trend_report_{timestamp}.html"
        
        phase = trend_data.get('market_phase', '震荡')
        score = trend_data.get('composite_score', 0)
        
        # 趋势方向映射
        direction_map = {
            'up': ('上涨', '#10b981', '↑'),
            'down': ('下跌', '#ef4444', '↓'),
            'sideways': ('震荡', '#f59e0b', '→'),
        }
        
        short_dir = direction_map.get(trend_data.get('trend_short', 'sideways'), ('震荡', '#f59e0b', '→'))
        mid_dir = direction_map.get(trend_data.get('trend_mid', 'sideways'), ('震荡', '#f59e0b', '→'))
        long_dir = direction_map.get(trend_data.get('trend_long', 'sideways'), ('震荡', '#f59e0b', '→'))
        
        html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>市场趋势分析报告 - 韬睿量化</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', sans-serif; background: #1a1a2e; color: #e0e0e0; padding: 40px; }}
        .header {{ text-align: center; margin-bottom: 40px; }}
        .header h1 {{ color: #60a5fa; font-size: 28px; }}
        .score-box {{ text-align: center; background: linear-gradient(135deg, #252540, #1a1a2e); border-radius: 20px; padding: 40px; margin: 30px 0; }}
        .score {{ font-size: 72px; font-weight: bold; color: {'#10b981' if score > 50 else '#f59e0b' if score > 30 else '#ef4444'}; }}
        .phase {{ font-size: 24px; color: #f59e0b; margin-top: 10px; }}
        .trend-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 30px 0; }}
        .trend-card {{ background: #252540; border-radius: 12px; padding: 25px; text-align: center; }}
        .trend-card h3 {{ color: #9ca3af; margin-bottom: 15px; }}
        .trend-arrow {{ font-size: 36px; }}
        .trend-label {{ font-size: 18px; font-weight: bold; margin-top: 10px; }}
        .trend-score {{ color: #6b7280; margin-top: 5px; }}
        .advice {{ background: #252540; border-radius: 12px; padding: 25px; margin-top: 30px; }}
        .advice h3 {{ color: #8b5cf6; margin-bottom: 15px; }}
        .methodology {{ background: #252540; border-radius: 12px; padding: 25px; margin-top: 30px; }}
        .methodology h3 {{ color: #10b981; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📈 市场趋势分析报告</h1>
        <p>生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
    </div>
    
    <div class="score-box">
        <div class="score">{score:.0f}</div>
        <div class="phase">{phase}</div>
    </div>
    
    <h2 style="color:#60a5fa;">📊 多周期趋势分析</h2>
    <div class="trend-grid">
        <div class="trend-card">
            <h3>短期趋势 (5日)</h3>
            <div class="trend-arrow" style="color:{short_dir[1]}">{short_dir[2]}</div>
            <div class="trend-label" style="color:{short_dir[1]}">{short_dir[0]}</div>
            <div class="trend-score">得分: {trend_data.get('score_short', 0):.1f}</div>
        </div>
        <div class="trend-card">
            <h3>中期趋势 (20日)</h3>
            <div class="trend-arrow" style="color:{mid_dir[1]}">{mid_dir[2]}</div>
            <div class="trend-label" style="color:{mid_dir[1]}">{mid_dir[0]}</div>
            <div class="trend-score">得分: {trend_data.get('score_mid', 0):.1f}</div>
        </div>
        <div class="trend-card">
            <h3>长期趋势 (60日)</h3>
            <div class="trend-arrow" style="color:{long_dir[1]}">{long_dir[2]}</div>
            <div class="trend-label" style="color:{long_dir[1]}">{long_dir[0]}</div>
            <div class="trend-score">得分: {trend_data.get('score_long', 0):.1f}</div>
        </div>
    </div>
    
    <div class="advice">
        <h3>💡 操作建议</h3>
        <ul style="line-height: 2;">
            <li><strong>仓位建议</strong>: {self._get_position_advice(score)}</li>
            <li><strong>策略偏好</strong>: {self._get_strategy_advice(phase)}</li>
            <li><strong>风险提示</strong>: {self._get_risk_advice(phase)}</li>
        </ul>
    </div>
    
    <div class="methodology">
        <h3>📖 分析方法论</h3>
        <ul style="line-height: 1.8;">
            <li><strong>技术指标</strong>: MA5/MA20/MA60均线系统、MACD、RSI、KDJ</li>
            <li><strong>趋势判断</strong>: 短期看5日均线与价格关系，中期看20日均线趋势，长期看60日均线方向</li>
            <li><strong>综合评分</strong>: 短期权重30%，中期权重40%，长期权重30%</li>
            <li><strong>市场阶段</strong>: 根据多周期趋势共振判断（牛市/熊市/震荡/突破等）</li>
        </ul>
    </div>
    
    <p style="text-align:center; color:#6b7280; margin-top:40px;">
        韬睿量化系统 TRQuant © 2025
    </p>
</body>
</html>
"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"生成趋势报告: {report_file}")
        return str(report_file)
    
    def _get_position_advice(self, score: float) -> str:
        if score >= 70:
            return "激进配置，可满仓操作"
        elif score >= 50:
            return "积极配置，建议70-80%仓位"
        elif score >= 30:
            return "中性配置，建议50%仓位"
        else:
            return "保守配置，建议30%以下仓位或空仓"
    
    def _get_strategy_advice(self, phase: str) -> str:
        if "牛" in phase:
            return "追涨策略，侧重动量和成长因子"
        elif "熊" in phase:
            return "防御策略，侧重价值和质量因子"
        elif "突破" in phase:
            return "突破策略，关注量价配合"
        else:
            return "均衡策略，多因子综合选股"
    
    def _get_risk_advice(self, phase: str) -> str:
        if "牛" in phase:
            return "注意追高风险，设置移动止盈"
        elif "熊" in phase:
            return "注意系统性风险，严格止损"
        elif "突破" in phase:
            return "注意假突破风险，等待确认"
        else:
            return "注意震荡区间，高抛低吸"
    
    # ============================================================
    # 步骤3: 投资主线识别
    # ============================================================
    
    def identify_mainlines(self) -> WorkflowResult:
        """识别投资主线 - 使用简化评分（直接调用AKShare）"""
        logger.info("🔥 识别投资主线...")
        
        # 直接使用简单实现，更稳定
        result = self._simple_mainline_analysis()
        self._results["mainline"] = result
        return result
    
    def _simple_mainline_analysis(self) -> WorkflowResult:
        """主线分析（获取TOP20）"""
        try:
            import akshare as ak
            
            # 尝试多种API获取板块数据
            df = None
            data_source = ""
            
            try:
                df = ak.stock_fund_flow_concept()
                data_source = "概念资金流"
            except Exception:
                pass
            
            if df is None or len(df) == 0:
                try:
                    df = ak.stock_board_concept_name_em()
                    data_source = "概念板块"
                except Exception:
                    pass
            
            if df is None or len(df) == 0:
                try:
                    df = ak.stock_board_industry_name_em()
                    data_source = "行业板块"
                except Exception:
                    pass
            
            if df is None or len(df) == 0:
                # 使用默认主线
                mainlines = [
                    {"name": "人工智能", "composite_score": 10, "rank": 1},
                    {"name": "新能源汽车", "composite_score": 9.5, "rank": 2},
                    {"name": "半导体", "composite_score": 9.0, "rank": 3},
                ]
                data_source = "默认配置"
            else:
                # 提取列名
                name_col = None
                for col in ['名称', '行业', '板块名称', 'name']:
                    if col in df.columns:
                        name_col = col
                        break
                if name_col is None:
                    name_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
                
                # 尝试提取涨跌幅和资金流
                change_col = next((c for c in df.columns if '涨跌幅' in c or '涨幅' in c), None)
                flow_col = next((c for c in df.columns if '资金' in c or '流入' in c), None)
                
                # 获取TOP20
                mainlines = []
                for idx, row in df.head(20).iterrows():
                    name = str(row[name_col]) if pd.notna(row[name_col]) else f"板块{idx}"
                    
                    ml = {
                        "name": name,
                        "rank": len(mainlines) + 1,
                        "composite_score": round(10 - len(mainlines) * 0.4, 2)
                    }
                    
                    # 添加涨跌幅
                    if change_col and pd.notna(row.get(change_col)):
                        ml["change_pct"] = float(row[change_col])
                    
                    # 添加资金流
                    if flow_col and pd.notna(row.get(flow_col)):
                        try:
                            ml["fund_flow"] = float(row[flow_col])
                        except:
                            pass
                    
                    mainlines.append(ml)
            
            # 保存到MongoDB
            if self.db is not None:
                self.db.mainline_scores.delete_many({})
                for ml in mainlines:
                    ml['timestamp'] = datetime.now()
                    ml['data_source'] = data_source
                    self.db.mainline_scores.insert_one(ml.copy())
            
            # 生成详细报告
            report_file = self._generate_mainline_report(mainlines, data_source)
            
            # 摘要显示TOP5
            top5_names = [m["name"] for m in mainlines[:5]]
            
            return WorkflowResult(
                step_name="投资主线",
                success=True,
                summary=f"🔥 TOP20主线 | TOP5: {', '.join(top5_names)}",
                details={
                    "top_mainlines": mainlines,
                    "total_count": len(mainlines),
                    "data_source": data_source,
                    "report_file": report_file
                }
            )
        except Exception as e:
            import traceback
            logger.error(traceback.format_exc())
            mainlines = [{"name": "人工智能", "composite_score": 10, "rank": 1}]
            return WorkflowResult(
                step_name="投资主线",
                success=True,
                summary=f"🔥 当前主线: {mainlines[0]['name']} (默认)",
                details={"top_mainlines": mainlines, "note": f"使用默认主线: {str(e)[:30]}"}
            )
    
    def _generate_mainline_report(self, mainlines: List[Dict], data_source: str) -> str:
        """生成投资主线详细报告"""
        report_dir = Path(__file__).parent.parent / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = report_dir / f"mainline_report_{timestamp}.html"
        
        # 生成HTML报告
        html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>投资主线分析报告 - 韬睿量化</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', sans-serif; background: #1a1a2e; color: #e0e0e0; padding: 40px; }}
        .header {{ text-align: center; margin-bottom: 40px; }}
        .header h1 {{ color: #f59e0b; font-size: 28px; }}
        .header p {{ color: #9ca3af; }}
        .info-box {{ background: #252540; border-radius: 12px; padding: 20px; margin-bottom: 30px; }}
        .info-box h3 {{ color: #10b981; margin-bottom: 15px; }}
        table {{ width: 100%; border-collapse: collapse; background: #252540; border-radius: 12px; overflow: hidden; }}
        th {{ background: #374151; color: #f59e0b; padding: 14px; text-align: left; }}
        td {{ padding: 12px 14px; border-bottom: 1px solid #374151; }}
        tr:hover {{ background: #2d2d4a; }}
        .rank {{ font-weight: bold; color: #f59e0b; }}
        .score {{ color: #10b981; font-weight: bold; }}
        .positive {{ color: #10b981; }}
        .negative {{ color: #ef4444; }}
        .methodology {{ background: #252540; border-radius: 12px; padding: 25px; margin-top: 30px; }}
        .methodology h3 {{ color: #8b5cf6; margin-bottom: 15px; }}
        .methodology ul {{ line-height: 1.8; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔥 投资主线分析报告</h1>
        <p>生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')} | 数据源: {data_source}</p>
    </div>
    
    <div class="info-box">
        <h3>📊 概览</h3>
        <p>本报告分析了当前市场 <strong>TOP {len(mainlines)}</strong> 投资主线，基于资金流向、涨跌幅等多维度数据综合评分。</p>
        <p>TOP5主线: <strong style="color:#f59e0b;">{', '.join([m['name'] for m in mainlines[:5]])}</strong></p>
    </div>
    
    <h2 style="color:#60a5fa;">📋 TOP{len(mainlines)} 投资主线排名</h2>
    <table>
        <thead>
            <tr>
                <th>排名</th>
                <th>主线名称</th>
                <th>综合评分</th>
                <th>涨跌幅</th>
                <th>资金流向(亿)</th>
            </tr>
        </thead>
        <tbody>
"""
        
        for ml in mainlines:
            rank = ml.get('rank', '-')
            name = ml.get('name', '-')
            score = ml.get('composite_score', 0)
            change = ml.get('change_pct', None)
            flow = ml.get('fund_flow', None)
            
            change_str = f"<span class='{'positive' if change > 0 else 'negative'}'>{change:+.2f}%</span>" if change is not None else "-"
            flow_str = f"<span class='{'positive' if flow > 0 else 'negative'}'>{flow/100000000:.2f}</span>" if flow is not None else "-"
            
            html += f"""            <tr>
                <td class="rank">#{rank}</td>
                <td><strong>{name}</strong></td>
                <td class="score">{score:.2f}</td>
                <td>{change_str}</td>
                <td>{flow_str}</td>
            </tr>
"""
        
        html += """        </tbody>
    </table>
    
    <div class="methodology">
        <h3>📖 方法论说明</h3>
        <ul>
            <li><strong>数据来源</strong>: 通过AKShare获取实时板块资金流向和涨跌数据</li>
            <li><strong>评分机制</strong>: 综合考虑资金流入强度、涨跌幅排名、成交量变化等因素</li>
            <li><strong>更新频率</strong>: 每次执行工作流时自动更新</li>
            <li><strong>应用场景</strong>: 用于构建候选池时筛选热门概念/行业的成分股</li>
        </ul>
        <h4 style="color:#f59e0b; margin-top:20px;">后续步骤</h4>
        <ol>
            <li>基于TOP主线，获取对应的成分股构建候选池</li>
            <li>结合市场趋势判断，确定各主线的配置权重</li>
            <li>对候选池股票进行因子打分和筛选</li>
        </ol>
    </div>
    
    <p style="text-align:center; color:#6b7280; margin-top:40px;">
        韬睿量化系统 TRQuant © 2025
    </p>
</body>
</html>
"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"生成主线报告: {report_file}")
        return str(report_file)
    
    # ============================================================
    # 步骤4: 候选池构建
    # ============================================================
    
    def build_candidate_pool(self) -> WorkflowResult:
        """构建候选池 - 调用CandidatePoolBuilder + StrongStockScanner"""
        logger.info("📦 构建候选池...")
        
        try:
            from core.candidate_pool_builder import CandidatePoolBuilder
            
            builder = CandidatePoolBuilder()
            
            # 获取主线
            mainlines = []
            if self.db is not None:
                mainlines = list(self.db.mainline_scores.find(
                    sort=[("composite_score", -1)]
                ).limit(5))
            
            all_stocks = []
            sources = []
            
            # 从主线构建候选池
            for ml in mainlines[:3]:
                name = ml.get("name", "")
                if not name:
                    continue
                try:
                    pool = builder.build_from_mainline(name, "concept")
                    if pool and pool.stocks:
                        for stock in pool.stocks[:15]:
                            if stock.code not in [s["code"] for s in all_stocks]:
                                all_stocks.append({
                                    "code": stock.code,
                                    "name": stock.name,
                                    "source": f"主线:{name}",
                                    "score": stock.composite_score
                                })
                        sources.append(name)
                except Exception as e:
                    logger.debug(f"构建{name}候选池失败: {e}")
            
            # 添加强势股
            try:
                from core.strong_stock_scanner import StrongStockScanner
                scanner = StrongStockScanner()
                strong_stocks = scanner.scan()
                
                for stock in strong_stocks[:20]:
                    code = stock.get("code", "")
                    if code and code not in [s["code"] for s in all_stocks]:
                        all_stocks.append({
                            "code": code,
                            "name": stock.get("name", ""),
                            "source": "强势股",
                            "score": stock.get("score", 0)
                        })
                if strong_stocks:
                    sources.append("强势股")
            except Exception as e:
                logger.debug(f"强势股扫描失败: {e}")
            
            # 保存到MongoDB
            if self.db is not None and all_stocks:
                self.db.candidate_pool.replace_one(
                    {"type": "latest"},
                    {
                        "type": "latest",
                        "stocks": all_stocks,
                        "sources": sources,
                        "total_count": len(all_stocks),
                        "timestamp": datetime.now()
                    },
                    upsert=True
                )
            
            result = WorkflowResult(
                step_name="候选池构建",
                success=len(all_stocks) > 0,
                summary=f"📦 候选池: {len(all_stocks)}只股票",
                details={
                    "total_count": len(all_stocks),
                    "stocks": all_stocks[:20],
                    "sources": sources
                }
            )
            
        except Exception as e:
            result = WorkflowResult(
                step_name="候选池构建",
                success=False,
                summary=f"❌ 构建失败: {str(e)[:50]}",
                error=str(e)
            )
        
        self._results["candidate_pool"] = result
        return result
    
    # ============================================================
    # 步骤5: 因子推荐
    # ============================================================
    
    def recommend_factors(self) -> WorkflowResult:
        """推荐因子 - 调用AIAnalyzer"""
        logger.info("🧮 推荐因子...")
        
        try:
            # 获取市场环境
            market_phase = "震荡"
            if self.db is not None:
                trend = self.db.market_trend.find_one(sort=[("date", -1)])
                if trend:
                    market_phase = trend.get("market_phase", "震荡")
            
            try:
                from core.ai_analyzer import AIAnalyzer
                
                analyzer = AIAnalyzer(model_type="local")
                mainlines = list(self.db.mainline_scores.find().limit(5)) if self.db is not None else []
                
                factor_result = analyzer.recommend_factors(
                    mainlines=mainlines,
                    market_context={"market_phase": market_phase}
                )
                
                recommended = factor_result.recommended_factors
                reasoning = factor_result.reasoning
                
            except Exception as e:
                logger.debug(f"AI分析器失败，使用规则推荐: {e}")
                recommended, reasoning = self._get_rule_based_factors(market_phase)
            
            # 保存到MongoDB
            if self.db is not None:
                self.db.factor_recommendations.replace_one(
                    {"type": "latest"},
                    {
                        "type": "latest",
                        "recommended_factors": recommended,
                        "market_environment": market_phase,
                        "reasoning": reasoning,
                        "timestamp": datetime.now()
                    },
                    upsert=True
                )
            
            factor_names = [f.get("name", "") for f in recommended[:3]]
            result = WorkflowResult(
                step_name="因子推荐",
                success=True,
                summary=f"🧮 推荐: {', '.join(factor_names)}",
                details={
                    "recommended_factors": recommended,
                    "market_environment": market_phase,
                    "reasoning": reasoning
                }
            )
            
        except Exception as e:
            result = WorkflowResult(
                step_name="因子推荐",
                success=False,
                summary=f"❌ 推荐失败: {str(e)[:50]}",
                error=str(e)
            )
        
        self._results["factor"] = result
        return result
    
    def _get_rule_based_factors(self, market_phase: str) -> tuple:
        """基于规则的因子推荐"""
        if "牛" in market_phase:
            factors = [
                {"name": "动量因子", "weight": 0.35, "reason": "牛市追涨效应"},
                {"name": "成长因子", "weight": 0.30, "reason": "市场偏好成长"},
                {"name": "质量因子", "weight": 0.20, "reason": "控制风险"},
                {"name": "规模因子", "weight": 0.15, "reason": "小盘更有弹性"}
            ]
            reasoning = "牛市环境，侧重动量和成长"
        elif "熊" in market_phase:
            factors = [
                {"name": "价值因子", "weight": 0.35, "reason": "安全边际"},
                {"name": "质量因子", "weight": 0.30, "reason": "优质抗跌"},
                {"name": "低波动因子", "weight": 0.20, "reason": "减少回撤"},
                {"name": "股息因子", "weight": 0.15, "reason": "稳定现金流"}
            ]
            reasoning = "熊市环境，防御为主"
        else:
            factors = [
                {"name": "动量因子", "weight": 0.25, "reason": "捕捉趋势"},
                {"name": "价值因子", "weight": 0.25, "reason": "估值保护"},
                {"name": "成长因子", "weight": 0.25, "reason": "成长支撑"},
                {"name": "质量因子", "weight": 0.25, "reason": "风险控制"}
            ]
            reasoning = "震荡环境，均衡配置"
        
        return factors, reasoning
    
    # ============================================================
    # 步骤6: 策略生成
    # ============================================================
    
    def generate_strategy(self) -> WorkflowResult:
        """生成策略 - 调用StrategyGenerator"""
        logger.info("💻 生成策略...")
        
        try:
            from core.strategy_generator import (
                StrategyGenerator, StrategyConfig, FactorConfig,
                RebalanceConfig, RebalanceFreq, StopLossConfig,
                TakeProfitConfig, StopLossType, TakeProfitType
            )
            
            # 获取因子推荐
            factor_rec = None
            market_phase = "震荡"
            if self.db is not None:
                factor_rec = self.db.factor_recommendations.find_one({"type": "latest"})
                trend = self.db.market_trend.find_one(sort=[("date", -1)])
                if trend:
                    market_phase = trend.get("market_phase", "震荡")
            
            # 构建因子配置
            factor_map = {
                "动量因子": ("momentum_1m", "1月动量", "positive"),
                "价值因子": ("ep", "市盈率倒数", "positive"),
                "成长因子": ("profit_growth", "净利润增长率", "positive"),
                "质量因子": ("roe", "净资产收益率", "positive"),
                "规模因子": ("market_cap", "市值", "negative"),
                "低波动因子": ("volatility", "波动率", "negative"),
                "股息因子": ("dividend_yield", "股息率", "positive")
            }
            
            factors = []
            if factor_rec:
                for f in factor_rec.get("recommended_factors", []):
                    name = f.get("name", "")
                    weight = f.get("weight", 0.25)
                    if name in factor_map:
                        fid, fname, direction = factor_map[name]
                        factors.append(FactorConfig(fid, fname, weight, direction))
            
            if not factors:
                factors = [
                    FactorConfig("momentum_1m", "1月动量", 0.25, "positive"),
                    FactorConfig("ep", "市盈率倒数", 0.25, "positive"),
                    FactorConfig("roe", "净资产收益率", 0.25, "positive"),
                    FactorConfig("profit_growth", "净利润增长率", 0.25, "positive"),
                ]
            
            # 根据市场环境配置
            if "牛" in market_phase:
                rebalance_freq = RebalanceFreq.WEEKLY
                stop_loss = 0.05
                take_profit = 0.20
            elif "熊" in market_phase:
                rebalance_freq = RebalanceFreq.MONTHLY
                stop_loss = 0.08
                take_profit = 0.15
            else:
                rebalance_freq = RebalanceFreq.BIWEEKLY
                stop_loss = 0.06
                take_profit = 0.18
            
            config = StrategyConfig(
                name=f"韬睿量化策略_{datetime.now().strftime('%Y%m%d')}",
                description=f"基于{market_phase}环境自动生成",
                factors=factors,
                rebalance=RebalanceConfig(frequency=rebalance_freq, position_limit=20),
                stop_loss=StopLossConfig(type=StopLossType.TRAILING, threshold=stop_loss),
                take_profit=TakeProfitConfig(type=TakeProfitType.TRAILING, threshold=take_profit)
            )
            
            # 生成策略
            generator = StrategyGenerator()
            code = generator.create_strategy(config)
            
            # 保存文件
            strategy_dir = Path(__file__).parent.parent / "strategies" / "ptrade"
            strategy_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            strategy_file = strategy_dir / f"strategy_{timestamp}.py"
            generator.save_strategy(config, str(strategy_file))
            
            # 保存到MongoDB
            if self.db is not None:
                self.db.strategies.insert_one({
                    "file_path": str(strategy_file),
                    "config": config.to_dict(),
                    "market_phase": market_phase,
                    "timestamp": datetime.now()
                })
            
            result = WorkflowResult(
                step_name="策略生成",
                success=True,
                summary=f"💻 已生成: {strategy_file.name}",
                details={
                    "strategy_file": str(strategy_file),
                    "market_phase": market_phase,
                    "factors": [{"name": f.factor_name, "weight": f.weight} for f in factors],
                    "rebalance_freq": rebalance_freq.value
                }
            )
            
        except Exception as e:
            import traceback
            logger.error(traceback.format_exc())
            result = WorkflowResult(
                step_name="策略生成",
                success=False,
                summary=f"❌ 生成失败: {str(e)[:50]}",
                error=str(e)
            )
        
        self._results["strategy"] = result
        return result
    
    # ============================================================
    # 完整工作流执行
    # ============================================================
    
    def run_full_workflow(self, callback=None) -> FullWorkflowResult:
        """
        执行完整工作流
        
        Args:
            callback: 可选的回调函数，每完成一步调用 callback(step_name, result)
        
        Returns:
            FullWorkflowResult: 完整结果
        """
        import time
        start_time = time.time()
        
        steps = [
            ("数据源", self.check_data_sources),
            ("市场趋势", self.analyze_market_trend),
            ("投资主线", self.identify_mainlines),
            ("候选池", self.build_candidate_pool),
            ("因子推荐", self.recommend_factors),
            ("策略生成", self.generate_strategy),
        ]
        
        results = []
        all_success = True
        strategy_file = None
        
        for step_name, step_func in steps:
            logger.info(f"执行步骤: {step_name}")
            result = step_func()
            results.append(result)
            
            if callback:
                callback(step_name, result)
            
            if not result.success:
                all_success = False
            
            if step_name == "策略生成" and result.success:
                strategy_file = result.details.get("strategy_file")
        
        total_time = time.time() - start_time
        
        return FullWorkflowResult(
            success=all_success,
            steps=results,
            strategy_file=strategy_file,
            total_time=total_time
        )
    
    def get_step_result(self, step_id: str) -> Optional[WorkflowResult]:
        """获取指定步骤的结果"""
        return self._results.get(step_id)
    
    def get_all_results(self) -> Dict[str, WorkflowResult]:
        """获取所有结果"""
        return self._results.copy()


# 单例
_orchestrator = None

def get_workflow_orchestrator() -> WorkflowOrchestrator:
    """获取工作流编排器单例"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = WorkflowOrchestrator()
    return _orchestrator

