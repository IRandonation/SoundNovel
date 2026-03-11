"""
项目管理器
负责项目的初始化、配置管理和目录结构维护
"""

import os
import json
import yaml
import requests
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
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
        
    def initialize_project(self, force: bool = False, interactive: bool = False) -> bool:
        self._create_directory_structure()
        self._generate_config_files(interactive=interactive)
        self._generate_template_files()
        print(f"✅ 项目初始化成功！项目根目录: {self.project_root}")
        return True
    
    def _create_directory_structure(self):
        """创建项目目录结构"""
        directories = [
            "01_source",
            "02_outline",
            "03_draft",
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
    
    def _generate_config_files(self, interactive: bool = False):
        config_template = {
            "api_key": "",
            "api_base_url": "https://open.bigmodel.cn/api/paas/v4",
            "doubao_api_key": "",
            "doubao_api_base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "ark_api_key": "",
            "models": {
                "logic_analysis_model": "glm-4-long",
                "major_chapters_model": "glm-4-long",
                "sub_chapters_model": "glm-4-long", 
                "expansion_model": "glm-4.5-flash",
                "default_model": "glm-4.5-flash"
            },
            "doubao_models": {
                "logic_analysis_model": "",
                "major_chapters_model": "",
                "sub_chapters_model": "",
                "expansion_model": "",
                "default_model": ""
            },
            "default_model": "zhipu",
            "available_models": ["zhipu", "doubao", "ark"],
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
                "context_chapters": 10,
                "default_word_count": 1500
            },
            "quality_gate": {
                "min_ratio": 0.55,
                "max_ratio": 1.9,
                "min_score": 70,
                "banned_words": ["复杂的思绪", "难以言喻", "命运的齿轮", "心中五味杂陈"]
            }
        }
        
        config_path = self.project_root / "05_script" / "config.json"
        
        if interactive:
            print("\n" + "=" * 50)
            print("📝 API 配置向导")
            print("=" * 50)
            print("\n请选择要使用的 AI 服务商：")
            print("  1. 智谱 AI (ZhipuAI) - 推荐")
            print("  2. 豆包 (Doubao)")
            print("  3. 跳过配置（稍后手动填写）")
            
            choice = input("\n请输入选择 [1/2/3]: ").strip()
            
            if choice == "1":
                # 智谱 AI 配置
                print("\n--- 智谱 AI 配置 ---")
                print("默认 API 地址: https://open.bigmodel.cn/api/paas/v4")
                
                custom_url = input("使用自定义 API 地址? [y/N]: ").strip().lower()
                if custom_url in ('y', 'yes'):
                    api_url = input("请输入 API 地址: ").strip()
                    if api_url:
                        config_template["api_base_url"] = api_url
                
                api_key = input("请输入智谱 API Key: ").strip()
                if api_key:
                    config_template["api_key"] = api_key
                    
                    # 测试连接
                    print("\n🔌 正在测试连接...")
                    success, message = self._test_zhipu_connection(
                        api_key, 
                        config_template["api_base_url"]
                    )
                    if success:
                        print(f"✅ 连接成功！{message}")
                        config_template["default_model"] = "zhipu"
                    else:
                        print(f"❌ 连接失败: {message}")
                        print("   配置已保存，请检查 API Key 是否正确")
                else:
                    print("⚠️  未输入 API Key，请稍后手动配置")
                    
            elif choice == "2":
                # 豆包配置
                print("\n--- 豆包 (Doubao) 配置 ---")
                print("默认 API 地址: https://ark.cn-beijing.volces.com/api/v3")
                
                custom_url = input("使用自定义 API 地址? [y/N]: ").strip().lower()
                if custom_url in ('y', 'yes'):
                    api_url = input("请输入 API 地址: ").strip()
                    if api_url:
                        config_template["doubao_api_base_url"] = api_url
                
                api_key = input("请输入豆包 API Key: ").strip()
                if api_key:
                    config_template["doubao_api_key"] = api_key
                    
                    endpoint = input("请输入 Endpoint ID (如: ep-2024xxxx): ").strip()
                    if endpoint:
                        for key in config_template["doubao_models"]:
                            config_template["doubao_models"][key] = endpoint
                    
                    # 测试连接
                    print("\n🔌 正在测试连接...")
                    success, message = self._test_doubao_connection(
                        api_key,
                        config_template["doubao_api_base_url"],
                        endpoint if endpoint else ""
                    )
                    if success:
                        print(f"✅ 连接成功！{message}")
                        config_template["default_model"] = "doubao"
                    else:
                        print(f"❌ 连接失败: {message}")
                        print("   配置已保存，请检查 API Key 和 Endpoint 是否正确")
                else:
                    print("⚠️  未输入 API Key，请稍后手动配置")
                    
            else:
                print("\n⏭️  跳过 API 配置，请稍后手动编辑 config.json")
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_template, f, ensure_ascii=False, indent=2)
        print(f"\n📄 配置文件已生成: {config_path}")
    
    def _test_zhipu_connection(self, api_key: str, api_base_url: str) -> Tuple[bool, str]:
        """
        测试智谱 AI 连接
        
        Args:
            api_key: API 密钥
            api_base_url: API 基础 URL
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # 发送一个简单的测试请求
            test_data = {
                "model": "glm-4-flash",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 10
            }
            
            response = requests.post(
                f"{api_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=test_data,
                timeout=10
            )
            
            if response.status_code == 200:
                return True, "API 连接正常"
            elif response.status_code == 401:
                return False, "API Key 无效"
            elif response.status_code == 403:
                return False, "访问被拒绝，请检查 API Key 权限"
            else:
                return False, f"HTTP 错误: {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, "连接超时，请检查网络"
        except requests.exceptions.ConnectionError:
            return False, "无法连接服务器，请检查网络和 API 地址"
        except Exception as e:
            return False, f"测试失败: {str(e)}"
    
    def _test_doubao_connection(self, api_key: str, api_base_url: str, endpoint: str) -> Tuple[bool, str]:
        """
        测试豆包连接
        
        Args:
            api_key: API 密钥
            api_base_url: API 基础 URL
            endpoint: Endpoint ID
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            if not endpoint:
                return False, "未提供 Endpoint ID"
                
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            test_data = {
                "model": endpoint,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 10
            }
            
            response = requests.post(
                f"{api_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=test_data,
                timeout=10
            )
            
            if response.status_code == 200:
                return True, "API 连接正常"
            elif response.status_code == 401:
                return False, "API Key 无效"
            elif response.status_code == 404:
                return False, "Endpoint 不存在，请检查 Endpoint ID"
            else:
                return False, f"HTTP 错误: {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, "连接超时，请检查网络"
        except requests.exceptions.ConnectionError:
            return False, "无法连接服务器，请检查网络和 API 地址"
        except Exception as e:
            return False, f"测试失败: {str(e)}"

    def update_api_config(self, provider: str, api_key: str, api_url: str = None, 
                          endpoint: str = None) -> Tuple[bool, str]:
        """
        更新 API 配置并测试连接
        
        Args:
            provider: 服务商 ('zhipu', 'doubao', 'ark')
            api_key: API 密钥
            api_url: API 基础 URL（可选）
            endpoint: Endpoint ID（豆包/Ark需要）
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        config_path = self.project_root / "05_script" / "config.json"
        
        try:
            # 加载现有配置
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 更新配置
            if provider == 'zhipu':
                config['api_key'] = api_key
                if api_url:
                    config['api_base_url'] = api_url
                    
                # 测试连接
                success, message = self._test_zhipu_connection(
                    api_key, 
                    config.get('api_base_url', 'https://open.bigmodel.cn/api/paas/v4')
                )
                
                if success:
                    config['default_model'] = 'zhipu'
                    
            elif provider == 'doubao':
                config['doubao_api_key'] = api_key
                if api_url:
                    config['doubao_api_base_url'] = api_url
                if endpoint:
                    for key in config.get('doubao_models', {}):
                        config['doubao_models'][key] = endpoint
                        
                # 测试连接
                success, message = self._test_doubao_connection(
                    api_key,
                    config.get('doubao_api_base_url', 'https://ark.cn-beijing.volces.com/api/v3'),
                    endpoint or ""
                )
                
                if success:
                    config['default_model'] = 'doubao'
                    
            elif provider == 'ark':
                config['ark_api_key'] = api_key
                success, message = True, "配置已保存"
                config['default_model'] = 'ark'
            else:
                return False, f"未知的服务商: {provider}"
            
            # 保存配置
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            return success, message
            
        except Exception as e:
            return False, f"更新配置失败: {str(e)}"

    def test_api_connection(self, provider: str = None) -> Dict[str, Tuple[bool, str]]:
        """
        测试 API 连接
        
        Args:
            provider: 指定服务商测试，为 None 则测试所有已配置的服务商
            
        Returns:
            Dict[str, Tuple[bool, str]]: 服务商 -> (是否成功, 消息)
        """
        config_path = self.project_root / "05_script" / "config.json"
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except:
            return {"error": (False, "无法读取配置文件")}
        
        results = {}
        
        # 测试智谱
        if provider in (None, 'zhipu') and config.get('api_key'):
            results['zhipu'] = self._test_zhipu_connection(
                config['api_key'],
                config.get('api_base_url', 'https://open.bigmodel.cn/api/paas/v4')
            )
        
        # 测试豆包
        if provider in (None, 'doubao') and config.get('doubao_api_key'):
            endpoint = config.get('doubao_models', {}).get('default_model', '')
            results['doubao'] = self._test_doubao_connection(
                config['doubao_api_key'],
                config.get('doubao_api_base_url', 'https://ark.cn-beijing.volces.com/api/v3'),
                endpoint
            )
        
        return results
    
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