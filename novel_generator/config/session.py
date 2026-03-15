"""
会话状态管理器

负责管理项目生成状态、API配置持久化和续写功能支持
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class APIConfigState:
    """API配置状态 - 每个服务商独立存储API密钥"""

    provider: str = "doubao"  # 当前使用的服务商

    # 豆包/火山引擎配置 (两者共用同一套API)
    doubao_api_key: str = ""
    doubao_api_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    doubao_models: Dict[str, str] = field(
        default_factory=lambda: {
            "logic_analysis_model": "doubao-seed-2-0-lite-260215",
            "major_chapters_model": "doubao-seed-2-0-lite-260215",
            "sub_chapters_model": "doubao-seed-2-0-lite-260215",
            "expansion_model": "doubao-seed-2-0-lite-260215",
            "default_model": "doubao-seed-2-0-lite-260215",
        }
    )

    # DeepSeek配置
    deepseek_api_key: str = ""
    deepseek_api_base_url: str = "https://api.deepseek.com"
    deepseek_models: Dict[str, str] = field(
        default_factory=lambda: {
            "logic_analysis_model": "deepseek-chat",
            "major_chapters_model": "deepseek-chat",
            "sub_chapters_model": "deepseek-chat",
            "expansion_model": "deepseek-chat",
            "default_model": "deepseek-chat",
        }
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "APIConfigState":
        return cls(
            provider=data.get("provider", "doubao"),
            doubao_api_key=data.get("doubao_api_key", ""),
            doubao_api_base_url=data.get(
                "doubao_api_base_url", "https://ark.cn-beijing.volces.com/api/v3"
            ),
            doubao_models=data.get("doubao_models", {}),
            deepseek_api_key=data.get("deepseek_api_key", ""),
            deepseek_api_base_url=data.get(
                "deepseek_api_base_url", "https://api.deepseek.com"
            ),
            deepseek_models=data.get("deepseek_models", {}),
        )


@dataclass
class AIRoleState:
    provider: str = "doubao"
    model: str = ""
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 8000
    system_prompt: str = ""
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AIRoleState":
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
class AIRolesState:
    generator: AIRoleState = field(
        default_factory=lambda: AIRoleState(
            provider="doubao",
            model="doubao-seed-2-0-lite-260215",
            temperature=0.7,
            top_p=0.9,
            max_tokens=8000,
        )
    )
    reviewer: AIRoleState = field(
        default_factory=lambda: AIRoleState(
            provider="deepseek",
            model="deepseek-chat",
            temperature=0.3,
            top_p=0.7,
            max_tokens=4000,
        )
    )
    refiner: AIRoleState = field(
        default_factory=lambda: AIRoleState(
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
    def from_dict(cls, data: Dict[str, Any]) -> "AIRolesState":
        state = cls()
        if "generator" in data:
            state.generator = AIRoleState.from_dict(data["generator"])
        if "reviewer" in data:
            state.reviewer = AIRoleState.from_dict(data["reviewer"])
        if "refiner" in data:
            state.refiner = AIRoleState.from_dict(data["refiner"])
        return state

    def get_role_state(self, role_name: str) -> AIRoleState:
        if role_name == "generator":
            return self.generator
        elif role_name == "reviewer":
            return self.reviewer
        elif role_name == "refiner":
            return self.refiner
        return self.generator

    def set_role_state(self, role_name: str, state: AIRoleState):
        if role_name == "generator":
            self.generator = state
        elif role_name == "reviewer":
            self.reviewer = state
        elif role_name == "refiner":
            self.refiner = state


@dataclass
class GenerationState:
    total_chapters: int = 0
    last_outline_chapter: int = 0
    last_draft_chapter: int = 0
    outline_file: str = ""
    last_session_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenerationState":
        return cls(
            total_chapters=data.get("total_chapters", 0),
            last_outline_chapter=data.get("last_outline_chapter", 0),
            last_draft_chapter=data.get("last_draft_chapter", 0),
            outline_file=data.get("outline_file", ""),
            last_session_at=data.get("last_session_at", ""),
        )


@dataclass
class GenerationConfig:
    batch_size: int = 15
    context_chapters: int = 10
    default_word_count: int = 1500

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenerationConfig":
        return cls(
            batch_size=data.get("batch_size", 15),
            context_chapters=data.get("context_chapters", 10),
            default_word_count=data.get("default_word_count", 1500),
        )


@dataclass
class SessionRecord:
    """单次会话记录"""

    date: str
    action: str  # expand / outline / init
    chapters: List[int] = field(default_factory=list)  # [start, end]
    model_used: str = ""
    success: bool = True
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionRecord":
        return cls(
            date=data.get("date", ""),
            action=data.get("action", ""),
            chapters=data.get("chapters", []),
            model_used=data.get("model_used", ""),
            success=data.get("success", True),
            error_message=data.get("error_message", ""),
        )


@dataclass
class SessionState:
    project_name: str = "未命名小说项目"
    created_at: str = ""
    updated_at: str = ""
    api_config: APIConfigState = field(default_factory=APIConfigState)
    generation_state: GenerationState = field(default_factory=GenerationState)
    generation_config: GenerationConfig = field(default_factory=GenerationConfig)
    ai_roles: AIRolesState = field(default_factory=AIRolesState)
    sessions: List[SessionRecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "api_config": self.api_config.to_dict(),
            "generation_state": self.generation_state.to_dict(),
            "generation_config": self.generation_config.to_dict(),
            "ai_roles": self.ai_roles.to_dict(),
            "sessions": [s.to_dict() for s in self.sessions],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionState":
        return cls(
            project_name=data.get("project_name", "未命名小说项目"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            api_config=APIConfigState.from_dict(data.get("api_config", {})),
            generation_state=GenerationState.from_dict(
                data.get("generation_state", {})
            ),
            generation_config=GenerationConfig.from_dict(
                data.get("generation_config", {})
            ),
            ai_roles=AIRolesState.from_dict(data.get("ai_roles", {})),
            sessions=[SessionRecord.from_dict(s) for s in data.get("sessions", [])],
        )


class SessionManager:
    """
    会话状态管理器

    功能:
    - 持久化 API 配置
    - 记录生成进度
    - 支持续写功能
    - 会话历史追踪
    """

    SESSION_FILE = "session.json"
    CONFIG_DIR = "05_script"

    def __init__(self, project_root: str = "."):
        """
        初始化会话管理器

        Args:
            project_root: 项目根目录路径
        """
        self.project_root = Path(project_root).resolve()
        self.session_file_path = self.project_root / self.CONFIG_DIR / self.SESSION_FILE
        self._state: Optional[SessionState] = None

    @property
    def state(self) -> SessionState:
        """获取当前会话状态（懒加载）"""
        if self._state is None:
            self._state = self.load()
        return self._state

    def load(self) -> SessionState:
        """
        加载会话状态

        Returns:
            SessionState: 会话状态对象
        """
        if not self.session_file_path.exists():
            logger.info(f"会话文件不存在，创建新会话: {self.session_file_path}")
            return self._create_default_session()

        try:
            with open(self.session_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._state = SessionState.from_dict(data)
            logger.info(f"加载会话状态成功: {self.session_file_path}")
            return self._state
        except Exception as e:
            logger.error(f"加载会话状态失败: {e}")
            return self._create_default_session()

    def save(self) -> bool:
        """
        保存会话状态

        Returns:
            bool: 是否保存成功
        """
        try:
            # 确保目录存在
            self.session_file_path.parent.mkdir(parents=True, exist_ok=True)

            # 更新时间戳
            self.state.updated_at = datetime.now().isoformat()

            with open(self.session_file_path, "w", encoding="utf-8") as f:
                json.dump(self.state.to_dict(), f, ensure_ascii=False, indent=2)

            logger.info(f"会话状态已保存: {self.session_file_path}")
            return True
        except Exception as e:
            logger.error(f"保存会话状态失败: {e}")
            return False

    def _create_default_session(self) -> SessionState:
        """创建默认会话状态"""
        now = datetime.now().isoformat()
        self._state = SessionState(
            project_name=self.project_root.name, created_at=now, updated_at=now
        )
        return self._state

    # ========== API 配置管理 ==========

    def get_api_config(self) -> Dict[str, Any]:
        api_state = self.state.api_config
        gen_config = self.state.generation_config
        config = {
            "default_model": api_state.provider,
            "max_tokens": 8000,
            "temperature": 0.7,
            "top_p": 0.7,
            "batch_size": gen_config.batch_size,
            "context_chapters": gen_config.context_chapters,
            "default_word_count": gen_config.default_word_count,
            "system": {"api": {"max_retries": 5, "retry_delay": 2, "timeout": 60}},
            "paths": self._get_default_paths(),
            "novel_generation": {
                "context_chapters": gen_config.context_chapters,
                "default_word_count": gen_config.default_word_count,
            },
            "doubao_api_key": api_state.doubao_api_key,
            "doubao_api_base_url": api_state.doubao_api_base_url,
            "doubao_models": api_state.doubao_models,
            "deepseek_api_key": api_state.deepseek_api_key,
            "deepseek_api_base_url": api_state.deepseek_api_base_url,
            "deepseek_models": api_state.deepseek_models,
        }

        config["ai_roles"] = self.state.ai_roles.to_dict()

        return config

    def get_ai_roles_config(self) -> Dict[str, Any]:
        return self.state.ai_roles.to_dict()

    def set_ai_role_config(
        self,
        role_name: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> bool:
        role_state = self.state.ai_roles.get_role_state(role_name)
        if provider is not None:
            role_state.provider = provider
        if model is not None:
            role_state.model = model
        if temperature is not None:
            role_state.temperature = temperature
        if top_p is not None:
            role_state.top_p = top_p
        if max_tokens is not None:
            role_state.max_tokens = max_tokens
        if system_prompt is not None:
            role_state.system_prompt = system_prompt
        if enabled is not None:
            role_state.enabled = enabled
        return self.save()

    def _get_default_paths(self) -> Dict[str, str]:
        """获取默认路径配置"""
        return {
            "core_setting": "01_source/core_setting.yaml",
            "outline_dir": "02_outline/",
            "draft_dir": "03_draft/",
            "prompt_dir": "04_prompt/",
            "log_dir": "06_log/",
        }

    def set_api_config(
        self,
        provider: str,
        api_key: str,
        api_base_url: Optional[str] = None,
        models: Optional[Dict[str, str]] = None,
    ) -> bool:
        self.state.api_config.provider = provider

        if provider == "doubao":
            self.state.api_config.doubao_api_key = api_key
            if api_base_url:
                self.state.api_config.doubao_api_base_url = api_base_url
            else:
                self.state.api_config.doubao_api_base_url = (
                    "https://ark.cn-beijing.volces.com/api/v3"
                )
            if models:
                self.state.api_config.doubao_models = models
        elif provider == "deepseek":
            self.state.api_config.deepseek_api_key = api_key
            if api_base_url:
                self.state.api_config.deepseek_api_base_url = api_base_url
            else:
                self.state.api_config.deepseek_api_base_url = "https://api.deepseek.com"
            if models:
                self.state.api_config.deepseek_models = models

        return self.save()

    # ========== 生成进度管理 ==========

    def get_last_chapter(self, action: str = "draft") -> int:
        """
        获取最后生成的章节号

        Args:
            action: 类型 (draft / outline)

        Returns:
            int: 最后章节号，未生成返回 0
        """
        if action == "draft":
            return self.state.generation_state.last_draft_chapter
        elif action == "outline":
            return self.state.generation_state.last_outline_chapter
        return 0

    def update_progress(
        self,
        action: str,
        start_chapter: int,
        end_chapter: int,
        outline_file: Optional[str] = None,
    ) -> bool:
        """
        更新生成进度

        Args:
            action: 动作类型 (draft / outline)
            start_chapter: 起始章节
            end_chapter: 结束章节
            outline_file: 大纲文件路径（可选）

        Returns:
            bool: 是否更新成功
        """
        if action == "draft":
            self.state.generation_state.last_draft_chapter = end_chapter
        elif action == "outline":
            self.state.generation_state.last_outline_chapter = end_chapter

        if outline_file:
            self.state.generation_state.outline_file = outline_file

        self.state.generation_state.last_session_at = datetime.now().isoformat()

        return self.save()

    def set_total_chapters(self, total: int) -> bool:
        """设置总章节数"""
        self.state.generation_state.total_chapters = total
        return self.save()

    def auto_detect_last_chapter(self, directory: str = "03_draft") -> int:
        """
        自动检测目录中最后生成的章节号

        Args:
            directory: 目录路径 (02_outline / 03_draft)

        Returns:
            int: 检测到的最后章节号
        """
        dir_path = self.project_root / directory
        if not dir_path.exists():
            return 0

        max_chapter = 0
        for file_path in dir_path.iterdir():
            if file_path.is_file():
                # 尝试从文件名中提取章节号
                import re

                match = re.search(r"(\d+)", file_path.stem)
                if match:
                    chapter_num = int(match.group(1))
                    max_chapter = max(max_chapter, chapter_num)

        return max_chapter

    def sync_with_files(self) -> bool:
        """
        从实际文件同步状态

        Returns:
            bool: 是否同步成功
        """
        # 检测草稿目录
        last_draft = self.auto_detect_last_chapter("03_draft")
        if last_draft > 0:
            self.state.generation_state.last_draft_chapter = last_draft

        # 检测大纲目录
        last_outline = self.auto_detect_last_chapter("02_outline")
        if last_outline > 0:
            self.state.generation_state.last_outline_chapter = last_outline

        return self.save()

    # ========== 会话记录管理 ==========

    def add_session_record(
        self,
        action: str,
        start_chapter: int,
        end_chapter: int,
        model_used: str = "",
        success: bool = True,
        error_message: str = "",
    ) -> bool:
        """
        添加会话记录

        Args:
            action: 动作类型 (expand / outline / init)
            start_chapter: 起始章节
            end_chapter: 结束章节
            model_used: 使用的模型
            success: 是否成功
            error_message: 错误信息

        Returns:
            bool: 是否添加成功
        """
        record = SessionRecord(
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            action=action,
            chapters=[start_chapter, end_chapter],
            model_used=model_used,
            success=success,
            error_message=error_message,
        )

        self.state.sessions.append(record)

        # 保留最近 50 条记录
        if len(self.state.sessions) > 50:
            self.state.sessions = self.state.sessions[-50:]

        return self.save()

    def get_recent_sessions(self, limit: int = 10) -> List[SessionRecord]:
        """
        获取最近的会话记录

        Args:
            limit: 最大数量

        Returns:
            List[SessionRecord]: 会话记录列表
        """
        return self.state.sessions[-limit:]

    # ========== 续写支持 ==========

    def get_continue_info(self, action: str = "draft") -> Dict[str, Any]:
        """
        获取续写信息

        Args:
            action: 动作类型 (draft / outline)

        Returns:
            Dict[str, Any]: 续写信息
        """
        if action == "draft":
            last_chapter = self.state.generation_state.last_draft_chapter
            outline_file = self.state.generation_state.outline_file
        else:
            last_chapter = self.state.generation_state.last_outline_chapter
            outline_file = ""

        total = self.state.generation_state.total_chapters
        next_chapter = last_chapter + 1 if last_chapter > 0 else 1

        return {
            "last_chapter": last_chapter,
            "next_chapter": next_chapter,
            "total_chapters": total,
            "progress_percent": (last_chapter / total * 100) if total > 0 else 0,
            "outline_file": outline_file,
            "provider": self.state.api_config.provider,
            "can_continue": last_chapter > 0 and (total == 0 or last_chapter < total),
        }

    def get_status_summary(self) -> Dict[str, Any]:
        """
        获取状态摘要（用于 status 命令）

        Returns:
            Dict[str, Any]: 状态摘要
        """
        return {
            "project_name": self.state.project_name,
            "created_at": self.state.created_at,
            "updated_at": self.state.updated_at,
            "api_provider": self.state.api_config.provider,
            "api_configured": bool(
                self.state.api_config.doubao_api_key
                or self.state.api_config.deepseek_api_key
            ),
            "total_chapters": self.state.generation_state.total_chapters,
            "last_outline": self.state.generation_state.last_outline_chapter,
            "last_draft": self.state.generation_state.last_draft_chapter,
            "outline_file": self.state.generation_state.outline_file,
            "session_count": len(self.state.sessions),
        }


def get_session_manager(project_root: str = ".") -> SessionManager:
    """
    获取会话管理器实例

    Args:
        project_root: 项目根目录

    Returns:
        SessionManager: 会话管理器实例
    """
    return SessionManager(project_root)
