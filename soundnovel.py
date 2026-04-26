#!/usr/bin/env python3
"""
SoundNovel - AI辅助小说创作工具

统一入口文件，支持 CLI 模式：

使用方式:
    # CLI 模式
    python soundnovel.py cli init              # 初始化项目
    python soundnovel.py cli outline           # 生成章节大纲
    python soundnovel.py cli expand --chapter 1    # 扩写章节
    python soundnovel.py cli agent             # 启动 Agent 对话模式

    # 查看帮助
    python soundnovel.py --help
    python soundnovel.py cli --help

或者使用模块方式直接运行:
    python -m novel_generator.cli init
"""

import argparse
import sys
from pathlib import Path


def run_cli(args_list=None):
    """
    运行 CLI 模式

    Args:
        args_list: 命令行参数列表，为 None 时直接使用 sys.argv
    """
    from novel_generator.cli.main import main as cli_main

    if args_list is not None:
        # 保存原始参数
        old_argv = sys.argv.copy()
        # 替换为新的参数（去掉 'cli' 子命令）
        sys.argv = [old_argv[0]] + args_list
        try:
            cli_main()
        finally:
            sys.argv = old_argv
    else:
        cli_main()


def create_parser() -> argparse.ArgumentParser:
    """创建参数解析器"""
    parser = argparse.ArgumentParser(
        prog='soundnovel',
        description='SoundNovel - AI辅助小说创作工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # CLI 模式 - 命令行操作
  %(prog)s cli init                    # 初始化项目
  %(prog)s cli outline                 # 生成章节大纲
  %(prog)s cli expand --chapter 1      # 扩写第1章
  %(prog)s cli agent                   # 启动 Agent 对话模式
  %(prog)s cli --help                  # 查看 CLI 帮助

更多信息:
  查看 README.md 获取完整文档
        """
    )
    
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s 0.1.0'
    )
    
    # 子命令
    subparsers = parser.add_subparsers(
        dest='mode',
        title='运行模式',
        help='选择运行模式'
    )

    # CLI 子命令
    cli_parser = subparsers.add_parser(
        'cli',
        help='命令行模式 (生成大纲、扩写章节等)',
        description='命令行模式 - 使用命令行进行小说创作',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
CLI 命令:
  init          初始化小说项目
  outline       生成章节大纲
  expand        扩写章节内容
  agent         Agent 对话模式

使用 %(prog)s cli --help 查看所有命令
        """
    )

    # 添加一个特殊的 --cli-help 参数来处理 CLI 帮助
    cli_parser.add_argument(
        'cli_args',
        nargs='*',
        help='CLI 命令和参数 (传递给 novel_generator.cli)'
    )

    return parser


def main():
    """主入口函数"""
    parser = create_parser()

    # 如果没有提供任何参数，显示帮助
    if len(sys.argv) < 2:
        parser.print_help()
        print("\n💡 提示: 使用 'soundnovel.py cli' 进入命令行模式")
        sys.exit(0)

    # 解析已知参数，保留未知的给子命令
    args, remaining = parser.parse_known_args()

    if args.mode == 'cli':
        # CLI 模式
        if not remaining and not args.cli_args:
            # 没有额外参数，显示 CLI 帮助
            remaining.append('--help')

        # 合并参数
        all_args = args.cli_args + remaining if args.cli_args else remaining
        run_cli(all_args)

    else:
        # 未知模式
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
