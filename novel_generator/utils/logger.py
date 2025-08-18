"""
日志管理器
负责系统日志和API调用日志的记录
"""

import logging
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from logging.handlers import RotatingFileHandler


class NovelLogger:
    """小说创作日志管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化日志管理器
        
        Args:
            config: 配置信息
        """
        self.config = config
        self.log_dir = Path(config.get('paths', {}).get('log_dir', '06_log'))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 确保日志子目录存在
        (self.log_dir / "system_logs").mkdir(parents=True, exist_ok=True)
        (self.log_dir / "ai_api_logs").mkdir(parents=True, exist_ok=True)
        
        # 系统日志配置
        self.system_log_file = self.log_dir / "system_logs" / "novel_generator.log"
        self.api_log_file = self.log_dir / "ai_api_logs" / "api_calls.log"
        
        # 创建日志记录器
        self.system_logger = self._setup_system_logger()
        self.api_logger = self._setup_api_logger()
        
        # 操作历史记录
        self.operation_history = []
        
    def _setup_system_logger(self) -> logging.Logger:
        """设置系统日志记录器"""
        logger = logging.getLogger('novel_generator.system')
        logger.setLevel(logging.INFO)
        
        # 避免重复添加处理器
        if logger.handlers:
            return logger
        
        # 创建文件处理器
        file_handler = RotatingFileHandler(
            self.system_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        
        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _setup_api_logger(self) -> logging.Logger:
        """设置API调用日志记录器"""
        logger = logging.getLogger('novel_generator.api')
        logger.setLevel(logging.INFO)
        
        # 避免重复添加处理器
        if logger.handlers:
            return logger
        
        # 创建文件处理器
        file_handler = RotatingFileHandler(
            self.api_log_file,
            maxBytes=50*1024*1024,  # 50MB
            backupCount=10,
            encoding='utf-8'
        )
        
        # 创建格式化器
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        
        file_handler.setFormatter(formatter)
        
        # 添加处理器
        logger.addHandler(file_handler)
        
        return logger
    
    def log_operation(self, operation: str, details: Dict[str, Any] = None):
        """
        记录操作日志
        
        Args:
            operation: 操作名称
            details: 操作详情
        """
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'operation': operation,
                'details': details or {}
            }
            
            # 记录到系统日志
            self.system_logger.info(f"操作: {operation} - 详情: {json.dumps(details, ensure_ascii=False)}")
            
            # 添加到操作历史
            self.operation_history.append(log_entry)
            
            # 限制历史记录数量
            if len(self.operation_history) > 1000:
                self.operation_history = self.operation_history[-500:]
                
        except Exception as e:
            self.system_logger.error(f"记录操作日志失败: {e}")
    
    def log_api_call(self, model: str, prompt: str, response: str, 
                    tokens_used: int = None, duration: float = None,
                    error: str = None):
        """
        记录API调用日志
        
        Args:
            model: 使用的模型
            prompt: 输入提示词
            response: API响应
            tokens_used: 消耗的token数
            duration: 调用时长（秒）
            error: 错误信息
        """
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'model': model,
                'prompt_length': len(prompt),
                'response_length': len(response),
                'tokens_used': tokens_used,
                'duration': duration,
                'error': error,
                'success': error is None
            }
            
            # 记录到API日志
            self.api_logger.info(json.dumps(log_entry, ensure_ascii=False))
            
            # 记录到系统日志
            if error:
                self.system_logger.error(f"API调用失败 - 模型: {model}, 错误: {error}")
            else:
                self.system_logger.info(f"API调用成功 - 模型: {model}, 耗时: {duration:.2f}秒")
                
        except Exception as e:
            self.system_logger.error(f"记录API调用日志失败: {e}")
    
    def log_error(self, error: Exception, context: str = ""):
        """
        记录错误日志
        
        Args:
            error: 错误对象
            context: 错误上下文
        """
        try:
            error_info = {
                'timestamp': datetime.now().isoformat(),
                'error_type': type(error).__name__,
                'error_message': str(error),
                'context': context
            }
            
            self.system_logger.error(f"错误: {error_info['error_type']} - {error_info['error_message']} - 上下文: {context}")
            
        except Exception as e:
            self.system_logger.error(f"记录错误日志失败: {e}")
    
    def log_chapter_generation(self, chapter_num: int, status: str, 
                              word_count: int = None, duration: float = None):
        """
        记录章节生成日志
        
        Args:
            chapter_num: 章节号
            status: 状态（成功/失败）
            word_count: 字数
            duration: 耗时
        """
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'chapter_num': chapter_num,
                'status': status,
                'word_count': word_count,
                'duration': duration
            }
            
            message = f"章节{chapter_num}生成{status}"
            if word_count:
                message += f", 字数: {word_count}"
            if duration:
                message += f", 耗时: {duration:.2f}秒"
            
            if status == "成功":
                self.system_logger.info(message)
            else:
                self.system_logger.error(message)
                
        except Exception as e:
            self.system_logger.error(f"记录章节生成日志失败: {e}")
    
    def get_operation_history(self, operation: str = None, 
                            start_time: str = None, 
                            end_time: str = None) -> List[Dict[str, Any]]:
        """
        获取操作历史
        
        Args:
            operation: 操作名称过滤
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            List[Dict[str, Any]]: 操作历史记录
        """
        try:
            filtered_history = self.operation_history
            
            # 按操作名称过滤
            if operation:
                filtered_history = [h for h in filtered_history if h['operation'] == operation]
            
            # 按时间范围过滤
            if start_time:
                filtered_history = [h for h in filtered_history if h['timestamp'] >= start_time]
            
            if end_time:
                filtered_history = [h for h in filtered_history if h['timestamp'] <= end_time]
            
            return filtered_history
            
        except Exception as e:
            self.system_logger.error(f"获取操作历史失败: {e}")
            return []
    
    def get_api_statistics(self, start_time: str = None, 
                         end_time: str = None) -> Dict[str, Any]:
        """
        获取API调用统计信息
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            # 读取API日志文件
            api_logs = []
            if self.api_log_file.exists():
                with open(self.api_log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            log_entry = json.loads(line.strip())
                            api_logs.append(log_entry)
                        except json.JSONDecodeError:
                            continue
            
            # 按时间范围过滤
            if start_time:
                api_logs = [log for log in api_logs if log.get('timestamp', '') >= start_time]
            
            if end_time:
                api_logs = [log for log in api_logs if log.get('timestamp', '') <= end_time]
            
            # 计算统计信息
            total_calls = len(api_logs)
            successful_calls = len([log for log in api_logs if log.get('success', False)])
            failed_calls = total_calls - successful_calls
            
            # 按模型统计
            model_stats = {}
            for log in api_logs:
                model = log.get('model', 'unknown')
                if model not in model_stats:
                    model_stats[model] = {
                        'calls': 0,
                        'success': 0,
                        'failed': 0,
                        'total_tokens': 0,
                        'total_duration': 0
                    }
                
                model_stats[model]['calls'] += 1
                if log.get('success', False):
                    model_stats[model]['success'] += 1
                else:
                    model_stats[model]['failed'] += 1
                
                if log.get('tokens_used'):
                    model_stats[model]['total_tokens'] += log['tokens_used']
                
                if log.get('duration'):
                    model_stats[model]['total_duration'] += log['duration']
            
            # 计算总体统计
            total_tokens = sum(log.get('tokens_used', 0) for log in api_logs)
            total_duration = sum(log.get('duration', 0) for log in api_logs)
            avg_duration = total_duration / total_calls if total_calls > 0 else 0
            
            return {
                'total_calls': total_calls,
                'successful_calls': successful_calls,
                'failed_calls': failed_calls,
                'success_rate': successful_calls / total_calls if total_calls > 0 else 0,
                'total_tokens': total_tokens,
                'total_duration': total_duration,
                'avg_duration': avg_duration,
                'model_statistics': model_stats
            }
            
        except Exception as e:
            self.system_logger.error(f"获取API统计信息失败: {e}")
            return {}
    
    def clear_old_logs(self, days: int = 30):
        """
        清理旧的日志文件
        
        Args:
            days: 保留天数
        """
        try:
            cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
            
            # 清理系统日志
            if self.system_log_file.exists():
                if self.system_log_file.stat().st_mtime < cutoff_time:
                    self.system_log_file.unlink()
                    self.system_logger.info(f"清理旧系统日志: {self.system_log_file}")
            
            # 清理API日志
            if self.api_log_file.exists():
                if self.api_log_file.stat().st_mtime < cutoff_time:
                    self.api_log_file.unlink()
                    self.system_logger.info(f"清理旧API日志: {self.api_log_file}")
            
            # 清理操作历史
            cutoff_datetime = datetime.fromtimestamp(cutoff_time).isoformat()
            self.operation_history = [
                h for h in self.operation_history 
                if h['timestamp'] >= cutoff_datetime
            ]
            
        except Exception as e:
            self.system_logger.error(f"清理旧日志失败: {e}")
    
    def export_logs(self, output_file: str, log_type: str = "all"):
        """
        导出日志
        
        Args:
            output_file: 输出文件路径
            log_type: 日志类型（system/api/all）
        """
        try:
            export_data = {
                'export_time': datetime.now().isoformat(),
                'system_logs': [],
                'api_logs': [],
                'operation_history': self.operation_history
            }
            
            # 导出系统日志
            if log_type in ['system', 'all']:
                if self.system_log_file.exists():
                    with open(self.system_log_file, 'r', encoding='utf-8') as f:
                        export_data['system_logs'] = f.readlines()
            
            # 导出API日志
            if log_type in ['api', 'all']:
                if self.api_log_file.exists():
                    with open(self.api_log_file, 'r', encoding='utf-8') as f:
                        export_data['api_logs'] = f.readlines()
            
            # 保存到文件
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.system_logger.info(f"日志导出成功: {output_file}")
            
        except Exception as e:
            self.system_logger.error(f"导出日志失败: {e}")


class BackupManager:
    """备份管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化备份管理器
        
        Args:
            config: 配置信息
        """
        self.config = config
        self.backup_dir = Path(config.get('paths', {}).get('log_dir', '06_log')) / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 备份配置
        self.max_backups = 10
        self.backup_enabled = config.get('system', {}).get('backup_enabled', True)
        
    def backup_project(self, project_root: str, backup_name: str = None) -> str:
        """
        备份整个项目
        
        Args:
            project_root: 项目根目录
            backup_name: 备份名称
            
        Returns:
            str: 备份文件路径
        """
        try:
            if not self.backup_enabled:
                return ""
            
            project_path = Path(project_root)
            
            # 生成备份名称
            if not backup_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"project_backup_{timestamp}"
            
            backup_file = self.backup_dir / f"{backup_name}.zip"
            
            # 创建备份
            import zipfile
            with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in project_path.rglob('*'):
                    if file_path.is_file() and not file_path.name.startswith('.'):
                        arcname = file_path.relative_to(project_path)
                        zipf.write(file_path, arcname)
            
            # 清理旧备份
            self._cleanup_old_backups()
            
            return str(backup_file)
            
        except Exception as e:
            raise Exception(f"项目备份失败: {e}")
    
    def backup_file(self, file_path: str, backup_name: str = None) -> str:
        """
        备份单个文件
        
        Args:
            file_path: 文件路径
            backup_name: 备份名称
            
        Returns:
            str: 备份文件路径
        """
        try:
            if not self.backup_enabled:
                return ""
            
            file_path_obj = Path(file_path)
            
            # 生成备份名称
            if not backup_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"{file_path_obj.stem}_{timestamp}"
            
            backup_file = self.backup_dir / f"{backup_name}{file_path_obj.suffix}"
            
            # 复制文件
            import shutil
            shutil.copy2(file_path_obj, backup_file)
            
            # 清理旧备份
            self._cleanup_old_backups()
            
            return str(backup_file)
            
        except Exception as e:
            raise Exception(f"文件备份失败: {e}")
    
    def _cleanup_old_backups(self):
        """清理旧备份"""
        try:
            # 获取所有备份文件
            backup_files = list(self.backup_dir.glob("*"))
            
            # 按修改时间排序
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # 删除旧备份
            for backup_file in backup_files[self.max_backups:]:
                backup_file.unlink()
                
        except Exception as e:
            # 忽略清理错误
            pass
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        列出所有备份
        
        Returns:
            List[Dict[str, Any]]: 备份列表
        """
        try:
            backups = []
            
            for backup_file in self.backup_dir.glob("*"):
                if backup_file.is_file():
                    stat = backup_file.stat()
                    backups.append({
                        'name': backup_file.name,
                        'path': str(backup_file),
                        'size': stat.st_size,
                        'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
            
            # 按修改时间排序
            backups.sort(key=lambda x: x['modified_time'], reverse=True)
            
            return backups
            
        except Exception as e:
            return []
    
    def restore_backup(self, backup_name: str, restore_path: str) -> bool:
        """
        恢复备份
        
        Args:
            backup_name: 备份名称
            restore_path: 恢复路径
            
        Returns:
            bool: 是否成功
        """
        try:
            backup_file = self.backup_dir / backup_name
            
            if not backup_file.exists():
                raise FileNotFoundError(f"备份文件不存在: {backup_file}")
            
            # 创建恢复目录
            restore_path_obj = Path(restore_path)
            restore_path_obj.mkdir(parents=True, exist_ok=True)
            
            # 解压备份
            import zipfile
            with zipfile.ZipFile(backup_file, 'r') as zipf:
                zipf.extractall(restore_path_obj)
            
            return True
            
        except Exception as e:
            raise Exception(f"恢复备份失败: {e}")