"""
章节扩写器
使用三角色流程：生成者 -> 评审者 -> 润色者
"""

import re
import logging
from pathlib import Path
from typing import Dict, Any, List

from novel_generator.config.settings import Settings
from novel_generator.config.generation_config import GenerationConfigManager
from novel_generator.utils.multi_model_client import MultiModelClient
from novel_generator.utils.prompt_manager import PromptManager
from novel_generator.core.character_tracker import CharacterTracker
from novel_generator.core.foreshadowing_tracker import ForeshadowingTracker
from novel_generator.core.emotional_arc_tracker import EmotionalArcTracker
from novel_generator.core.ai_roles import AIRoleManager, AIRole, RoleConfig, AIRolesConfig


class RetryableGenerationError(Exception):
    pass


class ChapterExpander:
    
    def __init__(self, config: Dict[str, Any], multi_model_client: MultiModelClient = None, project_root: str = "."):
        self.config = config
        self.settings = Settings(config)
        self.logger = logging.getLogger(__name__)
        self.project_root = project_root
        
        self.multi_model_client = multi_model_client or MultiModelClient(config)
        
        self.gen_config_manager = GenerationConfigManager(project_root)
        gen_config = self.gen_config_manager.get_generation_config()
        
        self.max_refine_iterations = gen_config.get('max_refine_iterations', 3)
        self.pass_score_threshold = gen_config.get('pass_score_threshold', 70)
        self.context_chapters = gen_config.get('context_chapters', 10)
        
        self.ai_role_manager = self._init_ai_role_manager()
        self.prompt_manager = PromptManager(project_root)
        
        self.character_tracker = CharacterTracker(config)
        self.foreshadowing_tracker = ForeshadowingTracker(config)
        self.emotional_arc_tracker = EmotionalArcTracker(config)
        
        self._init_trackers()
    
    def _init_ai_role_manager(self) -> AIRoleManager:
        manager = AIRoleManager(self.config, self.multi_model_client)
        saved_roles = self.gen_config_manager.get_all_roles_config()
        
        for role_name in ['generator', 'reviewer', 'refiner']:
            if role_name in saved_roles:
                role_data = saved_roles[role_name]
                role_config = RoleConfig(
                    provider=role_data.get('provider', 'zhipu'),
                    model=role_data.get('model', ''),
                    temperature=role_data.get('temperature', 0.7),
                    top_p=role_data.get('top_p', 0.9),
                    max_tokens=role_data.get('max_tokens', 8000),
                    system_prompt=role_data.get('system_prompt', ''),
                    enabled=role_data.get('enabled', True)
                )
                manager.roles_config.set_role_config(AIRole(role_name), role_config)
        
        return manager
    
    def _init_trackers(self):
        try:
            core_setting_path = Path(self.settings.path_config.core_setting_file)
            if core_setting_path.exists():
                self.character_tracker.load_from_core_setting(str(core_setting_path))
                self.foreshadowing_tracker.load_from_core_setting(str(core_setting_path))
            
            tracking_dir = Path(self.settings.path_config.prompt_dir) / "tracking"
            self.character_tracker.load_tracking_file(str(tracking_dir / "character_tracking.yaml"))
            self.foreshadowing_tracker.load_tracking_file(str(tracking_dir / "foreshadowing_tracking.yaml"))
            self.emotional_arc_tracker.save_tracking_file(str(tracking_dir / "emotional_arc_tracking.yaml"))
            
            self.logger.info("追踪器初始化完成")
        except Exception as e:
            self.logger.warning(f"追踪器初始化部分失败: {e}")
    
    def expand_chapter(
        self,
        chapter_num: int,
        chapter_outline: Dict[str, Any],
        previous_context: str = "",
        core_setting: Dict[str, Any] = None,
        style_guide: Dict[str, Any] = None
    ):
        self.logger.info(f"开始扩写第{chapter_num}章...")
        
        content = self._generate_with_review_cycle(
            chapter_num=chapter_num,
            chapter_outline=chapter_outline,
            previous_context=previous_context,
            core_setting=core_setting or {},
            style_guide=style_guide or {}
        )
        
        self._update_trackers(chapter_num, content, chapter_outline)
        state_card = self._generate_state_card(chapter_num, content, previous_context)
        
        self.logger.info(f"第{chapter_num}章扩写完成")
        return content, state_card
    
    def _generate_with_review_cycle(
        self,
        chapter_num: int,
        chapter_outline: Dict[str, Any],
        previous_context: str,
        core_setting: Dict[str, Any],
        style_guide: Dict[str, Any]
    ) -> str:
        content = self._generate_chapter(
            chapter_num=chapter_num,
            chapter_outline=chapter_outline,
            previous_context=previous_context,
            core_setting=core_setting,
            style_guide=style_guide
        )
        
        for iteration in range(self.max_refine_iterations):
            review_result = self._review_chapter(
                content=content,
                chapter_num=chapter_num,
                chapter_outline=chapter_outline,
                core_setting=core_setting,
                style_guide=style_guide
            )
            
            if review_result.get('passed', False):
                self.logger.info(f"第{chapter_num}章评审通过 (第{iteration + 1}次评审)")
                return content
            
            self.logger.info(f"第{chapter_num}章评审未通过 (总分: {review_result.get('total_score', 0)}), 进行润色...")
            
            content = self._refine_chapter(
                content=content,
                chapter_num=chapter_num,
                chapter_outline=chapter_outline,
                review_result=review_result,
                style_guide=style_guide
            )
        
        final_review = self._review_chapter(
            content=content,
            chapter_num=chapter_num,
            chapter_outline=chapter_outline,
            core_setting=core_setting,
            style_guide=style_guide
        )
        
        if not final_review.get('passed', False):
            self.logger.warning(f"第{chapter_num}章经过{self.max_refine_iterations}次润色仍未达标，使用当前版本")
        
        return content
    
    def _generate_chapter(
        self,
        chapter_num: int,
        chapter_outline: Dict[str, Any],
        previous_context: str,
        core_setting: Dict[str, Any],
        style_guide: Dict[str, Any]
    ) -> str:
        word_count_target = self._extract_word_count(chapter_outline)
        
        character_context = self.character_tracker.get_context_for_chapter(chapter_num, chapter_outline)
        foreshadowing_context = self.foreshadowing_tracker.get_context_for_chapter(chapter_num)
        emotional_context = self.emotional_arc_tracker.get_context_for_chapter(chapter_num)
        
        prompt = self.prompt_manager.build_generation_prompt(
            chapter_num=chapter_num,
            core_setting=core_setting,
            previous_context=previous_context,
            chapter_outline=chapter_outline,
            character_context=character_context,
            foreshadowing_context=foreshadowing_context,
            emotional_context=emotional_context,
            style_guide=style_guide,
            word_count=word_count_target
        )
        
        response = self.ai_role_manager.chat_completion(
            role=AIRole.GENERATOR,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return self._clean_response(response)
    
    def _review_chapter(
        self,
        content: str,
        chapter_num: int,
        chapter_outline: Dict[str, Any],
        core_setting: Dict[str, Any],
        style_guide: Dict[str, Any]
    ) -> Dict[str, Any]:
        prompt = self.prompt_manager.build_review_prompt(
            chapter_num=chapter_num,
            chapter_outline=chapter_outline,
            core_setting=core_setting,
            content=content
        )
        
        response = self.ai_role_manager.chat_completion(
            role=AIRole.REVIEWER,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return self._parse_review_response(response)
    
    def _parse_review_response(self, response: str) -> Dict[str, Any]:
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                import json
                return json.loads(json_match.group())
        except:
            pass
        
        return {
            "total_score": 0,
            "passed": False,
            "main_issues": ["评审结果解析失败"],
            "refine_suggestions": ["请重新评审"],
            "raw_response": response
        }
    
    def _refine_chapter(
        self,
        content: str,
        chapter_num: int,
        chapter_outline: Dict[str, Any],
        review_result: Dict[str, Any],
        style_guide: Dict[str, Any]
    ) -> str:
        main_issues = review_result.get('main_issues', [])
        refine_suggestions = review_result.get('refine_suggestions', [])
        
        prompt = self.prompt_manager.build_refine_prompt(
            chapter_num=chapter_num,
            chapter_outline=chapter_outline,
            issues=main_issues,
            suggestions=refine_suggestions,
            content=content
        )
        
        response = self.ai_role_manager.chat_completion(
            role=AIRole.REFINER,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return self._clean_response(response)
    
    def _clean_response(self, response: str) -> str:
        if not response:
            return ""
        
        response = response.strip()
        
        if response.startswith('```'):
            lines = response.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            response = '\n'.join(lines)
        
        return response.strip()
    
    def _extract_word_count(self, chapter_outline: Dict[str, Any]) -> int:
        raw_value = chapter_outline.get('字数目标', self.settings.get_default_word_count())
        if isinstance(raw_value, int):
            return raw_value
        if isinstance(raw_value, str):
            matched = re.search(r'(\d+)', raw_value)
            if matched:
                return int(matched.group(1))
        return self.settings.get_default_word_count()
    
    def _update_trackers(self, chapter_num: int, content: str, chapter_outline: Dict[str, Any]):
        self.character_tracker.update_from_chapter(chapter_num, content)
        self.foreshadowing_tracker.plant_foreshadowing(chapter_num, content)
        self.foreshadowing_tracker.check_recovery(chapter_num, content, chapter_outline)
        self.emotional_arc_tracker.analyze_chapter(chapter_num, content, chapter_outline)
        
        self._save_tracking_files()
    
    def _save_tracking_files(self):
        try:
            tracking_dir = Path(self.settings.path_config.prompt_dir) / "tracking"
            tracking_dir.mkdir(parents=True, exist_ok=True)
            
            self.character_tracker.save_tracking_file(str(tracking_dir / "character_tracking.yaml"))
            self.foreshadowing_tracker.save_tracking_file(str(tracking_dir / "foreshadowing_tracking.yaml"))
            self.emotional_arc_tracker.save_tracking_file(str(tracking_dir / "emotional_arc_tracking.yaml"))
        except Exception as e:
            self.logger.error(f"保存追踪文件失败: {e}")
    
    def _generate_state_card(self, chapter_num: int, content: str, previous_context: str) -> Dict[str, Any]:
        prompt = self.prompt_manager.build_state_card_prompt(content, previous_context)
        
        try:
            response = self.ai_role_manager.chat_completion(
                role=AIRole.REVIEWER,
                messages=[
                    {"role": "system", "content": "你是小说连续性分析助手，擅长提取章节结尾状态。"},
                    {"role": "user", "content": prompt}
                ]
            )
            
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                import json
                return json.loads(json_match.group())
        except Exception as e:
            self.logger.warning(f"生成状态卡失败: {e}")
        
        return {
            "人物状态": [],
            "当前位置": [],
            "情感基调": "",
            "未完成事件": [],
            "下章建议": ""
        }
    
    def save_chapter(self, chapter_num: int, content: str, output_dir: str = None) -> str:
        output_path = Path(output_dir or self.settings.path_config.draft_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        file_path = output_path / f"第{chapter_num:04d}章.txt"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.logger.info(f"章节已保存: {file_path}")
        return str(file_path)
    
    def expand_multiple_chapters(
        self,
        outline: Dict[str, Any],
        start_chapter: int,
        end_chapter: int,
        core_setting: Dict[str, Any] = None,
        style_guide: Dict[str, Any] = None,
        context_window: int = 10
    ) -> List[Dict[str, Any]]:
        results = []
        context_parts = []
        
        for chapter_num in range(start_chapter, end_chapter + 1):
            chapter_key = f"第{chapter_num}章"
            chapter_outline = outline.get(chapter_key, {})
            
            if not chapter_outline:
                self.logger.warning(f"未找到第{chapter_num}章的大纲，跳过")
                continue
            
            previous_context = "\n\n".join(context_parts[-context_window:]) if context_parts else ""
            
            try:
                content, state_card = self.expand_chapter(
                    chapter_num=chapter_num,
                    chapter_outline=chapter_outline,
                    previous_context=previous_context,
                    core_setting=core_setting or {},
                    style_guide=style_guide or {}
                )
                
                file_path = self.save_chapter(chapter_num, content)
                
                context_parts.append(f"【第{chapter_num}章摘要】\n{content[:500]}...")
                
                results.append({
                    "chapter": chapter_num,
                    "file_path": file_path,
                    "word_count": len(content),
                    "state_card": state_card,
                    "success": True
                })
                
            except Exception as e:
                self.logger.error(f"扩写第{chapter_num}章失败: {e}")
                results.append({
                    "chapter": chapter_num,
                    "error": str(e),
                    "success": False
                })
        
        return results