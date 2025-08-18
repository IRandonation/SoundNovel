"""
文件处理工具
负责文件读写、路径处理等操作
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import shutil


class FileHandler:
    """文件处理器"""
    
    def __init__(self, base_path: str = "."):
        """
        初始化文件处理器
        
        Args:
            base_path: 基础路径
        """
        self.base_path = Path(base_path).resolve()
        
    def read_yaml(self, file_path: str) -> Dict[str, Any]:
        """
        读取YAML文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict[str, Any]: 文件内容
        """
        try:
            full_path = self.base_path / file_path
            with open(full_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise Exception(f"读取YAML文件失败 {file_path}: {e}")
    
    def write_yaml(self, file_path: str, data: Dict[str, Any], 
                  backup: bool = True) -> str:
        """
        写入YAML文件
        
        Args:
            file_path: 文件路径
            data: 数据
            backup: 是否备份
            
        Returns:
            str: 实际保存路径
        """
        try:
            full_path = self.base_path / file_path
            
            # 备份现有文件
            if backup and full_path.exists():
                backup_path = self._backup_file(full_path)
                print(f"备份文件: {backup_path}")
            
            # 创建目录
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(full_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            
            return str(full_path)
            
        except Exception as e:
            raise Exception(f"写入YAML文件失败 {file_path}: {e}")
    
    def read_json(self, file_path: str) -> Dict[str, Any]:
        """
        读取JSON文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict[str, Any]: 文件内容
        """
        try:
            full_path = self.base_path / file_path
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"读取JSON文件失败 {file_path}: {e}")
    
    def write_json(self, file_path: str, data: Dict[str, Any], 
                  backup: bool = True) -> str:
        """
        写入JSON文件
        
        Args:
            file_path: 文件路径
            data: 数据
            backup: 是否备份
            
        Returns:
            str: 实际保存路径
        """
        try:
            full_path = self.base_path / file_path
            
            # 备份现有文件
            if backup and full_path.exists():
                backup_path = self._backup_file(full_path)
                print(f"备份文件: {backup_path}")
            
            # 创建目录
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return str(full_path)
            
        except Exception as e:
            raise Exception(f"写入JSON文件失败 {file_path}: {e}")
    
    def read_text(self, file_path: str) -> str:
        """
        读取文本文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 文件内容
        """
        try:
            full_path = self.base_path / file_path
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise Exception(f"读取文本文件失败 {file_path}: {e}")
    
    def write_text(self, file_path: str, content: str, 
                  backup: bool = True) -> str:
        """
        写入文本文件
        
        Args:
            file_path: 文件路径
            content: 内容
            backup: 是否备份
            
        Returns:
            str: 实际保存路径
        """
        try:
            full_path = self.base_path / file_path
            
            # 备份现有文件
            if backup and full_path.exists():
                backup_path = self._backup_file(full_path)
                print(f"备份文件: {backup_path}")
            
            # 创建目录
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return str(full_path)
            
        except Exception as e:
            raise Exception(f"写入文本文件失败 {file_path}: {e}")
    
    def file_exists(self, file_path: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否存在
        """
        full_path = self.base_path / file_path
        return full_path.exists()
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        获取文件信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict[str, Any]: 文件信息
        """
        try:
            full_path = self.base_path / file_path
            if not full_path.exists():
                return {}
            
            stat = full_path.stat()
            return {
                'name': full_path.name,
                'path': str(full_path),
                'size': stat.st_size,
                'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'created_time': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'is_file': full_path.is_file(),
                'is_dir': full_path.is_dir()
            }
        except Exception as e:
            raise Exception(f"获取文件信息失败 {file_path}: {e}")
    
    def list_files(self, dir_path: str, pattern: str = "*") -> List[str]:
        """
        列出目录中的文件
        
        Args:
            dir_path: 目录路径
            pattern: 文件匹配模式
            
        Returns:
            List[str]: 文件路径列表
        """
        try:
            full_dir = self.base_path / dir_path
            if not full_dir.exists():
                return []
            
            files = []
            for file_path in full_dir.glob(pattern):
                if file_path.is_file():
                    files.append(str(file_path.relative_to(self.base_path)))
            
            return sorted(files)
            
        except Exception as e:
            raise Exception(f"列出文件失败 {dir_path}: {e}")
    
    def create_directory(self, dir_path: str) -> str:
        """
        创建目录
        
        Args:
            dir_path: 目录路径
            
        Returns:
            str: 实际创建的路径
        """
        try:
            full_path = self.base_path / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            return str(full_path)
            
        except Exception as e:
            raise Exception(f"创建目录失败 {dir_path}: {e}")
    
    def copy_file(self, src_path: str, dst_path: str, 
                 backup: bool = True) -> str:
        """
        复制文件
        
        Args:
            src_path: 源文件路径
            dst_path: 目标文件路径
            backup: 是否备份目标文件
            
        Returns:
            str: 实际复制到的路径
        """
        try:
            src_full = self.base_path / src_path
            dst_full = self.base_path / dst_path
            
            if not src_full.exists():
                raise FileNotFoundError(f"源文件不存在: {src_full}")
            
            # 备份目标文件
            if backup and dst_full.exists():
                backup_path = self._backup_file(dst_full)
                print(f"备份文件: {backup_path}")
            
            # 创建目标目录
            dst_full.parent.mkdir(parents=True, exist_ok=True)
            
            # 复制文件
            shutil.copy2(src_full, dst_full)
            
            return str(dst_full)
            
        except Exception as e:
            raise Exception(f"复制文件失败 {src_path} -> {dst_path}: {e}")
    
    def move_file(self, src_path: str, dst_path: str, 
                 backup: bool = True) -> str:
        """
        移动文件
        
        Args:
            src_path: 源文件路径
            dst_path: 目标文件路径
            backup: 是否备份目标文件
            
        Returns:
            str: 实际移动到的路径
        """
        try:
            src_full = self.base_path / src_path
            dst_full = self.base_path / dst_path
            
            if not src_full.exists():
                raise FileNotFoundError(f"源文件不存在: {src_full}")
            
            # 备份目标文件
            if backup and dst_full.exists():
                backup_path = self._backup_file(dst_full)
                print(f"备份文件: {backup_path}")
            
            # 创建目标目录
            dst_full.parent.mkdir(parents=True, exist_ok=True)
            
            # 移动文件
            shutil.move(str(src_full), str(dst_full))
            
            return str(dst_full)
            
        except Exception as e:
            raise Exception(f"移动文件失败 {src_path} -> {dst_path}: {e}")
    
    def delete_file(self, file_path: str) -> bool:
        """
        删除文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否成功删除
        """
        try:
            full_path = self.base_path / file_path
            if full_path.exists():
                full_path.unlink()
                return True
            return False
            
        except Exception as e:
            raise Exception(f"删除文件失败 {file_path}: {e}")
    
    def _backup_file(self, file_path: Path) -> str:
        """
        备份文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 备份文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = file_path.parent / "backups" / backup_name
        
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 复制文件
        shutil.copy2(file_path, backup_path)
        
        return str(backup_path)
    
    def get_file_size(self, file_path: str) -> int:
        """
        获取文件大小
        
        Args:
            file_path: 文件路径
            
        Returns:
            int: 文件大小（字节）
        """
        try:
            full_path = self.base_path / file_path
            if full_path.exists():
                return full_path.stat().st_size
            return 0
            
        except Exception as e:
            raise Exception(f"获取文件大小失败 {file_path}: {e}")
    
    def get_file_modified_time(self, file_path: str) -> str:
        """
        获取文件修改时间
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 修改时间（ISO格式）
        """
        try:
            full_path = self.base_path / file_path
            if full_path.exists():
                stat = full_path.stat()
                return datetime.fromtimestamp(stat.st_mtime).isoformat()
            return ""
            
        except Exception as e:
            raise Exception(f"获取文件修改时间失败 {file_path}: {e}")


class PathManager:
    """路径管理器"""
    
    def __init__(self, base_path: str = "."):
        """
        初始化路径管理器
        
        Args:
            base_path: 基础路径
        """
        self.base_path = Path(base_path).resolve()
        self.file_handler = FileHandler(str(self.base_path))
    
    def get_absolute_path(self, relative_path: str) -> str:
        """
        获取绝对路径
        
        Args:
            relative_path: 相对路径
            
        Returns:
            str: 绝对路径
        """
        return str(self.base_path / relative_path)
    
    def get_relative_path(self, absolute_path: str) -> str:
        """
        获取相对路径
        
        Args:
            absolute_path: 绝对路径
            
        Returns:
            str: 相对路径
        """
        try:
            abs_path = Path(absolute_path).resolve()
            return str(abs_path.relative_to(self.base_path))
        except ValueError:
            return absolute_path
    
    def join_path(self, *args) -> str:
        """
        连接路径
        
        Args:
            *args: 路径片段
            
        Returns:
            str: 连接后的路径
        """
        return str(self.base_path.joinpath(*args))
    
    def ensure_directory(self, dir_path: str) -> str:
        """
        确保目录存在
        
        Args:
            dir_path: 目录路径
            
        Returns:
            str: 实际目录路径
        """
        return self.file_handler.create_directory(dir_path)
    
    def get_project_structure(self, max_depth: int = 3) -> Dict[str, Any]:
        """
        获取项目结构
        
        Args:
            max_depth: 最大深度
            
        Returns:
            Dict[str, Any]: 项目结构
        """
        def _scan_directory(path: Path, depth: int) -> Dict[str, Any]:
            if depth > max_depth:
                return {}
            
            structure = {
                'name': path.name,
                'path': str(path.relative_to(self.base_path)),
                'type': 'directory' if path.is_dir() else 'file',
                'children': []
            }
            
            if path.is_dir():
                try:
                    for item in sorted(path.iterdir()):
                        if not item.name.startswith('.'):
                            structure['children'].append(_scan_directory(item, depth + 1))
                except PermissionError:
                    pass
            
            return structure
        
        return _scan_directory(self.base_path, 0)
    
    def find_files(self, pattern: str = "*", 
                  dir_path: str = None, 
                  recursive: bool = True) -> List[str]:
        """
        查找文件
        
        Args:
            pattern: 文件匹配模式
            dir_path: 搜索目录
            recursive: 是否递归搜索
            
        Returns:
            List[str]: 匹配的文件路径列表
        """
        search_dir = self.base_path / (dir_path or "")
        
        if not search_dir.exists():
            return []
        
        if recursive:
            files = list(search_dir.rglob(pattern))
        else:
            files = list(search_dir.glob(pattern))
        
        return [str(f.relative_to(self.base_path)) for f in files if f.is_file()]
    
    def validate_paths(self, paths: List[str]) -> Dict[str, bool]:
        """
        验证路径是否存在
        
        Args:
            paths: 路径列表
            
        Returns:
            Dict[str, bool]: 路径存在状态
        """
        result = {}
        for path in paths:
            full_path = self.base_path / path
            result[path] = full_path.exists()
        
        return result