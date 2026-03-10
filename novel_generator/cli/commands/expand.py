"""
章节扩写命令

将章节大纲扩写为完整的小说正文
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from novel_generator.core.chapter_expander import ChapterExpander
from novel_generator.core.sliding_window import ContextManager
from novel_generator.config.settings import Settings
from novel_generator.utils.multi_model_client import MultiModelClient
from novel_generator.utils.common import (
    load_config, load_style_guide, load_yaml_file,
    get_project_root, get_latest_outline_file, parse_chapter_range,
    format_chapter_key, get_chapter_data, ensure_directories
)
from novel_generator.cli.utils import (
    print_success, print_error, print_info, print_warning,
    setup_cli_logging
)


def run(args: argparse.Namespace) -> int:
    """
    执行章节扩写
    
    Args:
        args: 命令行参数
        
    Returns:
        int: 退出码
    """
    logger = setup_cli_logging()
    
    print_info("🚀 开始章节扩写...")
    
    try:
        # 加载配置
        config = load_config(args.config)
        print_info("配置加载完成")
        
        # 验证配置
        settings = Settings(config)
        settings.validate()
        
        # 加载风格指导
        style_guide = load_style_guide()
        if style_guide:
            print_info("风格指导加载完成")
        
        # 确定大纲文件
        if args.outline_file:
            outline_file = Path(args.outline_file)
        else:
            outline_file = get_latest_outline_file()
        
        if not outline_file or not outline_file.exists():
            print_error("未找到大纲文件，请先生成大纲或指定--outline-file")
            return 1
        
        print_info(f"使用大纲文件: {outline_file}")
        
        # 加载大纲
        outline_data = load_yaml_file(outline_file)
        if not outline_data:
            print_error("大纲文件为空")
            return 1
        
        # 解析章节范围
        min_ch, max_ch = parse_chapter_range(outline_data)
        
        # 确定要扩写的章节
        if args.chapter:
            # 单章节模式
            chapters_to_expand = [args.chapter]
        elif args.start and args.end:
            # 范围模式
            if args.start < min_ch or args.end > max_ch:
                print_error(f"章节范围 {args.start}-{args.end} 超出大纲范围 ({min_ch}-{max_ch})")
                return 1
            chapters_to_expand = list(range(args.start, args.end + 1))
        else:
            # 交互模式
            print_info(f"大纲包含章节: 第{min_ch}章 - 第{max_ch}章")
            print()
            print("选择扩写模式:")
            print("  1. 扩写单个章节")
            print("  2. 扩写指定范围")
            print("  3. 扩写所有章节")
            
            choice = input("请输入选择 (1-3): ").strip()
            
            if choice == "1":
                ch = input("请输入章节号: ").strip()
                chapters_to_expand = [int(ch)]
            elif choice == "2":
                start = input("起始章节: ").strip()
                end = input("结束章节: ").strip()
                chapters_to_expand = list(range(int(start), int(end) + 1))
            elif choice == "3":
                chapters_to_expand = list(range(min_ch, max_ch + 1))
            else:
                print_error("无效选择")
                return 1
        
        # 验证章节范围
        for ch in chapters_to_expand:
            if ch < min_ch or ch > max_ch:
                print_error(f"章节 {ch} 超出范围 ({min_ch}-{max_ch})")
                return 1
        
        print_info(f"将扩写 {len(chapters_to_expand)} 个章节: {chapters_to_expand[0]}-{chapters_to_expand[-1]}")
        
        # 初始化多模型客户端
        client = MultiModelClient(config)
        print_info(f"当前使用模型: {client.get_current_model()}")
        
        # 创建扩写器和上下文管理器
        expander = ChapterExpander(config, client)
        context_manager = ContextManager(config, client)
        
        # 确保草稿目录存在
        draft_dir = config['paths'].get('draft_dir', '03_draft/')
        if not Path(draft_dir).is_absolute():
            draft_dir = str(get_project_root() / draft_dir)
        Path(draft_dir).mkdir(parents=True, exist_ok=True)
        
        # 扩写章节
        success_count = 0
        fail_count = 0
        
        for i, ch_num in enumerate(chapters_to_expand, 1):
            print()
            print_info(f"[{i}/{len(chapters_to_expand)}] 正在扩写第 {ch_num} 章...")
            
            try:
                # 准备上下文
                previous_context, needs_repair = context_manager.prepare_context(
                    current_chapter=ch_num,
                    outline_file=str(outline_file),
                    draft_dir=draft_dir
                )
                
                if needs_repair:
                    print_warning("检测到上下文断裂，已自动修复")
                
                # 获取章节数据
                ch_data = get_chapter_data(outline_data, ch_num)
                if not ch_data:
                    print_error(f"大纲中找不到第 {ch_num} 章的数据")
                    fail_count += 1
                    continue
                
                # 扩写章节
                content = expander.expand_chapter(
                    chapter_num=ch_num,
                    chapter_outline=ch_data,
                    previous_context=previous_context,
                    style_guide=style_guide
                )
                
                # 保存章节
                expander.save_chapter(ch_num, content, draft_dir)
                
                print_success(f"第 {ch_num} 章扩写完成")
                success_count += 1
                
            except Exception as e:
                print_error(f"扩写第 {ch_num} 章失败: {e}")
                fail_count += 1
                continue
        
        # 输出总结
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
