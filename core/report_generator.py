# -*- coding: utf-8 -*-
"""
回测报告生成器
==============

自动生成PDF格式的回测报告

功能:
1. 绩效摘要
2. 净值曲线图
3. 回撤分析
4. 交易记录
5. 风险分析
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import io

logger = logging.getLogger(__name__)

# 尝试导入PDF库
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image, PageBreak
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("ReportLab未安装，PDF报告功能不可用")


class ReportGenerator:
    """回测报告生成器"""
    
    def __init__(self):
        self.styles = None
        self._register_fonts()
    
    def _register_fonts(self):
        """注册中文字体"""
        if not REPORTLAB_AVAILABLE:
            return
        
        font_paths = [
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        ]
        
        for font_path in font_paths:
            if Path(font_path).exists():
                try:
                    pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                    logger.info(f"注册中文字体: {font_path}")
                    return
                except:
                    continue
        
        logger.warning("未找到中文字体，使用默认字体")
    
    def generate_report(self, 
                       backtest_result: Dict,
                       output_path: str = None,
                       strategy_name: str = "多因子选股策略") -> str:
        """
        生成回测报告PDF
        
        Args:
            backtest_result: 回测结果字典
            output_path: 输出路径
            strategy_name: 策略名称
        
        Returns:
            生成的PDF文件路径
        """
        if not REPORTLAB_AVAILABLE:
            return self._generate_text_report(backtest_result, output_path, strategy_name)
        
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"回测报告_{strategy_name}_{timestamp}.pdf"
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        self.styles = getSampleStyleSheet()
        self._add_custom_styles()
        
        story = []
        
        # 封面
        story.extend(self._create_cover(strategy_name, backtest_result))
        story.append(PageBreak())
        
        # 绩效摘要
        story.extend(self._create_performance_summary(backtest_result))
        story.append(Spacer(1, 1*cm))
        
        # 风险指标
        story.extend(self._create_risk_metrics(backtest_result))
        story.append(PageBreak())
        
        # 月度收益
        story.extend(self._create_monthly_returns(backtest_result))
        story.append(Spacer(1, 1*cm))
        
        # 交易记录
        story.extend(self._create_trade_records(backtest_result))
        
        doc.build(story)
        logger.info(f"PDF报告已生成: {output_path}")
        
        return output_path
    
    def _add_custom_styles(self):
        """添加自定义样式"""
        self.styles.add(ParagraphStyle(
            name='ChineseTitle',
            fontName='ChineseFont' if REPORTLAB_AVAILABLE else 'Helvetica',
            fontSize=24,
            leading=30,
            alignment=1,
            spaceAfter=20
        ))
        
        self.styles.add(ParagraphStyle(
            name='ChineseHeading',
            fontName='ChineseFont' if REPORTLAB_AVAILABLE else 'Helvetica',
            fontSize=14,
            leading=18,
            spaceAfter=10,
            textColor=colors.darkblue
        ))
        
        self.styles.add(ParagraphStyle(
            name='ChineseBody',
            fontName='ChineseFont' if REPORTLAB_AVAILABLE else 'Helvetica',
            fontSize=10,
            leading=14
        ))
    
    def _create_cover(self, strategy_name: str, result: Dict) -> List:
        """创建封面"""
        elements = []
        
        elements.append(Spacer(1, 5*cm))
        elements.append(Paragraph(f"量化策略回测报告", self.styles['ChineseTitle']))
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph(f"策略: {strategy_name}", self.styles['ChineseHeading']))
        
        summary = result.get('summary', {})
        elements.append(Spacer(1, 2*cm))
        
        info_text = f"""
        <para align="center">
        回测区间: {summary.get('start_date', 'N/A')} 至 {summary.get('end_date', 'N/A')}<br/>
        初始资金: ¥{summary.get('initial_capital', 1000000):,.0f}<br/>
        生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
        </para>
        """
        elements.append(Paragraph(info_text, self.styles['ChineseBody']))
        
        return elements
    
    def _create_performance_summary(self, result: Dict) -> List:
        """创建绩效摘要"""
        elements = []
        elements.append(Paragraph("一、绩效摘要", self.styles['ChineseHeading']))
        
        metrics = result.get('metrics', {})
        
        data = [
            ['指标', '数值', '指标', '数值'],
            ['总收益率', f"{metrics.get('total_return', 0)*100:.2f}%",
             '年化收益率', f"{metrics.get('annual_return', 0)*100:.2f}%"],
            ['夏普比率', f"{metrics.get('sharpe_ratio', 0):.2f}",
             '最大回撤', f"{abs(metrics.get('max_drawdown', 0))*100:.2f}%"],
            ['胜率', f"{metrics.get('win_rate', 0)*100:.1f}%",
             '盈亏比', f"{metrics.get('profit_loss_ratio', 0):.2f}"],
            ['波动率', f"{metrics.get('volatility', 0)*100:.2f}%",
             '交易次数', f"{metrics.get('total_trades', 0)}"],
        ]
        
        table = Table(data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'ChineseFont' if REPORTLAB_AVAILABLE else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(table)
        return elements
    
    def _create_risk_metrics(self, result: Dict) -> List:
        """创建风险指标"""
        elements = []
        elements.append(Paragraph("二、风险指标", self.styles['ChineseHeading']))
        
        metrics = result.get('metrics', {})
        
        data = [
            ['指标', '数值', '说明'],
            ['卡尔玛比率', f"{metrics.get('calmar_ratio', 0):.2f}", '年化收益/最大回撤'],
            ['索提诺比率', f"{metrics.get('sortino_ratio', 0):.2f}", '下行风险调整收益'],
            ['基准收益率', f"{metrics.get('benchmark_return', 0)*100:.2f}%", '基准指数收益'],
        ]
        
        table = Table(data, colWidths=[4*cm, 4*cm, 8*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'ChineseFont' if REPORTLAB_AVAILABLE else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(table)
        return elements
    
    def _create_monthly_returns(self, result: Dict) -> List:
        """创建月度收益表"""
        elements = []
        elements.append(Paragraph("三、月度收益", self.styles['ChineseHeading']))
        
        # 如果有月度数据则显示，否则显示提示
        elements.append(Paragraph(
            "（详细月度收益数据请参阅回测系统的图表展示）",
            self.styles['ChineseBody']
        ))
        
        return elements
    
    def _create_trade_records(self, result: Dict) -> List:
        """创建交易记录"""
        elements = []
        elements.append(Paragraph("四、交易记录（最近20条）", self.styles['ChineseHeading']))
        
        trades = result.get('trades', [])[-20:]
        
        if not trades:
            elements.append(Paragraph("暂无交易记录", self.styles['ChineseBody']))
            return elements
        
        data = [['日期', '股票', '方向', '价格', '数量', '金额']]
        
        for trade in trades:
            data.append([
                str(trade.get('date', ''))[:10],
                trade.get('code', ''),
                trade.get('direction', ''),
                f"¥{trade.get('price', 0):.2f}",
                str(trade.get('quantity', 0)),
                f"¥{trade.get('amount', 0):,.0f}"
            ])
        
        table = Table(data, colWidths=[2.5*cm, 3*cm, 2*cm, 2.5*cm, 2*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'ChineseFont' if REPORTLAB_AVAILABLE else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(table)
        return elements
    
    def _generate_text_report(self, result: Dict, output_path: str, strategy_name: str) -> str:
        """生成文本报告（ReportLab不可用时的备选）"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"回测报告_{strategy_name}_{timestamp}.txt"
        
        metrics = result.get('metrics', {})
        summary = result.get('summary', {})
        
        report = f"""
═══════════════════════════════════════════════════════════════
                    量化策略回测报告
═══════════════════════════════════════════════════════════════

策略名称: {strategy_name}
回测区间: {summary.get('start_date', 'N/A')} 至 {summary.get('end_date', 'N/A')}
初始资金: ¥{summary.get('initial_capital', 1000000):,.0f}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

═══════════════════════════════════════════════════════════════
                      绩效摘要
═══════════════════════════════════════════════════════════════

总收益率:     {metrics.get('total_return', 0)*100:>10.2f}%
年化收益率:   {metrics.get('annual_return', 0)*100:>10.2f}%
夏普比率:     {metrics.get('sharpe_ratio', 0):>10.2f}
最大回撤:     {abs(metrics.get('max_drawdown', 0))*100:>10.2f}%
胜率:         {metrics.get('win_rate', 0)*100:>10.1f}%
盈亏比:       {metrics.get('profit_loss_ratio', 0):>10.2f}
波动率:       {metrics.get('volatility', 0)*100:>10.2f}%
交易次数:     {metrics.get('total_trades', 0):>10}

═══════════════════════════════════════════════════════════════
                      风险指标
═══════════════════════════════════════════════════════════════

卡尔玛比率:   {metrics.get('calmar_ratio', 0):>10.2f}
索提诺比率:   {metrics.get('sortino_ratio', 0):>10.2f}
基准收益率:   {metrics.get('benchmark_return', 0)*100:>10.2f}%

═══════════════════════════════════════════════════════════════
                韬睿量化 - TRQuant
═══════════════════════════════════════════════════════════════
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"文本报告已生成: {output_path}")
        return output_path


def generate_backtest_report(result: Dict, output_path: str = None, 
                            strategy_name: str = "多因子选股策略") -> str:
    """
    生成回测报告
    
    Args:
        result: 回测结果
        output_path: 输出路径
        strategy_name: 策略名称
    
    Returns:
        报告文件路径
    """
    generator = ReportGenerator()
    return generator.generate_report(result, output_path, strategy_name)

