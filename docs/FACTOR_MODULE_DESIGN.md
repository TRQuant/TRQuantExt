# Alpha因子模块设计文档

## 概述

根据《Alpha因子模块集成方案设计》，实现了完整的因子工程模块，包括：

- **因子计算**：提供价值、成长、质量、动量、资金流五大类因子
- **因子验证**：IC/IR计算、分组回测、因子有效性检验
- **因子存储**：MongoDB + 文件存储双模式
- **因子组合**：等权、IC加权、自定义权重组合
- **候选池集成**：与主线选股无缝对接

## 目录结构

```
core/factors/
├── __init__.py              # 模块导出
├── base_factor.py           # 因子基类
├── factor_manager.py        # 因子管理器
├── factor_evaluator.py      # 因子验证评估
├── factor_storage.py        # MongoDB/文件存储
├── factor_pool_integration.py  # 候选池集成
├── value_factors.py         # 价值因子
├── growth_factors.py        # 成长因子
├── quality_factors.py       # 质量因子
├── momentum_factors.py      # 动量因子
└── flow_factors.py          # 资金流因子
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

## 版本历史

- v2.0.0: 添加因子验证、存储和候选池集成模块
- v1.0.0: 初始版本，包含基础因子计算功能

