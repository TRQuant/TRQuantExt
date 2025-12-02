# -*- coding: utf-8 -*-
"""
趋势预警与通知模块
==================

功能：
1. 趋势转折检测
2. 异常波动警报
3. 预警消息推送（桌面通知、日志）
4. 预警历史记录
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """预警级别"""
    INFO = "信息"
    WARNING = "警告"
    CRITICAL = "严重"


class AlertType(Enum):
    """预警类型"""
    TREND_CHANGE = "趋势转折"
    VOLATILITY_SPIKE = "波动异常"
    VOLUME_SPIKE = "成交异常"
    CAPITAL_FLOW = "资金异动"
    MULTI_PERIOD_RESONANCE = "多周期共振"


@dataclass
class TrendAlert:
    """趋势预警"""
    timestamp: datetime
    alert_type: AlertType
    level: AlertLevel
    title: str
    message: str
    details: Dict
    is_read: bool = False


class TrendAlertManager:
    """趋势预警管理器"""
    
    def __init__(self):
        self.alerts: List[TrendAlert] = []
        self.callbacks: List[Callable[[TrendAlert], None]] = []
        self.enabled = True
        
        # 预警阈值
        self.thresholds = {
            'trend_score_change': 30,      # 趋势得分变化阈值
            'volatility_spike': 50,        # 波动率异常阈值(%)
            'volume_spike': 2.0,           # 成交量异常倍数
            'capital_flow_threshold': 50,  # 资金流向阈值(亿)
        }
        
        # 上一次状态（用于对比）
        self._last_state = {}
    
    def register_callback(self, callback: Callable[[TrendAlert], None]):
        """注册预警回调"""
        self.callbacks.append(callback)
    
    def check_trend_change(self, current_result: Dict, previous_result: Optional[Dict] = None) -> List[TrendAlert]:
        """
        检测趋势变化
        
        Args:
            current_result: 当前趋势分析结果
            previous_result: 上一次趋势分析结果
            
        Returns:
            检测到的预警列表
        """
        if not self.enabled:
            return []
        
        alerts = []
        prev = previous_result or self._last_state
        
        if not prev:
            self._last_state = current_result
            return []
        
        try:
            # 1. 检测综合得分变化
            curr_composite = current_result.get('composite_score', 0)
            prev_composite = prev.get('composite_score', 0)
            score_change = curr_composite - prev_composite
            
            if abs(score_change) >= self.thresholds['trend_score_change']:
                level = AlertLevel.WARNING if abs(score_change) < 50 else AlertLevel.CRITICAL
                direction = "上升" if score_change > 0 else "下降"
                
                alert = TrendAlert(
                    timestamp=datetime.now(),
                    alert_type=AlertType.TREND_CHANGE,
                    level=level,
                    title=f"趋势得分大幅{direction}",
                    message=f"综合得分从 {prev_composite:+.0f} 变为 {curr_composite:+.0f}，变化 {score_change:+.0f}",
                    details={
                        'prev_score': prev_composite,
                        'curr_score': curr_composite,
                        'change': score_change
                    }
                )
                alerts.append(alert)
            
            # 2. 检测市场阶段变化
            curr_phase = current_result.get('market_phase', '')
            prev_phase = prev.get('market_phase', '')
            
            if curr_phase != prev_phase and prev_phase:
                # 判断变化的严重性
                bullish_phases = ['牛市启动', '牛市加速', '牛市']
                bearish_phases = ['熊市', '熊市加速', '见顶回落']
                
                is_bull_to_bear = prev_phase in bullish_phases and curr_phase in bearish_phases
                is_bear_to_bull = prev_phase in bearish_phases and curr_phase in bullish_phases
                
                if is_bull_to_bear or is_bear_to_bull:
                    level = AlertLevel.CRITICAL
                    title = "市场阶段重大转变"
                else:
                    level = AlertLevel.WARNING
                    title = "市场阶段变化"
                
                alert = TrendAlert(
                    timestamp=datetime.now(),
                    alert_type=AlertType.TREND_CHANGE,
                    level=level,
                    title=title,
                    message=f"市场阶段从 [{prev_phase}] 转变为 [{curr_phase}]",
                    details={
                        'prev_phase': prev_phase,
                        'curr_phase': curr_phase
                    }
                )
                alerts.append(alert)
            
            # 3. 检测多周期共振
            self._check_resonance(current_result, alerts)
            
            # 更新状态
            self._last_state = current_result
            
            # 触发回调
            for alert in alerts:
                self.alerts.append(alert)
                self._trigger_callbacks(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"检测趋势变化失败: {e}")
            return []
    
    def _check_resonance(self, result: Dict, alerts: List[TrendAlert]):
        """检测多周期共振"""
        try:
            short_score = result.get('short_term', {}).get('score', 0)
            medium_score = result.get('medium_term', {}).get('score', 0)
            long_score = result.get('long_term', {}).get('score', 0)
            
            # 三周期同向看多
            if short_score > 30 and medium_score > 30 and long_score > 30:
                alert = TrendAlert(
                    timestamp=datetime.now(),
                    alert_type=AlertType.MULTI_PERIOD_RESONANCE,
                    level=AlertLevel.WARNING,
                    title="⬆️ 多周期共振看多",
                    message=f"短期({short_score:+.0f}) + 中期({medium_score:+.0f}) + 长期({long_score:+.0f}) 全部看多",
                    details={'short': short_score, 'medium': medium_score, 'long': long_score}
                )
                alerts.append(alert)
            
            # 三周期同向看空
            elif short_score < -30 and medium_score < -30 and long_score < -30:
                alert = TrendAlert(
                    timestamp=datetime.now(),
                    alert_type=AlertType.MULTI_PERIOD_RESONANCE,
                    level=AlertLevel.CRITICAL,
                    title="⬇️ 多周期共振看空",
                    message=f"短期({short_score:+.0f}) + 中期({medium_score:+.0f}) + 长期({long_score:+.0f}) 全部看空",
                    details={'short': short_score, 'medium': medium_score, 'long': long_score}
                )
                alerts.append(alert)
                
        except Exception as e:
            logger.debug(f"共振检测失败: {e}")
    
    def check_capital_flow_alert(self, flow_score: float, net_inflow: float) -> Optional[TrendAlert]:
        """检测资金流向异动"""
        if not self.enabled:
            return None
        
        try:
            threshold = self.thresholds['capital_flow_threshold']
            
            if abs(net_inflow) >= threshold:
                if net_inflow > 0:
                    alert = TrendAlert(
                        timestamp=datetime.now(),
                        alert_type=AlertType.CAPITAL_FLOW,
                        level=AlertLevel.WARNING,
                        title="📈 大额资金流入",
                        message=f"北向资金净流入 {net_inflow:.1f} 亿元",
                        details={'net_inflow': net_inflow, 'flow_score': flow_score}
                    )
                else:
                    alert = TrendAlert(
                        timestamp=datetime.now(),
                        alert_type=AlertType.CAPITAL_FLOW,
                        level=AlertLevel.WARNING,
                        title="📉 大额资金流出",
                        message=f"北向资金净流出 {abs(net_inflow):.1f} 亿元",
                        details={'net_inflow': net_inflow, 'flow_score': flow_score}
                    )
                
                self.alerts.append(alert)
                self._trigger_callbacks(alert)
                return alert
            
            return None
            
        except Exception as e:
            logger.error(f"资金流向预警检测失败: {e}")
            return None
    
    def _trigger_callbacks(self, alert: TrendAlert):
        """触发预警回调"""
        for callback in self.callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"预警回调执行失败: {e}")
    
    def get_unread_alerts(self) -> List[TrendAlert]:
        """获取未读预警"""
        return [a for a in self.alerts if not a.is_read]
    
    def get_recent_alerts(self, count: int = 10) -> List[TrendAlert]:
        """获取最近预警"""
        return sorted(self.alerts, key=lambda x: x.timestamp, reverse=True)[:count]
    
    def mark_as_read(self, alert: TrendAlert):
        """标记为已读"""
        alert.is_read = True
    
    def mark_all_read(self):
        """全部标记已读"""
        for alert in self.alerts:
            alert.is_read = True
    
    def clear_alerts(self):
        """清空预警"""
        self.alerts.clear()
    
    def set_threshold(self, key: str, value: float):
        """设置预警阈值"""
        if key in self.thresholds:
            self.thresholds[key] = value
            logger.info(f"预警阈值已更新: {key} = {value}")
    
    def enable(self):
        """启用预警"""
        self.enabled = True
    
    def disable(self):
        """禁用预警"""
        self.enabled = False


def create_alert_manager() -> TrendAlertManager:
    """创建预警管理器"""
    return TrendAlertManager()


# 桌面通知功能（可选）
def send_desktop_notification(alert: TrendAlert):
    """发送桌面通知"""
    try:
        import subprocess
        
        icon = "dialog-warning" if alert.level == AlertLevel.WARNING else "dialog-error"
        urgency = "normal" if alert.level == AlertLevel.WARNING else "critical"
        
        subprocess.run([
            'notify-send',
            '-i', icon,
            '-u', urgency,
            f'韬睿量化 - {alert.title}',
            alert.message
        ], check=False)
        
    except Exception as e:
        logger.debug(f"桌面通知发送失败: {e}")

