"""
touch 命令

用户手动修改章节正文后，告知系统修改的性质。
cosmetic: 仅润色修改，不触发级联
content: 内容变更，触发脏传播
"""

import argparse
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from novel_generator.cli.utils import (
    print_success, print_error, print_info, print_warning,
    get_config_manager,
)


def run(args: argparse.Namespace) -> int:
    chapter_num = args.chapter
    change_type = args.type
    no_cascade = getattr(args, 'no_cascade', False)

    config_manager = get_config_manager(novel_id=getattr(args, 'novel_id', None))

    if change_type == "cosmetic":
        config_manager.set_chapter_state(chapter_num, "cosmetic")
        print_success(f"第{chapter_num}章已标记为 cosmetic（仅润色），不触发级联")
        return 0

    # content 类型
    config_manager.set_chapter_state(chapter_num, "clean")

    if no_cascade:
        print_info(f"第{chapter_num}章已标记为 content 变更（--no-cascade，不传播 dirty）")
        return 0

    # 获取窗口大小
    gen_config = config_manager.get_generation_config()
    draft_window = gen_config.get("draft_window", 10)

    count = config_manager.mark_dirty_cascade(chapter_num, draft_window)
    if count > 0:
        affected_end = chapter_num + draft_window
        print_warning(f"第{chapter_num}章为内容变更，第{chapter_num + 1}~{affected_end}章已标记为 dirty")
        print_info(f"建议运行 'soundnovel continue --cascade' 或 'soundnovel regenerate --chapters {chapter_num + 1}-{affected_end}'")
    else:
        print_info(f"第{chapter_num}章已标记为 content 变更，无后续章节需要级联")

    return 0
