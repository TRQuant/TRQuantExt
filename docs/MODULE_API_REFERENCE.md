# 韬睿量化系统 - 核心模块API参考

> **开发原则**：所有模块已打磨完成，后续开发只需调用这些API，不要重复实现。

---

## 📁 核心模块架构

```
core/
├── trend_analyzer.py       # 市场趋势分析
├── five_dimension_scorer.py # 投资主线五维评分
├── candidate_pool_builder.py # 候选池构建
├── strong_stock_scanner.py   # 强势股扫描
├── ai_analyzer.py            # AI智能分析
├── strategy_generator.py     # 策略代码生成
├── workflow_orchestrator.py  # 工作流编排器（调用上述模块）
└── __init__.py
```

---

## 🔧 模块API

### 1. TrendAnalyzer - 市场趋势分析

```python
from core.trend_analyzer import TrendAnalyzer

analyzer = TrendAnalyzer(jq_client=jq_client)  # 可选jq_client

# 分析市场趋势
result = analyzer.analyze_market()
# 返回: MarketTrendResult
#   - short_term: 短期趋势 (direction, score)
#   - medium_term: 中期趋势
#   - long_term: 长期趋势
#   - composite_score: 综合评分
#   - market_phase: 市场阶段 ("牛市初期"/"震荡"/"熊市"等)

# 获取仓位建议
advice = analyzer.get_position_advice(result)
```

---

### 2. FiveDimensionScorer - 投资主线评分

```python
from core.five_dimension_scorer import FiveDimensionScorer

scorer = FiveDimensionScorer()

# 对主线进行五维评分
result = scorer.score_theme(theme_name="人工智能", theme_type="concept")
# 返回: FiveDimensionScore
#   - fundamental_score: 基本面得分
#   - technical_score: 技术面得分
#   - capital_flow_score: 资金流向得分
#   - news_score: 新闻热度得分
#   - industry_position_score: 行业地位得分
#   - composite_score: 综合得分
```

---

### 3. CandidatePoolBuilder - 候选池构建

```python
from core.candidate_pool_builder import CandidatePoolBuilder

builder = CandidatePoolBuilder()

# 从主线构建候选池
pool = builder.build_from_mainline(mainline_name="人工智能", pool_type="concept")
# 返回: CandidatePool
#   - stocks: List[StockInfo] 股票列表
#   - total_count: 股票数量
#   - source: 来源

# 获取数据模式信息
data_mode = builder.get_data_mode_info()
# 返回: {"mode": "historical", "date_range": "..."}

# 列出可用概念/行业
concepts = builder.list_available_concepts()
industries = builder.list_available_industries()
```

---

### 4. StrongStockScanner - 强势股扫描

```python
from core.strong_stock_scanner import StrongStockScanner

scanner = StrongStockScanner()

# 扫描强势股
stocks = scanner.scan()
# 返回: List[Dict]
#   - code: 股票代码
#   - name: 股票名称
#   - score: 强势评分
#   - reasons: 入选原因
```

---

### 5. AIAnalyzer - AI智能分析

```python
from core.ai_analyzer import AIAnalyzer

analyzer = AIAnalyzer(model_type="local")  # "local", "openai", "ollama"

# 推荐因子
result = analyzer.recommend_factors(
    mainlines=[{"name": "人工智能", "score": 8.5}],
    market_context={"market_phase": "震荡"}
)
# 返回: FactorRecommendation
#   - recommended_factors: List[Dict] 推荐的因子
#   - reasoning: 推荐理由

# 分析股票
analysis = analyzer.analyze_stocks(stock_codes=["000001", "600000"])
```

---

### 6. StrategyGenerator - 策略生成

```python
from core.strategy_generator import (
    StrategyGenerator, StrategyConfig, FactorConfig,
    RebalanceConfig, RebalanceFreq,
    StopLossConfig, StopLossType,
    TakeProfitConfig, TakeProfitType
)

# 配置因子
factors = [
    FactorConfig("momentum_1m", "1月动量", 0.30, "positive"),
    FactorConfig("roe", "ROE", 0.30, "positive"),
    FactorConfig("ep", "市盈率倒数", 0.40, "positive"),
]

# 配置策略
config = StrategyConfig(
    name="我的策略",
    description="多因子选股策略",
    factors=factors,
    rebalance=RebalanceConfig(frequency=RebalanceFreq.BIWEEKLY, position_limit=20),
    stop_loss=StopLossConfig(type=StopLossType.TRAILING, threshold=0.08),
    take_profit=TakeProfitConfig(type=TakeProfitType.TRAILING, threshold=0.20)
)

# 生成策略代码
generator = StrategyGenerator()
code = generator.create_strategy(config)

# 保存策略
generator.save_strategy(config, "path/to/strategy.py")

# 获取策略模板
templates = generator.get_templates()
```

---

### 7. WorkflowOrchestrator - 工作流编排器

```python
from core import get_workflow_orchestrator

# 获取单例
orchestrator = get_workflow_orchestrator()

# 执行单个步骤
result = orchestrator.check_data_sources()
result = orchestrator.analyze_market_trend()
result = orchestrator.identify_mainlines()
result = orchestrator.build_candidate_pool()
result = orchestrator.recommend_factors()
result = orchestrator.generate_strategy()

# 执行完整工作流
full_result = orchestrator.run_full_workflow(callback=lambda step, result: print(f"{step}: {result.summary}"))
# 返回: FullWorkflowResult
#   - success: 是否全部成功
#   - steps: List[WorkflowResult] 各步骤结果
#   - strategy_file: 生成的策略文件路径
#   - total_time: 总耗时
```

---

## 📦 数据层模块

### JQDataClient - 聚宽数据

```python
from jqdata.client import JQDataClient

client = JQDataClient()
client.authenticate(username, password)

# 获取股票数据
df = client.get_price(security="000001.XSHE", start_date="2024-01-01", end_date="2024-12-01")

# 获取概念/行业成分股
stocks = client.get_concept_stocks(concept_name="人工智能")
stocks = client.get_industry_stocks(industry_code="C39")

# 获取权限信息
perm = client.get_permission()
```

---

## 🔄 调用示例：完整工作流

```python
from core import get_workflow_orchestrator

# 1. 获取编排器
orchestrator = get_workflow_orchestrator()

# 2. 执行完整流程
result = orchestrator.run_full_workflow()

# 3. 检查结果
if result.success:
    print(f"策略文件: {result.strategy_file}")
    for step in result.steps:
        print(f"  {step.step_name}: {step.summary}")
else:
    for step in result.steps:
        if not step.success:
            print(f"失败步骤: {step.step_name} - {step.error}")
```

---

## 🎯 开发规范

1. **不要重复实现** - 直接调用上述API
2. **扩展而非修改** - 如需新功能，继承现有类
3. **遵循时间维度** - 短期/中期/长期分别处理
4. **统一数据管理** - 所有数据通过MongoDB统一存储

---

*更新日期: 2025-12-02*

