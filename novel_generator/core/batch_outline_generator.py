#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import yaml
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from novel_generator.core.outline_generator import OutlineGenerator

class BatchOutlineGenerator:
    
    def __init__(self, config):
        self.config = config
        self.outline_generator = OutlineGenerator(config)
        self.output_path = None
        self.incremental_save = True
    
    def generate_batch_outline(self, core_setting, overall_outline,
                              total_chapters=None, batch_size=15, 
                              start_chapter_idx=None, end_chapter_idx=None,
                              progress_callback=None,
                              output_path=None,
                              incremental_save=True):
        
        if total_chapters is None:
            total_chapters = self.outline_generator.extract_total_chapters(overall_outline)
        
        actual_start = start_chapter_idx if start_chapter_idx else 1
        actual_end = end_chapter_idx if end_chapter_idx else total_chapters
        
        actual_start = max(1, actual_start)
        actual_end = min(total_chapters, max(actual_start, actual_end))
        
        self.incremental_save = incremental_save
        self.output_path = output_path
        
        print(f"\n📝 开始批量生成章节大纲，范围: 第{actual_start}-{actual_end}章，每批{batch_size}章...")
        if progress_callback:
            progress_callback(0, actual_end - actual_start + 1, f"准备开始生成第{actual_start}-{actual_end}章...")

        complete_outline = {}
        
        if output_path and Path(output_path).exists():
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                    existing = yaml.safe_load(f)
                    if existing and isinstance(existing, dict):
                        complete_outline = existing
                        print(f"📂 加载已有大纲: {len(complete_outline)} 章")
            except:
                pass
        
        current_start = actual_start
        total_to_gen = actual_end - actual_start + 1
        processed_count = 0

        while current_start <= actual_end:
            current_end = min(current_start + batch_size - 1, actual_end)
            
            skip_batch = True
            for ch in range(current_start, current_end + 1):
                if f"第{ch}章" not in complete_outline:
                    skip_batch = False
                    break
            
            if skip_batch:
                print(f"⏭️  第 {current_start}-{current_end} 章已存在，跳过")
                processed_count += current_end - current_start + 1
                current_start = current_end + 1
                continue
            
            msg = f"正在生成第 {current_start}-{current_end} 章..."
            print(f"\n🔄 {msg}")
            if progress_callback:
                progress_callback(processed_count, total_to_gen, msg)
            
            batch_outline = self.outline_generator.generate_outline(
                core_setting=core_setting,
                overall_outline=overall_outline,
                chapter_range=(current_start, current_end)
            )
            
            complete_outline.update(batch_outline)
            
            if self.incremental_save and self.output_path:
                self._save_incremental(complete_outline, self.output_path)
                print(f"💾 已保存进度: {len(complete_outline)} 章")
            
            batch_count = current_end - current_start + 1
            processed_count += batch_count
            
            print(f"✅ 批次完成，已生成 {len(batch_outline)} 章")
            
            current_start = current_end + 1
        
        if progress_callback:
            progress_callback(total_to_gen, total_to_gen, "✅ 生成完成！")
            
        print(f"\n🎉 批量章节大纲生成完成！本次生成{len(complete_outline)}章")
        return complete_outline
    
    def _save_incremental(self, outline, output_path):
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(outline, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        except Exception as e:
            print(f"⚠️ 增量保存失败: {e}")
    
    def save_batch_outline(self, outline, output_path, backup=True):
        return self.outline_generator.save_outline(outline, output_path, backup)