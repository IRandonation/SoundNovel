"""
Agent 命令 - 启动对话式 REPL 模式
"""

import argparse
import sys
from pathlib import Path

from novel_generator.cli.utils import print_error


def run(args: argparse.Namespace) -> int:
    """运行 Agent REPL 模式"""
    try:
        from novel_generator.agent.cli_repl import run_agent_repl

        project_root = getattr(args, 'project_root', '.')
        return run_agent_repl(project_root)

    except ImportError as e:
        print_error(f"无法加载 Agent 模块: {e}")
        return 1
    except Exception as e:
        print_error(f"Agent 模式启动失败: {e}")
        return 1


def add_parser(subparsers):
    """添加 agent 子命令参数"""
    agent_parser = subparsers.add_parser(
        'agent',
        help='启动 Agent 对话模式',
        description='以对话方式与 SoundNovel 交互，使用自然语言指令'
    )
    agent_parser.add_argument(
        '--project-root',
        type=str,
        default='.',
        help='项目根目录路径（默认: 当前目录）'
    )
    agent_parser.set_defaults(func=run)
