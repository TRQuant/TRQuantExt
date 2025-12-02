# -*- coding: utf-8 -*-
"""
通知管理器
==========

支持多渠道消息推送：
1. 桌面通知
2. 邮件通知
3. 企业微信/钉钉
4. Telegram Bot

通知类型：
- 趋势变化预警
- 资金异动提醒
- 策略信号通知
- 系统状态报告
"""

import logging
import smtplib
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """通知类型"""
    TREND_ALERT = "trend_alert"          # 趋势预警
    CAPITAL_FLOW = "capital_flow"        # 资金异动
    STRATEGY_SIGNAL = "strategy_signal"  # 策略信号
    SYSTEM_STATUS = "system_status"      # 系统状态
    CUSTOM = "custom"                     # 自定义


class NotificationPriority(Enum):
    """通知优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationChannel(Enum):
    """通知渠道"""
    DESKTOP = "desktop"        # 桌面通知
    EMAIL = "email"            # 邮件
    WECHAT_WORK = "wechat"     # 企业微信
    DINGTALK = "dingtalk"      # 钉钉
    TELEGRAM = "telegram"      # Telegram
    WEBHOOK = "webhook"        # 自定义Webhook


@dataclass
class NotificationMessage:
    """通知消息"""
    title: str
    content: str
    type: NotificationType = NotificationType.CUSTOM
    priority: NotificationPriority = NotificationPriority.NORMAL
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'title': self.title,
            'content': self.content,
            'type': self.type.value,
            'priority': self.priority.value,
            'timestamp': self.timestamp,
            'data': self.data
        }


@dataclass
class ChannelConfig:
    """渠道配置"""
    enabled: bool = False
    config: Dict[str, Any] = field(default_factory=dict)


class NotificationManager:
    """
    通知管理器
    
    功能：
    1. 多渠道消息推送
    2. 消息队列管理
    3. 发送状态追踪
    4. 配置管理
    """
    
    CONFIG_FILE = Path.home() / '.trquant' / 'notification_config.json'
    
    def __init__(self):
        self._channels: Dict[NotificationChannel, ChannelConfig] = {}
        self._message_history: List[Dict] = []
        self._max_history = 100
        self._lock = threading.Lock()
        
        # 初始化配置
        self._load_config()
        
        # 注册默认渠道处理器
        self._handlers: Dict[NotificationChannel, Callable] = {
            NotificationChannel.DESKTOP: self._send_desktop,
            NotificationChannel.EMAIL: self._send_email,
            NotificationChannel.WECHAT_WORK: self._send_wechat_work,
            NotificationChannel.DINGTALK: self._send_dingtalk,
            NotificationChannel.TELEGRAM: self._send_telegram,
            NotificationChannel.WEBHOOK: self._send_webhook,
        }
    
    def _load_config(self):
        """加载配置"""
        try:
            if self.CONFIG_FILE.exists():
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for channel_name, config_data in data.get('channels', {}).items():
                    try:
                        channel = NotificationChannel(channel_name)
                        self._channels[channel] = ChannelConfig(
                            enabled=config_data.get('enabled', False),
                            config=config_data.get('config', {})
                        )
                    except:
                        pass
            else:
                # 默认配置
                self._channels[NotificationChannel.DESKTOP] = ChannelConfig(enabled=True)
                
        except Exception as e:
            logger.warning(f"加载通知配置失败: {e}")
            self._channels[NotificationChannel.DESKTOP] = ChannelConfig(enabled=True)
    
    def save_config(self):
        """保存配置"""
        try:
            self.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'channels': {
                    channel.value: {
                        'enabled': config.enabled,
                        'config': config.config
                    }
                    for channel, config in self._channels.items()
                }
            }
            
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"保存通知配置失败: {e}")
    
    def configure_channel(self, channel: NotificationChannel, enabled: bool, config: Dict = None):
        """配置通知渠道"""
        self._channels[channel] = ChannelConfig(
            enabled=enabled,
            config=config or {}
        )
        self.save_config()
        logger.info(f"📧 通知渠道已配置: {channel.value} ({'启用' if enabled else '禁用'})")
    
    def send(
        self,
        title: str,
        content: str,
        type: NotificationType = NotificationType.CUSTOM,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channels: List[NotificationChannel] = None,
        data: Dict = None
    ) -> bool:
        """
        发送通知
        
        Args:
            title: 标题
            content: 内容
            type: 通知类型
            priority: 优先级
            channels: 指定渠道（None则使用所有启用的渠道）
            data: 附加数据
        """
        message = NotificationMessage(
            title=title,
            content=content,
            type=type,
            priority=priority,
            data=data or {}
        )
        
        # 确定要使用的渠道
        if channels is None:
            channels = [ch for ch, cfg in self._channels.items() if cfg.enabled]
        
        if not channels:
            logger.warning("没有启用的通知渠道")
            return False
        
        # 发送到各渠道
        success_count = 0
        for channel in channels:
            try:
                handler = self._handlers.get(channel)
                if handler:
                    if handler(message, self._channels.get(channel, ChannelConfig()).config):
                        success_count += 1
            except Exception as e:
                logger.error(f"发送到 {channel.value} 失败: {e}")
        
        # 记录历史
        with self._lock:
            self._message_history.append({
                **message.to_dict(),
                'channels': [ch.value for ch in channels],
                'success_count': success_count
            })
            
            # 限制历史记录数量
            if len(self._message_history) > self._max_history:
                self._message_history = self._message_history[-self._max_history:]
        
        return success_count > 0
    
    # ============ 渠道发送处理器 ============
    
    def _send_desktop(self, message: NotificationMessage, config: Dict) -> bool:
        """发送桌面通知"""
        try:
            # 使用notify-send（Linux）
            import subprocess
            
            icon = {
                NotificationType.TREND_ALERT: "dialog-warning",
                NotificationType.CAPITAL_FLOW: "dialog-information",
                NotificationType.STRATEGY_SIGNAL: "dialog-ok",
                NotificationType.SYSTEM_STATUS: "dialog-information",
            }.get(message.type, "dialog-information")
            
            urgency = {
                NotificationPriority.LOW: "low",
                NotificationPriority.NORMAL: "normal",
                NotificationPriority.HIGH: "critical",
                NotificationPriority.URGENT: "critical",
            }.get(message.priority, "normal")
            
            subprocess.run([
                'notify-send',
                '-i', icon,
                '-u', urgency,
                f'韬睿量化: {message.title}',
                message.content
            ], check=True, capture_output=True)
            
            logger.debug(f"桌面通知已发送: {message.title}")
            return True
            
        except FileNotFoundError:
            logger.debug("notify-send不可用")
            return False
        except Exception as e:
            logger.warning(f"桌面通知失败: {e}")
            return False
    
    def _send_email(self, message: NotificationMessage, config: Dict) -> bool:
        """发送邮件通知"""
        try:
            smtp_server = config.get('smtp_server', 'smtp.qq.com')
            smtp_port = config.get('smtp_port', 587)
            username = config.get('username', '')
            password = config.get('password', '')
            from_addr = config.get('from_addr', username)
            to_addrs = config.get('to_addrs', [])
            
            if not username or not password or not to_addrs:
                logger.warning("邮件配置不完整")
                return False
            
            # 构建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'[韬睿量化] {message.title}'
            msg['From'] = from_addr
            msg['To'] = ', '.join(to_addrs)
            
            # HTML内容
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="background: #1a1a2e; color: #eee; padding: 20px; border-radius: 8px;">
                    <h2 style="color: #4CAF50; margin-bottom: 10px;">📊 {message.title}</h2>
                    <p style="font-size: 14px; line-height: 1.6;">{message.content}</p>
                    <hr style="border-color: #333;">
                    <p style="font-size: 12px; color: #888;">
                        时间: {message.timestamp}<br>
                        类型: {message.type.value}<br>
                        优先级: {message.priority.value}
                    </p>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(message.content, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # 发送
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(username, password)
                server.sendmail(from_addr, to_addrs, msg.as_string())
            
            logger.info(f"📧 邮件已发送: {message.title}")
            return True
            
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False
    
    def _send_wechat_work(self, message: NotificationMessage, config: Dict) -> bool:
        """发送企业微信通知"""
        try:
            import requests
            
            webhook_url = config.get('webhook_url', '')
            if not webhook_url:
                logger.warning("企业微信Webhook未配置")
                return False
            
            # 构建消息
            priority_emoji = {
                NotificationPriority.LOW: "ℹ️",
                NotificationPriority.NORMAL: "📊",
                NotificationPriority.HIGH: "⚠️",
                NotificationPriority.URGENT: "🚨",
            }.get(message.priority, "📊")
            
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"""### {priority_emoji} {message.title}
                    
{message.content}

> 时间: {message.timestamp}
> 类型: {message.type.value}"""
                }
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            
            if response.status_code == 200 and response.json().get('errcode') == 0:
                logger.info(f"📱 企业微信通知已发送: {message.title}")
                return True
            else:
                logger.warning(f"企业微信发送失败: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"企业微信通知失败: {e}")
            return False
    
    def _send_dingtalk(self, message: NotificationMessage, config: Dict) -> bool:
        """发送钉钉通知"""
        try:
            import requests
            
            webhook_url = config.get('webhook_url', '')
            if not webhook_url:
                logger.warning("钉钉Webhook未配置")
                return False
            
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": message.title,
                    "text": f"### {message.title}\n\n{message.content}\n\n> {message.timestamp}"
                }
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            
            if response.status_code == 200 and response.json().get('errcode') == 0:
                logger.info(f"📱 钉钉通知已发送: {message.title}")
                return True
            else:
                logger.warning(f"钉钉发送失败: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"钉钉通知失败: {e}")
            return False
    
    def _send_telegram(self, message: NotificationMessage, config: Dict) -> bool:
        """发送Telegram通知"""
        try:
            import requests
            
            bot_token = config.get('bot_token', '')
            chat_id = config.get('chat_id', '')
            
            if not bot_token or not chat_id:
                logger.warning("Telegram配置不完整")
                return False
            
            text = f"*{message.title}*\n\n{message.content}\n\n_{message.timestamp}_"
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"📱 Telegram通知已发送: {message.title}")
                return True
            else:
                logger.warning(f"Telegram发送失败: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Telegram通知失败: {e}")
            return False
    
    def _send_webhook(self, message: NotificationMessage, config: Dict) -> bool:
        """发送到自定义Webhook"""
        try:
            import requests
            
            webhook_url = config.get('url', '')
            headers = config.get('headers', {})
            
            if not webhook_url:
                logger.warning("Webhook URL未配置")
                return False
            
            payload = message.to_dict()
            
            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"🔗 Webhook通知已发送: {message.title}")
                return True
            else:
                logger.warning(f"Webhook发送失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Webhook通知失败: {e}")
            return False
    
    # ============ 便捷方法 ============
    
    def send_trend_alert(self, title: str, content: str, priority: NotificationPriority = NotificationPriority.HIGH):
        """发送趋势预警"""
        return self.send(
            title=f"📈 趋势预警: {title}",
            content=content,
            type=NotificationType.TREND_ALERT,
            priority=priority
        )
    
    def send_capital_alert(self, title: str, content: str, priority: NotificationPriority = NotificationPriority.NORMAL):
        """发送资金异动提醒"""
        return self.send(
            title=f"💰 资金异动: {title}",
            content=content,
            type=NotificationType.CAPITAL_FLOW,
            priority=priority
        )
    
    def send_strategy_signal(self, title: str, content: str, priority: NotificationPriority = NotificationPriority.HIGH):
        """发送策略信号"""
        return self.send(
            title=f"🎯 策略信号: {title}",
            content=content,
            type=NotificationType.STRATEGY_SIGNAL,
            priority=priority
        )
    
    def send_system_status(self, title: str, content: str, priority: NotificationPriority = NotificationPriority.LOW):
        """发送系统状态"""
        return self.send(
            title=f"⚙️ 系统状态: {title}",
            content=content,
            type=NotificationType.SYSTEM_STATUS,
            priority=priority
        )
    
    def get_message_history(self) -> List[Dict]:
        """获取消息历史"""
        with self._lock:
            return self._message_history.copy()
    
    def get_enabled_channels(self) -> List[str]:
        """获取已启用的渠道"""
        return [ch.value for ch, cfg in self._channels.items() if cfg.enabled]


# 全局通知管理器
_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """获取通知管理器单例"""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager

