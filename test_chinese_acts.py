#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试中文格式幕名称的处理功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from novel_generator.core.outline_generator import OutlineGenerator

def test_chinese_acts():
    """测试中文格式幕名称的处理功能"""
    print("🧪 测试中文格式幕名称的处理功能...")
    
    # 测试数据 - 使用中文格式的键名
    test_outline = {
        "第一幕": "第1-5章，开篇介绍",
        "第二幕": "第6-10章，发展剧情", 
        "第三幕": "第11-15章，高潮部分",
        "第四幕": "第16-20章，转折点",
        "第五幕": "第21-25章，结局",
        "关键转折点": "- 第8章：重要转折"
    }
    
    # 模拟配置
    config = {
        "api_key": "test_key",
        "model": "test_model",
        "timeout": 30
    }
    
    # 创建大纲生成器
    generator = OutlineGenerator(config)
    
    # 测试构建幕文本功能
    print("📝 测试 _build_acts_text 方法:")
    acts_text = generator._build_acts_text(test_outline)
    print(f"返回结果:\n{acts_text}")
    print(f"长度: {len(acts_text)}")
    
    # 测试提示词构建
    print("\n📝 测试 _build_outline_prompt 方法:")
    prompt = generator._build_outline_prompt(
        core_setting={"世界观": "测试世界观", "核心冲突": "测试冲突"},
        overall_outline=test_outline,
        chapter_range=(1, 5)
    )
    
    # 提取幕部分
    start_idx = prompt.find("【整体大纲】")
    end_idx = prompt.find("关键转折点")
    if start_idx != -1 and end_idx != -1:
        acts_section = prompt[start_idx:end_idx]
        print(f"幕部分内容:\n{acts_section}")
    else:
        print("未找到幕部分")
    
    print("\n✅ 测试完成")

if __name__ == "__main__":
    test_chinese_acts()
    print("🎉 中文格式幕名称处理测试完成！")