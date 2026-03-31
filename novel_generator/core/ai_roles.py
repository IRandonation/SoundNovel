"""
AI角色管理器
管理三个AI角色：Generator/Reviewer/Refiner
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
import logging
import copy

from novel_generator.config.ai_roles import AIRoleConfig, AIRolesConfig


class AIRole(Enum):
    GENERATOR = "generator"
    REVIEWER = "reviewer"
    REFINER = "refiner"


DEFAULT_ROLE_CONFIGS = {
    AIRole.GENERATOR: {
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 8000,
        "provider": "doubao",
        "model": "doubao-seed-2-0-lite-260215",
    },
    AIRole.REVIEWER: {
        "temperature": 0.3,
        "top_p": 0.7,
        "max_tokens": 4000,
        "provider": "deepseek",
        "model": "deepseek-chat",
    },
    AIRole.REFINER: {
        "temperature": 0.5,
        "top_p": 0.8,
        "max_tokens": 8000,
        "provider": "doubao",
        "model": "doubao-seed-2-0-lite-260215",
    },
}


class AIRoleManager:
    def __init__(self, config: Dict[str, Any], multi_model_client=None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.multi_model_client = multi_model_client

        roles_config_data = config.get("ai_roles", {})
        self.roles_config = AIRolesConfig.from_dict(roles_config_data)

    def get_role_config(self, role: AIRole) -> AIRoleConfig:
        return self.roles_config.get_role_config(role.value)

    def set_role_config(self, role: AIRole, config: AIRoleConfig):
        self.roles_config.set_role_config(role.value, config)

    def update_role_config(self, role: AIRole, **kwargs):
        config = self.get_role_config(role)
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

    def get_roles_config_dict(self) -> Dict[str, Any]:
        return self.roles_config.to_dict()

    def chat_completion(
        self, role: AIRole, messages: List[Dict[str, str]], **kwargs
    ) -> str:
        if not self.multi_model_client:
            raise ValueError("MultiModelClient 未初始化")

        role_config = self.get_role_config(role)

        if not role_config.enabled:
            self.logger.warning(f"角色 {role.value} 已禁用，使用生成者角色代替")
            role_config = self.get_role_config(AIRole.GENERATOR)

        enhanced_messages = messages.copy()

        if enhanced_messages and enhanced_messages[0].get("role") != "system":
            if role_config.system_prompt:
                enhanced_messages.insert(
                    0, {"role": "system", "content": role_config.system_prompt}
                )

        completion_kwargs = {
            "model_type": role_config.provider,
            "model": role_config.model if role_config.model else None,
            "temperature": kwargs.pop("temperature", role_config.temperature),
            "top_p": kwargs.pop("top_p", role_config.top_p),
            "max_tokens": kwargs.pop("max_tokens", role_config.max_tokens),
            **kwargs,
        }

        self.logger.info(
            f"使用角色 {role.value} 进行调用 (provider: {role_config.provider}, model: {role_config.model})"
        )

        return self.multi_model_client.chat_completion(
            messages=enhanced_messages, **completion_kwargs
        )


def get_ai_role_manager(
    config: Dict[str, Any], multi_model_client=None
) -> AIRoleManager:
    return AIRoleManager(config, multi_model_client)
