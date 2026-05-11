"""
SoundNovel CLI 主入口

统一命令行接口，支持:
- outline: 生成章节大纲
- expand: 扩写章节内容
- continue: 续写章节
- status: 查看项目状态
- settings: 配置AI角色和设置
- touch: 标记章节修改类型
- regenerate: 重生成指定章节
- api: 管理API配置
- novel: 管理小说项目
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from novel_generator.cli import commands
from novel_generator.cli.utils import setup_cli_logging
from novel_generator.cli.commands.api_commands import (
    api_list, api_create, api_use, api_test, api_delete, api_edit
)
from novel_generator.cli.commands.novel_commands import (
    novel_list, novel_create, novel_switch, novel_rename,
    novel_delete, novel_info, novel_export, novel_import
)


def create_parser() -> argparse.ArgumentParser:
    """创建主参数解析器"""
    parser = argparse.ArgumentParser(
        prog='soundnovel',
        description='SoundNovel - AI辅助小说创作工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s novel create              创建新小说项目
  %(prog)s novel list                列出所有小说
  %(prog)s novel switch <id>         切换当前小说
  %(prog)s novel info                查看当前小说信息

  %(prog)s api create                创建API配置
  %(prog)s api list                  列出API配置
  %(prog)s api use <id>              设置默认API

  %(prog)s outline                   生成章节大纲
  %(prog)s expand --chapter 1        扩写第1章
  %(prog)s expand --start 1 --end 10 扩写第1-10章
  %(prog)s continue                  续写章节
  %(prog)s status                    查看项目状态
  %(prog)s touch --chapter 15 --type content  标记章节修改
  %(prog)s regenerate --chapters 12-14        重生成章节

全局选项:
  --novel <id>                       指定小说ID（使用默认配置时）

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
    parser.add_argument(
        '--novel',
        dest='novel_id',
        type=str,
        default=None,
        help='指定小说ID（可选，默认使用当前小说）'
    )

    # 子命令
    subparsers = parser.add_subparsers(
        dest='command',
        title='可用命令',
        help='使用 %(prog)s <command> -h 查看命令帮助'
    )

    # outline 命令
    outline_parser = subparsers.add_parser(
        'outline',
        help='生成章节大纲',
        description='基于核心设定和整体大纲生成详细章节大纲'
    )
    outline_parser.add_argument(
        '--config', '-c',
        type=str,
        default=None,
        help='配置文件路径（已废弃，配置现在存储在novels/<novel>/config/）'
    )
    outline_parser.add_argument(
        '--output', '-o',
        type=str,
        help='输出文件路径（默认: 自动命名）'
    )
    outline_parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=None,
        help='每批生成章节数（默认: 从 session.json 读取，初始值 15）'
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
    outline_parser.add_argument(
        '--num-acts', '-a',
        type=int,
        default=3,
        help='幕数（默认: 3）'
    )
    outline_parser.add_argument(
        '--window', '-w',
        type=int,
        default=None,
        help='对话窗口大小（默认: 100章）'
    )
    outline_parser.add_argument(
        '--resume', '-r',
        action='store_true',
        help='从上次检查点恢复生成'
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
        default=None,
        help='配置文件路径（已废弃，配置现在存储在novels/<novel>/config/）'
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
        '--from-last',
        action='store_true',
        help='从上次结束的章节继续'
    )
    expand_parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='强制交互模式'
    )
    expand_parser.add_argument(
        '--outline-window',
        type=int,
        default=None,
        help='大纲上下文窗口大小（默认: 30）'
    )
    expand_parser.add_argument(
        '--draft-window',
        type=int,
        default=None,
        help='正文上下文窗口大小（默认: 10）'
    )
    expand_parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=None,
        help='批量生成时每批章节数（默认: 从配置读取，初始值 10）'
    )
    expand_parser.add_argument(
        '--single',
        action='store_true',
        help='强制使用单章模式（禁用批量优化，用于调试）'
    )
    expand_parser.set_defaults(func=commands.expand)

    # status 命令
    status_parser = subparsers.add_parser(
        'status',
        help='查看项目状态',
        description='显示当前项目的生成进度、配置状态和章节状态'
    )
    status_parser.set_defaults(func=commands.status)

    # continue 命令
    continue_parser = subparsers.add_parser(
        'continue',
        help='续写章节',
        description='从上次结束的章节或第一个dirty章节继续生成'
    )
    continue_parser.add_argument(
        '--end', '-e',
        type=int,
        help='结束章节号（默认: 总章节数）'
    )
    continue_parser.add_argument(
        '--cascade',
        action='store_true',
        help='自动级联重生成所有dirty章节'
    )
    continue_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅显示将生成哪些章节，不实际执行'
    )
    continue_parser.set_defaults(func=commands.continue_write)

    # touch 命令
    touch_parser = subparsers.add_parser(
        'touch',
        help='标记章节修改类型',
        description='用户修改章节正文后，告知系统修改的性质（cosmetic/content）'
    )
    touch_parser.add_argument(
        '--chapter', '-ch',
        type=int,
        required=True,
        help='章节号'
    )
    touch_parser.add_argument(
        '--type', '-t',
        type=str,
        choices=['cosmetic', 'content'],
        required=True,
        help='修改类型: cosmetic=仅润色, content=内容变更'
    )
    touch_parser.add_argument(
        '--no-cascade',
        action='store_true',
        help='不触发级联dirty标记'
    )
    touch_parser.set_defaults(func=commands.touch)

    # regenerate 命令
    regenerate_parser = subparsers.add_parser(
        'regenerate',
        help='重生成指定章节',
        description='重生成指定范围的章节正文或大纲'
    )
    regenerate_parser.add_argument(
        '--chapters',
        type=str,
        help='章节范围，如 "12-14" 或 "15"'
    )
    regenerate_parser.add_argument(
        '--chapter',
        type=int,
        help='单章节号'
    )
    regenerate_parser.add_argument(
        '--outline',
        action='store_true',
        help='仅重生成大纲（而非正文）'
    )
    regenerate_parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='跳过确认，自动级联'
    )
    regenerate_parser.set_defaults(func=commands.regenerate)

    from novel_generator.cli.commands.settings_cmd import add_parser as add_settings_parser
    add_settings_parser(subparsers)

    # api 命令
    from novel_generator.cli.commands.api_commands import add_parser as add_api_parser
    add_api_parser(subparsers)

    # novel 命令
    from novel_generator.cli.commands.novel_commands import add_parser as add_novel_parser
    add_novel_parser(subparsers)

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
        try:
            print("\n\n⚠️  操作已取消")
        except UnicodeEncodeError:
            print("\n\n[WARN] 操作已取消")
        sys.exit(130)
    except Exception as e:
        try:
            print(f"\n❌ 错误: {e}")
        except UnicodeEncodeError:
            print(f"\n[ERROR] {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
