"""
regenerate 命令

重生成指定范围的章节，自动处理级联传播。
"""

import argparse
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from novel_generator.core.chapter_expander import (
    ChapterExpander,
    _build_outline_context,
    _build_draft_context,
)
from novel_generator.utils.multi_model_client import MultiModelClient
from novel_generator.utils.common import (
    load_yaml_file,
    get_latest_outline_file,
    get_chapter_data,
)
from novel_generator.cli.utils import (
    print_success, print_error, print_info, print_warning,
    confirm_action, get_config_manager,
)
from novel_generator.core.ai_roles import AIRole


def _parse_chapter_range(range_str: str):
    """解析 '12-14' 或 '15' 格式的章节范围"""
    if '-' in range_str:
        parts = range_str.split('-')
        return int(parts[0].strip()), int(parts[1].strip())
    return int(range_str.strip()), int(range_str.strip())


def run(args: argparse.Namespace) -> int:
    config_manager = get_config_manager(novel_id=getattr(args, 'novel_id', None))

    # 解析章节范围
    if args.chapters:
        start_ch, end_ch = _parse_chapter_range(args.chapters)
    elif args.chapter:
        start_ch = end_ch = args.chapter
    else:
        print_error("请指定 --chapters 或 --chapter")
        return 1

    # 正文重生成
    config = config_manager.get_api_config()
    gen_config = config_manager.get_generation_config()
    outline_window = gen_config.get("outline_window", 30)
    draft_window = gen_config.get("draft_window", 10)

    # Get outline file from state
    state = config_manager.state
    outline_file = state.get("outline_file", "")
    if not outline_file:
        outline_file = get_latest_outline_file()

    if not outline_file:
        print_error("未找到大纲文件")
        return 1

    outline_data = load_yaml_file(Path(outline_file))
    if not outline_data:
        print_error("大纲文件为空")
        return 1

    # 检测级联范围
    cascade_end = end_ch + draft_window
    affected = list(range(end_ch + 1, cascade_end + 1))

    # Get novel paths
    novel_paths = config_manager.get_novel_paths()
    draft_dir = novel_paths["draft_dir"]

    existing_affected = []
    for ch in affected:
        if (draft_dir / f"第{ch:04d}章.txt").exists():
            existing_affected.append(ch)

    if existing_affected:
        print_warning(f"重生成第{start_ch}-{end_ch}章将影响第{existing_affected[0]}-{existing_affected[-1]}章（上下文窗口={draft_window}）")

        if not args.yes:
            cascade_confirm = confirm_action("是否级联重生成所有受影响章节?", default=True)
            if cascade_confirm:
                end_ch = existing_affected[-1]
                print_info(f"将级联重生成第{start_ch}-{end_ch}章")
            else:
                print_info(f"仅重生成第{start_ch}-{end_ch}章，受影响章节将标记为 dirty")
                for ch in existing_affected:
                    config_manager.set_chapter_state(ch, "dirty")
    else:
        print_info(f"重生成第{start_ch}-{end_ch}章（无后续章节受影响）")

    # 执行重生成
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

    success_count = 0
    fail_count = 0
    chapters_to_gen = list(range(start_ch, end_ch + 1))

    for i, ch_num in enumerate(chapters_to_gen, 1):
        print()
        print_info(f"[{i}/{len(chapters_to_gen)}] 正在重生成第 {ch_num} 章...")

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

            print_success(f"第 {ch_num} 章重生成完成 ({len(content)}字)")
            success_count += 1

        except Exception as e:
            print_error(f"重生成第 {ch_num} 章失败: {e}")
            fail_count += 1
            continue

    # 获取实际使用的 role_config
    role_config = expander.ai_role_manager.get_role_config(AIRole.GENERATOR)
    model_info = f"{role_config.provider}/{role_config.model}" if role_config.model else role_config.provider

    config_manager.add_session_record(
        action="regenerate",
        start_chapter=start_ch,
        end_chapter=end_ch,
        model_used=model_info,
        success=(fail_count == 0),
    )

    print()
    print_info("=" * 50)
    print_info(f"重生成完成: 成功 {success_count} 章, 失败 {fail_count} 章")
    print_info(f"大纲窗口: {outline_window} | 正文窗口: {draft_window}")
    print_info("=" * 50)

    return 0 if fail_count == 0 else 1
