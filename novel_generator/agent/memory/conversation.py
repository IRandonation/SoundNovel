"""对话记忆模块"""

import json
import uuid
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class DialogTurn:
    """对话轮次"""
    turn_id: str
    timestamp: str
    user_input: str
    agent_response: str
    intent_action: Optional[str] = None


class ConversationMemory:
    """对话记忆（短期）"""

    def __init__(self, max_turns: int = 50):
        self.max_turns = max_turns
        self.turns: deque = deque(maxlen=max_turns)

    def add_turn(self, user_input: str, agent_response: str, intent_action: str = None) -> DialogTurn:
        """添加对话记录"""
        turn = DialogTurn(
            turn_id=str(uuid.uuid4())[:8],
            timestamp=datetime.now().isoformat(),
            user_input=user_input,
            agent_response=agent_response,
            intent_action=intent_action
        )
        self.turns.append(turn)
        return turn

    def get_recent(self, n: int = 10) -> List[DialogTurn]:
        """获取最近 n 轮对话"""
        return list(self.turns)[-n:]

    def get_all(self) -> List[DialogTurn]:
        """获取所有对话"""
        return list(self.turns)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于保存）"""
        return {
            'max_turns': self.max_turns,
            'turns': [
                {
                    'turn_id': turn.turn_id,
                    'timestamp': turn.timestamp,
                    'user_input': turn.user_input,
                    'agent_response': turn.agent_response,
                    'intent_action': turn.intent_action
                }
                for turn in self.turns
            ]
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """从字典加载"""
        self.max_turns = data.get('max_turns', 50)
        self.turns = deque(maxlen=self.max_turns)

        for turn_data in data.get('turns', []):
            turn = DialogTurn(
                turn_id=turn_data['turn_id'],
                timestamp=turn_data['timestamp'],
                user_input=turn_data['user_input'],
                agent_response=turn_data['agent_response'],
                intent_action=turn_data.get('intent_action')
            )
            self.turns.append(turn)

    def save_to_file(self, filepath: str) -> None:
        """保存到 JSON 文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def load_from_file(self, filepath: str) -> bool:
        """从 JSON 文件加载"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.from_dict(data)
            return True
        except (FileNotFoundError, json.JSONDecodeError):
            return False

    def clear(self) -> None:
        """清空记忆"""
        self.turns.clear()

    def count(self) -> int:
        """返回对话轮数"""
        return len(self.turns)
