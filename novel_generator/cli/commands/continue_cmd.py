"""
续写命令

从上次结束的章节继续生成
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from novel_generator.config.session import SessionManager
from novel_generator.core.chapter_expander import ChapterExpander
from novel_generator.utils.multi_model_client import MultiModelClient
from novel_generator.utils.common import (
    load_style_guide, load_yaml_file,
    get_project_root, get_latest_outline_file,
    get_chapter_data, ensure_directories
)
from novel_generator.cli.utils import (
    print_success, print_error, print_info, print_warning,
    setup_cli_logging
)


def run(args: argparse.Namespace) -> int:
    logger = setup_cli_logging()
    
    session_manager = SessionManager(str(Path.cwd()))
    
    continue_info = session_manager.get_continue_info("draft")
    
    if not continue_info["can_continue"] and continue_info["last_chapter"] == 0:
        print_error("没有找到已生成的章节，请先运行 'soundnovel expand' 生成初始章节")
        return 1
    
    start_chapter = continue_info["next_chapter"]
    total_chapters = continue_info["total_chapters"]
    
    if args.end:
        end_chapter = args.end
    elif total_chapters > 0:
        end_chapter = total_chapters
    else:
        end_chapter = start_chapter + 10
        print_warning(f"未设置总章节数，默认生成 {end_chapter - start_chapter + 1} 章")
        confirm = input(f"将从第 {start_chapter} 章生成到第 {end_chapter} 章，确认? [Y/n]: ").strip().lower()
        if confirm in ('n', 'no'):
            print_info("操作已取消")
            return 0
    
    if total_chapters > 0 and end_chapter > total_chapters:
        print_warning(f"结束章节 {end_chapter} 超过总章节数 {total_chapters}，已调整为 {total_chapters}")
        end_chapter = total_chapters
    
    print_info(f"续写模式: 第 {start_chapter} 章 - 第 {end_chapter} 章")
    print_info(f"当前进度: {continue_info['last_chapter']} / {total_chapters if total_chapters > 0 else '?'} 章")
    print()
    
    config = session_manager.get_api_config()
    
    outline_file = continue_info.get("outline_file")
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
    
    style_guide = load_style_guide()
    
    client = MultiModelClient(config)
    print_info(f"当前使用模型: {client.get_current_model()}")
    
    expander = ChapterExpander(config, client)
    
    draft_dir = config.get('paths', {}).get('draft_dir', '03_draft/')
    if not Path(draft_dir).is_absolute():
        draft_dir = str(Path.cwd() / draft_dir)
    Path(draft_dir).mkdir(parents=True, exist_ok=True)
    
    context_window = config.get('novel_generation', {}).get('context_chapters', 10)
    context_parts = []
    
    success_count = 0
    fail_count = 0
    
    for i, ch_num in enumerate(range(start_chapter, end_chapter + 1), 1):
        print()
        print_info(f"[{i}/{end_chapter - start_chapter + 1}] 正在扩写第 {ch_num} 章...")
        
        try:
            ch_data = get_chapter_data(outline_data, ch_num)
            if not ch_data:
                print_error(f"大纲中找不到第 {ch_num} 章的数据")
                fail_count += 1
                continue
            
            previous_context = "\n\n".join(context_parts[-context_window:]) if context_parts else ""
            
            result = expander.expand_chapter(
                chapter_num=ch_num,
                chapter_outline=ch_data,
                previous_context=previous_context,
                style_guide=style_guide
            )
            
            content = result[0] if isinstance(result, tuple) else result
            
            expander.save_chapter(ch_num, content, draft_dir)
            
            context_parts.append(f"【第{ch_num}章摘要】\n{content[:500]}...")
            
            session_manager.update_progress("draft", start_chapter, ch_num, str(outline_file))
            
            print_success(f"第 {ch_num} 章扩写完成")
            success_count += 1
            
        except Exception as e:
            print_error(f"扩写第 {ch_num} 章失败: {e}")
            fail_count += 1
            continue
    
    session_manager.add_session_record(
        action="expand",
        start_chapter=start_chapter,
        end_chapter=end_chapter,
        model_used=client.get_current_model(),
        success=(fail_count == 0)
    )
    
    print()
    print_info("=" * 50)
    print_info("续写完成！")
    print_info(f"成功: {success_count} 章")
    if fail_count > 0:
        print_warning(f"失败: {fail_count} 章")
    print_info(f"草稿位置: {draft_dir}")
    
    new_info = session_manager.get_continue_info("draft")
    if new_info["can_continue"]:
        print_info(f"继续续写: 运行 'soundnovel continue'")
    else:
        print_success("所有章节已完成！")
    
    print_info("=" * 50)
    
    return 0 if fail_count == 0 else 1