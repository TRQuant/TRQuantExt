# -*- coding: utf-8 -*-
"""
候选池数据导入导出管理器
========================

功能:
1. 从CSV/Excel导入外部股票列表
2. 导出候选池到Excel
3. 版本对比与变更追踪
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Optional, Any
from pathlib import Path
import pandas as pd
import json

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """导入结果"""
    success: bool
    total_rows: int
    imported_count: int
    skipped_count: int
    errors: List[str]
    stocks: List[Dict]
    
    def to_dict(self) -> dict:
        return {
            'success': self.success,
            'total_rows': self.total_rows,
            'imported_count': self.imported_count,
            'skipped_count': self.skipped_count,
            'errors': self.errors,
            'stocks': self.stocks
        }


@dataclass
class ExportResult:
    """导出结果"""
    success: bool
    file_path: str
    row_count: int
    error: Optional[str] = None


@dataclass
class PoolVersion:
    """候选池版本"""
    version_id: str
    created_at: str
    stock_count: int
    stocks: List[Dict]
    description: str = ""
    
    def to_dict(self) -> dict:
        return {
            'version_id': self.version_id,
            'created_at': self.created_at,
            'stock_count': self.stock_count,
            'stocks': self.stocks,
            'description': self.description
        }


@dataclass
class VersionDiff:
    """版本差异"""
    added: List[Dict]      # 新增股票
    removed: List[Dict]    # 移除股票
    unchanged: List[Dict]  # 未变化
    
    @property
    def has_changes(self) -> bool:
        return len(self.added) > 0 or len(self.removed) > 0


class PoolIOManager:
    """候选池导入导出管理器"""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir or "output/pools")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.versions_dir = self.output_dir / "versions"
        self.versions_dir.mkdir(exist_ok=True)
        
        self._versions: List[PoolVersion] = []
        self._load_versions()
    
    def import_from_file(self, file_path: str) -> ImportResult:
        """
        从文件导入股票列表
        
        Args:
            file_path: CSV或Excel文件路径
        
        Returns:
            ImportResult
        """
        logger.info(f"📥 导入文件: {file_path}")
        
        path = Path(file_path)
        if not path.exists():
            return ImportResult(
                success=False,
                total_rows=0,
                imported_count=0,
                skipped_count=0,
                errors=[f"文件不存在: {file_path}"],
                stocks=[]
            )
        
        try:
            # 读取文件
            if path.suffix.lower() in ['.csv']:
                df = pd.read_csv(path, dtype=str)
            elif path.suffix.lower() in ['.xlsx', '.xls']:
                df = pd.read_excel(path, dtype=str)
            else:
                return ImportResult(
                    success=False,
                    total_rows=0,
                    imported_count=0,
                    skipped_count=0,
                    errors=[f"不支持的文件格式: {path.suffix}"],
                    stocks=[]
                )
            
            # 解析数据
            stocks = []
            errors = []
            skipped = 0
            
            # 自动识别列名
            code_col = self._find_column(df.columns, ['代码', 'code', '股票代码', 'symbol'])
            name_col = self._find_column(df.columns, ['名称', 'name', '股票名称'])
            
            if code_col is None:
                return ImportResult(
                    success=False,
                    total_rows=len(df),
                    imported_count=0,
                    skipped_count=len(df),
                    errors=["未找到股票代码列（需要列名包含：代码/code/股票代码/symbol）"],
                    stocks=[]
                )
            
            for idx, row in df.iterrows():
                try:
                    code = str(row[code_col]).strip()
                    if not code or code == 'nan':
                        skipped += 1
                        continue
                    
                    # 标准化代码格式
                    code = self._normalize_code(code)
                    
                    stock = {
                        'code': code,
                        'name': str(row[name_col]).strip() if name_col else '',
                        'source': 'import',
                        'import_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # 提取其他列
                    for col in df.columns:
                        if col not in [code_col, name_col]:
                            val = row[col]
                            if pd.notna(val):
                                stock[col] = str(val).strip()
                    
                    stocks.append(stock)
                    
                except Exception as e:
                    errors.append(f"行 {idx + 2}: {e}")
                    skipped += 1
            
            result = ImportResult(
                success=len(stocks) > 0,
                total_rows=len(df),
                imported_count=len(stocks),
                skipped_count=skipped,
                errors=errors,
                stocks=stocks
            )
            
            logger.info(f"✅ 导入完成: {len(stocks)}/{len(df)} 只股票")
            return result
            
        except Exception as e:
            logger.error(f"导入失败: {e}")
            return ImportResult(
                success=False,
                total_rows=0,
                imported_count=0,
                skipped_count=0,
                errors=[str(e)],
                stocks=[]
            )
    
    def export_to_excel(self, stocks: List[Dict], filename: str = None) -> ExportResult:
        """
        导出候选池到Excel
        
        Args:
            stocks: 股票列表
            filename: 文件名（不含路径）
        
        Returns:
            ExportResult
        """
        if not stocks:
            return ExportResult(
                success=False,
                file_path="",
                row_count=0,
                error="没有数据可导出"
            )
        
        if filename is None:
            filename = f"候选池_{date.today().strftime('%Y%m%d')}.xlsx"
        
        file_path = self.output_dir / filename
        
        try:
            df = pd.DataFrame(stocks)
            
            # 重排列顺序
            preferred_order = ['code', 'name', 'price', 'change_pct', 'score', 'industry', 'source']
            cols = [c for c in preferred_order if c in df.columns]
            cols += [c for c in df.columns if c not in cols]
            df = df[cols]
            
            # 重命名列
            rename_map = {
                'code': '代码',
                'name': '名称',
                'price': '价格',
                'change_pct': '涨跌幅%',
                'score': '评分',
                'industry': '行业',
                'source': '来源',
                'scan_type': '扫描类型',
                'turnover': '成交额(亿)',
                'volume_ratio': '量比'
            }
            df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
            
            # 导出
            df.to_excel(file_path, index=False, engine='openpyxl')
            
            logger.info(f"✅ 导出成功: {file_path}")
            return ExportResult(
                success=True,
                file_path=str(file_path),
                row_count=len(stocks)
            )
            
        except Exception as e:
            logger.error(f"导出失败: {e}")
            return ExportResult(
                success=False,
                file_path="",
                row_count=0,
                error=str(e)
            )
    
    def save_version(self, stocks: List[Dict], description: str = "") -> PoolVersion:
        """
        保存候选池版本
        
        Args:
            stocks: 股票列表
            description: 版本描述
        
        Returns:
            PoolVersion
        """
        version_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        version = PoolVersion(
            version_id=version_id,
            created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            stock_count=len(stocks),
            stocks=stocks,
            description=description
        )
        
        # 保存到文件
        version_file = self.versions_dir / f"v_{version_id}.json"
        with open(version_file, 'w', encoding='utf-8') as f:
            json.dump(version.to_dict(), f, ensure_ascii=False, indent=2)
        
        self._versions.append(version)
        
        logger.info(f"✅ 保存版本 {version_id}: {len(stocks)} 只股票")
        return version
    
    def get_versions(self) -> List[PoolVersion]:
        """获取所有版本列表"""
        return sorted(self._versions, key=lambda v: v.created_at, reverse=True)
    
    def get_version(self, version_id: str) -> Optional[PoolVersion]:
        """获取指定版本"""
        for v in self._versions:
            if v.version_id == version_id:
                return v
        return None
    
    def compare_versions(self, version_id_1: str, version_id_2: str) -> Optional[VersionDiff]:
        """
        对比两个版本
        
        Args:
            version_id_1: 旧版本ID
            version_id_2: 新版本ID
        
        Returns:
            VersionDiff
        """
        v1 = self.get_version(version_id_1)
        v2 = self.get_version(version_id_2)
        
        if not v1 or not v2:
            return None
        
        codes_1 = {s['code'] for s in v1.stocks}
        codes_2 = {s['code'] for s in v2.stocks}
        
        added_codes = codes_2 - codes_1
        removed_codes = codes_1 - codes_2
        unchanged_codes = codes_1 & codes_2
        
        added = [s for s in v2.stocks if s['code'] in added_codes]
        removed = [s for s in v1.stocks if s['code'] in removed_codes]
        unchanged = [s for s in v2.stocks if s['code'] in unchanged_codes]
        
        return VersionDiff(
            added=added,
            removed=removed,
            unchanged=unchanged
        )
    
    def _load_versions(self):
        """加载所有版本"""
        self._versions = []
        
        for version_file in self.versions_dir.glob("v_*.json"):
            try:
                with open(version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    version = PoolVersion(
                        version_id=data['version_id'],
                        created_at=data['created_at'],
                        stock_count=data['stock_count'],
                        stocks=data['stocks'],
                        description=data.get('description', '')
                    )
                    self._versions.append(version)
            except Exception as e:
                logger.warning(f"加载版本失败 {version_file}: {e}")
    
    def _find_column(self, columns, candidates: List[str]) -> Optional[str]:
        """查找列名"""
        cols_lower = {str(c).lower(): c for c in columns}
        for candidate in candidates:
            if candidate.lower() in cols_lower:
                return cols_lower[candidate.lower()]
        return None
    
    def _normalize_code(self, code: str) -> str:
        """标准化股票代码"""
        code = code.replace('.SZ', '').replace('.SH', '').replace('.XSHE', '').replace('.XSHG', '')
        code = code.strip()
        
        # 确保6位
        if len(code) < 6:
            code = code.zfill(6)
        
        # 添加后缀
        if code.startswith(('6', '9')):
            return f"{code}.XSHG"
        else:
            return f"{code}.XSHE"


# 单例
_manager = None

def get_pool_io_manager() -> PoolIOManager:
    global _manager
    if _manager is None:
        _manager = PoolIOManager()
    return _manager

