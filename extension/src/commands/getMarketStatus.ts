/**
 * 获取市场状态命令
 * ==================
 * 
 * 功能：
 * - 获取A股市场当前状态（Regime）
 * - 显示指数趋势和风格轮动
 * - 生成AI Prompt
 * 
 * 遵循：
 * - 单一职责原则
 * - 命令模式
 */

import * as vscode from 'vscode';
import { TRQuantClient } from '../services/trquantClient';
import { logger } from '../utils/logger';
import { ErrorHandler } from '../utils/errors';
import { MarketStatus, MarketRegime } from '../types';

const MODULE = 'GetMarketStatus';

/**
 * 执行获取市场状态命令
 */
export async function getMarketStatus(
    client: TRQuantClient,
    context: vscode.ExtensionContext
): Promise<void> {
    logger.info('执行获取市场状态命令', MODULE);

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: "TRQuant",
        cancellable: true
    }, async (progress, token) => {
        try {
            progress.report({ message: '正在获取市场状态...', increment: 0 });

            // 检查取消
            if (token.isCancellationRequested) {
                logger.info('用户取消操作', MODULE);
                return;
            }

            const result = await client.getMarketStatus({
                universe: 'CN_EQ',
                as_of: new Date().toISOString().split('T')[0]
            });

            progress.report({ increment: 50 });

            if (!result.ok || !result.data) {
                vscode.window.showErrorMessage(`获取市场状态失败: ${result.error || '未知错误'}`);
                return;
            }

            const data = result.data;
            logger.info(`市场状态: ${data.regime}`, MODULE);

            progress.report({ message: '渲染结果...', increment: 30 });

            // 创建WebView显示结果
            const panel = createMarketStatusPanel(context, data);

            progress.report({ increment: 20 });

            // 提供后续操作
            showFollowUpActions(data);

        } catch (error) {
            ErrorHandler.handle(error, MODULE);
        }
    });
}

/**
 * 创建市场状态WebView面板
 */
function createMarketStatusPanel(
    context: vscode.ExtensionContext,
    data: MarketStatus
): vscode.WebviewPanel {
    const panel = vscode.window.createWebviewPanel(
        'trquantMarketStatus',
        '📊 市场状态',
        vscode.ViewColumn.Beside,
        { 
            enableScripts: true,
            retainContextWhenHidden: true
        }
    );

    panel.webview.html = generateWebviewHtml(data);

    // 处理WebView消息
    panel.webview.onDidReceiveMessage(
        async (message) => {
            switch (message.command) {
                case 'copyPrompt':
                    const prompt = generatePrompt(data);
                    await vscode.env.clipboard.writeText(prompt);
                    vscode.window.showInformationMessage('Prompt已复制到剪贴板');
                    break;
                case 'refresh':
                    // 重新执行命令
                    vscode.commands.executeCommand('trquant.getMarketStatus');
                    panel.dispose();
                    break;
            }
        },
        undefined,
        context.subscriptions
    );

    return panel;
}

/**
 * 生成WebView HTML内容
 */
function generateWebviewHtml(data: MarketStatus): string {
    const regimeInfo = getRegimeInfo(data.regime);
    const indexTrendHtml = generateIndexTrendHtml(data.index_trend);
    const styleRotationHtml = generateStyleRotationHtml(data.style_rotation);

    return `<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>市场状态</title>
    <style>
        :root {
            --bg-primary: #1a1a2e;
            --bg-secondary: #252540;
            --bg-tertiary: #2d2d4a;
            --text-primary: #ffffff;
            --text-secondary: #9ca3af;
            --text-muted: #6b7280;
            --primary: #667eea;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --border: #3d3d5c;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            padding: 24px;
            line-height: 1.6;
        }

        .header {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border);
        }

        .header-icon { font-size: 36px; }

        .header-content { flex: 1; }

        .header-title {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 4px;
        }

        .header-subtitle {
            color: var(--text-secondary);
            font-size: 14px;
        }

        .regime-badge {
            background: ${regimeInfo.color};
            color: white;
            padding: 8px 20px;
            border-radius: 24px;
            font-weight: 600;
            font-size: 14px;
            text-transform: uppercase;
        }

        .card {
            background: var(--bg-secondary);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 16px;
            border: 1px solid var(--border);
        }

        .card-title {
            font-size: 14px;
            color: var(--text-secondary);
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .card-title::before {
            content: '';
            width: 4px;
            height: 16px;
            background: var(--primary);
            border-radius: 2px;
        }

        .trend-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
        }

        .trend-item {
            background: var(--bg-tertiary);
            border-radius: 12px;
            padding: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .trend-name {
            font-weight: 500;
            font-size: 14px;
        }

        .trend-value {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .trend-direction {
            font-size: 18px;
        }

        .zscore {
            font-size: 13px;
            color: var(--text-secondary);
        }

        .positive { color: var(--success); }
        .negative { color: var(--danger); }
        .neutral { color: var(--warning); }

        .style-list {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
        }

        .style-item {
            background: var(--bg-tertiary);
            border-radius: 12px;
            padding: 12px 20px;
            display: flex;
            align-items: center;
            gap: 12px;
            flex: 1;
            min-width: 150px;
        }

        .style-name { font-weight: 500; }

        .style-score {
            margin-left: auto;
            font-weight: 600;
            font-size: 18px;
        }

        .summary-card {
            background: linear-gradient(135deg, ${regimeInfo.color}22, ${regimeInfo.color}11);
            border-left: 4px solid ${regimeInfo.color};
        }

        .summary-text {
            color: var(--text-primary);
            font-size: 15px;
            line-height: 1.8;
        }

        .actions {
            display: flex;
            gap: 12px;
            margin-top: 24px;
        }

        .btn {
            padding: 12px 24px;
            border-radius: 10px;
            border: none;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s;
        }

        .btn-primary {
            background: var(--primary);
            color: white;
        }

        .btn-primary:hover {
            background: #5a6fd6;
        }

        .btn-secondary {
            background: var(--bg-tertiary);
            color: var(--text-primary);
        }

        .btn-secondary:hover {
            background: #3d3d5c;
        }

        .timestamp {
            text-align: center;
            color: var(--text-muted);
            font-size: 12px;
            margin-top: 24px;
        }
    </style>
</head>
<body>
    <div class="header">
        <span class="header-icon">${regimeInfo.icon}</span>
        <div class="header-content">
            <div class="header-title">A股市场状态</div>
            <div class="header-subtitle">基于多维度指标综合分析</div>
        </div>
        <span class="regime-badge">${data.regime}</span>
    </div>

    <div class="card summary-card">
        <div class="card-title">分析结论</div>
        <div class="summary-text">${data.summary || regimeInfo.description}</div>
    </div>

    <div class="card">
        <div class="card-title">指数趋势</div>
        <div class="trend-grid">
            ${indexTrendHtml}
        </div>
    </div>

    <div class="card">
        <div class="card-title">风格轮动</div>
        <div class="style-list">
            ${styleRotationHtml}
        </div>
    </div>

    <div class="actions">
        <button class="btn btn-primary" onclick="copyPrompt()">
            📋 复制为AI Prompt
        </button>
        <button class="btn btn-secondary" onclick="refresh()">
            🔄 刷新数据
        </button>
    </div>

    <div class="timestamp">
        更新时间: ${new Date().toLocaleString('zh-CN')}
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        
        function copyPrompt() {
            vscode.postMessage({ command: 'copyPrompt' });
        }
        
        function refresh() {
            vscode.postMessage({ command: 'refresh' });
        }
    </script>
</body>
</html>`;
}

/**
 * 获取Regime信息
 */
function getRegimeInfo(regime: MarketRegime): {
    icon: string;
    color: string;
    description: string;
} {
    const regimeMap: Record<MarketRegime, { icon: string; color: string; description: string }> = {
        'risk_on': {
            icon: '📈',
            color: '#10b981',
            description: '当前市场风险偏好上升，适合积极配置成长股和高Beta资产。建议关注科技、新能源等高成长板块。'
        },
        'risk_off': {
            icon: '📉',
            color: '#ef4444',
            description: '当前市场风险偏好下降，建议防御性配置。可关注高分红、低波动的价值股，适当降低仓位。'
        },
        'neutral': {
            icon: '➡️',
            color: '#f59e0b',
            description: '当前市场处于震荡格局，建议均衡配置。可采用市场中性策略，控制风险敞口。'
        }
    };

    return regimeMap[regime] || regimeMap['neutral'];
}

/**
 * 生成指数趋势HTML
 */
function generateIndexTrendHtml(indexTrend: Record<string, { zscore: number; trend: string }>): string {
    const indexNames: Record<string, string> = {
        'SH000300': '沪深300',
        'SZ399006': '创业板指',
        'SH000016': '上证50',
        'SZ399905': '中证500'
    };

    return Object.entries(indexTrend)
        .map(([code, info]) => {
            const name = indexNames[code] || code;
            const trendIcon = info.trend === 'up' ? '↑' : info.trend === 'down' ? '↓' : '→';
            const colorClass = info.zscore > 0 ? 'positive' : info.zscore < 0 ? 'negative' : 'neutral';

            return `
                <div class="trend-item">
                    <span class="trend-name">${name}</span>
                    <div class="trend-value">
                        <span class="trend-direction ${colorClass}">${trendIcon}</span>
                        <span class="zscore">(${info.zscore >= 0 ? '+' : ''}${info.zscore.toFixed(2)})</span>
                    </div>
                </div>
            `;
        })
        .join('');
}

/**
 * 生成风格轮动HTML
 */
function generateStyleRotationHtml(styleRotation: Array<{ style: string; score: number }>): string {
    const styleNames: Record<string, string> = {
        'growth': '成长',
        'value': '价值',
        'momentum': '动量',
        'quality': '质量',
        'size': '市值'
    };

    return styleRotation
        .map(item => {
            const name = styleNames[item.style] || item.style;
            const colorClass = item.score > 0 ? 'positive' : item.score < 0 ? 'negative' : 'neutral';
            const sign = item.score > 0 ? '+' : '';

            return `
                <div class="style-item">
                    <span class="style-name">${name}</span>
                    <span class="style-score ${colorClass}">${sign}${item.score.toFixed(2)}</span>
                </div>
            `;
        })
        .join('');
}

/**
 * 生成AI Prompt
 */
function generatePrompt(data: MarketStatus): string {
    const regimeInfo = getRegimeInfo(data.regime);
    
    return `# A股市场状态分析

## 市场Regime: ${data.regime.toUpperCase()}
${regimeInfo.description}

## 指数趋势
${Object.entries(data.index_trend)
    .map(([code, info]) => `- ${code}: ${info.trend} (动量: ${info.zscore >= 0 ? '+' : ''}${info.zscore.toFixed(2)})`)
    .join('\n')}

## 风格轮动
${data.style_rotation
    .map(s => `- ${s.style}: ${s.score > 0 ? '占优' : '弱势'} (${s.score >= 0 ? '+' : ''}${s.score.toFixed(2)})`)
    .join('\n')}

## 分析总结
${data.summary || regimeInfo.description}

---
请基于以上市场状态，帮我生成适合当前市场环境的PTrade量化策略代码。要求：
1. 根据市场Regime选择合适的策略风格
2. 包含完整的风控逻辑（止损8%，止盈20%）
3. 单票最大仓位10%
4. 添加详细的中文注释
`;
}

/**
 * 显示后续操作选项
 */
async function showFollowUpActions(data: MarketStatus): Promise<void> {
    const action = await vscode.window.showInformationMessage(
        `市场状态: ${data.regime.toUpperCase()}`,
        '复制Prompt',
        '生成策略',
        '查看主线'
    );

    switch (action) {
        case '复制Prompt':
            const prompt = generatePrompt(data);
            await vscode.env.clipboard.writeText(prompt);
            vscode.window.showInformationMessage('Prompt已复制到剪贴板');
            break;
        case '生成策略':
            vscode.commands.executeCommand('trquant.generateStrategy');
            break;
        case '查看主线':
            vscode.commands.executeCommand('trquant.getMainlines');
            break;
    }
}
