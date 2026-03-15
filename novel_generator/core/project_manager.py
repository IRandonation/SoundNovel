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

from novel_generator.config.session import SessionManager, SessionState


class ProjectManager:
    """项目管理器类"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.config = {}
        self.logger = None
        self.session_manager = SessionManager(str(self.project_root))

    def initialize_project(self) -> bool:
        self._create_directory_structure()
        self._generate_session_file()
        self._generate_template_files()
        print(f"✅ 项目初始化成功！项目根目录：{self.project_root}")
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
            "06_log/system_logs",
        ]

        for directory in directories:
            dir_path = self.project_root / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"📁 创建目录: {dir_path}")

    def _generate_session_file(self):
        self.session_manager.save()
        print(f"\n📄 会话文件已生成：{self.session_manager.session_file_path}")
        print("   提示：运行 'soundnovel settings --interactive' 配置 API Key 和模型")

    def _test_doubao_connection(
        self, api_key: str, api_base_url: str, model: str
    ) -> Tuple[bool, str]:
        try:
            if not model:
                return False, "未提供模型名称"

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            test_data = {
                "model": model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 10,
            }

            response = requests.post(
                f"{api_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=test_data,
                timeout=15,
            )

            if response.status_code == 200:
                return True, "API 连接正常"
            elif response.status_code == 401:
                return False, "API Key 无效"
            elif response.status_code == 404:
                return (
                    False,
                    "模型不存在，请检查模型名称（支持直接模型名如 doubao-seed-2-0-lite-260215 或 Endpoint ID 如 ep-2024xxxx）",
                )
            else:
                try:
                    error_detail = (
                        response.json()
                        .get("error", {})
                        .get("message", response.text[:200])
                    )
                except:
                    error_detail = response.text[:200]
                return False, f"HTTP {response.status_code}: {error_detail}"

        except requests.exceptions.Timeout:
            return False, "连接超时，请检查网络"
        except requests.exceptions.ConnectionError:
            return False, "无法连接服务器，请检查网络和 API 地址"
        except Exception as e:
            return False, f"测试失败: {str(e)}"

    def _test_deepseek_connection(
        self, api_key: str, api_base_url: str
    ) -> Tuple[bool, str]:
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            test_data = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 10,
            }

            response = requests.post(
                f"{api_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=test_data,
                timeout=15,
            )

            if response.status_code == 200:
                return True, "API 连接正常"
            elif response.status_code == 401:
                return False, "API Key 无效"
            elif response.status_code == 403:
                return False, "访问被拒绝，请检查 API Key 权限"
            else:
                try:
                    error_detail = (
                        response.json()
                        .get("error", {})
                        .get("message", response.text[:200])
                    )
                except:
                    error_detail = response.text[:200]
                return False, f"HTTP {response.status_code}: {error_detail}"

        except requests.exceptions.Timeout:
            return False, "连接超时，请检查网络"
        except requests.exceptions.ConnectionError:
            return False, "无法连接服务器，请检查网络和 API 地址"
        except Exception as e:
            return False, f"测试失败: {str(e)}"

    def update_api_config(
        self,
        provider: str,
        api_key: str,
        api_url: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> Tuple[bool, str]:
        session = self.session_manager.state
        session.api_config.provider = provider

        if provider == "doubao":
            session.api_config.doubao_api_key = api_key
            if api_url:
                session.api_config.doubao_api_base_url = api_url
            else:
                session.api_config.doubao_api_base_url = (
                    "https://ark.cn-beijing.volces.com/api/v3"
                )

            if endpoint:
                for key in session.api_config.doubao_models:
                    session.api_config.doubao_models[key] = endpoint

            model = endpoint or session.api_config.doubao_models.get(
                "default_model", ""
            )
            success, message = self._test_doubao_connection(
                api_key, session.api_config.doubao_api_base_url, model
            )

        elif provider == "deepseek":
            session.api_config.deepseek_api_key = api_key
            if api_url:
                session.api_config.deepseek_api_base_url = api_url
            else:
                session.api_config.deepseek_api_base_url = "https://api.deepseek.com"

            success, message = self._test_deepseek_connection(
                api_key, session.api_config.deepseek_api_base_url
            )
        else:
            return False, f"未知的服务商: {provider}"

        self.session_manager.save()
        return success, message

    def test_api_connection(
        self, provider: Optional[str] = None
    ) -> Dict[str, Tuple[bool, str]]:
        session = self.session_manager.state
        results = {}

        if provider in (None, "doubao") and session.api_config.doubao_api_key:
            if session.api_config.provider == "doubao":
                endpoint = session.api_config.doubao_models.get("default_model", "")
                results["doubao"] = self._test_doubao_connection(
                    session.api_config.doubao_api_key,
                    session.api_config.doubao_api_base_url,
                    endpoint,
                )

        if provider in (None, "deepseek") and session.api_config.deepseek_api_key:
            if session.api_config.provider == "deepseek":
                results["deepseek"] = self._test_deepseek_connection(
                    session.api_config.deepseek_api_key,
                    session.api_config.deepseek_api_base_url,
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
        with open(core_setting_path, "w", encoding="utf-8") as f:
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
        with open(overall_outline_path, "w", encoding="utf-8") as f:
            f.write(overall_outline_template)
        print(f"📄 生成整体大纲模板: {overall_outline_path}")

    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        if config_path is None:
            return self.session_manager.get_api_config()

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
            return self.config
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            return self.session_manager.get_api_config()

    def validate_project_structure(self) -> bool:
        required_files = [
            "01_source/core_setting.yaml",
            "01_source/overall_outline.yaml",
            "04_prompt/chapter_expand_prompt.yaml",
            "04_prompt/style_guide.yaml",
            "05_script/session.json",
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
            "config": self.config,
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
