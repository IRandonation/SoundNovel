"""
大纲生成命令

执行 Stage 2：生成章骨架（outline.json）
使用 chapter_plan.yaml 的5章区间规划替代幕结构和梗概。
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import json
import yaml
from novel_generator.core.outline_generator import OutlineGenerator
from novel_generator.config.settings import Settings
from novel_generator.utils.common import (
    get_project_root, ensure_directories
)
from novel_generator.cli.utils import (
    print_success, print_error, print_info, print_warning,
    setup_cli_logging, get_config_manager
)


def run(args: argparse.Namespace) -> int:
    """
    执行章骨架生成（Stage 2）

    Args:
        args: 命令行参数

    Returns:
        int: 退出码
    """
    logger = setup_cli_logging()

    print_info("开始章骨架生成...")

    try:
        config_manager = get_config_manager(novel_id=getattr(args, 'novel_id', None))
        gen_config = config_manager.get_generation_config()

        paths = config_manager.get_novel_paths()
        outline_dir = paths["outline_dir"]

        # Load source files
        core_setting_path = paths["core_setting"]
        chapter_plan_path = paths.get("chapter_plan") or paths["source_dir"] / "chapter_plan.yaml"

        if core_setting_path.exists():
            with open(core_setting_path, "r", encoding="utf-8") as f:
                core_setting = yaml.safe_load(f) or {}
        else:
            core_setting = {}

        if chapter_plan_path.exists():
            with open(chapter_plan_path, "r", encoding="utf-8") as f:
                chapter_plan = yaml.safe_load(f) or {}
        else:
            chapter_plan = {}

        if not core_setting:
            print_error("核心设定为空，请先填写 source/core_setting.yaml")
            return 1

        if not chapter_plan or not chapter_plan.get("剧情规划"):
            print_error("章节规划为空，请先填写 source/chapter_plan.yaml")
            return 1

        print_info("核心设定和章节规划加载完成")

        # Use API config for settings
        api_config = config_manager.get_api_config()
        settings = Settings(api_config)
        settings.validate()

        # Initialize outline generator
        outline_gen = OutlineGenerator(api_config, output_dir=outline_dir, project_root=str(config_manager.project_root))

        total_chapters = chapter_plan.get("总章节数", 793)
        print_info(f"检测到总章节数: {total_chapters}")

        start_ch = args.start if args.start else 1
        end_ch = args.end if args.end else total_chapters

        if start_ch < 1 or end_ch > total_chapters or start_ch > end_ch:
            print_error(f"无效的章节范围: {start_ch}-{end_ch} (有效范围: 1-{total_chapters})")
            return 1

        print_info(f"生成章节范围: 第{start_ch}章 - 第{end_ch}章")

        # Check existing skeletons
        skeletons_exists = outline_gen.skeletons_file.exists()
        print_info("当前进度:")
        print(f"  - 级骨架: {'已存在' if skeletons_exists else '待生成'}")

        # Execute generation
        batch_size = args.batch_size if args.batch_size else None
        window = args.window if args.window else None

        final_outline = outline_gen.generate_skeletons_only(
            core_setting=core_setting,
            chapter_plan=chapter_plan,
            chapter_range=(start_ch, end_ch),
            batch_size=batch_size,
            conversation_window=window,
        )

        # Update session
        config_manager.update_progress("outline", start_ch, end_ch, str(outline_gen.outline_file.resolve()))

        print()
        print_success(f"章骨架生成完成！共 {len(final_outline)} 章")
        print()
        print_info("生成文件:")
        print(f"  {outline_gen.outline_file}")
        print()
        print_info("下一步操作:")
        print("  1. 审阅生成的骨架内容")
        print("  2. 运行 'soundnovel expand --chapter 1' 开始扩写章节")

        return 0

    except FileNotFoundError as e:
        print_error(f"文件未找到: {e}")
        return 1
    except Exception as e:
        print_error(f"生成章骨架失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
