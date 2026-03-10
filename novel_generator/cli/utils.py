"""
CLI 工具函数

提供命令行特定的辅助功能
"""

import logging
import sys
from pathlib import Path


def setup_cli_logging(log_file: str = "06_log/cli.log") -> logging.Logger:
    """
    为CLI命令设置日志
    
    Args:
        log_file: 日志文件路径
        
    Returns:
        logging.Logger: 配置好的logger
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 清除现有处理器
    logger.handlers.clear()
    
    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 项目根目录
    try:
        project_root = Path(__file__).parent.parent.parent
        log_path = project_root / log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 文件处理器
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # 如果无法创建日志文件，只使用控制台
        print(f"警告: 无法创建日志文件 {log_file}: {e}", file=sys.stderr)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


def get_executable_name() -> str:
    """
    获取可执行文件名（用于帮助信息）
    
    Returns:
        str: 可执行文件名
    """
    return "soundnovel"


def print_success(message: str) -> None:
    """打印成功消息"""
    print(f"✅ {message}")


def print_error(message: str) -> None:
    """打印错误消息"""
    print(f"❌ {message}", file=sys.stderr)


def print_warning(message: str) -> None:
    """打印警告消息"""
    print(f"⚠️  {message}")


def print_info(message: str) -> None:
    """打印信息消息"""
    print(f"ℹ️  {message}")


def confirm_action(prompt: str, default: bool = False) -> bool:
    """
    请求用户确认
    
    Args:
        prompt: 提示文本
        default: 默认值
        
    Returns:
        bool: 用户是否确认
    """
    suffix = " [Y/n]" if default else " [y/N]"
    response = input(f"{prompt}{suffix}: ").strip().lower()
    
    if not response:
        return default
    
    return response in ('y', 'yes')
