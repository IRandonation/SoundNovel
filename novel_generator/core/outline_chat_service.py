"""
大纲对话修改服务
支持通过AI对话方式修改大纲内容
"""

import yaml
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import copy

from novel_generator.utils.multi_model_client import MultiModelClient


class OutlineChatService:
    
    SYSTEM_PROMPT = """你是一位专业的小说创作顾问，帮助作者修改和完善小说大纲。
你的职责：
1. 理解作者对大纲的修改需求
2. 提供专业的修改建议
3. 生成符合规范的YAML格式内容

修改原则：
- 保持与现有设定的连贯性
- 遵循故事结构的内在逻辑
- 确保角色行为符合人设
- 伏笔埋设与回收要合理

输出格式要求：
- 当需要输出修改后的内容时，使用```yaml代码块包裹
- 先解释修改思路，再给出具体内容
- 如果修改会影响其他部分，需要提醒作者"""

    def __init__(self, config: Dict[str, Any], client: MultiModelClient):
        self.config = config
        self.client = client
        self.logger = logging.getLogger(__name__)
        self.core_setting: Dict[str, Any] = {}
        self.overall_outline: Dict[str, Any] = {}
        self.conversation_history: List[Dict[str, str]] = []
        self.core_setting_path: Optional[str] = None
        self.overall_outline_path: Optional[str] = None
    
    def load_settings(self, core_setting_path: str, overall_outline_path: str) -> bool:
        try:
            self.core_setting_path = core_setting_path
            self.overall_outline_path = overall_outline_path
            
            with open(core_setting_path, 'r', encoding='utf-8') as f:
                self.core_setting = yaml.safe_load(f) or {}
            
            with open(overall_outline_path, 'r', encoding='utf-8') as f:
                self.overall_outline = yaml.safe_load(f) or {}
            
            self.conversation_history = []
            
            self.logger.info("已加载设定文件，可以开始对话修改")
            return True
            
        except Exception as e:
            self.logger.error(f"加载设定文件失败: {e}")
            return False
    
    def chat(self, user_message: str) -> str:
        if not self.conversation_history:
            context = self._build_initial_context()
            self.conversation_history.append({
                "role": "system",
                "content": self.SYSTEM_PROMPT + "\n\n" + context
            })
        
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        try:
            response = self.client.chat_completion(
                model_type=self.config.get("provider", "deepseek"),
                messages=self.conversation_history,
                temperature=0.5,
                max_tokens=4000
            )
            
            self.conversation_history.append({
                "role": "assistant",
                "content": response
            })
            
            return response
            
        except Exception as e:
            self.logger.error(f"AI对话失败: {e}")
            return f"抱歉，对话出现问题：{e}"
    
    def _build_initial_context(self) -> str:
        context_parts = ["以下是当前小说的设定和大纲信息：\n"]
        
        context_parts.append("【核心设定摘要】")
        if self.core_setting.get('世界观'):
            world = self.core_setting['世界观']
            context_parts.append(f"世界观: {world[:200]}..." if len(str(world)) > 200 else f"世界观: {world}")
        
        if self.core_setting.get('核心冲突'):
            conflict = self.core_setting['核心冲突']
            context_parts.append(f"核心冲突: {conflict[:200]}..." if len(str(conflict)) > 200 else f"核心冲突: {conflict}")
        
        if self.core_setting.get('人物小传'):
            chars = list(self.core_setting['人物小传'].keys())
            context_parts.append(f"主要角色: {', '.join(chars[:10])}")
        
        if self.core_setting.get('伏笔清单'):
            context_parts.append(f"伏笔数量: {len(self.core_setting['伏笔清单'])}个")
        
        context_parts.append("\n【整体大纲摘要】")
        if self.overall_outline.get('总章节数'):
            context_parts.append(f"总章节数: {self.overall_outline['总章节数']}")
        
        if self.overall_outline.get('故事概述'):
            summary = self.overall_outline['故事概述']
            context_parts.append(f"故事概述: {summary[:200]}..." if len(str(summary)) > 200 else f"故事概述: {summary}")
        
        if self.overall_outline.get('幕结构'):
            acts = list(self.overall_outline['幕结构'].keys())
            context_parts.append(f"幕结构: {', '.join(acts)}")
        
        if self.overall_outline.get('关键转折点'):
            context_parts.append(f"关键转折点: {len(self.overall_outline['关键转折点'])}个")
        
        return "\n".join(context_parts)
    
    def apply_modification(self, target: str, modification: Dict[str, Any]) -> bool:
        try:
            if target == "core_setting":
                self._deep_update(self.core_setting, modification)
            elif target == "overall_outline":
                self._deep_update(self.overall_outline, modification)
            else:
                return False
            
            self.logger.info(f"已应用修改到 {target}")
            return True
            
        except Exception as e:
            self.logger.error(f"应用修改失败: {e}")
            return False
    
    def _deep_update(self, target: Dict, source: Dict):
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = copy.deepcopy(value)
    
    def extract_yaml_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        yaml_pattern = r'```yaml\s*\n(.*?)\n```'
        matches = re.findall(yaml_pattern, response, re.DOTALL)
        
        if not matches:
            return None
        
        for match in matches:
            try:
                data = yaml.safe_load(match)
                if isinstance(data, dict):
                    return data
            except yaml.YAMLError:
                continue
        
        return None
    
    def save_core_setting(self, output_path: Optional[str] = None) -> bool:
        save_path = output_path or self.core_setting_path
        if not save_path:
            return False
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.core_setting, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            
            self.logger.info(f"核心设定已保存: {save_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存核心设定失败: {e}")
            return False
    
    def save_overall_outline(self, output_path: Optional[str] = None) -> bool:
        save_path = output_path or self.overall_outline_path
        if not save_path:
            return False
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.overall_outline, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            
            self.logger.info(f"整体大纲已保存: {save_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存整体大纲失败: {e}")
            return False
    
    def save_all(self) -> bool:
        core_saved = self.save_core_setting()
        outline_saved = self.save_overall_outline()
        return core_saved and outline_saved
    
    def get_core_setting(self) -> Dict[str, Any]:
        return copy.deepcopy(self.core_setting)
    
    def get_overall_outline(self) -> Dict[str, Any]:
        return copy.deepcopy(self.overall_outline)
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        return copy.deepcopy(self.conversation_history)
    
    def clear_history(self):
        self.conversation_history = []
    
    def get_modification_suggestions(self, issue_description: str) -> str:
        prompt = f"""基于以下问题，请提供具体的修改建议：

问题描述：
{issue_description}

请分析问题原因，并提供：
1. 具体的修改方案
2. 需要调整的大纲部分
3. 可能的影响范围

如果需要修改大纲内容，请用```yaml代码块提供修改后的内容。"""
        
        return self.chat(prompt)
    
    def batch_fix_issues(self, issues: List[Dict[str, Any]]) -> str:
        issues_text = "\n\n".join([
            f"问题{i+1} [{issue.get('severity', 'warning')}]:\n"
            f"类别: {issue.get('category', '未知')}\n"
            f"章节: {issue.get('chapter_range', '未知')}\n"
            f"描述: {issue.get('description', '')}\n"
            f"建议: {issue.get('suggestion', '')}"
            for i, issue in enumerate(issues)
        ])
        
        prompt = f"""以下是审查发现的问题列表，请逐一分析并提供修改方案：

{issues_text}

请按优先级排序，先处理严重问题(error)，再处理警告(warning)，最后处理建议(suggestion)。
对每个问题提供具体的修改内容。"""
        
        return self.chat(prompt)
    
    def export_conversation(self, output_path: str) -> bool:
        try:
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "core_setting_path": self.core_setting_path,
                "overall_outline_path": self.overall_outline_path,
                "conversation": self.conversation_history
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"导出对话记录失败: {e}")
            return False