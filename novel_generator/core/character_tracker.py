"""
人物状态追踪器
用于在章节生成过程中追踪和保持人物状态一致性
"""

import yaml
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import logging


@dataclass
class CharacterState:
    name: str
    location: str = "未知"
    body_state: str = "正常"
    mental_state: str = "正常"
    current_goal: str = ""
    relationships: Dict[str, str] = field(default_factory=dict)
    inventory: List[str] = field(default_factory=list)
    last_appearance: int = 0
    notes: List[str] = field(default_factory=list)


class CharacterTracker:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.characters: Dict[str, CharacterState] = {}
        self.tracking_file: Optional[Path] = None

    def load_from_core_setting(self, core_setting_path: str) -> bool:
        try:
            with open(core_setting_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data or "人物小传" not in data:
                return False

            for char_name, char_info in data["人物小传"].items():
                if isinstance(char_info, dict):
                    self.characters[char_name] = CharacterState(
                        name=char_name,
                        location=char_info.get("当前位置", "未知"),
                        body_state=char_info.get("身体状态", "正常"),
                        mental_state=char_info.get("心理状态", "正常"),
                        current_goal=char_info.get("当前目标", ""),
                        relationships=char_info.get("关系", {}),
                        inventory=char_info.get("物品", []),
                    )

            self.logger.info(f"从核心设定加载了 {len(self.characters)} 个角色")
            return True

        except Exception as e:
            self.logger.error(f"加载人物设定失败: {e}")
            return False

    def load_tracking_file(self, tracking_path: str) -> bool:
        try:
            self.tracking_file = Path(tracking_path)
            if not self.tracking_file.exists():
                return False

            with open(self.tracking_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data or "人物状态" not in data:
                return False

            for char_name, char_info in data["人物状态"].items():
                self.characters[char_name] = CharacterState(
                    name=char_name,
                    location=char_info.get("当前位置", "未知"),
                    body_state=char_info.get("身体状态", "正常"),
                    mental_state=char_info.get("心理状态", "正常"),
                    current_goal=char_info.get("当前目标", ""),
                    relationships=char_info.get("关系变化", {}),
                    inventory=char_info.get("持有物品", []),
                    last_appearance=char_info.get("上次出场", 0),
                    notes=char_info.get("备注", []),
                )

            self.logger.info(f"从追踪文件加载了 {len(self.characters)} 个角色状态")
            return True

        except Exception as e:
            self.logger.error(f"加载追踪文件失败: {e}")
            return False

    def update_from_chapter(
        self, chapter_num: int, content: str, state_card: Optional[Dict] = None
    ) -> Dict[str, Any]:
        updates = {}

        if state_card and "人物状态" in state_card:
            for item in state_card["人物状态"]:
                char_match = re.match(r"^([^：:]+)[：:](.+)$", str(item))
                if char_match:
                    char_name = char_match.group(1).strip()
                    char_status = char_match.group(2).strip()

                    if char_name in self.characters:
                        self.characters[char_name].mental_state = char_status
                        self.characters[char_name].last_appearance = chapter_num
                        updates[char_name] = f"心理状态更新: {char_status}"
                    else:
                        self.characters[char_name] = CharacterState(
                            name=char_name,
                            mental_state=char_status,
                            last_appearance=chapter_num,
                        )
                        updates[char_name] = f"新角色: {char_name}"

        if state_card and "当前位置" in state_card:
            for item in state_card.get("当前位置", []):
                loc_match = re.match(r"^([^：:]+)[：:](.+)$", str(item))
                if loc_match:
                    char_name = loc_match.group(1).strip()
                    location = loc_match.group(2).strip()
                    if char_name in self.characters:
                        self.characters[char_name].location = location
                        if char_name not in updates:
                            updates[char_name] = f"位置更新: {location}"
                        else:
                            updates[char_name] += f"; 位置: {location}"

        for char_name in self.characters.keys():
            if char_name in content:
                self.characters[char_name].last_appearance = chapter_num
                extracted_loc = self._extract_location_from_content(char_name, content)
                if extracted_loc and self.characters[char_name].location == "未知":
                    self.characters[char_name].location = extracted_loc
                    if char_name not in updates:
                        updates[char_name] = f"位置推断: {extracted_loc}"

        return updates

    def _extract_location_from_content(
        self, char_name: str, content: str
    ) -> Optional[str]:
        location_patterns = [
            r"{char}[^。！？]*?(来到|抵达|到达|进入|身处|位于|在)[^。！？]*?([^。！？\s]{2,15})",
            r"{char}[^。！？]*?(返回|回到|赶回|退回)[^。！？]*?([^。！？\s]{2,15})",
            r"([^。！？\s]{2,15})[^。！？]*?(中|里|内|外)[^。！？]*?{char}",
        ]

        for pattern_template in location_patterns:
            pattern = pattern_template.replace("{char}", char_name)
            match = re.search(pattern, content)
            if match:
                groups = match.groups()
                for g in groups:
                    if (
                        g != char_name
                        and len(g) >= 2
                        and g
                        not in [
                            "来到",
                            "抵达",
                            "到达",
                            "进入",
                            "身处",
                            "位于",
                            "在",
                            "返回",
                            "回到",
                            "赶回",
                            "退回",
                            "中",
                            "里",
                            "内",
                            "外",
                        ]
                    ):
                        return g
        return None

    def get_context_for_chapter(
        self, chapter_num: int, chapter_outline: Dict[str, Any]
    ) -> str:
        context_parts = ["=== 人物状态追踪 ==="]

        mentioned_chars = self._extract_mentioned_characters(chapter_outline)

        for char_name in mentioned_chars:
            if char_name in self.characters:
                char = self.characters[char_name]
                context_parts.append(f"\n【{char_name}】")
                context_parts.append(f"  位置: {char.location}")
                context_parts.append(f"  身体: {char.body_state}")
                context_parts.append(f"  心理: {char.mental_state}")
                if char.current_goal:
                    context_parts.append(f"  目标: {char.current_goal}")
                if char.relationships:
                    rel_str = "；".join(
                        [f"{k}: {v}" for k, v in char.relationships.items()]
                    )
                    context_parts.append(f"  关系: {rel_str}")
                if char.inventory:
                    context_parts.append(f"  物品: {', '.join(char.inventory)}")
                if char.last_appearance > 0:
                    gap = chapter_num - char.last_appearance
                    if gap > 3:
                        context_parts.append(f"  [注意: 已{gap}章未出场]")

        missing_chars = self._check_missing_characters(chapter_num)
        if missing_chars:
            context_parts.append(
                f"\n[提醒] 以下角色较长时间未出场: {', '.join(missing_chars)}"
            )

        return "\n".join(context_parts)

    def _extract_mentioned_characters(
        self, chapter_outline: Dict[str, Any]
    ) -> List[str]:
        mentioned = []

        text_fields = ["核心事件", "人物行动", "伏笔回收", "标题"]
        for field in text_fields:
            text = str(chapter_outline.get(field, ""))
            for char_name in self.characters.keys():
                if char_name in text and char_name not in mentioned:
                    mentioned.append(char_name)

        return mentioned

    def _check_missing_characters(self, current_chapter: int) -> List[str]:
        missing = []
        for char_name, char in self.characters.items():
            if char.last_appearance > 0:
                gap = current_chapter - char.last_appearance
                if gap > 5:
                    missing.append(char_name)
        return missing

    def save_tracking_file(self, output_path: Optional[str] = None) -> bool:
        try:
            save_path = Path(output_path) if output_path else self.tracking_file
            if not save_path:
                return False

            data = {"人物状态": {}}

            for char_name, char in self.characters.items():
                if char.last_appearance == 0 and not char.notes:
                    continue

                notes_to_save = char.notes[-10:] if len(char.notes) > 10 else char.notes

                data["人物状态"][char_name] = {
                    "当前位置": char.location,
                    "身体状态": char.body_state,
                    "心理状态": char.mental_state,
                    "当前目标": char.current_goal,
                    "关系变化": char.relationships,
                    "持有物品": char.inventory,
                    "上次出场": char.last_appearance,
                    "备注": notes_to_save,
                }

            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    data,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                )

            self.logger.info(f"人物状态追踪已保存: {save_path}")
            return True

        except Exception as e:
            self.logger.error(f"保存追踪文件失败: {e}")
            return False

    def detect_inconsistencies(
        self, chapter_content: str, chapter_num: int
    ) -> List[Dict[str, Any]]:
        issues = []

        for char_name, char in self.characters.items():
            if char_name in chapter_content:
                if char.last_appearance > 0:
                    prev_location = char.location

                    location_transitions = [
                        "走到了",
                        "来到",
                        "抵达",
                        "到达",
                        "飞到",
                        "跑进",
                        "冲进",
                    ]

                    has_transition = any(
                        t in chapter_content for t in location_transitions
                    )

                    if prev_location != "未知" and not has_transition:
                        pass

        return issues

    def get_all_characters(self) -> List[str]:
        return list(self.characters.keys())

    def get_character_state(self, name: str) -> Optional[CharacterState]:
        return self.characters.get(name)

    def set_character_state(self, name: str, **kwargs) -> bool:
        if name not in self.characters:
            self.characters[name] = CharacterState(name=name)

        char = self.characters[name]
        for key, value in kwargs.items():
            if hasattr(char, key):
                setattr(char, key, value)

        return True

    def cleanup_characters(
        self, current_chapter: int, state_card: Dict[str, Any] = None
    ) -> List[str]:
        removed = []
        dead_keywords = ["dead", "死亡", "已死", "陨落", "身死", "身亡", "阵亡", "战死"]
        retired_keywords = ["退场", "杀青", "离开", "离去", "告别", "远走", "离去"]

        for char_name in list(self.characters.keys()):
            char = self.characters[char_name]
            should_remove = False
            reason = ""

            if char.body_state and char.body_state.lower() in dead_keywords:
                gap = current_chapter - char.last_appearance
                if gap >= 5:
                    should_remove = True
                    reason = f"死亡角色, 已过{gap}章"

            if state_card:
                char_status_list = state_card.get("人物状态", [])
                for status in char_status_list:
                    if char_name in str(status):
                        for kw in retired_keywords:
                            if kw in str(status):
                                should_remove = True
                                reason = f"退场: {status}"
                                break

            if char.last_appearance > 0:
                gap = current_chapter - char.last_appearance
                if gap >= 30 and len(char.notes) == 0:
                    should_remove = True
                    reason = f"龙套角色, {gap}章未出场且无重要事件"

            if (
                char.last_appearance == 0
                and len(char.notes) == 0
                and char.location == "未知"
            ):
                should_remove = True
                reason = "模板角色, 未使用"

            if should_remove:
                del self.characters[char_name]
                removed.append(f"{char_name} ({reason})")
                self.logger.info(f"清理角色: {char_name} - {reason}")

        return removed
