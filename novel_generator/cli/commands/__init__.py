"""
CLI 命令模块
"""

from novel_generator.cli.commands.init import run as init
from novel_generator.cli.commands.outline import run as outline
from novel_generator.cli.commands.expand import run as expand

__all__ = ['init', 'outline', 'expand']
