"""
SoundNovel CLI 主入口

统一命令行接口，支持:
- init: 初始化项目
- outline: 生成章节大纲
- expand: 扩写章节内容
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from novel_generator.cli import commands
from novel_generator.cli.utils import setup_cli_logging


def create_parser() -> argparse.ArgumentParser:
    """创建主参数解析器"""
    parser = argparse.ArgumentParser(
        prog='soundnovel',
        description='SoundNovel - AI辅助小说创作工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s init                    初始化新项目
  %(prog)s outline                 生成章节大纲
  %(prog)s expand --chapter 1      扩写第1章
  %(prog)s expand --start 1 --end 10   扩写第1-10章

更多信息:
  查看 README.md 获取详细使用指南
        """
    )
    
    # 全局选项
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s 0.1.0'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='显示详细日志'
    )
    
    # 子命令
    subparsers = parser.add_subparsers(
        dest='command',
        title='可用命令',
        help='使用 %(prog)s <command> -h 查看命令帮助'
    )
    
    # init 命令
    init_parser = subparsers.add_parser(
        'init',
        help='初始化小说项目',
        description='创建项目目录结构和示例文件'
    )
    init_parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='强制覆盖已有文件'
    )
    init_parser.add_argument(
        '--project-root',
        type=str,
        help='项目根目录路径（默认: 当前目录）'
    )
    init_parser.add_argument(
        '--skip-config',
        action='store_true',
        help='跳过交互式 API 配置向导'
    )
    init_parser.set_defaults(func=commands.init)
    
    # outline 命令
    outline_parser = subparsers.add_parser(
        'outline',
        help='生成章节大纲',
        description='基于核心设定和整体大纲生成详细章节大纲'
    )
    outline_parser.add_argument(
        '--config', '-c',
        type=str,
        default='05_script/config.json',
        help='配置文件路径（默认: 05_script/config.json）'
    )
    outline_parser.add_argument(
        '--output', '-o',
        type=str,
        help='输出文件路径（默认: 自动命名）'
    )
    outline_parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=15,
        help='每批生成章节数（默认: 15）'
    )
    outline_parser.add_argument(
        '--start', '-s',
        type=int,
        help='起始章节号'
    )
    outline_parser.add_argument(
        '--end', '-e',
        type=int,
        help='结束章节号'
    )
    outline_parser.set_defaults(func=commands.outline)
    
    # expand 命令
    expand_parser = subparsers.add_parser(
        'expand',
        help='扩写章节内容',
        description='将章节大纲扩写为完整正文'
    )
    expand_parser.add_argument(
        '--config', '-c',
        type=str,
        default='05_script/config.json',
        help='配置文件路径（默认: 05_script/config.json）'
    )
    expand_parser.add_argument(
        '--outline-file', '-f',
        type=str,
        help='大纲文件路径（默认: 自动查找最新）'
    )
    expand_parser.add_argument(
        '--chapter', '-ch',
        type=int,
        help='单章节号'
    )
    expand_parser.add_argument(
        '--start', '-s',
        type=int,
        help='起始章节号（与--end配合使用）'
    )
    expand_parser.add_argument(
        '--end', '-e',
        type=int,
        help='结束章节号（与--start配合使用）'
    )
    expand_parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='强制交互模式'
    )
    expand_parser.set_defaults(func=commands.expand)
    
    return parser


def main():
    """主入口函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    # 没有子命令时显示帮助
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 设置日志
    logger = setup_cli_logging()
    if args.verbose:
        logger.setLevel('DEBUG')
    
    # 执行命令
    try:
        exit_code = args.func(args)
        sys.exit(exit_code if exit_code is not None else 0)
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已取消")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
