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
            with open(core_setting_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data or '人物小传' not in data:
                return False
            
            for char_name, char_info in data['人物小传'].items():
                if isinstance(char_info, dict):
                    self.characters[char_name] = CharacterState(
                        name=char_name,
                        location=char_info.get('当前位置', '未知'),
                        body_state=char_info.get('身体状态', '正常'),
                        mental_state=char_info.get('心理状态', '正常'),
                        current_goal=char_info.get('当前目标', ''),
                        relationships=char_info.get('关系', {}),
                        inventory=char_info.get('物品', []),
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
            
            with open(self.tracking_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data or '人物状态' not in data:
                return False
            
            for char_name, char_info in data['人物状态'].items():
                self.characters[char_name] = CharacterState(
                    name=char_name,
                    location=char_info.get('当前位置', '未知'),
                    body_state=char_info.get('身体状态', '正常'),
                    mental_state=char_info.get('心理状态', '正常'),
                    current_goal=char_info.get('当前目标', ''),
                    relationships=char_info.get('关系变化', {}),
                    inventory=char_info.get('持有物品', []),
                    last_appearance=char_info.get('上次出场', 0),
                    notes=char_info.get('备注', []),
                )
            
            self.logger.info(f"从追踪文件加载了 {len(self.characters)} 个角色状态")
            return True
            
        except Exception as e:
            self.logger.error(f"加载追踪文件失败: {e}")
            return False
    
    def update_from_chapter(self, chapter_num: int, content: str, 
                           state_card: Optional[Dict] = None) -> Dict[str, Any]:
        updates = {}
        
        if state_card and '人物状态' in state_card:
            for item in state_card['人物状态']:
                char_match = re.match(r'^([^：:]+)[：:](.+)$', str(item))
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
                            last_appearance=chapter_num
                        )
                        updates[char_name] = f"新角色: {char_name}"
        
        for char_name in self.characters.keys():
            if char_name in content:
                self.characters[char_name].last_appearance = chapter_num
        
        return updates
    
    def get_context_for_chapter(self, chapter_num: int, 
                                chapter_outline: Dict[str, Any]) -> str:
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
                    rel_str = "；".join([f"{k}: {v}" for k, v in char.relationships.items()])
                    context_parts.append(f"  关系: {rel_str}")
                if char.inventory:
                    context_parts.append(f"  物品: {', '.join(char.inventory)}")
                if char.last_appearance > 0:
                    gap = chapter_num - char.last_appearance
                    if gap > 3:
                        context_parts.append(f"  [注意: 已{gap}章未出场]")
        
        missing_chars = self._check_missing_characters(chapter_num)
        if missing_chars:
            context_parts.append(f"\n[提醒] 以下角色较长时间未出场: {', '.join(missing_chars)}")
        
        return "\n".join(context_parts)
    
    def _extract_mentioned_characters(self, chapter_outline: Dict[str, Any]) -> List[str]:
        mentioned = []
        
        text_fields = ['核心事件', '人物行动', '伏笔回收', '标题']
        for field in text_fields:
            text = str(chapter_outline.get(field, ''))
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
            
            data = {
                '人物状态': {}
            }
            
            for char_name, char in self.characters.items():
                data['人物状态'][char_name] = {
                    '当前位置': char.location,
                    '身体状态': char.body_state,
                    '心理状态': char.mental_state,
                    '当前目标': char.current_goal,
                    '关系变化': char.relationships,
                    '持有物品': char.inventory,
                    '上次出场': char.last_appearance,
                    '备注': char.notes
                }
            
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            
            self.logger.info(f"人物状态追踪已保存: {save_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存追踪文件失败: {e}")
            return False
    
    def detect_inconsistencies(self, chapter_content: str, 
                               chapter_num: int) -> List[Dict[str, Any]]:
        issues = []
        
        for char_name, char in self.characters.items():
            if char_name in chapter_content:
                if char.last_appearance > 0:
                    prev_location = char.location
                    
                    location_transitions = [
                        "走到了", "来到", "抵达", "到达", "飞到", "跑进", "冲进"
                    ]
                    
                    has_transition = any(t in chapter_content for t in location_transitions)
                    
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