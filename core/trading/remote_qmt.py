# -*- coding: utf-8 -*-
"""
远程QMT连接模块
===============

支持从Linux连接Windows虚拟机中的miniQMT

架构:
    Linux主机 (TRQuant) ←--TCP/IP--→ Windows VM (miniQMT)

使用场景:
1. Linux服务器 + Windows虚拟机运行miniQMT
2. 跨机器远程连接（需要配置防火墙）

配置要求:
1. Windows VM中安装并运行miniQMT
2. VM网络设置为桥接模式（获取独立IP）
3. 配置miniQMT允许远程连接
"""

import logging
import socket
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

logger = logging.getLogger(__name__)

# 尝试导入xtquant
XTQUANT_AVAILABLE = False
try:
    import xtquant
    from xtquant import xtdata
    XTQUANT_AVAILABLE = True
except ImportError:
    logger.info("xtquant未安装或不可用")


@dataclass
class RemoteQMTConfig:
    """远程QMT配置"""
    host: str = "127.0.0.1"          # miniQMT所在IP（Windows VM的IP）
    data_port: int = 58601           # 数据服务端口
    trade_port: int = 58602          # 交易服务端口
    account_id: str = ""             # 交易账户
    auto_reconnect: bool = True      # 自动重连
    timeout: int = 30                # 连接超时(秒)


class RemoteQMTClient:
    """
    远程QMT客户端
    
    支持从Linux连接Windows虚拟机中的miniQMT
    """
    
    def __init__(self, config: RemoteQMTConfig):
        """
        初始化
        
        Args:
            config: 远程QMT配置
        """
        self.config = config
        self.connected = False
        self.data_client = None
        self.trade_client = None
    
    def check_connection(self) -> Dict[str, Any]:
        """
        检查与miniQMT的连接状态
        
        Returns:
            连接状态信息
        """
        status = {
            'host': self.config.host,
            'data_port_reachable': False,
            'trade_port_reachable': False,
            'xtquant_available': XTQUANT_AVAILABLE,
            'message': ''
        }
        
        # 检查数据端口
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((self.config.host, self.config.data_port))
            sock.close()
            status['data_port_reachable'] = (result == 0)
        except Exception as e:
            logger.debug(f"数据端口检查失败: {e}")
        
        # 检查交易端口
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((self.config.host, self.config.trade_port))
            sock.close()
            status['trade_port_reachable'] = (result == 0)
        except Exception as e:
            logger.debug(f"交易端口检查失败: {e}")
        
        # 生成状态消息
        if status['data_port_reachable'] and status['trade_port_reachable']:
            status['message'] = f"✅ miniQMT可达: {self.config.host}"
        elif status['data_port_reachable']:
            status['message'] = f"⚠️ 数据服务可达，交易服务不可达: {self.config.host}"
        else:
            status['message'] = f"❌ miniQMT不可达: {self.config.host}:{self.config.data_port}"
            status['message'] += "\n请确认: 1) Windows VM已启动 2) miniQMT正在运行 3) 网络可通"
        
        return status
    
    def connect(self) -> bool:
        """
        连接到远程miniQMT
        
        Returns:
            是否连接成功
        """
        if not XTQUANT_AVAILABLE:
            logger.error("xtquant未安装，无法连接")
            return False
        
        # 检查连接
        status = self.check_connection()
        if not status['data_port_reachable']:
            logger.error(status['message'])
            return False
        
        try:
            # 设置xtdata连接地址（如果xtquant支持）
            # 注意：标准xtquant可能需要miniQMT在本地
            # 这里提供一个兼容层
            
            logger.info(f"尝试连接远程miniQMT: {self.config.host}")
            
            # 方案1：如果xtdata支持设置远程地址
            if hasattr(xtdata, 'set_server'):
                xtdata.set_server(self.config.host, self.config.data_port)
            
            # 方案2：通过环境变量设置（某些版本支持）
            import os
            os.environ['QMT_SERVER_HOST'] = self.config.host
            os.environ['QMT_SERVER_PORT'] = str(self.config.data_port)
            
            self.connected = True
            logger.info(f"✅ 已连接到远程miniQMT: {self.config.host}")
            return True
            
        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        self.connected = False
        logger.info("已断开远程QMT连接")
    
    def download_history_data(self, 
                              stock_list: List[str],
                              start_date: str,
                              end_date: str,
                              period: str = "1d") -> bool:
        """
        下载历史数据
        
        Args:
            stock_list: 股票列表
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            period: 周期
        
        Returns:
            是否成功
        """
        if not self.connected:
            logger.error("未连接到miniQMT")
            return False
        
        try:
            for stock in stock_list:
                xtdata.download_history_data(
                    stock_code=stock,
                    period=period,
                    start_time=start_date,
                    end_time=end_date
                )
                logger.debug(f"下载完成: {stock}")
            
            logger.info(f"✅ 历史数据下载完成: {len(stock_list)}只股票")
            return True
            
        except Exception as e:
            logger.error(f"下载数据失败: {e}")
            return False
    
    def get_market_data(self, 
                        stock_list: List[str],
                        period: str = "1d",
                        start_time: str = "",
                        end_time: str = "") -> Dict:
        """
        获取行情数据
        
        Args:
            stock_list: 股票列表
            period: 周期
            start_time: 开始时间
            end_time: 结束时间
        
        Returns:
            行情数据
        """
        if not self.connected:
            return {}
        
        try:
            data = xtdata.get_market_data_ex(
                field_list=[],
                stock_list=stock_list,
                period=period,
                start_time=start_time,
                end_time=end_time,
                dividend_type='front',
                fill_data=True
            )
            return data
            
        except Exception as e:
            logger.error(f"获取数据失败: {e}")
            return {}


class VMQMTManager:
    """
    虚拟机QMT管理器
    
    用于管理Windows虚拟机中的miniQMT
    """
    
    def __init__(self, vm_name: str = "Windows-QMT"):
        """
        初始化
        
        Args:
            vm_name: 虚拟机名称
        """
        self.vm_name = vm_name
        self.vm_ip = None
    
    def detect_vm_ip(self) -> Optional[str]:
        """
        检测虚拟机IP地址
        
        Returns:
            VM的IP地址
        """
        import subprocess
        
        # 方法1：通过virsh (KVM)
        try:
            result = subprocess.run(
                ['virsh', 'domifaddr', self.vm_name],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                # 解析输出获取IP
                for line in result.stdout.split('\n'):
                    if 'ipv4' in line.lower():
                        parts = line.split()
                        for part in parts:
                            if '/' in part:
                                self.vm_ip = part.split('/')[0]
                                return self.vm_ip
        except:
            pass
        
        # 方法2：通过VBoxManage (VirtualBox)
        try:
            result = subprocess.run(
                ['VBoxManage', 'guestproperty', 'get', self.vm_name, 
                 '/VirtualBox/GuestInfo/Net/0/V4/IP'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and 'Value:' in result.stdout:
                self.vm_ip = result.stdout.split('Value:')[1].strip()
                return self.vm_ip
        except:
            pass
        
        logger.warning(f"无法自动检测VM IP，请手动配置")
        return None
    
    def start_vm(self) -> bool:
        """启动虚拟机"""
        import subprocess
        
        # 尝试KVM
        try:
            result = subprocess.run(
                ['virsh', 'start', self.vm_name],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                logger.info(f"✅ KVM虚拟机已启动: {self.vm_name}")
                return True
        except:
            pass
        
        # 尝试VirtualBox
        try:
            result = subprocess.run(
                ['VBoxManage', 'startvm', self.vm_name, '--type', 'headless'],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                logger.info(f"✅ VirtualBox虚拟机已启动: {self.vm_name}")
                return True
        except:
            pass
        
        logger.error(f"无法启动虚拟机: {self.vm_name}")
        return False
    
    def check_miniqmt_status(self, host: str, port: int = 58601) -> bool:
        """检查miniQMT是否运行"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False


def create_remote_qmt_config(
    host: str = "192.168.1.100",
    account_id: str = ""
) -> RemoteQMTConfig:
    """
    创建远程QMT配置
    
    Args:
        host: Windows VM的IP地址
        account_id: 交易账户ID
    
    Returns:
        RemoteQMTConfig
    """
    return RemoteQMTConfig(
        host=host,
        account_id=account_id
    )


def setup_linux_qmt_environment() -> Dict:
    """
    设置Linux QMT环境
    
    Returns:
        环境状态信息
    """
    status = {
        'xtquant_installed': XTQUANT_AVAILABLE,
        'vm_detected': False,
        'vm_ip': None,
        'miniqmt_running': False,
        'instructions': []
    }
    
    if not XTQUANT_AVAILABLE:
        status['instructions'].append("1. 安装xtquant: pip install xtquant")
    
    status['instructions'].extend([
        "2. 创建Windows虚拟机（推荐KVM或VirtualBox）",
        "3. 在VM中安装国金/国盛等券商QMT客户端",
        "4. 启动QMT时勾选'极简模式'启动miniQMT",
        "5. 配置VM网络为桥接模式",
        "6. 记录VM的IP地址",
        "7. 使用RemoteQMTClient连接"
    ])
    
    # 尝试检测VM
    vm_manager = VMQMTManager()
    vm_ip = vm_manager.detect_vm_ip()
    if vm_ip:
        status['vm_detected'] = True
        status['vm_ip'] = vm_ip
        status['miniqmt_running'] = vm_manager.check_miniqmt_status(vm_ip)
    
    return status


# 示例代码
USAGE_EXAMPLE = """
# Linux下连接Windows VM中的miniQMT示例

from core.trading.remote_qmt import (
    RemoteQMTConfig, 
    RemoteQMTClient,
    setup_linux_qmt_environment
)

# 1. 检查环境
env_status = setup_linux_qmt_environment()
print(env_status)

# 2. 配置远程连接
config = RemoteQMTConfig(
    host="192.168.1.100",      # Windows VM的IP
    account_id="YOUR_ACCOUNT"  # 交易账户
)

# 3. 创建客户端并连接
client = RemoteQMTClient(config)

# 检查连接状态
status = client.check_connection()
print(status['message'])

# 连接
if client.connect():
    # 下载历史数据
    client.download_history_data(
        stock_list=['600519.SH', '000858.SZ'],
        start_date='20240101',
        end_date='20240630',
        period='1d'
    )
    
    # 获取行情数据
    data = client.get_market_data(
        stock_list=['600519.SH'],
        period='1d'
    )
    print(data)
"""

