"""
情感弧线追踪器
用于追踪故事的情感节奏和情绪走向
"""

import yaml
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import logging


@dataclass
class EmotionalBeat:
    chapter: int
    emotion: str
    intensity: int
    event: str
    character: str = ""


class EmotionalArcTracker:
    
    EMOTION_SPECTRUM = {
        '希望': {'opposite': '绝望', 'intensity_base': 6},
        '喜悦': {'opposite': '悲伤', 'intensity_base': 7},
        '愤怒': {'opposite': '平静', 'intensity_base': 8},
        '恐惧': {'opposite': '安心', 'intensity_base': 7},
        '惊讶': {'opposite': '预期', 'intensity_base': 5},
        '期待': {'opposite': '失望', 'intensity_base': 5},
        '紧张': {'opposite': '放松', 'intensity_base': 6},
        '感动': {'opposite': '冷漠', 'intensity_base': 7},
        '绝望': {'opposite': '希望', 'intensity_base': 8},
        '平静': {'opposite': '激动', 'intensity_base': 3},
    }
    
    EMOTION_KEYWORDS = {
        '希望': ['希望', '期盼', '梦想', '未来', '期待', '曙光'],
        '喜悦': ['笑', '开心', '高兴', '快乐', '欣喜', '幸福'],
        '愤怒': ['怒', '愤', '恨', '气', '火', '暴怒'],
        '恐惧': ['怕', '惧', '恐', '惊', '吓', '颤栗'],
        '惊讶': ['惊', '意外', '震惊', '没想到', '出乎意料'],
        '期待': ['等着', '盼', '期待', '即将', '将要'],
        '紧张': ['紧', '绷', '急', '焦', '忐忑', '紧张'],
        '感动': ['感动', '暖', '泪', '触动', '心酸'],
        '绝望': ['绝望', '死心', '放弃', '崩溃', '黑暗'],
        '平静': ['平静', '安', '静', '淡', '从容'],
    }
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.beats: List[EmotionalBeat] = []
        self.current_arc: str = "上升"
        self.arc_start_chapter: int = 1
    
    def analyze_chapter(self, chapter_num: int, content: str, 
                       chapter_outline: Dict[str, Any]) -> EmotionalBeat:
        emotion_scores: Dict[str, int] = {}
        
        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            score = sum(content.count(kw) for kw in keywords)
            if score > 0:
                emotion_scores[emotion] = score
        
        if not emotion_scores:
            primary_emotion = '平静'
            intensity = 3
        else:
            primary_emotion = max(emotion_scores.keys(), key=lambda e: emotion_scores[e])
            intensity = min(10, self.EMOTION_SPECTRUM[primary_emotion]['intensity_base'] + emotion_scores[primary_emotion] // 2)
        
        event = str(chapter_outline.get('核心事件', ''))[:50]
        
        beat = EmotionalBeat(
            chapter=chapter_num,
            emotion=primary_emotion,
            intensity=intensity,
            event=event
        )
        
        self.beats.append(beat)
        self._update_arc_status(beat)
        
        return beat
    
    def _update_arc_status(self, new_beat: EmotionalBeat):
        if len(self.beats) < 2:
            return
        
        prev_beat = self.beats[-2]
        
        if new_beat.intensity > prev_beat.intensity + 1:
            self.current_arc = "上升"
        elif new_beat.intensity < prev_beat.intensity - 1:
            self.current_arc = "下降"
        else:
            pass
    
    def get_context_for_chapter(self, chapter_num: int) -> str:
        context_parts = ["=== 情感弧线 ==="]
        
        recent_beats = [b for b in self.beats if b.chapter >= chapter_num - 3]
        
        if recent_beats:
            context_parts.append("\n近3章情感走向:")
            for beat in recent_beats:
                bar = "█" * beat.intensity + "░" * (10 - beat.intensity)
                context_parts.append(f"  第{beat.chapter}章: {beat.emotion} {bar}")
        
        context_parts.append(f"\n当前弧线: {self.current_arc}")
        
        suggestions = self._get_emotion_suggestions(chapter_num)
        if suggestions:
            context_parts.append(f"建议: {suggestions}")
        
        return "\n".join(context_parts)
    
    def _get_emotion_suggestions(self, chapter_num: int) -> str:
        if len(self.beats) < 3:
            return "开篇阶段，建议建立情感基调"
        
        recent_emotions = [b.emotion for b in self.beats[-3:]]
        recent_intensities = [b.intensity for b in self.beats[-3:]]
        
        if all(i >= 7 for i in recent_intensities):
            return "情感强度持续高涨，建议适当缓解节奏"
        
        if all(i <= 4 for i in recent_intensities):
            return "情感强度持续低迷，建议增加冲突或转折"
        
        if len(set(recent_emotions)) == 1:
            return f"连续{recent_emotions[0]}，建议引入情感变化"
        
        if self.current_arc == "上升":
            return "弧线上升中，可继续推进或准备转折"
        else:
            return "弧线下降中，适合反思或铺垫新冲突"
    
    def get_arc_analysis(self) -> Dict[str, Any]:
        if not self.beats:
            return {'状态': '未开始'}
        
        intensities = [b.intensity for b in self.beats]
        emotions = [b.emotion for b in self.beats]
        
        return {
            '总章节': len(self.beats),
            '平均强度': sum(intensities) / len(intensities),
            '最高强度': max(intensities),
            '最低强度': min(intensities),
            '主要情感': max(set(emotions), key=emotions.count),
            '当前弧线': self.current_arc
        }
    
    def detect_emotional_issues(self, chapter_num: int) -> List[str]:
        issues = []
        
        if len(self.beats) >= 5:
            recent = self.beats[-5:]
            if all(b.intensity >= 8 for b in recent):
                issues.append("连续5章高强度情感，读者可能疲劳")
            
            if all(b.intensity <= 3 for b in recent):
                issues.append("连续5章低强度情感，节奏可能拖沓")
        
        if len(self.beats) >= 3:
            recent_emotions = [b.emotion for b in self.beats[-3:]]
            if len(set(recent_emotions)) == 1:
                issues.append(f"连续3章情感类型相同({recent_emotions[0]})，建议变化")
        
        return issues
    
    def save_tracking_file(self, output_path: str) -> bool:
        try:
            data = {
                '情感弧线': {
                    '当前状态': self.current_arc,
                    '起点章节': self.arc_start_chapter,
                    '节拍记录': [
                        {
                            '章节': b.chapter,
                            '情感': b.emotion,
                            '强度': b.intensity,
                            '事件': b.event
                        }
                        for b in self.beats
                    ]
                }
            }
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            
            return True
            
        except Exception as e:
            self.logger.error(f"保存情感弧线追踪失败: {e}")
            return False