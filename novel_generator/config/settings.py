"""
配置管理器
负责管理项目配置和API设置
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List


@dataclass
class AIRoleConfig:
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
    def from_dict(cls, data: Dict[str, Any]) -> "AIRoleConfig":
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
    generator: AIRoleConfig = field(default_factory=lambda: AIRoleConfig(
        provider="zhipu", model="glm-4.5-flash", temperature=0.7, top_p=0.9, max_tokens=8000
    ))
    reviewer: AIRoleConfig = field(default_factory=lambda: AIRoleConfig(
        provider="deepseek", model="deepseek-chat", temperature=0.3, top_p=0.7, max_tokens=4000
    ))
    refiner: AIRoleConfig = field(default_factory=lambda: AIRoleConfig(
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


@dataclass
class APIConfig:
    """API配置类"""
    # 智谱AI配置
    api_key: str = ""
    api_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    models: Dict[str, str] = field(default_factory=lambda: {
        "logic_analysis_model": "glm-4-long",
        "major_chapters_model": "glm-4-long",
        "sub_chapters_model": "glm-4-long",
        "expansion_model": "glm-4.5-flash",
        "default_model": "glm-4.5-flash"
    })
    
# 豆包配置
    doubao_api_key: str = ""
    doubao_api_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    doubao_models: Dict[str, str] = field(default_factory=lambda: {
        "logic_analysis_model": "doubao-1-5-lite-32k-250115",
        "major_chapters_model": "doubao-1-5-lite-32k-250115",
        "sub_chapters_model": "doubao-1-5-lite-32k-250115",
        "expansion_model": "doubao-1-5-lite-32k-250115",
        "default_model": "doubao-1-5-lite-32k-250115"
    })
    
    # 火山引擎Ark配置
    ark_api_key: str = ""
    ark_models: Dict[str, str] = field(default_factory=lambda: {
        "logic_analysis_model": "ep-20241210233657-lz8fv",
        "major_chapters_model": "ep-20241210233657-lz8fv",
        "sub_chapters_model": "ep-20241210233657-lz8fv",
        "expansion_model": "ep-20241210233657-lz8fv",
        "default_model": "ep-20241210233657-lz8fv"
    })
    
    # DeepSeek配置
    deepseek_api_key: str = ""
    deepseek_api_base_url: str = "https://api.deepseek.com"
    deepseek_models: Dict[str, str] = field(default_factory=lambda: {
        "logic_analysis_model": "deepseek-chat",
        "major_chapters_model": "deepseek-chat",
        "sub_chapters_model": "deepseek-chat",
        "expansion_model": "deepseek-chat",
        "default_model": "deepseek-chat"
    })
    
    # 多模型配置
    default_model: str = "zhipu"  # 默认使用智谱AI
    available_models: List[str] = field(default_factory=lambda: ["zhipu", "doubao", "ark", "deepseek"])
    
    # 通用配置
    max_tokens: int = 8000
    temperature: float = 0.7
    top_p: float = 0.7
    max_retries: int = 5
    retry_delay: int = 2
    timeout: int = 120


@dataclass
class SystemConfig:
    """系统配置类"""
    logging_level: str = "INFO"
    log_file: str = "06_log/novel_generator.log"
    backup_enabled: bool = True
    backup_history: int = 10  # 保留最近10个备份


@dataclass
class PathConfig:
    """路径配置类"""
    project_root: str = "."
    core_setting_file: str = "01_source/core_setting.yaml"
    outline_dir: str = "02_outline/"
    draft_dir: str = "03_draft/"
    prompt_dir: str = "04_prompt/"
    log_dir: str = "06_log/"
    api_log_dir: str = "06_log/ai_api_logs/"
    system_log_dir: str = "06_log/system_logs/"


@dataclass
class GenerationConfig:
    """生成配置类"""
    stage1_use_long_model: bool = True
    stage2_use_long_model: bool = True
    stage3_use_regular_model: bool = True
    stage4_use_regular_model: bool = True
    stage5_use_regular_model: bool = True
    context_chapters: int = 10
    default_word_count: int = 1500
    copyright_bypass: bool = True
    world_style: str = ""


class Settings:
    """配置管理器"""
    
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        self.api_config = APIConfig()
        self.system_config = SystemConfig()
        self.path_config = PathConfig()
        self.generation_config = GenerationConfig()
        self.ai_roles_config = AIRolesConfig()
        
        if config_dict:
            self.load_from_dict(config_dict)
    
    def load_from_dict(self, config_dict: Dict[str, Any]):
        """从字典加载配置"""
        # 加载智谱AI配置
        if "api_key" in config_dict:
            self.api_config.api_key = config_dict["api_key"]
        if "api_base_url" in config_dict:
            self.api_config.api_base_url = config_dict["api_base_url"]
        if "models" in config_dict:
            self.api_config.models.update(config_dict["models"])
        
        # 加载豆包配置
        if "doubao_api_key" in config_dict:
            self.api_config.doubao_api_key = config_dict["doubao_api_key"]
        if "doubao_api_base_url" in config_dict:
            self.api_config.doubao_api_base_url = config_dict["doubao_api_base_url"]
        if "doubao_models" in config_dict:
            self.api_config.doubao_models.update(config_dict["doubao_models"])
        
        # 加载Ark配置
        if "ark_api_key" in config_dict:
            self.api_config.ark_api_key = config_dict["ark_api_key"]
        if "ark_models" in config_dict:
            self.api_config.ark_models.update(config_dict["ark_models"])
        
        # 加载DeepSeek配置
        if "deepseek_api_key" in config_dict:
            self.api_config.deepseek_api_key = config_dict["deepseek_api_key"]
        if "deepseek_api_base_url" in config_dict:
            self.api_config.deepseek_api_base_url = config_dict["deepseek_api_base_url"]
        if "deepseek_models" in config_dict:
            self.api_config.deepseek_models.update(config_dict["deepseek_models"])
        
        # 加载多模型配置
        if "default_model" in config_dict:
            self.api_config.default_model = config_dict["default_model"]
        if "available_models" in config_dict:
            self.api_config.available_models = config_dict["available_models"]
        
        # 加载通用配置
        if "max_tokens" in config_dict:
            self.api_config.max_tokens = config_dict["max_tokens"]
        if "temperature" in config_dict:
            self.api_config.temperature = config_dict["temperature"]
        if "top_p" in config_dict:
            self.api_config.top_p = config_dict["top_p"]
        if "system" in config_dict and "api" in config_dict["system"]:
            api_system = config_dict["system"]["api"]
            if "max_retries" in api_system:
                self.api_config.max_retries = api_system["max_retries"]
            if "retry_delay" in api_system:
                self.api_config.retry_delay = api_system["retry_delay"]
            if "timeout" in api_system:
                self.api_config.timeout = api_system["timeout"]
        
        # 加载系统配置
        if "system" in config_dict and "logging" in config_dict["system"]:
            logging_config = config_dict["system"]["logging"]
            if "level" in logging_config:
                self.system_config.logging_level = logging_config["level"]
            if "file" in logging_config:
                self.system_config.log_file = logging_config["file"]
        
        # 加载路径配置
        if "paths" in config_dict:
            paths = config_dict["paths"]
            if "core_setting" in paths:
                self.path_config.core_setting_file = paths["core_setting"]
            if "outline_dir" in paths:
                self.path_config.outline_dir = paths["outline_dir"]
            if "draft_dir" in paths:
                self.path_config.draft_dir = paths["draft_dir"]
            if "prompt_dir" in paths:
                self.path_config.prompt_dir = paths["prompt_dir"]
            if "log_dir" in paths:
                self.path_config.log_dir = paths["log_dir"]
        
        # 加载生成配置
        if "novel_generation" in config_dict:
            gen_config = config_dict["novel_generation"]
            if "stage1_use_long_model" in gen_config:
                self.generation_config.stage1_use_long_model = gen_config["stage1_use_long_model"]
            if "stage2_use_long_model" in gen_config:
                self.generation_config.stage2_use_long_model = gen_config["stage2_use_long_model"]
            if "stage3_use_regular_model" in gen_config:
                self.generation_config.stage3_use_regular_model = gen_config["stage3_use_regular_model"]
            if "stage4_use_regular_model" in gen_config:
                self.generation_config.stage4_use_regular_model = gen_config["stage4_use_regular_model"]
            if "stage5_use_regular_model" in gen_config:
                self.generation_config.stage5_use_regular_model = gen_config["stage5_use_regular_model"]
            if "context_chapters" in gen_config:
                self.generation_config.context_chapters = gen_config["context_chapters"]
            if "default_word_count" in gen_config:
                self.generation_config.default_word_count = gen_config["default_word_count"]
            if "copyright_bypass" in gen_config:
                self.generation_config.copyright_bypass = gen_config["copyright_bypass"]
            if "world_style" in gen_config:
                self.generation_config.world_style = gen_config["world_style"]
        
        if "ai_roles" in config_dict:
            self.ai_roles_config = AIRolesConfig.from_dict(config_dict["ai_roles"])
    
    def load_from_file(self, file_path: str):
        """
        从文件加载配置
        
        Args:
            file_path: 配置文件路径
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            self.load_from_dict(config_dict)
        except Exception as e:
            raise Exception(f"加载配置文件失败: {e}")
    
    def save_to_file(self, file_path: str):
        """
        保存配置到文件
        
        Args:
            file_path: 配置文件路径
        """
        try:
            config_dict = self.to_dict()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise Exception(f"保存配置文件失败: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            # 智谱AI配置
            "api_key": self.api_config.api_key,
            "api_base_url": self.api_config.api_base_url,
            "models": self.api_config.models,
            
            # 豆包配置
            "doubao_api_key": self.api_config.doubao_api_key,
            "doubao_api_base_url": self.api_config.doubao_api_base_url,
            "doubao_models": self.api_config.doubao_models,
            
            # Ark配置
            "ark_api_key": self.api_config.ark_api_key,
            "ark_models": self.api_config.ark_models,
            
            # DeepSeek配置
            "deepseek_api_key": self.api_config.deepseek_api_key,
            "deepseek_api_base_url": self.api_config.deepseek_api_base_url,
            "deepseek_models": self.api_config.deepseek_models,
            
            # 多模型配置
            "default_model": self.api_config.default_model,
            "available_models": self.api_config.available_models,
            
            # 通用配置
            "max_tokens": self.api_config.max_tokens,
            "temperature": self.api_config.temperature,
            "top_p": self.api_config.top_p,
            "system": {
                "api": {
                    "max_retries": self.api_config.max_retries,
                    "retry_delay": self.api_config.retry_delay,
                    "timeout": self.api_config.timeout
                },
                "logging": {
                    "level": self.system_config.logging_level,
                    "file": self.system_config.log_file
                }
            },
            "paths": {
                "core_setting": self.path_config.core_setting_file,
                "outline_dir": self.path_config.outline_dir,
                "draft_dir": self.path_config.draft_dir,
                "prompt_dir": self.path_config.prompt_dir,
                "log_dir": self.path_config.log_dir
            },
            "novel_generation": {
                "stage1_use_long_model": self.generation_config.stage1_use_long_model,
                "stage2_use_long_model": self.generation_config.stage2_use_long_model,
                "stage3_use_regular_model": self.generation_config.stage3_use_regular_model,
                "stage4_use_regular_model": self.generation_config.stage4_use_regular_model,
                "stage5_use_regular_model": self.generation_config.stage5_use_regular_model,
                "context_chapters": self.generation_config.context_chapters,
                "default_word_count": self.generation_config.default_word_count,
                "copyright_bypass": self.generation_config.copyright_bypass,
                "world_style": self.generation_config.world_style
            },
            "ai_roles": self.ai_roles_config.to_dict()
        }
    
    def validate(self) -> bool:
        """验证配置有效性"""
        has_valid_api = (
            self.api_config.api_key or
            self.api_config.doubao_api_key or
            self.api_config.ark_api_key or
            self.api_config.deepseek_api_key
        )
        
        if not has_valid_api:
            raise Exception("API密钥未配置（请配置智谱/豆包/Ark 任一服务商的API密钥）")
        
        # 验证路径配置
        if not self.path_config.core_setting_file:
            raise Exception("核心设定文件路径未配置")
        
        return True
    
    def get_api_model(self, stage: str) -> str:
        stage_mapping = {
            "stage1": "logic_analysis_model",
            "stage2": "major_chapters_model", 
            "stage3": "sub_chapters_model",
            "stage4": "expansion_model",
            "stage5": "expansion_model"
        }
        
        model_key = stage_mapping.get(stage, "default_model")
        
        if self.api_config.doubao_api_key:
            return self.api_config.doubao_models.get(model_key, self.api_config.doubao_models.get("default_model", "doubao-1-5-lite-32k-250115"))
        elif self.api_config.ark_api_key:
            return self.api_config.ark_models.get(model_key, self.api_config.ark_models.get("default_model", "doubao-1-5-lite-32k-250115"))
        else:
            return self.api_config.models.get(model_key, self.api_config.models.get("default_model", "glm-4.5-flash"))
    
    def get_context_chapters(self) -> int:
        """获取上下文章节数"""
        return self.generation_config.context_chapters
    
    def get_default_word_count(self) -> int:
        """获取默认字数"""
        return self.generation_config.default_word_count
    
    def update_api_key(self, api_key: str):
        """更新API密钥"""
        self.api_config.api_key = api_key
    
    def update_world_style(self, world_style: str):
        """更新世界风格"""
        self.generation_config.world_style = world_style
    
    def get_project_paths(self) -> Dict[str, str]:
        """获取项目路径配置"""
        return {
            "core_setting": self.path_config.core_setting_file,
            "outline_dir": self.path_config.outline_dir,
            "draft_dir": self.path_config.draft_dir,
            "prompt_dir": self.path_config.prompt_dir,
            "log_dir": self.path_config.log_dir,
            "api_log_dir": self.path_config.api_log_dir,
            "system_log_dir": self.path_config.system_log_dir
        }


def create_default_config() -> Dict[str, Any]:
    """创建默认配置"""
    return {
        # 智谱AI配置
        "api_key": "请在此处填写智谱API密钥",
        "api_base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": {
            "logic_analysis_model": "glm-4-long",
            "major_chapters_model": "glm-4-long",
            "sub_chapters_model": "glm-4-long",
            "expansion_model": "glm-4.5-flash",
            "default_model": "glm-4.5-flash"
        },
        
        # 豆包配置
        "doubao_api_key": "请在此处填写豆包API密钥",
        "doubao_api_base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "doubao_models": {
            "logic_analysis_model": "doubao-1-5-lite-32k-250115",
            "major_chapters_model": "doubao-1-5-lite-32k-250115",
            "sub_chapters_model": "doubao-1-5-lite-32k-250115",
            "expansion_model": "doubao-1-5-lite-32k-250115",
            "default_model": "doubao-1-5-lite-32k-250115"
        },
        
# Ark配置
        "ark_api_key": "请在此处填写Ark API密钥或设置ARK_API_KEY环境变量",
        "ark_models": {
            "logic_analysis_model": "doubao-1-5-lite-32k-250115",
            "major_chapters_model": "doubao-1-5-lite-32k-250115",
            "sub_chapters_model": "doubao-1-5-lite-32k-250115",
            "expansion_model": "doubao-1-5-lite-32k-250115",
            "default_model": "doubao-1-5-lite-32k-250115"
        },
        
        # DeepSeek配置
        "deepseek_api_key": "请在此处填写DeepSeek API密钥或设置DEEPSEEK_API_KEY环境变量",
        "deepseek_api_base_url": "https://api.deepseek.com",
        "deepseek_models": {
            "logic_analysis_model": "deepseek-chat",
            "major_chapters_model": "deepseek-chat",
            "sub_chapters_model": "deepseek-chat",
            "expansion_model": "deepseek-chat",
            "default_model": "deepseek-chat"
        },
        
        # 多模型配置
        "default_model": "zhipu",
        "available_models": ["zhipu", "doubao", "ark", "deepseek"],
        
        # 通用配置
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
            "context_chapters": 5,
            "default_word_count": 1500,
            "copyright_bypass": True,
            "world_style": ""
        },
        "ai_roles": {
            "generator": {
                "provider": "zhipu",
                "model": "glm-4.5-flash",
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 8000,
                "system_prompt": "你是一个专业的小说创作助手，擅长根据大纲和设定生成引人入胜的章节内容。",
                "enabled": True
            },
            "reviewer": {
                "provider": "deepseek",
                "model": "deepseek-chat",
                "temperature": 0.3,
                "top_p": 0.7,
                "max_tokens": 4000,
                "system_prompt": "你是一个专业的文学编辑和评审专家，擅长分析小说内容的情节逻辑和连贯性。",
                "enabled": True
            },
            "refiner": {
                "provider": "zhipu",
                "model": "glm-4-long",
                "temperature": 0.5,
                "top_p": 0.8,
                "max_tokens": 8000,
                "system_prompt": "你是一个专业的文字润色专家，擅长优化句子结构和表达方式。",
                "enabled": True
            }
        }
    }