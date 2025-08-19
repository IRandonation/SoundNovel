#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试改进后的章节扩写系统
验证是否能够有效减少前瞻性内容并提高章节内容的具体性
"""

import sys
import os
import yaml
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from novel_generator.core.chapter_expander import ChapterExpander
from novel_generator.config.settings import Settings


def load_test_config():
    """加载测试配置"""
    config_path = project_root / "05_script" / "config.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_test_chapter_outline():
    """加载测试章节大纲"""
    # 使用第一章作为测试
    outline_path = project_root / "02_outline" / "chapter_outline_01-58.yaml"
    with open(outline_path, 'r', encoding='utf-8') as f:
        outline = yaml.safe_load(f)
    
    # 返回第一章的大纲
    return outline.get("第1章", {})


def test_chapter_expansion():
    """测试章节扩写功能"""
    print("=" * 50)
    print("开始测试改进后的章节扩写系统")
    print("=" * 50)
    
    # 加载配置和大纲
    config = load_test_config()
    chapter_outline = load_test_chapter_outline()
    
    print(f"测试章节：{chapter_outline.get('标题', '未知')}")
    print(f"核心事件：{chapter_outline.get('核心事件', '未知')}")
    print("-" * 50)
    
    # 初始化章节扩写器
    expander = ChapterExpander(config)
    
    # 扩写章节
    try:
        content = expander.expand_chapter(
            chapter_num=1,
            chapter_outline=chapter_outline,
            previous_context="",
            style_guide={}
        )
        
        print("生成的章节内容：")
        print("-" * 50)
        print(content[:500] + "..." if len(content) > 500 else content)
        print("-" * 50)
        
        # 分析内容质量
        print("\n内容质量分析：")
        print("-" * 50)
        
        # 检查前瞻性关键词
        future_keywords = ['最终', '结局', '后来', '从此', '以后', '最终成为', '最终走向', '最终被']
        future_count = sum(content.count(keyword) for keyword in future_keywords)
        print(f"前瞻性关键词出现次数：{future_count}")
        
        # 检查概括性短语
        vague_phrases = ['这个故事', '这个传说', '这段经历', '这段历史', '这个事件']
        vague_count = sum(content.count(phrase) for phrase in vague_phrases)
        print(f"概括性短语出现次数：{vague_count}")
        
        # 检查具体性指标
        concrete_indicators = ['说', '做', '走', '看', '听', '想', '感到', '拿起', '放下', '转身']
        concrete_count = sum(content.count(indicator) for indicator in concrete_indicators)
        concrete_ratio = concrete_count / len(content) * 100
        print(f"具体性指标比例：{concrete_ratio:.2f}%")
        
        # 检查字数
        word_count = len(content)
        target_count = 1500  # 目标字数
        print(f"实际字数：{word_count}（目标：{target_count}）")
        
        # 评估结果
        print("\n评估结果：")
        print("-" * 50)
        
        if future_count == 0:
            print("✅ 前瞻性内容控制良好")
        elif future_count <= 2:
            print("⚠️ 前瞻性内容较少，但仍需注意")
        else:
            print("❌ 前瞻性内容过多")
        
        if vague_count == 0:
            print("✅ 概括性内容控制良好")
        elif vague_count <= 2:
            print("⚠️ 概括性内容较少，但仍需注意")
        else:
            print("❌ 概括性内容过多")
        
        if concrete_ratio > 2.0:
            print("✅ 具体性内容丰富")
        elif concrete_ratio > 1.0:
            print("⚠️ 具体性内容一般")
        else:
            print("❌ 具体性内容不足")
        
        if abs(word_count - target_count) / target_count <= 0.2:
            print("✅ 字数控制良好")
        else:
            print("❌ 字数控制不佳")
        
        return True
        
    except Exception as e:
        print(f"测试失败：{e}")
        return False


if __name__ == "__main__":
    success = test_chapter_expansion()
    if success:
        print("\n测试完成！")
    else:
        print("\n测试失败！")
        sys.exit(1)