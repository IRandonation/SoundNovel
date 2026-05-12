"""
章节梗概命令

仅执行 Stage 1：生成章节梗概（chapter_summary.json）
不依赖 act_plan.json，直接从 overall_outline.yaml 的幕结构读取幕信息。
"""

import argparse
import sys
import json
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
    执行章节梗概生成（Stage 1）

    Args:
        args: 命令行参数

    Returns:
        int: 退出码
    """
    logger = setup_cli_logging()

    print_info("开始章节梗概生成（Stage 1）...")

    try:
        config_manager = get_config_manager(novel_id=getattr(args, 'novel_id', None))

        paths = config_manager.get_novel_paths()
        outline_dir = paths["outline_dir"]

        # Load source files
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

        # Use API config
        api_config = config_manager.get_api_config()
        settings = Settings(api_config)
        settings.validate()

        # Initialize outline generator
        outline_gen = OutlineGenerator(api_config, output_dir=outline_dir)

        total_chapters = outline_gen.extract_total_chapters(overall_outline)

        # Determine chapter range
        start_ch = args.start if args.start else 1
        end_ch = args.end if args.end and args.end > 0 else total_chapters

        if start_ch < 1 or end_ch > total_chapters or start_ch > end_ch:
            print_error(f"无效的章节范围: {start_ch}-{end_ch} (有效范围: 1-{total_chapters})")
            return 1

        print_info(f"生成章节范围: 第{start_ch}章 - 第{end_ch}章")

        # Check existing summaries
        summary_file = outline_gen.summary_file
        if summary_file.exists() and not args.force:
            with open(summary_file, "r", encoding="utf-8") as f:
                existing_summaries = json.load(f)

            missing = []
            for ch in range(start_ch, end_ch + 1):
                if f"第{ch}章" not in existing_summaries:
                    missing.append(ch)

            if not missing:
                print_warning(f"章节梗概已完整: 第{start_ch}-{end_ch}章")
                print_info("使用 --force 参数强制重新生成指定范围")
                return 0
            else:
                print_info(f"已存在部分梗概，缺少 {len(missing)} 章，将补充生成")
        elif args.force:
            print_warning("--force 参数将重新生成指定范围的所有梗概")

        # Execute Stage 1
        batch_size = args.batch_size if args.batch_size else None

        summaries = outline_gen.generate_summaries_only(
            core_setting=core_setting,
            overall_outline=overall_outline,
            chapter_range=(start_ch, end_ch),
            batch_size=batch_size,
            force_regenerate=args.force,
        )

        # Update progress
        config_manager.update_progress("chapter_summary", start_ch, end_ch)

        print()
        print_success("章节梗概生成完成！")
        print()
        print_info("生成文件:")
        print(f"  {outline_gen.summary_file}")
        print_info(f"共生成 {len(summaries)} 章梗概")
        print()
        print_info("下一步操作:")
        print("  1. 审阅每章梗概是否合理")
        print("  2. 运行 'soundnovel outline' 生成详细骨架")

        return 0

    except FileNotFoundError as e:
        print_error(f"文件未找到: {e}")
        return 1
    except Exception as e:
        print_error(f"生成章节梗概失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
