"""
生成配置管理器
统一管理generation_config.json配置文件
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
import logging
import copy

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "version": "1.0",
    "generation": {
        "max_refine_iterations": 3,
        "pass_score_threshold": 70,
        "context_chapters": 10,
        "context_before_full": 10,
        "context_after_full": 5,
        "default_word_count": 1500,
        "batch_size": 15,
    },
    "roles": {
        "generator": {
            "name": "生成者",
            "description": "负责大纲生成、章节扩写等创作任务",
            "provider": "deepseek",
            "model": "deepseek-chat",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 8000,
            "enabled": True,
            "system_prompt": "你是一个专业的网络小说作家，擅长根据大纲创作引人入胜的章节内容。",
        },
        "reviewer": {
            "name": "评审者",
            "description": "负责质量检查、一致性检查等评审任务",
            "provider": "deepseek",
            "model": "deepseek-chat",
            "temperature": 0.3,
            "top_p": 0.7,
            "max_tokens": 4000,
            "enabled": True,
            "system_prompt": "你是一个专业的文学编辑，负责评审小说章节质量。",
        },
        "refiner": {
            "name": "润色者",
            "description": "负责内容润色、修复问题等优化任务",
            "provider": "doubao",
            "model": "doubao-seed-2-0-lite-260215",
            "temperature": 0.5,
            "top_p": 0.8,
            "max_tokens": 8000,
            "enabled": True,
            "system_prompt": "你是一个专业的文字润色专家。",
        },
    },
    "providers": {
        "deepseek": {
            "name": "DeepSeek",
            "api_base_url": "https://api.deepseek.com",
            "default_models": ["deepseek-chat", "deepseek-coder"],
        },
        "doubao": {
            "name": "豆包/火山引擎",
            "api_base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "default_models": ["doubao-seed-2-0-lite-260215"],
        },
    },
    "quality_check": {
        "banned_words": [
            "复杂的思绪",
            "难以言喻",
            "命运的齿轮",
            "心中五味杂陈",
            "一种莫名的",
            "仿佛",
            "似乎",
            "这一刻",
        ],
        "ai_patterns": ["一种莫名的", "仿佛", "似乎", "这一刻", "不由得", "不禁"],
    },
}


class GenerationConfigManager:
    CONFIG_FILE = "generation_config.json"
    CONFIG_DIR = "05_script"

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.config_path = self.project_root / self.CONFIG_DIR / self.CONFIG_FILE
        self._config: Optional[Dict[str, Any]] = None

    @property
    def config(self) -> Dict[str, Any]:
        if self._config is None:
            self._config = self.load()
        return self._config

    def load(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            logger.info(f"配置文件不存在，创建默认配置: {self.config_path}")
            self._create_default_config()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            config = self._merge_with_defaults(config)

            logger.info(f"加载配置文件成功: {self.config_path}")
            return config

        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return copy.deepcopy(DEFAULT_CONFIG)

    def save(self, config: Optional[Dict[str, Any]] = None) -> bool:
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            save_config = config or self._config or self.config

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(save_config, f, ensure_ascii=False, indent=2)

            self._config = save_config

            logger.info(f"配置文件已保存: {self.config_path}")
            return True

        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False

    def _create_default_config(self):
        self.save(copy.deepcopy(DEFAULT_CONFIG))

    def _merge_with_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        merged = copy.deepcopy(DEFAULT_CONFIG)

        if "generation" in config:
            merged["generation"].update(config["generation"])

        if "roles" in config:
            for role_name, role_config in config["roles"].items():
                if role_name in merged["roles"]:
                    merged["roles"][role_name].update(role_config)
                else:
                    merged["roles"][role_name] = role_config

        if "providers" in config:
            merged["providers"].update(config["providers"])

        if "quality_check" in config:
            merged["quality_check"].update(config["quality_check"])

        return merged

    def get_generation_config(self) -> Dict[str, Any]:
        return self.config.get("generation", DEFAULT_CONFIG["generation"])

    def get_role_config(self, role_name: str) -> Dict[str, Any]:
        roles = self.config.get("roles", DEFAULT_CONFIG["roles"])
        return roles.get(role_name, {})

    def get_all_roles_config(self) -> Dict[str, Any]:
        return self.config.get("roles", DEFAULT_CONFIG["roles"])

    def set_role_config(self, role_name: str, **kwargs) -> bool:
        if "roles" not in self._config:
            self._config["roles"] = {}

        if role_name not in self._config["roles"]:
            self._config["roles"][role_name] = copy.deepcopy(
                DEFAULT_CONFIG["roles"].get(role_name, {})
            )

        self._config["roles"][role_name].update(kwargs)
        return self.save()

    def set_generation_config(self, **kwargs) -> bool:
        if "generation" not in self._config:
            self._config["generation"] = {}

        self._config["generation"].update(kwargs)
        return self.save()

    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        providers = self.config.get("providers", DEFAULT_CONFIG["providers"])
        return providers.get(provider_name, {})

    def get_all_providers(self) -> Dict[str, str]:
        providers = self.config.get("providers", DEFAULT_CONFIG["providers"])
        return {k: v.get("name", k) for k, v in providers.items()}

    def get_provider_models(self, provider_name: str) -> list:
        provider = self.get_provider_config(provider_name)
        return provider.get("default_models", [])

    def get_banned_words(self) -> list:
        quality = self.config.get("quality_check", DEFAULT_CONFIG["quality_check"])
        return quality.get("banned_words", [])

    def get_ai_patterns(self) -> list:
        quality = self.config.get("quality_check", DEFAULT_CONFIG["quality_check"])
        return quality.get("ai_patterns", [])

    def set_banned_words(self, words: list) -> bool:
        if "quality_check" not in self._config:
            self._config["quality_check"] = {}
        self._config["quality_check"]["banned_words"] = words
        return self.save()

    def reset_to_default(self) -> bool:
        return self.save(copy.deepcopy(DEFAULT_CONFIG))

    def export_config(self, export_path: str) -> bool:
        try:
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            return False

    def import_config(self, import_path: str) -> bool:
        try:
            with open(import_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            merged = self._merge_with_defaults(config)
            return self.save(merged)

        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            return False


def get_generation_config_manager(project_root: str = ".") -> GenerationConfigManager:
    return GenerationConfigManager(project_root)
