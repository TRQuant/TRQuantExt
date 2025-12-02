# -*- coding: utf-8 -*-
"""
信息获取面板 - 多元化投资信息源整合中心
=====================================

功能模块：
1. 投资主线 - 实时发现和追踪热门投资主线
2. 数据源管理 - 配置和监控多数据源
3. 资讯聚合 - 财经新闻和市场动态
4. 知识库 - 投资理论和策略参考
5. 工具箱 - 实用投资分析工具
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QScrollArea, QTabWidget, QLineEdit,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QSplitter,
    QTextBrowser, QGroupBox, QStackedWidget, QToolButton,
    QMessageBox, QApplication, QTextEdit, QComboBox,
    QProgressBar, QTableWidget, QTableWidgetItem
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QFont, QDesktopServices, QIcon
from datetime import datetime
from pathlib import Path
import webbrowser
import logging

from gui.styles.theme import Colors, Typography, ButtonStyles, CardStyles

logger = logging.getLogger(__name__)


# ============================================================
# 数据源测试工作线程
# ============================================================

class DataSourceTestWorker(QThread):
    """数据源连接测试工作线程 - 避免阻塞UI"""
    finished = pyqtSignal(str, dict)  # source_name, result
    progress = pyqtSignal(str)  # status message
    
    def __init__(self, source_name: str, parent=None):
        super().__init__(parent)
        self.source_name = source_name
    
    def run(self):
        """执行测试"""
        try:
            self.progress.emit(f"正在测试 {self.source_name}...")
            
            if "JQData" in self.source_name:
                result = self._test_jqdata()
            elif "AKShare" in self.source_name:
                result = self._test_akshare()
            elif "TuShare" in self.source_name:
                result = self._test_tushare()
            elif "Baostock" in self.source_name:
                result = self._test_baostock()
            elif "通达信" in self.source_name or "TDX" in self.source_name:
                result = self._test_tdx()
            else:
                result = {"success": False, "message": f"未知数据源: {self.source_name}"}
            
            self.finished.emit(self.source_name, result)
            
        except Exception as e:
            self.finished.emit(self.source_name, {
                "success": False, 
                "message": f"测试异常: {str(e)}"
            })
    
    def _test_jqdata(self) -> dict:
        """测试JQData连接"""
        try:
            import jqdatasdk as jq
            from config.config_manager import ConfigManager
            
            config = ConfigManager()
            jq_config = config.load_config("jqdata_config.json")
            
            if not jq_config:
                return {"success": False, "message": "未找到JQData配置文件\n请在 config/ 目录下创建 jqdata_config.json"}
            
            username = jq_config.get("username", "")
            password = jq_config.get("password", "")
            
            if not username or not password:
                return {"success": False, "message": "JQData配置不完整\n缺少用户名或密码"}
            
            # 先登出再登录
            try:
                jq.logout()
            except:
                pass
            
            jq.auth(username, password)
            
            # 测试获取数据
            test_result = jq.get_query_count()
            
            return {
                "success": True,
                "message": f"JQData连接成功!\n\n今日剩余请求次数: {test_result.get('spare', 'N/A')}\n账户类型: 试用账户"
            }
        except Exception as e:
            return {"success": False, "message": f"JQData连接失败:\n{str(e)}"}
    
    def _test_akshare(self) -> dict:
        """测试AKShare连接"""
        try:
            import akshare as ak
            
            # 测试获取股票列表（轻量级请求）
            df = ak.stock_info_a_code_name()
            
            if df is not None and len(df) > 0:
                return {
                    "success": True,
                    "message": f"AKShare连接成功!\n\n获取到 {len(df)} 只A股股票信息\n数据源状态: 正常"
                }
            else:
                return {"success": False, "message": "AKShare返回空数据"}
        except Exception as e:
            return {"success": False, "message": f"AKShare连接失败:\n{str(e)}"}
    
    def _test_tushare(self) -> dict:
        """测试TuShare连接"""
        try:
            import tushare as ts
            from config.config_manager import ConfigManager
            
            config = ConfigManager()
            ts_config = config.load_config("tushare_config.json")
            
            if not ts_config:
                return {"success": False, "message": "未找到TuShare配置\n请配置 config/tushare_config.json"}
            
            token = ts_config.get("token", "")
            if not token:
                return {"success": False, "message": "TuShare token未配置"}
            
            pro = ts.pro_api(token)
            df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,name')
            
            if df is not None and len(df) > 0:
                return {
                    "success": True,
                    "message": f"TuShare连接成功!\n\n获取到 {len(df)} 只股票信息"
                }
            else:
                return {"success": False, "message": "TuShare返回空数据"}
        except Exception as e:
            return {"success": False, "message": f"TuShare连接失败:\n{str(e)}"}
    
    def _test_baostock(self) -> dict:
        """测试Baostock连接"""
        try:
            import baostock as bs
            
            login_result = bs.login()
            
            if login_result.error_code == '0':
                # 测试获取数据
                rs = bs.query_stock_basic()
                count = 0
                while rs.next():
                    count += 1
                    if count >= 10:
                        break
                
                bs.logout()
                
                return {
                    "success": True,
                    "message": f"Baostock连接成功!\n\n登录状态: 正常\n可获取历史数据"
                }
            else:
                return {
                    "success": False,
                    "message": f"Baostock登录失败:\n{login_result.error_msg}"
                }
        except Exception as e:
            return {"success": False, "message": f"Baostock连接失败:\n{str(e)}"}
    
    def _test_tdx(self) -> dict:
        """测试通达信本地数据"""
        from pathlib import Path
        
        # 常见通达信安装路径
        common_paths = [
            Path.home() / "通达信",
            Path("/opt/通达信"),
            Path.home() / ".wine/drive_c/new_tdx",
            Path.home() / ".wine/drive_c/tdx",
            Path("/mnt/c/new_tdx"),
        ]
        
        for tdx_path in common_paths:
            data_path = tdx_path / "vipdoc"
            if data_path.exists():
                # 检查数据目录
                sh_path = data_path / "sh" / "lday"
                sz_path = data_path / "sz" / "lday"
                
                sh_count = len(list(sh_path.glob("*.day"))) if sh_path.exists() else 0
                sz_count = len(list(sz_path.glob("*.day"))) if sz_path.exists() else 0
                
                if sh_count > 0 or sz_count > 0:
                    return {
                        "success": True,
                        "message": f"通达信数据找到!\n\n路径: {tdx_path}\n沪市日线: {sh_count}个文件\n深市日线: {sz_count}个文件"
                    }
        
        return {
            "success": False,
            "message": "未找到通达信数据目录\n\n请安装通达信客户端并下载盘后数据\n或在 config/tdx_config.json 中配置路径"
        }


# ============================================================
# 信息源数据库（完整版）
# ============================================================

DATA_SOURCES = {
    "knowledge": {
        "name": "📚 知识库",
        "icon": "📚",
        "description": "系统化投资理论、策略和案例分析",
        "sources": [
            {
                "name": "A股量化实操手册",
                "description": "因子投资体系完整教程，涵盖价值、成长、质量、动量、资金流等因子",
                "url": "internal://manual",
                "type": "internal",
                "tags": ["因子投资", "量化策略", "A股"],
                "rating": 5,
            },
            {
                "name": "聚宽量化课堂",
                "description": "JoinQuant官方量化投资教程，从入门到进阶",
                "url": "https://www.joinquant.com/view/community/list?type=6",
                "type": "external",
                "tags": ["量化入门", "策略开发", "API教程"],
                "rating": 5,
            },
            {
                "name": "量化投资学习路径",
                "description": "GitHub上整理的量化学习资源汇总",
                "url": "https://github.com/thuquant/awesome-quant",
                "type": "external",
                "tags": ["量化理论", "开源资源", "学习路径"],
                "rating": 4,
            },
            {
                "name": "CFA Institute",
                "description": "CFA协会官网，投资专业认证和研究资源",
                "url": "https://www.cfainstitute.org/",
                "type": "external",
                "tags": ["专业认证", "投资标准", "研究报告"],
                "rating": 5,
            },
            {
                "name": "SSRN金融论文库",
                "description": "社会科学研究网络，最新金融学术论文",
                "url": "https://papers.ssrn.com/sol3/DisplayJournalBrowse.cfm",
                "type": "external",
                "tags": ["学术研究", "前沿理论", "实证分析"],
                "rating": 4,
            },
        ]
    },
    "quant_data": {
        "name": "📊 量化数据源",
        "icon": "📊",
        "description": "专业量化投资数据接口和平台",
        "sources": [
            {
                "name": "聚宽 JQData",
                "description": "A股全量数据，支持因子计算、回测、实盘，本平台核心数据源",
                "url": "https://www.joinquant.com/data",
                "type": "api",
                "api_status": "已配置",
                "tags": ["行情数据", "财务数据", "因子数据", "Level2"],
                "rating": 5,
                "config_key": "jqdata",
            },
            {
                "name": "TuShare Pro",
                "description": "免费开源金融数据接口，覆盖股票、基金、期货等",
                "url": "https://tushare.pro/",
                "type": "api",
                "api_status": "可配置",
                "tags": ["免费数据", "Python接口", "社区活跃"],
                "rating": 4,
                "config_key": "tushare",
            },
            {
                "name": "Wind万得",
                "description": "机构级金融数据终端，覆盖全球市场",
                "url": "https://www.wind.com.cn/",
                "type": "terminal",
                "tags": ["机构数据", "全球覆盖", "终端软件"],
                "rating": 5,
            },
            {
                "name": "东方财富Choice",
                "description": "东方财富金融数据终端，性价比较高",
                "url": "https://choice.eastmoney.com/",
                "type": "terminal",
                "tags": ["A股数据", "研报数据", "资金流向"],
                "rating": 4,
            },
            {
                "name": "同花顺iFinD",
                "description": "同花顺金融数据平台，智能投研工具",
                "url": "https://www.51ifind.com/",
                "type": "terminal",
                "tags": ["智能投研", "另类数据", "AI分析"],
                "rating": 4,
            },
            {
                "name": "AKShare",
                "description": "开源财经数据接口库，数据源丰富",
                "url": "https://akshare.akfamily.xyz/",
                "type": "api",
                "api_status": "已配置",
                "tags": ["开源免费", "多数据源", "Python"],
                "rating": 4,
                "config_key": "akshare",
            },
            {
                "name": "Baostock",
                "description": "证券宝，免费开源A股数据",
                "url": "http://baostock.com/",
                "type": "api",
                "api_status": "可配置",
                "tags": ["免费", "历史数据", "分钟数据"],
                "rating": 3,
                "config_key": "baostock",
            },
        ]
    },
    "news": {
        "name": "📰 财经媒体",
        "icon": "📰",
        "description": "实时财经新闻和市场动态",
        "sources": [
            {
                "name": "财联社",
                "description": "7x24小时滚动财经快讯，机构投资者必备",
                "url": "https://www.cls.cn/",
                "type": "news",
                "tags": ["实时快讯", "独家消息", "电报"],
                "rating": 5,
            },
            {
                "name": "第一财经",
                "description": "专业财经媒体，深度报道和分析",
                "url": "https://www.yicai.com/",
                "type": "news",
                "tags": ["深度报道", "视频财经", "政策解读"],
                "rating": 5,
            },
            {
                "name": "华尔街见闻",
                "description": "全球财经资讯，实时追踪国际市场",
                "url": "https://wallstreetcn.com/",
                "type": "news",
                "tags": ["全球市场", "宏观分析", "VIP内容"],
                "rating": 4,
            },
            {
                "name": "新浪财经",
                "description": "综合财经门户，覆盖面广",
                "url": "https://finance.sina.com.cn/",
                "type": "news",
                "tags": ["综合门户", "股吧社区", "自选股"],
                "rating": 4,
            },
            {
                "name": "Bloomberg",
                "description": "彭博社，全球金融市场权威媒体",
                "url": "https://www.bloomberg.com/",
                "type": "news",
                "tags": ["国际市场", "专业分析", "英文"],
                "rating": 5,
            },
            {
                "name": "Reuters路透社",
                "description": "国际通讯社，全球财经新闻",
                "url": "https://www.reuters.com/markets/",
                "type": "news",
                "tags": ["国际新闻", "实时行情", "英文"],
                "rating": 5,
            },
            {
                "name": "FT金融时报",
                "description": "英国金融时报，深度财经分析",
                "url": "https://www.ft.com/",
                "type": "news",
                "tags": ["深度分析", "国际视野", "付费"],
                "rating": 5,
            },
        ]
    },
    "macro": {
        "name": "🏛️ 宏观数据",
        "icon": "🏛️",
        "description": "官方宏观经济数据和政策信息",
        "sources": [
            {
                "name": "国家统计局",
                "description": "中国官方统计数据，GDP、CPI、PMI等",
                "url": "https://www.stats.gov.cn/",
                "type": "official",
                "tags": ["官方数据", "宏观指标", "统计公报"],
                "rating": 5,
            },
            {
                "name": "中国人民银行",
                "description": "货币政策、利率、汇率、金融数据",
                "url": "http://www.pbc.gov.cn/",
                "type": "official",
                "tags": ["货币政策", "利率", "外汇储备"],
                "rating": 5,
            },
            {
                "name": "中国证监会",
                "description": "证券市场监管政策和公告",
                "url": "http://www.csrc.gov.cn/",
                "type": "official",
                "tags": ["监管政策", "IPO", "市场规则"],
                "rating": 5,
            },
            {
                "name": "财政部",
                "description": "财政政策、国债、税收数据",
                "url": "http://www.mof.gov.cn/",
                "type": "official",
                "tags": ["财政政策", "国债", "税收"],
                "rating": 4,
            },
            {
                "name": "海关总署",
                "description": "进出口贸易数据",
                "url": "http://www.customs.gov.cn/",
                "type": "official",
                "tags": ["贸易数据", "进出口", "关税"],
                "rating": 4,
            },
            {
                "name": "美联储 Federal Reserve",
                "description": "美国联邦储备系统，全球最重要央行",
                "url": "https://www.federalreserve.gov/",
                "type": "official",
                "tags": ["美联储", "利率决议", "FOMC"],
                "rating": 5,
            },
            {
                "name": "FRED经济数据库",
                "description": "圣路易斯联储经济数据库，全球宏观数据",
                "url": "https://fred.stlouisfed.org/",
                "type": "database",
                "tags": ["免费数据", "全球宏观", "API接口"],
                "rating": 5,
            },
            {
                "name": "世界银行",
                "description": "全球发展数据和研究报告",
                "url": "https://data.worldbank.org/",
                "type": "official",
                "tags": ["全球数据", "发展指标", "研究报告"],
                "rating": 4,
            },
            {
                "name": "IMF国际货币基金组织",
                "description": "全球经济展望和金融稳定报告",
                "url": "https://www.imf.org/en/Data",
                "type": "official",
                "tags": ["全球经济", "金融稳定", "预测报告"],
                "rating": 5,
            },
        ]
    },
    "company": {
        "name": "🏢 公司财报",
        "icon": "🏢",
        "description": "上市公司公告、财报和投资者关系",
        "sources": [
            {
                "name": "巨潮资讯网",
                "description": "中国证监会指定信息披露网站",
                "url": "http://www.cninfo.com.cn/",
                "type": "official",
                "tags": ["官方披露", "公告查询", "年报季报"],
                "rating": 5,
            },
            {
                "name": "上交所公告",
                "description": "上海证券交易所公司公告",
                "url": "http://www.sse.com.cn/disclosure/listedinfo/announcement/",
                "type": "official",
                "tags": ["沪市公告", "科创板", "债券"],
                "rating": 5,
            },
            {
                "name": "深交所公告",
                "description": "深圳证券交易所公司公告",
                "url": "http://www.szse.cn/disclosure/listed/notice/index.html",
                "type": "official",
                "tags": ["深市公告", "创业板", "中小板"],
                "rating": 5,
            },
            {
                "name": "北交所公告",
                "description": "北京证券交易所公司公告",
                "url": "https://www.bse.cn/disclosure/announcement.html",
                "type": "official",
                "tags": ["北交所", "专精特新", "新三板"],
                "rating": 4,
            },
            {
                "name": "SEC EDGAR",
                "description": "美国证监会电子数据库，美股财报",
                "url": "https://www.sec.gov/edgar/searchedgar/companysearch",
                "type": "official",
                "tags": ["美股", "10-K", "10-Q"],
                "rating": 5,
            },
            {
                "name": "港交所披露易",
                "description": "香港交易所上市公司公告",
                "url": "https://www.hkexnews.hk/",
                "type": "official",
                "tags": ["港股", "公告", "招股书"],
                "rating": 5,
            },
        ]
    },
    "community": {
        "name": "💬 投资社区",
        "icon": "💬",
        "description": "投资者交流平台和社交媒体",
        "sources": [
            {
                "name": "雪球",
                "description": "中国最大投资者社区，组合跟踪、讨论互动",
                "url": "https://xueqiu.com/",
                "type": "community",
                "tags": ["投资社区", "组合", "大V观点"],
                "rating": 5,
            },
            {
                "name": "东方财富股吧",
                "description": "个股讨论社区，散户情绪晴雨表",
                "url": "https://guba.eastmoney.com/",
                "type": "community",
                "tags": ["股吧", "散户情绪", "个股讨论"],
                "rating": 4,
            },
            {
                "name": "淘股吧",
                "description": "游资和短线交易者聚集地",
                "url": "https://www.taoguba.com.cn/",
                "type": "community",
                "tags": ["游资", "短线", "龙虎榜"],
                "rating": 4,
            },
            {
                "name": "集思录",
                "description": "低风险投资社区，可转债、套利策略",
                "url": "https://www.jisilu.cn/",
                "type": "community",
                "tags": ["低风险", "可转债", "套利"],
                "rating": 5,
            },
            {
                "name": "Reddit r/investing",
                "description": "Reddit投资板块，国际投资者社区",
                "url": "https://www.reddit.com/r/investing/",
                "type": "community",
                "tags": ["国际", "讨论", "英文"],
                "rating": 4,
            },
            {
                "name": "Twitter/X 财经",
                "description": "关注财经KOL和机构账号",
                "url": "https://twitter.com/search?q=finance",
                "type": "social",
                "tags": ["实时", "KOL", "国际"],
                "rating": 4,
            },
            {
                "name": "微博财经",
                "description": "财经大V和机构官方账号",
                "url": "https://weibo.com/",
                "type": "social",
                "tags": ["大V", "热点", "情绪"],
                "rating": 3,
            },
        ]
    },
    "research": {
        "name": "📋 券商研报",
        "icon": "📋",
        "description": "券商研究报告和行业分析",
        "sources": [
            {
                "name": "慧博投研资讯",
                "description": "最全面的券商研报聚合平台",
                "url": "https://www.hibor.com.cn/",
                "type": "research",
                "tags": ["研报聚合", "行业研究", "公司研究"],
                "rating": 5,
            },
            {
                "name": "东方财富研报中心",
                "description": "免费研报查询和下载",
                "url": "https://data.eastmoney.com/report/",
                "type": "research",
                "tags": ["免费研报", "评级", "盈利预测"],
                "rating": 4,
            },
            {
                "name": "萝卜投研",
                "description": "AI驱动的智能投研平台",
                "url": "https://robo.datayes.com/",
                "type": "research",
                "tags": ["AI投研", "智能分析", "数据可视化"],
                "rating": 4,
            },
            {
                "name": "Wind研报",
                "description": "万得金融终端研报模块",
                "url": "https://www.wind.com.cn/",
                "type": "terminal",
                "tags": ["机构研报", "深度报告", "付费"],
                "rating": 5,
            },
            {
                "name": "中金公司研究",
                "description": "顶级券商研究报告",
                "url": "https://research.cicc.com/",
                "type": "research",
                "tags": ["中金", "宏观策略", "行业"],
                "rating": 5,
            },
            {
                "name": "国泰君安研究所",
                "description": "国君研究报告和观点",
                "url": "https://www.gtja.com/content/research/index.html",
                "type": "research",
                "tags": ["国君", "策略", "行业"],
                "rating": 4,
            },
        ]
    },
    "alternative": {
        "name": "🛰️ 另类数据",
        "icon": "🛰️",
        "description": "卫星图像、供应链、社交情绪等非传统数据",
        "sources": [
            {
                "name": "Orbital Insight",
                "description": "卫星图像分析，零售流量、石油库存等",
                "url": "https://orbitalinsight.com/",
                "type": "alternative",
                "tags": ["卫星图像", "零售分析", "能源"],
                "rating": 5,
            },
            {
                "name": "Planet Labs",
                "description": "高频卫星图像，农业、基建监测",
                "url": "https://www.planet.com/",
                "type": "alternative",
                "tags": ["卫星", "农业", "基建"],
                "rating": 5,
            },
            {
                "name": "Thinknum Alternative Data",
                "description": "网站流量、招聘数据、社交媒体等",
                "url": "https://www.thinknum.com/",
                "type": "alternative",
                "tags": ["网站数据", "招聘", "社交"],
                "rating": 4,
            },
            {
                "name": "Quandl (Nasdaq)",
                "description": "另类数据市场，多种数据集",
                "url": "https://data.nasdaq.com/",
                "type": "alternative",
                "tags": ["数据市场", "API", "多样化"],
                "rating": 4,
            },
            {
                "name": "SimilarWeb",
                "description": "网站流量和数字市场情报",
                "url": "https://www.similarweb.com/",
                "type": "alternative",
                "tags": ["网站流量", "竞品分析", "电商"],
                "rating": 4,
            },
            {
                "name": "App Annie (data.ai)",
                "description": "移动应用数据和分析",
                "url": "https://www.data.ai/",
                "type": "alternative",
                "tags": ["App数据", "下载量", "用户活跃"],
                "rating": 4,
            },
            {
                "name": "百度指数",
                "description": "搜索趋势数据，反映市场关注度",
                "url": "https://index.baidu.com/",
                "type": "alternative",
                "tags": ["搜索趋势", "关注度", "免费"],
                "rating": 4,
            },
            {
                "name": "Google Trends",
                "description": "全球搜索趋势，情绪指标",
                "url": "https://trends.google.com/",
                "type": "alternative",
                "tags": ["搜索趋势", "全球", "免费"],
                "rating": 4,
            },
            {
                "name": "船讯网",
                "description": "全球船舶AIS数据，贸易物流监测",
                "url": "https://www.shipxy.com/",
                "type": "alternative",
                "tags": ["航运", "贸易", "物流"],
                "rating": 4,
            },
            {
                "name": "天眼查/企查查",
                "description": "企业工商数据、股权关系、诉讼信息",
                "url": "https://www.tianyancha.com/",
                "type": "alternative",
                "tags": ["企业数据", "股权", "风险"],
                "rating": 4,
            },
        ]
    },
    "tools": {
        "name": "🔧 投资工具",
        "icon": "🔧",
        "description": "实用投资分析和管理工具",
        "sources": [
            {
                "name": "理杏仁",
                "description": "专业估值工具，历史PE/PB分位",
                "url": "https://www.lixinger.com/",
                "type": "tool",
                "tags": ["估值", "分位数", "指数"],
                "rating": 5,
            },
            {
                "name": "韭圈儿",
                "description": "基金投资工具，持仓分析",
                "url": "https://funddb.cn/",
                "type": "tool",
                "tags": ["基金", "持仓", "分析"],
                "rating": 4,
            },
            {
                "name": "乌龟量化",
                "description": "量化投资工具，因子分析",
                "url": "https://www.wuguiquant.com/",
                "type": "tool",
                "tags": ["量化", "因子", "回测"],
                "rating": 4,
            },
            {
                "name": "Investing.com",
                "description": "全球市场行情和经济日历",
                "url": "https://cn.investing.com/",
                "type": "tool",
                "tags": ["全球行情", "日历", "技术分析"],
                "rating": 4,
            },
            {
                "name": "TradingView",
                "description": "专业图表和技术分析平台",
                "url": "https://www.tradingview.com/",
                "type": "tool",
                "tags": ["图表", "技术分析", "社区"],
                "rating": 5,
            },
            {
                "name": "Portfolio Visualizer",
                "description": "组合分析和回测工具（美股）",
                "url": "https://www.portfoliovisualizer.com/",
                "type": "tool",
                "tags": ["组合分析", "回测", "美股"],
                "rating": 4,
            },
        ]
    },
}


class SourceCard(QFrame):
    """信息源卡片"""
    clicked = pyqtSignal(dict)
    
    TYPE_CONFIG = {
        "internal": ("#10B981", "📦", "内置"),
        "api": ("#3B82F6", "🔌", "API"),
        "terminal": ("#F59E0B", "🖥️", "终端"),
        "official": ("#8B5CF6", "🏛️", "官方"),
        "news": ("#EC4899", "📰", "新闻"),
        "community": ("#6366F1", "💬", "社区"),
        "research": ("#14B8A6", "📊", "研报"),
        "alternative": ("#F97316", "🛰️", "另类"),
        "tool": ("#22C55E", "🔧", "工具"),
        "external": ("#64748B", "🔗", "外部"),
    }
    
    def __init__(self, source: dict, parent=None):
        super().__init__(parent)
        self.source = source
        self.source_type = source.get("type", "external")
        self.type_color = self.TYPE_CONFIG.get(self.source_type, self.TYPE_CONFIG["external"])[0]
        self.setup_ui()
        
    def setup_ui(self):
        self.setFixedHeight(120)
        self.setStyleSheet(f"""
            QFrame#sourceCard {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 10px;
            }}
            QFrame#sourceCard:hover {{
                border: 2px solid {self.type_color};
                background-color: {self.type_color}10;
            }}
        """)
        self.setObjectName("sourceCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)
        
        # 顶部：类型 + 评分
        top_layout = QHBoxLayout()
        type_icon, type_text = self.TYPE_CONFIG.get(self.source_type, self.TYPE_CONFIG["external"])[1:3]
        
        type_badge = QLabel(f"{type_icon} {type_text}")
        type_badge.setStyleSheet(f"""
            font-size: 11px;
            font-weight: 600;
            color: {self.type_color};
            background-color: {self.type_color}18;
            padding: 3px 8px;
            border-radius: 10px;
        """)
        top_layout.addWidget(type_badge)
        top_layout.addStretch()
        
        # 评分
        rating = self.source.get("rating", 3)
        rating_label = QLabel("★" * rating + "☆" * (5 - rating))
        rating_label.setStyleSheet(f"font-size: 11px; color: #FBBF24;")
        top_layout.addWidget(rating_label)
        
        layout.addLayout(top_layout)
        
        # 名称
        name_label = QLabel(self.source["name"])
        name_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 700;
            color: {Colors.TEXT_PRIMARY};
        """)
        layout.addWidget(name_label)
        
        # 描述
        desc_label = QLabel(self.source["description"])
        desc_label.setStyleSheet(f"""
            font-size: 12px;
            color: {Colors.TEXT_MUTED};
        """)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        layout.addStretch()
        
        # 标签
        tags_layout = QHBoxLayout()
        for tag in self.source.get("tags", [])[:2]:
            tag_label = QLabel(tag)
            tag_label.setStyleSheet(f"""
                font-size: 10px;
                color: {Colors.TEXT_SECONDARY};
                background-color: {Colors.BG_PRIMARY};
                padding: 2px 6px;
                border-radius: 4px;
            """)
            tags_layout.addWidget(tag_label)
        tags_layout.addStretch()
        
        # API状态
        if "api_status" in self.source:
            status = self.source["api_status"]
            is_ok = status == "已配置"
            status_color = "#10B981" if is_ok else "#F59E0B"
            status_label = QLabel(f"● {status}")
            status_label.setStyleSheet(f"font-size: 10px; color: {status_color}; font-weight: 600;")
            tags_layout.addWidget(status_label)
        
        layout.addLayout(tags_layout)
    
    def mousePressEvent(self, event):
        self.clicked.emit(self.source)
        super().mousePressEvent(event)


class ThemeCard(QFrame):
    """投资主线卡片"""
    clicked = pyqtSignal(dict)
    
    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setup_ui()
    
    def setup_ui(self):
        self.setFixedHeight(140)
        
        heat = self.theme.get('heat_score', 50)
        sentiment = self.theme.get('sentiment', 'neutral')
        
        # 根据情绪设置颜色
        if sentiment == 'positive':
            accent_color = "#10B981"
        elif sentiment == 'negative':
            accent_color = "#EF4444"
        else:
            accent_color = "#F59E0B"
        
        self.setStyleSheet(f"""
            QFrame#themeCard {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {Colors.BG_TERTIARY},
                    stop:1 {accent_color}08
                );
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-left: 4px solid {accent_color};
                border-radius: 10px;
            }}
            QFrame#themeCard:hover {{
                border: 2px solid {accent_color};
                border-left: 4px solid {accent_color};
            }}
        """)
        self.setObjectName("themeCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # 顶部：名称 + 热度
        top_layout = QHBoxLayout()
        
        name_label = QLabel(f"🔥 {self.theme.get('name', '未知主线')}")
        name_label.setStyleSheet(f"""
            font-size: 15px;
            font-weight: 700;
            color: {Colors.TEXT_PRIMARY};
        """)
        top_layout.addWidget(name_label)
        top_layout.addStretch()
        
        # 热度徽章
        heat_badge = QLabel(f"热度 {heat}")
        heat_badge.setStyleSheet(f"""
            font-size: 11px;
            font-weight: 600;
            color: {accent_color};
            background-color: {accent_color}20;
            padding: 4px 10px;
            border-radius: 12px;
        """)
        top_layout.addWidget(heat_badge)
        
        layout.addLayout(top_layout)
        
        # 投资逻辑
        logic = self.theme.get('investment_logic', '')
        if len(logic) > 60:
            logic = logic[:60] + '...'
        
        logic_label = QLabel(logic)
        logic_label.setStyleSheet(f"""
            font-size: 12px;
            color: {Colors.TEXT_MUTED};
            line-height: 1.4;
        """)
        logic_label.setWordWrap(True)
        layout.addWidget(logic_label)
        
        layout.addStretch()
        
        # 底部：关键词 + 相关股票数
        bottom_layout = QHBoxLayout()
        
        keywords = self.theme.get('keywords', [])[:3]
        for kw in keywords:
            kw_label = QLabel(kw)
            kw_label.setStyleSheet(f"""
                font-size: 10px;
                color: {Colors.TEXT_SECONDARY};
                background-color: {Colors.BG_PRIMARY};
                padding: 2px 6px;
                border-radius: 4px;
            """)
            bottom_layout.addWidget(kw_label)
        
        bottom_layout.addStretch()
        
        symbols = self.theme.get('related_symbols', [])
        if symbols:
            stock_label = QLabel(f"📈 {len(symbols)}只相关股票")
            stock_label.setStyleSheet(f"font-size: 10px; color: {Colors.PRIMARY};")
            bottom_layout.addWidget(stock_label)
        
        layout.addLayout(bottom_layout)
    
    def mousePressEvent(self, event):
        self.clicked.emit(self.theme)
        super().mousePressEvent(event)


class DataSourceStatusWidget(QFrame):
    """数据源状态组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_manager = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 10px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)
        
        # 标题
        title = QLabel("📡 数据源状态")
        title.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 700;
            color: {Colors.TEXT_PRIMARY};
        """)
        layout.addWidget(title)
        
        # 状态表格
        self.status_layout = QVBoxLayout()
        self.status_layout.setSpacing(8)
        layout.addLayout(self.status_layout)
        
        # 初始化状态
        self.update_status()
        
        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新状态")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY}20;
                color: {Colors.PRIMARY};
                border: 1px solid {Colors.PRIMARY}40;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY}30;
            }}
        """)
        refresh_btn.clicked.connect(self.update_status)
        layout.addWidget(refresh_btn)
    
    def update_status(self):
        """更新数据源状态"""
        # 清除旧状态
        while self.status_layout.count():
            item = self.status_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 尝试获取真实状态
        sources_status = self._get_sources_status()
        
        for name, status in sources_status.items():
            row = QFrame()
            row.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.BG_PRIMARY};
                    border-radius: 6px;
                    padding: 4px;
                }}
            """)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 6, 10, 6)
            
            # 名称
            name_label = QLabel(name)
            name_label.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_PRIMARY};")
            row_layout.addWidget(name_label)
            
            row_layout.addStretch()
            
            # 状态
            is_ok = status.get('status') == 'ok'
            status_color = "#10B981" if is_ok else "#EF4444"
            status_text = "已连接" if is_ok else "未连接"
            
            # 显示账户类型
            account_type = status.get('account_type', '')
            if account_type and account_type != 'N/A':
                type_map = {'trial': '试用版', 'standard': '标准版', 'premium': '高级版'}
                type_text = type_map.get(account_type, account_type)
                status_text = f"{status_text} ({type_text})"
            
            status_label = QLabel(f"● {status_text}")
            status_label.setStyleSheet(f"font-size: 11px; color: {status_color}; font-weight: 600;")
            row_layout.addWidget(status_label)
            
            # 延迟
            if is_ok and 'latency' in status:
                latency_label = QLabel(f"{status['latency']}ms")
                latency_label.setStyleSheet(f"font-size: 10px; color: {Colors.TEXT_MUTED};")
                row_layout.addWidget(latency_label)
            
            self.status_layout.addWidget(row)
    
    def _get_sources_status(self) -> dict:
        """获取数据源状态"""
        try:
            # 使用新的数据源管理器
            from core.data_source_manager import get_data_source_manager
            
            manager = get_data_source_manager()
            all_status = manager.get_all_status()
            
            result = {}
            for source_type, status in all_status.items():
                name_map = {
                    'jqdata': 'JQData',
                    'akshare': 'AKShare',
                    'baostock': 'Baostock',
                    'local_cache': 'MongoDB'
                }
                display_name = name_map.get(source_type.value, source_type.value)
                
                result[display_name] = {
                    'status': 'ok' if status.is_available else 'error',
                    'account_type': status.account_type.value if status.is_available else 'N/A',
                    'date_range': f"{status.start_date or 'N/A'} ~ {status.end_date or 'N/A'}" if status.is_available else '',
                    'is_realtime': status.is_realtime
                }
            
            return result
            
        except Exception as e:
            logger.error(f"获取数据源状态失败: {e}")
            # 回退到旧方法
            try:
                from data_sources import DataSourceManager
                manager = DataSourceManager(use_cache=True)
                manager.connect_source('akshare')
                status = manager.get_status()
                return status.get('sources', {})
            except:
                return {
                    "JQData": {"status": "unknown"},
                    "AKShare": {"status": "unknown"},
                    "MongoDB": {"status": "unknown"},
                }


class DataSourcePanel(QWidget):
    """信息获取面板 - 重构版"""
    
    open_manual = pyqtSignal()
    open_settings = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_manager = None
        self.theme_discovery = None
        self.setup_ui()
        self._init_data_manager()
    
    def _init_data_manager(self):
        """初始化数据源管理器"""
        try:
            # 优先使用新的数据源管理器
            from core.data_source_manager import get_data_source_manager
            self.new_data_manager = get_data_source_manager()
            
            # 保留旧管理器兼容性
            try:
                from data_sources import DataSourceManager
                from data_sources.theme_discovery import ThemeDiscovery
                from data_sources.cache_manager import MongoDBCache
                
                self.data_manager = DataSourceManager(use_cache=True)
                self.data_manager.connect_source('akshare')
                
                cache = MongoDBCache()
                self.theme_discovery = ThemeDiscovery(cache=cache, data_manager=self.data_manager)
            except Exception as e:
                logger.debug(f"旧数据源管理器初始化失败（可忽略）: {e}")
                self.data_manager = None
                self.theme_discovery = None
            
            logger.info("数据源管理器初始化成功")
        except Exception as e:
            logger.error(f"数据源管理器初始化失败: {e}")
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建Tab控件（使用信息获取模块主题色）
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {Colors.BG_SECONDARY};
            }}
            QTabBar::tab {{
                background-color: {Colors.BG_PRIMARY};
                color: {Colors.TEXT_MUTED};
                border: none;
                padding: 12px 24px;
                font-size: 13px;
                font-weight: 600;
                min-width: 100px;
            }}
            QTabBar::tab:selected {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.MODULE_DATA_START};
                border-bottom: 3px solid {Colors.MODULE_DATA_START};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        
        # 添加选项卡（专业主线识别已移至"投资主线"模块）
        self.tab_widget.addTab(self._create_data_sources_tab(), "📊 数据源管理")
        self.tab_widget.addTab(self._create_news_tab(), "📰 资讯聚合")
        self.tab_widget.addTab(self._create_knowledge_tab(), "📚 知识库")
        self.tab_widget.addTab(self._create_tools_tab(), "🔧 工具箱")
        
        layout.addWidget(self.tab_widget)
    
    def _create_themes_tab(self) -> QWidget:
        """创建投资主线Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)
        
        # 顶部说明
        intro_frame = QFrame()
        intro_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.PRIMARY}15,
                    stop:1 {Colors.ACCENT}15
                );
                border: 1px solid {Colors.PRIMARY}30;
                border-radius: 12px;
            }}
        """)
        intro_layout = QVBoxLayout(intro_frame)
        intro_layout.setContentsMargins(20, 16, 20, 16)
        
        intro_title = QLabel("🎯 投资主线发现")
        intro_title.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 700;
            color: {Colors.TEXT_PRIMARY};
        """)
        intro_layout.addWidget(intro_title)
        
        intro_desc = QLabel(
            "基于新闻、市场数据、社交媒体等多维度信息，AI自动发现和追踪当前市场热门投资主线。\n"
            "点击主线卡片可查看详情、相关股票，并一键生成主题策略代码。"
        )
        intro_desc.setStyleSheet(f"""
            font-size: 12px;
            color: {Colors.TEXT_MUTED};
            line-height: 1.5;
        """)
        intro_desc.setWordWrap(True)
        intro_layout.addWidget(intro_desc)
        
        layout.addWidget(intro_frame)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        discover_btn = QPushButton("🔍 发现主线")
        discover_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY}DD;
            }}
        """)
        discover_btn.clicked.connect(self._discover_themes)
        btn_layout.addWidget(discover_btn)
        
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_PRIMARY};
            }}
        """)
        refresh_btn.clicked.connect(self._refresh_themes)
        btn_layout.addWidget(refresh_btn)
        
        btn_layout.addStretch()
        
        # 数据源状态
        status_widget = DataSourceStatusWidget()
        status_widget.setFixedWidth(280)
        btn_layout.addWidget(status_widget)
        
        layout.addLayout(btn_layout)
        
        # 主线卡片区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
        """)
        
        self.themes_container = QWidget()
        self.themes_layout = QGridLayout(self.themes_container)
        self.themes_layout.setContentsMargins(0, 0, 0, 0)
        self.themes_layout.setSpacing(16)
        
        scroll.setWidget(self.themes_container)
        layout.addWidget(scroll)
        
        # 加载默认主线
        self._load_default_themes()
        
        return widget
    
    def _create_data_sources_tab(self) -> QWidget:
        """
        创建数据源管理Tab
        
        设计原则：
        1. 首先介绍方法论 - 数据在量化投资中的作用
        2. 统一管理所有数据类型（API数据、调研报告、社交信息）
        3. 说明每个数据源的功能和在工具链中的位置
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {Colors.BG_SECONDARY};
            }}
        """)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(28, 24, 28, 24)
        content_layout.setSpacing(24)
        
        # ============================================================
        # 1. 方法论介绍 - 数据在量化投资中的作用
        # ============================================================
        methodology_frame = QFrame()
        methodology_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1E3A5F,
                    stop:1 #0F2744
                );
                border-radius: 16px;
                border: 1px solid {Colors.PRIMARY}40;
            }}
        """)
        methodology_layout = QVBoxLayout(methodology_frame)
        methodology_layout.setContentsMargins(28, 24, 28, 24)
        methodology_layout.setSpacing(16)
        
        # 标题
        title = QLabel("📊 数据源管理 - 量化投资的基石")
        title.setStyleSheet(f"""
            font-size: 22px;
            font-weight: 800;
            color: {Colors.TEXT_PRIMARY};
        """)
        methodology_layout.addWidget(title)
        
        # 方法论说明
        methodology_text = QLabel(
            "在量化投资中，<b>数据是一切策略的基础</b>。高质量、及时、准确的数据决定了：\n\n"
            "• <b>因子计算的准确性</b> - 财务数据、行情数据是因子的原材料\n"
            "• <b>策略回测的可靠性</b> - 历史数据的质量直接影响回测结果\n"
            "• <b>实盘交易的稳定性</b> - 实时数据延迟可能导致交易滑点\n"
            "• <b>投资决策的全面性</b> - 另类数据（调研、社交）提供独特视角"
        )
        methodology_text.setStyleSheet(f"""
            font-size: 13px;
            color: {Colors.TEXT_MUTED};
            line-height: 1.8;
        """)
        methodology_text.setWordWrap(True)
        methodology_text.setTextFormat(Qt.TextFormat.RichText)
        methodology_layout.addWidget(methodology_text)
        
        # 数据流程图 - 使用高对比度配色
        flow_layout = QHBoxLayout()
        flow_layout.setSpacing(12)
        
        flow_steps = [
            ("数据采集", "API/终端/调研", "#3B82F6"),
            ("数据清洗", "去噪/对齐/填充", "#10B981"),
            ("数据存储", "MongoDB缓存", "#F59E0B"),
            ("数据应用", "因子/回测/实盘", "#EC4899"),
        ]
        
        for i, (step, desc, color) in enumerate(flow_steps):
            step_frame = QFrame()
            step_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {color};
                    border: none;
                    border-radius: 10px;
                }}
            """)
            step_layout = QVBoxLayout(step_frame)
            step_layout.setContentsMargins(16, 12, 16, 12)
            step_layout.setSpacing(4)
            
            # 标题使用深色文字，确保在亮色背景上可读
            step_label = QLabel(step)
            step_label.setStyleSheet(f"font-size: 13px; font-weight: 700; color: #0d0d14;")
            step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            step_layout.addWidget(step_label)
            
            # 描述也使用深色文字
            desc_label = QLabel(desc)
            desc_label.setStyleSheet(f"font-size: 11px; color: #1a1a2e;")
            desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            step_layout.addWidget(desc_label)
            
            flow_layout.addWidget(step_frame)
            
            if i < len(flow_steps) - 1:
                arrow = QLabel("→")
                arrow.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {Colors.TEXT_SECONDARY};")
                flow_layout.addWidget(arrow)
        
        flow_layout.addStretch()
        methodology_layout.addLayout(flow_layout)
        
        content_layout.addWidget(methodology_frame)
        
        # ============================================================
        # 2. 数据分类管理
        # ============================================================
        categories_title = QLabel("📁 数据分类管理")
        categories_title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 700;
            color: {Colors.TEXT_PRIMARY};
        """)
        content_layout.addWidget(categories_title)
        
        # 数据分类说明
        categories_desc = QLabel(
            "统一管理所有类型的投资数据，包括API数据源、行业调研报告、社交信息等。"
        )
        categories_desc.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_MUTED};")
        content_layout.addWidget(categories_desc)
        
        # 三大数据类别
        categories_layout = QHBoxLayout()
        categories_layout.setSpacing(16)
        
        data_categories = [
            {
                "icon": "🔌",
                "name": "API数据源",
                "desc": "程序化接口获取的标准化数据",
                "color": "#3B82F6",
                "items": ["JQData (主力)", "AKShare (免费)", "Baostock", "通达信(TDX)"],
                "usage": "因子计算、回测、实盘"
            },
            {
                "icon": "📋",
                "name": "调研报告",
                "desc": "行业调研、实地考察、会议纪要",
                "color": "#10B981",
                "items": ["行业调研报告", "公司实地调研", "管理层访谈", "专家会议"],
                "usage": "定性分析、投资逻辑验证"
            },
            {
                "icon": "💬",
                "name": "社交信息",
                "desc": "校友圈、行业交流获得的非公开信息",
                "color": "#F59E0B",
                "items": ["校友信息", "行业交流", "投资人脉", "市场传闻"],
                "usage": "信息优势、投资线索"
            },
        ]
        
        for cat in data_categories:
            cat_frame = QFrame()
            cat_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.BG_TERTIARY};
                    border: 1px solid {cat['color']}30;
                    border-left: 4px solid {cat['color']};
                    border-radius: 10px;
                }}
            """)
            cat_layout = QVBoxLayout(cat_frame)
            cat_layout.setContentsMargins(16, 14, 16, 14)
            cat_layout.setSpacing(10)
            
            # 标题
            header_layout = QHBoxLayout()
            icon_label = QLabel(cat['icon'])
            icon_label.setStyleSheet("font-size: 24px;")
            header_layout.addWidget(icon_label)
            
            name_label = QLabel(cat['name'])
            name_label.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
            header_layout.addWidget(name_label)
            header_layout.addStretch()
            cat_layout.addLayout(header_layout)
            
            # 描述
            desc_label = QLabel(cat['desc'])
            desc_label.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED};")
            cat_layout.addWidget(desc_label)
            
            # 包含项目
            items_text = " | ".join(cat['items'])
            items_label = QLabel(items_text)
            items_label.setStyleSheet(f"font-size: 10px; color: {cat['color']}; background-color: {cat['color']}15; padding: 6px; border-radius: 4px;")
            items_label.setWordWrap(True)
            cat_layout.addWidget(items_label)
            
            # 用途
            usage_label = QLabel(f"📌 用途: {cat['usage']}")
            usage_label.setStyleSheet(f"font-size: 10px; color: {Colors.TEXT_MUTED};")
            cat_layout.addWidget(usage_label)
            
            categories_layout.addWidget(cat_frame)
        
        content_layout.addLayout(categories_layout)
        
        # ============================================================
        # 3. API数据源配置
        # ============================================================
        api_title = QLabel("🔌 API数据源配置")
        api_title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 700;
            color: {Colors.TEXT_PRIMARY};
            margin-top: 8px;
        """)
        content_layout.addWidget(api_title)
        
        # API数据源详细说明
        api_sources = [
            {
                "name": "JQData (聚宽)",
                "status": "已配置",
                "color": "#10B981",
                "desc": "本平台主力数据源，提供A股全量数据",
                "data_types": ["日/分钟行情", "财务数据", "因子数据", "Level2数据", "板块数据"],
                "usage_in_workflow": [
                    "因子构建 → 提供财务和行情数据计算因子",
                    "策略回测 → 提供历史数据进行回测",
                    "投资主线 → 提供板块和资金流向数据",
                ],
                "api_example": "from jqdatasdk import *\nauth('账号', '密码')\ndf = get_price('000001.XSHE', start_date='2024-01-01')",
                "test_func": "test_jqdata",
            },
            {
                "name": "AKShare",
                "status": "已配置",
                "color": "#10B981",
                "desc": "免费开源数据源，作为JQData的补充",
                "data_types": ["实时行情", "板块数据", "资金流向", "宏观数据", "另类数据"],
                "usage_in_workflow": [
                    "投资主线 → 获取板块热度和资金流向",
                    "资讯聚合 → 获取财经新闻",
                    "宏观分析 → 获取宏观经济指标",
                ],
                "api_example": "import akshare as ak\ndf = ak.stock_zh_a_spot_em()  # 获取A股实时行情",
                "test_func": "test_akshare",
            },
            {
                "name": "TuShare Pro",
                "status": "可配置",
                "color": "#F59E0B",
                "desc": "社区活跃的免费数据源",
                "data_types": ["股票数据", "基金数据", "期货数据", "港股数据"],
                "usage_in_workflow": [
                    "数据补充 → 获取TuShare特有数据",
                    "跨市场分析 → 获取港股等数据",
                ],
                "api_example": "import tushare as ts\npro = ts.pro_api('TOKEN')\ndf = pro.daily(ts_code='000001.SZ')",
                "test_func": "test_tushare",
            },
            {
                "name": "Baostock",
                "status": "可配置",
                "color": "#10B981",
                "desc": "证券宝开源数据，提供长历史数据（适合试用账户补充）",
                "data_types": ["日K线(1990年至今)", "分钟线", "财务数据", "除权因子"],
                "usage_in_workflow": [
                    "历史数据 → 提供超长历史回测数据",
                    "JQData备用 → 试用账户时的数据补充",
                    "因子计算 → 提供财务数据支持",
                ],
                "api_example": "import baostock as bs\nbs.login()\nrs = bs.query_history_k_data('sh.600519', 'date,open,close')",
                "test_func": "test_baostock",
            },
            {
                "name": "通达信(TDX)",
                "status": "可配置",
                "color": "#8B5CF6",
                "desc": "读取本地通达信数据文件，支持分钟级数据",
                "data_types": ["日K线", "分钟K线", "Tick数据", "财务数据"],
                "usage_in_workflow": [
                    "本地数据 → 读取已下载的通达信数据",
                    "高频回测 → 提供分钟级历史数据",
                    "离线分析 → 无需网络即可分析",
                ],
                "api_example": "from core.tdx_data_reader import TDXDataReader\nreader = TDXDataReader('/path/to/tdx')\ndf = reader.read_daily_data('000001')",
                "test_func": "test_tdx",
            },
        ]
        
        for source in api_sources:
            source_frame = QFrame()
            source_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.BG_TERTIARY};
                    border: 1px solid {Colors.BORDER_PRIMARY};
                    border-radius: 12px;
                }}
            """)
            source_layout = QVBoxLayout(source_frame)
            source_layout.setContentsMargins(20, 16, 20, 16)
            source_layout.setSpacing(12)
            
            # 标题行
            header = QHBoxLayout()
            name = QLabel(source['name'])
            name.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
            header.addWidget(name)
            
            status = QLabel(source['status'])
            status.setStyleSheet(f"""
                font-size: 11px;
                font-weight: 600;
                color: {source['color']};
                background-color: {source['color']}20;
                padding: 4px 10px;
                border-radius: 10px;
            """)
            header.addWidget(status)
            header.addStretch()
            
            # 测试连接按钮
            test_btn = QPushButton("🔗 测试连接")
            test_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.PRIMARY};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {Colors.PRIMARY_DARK};
                }}
            """)
            test_func_name = source.get('test_func', 'test_' + source['name'].lower().replace(' ', '_'))
            test_btn.clicked.connect(lambda checked, name=source['name']: self._test_data_source(name))
            header.addWidget(test_btn)
            
            # 配置按钮
            config_btn = QPushButton("⚙️ 配置")
            config_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.BG_PRIMARY};
                    color: {Colors.TEXT_PRIMARY};
                    border: 1px solid {Colors.BORDER_PRIMARY};
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {Colors.BG_HOVER};
                }}
            """)
            header.addWidget(config_btn)
            source_layout.addLayout(header)
            
            # 描述
            desc = QLabel(source['desc'])
            desc.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_MUTED};")
            source_layout.addWidget(desc)
            
            # 数据类型
            data_types_layout = QHBoxLayout()
            data_types_layout.setSpacing(6)
            for dt in source['data_types']:
                tag = QLabel(dt)
                tag.setStyleSheet(f"""
                    font-size: 10px;
                    color: {Colors.PRIMARY};
                    background-color: {Colors.PRIMARY}15;
                    padding: 3px 8px;
                    border-radius: 4px;
                """)
                data_types_layout.addWidget(tag)
            data_types_layout.addStretch()
            source_layout.addLayout(data_types_layout)
            
            # 在工具链中的使用
            usage_title = QLabel("📌 在工具链中的使用:")
            usage_title.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {Colors.TEXT_PRIMARY}; margin-top: 4px;")
            source_layout.addWidget(usage_title)
            
            for usage in source['usage_in_workflow']:
                usage_label = QLabel(f"  • {usage}")
                usage_label.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED};")
                source_layout.addWidget(usage_label)
            
            # API示例
            example_title = QLabel("💻 API调用示例:")
            example_title.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {Colors.TEXT_PRIMARY}; margin-top: 4px;")
            source_layout.addWidget(example_title)
            
            example_code = QLabel(source['api_example'])
            example_code.setStyleSheet(f"""
                font-size: 10px;
                font-family: 'Consolas', 'Monaco', monospace;
                color: {Colors.TEXT_PRIMARY};
                background-color: {Colors.BG_PRIMARY};
                padding: 10px;
                border-radius: 6px;
                border: 1px solid {Colors.BORDER_PRIMARY};
            """)
            example_code.setWordWrap(True)
            source_layout.addWidget(example_code)
            
            content_layout.addWidget(source_frame)
        
        # ============================================================
        # 4. 调研报告管理（完整功能模块）
        # ============================================================
        research_title = QLabel("📋 调研报告管理")
        research_title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 700;
            color: {Colors.TEXT_PRIMARY};
            margin-top: 8px;
        """)
        content_layout.addWidget(research_title)
        
        research_frame = QFrame()
        research_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 12px;
            }}
        """)
        research_layout = QVBoxLayout(research_frame)
        research_layout.setContentsMargins(20, 16, 20, 16)
        research_layout.setSpacing(16)
        
        # 功能说明
        research_desc = QLabel(
            "<b>📁 统一管理所有调研资料</b><br><br>"
            "存储和管理行业调研报告、实地考察记录、专家会议纪要、校友圈信息等非结构化数据。<br>"
            "这些信息作为知识库的重要组成部分，在策略开发时会被自动检索和参考。"
        )
        research_desc.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_MUTED}; line-height: 1.6;")
        research_desc.setWordWrap(True)
        research_desc.setTextFormat(Qt.TextFormat.RichText)
        research_layout.addWidget(research_desc)
        
        # 默认存储路径
        path_frame = QFrame()
        path_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.PRIMARY}30;
                border-radius: 8px;
            }}
        """)
        path_layout = QHBoxLayout(path_frame)
        path_layout.setContentsMargins(14, 10, 14, 10)
        
        path_icon = QLabel("📂")
        path_icon.setStyleSheet("font-size: 18px;")
        path_layout.addWidget(path_icon)
        
        path_info = QVBoxLayout()
        path_info.setSpacing(2)
        path_label = QLabel("默认存储路径")
        path_label.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED};")
        path_info.addWidget(path_label)
        
        from pathlib import Path
        default_path = Path.home() / ".local/share/trquant/data/research_reports"
        path_value = QLabel(str(default_path))
        path_value.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {Colors.PRIMARY}; font-family: 'Consolas', monospace;")
        path_info.addWidget(path_value)
        path_layout.addLayout(path_info)
        path_layout.addStretch()
        
        open_folder_btn = QPushButton("📂 打开文件夹")
        open_folder_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 8px 14px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_HOVER};
            }}
        """)
        open_folder_btn.clicked.connect(lambda: self._open_research_folder())
        path_layout.addWidget(open_folder_btn)
        research_layout.addWidget(path_frame)
        
        # 报告分类（5种类型）
        report_types_layout = QHBoxLayout()
        report_types_layout.setSpacing(10)
        
        report_types = [
            ("🏭", "行业调研", "industry", "产业链分析", "#3B82F6"),
            ("🏢", "公司调研", "company", "实地考察", "#10B981"),
            ("🎤", "专家会议", "expert", "专家观点", "#F59E0B"),
            ("📊", "券商研报", "broker", "研究报告", "#8B5CF6"),
            ("💬", "社交信息", "social", "校友圈/人脉", "#EC4899"),
        ]
        
        for icon, name, category, desc, color in report_types:
            type_frame = QFrame()
            type_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {color}10;
                    border: 1px solid {color}30;
                    border-radius: 8px;
                }}
                QFrame:hover {{
                    background-color: {color}20;
                    border: 1px solid {color}50;
                }}
            """)
            type_frame.setCursor(Qt.CursorShape.PointingHandCursor)
            type_layout = QVBoxLayout(type_frame)
            type_layout.setContentsMargins(12, 10, 12, 10)
            type_layout.setSpacing(4)
            
            icon_label = QLabel(icon)
            icon_label.setStyleSheet("font-size: 22px;")
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            type_layout.addWidget(icon_label)
            
            name_label = QLabel(name)
            name_label.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {color};")
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            type_layout.addWidget(name_label)
            
            desc_label = QLabel(desc)
            desc_label.setStyleSheet(f"font-size: 9px; color: {Colors.TEXT_MUTED};")
            desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            type_layout.addWidget(desc_label)
            
            report_types_layout.addWidget(type_frame)
        
        research_layout.addLayout(report_types_layout)
        
        # 报告统计和操作区
        stats_ops_layout = QHBoxLayout()
        stats_ops_layout.setSpacing(16)
        
        # 左侧：统计信息
        stats_frame = QFrame()
        stats_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
            }}
        """)
        stats_layout = QVBoxLayout(stats_frame)
        stats_layout.setContentsMargins(14, 12, 14, 12)
        stats_layout.setSpacing(8)
        
        stats_title = QLabel("📊 报告统计")
        stats_title.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        stats_layout.addWidget(stats_title)
        
        self.research_stats_label = QLabel("正在加载统计信息...")
        self.research_stats_label.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED}; line-height: 1.6;")
        stats_layout.addWidget(self.research_stats_label)
        
        stats_ops_layout.addWidget(stats_frame, stretch=1)
        
        # 右侧：操作按钮
        ops_frame = QFrame()
        ops_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
            }}
        """)
        ops_layout = QVBoxLayout(ops_frame)
        ops_layout.setContentsMargins(14, 12, 14, 12)
        ops_layout.setSpacing(8)
        
        ops_title = QLabel("⚡ 快捷操作")
        ops_title.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        ops_layout.addWidget(ops_title)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        upload_btn = QPushButton("📤 上传报告")
        upload_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #10B981;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 14px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #059669;
            }}
        """)
        upload_btn.clicked.connect(self._upload_research_report)
        btn_layout.addWidget(upload_btn)
        
        add_note_btn = QPushButton("📝 新建笔记")
        add_note_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #3B82F6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 14px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #2563EB;
            }}
        """)
        add_note_btn.clicked.connect(self._add_research_note)
        btn_layout.addWidget(add_note_btn)
        
        scan_btn = QPushButton("🔍 扫描文件夹")
        scan_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 8px 14px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_HOVER};
            }}
        """)
        scan_btn.clicked.connect(self._scan_research_folder)
        btn_layout.addWidget(scan_btn)
        
        ops_layout.addLayout(btn_layout)
        stats_ops_layout.addWidget(ops_frame, stretch=1)
        
        research_layout.addLayout(stats_ops_layout)
        
        # 最近报告列表
        recent_title = QLabel("📋 最近添加的报告")
        recent_title.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {Colors.TEXT_PRIMARY}; margin-top: 4px;")
        research_layout.addWidget(recent_title)
        
        self.recent_reports_table = QTableWidget()
        self.recent_reports_table.setColumnCount(5)
        self.recent_reports_table.setHorizontalHeaderLabels(["标题", "类型", "日期", "关联股票", "操作"])
        self.recent_reports_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                gridline-color: {Colors.BORDER_PRIMARY};
            }}
            QTableWidget::item {{
                padding: 8px;
                color: {Colors.TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_MUTED};
                border: none;
                padding: 8px;
                font-size: 11px;
                font-weight: 600;
            }}
        """)
        self.recent_reports_table.setMaximumHeight(180)
        self.recent_reports_table.horizontalHeader().setStretchLastSection(True)
        self.recent_reports_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.recent_reports_table.verticalHeader().setVisible(False)
        self.recent_reports_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        research_layout.addWidget(self.recent_reports_table)
        
        # 策略集成说明
        integration_frame = QFrame()
        integration_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #10B98115;
                border: 1px solid #10B98130;
                border-radius: 8px;
            }}
        """)
        integration_layout = QHBoxLayout(integration_frame)
        integration_layout.setContentsMargins(14, 10, 14, 10)
        
        integration_icon = QLabel("💡")
        integration_icon.setStyleSheet("font-size: 18px;")
        integration_layout.addWidget(integration_icon)
        
        integration_text = QLabel(
            "<b>策略开发集成</b>：所有调研报告会被自动索引，在策略开发时可通过关联股票或标签进行检索，"
            "AI助手会参考相关调研内容生成更准确的投资逻辑。"
        )
        integration_text.setStyleSheet(f"font-size: 11px; color: #10B981; line-height: 1.5;")
        integration_text.setWordWrap(True)
        integration_text.setTextFormat(Qt.TextFormat.RichText)
        integration_layout.addWidget(integration_text)
        
        research_layout.addWidget(integration_frame)
        
        content_layout.addWidget(research_frame)
        
        # 加载报告统计
        QTimer.singleShot(500, self._update_research_stats)
        
        # ============================================================
        # 5. 数据源连接状态面板
        # ============================================================
        status_title = QLabel("📡 数据源连接状态")
        status_title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 700;
            color: {Colors.TEXT_PRIMARY};
            margin-top: 8px;
        """)
        content_layout.addWidget(status_title)
        
        status_desc = QLabel(
            "实时监控所有数据源的连接状态，确保数据获取正常。点击\"测试连接\"检查各API可用性。"
        )
        status_desc.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_MUTED};")
        content_layout.addWidget(status_desc)
        
        # 导入并添加数据状态面板
        try:
            from gui.widgets.data_status_panel import DataStatusPanel
            self.data_status_panel = DataStatusPanel()
            self.data_status_panel.setMaximumHeight(500)
            content_layout.addWidget(self.data_status_panel)
        except Exception as e:
            logger.error(f"加载数据状态面板失败: {e}")
            # 降级显示
            cache_frame = QFrame()
            cache_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.BG_TERTIARY};
                    border: 1px solid {Colors.BORDER_PRIMARY};
                    border-radius: 12px;
                }}
            """)
            cache_layout = QVBoxLayout(cache_frame)
            cache_layout.setContentsMargins(20, 16, 20, 16)
            cache_layout.setSpacing(10)
            
            self.cache_status_label = QLabel(f"数据状态面板加载失败: {e}")
            self.cache_status_label.setStyleSheet(f"font-size: 12px; color: {Colors.ERROR};")
            cache_layout.addWidget(self.cache_status_label)
            
            content_layout.addWidget(cache_frame)
        
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return widget
    
    def _open_research_folder(self):
        """打开调研报告文件夹"""
        from pathlib import Path
        import subprocess
        import platform
        
        folder = Path.home() / ".local/share/trquant/data/research_reports"
        folder.mkdir(parents=True, exist_ok=True)
        
        try:
            if platform.system() == "Linux":
                subprocess.run(["xdg-open", str(folder)])
            elif platform.system() == "Darwin":
                subprocess.run(["open", str(folder)])
            else:
                subprocess.run(["explorer", str(folder)])
        except Exception as e:
            QMessageBox.warning(self, "打开失败", f"无法打开文件夹: {e}")
    
    def _upload_research_report(self):
        """上传调研报告"""
        from PyQt6.QtWidgets import QFileDialog, QDialog, QFormLayout, QDialogButtonBox
        
        # 选择文件
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择调研报告",
            str(Path.home()),
            "支持的文件 (*.pdf *.doc *.docx *.md *.txt);;PDF文件 (*.pdf);;Word文档 (*.doc *.docx);;Markdown (*.md);;文本文件 (*.txt)"
        )
        
        if not file_path:
            return
        
        # 弹出信息填写对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("📋 添加调研报告")
        dialog.setMinimumWidth(500)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_SECONDARY};
            }}
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-size: 12px;
            }}
            QLineEdit, QComboBox, QTextEdit {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }}
        """)
        
        layout = QFormLayout(dialog)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        
        # 标题
        title_edit = QLineEdit()
        title_edit.setText(Path(file_path).stem)
        layout.addRow("标题:", title_edit)
        
        # 分类
        category_combo = QComboBox()
        category_combo.addItems(["行业调研", "公司调研", "专家会议", "券商研报", "社交信息"])
        layout.addRow("分类:", category_combo)
        
        # 关联股票
        stocks_edit = QLineEdit()
        stocks_edit.setPlaceholderText("如: 000001.SZ, 600000.SH（多个用逗号分隔）")
        layout.addRow("关联股票:", stocks_edit)
        
        # 标签
        tags_edit = QLineEdit()
        tags_edit.setPlaceholderText("如: 新能源, 锂电池, 产业链（多个用逗号分隔）")
        layout.addRow("标签:", tags_edit)
        
        # 摘要
        summary_edit = QTextEdit()
        summary_edit.setMaximumHeight(80)
        summary_edit.setPlaceholderText("报告核心内容摘要...")
        layout.addRow("摘要:", summary_edit)
        
        # 投资逻辑
        logic_edit = QTextEdit()
        logic_edit.setMaximumHeight(60)
        logic_edit.setPlaceholderText("从报告中提取的投资逻辑...")
        layout.addRow("投资逻辑:", logic_edit)
        
        # 风险提示
        risk_edit = QLineEdit()
        risk_edit.setPlaceholderText("需要注意的风险点...")
        layout.addRow("风险提示:", risk_edit)
        
        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                from data_sources.research_manager import get_research_manager, REPORT_CATEGORIES
                
                # 分类映射
                category_map = {
                    "行业调研": "industry",
                    "公司调研": "company",
                    "专家会议": "expert",
                    "券商研报": "broker",
                    "社交信息": "social",
                }
                
                manager = get_research_manager()
                report = manager.add_report(
                    title=title_edit.text(),
                    category=category_map.get(category_combo.currentText(), "industry"),
                    file_path=file_path,
                    tags=[t.strip() for t in tags_edit.text().split(",") if t.strip()],
                    related_stocks=[s.strip() for s in stocks_edit.text().split(",") if s.strip()],
                    summary=summary_edit.toPlainText(),
                    investment_logic=logic_edit.toPlainText(),
                    risk_notes=risk_edit.text(),
                )
                
                QMessageBox.information(
                    self,
                    "上传成功",
                    f"✅ 调研报告已添加到知识库\n\n"
                    f"标题: {report.title}\n"
                    f"分类: {category_combo.currentText()}\n"
                    f"文件已保存到: {report.file_path}"
                )
                
                # 刷新统计和列表
                self._update_research_stats()
                
            except Exception as e:
                QMessageBox.critical(self, "上传失败", f"添加报告时出错: {e}")
    
    def _add_research_note(self):
        """新建调研笔记"""
        from PyQt6.QtWidgets import QDialog, QFormLayout, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("📝 新建调研笔记")
        dialog.setMinimumWidth(550)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_SECONDARY};
            }}
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-size: 12px;
            }}
            QLineEdit, QComboBox, QTextEdit {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }}
        """)
        
        layout = QFormLayout(dialog)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        
        # 标题
        title_edit = QLineEdit()
        title_edit.setPlaceholderText("调研笔记标题")
        layout.addRow("标题:", title_edit)
        
        # 分类
        category_combo = QComboBox()
        category_combo.addItems(["行业调研", "公司调研", "专家会议", "券商研报", "社交信息"])
        layout.addRow("分类:", category_combo)
        
        # 来源
        source_edit = QLineEdit()
        source_edit.setPlaceholderText("如: 某公司实地调研、某校友分享、行业专家电话会")
        layout.addRow("信息来源:", source_edit)
        
        # 关联股票
        stocks_edit = QLineEdit()
        stocks_edit.setPlaceholderText("如: 000001.SZ, 600000.SH（多个用逗号分隔）")
        layout.addRow("关联股票:", stocks_edit)
        
        # 标签
        tags_edit = QLineEdit()
        tags_edit.setPlaceholderText("如: 新能源, 锂电池, 产业链（多个用逗号分隔）")
        layout.addRow("标签:", tags_edit)
        
        # 内容
        content_edit = QTextEdit()
        content_edit.setMinimumHeight(150)
        content_edit.setPlaceholderText(
            "记录调研内容...\n\n"
            "建议包含：\n"
            "1. 核心信息点\n"
            "2. 投资逻辑\n"
            "3. 风险提示\n"
            "4. 后续跟进事项"
        )
        layout.addRow("内容:", content_edit)
        
        # 投资逻辑
        logic_edit = QTextEdit()
        logic_edit.setMaximumHeight(60)
        logic_edit.setPlaceholderText("提炼的投资逻辑...")
        layout.addRow("投资逻辑:", logic_edit)
        
        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if not title_edit.text().strip():
                QMessageBox.warning(self, "提示", "请输入笔记标题")
                return
            
            if not content_edit.toPlainText().strip():
                QMessageBox.warning(self, "提示", "请输入笔记内容")
                return
            
            try:
                from data_sources.research_manager import get_research_manager
                
                category_map = {
                    "行业调研": "industry",
                    "公司调研": "company",
                    "专家会议": "expert",
                    "券商研报": "broker",
                    "社交信息": "social",
                }
                
                manager = get_research_manager()
                report = manager.add_report(
                    title=title_edit.text(),
                    category=category_map.get(category_combo.currentText(), "industry"),
                    content=content_edit.toPlainText(),
                    source=source_edit.text(),
                    tags=[t.strip() for t in tags_edit.text().split(",") if t.strip()],
                    related_stocks=[s.strip() for s in stocks_edit.text().split(",") if s.strip()],
                    investment_logic=logic_edit.toPlainText(),
                )
                
                QMessageBox.information(
                    self,
                    "保存成功",
                    f"✅ 调研笔记已保存\n\n"
                    f"标题: {report.title}\n"
                    f"分类: {category_combo.currentText()}\n"
                    f"文件: {report.file_path}"
                )
                
                self._update_research_stats()
                
            except Exception as e:
                QMessageBox.critical(self, "保存失败", f"保存笔记时出错: {e}")
    
    def _scan_research_folder(self):
        """扫描文件夹发现未索引的文件"""
        try:
            from data_sources.research_manager import get_research_manager
            
            manager = get_research_manager()
            unindexed = manager.scan_folder()
            
            if not unindexed:
                QMessageBox.information(
                    self,
                    "扫描完成",
                    "✅ 所有文件都已索引，没有发现新文件。"
                )
            else:
                file_list = "\n".join([f"• {Path(f).name}" for f in unindexed[:10]])
                if len(unindexed) > 10:
                    file_list += f"\n... 还有 {len(unindexed) - 10} 个文件"
                
                reply = QMessageBox.question(
                    self,
                    "发现未索引文件",
                    f"发现 {len(unindexed)} 个未索引的文件：\n\n{file_list}\n\n"
                    "是否逐个添加到知识库？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # TODO: 实现批量添加
                    QMessageBox.information(
                        self,
                        "提示",
                        "请使用「上传报告」功能逐个添加文件，\n或直接将文件放入对应分类文件夹后刷新。"
                    )
        except Exception as e:
            QMessageBox.critical(self, "扫描失败", f"扫描文件夹时出错: {e}")
    
    def _update_research_stats(self):
        """更新调研报告统计"""
        try:
            from data_sources.research_manager import get_research_manager, REPORT_CATEGORIES
            
            manager = get_research_manager()
            stats = manager.get_statistics()
            
            # 更新统计标签
            cat_stats = []
            for cat_key, count in stats['by_category'].items():
                cat_name = REPORT_CATEGORIES.get(cat_key, {}).get('name', cat_key)
                cat_stats.append(f"{cat_name}: {count}份")
            
            stats_text = (
                f"📊 总计: <b>{stats['total']}</b> 份报告\n"
                f"📅 最近7天: <b>{stats['recent_7_days']}</b> 份\n"
                f"📁 分类: {' | '.join(cat_stats) if cat_stats else '暂无'}\n"
                f"🏷️ 覆盖股票: {len(stats['stocks_covered'])} 只"
            )
            self.research_stats_label.setText(stats_text)
            self.research_stats_label.setTextFormat(Qt.TextFormat.RichText)
            
            # 更新最近报告列表
            reports = manager.list_reports(limit=5)
            self.recent_reports_table.setRowCount(len(reports))
            
            category_names = {
                "industry": "🏭 行业调研",
                "company": "🏢 公司调研",
                "expert": "🎤 专家会议",
                "broker": "📊 券商研报",
                "social": "💬 社交信息",
            }
            
            for i, report in enumerate(reports):
                self.recent_reports_table.setItem(i, 0, QTableWidgetItem(report.title))
                self.recent_reports_table.setItem(i, 1, QTableWidgetItem(category_names.get(report.category, report.category)))
                self.recent_reports_table.setItem(i, 2, QTableWidgetItem(report.date))
                self.recent_reports_table.setItem(i, 3, QTableWidgetItem(", ".join(report.related_stocks[:3])))
                
                # 操作按钮
                view_btn = QPushButton("查看")
                view_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {Colors.PRIMARY}20;
                        color: {Colors.PRIMARY};
                        border: none;
                        border-radius: 4px;
                        padding: 4px 8px;
                        font-size: 10px;
                    }}
                """)
                view_btn.clicked.connect(lambda checked, r=report: self._view_report(r))
                self.recent_reports_table.setCellWidget(i, 4, view_btn)
            
        except Exception as e:
            self.research_stats_label.setText(f"加载失败: {e}")
            logger.error(f"更新调研报告统计失败: {e}")
    
    def _view_report(self, report):
        """查看报告详情"""
        from PyQt6.QtWidgets import QDialog, QTextBrowser
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"📋 {report.title}")
        dialog.setMinimumSize(600, 500)
        dialog.setStyleSheet(f"background-color: {Colors.BG_SECONDARY};")
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 16, 20, 16)
        
        # 报告内容
        browser = QTextBrowser()
        browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 8px;
                padding: 16px;
                font-size: 13px;
            }}
        """)
        
        html = f"""
        <h2>{report.title}</h2>
        <p><b>分类:</b> {report.category} | <b>日期:</b> {report.date} | <b>来源:</b> {report.source}</p>
        <hr>
        <h3>📌 摘要</h3>
        <p>{report.summary or '暂无摘要'}</p>
        <h3>💡 投资逻辑</h3>
        <p>{report.investment_logic or '暂无'}</p>
        <h3>⚠️ 风险提示</h3>
        <p>{report.risk_notes or '暂无'}</p>
        <h3>🏷️ 标签</h3>
        <p>{', '.join(report.tags) if report.tags else '暂无'}</p>
        <h3>📈 关联股票</h3>
        <p>{', '.join(report.related_stocks) if report.related_stocks else '暂无'}</p>
        """
        
        if report.file_path:
            html += f"<h3>📁 文件</h3><p>{report.file_path}</p>"
        
        browser.setHtml(html)
        layout.addWidget(browser)
        
        # 打开文件按钮
        if report.file_path and Path(report.file_path).exists():
            open_btn = QPushButton("📂 打开原始文件")
            open_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.PRIMARY};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 12px;
                }}
            """)
            open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(report.file_path)))
            layout.addWidget(open_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        dialog.exec()
    
    def _create_news_tab(self) -> QWidget:
        """创建资讯Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)
        
        # 顶部说明
        intro = QLabel(
            "📰 <b>财经资讯聚合</b><br>"
            f"<span style='color: {Colors.TEXT_SECONDARY};'>实时财经新闻和市场动态，支持关键词过滤和主题分类。</span>"
        )
        intro.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_PRIMARY};")
        intro.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(intro)
        
        # 快速链接
        links_frame = QFrame()
        links_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 10px;
            }}
        """)
        links_layout = QHBoxLayout(links_frame)
        links_layout.setContentsMargins(16, 12, 16, 12)
        links_layout.setSpacing(12)
        
        news_sources = [
            ("财联社", "https://www.cls.cn/", "#EC4899"),
            ("第一财经", "https://www.yicai.com/", "#3B82F6"),
            ("华尔街见闻", "https://wallstreetcn.com/", "#10B981"),
            ("新浪财经", "https://finance.sina.com.cn/", "#F59E0B"),
            ("Bloomberg", "https://www.bloomberg.com/", "#8B5CF6"),
        ]
        
        for name, url, color in news_sources:
            btn = QPushButton(name)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color}20;
                    color: {color};
                    border: 1px solid {color}40;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 12px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {color}30;
                }}
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, u=url: QDesktopServices.openUrl(QUrl(u)))
            links_layout.addWidget(btn)
        
        links_layout.addStretch()
        layout.addWidget(links_frame)
        
        # 资讯列表（占位）
        news_frame = QFrame()
        news_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 10px;
            }}
        """)
        news_layout = QVBoxLayout(news_frame)
        news_layout.setContentsMargins(16, 14, 16, 14)
        
        news_title = QLabel("📋 最新资讯")
        news_title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        news_layout.addWidget(news_title)
        
        fetch_btn = QPushButton("🔄 获取最新资讯")
        fetch_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY}DD;
            }}
        """)
        fetch_btn.clicked.connect(self._fetch_news)
        news_layout.addWidget(fetch_btn)
        
        self.news_list = QTextEdit()
        self.news_list.setReadOnly(True)
        self.news_list.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_PRIMARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 10px;
                font-size: 12px;
            }}
        """)
        self.news_list.setPlaceholderText("点击上方按钮获取最新资讯...")
        news_layout.addWidget(self.news_list)
        
        layout.addWidget(news_frame)
        
        return widget
    
    def _create_knowledge_tab(self) -> QWidget:
        """创建知识库Tab - 整合所有信息源分类"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {Colors.BORDER_PRIMARY};
                width: 1px;
            }}
        """)
        
        # 左侧：分类导航
        left_panel = QFrame()
        left_panel.setFixedWidth(220)
        left_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border-right: 1px solid {Colors.BORDER_PRIMARY};
            }}
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # 标题
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_SECONDARY};
                border-bottom: 1px solid {Colors.BORDER_PRIMARY};
            }}
        """)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        
        title = QLabel("📚 信息源总览")
        title.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 700;
            color: {Colors.TEXT_PRIMARY};
        """)
        header_layout.addWidget(title)
        
        subtitle = QLabel("全方位投资信息资源")
        subtitle.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED};")
        header_layout.addWidget(subtitle)
        
        left_layout.addWidget(header)
        
        # 分类按钮
        scroll_left = QScrollArea()
        scroll_left.setWidgetResizable(True)
        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_left.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {Colors.BG_PRIMARY};
            }}
            QScrollBar:vertical {{ width: 0px; }}
        """)
        
        categories_widget = QWidget()
        categories_widget.setStyleSheet(f"background-color: {Colors.BG_PRIMARY};")
        categories_layout = QVBoxLayout(categories_widget)
        categories_layout.setContentsMargins(10, 12, 10, 12)
        categories_layout.setSpacing(4)
        
        self.knowledge_category_buttons = {}
        
        # 分类配色
        category_colors = {
            "knowledge": "#8B5CF6",
            "quant_data": "#3B82F6",
            "news": "#EC4899",
            "macro": "#6366F1",
            "company": "#14B8A6",
            "community": "#F59E0B",
            "research": "#10B981",
            "alternative": "#F97316",
            "tools": "#06B6D4",
        }
        
        for key, data in DATA_SOURCES.items():
            color = category_colors.get(key, Colors.PRIMARY)
            source_count = len(data["sources"])
            
            btn = QPushButton(f"  {data['icon']}  {data['name'].replace(data['icon'], '').strip()}  ({source_count})")
            btn.setCheckable(True)
            btn.setFixedHeight(38)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    border-radius: 6px;
                    padding: 0px 10px;
                    text-align: left;
                    font-size: 12px;
                    color: {Colors.TEXT_SECONDARY};
                }}
                QPushButton:hover {{
                    background-color: {color}15;
                    color: {Colors.TEXT_PRIMARY};
                }}
                QPushButton:checked {{
                    background-color: {color}20;
                    color: {color};
                    font-weight: 600;
                    border-left: 3px solid {color};
                    border-radius: 0px 6px 6px 0px;
                }}
            """)
            btn.clicked.connect(lambda checked, k=key: self._select_knowledge_category(k))
            categories_layout.addWidget(btn)
            self.knowledge_category_buttons[key] = btn
        
        categories_layout.addStretch()
        
        # 统计信息
        total_sources = sum(len(cat["sources"]) for cat in DATA_SOURCES.values())
        stats_label = QLabel(f"📊 共 {len(DATA_SOURCES)} 个分类，{total_sources} 个信息源")
        stats_label.setStyleSheet(f"""
            font-size: 11px;
            color: {Colors.TEXT_MUTED};
            padding: 12px;
            background-color: {Colors.BG_SECONDARY};
            border-top: 1px solid {Colors.BORDER_PRIMARY};
        """)
        stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        scroll_left.setWidget(categories_widget)
        left_layout.addWidget(scroll_left)
        left_layout.addWidget(stats_label)
        
        splitter.addWidget(left_panel)
        
        # 右侧：内容区域
        right_panel = QFrame()
        right_panel.setStyleSheet(f"background-color: {Colors.BG_SECONDARY};")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # 内容头部
        self.knowledge_header = QFrame()
        self.knowledge_header.setFixedHeight(80)
        self.knowledge_header.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border-bottom: 1px solid {Colors.BORDER_PRIMARY};
            }}
        """)
        kh_layout = QHBoxLayout(self.knowledge_header)
        kh_layout.setContentsMargins(24, 16, 24, 16)
        
        kh_text = QVBoxLayout()
        self.knowledge_title = QLabel("📚 知识库")
        self.knowledge_title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        kh_text.addWidget(self.knowledge_title)
        
        self.knowledge_desc = QLabel("系统化投资理论、策略和案例分析")
        self.knowledge_desc.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_MUTED};")
        kh_text.addWidget(self.knowledge_desc)
        
        kh_layout.addLayout(kh_text)
        kh_layout.addStretch()
        
        self.knowledge_count = QLabel("5 个信息源")
        self.knowledge_count.setStyleSheet(f"""
            font-size: 11px;
            font-weight: 600;
            color: {Colors.PRIMARY};
            background-color: {Colors.PRIMARY}15;
            padding: 6px 14px;
            border-radius: 16px;
        """)
        kh_layout.addWidget(self.knowledge_count)
        
        right_layout.addWidget(self.knowledge_header)
        
        # 内容滚动区域
        self.knowledge_scroll = QScrollArea()
        self.knowledge_scroll.setWidgetResizable(True)
        self.knowledge_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.knowledge_scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {Colors.BG_SECONDARY};
            }}
            QScrollBar:vertical {{
                background-color: {Colors.BG_SECONDARY};
                width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {Colors.BORDER_PRIMARY};
                border-radius: 4px;
            }}
        """)
        
        self.knowledge_content = QWidget()
        self.knowledge_content.setStyleSheet(f"background-color: {Colors.BG_SECONDARY};")
        self.knowledge_content_layout = QGridLayout(self.knowledge_content)
        self.knowledge_content_layout.setContentsMargins(24, 20, 24, 20)
        self.knowledge_content_layout.setSpacing(16)
        
        self.knowledge_scroll.setWidget(self.knowledge_content)
        right_layout.addWidget(self.knowledge_scroll)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([220, 800])
        
        layout.addWidget(splitter)
        
        # 默认选中第一个分类
        self._select_knowledge_category("knowledge")
        
        return widget
    
    def _select_knowledge_category(self, category_key: str):
        """选择知识库分类"""
        # 更新按钮状态
        for key, btn in self.knowledge_category_buttons.items():
            btn.setChecked(key == category_key)
        
        # 获取分类数据
        category = DATA_SOURCES.get(category_key)
        if not category:
            return
        
        # 更新头部
        self.knowledge_title.setText(category["name"])
        self.knowledge_desc.setText(category["description"])
        self.knowledge_count.setText(f"{len(category['sources'])} 个信息源")
        
        # 清除现有内容
        while self.knowledge_content_layout.count():
            item = self.knowledge_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 添加信息源卡片
        sources = category["sources"]
        for i, source in enumerate(sources):
            card = SourceCard(source)
            card.clicked.connect(self._on_source_clicked)
            self.knowledge_content_layout.addWidget(card, i // 3, i % 3)
        
        # 设置列拉伸
        self.knowledge_content_layout.setColumnStretch(0, 1)
        self.knowledge_content_layout.setColumnStretch(1, 1)
        self.knowledge_content_layout.setColumnStretch(2, 1)
    
    def _create_tools_tab(self) -> QWidget:
        """创建工具箱Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)
        
        # 顶部说明
        intro = QLabel(
            "🔧 <b>投资工具箱</b><br>"
            f"<span style='color: {Colors.TEXT_SECONDARY};'>实用投资分析和管理工具，包含估值、图表、社区等。</span>"
        )
        intro.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_PRIMARY};")
        intro.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(intro)
        
        # 工具卡片
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
        """)
        
        content = QWidget()
        content_layout = QGridLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)
        
        for i, source in enumerate(DATA_SOURCES["tools"]["sources"]):
            card = SourceCard(source)
            card.clicked.connect(self._on_source_clicked)
            content_layout.addWidget(card, i // 3, i % 3)
        
        content_layout.setColumnStretch(0, 1)
        content_layout.setColumnStretch(1, 1)
        content_layout.setColumnStretch(2, 1)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return widget
    
    # ============================================================
    # 事件处理
    # ============================================================
    
    def _discover_themes(self):
        """发现投资主线"""
        if not self.theme_discovery:
            QMessageBox.warning(self, "提示", "数据源管理器未初始化，请稍后重试")
            return
        
        try:
            themes = self.theme_discovery.discover_themes()
            self._display_themes(themes)
            QMessageBox.information(self, "成功", f"发现 {len(themes)} 个投资主线")
        except Exception as e:
            logger.error(f"发现主线失败: {e}")
            QMessageBox.warning(self, "错误", f"发现主线失败: {e}")
    
    def _refresh_themes(self):
        """刷新主线"""
        if self.data_manager and self.data_manager.cache:
            themes = self.data_manager.cache.get_hot_themes(10)
            if themes:
                self._display_themes(themes)
            else:
                self._load_default_themes()
    
    def _load_default_themes(self):
        """加载默认主线"""
        if self.theme_discovery:
            themes = self.theme_discovery._get_default_themes()
            self._display_themes(themes)
    
    def _display_themes(self, themes: list):
        """显示主线卡片"""
        # 清除旧卡片
        while self.themes_layout.count():
            item = self.themes_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 添加新卡片
        for i, theme in enumerate(themes):
            card = ThemeCard(theme)
            card.clicked.connect(self._on_theme_clicked)
            self.themes_layout.addWidget(card, i // 2, i % 2)
        
        self.themes_layout.setColumnStretch(0, 1)
        self.themes_layout.setColumnStretch(1, 1)
    
    def _on_theme_clicked(self, theme: dict):
        """点击主线"""
        name = theme.get('name', '未知主线')
        logic = theme.get('investment_logic', '')
        symbols = theme.get('related_symbols', [])
        
        msg = f"<b>{name}</b><br><br>"
        msg += f"<b>投资逻辑：</b>{logic}<br><br>"
        msg += f"<b>相关股票：</b><br>"
        for s in symbols[:5]:
            msg += f"  • {s}<br>"
        
        reply = QMessageBox.question(
            self, f"投资主线: {name}",
            f"{msg}<br>是否生成该主线的策略代码？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._generate_theme_strategy(theme)
    
    def _generate_theme_strategy(self, theme: dict):
        """生成主线策略"""
        if not self.theme_discovery:
            return
        
        try:
            code = self.theme_discovery.generate_theme_strategy(theme)
            
            # 保存到文件
            from pathlib import Path
            strategies_dir = Path.home() / ".local/share/trquant/strategies/ptrade"
            strategies_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"theme_{theme['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            filepath = strategies_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code)
            
            QMessageBox.information(
                self, "成功",
                f"策略代码已生成：\n{filepath}\n\n"
                "请前往「策略开发」页面编辑和回测。"
            )
        except Exception as e:
            logger.error(f"生成策略失败: {e}")
            QMessageBox.warning(self, "错误", f"生成策略失败: {e}")
    
    def _on_source_clicked(self, source: dict):
        """点击信息源"""
        url = source.get("url", "")
        
        if url == "internal://manual":
            self.open_manual.emit()
            return
        
        if url:
            QDesktopServices.openUrl(QUrl(url))
    
    def _fetch_news(self):
        """获取资讯"""
        if not self.data_manager:
            self.news_list.setPlainText("数据源未初始化")
            return
        
        try:
            news = self.data_manager.get_news(limit=20)
            if news:
                text = ""
                for n in news:
                    title = n.get('title', '')
                    time = n.get('publish_time', '')
                    text += f"【{time}】{title}\n\n"
                self.news_list.setPlainText(text)
            else:
                self.news_list.setPlainText("暂无资讯数据")
        except Exception as e:
            logger.error(f"获取资讯失败: {e}")
            self.news_list.setPlainText(f"获取资讯失败: {e}")
    
    def _update_cache_status(self):
        """更新缓存状态"""
        try:
            if self.data_manager and self.data_manager.cache:
                status = self.data_manager.cache.get_status()
                if status.get('status') == 'connected':
                    collections = status.get('collections', {})
                    text = "✅ MongoDB已连接\n"
                    for name, count in collections.items():
                        text += f"  • {name}: {count}条记录\n"
                    self.cache_status_label.setText(text)
                else:
                    self.cache_status_label.setText("❌ MongoDB未连接")
            else:
                self.cache_status_label.setText("⚠️ 缓存管理器未初始化")
        except Exception as e:
            self.cache_status_label.setText(f"❌ 错误: {e}")
    
    def _test_data_source(self, source_name: str):
        """测试数据源连接 - 使用异步线程，保持UI响应"""
        # 如果已有测试在运行，先等待
        if hasattr(self, '_test_worker') and self._test_worker and self._test_worker.isRunning():
            QMessageBox.information(self, "请稍候", "正在测试其他数据源，请稍后重试")
            return
        
        # 显示等待状态
        self._show_testing_status(source_name)
        
        # 创建并启动工作线程
        self._test_worker = DataSourceTestWorker(source_name)
        self._test_worker.progress.connect(self._on_test_progress)
        self._test_worker.finished.connect(self._on_test_finished)
        self._test_worker.start()
    
    def _show_testing_status(self, source_name: str):
        """显示测试中状态"""
        # 可以在UI上显示一个提示
        logger.info(f"🔄 开始测试数据源: {source_name}")
    
    def _on_test_progress(self, message: str):
        """测试进度更新"""
        logger.info(message)
    
    def _on_test_finished(self, source_name: str, result: dict):
        """测试完成回调"""
        if result["success"]:
            QMessageBox.information(
                self, 
                f"✅ {source_name} 连接成功",
                result["message"]
            )
        else:
            QMessageBox.warning(
                self,
                f"❌ {source_name} 连接失败",
                result["message"]
            )
    
    # 注：数据源测试方法已移至 DataSourceTestWorker 类中
    # 采用异步线程执行，避免阻塞UI
