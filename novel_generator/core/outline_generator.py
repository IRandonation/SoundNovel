"""
大纲生成器
负责基于原始素材生成章节大纲
采用两阶段生成架构：幕级规划 → 章级骨架（骨架直接驱动扩写）
"""

import json
import re
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging

from novel_generator.config.settings import Settings
from novel_generator.utils.multi_model_client import MultiModelClient
from novel_generator.core.ai_roles import AIRoleManager, AIRole

class RetryableGenerationError(Exception):
    pass


class ActLevelPlanner:
    """幕级规划器 — 单次API调用生成全部幕规划，源材料只注入一次"""

    def __init__(self, config: Dict[str, Any], ai_role_manager: AIRoleManager):
        self.config = config
        self.ai_role_manager = ai_role_manager
        self.logger = logging.getLogger(__name__)

    def generate_act_plan(
        self,
        core_setting: Dict[str, Any],
        overall_outline: Dict[str, Any],
        num_acts: int = 0,
        total_chapters: int = 150,
    ) -> Dict[str, Any]:
        """
        生成幕级规划。单次API调用生成全部幕，AI在上下文中协调各幕避免重复。
        """
        act_structure = self._extract_act_structure(overall_outline)
        actual_num_acts = len(act_structure) if act_structure else num_acts

        self.logger.info(f"开始生成幕级规划（单次调用），共{actual_num_acts}幕，{total_chapters}章")

        prompt = self._build_all_acts_prompt(
            core_setting, overall_outline, act_structure, actual_num_acts
        )
        self.logger.debug(f"幕规划 Prompt 长度: {len(prompt)} 字符")
        response = self._call_ai_api(prompt)
        act_plan = self._parse_all_acts_response(response)

        self.logger.info(f"幕级规划生成完成，共{len(act_plan.get('幕规划', act_plan))}幕")
        return act_plan

    def _extract_act_structure(
        self, overall_outline: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """从整体大纲中提取幕结构信息（真实幕名、章范围、标题、概述）"""
        outline_data = overall_outline.get("幕结构", overall_outline)
        acts = []

        for key, value in outline_data.items():
            if not isinstance(value, dict):
                continue
            chapter_range = value.get("章节范围", "")
            chapters = self._parse_chapter_range(chapter_range)
            acts.append({
                "name": key,
                "章节范围": chapter_range,
                "标题": value.get("标题", ""),
                "概述": value.get("概述", ""),
                "章数": chapters,
                "剧情要点": value.get("剧情要点", []),
            })

        if not acts:
            # fallback: 等分计算
            total = overall_outline.get("总章节数", 150)
            preset_num = max(3, len(overall_outline.get("幕结构", {})))
            chapters_per_act = total // preset_num
            for i in range(preset_num):
                start = i * chapters_per_act + 1
                end = min((i + 1) * chapters_per_act, total)
                acts.append({
                    "name": f"第{i + 1}幕",
                    "章节范围": f"第{start}-{end}章",
                    "标题": "",
                    "概述": "",
                    "章数": end - start + 1,
                    "剧情要点": [],
                })

        return acts

    def _parse_chapter_range(self, range_str: str) -> int:
        """从章节范围字符串解析章数"""
        m = re.search(r"第?\s*(\d+)\s*[-–到]\s*第?\s*(\d+)\s*章?", str(range_str))
        if m:
            return int(m.group(2)) - int(m.group(1)) + 1
        m = re.search(r"第?\s*(\d+)\s*章?", str(range_str))
        if m:
            return 1
        return 0

    def _build_all_acts_prompt(
        self,
        core_setting: Dict[str, Any],
        overall_outline: Dict[str, Any],
        act_structure: List[Dict[str, Any]],
        num_acts: int,
    ) -> str:
        """构建一次性全部幕规划的Prompt（硬编码模板）"""

        # 硬编码的幕级规划模板
        template_str = """【任务】基于核心设定和整体大纲，生成全部{num_acts}幕的详细规划

【核心设定】
{core_setting}

【整体故事大纲】
{overall_story}

【幕结构信息】
{act_structure_info}

【规划规则】
{planning_rules}

【输出格式】
请按JSON格式输出全部{num_acts}幕的规划，确保各幕之间剧情连贯、节奏合理：

{{
  "幕规划": [
    {{
      "幕号": 1,
      "幕名": "第一幕名称",
      "章节范围": "第1-15章",
      "核心冲突": "本幕核心矛盾",
      "剧情概要": "本幕主要剧情发展",
      "爽点/爆点设计": ["设计点1", "设计点2"],
      "关键场景": ["场景1", "场景2", "场景3"],
      "情绪曲线": "起-承-转-合设计",
      "伏笔设置": ["伏笔1: 第X章回收"],
      "与下幕衔接": "如何自然过渡到下一幕"
    }}
  ]
}}

要求：
1. 严格遵循网文节奏设计原则
2. 确保各幕剧情连贯，无明显断层
3. 自然融入爽点/爆点设计，不刻意
4. 每个幕的章节范围要合理分配"""

        # 源材料
        core_setting_text = yaml.dump(core_setting, allow_unicode=True, default_flow_style=False)
        overall_story = self._build_overall_story_text(overall_outline)
        act_structure_text = self._format_act_structure(act_structure)

        # 规划规则
        planning_rules = self._build_planning_rules(core_setting, overall_outline)

        return template_str.format(
            num_acts=num_acts,
            core_setting=core_setting_text,
            overall_story=overall_story,
            act_structure_info=act_structure_text,
            planning_rules=planning_rules,
        )

    def _format_act_structure(self, act_structure: List[Dict[str, Any]]) -> str:
        """格式化幕结构信息为可读文本"""
        lines = []
        for i, act in enumerate(act_structure):
            chapter_range = act.get("章节范围", "")
            title = act.get("标题", "")
            overview = act.get("概述", "")
            lines.append(f"第{i + 1}幕「{act['name']}」")
            lines.append(f"  章节范围: {chapter_range}（共{act.get('章数', '?')}章）")
            if title:
                lines.append(f"  标题: {title}")
            if overview:
                lines.append(f"  概述: {overview}")
            plot_points = act.get("剧情要点", [])
            if plot_points:
                lines.append("  关键剧情节点:")
                for pt in plot_points:
                    lines.append(f"    - {pt}")
            lines.append("")
        return "\n".join(lines)

    def _build_overall_story_text(self, overall_outline: Dict[str, Any]) -> str:
        """构建整体故事文本（包含标题和概述）"""
        parts = []

        if "幕结构" in overall_outline:
            for key, value in overall_outline["幕结构"].items():
                if isinstance(value, dict):
                    chapter_range = value.get("章节范围", "")
                    title = value.get("标题", "")
                    overview = value.get("概述", "")
                    range_str = f"({chapter_range})" if chapter_range else ""
                    detail = f"{title} — {overview}" if title or overview else ""
                    parts.append(f"{key} {range_str}: {detail}")
                else:
                    parts.append(f"{key}: {value}")
        else:
            for key, value in overall_outline.items():
                parts.append(f"{key}: {value}")

        return "\n".join(parts)

    def _build_planning_rules(
        self, core_setting: Dict[str, Any], _overall_outline: Dict[str, Any]
    ) -> str:
        """构建规划规则文本（含爽点融入策略）"""
        protagonist = ""
        if isinstance(core_setting, dict):
            for key in ("主角", "主角设定", "protagonist"):
                val = core_setting.get(key, "")
                if isinstance(val, str) and val.strip():
                    protagonist = val
                    break
                elif isinstance(val, dict):
                    protagonist = val.get("姓名", val.get("名字", str(val)))
                    break

        parts = [
            "【爽点融入策略】",
            "请将以下爽点类型自然融入剧情发展：",
            "",
            "1. 身份反转型：底层/被轻视的身份在关键时刻展露实力，颠覆他人认知",
            "2. 实力跃升型：瓶颈突破、奇遇收获、境界提升，以战斗或能力展示验证成长",
            "3. 信息差揭露型：读者已知但剧中人不知的信息逐步揭示，造成戏剧性反转",
            "4. 情感共鸣型：亲情/友情/爱情在关键节点的爆发，让读者产生情感满足",
            "5. 地位提升型：获得认可、权力、地位的正向反馈",
            "",
            "融入要求：",
            "- 每个爽点必须由剧情自然推动产生，杜绝硬植入",
            "- 爽点前必有铺垫（压抑/悬念/积累），铺垫越长释放越爽",
            "- 爽点后必有代价或新挑战，避免\"爽完就空虚\"",
            "- 小爽点每5-8章一个，中爽点每幕2-3个，大爽点幕高潮处释放",
        ]

        if protagonist:
            parts.insert(2, f"主角定位：{protagonist}")

        return "\n".join(parts)

    def _call_ai_api(self, prompt: str) -> str:
        """调用AI API"""
        try:
            response = self.ai_role_manager.chat_completion(
                role=AIRole.GENERATOR,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的小说结构规划师，擅长设计幕级故事架构。输出必须严格遵循用户指定的JSON格式。",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            return response or ""
        except Exception as e:
            self.logger.error(f"AI API调用失败: {e}")
            raise RetryableGenerationError(f"AI API调用失败: {e}")

    def _parse_all_acts_response(self, response: str) -> Dict[str, Any]:
        """解析全部幕规划响应"""
        try:
            cleaned = self._clean_markdown_response(response)
            data = json.loads(cleaned)

            if isinstance(data, dict):
                if "幕规划" in data:
                    return data
                # 兼容驼峰命名的key
                for key in list(data.keys()):
                    if "幕" in key and isinstance(data[key], dict) and len(data[key]) > 1:
                        return {"幕规划": data}
                return {"幕规划": data}
            else:
                self.logger.warning("解析结果非字典，返回原始内容片段")
                return {"幕规划": {"原始响应": response[:800]}}
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON解析失败: {e}，尝试YAML解析")
            try:
                cleaned = self._clean_markdown_response(response)
                data = yaml.safe_load(cleaned)
                if isinstance(data, dict):
                    return {"幕规划": data}
            except Exception:
                pass
            return {"幕规划": {"原始响应": response[:800]}}
        except Exception as e:
            self.logger.warning(f"解析幕规划响应失败: {e}")
            return {"幕规划": {"原始响应": response[:800]}}

    def _clean_markdown_response(self, response: str) -> str:
        """清理Markdown格式的响应"""
        lines = response.split("\n")
        cleaned_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                continue
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)


class ChapterSkeletonGenerator:
    """章级骨架生成器 — 批次模式：一次API调用生成一批章，源材料只注入一次"""

    def __init__(
        self,
        config: Dict[str, Any],
        ai_role_manager: AIRoleManager,
        act_plan: Dict[str, Any],
        core_setting: Dict[str, Any] = None,
        overall_outline: Dict[str, Any] = None,
        existing_skeletons: Dict[str, Any] = None,
        context_window: int = 15,
    ):
        self.config = config
        self.ai_role_manager = ai_role_manager
        self.act_plan = act_plan
        self.core_setting = core_setting or {}
        self.overall_outline = overall_outline or {}
        self.existing_skeletons = existing_skeletons or {}
        self.context_window = context_window
        self.logger = logging.getLogger(__name__)

        # 预计算静态内容，用于缓存优化
        self._static_core_setting = yaml.dump(
            self.core_setting, allow_unicode=True, default_flow_style=False
        )
        self._static_overall_story = self._build_overall_story_text()

    def _build_static_context(self, act_data: Dict[str, Any]) -> str:
        """构建静态上下文（可缓存部分）"""
        act_info = yaml.dump(act_data, allow_unicode=True, default_flow_style=False)

        return f"""【核心设定】
{self._static_core_setting}

【整体故事框架】
{self._static_overall_story}

【当前幕规划】
{act_info}
"""

    def generate_chapter_skeletons(
        self, act_number: int, chapter_range: Tuple[int, int]
    ) -> Dict[str, Any]:
        """
        为指定幕生成一批章级骨架（单次API调用，解析失败时自动重试）。

        返回: Dict {章节号: 骨架内容}
        """
        start_ch, end_ch = chapter_range
        batch_count = end_ch - start_ch + 1
        self.logger.info(f"生成章级骨架批次: 第{start_ch}-{end_ch}章 ({batch_count}章)")

        act_data, _ = self._find_act_data(act_number)

        # 构建静态和动态prompt
        static_context = self._build_static_context(act_data)
        dynamic_prompt = self._build_dynamic_prompt(
            act_number, act_data, chapter_range
        )
        self.logger.debug(f"静态上下文长度: {len(static_context)} 字符, 动态Prompt长度: {len(dynamic_prompt)} 字符")

        # 重试循环：解析失败时最多重试2次
        max_retries = 2
        chapter_count = end_ch - start_ch + 1
        for attempt in range(max_retries + 1):
            # 启用JSON输出模式（DeepSeek原生支持）
            response = self._call_ai_api(
                static_context=static_context,
                dynamic_prompt=dynamic_prompt,
                json_output=True,
                chapter_count=chapter_count,
            )
            skeletons = self._parse_batch_skeleton_response(response, chapter_range)

            if skeletons:
                self.logger.info(f"章级骨架批次完成，共{len(skeletons)}章")
                return skeletons

            if attempt < max_retries:
                self.logger.warning(
                    f"批次第{start_ch}-{end_ch}章解析失败，第{attempt + 1}次重试..."
                )
                # 重试时在动态prompt末尾追加JSON格式强调
                if "—— 重要提醒" not in dynamic_prompt:
                    dynamic_prompt += (
                        f"\n\n—— 重要提醒（第{attempt + 1}次重试）——\n"
                        "上轮输出JSON格式有误导致解析失败。请务必：\n"
                        "1. 确保所有字符串值中的双引号已转义（\\\"）\n"
                        "2. 不要在字符串值内使用未转义的控制字符\n"
                        "3. 确保所有逗号、花括号、方括号配对正确\n"
                        "4. 严格遵循输出格式模板，不要遗漏任何字段"
                    )

        self.logger.error(f"批次第{start_ch}-{end_ch}章解析失败，已重试{max_retries}次，返回空结果")
        return {}

    def _find_act_data(self, act_number: int) -> Tuple[Dict[str, Any], str]:
        """根据幕序号在act_plan中找到对应的幕数据"""
        plan = self.act_plan.get("幕规划", {})
        keys = list(plan.keys())
        if act_number <= len(keys):
            return plan[keys[act_number - 1]], keys[act_number - 1]
        return plan.get(f"第{act_number}幕", {}), f"第{act_number}幕"

    def _parse_chapter_phases(
        self, chapter_divisions: List[str], chapter_range: Tuple[int, int]
    ) -> Dict[int, str]:
        """从章节划分列表中解析每章所属的阶段描述（支持范围和单章）"""
        phase_map: Dict[int, str] = {}
        for entry in chapter_divisions:
            desc = str(entry).strip()
            m = re.search(r"第?\s*(\d+)\s*[-–到]\s*第?\s*(\d+)\s*章?", desc)
            if m:
                phase_start = int(m.group(1))
                phase_end = int(m.group(2))
            else:
                m = re.search(r"第?\s*(\d+)\s*章", desc)
                if m:
                    phase_start = phase_end = int(m.group(1))
                else:
                    continue
            for ch in range(phase_start, phase_end + 1):
                if chapter_range[0] <= ch <= chapter_range[1]:
                    phase_map[ch] = desc
        return phase_map

    def _build_dynamic_prompt(
        self,
        act_number: int,
        act_data: Dict[str, Any],
        chapter_range: Tuple[int, int],
    ) -> str:
        """构建动态部分Prompt（每批不同的内容）"""
        start_ch, end_ch = chapter_range
        batch_count = end_ch - start_ch + 1

        # 前文大纲（动态内容）
        previous_skeletons = self._format_previous_skeletons(start_ch)

        # 批次阶段指引（动态内容）
        phase_map = self._parse_chapter_phases(act_data.get("章节划分", []), chapter_range)
        batch_phases = self._format_batch_phases(chapter_range, phase_map)

        # 构建动态prompt（只包含变化的部分）
        prompt = f"""【任务】一次性生成以下 {batch_count} 章的详细骨架（第{start_ch}-{end_ch}章）。

══════════════════════════════════════
—— 已生成大纲（前章上下文）——
══════════════════════════════════════

{previous_skeletons}

══════════════════════════════════════
—— 本章批次指引 ——
══════════════════════════════════════

{batch_phases}

══════════════════════════════════════
—— 骨架设计规则 ——
══════════════════════════════════════

1. 每章必须有独立的"起承转合"微结构，不能只是上一章的延续
2. 核心事件要写明因果逻辑（因为X，所以Y，导致Z）
3. 章节之间剧情自然递进，前章的结尾卡点导向后章的开场
4. 情绪曲线在整批章节内有起有伏，避免连续多章同质情绪
5. 伏笔埋设与回收要跨章协调：前几章埋的伏笔可在后几章回收

══════════════════════════════════════
—— 输出格式 ——
══════════════════════════════════════

请以 JSON 格式输出（务必使用双引号），为第{start_ch}-{end_ch}章的每一章生成完整骨架：
```json
{{
  "第N章": {{
    "标题": "章节标题",
    "字数目标": 2500,
    "章节定位": "本章在幕中的角色（幕首章/过渡铺垫/冲突升级/小高潮/缓冲章/幕尾高潮）",
    "核心事件": "2-3句描述核心情节，写明因果链",
    "与前章因果": "承接上章XX，推进YY，为下章ZZ埋笔",
    "人物行动": {{
      "主角": "主角行动与动机",
      "关键配角": "配角行动与主线关联"
    }},
    "场景概览": [
      "开场：XX地点 — 核心事件概述",
      "发展：XX地点 — 核心事件概述",
      "高潮：XX地点 — 核心事件概述",
      "收束：XX地点 — 核心事件概述"
    ],
    "情绪曲线": "本章情绪走向",
    "伏笔处理": {{
      "埋设": ["伏笔描述"],
      "回收": ["回收描述（标注前章编号）"]
    }},
    "结尾卡点": "章末悬念/钩子（具体描述）"
  }}
}}
```
重要：必须为第{start_ch}-{end_ch}章的每一章输出完整骨架，不得遗漏任何一章。章节之间剧情自然递进，伏笔跨章协调。
"""

        return prompt

    def _build_overall_story_text(self) -> str:
        """构建整体故事框架文本"""
        parts = []
        outline_data = self.overall_outline.get("幕结构", self.overall_outline)
        for key, value in outline_data.items():
            if isinstance(value, dict):
                chapter_range = value.get("章节范围", "")
                title = value.get("标题", "")
                overview = value.get("概述", "")
                range_str = f"({chapter_range})" if chapter_range else ""
                detail = f"{title} — {overview}" if title or overview else ""
                parts.append(f"{key} {range_str}: {detail}")
            else:
                parts.append(f"{key}: {value}")
        return "\n".join(parts)

    def _format_previous_skeletons(self, current_start: int) -> str:
        """构建前N章已生成大纲的紧凑摘要"""
        window = self.context_window
        prev_start = max(1, current_start - window)
        prev_chapters = []

        for ch in range(prev_start, current_start):
            key = f"第{ch}章"
            sk = self.existing_skeletons.get(key)
            if sk:
                title = sk.get("标题", "")
                core = sk.get("核心事件", "")
                ending = sk.get("结尾卡点", "")
                foreshadow = sk.get("伏笔处理", {})
                planted = foreshadow.get("埋设", []) if isinstance(foreshadow, dict) else []
                parts = [key]
                if title:
                    parts.append(f"《{title}》")
                if core:
                    parts.append(f"核心: {core}")
                if ending:
                    parts.append(f"结尾: {ending}")
                if planted:
                    parts.append(f"埋笔: {'; '.join(planted[:3])}")
                prev_chapters.append(" | ".join(parts))

        if prev_chapters:
            return "以下为已生成的前文大纲（按章序），请确保本批次剧情与上文衔接：\n" + "\n".join(prev_chapters)
        return "（本批次为首批章节，无前文大纲）"

    def _format_batch_phases(
        self, chapter_range: Tuple[int, int], phase_map: Dict[int, str]
    ) -> str:
        """格式化批次阶段指引"""
        start_ch, end_ch = chapter_range
        lines = []
        # Group consecutive chapters with the same phase
        i = start_ch
        while i <= end_ch:
            phase = phase_map.get(i, "（从上方幕规划的章节划分中推断本章剧情）")
            # Find how many consecutive chapters share this phase
            j = i
            while j + 1 <= end_ch and phase_map.get(j + 1) == phase:
                j += 1
            if i == j:
                lines.append(f"第{i}章 → {phase}")
            else:
                lines.append(f"第{i}-{j}章 → {phase}")
            i = j + 1

        return "\n".join(lines) if lines else "（参见幕规划章节划分）"

    def _call_ai_api(
        self,
        static_context: str,
        dynamic_prompt: str,
        json_output: bool = False,
        chapter_count: int = 1,
    ) -> str:
        """调用AI API，支持JSON输出模式。静态内容放入system message以利用缓存。"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": f"""你是一个专业的小说章节规划师，擅长设计章节骨架结构，确保章节间的因果链、情绪节奏和伏笔衔接到位。输出必须严格遵循用户指定的JSON格式。

══════════════════════════════════════
—— 源材料（所有批次共享）——
══════════════════════════════════════

{static_context}""",
                },
                {"role": "user", "content": dynamic_prompt},
            ]

            kwargs = {}
            if json_output:
                kwargs["response_format"] = {"type": "json_object"}
                self.logger.info("启用JSON输出模式")
                # JSON输出模式需要更多token，根据章节数动态计算
                # 每章大约需要 500-800 token 的JSON输出
                role_config = self.ai_role_manager.get_role_config(AIRole.GENERATOR)
                configured_max = role_config.max_tokens
                estimated_tokens = min(configured_max, max(8000, chapter_count * 800))
                kwargs["max_tokens"] = estimated_tokens
                self.logger.info(f"设置最大token数: {estimated_tokens} (章节数: {chapter_count}, 配置上限: {configured_max})")

            response = self.ai_role_manager.chat_completion(
                role=AIRole.GENERATOR,
                messages=messages,
                **kwargs,
            )
            return response or ""
        except Exception as e:
            self.logger.error(f"AI API调用失败: {e}")
            raise RetryableGenerationError(f"AI API调用失败: {e}")

    def _parse_batch_skeleton_response(
        self, response: str, chapter_range: Tuple[int, int]
    ) -> Dict[str, Any]:
        """解析批次章骨架响应"""
        start_ch, end_ch = chapter_range
        try:
            cleaned = self._clean_markdown_response(response)
            data = json.loads(cleaned)

            if not isinstance(data, dict):
                raise ValueError("响应不是JSON对象")

            # Filter and validate chapters
            skeletons = {}
            for ch in range(start_ch, end_ch + 1):
                key = f"第{ch}章"
                if key in data:
                    skeletons[key] = data[key]

            if not skeletons:
                # Maybe the response is a list: try numeric keys or re-index
                for key, value in data.items():
                    if "第" in key and "章" in key:
                        skeletons[key] = value
                if not skeletons:
                    self.logger.warning(f"未解析到章节骨架，响应前500字符: {response[:500]}")
                    return {}

            self.logger.info(f"解析到 {len(skeletons)} 章骨架")
            return skeletons

        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON解析失败: {e}，尝试YAML解析")
            try:
                cleaned = self._clean_markdown_response(response)
                data = yaml.safe_load(cleaned)
                if isinstance(data, dict):
                    skeletons = {}
                    for ch in range(start_ch, end_ch + 1):
                        key = f"第{ch}章"
                        if key in data:
                            skeletons[key] = data[key]
                    return skeletons
            except Exception:
                pass
            self.logger.error(f"批次解析失败，响应前800字符: {response[:800]}")
            return {}
        except Exception as e:
            self.logger.warning(f"解析批次响应失败: {e}")
            return {}

    def _clean_markdown_response(self, response: str) -> str:
        """清理Markdown格式的响应并修复常见JSON问题"""
        # 移除markdown代码块标记
        lines = response.split("\n")
        cleaned_lines = []
        for line in lines:
            if line.strip().startswith("```"):
                continue
            cleaned_lines.append(line)
        result = "\n".join(cleaned_lines)

        # 修复JSON字符串内未转义的控制字符（\x00-\x1f 除了 \n）
        # AI有时在字符串值中输出字面换行/制表符等，导致json.loads失败
        in_string = False
        escaped = False
        chars = list(result)
        for i, ch in enumerate(chars):
            if escaped:
                escaped = False
                continue
            if ch == '\\':
                escaped = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string and ord(ch) < 0x20 and ch not in ('\n',):
                chars[i] = ch = ' '
        return ''.join(chars)


class OutlineGenerator:
    """大纲生成器（两阶段：幕规划 → 章骨架，骨架直接驱动扩写）"""

    def __init__(
        self, config: Dict[str, Any], multi_model_client: MultiModelClient = None, output_dir: Optional[Path] = None
    ):
        self.config = config
        self.settings = Settings(config)
        self.logger = logging.getLogger(__name__)
        if multi_model_client:
            self.multi_model_client = multi_model_client
        else:
            self.multi_model_client = MultiModelClient(config)

        self.ai_role_manager = AIRoleManager(config, self.multi_model_client)

        if output_dir:
            self.output_dir = output_dir
        else:
            # 默认使用当前目录（调用者应传入正确路径）
            self.output_dir = Path(".")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.act_plan_file = self.output_dir / "act_plan.json"
        self.outline_file = self.output_dir / "outline.json"
        # skeletons_file 与 outline_file 统一，不再生成两个文件
        self.skeletons_file = self.outline_file

    def _load_existing_act_plan(self) -> Optional[Dict[str, Any]]:
        """加载已存在的幕规划"""
        if self.act_plan_file.exists():
            try:
                with open(self.act_plan_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"加载幕规划文件失败: {e}")
        return None

    def _save_act_plan(self, act_plan: Dict[str, Any]) -> bool:
        """保存幕规划"""
        try:
            with open(self.act_plan_file, "w", encoding="utf-8") as f:
                json.dump(act_plan, f, ensure_ascii=False, indent=2)
            self.logger.info(f"幕规划已保存: {self.act_plan_file}")
            return True
        except Exception as e:
            self.logger.error(f"保存幕规划失败: {e}")
            return False

    def _load_existing_skeletons(self) -> Dict[str, Any]:
        """加载已存在的大纲"""
        if self.skeletons_file.exists():
            try:
                with open(self.skeletons_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"加载骨架文件失败: {e}")
        return {}

    def _save_skeletons(self, skeletons: Dict[str, Any]) -> bool:
        """保存章级骨架"""
        try:
            with open(self.skeletons_file, "w", encoding="utf-8") as f:
                json.dump(skeletons, f, ensure_ascii=False, indent=2)
            self.logger.info(f"大纲已保存: {self.skeletons_file}")
            return True
        except Exception as e:
            self.logger.error(f"保存骨架失败: {e}")
            return False

    def _get_first_missing_chapter(self, existing: Dict[str, Any], start: int, end: int) -> int:
        """获取第一个缺失的章节号"""
        for ch in range(start, end + 1):
            if f"第{ch}章" not in existing:
                return ch
        return end + 1

    def generate_outline_v2(
        self,
        core_setting: Dict[str, Any],
        overall_outline: Dict[str, Any],
        num_acts: int = 0,
        chapter_range: Optional[Tuple[int, int]] = None,
        batch_size: int = None,
    ) -> Dict[str, Any]:
        """
        两阶段大纲生成（幕规划 → 章骨架），骨架直接驱动扩写。

        流程:
        1. Stage 1: 幕级规划（可复用，已存在则跳过）
        2. Stage 2: 章级骨架（增量，跳过已生成）

        返回: Dict 章级骨架（即最终大纲）
        """
        self.logger.info("开始两阶段大纲生成（支持增量）")

        total_chapters = self.extract_total_chapters(overall_outline)
        if num_acts <= 0:
            num_acts = self.extract_num_acts(overall_outline)
        if chapter_range is None:
            chapter_range = (1, total_chapters)

        start_ch, end_ch = chapter_range

        # Stage 1: 幕级规划（检查复用）
        self.logger.info("Stage 1: 幕级规划")
        act_plan = self._load_existing_act_plan()
        if act_plan:
            self.logger.info("幕规划已存在，复用")
        else:
            act_planner = ActLevelPlanner(self.config, self.ai_role_manager)
            act_plan = act_planner.generate_act_plan(
                core_setting, overall_outline, num_acts, total_chapters
            )
            self._save_act_plan(act_plan)
            self.logger.info("幕规划生成完成")

        # Stage 2: 章级骨架（增量生成，批次模式）
        self.logger.info("Stage 2: 章级骨架生成（批次增量）")
        existing_skeletons = self._load_existing_skeletons()

        gen_config = self.config.get("generation", {})
        # 使用传入的 batch_size 或从配置读取
        batch_size = batch_size or gen_config.get("skeleton_batch_size", 10)
        context_window = gen_config.get("skeleton_context_window", 15)

        skeleton_generator = ChapterSkeletonGenerator(
            self.config, self.ai_role_manager, act_plan,
            core_setting=core_setting,
            overall_outline=overall_outline,
            existing_skeletons=existing_skeletons,
            context_window=context_window,
        )

        first_missing = self._get_first_missing_chapter(existing_skeletons, start_ch, end_ch)
        if first_missing > end_ch:
            self.logger.info(f"章级骨架已完整，范围 {start_ch}-{end_ch} 全部存在")
        else:
            self.logger.info(f"从第 {first_missing} 章开始生成骨架（批次大小={batch_size}, 上下文窗口={context_window}）")

            chapters_per_act = total_chapters // num_acts

            for act_num in range(1, num_acts + 1):
                act_start = (act_num - 1) * chapters_per_act + 1
                act_end = min(act_num * chapters_per_act, total_chapters)

                if act_start > end_ch or act_end < first_missing:
                    continue

                actual_start = max(act_start, first_missing)
                actual_end = min(act_end, end_ch)

                # 批次循环：每次生成 batch_size 章
                for batch_start in range(actual_start, actual_end + 1, batch_size):
                    batch_end = min(batch_start + batch_size - 1, actual_end)

                    all_exist = all(
                        f"第{ch}章" in existing_skeletons
                        for ch in range(batch_start, batch_end + 1)
                    )
                    if all_exist:
                        self.logger.info(f"第 {batch_start}-{batch_end} 章骨架已存在，跳过")
                        continue

                    self.logger.info(f"生成批次: 第{batch_start}-{batch_end}章")
                    skeletons = skeleton_generator.generate_chapter_skeletons(
                        act_num, (batch_start, batch_end)
                    )
                    existing_skeletons.update(skeletons)
                    # 更新 generator 中的引用，使后续批次的上下文包含本章批次
                    skeleton_generator.existing_skeletons = existing_skeletons
                    self._save_skeletons(existing_skeletons)
                    self.logger.info(f"第 {batch_start}-{batch_end} 章骨架已保存")

        self.logger.info(f"两阶段大纲生成完成，共{len(existing_skeletons)}章")
        return existing_skeletons

    def _extract_chapter_number(self, chapter_key: str) -> int:
        """从章节键提取章节号"""
        matched = re.search(r"(\d+)", str(chapter_key))
        if matched:
            return int(matched.group(1))
        return 0

    # ==================== 保留原有方法（向后兼容） ====================

    def generate_outline(
        self,
        core_setting: Dict[str, Any],
        overall_outline: Dict[str, Any],
        chapter_range: tuple = (1, 10),
    ) -> Dict[str, Any]:
        """
        生成章节大纲（旧版，保留向后兼容）

        Args:
            core_setting: 核心设定
            overall_outline: 整体大纲
            chapter_range: 章节范围

        Returns:
            Dict[str, Any]: 生成的章节大纲
        """
        try:
            self.logger.info(f"开始生成章节大纲，范围: {chapter_range}")

            # 构建提示词
            prompt = self._build_outline_prompt(
                core_setting, overall_outline, chapter_range
            )

            # 调用AI API
            response = self._call_ai_api(prompt)

            # 解析响应
            outline = self._parse_response(response)

            # 验证大纲
            self._validate_outline(outline)

            self.logger.info(f"章节大纲生成成功，共{len(outline)}章")
            return outline

        except Exception as e:
            self.logger.error(f"生成章节大纲失败: {e}")
            raise

    def _build_outline_prompt(
        self,
        core_setting: Dict[str, Any],
        overall_outline: Dict[str, Any],
        chapter_range: tuple,
    ) -> str:
        prompt = f"""
请根据以下信息生成详细的章节大纲：

【核心设定】
世界观：{core_setting.get("世界观", "")}
核心冲突：{core_setting.get("核心冲突", "")}
主要人物：{self._format_characters(core_setting.get("人物小传", {}))}

【整体大纲】
{self._build_acts_text(overall_outline)}

关键转折点：{overall_outline.get("关键转折点", "")}

【生成要求】
请生成第{chapter_range[0]}-{chapter_range[1]}章的详细大纲。

【输出格式】
必须严格按以下YAML格式输出，不要添加任何额外说明文字：

第1章:
  标题: 章节标题
  核心事件: 本章关键情节
  场景: 地点和环境
  人物行动: 角色的主要行为
  伏笔回收: 无
  字数目标: 1500

第2章:
  标题: 章节标题
  核心事件: 本章关键情节
  场景: 地点和环境
  人物行动: 角色的主要行为
  伏笔回收: 无
  字数目标: 1500

...（依此类推）
"""
        return prompt.strip()

    def _format_characters(self, characters: Dict[str, Any]) -> str:
        result = []
        for name, info in characters.items():
            if isinstance(info, dict):
                info_parts = []
                for k, v in info.items():
                    if isinstance(v, str) and len(v) > 100:
                        v = v[:100] + "..."
                    info_parts.append(f"{k}: {v}")
                info_str = ", ".join(info_parts[:3])
                result.append(f"{name}({info_str})")
            else:
                result.append(f"{name}: {info}")
        return "; ".join(result[:5])

    def _build_acts_text(self, overall_outline: Dict[str, Any]) -> str:
        acts_content = []
        act_number = 1

        chinese_numbers = [
            "一",
            "二",
            "三",
            "四",
            "五",
            "六",
            "七",
            "八",
            "九",
            "十",
            "十一",
            "十二",
            "十三",
            "十四",
            "十五",
            "十六",
            "十七",
            "十八",
            "十九",
            "二十",
        ]

        # 处理嵌套的"幕结构"层级
        outline_data = overall_outline
        if "幕结构" in overall_outline:
            outline_data = overall_outline["幕结构"]

        while True:
            act_key_numeric = f"第{act_number}幕"
            act_key_chinese = (
                f"第{chinese_numbers[act_number - 1]}幕"
                if act_number <= len(chinese_numbers)
                else ""
            )
            act_content = outline_data.get(act_key_numeric, "") or outline_data.get(
                act_key_chinese, ""
            )

            if act_content:
                display_key = (
                    act_key_numeric
                    if outline_data.get(act_key_numeric)
                    else act_key_chinese
                )

                if isinstance(act_content, dict):
                    chapter_range = act_content.get("章节范围", "")
                    # 优先使用"剧情逻辑脉络"，兼容"核心剧情"
                    plot_content = act_content.get(
                        "剧情逻辑脉络", ""
                    ) or act_content.get("核心剧情", "")

                    # 处理列表形式的剧情逻辑脉络
                    if isinstance(plot_content, list):
                        plot_text = "\n".join(f"  - {item}" for item in plot_content)
                    else:
                        plot_text = str(plot_content)

                    act_text = f"{display_key}（{chapter_range}）\n{plot_text}"
                else:
                    act_text = f"{display_key}：{act_content}"

                acts_content.append(act_text)
                act_number += 1
            else:
                break

        return "\n\n".join(acts_content)

    def extract_num_acts(self, overall_outline: Dict[str, Any]) -> int:
        """从整体大纲中提取幕的数量"""
        outline_data = overall_outline
        if "幕结构" in overall_outline:
            outline_data = overall_outline["幕结构"]

        count = 0
        for key in outline_data:
            if isinstance(outline_data[key], dict) and key.startswith("第"):
                count += 1
        if count > 0:
            return count
        # fallback: 检查顶层
        for key in overall_outline:
            if isinstance(overall_outline[key], dict) and key.startswith("第"):
                count += 1
        return count if count > 0 else 3

    def extract_total_chapters(self, overall_outline: Dict[str, Any]) -> int:
        try:
            # 优先读取顶层"总章节数"字段
            if "总章节数" in overall_outline:
                total = int(overall_outline["总章节数"])
                self.logger.info(f"从总章节数字段提取到总章节数量: {total}")
                return total

            total_chapters = 0

            outline_data = overall_outline
            if "幕结构" in overall_outline:
                outline_data = overall_outline["幕结构"]

            chapter_patterns = [
                r"第\s*(\d+)\s*-\s*(\d+)\s*章",
                r"第\s*(\d+)\s*章\s*到\s*第\s*(\d+)\s*章",
                r"(\d+)\s*-\s*(\d+)\s*章",
                r"第\s*(\d+)\s*章",
            ]

            for key, act_content in outline_data.items():
                if not isinstance(act_content, dict):
                    continue
                chapter_range = act_content.get("章节范围", "")
                search_text = str(chapter_range)

                for pattern in chapter_patterns:
                    matches = re.findall(pattern, search_text)
                    for match in matches:
                        if len(match) == 2:
                            end_chapter = int(match[1])
                            total_chapters = max(total_chapters, end_chapter)
                        else:
                            chapter_num = int(match[0])
                            total_chapters = max(total_chapters, chapter_num)

            if total_chapters == 0:
                self.logger.warning("无法从整体大纲中提取章节数量，使用默认值150")
                return 150

            self.logger.info(f"从幕结构中提取到总章节数量: {total_chapters}")
            return total_chapters

        except Exception as e:
            self.logger.error(f"提取章节数量失败: {e}")
            return 150

    def _call_ai_api(self, prompt: str) -> str:
        """调用AI API生成大纲"""
        try:
            self.logger.info("正在调用AI API生成章节大纲...")

            response = self.ai_role_manager.chat_completion(
                role=AIRole.GENERATOR,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的小说大纲策划师，擅长创作引人入胜的故事情节。",
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            if not response:
                raise RetryableGenerationError("AI API返回空响应，可重试")

            self.logger.info("AI API调用成功")
            return response

        except RetryableGenerationError:
            raise
        except Exception as e:
            self.logger.error(f"AI API调用失败: {e}")
            raise RetryableGenerationError(f"AI API调用失败，可重试: {e}") from e

    def _get_mock_response(self) -> str:
        """获取模拟响应（用于测试）"""
        return """
第1章:
  标题: "开篇"
  核心事件: "主角登场，介绍背景和世界观"
  场景: "主角所在地点，如山村、书院等"
  人物行动: "主角的日常活动，展现性格特点"
  伏笔回收: ""
  字数目标: 1500

第2章:
  标题: "变故"
  核心事件: "发生重要事件，改变主角生活轨迹"
  场景: "事件发生地点，如家中、野外等"
  人物行动: "主角应对变故的行动"
  伏笔回收: ""
  字数目标: 1500
"""

    def _parse_response(self, response: str) -> Dict[str, Any]:
        try:
            cleaned_response = self._clean_markdown_response(response)

            self.logger.debug(f"清理后的响应前500字符: {cleaned_response[:500]}")

            outline = yaml.safe_load(cleaned_response)

            if isinstance(outline, str):
                self.logger.warning("YAML解析返回字符串，尝试简单文本解析")
                result = self._simple_parse(cleaned_response)
                if result:
                    return result
                self.logger.error(
                    f"简单解析也失败，响应内容: {cleaned_response[:1000]}"
                )
                return {}

            if isinstance(outline, dict):
                if not outline:
                    self.logger.warning("YAML解析返回空字典，尝试简单文本解析")
                    return self._simple_parse(cleaned_response)
                return outline

            self.logger.warning(f"YAML解析返回非预期类型: {type(outline)}")
            return self._simple_parse(cleaned_response)

        except yaml.YAMLError as e:
            self.logger.error(f"YAML解析错误: {e}")
            return self._simple_parse(response)
        except Exception as e:
            self.logger.error(f"解析AI响应失败: {e}")
            return self._simple_parse(response)

    def _clean_markdown_response(self, response: str) -> str:
        """清理Markdown格式的响应"""
        # 移除markdown代码块标记
        lines = response.split("\n")
        cleaned_lines = []

        for line in lines:
            stripped = line.strip()
            # 跳过代码块开始和结束标记（```json, ```yaml, ```, etc.）
            if stripped.startswith("```"):
                continue
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def _simple_parse(self, response: str) -> Dict[str, Any]:
        outline = {}
        lines = response.strip().split("\n")
        current_chapter = None

        for line in lines:
            stripped = line.strip()

            chapter_match = re.match(r"^第\s*(\d+)\s*章\s*[:：]?\s*(.*)$", stripped)
            if chapter_match:
                chapter_num = chapter_match.group(1)
                current_chapter = f"第{chapter_num}章"
                outline[current_chapter] = {
                    "标题": chapter_match.group(2).strip()
                    if chapter_match.group(2)
                    else f"第{chapter_num}章",
                    "核心事件": "",
                    "场景": "",
                    "人物行动": "",
                    "伏笔回收": "",
                    "字数目标": 1500,
                }
                continue

            if current_chapter and stripped:
                if stripped.startswith("- "):
                    stripped = stripped[2:]

                field_match = re.match(
                    r"^(标题|核心事件|场景|人物行动|伏笔回收|字数目标|目标字数|字数)[:：]\s*(.*)$",
                    stripped,
                )
                if field_match:
                    field_name = field_match.group(1)
                    field_value = field_match.group(2).strip()

                    if field_name in ["目标字数", "字数"]:
                        field_name = "字数目标"
                        num_match = re.search(r"\d+", str(field_value))
                        if num_match:
                            field_value = int(num_match.group())
                        else:
                            field_value = 1500

                    outline[current_chapter][field_name] = field_value

        if not outline:
            self.logger.warning(
                f"简单解析未能提取任何章节，原始响应前500字符: {response[:500]}"
            )

        return outline

    def _validate_outline(self, outline: Dict[str, Any]):
        """验证大纲格式"""
        required_fields = [
            "标题",
            "核心事件",
            "场景",
            "人物行动",
            "伏笔回收",
            "字数目标",
        ]

        for chapter, content in outline.items():
            if not isinstance(content, dict):
                raise ValueError(f"章节 {chapter} 内容格式错误")

            for field in required_fields:
                # 检查字段是否存在
                if field not in content:
                    # 检查字段变体
                    if field == "字数目标":
                        # 检查可能的变体
                        if "字数目标" in content:
                            content["字数目标"] = content.pop("字数目标")
                        elif "目标字数" in content:
                            content["字数目标"] = content.pop("目标字数")
                        elif "字数" in content:
                            content["字数目标"] = content.pop("字数")
                        else:
                            # 如果没有找到任何变体，设置默认值
                            content["字数目标"] = "1500字左右"
                    elif field == "伏笔回收":
                        # 伏笔回收可以是可选的，如果没有则设置为"无"
                        if "伏笔回收" not in content:
                            content["伏笔回收"] = "无"
                    else:
                        # 检查是否有相似的字段
                        similar_fields = [
                            k for k in content.keys() if field in k or k in field
                        ]
                        if similar_fields:
                            # 使用相似字段
                            content[field] = content.pop(similar_fields[0])
                        else:
                            # 如果没有找到相似字段，设置默认值
                            if field == "标题":
                                content["标题"] = "未命名章节"
                            elif field == "核心事件":
                                content["核心事件"] = "待定"
                            elif field == "场景":
                                content["场景"] = "待定"
                            elif field == "人物行动":
                                content["人物行动"] = "待定"

    def save_outline(
        self, outline: Dict[str, Any], output_path: str, backup: bool = True
    ) -> str:
        """
        保存大纲文件

        Args:
            outline: 大纲内容
            output_path: 输出路径
            backup: 是否备份

        Returns:
            str: 实际保存路径
        """
        try:
            core_setting = self._load_core_setting()
            self._validate_outline(outline)
            outline = self.optimize_outline(outline, core_setting)
            outline = self._check_foreshadowing_consistency(outline, core_setting)
            outline = self._check_pacing(outline)

            output_file = Path(output_path)

            # 备份现有文件
            if backup and output_file.exists():
                backup_path = self._backup_file(output_file)
                self.logger.info(f"备份现有大纲文件: {backup_path}")

            # 保存新文件
            with open(output_file, "w", encoding="utf-8") as f:
                yaml.dump(outline, f, default_flow_style=False, allow_unicode=True)

            self.logger.info(f"大纲文件保存成功: {output_file}")
            return str(output_file)

        except Exception as e:
            self.logger.error(f"保存大纲文件失败: {e}")
            raise

    def _backup_file(self, file_path: Path) -> str:
        """
        备份文件
        注意：此方法保留是为了兼容性，但不再创建 outline_history 目录
        如果需要备份功能，建议使用版本控制系统
        """
        # 功能已禁用，直接返回空路径
        return ""

    def load_outline(self, file_path: str) -> Dict[str, Any]:
        """
        加载大纲文件

        Args:
            file_path: 文件路径

        Returns:
            Dict[str, Any]: 大纲内容
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                outline = yaml.safe_load(f)

            self.logger.info(f"大纲文件加载成功: {file_path}")
            return outline

        except Exception as e:
            self.logger.error(f"加载大纲文件失败: {e}")
            raise

    def optimize_outline(
        self, outline: Dict[str, Any], core_setting: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        优化大纲
        """
        try:
            self.logger.info("开始优化大纲...")

            fixed_count = 0
            for chapter, content in outline.items():
                # 1. 确保核心字段存在
                if "核心事件" not in content or not content["核心事件"]:
                    content["核心事件"] = "待补充核心事件"
                    fixed_count += 1

                # 2. 规范化字数目标
                if "字数目标" not in content:
                    content["字数目标"] = "2000字"
                    fixed_count += 1

                # 3. 确保伏笔回收字段
                if "伏笔回收" not in content:
                    content["伏笔回收"] = "无"
                    fixed_count += 1

                # 4. 确保标题存在
                if "标题" not in content:
                    content["标题"] = f"未命名{chapter}"
                    fixed_count += 1

            if fixed_count > 0:
                self.logger.info(f"自动修复了大纲中的 {fixed_count} 处格式问题")

            # 检查人物一致性
            outline = self._check_character_consistency(outline, core_setting)

            self.logger.info("大纲优化完成")
            return outline

        except Exception as e:
            self.logger.error(f"大纲优化失败: {e}")
            return outline

    def _check_character_consistency(
        self, outline: Dict[str, Any], core_setting: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检查人物一致性"""
        characters = core_setting.get("人物小传", {})
        known_names = [
            str(name).strip() for name in characters.keys() if str(name).strip()
        ]

        for chapter, content in outline.items():
            chapter_text = " ".join(
                [
                    str(content.get("核心事件", "")),
                    str(content.get("人物行动", "")),
                    str(content.get("伏笔回收", "")),
                ]
            )
            if not known_names:
                continue

            mentioned = [name for name in known_names if name in chapter_text]
            if not mentioned:
                content["一致性提示"] = "未检测到核心人物，建议补充人物行为与动机"
            elif len(mentioned) > 4:
                content["一致性提示"] = (
                    f"出场人物较多({len(mentioned)}位)，注意控制叙事焦点"
                )

        return outline

    def _check_foreshadowing_consistency(
        self, outline: Dict[str, Any], core_setting: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检查伏笔连贯性"""
        foreshadowing_plan = core_setting.get("伏笔清单", [])
        planned_keywords: List[str] = []
        if isinstance(foreshadowing_plan, list):
            for item in foreshadowing_plan:
                text = str(item).strip()
                if text:
                    planned_keywords.append(text[:18])

        seen: Dict[str, int] = {}
        for _, content in outline.items():
            raw_value = str(content.get("伏笔回收", "")).strip()
            if not raw_value or raw_value == "无":
                continue
            tokens = [
                token.strip()
                for token in re.split(r"[,，；;、]", raw_value)
                if token.strip()
            ]
            normalized_tokens = []
            for token in tokens:
                if len(token) > 18:
                    normalized_tokens.append(token[:18])
                else:
                    normalized_tokens.append(token)
            for token in normalized_tokens:
                seen[token] = seen.get(token, 0) + 1
            duplicate = [token for token in normalized_tokens if seen.get(token, 0) > 2]
            if duplicate:
                content["伏笔提示"] = (
                    f"伏笔项重复回收偏多: {', '.join(sorted(set(duplicate))[:3])}"
                )
            if planned_keywords:
                hit = any(plan in raw_value for plan in planned_keywords)
                if not hit and "伏笔提示" not in content:
                    content["伏笔提示"] = "当前伏笔回收与设定清单关联较弱"

        return outline

    def _check_pacing(self, outline: Dict[str, Any]) -> Dict[str, Any]:
        """检查节奏合理性"""
        ordered_chapters = sorted(
            outline.items(), key=lambda item: self._extract_chapter_number(item[0])
        )
        previous_target = None
        for _, content in ordered_chapters:
            current_target = self._extract_target_word_count(
                content.get("字数目标", 1500)
            )
            if previous_target and previous_target > 0:
                ratio = current_target / previous_target
                if ratio >= 1.8:
                    content["节奏提示"] = (
                        f"字数目标增幅较大({previous_target}->{current_target})"
                    )
                elif ratio <= 0.55:
                    content["节奏提示"] = (
                        f"字数目标降幅较大({previous_target}->{current_target})"
                    )
            previous_target = current_target

        return outline

    def _extract_target_word_count(self, raw_value: Any) -> int:
        if isinstance(raw_value, int):
            return raw_value
        matched = re.search(r"(\d+)", str(raw_value))
        if matched:
            return int(matched.group(1))
        return 1500

    def _load_core_setting(self) -> Dict[str, Any]:
        try:
            core_setting_path = Path(self.settings.path_config.core_setting_file)
            with open(core_setting_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}
