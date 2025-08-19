"""
草稿合并脚本
将03_draft目录下的所有章节文件合并为一个完整的txt文件
"""

import os
import sys
import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from novel_generator.utils.file_handler import FileHandler
from novel_generator.config.settings import Settings, create_default_config


def setup_logging(log_file: str = "06_log/novel_generator.log"):
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def load_config(config_path: str = "05_script/config.json") -> Dict[str, Any]:
    """加载配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"❌ 加载配置文件失败: {e}")
        print("🔄 使用默认配置...")
        return create_default_config()


def get_chapter_files(draft_dir: str) -> List[Tuple[int, str]]:
    """
    获取draft目录下的所有章节文件
    
    Args:
        draft_dir: 草稿目录路径
        
    Returns:
        List[Tuple[int, str]]: 章节号和文件路径的列表
    """
    try:
        draft_path = Path(draft_dir)
        if not draft_path.exists():
            print(f"❌ 草稿目录不存在: {draft_dir}")
            return []
        
        chapter_files = []
        # 匹配 chapter_XX.md 格式的文件
        pattern = re.compile(r'chapter_(\d+)\.md$')
        
        for file_path in draft_path.glob("chapter_*.md"):
            match = pattern.match(file_path.name)
            if match:
                chapter_num = int(match.group(1))
                chapter_files.append((chapter_num, str(file_path)))
        
        # 按章节号排序
        chapter_files.sort(key=lambda x: x[0])
        
        return chapter_files
        
    except Exception as e:
        print(f"❌ 获取章节文件失败: {e}")
        return []


def read_chapter_content(file_path: str) -> str:
    """
    读取章节内容
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: 章节内容
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 移除Markdown标题的#符号，转换为纯文本格式
        lines = content.split('\n')
        processed_lines = []
        
        for line in lines:
            if line.startswith('# '):
                # 将一级标题转换为居中的章节标题
                title = line[2:].strip()
                processed_lines.append(f"\n{'=' * 50}")
                processed_lines.append(f"{title.center(50)}")
                processed_lines.append(f"{'=' * 50}\n")
            elif line.startswith('## '):
                # 将二级标题转换为加粗标题
                title = line[3:].strip()
                processed_lines.append(f"\n【{title}】\n")
            elif line.startswith('### '):
                # 将三级标题转换为普通标题
                title = line[4:].strip()
                processed_lines.append(f"\n{title}\n")
            else:
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
        
    except Exception as e:
        print(f"❌ 读取章节内容失败 {file_path}: {e}")
        return ""


def create_novel_content(chapter_files: List[Tuple[int, str]], 
                        include_toc: bool = True,
                        include_metadata: bool = True) -> str:
    """
    创建小说内容
    
    Args:
        chapter_files: 章节文件列表
        include_toc: 是否包含目录
        include_metadata: 是否包含元数据
        
    Returns:
        str: 完整的小说内容
    """
    content_parts = []
    
    # 添加元数据
    if include_metadata:
        content_parts.append("=" * 80)
        content_parts.append("小说生成时间：{}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        content_parts.append("生成工具：SoundNovel AI Agent")
        content_parts.append("总章节数：{}".format(len(chapter_files)))
        content_parts.append("=" * 80)
        content_parts.append("\n\n")
    
    # 添加目录
    if include_toc:
        content_parts.append("目 录")
        content_parts.append("=" * 50)
        for chapter_num, file_path in chapter_files:
            # 读取标题
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line.startswith('# '):
                        title = first_line[2:].strip()
                    else:
                        title = f"第{chapter_num}章"
            except:
                title = f"第{chapter_num}章"
            
            content_parts.append(f"第{chapter_num:2d}章  {title}")
        
        content_parts.append("\n\n")
    
    # 添加章节内容
    for chapter_num, file_path in chapter_files:
        print(f"📖 正在处理第{chapter_num}章...")
        chapter_content = read_chapter_content(file_path)
        
        if chapter_content:
            # 添加章节分隔符
            if chapter_num > 1:
                content_parts.append("\n" + "-" * 80 + "\n")
            
            content_parts.append(chapter_content)
    
    return '\n'.join(content_parts)


def save_merged_novel(content: str, output_path: str, backup: bool = True) -> bool:
    """
    保存合并后的小说
    
    Args:
        content: 小说内容
        output_path: 输出路径
        backup: 是否备份
        
    Returns:
        bool: 是否成功
    """
    try:
        output_file = Path(output_path)
        
        # 备份现有文件
        if backup and output_file.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = output_file.parent / f"{output_file.stem}_{timestamp}{output_file.suffix}"
            output_file.rename(backup_path)
            print(f"📋 备份现有文件: {backup_path}")
        
        # 创建目录
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 小说合并完成: {output_path}")
        print(f"📄 文件大小: {len(content)} 字符")
        return True
        
    except Exception as e:
        print(f"❌ 保存合并小说失败: {e}")
        return False


def validate_draft_files(chapter_files: List[Tuple[int, str]]) -> bool:
    """
    验证草稿文件
    
    Args:
        chapter_files: 章节文件列表
        
    Returns:
        bool: 是否验证通过
    """
    if not chapter_files:
        print("❌ 未找到任何章节文件")
        return False
    
    print(f"📊 找到 {len(chapter_files)} 个章节文件")
    
    # 检查章节连续性
    chapter_numbers = [num for num, _ in chapter_files]
    expected_numbers = list(range(1, max(chapter_numbers) + 1))
    
    missing_chapters = set(expected_numbers) - set(chapter_numbers)
    if missing_chapters:
        print(f"⚠️  发现缺失的章节: {sorted(missing_chapters)}")
        print("是否继续合并？(y/n)")
        
        try:
            choice = input().strip().lower()
            if choice != 'y':
                print("❌ 操作已取消")
                return False
        except KeyboardInterrupt:
            print("\n❌ 操作已取消")
            return False
    
    return True


def main():
    """主函数"""
    print("🚀 草稿合并工具启动...")
    
    # 设置日志
    setup_logging()
    
    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    
    # 加载配置
    config = load_config()
    
    # 获取草稿目录
    draft_dir = project_root / config.get('paths', {}).get('draft_dir', '03_draft')
    
    # 获取章节文件
    chapter_files = get_chapter_files(str(draft_dir))
    
    # 验证文件
    if not validate_draft_files(chapter_files):
        return
    
    # 显示合并选项
    print(f"\n📋 合并选项:")
    print("1. 包含目录和元数据")
    print("2. 仅包含目录")
    print("3. 仅包含元数据")
    print("4. 纯文本内容")
    
    try:
        choice = input("请选择合并格式 (1-4): ").strip()
        
        include_toc = choice in ['1', '2']
        include_metadata = choice in ['1', '3']
        
        # 生成输出文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"merged_novel_{timestamp}.txt"
        output_path = project_root / "07_output" / output_filename
        
        # 创建小说内容
        novel_content = create_novel_content(
            chapter_files=chapter_files,
            include_toc=include_toc,
            include_metadata=include_metadata
        )
        
        # 保存文件
        if save_merged_novel(novel_content, str(output_path)):
            print(f"\n🎉 草稿合并成功！")
            print(f"📄 输出文件: {output_path}")
            
            # 显示统计信息
            chapter_count = len(chapter_files)
            char_count = len(novel_content)
            print(f"📊 统计信息:")
            print(f"   章节数: {chapter_count}")
            print(f"   字符数: {char_count}")
            print(f"   平均每章: {char_count // chapter_count} 字符")
            
        else:
            print(f"\n❌ 草稿合并失败")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已取消")
    except Exception as e:
        print(f"\n❌ 操作失败: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="草稿合并工具")
    parser.add_argument("--draft-dir", type=str, help="草稿目录路径")
    parser.add_argument("--output", type=str, help="输出文件路径")
    parser.add_argument("--no-toc", action="store_true", help="不包含目录")
    parser.add_argument("--no-metadata", action="store_true", help="不包含元数据")
    parser.add_argument("--config", type=str, help="配置文件路径")
    
    args = parser.parse_args()
    
    if args.draft_dir or args.output:
        # 命令行模式
        config = load_config(args.config)
        
        draft_dir = args.draft_dir or (project_root / config.get('paths', {}).get('draft_dir', '03_draft'))
        output_path = args.output or (project_root / "07_output" / f"merged_novel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        
        chapter_files = get_chapter_files(draft_dir)
        if not validate_draft_files(chapter_files):
            sys.exit(1)
        
        novel_content = create_novel_content(
            chapter_files=chapter_files,
            include_toc=not args.no_toc,
            include_metadata=not args.no_metadata
        )
        
        success = save_merged_novel(novel_content, output_path)
        sys.exit(0 if success else 1)
    else:
        # 交互模式
        main()