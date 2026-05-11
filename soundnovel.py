#!/usr/bin/env python3
"""
SoundNovel - AI辅助小说创作工具

统一入口文件，支持 CLI、API 管理和小说项目管理模式：

使用方式:
    # CLI 模式 - 小说创作命令
    python soundnovel.py cli outline           # 生成章节大纲
    python soundnovel.py cli expand --chapter 1    # 扩写章节

    # API 管理
    python soundnovel.py api list              # 列出所有API配置
    python soundnovel.py api create            # 创建新API配置
    python soundnovel.py api use <name>        # 切换默认API

    # 小说项目管理
    python soundnovel.py novel list            # 列出所有小说项目
    python soundnovel.py novel create          # 创建新小说项目
    python soundnovel.py novel switch <name>   # 切换当前小说

    # 查看帮助
    python soundnovel.py --help
    python soundnovel.py cli --help
    python soundnovel.py api --help
    python soundnovel.py novel --help

或者使用模块方式直接运行:
    python -m novel_generator.cli
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


def run_api(args_list=None):
    """
    运行 API 管理模式

    Args:
        args_list: 命令行参数列表，为 None 时直接使用 sys.argv
    """
    from novel_generator.cli.commands.api_commands import main as api_main

    if args_list is not None:
        old_argv = sys.argv.copy()
        sys.argv = [old_argv[0]] + args_list
        try:
            api_main()
        finally:
            sys.argv = old_argv
    else:
        api_main()


def run_novel(args_list=None):
    """
    运行小说项目管理模式

    Args:
        args_list: 命令行参数列表，为 None 时直接使用 sys.argv
    """
    from novel_generator.cli.commands.novel_commands import main as novel_main

    if args_list is not None:
        old_argv = sys.argv.copy()
        sys.argv = [old_argv[0]] + args_list
        try:
            novel_main()
        finally:
            sys.argv = old_argv
    else:
        novel_main()


def create_parser() -> argparse.ArgumentParser:
    """创建参数解析器"""
    parser = argparse.ArgumentParser(
        prog='soundnovel',
        description='SoundNovel - AI辅助小说创作工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # CLI 模式 - 命令行操作
  %(prog)s cli outline                 # 生成章节大纲
  %(prog)s cli expand --chapter 1      # 扩写第1章

  # API 管理
  %(prog)s api list                    # 列出所有API配置
  %(prog)s api create                  # 创建新API配置
  %(prog)s api use <name>              # 切换默认API

  # 小说项目管理
  %(prog)s novel list                  # 列出所有小说项目
  %(prog)s novel create              # 创建新小说项目
  %(prog)s novel switch <name>         # 切换当前小说

  # 查看帮助
  %(prog)s cli --help                  # 查看 CLI 帮助
  %(prog)s api --help                  # 查看 API 管理帮助
  %(prog)s novel --help                # 查看小说项目管理帮助

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
  outline       生成章节大纲
  expand        扩写章节内容
  continue      续写章节
  status        查看项目状态
  settings      配置AI角色和设置
  touch         标记章节修改类型
  regenerate    重生成指定章节

使用 %(prog)s cli --help 查看所有命令
        """
    )

    # 添加一个特殊的 --cli-help 参数来处理 CLI 帮助
    cli_parser.add_argument(
        'cli_args',
        nargs='*',
        help='CLI 命令和参数 (传递给 novel_generator.cli)'
    )

    # API 子命令
    api_parser = subparsers.add_parser(
        'api',
        help='API 管理模式 (管理API配置)',
        description='API 管理模式 - 管理多API配置',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
API 命令:
  list          列出所有API配置
  create        创建新API配置
  use <name>    切换默认API
  test [name]   测试API连接
  delete <name> 删除API配置
  edit <name>   编辑API配置

使用 %(prog)s api --help 查看所有命令
        """
    )

    api_parser.add_argument(
        'api_args',
        nargs='*',
        help='API 管理命令和参数'
    )

    # novel 子命令
    novel_parser = subparsers.add_parser(
        'novel',
        help='小说项目管理模式 (管理多小说项目)',
        description='小说项目管理模式 - 管理多小说项目',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Novel 命令:
  list              列出所有小说项目
  create <name>     创建新小说项目
  switch <name>     切换当前小说
  rename <old> <new> 重命名小说项目
  delete <name>     删除小说项目
  info [name]       查看小说项目信息
  export <name>     导出小说项目
  import <path>     导入小说项目

使用 %(prog)s novel --help 查看所有命令
        """
    )

    novel_parser.add_argument(
        'novel_args',
        nargs='*',
        help='小说项目管理命令和参数'
    )

    return parser


def main():
    """主入口函数"""
    parser = create_parser()

    # 如果没有提供任何参数，显示帮助
    if len(sys.argv) < 2:
        parser.print_help()
        print("\n提示: 使用 'soundnovel.py cli' 进入命令行模式")
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

    elif args.mode == 'api':
        # API 管理模式
        if not remaining and not getattr(args, 'api_args', None):
            remaining.append('--help')

        all_args = args.api_args + remaining if getattr(args, 'api_args', None) else remaining
        run_api(all_args)

    elif args.mode == 'novel':
        # 小说项目管理模式
        if not remaining and not getattr(args, 'novel_args', None):
            remaining.append('--help')

        all_args = args.novel_args + remaining if getattr(args, 'novel_args', None) else remaining
        run_novel(all_args)

    else:
        # 未知模式
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
