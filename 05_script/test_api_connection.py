"""
AI API连接测试脚本
用于验证AI API调用功能是否正常工作
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from novel_generator.utils.api_client import ZhipuAIClient
from novel_generator.config.settings import Settings


def test_api_connection():
    """测试API连接"""
    print("🔧 测试AI API连接...")
    
    # 加载配置
    config_path = Path(__file__).parent / "config.json"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print("✅ 配置文件加载成功")
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        return False
    
    # 验证配置
    try:
        settings = Settings(config)
        settings.validate()
        print("✅ 配置验证成功")
    except Exception as e:
        print(f"❌ 配置验证失败: {e}")
        return False
    
    # 创建API客户端
    try:
        api_client = ZhipuAIClient(config)
        print("✅ API客户端创建成功")
    except Exception as e:
        print(f"❌ API客户端创建失败: {e}")
        return False
    
    # 测试连接
    try:
        print("🔄 正在测试API连接...")
        success = api_client.test_connection()
        if success:
            print("✅ API连接测试成功")
        else:
            print("❌ API连接测试失败")
            # 尝试获取模型列表来验证连接
            try:
                models = api_client.list_models()
                print(f"✅ 可以获取模型列表，共 {len(models)} 个模型")
                for model in models[:3]:  # 显示前3个模型
                    print(f"   - {model.get('id', 'Unknown')}")
            except Exception as e:
                print(f"❌ 获取模型列表失败: {e}")
            return False
    except Exception as e:
        print(f"❌ API连接测试异常: {e}")
        # 尝试直接调用API来获取更详细的错误信息
        try:
            response = api_client.chat_completion(
                api_client.settings.get_api_model('default'),
                [{'role': 'user', 'content': '测试'}]
            )
            print(f"✅ 直接API调用成功: {response}")
        except Exception as e2:
            print(f"❌ 直接API调用也失败: {e2}")
        return False
    
    # 测试章节扩写功能
    try:
        print("🔄 正在测试章节扩写功能...")
        test_prompt = """
请扩写以下小说章节：

【核心设定】
{"世界观": "现代都市背景，存在隐藏的异能者", "核心冲突": "异能者与普通人的共存问题"}

【上下文回顾】
无前序上下文

【本章大纲】
{"标题": "觉醒", "核心事件": "主角意外觉醒异能", "场景": ["大学校园", "图书馆"], "人物行动": ["主角在图书馆学习", "意外触发电击", "发现自身异能"], "伏笔回收": ""}

【风格要求】
语言风格：现代都市风格，简洁明快；对话特点：自然流畅；场景描写：注重细节

【输出要求】
字数：500字左右；重点描写：意外觉醒异能的过程；格式：分段落，无冗余内容；保持人物性格一致性；注意伏笔的埋设和回收

请严格按照上述要求生成章节内容，确保故事逻辑连贯、人设统一、风格一致。
"""
        
        response = api_client.expand_chapter(test_prompt)
        if response and len(response.strip()) > 0:
            print("✅ 章节扩写测试成功")
            print(f"📝 生成的内容长度: {len(response)} 字符")
            print("📄 内容预览:")
            print("-" * 50)
            print(response[:200] + "..." if len(response) > 200 else response)
            print("-" * 50)
        else:
            print("❌ 章节扩写测试失败：返回空内容")
            return False
    except Exception as e:
        print(f"❌ 章节扩写测试异常: {e}")
        return False
    
    print("\n🎉 所有测试通过！AI API功能已正常工作")
    return True


def test_chapter_expander():
    """测试章节扩写器"""
    print("\n🔧 测试章节扩写器...")
    
    # 加载配置
    config_path = Path(__file__).parent / "config.json"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        return False
    
    # 创建章节扩写器
    try:
        from novel_generator.core.chapter_expander import ChapterExpander
        expander = ChapterExpander(config)
        print("✅ 章节扩写器创建成功")
    except Exception as e:
        print(f"❌ 章节扩写器创建失败: {e}")
        return False
    
    # 测试模拟响应（确保API调用失败时有备用方案）
    try:
        mock_response = expander._get_mock_response()
        if mock_response and len(mock_response.strip()) > 0:
            print("✅ 模拟响应功能正常")
        else:
            print("❌ 模拟响应功能异常")
            return False
    except Exception as e:
        print(f"❌ 模拟响应测试异常: {e}")
        return False
    
    print("✅ 章节扩写器测试完成")
    return True


if __name__ == "__main__":
    print("🚀 开始AI API功能测试...")
    
    # 测试API连接
    api_success = test_api_connection()
    
    # 测试章节扩写器
    expander_success = test_chapter_expander()
    
    if api_success and expander_success:
        print("\n🎉 所有测试通过！AI API功能已成功集成到项目中")
        print("\n📋 使用说明:")
        print("1. 确保在 config.json 中配置了正确的API密钥")
        print("2. 运行 python expand_chapters.py 开始生成章节内容")
        print("3. 生成的内容将使用真实的AI API，而不是模拟数据")
    else:
        print("\n❌ 部分测试失败，请检查配置和网络连接")
        sys.exit(1)