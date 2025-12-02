#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
韬睿量化专业版 - TaoRui Quant Professional
双击此文件启动应用

启动模式:
  --fast    快速启动（无启动画面）
  --splash  显示启动画面（默认1.5秒）
  默认      快速启动
"""
import sys
import os
import logging
from pathlib import Path

# 设置项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'

# 确保日志目录存在
logs_dir = project_root / "logs"
logs_dir.mkdir(exist_ok=True)

# 配置日志（在导入其他模块之前）
log_file = logs_dir / "trquant.log"
try:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8', mode='a'),
            logging.StreamHandler()
        ]
    )
except PermissionError:
    # 如果文件被锁定，只使用控制台日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )
    print(f"警告: 无法写入日志文件 {log_file}")

logger = logging.getLogger(__name__)


# ============================================================
# 版本管理
# ============================================================
def get_app_version() -> str:
    """获取应用版本号"""
    try:
        from core.version import get_version
        return get_version()
    except Exception:
        return "2.0.0"


# ============================================================
# 启动模式配置
# ============================================================
# 效率优先：默认快速启动，无启动画面
# 如需启动画面，使用 --splash 参数
FAST_MODE = '--fast' in sys.argv or '--splash' not in sys.argv
SPLASH_DURATION = 1500  # 启动画面持续时间（毫秒），仅在 --splash 模式下使用


def main():
    """主入口"""
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        from PyQt6.QtCore import Qt, QTimer
        from PyQt6.QtGui import QFont
        
        # 创建应用
        app = QApplication(sys.argv)
        
        # 设置高DPI支持
        app.setStyle('Fusion')
        
        # 设置应用信息
        app.setApplicationName("韬睿量化专业版")
        app.setApplicationVersion(get_app_version())
        app.setOrganizationName("TaoRui Technology")
        
        # 设置默认字体
        font = QFont()
        font.setFamily("Microsoft YaHei")
        font.setPointSize(10)
        app.setFont(font)
        
        # 应用主题样式
        from gui.styles.theme import GLOBAL_STYLE
        app.setStyleSheet(GLOBAL_STYLE)
        
        # ========== 快速启动模式（默认） ==========
        if FAST_MODE:
            # 直接创建并显示主窗口，无任何延迟
            from gui.main_window import MainWindow
            window = MainWindow()
            window.show()  # 先显示
            window.showMaximized()  # 再最大化
            window.raise_()  # 提升到最前
            window.activateWindow()  # 激活窗口
            
            # 启动时显示使用指南（如果用户未选择不再显示）
            window.show_startup_guide()
            
            logger.info("韬睿量化启动完成（快速模式）")
            return app.exec()
        
        # ========== 启动画面模式 ==========
        from gui.widgets.splash_screen import SplashScreen
        splash = SplashScreen()
        splash.center_on_screen()
        splash.show()
        
        # 处理事件确保启动画面显示
        app.processEvents()
        
        # 创建主窗口（但不显示）
        from gui.main_window import MainWindow
        window = MainWindow()
        
        # 设置简短的加载提示
        splash.set_status("正在启动...", 50)
        app.processEvents()
        
        # 定时显示主窗口
        def show_main_window():
            splash.close()
            window.showMaximized()
            
            # 启动时显示使用指南（如果用户未选择不再显示）
            window.show_startup_guide()
            
            logger.info("韬睿量化启动完成（启动画面模式）")
        
        # 短暂延迟后显示主窗口（仅用于品牌展示）
        QTimer.singleShot(SPLASH_DURATION, show_main_window)
        
        # 运行应用
        return app.exec()
        
    except ImportError as e:
        print(f"导入错误: {e}")
        print("\n请确保已安装所需依赖:")
        print("  pip install PyQt6 pyqtgraph")
        print("\n或激活虚拟环境:")
        print("  source venv/bin/activate")
        return 1
    except Exception as e:
        print(f"启动错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
