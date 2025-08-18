"""
小说创作AI Agent主程序
实现从原始素材到签约级小说的自动化辅助创作
"""

import os
import sys
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from novel_generator.core.project_manager import ProjectManager
from novel_generator.core.outline_generator import OutlineGenerator
from novel_generator.config.settings import Settings, create_default_config


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


def load_core_setting(project_root: Path) -> Dict[str, Any]:
    """加载核心设定"""
    try:
        with open(project_root / "01_source" / "core_setting.yaml", 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ 加载核心设定失败: {e}")
        return {}


def load_overall_outline(project_root: Path) -> Dict[str, Any]:
    """加载整体大纲"""
    try:
        with open(project_root / "01_source" / "overall_outline.yaml", 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ 加载整体大纲失败: {e}")
        return {}


def load_style_guide(project_root: Path) -> Dict[str, Any]:
    """加载风格指导"""
    try:
        with open(project_root / "04_prompt" / "style_guide.yaml", 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ 加载风格指导失败: {e}")
        return {}


def generate_outline(config: Dict[str, Any], 
                    core_setting: Dict[str, Any],
                    overall_outline: Dict[str, Any]) -> bool:
    """生成章节大纲"""
    try:
        print("\n📝 开始生成章节大纲...")
        
        # 创建大纲生成器
        outline_generator = OutlineGenerator(config)
        
        # 生成大纲
        outline = outline_generator.generate_outline(
            core_setting=core_setting,
            overall_outline=overall_outline,
            chapter_range=(1, 20)  # 生成前10章大纲
        )
        
        # 保存大纲
        outline_path = project_root / "02_outline" / "chapter_outline_01-10.yaml"
        outline_generator.save_outline(outline, str(outline_path))
        
        print(f"✅ 章节大纲生成成功: {outline_path}")
        return True
        
    except Exception as e:
        print(f"❌ 生成章节大纲失败: {e}")
        return False


def main():
    """主函数"""
    print("🚀 小说创作AI Agent启动...")
    
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
    
    # 加载核心设定和整体大纲
    core_setting = load_core_setting(project_root)
    overall_outline = load_overall_outline(project_root)
    style_guide = load_style_guide(project_root)
    
    if not core_setting or not overall_outline:
        print("❌ 核心设定或整体大纲为空，请先填写相关内容")
        return
    
    # 显示项目信息
    print(f"\n📋 项目信息:")
    print(f"   项目根目录: {project_root}")
    print(f"   世界风格: {settings.generation_config.world_style or '未设置'}")
    print(f"   上下文章节数: {settings.get_context_chapters()}")
    print(f"   默认字数: {settings.get_default_word_count()}")
    
    # 显示核心设定
    print(f"\n📖 核心设定:")
    print(f"   世界观: {core_setting.get('世界观', '未设置')[:50]}...")
    print(f"   核心冲突: {core_setting.get('核心冲突', '未设置')[:50]}...")
    
    # 显示整体大纲
    print(f"\n📊 整体大纲:")
    print(f"   第一幕: {overall_outline.get('第一幕', '未设置')[:50]}...")
    print(f"   第二幕: {overall_outline.get('第二幕', '未设置')[:50]}...")
    print(f"   第三幕: {overall_outline.get('第三幕', '未设置')[:50]}...")
    
    # 生成章节大纲
    if generate_outline(config, core_setting, overall_outline):
        print("\n🎉 章节大纲生成完成！")
        print("\n📋 下一步操作:")
        print("1. 查看 02_outline/chapter_outline_01-10.yaml 并优化大纲")
        print("2. 运行 python expand_chapters.py 开始生成章节内容")
    else:
        print("\n❌ 章节大纲生成失败，请检查错误信息")


def init_project():
    """初始化项目"""
    print("🚀 开始初始化小说创作AI Agent项目...")
    
    # 创建项目管理器
    manager = ProjectManager()
    
    # 初始化项目
    if manager.initialize_project():
        print("\n🎉 项目初始化完成！")
        print("\n📋 下一步操作指南:")
        print("1. 填写 01_source/ 目录下的核心设定和整体大纲")
        print("2. 在 05_script/config.json 中配置API密钥")
        print("3. 运行 python main.py 开始创作")
    else:
        print("\n❌ 项目初始化失败，请检查错误信息")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="小说创作AI Agent")
    parser.add_argument("--init", action="store_true", help="初始化项目")
    parser.add_argument("--config", type=str, help="配置文件路径")
    
    args = parser.parse_args()
    
    if args.init:
        init_project()
    else:
        main()