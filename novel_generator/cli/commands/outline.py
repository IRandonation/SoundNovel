"""
大纲生成命令

基于核心设定和整体大纲生成详细章节大纲（两阶段增量）
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

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
    执行大纲生成（两阶段增量）

    Args:
        args: 命令行参数

    Returns:
        int: 退出码
    """
    logger = setup_cli_logging()

    print_info("开始两阶段大纲生成（幕规划 → 章骨架）...")

    try:
        config_manager = get_config_manager(novel_id=getattr(args, 'novel_id', None))
        gen_config = config_manager.get_generation_config()

        # Load source files from novel
        paths = config_manager.get_novel_paths()
        core_setting_path = paths["core_setting"]
        overall_outline_path = paths["overall_outline"]

        # Load source content
        import yaml
        if core_setting_path.exists():
            with open(core_setting_path, "r", encoding="utf-8") as f:
                core_setting = yaml.safe_load(f) or {}
        else:
            core_setting = {}

        if overall_outline_path.exists():
            with open(overall_outline_path, "r", encoding="utf-8") as f:
                overall_outline = yaml.safe_load(f) or {}
        else:
            overall_outline = {}

        if not core_setting:
            print_error("核心设定为空，请先填写 source/core_setting.yaml")
            return 1

        if not overall_outline:
            print_error("整体大纲为空，请先填写 source/overall_outline.yaml")
            return 1

        print_info("核心设定和整体大纲加载完成")

        # Use API config for settings
        api_config = config_manager.get_api_config()
        settings = Settings(api_config)
        settings.validate()

        # Initialize outline generator with novel paths
        outline_gen = OutlineGenerator(api_config, output_dir=paths["outline_dir"])

        total_chapters = outline_gen.extract_total_chapters(overall_outline)
        print_info(f"检测到总章节数: {total_chapters}")

        start_ch = args.start if args.start else 1
        end_ch = args.end if args.end else total_chapters

        if start_ch < 1 or end_ch > total_chapters or start_ch > end_ch:
            print_error(f"无效的章节范围: {start_ch}-{end_ch} (有效范围: 1-{total_chapters})")
            return 1

        print_info(f"生成章节范围: 第{start_ch}章 - 第{end_ch}章")

        # 检查已有进度
        act_plan_exists = outline_gen.act_plan_file.exists()
        skeletons_exists = outline_gen.skeletons_file.exists()

        print_info("当前进度:")
        print(f"  - 幕规划: {'已存在' if act_plan_exists else '待生成'}")
        print(f"  - 章级骨架: {'已存在' if skeletons_exists else '待生成'}")

        num_acts = args.num_acts if args.num_acts else outline_gen.extract_num_acts(overall_outline)
        print_info(f"检测到 {num_acts} 幕结构")

        # 执行两阶段生成（自动增量）
        batch_size = args.batch_size if args.batch_size else None
        final_outline = outline_gen.generate_outline_v2(
            core_setting=core_setting,
            overall_outline=overall_outline,
            num_acts=num_acts,
            chapter_range=(start_ch, end_ch),
            batch_size=batch_size,
        )

        # 更新 session 中的大纲文件路径
        config_manager.update_progress("outline", start_ch, end_ch, str(outline_gen.outline_file.resolve()))

        print()
        print_success(f"大纲生成完成！共 {len(final_outline)} 章")
        print()
        print_info("生成文件:")
        print(f"  - 幕规划: {outline_gen.act_plan_file}")
        print(f"  - 章节大纲: {outline_gen.outline_file}")
        print()
        print_info("下一步操作:")
        print("  1. 查看生成的大纲文件")
        print("  2. 运行 'soundnovel cli expand --chapter 1' 开始扩写章节")

        return 0

    except FileNotFoundError as e:
        print_error(f"文件未找到: {e}")
        return 1
    except Exception as e:
        print_error(f"生成大纲失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
