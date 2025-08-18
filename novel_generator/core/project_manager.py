"""
项目管理器
负责项目的初始化、配置管理和目录结构维护
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class ProjectManager:
    """项目管理器类"""
    
    def __init__(self, project_root: str = "."):
        """
        初始化项目管理器
        
        Args:
            project_root: 项目根目录路径
        """
        self.project_root = Path(project_root).resolve()
        self.config = {}
        self.logger = None
        
    def initialize_project(self, force: bool = False) -> bool:
        """
        初始化项目结构
        
        Args:
            force: 是否强制覆盖现有文件
            
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 创建必要的目录结构
            self._create_directory_structure()
            
            # 生成配置文件
            self._generate_config_files()
            
            # 生成模板文件
            self._generate_template_files()
            
            print(f"✅ 项目初始化成功！项目根目录: {self.project_root}")
            return True
            
        except Exception as e:
            print(f"❌ 项目初始化失败: {e}")
            return False
    
    def _create_directory_structure(self):
        """创建项目目录结构"""
        directories = [
            "01_source",
            "02_outline",
            "02_outline/outline_history", 
            "03_draft",
            "03_draft/draft_history",
            "04_prompt",
            "05_script",
            "06_log",
            "06_log/ai_api_logs",
            "06_log/system_logs"
        ]
        
        for directory in directories:
            dir_path = self.project_root / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"📁 创建目录: {dir_path}")
    
    def _generate_config_files(self):
        """生成配置文件"""
        config_template = {
            "api_key": "请在此处填写智谱API密钥",
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
            }
        }
        
        config_path = self.project_root / "05_script" / "config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_template, f, ensure_ascii=False, indent=2)
        print(f"📄 生成配置文件: {config_path}")
    
    def _generate_template_files(self):
        """生成模板文件"""
        # 生成核心设定模板
        core_setting_template = """# 核心设定模板
# 请根据您的小说创作需求填写以下内容

世界观: 
  # 【请填写】故事背景、世界规则等
  # 例如：这是一个修仙世界，灵气复苏，人人可修炼，但修炼资源稀缺...

核心冲突: 
  # 【请填写】主线矛盾、核心目标
  # 例如：主角需要寻找传说中的神器来拯救即将毁灭的世界，但各大势力都在争夺...

人物小传:
  主角: 
    # 【请填写】姓名、身份、性格、核心动机
    # 姓名：
    # 身份：
    # 性格：
    # 核心动机：
  
  配角1: 
    # 【请填写】姓名、身份、性格、核心动机
    # 姓名：
    # 身份：
    # 性格：
    # 核心动机：
  
  配角2: 
    # 【请填写】姓名、身份、性格、核心动机
    # 姓名：
    # 身份：
    # 性格：
    # 核心动机：

伏笔清单:
  # 【请填写】重要伏笔及其计划回收章节
  # - 伏笔1: [描述+计划回收章节]
  # - 伏笔2: [描述+计划回收章节]
  # - 伏笔3: [描述+计划回收章节]

# 补充设定（可选）
# 可以添加其他您认为重要的设定信息
"""
        
        core_setting_path = self.project_root / "01_source" / "core_setting.yaml"
        with open(core_setting_path, 'w', encoding='utf-8') as f:
            f.write(core_setting_template)
        print(f"📄 生成核心设定模板: {core_setting_path}")
        
        # 生成整体大纲模板
        overall_outline_template = """# 整体大纲模板
# 请根据您的小说创作需求填写以下内容

第一幕: 
  # 【请填写】章节范围+核心剧情
  # 例如：第1-15章，主角踏入江湖，初露锋芒

第二幕: 
  # 【请填写】章节范围+核心剧情
  # 例如：第16-40章，揭秘阴谋，势力角逐

第三幕: 
  # 【请填写】章节范围+核心剧情
  # 例如：第41-60章，最终对决，尘埃落定

关键转折点:
  # 【请填写】重要转折点及其章节
  # - 第X章: [具体事件，如"主角发现父亲秘密"]
  # - 第Y章: [具体事件，如"重要角色牺牲"]
  # - 第Z章: [具体事件，如"真相大白"]

# 章节规划（可选）
# 可以添加更详细的章节规划
# 第一章: [开篇介绍，主角背景]
# 第二章: [事件发生，主角行动]
# ...

# 故事主题（可选）
# 主题：
# 核心思想：
"""
        
        overall_outline_path = self.project_root / "01_source" / "overall_outline.yaml"
        with open(overall_outline_path, 'w', encoding='utf-8') as f:
            f.write(overall_outline_template)
        print(f"📄 生成整体大纲模板: {overall_outline_path}")
    
    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径，默认为05_script/config.json
            
        Returns:
            Dict[str, Any]: 配置信息
        """
        if config_path is None:
            config_path = self.project_root / "05_script" / "config.json"
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            return self.config
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            return {}
    
    def validate_project_structure(self) -> bool:
        """
        验证项目结构是否完整
        
        Returns:
            bool: 项目结构是否完整
        """
        required_files = [
            "01_source/core_setting.yaml",
            "01_source/overall_outline.yaml", 
            "04_prompt/chapter_expand_prompt.yaml",
            "04_prompt/style_guide.yaml",
            "05_script/config.json"
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                missing_files.append(file_path)
        
        if missing_files:
            print(f"❌ 缺少必要文件: {', '.join(missing_files)}")
            return False
        
        print("✅ 项目结构验证通过")
        return True
    
    def get_project_info(self) -> Dict[str, Any]:
        """
        获取项目信息
        
        Returns:
            Dict[str, Any]: 项目信息
        """
        return {
            "project_root": str(self.project_root),
            "created_at": datetime.now().isoformat(),
            "config": self.config
        }


def main():
    """主函数"""
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
    main()