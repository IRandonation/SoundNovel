import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging


class PromptManager:
    """提示词管理器（新架构版本）"""

    def __init__(self, project_root: str = ".", novel_id: Optional[str] = None):
        """
        初始化提示词管理器

        Args:
            project_root: 项目根目录
            novel_id: 小说ID（可选，默认使用当前小说）
        """
        from novel_generator.utils.common import get_current_novel_id, get_current_novel_paths

        self.project_root = Path(project_root).resolve()
        self.logger = logging.getLogger(__name__)

        # 确定小说ID
        if novel_id is None:
            novel_id = get_current_novel_id(self.project_root)

        # 获取小说路径
        if novel_id:
            paths = get_current_novel_paths(self.project_root)
            if paths:
                self.prompt_dir = paths.get("prompts_dir", self.project_root / "novels" / novel_id / "prompts")
            else:
                self.prompt_dir = self.project_root / "novels" / novel_id / "prompts"
        else:
            self.prompt_dir = self.project_root / "prompts"

        self._system_prompts = None
        self._generation_prompts = None
        self._chapter_expansion_prompts = None
        self._skeleton_generation_prompts = None
        self._outline_generation_prompts = None

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        filepath = self.prompt_dir / filename
        if not filepath.exists():
            self.logger.warning(f"Prompt文件不存在: {filepath}")
            return {}

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            self.logger.error(f"加载Prompt文件失败 {filename}: {e}")
            return {}

    @property
    def system_prompts(self) -> Dict[str, Any]:
        if self._system_prompts is None:
            self._system_prompts = self._load_yaml("system_prompts.yaml")
        return self._system_prompts

    @property
    def generation_prompts(self) -> Dict[str, Any]:
        if self._generation_prompts is None:
            self._generation_prompts = self._load_yaml("generation_prompts.yaml")
        return self._generation_prompts

    @property
    def chapter_expansion_prompts(self) -> Dict[str, Any]:
        """章节扩写提示词配置（chapter_expander.py 使用）"""
        if self._chapter_expansion_prompts is None:
            self._chapter_expansion_prompts = self._load_yaml("chapter_expansion.yaml")
        return self._chapter_expansion_prompts

    @property
    def skeleton_generation_prompts(self) -> Dict[str, Any]:
        """骨架生成提示词配置（SlidingWindowSkeletonGenerator 使用）"""
        if self._skeleton_generation_prompts is None:
            self._skeleton_generation_prompts = self._load_yaml("skeleton_generation.yaml")
        return self._skeleton_generation_prompts

    @property
    def outline_generation_prompts(self) -> Dict[str, Any]:
        """大纲生成提示词配置（旧版 OutlineGenerator 使用）"""
        if self._outline_generation_prompts is None:
            self._outline_generation_prompts = self._load_yaml("outline_generation.yaml")
        return self._outline_generation_prompts

    def get_system_prompt(self, role: str) -> str:
        prompts = self.system_prompts.get(role, {})
        return prompts.get("template", "")

    # ─── 章节扩写 / 骨架生成 便捷访问方法 ────────────────────

    def get_chapter_expansion_config(self) -> Dict[str, Any]:
        """获取 ChapterExpander 的完整提示词配置"""
        return self.chapter_expansion_prompts

    def get_skeleton_generation_config(self) -> Dict[str, Any]:
        """获取 SlidingWindowSkeletonGenerator 的完整提示词配置"""
        return self.skeleton_generation_prompts

    def get_compact_skeleton_labels(self) -> Dict[str, Any]:
        """获取 _build_compact_skeleton() 的格式化标签"""
        return self.chapter_expansion_prompts.get("compact_skeleton", {})

    def get_batch_prompt_labels(self) -> Dict[str, Any]:
        """获取 _build_batch_prompt() 的格式化标签"""
        return self.chapter_expansion_prompts.get("batch_prompt", {})

    def get_chapter_prompt_labels(self) -> Dict[str, Any]:
        """获取 _build_chapter_prompt() 的格式化标签"""
        return self.chapter_expansion_prompts.get("chapter_prompt", {})

    def get_system_fallback(self) -> str:
        """获取 _build_system_content() 的回退角色文本"""
        return self.chapter_expansion_prompts.get("system", {}).get("fallback_role", "")

def get_prompt_manager(project_root: str = ".") -> PromptManager:
    return PromptManager(project_root)
