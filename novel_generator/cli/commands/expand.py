"""
章节扩写命令

将章节大纲扩写为完整的小说正文
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Tuple

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from novel_generator.core.chapter_expander import ChapterExpander
from novel_generator.config.settings import Settings
from novel_generator.config.config_manager import ConfigManager
from novel_generator.utils.multi_model_client import MultiModelClient
from novel_generator.utils.common import (
    load_config,
    load_style_guide,
    load_yaml_file,
    get_project_root,
    get_latest_outline_file,
    parse_chapter_range,
    format_chapter_key,
    get_chapter_data,
    ensure_directories,
)
from novel_generator.cli.utils import (
    print_success,
    print_error,
    print_info,
    print_warning,
    setup_cli_logging,
)


def run(args: argparse.Namespace) -> int:
    logger = setup_cli_logging()

    print_info("🚀 开始章节扩写...")

    try:
        config_manager = ConfigManager(str(Path.cwd()))

        if args.from_last:
            continue_info = config_manager.get_continue_info("draft")
            if continue_info["last_chapter"] == 0:
                print_error("没有找到已生成的章节，无法续写")
                return 1

            start_chapter = continue_info["next_chapter"]
            total_chapters = continue_info["total_chapters"]

            if args.end:
                end_chapter = args.end
            elif total_chapters > 0:
                end_chapter = total_chapters
            else:
                print_error("未设置总章节数，请使用 --end 指定结束章节")
                return 1

            print_info(f"续写模式: 从第 {start_chapter} 章开始")
        else:
            start_chapter = None
            end_chapter = None

        config = config_manager.get_api_config()
        print_info("配置加载完成")

        settings = Settings(config)
        settings.validate()

        style_guide = load_style_guide()
        if style_guide:
            print_info("风格指导加载完成")

        outline_file_from_session = config_manager.state.generation_state.outline_file

        if args.outline_file:
            outline_file = Path(args.outline_file)
        elif outline_file_from_session:
            outline_file = Path(outline_file_from_session)
        else:
            outline_file = get_latest_outline_file()

        if not outline_file or not outline_file.exists():
            print_error("未找到大纲文件，请先生成大纲或指定--outline-file")
            return 1

        print_info(f"使用大纲文件: {outline_file}")

        outline_data = load_yaml_file(outline_file)
        if not outline_data:
            print_error("大纲文件为空")
            return 1

        min_ch, max_ch = parse_chapter_range(outline_data)

        if args.from_last:
            chapters_to_expand = list(range(start_chapter, end_chapter + 1))
        elif args.chapter:
            chapters_to_expand = [args.chapter]
        elif args.start and args.end:
            if args.start < min_ch or args.end > max_ch:
                print_error(
                    f"章节范围 {args.start}-{args.end} 超出大纲范围 ({min_ch}-{max_ch})"
                )
                return 1
            chapters_to_expand = list(range(args.start, args.end + 1))
        else:
            print_info(f"大纲包含章节: 第{min_ch}章 - 第{max_ch}章")
            print()
            print("选择扩写模式:")
            print("  1. 扩写单个章节")
            print("  2. 扩写指定范围")
            print("  3. 扩写所有章节")
            print("  4. 从上次结束处续写")

            choice = input("请输入选择 (1-4): ").strip()

            if choice == "1":
                ch = input("请输入章节号: ").strip()
                chapters_to_expand = [int(ch)]
            elif choice == "2":
                start = input("起始章节: ").strip()
                end = input("结束章节: ").strip()
                chapters_to_expand = list(range(int(start), int(end) + 1))
            elif choice == "3":
                chapters_to_expand = list(range(min_ch, max_ch + 1))
            elif choice == "4":
                continue_info = config_manager.get_continue_info("draft")
                if continue_info["last_chapter"] == 0:
                    print_warning("没有找到已生成的章节，将从第1章开始")
                    chapters_to_expand = list(range(min_ch, max_ch + 1))
                else:
                    start_chapter = continue_info["next_chapter"]
                    chapters_to_expand = list(range(start_chapter, max_ch + 1))
                    print_info(f"从第 {start_chapter} 章继续")
            else:
                print_error("无效选择")
                return 1

        for ch in chapters_to_expand:
            if ch < min_ch or ch > max_ch:
                print_error(f"章节 {ch} 超出范围 ({min_ch}-{max_ch})")
                return 1

        print_info(
            f"将扩写 {len(chapters_to_expand)} 个章节: {chapters_to_expand[0]}-{chapters_to_expand[-1]}"
        )

        client = MultiModelClient(config)
        print_info(f"当前使用模型: {client.get_current_model()}")

        expander = ChapterExpander(config, client)

        draft_dir = config.get("paths", {}).get("draft_dir", "03_draft/")
        if not Path(draft_dir).is_absolute():
            draft_dir = str(Path.cwd() / draft_dir)
        Path(draft_dir).mkdir(parents=True, exist_ok=True)

        gen_config = config_manager.get_generation_config()
        context_before_full = gen_config.get("context_before_full", 10)
        context_after_full = gen_config.get("context_after_full", 5)

        def get_existing_chapters(draft_path: str) -> list:
            existing = []
            draft_path_obj = Path(draft_path)
            if draft_path_obj.exists():
                import re

                for f in draft_path_obj.glob("第*章.txt"):
                    match = re.search(r"第(\d+)章", f.name)
                    if match:
                        existing.append(int(match.group(1)))
            return sorted(existing)

        def load_chapter_content(ch_num: int, draft_path: str) -> str:
            file_path = Path(draft_path) / f"第{ch_num:04d}章.txt"
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            return ""

        existing_chapters = get_existing_chapters(draft_dir)
        context_parts = []

        success_count = 0
        fail_count = 0
        actual_start = chapters_to_expand[0]
        end_chapter = chapters_to_expand[-1]

        for i, ch_num in enumerate(chapters_to_expand, 1):
            print()
            print_info(f"[{i}/{len(chapters_to_expand)}] 正在扩写第 {ch_num} 章...")

            try:
                ch_data = get_chapter_data(outline_data, ch_num)
                if not ch_data:
                    print_error(f"大纲中找不到第 {ch_num} 章的数据")
                    fail_count += 1
                    continue

                previous_full_count = min(len(context_parts), context_before_full)
                previous_context = (
                    "\n\n".join(context_parts[-previous_full_count:])
                    if context_parts
                    else ""
                )

                after_context = ""
                if ch_num == end_chapter:
                    after_chapters = [
                        ch for ch in existing_chapters if ch > end_chapter
                    ]
                    if after_chapters:
                        take_count = min(len(after_chapters), context_after_full)
                        after_chapters_to_read = after_chapters[:take_count]

                        after_parts = []
                        for ch in after_chapters_to_read:
                            content = load_chapter_content(ch, draft_dir)
                            if content:
                                after_parts.append(f"【第{ch}章】\n{content}")

                        if after_parts:
                            after_context = "\n\n".join(after_parts)
                            print_info(
                                f"检测到后文，纳入第{after_chapters_to_read[0]}-{after_chapters_to_read[-1]}章作为上下文"
                            )

                result = expander.expand_chapter(
                    chapter_num=ch_num,
                    chapter_outline=ch_data,
                    previous_context=previous_context,
                    after_context=after_context,
                    style_guide=style_guide,
                )

                content = result[0] if isinstance(result, tuple) else result

                expander.save_chapter(ch_num, content, draft_dir)

                context_parts.append(f"【第{ch_num}章】\n{content}")

                config_manager.update_progress(
                    "draft", actual_start, ch_num, str(outline_file)
                )

                print_success(f"第 {ch_num} 章扩写完成")
                success_count += 1

            except Exception as e:
                print_error(f"扩写第 {ch_num} 章失败: {e}")
                fail_count += 1
                continue

        config_manager.add_session_record(
            action="expand",
            start_chapter=chapters_to_expand[0],
            end_chapter=chapters_to_expand[-1],
            model_used=client.get_current_model(),
            success=(fail_count == 0),
        )

        print()
        print_info("=" * 50)
        print_info("扩写完成！")
        print_info(f"成功: {success_count} 章")
        if fail_count > 0:
            print_warning(f"失败: {fail_count} 章")
        print_info(f"草稿位置: {draft_dir}")
        print_info("=" * 50)

        return 0 if fail_count == 0 else 1

    except FileNotFoundError as e:
        print_error(f"文件未找到: {e}")
        return 1
    except KeyboardInterrupt:
        print()
        print_warning("操作已取消")
        return 130
    except Exception as e:
        print_error(f"扩写失败: {e}")
        import traceback

        traceback.print_exc()
        return 1
