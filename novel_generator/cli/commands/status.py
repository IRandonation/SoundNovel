"""
状态查看命令

显示当前项目的生成进度和配置状态
"""

import argparse
from pathlib import Path
from typing import Optional

project_root = Path(__file__).parent.parent.parent.parent

from novel_generator.config.session import SessionManager
from novel_generator.cli.utils import print_success, print_error, print_info, print_warning


def run(args: argparse.Namespace) -> int:
    session_manager = SessionManager(str(Path.cwd()))
    status = session_manager.get_status_summary()
    
    print()
    print_info("=" * 50)
    print_info("📊 项目状态")
    print_info("=" * 50)
    print()
    
    print(f"  📁 项目名称: {status['project_name']}")
    print(f"  📅 创建时间: {status['created_at'] or '未初始化'}")
    print(f"  🔄 更新时间: {status['updated_at'] or '未初始化'}")
    print()
    
    print_info("--- API 配置 ---")
    provider_names = {"zhipu": "智谱 AI", "doubao": "豆包", "ark": "Ark"}
    print(f"  🤖 当前服务商: {provider_names.get(status['api_provider'], status['api_provider'])}")
    print(f"  🔑 API 状态: {'已配置 ✅' if status['api_configured'] else '未配置 ❌'}")
    print()
    
    print_info("--- 生成进度 ---")
    total = status['total_chapters']
    last_draft = status['last_draft']
    last_outline = status['last_outline']
    
    if total > 0:
        progress = (last_draft / total * 100) if total > 0 else 0
        print(f"  📖 总章节: {total} 章")
        print(f"  📝 大纲进度: {last_outline} / {total} 章 ({last_outline/total*100:.1f}%)")
        print(f"  ✍️  草稿进度: {last_draft} / {total} 章 ({progress:.1f}%)")
        
        if last_draft < total:
            next_chapter = last_draft + 1
            print()
            print_info(f"💡 续写建议: 运行 'soundnovel continue' 从第 {next_chapter} 章继续")
        else:
            print()
            print_success("🎉 所有章节已完成！")
    else:
        print(f"  📝 最后生成大纲: 第 {last_outline} 章" if last_outline > 0 else "  📝 大纲: 未生成")
        print(f"  ✍️  最后生成草稿: 第 {last_draft} 章" if last_draft > 0 else "  ✍️  草稿: 未生成")
    
    if status['outline_file']:
        print(f"  📄 大纲文件: {status['outline_file']}")
    
    print()
    print_info(f"  📋 会话记录: {status['session_count']} 条")
    
    recent = session_manager.get_recent_sessions(5)
    if recent:
        print()
        print_info("--- 最近会话 ---")
        for s in recent:
            status_icon = "✅" if s.success else "❌"
            chapters_str = f"第{s.chapters[0]}-{s.chapters[1]}章" if s.chapters else ""
            print(f"  {status_icon} [{s.date}] {s.action} {chapters_str}")
    
    print()
    print_info("=" * 50)
    
    return 0