"""
伏笔追踪器
用于追踪伏笔的埋设和回收，确保故事逻辑连贯
"""

import yaml
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging


@dataclass
class Foreshadowing:
    description: str
    plant_chapter: int
    planned_recover_chapter: int = 0
    actual_recover_chapter: int = 0
    status: str = "pending"
    hints: List[str] = field(default_factory=list)
    importance: str = "normal"


class ForeshadowingTracker:
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.foreshadowings: Dict[str, Foreshadowing] = {}
        self.tracking_file: Optional[Path] = None
    
    def load_from_core_setting(self, core_setting_path: str) -> bool:
        try:
            with open(core_setting_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data or '伏笔清单' not in data:
                return False
            
            foreshadowing_list = data['伏笔清单']
            if not isinstance(foreshadowing_list, list):
                return False
            
            for idx, item in enumerate(foreshadowing_list):
                if isinstance(item, str):
                    self._parse_foreshadowing_string(item, idx)
                elif isinstance(item, dict):
                    self._parse_foreshadowing_dict(item, idx)
            
            self.logger.info(f"从核心设定加载了 {len(self.foreshadowings)} 个伏笔")
            return True
            
        except Exception as e:
            self.logger.error(f"加载伏笔清单失败: {e}")
            return False
    
    def _parse_foreshadowing_string(self, text: str, idx: int):
        chapter_match = re.search(r'第?(\d+)[章节]', text)
        planned_chapter = int(chapter_match.group(1)) if chapter_match else 0
        
        key = f"伏笔_{idx+1}"
        self.foreshadowings[key] = Foreshadowing(
            description=text,
            plant_chapter=0,
            planned_recover_chapter=planned_chapter,
            status="pending"
        )
    
    def _parse_foreshadowing_dict(self, item: Dict, idx: int):
        desc = item.get('描述', item.get('内容', ''))
        key = item.get('名称', f"伏笔_{idx+1}")
        
        self.foreshadowings[key] = Foreshadowing(
            description=desc,
            plant_chapter=item.get('埋设章节', 0),
            planned_recover_chapter=item.get('回收章节', 0),
            status=item.get('状态', 'pending'),
            importance=item.get('重要性', 'normal')
        )
    
    def load_tracking_file(self, tracking_path: str) -> bool:
        try:
            self.tracking_file = Path(tracking_path)
            if not self.tracking_file.exists():
                return False
            
            with open(self.tracking_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data or '伏笔追踪' not in data:
                return False
            
            for key, item in data['伏笔追踪'].items():
                self.foreshadowings[key] = Foreshadowing(
                    description=item.get('描述', ''),
                    plant_chapter=item.get('埋设章节', 0),
                    planned_recover_chapter=item.get('计划回收章节', 0),
                    actual_recover_chapter=item.get('实际回收章节', 0),
                    status=item.get('状态', 'pending'),
                    hints=item.get('提示', []),
                    importance=item.get('重要性', 'normal')
                )
            
            self.logger.info(f"从追踪文件加载了 {len(self.foreshadowings)} 个伏笔")
            return True
            
        except Exception as e:
            self.logger.error(f"加载伏笔追踪文件失败: {e}")
            return False
    
    def plant_foreshadowing(self, chapter_num: int, content: str) -> List[Dict[str, Any]]:
        planted = []
        
        for key, fs in self.foreshadowings.items():
            if fs.status != "pending":
                continue
            
            keywords = self._extract_keywords(fs.description)
            hits = sum(1 for kw in keywords if kw in content)
            
            if hits >= len(keywords) * 0.5:
                fs.plant_chapter = chapter_num
                fs.status = "planted"
                planted.append({
                    'key': key,
                    'description': fs.description,
                    'chapter': chapter_num
                })
        
        return planted
    
    def check_recovery(self, chapter_num: int, content: str, 
                       chapter_outline: Dict[str, Any]) -> List[Dict[str, Any]]:
        recovered = []
        
        outline_text = str(chapter_outline.get('伏笔回收', ''))
        if outline_text and outline_text != "无":
            for key, fs in self.foreshadowings.items():
                if fs.status != "planted":
                    continue
                
                keywords = self._extract_keywords(fs.description)
                outline_hits = sum(1 for kw in keywords if kw in outline_text)
                content_hits = sum(1 for kw in keywords if kw in content)
                
                if outline_hits >= 1 or content_hits >= len(keywords) * 0.5:
                    fs.actual_recover_chapter = chapter_num
                    fs.status = "recovered"
                    recovered.append({
                        'key': key,
                        'description': fs.description,
                        'plant_chapter': fs.plant_chapter,
                        'recover_chapter': chapter_num,
                        'gap': chapter_num - fs.plant_chapter
                    })
        
        return recovered
    
    def get_pending_for_chapter(self, chapter_num: int) -> List[Dict[str, Any]]:
        should_plant = []
        should_recover = []
        
        for key, fs in self.foreshadowings.items():
            if fs.planned_recover_chapter == chapter_num and fs.status == "planted":
                should_recover.append({
                    'key': key,
                    'description': fs.description,
                    'plant_chapter': fs.plant_chapter
                })
            
            if fs.status == "pending" and not should_plant:
                should_plant.append({
                    'key': key,
                    'description': fs.description,
                    'planned_recover': fs.planned_recover_chapter
                })
        
        return {
            '可埋设': should_plant[:3],
            '应回收': should_recover
        }
    
    def get_context_for_chapter(self, chapter_num: int) -> str:
        context_parts = ["=== 伏笔追踪 ==="]
        
        planted_not_recovered = [
            (k, fs) for k, fs in self.foreshadowings.items() 
            if fs.status == "planted"
        ]
        
        if planted_not_recovered:
            context_parts.append("\n已埋设待回收:")
            for key, fs in planted_not_recovered[:5]:
                gap = chapter_num - fs.plant_chapter
                context_parts.append(f"  [{key}] {fs.description[:30]}... (已{gap}章)")
                if fs.planned_recover_chapter > 0:
                    if chapter_num >= fs.planned_recover_chapter - 2:
                        context_parts.append(f"    ★ 计划第{fs.planned_recover_chapter}章回收")
        
        pending = [fs for fs in self.foreshadowings.values() if fs.status == "pending"]
        if pending:
            context_parts.append(f"\n待埋设: {len(pending)}个")
        
        overdue = self._check_overdue_foreshadowings(chapter_num)
        if overdue:
            context_parts.append(f"\n⚠️ 超期未回收: {len(overdue)}个")
            for fs in overdue[:3]:
                context_parts.append(f"  - {fs.description[:30]}... (计划第{fs.planned_recover_chapter}章)")
        
        return "\n".join(context_parts)
    
    def _check_overdue_foreshadowings(self, chapter_num: int) -> List[Foreshadowing]:
        overdue = []
        for fs in self.foreshadowings.values():
            if fs.status == "planted" and fs.planned_recover_chapter > 0:
                if chapter_num > fs.planned_recover_chapter + 5:
                    overdue.append(fs)
        return overdue
    
    def _extract_keywords(self, text: str) -> List[str]:
        cleaned = re.sub(r'[，。！？、；：""''（）\[\]【】]', ' ', text)
        words = cleaned.split()
        return [w for w in words if len(w) >= 2][:10]
    
    def save_tracking_file(self, output_path: Optional[str] = None) -> bool:
        try:
            save_path = Path(output_path) if output_path else self.tracking_file
            if not save_path:
                return False
            
            data = {'伏笔追踪': {}}
            
            for key, fs in self.foreshadowings.items():
                data['伏笔追踪'][key] = {
                    '描述': fs.description,
                    '埋设章节': fs.plant_chapter,
                    '计划回收章节': fs.planned_recover_chapter,
                    '实际回收章节': fs.actual_recover_chapter,
                    '状态': fs.status,
                    '提示': fs.hints,
                    '重要性': fs.importance
                }
            
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            
            return True
            
        except Exception as e:
            self.logger.error(f"保存伏笔追踪文件失败: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        total = len(self.foreshadowings)
        planted = sum(1 for fs in self.foreshadowings.values() if fs.status == "planted")
        recovered = sum(1 for fs in self.foreshadowings.values() if fs.status == "recovered")
        pending = sum(1 for fs in self.foreshadowings.values() if fs.status == "pending")
        
        return {
            '总数': total,
            '已埋设': planted,
            '已回收': recovered,
            '待处理': pending,
            '回收率': f"{recovered/total*100:.1f}%" if total > 0 else "0%"
        }