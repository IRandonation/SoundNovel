"""
场景组装器
将多个扩写后的场景组装成完整章节
"""

import logging
from typing import Dict, Any, List


class SceneAssembler:
    """场景组装器 - 负责将多个场景组装成章节"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def assemble_chapter(
        self, scene_contents: List[str], chapter_skeleton: Dict[str, Any]
    ) -> str:
        """
        组装章节

        Args:
            scene_contents: 场景内容列表
            chapter_skeleton: 章节骨架信息

        Returns:
            组装后的完整章节内容
        """
        if not scene_contents:
            self.logger.warning("场景内容为空，返回空章节")
            return ""

        self.logger.info(f"开始组装章节，共{len(scene_contents)}个场景")

        # 生成场景间过渡
        transitions = self._generate_transitions(scene_contents)

        # 组装内容
        assembled_parts = []
        for i, content in enumerate(scene_contents):
            if i > 0 and i - 1 < len(transitions):
                assembled_parts.append(transitions[i - 1])
            assembled_parts.append(content)

        chapter_content = "\n\n".join(assembled_parts)

        # 添加章节标题
        chapter_title = chapter_skeleton.get("章节标题", "")
        if chapter_title:
            chapter_content = self._add_chapter_title(chapter_content, chapter_title)

        self.logger.info("章节组装完成")
        return chapter_content

    def _generate_transitions(self, scenes: List[str]) -> List[str]:
        """
        生成场景间过渡

        Args:
            scenes: 场景内容列表

        Returns:
            过渡段落列表
        """
        transitions = []

        for i in range(len(scenes) - 1):
            prev_scene = scenes[i]
            curr_scene = scenes[i + 1]
            transition = self._simple_transition(prev_scene, curr_scene)
            transitions.append(transition)

        return transitions

    def _simple_transition(self, prev_scene: str, curr_scene: str) -> str:
        """
        生成简单过渡

        策略：
        - 检测场景间的变化（时间、地点、POV）
        - 根据变化类型生成相应过渡

        Args:
            prev_scene: 前一场景内容
            curr_scene: 当前场景内容

        Returns:
            过渡段落
        """
        # 分析前一场景的结尾特征
        prev_lines = prev_scene.strip().split("\n")
        prev_ending = prev_lines[-1] if prev_lines else ""

        # 分析当前场景的开头特征
        curr_lines = curr_scene.strip().split("\n")
        curr_beginning = curr_lines[0] if curr_lines else ""

        # 根据内容特征判断需要什么样的过渡
        transition = self._determine_transition_type(prev_ending, curr_beginning)

        return transition

    def _determine_transition_type(self, prev_ending: str, curr_beginning: str) -> str:
        """
        确定过渡类型并生成过渡文本

        Args:
            prev_ending: 前一场景结尾
            curr_beginning: 当前场景开头

        Returns:
            过渡文本
        """
        # 时间线索词检测
        time_indicators = {
            "时间跳跃": ["三天后", "一周后", "一个月后", "一年后", "次日", "翌日", "当晚", "黎明", "黄昏", "午夜"],
            "同时": ["与此同时", "同一时刻", "另一边", "在"],
        }

        # 检查当前场景开头是否已包含过渡信息
        for indicator_type, keywords in time_indicators.items():
            for keyword in keywords:
                if keyword in curr_beginning[:50]:  # 只检查开头部分
                    return ""  # 场景自带过渡，不需要额外添加

        # 检测场景切换类型
        # 基于内容长度和特征判断时间跳跃
        prev_ending_sensory = self._is_sensory_detail(prev_ending)
        curr_beginning_sensory = self._is_sensory_detail(curr_beginning)

        if prev_ending_sensory and curr_beginning_sensory:
            # 如果都以感官细节结尾和开头，可能是时间跳跃
            return self._generate_time_transition("short")

        # 默认使用空行分隔（场景紧密衔接）
        return ""

    def _is_sensory_detail(self, text: str) -> bool:
        """
        检测文本是否为感官细节描述

        Args:
            text: 文本片段

        Returns:
            是否为感官细节
        """
        sensory_words = [
            "看", "见", "望", "视", "瞧",
            "听", "闻", "嗅", "香", "臭",
            "触", "摸", "感", "觉",
            "冷", "热", "暖", "凉",
            "光", "暗", "影", "色",
            "声", "音", "响", "静",
        ]

        text_lower = text.lower()
        return any(word in text_lower for word in sensory_words)

    def _generate_time_transition(self, jump_type: str) -> str:
        """
        生成时间过渡文本

        Args:
            jump_type: 跳跃类型 (short/medium/long)

        Returns:
            过渡文本
        """
        transitions = {
            "short": ["片刻后，", "不一会儿，", "稍顷，"],
            "medium": ["几小时后，", "当天晚些时候，", "傍晚时分，"],
            "long": ["三天后。", "一周后。", "时光流转，"],
        }

        import random

        options = transitions.get(jump_type, transitions["short"])
        return random.choice(options)

    def _generate_location_transition(
        self, prev_location: str, curr_location: str
    ) -> str:
        """
        生成地点过渡

        Args:
            prev_location: 前一地点
            curr_location: 当前地点

        Returns:
            过渡文本
        """
        if prev_location == curr_location:
            return ""

        return f"{curr_location}。"

    def _generate_pov_transition(self, prev_pov: str, curr_pov: str) -> str:
        """
        生成POV视角过渡

        Args:
            prev_pov: 前一视角人物
            curr_pov: 当前视角人物

        Returns:
            过渡文本
        """
        if prev_pov == curr_pov:
            return ""

        return f"{curr_pov}的视角——"

    def _add_chapter_title(self, content: str, title: str) -> str:
        """
        添加章节标题

        Args:
            content: 章节内容
            title: 章节标题

        Returns:
            带标题的章节内容
        """
        return f"{title}\n\n{content}"
