from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from novel_generator.novel_manager import NovelManager
from api.manager import APIManager

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器 - 仅支持新架构（novels/{novel_id}/）"""

    def __init__(self, project_root: str = ".", novel_id: Optional[str] = None):
        self.project_root = Path(project_root).resolve()
        self.novel_id = novel_id

        # 初始化管理器
        self._novel_manager = NovelManager(str(self.project_root / "novels"))
        self._api_manager = APIManager(str(self.project_root))

        if not self.novel_id:
            # 尝试获取当前活跃小说
            self.novel_id = self._novel_manager.get_current_novel_id()

        if not self.novel_id:
            raise ValueError("未指定小说ID，且没有当前活跃小说")

        self._novel = self._novel_manager.get_novel(self.novel_id)
        if not self._novel:
            raise ValueError(f"小说 '{self.novel_id}' 不存在")

    @property
    def novel(self):
        """获取当前小说项目"""
        return self._novel

    @property
    def state(self) -> Dict[str, Any]:
        """获取当前状态"""
        return self._novel.load_state()

    @property
    def config(self) -> Dict[str, Any]:
        """获取小说配置"""
        return self._novel.load_config()

    def load(self) -> Dict[str, Any]:
        """加载完整配置"""
        novel_config = self._novel.load_config()
        state_data = self._novel.load_state()
        gen_config = self._novel.load_generation_config()

        # 获取API配置
        api_ref = novel_config.get("api_config_ref", "")
        api_config = {}
        if api_ref:
            api_config = self._api_manager.get_config(api_ref) or {}

        return {
            "novel": novel_config,
            "state": state_data,
            "generation": gen_config,
            "api": api_config,
        }

    def save(self) -> bool:
        """保存配置"""
        # 各组件自行保存
        return True

    def get_api_key(self, provider: str) -> str:
        """获取API密钥"""
        novel_config = self._novel.load_config()
        api_ref = novel_config.get("api_config_ref", "")

        if api_ref:
            api_config = self._api_manager.get_config(api_ref)
            if api_config and api_config.get("provider") == provider:
                return api_config.get("api_key", "")
        return ""

    def get_novel_paths(self) -> Dict[str, Path]:
        """获取当前小说的各目录路径"""
        return self._novel.get_paths()

    def get_source_path(self, filename: str) -> Path:
        """获取素材文件路径"""
        return self._novel.source_dir / filename

    def get_outline_path(self, filename: str) -> Path:
        """获取大纲文件路径"""
        return self._novel.outline_dir / filename

    def get_draft_path(self, filename: str) -> Path:
        """获取正文文件路径"""
        return self._novel.draft_dir / filename

    def _build_api_config_dict(self, api_config) -> Dict[str, Any]:
        """将 api.manager.APIConfig 转换为兼容 Settings 的字典"""
        config = vars(api_config).copy()
        provider = api_config.provider
        model = api_config.models.get("expansion_model", "") if api_config.models else ""
        if not model:
            model = "deepseek-chat" if provider == "deepseek" else "doubao-seed-2-0-lite-260215"

        if provider == "deepseek":
            config["deepseek_api_key"] = api_config.api_key
            config["deepseek_api_base_url"] = api_config.api_base_url
            config["deepseek_models"] = api_config.models
        elif provider == "doubao":
            config["doubao_api_key"] = api_config.api_key
            config["doubao_api_base_url"] = api_config.api_base_url
            config["doubao_models"] = api_config.models

        config["ai_roles"] = {
            "generator": {
                "provider": provider,
                "model": model,
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 8000,
                "system_prompt": "",
                "enabled": True,
            }
        }

        gen_config = self._novel.load_generation_config()
        config.setdefault("novel_generation", {})
        config["novel_generation"]["context_chapters"] = gen_config.get(
            "context_chapters", 10
        )
        config["novel_generation"]["default_word_count"] = gen_config.get(
            "default_word_count", 1500
        )
        return config

    def get_api_config(self) -> Dict[str, Any]:
        """获取API配置，找不到引用时自动降级使用默认配置"""
        novel_config = self._novel.load_config()
        api_ref = novel_config.get("api_config_ref", "")

        if api_ref:
            api_config = self._api_manager.get_config(api_ref)
            if api_config:
                return self._build_api_config_dict(api_config)

        # 降级：尝试使用默认 API 配置
        default_config = self._api_manager.get_default()
        if default_config:
            logger.info("小说未绑定API配置，自动使用默认配置: %s", default_config.id)
            return self._build_api_config_dict(default_config)

        return {}

    def get_generation_config(self) -> Dict[str, Any]:
        """获取生成配置"""
        return self._novel.load_generation_config()

    def set_generation_config(self, **kwargs: Any) -> bool:
        """设置生成配置"""
        current = self._novel.load_generation_config()
        current.update(kwargs)
        return self._novel.save_generation_config(current)

    def update_progress(
        self,
        action: str,
        start_chapter: int,
        end_chapter: int,
        outline_file: Optional[str] = None,
    ) -> bool:
        """更新进度"""
        state = self._novel.load_state()

        if action == "draft":
            state["last_draft_chapter"] = end_chapter
        elif action == "outline":
            state["last_outline_chapter"] = end_chapter

        if outline_file:
            state["outline_file"] = outline_file

        state["last_session_at"] = __import__("datetime").datetime.now().isoformat()

        return self._novel.save_state(state)

    def get_continue_info(self, action: str = "draft") -> Dict[str, Any]:
        """获取续写信息"""
        state = self._novel.load_state()
        novel_config = self._novel.load_config()

        if action == "draft":
            last_chapter = state.get("last_draft_chapter", 0)
        else:
            last_chapter = state.get("last_outline_chapter", 0)

        total = state.get("total_chapters", 0)
        next_chapter = last_chapter + 1 if last_chapter > 0 else 1

        return {
            "last_chapter": last_chapter,
            "next_chapter": next_chapter,
            "total_chapters": total,
            "progress_percent": (last_chapter / total * 100) if total > 0 else 0,
            "outline_file": state.get("outline_file", ""),
            "can_continue": last_chapter > 0 and (total == 0 or last_chapter < total),
        }

    def get_status_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        state = self._novel.load_state()
        novel_config = self._novel.load_config()

        return {
            "project_name": novel_config.get("name", self.novel_id),
            "created_at": novel_config.get("created_at", ""),
            "updated_at": novel_config.get("updated_at", ""),
            "api_configured": bool(novel_config.get("api_config_ref", "")),
            "total_chapters": state.get("total_chapters", 0),
            "last_outline": state.get("last_outline_chapter", 0),
            "last_draft": state.get("last_draft_chapter", 0),
            "outline_file": state.get("outline_file", ""),
            "session_count": 0,  # 新架构暂不支持
        }

    def set_chapter_state(self, chapter_num: int, state: str) -> bool:
        """设置章节状态"""
        state_data = self._novel.load_state()
        chapter_states = state_data.get("chapter_states", {})
        chapter_states[str(chapter_num)] = state
        state_data["chapter_states"] = chapter_states
        return self._novel.save_state(state_data)

    def add_session_record(self, **kwargs) -> bool:
        """添加会话记录（新架构暂不支持，保留接口）"""
        # 新架构暂不支持会话记录，仅更新最后会话时间
        state = self._novel.load_state()
        state["last_session_at"] = __import__("datetime").datetime.now().isoformat()
        return self._novel.save_state(state)

    def mark_dirty_cascade(self, chapter_num: int, draft_window: int) -> int:
        """标记级联dirty章节，返回影响的章节数"""
        state = self._novel.load_state()
        chapter_states = state.get("chapter_states", {})

        count = 0
        for i in range(1, draft_window + 1):
            affected_chapter = chapter_num + i
            ch_key = str(affected_chapter)
            if ch_key in chapter_states:
                chapter_states[ch_key] = "dirty"
                count += 1

        state["chapter_states"] = chapter_states
        self._novel.save_state(state)
        return count

    def get_first_dirty_chapter(self) -> int:
        """获取第一个dirty章节，返回章节号或0"""
        state = self._novel.load_state()
        chapter_states = state.get("chapter_states", {})

        dirty_chapters = [int(k) for k, v in chapter_states.items() if v == "dirty"]
        return min(dirty_chapters) if dirty_chapters else 0

    def get_chapter_state(self, chapter_num: int) -> str:
        """获取章节状态"""
        state = self._novel.load_state()
        chapter_states = state.get("chapter_states", {})
        return chapter_states.get(str(chapter_num), "clean")

    def get_chapter_states_summary(self) -> Dict[str, int]:
        """获取章节状态统计"""
        state = self._novel.load_state()
        chapter_states = state.get("chapter_states", {})

        return {
            "clean": sum(1 for v in chapter_states.values() if v == "clean"),
            "dirty": sum(1 for v in chapter_states.values() if v == "dirty"),
            "cosmetic": sum(1 for v in chapter_states.values() if v == "cosmetic"),
            "total": len(chapter_states),
        }


def get_config_manager(project_root: str = ".", novel_id: Optional[str] = None) -> ConfigManager:
    """获取配置管理器实例"""
    return ConfigManager(project_root, novel_id)


def dump_json(path: Path, payload: Dict[str, Any]) -> None:
    """保存JSON文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
