"""
配置集成脚本
将现有的config.json配置集成到项目中
"""

import os
import sys
import json
import shutil
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from novel_generator.config.settings import Settings, create_default_config
from novel_generator.utils.logger import NovelLogger, BackupManager
from novel_generator.utils.file_handler import FileHandler


def load_existing_config() -> dict:
    """加载现有的config.json配置"""
    try:
        # 尝试加载项目根目录下的config.json
        config_path = project_root / "config.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 尝试加载05_script目录下的config.json
        config_path = project_root / "05_script" / "config.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        print("❌ 未找到现有的config.json文件")
        return {}
        
    except Exception as e:
        print(f"❌ 加载现有配置失败: {e}")
        return {}


def merge_configs(existing_config: dict, default_config: dict) -> dict:
    """
    合并配置
    
    Args:
        existing_config: 现有配置
        default_config: 默认配置
        
    Returns:
        dict: 合并后的配置
    """
    merged_config = default_config.copy()
    
    # 递归合并配置
    def deep_merge(target, source):
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                deep_merge(target[key], value)
            else:
                target[key] = value
    
    deep_merge(merged_config, existing_config)
    
    return merged_config


def backup_existing_config(config_path: Path) -> str:
    """备份现有配置文件"""
    try:
        backup_manager = BackupManager({})
        backup_path = backup_manager.backup_file(str(config_path))
        return backup_path
    except Exception as e:
        print(f"⚠️  备份配置文件失败: {e}")
        return ""


def integrate_config():
    """集成配置"""
    print("🔧 开始集成现有配置...")
    
    # 加载现有配置
    existing_config = load_existing_config()
    if not existing_config:
        print("❌ 未找到现有配置，使用默认配置")
        return False
    
    # 创建默认配置
    default_config = create_default_config()
    
    # 合并配置
    merged_config = merge_configs(existing_config, default_config)
    
    # 显示配置差异
    print("\n📋 配置集成信息:")
    print(f"   现有配置项: {len(existing_config)}")
    print(f"   默认配置项: {len(default_config)}")
    print(f"   合并配置项: {len(merged_config)}")
    
    # 显示API配置
    if 'api_key' in existing_config:
        api_key = existing_config['api_key']
        masked_key = api_key[:8] + "*" * (len(api_key) - 8) if len(api_key) > 8 else "*" * len(api_key)
        print(f"   API密钥: {masked_key}")
    
    if 'models' in existing_config:
        models = existing_config['models']
        print(f"   模型配置: {list(models.keys())}")
    
    # 备份现有配置
    config_path = project_root / "05_script" / "config.json"
    if config_path.exists():
        backup_path = backup_existing_config(config_path)
        if backup_path:
            print(f"   备份文件: {backup_path}")
    
    # 保存合并后的配置
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(merged_config, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 配置集成完成: {config_path}")
        return True
        
    except Exception as e:
        print(f"❌ 保存配置失败: {e}")
        return False


def validate_integrated_config() -> bool:
    """验证集成后的配置"""
    print("\n🔍 验证集成配置...")
    
    try:
        # 加载配置
        config_path = project_root / "05_script" / "config.json"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 创建设置对象并验证
        settings = Settings(config)
        settings.validate()
        
        # 检查必要配置项
        required_keys = ['api_key', 'api_base_url', 'models', 'paths']
        missing_keys = [key for key in required_keys if key not in config]
        
        if missing_keys:
            print(f"❌ 缺少必要配置项: {', '.join(missing_keys)}")
            return False
        
        # 检查API密钥
        if not config['api_key'] or config['api_key'] == "请在此处填写智谱API密钥":
            print("⚠️  API密钥未配置")
        
        print("✅ 配置验证通过")
        return True
        
    except Exception as e:
        print(f"❌ 配置验证失败: {e}")
        return False


def create_config_template():
    """创建配置模板"""
    print("\n📄 创建配置模板...")
    
    try:
        # 创建配置模板
        template_config = {
            "api_key": "请在此处填写您的智谱API密钥",
            "api_base_url": "https://open.bigmodel.cn/api/paas/v4",
            "models": {
                "logic_analysis_model": "glm-4-long",
                "major_chapters_model": "glm-4-long",
                "sub_chapters_model": "glm-4-long",
                "expansion_model": "glm-4.5-flash",
                "default_model": "glm-4.5-flash"
            },
            "max_tokens": 4000,
            "temperature": 0.7,
            "top_p": 0.7,
            "system": {
                "api": {
                    "max_retries": 5,
                    "retry_delay": 2,
                    "timeout": 60
                },
                "logging": {
                    "level": "INFO",
                    "file": "06_log/novel_generator.log"
                }
            },
            "paths": {
                "core_setting": "01_source/core_setting.yaml",
                "outline_dir": "02_outline/",
                "draft_dir": "03_draft/",
                "prompt_dir": "04_prompt/",
                "log_dir": "06_log/"
            },
            "novel_generation": {
                "stage1_use_long_model": True,
                "stage2_use_long_model": True,
                "stage3_use_regular_model": True,
                "stage4_use_regular_model": True,
                "stage5_use_regular_model": True,
                "sub_chapter_range": [15, 55],
                "context_chapters": 5,
                "copyright_bypass": True,
                "world_style": ""
            }
        }
        
        # 保存模板
        template_path = project_root / "config_template.json"
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(template_config, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 配置模板已创建: {template_path}")
        return True
        
    except Exception as e:
        print(f"❌ 创建配置模板失败: {e}")
        return False


def main():
    """主函数"""
    print("🚀 配置集成工具启动...")
    
    # 检查项目结构
    project_root = Path(__file__).parent.parent
    if not (project_root / "novel_generator").exists():
        print("❌ 未找到novel_generator目录，请确保在正确的项目根目录下运行")
        return
    
    # 集成配置
    if integrate_config():
        # 验证配置
        if validate_integrated_config():
            print("\n🎉 配置集成成功！")
            
            # 创建配置模板
            create_config_template()
            
            print("\n📋 下一步操作:")
            print("1. 在 05_script/config.json 中填写您的API密钥")
            print("2. 运行 python main.py --init 初始化项目")
            print("3. 运行 python main.py 开始创作")
        else:
            print("\n❌ 配置验证失败，请检查配置文件")
    else:
        print("\n❌ 配置集成失败")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="配置集成工具")
    parser.add_argument("--validate", action="store_true", help="仅验证配置")
    parser.add_argument("--template", action="store_true", help="创建配置模板")
    
    args = parser.parse_args()
    
    if args.validate:
        validate_integrated_config()
    elif args.template:
        create_config_template()
    else:
        main()