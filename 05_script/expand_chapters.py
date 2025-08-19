"""
章节扩写脚本
实现基于滑动窗口技术的章节内容生成
"""

import os
import sys
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from novel_generator.core.chapter_expander import ChapterExpander
from novel_generator.core.sliding_window import ContextManager
from novel_generator.config.settings import Settings, create_default_config
from novel_generator.utils.multi_model_client import MultiModelClient


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


def validate_project_structure(project_root: Path) -> bool:
    """验证项目结构"""
    required_files = [
        "01_source/core_setting.yaml",
        "01_source/overall_outline.yaml",
        "02_outline/chapter_outline_01-58.yaml",
        "04_prompt/chapter_expand_prompt.yaml",
        "04_prompt/style_guide.yaml"
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = project_root / file_path
        if not full_path.exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ 缺少必要文件: {', '.join(missing_files)}")
        return False
    
    return True


def load_style_guide(project_root: Path) -> Dict[str, Any]:
    """加载风格指导"""
    try:
        with open(project_root / "04_prompt" / "style_guide.yaml", 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ 加载风格指导失败: {e}")
        return {}


def initialize_multi_model_client(config: Dict[str, Any]) -> MultiModelClient:
    """
    初始化多模型客户端
    
    Args:
        config: 配置信息
        
    Returns:
        MultiModelClient: 多模型客户端实例
    """
    try:
        client = MultiModelClient(config)
        print(f"✅ 多模型客户端初始化成功")
        print(f"   当前使用模型: {client.get_current_model()}")
        print(f"   可用模型: {client.get_available_models()}")
        return client
    except Exception as e:
        print(f"❌ 多模型客户端初始化失败: {e}")
        return None


def get_chapter_range_from_outline(outline_file: str) -> Tuple[int, int]:
    """
    从大纲文件获取章节范围
    
    Args:
        outline_file: 大纲文件路径
        
    Returns:
        Tuple[int, int]: (起始章节, 结束章节)
    """
    try:
        with open(outline_file, 'r', encoding='utf-8') as f:
            outline = yaml.safe_load(f)
        
        # 提取章节号
        chapters = []
        for key in outline.keys():
            if key.startswith('第') and '章' in key:
                try:
                    chapter_num = int(key.replace('第', '').replace('章', ''))
                    chapters.append(chapter_num)
                except ValueError:
                    continue
        
        if not chapters:
            raise ValueError("大纲文件中未找到有效的章节信息")
        
        return min(chapters), max(chapters)
        
    except Exception as e:
        print(f"❌ 解析章节范围失败: {e}")
        return 1, 10  # 默认范围


def expand_single_chapter(chapter_num: int, config: Dict[str, Any],
                         outline_file: str, style_guide: Dict[str, Any],
                         multi_model_client: MultiModelClient = None) -> bool:
    """
    扩写单个章节
    
    Args:
        chapter_num: 章节号
        config: 配置信息
        outline_file: 大纲文件路径
        style_guide: 风格指导
        multi_model_client: 多模型客户端
        
    Returns:
        bool: 是否成功
    """
    try:
        print(f"\n📝 开始扩写第{chapter_num}章...")
        
        # 加载大纲
        with open(outline_file, 'r', encoding='utf-8') as f:
            outline = yaml.safe_load(f)
        
        chapter_key = f"第{chapter_num}章"
        if chapter_key not in outline:
            print(f"❌ 第{chapter_num}章大纲不存在")
            return False
        
        chapter_outline = outline[chapter_key]
        
        # 创建章节扩写器
        expander = ChapterExpander(config)
        
        # 如果有多模型客户端，设置多模型功能
        if multi_model_client:
            expander.multi_model_client = multi_model_client
            print(f"   使用模型: {multi_model_client.get_current_model()}")
        
        # 准备上下文
        context_manager = ContextManager(config)
        previous_context, needs_repair = context_manager.prepare_context(
            current_chapter=chapter_num,
            outline_file=outline_file,
            draft_dir=config['paths']['draft_dir']
        )
        
        if needs_repair:
            print("⚠️  检测到上下文断裂，已自动修复")
        
        # 扩写章节
        content = expander.expand_chapter(
            chapter_num=chapter_num,
            chapter_outline=chapter_outline,
            previous_context=previous_context,
            style_guide=style_guide
        )
        
        # 保存章节
        output_dir = Path(config['paths']['draft_dir'])
        expander.save_chapter(chapter_num, content, str(output_dir))
        
        print(f"✅ 第{chapter_num}章扩写完成")
        return True
        
    except Exception as e:
        print(f"❌ 扩写第{chapter_num}章失败: {e}")
        return False


def expand_multiple_chapters(start_chapter: int, end_chapter: int,
                            config: Dict[str, Any],
                            outline_file: str,
                            style_guide: Dict[str, Any],
                            multi_model_client: MultiModelClient = None) -> bool:
    """
    批量扩写章节
    
    Args:
        start_chapter: 起始章节
        end_chapter: 结束章节
        config: 配置信息
        outline_file: 大纲文件路径
        style_guide: 风格指导
        multi_model_client: 多模型客户端
        
    Returns:
        bool: 是否全部成功
    """
    try:
        print(f"\n🚀 开始批量扩写章节 {start_chapter}-{end_chapter}...")
        
        # 创建章节扩写器
        expander = ChapterExpander(config)
        
        # 如果有多模型客户端，设置多模型功能
        if multi_model_client:
            expander.multi_model_client = multi_model_client
            print(f"   使用模型: {multi_model_client.get_current_model()}")
        
        # 扩写章节
        success = expander.expand_multiple_chapters(
            chapter_range=(start_chapter, end_chapter),
            outline_file=outline_file,
            style_guide=style_guide
        )
        
        if success:
            print(f"\n🎉 批量扩写完成！共生成 {end_chapter - start_chapter + 1} 章")
        else:
            print(f"\n⚠️  批量扩写部分完成，请检查日志")
        
        return success
        
    except Exception as e:
        print(f"❌ 批量扩写失败: {e}")
        return False


def main():
    """主函数"""
    print("🚀 章节扩写器启动...")
    
    # 设置日志
    setup_logging()
    
    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    
    # 验证项目结构
    if not validate_project_structure(project_root):
        print("❌ 项目结构不完整，请先运行初始化脚本")
        return
    
    # 加载配置
    config = load_config()
    
    # 验证配置
    settings = Settings(config)
    try:
        settings.validate()
    except Exception as e:
        print(f"❌ 配置验证失败: {e}")
        return
    
    # 加载风格指导
    style_guide = load_style_guide(project_root)
    
    # 获取大纲文件
    outline_file = project_root / "02_outline" / "chapter_outline_01-58.yaml"
    if not outline_file.exists():
        print("❌ 章节大纲文件不存在，请先生成大纲")
        return
    
    # 获取章节范围
    try:
        start_chapter, end_chapter = get_chapter_range_from_outline(str(outline_file))
        print(f"📊 检测到章节范围: {start_chapter}-{end_chapter}")
    except Exception as e:
        print(f"❌ 解析章节范围失败: {e}")
        start_chapter, end_chapter = 1, 10
    
    # 初始化多模型客户端
    multi_model_client = initialize_multi_model_client(config)
    if not multi_model_client:
        print("❌ 多模型客户端初始化失败，使用传统方式")
        # 使用传统方式
        print(f"\n📋 扩写配置:")
        print(f"   上下文章节数: {settings.get_context_chapters()}")
        print(f"   默认字数: {settings.get_default_word_count()}")
        print(f"   使用模型: {settings.get_api_model('stage4')}")
    else:
        # 显示配置信息
        print(f"\n📋 扩写配置:")
        print(f"   上下文章节数: {settings.get_context_chapters()}")
        print(f"   默认字数: {settings.get_default_word_count()}")
        print(f"   当前使用模型: {multi_model_client.get_current_model()}")
        
        # 询问是否切换模型
        print(f"\n🔄 模型选择:")
        available_models = multi_model_client.get_available_models()
        for i, model_type in enumerate(available_models, 1):
            print(f"{i}. {model_type}")
        
        try:
            model_choice = input(f"请选择模型 (1-{len(available_models)}, 直接回车使用当前模型): ").strip()
            if model_choice:
                model_index = int(model_choice) - 1
                if 0 <= model_index < len(available_models):
                    selected_model = available_models[model_index]
                    if multi_model_client.switch_model(selected_model):
                        print(f"✅ 已切换到 {selected_model} 模型")
                    else:
                        print(f"❌ 切换到 {selected_model} 模型失败")
        except (ValueError, KeyboardInterrupt):
            print("   使用当前模型")
    
    # 显示风格指导
    if style_guide:
        print(f"\n🎨 风格指导:")
        print(f"   语言风格: {style_guide.get('语言风格', '未设置')}")
        print(f"   对话特点: {style_guide.get('对话特点', '未设置')}")
    
    # 询问扩写模式
    print(f"\n📝 请选择扩写模式:")
    print("1. 扩写单个章节")
    print("2. 批量扩写所有章节")
    print("3. 批量扩写指定范围")
    
    try:
        choice = input("请输入选择 (1-3): ").strip()
        
        if choice == "1":
            # 单章节扩写
            chapter_num = int(input("请输入要扩写的章节号: ").strip())
            success = expand_single_chapter(chapter_num, config, str(outline_file), style_guide, multi_model_client)
            
            if success:
                print(f"\n✅ 第{chapter_num}章扩写完成！")
                print(f"📄 文件位置: {config['paths']['draft_dir']}chapter_{chapter_num:02d}.md")
        
        elif choice == "2":
            # 批量扩写所有章节
            success = expand_multiple_chapters(start_chapter, end_chapter, 
                                             config, str(outline_file), style_guide, multi_model_client)
            
            if success:
                print(f"\n✅ 所有章节扩写完成！")
                print(f"📄 文件位置: {config['paths']['draft_dir']}")
        
        elif choice == "3":
            # 指定范围扩写
            custom_start = int(input("请输入起始章节号: ").strip())
            custom_end = int(input("请输入结束章节号: ").strip())
            
            if custom_start < start_chapter or custom_end > end_chapter:
                print(f"❌ 章节范围超出大纲范围 ({start_chapter}-{end_chapter})")
                return
            
            success = expand_multiple_chapters(custom_start, custom_end,
                                             config, str(outline_file), style_guide, multi_model_client)
            
            if success:
                print(f"\n✅ 指定范围章节扩写完成！")
                print(f"📄 文件位置: {config['paths']['draft_dir']}")
        
        else:
            print("❌ 无效选择")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已取消")
    except Exception as e:
        print(f"\n❌ 操作失败: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="章节扩写器")
    parser.add_argument("--chapter", type=int, help="指定要扩写的章节号")
    parser.add_argument("--start", type=int, help="起始章节号")
    parser.add_argument("--end", type=int, help="结束章节号")
    parser.add_argument("--config", type=str, help="配置文件路径")
    
    args = parser.parse_args()
    
    if args.chapter:
        # 单章节模式
        config = load_config(args.config)
        settings = Settings(config)
        settings.validate()
        
        style_guide = load_style_guide(Path(args.config).parent.parent)
        outline_file = Path(args.config).parent.parent / "02_outline" / "chapter_outline_01-10.yaml"
        
        # 初始化多模型客户端
        multi_model_client = initialize_multi_model_client(config)
        
        success = expand_single_chapter(args.chapter, config, str(outline_file), style_guide, multi_model_client)
        print(f"{'✅' if success else '❌'} 第{args.chapter}章扩写{'成功' if success else '失败'}")
    
    elif args.start and args.end:
        # 批量模式
        config = load_config(args.config)
        settings = Settings(config)
        settings.validate()
        
        style_guide = load_style_guide(Path(args.config).parent.parent)
        outline_file = Path(args.config).parent.parent / "02_outline" / "chapter_outline_01-10.yaml"
        
        # 初始化多模型客户端
        multi_model_client = initialize_multi_model_client(config)
        
        success = expand_multiple_chapters(args.start, args.end, config, str(outline_file), style_guide, multi_model_client)
        print(f"{'✅' if success else '❌'} 章节扩写{'成功' if success else '部分成功'}")
    
    else:
        # 交互模式
        main()