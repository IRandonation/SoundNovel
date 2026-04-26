"""意图解析器"""

import re
import uuid
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

from novel_generator.agent.intent.rules import compile_rules


@dataclass
class UserIntent:
    """用户意图数据结构"""
    action: str  # generate, modify, query_character, query_foreshadowing, status, plan, help, exit
    target_type: Optional[str] = None  # chapter, character, foreshadowing, project, outline, system
    target_id: Optional[str] = None  # 具体ID（章节号、人物名）
    parameters: Dict[str, Any] = field(default_factory=dict)  # 额外参数
    raw_input: str = ""  # 原始输入
    confidence: float = 0.0  # 解析置信度 (0-1)


class IntentParser:
    """基于规则的意图解析器"""

    def __init__(self):
        self.compiled_rules = compile_rules()

    def parse(self, user_input: str) -> UserIntent:
        """解析用户输入，返回意图"""
        user_input = user_input.strip()

        if not user_input:
            return UserIntent(
                action="unknown",
                raw_input=user_input,
                confidence=0.0
            )

        # 尝试规则匹配
        return self._try_rules(user_input)

    def _try_rules(self, user_input: str) -> UserIntent:
        """使用预定义规则匹配"""
        for pattern, intent_template in self.compiled_rules:
            match = pattern.match(user_input)
            if match:
                # 提取捕获组作为参数
                params = {}
                if match.groups():
                    params['target'] = match.group(1)

                # 构建意图
                intent = UserIntent(
                    action=intent_template.get('action', 'unknown'),
                    target_type=intent_template.get('target_type'),
                    target_id=match.group(1) if match.groups() else None,
                    parameters=params,
                    raw_input=user_input,
                    confidence=0.95 if intent_template.get('action') else 0.5
                )
                return intent

        # 没有匹配到规则
        return UserIntent(
            action="unknown",
            raw_input=user_input,
            confidence=0.0
        )

    def extract_chapter_number(self, text: str) -> Optional[int]:
        """从文本中提取章节号"""
        patterns = [
            r"第(\d+)章",
            r"(\d+)章",
            r"chapter\s*(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        return None

    def extract_character_name(self, text: str) -> Optional[str]:
        """从文本中提取人物名"""
        # 简单实现：查找常见的询问模式
        patterns = [
            r"(.+?)现在",
            r"(.+?)的状态",
            r"(.+?)在哪",
            r"(.+?)怎么样",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                # 过滤掉常见词
                if name not in ['我', '你', '他', '她', '它', '我们', '你们', '他们']:
                    return name
        return None
