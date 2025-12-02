# Alpha因子模块设计文档

## 概述

根据《Alpha因子模块集成方案设计》和《补充因子构建模块完善建议》，实现了完整的因子工程模块，包括：

- **因子推荐引擎**：基于市场环境和候选池特征，智能推荐因子组合（新增v2.2.0）
- **因子计算**：提供价值、成长、质量、动量、资金流、规模、波动率、流动性八大类因子
- **因子验证**：IC/IR计算、分组回测、因子有效性检验
- **因子中性化**：行业中性化、市值中性化
- **因子相关性分析**：冗余因子检测、因子筛选建议
- **换手率分析**：交易成本估算、可交易性评估
- **因子存储**：MongoDB + 文件存储双模式
- **因子组合**：等权、IC加权、自定义权重组合
- **自动化流水线**：定期计算、存储、监控
- **候选池集成**：与主线选股无缝对接

## 工作流程

```
1. 方法论学习 (📖 方法论) → 了解Alpha工程基础
           ↓
2. 因子库浏览 (📚 因子库, 🏆 经典因子) → 熟悉可用因子
           ↓
3. 智能推荐 (🧠 因子推荐) → 根据市场环境推荐因子组合【核心步骤】
           ↓
4. 因子筛选 (🔍 因子筛选) → 基于候选池进行因子筛选
           ↓
5. 因子计算 (🔧 因子计算) → 计算因子值并生成策略
```

## 目录结构

```
core/factors/
├── __init__.py              # 模块导出
├── base_factor.py           # 因子基类
├── factor_manager.py        # 因子管理器
├── factor_evaluator.py      # 因子验证评估
├── factor_storage.py        # MongoDB/文件存储
├── factor_neutralizer.py    # 因子中性化
├── factor_pipeline.py       # 自动化流水线
├── factor_pool_integration.py  # 候选池集成
├── extended_factors.py      # 扩展因子
├── value_factors.py         # 价值因子
├── growth_factors.py        # 成长因子
├── quality_factors.py       # 质量因子
├── momentum_factors.py      # 动量因子
└── flow_factors.py          # 资金流因子

core/
├── ai_analyzer.py           # AI智能分析器（因子推荐）

gui/widgets/
├── factor_builder_panel.py  # 因子构建面板
├── factor_recommend_tab.py  # 因子推荐标签页（新增v2.2.0）
└── factor_filter_tab.py     # 因子筛选标签页

tests/
└── test_factors_real.py     # 因子真实数据测试
```

## 因子推荐引擎（新增v2.2.0）

### 工作原理

因子推荐引擎基于三个维度进行分析：

1. **市场环境分析**：
   - 分析大盘趋势（牛市/熊市/震荡/复苏）
   - 评估成交量变化
   - 判断资金面状态

2. **候选池特征分析**：
   - 统计行业分布
   - 识别主导行业类型
   - 估算平均市值

3. **投资周期考量**：
   - 短期策略：侧重动量、资金流、反转
   - 中期策略：均衡配置
   - 长期策略：侧重价值、成长、质量

### 市场环境因子映射

| 市场环境 | 推荐因子 | 避免因子 |
|---------|---------|---------|
| 牛市上涨 | 动量、成长、资金流 | 反转、低波动 |
| 熊市下跌 | 价值、质量、低波动 | 动量、小盘 |
| 震荡盘整 | 反转、质量、流动性 | 长周期动量 |
| 触底反弹 | 短期动量、成长、资金流 | 高股息、低波动 |

### 使用示例

```python
from core.ai_analyzer import AIAnalyzer

analyzer = AIAnalyzer(model_type='rule')  # 或 'openai', 'local'

result = analyzer.recommend_factors(
    market_trend='bull',
    pool_characteristics={
        'stock_count': 50,
        'main_industry_type': '科技',
        'industry_distribution': {'人工智能': 15, '芯片': 12}
    },
    period='medium'
)

print(f"推荐因子: {result.recommended_factors}")
print(f"应避免: {result.avoid_factors}")
print(f"建议开发: {result.development_needs}")
```

## 因子分类

### 1. 价值因子 (Value)
| 因子名 | 描述 | 方向 |
|--------|------|------|
| EP | 盈利收益率 (1/PE) | 正向 |
| BP | 账面市值比 | 正向 |
| SP | 营收收益率 | 正向 |
| DividendYield | 股息率 | 正向 |
| CompositeValue | 综合价值因子 | 正向 |

### 2. 成长因子 (Growth)
| 因子名 | 描述 | 方向 |
|--------|------|------|
| RevenueGrowth | 营收增速 | 正向 |
| ProfitGrowth | 利润增速 | 正向 |
| ROEChange | ROE变化 | 正向 |
| CompositeGrowth | 综合成长因子 | 正向 |

### 3. 质量因子 (Quality)
| 因子名 | 描述 | 方向 |
|--------|------|------|
| ROE | 净资产收益率 | 正向 |
| GrossMargin | 毛利率 | 正向 |
| AssetTurnover | 资产周转率 | 正向 |
| Leverage | 杠杆率 | 负向 |
| CompositeQuality | 综合质量因子 | 正向 |

### 4. 动量因子 (Momentum)
| 因子名 | 描述 | 方向 |
|--------|------|------|
| PriceMomentum | 价格动量(6个月) | 正向 |
| Reversal | 短期反转(1周) | 负向 |
| RelativeStrength | 相对强弱 | 正向 |
| CompositeMomentum | 综合动量因子 | 正向 |

### 5. 资金流因子 (Flow)
| 因子名 | 描述 | 方向 |
|--------|------|------|
| NorthboundFlow | 北向资金流入 | 正向 |
| MainForceFlow | 主力资金流入 | 正向 |
| MarginBalance | 融资融券余额 | 正向 |
| CompositeFlow | 综合资金流因子 | 正向 |

### 6. 规模因子 (Size) - 新增
| 因子名 | 描述 | 方向 |
|--------|------|------|
| Size | 规模因子（-log市值） | 负向 |
| MarketCap | 市值因子（log市值） | 无 |
| CompositeSize | 综合规模因子 | 负向 |

### 7. 波动率因子 (Volatility) - 新增
| 因子名 | 描述 | 方向 |
|--------|------|------|
| Volatility | 波动率（年化） | 负向 |
| Beta | 市场Beta | 负向 |
| CompositeVolatility | 综合波动率因子 | 负向 |

### 8. 流动性因子 (Liquidity) - 新增
| 因子名 | 描述 | 方向 |
|--------|------|------|
| Turnover | 换手率 | 负向 |
| Amount | 成交额（log） | 无 |
| Illiquidity | 非流动性（Amihud） | 负向 |
| CompositeLiquidity | 综合流动性因子 | 无 |

## 使用示例

### 1. 基本因子计算

```python
from core.factors import FactorManager
from jqdata.client import JQDataClient

# 初始化
jq_client = JQDataClient()
jq_client.authenticate("username", "password")

factor_manager = FactorManager(jq_client=jq_client)

# 计算单个因子
result = factor_manager.calculate_factor(
    'PriceMomentum', 
    stocks=['000001.XSHE', '600000.XSHG'],
    date='2024-01-15'
)

print(f"因子值: {result.values}")
print(f"前10名: {result.top_n(10)}")
```

### 2. 多因子组合

```python
# 计算多个因子
results = factor_manager.calculate_factors(
    ['CompositeValue', 'CompositeGrowth', 'CompositeMomentum'],
    stocks=stock_list,
    date='2024-01-15'
)

# 等权组合
combined = factor_manager.combine_factors(results, method='equal')

# 自定义权重组合
weights = {
    'CompositeValue': 0.4,
    'CompositeGrowth': 0.3,
    'CompositeMomentum': 0.3
}
combined = factor_manager.combine_factors(results, weights=weights)

# 选股
selected = factor_manager.select_stocks(combined, top_n=30)
```

### 3. 因子验证

```python
from core.factors import FactorEvaluator

evaluator = FactorEvaluator(jq_client=jq_client)

# 计算IC时间序列
ic_series = evaluator.calculate_ic_series(
    factor_manager.get_factor('PriceMomentum'),
    stocks=stock_list,
    start_date='2022-01-01',
    end_date='2024-01-01',
    freq='M'
)

print(f"平均IC: {ic_series['rank_ic'].mean():.4f}")
print(f"IC IR: {ic_series['rank_ic'].mean() / ic_series['rank_ic'].std():.4f}")

# 分组回测
group_result = evaluator.group_backtest(
    factor_manager.get_factor('CompositeValue'),
    stocks=stock_list,
    start_date='2022-01-01',
    end_date='2024-01-01',
    n_groups=5
)

print(f"多空收益: {group_result.long_short_return:.2%}")
print(f"是否单调: {group_result.is_monotonic}")
```

### 4. 因子存储

```python
from core.factors import FactorStorage

storage = FactorStorage()

# 保存因子值
storage.save_factor_values('PriceMomentum', '2024-01-15', result.values)

# 保存因子元信息
storage.save_factor_info(
    factor_name='PriceMomentum',
    category='momentum',
    description='价格动量因子',
    definition='过去120日收益率，跳过最近20日',
    evidence='Jegadeesh & Titman (1993)'
)

# 加载因子值
values = storage.load_factor_values('PriceMomentum', '2024-01-15')
```

### 5. 候选池集成

```python
from core.factors import FactorPoolIntegration

integration = FactorPoolIntegration(jq_client=jq_client)

# 处理候选池
signals = integration.process_candidate_pool(
    stocks=candidate_stocks,
    date='2024-01-15',
    period='medium',  # 中期投资
    mainline_scores=mainline_scores,  # 主线评分
    top_n=30
)

for signal in signals:
    print(f"{signal.code} {signal.name}: "
          f"综合{signal.combined_score:.1f}, "
          f"因子{signal.factor_score:.1f}, "
          f"主线{signal.mainline_score:.1f}")
```

### 6. 生成PTrade策略

```python
# 生成PTrade策略代码
strategy_code = factor_manager.generate_ptrade_strategy(
    factor_names=['CompositeValue', 'CompositeGrowth', 'CompositeMomentum'],
    weights={'CompositeValue': 0.4, 'CompositeGrowth': 0.3, 'CompositeMomentum': 0.3},
    stock_pool='000300.XSHG',  # 沪深300
    hold_num=30,
    rebalance_freq='monthly'
)

# 保存策略
filepath = factor_manager.save_strategy(
    strategy_code,
    filename='multifactor_strategy.py',
    metadata={'description': '多因子选股策略'}
)
```

## 因子验证标准

根据方案设计，因子入库需满足：

1. **IC信息系数**
   - IC均值 > 0.02
   - IR (IC/IC标准差) > 0.3
   - IC为正的比例 > 55%

2. **分组回测**
   - 分组收益单调递增/递减
   - 多空组合年化收益 > 5%
   - 最高组超额收益显著

3. **其他检验**
   - 与现有因子相关性 < 0.7
   - 因子换手率合理
   - 多个市场周期稳定

## 因子监控

系统提供因子状态监控：

| 状态 | 条件 | 处理 |
|------|------|------|
| active | IC > 0.02, IR > 0.3, 单调 | 正常使用 |
| warning | IC < 0.02 或 不单调 | 降低权重 |
| inactive | IC < 0 | 暂停使用 |

## MongoDB表结构

### factor_data
```json
{
  "factor_name": "PriceMomentum",
  "date": "2024-01-15T00:00:00",
  "stock_id": "000001.XSHE",
  "value": 1.234,
  "updated_at": "2024-01-15T18:00:00"
}
```

### factor_info
```json
{
  "factor_name": "PriceMomentum",
  "category": "momentum",
  "description": "价格动量因子",
  "definition": "过去120日收益率，跳过最近20日",
  "evidence": "Jegadeesh & Titman (1993)",
  "frequency": "daily",
  "direction": 1,
  "status": "active",
  "updated_at": "2024-01-15T18:00:00"
}
```

### factor_performance
```json
{
  "factor_name": "PriceMomentum",
  "date": "2024-01-31T00:00:00",
  "ic": 0.035,
  "ic_ir": 0.52,
  "group_returns": {"1": 0.02, "2": 0.04, "3": 0.06, "4": 0.08, "5": 0.12},
  "long_short_return": 0.10,
  "status": "active"
}
```

## 扩展指南

### 添加新因子

1. 在对应类别文件中继承 `BaseFactor`
2. 实现 `calculate_raw` 方法
3. 设置 `name`, `category`, `description`, `direction`
4. 在 `factor_manager.py` 中注册

```python
class NewFactor(BaseFactor):
    name = "NewFactor"
    category = "custom"
    description = "新因子描述"
    direction = 1
    
    def calculate_raw(self, stocks, date, **kwargs):
        # 实现计算逻辑
        return pd.Series(...)
```

### 集成新数据源

1. 在 `base_factor.py` 中扩展数据获取方法
2. 或在具体因子中实现数据获取逻辑
3. 支持JQData、AKShare等多数据源

## 因子中性化

根据建议文档，实现了因子中性化处理：

```python
from core.factors import FactorNeutralizer

neutralizer = FactorNeutralizer(jq_client=jq_client)

# 行业+市值中性化
neutralized = neutralizer.neutralize(
    factor_values, stocks, date,
    neutralize_industry=True,
    neutralize_size=True
)
```

## 因子相关性分析

```python
from core.factors import FactorCorrelationAnalyzer

analyzer = FactorCorrelationAnalyzer(correlation_threshold=0.7)

# 计算相关性矩阵
corr_matrix = analyzer.calculate_correlation_matrix(factor_dict)

# 检测冗余因子
redundant = analyzer.detect_redundant_factors(factor_dict)

# 因子筛选建议
selected = analyzer.suggest_factor_selection(factor_dict, ic_values)
```

## 换手率与交易成本

```python
from core.factors import TurnoverAnalyzer

analyzer = TurnoverAnalyzer(
    commission_rate=0.001,
    slippage_rate=0.001,
    stamp_tax_rate=0.001
)

# 评估可交易性
result = analyzer.evaluate_factor_tradability(
    factor_annual_return=0.15,
    avg_turnover=0.5,
    periods_per_year=12
)
print(f"净收益: {result['net_return']:.2%}")
```

## 自动化流水线

```python
from core.factors import FactorPipeline

# 创建流水线
pipeline = FactorPipeline(
    jq_client=jq_client,
    stock_pool='hs300',
    neutralize=True
)

# 运行每日计算
stats = pipeline.run_daily(date='2024-01-15')

# 运行月度评估
evaluation = pipeline.run_monthly_evaluation()
```

命令行运行：
```bash
cd /home/taotao/dev/QuantTest/TRQuant
source venv/bin/activate
python -m core.factors.factor_pipeline --pool hs300
```

## 测试脚本

运行因子模块综合测试：
```bash
cd /home/taotao/dev/QuantTest/TRQuant
source venv/bin/activate
python tests/test_factors_real.py
```

测试内容：
1. JQData连接测试
2. 因子计算正确性
3. 多因子组合与选股
4. 因子评估（IC计算）
5. 因子中性化
6. 扩展因子测试
7. PTrade策略生成

## 版本历史

- v2.1.0: 添加扩展因子、中性化、流水线等模块（补充建议）
- v2.0.0: 添加因子验证、存储和候选池集成模块
- v1.0.0: 初始版本，包含基础因子计算功能

