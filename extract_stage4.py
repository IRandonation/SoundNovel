#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取 novel_processing_result.json 中的 stage4 内容并整理为完整的 txt 文件
"""

import json
import os
from pathlib import Path

def extract_stage4_to_txt(json_file_path, output_file_path=None):
    """
    从 JSON 文件中提取 stage4 内容并保存为 txt 文件
    
    Args:
        json_file_path (str): JSON 文件路径
        output_file_path (str): 输出的 txt 文件路径，如果为 None 则自动生成
    
    Returns:
        str: 输出文件路径
    """
    # 读取 JSON 文件
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"错误：找不到文件 {json_file_path}")
        return None
    except json.JSONDecodeError:
        print(f"错误：文件 {json_file_path} 不是有效的 JSON 格式")
        return None
    
    # 如果没有指定输出文件路径，则自动生成
    if output_file_path is None:
        json_path = Path(json_file_path)
        output_file_path = json_path.parent / f"{json_path.stem}_stage4.txt"
    
    # 提取 stage4 内容
    stage4_content = []
    
    # 添加标题
    stage4_content.append("=" * 60)
    stage4_content.append("小说 Stage4 完整内容")
    stage4_content.append("=" * 60)
    stage4_content.append("")
    
    # 添加基本信息
    if 'input_file' in data:
        stage4_content.append(f"原始文件：{data['input_file']}")
    
    if 'total_chapters' in data:
        stage4_content.append(f"总章节数：{data['total_chapters']}")
    
    if 'processing_time' in data:
        stage4_content.append(f"处理时间：{data['processing_time']}")
    
    stage4_content.append("")
    stage4_content.append("=" * 60)
    stage4_content.append("")
    
    # 提取各章节的 stage4 内容
    processed_chapters = data.get('processed_chapters', [])
    
    for chapter in processed_chapters:
        chapter_number = chapter.get('chapter_number', 0)
        stage4_text = chapter.get('stage4_content', '')
        
        if stage4_text.strip():  # 只添加非空内容
            # 添加章节标题
            stage4_content.append(f"第{chapter_number}章")
            stage4_content.append("-" * 40)
            stage4_content.append("")
            
            # 添加章节内容
            stage4_content.append(stage4_text.strip())
            stage4_content.append("")
            stage4_content.append("")
    
    # 将内容写入 txt 文件
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(stage4_content))
        
        print(f"成功！Stage4 内容已保存到：{output_file_path}")
        print(f"文件大小：{os.path.getsize(output_file_path)} 字节")
        
        return output_file_path
    
    except Exception as e:
        print(f"错误：无法写入文件 {output_file_path} - {e}")
        return None

def main():
    """主函数"""
    json_file = "output/novel_processing_result.json"
    
    print("正在提取 Stage4 内容...")
    print(f"源文件：{json_file}")
    
    # 提取并保存到 txt 文件
    output_file = extract_stage4_to_txt(json_file)
    
    if output_file:
        print("\n提取完成！")
        print(f"输出文件：{output_file}")
        
        # 显示文件的前几行作为预览
        print("\n文件预览（前 200 字符）：")
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                preview = f.read(200)
                print(preview)
        except Exception as e:
            print(f"无法预览文件：{e}")

if __name__ == "__main__":
    main()