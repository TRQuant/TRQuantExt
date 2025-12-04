# 开发模板与规则 (Development Templates and Rules)

本目录包含TRQuant项目的开发规范、模板和规则文件，旨在：

1. **统一开发规范** - 确保代码风格和架构一致性
2. **指导AI开发** - 为Cursor + Claude提供项目上下文
3. **提高开发效率** - 减少重复决策和沟通成本
4. **保证代码质量** - 通过规范和检查清单确保质量

## 📁 文件说明

### 核心文档

- **`PROJECT_BRIEF.md`** - 项目概要
  - 项目整体目标和架构设计
  - 模块职责概述
  - 接口与调用关系
  - **用途**：为AI和开发者提供项目高层概览

- **`MODULE_INDEX.md`** - 模块索引
  - 所有模块的路径、职责、接口
  - 模块调用关系图
  - **用途**：快速定位模块位置和职责

- **`DECISIONS.md`** - 架构决策记录
  - 关键设计决策及原因
  - 替代方案权衡
  - **用途**：记录决策历史，避免重复讨论

### 开发规范

- **`ENGINEERING_RULES.md`** - 工程编码规范
  - DRY原则、容错处理、接口设计
  - 测试要求、日志规范、命名规范
  - VS Code Extension特定规范
  - **用途**：指导日常编码工作

- **`.cursor-rules.mdc`** - Cursor规则文件
  - AI代码生成约束
  - 项目特定约定
  - **用途**：让Cursor自动遵循项目规范

### 开发工具

- **`PR_CHECKLIST.md`** - 提交前检查清单
  - 代码构建、测试、规范检查
  - **用途**：提交前自检，确保质量

- **`TASK_TEMPLATE.md`** - AI任务模板
  - 结构化任务描述模板
  - **用途**：与AI协作时提供清晰的任务描述

- **`CURSOR_BEST_PRACTICES.md`** - Cursor最佳实践 ⭐
  - 基于深度研究的开发规则
  - Token成本控制策略
  - 上下文缓存机制
  - 结构化提示模板
  - **用途**：指导高效使用Cursor + Claude Opus 4.5

## 🚀 使用指南

### 对于开发者

1. **新功能开发前**：阅读`PROJECT_BRIEF.md`和`MODULE_INDEX.md`了解架构
2. **编码时**：遵循`ENGINEERING_RULES.md`中的规范
3. **提交前**：使用`PR_CHECKLIST.md`逐项检查
4. **与AI协作**：
   - 使用`TASK_TEMPLATE.md`编写任务描述
   - 参考`CURSOR_BEST_PRACTICES.md`优化Token使用
   - 使用上下文缓存避免重复分析

### 对于AI (Cursor)

- `.cursor-rules.mdc`会自动加载，AI会遵循其中的规则
- 生成代码时会参考`PROJECT_BRIEF.md`和`MODULE_INDEX.md`
- 建议在提示中引用相关规范文件

## 📝 维护说明

- **更新频率**：当项目架构或规范发生重大变更时更新
- **版本控制**：所有文件纳入Git版本控制
- **审查周期**：每个开发阶段结束后审查并更新

## 🔗 相关文档

- 项目根目录：`/extension/`
- 架构文档：`/extension/docs/`
- 策略优化器文档：`/extension/docs/07_workflow/策略优化器学习引擎文档.md`
- Cursor最佳实践：`/extension/development_templates_and_rules/CURSOR_BEST_PRACTICES.md`

---

**最后更新**：2025-12-04  
**维护者**：TRQuant Team

