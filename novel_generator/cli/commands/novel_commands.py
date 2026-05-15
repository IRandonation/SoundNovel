"""
小说项目管理命令

管理多小说项目：创建、切换、重命名、删除、导入导出等
"""

import argparse
import sys
import json
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))  # noqa: E402

from novel_generator.cli.utils import (  # noqa: E402
    print_success,
    print_error,
    print_info,
    print_warning,
    confirm_action,
)
from novel_generator.config.config_manager import ConfigManager  # noqa: E402
from novel_generator.novel_manager import NovelManager, NovelProject  # noqa: E402


NOVELS_DIR = Path("novels")


def _get_novels_dir(project_root: str = ".") -> Path:
    """获取小说目录"""
    return Path(project_root) / NOVELS_DIR


def _ensure_novels_dir(project_root: str = ".") -> Path:
    """确保小说目录存在"""
    novels_dir = _get_novels_dir(project_root)
    novels_dir.mkdir(parents=True, exist_ok=True)
    return novels_dir


def _get_novel_dirs(project_root: str = ".") -> List[Path]:
    """获取所有小说目录"""
    novels_dir = _get_novels_dir(project_root)
    if not novels_dir.exists():
        return []
    return [d for d in novels_dir.iterdir() if d.is_dir()]


def _get_novel_info(novel_dir: Path) -> Dict[str, Any]:
    """获取小说信息"""
    info = {
        "id": novel_dir.name,
        "name": novel_dir.name,
        "description": "",
        "created_at": "",
        "updated_at": "",
    }

    # 从新架构的 config/novel.json 读取信息
    novel_config_file = novel_dir / "config" / "novel.json"
    if novel_config_file.exists():
        try:
            with open(novel_config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                info["name"] = data.get("name", novel_dir.name)
                info["description"] = data.get("description", "")
                info["created_at"] = data.get("created_at", "")
                info["updated_at"] = data.get("updated_at", "")
        except Exception:
            pass
    else:
        # 兼容旧版：尝试从session.json读取信息
        session_file = novel_dir / "user" / "config" / "session.json"
        if session_file.exists():
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    info["name"] = data.get("project_name", novel_dir.name)
                    info["created_at"] = data.get("created_at", "")
                    info["updated_at"] = data.get("updated_at", "")
            except Exception:
                pass

    return info


def _get_current_novel_id(project_root: str = ".") -> Optional[str]:
    """获取当前活跃小说ID"""
    current_file = Path(project_root) / ".current_novel"
    if current_file.exists():
        try:
            with open(current_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return None


def _set_current_novel(novel_id: str, project_root: str = ".") -> bool:
    """设置当前活跃小说"""
    try:
        current_file = Path(project_root) / ".current_novel"
        with open(current_file, "w", encoding="utf-8") as f:
            f.write(novel_id)
        return True
    except Exception as e:
        print_error(f"设置当前小说失败: {e}")
        return False


def _format_datetime(dt_str: str) -> str:
    """格式化日期时间"""
    if not dt_str:
        return "未知"
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return dt_str


def _list_novels_table(novels: List[Dict[str, Any]], current_id: Optional[str]) -> None:
    """以表格形式展示小说列表"""
    from rich.console import Console
    from rich.table import Table
    from rich import box

    console = Console()

    table = Table(
        title="小说项目列表",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )

    table.add_column("ID", style="dim", width=20)
    table.add_column("名称", width=25)
    table.add_column("描述", width=30)
    table.add_column("创建时间", width=16)
    table.add_column("当前", width=6)

    for novel in novels:
        is_current = "✓" if novel["id"] == current_id else ""
        created_at = _format_datetime(novel.get("created_at", ""))
        desc = novel.get("description", "")[:28] + "..." if len(novel.get("description", "")) > 30 else novel.get("description", "")

        table.add_row(
            novel["id"],
            novel["name"],
            desc if desc else "-",
            created_at,
            is_current,
        )

    console.print(table)


def novel_list(args: argparse.Namespace) -> int:
    """列出所有小说"""
    novels_dir = _get_novels_dir(str(Path.cwd()))

    if not novels_dir.exists():
        print_info("暂无小说项目")
        print_info(f"运行 'soundnovel novel create' 创建新小说")
        return 0

    novel_dirs = _get_novel_dirs(str(Path.cwd()))
    if not novel_dirs:
        print_info("暂无小说项目")
        print_info(f"运行 'soundnovel novel create' 创建新小说")
        return 0

    novels = [_get_novel_info(d) for d in novel_dirs]
    current_id = _get_current_novel_id(str(Path.cwd()))

    _list_novels_table(novels, current_id)

    if current_id:
        print_info(f"\n当前活跃小说: {current_id}")
    else:
        print_info("\n提示: 使用 'soundnovel novel switch <ID>' 切换当前小说")

    return 0


def novel_create(args: argparse.Namespace) -> int:
    """交互式创建新小说"""
    project_root = Path.cwd()
    novels_dir = _ensure_novels_dir(str(project_root))

    print_info("=" * 60)
    print_info("创建新小说项目")
    print_info("=" * 60)

    # 小说名称
    name = input("\n小说名称: ").strip()
    if not name:
        print_error("小说名称不能为空")
        return 1

    # 生成小说ID（使用小写字母和数字）
    import re
    novel_id = re.sub(r'[^\w\s-]', '', name.lower())
    novel_id = re.sub(r'[-\s]+', '-', novel_id)
    novel_id = novel_id[:30]  # 限制长度

    # 检查是否已存在
    novel_dir = novels_dir / novel_id
    if novel_dir.exists():
        print_error(f"小说 '{novel_id}' 已存在")
        return 1

    # 描述
    description = input("小说描述（可选）: ").strip()

    # 选择API配置（使用新架构 APIManager）
    from api.manager import APIManager
    api_manager = APIManager(str(project_root))
    all_configs = api_manager.list_configs()
    default_config = api_manager.get_default()

    print_info("\n可用API配置:")
    config_choices = []
    for i, cfg in enumerate(all_configs, 1):
        is_default = "(默认)" if default_config and cfg["id"] == default_config.id else ""
        print(f"  {i}. {cfg['name']} ({cfg['provider']}) {is_default}")
        config_choices.append(cfg["id"])

    if not config_choices:
        print_warning("未配置API，请先运行 'soundnovel api create' 配置API")
        if not confirm_action("是否仍要继续创建小说?"):
            return 0
        selected_provider = ""
    else:
        default_id = default_config.id if default_config else config_choices[0]
        provider_choice = input("\n请选择API配置 (输入序号，直接回车使用默认): ").strip()
        if provider_choice:
            try:
                idx = int(provider_choice) - 1
                if 0 <= idx < len(config_choices):
                    selected_provider = config_choices[idx]
                else:
                    selected_provider = default_id
            except ValueError:
                selected_provider = default_id
        else:
            selected_provider = default_id

    # 创建目录结构
    try:
        print_info(f"\n正在创建小说项目: {novel_id}")

        # 使用 NovelProject 初始化（新架构）
        novel_project = NovelProject(novel_dir)
        novel_project.initialize(
            name=name,
            description=description,
            api_config_ref=selected_provider
        )

        # 设置为当前小说
        _set_current_novel(novel_id, str(project_root))

        print_success(f"\n小说项目 '{name}' 创建成功!")
        print_info(f"  项目ID: {novel_id}")
        print_info(f"  项目路径: {novel_dir}")
        if selected_provider:
            print_info(f"  API配置: {selected_provider}")
        print_info("\n下一步:")
        print_info("  1. 编辑 source/core_setting.yaml 填写核心设定")
        print_info("  2. 编辑 source/chapter_plan.yaml 填写章节规划（5章区间）")
        print_info("  3. 编辑 prompts/style_guide.yaml 调整风格指导")
        print_info("  4. 运行 'soundnovel cli outline' 生成章节大纲")

        return 0
    except Exception as e:
        print_error(f"创建小说项目失败: {e}")
        # 清理已创建的目录
        if novel_dir.exists():
            shutil.rmtree(novel_dir)
        return 1


def novel_switch(args: argparse.Namespace) -> int:
    """切换当前小说"""
    novel_id = args.novel_id
    project_root = Path.cwd()
    novels_dir = _get_novels_dir(str(project_root))

    novel_dir = novels_dir / novel_id
    if not novel_dir.exists():
        print_error(f"小说 '{novel_id}' 不存在")
        return 1

    if _set_current_novel(novel_id, str(project_root)):
        info = _get_novel_info(novel_dir)
        print_success(f"已切换到小说: {info['name']} ({novel_id})")
        return 0
    else:
        return 1


def novel_rename(args: argparse.Namespace) -> int:
    """重命名小说"""
    novel_id = args.novel_id
    new_name = args.new_name
    project_root = Path.cwd()
    novels_dir = _get_novels_dir(str(project_root))

    novel_dir = novels_dir / novel_id
    if not novel_dir.exists():
        print_error(f"小说 '{novel_id}' 不存在")
        return 1

    # 更新session.json中的项目名称
    session_file = novel_dir / "user" / "config" / "session.json"
    if session_file.exists():
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["project_name"] = new_name
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print_error(f"更新项目名称失败: {e}")
            return 1

    # 更新novel_info.json
    info_file = novel_dir / "novel_info.json"
    if info_file.exists():
        try:
            with open(info_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["name"] = new_name
            with open(info_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print_error(f"更新小说信息失败: {e}")
            return 1

    print_success(f"已将小说重命名为: {new_name}")
    return 0


def novel_delete(args: argparse.Namespace) -> int:
    """删除小说"""
    novel_id = args.novel_id
    project_root = Path.cwd()
    novels_dir = _get_novels_dir(str(project_root))

    novel_dir = novels_dir / novel_id
    if not novel_dir.exists():
        print_error(f"小说 '{novel_id}' 不存在")
        return 1

    # 获取小说信息用于确认
    info = _get_novel_info(novel_dir)

    # 确认删除
    print_warning(f"即将删除小说: {info['name']} ({novel_id})")
    print_warning(f"项目路径: {novel_dir}")
    if not confirm_action("此操作不可撤销，确认删除?"):
        print_info("已取消")
        return 0

    try:
        shutil.rmtree(novel_dir)

        # 如果删除的是当前活跃小说，清空当前标记
        current_id = _get_current_novel_id(str(project_root))
        if current_id == novel_id:
            current_file = Path(project_root) / ".current_novel"
            if current_file.exists():
                current_file.unlink()

        print_success(f"已删除小说: {info['name']}")
        return 0
    except Exception as e:
        print_error(f"删除小说失败: {e}")
        return 1


def novel_info(args: argparse.Namespace) -> int:
    """查看小说信息"""
    project_root = Path.cwd()
    novels_dir = _get_novels_dir(str(project_root))

    novel_id = getattr(args, 'novel_id', None)

    if novel_id:
        novel_dir = novels_dir / novel_id
        if not novel_dir.exists():
            print_error(f"小说 '{novel_id}' 不存在")
            return 1
    else:
        novel_id = _get_current_novel_id(str(project_root))
        if not novel_id:
            print_error("未指定小说ID，且没有当前活跃小说")
            return 1
        novel_dir = novels_dir / novel_id

    info = _get_novel_info(novel_dir)

    # 从新架构的 config/state.json 读取进度
    state_file = novel_dir / "config" / "state.json"
    state_data = {}
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state_data = json.load(f)
        except Exception:
            pass

    # 从 config/novel.json 读取API配置引用
    novel_config_file = novel_dir / "config" / "novel.json"
    api_configured = False
    if novel_config_file.exists():
        try:
            with open(novel_config_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                api_configured = bool(config_data.get("api_config_ref", ""))
        except Exception:
            pass

    # 获取进度信息
    total_chapters = state_data.get("total_chapters", 0)
    last_outline = state_data.get("last_outline_chapter", 0)
    last_draft = state_data.get("last_draft_chapter", 0)
    chapter_states = state_data.get("chapter_states", {})
    dirty_count = sum(1 for v in chapter_states.values() if v == "dirty")

    print_info("=" * 60)
    print_info(f"小说项目信息: {info['name']}")
    print_info("=" * 60)

    print(f"\n  项目ID: {info['id']}")
    print(f"  项目名称: {info['name']}")
    print(f"  描述: {info['description'] if info['description'] else '无'}")
    print(f"  项目路径: {novel_dir}")
    print(f"  创建时间: {_format_datetime(info['created_at'])}")
    print(f"  更新时间: {_format_datetime(info['updated_at'])}")

    print(f"\n  API配置: {'已配置' if api_configured else '未配置'}")

    print(f"\n  生成进度:")
    if total_chapters > 0:
        print(f"    总章节: {total_chapters}")
        print(f"    大纲进度: {last_outline} / {total_chapters} ({last_outline/total_chapters*100:.1f}%)")
        print(f"    草稿进度: {last_draft} / {total_chapters} ({last_draft/total_chapters*100:.1f}%)")
    else:
        print(f"    大纲: {last_outline if last_outline > 0 else '未生成'} 章")
        print(f"    草稿: {last_draft if last_draft > 0 else '未生成'} 章")

    if dirty_count > 0:
        print(f"\n  章节状态: {dirty_count} 章需要重生成")

    # 检查是否为当前活跃小说
    current_id = _get_current_novel_id(str(project_root))
    if current_id == novel_id:
        print(f"\n  [当前活跃小说]")

    print_info("=" * 60)
    return 0

    print(f"\n  会话记录: {status['session_count']} 条")

    # 检查是否是当前活跃小说
    current_id = _get_current_novel_id(str(project_root))
    if current_id == info['id']:
        print_info("\n  [当前活跃小说]")

    print_info("\n" + "=" * 60)

    return 0


def novel_export(args: argparse.Namespace) -> int:
    """导出小说备份"""
    novel_id = args.novel_id
    project_root = Path.cwd()
    novels_dir = _get_novels_dir(str(project_root))

    novel_dir = novels_dir / novel_id
    if not novel_dir.exists():
        print_error(f"小说 '{novel_id}' 不存在")
        return 1

    # 确定输出路径
    if hasattr(args, 'output_path') and args.output_path:
        output_path = Path(args.output_path)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = project_root / f"{novel_id}_{timestamp}.zip"

    try:
        print_info(f"正在导出小说: {novel_id}")
        print_info(f"目标文件: {output_path}")

        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in novel_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(novel_dir)
                    zipf.write(file_path, arcname)

        print_success(f"导出成功: {output_path}")
        return 0
    except Exception as e:
        print_error(f"导出失败: {e}")
        return 1


def novel_import(args: argparse.Namespace) -> int:
    """导入小说"""
    import_path = Path(args.import_path)
    project_root = Path.cwd()
    novels_dir = _ensure_novels_dir(str(project_root))

    if not import_path.exists():
        print_error(f"导入文件不存在: {import_path}")
        return 1

    if not zipfile.is_zipfile(import_path):
        print_error(f"不是有效的zip文件: {import_path}")
        return 1

    try:
        print_info(f"正在导入小说: {import_path}")

        # 先读取zip内容确定novel_id
        with zipfile.ZipFile(import_path, 'r') as zipf:
            # 尝试从novel_info.json获取ID
            novel_id = None
            try:
                info_content = zipf.read('novel_info.json')
                info_data = json.loads(info_content)
                novel_id = info_data.get('id')
                novel_name = info_data.get('name', novel_id)
            except Exception:
                novel_id = import_path.stem
                novel_name = novel_id

            # 检查是否已存在
            target_dir = novels_dir / novel_id
            if target_dir.exists():
                if not confirm_action(f"小说 '{novel_id}' 已存在，是否覆盖?"):
                    print_info("已取消")
                    return 0
                shutil.rmtree(target_dir)

            # 解压到目标目录
            zipf.extractall(target_dir)

        print_success(f"导入成功: {novel_name} ({novel_id})")
        print_info(f"项目路径: {target_dir}")
        print_info(f"运行 'soundnovel novel switch {novel_id}' 切换到该小说")

        return 0
    except Exception as e:
        print_error(f"导入失败: {e}")
        return 1


def run(args: argparse.Namespace) -> int:
    """主入口函数"""
    if not args.subcommand:
        print_error("请指定子命令: list, create, switch, rename, delete, info, export, import")
        return 1

    command_map = {
        "list": novel_list,
        "create": novel_create,
        "switch": novel_switch,
        "rename": novel_rename,
        "delete": novel_delete,
        "info": novel_info,
        "export": novel_export,
        "import": novel_import,
    }

    handler = command_map.get(args.subcommand)
    if not handler:
        print_error(f"未知子命令: {args.subcommand}")
        return 1

    return handler(args)


def add_parser(subparsers):
    """添加小说命令解析器"""
    novel_parser = subparsers.add_parser(
        "novel",
        help="管理小说项目",
        description="管理多小说项目：创建、切换、重命名、删除、导入导出等",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s novel list                     列出所有小说
  %(prog)s novel create                   交互式创建新小说
  %(prog)s novel switch my-novel          切换到指定小说
  %(prog)s novel rename my-novel "新名称"  重命名小说
  %(prog)s novel delete my-novel          删除小说
  %(prog)s novel info                     查看当前小说信息
  %(prog)s novel info my-novel            查看指定小说信息
  %(prog)s novel export my-novel          导出小说备份
  %(prog)s novel export my-novel -o backup.zip  导出到指定路径
  %(prog)s novel import backup.zip        导入小说
        """
    )

    novel_parser.add_argument(
        "subcommand",
        nargs="?",
        choices=["list", "create", "switch", "rename", "delete", "info", "export", "import"],
        help="子命令",
    )

    novel_parser.add_argument(
        "novel_id",
        nargs="?",
        help="小说ID",
    )

    novel_parser.add_argument(
        "new_name",
        nargs="?",
        help="新名称（用于rename命令）",
    )

    novel_parser.add_argument(
        "--output", "-o",
        dest="output_path",
        help="导出文件路径（用于export命令）",
    )

    novel_parser.add_argument(
        "--import-path", "-i",
        dest="import_path",
        help="导入文件路径（用于import命令）",
    )

    novel_parser.set_defaults(func=run)

    return novel_parser


def _create_novel_parser() -> argparse.ArgumentParser:
    """创建独立的小说命令解析器（用于soundnovel novel入口）"""
    parser = argparse.ArgumentParser(
        prog='soundnovel novel',
        description='管理多小说项目',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  soundnovel novel list                   列出所有小说
  soundnovel novel create                 交互式创建新小说
  soundnovel novel switch my-novel        切换到指定小说
  soundnovel novel rename my-novel "新名称" 重命名小说
  soundnovel novel delete my-novel        删除小说
  soundnovel novel info                   查看当前小说信息
  soundnovel novel export my-novel        导出小说备份
  soundnovel novel import backup.zip      导入小说
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # list 命令
    list_parser = subparsers.add_parser('list', help='列出所有小说项目')
    list_parser.set_defaults(func=novel_list)

    # create 命令
    create_parser = subparsers.add_parser('create', help='创建新小说项目')
    create_parser.set_defaults(func=novel_create)

    # switch 命令
    switch_parser = subparsers.add_parser('switch', help='切换当前小说')
    switch_parser.add_argument('novel_id', help='小说ID')
    switch_parser.set_defaults(func=novel_switch)

    # rename 命令
    rename_parser = subparsers.add_parser('rename', help='重命名小说项目')
    rename_parser.add_argument('novel_id', help='小说ID')
    rename_parser.add_argument('new_name', help='新名称')
    rename_parser.set_defaults(func=novel_rename)

    # delete 命令
    delete_parser = subparsers.add_parser('delete', help='删除小说项目')
    delete_parser.add_argument('novel_id', help='小说ID')
    delete_parser.set_defaults(func=novel_delete)

    # info 命令
    info_parser = subparsers.add_parser('info', help='查看小说项目信息')
    info_parser.add_argument('novel_id', nargs='?', help='小说ID（可选）')
    info_parser.set_defaults(func=novel_info)

    # export 命令
    export_parser = subparsers.add_parser('export', help='导出小说项目')
    export_parser.add_argument('novel_id', help='小说ID')
    export_parser.add_argument('--output', '-o', dest='output_path', help='导出文件路径')
    export_parser.set_defaults(func=novel_export)

    # import 命令
    import_parser = subparsers.add_parser('import', help='导入小说项目')
    import_parser.add_argument('import_path', help='导入文件路径')
    import_parser.set_defaults(func=novel_import)

    return parser


def main(args_list=None):
    """独立入口函数（用于soundnovel novel命令）"""
    parser = _create_novel_parser()

    if args_list:
        args = parser.parse_args(args_list)
    else:
        args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    handler = getattr(args, 'func', None)
    if handler:
        return handler(args)

    return 0
