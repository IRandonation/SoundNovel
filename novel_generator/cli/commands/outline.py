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
        # 加载配置
        config = load_config(args.config)
        print_info("配置加载完成")
        
        # 验证配置
        settings = Settings(config)
        settings.validate()
        
        # 加载核心设定和整体大纲
        core_setting = load_core_setting()
        overall_outline = load_overall_outline()
        
        if not core_setting:
            print_error("核心设定为空，请先填写 01_source/core_setting.yaml")
            return 1
        
        if not overall_outline:
            print_error("整体大纲为空，请先填写 01_source/overall_outline.yaml")
            return 1
        
        print_info("核心设定和整体大纲加载完成")
        
        # 确保输出目录存在
        ensure_directories()
        
        # 创建大纲生成器
        batch_generator = BatchOutlineGenerator(config)
        outline_gen = OutlineGenerator(config)
        
        # 自动提取总章节数
        total_chapters = outline_gen.extract_total_chapters(overall_outline)
        print_info(f"检测到总章节数: {total_chapters}")
        
        # 确定生成范围
        start_ch = args.start if args.start else 1
        end_ch = args.end if args.end else total_chapters
        
        if start_ch < 1 or end_ch > total_chapters or start_ch > end_ch:
            print_error(f"无效的章节范围: {start_ch}-{end_ch} (有效范围: 1-{total_chapters})")
            return 1
        
        print_info(f"生成章节范围: 第{start_ch}章 - 第{end_ch}章")
        print_info(f"批次大小: {args.batch_size}")
        
        # 生成大纲
        def progress_callback(current: int, total: int, message: str):
            percent = min(current / total, 1.0) if total > 0 else 0
            print(f"\r  进度: [{int(percent*100)}%] {message}", end='', flush=True)
        
        outline = batch_generator.generate_batch_outline(
            core_setting=core_setting,
            overall_outline=overall_outline,
            total_chapters=total_chapters,
            batch_size=args.batch_size,
            start_chapter_idx=start_ch,
            end_chapter_idx=end_ch,
            progress_callback=progress_callback
        )
        
        print()  # 换行
        
        # 确定输出文件路径
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = get_project_root() / "02_outline" / f"chapter_outline_{start_ch:03d}-{end_ch:03d}.yaml"
        
        # 保存大纲
        batch_generator.save_batch_outline(outline, str(output_path))
        
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
