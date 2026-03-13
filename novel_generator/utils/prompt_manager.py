import yaml
from pathlib import Path
from typing import Dict, Any, List
import logging


class PromptManager:
    
    DEFAULT_PROMPT_DIR = "04_prompt"
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.prompt_dir = self.project_root / self.DEFAULT_PROMPT_DIR / "prompts"
        self.tracking_dir = self.project_root / self.DEFAULT_PROMPT_DIR / "tracking"
        self.logger = logging.getLogger(__name__)
        
        self._system_prompts = None
        self._generation_prompts = None
        self._review_prompts = None
        self._refine_prompts = None
        self._first_refine_prompts = None
        self._state_card_prompt = None
    
    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        filepath = self.prompt_dir / filename
        if not filepath.exists():
            self.logger.warning(f"Prompt文件不存在: {filepath}")
            return {}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            self.logger.error(f"加载Prompt文件失败 {filename}: {e}")
            return {}
    
    @property
    def system_prompts(self) -> Dict[str, Any]:
        if self._system_prompts is None:
            self._system_prompts = self._load_yaml("system_prompts.yaml")
        return self._system_prompts
    
    @property
    def generation_prompts(self) -> Dict[str, Any]:
        if self._generation_prompts is None:
            self._generation_prompts = self._load_yaml("generation_prompts.yaml")
        return self._generation_prompts
    
    @property
    def review_prompts(self) -> Dict[str, Any]:
        if self._review_prompts is None:
            self._review_prompts = self._load_yaml("review_prompts.yaml")
        return self._review_prompts
    
    @property
    def refine_prompts(self) -> Dict[str, Any]:
        if self._refine_prompts is None:
            self._refine_prompts = self._load_yaml("refine_prompts.yaml")
        return self._refine_prompts
    
    @property
    def first_refine_prompts(self) -> Dict[str, Any]:
        if self._first_refine_prompts is None:
            refine_data = self._load_yaml("refine_prompts.yaml")
            self._first_refine_prompts = refine_data.get("first_refine", {})
        return self._first_refine_prompts
    
    @property
    def state_card_prompt(self) -> Dict[str, Any]:
        if self._state_card_prompt is None:
            self._state_card_prompt = self._load_yaml("state_card_prompt.yaml")
        return self._state_card_prompt
    
    def get_system_prompt(self, role: str) -> str:
        prompts = self.system_prompts.get(role, {})
        return prompts.get("template", "")
    
    def get_generation_template(self) -> str:
        return self.generation_prompts.get("template", "")
    
    def get_review_template(self) -> str:
        return self.review_prompts.get("template", "")
    
    def get_refine_template(self) -> str:
        return self.refine_prompts.get("template", "")
    
    def get_first_refine_template(self) -> str:
        return self.first_refine_prompts.get("template", "")
    
    def get_state_card_template(self) -> str:
        return self.state_card_prompt.get("template", "")
    
    def get_writing_rules(self) -> list:
        return self.generation_prompts.get("writing_rules", [])
    
    def get_review_dimensions(self) -> list:
        return self.review_prompts.get("dimensions", [])
    
    def get_banned_words(self) -> list:
        banned = self.system_prompts.get("generator", {}).get("banned_words", [])
        return banned
    
    def get_ai_patterns(self) -> list:
        patterns = self.review_prompts.get("dimensions", [])
        for dim in patterns:
            if dim.get("id") == "ai_pattern":
                return dim.get("check_patterns", [])
        return []
    
    def get_pass_threshold(self) -> int:
        return self.review_prompts.get("pass_criteria", {}).get("min_total_score", 70)
    
    def build_generation_prompt(
        self,
        chapter_num: int,
        core_setting: Dict[str, Any],
        previous_context: str,
        chapter_outline: Dict[str, Any],
        character_context: str,
        foreshadowing_context: str,
        emotional_context: str,
        style_guide: Dict[str, Any],
        word_count: int
    ) -> str:
        import json
        
        template = self.get_generation_template()
        if not template:
            return self._default_generation_prompt(
                chapter_num, core_setting, previous_context, chapter_outline,
                character_context, foreshadowing_context, emotional_context,
                style_guide, word_count
            )
        
        return template.format(
            chapter_num=chapter_num,
            core_setting=json.dumps(core_setting, ensure_ascii=False, indent=2),
            previous_context=previous_context if previous_context else "无前序上下文",
            chapter_outline=json.dumps(chapter_outline, ensure_ascii=False, indent=2),
            character_context=character_context,
            foreshadowing_context=foreshadowing_context,
            emotional_context=emotional_context,
            style_guide=json.dumps(style_guide, ensure_ascii=False, indent=2),
            word_count=word_count
        )
    
    def _default_generation_prompt(
        self, chapter_num, core_setting, previous_context, chapter_outline,
        character_context, foreshadowing_context, emotional_context,
        style_guide, word_count
    ) -> str:
        import json
        
        return f"""【任务】撰写小说第{chapter_num}章正文

1. 核心设定：
{json.dumps(core_setting, ensure_ascii=False, indent=2)}

2. 前文剧情摘要（已发生，不可重复）：
{previous_context if previous_context else "无前序上下文"}

⚠️ 以上是第{chapter_num}章之前已经发生的剧情，绝对不能重复！

3. 本章大纲：
{json.dumps(chapter_outline, ensure_ascii=False, indent=2)}

4. {character_context}

5. {foreshadowing_context}

6. {emotional_context}

7. 风格要求：
{json.dumps(style_guide, ensure_ascii=False, indent=2)}

【写作法则】
1. 禁止重复前文：前文剧情已经发生，本章必须是全新剧情推进
2. 展示而非讲述：用具体动作代替情绪标签
3. 结尾落地：结尾必须落在具体感官细节上，禁止总结、升华
4. 字数要求：{word_count}字左右（误差不超过±100字）

请直接输出章节正文内容，不要添加任何解释或标记。"""
    
    def build_review_prompt(
        self,
        chapter_num: int,
        chapter_outline: Dict[str, Any],
        core_setting: Dict[str, Any],
        content: str
    ) -> str:
        import json
        
        template = self.get_review_template()
        if not template:
            return self._default_review_prompt(chapter_num, chapter_outline, core_setting, content)
        
        return template.format(
            chapter_num=chapter_num,
            chapter_outline=json.dumps(chapter_outline, ensure_ascii=False),
            core_setting=json.dumps(core_setting, ensure_ascii=False, indent=2),
            content=content[:4000]
        )
    
    def _default_review_prompt(self, chapter_num, chapter_outline, core_setting, content) -> str:
        import json
        
        return f"""请对以下小说章节进行全面评审。

【章节信息】
章节号：第{chapter_num}章
章节大纲：{json.dumps(chapter_outline, ensure_ascii=False)}

【核心设定】
{json.dumps(core_setting, ensure_ascii=False, indent=2)}

【待评审内容】
{content[:4000]}

【评审维度】（每项0-100分）

1. 剧情一致性（30%权重）
   - 是否重复了前文已经发生的剧情？（最重要！）
   - 人物行为是否符合设定？
   - 情节逻辑是否连贯？

2. 禁忌词检测（20%权重）
3. AI感检测（15%权重）
4. 情节推进（20%权重）
5. 文笔质量（15%权重）

【输出格式】JSON格式，包含每个维度的score、issues、suggestions，以及total_score和passed

评分标准：总分≥70分且无严重问题 passed=true"""
    
    def build_refine_prompt(
        self,
        chapter_num: int,
        chapter_outline: Dict[str, Any],
        issues: list,
        suggestions: list,
        content: str
    ) -> str:
        import json
        
        template = self.get_refine_template()
        issues_text = "\n".join(f"- {issue}" for issue in issues)
        suggestions_text = "\n".join(f"- {s}" for s in suggestions)
        
        if not template:
            return self._default_refine_prompt(chapter_num, chapter_outline, issues_text, suggestions_text, content)
        
        return template.format(
            chapter_num=chapter_num,
            chapter_outline=json.dumps(chapter_outline, ensure_ascii=False),
            issues=issues_text,
            suggestions=suggestions_text,
            content=content
        )
    
    def build_first_refine_prompt(
        self,
        chapter_num: int,
        chapter_outline: Dict[str, Any],
        core_setting: Dict[str, Any],
        previous_context: str,
        content: str
    ) -> str:
        import json
        
        template = self.get_first_refine_template()
        if not template:
            return self._default_first_refine_prompt(
                chapter_num, chapter_outline, core_setting, previous_context, content
            )
        
        return template.format(
            chapter_num=chapter_num,
            chapter_outline=json.dumps(chapter_outline, ensure_ascii=False),
            core_setting=json.dumps(core_setting, ensure_ascii=False, indent=2),
            previous_context=previous_context if previous_context else "无前序上下文",
            content=content
        )
    
    def _default_first_refine_prompt(
        self, chapter_num, chapter_outline, core_setting, previous_context, content
    ) -> str:
        import json
        
        return f"""请对以下新生成的小说章节进行首次润色，执行硬性规则检查和优化。

【章节信息】
章节号：第{chapter_num}章
章节大纲：{json.dumps(chapter_outline, ensure_ascii=False)}

【前文上下文】
{previous_context if previous_context else "无前序上下文"}

【核心设定】
{json.dumps(core_setting, ensure_ascii=False, indent=2)}

【待润色内容】
{content}

【硬性规则检查】（必须逐一检查，不可跳过）

⚠️ 规则1：剧情连贯性（最高优先级）
- 检查是否与前文剧情逻辑一致，无矛盾
- 检查人物行为是否符合其性格设定
- 检查时间线是否合理，无跳跃或错乱
- 检查地点转换是否自然，无突兀跳跃

⚠️ 规则2：人物一致性
- 人物对话风格是否符合其身份和性格
- 人物关系互动是否符合前文设定
- 人物称谓是否一致

⚠️ 规则3：无重复内容
- 确保没有重复前文已发生的剧情
- 同一场景描写不要重复
- 对话不要重复表达相同意思

规则4：语言质量
- 消除AI感表达：「一种莫名的」「仿佛」「似乎」「这一刻」「不由得」「不禁」
- 消除禁忌词：「复杂的思绪」「难以言喻」「命运的齿轮」「心中五味杂陈」
- 用具体动作代替情绪标签
- 用感官细节代替抽象描述

规则5：节奏控制
- 关键场景是否充分展开
- 过渡段落是否简洁
- 结尾是否落在具体细节上（禁止总结、升华）

【润色要求】
1. 发现硬性规则问题必须修正
2. 保持原有剧情走向和核心事件不变
3. 提升语言生动性和画面感
4. 保持字数规模（±10%）

请直接输出润色后的章节内容，不要添加任何解释或标记。"""
    
    def _default_refine_prompt(self, chapter_num, chapter_outline, issues, suggestions, content) -> str:
        import json
        
        return f"""请根据评审意见对以下小说章节进行润色修改。

【章节信息】
章节号：第{chapter_num}章
章节大纲：{json.dumps(chapter_outline, ensure_ascii=False)}

【评审发现的问题】
{issues}

【润色建议】
{suggestions}

【原始内容】
{content}

【润色要求】
1. 保持原有剧情走向和人物关系不变
2. 针对评审指出的问题进行修改
3. 提升语言的生动性和自然度
4. 消除AI感表达和禁忌词
5. 保持原有的字数规模

请直接输出润色后的章节内容，不要添加任何解释或标记。"""
    
    def build_state_card_prompt(self, content: str, previous_context: str) -> str:
        template = self.get_state_card_template()
        if not template:
            return self._default_state_card_prompt(content, previous_context)
        
        return template.format(
            content=content[:3000],
            previous_context=previous_context[:500] if previous_context else "无"
        )
    
    def _default_state_card_prompt(self, content, previous_context) -> str:
        return f"""分析以下小说章节的结尾状态，提取关键信息供下一章使用。

【章节内容】
{content[:3000]}

【前文状态】
{previous_context[:500] if previous_context else "无"}

请按以下JSON格式输出章节结尾状态：
{{
    "人物状态": ["角色名: 当前状态描述"],
    "当前位置": ["场景位置"],
    "情感基调": "本章结尾的情感",
    "未完成事件": ["待续的剧情线"],
    "下章建议": "对下一章开头的建议"
}}"""


def get_prompt_manager(project_root: str = ".") -> PromptManager:
    return PromptManager(project_root)