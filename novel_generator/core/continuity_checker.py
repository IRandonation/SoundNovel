"""
连续性检查器
用于检查章节内容的人物状态连续性和叙事一致性
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CharacterState:
    """人物状态数据类"""
    name: str
    location: str = "未知"
    body_state: str = "正常"
    mental_state: str = "正常"
    holding_items: List[str] = field(default_factory=list)
    emotional_state: str = "平静"


@dataclass
class ContinuityIssue:
    """连续性问题数据类"""
    type: str  # 问题类型: "character", "location", "item", "new_line", etc.
    severity: str  # "high", "medium", "low"
    character: str = ""
    expected: str = ""
    actual: str = ""
    suggestion: str = ""


class StateExtractor:
    """状态提取器 - 从章节内容中提取人物状态"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def extract_character_states(
        self,
        content: str,
        known_characters: List[str]
    ) -> Dict[str, CharacterState]:
        """
        从内容中提取人物状态

        Args:
            content: 章节内容
            known_characters: 已知角色名称列表

        Returns:
            Dict[str, CharacterState]: 提取到的人物状态
        """
        states = {}

        for char_name in known_characters:
            if char_name not in content:
                continue

            state = CharacterState(name=char_name)
            state.location = self._extract_location(char_name, content)
            state.body_state = self._extract_body_state(char_name, content)
            state.mental_state = self._extract_mental_state(char_name, content)
            state.holding_items = self._extract_items(char_name, content)
            state.emotional_state = self._extract_ending_emotion(char_name, content)

            states[char_name] = state

        return states

    def _extract_location(self, char_name: str, content: str) -> str:
        """
        提取人物位置

        Args:
            char_name: 角色名称
            content: 章节内容

        Returns:
            str: 提取到的位置
        """
        # 位置提取模式
        location_patterns = [
            # X来到/抵达/到达/进入/身处/位于/在 Y
            rf"{char_name}[^。！？]*?(?:来到|抵达|到达|进入|身处|位于|在)[^。！？]*?([^。！？\s,，{{}}\[\]]{{2,20}})(?:中|里|内|处|旁|边|前|后|上|下)?[。，！？]",
            # X返回/回到/赶回 Y
            rf"{char_name}[^。！？]*?(?:返回|回到|赶回|退回)[^。！？]*?([^。！？\s,，{{}}\[\]]{{2,20}})(?:中|里|内|处)?[。，！？]",
            # 在Y的X
            rf"在([^。！？\s,，{{}}\[\]]{{2,15}})(?:中|里|内)?的{char_name}",
            # Y中/里/内的X
            rf"([^。！？\s,，{{}}\[\]]{{2,15}})(?:中|里|内|处)的{char_name}",
        ]

        for pattern in location_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.UNICODE)
            for match in matches:
                if match.lastindex and match.lastindex > 0:
                    location = match.group(1).strip()
                    # 过滤常见动词和虚词
                    if location and len(location) >= 2:
                        filtered = self._filter_location_noise(location)
                        if filtered:
                            return filtered

        return "未知"

    def _filter_location_noise(self, location: str) -> str:
        """过滤位置信息中的噪音"""
        noise_words = [
            "这里", "那里", "哪里", "此处", "彼处", "一旁", "一边",
            "身边", "身旁", "面前", "身后", "手中", "怀里", "心中",
            "面前", "眼前", "耳边", "嘴边", "身旁", "身后", "眼前"
        ]
        for noise in noise_words:
            if noise in location:
                return ""
        return location

    def _extract_body_state(self, char_name: str, content: str) -> str:
        """
        提取人物身体状态

        Args:
            char_name: 角色名称
            content: 章节内容

        Returns:
            str: 身体状态
        """
        # 身体状态模式
        body_patterns = [
            # 受伤状态
            (r"(?:受伤|重伤|轻伤|负伤|挂彩|流血|伤口|骨折|中毒|昏迷|晕倒)", "受伤"),
            (r"(?:奄奄一息|命悬一线|危在旦夕|气息奄奄|生命垂危)", "重伤"),
            # 疲劳状态
            (r"(?:疲惫|疲劳|精疲力竭|筋疲力尽|气喘吁吁|汗流浃背)", "疲劳"),
            # 良好状态
            (r"(?:精力充沛|神采奕奕|精神焕发|容光焕发|气宇轩昂)", "良好"),
            # 生病状态
            (r"(?:生病|染病|不适|发烧|咳嗽|虚弱|病倒)", "生病"),
        ]

        # 查找角色相关的句子
        char_sentences = re.findall(
            rf"[^。！？]*{char_name}[^。！？]*[。！？]",
            content,
            re.MULTILINE | re.UNICODE
        )

        sentences_text = "".join(char_sentences)

        for pattern, state in body_patterns:
            if re.search(pattern, sentences_text):
                return state

        return "正常"

    def _extract_mental_state(self, char_name: str, content: str) -> str:
        """
        提取人物心理状态

        Args:
            char_name: 角色名称
            content: 章节内容

        Returns:
            str: 心理状态
        """
        # 心理状态模式
        mental_patterns = [
            (r"(?:愤怒|暴怒|大怒|愤怒|恼火|气愤|怒气冲冲|怒火中烧)", "愤怒"),
            (r"(?:恐惧|害怕|惊恐|畏惧|胆寒|心悸|不寒而栗)", "恐惧"),
            (r"(?:喜悦|高兴|欣喜|开心|兴奋|喜悦|欢喜|心花怒放)", "喜悦"),
            (r"(?:悲伤|难过|伤心|悲痛|哀伤|凄然|黯然神伤)", "悲伤"),
            (r"(?:紧张|焦虑|忐忑|不安|紧张|忧心忡忡|坐立不安)", "紧张"),
            (r"(?:冷静|镇定|从容|淡定|泰然自若|从容不迫)", "冷静"),
            (r"(?:犹豫|迟疑|纠结|踌躇|举棋不定|优柔寡断)", "犹豫"),
            (r"(?:坚定|坚毅|决绝|果断|毫不犹豫|斩钉截铁)", "坚定"),
        ]

        char_sentences = re.findall(
            rf"[^。！？]*{char_name}[^。！？]*[。！？]",
            content,
            re.MULTILINE | re.UNICODE
        )

        sentences_text = "".join(char_sentences)

        for pattern, state in mental_patterns:
            if re.search(pattern, sentences_text):
                return state

        return "平静"

    def _extract_items(self, char_name: str, content: str) -> List[str]:
        """
        提取人物持有物品

        Args:
            char_name: 角色名称
            content: 章节内容

        Returns:
            List[str]: 物品列表
        """
        items = []

        # 物品提取模式
        item_patterns = [
            # X手中握着/拿着/持着 Y
            rf"{char_name}[^。！？]*?(?:手中|手里)[^。！？]*?(?:握着|拿着|持着|提着|捧着|抓着)[^。！？]*?([^。！？\s,，{{}}\[\]""']{{1,10}})",
            # X取出/掏出/拿出 Y
            rf"{char_name}[^。！？]*?(?:取出|掏出|拿出|抽出|亮出)[^。！？]*?([^。！？\s,，{{}}\[\]""']{{1,10}})",
            # X的 Y (剑/刀/武器等)
            rf"{char_name}的([^。！？\s,，{{}}\[\]""']{{1,8}}(?:剑|刀|枪|杖|鞭|扇|铃|镜|珠|玉|佩|囊|袋|瓶|壶))",
        ]

        for pattern in item_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.UNICODE)
            for match in matches:
                if match.lastindex and match.lastindex > 0:
                    item = match.group(1).strip()
                    if item and len(item) >= 1 and item not in items:
                        items.append(item)

        return items

    def _extract_ending_emotion(self, char_name: str, content: str) -> str:
        """
        提取人物在章节结尾的情感状态

        Args:
            char_name: 角色名称
            content: 章节内容

        Returns:
            str: 结尾情感状态
        """
        # 取最后500字分析
        ending_text = content[-500:] if len(content) > 500 else content

        emotion_patterns = [
            (r"(?:愤怒|暴怒|大怒|愤怒|怒火|怒气)", "愤怒"),
            (r"(?:恐惧|害怕|惊恐|畏惧|胆寒|心悸)", "恐惧"),
            (r"(?:喜悦|高兴|欣喜|开心|兴奋|欢喜)", "喜悦"),
            (r"(?:悲伤|难过|伤心|悲痛|哀伤|凄然)", "悲伤"),
            (r"(?:紧张|焦虑|忐忑|不安|忧心忡忡)", "紧张"),
            (r"(?:冷静|镇定|从容|淡定|泰然)", "冷静"),
            (r"(?:希望|期待|憧憬|向往|盼望)", "希望"),
            (r"(?:失望|绝望|心灰意冷|万念俱灰)", "绝望"),
            (r"(?:疑惑|困惑|不解|迷惑|纳闷)", "疑惑"),
            (r"(?:释然|放松|轻松|解脱|如释重负)", "释然"),
        ]

        # 查找包含角色名称的句子
        char_sentences = re.findall(
            rf"[^。！？]*{char_name}[^。！？]*[。！？]",
            ending_text,
            re.MULTILINE | re.UNICODE
        )

        if not char_sentences:
            return "未知"

        sentences_text = "".join(char_sentences)

        for pattern, emotion in emotion_patterns:
            if re.search(pattern, sentences_text):
                return emotion

        return "平静"


class ContinuityChecker:
    """连续性检查器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.state_extractor = StateExtractor()

    def check_continuity(
        self,
        current_content: str,
        previous_state: Dict[str, CharacterState],
        chapter_skeleton: Dict[str, Any],
        known_characters: List[str]
    ) -> List[ContinuityIssue]:
        """
        执行连续性检查

        Args:
            current_content: 当前章节内容
            previous_state: 上一章的人物状态
            chapter_skeleton: 章节骨架/大纲
            known_characters: 已知角色列表

        Returns:
            List[ContinuityIssue]: 发现的连续性问题
        """
        issues = []

        # 检查是否需要连续性检查
        if not self._should_check_continuity(chapter_skeleton):
            return issues

        # 提取当前状态
        current_state = self.state_extractor.extract_character_states(
            current_content, known_characters
        )

        # 检查每个人物的连续性
        for char_name in known_characters:
            if char_name in previous_state and char_name in current_state:
                char_issues = self._check_character_continuity(
                    char_name,
                    previous_state[char_name],
                    current_state[char_name]
                )
                issues.extend(char_issues)

        # 检查新线Setup
        new_line_issues = self._check_new_line_setup(
            current_content, chapter_skeleton
        )
        issues.extend(new_line_issues)

        return issues

    def _should_check_continuity(self, chapter_skeleton: Dict[str, Any]) -> bool:
        """
        根据大纲标记决定是否检查连续性

        Args:
            chapter_skeleton: 章节骨架

        Returns:
            bool: 是否需要检查
        """
        # 如果明确标记不需要连续性检查
        if chapter_skeleton.get("continuity_required") is False:
            return False

        # 如果是新叙事线开头，检查新线Setup
        narrative_line = chapter_skeleton.get("narrative_line", "")
        if "新线" in str(narrative_line) or "setup" in str(narrative_line).lower():
            return True

        # 默认检查
        return chapter_skeleton.get("continuity_required", True)

    def _check_character_continuity(
        self,
        char_name: str,
        prev: CharacterState,
        curr: CharacterState
    ) -> List[ContinuityIssue]:
        """
        检查单个人物的连续性

        Args:
            char_name: 角色名称
            prev: 上一章状态
            curr: 当前章状态

        Returns:
            List[ContinuityIssue]: 连续性问题列表
        """
        issues = []

        # 检查位置变化
        if prev.location != "未知" and curr.location != "未知":
            if prev.location != curr.location:
                location_issue = self._check_location_transition(
                    prev.location, curr.location, char_name
                )
                if location_issue:
                    issues.append(location_issue)

        # 检查身体状态突变
        if prev.body_state != curr.body_state:
            body_transition_valid = self._is_valid_body_transition(
                prev.body_state, curr.body_state
            )
            if not body_transition_valid:
                issues.append(ContinuityIssue(
                    type="character",
                    severity="medium",
                    character=char_name,
                    expected=f"身体状态: {prev.body_state}",
                    actual=f"身体状态: {curr.body_state}",
                    suggestion=f"{char_name}的身体状态从'{prev.body_state}'变为'{curr.body_state}'，缺乏合理过渡"
                ))

        # 检查物品一致性
        prev_items = set(prev.holding_items)
        curr_items = set(curr.holding_items)
        lost_items = prev_items - curr_items
        gained_items = curr_items - prev_items

        if lost_items:
            issues.append(ContinuityIssue(
                type="item",
                severity="low",
                character=char_name,
                expected=f"持有物品: {', '.join(prev.holding_items)}",
                actual=f"持有物品: {', '.join(curr.holding_items)}",
                suggestion=f"{char_name}失去了物品: {', '.join(lost_items)}，请确认是否已交代丢失原因"
            ))

        return issues

    def _check_location_transition(
        self,
        prev_loc: str,
        curr_loc: str,
        character: str = ""
    ) -> Optional[ContinuityIssue]:
        """
        检查位置过渡是否合理

        Args:
            prev_loc: 上一位置
            curr_loc: 当前位置
            character: 角色名称

        Returns:
            Optional[ContinuityIssue]: 如果存在问题的返回问题对象
        """
        # 明显不合理的位置跳跃
        impossible_transitions = [
            # 从极远地点瞬间移动
            (r"(?:东|西|南|北).{0,5}(?:域|洲|界|国)", r"(?:东|西|南|北).{0,5}(?:域|洲|界|国)"),
        ]

        for prev_pattern, curr_pattern in impossible_transitions:
            if re.search(prev_pattern, prev_loc) and re.search(curr_pattern, curr_loc):
                if prev_loc != curr_loc:
                    return ContinuityIssue(
                        type="location",
                        severity="high",
                        character=character,
                        expected=f"位置: {prev_loc}",
                        actual=f"位置: {curr_loc}",
                        suggestion=f"{character or '角色'}从'{prev_loc}'出现在'{curr_loc}'，位置跳跃过大，缺乏过渡"
                    )

        return None

    def _is_valid_body_transition(self, prev_state: str, curr_state: str) -> bool:
        """
        检查身体状态变化是否有效

        Args:
            prev_state: 上一状态
            curr_state: 当前状态

        Returns:
            bool: 是否有效
        """
        # 合理的自动恢复
        valid_transitions = {
            ("疲劳", "正常"): True,
            ("生病", "正常"): True,
            ("受伤", "正常"): False,  # 受伤需要治疗
            ("重伤", "正常"): False,  # 重伤不可能自动恢复
            ("重伤", "受伤"): False,  # 需要治疗
        }

        key = (prev_state, curr_state)
        if key in valid_transitions:
            return valid_transitions[key]

        # 相同状态是有效的
        if prev_state == curr_state:
            return True

        # 状态恶化通常是有效的（除非跳跃过大）
        if prev_state == "正常" and curr_state in ["受伤", "重伤"]:
            return True

        return True  # 默认允许

    def _check_new_line_setup(
        self,
        content: str,
        skeleton: Dict[str, Any]
    ) -> List[ContinuityIssue]:
        """
        检查新叙事线的Setup是否完整

        Args:
            content: 章节内容
            skeleton: 章节骨架

        Returns:
            List[ContinuityIssue]: 问题列表
        """
        issues = []

        narrative_line = skeleton.get("narrative_line", "")
        if not narrative_line or "新线" not in str(narrative_line):
            return issues

        # 新线需要的Setup元素
        required_setup = [
            (r"(?:场景|地点|环境|背景).*?(?:描写|描述|交代)", "新场景描写"),
            (r"(?:人物|角色|新人).*?(?:登场|出场|出现|介绍)", "新人物登场"),
            (r"(?:冲突|矛盾|事件|危机).*?(?:出现|发生|爆发)", "冲突引入"),
            (r"(?:目标|动机|目的|打算|计划)", "人物动机"),
        ]

        for pattern, element_name in required_setup:
            if not re.search(pattern, content, re.MULTILINE | re.UNICODE):
                # 检查骨架中是否已声明此元素
                skeleton_text = str(skeleton)
                if element_name not in skeleton_text:
                    issues.append(ContinuityIssue(
                        type="new_line",
                        severity="medium",
                        expected=f"包含{element_name}",
                        actual=f"未找到{element_name}",
                        suggestion=f"新叙事线章节建议包含{element_name}，帮助读者理解新场景"
                    ))

        return issues

    def generate_continuity_report(
        self,
        issues: List[ContinuityIssue]
    ) -> Dict[str, Any]:
        """
        生成连续性检查报告

        Args:
            issues: 问题列表

        Returns:
            Dict: 报告数据
        """
        if not issues:
            return {
                "status": "passed",
                "total_issues": 0,
                "high_severity": 0,
                "medium_severity": 0,
                "low_severity": 0,
                "issues": []
            }

        high = sum(1 for i in issues if i.severity == "high")
        medium = sum(1 for i in issues if i.severity == "medium")
        low = sum(1 for i in issues if i.severity == "low")

        status = "failed" if high > 0 else "warning" if medium > 0 else "passed"

        return {
            "status": status,
            "total_issues": len(issues),
            "high_severity": high,
            "medium_severity": medium,
            "low_severity": low,
            "issues": [
                {
                    "type": i.type,
                    "severity": i.severity,
                    "character": i.character,
                    "expected": i.expected,
                    "actual": i.actual,
                    "suggestion": i.suggestion
                }
                for i in issues
            ]
        }
