# -*- coding: utf-8 -*-
"""
趋势历史图表生成器
==================

生成带趋势状态背景着色的K线图表，用于可视化历史趋势变化。

功能：
1. K线图 + 成交量
2. 趋势状态背景着色（绿色=上涨，红色=下跌，灰色=震荡）
3. 多周期趋势信号叠加
4. 技术指标叠加（MA、MACD等）
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from io import BytesIO
import base64
import logging

logger = logging.getLogger(__name__)

# 尝试导入绘图库
try:
    import matplotlib
    matplotlib.use('Agg')  # 非GUI后端
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.patches import Rectangle
    from matplotlib.collections import PatchCollection
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("matplotlib未安装，趋势图表功能不可用")


class TrendChartGenerator:
    """趋势历史图表生成器"""
    
    # 趋势颜色定义
    TREND_COLORS = {
        "strong_up": "#22c55e33",      # 强势上涨 - 绿色透明
        "up": "#84cc1633",              # 上涨 - 浅绿透明
        "weak_up": "#a3e63533",         # 弱势上涨 - 更浅绿
        "sideways": "#94a3b833",        # 震荡 - 灰色透明
        "weak_down": "#fbbf2433",       # 弱势下跌 - 黄色透明
        "down": "#f9731633",            # 下跌 - 橙色透明
        "strong_down": "#ef444433",     # 强势下跌 - 红色透明
    }
    
    def __init__(self, jq_client=None):
        self.jq_client = jq_client
        self._use_english_labels = False
        self._setup_style()
    
    def _setup_style(self):
        """设置图表样式"""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        # 查找可用的中文字体
        font_found = False
        font_candidates = [
            'Noto Sans CJK SC', 'Noto Sans CJK JP', 'Noto Sans CJK TC',
            'WenQuanYi Micro Hei', 'WenQuanYi Zen Hei', 
            'SimHei', 'Microsoft YaHei', 'STHeiti',
            'Source Han Sans SC', 'Source Han Sans CN'
        ]
        
        try:
            from matplotlib import font_manager
            available_fonts = set(f.name for f in font_manager.fontManager.ttflist)
            
            for font in font_candidates:
                if font in available_fonts:
                    plt.rcParams['font.sans-serif'] = [font, 'DejaVu Sans']
                    font_found = True
                    logger.info(f"图表使用中文字体: {font}")
                    break
        except Exception as e:
            logger.warning(f"检测中文字体失败: {e}")
        
        if not font_found:
            # 使用默认字体，标题改用英文
            plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
            logger.warning("未找到中文字体，将使用英文标签")
            self._use_english_labels = True
        else:
            self._use_english_labels = False
        
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['figure.facecolor'] = '#1a1a2e'
        plt.rcParams['axes.facecolor'] = '#16213e'
        plt.rcParams['axes.edgecolor'] = '#4a5568'
        plt.rcParams['axes.labelcolor'] = '#e2e8f0'
        plt.rcParams['xtick.color'] = '#a0aec0'
        plt.rcParams['ytick.color'] = '#a0aec0'
        plt.rcParams['grid.color'] = '#2d3748'
        plt.rcParams['text.color'] = '#e2e8f0'
    
    def generate_trend_chart(
        self,
        index_code: str = "000001.XSHG",
        days: int = 120,
        period: str = "medium",
        show_ma: bool = True,
        show_volume: bool = True,
        figsize: Tuple[int, int] = (14, 10)
    ) -> Optional[str]:
        """
        生成趋势历史图表
        
        Args:
            index_code: 指数代码
            days: 显示天数
            period: 趋势周期 (short/medium/long)
            show_ma: 是否显示均线
            show_volume: 是否显示成交量
            figsize: 图表尺寸
            
        Returns:
            Base64编码的PNG图片
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib不可用")
            return None
        
        try:
            # 获取数据
            df = self._get_price_data(index_code, days + 50)  # 多取50天用于计算指标
            if df is None or df.empty:
                logger.warning(f"无法获取{index_code}数据")
                return None
            
            # 计算趋势信号
            df = self._calculate_trend_signals(df, period)
            
            # 只保留最近days天用于显示
            df = df.tail(days).reset_index(drop=True)
            
            # 生成图表
            fig = self._create_chart(df, index_code, period, show_ma, show_volume, figsize)
            
            # 转换为Base64
            buf = BytesIO()
            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight',
                       facecolor=fig.get_facecolor(), edgecolor='none')
            plt.close(fig)
            buf.seek(0)
            
            return base64.b64encode(buf.read()).decode('utf-8')
            
        except Exception as e:
            logger.error(f"生成趋势图表失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_price_data(self, code: str, days: int) -> Optional[pd.DataFrame]:
        """获取价格数据"""
        try:
            import jqdatasdk as jq
            
            # 确定结束日期
            if self.jq_client:
                perm = self.jq_client.get_permission()
                end_date = perm.end_date if perm else "2025-08-29"
            else:
                end_date = "2025-08-29"
            
            df = jq.get_price(
                code,
                end_date=end_date,
                count=days,
                frequency='daily',
                fields=['open', 'high', 'low', 'close', 'volume']
            )
            
            if df is not None and not df.empty:
                df = df.reset_index()
                if 'index' in df.columns:
                    df = df.rename(columns={'index': 'date'})
                return df
            
            return None
            
        except Exception as e:
            logger.error(f"获取价格数据失败: {e}")
            return None
    
    def _calculate_trend_signals(self, df: pd.DataFrame, period: str) -> pd.DataFrame:
        """计算趋势信号"""
        # 根据周期设置参数
        if period == "short":
            ma_fast, ma_slow = 5, 20
        elif period == "long":
            ma_fast, ma_slow = 60, 120
        else:  # medium
            ma_fast, ma_slow = 20, 60
        
        # 计算均线
        df['ma_fast'] = df['close'].rolling(ma_fast).mean()
        df['ma_slow'] = df['close'].rolling(ma_slow).mean()
        
        # 计算MACD
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 计算RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta).where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 计算趋势得分
        df['trend_score'] = 0.0
        
        # 均线得分
        df.loc[df['close'] > df['ma_fast'], 'trend_score'] += 20
        df.loc[df['close'] > df['ma_slow'], 'trend_score'] += 20
        df.loc[df['ma_fast'] > df['ma_slow'], 'trend_score'] += 20
        
        df.loc[df['close'] < df['ma_fast'], 'trend_score'] -= 20
        df.loc[df['close'] < df['ma_slow'], 'trend_score'] -= 20
        df.loc[df['ma_fast'] < df['ma_slow'], 'trend_score'] -= 20
        
        # MACD得分
        df.loc[df['macd_hist'] > 0, 'trend_score'] += 20
        df.loc[df['macd_hist'] < 0, 'trend_score'] -= 20
        
        # RSI得分
        df.loc[df['rsi'] > 50, 'trend_score'] += 20
        df.loc[df['rsi'] < 50, 'trend_score'] -= 20
        
        # 确定趋势状态
        df['trend_state'] = 'sideways'
        df.loc[df['trend_score'] > 60, 'trend_state'] = 'strong_up'
        df.loc[(df['trend_score'] > 30) & (df['trend_score'] <= 60), 'trend_state'] = 'up'
        df.loc[(df['trend_score'] > 0) & (df['trend_score'] <= 30), 'trend_state'] = 'weak_up'
        df.loc[(df['trend_score'] < 0) & (df['trend_score'] >= -30), 'trend_state'] = 'weak_down'
        df.loc[(df['trend_score'] < -30) & (df['trend_score'] >= -60), 'trend_state'] = 'down'
        df.loc[df['trend_score'] < -60, 'trend_state'] = 'strong_down'
        
        return df
    
    def _create_chart(
        self,
        df: pd.DataFrame,
        index_code: str,
        period: str,
        show_ma: bool,
        show_volume: bool,
        figsize: Tuple[int, int]
    ) -> plt.Figure:
        """创建图表"""
        # 确定子图数量
        n_plots = 1 + (1 if show_volume else 0) + 1  # 价格 + 成交量 + MACD
        height_ratios = [3] + ([1] if show_volume else []) + [1]
        
        fig, axes = plt.subplots(n_plots, 1, figsize=figsize, 
                                  gridspec_kw={'height_ratios': height_ratios, 'hspace': 0.05})
        if n_plots == 1:
            axes = [axes]
        
        ax_price = axes[0]
        ax_idx = 1
        
        if show_volume:
            ax_volume = axes[ax_idx]
            ax_idx += 1
        
        ax_macd = axes[ax_idx]
        
        x = range(len(df))
        
        # ===== 绘制趋势背景 =====
        self._draw_trend_background(ax_price, df, x)
        
        # ===== 绘制K线 =====
        self._draw_candlestick(ax_price, df, x)
        
        # ===== 绘制均线 =====
        if show_ma:
            ma_fast, ma_slow = self._get_ma_period(period)
            ax_price.plot(x, df['ma_fast'], color='#fbbf24', linewidth=1.2, 
                         label=f'MA{ma_fast}', alpha=0.9)
            ax_price.plot(x, df['ma_slow'], color='#60a5fa', linewidth=1.2,
                         label=f'MA{ma_slow}', alpha=0.9)
            ax_price.legend(loc='upper left', fontsize=9, framealpha=0.7)
        
        # 设置价格轴
        if self._use_english_labels:
            ax_price.set_ylabel('Price', fontsize=11)
        else:
            ax_price.set_ylabel('价格', fontsize=11)
        ax_price.set_xlim(-1, len(df))
        ax_price.grid(True, alpha=0.3)
        
        # 标题
        if self._use_english_labels:
            period_name = {"short": "Short-term", "medium": "Medium-term", "long": "Long-term"}.get(period, "Medium-term")
            ax_price.set_title(f'{index_code} {period_name} Trend Analysis', fontsize=14, fontweight='bold', pad=10)
        else:
            period_name = {"short": "短期", "medium": "中期", "long": "长期"}.get(period, "中期")
            ax_price.set_title(f'{index_code} {period_name}趋势分析图', fontsize=14, fontweight='bold', pad=10)
        
        # ===== 绘制成交量 =====
        if show_volume:
            self._draw_trend_background(ax_volume, df, x)
            colors = ['#ef4444' if df['close'].iloc[i] < df['open'].iloc[i] else '#22c55e' 
                     for i in range(len(df))]
            ax_volume.bar(x, df['volume'], color=colors, alpha=0.7, width=0.8)
            ax_volume.set_ylabel('Volume' if self._use_english_labels else '成交量', fontsize=10)
            ax_volume.set_xlim(-1, len(df))
            ax_volume.grid(True, alpha=0.3)
        
        # ===== 绘制MACD =====
        self._draw_trend_background(ax_macd, df, x)
        colors = ['#22c55e' if v >= 0 else '#ef4444' for v in df['macd_hist']]
        ax_macd.bar(x, df['macd_hist'], color=colors, alpha=0.7, width=0.8)
        ax_macd.plot(x, df['macd'], color='#60a5fa', linewidth=1, label='MACD')
        ax_macd.plot(x, df['macd_signal'], color='#fbbf24', linewidth=1, label='Signal')
        ax_macd.axhline(y=0, color='#4a5568', linewidth=0.5)
        ax_macd.set_ylabel('MACD', fontsize=10)
        ax_macd.set_xlim(-1, len(df))
        ax_macd.grid(True, alpha=0.3)
        ax_macd.legend(loc='upper left', fontsize=8, framealpha=0.7)
        
        # 设置X轴日期标签
        tick_positions = np.linspace(0, len(df)-1, min(10, len(df))).astype(int)
        tick_labels = [df['date'].iloc[i].strftime('%m-%d') if hasattr(df['date'].iloc[i], 'strftime') 
                      else str(df['date'].iloc[i])[:10] for i in tick_positions]
        ax_macd.set_xticks(tick_positions)
        ax_macd.set_xticklabels(tick_labels, rotation=45, ha='right')
        
        # 隐藏其他轴的X标签
        for ax in axes[:-1]:
            ax.set_xticklabels([])
        
        return fig
    
    def _draw_trend_background(self, ax, df: pd.DataFrame, x):
        """绘制趋势背景色"""
        # 找出连续相同趋势的区间
        current_state = None
        start_idx = 0
        
        for i, state in enumerate(df['trend_state']):
            if state != current_state:
                if current_state is not None:
                    # 绘制上一个区间
                    color = self.TREND_COLORS.get(current_state, '#94a3b833')
                    ax.axvspan(start_idx - 0.5, i - 0.5, facecolor=color, alpha=1)
                current_state = state
                start_idx = i
        
        # 绘制最后一个区间
        if current_state is not None:
            color = self.TREND_COLORS.get(current_state, '#94a3b833')
            ax.axvspan(start_idx - 0.5, len(df) - 0.5, facecolor=color, alpha=1)
    
    def _draw_candlestick(self, ax, df: pd.DataFrame, x):
        """绘制K线"""
        for i in range(len(df)):
            open_price = df['open'].iloc[i]
            close_price = df['close'].iloc[i]
            high_price = df['high'].iloc[i]
            low_price = df['low'].iloc[i]
            
            if close_price >= open_price:
                color = '#22c55e'  # 阳线绿色
                body_bottom = open_price
                body_height = close_price - open_price
            else:
                color = '#ef4444'  # 阴线红色
                body_bottom = close_price
                body_height = open_price - close_price
            
            # 绘制影线
            ax.plot([i, i], [low_price, high_price], color=color, linewidth=1)
            
            # 绘制实体
            if body_height > 0:
                rect = Rectangle((i - 0.35, body_bottom), 0.7, body_height, 
                                 facecolor=color, edgecolor=color)
                ax.add_patch(rect)
            else:
                ax.plot([i - 0.35, i + 0.35], [close_price, close_price], 
                       color=color, linewidth=1.5)
    
    def _get_ma_period(self, period: str) -> Tuple[int, int]:
        """获取均线周期"""
        if period == "short":
            return (5, 20)
        elif period == "long":
            return (60, 120)
        else:
            return (20, 60)
    
    def get_trend_history(
        self,
        index_code: str = "000001.XSHG",
        days: int = 60
    ) -> List[Dict]:
        """
        获取趋势历史数据
        
        Returns:
            趋势历史列表，每项包含日期、趋势状态、得分等
        """
        try:
            df = self._get_price_data(index_code, days + 50)
            if df is None:
                return []
            
            df = self._calculate_trend_signals(df, "medium")
            df = df.tail(days)
            
            history = []
            for _, row in df.iterrows():
                history.append({
                    "date": row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']),
                    "close": row['close'],
                    "trend_state": row['trend_state'],
                    "trend_score": row['trend_score'],
                    "ma_fast": row['ma_fast'],
                    "ma_slow": row['ma_slow'],
                    "rsi": row['rsi']
                })
            
            return history
            
        except Exception as e:
            logger.error(f"获取趋势历史失败: {e}")
            return []


def create_trend_chart_generator(jq_client=None) -> TrendChartGenerator:
    """创建趋势图表生成器"""
    return TrendChartGenerator(jq_client=jq_client)

