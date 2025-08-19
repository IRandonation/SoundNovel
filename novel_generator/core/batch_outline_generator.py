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
                              total_chapters=None, batch_size=15):
        """
        分批生成章节大纲
        
        Args:
            core_setting: 核心设定
            overall_outline: 整体大纲
            total_chapters: 总章节数（如果为None，则自动从整体大纲中提取）
            batch_size: 每批生成的章节数
            
        Returns:
            Dict[str, Any]: 生成的完整章节大纲
        """
        # 如果没有指定总章节数，则自动从整体大纲中提取
        if total_chapters is None:
            total_chapters = self.outline_generator.extract_total_chapters(overall_outline)
        
        print(f"\n📝 开始批量生成章节大纲，总共{total_chapters}章，每批{batch_size}章...")
        
        complete_outline = {}
        
        # 计算需要分多少批
        num_batches = (total_chapters + batch_size - 1) // batch_size
        
        for batch_num in range(num_batches):
            start_chapter = batch_num * batch_size + 1
            end_chapter = min((batch_num + 1) * batch_size, total_chapters)
            
            print(f"\n🔄 正在生成第{batch_num+1}批：第{start_chapter}-{end_chapter}章...")
            
            # 生成当前批次的大纲
            batch_outline = self.outline_generator.generate_outline(
                core_setting=core_setting,
                overall_outline=overall_outline,
                chapter_range=(start_chapter, end_chapter)
            )
            
            # 将当前批次的大纲合并到完整大纲中
            complete_outline.update(batch_outline)
            
            print(f"✅ 第{batch_num+1}批生成完成，共{len(batch_outline)}章")
        
        print(f"\n🎉 批量章节大纲生成完成！总共{len(complete_outline)}章")
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