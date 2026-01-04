#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量大纲生成器
用于分批生成大量章节的大纲
"""

import sys
import yaml
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from novel_generator.core.outline_generator import OutlineGenerator

class BatchOutlineGenerator:
    """批量大纲生成器类"""
    
    def __init__(self, config):
        """
        初始化批量大纲生成器
        
        Args:
            config: 配置信息
        """
        self.config = config
        self.outline_generator = OutlineGenerator(config)
    
    def generate_batch_outline(self, core_setting, overall_outline,
                              total_chapters=None, batch_size=15, 
                              start_chapter_idx=None, end_chapter_idx=None,
                              progress_callback=None):
        """
        分批生成章节大纲
        
        Args:
            core_setting: 核心设定
            overall_outline: 整体大纲
            total_chapters: 总章节数（如果为None，则自动从整体大纲中提取）
            batch_size: 每批生成的章节数
            start_chapter_idx: 起始章节序号 (从1开始)
            end_chapter_idx: 结束章节序号
            progress_callback: 进度回调函数，func(current, total, message)
            
        Returns:
            Dict[str, Any]: 生成的完整章节大纲
        """
        # 如果没有指定总章节数，则自动从整体大纲中提取
        if total_chapters is None:
            total_chapters = self.outline_generator.extract_total_chapters(overall_outline)
        
        # 确定生成范围
        actual_start = start_chapter_idx if start_chapter_idx else 1
        actual_end = end_chapter_idx if end_chapter_idx else total_chapters
        
        # 确保范围有效
        actual_start = max(1, actual_start)
        actual_end = min(total_chapters, max(actual_start, actual_end))
        
        print(f"\n📝 开始批量生成章节大纲，范围: 第{actual_start}-{actual_end}章，每批{batch_size}章...")
        if progress_callback:
            progress_callback(0, actual_end - actual_start + 1, f"准备开始生成第{actual_start}-{actual_end}章...")

        complete_outline = {}
        
        # 加载已有大纲作为上下文（如果存在）
        # 这里简单起见，假设外部已经处理了文件合并，或者我们总是追加模式
        # 实际上 outline_generator 内部可能会处理上下文，我们主要关注 batch loop
        
        current_start = actual_start
        total_to_gen = actual_end - actual_start + 1
        processed_count = 0

        while current_start <= actual_end:
            current_end = min(current_start + batch_size - 1, actual_end)
            
            msg = f"正在生成第 {current_start}-{current_end} 章..."
            print(f"\n🔄 {msg}")
            if progress_callback:
                progress_callback(processed_count, total_to_gen, msg)
            
            # 生成当前批次的大纲
            # 注意：outline_generator.generate_outline 应该会读取磁盘上已有的 outline 作为 context
            # 如果需要显式传递 context，需要修改 generate_outline 接口，目前假设它会自动处理或 context 不跨批次太远
            batch_outline = self.outline_generator.generate_outline(
                core_setting=core_setting,
                overall_outline=overall_outline,
                chapter_range=(current_start, current_end)
            )
            
            # 将当前批次的大纲合并到完整大纲中
            complete_outline.update(batch_outline)
            
            batch_count = current_end - current_start + 1
            processed_count += batch_count
            
            print(f"✅ 批次完成，已生成 {len(batch_outline)} 章")
            
            current_start = current_end + 1
        
        if progress_callback:
            progress_callback(total_to_gen, total_to_gen, "✅ 生成完成！")
            
        print(f"\n🎉 批量章节大纲生成完成！本次生成{len(complete_outline)}章")
        return complete_outline
    
    def save_batch_outline(self, outline, output_path, backup=True):
        """
        保存批量生成的大纲
        
        Args:
            outline: 大纲内容
            output_path: 输出路径
            backup: 是否备份
            
        Returns:
            str: 实际保存路径
        """
        return self.outline_generator.save_outline(outline, output_path, backup)