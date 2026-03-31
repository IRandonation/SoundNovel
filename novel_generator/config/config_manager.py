from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from novel_generator.config.generation_config import (
    DEFAULT_CONFIG,
    GenerationConfigManager,
)
from novel_generator.config.session import SessionManager, SessionState

logger = logging.getLogger(__name__)


class ConfigManager:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.session_manager = SessionManager(str(self.project_root))
        self.generation_manager = GenerationConfigManager(str(self.project_root))
        self._unified: Optional[Dict[str, Any]] = None

    @property
    def state(self) -> SessionState:
        return self.session_manager.state

    @property
    def config(self) -> Dict[str, Any]:
        if self._unified is None:
            self.load()
        return self._unified or {}

    def load(self) -> Dict[str, Any]:
        generation_data = self.generation_manager.load()
        session_state = self.session_manager.load()

        merged = {
            "generation": generation_data.get("generation", {}),
            "roles": generation_data.get("roles", {}),
            "providers": generation_data.get("providers", {}),
            "quality_check": generation_data.get("quality_check", {}),
            "session": session_state.to_dict(),
        }

        self._unified = merged
        return merged

    def save(self) -> bool:
        if self._unified is None:
            self.load()

        unified = self._unified or {}
        ok_generation = self._save_generation_from_unified(unified)
        ok_session = self._save_session_from_unified(unified)
        return ok_generation and ok_session

    def _save_generation_from_unified(self, unified: Dict[str, Any]) -> bool:
        current = self.generation_manager.load()
        payload = copy.deepcopy(current)

        payload["generation"] = unified.get("generation", payload.get("generation", {}))
        payload["roles"] = unified.get("roles", payload.get("roles", {}))
        payload["providers"] = unified.get("providers", payload.get("providers", {}))
        payload["quality_check"] = unified.get(
            "quality_check", payload.get("quality_check", {})
        )

        return self.generation_manager.save(payload)

    def _save_session_from_unified(self, unified: Dict[str, Any]) -> bool:
        session_payload = unified.get("session", {})
        if session_payload:
            self.session_manager._state = SessionState.from_dict(session_payload)

        generation_cfg = unified.get("generation", {})
        if generation_cfg:
            self.session_manager.state.generation_config.batch_size = generation_cfg.get(
                "batch_size", self.session_manager.state.generation_config.batch_size
            )
            self.session_manager.state.generation_config.context_chapters = (
                generation_cfg.get(
                    "context_chapters",
                    self.session_manager.state.generation_config.context_chapters,
                )
            )
            self.session_manager.state.generation_config.default_word_count = (
                generation_cfg.get(
                    "default_word_count",
                    self.session_manager.state.generation_config.default_word_count,
                )
            )

        roles = unified.get("roles", {})
        if roles:
            self.session_manager.state.ai_roles = self.session_manager.state.ai_roles.from_dict(
                roles
            )

        return self.session_manager.save()

    def get_role_config(self, role_name: str) -> Dict[str, Any]:
        roles = self.config.get("roles")
        if not roles:
            roles = self.generation_manager.get_all_roles_config()
        return roles.get(role_name, {})

    def get_all_roles_config(self) -> Dict[str, Any]:
        return self.config.get("roles", self.generation_manager.get_all_roles_config())

    def set_role_config(self, role_name: str, **kwargs: Any) -> bool:
        if self._unified is None:
            self.load()

        roles = self._unified.setdefault("roles", {})
        base = copy.deepcopy(DEFAULT_CONFIG.get("roles", {}).get(role_name, {}))
        base.update(roles.get(role_name, {}))
        base.update(kwargs)
        roles[role_name] = base
        return self.save()

    def get_api_key(self, provider: str) -> str:
        api_cfg = self.state.api_config
        if provider == "doubao":
            return api_cfg.doubao_api_key
        if provider == "deepseek":
            return api_cfg.deepseek_api_key
        return ""

    def get_api_config(self) -> Dict[str, Any]:
        config = self.session_manager.get_api_config()
        generation_cfg = self.config.get("generation", {})
        roles_cfg = self.config.get("roles", {})

        config["ai_roles"] = roles_cfg or config.get("ai_roles", {})
        config.setdefault("novel_generation", {})
        config["novel_generation"]["context_chapters"] = generation_cfg.get(
            "context_chapters",
            config["novel_generation"].get("context_chapters", 10),
        )
        config["novel_generation"]["default_word_count"] = generation_cfg.get(
            "default_word_count",
            config["novel_generation"].get("default_word_count", 1500),
        )
        config["batch_size"] = generation_cfg.get("batch_size", config.get("batch_size", 15))

        return config

    def get_generation_config(self) -> Dict[str, Any]:
        return self.config.get("generation", self.generation_manager.get_generation_config())

    def set_generation_config(self, **kwargs: Any) -> bool:
        if self._unified is None:
            self.load()

        generation = self._unified.setdefault("generation", {})
        generation.update(kwargs)
        return self.save()

    def set_api_config(
        self,
        provider: str,
        api_key: str,
        api_base_url: Optional[str] = None,
        models: Optional[Dict[str, str]] = None,
    ) -> bool:
        return self.session_manager.set_api_config(
            provider=provider,
            api_key=api_key,
            api_base_url=api_base_url,
            models=models,
        )

    def get_continue_info(self, action: str = "draft") -> Dict[str, Any]:
        return self.session_manager.get_continue_info(action)

    def update_progress(
        self,
        action: str,
        start_chapter: int,
        end_chapter: int,
        outline_file: Optional[str] = None,
    ) -> bool:
        return self.session_manager.update_progress(
            action=action,
            start_chapter=start_chapter,
            end_chapter=end_chapter,
            outline_file=outline_file,
        )

    def add_session_record(
        self,
        action: str,
        start_chapter: int,
        end_chapter: int,
        model_used: str = "",
        success: bool = True,
        error_message: str = "",
    ) -> bool:
        return self.session_manager.add_session_record(
            action=action,
            start_chapter=start_chapter,
            end_chapter=end_chapter,
            model_used=model_used,
            success=success,
            error_message=error_message,
        )

    def get_status_summary(self) -> Dict[str, Any]:
        return self.session_manager.get_status_summary()


def get_config_manager(project_root: str = ".") -> ConfigManager:
    return ConfigManager(project_root)


def dump_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
