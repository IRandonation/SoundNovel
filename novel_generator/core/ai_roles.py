"""
AI角色管理器
管理三个AI角色：Generator/Reviewer/Refiner
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
import logging
import copy


class AIRole(Enum):
    GENERATOR = "generator"
    REVIEWER = "reviewer"
    REFINER = "refiner"


DEFAULT_ROLE_CONFIGS = {
    AIRole.GENERATOR: {
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 8000,
        "provider": "zhipu",
        "model": "glm-4.5-flash"
    },
    AIRole.REVIEWER: {
        "temperature": 0.3,
        "top_p": 0.7,
        "max_tokens": 4000,
        "provider": "deepseek",
        "model": "deepseek-chat"
    },
    AIRole.REFINER: {
        "temperature": 0.5,
        "top_p": 0.8,
        "max_tokens": 8000,
        "provider": "zhipu",
        "model": "glm-4-long"
    }
}


@dataclass
class RoleConfig:
    provider: str = "zhipu"
    model: str = ""
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 8000
    system_prompt: str = ""
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "system_prompt": self.system_prompt,
            "enabled": self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoleConfig":
        return cls(
            provider=data.get("provider", "zhipu"),
            model=data.get("model", ""),
            temperature=data.get("temperature", 0.7),
            top_p=data.get("top_p", 0.9),
            max_tokens=data.get("max_tokens", 8000),
            system_prompt=data.get("system_prompt", ""),
            enabled=data.get("enabled", True)
        )


@dataclass
class AIRolesConfig:
    generator: RoleConfig = field(default_factory=lambda: RoleConfig(
        provider="zhipu", model="glm-4.5-flash", temperature=0.7, top_p=0.9, max_tokens=8000
    ))
    reviewer: RoleConfig = field(default_factory=lambda: RoleConfig(
        provider="deepseek", model="deepseek-chat", temperature=0.3, top_p=0.7, max_tokens=4000
    ))
    refiner: RoleConfig = field(default_factory=lambda: RoleConfig(
        provider="zhipu", model="glm-4-long", temperature=0.5, top_p=0.8, max_tokens=8000
    ))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "generator": self.generator.to_dict(),
            "reviewer": self.reviewer.to_dict(),
            "refiner": self.refiner.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AIRolesConfig":
        config = cls()
        if "generator" in data:
            config.generator = RoleConfig.from_dict(data["generator"])
        if "reviewer" in data:
            config.reviewer = RoleConfig.from_dict(data["reviewer"])
        if "refiner" in data:
            config.refiner = RoleConfig.from_dict(data["refiner"])
        return config
    
    def get_role_config(self, role: AIRole) -> RoleConfig:
        if role == AIRole.GENERATOR:
            return self.generator
        elif role == AIRole.REVIEWER:
            return self.reviewer
        elif role == AIRole.REFINER:
            return self.refiner
        return self.generator
    
    def set_role_config(self, role: AIRole, config: RoleConfig):
        if role == AIRole.GENERATOR:
            self.generator = config
        elif role == AIRole.REVIEWER:
            self.reviewer = config
        elif role == AIRole.REFINER:
            self.refiner = config


class AIRoleManager:
    
    def __init__(self, config: Dict[str, Any], multi_model_client=None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.multi_model_client = multi_model_client
        
        roles_config_data = config.get("ai_roles", {})
        self.roles_config = AIRolesConfig.from_dict(roles_config_data)
    
    def get_role_config(self, role: AIRole) -> RoleConfig:
        return self.roles_config.get_role_config(role)
    
    def set_role_config(self, role: AIRole, config: RoleConfig):
        self.roles_config.set_role_config(role, config)
    
    def update_role_config(self, role: AIRole, **kwargs):
        config = self.get_role_config(role)
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
    
    def get_roles_config_dict(self) -> Dict[str, Any]:
        return self.roles_config.to_dict()
    
    def chat_completion(
        self,
        role: AIRole,
        messages: List[Dict[str, str]],
        **kwargs
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
                enhanced_messages.insert(0, {
                    "role": "system",
                    "content": role_config.system_prompt
                })
        
        completion_kwargs = {
            "model_type": role_config.provider,
            "model": role_config.model if role_config.model else None,
            "temperature": kwargs.pop("temperature", role_config.temperature),
            "top_p": kwargs.pop("top_p", role_config.top_p),
            "max_tokens": kwargs.pop("max_tokens", role_config.max_tokens),
            **kwargs
        }
        
        self.logger.info(f"使用角色 {role.value} 进行调用 (provider: {role_config.provider}, model: {role_config.model})")
        
        return self.multi_model_client.chat_completion(
            messages=enhanced_messages,
            **completion_kwargs
        )


def get_ai_role_manager(config: Dict[str, Any], multi_model_client=None) -> AIRoleManager:
    return AIRoleManager(config, multi_model_client)