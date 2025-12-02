# TRQuant Cursor Extension - 深度研究目标

## 🎯 研究目标

开发一个Cursor IDE插件（TRQuant Extension），将韬睿量化系统与Cursor的AI能力深度集成，解决当前系统"AI分析能力有限、策略代码过于简单"的问题。

---

## 📊 当前问题

1. **AI分析器（ai_analyzer.py）使用规则引擎**
   - 因子推荐基于if-else逻辑
   - 无法进行深度市场分析
   - 推荐内容千篇一律

2. **策略生成器（strategy_generator.py）模板化**
   - 生成的PTrade代码较为基础
   - 缺乏复杂交易逻辑
   - 风控模块不完善

3. **缺乏专业深度分析**
   - 市场解读需要人工判断
   - 因子选择缺乏专业论证
   - 策略优化依赖经验

---

## 💡 解决方案：Cursor插件

### 为什么选择Cursor插件而非直接调用API？

1. **上下文感知**: Cursor能理解整个项目代码结构
2. **交互式开发**: 实时对话、迭代优化
3. **代码质量**: 大模型生成的代码更专业
4. **无缝集成**: 在开发环境中完成全部工作

### 插件架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      Cursor IDE                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │             TRQuant Extension                        │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │    │
│  │  │ Command     │  │ WebView     │  │ Status Bar  │  │    │
│  │  │ Palette     │  │ Panel       │  │ Widget      │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │    │
│  └───────────────────────┬─────────────────────────────┘    │
│                          │                                   │
│  ┌───────────────────────▼─────────────────────────────┐    │
│  │              TRQuant Backend (Python)                │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │    │
│  │  │ Trend       │  │ Candidate   │  │ Strategy    │  │    │
│  │  │ Analyzer    │  │ Pool Builder│  │ Generator   │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔬 需要研究的问题

### 1. Cursor Extension开发基础
- Cursor是否使用标准VS Code Extension API？
- 如何创建Cursor专属扩展？
- Extension与Cursor AI的交互方式？

### 2. 与Python后端通信
- 如何在Extension中调用Python脚本？
- 使用HTTP API还是直接子进程？
- 数据格式（JSON）如何设计？

### 3. 与Cursor AI集成
- 如何向Cursor AI注入自定义Prompt？
- 如何传递市场数据作为上下文？
- 如何接收并处理AI生成的代码？

### 4. 最佳实践
- 是否有类似的量化/金融Cursor插件可参考？
- Extension的发布和分发方式？
- 本地开发和调试流程？

---

## 📋 期望研究输出

1. **技术可行性分析**
   - Cursor Extension API的能力边界
   - 与Python后端集成的最佳方案
   - 与AI交互的接口设计

2. **架构设计方案**
   - Extension目录结构
   - 通信协议设计
   - 数据流转流程

3. **开发路线图**
   - MVP功能列表
   - 开发顺序和优先级
   - 预估工作量

4. **参考资源**
   - 官方文档链接
   - 示例项目
   - 社区最佳实践

---

## 🚀 预期功能清单

### MVP (最小可行产品)

| 功能 | 命令 | 说明 |
|------|------|------|
| 获取市场状态 | `TRQuant: Get Market Status` | 调用TrendAnalyzer，生成市场分析Prompt |
| 获取投资主线 | `TRQuant: Get Mainlines` | 获取TOP20主线，注入AI上下文 |
| 生成因子推荐 | `TRQuant: Recommend Factors` | 基于市场+主线，请求AI推荐因子 |
| 生成策略代码 | `TRQuant: Generate Strategy` | AI生成专业PTrade代码 |

### 进阶功能

| 功能 | 命令 | 说明 |
|------|------|------|
| 回测分析 | `TRQuant: Analyze Backtest` | 分析回测结果，提供优化建议 |
| 因子计算 | `TRQuant: Calculate Factors` | 计算指定因子值 |
| 风险评估 | `TRQuant: Risk Assessment` | 评估当前持仓风险 |
| 策略对比 | `TRQuant: Compare Strategies` | 对比多个策略表现 |

---

## 📁 项目结构预览

```
trquant-cursor-extension/
├── package.json              # Extension配置
├── src/
│   ├── extension.ts          # 入口
│   ├── commands/             # 命令实现
│   │   ├── getMarketStatus.ts
│   │   ├── getMainlines.ts
│   │   ├── recommendFactors.ts
│   │   └── generateStrategy.ts
│   ├── services/             # 后端通信
│   │   └── trquantClient.ts
│   ├── views/                # WebView面板
│   │   └── marketPanel.ts
│   └── utils/
│       └── promptBuilder.ts  # Prompt构建器
├── python/                   # Python桥接脚本
│   └── bridge.py
└── README.md
```

---

## ✅ 研究完成标准

- [ ] 明确Cursor Extension API使用方法
- [ ] 确定与TRQuant后端的通信方案
- [ ] 设计AI Prompt注入机制
- [ ] 提供可执行的开发计划
- [ ] 列出参考资源和示例代码

---

*此文档用于深度研究，请基于以上目标进行调研并反馈研究结果。*

