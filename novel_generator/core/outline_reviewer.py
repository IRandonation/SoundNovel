"""
大纲审查器
支持规则硬审查和AI智能审查两种模式
"""

import yaml
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

from novel_generator.utils.multi_model_client import MultiModelClient


@dataclass
class ReviewIssue:
    category: str
    severity: str
    chapter_range: str
    description: str
    suggestion: str
    related_content: str = ""


@dataclass
class ReviewResult:
    timestamp: str
    total_issues: int
    errors: int
    warnings: int
    suggestions: int
    issues: List[ReviewIssue]
    summary: str
    review_mode: str = "rule"


AI_REVIEW_PROMPT = """你是一位专业的小说编辑，负责审查小说大纲的质量和一致性。

请从以下维度审查大纲：

1. **伏笔一致性**
   - 伏笔是否在合理章节内回收
   - 伏笔回收是否有足够的铺垫
   - 是否存在"挖坑不填"或"突然回收无铺垫"的问题
   - 伏笔与核心剧情的关联度

2. **角色弧线**
   - 主角的成长轨迹是否清晰合理
   - 配角是否有明确的作用和结局
   - 反派动机是否足够支撑冲突
   - 角色行为是否符合其性格设定
   - 角色关系发展是否自然

3. **剧情连贯性**
   - 各幕之间的衔接是否自然
   - 关键转折点是否有足够的铺垫
   - 高潮设置是否合理
   - 节奏是否平衡（是否有过快或拖沓的部分）
   - 核心冲突是否贯穿始终

4. **商业节奏**（可选）
   - 黄金三章是否足够吸引读者
   - 爽点分布是否合理
   - 是否符合平台读者的期待

请以JSON格式输出审查结果，格式如下：
```json
{
  "issues": [
    {
      "category": "伏笔一致性/角色弧线/剧情连贯性/商业节奏",
      "severity": "error/warning/suggestion",
      "chapter_range": "相关章节范围",
      "description": "问题详细描述",
      "suggestion": "具体修改建议"
    }
  ],
  "summary": "整体评价摘要",
  "highlights": ["亮点1", "亮点2"]
}
```

注意：
- error：严重问题，必须修复（如逻辑矛盾、核心设定冲突）
- warning：需要注意的问题（如伏笔跨度过长、角色弧线不完整）
- suggestion：优化建议（如节奏调整、细节丰富）

以下是小说设定和大纲："""


class OutlineReviewer:
    
    def __init__(self, config: Dict[str, Any], client: Optional[MultiModelClient] = None):
        self.config = config
        self.client = client
        self.logger = logging.getLogger(__name__)
        self.core_setting: Dict[str, Any] = {}
        self.overall_outline: Dict[str, Any] = {}
        self.characters: Dict[str, Dict] = {}
        self.foreshadowings: List[str] = []
        self.turning_points: List[Dict] = []
        self.act_structure: Dict[str, Dict] = {}
    
    def load_settings(self, core_setting_path: str, overall_outline_path: str) -> bool:
        try:
            with open(core_setting_path, 'r', encoding='utf-8') as f:
                self.core_setting = yaml.safe_load(f) or {}
            
            with open(overall_outline_path, 'r', encoding='utf-8') as f:
                self.overall_outline = yaml.safe_load(f) or {}
            
            self._extract_characters()
            self._extract_foreshadowings()
            self._extract_structure()
            
            self.logger.info(f"已加载设定: {len(self.characters)}个角色, {len(self.foreshadowings)}个伏笔")
            return True
            
        except Exception as e:
            self.logger.error(f"加载设定文件失败: {e}")
            return False
    
    def _extract_characters(self):
        self.characters = self.core_setting.get('人物小传', {})
    
    def _extract_foreshadowings(self):
        self.foreshadowings = self.core_setting.get('伏笔清单', [])
    
    def _extract_structure(self):
        self.act_structure = self.overall_outline.get('幕结构', {})
        self.turning_points = self.overall_outline.get('关键转折点', [])
    
    def review_with_rules(self) -> ReviewResult:
        issues: List[ReviewIssue] = []
        issues.extend(self._review_foreshadowing_consistency())
        issues.extend(self._review_character_arc())
        issues.extend(self._review_plot_coherence())
        
        errors = sum(1 for i in issues if i.severity == 'error')
        warnings = sum(1 for i in issues if i.severity == 'warning')
        suggestions = sum(1 for i in issues if i.severity == 'suggestion')
        
        summary = self._generate_summary(issues, errors, warnings, suggestions)
        
        return ReviewResult(
            timestamp=datetime.now().isoformat(),
            total_issues=len(issues),
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            issues=issues,
            summary=summary,
            review_mode="rule"
        )
    
    def review_with_ai(self, include_commercial: bool = False) -> ReviewResult:
        if not self.client:
            self.logger.warning("未配置AI客户端，回退到规则审查")
            return self.review_with_rules()
        
        try:
            context = self._build_ai_review_context(include_commercial)
            messages = [
                {"role": "system", "content": AI_REVIEW_PROMPT},
                {"role": "user", "content": context}
            ]
            
            response = self.client.chat_completion(
                model_type=self.config.get("provider", "deepseek"),
                messages=messages,
                temperature=0.3,
                max_tokens=4000
            )
            
            return self._parse_ai_response(response)
            
        except Exception as e:
            self.logger.error(f"AI审查失败: {e}")
            return self.review_with_rules()
    
    def _build_ai_review_context(self, include_commercial: bool) -> str:
        parts = []
        
        parts.append("=== 核心设定 ===")
        
        if self.core_setting.get('世界观'):
            world = str(self.core_setting['世界观'])
            parts.append(f"【世界观】\n{world[:1500]}..." if len(world) > 1500 else f"【世界观】\n{world}")
        
        if self.core_setting.get('核心冲突'):
            conflict = str(self.core_setting['核心冲突'])
            parts.append(f"\n【核心冲突】\n{conflict[:1000]}..." if len(conflict) > 1000 else f"\n【核心冲突】\n{conflict}")
        
        if self.characters:
            parts.append("\n【人物小传】")
            for char_name, char_info in list(self.characters.items())[:8]:
                if isinstance(char_info, dict):
                    role_type = char_info.get('角色类型', '未定义')
                    personality = char_info.get('性格', '')
                    motivation = char_info.get('核心动机', '')
                    parts.append(f"- {char_name}（{role_type}）: {personality[:100]}... 动机: {motivation[:100]}")
        
        if self.foreshadowings:
            parts.append("\n【伏笔清单】")
            for fs in self.foreshadowings[:10]:
                parts.append(f"- {str(fs)[:150]}")
        
        parts.append("\n=== 整体大纲 ===")
        
        if self.overall_outline.get('总章节数'):
            parts.append(f"【总章节数】{self.overall_outline['总章节数']}")
        
        if self.overall_outline.get('故事概述'):
            summary = str(self.overall_outline['故事概述'])
            parts.append(f"\n【故事概述】\n{summary[:800]}..." if len(summary) > 800 else f"\n【故事概述】\n{summary}")
        
        if self.act_structure:
            parts.append("\n【幕结构】")
            for act_name, act_info in self.act_structure.items():
                if isinstance(act_info, dict):
                    parts.append(f"\n{act_name}:")
                    parts.append(f"  章节范围: {act_info.get('章节范围', '未定义')}")
                    overview = str(act_info.get('概述', ''))
                    parts.append(f"  概述: {overview[:300]}..." if len(overview) > 300 else f"  概述: {overview}")
                    points = act_info.get('剧情要点', [])
                    if points:
                        parts.append(f"  剧情要点: {len(points)}个")
        
        if self.turning_points:
            parts.append("\n【关键转折点】")
            for tp in self.turning_points[:15]:
                if isinstance(tp, dict):
                    parts.append(f"- 第{tp.get('章节', '?')}章: {tp.get('事件', '')[:50]}")
        
        if include_commercial and self.core_setting.get('补充设定', {}).get('商业节奏标记'):
            parts.append("\n【商业节奏标记】")
            for mark in self.core_setting['补充设定']['商业节奏标记'][:5]:
                parts.append(f"- {str(mark)[:100]}")
        
        return "\n".join(parts)
    
    def _parse_ai_response(self, response: str) -> ReviewResult:
        issues: List[ReviewIssue] = []
        summary = "AI审查完成"
        
        json_match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
        if not json_match:
            json_match = re.search(r'\{[\s\S]*"issues"[\s\S]*\}', response)
        
        if json_match:
            try:
                json_str = json_match.group(1) if '```' in response else json_match.group(0)
                data = json.loads(json_str)
                
                for item in data.get('issues', []):
                    issues.append(ReviewIssue(
                        category=item.get('category', '其他'),
                        severity=item.get('severity', 'suggestion'),
                        chapter_range=item.get('chapter_range', '未知'),
                        description=item.get('description', ''),
                        suggestion=item.get('suggestion', '')
                    ))
                
                summary = data.get('summary', summary)
                
            except json.JSONDecodeError as e:
                self.logger.error(f"解析AI响应JSON失败: {e}")
        
        errors = sum(1 for i in issues if i.severity == 'error')
        warnings = sum(1 for i in issues if i.severity == 'warning')
        suggestions = sum(1 for i in issues if i.severity == 'suggestion')
        
        return ReviewResult(
            timestamp=datetime.now().isoformat(),
            total_issues=len(issues),
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            issues=issues,
            summary=summary,
            review_mode="ai"
        )
    
    def _review_foreshadowing_consistency(self) -> List[ReviewIssue]:
        issues = []
        
        if not self.foreshadowings:
            issues.append(ReviewIssue(
                category="伏笔一致性",
                severity="suggestion",
                chapter_range="全部",
                description="未设置任何伏笔，故事可能缺乏悬念和深度",
                suggestion="考虑在核心设定中添加伏笔清单，埋设一些贯穿全书的悬念"
            ))
            return issues
        
        for idx, fs in enumerate(self.foreshadowings):
            if not isinstance(fs, str):
                continue
            
            chapters = re.findall(r'第?(\d+)[章节]', fs)
            has_setup = '第' in fs and '章' in fs
            has_payoff = '——' in fs or '揭示' in fs or '揭晓' in fs or '回收' in fs
            
            if not has_setup:
                issues.append(ReviewIssue(
                    category="伏笔一致性",
                    severity="warning",
                    chapter_range="未知",
                    description=f"伏笔{idx+1}未标明埋设章节，难以追踪",
                    suggestion=f"建议格式：'第X章：伏笔描述——第Y章揭示/回收'",
                    related_content=fs[:50] + "..." if len(fs) > 50 else fs
                ))
            
            if has_setup and chapters:
                try:
                    setup_chapter = int(chapters[0])
                    if len(chapters) >= 2:
                        payoff_chapter = int(chapters[1])
                        gap = payoff_chapter - setup_chapter
                        
                        if gap < 5:
                            issues.append(ReviewIssue(
                                category="伏笔一致性",
                                severity="suggestion",
                                chapter_range=f"第{setup_chapter}-{payoff_chapter}章",
                                description=f"伏笔'{fs[:30]}...'埋设到回收间隔仅{gap}章，可能缺乏悬念",
                                suggestion="考虑延长伏笔跨度，在中间章节添加暗示或干扰项"
                            ))
                        elif gap > 100:
                            issues.append(ReviewIssue(
                                category="伏笔一致性",
                                severity="warning",
                                chapter_range=f"第{setup_chapter}-{payoff_chapter}章",
                                description=f"伏笔'{fs[:30]}...'跨度{gap}章，读者可能遗忘",
                                suggestion="建议在中间章节添加暗示或提醒，保持伏笔热度"
                            ))
                except (ValueError, IndexError):
                    pass
        
        return issues
    
    def _review_character_arc(self) -> List[ReviewIssue]:
        issues = []
        
        if not self.characters:
            issues.append(ReviewIssue(
                category="角色弧线",
                severity="error",
                chapter_range="全部",
                description="未设置任何角色，故事缺乏人物支撑",
                suggestion="在核心设定中添加人物小传，至少定义主角和主要配角"
            ))
            return issues
        
        protagonist = None
        for char_name, char_info in self.characters.items():
            if isinstance(char_info, dict) and char_info.get('角色类型') == '主角':
                protagonist = (char_name, char_info)
                break
        
        if not protagonist:
            issues.append(ReviewIssue(
                category="角色弧线",
                severity="error",
                chapter_range="全部",
                description="未定义主角，故事缺乏核心视角",
                suggestion="在人物小传中设置一个角色类型为'主角'的角色"
            ))
        else:
            name, info = protagonist
            required_fields = ['性格', '核心动机']
            missing = [f for f in required_fields if not info.get(f)]
            if missing:
                issues.append(ReviewIssue(
                    category="角色弧线",
                    severity="warning",
                    chapter_range="全部",
                    description=f"主角'{name}'缺少关键字段: {', '.join(missing)}",
                    suggestion=f"补充主角的{', '.join(missing)}，使角色更加立体"
                ))
        
        role_types = {}
        for char_name, char_info in self.characters.items():
            if isinstance(char_info, dict):
                role_type = char_info.get('角色类型', '未定义')
                role_types[role_type] = role_types.get(role_type, 0) + 1
        
        if '反派' not in role_types:
            issues.append(ReviewIssue(
                category="角色弧线",
                severity="warning",
                chapter_range="全部",
                description="未定义反派角色，主角可能缺乏对抗力量",
                suggestion="添加反派角色，与主角形成明确的价值冲突"
            ))
        
        if self.act_structure:
            all_plot_text = ""
            for act_name, act_info in self.act_structure.items():
                if isinstance(act_info, dict):
                    all_plot_text += str(act_info.get('概述', ''))
                    for point in act_info.get('剧情要点', []):
                        all_plot_text += str(point)
            
            for char_name in self.characters.keys():
                if char_name not in all_plot_text:
                    issues.append(ReviewIssue(
                        category="角色弧线",
                        severity="warning",
                        chapter_range="全部",
                        description=f"角色'{char_name}'在剧情大纲中未被提及",
                        suggestion=f"确保角色'{char_name}'在剧情中有明确的出场和作用"
                    ))
        
        return issues
    
    def _review_plot_coherence(self) -> List[ReviewIssue]:
        issues = []
        
        total_chapters = self.overall_outline.get('总章节数', 0)
        if not total_chapters:
            issues.append(ReviewIssue(
                category="剧情连贯性",
                severity="error",
                chapter_range="全部",
                description="未设置总章节数，无法规划故事规模",
                suggestion="在整体大纲中设置总章节数，明确故事规模"
            ))
        
        if not self.overall_outline.get('故事概述'):
            issues.append(ReviewIssue(
                category="剧情连贯性",
                severity="error",
                chapter_range="全部",
                description="未设置故事概述，缺乏整体方向",
                suggestion="在整体大纲中添加故事概述，用一段话描述从开端到结局的主线"
            ))
        
        if not self.act_structure:
            issues.append(ReviewIssue(
                category="剧情连贯性",
                severity="error",
                chapter_range="全部",
                description="未设置幕结构，故事缺乏起承转合",
                suggestion="在整体大纲中添加幕结构（如三幕结构），规划各幕的章节范围和剧情要点"
            ))
        
        if not self.turning_points:
            issues.append(ReviewIssue(
                category="剧情连贯性",
                severity="warning",
                chapter_range="全部",
                description="未设置关键转折点，故事可能缺乏高潮节奏",
                suggestion="在整体大纲中添加关键转折点，标明章节、事件和影响"
            ))
        
        return issues
    
    def _generate_summary(self, issues: List[ReviewIssue], errors: int, warnings: int, suggestions: int) -> str:
        parts = [f"共发现{len(issues)}个问题："]
        
        if errors:
            parts.append(f"❌ {errors}个严重问题需要修复")
        if warnings:
            parts.append(f"⚠️ {warnings}个警告建议处理")
        if suggestions:
            parts.append(f"💡 {suggestions}个优化建议")
        
        if not issues:
            parts.append("✅ 大纲结构完整，未发现明显问题")
        
        categories = {}
        for issue in issues:
            categories[issue.category] = categories.get(issue.category, 0) + 1
        
        if categories:
            parts.append("\n问题分布：")
            for cat, count in categories.items():
                parts.append(f"  - {cat}: {count}个")
        
        return "\n".join(parts)
    
    def save_review_result(self, result: ReviewResult, output_path: str) -> bool:
        try:
            data = {
                'timestamp': result.timestamp,
                'total_issues': result.total_issues,
                'errors': result.errors,
                'warnings': result.warnings,
                'suggestions': result.suggestions,
                'summary': result.summary,
                'review_mode': result.review_mode,
                'issues': [
                    {
                        'category': i.category,
                        'severity': i.severity,
                        'chapter_range': i.chapter_range,
                        'description': i.description,
                        'suggestion': i.suggestion,
                        'related_content': i.related_content
                    }
                    for i in result.issues
                ]
            }
            
            save_path = Path(output_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            
            self.logger.info(f"审查结果已保存: {save_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存审查结果失败: {e}")
            return False