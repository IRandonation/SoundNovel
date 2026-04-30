"""
状态查看命令

显示当前项目的生成进度、配置状态和章节状态。
"""

import argparse
from pathlib import Path
from typing import Optional

project_root = Path(__file__).parent.parent.parent.parent

from novel_generator.config.session import SessionManager
from novel_generator.cli.utils import (
    print_success,
    print_error,
    print_info,
    print_warning,
)


def run(args: argparse.Namespace) -> int:
    session_manager = SessionManager(str(Path.cwd()))
    status = session_manager.get_status_summary()

    print()
    print_info("=" * 50)
    print_info("项目状态")
    print_info("=" * 50)
    print()

    print(f"  项目名称: {status['project_name']}")
    print(f"  创建时间: {status['created_at'] or '未初始化'}")
    print(f"  更新时间: {status['updated_at'] or '未初始化'}")
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
            print_info(f"续写建议: 运行 'soundnovel continue' 从第 {next_chapter} 章继续")
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
    state_summary = session_manager.get_chapter_states_summary()
    if state_summary["total_tracked"] > 0:
        print()
        print_info("--- 章节状态 ---")
        print(f"  已追踪: {state_summary['total_tracked']} 章")
        print(f"  [C]lean: {state_summary['clean']} | [D]irty: {state_summary['dirty']} | Cosmetic[O]: {state_summary['cosmetic']}")

        # 按章节号排序显示
        states = state_summary["states"]
        sorted_chapters = sorted(states.keys(), key=lambda x: int(x))
        state_chars = {"clean": "C", "dirty": "D", "cosmetic": "O"}

        # 每10章一行
        if sorted_chapters:
            print()
            for row_start in range(0, len(sorted_chapters), 10):
                row_chapters = sorted_chapters[row_start:row_start + 10]
                row_parts = []
                for ch in row_chapters:
                    s = states.get(ch, "?")
                    row_parts.append(f"{ch}:{state_chars.get(s, '?')}")
                print(f"  {'  '.join(row_parts)}")

        # 级联警告
        dirty_chapters = [int(k) for k, v in states.items() if v == "dirty"]
        if dirty_chapters:
            first_dirty = min(dirty_chapters)
            print()
            print_warning(f"第一个 dirty 章节: 第{first_dirty}章")
            print_info(f"建议运行: soundnovel continue --cascade  或  soundnovel regenerate --chapters {first_dirty}-...")

    print()
    print_info(f"  会话记录: {status['session_count']} 条")

    recent = session_manager.get_recent_sessions(5)
    if recent:
        print()
        print_info("--- 最近会话 ---")
        for s in recent:
            status_icon = "+" if s.success else "X"
            chapters_str = f"第{s.chapters[0]}-{s.chapters[1]}章" if s.chapters else ""
            print(f"  [{status_icon}] [{s.date}] {s.action} {chapters_str}")

    print()
    print_info("=" * 50)

    return 0
