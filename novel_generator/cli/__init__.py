"""
SoundNovel CLI 模块

提供统一的命令行接口，支持项目初始化、大纲生成、章节扩写等功能
"""

__version__ = "0.1.0"

from novel_generator.cli.main import main

__all__ = ['main']
