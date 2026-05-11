"""
状态查看命令

显示当前小说项目的生成进度、配置状态和章节状态。
"""

import argparse
from pathlib import Path
from typing import Optional

project_root = Path(__file__).parent.parent.parent.parent

from novel_generator.cli.utils import (
    print_success,
    print_error,
    print_info,
    print_warning,
    get_config_manager,
)


def run(args: argparse.Namespace) -> int:
    """运行状态命令"""
    try:
        config_manager = get_config_manager(novel_id=getattr(args, 'novel_id', None))
    except ValueError as e:
        print_error(str(e))
        print_info("请先运行 'soundnovel novel create' 创建小说项目")
        return 1
    except Exception as e:
        print_error(f"加载配置失败: {e}")
        return 1

    status = config_manager.get_status_summary()

    print()
    print_info("=" * 50)
    print_info(f"小说状态: {status['project_name']}")
    print_info("=" * 50)
    print()

    print(f"  小说ID: {config_manager.novel_id}")
    print(f"  创建时间: {status['created_at'] or '未记录'}")
    print(f"  更新时间: {status['updated_at'] or '未记录'}")
    print()

    print_info("--- API 配置 ---")
    print(f"  API 状态: {'已配置' if status['api_configured'] else '未配置'}")
    print()

    print_info("--- 生成进度 ---")
    total = status["total_chapters"]
    last_draft = status["last_draft"]
    last_outline = status["last_outline"]

    if total > 0:
        progress = (last_draft / total * 100) if total > 0 else 0
        print(f"  总章节: {total} 章")
        print(
            f"  大纲进度: {last_outline} / {total} 章 ({last_outline / total * 100:.1f}%)"
        )
        print(f"  草稿进度: {last_draft} / {total} 章 ({progress:.1f}%)")

        if last_draft < total:
            next_chapter = last_draft + 1
            print()
            print_info(f"续写建议: 运行 'soundnovel cli continue' 从第 {next_chapter} 章继续")
        else:
            print()
            print_success("所有章节已完成！")
    else:
        print(
            f"  最后生成大纲: 第 {last_outline} 章"
            if last_outline > 0
            else "  大纲: 未生成"
        )
        print(
            f"  最后生成草稿: 第 {last_draft} 章"
            if last_draft > 0
            else "  草稿: 未生成"
        )

    if status["outline_file"]:
        print(f"  大纲文件: {status['outline_file']}")

    # 章节状态一览
    state = config_manager.state
    chapter_states = state.get("chapter_states", {})
    if chapter_states:
        print()
        print_info("--- 章节状态 ---")

        clean_count = sum(1 for v in chapter_states.values() if v == "clean")
        dirty_count = sum(1 for v in chapter_states.values() if v == "dirty")
        cosmetic_count = sum(1 for v in chapter_states.values() if v == "cosmetic")

        print(f"  已追踪: {len(chapter_states)} 章")
        print(f"  [C]lean: {clean_count} | [D]irty: {dirty_count} | Cosmetic[O]: {cosmetic_count}")

        # 按章节号排序显示
        sorted_chapters = sorted(chapter_states.keys(), key=lambda x: int(x))
        state_chars = {"clean": "C", "dirty": "D", "cosmetic": "O"}

        # 每10章一行
        if sorted_chapters:
            print()
            for row_start in range(0, len(sorted_chapters), 10):
                row_chapters = sorted_chapters[row_start:row_start + 10]
                row_parts = []
                for ch in row_chapters:
                    s = chapter_states.get(ch, "?")
                    row_parts.append(f"{ch}:{state_chars.get(s, '?')}")
                print(f"  {'  '.join(row_parts)}")

    print()
    print_info("=" * 50)
    return 0
