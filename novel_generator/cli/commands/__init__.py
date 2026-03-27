"""
CLI 命令模块
"""

from novel_generator.cli.commands.init import run as init
from novel_generator.cli.commands.outline import run as outline
from novel_generator.cli.commands.expand import run as expand
from novel_generator.cli.commands.status import run as status
from novel_generator.cli.commands.continue_cmd import run as continue_write
from novel_generator.cli.commands.settings_cmd import run as settings
from novel_generator.cli.commands.review_cmd import run as review

__all__ = ['init', 'outline', 'expand', 'status', 'continue_write', 'settings', 'review']
