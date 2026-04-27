"""
场景扩写器
将场景剧本转化为小说正文（极简单次调用）
"""

import re
import logging
from typing import Dict, Any, Optional

from novel_generator.core.ai_roles import AIRoleManager, AIRole


class SceneExpander:
    """场景级扩写器 - 极简单次API调用"""

    def __init__(
        self,
        config: Dict[str, Any],
        ai_role_manager: AIRoleManager,
    ):
        self.config = config
        self.ai_role_manager = ai_role_manager
        self.logger = logging.getLogger(__name__)

    def expand_scene(self, scene_detail: Dict[str, Any]) -> str:
        """
        将场景剧本扩写为正文

        Args:
            scene_detail: 场景详情，包含节拍设计、对白、感官细节等

        Returns:
            扩写后的场景正文
        """
        self.logger.info(f"开始扩写场景: {scene_detail.get('场景ID', '未知')}")

        prompt = self._build_scene_prompt(scene_detail)

        response = self.ai_role_manager.chat_completion(
            role=AIRole.GENERATOR,
            messages=[{"role": "user", "content": prompt}],
        )

        content = self._clean_response(response)

        # 检查字数
        target_word_count = scene_detail.get("字数目标", 500)
        actual_word_count = len(content)
        self._check_word_count(content, target_word_count)

        self.logger.info(
            f"场景扩写完成: {scene_detail.get('场景ID', '未知')} "
            f"(目标: {target_word_count}字, 实际: {actual_word_count}字)"
        )

        return content

    def _build_scene_prompt(self, scene_detail: Dict[str, Any]) -> str:
        """
        构建场景扩写Prompt（Prompt C - 极简版）

        Args:
            scene_detail: 场景详情字典

        Returns:
            格式化后的prompt字符串
        """
        scene_id = scene_detail.get("场景ID", "")
        scene_type = scene_detail.get("类型", "")
        beat_design = scene_detail.get("节拍设计", {})
        hook = beat_design.get("钩子", "")
        rising = beat_design.get("上升动作", "")
        climax = beat_design.get("转折点", "")
        resolution = beat_design.get("落点", "")
        dialogues = scene_detail.get("对白要点", "")
        sensory = scene_detail.get("感官细节", "")
        word_count = scene_detail.get("字数目标", 500)
        pov = scene_detail.get("POV", "第三人称")
        banned_words = scene_detail.get("禁止词", "")

        prompt = f"""【任务】将场景剧本转化为小说正文

【场景剧本】
场景ID: {scene_id}
类型: {scene_type}
节拍设计:
  钩子: {hook}
  上升动作: {rising}
  转折点: {climax}
  落点: {resolution}
对白要点: {dialogues}
感官细节: {sensory}

【执行指令】
1. 严格按照节拍设计的4段结构展开
2. 使用对白要点中的核心对白，可扩展但保留原意
3. 融入感官细节营造氛围
4. 字数控制: {word_count}字
5. POV: {pov}（限知视角）

【技术约束】
- 禁止词：{banned_words}
- 展示而非讲述：用动作代替情绪标签
- 结尾定格在感官细节上

【输出】直接输出正文，不要场景标题。"""

        return prompt

    def _clean_response(self, response: str) -> str:
        """
        清理API响应，移除markdown代码块等

        Args:
            response: 原始响应字符串

        Returns:
            清理后的内容
        """
        if not response:
            return ""

        content = response.strip()

        # 移除markdown代码块标记
        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)

        return content.strip()

    def _check_word_count(self, content: str, target: int) -> bool:
        """
        检查字数是否在可接受范围内

        Args:
            content: 内容字符串
            target: 目标字数

        Returns:
            是否通过检查
        """
        actual = len(content)
        tolerance = 0.2  # 20%容差

        min_acceptable = int(target * (1 - tolerance))
        max_acceptable = int(target * (1 + tolerance))

        if actual < min_acceptable:
            self.logger.warning(
                f"字数不足: 实际{actual}字，目标{target}字，最低要求{min_acceptable}字"
            )
            return False
        elif actual > max_acceptable:
            self.logger.warning(
                f"字数超出: 实际{actual}字，目标{target}字，最高限制{max_acceptable}字"
            )
            return False

        return True
