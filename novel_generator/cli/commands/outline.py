"""
大纲生成命令

基于核心设定和整体大纲生成详细章节大纲
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from novel_generator.core.batch_outline_generator import BatchOutlineGenerator
from novel_generator.core.outline_generator import OutlineGenerator
from novel_generator.config.settings import Settings
from novel_generator.config.config_manager import ConfigManager
from novel_generator.utils.common import (
    load_config, load_core_setting, load_overall_outline,
    get_project_root, ensure_directories
)
from novel_generator.cli.utils import (
    print_success, print_error, print_info, print_warning,
    setup_cli_logging
)


def run(args: argparse.Namespace) -> int:
    """
    执行大纲生成
    
    Args:
        args: 命令行参数
        
    Returns:
        int: 退出码
    """
    logger = setup_cli_logging()
    
    print_info("🚀 开始生成章节大纲...")
    
    try:
        config = load_config(args.config)
        print_info("配置加载完成")
        
        config_manager = ConfigManager(str(get_project_root()))
        gen_config = config_manager.state.generation_config
        
        settings = Settings(config)
        settings.validate()
        
        core_setting = load_core_setting()
        overall_outline = load_overall_outline()
        
        if not core_setting:
            print_error("核心设定为空，请先填写 01_source/core_setting.yaml")
            return 1
        
        if not overall_outline:
            print_error("整体大纲为空，请先填写 01_source/overall_outline.yaml")
            return 1
        
        print_info("核心设定和整体大纲加载完成")
        
        ensure_directories()
        
        batch_generator = BatchOutlineGenerator(config)
        outline_gen = OutlineGenerator(config)
        
        total_chapters = outline_gen.extract_total_chapters(overall_outline)
        print_info(f"检测到总章节数: {total_chapters}")
        
        start_ch = args.start if args.start else 1
        end_ch = args.end if args.end else total_chapters
        
        batch_size = args.batch_size if args.batch_size else gen_config.batch_size
        
        if start_ch < 1 or end_ch > total_chapters or start_ch > end_ch:
            print_error(f"无效的章节范围: {start_ch}-{end_ch} (有效范围: 1-{total_chapters})")
            return 1
        
        print_info(f"生成章节范围: 第{start_ch}章 - 第{end_ch}章")
        print_info(f"批次大小: {batch_size} (可通过 session.json 配置)")
        print_info(f"上下文章节数: {gen_config.context_chapters}")
        print_info(f"目标字数: {gen_config.default_word_count}")
        
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = get_project_root() / "02_outline" / f"chapter_outline_{start_ch:03d}-{end_ch:03d}.yaml"
        
        print_info(f"输出文件: {output_path}")
        print_info("💾 增量保存已启用（每批次自动保存）")
        
        def progress_callback(current: int, total: int, message: str):
            percent = min(current / total, 1.0) if total > 0 else 0
            print(f"\r  进度: [{int(percent*100)}%] {message}", end='', flush=True)
        
        outline = batch_generator.generate_batch_outline(
            core_setting=core_setting,
            overall_outline=overall_outline,
            total_chapters=total_chapters,
            batch_size=batch_size,
            start_chapter_idx=start_ch,
            end_chapter_idx=end_ch,
            progress_callback=progress_callback,
            output_path=str(output_path),
            incremental_save=True
        )
        
        print()
        
        print_success(f"大纲生成完成！已保存至: {output_path}")
        print()
        print_info("📋 下一步操作:")
        print("  1. 查看并编辑生成的大纲文件")
        print("  2. 运行 'soundnovel expand --chapter 1' 开始扩写章节")
        
        return 0
        
    except FileNotFoundError as e:
        print_error(f"文件未找到: {e}")
        return 1
    except Exception as e:
        print_error(f"生成大纲失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
