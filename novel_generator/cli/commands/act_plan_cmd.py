"""
幕规划命令

仅执行 Stage 1：生成幕规划（act_plan.json）
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from novel_generator.core.outline_generator import OutlineGenerator
from novel_generator.config.settings import Settings
from novel_generator.cli.utils import (
    print_success, print_error, print_info, print_warning,
    setup_cli_logging, get_config_manager
)


def run(args: argparse.Namespace) -> int:
    """
    执行幕规划生成（Stage 1）

    Args:
        args: 命令行参数

    Returns:
        int: 退出码
    """
    logger = setup_cli_logging()

    print_info("开始幕规划生成（Stage 1）...")

    try:
        config_manager = get_config_manager(novel_id=getattr(args, 'novel_id', None))

        # Load source files
        paths = config_manager.get_novel_paths()
        core_setting_path = paths["core_setting"]
        overall_outline_path = paths["overall_outline"]

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

        # Initialize outline generator
        outline_gen = OutlineGenerator(api_config, output_dir=paths["outline_dir"])

        # Check if act_plan already exists
        if outline_gen.act_plan_file.exists() and not args.force:
            print_warning(f"幕规划已存在: {outline_gen.act_plan_file}")
            print_info("使用 --force 参数强制重新生成")
            return 0

        total_chapters = outline_gen.extract_total_chapters(overall_outline)
        num_acts = args.num_acts if args.num_acts else outline_gen.extract_num_acts(overall_outline)

        print_info(f"总章节数: {total_chapters}, 幕数: {num_acts}")

        # Execute Stage 1 only
        act_plan = outline_gen.generate_act_plan_only(
            core_setting=core_setting,
            overall_outline=overall_outline,
            num_acts=num_acts,
        )

        # Update progress
        config_manager.update_progress("act_plan", 1, total_chapters)

        print()
        print_success("幕规划生成完成！")
        print()
        print_info("生成文件:")
        print(f"  {outline_gen.act_plan_file}")
        print()
        print_info("下一步操作:")
        print("  1. 审阅幕规划内容")
        print("  2. 运行 'soundnovel chapter-summary' 生成章节梗概")

        return 0

    except FileNotFoundError as e:
        print_error(f"文件未找到: {e}")
        return 1
    except Exception as e:
        print_error(f"生成幕规划失败: {e}")
        import traceback
        traceback.print_exc()
        return 1