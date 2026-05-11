"""
续写命令

从上次结束的章节继续生成，或从第一个dirty章节级联重生成。
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from novel_generator.core.chapter_expander import (
    ChapterExpander,
    _build_outline_context,
    _build_draft_context,
)
from novel_generator.utils.multi_model_client import MultiModelClient
from novel_generator.utils.common import (
    load_style_guide, load_yaml_file,
    get_project_root, get_latest_outline_file,
    get_chapter_data, ensure_directories
)
from novel_generator.cli.utils import (
    print_success, print_error, print_info, print_warning,
    setup_cli_logging, get_config_manager
)
from novel_generator.core.ai_roles import AIRole


def run(args: argparse.Namespace) -> int:
    logger = setup_cli_logging()

    config_manager = get_config_manager(novel_id=getattr(args, 'novel_id', None))
    gen_config = config_manager.get_generation_config()

    # 检查是否有 dirty 章节
    first_dirty = config_manager.get_first_dirty_chapter()
    if first_dirty > 0 and args.cascade:
        start_chapter = first_dirty
        print_info(f"级联模式: 从第 {first_dirty} 章（dirty）开始重生成")
    elif first_dirty > 0:
        print_warning(f"检测到 dirty 章节（最早: 第{first_dirty}章）")
        print_info("使用 --cascade 自动级联重生成，或使用 'soundnovel regenerate' 手动处理")
        start_from_dirty = input("是否从第 {} 章开始？[Y/n]: ".format(first_dirty)).strip().lower()
        if start_from_dirty in ('', 'y', 'yes'):
            start_chapter = first_dirty
        else:
            continue_info = config_manager.get_continue_info("draft")
            start_chapter = continue_info["next_chapter"]
    else:
        continue_info = config_manager.get_continue_info("draft")

        if not continue_info["can_continue"] and continue_info["last_chapter"] == 0:
            print_error("没有找到已生成的章节，请先运行 'soundnovel expand' 生成初始章节")
            return 1

        start_chapter = continue_info["next_chapter"]

    # Get state dict
    state = config_manager.state
    total_chapters = state.get("total_chapters", 0)

    if args.end:
        end_chapter = args.end
    elif total_chapters > 0:
        end_chapter = total_chapters
    else:
        end_chapter = start_chapter + 10
        print_warning(f"未设置总章节数，默认生成 {end_chapter - start_chapter + 1} 章")

    if total_chapters > 0 and end_chapter > total_chapters:
        print_warning(f"结束章节 {end_chapter} 超过总章节数 {total_chapters}，已调整为 {total_chapters}")
        end_chapter = total_chapters

    chapters_to_generate = list(range(start_chapter, end_chapter + 1))

    if args.dry_run:
        print_info("=== 干运行模式 ===")
        print_info(f"将生成章节: 第{start_chapter}章 - 第{end_chapter}章 ({len(chapters_to_generate)}章)")
        dirty_list = [ch for ch in chapters_to_generate if config_manager.get_chapter_state(ch) == "dirty"]
        if dirty_list:
            print_warning(f"其中 dirty 章节: {dirty_list}")
        state_summary = config_manager.get_chapter_states_summary()
        print_info(f"章节状态统计: clean={state_summary['clean']}, dirty={state_summary['dirty']}, cosmetic={state_summary['cosmetic']}")
        return 0

    print_info(f"续写模式: 第 {start_chapter} 章 - 第 {end_chapter} 章")
    print()

    config = config_manager.get_api_config()

    # Get outline file from state
    state = config_manager.state
    outline_file = state.get("outline_file", "")
    if not outline_file:
        outline_file = get_latest_outline_file()

    if not outline_file:
        print_error("未找到大纲文件，请先生成大纲")
        return 1

    print_info(f"使用大纲文件: {outline_file}")

    outline_data = load_yaml_file(Path(outline_file))
    if not outline_data:
        print_error("大纲文件为空")
        return 1

    client = MultiModelClient(config)

    from novel_generator.utils.common import load_core_setting
    core_setting = load_core_setting()
    expander = ChapterExpander(config, client, core_setting=core_setting)

    # 显示当前使用的角色配置
    role_config = expander.ai_role_manager.get_role_config(AIRole.GENERATOR)
    if role_config.provider:
        print_info(f"当前使用模型: {role_config.provider}/{role_config.model}")
    else:
        print_error("AI 角色未配置 provider，请先运行 'soundnovel settings --interactive'")
        return 1

    outline_window = gen_config.get("outline_window", 30)
    draft_window = gen_config.get("draft_window", 10)

    # Use novel paths
    novel_paths = config_manager.get_novel_paths()
    draft_dir = novel_paths["draft_dir"]
    draft_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    fail_count = 0

    for i, ch_num in enumerate(chapters_to_generate, 1):
        print()
        print_info(f"[{i}/{len(chapters_to_generate)}] 正在扩写第 {ch_num} 章...")

        try:
            ch_data = get_chapter_data(outline_data, ch_num)
            if not ch_data:
                print_error(f"大纲中找不到第 {ch_num} 章的数据")
                fail_count += 1
                continue

            outline_ctx = _build_outline_context(outline_data, ch_num, outline_window)
            draft_ctx = _build_draft_context(draft_dir, ch_num, draft_window)

            content = expander.expand_chapter(
                chapter_num=ch_num,
                chapter_outline=ch_data,
                outline_context=outline_ctx,
                draft_context=draft_ctx,
            )

            expander.save_chapter(ch_num, content, draft_dir)

            config_manager.set_chapter_state(ch_num, "clean")

            config_manager.update_progress("draft", start_chapter, ch_num, str(outline_file))

            print_success(f"第 {ch_num} 章扩写完成 ({len(content)}字)")
            success_count += 1

        except Exception as e:
            print_error(f"扩写第 {ch_num} 章失败: {e}")
            fail_count += 1
            continue

    # 获取实际使用的 role_config
    role_config = expander.ai_role_manager.get_role_config(AIRole.GENERATOR)
    model_info = f"{role_config.provider}/{role_config.model}" if role_config.model else role_config.provider

    config_manager.add_session_record(
        action="expand",
        start_chapter=start_chapter,
        end_chapter=end_chapter,
        model_used=model_info,
        success=(fail_count == 0)
    )

    print()
    print_info("=" * 50)
    print_info("续写完成！")
    print_info(f"成功: {success_count} 章")
    if fail_count > 0:
        print_warning(f"失败: {fail_count} 章")
    print_info(f"草稿位置: {draft_dir}")

    new_info = config_manager.get_continue_info("draft")
    if new_info["can_continue"]:
        print_info(f"继续续写: 运行 'soundnovel continue'")
    else:
        print_success("所有章节已完成！")

    print_info("=" * 50)

    return 0 if fail_count == 0 else 1
