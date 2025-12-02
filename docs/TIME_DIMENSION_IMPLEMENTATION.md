# 时间维度功能实现文档

## 概述

根据 `TIME_DIMENSION_PRINCIPLES.md` 的设计原则，实现了完整的时间维度数据管理功能。

## 实现的功能

### 1. 时间维度数据管理器 (`core/time_dimension_manager.py`)

核心类，统一管理所有模块的时间维度数据。

#### 主要类

| 类名 | 说明 |
|------|------|
| `Period` | 投资周期枚举 (SHORT/MEDIUM/LONG) |
| `SnapshotMeta` | 快照元数据 |
| `CandidatePoolSnapshot` | 候选池快照 |
| `MainlineSnapshot` | 主线快照 |
| `ChangeRecord` | 变更记录 |
| `MongoDBRepository` | MongoDB数据仓库 |
| `TimeDimensionManager` | 时间维度管理器 |

#### 功能方法

```python
# 候选池管理
tdm.save_candidate_pool_snapshot(stocks, mainlines_used, period, date)
tdm.get_candidate_pool_snapshot(date, period)
tdm.get_latest_candidate_pool(period)
tdm.get_candidate_pool_history(start_date, end_date, period)

# 主线管理
tdm.save_mainline_snapshot(mainlines, period, date)
tdm.get_mainline_snapshot(date, period)
tdm.get_latest_mainline(period)
tdm.get_mainline_history(start_date, end_date, period)

# 板块轮动分析
tdm.analyze_rotation(days, period)

# 变更历史
tdm.get_stock_history(stock_code)
tdm.get_recent_changes(limit)
```

### 2. 历史查询Tab (`gui/widgets/history_viewer_tab.py`)

提供图形化的历史数据查询界面。

#### 子Tab

| Tab | 功能 |
|-----|------|
| 📊 主线历史 | 查询指定日期的主线快照 |
| 📦 候选池历史 | 查询指定日期的候选池快照 |
| 🔄 板块轮动 | 分析板块热度变化趋势 |
| 📝 变更记录 | 追踪股票进出候选池历史 |

### 3. 趋势-因子联动 (`core/trend_factor_linker.py`)

根据市场趋势自动调整因子权重。

#### 市场状态对应权重

| 市场状态 | 动量 | 成长 | 价值 | 质量 | 资金流 |
|----------|------|------|------|------|--------|
| 强势牛市 | 30% | 25% | 5% | 10% | 15% |
| 牛市 | 25% | 20% | 10% | 15% | 15% |
| 震荡 | 10% | 15% | 20% | 20% | 10% |
| 熊市 | 5% | 5% | 30% | 25% | 5% |
| 强势熊市 | 0% | 5% | 35% | 25% | 5% |

#### 使用示例

```python
from core.trend_factor_linker import get_trend_factor_linker

linker = get_trend_factor_linker()
weights = linker.update_from_trend(trend_result)

# 获取推荐因子
recommended = linker.get_recommended_factors(top_n=3)
# [('momentum', 0.30), ('growth', 0.25), ('flow', 0.15)]

# 获取应避免的因子
avoided = linker.get_avoided_factors()
# ['value', 'volatility']
```

## MongoDB集合结构

### candidate_pool_snapshots

```json
{
  "meta": {
    "snapshot_id": "pool_2025-12-01_medium",
    "snapshot_date": "2025-12-01",
    "period": "medium",
    "created_at": "2025-12-01T10:00:00",
    "source": "jqdata"
  },
  "mainlines_used": [...],
  "stocks": [...],
  "statistics": {
    "count": 50,
    "mainline_distribution": {"人工智能": 15, "芯片": 12},
    "avg_score": 75.5
  },
  "data_permission": {...}
}
```

### mainline_snapshots

```json
{
  "meta": {
    "snapshot_id": "mainline_2025-12-01_medium",
    "snapshot_date": "2025-12-01",
    "period": "medium",
    "created_at": "2025-12-01T10:00:00",
    "source": "composite_score"
  },
  "mainlines": [...],
  "rotation_signal": null,
  "market_context": {}
}
```

### change_records

```json
{
  "timestamp": "2025-12-01T10:00:00",
  "change_type": "add",
  "item_type": "stock",
  "item_id": "000001.XSHE",
  "item_name": "平安银行",
  "details": {
    "mainline": "金融科技",
    "date": "2025-12-01",
    "period": "medium"
  }
}
```

## 索引设计

```javascript
// 候选池快照
db.candidate_pool_snapshots.createIndex(
  {"meta.snapshot_date": -1, "meta.period": 1}, 
  {unique: true}
)

// 主线快照
db.mainline_snapshots.createIndex(
  {"meta.snapshot_date": -1, "meta.period": 1}, 
  {unique: true}
)

// 变更记录
db.change_records.createIndex({"timestamp": -1})
db.change_records.createIndex({"item_id": 1})
```

## 集成点

### 1. 候选池模块 (`stock_pool_panel.py`)

在 `_save_scan_results` 方法中自动保存时间维度快照：

```python
def _save_scan_results(self, stocks, period):
    # ... 保存到缓存
    # 同时保存时间维度快照
    self._save_time_dimension_snapshot(stocks, period)
```

### 2. 综合评分模块 (`composite_tab.py`)

在 `_save_composite_scores` 方法中自动保存主线快照：

```python
def _save_composite_scores(self, results):
    # ... 映射和保存
    # 同时保存时间维度快照
    self._save_mainline_time_snapshot(mapped_mainlines, period)
```

### 3. 市场趋势模块 (`market_trend_panel.py`)

在 `_on_finished` 方法中自动更新因子权重：

```python
def _on_finished(self, result):
    # ... 显示结果
    # 趋势-因子联动
    self._update_factor_weights(result)
```

## 使用流程

```
1. 投资主线分析 (综合评分)
   → 自动保存主线快照到 mainline_snapshots
   
2. 候选池扫描 (一键扫描全部)
   → 自动保存候选池快照到 candidate_pool_snapshots
   → 记录股票变更到 change_records
   
3. 历史查询 (投资主线 → 历史查询Tab)
   → 按日期查询主线/候选池快照
   → 分析板块轮动
   → 查看变更记录
   
4. 市场趋势分析
   → 自动更新因子权重 (趋势-因子联动)
   → 推荐/避免因子列表
```

## 后续扩展

- [ ] 主线生命周期追踪（启动/高峰/衰退）
- [ ] 候选池对比功能（两个日期的差异）
- [ ] 轮动预测模型
- [ ] 批量历史回测

