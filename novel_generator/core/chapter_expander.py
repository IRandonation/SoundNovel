"""
章节扩写器（简化版）
基于场景级扩写的新流程
"""

import re
import logging
from pathlib import Path
from typing import Dict, Any, List

from novel_generator.config.settings import Settings
from novel_generator.config.generation_config import GenerationConfigManager
from novel_generator.utils.multi_model_client import MultiModelClient
from novel_generator.core.ai_roles import AIRoleManager, AIRole
from novel_generator.core.character_tracker import CharacterTracker
from novel_generator.core.foreshadowing_tracker import ForeshadowingTracker
from novel_generator.core.emotional_arc_tracker import EmotionalArcTracker
from novel_generator.core.scene_expander import SceneExpander
from novel_generator.core.scene_assembler import SceneAssembler


class ChapterExpander:
    """章节扩写器 - 基于场景级扩写的简化流程"""

    def __init__(
        self,
        config: Dict[str, Any],
        multi_model_client: MultiModelClient = None,
        project_root: str = ".",
    ):
        self.config = config
        self.settings = Settings(config)
        self.logger = logging.getLogger(__name__)
        self.project_root = project_root

        self.multi_model_client = multi_model_client or MultiModelClient(config)

        self.gen_config_manager = GenerationConfigManager(project_root)

        # 初始化AI角色管理器
        self.ai_role_manager = AIRoleManager(config, self.multi_model_client)
        self._init_ai_roles()

        # 初始化追踪器
        self.character_tracker = CharacterTracker(config)
        self.foreshadowing_tracker = ForeshadowingTracker(config)
        self.emotional_arc_tracker = EmotionalArcTracker(config)
        self._init_trackers()

        # 初始化场景扩写器和组装器
        self.scene_expander = SceneExpander(config, self.ai_role_manager)
        self.scene_assembler = SceneAssembler()

    def _init_ai_roles(self):
        """初始化AI角色配置"""
        saved_roles = self.gen_config_manager.get_all_roles_config()

        from novel_generator.config.ai_roles import AIRoleConfig

        for role_name in ["generator", "reviewer", "refiner"]:
            if role_name in saved_roles:
                role_data = saved_roles[role_name]
                role_config = AIRoleConfig(
                    provider=role_data.get("provider", "doubao"),
                    model=role_data.get("model", ""),
                    temperature=role_data.get("temperature", 0.7),
                    top_p=role_data.get("top_p", 0.9),
                    max_tokens=role_data.get("max_tokens", 8000),
                    system_prompt=role_data.get("system_prompt", ""),
                    enabled=role_data.get("enabled", True),
                )
                self.ai_role_manager.set_role_config(AIRole(role_name), role_config)

    def _init_trackers(self):
        """初始化追踪器"""
        try:
            core_setting_path = Path(self.settings.path_config.core_setting_file)
            if core_setting_path.exists():
                self.character_tracker.load_from_core_setting(str(core_setting_path))
                self.foreshadowing_tracker.load_from_core_setting(
                    str(core_setting_path)
                )

            tracking_dir = Path(self.settings.path_config.prompt_dir) / "tracking"
            self.character_tracker.load_tracking_file(
                str(tracking_dir / "character_tracking.yaml")
            )
            self.foreshadowing_tracker.load_tracking_file(
                str(tracking_dir / "foreshadowing_tracking.yaml")
            )
            self.emotional_arc_tracker.load_tracking_file(
                str(tracking_dir / "emotional_arc_tracking.yaml")
            )

            self.logger.info("追踪器初始化完成")
        except Exception as e:
            self.logger.warning(f"追踪器初始化部分失败: {e}")

    def expand_chapter(
        self,
        chapter_num: int,
        chapter_outline: Dict[str, Any],
        previous_context: str = "",
        after_context: str = "",
        core_setting: Dict[str, Any] = None,
        style_guide: Dict[str, Any] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """
        简化版章节扩写

        Args:
            chapter_num: 章节编号
            chapter_outline: 章节大纲
            previous_context: 前文上下文
            after_context: 后文上下文
            core_setting: 核心设定
            style_guide: 风格指南

        Returns:
            (章节内容, 状态卡)
        """
        self.logger.info(f"开始扩写第{chapter_num}章...")

        # 1. 读取场景列表
        scenes = chapter_outline.get("场景列表", [])
        if not scenes:
            self.logger.warning(f"第{chapter_num}章没有场景列表，尝试使用整章大纲")
            scenes = [{"场景ID": f"场景{chapter_num}-1", "节拍设计": {"钩子": chapter_outline.get("核心钩子", ""), "落点": chapter_outline.get("章节落点", "")}, "字数目标": self.settings.get_default_word_count()}]

        # 2. 逐个扩写场景
        scene_contents = []
        for scene in scenes:
            content = self.scene_expander.expand_scene(scene)
            scene_contents.append(content)

        # 3. 组装章节
        chapter_content = self.scene_assembler.assemble_chapter(
            scene_contents, chapter_outline
        )

        # 4. 轻量级润色（编码实现）
        chapter_content = self._quick_polish(chapter_content)

        # 5. 生成state_card
        state_card = self._generate_state_card(chapter_num, chapter_content, previous_context)

        # 6. 更新追踪器
        self._update_trackers(chapter_num, chapter_content, chapter_outline, state_card)

        self.logger.info(f"第{chapter_num}章扩写完成")
        return chapter_content, state_card

    def _quick_polish(self, content: str) -> str:
        """
        轻量级润色（编码实现，无需API调用）

        Args:
            content: 原始内容

        Returns:
            润色后的内容
        """
        if not content:
            return ""

        # 1. 清理多余空行
        content = re.sub(r"\n{3,}", "\n\n", content)

        # 2. 标准化引号
        content = content.replace('"', '"').replace('"', '"')
        content = content.replace("'", "'").replace("'", "'")

        # 3. 清理行首尾空格
        lines = [line.strip() for line in content.split("\n")]
        content = "\n".join(lines)

        # 4. 确保段落间有空行
        paragraphs = content.split("\n\n")
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        content = "\n\n".join(paragraphs)

        return content.strip()

    def _generate_state_card(
        self, chapter_num: int, content: str, previous_context: str
    ) -> Dict[str, Any]:
        """
        生成状态卡

        Args:
            chapter_num: 章节编号
            content: 章节内容
            previous_context: 前文上下文

        Returns:
            状态卡字典
        """
        # 简化版：从内容中提取关键信息
        state_card = {
            "人物状态": self._extract_characters_from_content(content),
            "当前位置": self._extract_locations_from_content(content),
            "情感基调": self._extract_emotion_tone(content),
            "未完成事件": [],
            "下章建议": "",
        }

        # 检测未完成事件（以省略号、问号结尾的对话或描述）
        lines = content.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.endswith("...") or stripped.endswith("……"):
                state_card["未完成事件"].append(stripped[:100])  # 限制长度

        return state_card

    def _extract_characters_from_content(self, content: str) -> List[str]:
        """从内容中提取出现的人物"""
        # 简单实现：查找引号内的对话，推测说话人
        # 实际项目中可以使用更复杂的NER
        return []

    def _extract_locations_from_content(self, content: str) -> List[str]:
        """从内容中提取地点"""
        # 简单实现
        return []

    def _extract_emotion_tone(self, content: str) -> str:
        """提取情感基调"""
        # 简单实现
        return ""

    def _update_trackers(
        self,
        chapter_num: int,
        content: str,
        chapter_outline: Dict[str, Any],
        state_card: Dict[str, Any] = None,
    ):
        """
        更新追踪器

        Args:
            chapter_num: 章节编号
            content: 章节内容
            chapter_outline: 章节大纲
            state_card: 状态卡
        """
        self.character_tracker.update_from_chapter(chapter_num, content, state_card)

        removed = self.character_tracker.cleanup_characters(chapter_num, state_card)
        if removed:
            self.logger.info(f"清理角色: {', '.join(removed)}")

        self.foreshadowing_tracker.plant_foreshadowing(chapter_num, content)
        self.foreshadowing_tracker.check_recovery(chapter_num, content, chapter_outline)
        self.emotional_arc_tracker.analyze_chapter(
            chapter_num, content, chapter_outline
        )

        self._save_tracking_files()

    def _save_tracking_files(self):
        """保存追踪文件"""
        try:
            tracking_dir = Path(self.settings.path_config.prompt_dir) / "tracking"
            tracking_dir.mkdir(parents=True, exist_ok=True)

            self.character_tracker.save_tracking_file(
                str(tracking_dir / "character_tracking.yaml")
            )
            self.foreshadowing_tracker.save_tracking_file(
                str(tracking_dir / "foreshadowing_tracking.yaml")
            )
            self.emotional_arc_tracker.save_tracking_file(
                str(tracking_dir / "emotional_arc_tracking.yaml")
            )
        except Exception as e:
            self.logger.error(f"保存追踪文件失败: {e}")

    def save_chapter(
        self, chapter_num: int, content: str, output_dir: str = None
    ) -> str:
        """
        保存章节到文件

        Args:
            chapter_num: 章节编号
            content: 章节内容
            output_dir: 输出目录

        Returns:
            保存的文件路径
        """
        output_path = Path(output_dir or self.settings.path_config.draft_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        file_path = output_path / f"第{chapter_num:04d}章.txt"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        self.logger.info(f"章节已保存: {file_path}")
        return str(file_path)

    def load_existing_chapter(self, chapter_num: int, draft_dir: str = None) -> str:
        """
        读取已存在的章节内容

        Args:
            chapter_num: 章节编号
            draft_dir: 草稿目录

        Returns:
            章节内容，如果不存在则返回空字符串
        """
        output_path = Path(draft_dir or self.settings.path_config.draft_dir)
        file_path = output_path / f"第{chapter_num:04d}章.txt"

        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                self.logger.warning(f"读取章节 {chapter_num} 失败: {e}")
        return ""

    def get_existing_chapters(self, draft_dir: str = None) -> List[int]:
        """
        获取已存在的章节列表

        Args:
            draft_dir: 草稿目录

        Returns:
            已存在的章节编号列表
        """
        output_path = Path(draft_dir or self.settings.path_config.draft_dir)
        existing = []

        if output_path.exists():
            for f in output_path.glob("第*章.txt"):
                try:
                    match = re.search(r"第(\d+)章", f.name)
                    if match:
                        existing.append(int(match.group(1)))
                except Exception:
                    continue

        return sorted(existing)

    def expand_multiple_chapters(
        self,
        outline: Dict[str, Any],
        start_chapter: int,
        end_chapter: int,
        core_setting: Dict[str, Any] = None,
        style_guide: Dict[str, Any] = None,
        context_window: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        批量扩写多个章节

        Args:
            outline: 完整大纲
            start_chapter: 起始章节
            end_chapter: 结束章节
            core_setting: 核心设定
            style_guide: 风格指南
            context_window: 上下文窗口大小

        Returns:
            扩写结果列表
        """
        results = []
        context_parts = []

        existing_chapters = self.get_existing_chapters()

        for chapter_num in range(start_chapter, end_chapter + 1):
            chapter_key = f"第{chapter_num}章"
            chapter_outline = outline.get(chapter_key, {})

            if not chapter_outline:
                self.logger.warning(f"未找到第{chapter_num}章的大纲，跳过")
                continue

            # 构建前文上下文
            previous_context = ""
            if context_parts:
                take_count = min(len(context_parts), context_window)
                previous_context = "\n\n".join(context_parts[-take_count:])

            # 构建后文上下文（仅对最后一个章节）
            after_context = ""
            if chapter_num == end_chapter:
                after_chapters = [ch for ch in existing_chapters if ch > end_chapter]
                if after_chapters:
                    take_count = min(len(after_chapters), 3)  # 最多取3章
                    after_chapters_to_read = after_chapters[:take_count]

                    after_parts = []
                    for ch in after_chapters_to_read:
                        content = self.load_existing_chapter(ch)
                        if content:
                            after_parts.append(f"【第{ch}章】\n{content}")

                    if after_parts:
                        after_context = "\n\n".join(after_parts)

            try:
                content, state_card = self.expand_chapter(
                    chapter_num=chapter_num,
                    chapter_outline=chapter_outline,
                    previous_context=previous_context,
                    after_context=after_context,
                    core_setting=core_setting or {},
                    style_guide=style_guide or {},
                )

                file_path = self.save_chapter(chapter_num, content)

                context_parts.append(f"【第{chapter_num}章】\n{content}")

                results.append(
                    {
                        "chapter": chapter_num,
                        "file_path": file_path,
                        "word_count": len(content),
                        "state_card": state_card,
                        "success": True,
                    }
                )

            except Exception as e:
                self.logger.error(f"扩写第{chapter_num}章失败: {e}")
                results.append(
                    {"chapter": chapter_num, "error": str(e), "success": False}
                )

        return results
