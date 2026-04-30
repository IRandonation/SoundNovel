"""
章节扩写器
章节级一次生成，不拆场景。上下文注入：大纲窗口 + 正文窗口。
"""

import re
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from novel_generator.config.settings import Settings
from novel_generator.utils.multi_model_client import MultiModelClient
from novel_generator.core.ai_roles import AIRoleManager, AIRole


def _summarize_chapter_skeleton(ch_data: Dict[str, Any]) -> str:
    """从章级骨架提取简洁摘要（不含场景节拍细节）"""
    parts = []
    core_event = ch_data.get("核心事件", "")
    position = ch_data.get("章节定位", "")
    cause_chain = ch_data.get("与前章因果", "")
    scenes = ch_data.get("场景概览", [])
    emotion = ch_data.get("情绪曲线", "")
    foreshadowing = ch_data.get("伏笔处理", {})
    ending_hook = ch_data.get("结尾卡点", "")

    if position:
        parts.append(f"定位: {position}")
    if core_event:
        parts.append(f"事件: {core_event}")
    if cause_chain:
        parts.append(f"因果: {cause_chain}")
    if isinstance(scenes, list) and scenes:
        parts.append(f"场景: {'; '.join(str(s) for s in scenes[:4])}")
    if emotion:
        parts.append(f"情绪: {emotion}")
    if isinstance(foreshadowing, dict):
        buried = foreshadowing.get("埋设", [])
        recovered = foreshadowing.get("回收", [])
        if buried:
            parts.append(f"埋设: {', '.join(str(x) for x in buried[:2])}")
        if recovered:
            parts.append(f"回收: {', '.join(str(x) for x in recovered[:2])}")
    if ending_hook:
        parts.append(f"卡点: {ending_hook}")
    return " | ".join(parts)


def _build_outline_context(outline: Dict[str, Any], current_ch: int, window: int = 30) -> str:
    """构建前N章大纲上下文（骨架级摘要，含叙事逻辑链）"""
    start = max(1, current_ch - window)
    parts = []
    for ch in range(start, current_ch):
        ch_key = f"第{ch}章"
        ch_data = outline.get(ch_key)
        if not ch_data:
            continue
        title = ch_data.get("标题", "")
        summary = _summarize_chapter_skeleton(ch_data)

        block = f"【第{ch}章】"
        if title:
            block += f" {title}"
        block += "\n"
        if summary:
            block += f"  {summary}\n"
        parts.append(block)
    return "\n".join(parts) if parts else ""


def _build_draft_context(draft_dir: str, current_ch: int, window: int = 10) -> str:
    """构建前N章正文全文上下文（从磁盘读取）"""
    start = max(1, current_ch - window)
    parts = []
    draft_path = Path(draft_dir)
    for ch in range(start, current_ch):
        file_path = draft_path / f"第{ch:04d}章.txt"
        if not file_path.exists():
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
            parts.append(f"【第{ch}章】\n{content}")
        except Exception:
            continue
    return "\n\n".join(parts) if parts else ""


class ChapterExpander:
    """章节扩写器 — 章节级一次生成，不拆场景。"""

    def __init__(
        self,
        config: Dict[str, Any],
        multi_model_client: MultiModelClient = None,
        project_root: str = ".",
        core_setting: Dict[str, Any] = None,
    ):
        self.config = config
        self.settings = Settings(config)
        self.logger = logging.getLogger(__name__)
        self.project_root = project_root
        self.multi_model_client = multi_model_client or MultiModelClient(config)
        self.ai_role_manager = AIRoleManager(config, self.multi_model_client)
        self.core_setting = core_setting or {}

    def expand_chapter(
        self,
        chapter_num: int,
        chapter_outline: Dict[str, Any],
        outline_context: str = "",
        draft_context: str = "",
    ) -> str:
        """一次API调用生成完整章节正文。"""
        self.logger.info(f"开始扩写第{chapter_num}章...")

        prompt = self._build_chapter_prompt(
            chapter_num, chapter_outline, outline_context, draft_context
        )

        response = self.ai_role_manager.chat_completion(
            role=AIRole.GENERATOR,
            messages=[{"role": "user", "content": prompt}],
        )

        content = self._quick_polish(response)
        self.logger.info(f"第{chapter_num}章扩写完成")
        return content

    def _build_chapter_prompt(
        self,
        chapter_num: int,
        chapter_outline: Dict[str, Any],
        outline_context: str,
        draft_context: str,
    ) -> str:
        """构建章节扩写prompt：大纲上下文 + 正文上下文 + 当前章骨架"""
        title = chapter_outline.get("标题", f"第{chapter_num}章")
        core_event = chapter_outline.get("核心事件", "")
        position = chapter_outline.get("章节定位", "")
        cause_chain = chapter_outline.get("与前章因果", "")
        scene_overview = chapter_outline.get("场景概览", [])
        emotion_target = chapter_outline.get("情绪曲线", "")
        character_actions = chapter_outline.get("人物行动", "")
        foreshadowing = chapter_outline.get("伏笔处理", "")
        ending_hook = chapter_outline.get("结尾卡点", "")
        dialogue_points = chapter_outline.get("关键对话", "")
        forbidden = chapter_outline.get("禁止元素", [])
        satisfaction = chapter_outline.get("爽点标记")
        word_count = chapter_outline.get("字数目标", self.settings.get_default_word_count())

        parts = []

        if self.core_setting:
            cs_text = yaml.dump(self.core_setting, allow_unicode=True, default_flow_style=False)
            parts.append(f"【核心设定参考（保证人物/世界观/力量体系一致性）】\n{cs_text}")

        if outline_context:
            parts.append(f"【前文大纲上下文（保证宏观连续性）】\n{outline_context}")

        if draft_context:
            parts.append(f"【前文正文全文（保持文风、语气、细节连贯）】\n{draft_context}")

        parts.append(f"【当前章节骨架 - 第{chapter_num}章】")
        parts.append(f"标题: {title}")
        if position:
            parts.append(f"章节定位: {position}")
        if core_event:
            parts.append(f"核心事件: {core_event}")
        if cause_chain:
            parts.append(f"与前章因果: {cause_chain}")
        if emotion_target:
            parts.append(f"情绪曲线: {emotion_target}")
        if character_actions:
            if isinstance(character_actions, dict):
                for role, action in character_actions.items():
                    parts.append(f"  {role}: {action}")
            else:
                parts.append(f"角色行动: {character_actions}")
        if foreshadowing:
            if isinstance(foreshadowing, dict):
                buried = foreshadowing.get("埋设", [])
                recovered = foreshadowing.get("回收", [])
                if buried:
                    parts.append(f"伏笔埋设: {', '.join(str(x) for x in buried)}")
                if recovered:
                    parts.append(f"伏笔回收: {', '.join(str(x) for x in recovered)}")
            else:
                parts.append(f"伏笔处理: {foreshadowing}")

        if isinstance(scene_overview, list) and scene_overview:
            parts.append(f"\n场景概览 ({len(scene_overview)}个场景):")
            for s in scene_overview:
                parts.append(f"  - {s}")

        if dialogue_points:
            if isinstance(dialogue_points, list):
                parts.append(f"\n关键对话:")
                for d in dialogue_points:
                    parts.append(f"  - {d}")
            else:
                parts.append(f"\n关键对话: {dialogue_points}")

        if satisfaction and isinstance(satisfaction, dict):
            sat_type = satisfaction.get("type", "")
            sat_intensity = satisfaction.get("intensity", "")
            sat_rhythm = satisfaction.get("节奏指引", "")
            parts.append(f"\n【爽点章节指引】")
            if sat_type:
                parts.append(f"类型: {sat_type}")
            if sat_intensity:
                parts.append(f"强度: {sat_intensity}/10")
            if sat_rhythm:
                parts.append(f"节奏指引: {sat_rhythm}")

        if ending_hook:
            parts.append(f"\n结尾卡点（必须以此结束）: {ending_hook}")

        if isinstance(forbidden, list) and forbidden:
            parts.append(f"\n禁止元素:")
            for item in forbidden:
                parts.append(f"  - {item}")

        parts.append(f"\n字数目标: {word_count}字")
        parts.append("\n请根据以上骨架和上下文，生成完整的章节正文。")
        parts.append("场景概览是粗粒度的剧情推进指引，场景间的具体过渡、对话细节、感官描写由你自然发挥。")
        parts.append("要求：文风一致、细节连贯、伏笔贯通、情绪到位、章节结尾必须匹配结尾卡点。")

        return "\n\n".join(parts)

    def _quick_polish(self, content: str) -> str:
        """轻量级润色（编码实现，无需API调用）"""
        if not content:
            return ""

        content = re.sub(r"\n{3,}", "\n\n", content)
        content = content.replace('"', '"').replace('"', '"')
        content = content.replace("'", "'").replace("'", "'")
        lines = [line.strip() for line in content.split("\n")]
        content = "\n".join(lines)
        paragraphs = content.split("\n\n")
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        content = "\n\n".join(paragraphs)

        return content.strip()

    def save_chapter(
        self, chapter_num: int, content: str, output_dir: str = None
    ) -> str:
        """保存章节到文件"""
        output_path = Path(output_dir or self.settings.path_config.draft_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        file_path = output_path / f"第{chapter_num:04d}章.txt"
        file_path.write_text(content, encoding="utf-8")

        self.logger.info(f"章节已保存: {file_path}")
        return str(file_path)

    def load_existing_chapter(self, chapter_num: int, draft_dir: str = None) -> str:
        """读取已存在的章节内容"""
        output_path = Path(draft_dir or self.settings.path_config.draft_dir)
        file_path = output_path / f"第{chapter_num:04d}章.txt"

        if file_path.exists():
            try:
                return file_path.read_text(encoding="utf-8")
            except Exception as e:
                self.logger.warning(f"读取章节 {chapter_num} 失败: {e}")
        return ""

    def get_existing_chapters(self, draft_dir: str = None) -> List[int]:
        """获取已存在的章节列表"""
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
        outline_window: int = 30,
        draft_window: int = 10,
        draft_dir: str = None,
    ) -> List[Dict[str, Any]]:
        """批量扩写多个章节"""
        results = []
        _draft_dir = draft_dir or self.settings.path_config.draft_dir

        for chapter_num in range(start_chapter, end_chapter + 1):
            chapter_key = f"第{chapter_num}章"
            chapter_outline = outline.get(chapter_key, {})

            if not chapter_outline:
                self.logger.warning(f"未找到第{chapter_num}章的大纲，跳过")
                continue

            outline_ctx = _build_outline_context(outline, chapter_num, outline_window)
            draft_ctx = _build_draft_context(_draft_dir, chapter_num, draft_window)

            try:
                content = self.expand_chapter(
                    chapter_num=chapter_num,
                    chapter_outline=chapter_outline,
                    outline_context=outline_ctx,
                    draft_context=draft_ctx,
                )

                file_path = self.save_chapter(chapter_num, content, _draft_dir)

                results.append({
                    "chapter": chapter_num,
                    "file_path": file_path,
                    "word_count": len(content),
                    "success": True,
                })

            except Exception as e:
                self.logger.error(f"扩写第{chapter_num}章失败: {e}")
                results.append({"chapter": chapter_num, "error": str(e), "success": False})

        return results
