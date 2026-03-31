"""
AI角色配置管理
统一管理AIRoleConfig和AIRolesConfig
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class AIRoleConfig:
    provider: str = "doubao"
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
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AIRoleConfig":
        return cls(
            provider=data.get("provider", "doubao"),
            model=data.get("model", ""),
            temperature=data.get("temperature", 0.7),
            top_p=data.get("top_p", 0.9),
            max_tokens=data.get("max_tokens", 8000),
            system_prompt=data.get("system_prompt", ""),
            enabled=data.get("enabled", True),
        )


@dataclass
class AIRolesConfig:
    generator: AIRoleConfig = field(
        default_factory=lambda: AIRoleConfig(
            provider="doubao",
            model="doubao-seed-2-0-lite-260215",
            temperature=0.7,
            top_p=0.9,
            max_tokens=8000,
        )
    )
    reviewer: AIRoleConfig = field(
        default_factory=lambda: AIRoleConfig(
            provider="deepseek",
            model="deepseek-chat",
            temperature=0.3,
            top_p=0.7,
            max_tokens=4000,
        )
    )
    refiner: AIRoleConfig = field(
        default_factory=lambda: AIRoleConfig(
            provider="doubao",
            model="doubao-seed-2-0-lite-260215",
            temperature=0.5,
            top_p=0.8,
            max_tokens=8000,
        )
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generator": self.generator.to_dict(),
            "reviewer": self.reviewer.to_dict(),
            "refiner": self.refiner.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AIRolesConfig":
        config = cls()
        if "generator" in data:
            config.generator = AIRoleConfig.from_dict(data["generator"])
        if "reviewer" in data:
            config.reviewer = AIRoleConfig.from_dict(data["reviewer"])
        if "refiner" in data:
            config.refiner = AIRoleConfig.from_dict(data["refiner"])
        return config

    def get_role_config(self, role_name: str) -> AIRoleConfig:
        if role_name == "generator":
            return self.generator
        elif role_name == "reviewer":
            return self.reviewer
        elif role_name == "refiner":
            return self.refiner
        return self.generator

    def set_role_config(self, role_name: str, config: AIRoleConfig):
        if role_name == "generator":
            self.generator = config
        elif role_name == "reviewer":
            self.reviewer = config
        elif role_name == "refiner":
            self.refiner = config