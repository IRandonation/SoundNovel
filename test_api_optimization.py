#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试API优化效果
验证熔断器、限流和重试机制是否正常工作
"""

import sys
import os
import yaml
import time
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


def test_api_optimization():
    """测试API优化效果"""
    print("=" * 60)
    print("开始测试API优化效果")
    print("=" * 60)
    
    # 加载配置和大纲
    config = load_test_config()
    chapter_outline = load_test_chapter_outline()
    
    print(f"测试章节：{chapter_outline.get('标题', '未知')}")
    print(f"核心事件：{chapter_outline.get('核心事件', '未知')}")
    print("-" * 60)
    
    # 初始化章节扩写器
    expander = ChapterExpander(config)
    
    # 测试多次请求，观察重试和限流效果
    success_count = 0
    total_count = 3
    
    for i in range(total_count):
        print(f"\n第 {i+1} 次测试：")
        print("-" * 40)
        
        start_time = time.time()
        
        try:
            content = expander.expand_chapter(
                chapter_num=1,
                chapter_outline=chapter_outline,
                previous_context="",
                style_guide={}
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"✅ 请求成功")
            print(f"   耗时：{duration:.2f} 秒")
            print(f"   字数：{len(content)}")
            
            success_count += 1
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"❌ 请求失败：{e}")
            print(f"   耗时：{duration:.2f} 秒")
        
        # 请求间隔
        if i < total_count - 1:
            print("等待 2 秒后进行下一次测试...")
            time.sleep(2)
    
    # 统计结果
    print("\n" + "=" * 60)
    print("测试结果统计：")
    print("=" * 60)
    print(f"总测试次数：{total_count}")
    print(f"成功次数：{success_count}")
    print(f"失败次数：{total_count - success_count}")
    print(f"成功率：{success_count/total_count*100:.1f}%")
    
    if success_count == total_count:
        print("\n🎉 所有测试均成功！API优化效果良好。")
    elif success_count > 0:
        print(f"\n⚠️ 部分测试成功，成功率为 {success_count/total_count*100:.1f}%。")
    else:
        print("\n❌ 所有测试均失败，需要进一步优化API配置。")
    
    return success_count > 0


if __name__ == "__main__":
    success = test_api_optimization()
    if success:
        print("\n测试完成！")
    else:
        print("\n测试失败！")
        sys.exit(1)