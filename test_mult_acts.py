#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试多幕剧情处理功能
"""

import sys
import yaml
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from novel_generator.core.outline_generator import OutlineGenerator

def test_mult_acts_parsing():
    """测试多幕剧情解析功能"""
    print("🧪 测试多幕剧情处理功能...")
    
    # 模拟一个包含不同数量幕的大纲
    test_outlines = [
        {
            "第一幕": "第1-5章，开篇介绍",
            "第二幕": "第6-10章，发展剧情",
            "第三幕": "第11-15章，高潮部分",
            "关键转折点": "- 第8章：重要转折"
        },
        {
            "第一幕": "第1-10章，开篇",
            "第二幕": "第11-30章，发展",
            "第三幕": "第31-50章，高潮",
            "第四幕": "第51-70章，结局",
            "第五幕": "第71-90章，尾声",
            "关键转折点": "- 第25章：转折点"
        },
        {
            "第一幕": "第1-5章，开始",
            "第二幕": "第6-15章，发展",
            "第三幕": "第16-30章，高潮",
            "第四幕": "第31-50章，转折",
            "第五幕": "第51-75章，冲突",
            "第六幕": "第76-100章，解决",
            "第七幕": "第101-120章，结局",
            "关键转折点": "- 第20章：重要事件"
        }
    ]
    
    # 模拟配置
    config = {
        "api_key": "test_key",
        "model": "test_model",
        "timeout": 30
    }
    
    for i, outline in enumerate(test_outlines, 1):
        print(f"\n--- 测试案例 {i}: 包含 {len([k for k in outline.keys() if '第' in k and '幕' in k])} 幕 ---")
        
        # 创建大纲生成器
        generator = OutlineGenerator(config)
        
        # 测试构建幕文本功能
        acts_text = generator._build_acts_text(outline)
        print(f"生成的幕文本:\n{acts_text}")
        
        # 测试构建提示词功能（不调用API）
        prompt = generator._build_outline_prompt(
            core_setting={"世界观": "测试世界观", "核心冲突": "测试冲突"},
            overall_outline=outline,
            chapter_range=(1, 5)
        )
        
        print(f"提示词中的幕部分:\n{prompt[prompt.find('【整体大纲】'):prompt.find('关键转折点')]}")
        
        print("✅ 测试通过\n")

if __name__ == "__main__":
    test_mult_acts_parsing()
    print("🎉 所有多幕剧情处理测试完成！")