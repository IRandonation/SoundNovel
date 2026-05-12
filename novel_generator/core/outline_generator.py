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
from datetime import datetime

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

        # 硬编码的幕级规划模板（精简版，不含章节划分）
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
请按JSON格式输出全部{num_acts}幕的规划（不需要输出"章节划分"字段，该内容将在后续"章节梗概"阶段生成）：

{{
  "幕规划": {{
    "<使用上方【幕结构信息】中的幕名>": {{
      "主题": "幕主题",
      "目标": "幕目标",
      "核心冲突": "核心冲突描述",
      "情感基调": "情感基调",
      "预估章数": <该幕实际章数>,
      "关键转折点": ["第X章：转折事件描述", ...]
    }}
  }}
}}

要求：
1. 严格遵循网文节奏设计原则
2. 确保各幕剧情连贯，无明显断层
3. 自然融入爽点/爆点设计，不刻意
4. 关键转折点需标注具体章节号"""

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


class ChapterSummaryGenerator:
    """章节梗概生成器 — 按幕批次生成，单次API调用生成一批章的梗概"""

    # 默认配置常量
    DEFAULT_BATCH_SIZE = 50  # 从150降低到50，减少单次失败风险
    DEFAULT_MAX_RETRIES = 5  # 增加重试次数
    FALLBACK_SIZES = [50, 10, 1]  # 降级梯度
    MIN_ACCEPTABLE_RATIO = 0.95  # 从0.8提高到0.95，更严格的完整性要求

    def __init__(
        self,
        config: Dict[str, Any],
        ai_role_manager: AIRoleManager,
        act_plan: Dict[str, Any],
        core_setting: Dict[str, Any] = None,
        overall_outline: Dict[str, Any] = None,
        existing_summaries: Dict[str, Any] = None,
        batch_size: int = None,  # 改为None，使用类常量默认值
    ):
        self.config = config
        self.ai_role_manager = ai_role_manager
        self.act_plan = act_plan
        self.core_setting = core_setting or {}
        self.overall_outline = overall_outline or {}
        self.existing_summaries = existing_summaries or {}

        # 从配置或类常量获取批次大小
        gen_config = config.get("generation", {}).get("outline", {})
        self.batch_size = batch_size or gen_config.get("batch_size", self.DEFAULT_BATCH_SIZE)
        self.max_retries = gen_config.get("max_retries", self.DEFAULT_MAX_RETRIES)
        self.fallback_sizes = gen_config.get("fallback_sizes", self.FALLBACK_SIZES)
        self.min_acceptable_ratio = self.MIN_ACCEPTABLE_RATIO

        self.logger = logging.getLogger(__name__)

    def generate_summaries_for_act(
        self,
        act_number: int,
        chapter_range: Tuple[int, int],
    ) -> Dict[str, Any]:
        """为指定幕生成章节梗概，包含重试和降级机制

        改进点：
        - 使用配置的重试次数和降级梯度
        - 更严格的完整性要求（95%而非80%）
        - 缺失章节自动补充生成
        """
        start_ch, end_ch = chapter_range
        act_data, act_name = self._find_act_data(act_number)

        all_summaries = {}

        # 拆分批次（每批不超过 batch_size 章）
        for batch_start in range(start_ch, end_ch + 1, self.batch_size):
            batch_end = min(batch_start + self.batch_size - 1, end_ch)

            self.logger.info(f"生成章节梗概批次: 第{batch_start}-{batch_end}章")

            # 使用降级梯度进行重试
            batch_summaries = self._generate_with_fallback(
                act_number, act_data, act_name, batch_start, batch_end
            )

            # 更新结果
            if batch_summaries:
                all_summaries.update(batch_summaries)
                self.existing_summaries.update(batch_summaries)

                # 验证完整性
                missing = self._check_missing_chapters(batch_summaries, batch_start, batch_end)
                if missing:
                    self.logger.warning(f"批次缺少{len(missing)}章: {missing[:10]}...")
                    # 补充缺失章节（单章生成）
                    for ch in missing:
                        single_summary = self._generate_single_summary(
                            act_number, act_data, act_name, ch
                        )
                        if single_summary:
                            all_summaries[f"第{ch}章"] = single_summary
                            self.existing_summaries[f"第{ch}章"] = single_summary
                            self.logger.info(f"补充缺失章节: 第{ch}章")

                self.logger.info(f"梗概批次完成: 第{batch_start}-{batch_end}章")
            else:
                self.logger.error(f"批次第{batch_start}-{batch_end}章所有降级尝试失败")

        return all_summaries

    def _generate_with_fallback(
        self,
        act_number: int,
        act_data: Dict[str, Any],
        act_name: str,
        batch_start: int,
        batch_end: int,
    ) -> Dict[str, Any]:
        """带降级梯度的批次生成"""
        batch_count = batch_end - batch_start + 1

        for size in self.fallback_sizes:
            if batch_count < size:
                continue

            self.logger.info(f"尝试批次大小={size}章")

            # 按当前批次大小分批
            all_results = {}
            has_failure = False  # 标记是否有子批次失败

            for sub_start in range(batch_start, batch_end + 1, size):
                sub_end = min(sub_start + size - 1, batch_end)
                sub_count = sub_end - sub_start + 1

                # 尝试生成
                sub_success = False
                for retry in range(self.max_retries):
                    try:
                        prompt = self._build_batch_prompt(
                            act_number, act_data, act_name, (sub_start, sub_end)
                        )
                        self.logger.debug(f"梗概 Prompt 长度: {len(prompt)} 字符")
                        response = self._call_ai_api(prompt, sub_count)
                        summaries = self._parse_response(response, (sub_start, sub_end))

                        # 严格完整性检查
                        expected = sub_count
                        actual = len(summaries)

                        if actual >= expected * self.min_acceptable_ratio:
                            all_results.update(summaries)
                            self.logger.info(f"批次成功: 第{sub_start}-{sub_end}章 ({actual}/{expected})")
                            sub_success = True
                            break  # 成功，跳出重试循环
                        else:
                            self.logger.warning(
                                f"批次不完整: 第{sub_start}-{sub_end}章 ({actual}/{expected}), "
                                f"低于阈值{self.min_acceptable_ratio}"
                            )
                            if retry < self.max_retries - 1:
                                self.logger.info(f"重试 #{retry + 1}")

                    except RetryableGenerationError as e:
                        self.logger.warning(f"API调用异常: {e}")
                        if retry < self.max_retries - 1:
                            self.logger.info(f"重试 #{retry + 1}")

                # 如果该子批次失败，标记并考虑降级
                if not sub_success:
                    self.logger.warning(f"子批次第{sub_start}-{sub_end}章失败")
                    has_failure = True
                    # 可以选择继续尝试剩余子批次，或者直接降级
                    # 这里选择直接降级，避免浪费时间
                    break

            # 完成所有子批次后，检查是否完整
            total_expected = batch_end - batch_start + 1
            if len(all_results) >= total_expected * self.min_acceptable_ratio:
                self.logger.info(f"批次大小={size}完成，共{len(all_results)}/{total_expected}章")
                return all_results

            # 如果不完整，降级到下一批次大小
            if has_failure or len(all_results) < total_expected * self.min_acceptable_ratio:
                self.logger.warning(
                    f"批次大小={size}结果不完整 ({len(all_results)}/{total_expected})，降级到下一梯度"
                )
                # 继续尝试下一个批次大小

        # 所有降级尝试都失败，返回部分结果
        self.logger.error(f"所有降级尝试失败，返回部分结果: {len(all_results)}章")
        return all_results

    def _generate_single_summary(
        self,
        act_number: int,
        act_data: Dict[str, Any],
        act_name: str,
        chapter: int,
    ) -> Optional[Dict[str, Any]]:
        """生成单章梗概（用于补充缺失章节）"""
        self.logger.info(f"单章补充生成: 第{chapter}章")

        for retry in range(3):  # 单章最多3次重试
            try:
                prompt = self._build_batch_prompt(
                    act_number, act_data, act_name, (chapter, chapter)
                )
                response = self._call_ai_api(prompt, 1)
                summaries = self._parse_response(response, (chapter, chapter))

                if f"第{chapter}章" in summaries:
                    return summaries[f"第{chapter}章"]

            except RetryableGenerationError as e:
                self.logger.warning(f"单章生成失败: {e}")
                if retry < 2:
                    self.logger.info(f"重试 #{retry + 1}")

        return None

    def _check_missing_chapters(
        self,
        summaries: Dict[str, Any],
        start_ch: int,
        end_ch: int,
    ) -> List[int]:
        """检查缺失的章节号"""
        missing = []
        for ch in range(start_ch, end_ch + 1):
            if f"第{ch}章" not in summaries:
                missing.append(ch)
        return missing

    def _find_act_data(self, act_number: int) -> Tuple[Dict[str, Any], str]:
        """根据幕序号在act_plan中找到对应的幕数据"""
        plan = self.act_plan.get("幕规划", {})
        keys = list(plan.keys())
        if act_number <= len(keys):
            return plan[keys[act_number - 1]], keys[act_number - 1]
        return plan.get(f"第{act_number}幕", {}), f"第{act_number}幕"

    def _build_batch_prompt(
        self,
        act_number: int,
        act_data: Dict[str, Any],
        act_name: str,
        chapter_range: Tuple[int, int],
    ) -> str:
        """构建梗概生成Prompt - 改进版本，明确列出必须输出的章节号"""
        start_ch, end_ch = chapter_range
        batch_count = end_ch - start_ch + 1

        # 明确列出必须输出的章节号列表
        required_chapters = [f"第{i}章" for i in range(start_ch, end_ch + 1)]
        required_chapters_str = ", ".join(required_chapters)

        # 前文梗概上下文
        previous_summaries = self._format_previous_summaries(start_ch)

        # 幕信息
        act_info = yaml.dump(act_data, allow_unicode=True, default_flow_style=False)

        # 源材料
        core_setting_text = yaml.dump(
            self.core_setting, allow_unicode=True, default_flow_style=False
        )
        overall_story = self._build_overall_story_text()

        prompt = f"""【任务】为以下章节生成故事梗概。

══════════════════════════════════════
—— 【必须输出的章节列表】——
══════════════════════════════════════

你需要为以下 {batch_count} 章生成梗概，必须包含以下所有章节号，不可跳过任何一章：
{required_chapters_str}

══════════════════════════════════════
—— 源材料 ——
══════════════════════════════════════

【核心设定】
{core_setting_text}

【整体故事框架】
{overall_story}

【当前幕规划：{act_name}】
{act_info}

══════════════════════════════════════
—— 已生成梗概（前章上下文）——
══════════════════════════════════════

{previous_summaries}

══════════════════════════════════════
—— 梗概生成规则 ——
══════════════════════════════════════

1. 每章梗概长度：50-80字，简洁但完整描述本章核心故事
2. 楔概内容需包含：主要事件、角色关键行动、情绪转折点
3. 章节之间剧情自然衔接，前章梗概结尾与后章开头呼应
4. 严格遵循幕规划中的节奏，不得跳过或压缩阶段

5. 关键转折点处理规则（内容锚定模式）：
   转折点是幕规划的内容锚定点，转折点描述的事件应该在该章节发生或达到高潮。

   【重要】如果前文梗概已经提前完成了转折点描述的核心事件：
   - 该转折点章节应作为事件的"确认节点"或"影响展开节点"
   - 不要机械重复事件本身，而是写事件的影响、后续发展或关系的正式确立
   - 示例："救下墨麟"已在第17章展开 → 第22章转折点应写"墨麟正式归心，天大因果确立"

6. 每章梗概必须与前文梗概上下文保持连贯：
   - 仔细阅读"已生成梗概（前章上下文）"部分
   - 确认该章节的事件是否已在前章展开
   - 如果已展开，本章应承接后续而非重复

══════════════════════════════════════
—— JSON 输出格式 ——
══════════════════════════════════════

请以严格的 JSON 格式输出，使用英文双引号包裹所有键和字符串值。

EXAMPLE JSON OUTPUT:
```json
{{
  "第{start_ch}章": {{
    "梗概": "第{start_ch}章的50-80字完整故事梗概，包含主要事件和情绪转折",
    "所属幕": "{act_name}",
    "情绪定位": "本章核心情绪走向（如：绝望→觉醒→求生）"
  }},
  "第{start_ch + 1}章": {{
    "梗概": "第{start_ch + 1}章的故事梗概，与前章衔接",
    "所属幕": "{act_name}",
    "情绪定位": "情绪走向"
  }}
}}
```

【严格要求】
1. 必须为以下所有章节输出完整梗概：{required_chapters_str}
2. 你的输出必须包含 {batch_count} 个章节对象
3. 每个"梗概"值必须是完整的字符串（50-80字），不得中途截断
4. 禁止在 JSON 对象外输出任何内容
5. 禁止使用中文引号（""）或单引号（'），必须使用英文双引号（"）
6. 禁止使用 True/False/None，必须使用 true/false/null
7. 禁止跳过任何章节号

现在请输出包含以上 {batch_count} 章的完整 JSON：
"""
        return prompt

    def _format_previous_summaries(self, current_start: int) -> str:
        """格式化前文梗概作为上下文"""
        if not self.existing_summaries:
            return "（本批次为首批章节，无前文梗概）"

        parts = []
        for ch in range(1, current_start):
            key = f"第{ch}章"
            if key in self.existing_summaries:
                summary = self.existing_summaries[key].get("梗概", "")
                if summary:
                    parts.append(f"{key}: {summary}")

        if parts:
            # 最多显示100章前文梗概
            display_parts = parts[-100:] if len(parts) > 100 else parts
            return "以下为已生成的前文梗概：\n" + "\n".join(display_parts)
        return "（无前文梗概）"

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

    def _call_ai_api(self, prompt: str, chapter_count: int) -> str:
        """调用AI API生成梗概，遵循DeepSeek JSON Output规范"""
        try:
            # 动态计算 max_tokens：每章预估 150 tokens（80字梗概 + JSON结构）
            role_config = self.ai_role_manager.get_role_config(AIRole.GENERATOR)
            configured_max = role_config.max_tokens
            # 107章 × 150 = 16050，需要足够的输出空间
            estimated_tokens = min(configured_max, max(8000, chapter_count * 150))

            kwargs = {
                "response_format": {"type": "json_object"},  # DeepSeek JSON Output
                "max_tokens": estimated_tokens,
            }

            self.logger.info(f"梗概生成设置 max_tokens={estimated_tokens} (章节数={chapter_count})")

            response = self.ai_role_manager.chat_completion(
                role=AIRole.GENERATOR,
                messages=[
                    {
                        "role": "system",
                        "content": "你是专业的小说故事规划师。输出必须是严格的JSON格式，使用双引号包裹所有键和字符串值。禁止输出任何JSON之外的内容。",
                    },
                    {"role": "user", "content": prompt},
                ],
                **kwargs,
            )

            # DeepSeek JSON Output 可能返回空 content，触发重试
            if not response or response.strip() == "":
                self.logger.warning("API返回空content（DeepSeek已知问题），触发重试")
                raise RetryableGenerationError("API返回空content")

            return response
        except Exception as e:
            self.logger.error(f"AI API调用失败: {e}")
            raise RetryableGenerationError(f"AI API调用失败: {e}")

    def _parse_response(
        self, response: str, chapter_range: Tuple[int, int]
    ) -> Dict[str, Any]:
        """解析梗概响应，包含截断修复逻辑

        改进点：记录缺失章节，便于上层补充生成
        """
        start_ch, end_ch = chapter_range
        expected_count = end_ch - start_ch + 1

        # 尝试标准解析
        try:
            cleaned = self._clean_markdown_response(response)
            data = json.loads(cleaned)

            if not isinstance(data, dict):
                raise ValueError("响应不是JSON对象")

            summaries = self._extract_summaries_from_data(data, start_ch, end_ch)

            if summaries:
                # 检查缺失章节
                missing = self._check_missing_chapters(summaries, start_ch, end_ch)
                if missing:
                    self.logger.warning(
                        f"解析结果缺失{len(missing)}章: 第{missing[0]}章等"
                    )
                self.logger.info(f"解析到 {len(summaries)} 章梗概 (期望{expected_count}章)")
                return summaries

        except json.JSONDecodeError as e:
            self.logger.warning(f"标准JSON解析失败: {e}")

        # 尝试修复截断的 JSON
        try:
            repaired = self._repair_truncated_json(response, start_ch, end_ch)
            if repaired:
                self.logger.info(f"成功修复截断JSON，提取 {len(repaired)} 章")
                return repaired
        except Exception as e:
            self.logger.warning(f"JSON修复失败: {e}")

        # 尝试 YAML fallback
        try:
            cleaned = self._clean_markdown_response(response)
            data = yaml.safe_load(cleaned)
            if isinstance(data, dict):
                summaries = self._extract_summaries_from_data(data, start_ch, end_ch)
                if summaries:
                    return summaries
        except Exception:
            pass

        self.logger.error(f"梗概解析完全失败，响应前500字符: {response[:500]}")
        return {}

    def _extract_summaries_from_data(
        self, data: Dict[str, Any], start_ch: int, end_ch: int
    ) -> Dict[str, Any]:
        """从解析后的数据中提取章节梗概"""
        summaries = {}
        for ch in range(start_ch, end_ch + 1):
            key = f"第{ch}章"
            if key in data:
                summaries[key] = data[key]

        if not summaries:
            # 尝试其他可能的键格式
            for k, v in data.items():
                if "章" in k and isinstance(v, dict):
                    summaries[k] = v

        return summaries

    def _repair_truncated_json(
        self, response: str, start_ch: int, end_ch: int
    ) -> Dict[str, Any]:
        """尝试修复截断的JSON，提取已生成的有效数据

        改进点：更好地处理截断情况，保留部分结果
        """
        cleaned = self._clean_markdown_response(response)

        # 策略1: 正则匹配完整的章节对象
        # 匹配 "第N章": { "梗概": "...", "所属幕": "...", "情绪定位": "..." }
        pattern = r'"第(\d+)章"\s*:\s*\{\s*"梗概"\s*:\s*"([^"]+)"\s*,\s*"所属幕"\s*:\s*"([^"]+)"\s*,\s*"情绪定位"\s*:\s*"([^"]*)"'
        matches = re.findall(pattern, cleaned)

        if matches:
            summaries = {}
            last_complete_ch = 0
            for m in matches:
                ch_num = int(m[0])
                if start_ch <= ch_num <= end_ch:
                    summaries[f"第{ch_num}章"] = {
                        "梗概": m[1],
                        "所属幕": m[2],
                        "情绪定位": m[3] if m[3] else "待补充",
                    }
                    last_complete_ch = ch_num

            if summaries:
                self.logger.info(f"正则提取到 {len(summaries)} 章完整梗概")
                # 记录截断位置
                if last_complete_ch < end_ch:
                    self.logger.warning(
                        f"JSON截断于第{last_complete_ch}章，缺失第{last_complete_ch + 1}-{end_ch}章"
                    )
                return summaries

        # 策略2: 尝试补全 JSON 结构
        try:
            # 找最后一个完整的 }
            last_brace = cleaned.rfind("}")
            if last_brace > 0:
                partial = cleaned[:last_brace + 1]
                if partial.strip().startswith("{"):
                    # 计算缺少的闭合括号数
                    open_braces = partial.count("{") - partial.count("}")
                    closed = partial + "}" * open_braces
                    data = json.loads(closed)
                    return self._extract_summaries_from_data(data, start_ch, end_ch)
        except Exception:
            pass

        return {}

    def _clean_markdown_response(self, response: str) -> str:
        """清理Markdown格式的响应"""
        lines = response.split("\n")
        cleaned_lines = []
        for line in lines:
            if line.strip().startswith("```"):
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


class SlidingWindowSkeletonGenerator:
    """滑动窗口多轮大纲生成器

    支持任意起始点的增量生成，跨幕无缝衔接。
    以对话窗口（50-100章）为单位累积上下文。
    增加章节梗概上下文注入，提高故事一致性。
    """

    def __init__(
        self,
        config: Dict[str, Any],
        ai_role_manager: Any,
        act_plan: Dict[str, Any],
        core_setting: Dict[str, Any] = None,
        overall_outline: Dict[str, Any] = None,
        chapter_summaries: Dict[str, Any] = None,  # 新增：章节梗概
        output_dir: Optional[Path] = None,
        conversation_window: int = 100,  # 对话窗口大小（章节数）
        batch_size: int = 10,  # 每批章节数
        summary_window: int = 100,  # 新增：梗概上下文窗口
    ):
        self.config = config
        self.ai_role_manager = ai_role_manager
        self.act_plan = act_plan
        self.core_setting = core_setting or {}
        self.overall_outline = overall_outline or {}
        self.chapter_summaries = chapter_summaries or {}  # 新增
        self.conversation_window = conversation_window
        self.batch_size = batch_size
        self.summary_window = summary_window  # 新增
        self.output_dir = output_dir or Path(".")
        self.logger = logging.getLogger(__name__)

        # 对话状态
        self.messages: List[Dict[str, str]] = []  # 当前对话历史
        self.window_start: int = 0  # 当前窗口起始章

        # 幕规划缓存
        self._act_chapter_ranges = self._parse_act_ranges(act_plan)

    def generate_skeletons(
        self,
        chapter_range: Tuple[int, int],
        existing_skeletons: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """生成指定范围的大纲（支持任意起始点）

        Args:
            chapter_range: (start_ch, end_ch) 要生成的章节范围
            existing_skeletons: 已存在的大纲（用于初始化上下文）

        Returns:
            Dict[str, Any]: 生成的章节大纲
        """
        start_ch, end_ch = chapter_range
        self.logger.info(f"开始滑动窗口多轮生成: 第{start_ch}-{end_ch}章")

        # 初始化对话窗口
        self._init_conversation_window(start_ch, existing_skeletons)

        all_skeletons = existing_skeletons.copy() if existing_skeletons else {}

        # 批次生成
        for batch_start in range(start_ch, end_ch + 1, self.batch_size):
            batch_end = min(batch_start + self.batch_size - 1, end_ch)

            # 检查是否需要滑动窗口
            if batch_start > self.window_start + self.conversation_window:
                self._slide_window(batch_start, all_skeletons)

            # 构建用户消息
            user_msg = self._build_batch_prompt(batch_start, batch_end, all_skeletons)
            self.messages.append({"role": "user", "content": user_msg})

            # 调用API（携带完整对话历史）
            response = self._call_ai_api()

            # 解析响应（带重试）
            batch_skeletons = self._parse_batch_response(response, (batch_start, batch_end))
            expected_count = batch_end - batch_start + 1
            actual_count = len(batch_skeletons) if batch_skeletons else 0

            # 解析失败或章节数量不足，都触发重试
            if not batch_skeletons or actual_count < expected_count:
                if batch_skeletons and actual_count < expected_count:
                    self.logger.warning(
                        f"批次{batch_start}-{batch_end}只生成{actual_count}/{expected_count}章，"
                        f"缺少{expected_count - actual_count}章，开始重试..."
                    )

                # 解析失败，先尝试重试（最多2次）
                retry_count = 0
                max_retries = 2

                while retry_count < max_retries:
                    retry_count += 1
                    self.logger.warning(f"第{retry_count}次重试...")

                    # 构建重试提示词，强调JSON格式要求
                    retry_prompt = self._build_retry_prompt(
                        batch_start, batch_end, response,
                        missing_count=expected_count - actual_count if batch_skeletons else expected_count
                    )
                    self.messages.append({"role": "user", "content": retry_prompt})

                    # 重新调用API
                    response = self._call_ai_api()

                    # 再次解析
                    batch_skeletons = self._parse_batch_response(response, (batch_start, batch_end))
                    actual_count = len(batch_skeletons) if batch_skeletons else 0

                    if batch_skeletons and actual_count >= expected_count:
                        self.logger.info(f"第{retry_count}次重试成功！解析到 {actual_count} 章")
                        break

                # 重试后仍不足，但有一些结果，记录警告继续
                if batch_skeletons and actual_count < expected_count:
                    self.logger.warning(
                        f"重试后仍缺少{expected_count - actual_count}章，继续生成..."
                    )
                elif not batch_skeletons:
                    # 重试后完全没有结果，回退到单章模式
                    self.logger.warning(f"重试{max_retries}次后仍失败，回退到单章模式")
                    batch_skeletons = self._fallback_single_generation(
                        batch_start, batch_end, all_skeletons
                    )

            all_skeletons.update(batch_skeletons)

            # 将AI回复加入对话历史
            self.messages.append({"role": "assistant", "content": response})

            # 简化过长的对话历史（保留窗口大小）
            self._trim_conversation_if_needed()

        return all_skeletons

    def _init_conversation_window(
        self, start_ch: int, existing_skeletons: Optional[Dict[str, Any]]
    ) -> None:
        """初始化对话窗口

        加载前N章（窗口大小）作为初始上下文
        """
        self.window_start = max(1, start_ch - self.conversation_window + self.batch_size)

        # 构建system消息（含核心设定和全部幕规划）
        system_content = self._build_system_content()
        self.messages = [{"role": "system", "content": system_content}]

        # 加载前文作为初始assistant消息（如果有）
        if existing_skeletons:
            prev_context = self._format_previous_skeletons(
                self.window_start, start_ch - 1, existing_skeletons
            )
            if prev_context:
                self.messages.append({
                    "role": "assistant",
                    "content": f"前文大纲（第{self.window_start}-{start_ch-1}章）：\n{prev_context}",
                })
                self.logger.info(f"已加载前文大纲（第{self.window_start}-{start_ch-1}章）作为上下文")

    def _build_system_content(self) -> str:
        """构建system消息内容（含核心设定、幕规划、章节梗概）"""
        parts = []

        # 核心设定
        if self.core_setting:
            core_yaml = yaml.dump(
                self.core_setting, allow_unicode=True, default_flow_style=False
            )
            parts.append(f"【核心设定】\n{core_yaml}")

        # 全部幕规划
        act_plans_text = self._build_all_act_plans_text()
        if act_plans_text:
            parts.append(f"\n【幕规划（全部）】\n{act_plans_text}")

        # 新增：全部章节梗概（关键上下文）
        if self.chapter_summaries:
            summaries_text = self._build_all_summaries_text()
            if summaries_text:
                parts.append(f"\n【章节梗概（全部）】\n{summaries_text}")

        # 整体故事框架
        overall_text = self._build_overall_story_text()
        if overall_text:
            parts.append(f"\n【整体故事框架】\n{overall_text}")

        # 系统指令
        parts.append("\n【你的任务】")
        parts.append("你是一个专业的小说章节规划师，擅长设计章节骨架结构。")
        parts.append("请根据以上设定、幕规划和章节梗概，依次生成指定章节的详细骨架。")
        parts.append("确保章节内容覆盖梗概描述的核心故事，剧情连贯、伏笔贯通、情绪节奏合理。")

        return "\n\n".join(parts)

    def _build_all_summaries_text(self) -> str:
        """构建全部章节梗概文本（注入system message）"""
        if not self.chapter_summaries:
            return ""

        lines = ["以下为全书的章节故事梗概，生成骨架时必须覆盖这些核心内容："]
        lines.append("")

        # 按章节号排序
        sorted_chapters = []
        for key in self.chapter_summaries.keys():
            match = re.search(r"\d+", key)
            if match:
                sorted_chapters.append((int(match.group()), key))

        sorted_chapters.sort(key=lambda x: x[0])

        for ch_num, key in sorted_chapters:
            summary_data = self.chapter_summaries[key]
            genggai = summary_data.get("梗概", "")
            emotion = summary_data.get("情绪定位", "")
            if genggai:
                lines.append(f"{key}: {genggai}（情绪：{emotion}）")

        return "\n".join(lines)

    def _build_all_act_plans_text(self) -> str:
        """构建全部幕规划文本（含关键转折点硬约束）"""
        acts = self.act_plan.get("幕规划", {})
        if not acts:
            return ""

        # 计算总章节数
        total_chapters = 0
        for act_data in acts.values():
            chapter_range = act_data.get("章节范围", "")
            match = re.search(r"第?(\d+)\s*[-–到]\s*第?(\d+)\s*章?", chapter_range)
            if match:
                total_chapters = max(total_chapters, int(match.group(2)))

        lines = []
        lines.append(f"【故事整体规划：共{total_chapters}章，分为{len(acts)}幕】")
        lines.append("")

        # 【新增】全局关键转折点汇总（放在最前面，强化印象）
        all_turning_points = []
        for act_data in acts.values():
            turning_points = act_data.get("关键转折点", [])
            all_turning_points.extend(turning_points)

        if all_turning_points:
            lines.append("【全局关键转折点（硬约束）】")
            lines.append("以下事件必须在指定章节发生，严禁提前或延后：")
            for tp in all_turning_points:
                lines.append(f"  ★ {tp}")
            lines.append("")
            lines.append("违反此约束将导致故事结构崩坏，是不可接受的错误！")
            lines.append("")

        for i, (act_name, act_data) in enumerate(acts.items(), 1):
            lines.append(f"\n=== 第{i}幕：{act_name} ===")

            # 章节范围
            chapter_range = act_data.get("章节范围", "")
            if chapter_range:
                lines.append(f"章节范围: {chapter_range}")

            # 核心信息
            core_conflict = act_data.get("核心冲突", "")
            plot_summary = act_data.get("剧情概要", "")
            if core_conflict:
                lines.append(f"核心冲突: {core_conflict}")
            if plot_summary:
                lines.append(f"剧情概要: {plot_summary}")

            # 爽点/爆点设计
            highlights = act_data.get("爽点/爆点设计", [])
            if highlights:
                lines.append(f"爽点设计: {', '.join(str(h) for h in highlights[:3])}")

            # 【新增】本幕关键转折点（重复强调）
            turning_points = act_data.get("关键转折点", [])
            if turning_points:
                lines.append("")
                lines.append("【本幕关键转折点】")
                for tp in turning_points:
                    lines.append(f"  ★ {tp} ★（硬约束）")

            # 【新增】本幕章节划分
            chapter_divisions = act_data.get("章节划分", [])
            if chapter_divisions:
                lines.append("")
                lines.append("【章节划分】")
                for div in chapter_divisions:
                    lines.append(f"  • {div}")

            # 与下幕衔接
            next_act_link = act_data.get("与下幕衔接", "")
            if next_act_link:
                lines.append(f"与下幕衔接: {next_act_link}")

        return "\n".join(lines)

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

    def _format_previous_skeletons(
        self, start_ch: int, end_ch: int, existing_skeletons: Dict[str, Any]
    ) -> str:
        """格式化前文大纲为紧凑摘要"""
        if not existing_skeletons:
            return ""

        summaries = []
        for ch in range(start_ch, end_ch + 1):
            key = f"第{ch}章"
            sk = existing_skeletons.get(key)
            if not sk:
                continue

            parts = [key]
            title = sk.get("标题", "")
            if title:
                parts.append(f"《{title}》")

            core = sk.get("核心事件", "")
            if core:
                parts.append(f"核心: {core}")

            ending = sk.get("结尾卡点", "")
            if ending:
                parts.append(f"结尾: {ending}")

            foreshadow = sk.get("伏笔处理", {})
            if isinstance(foreshadow, dict):
                planted = foreshadow.get("埋设", [])
                if planted:
                    parts.append(f"埋笔: {'; '.join(str(p) for p in planted[:2])}")

            summaries.append(" | ".join(parts))

        return "\n".join(summaries) if summaries else ""

    def _parse_act_ranges(self, act_plan: Dict[str, Any]) -> Dict[int, Tuple[int, int]]:
        """解析幕规划中的章节范围

        Returns:
            Dict[int, Tuple[int, int]]: {幕号: (起始章, 结束章)}
        """
        ranges = {}
        acts = act_plan.get("幕规划", {})

        for i, (act_name, act_data) in enumerate(acts.items(), 1):
            chapter_range = act_data.get("章节范围", "")
            # 解析 "第1-50章" 或 "1-50" 格式
            match = re.search(r"第?(\d+)\s*-\s*第?(\d+)\s*章?", chapter_range)
            if match:
                ranges[i] = (int(match.group(1)), int(match.group(2)))

        return ranges

    def _slide_window(
        self, new_start: int, all_skeletons: Dict[str, Any]
    ) -> None:
        """滑动对话窗口

        保留最近的N章在对话历史中，移除更早的消息
        """
        # 计算新的窗口起始章
        self.window_start = new_start - self.conversation_window + self.batch_size

        # 保留system消息
        new_messages = [self.messages[0]]

        # 计算需要保留的消息数量（每批生成batch_size章，每批对应2条消息：user + assistant）
        messages_per_batch = 2
        num_batches_to_keep = self.conversation_window // self.batch_size
        messages_to_keep = num_batches_to_keep * messages_per_batch

        # 保留最近的消息
        if len(self.messages) > messages_to_keep + 1:  # +1 for system message
            keep_start_idx = len(self.messages) - messages_to_keep
            new_messages.extend(self.messages[keep_start_idx:])
        else:
            new_messages.extend(self.messages[1:])

        self.messages = new_messages
        self.logger.info(f"窗口滑动至: 第{self.window_start}章起，保留{num_batches_to_keep}批对话")

    def _build_batch_prompt(
        self, batch_start: int, batch_end: int, all_skeletons: Dict[str, Any]
    ) -> str:
        """构建批次生成提示词"""
        batch_count = batch_end - batch_start + 1

        # 计算总章节数（用于进度提示）
        total_chapters = 0
        for act_range in self._act_chapter_ranges.values():
            total_chapters = max(total_chapters, act_range[1])

        # 计算当前进度
        if total_chapters > 0:
            progress_pct = (batch_start / total_chapters * 100)
            end_pct = (batch_end / total_chapters * 100)
        else:
            total_chapters = 793  # 默认总章节数
            progress_pct = (batch_start / total_chapters * 100)
            end_pct = (batch_end / total_chapters * 100)

        lines = []
        lines.append(f"【任务】生成第{batch_start}-{batch_end}章的详细骨架（共{batch_count}章）")
        lines.append("")

        # 【新增】检查当前批次是否涉及关键转折点
        involved_turning_points = self._get_involved_turning_points(batch_start, batch_end)

        # 【新增】关键转折点硬约束（如果本批次涉及）
        if involved_turning_points:
            lines.append("【★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★】")
            lines.append("【★★★★★★★★ 硬约束：本批次包含关键转折点 ★★★★★★★★】")
            lines.append("【★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★】")
            lines.append("")
            lines.append("以下事件必须在指定章节发生指定内容，严禁提前、延后或跳过：")
            lines.append("")
            for tp in involved_turning_points:
                # 解析章节号和事件描述
                match = re.search(r"第(\d+)章(.+)", tp)
                if match:
                    ch_num = int(match.group(1))
                    event_desc = match.group(2).strip()
                    lines.append(f"★★★ 第{ch_num}章：【必须发生】{event_desc} ★★★")
                    lines.append(f"     这是全局关键转折点，违反将导致故事结构崩坏！")
            lines.append("")
            lines.append("注意：即使本批次其他章节可以灵活调整，关键转折点章节必须严格遵循！")
            lines.append("")

        lines.append(f"【重要：整体故事定位】")
        lines.append(f"• 本小说总章节数：{total_chapters}章")
        lines.append(f"• 当前批次位置：第{batch_start}-{batch_end}章（占总篇幅的约{progress_pct:.1f}%-{end_pct:.1f}%）")
        if involved_turning_points:
            lines.append(f"• **本批次包含关键转折点，必须严格遵守！**")
        else:
            lines.append(f"• **关键提示：本批次只是整体故事的一部分，不是全部！**")
        lines.append(f"• 严禁在本批次内跳过或压缩阶段，必须严格按【幕章节划分】推进")
        lines.append("")
        lines.append("【重要要求】")
        lines.append(f"1. 必须一次性生成全部{batch_count}章的完整骨架，不得省略或简化")
        lines.append(f"2. 每章都必须包含完整的10个字段（标题、字数目标、章节定位、核心事件、与前章因果、人物行动、场景概览、情绪曲线、伏笔处理、结尾卡点）")
        lines.append("3. 确保章节之间剧情连贯，伏笔呼应")
        lines.append("4. **严格遵循下方【幕章节划分】的阶段性要求，不得跳过或跳跃阶段**")
        lines.append("5. **必须明确：当前批次处于故事整体进度的哪个阶段，不要加速或跳过大段剧情**")
        lines.append("")
        lines.append("【本批次要求】")
        lines.append("1. 每章必须有独立的'起承转合'微结构")
        lines.append("2. 核心事件要写清因果逻辑（因为X，所以Y，导致Z）")
        lines.append("3. 章节之间剧情自然递进，前章的结尾卡点导向后章的开场")
        lines.append("4. 情绪曲线在本批次内有起有伏")
        lines.append("5. 伏笔埋设与回收要跨章协调")
        lines.append("6. **当前批次剧情必须服务于整体故事结构，不得过早或过晚**")
        lines.append("")

        # 添加幕定位信息和详细章节划分
        involved_acts = self._get_involved_acts(batch_start, batch_end)
        if involved_acts:
            lines.append("【涉及幕定位】")
            for act_num in involved_acts:
                act_range = self._act_chapter_ranges.get(act_num)
                if act_range:
                    lines.append(f"- 第{act_num}幕：第{act_range[0]}-{act_range[1]}章")
            lines.append("")

            # 添加详细的章节划分指引
            lines.append("【幕章节划分】")
            lines.append("本批次必须严格遵循以下阶段性剧情安排：")
            lines.append("")
            for act_num in involved_acts:
                act_data = self._get_act_data_by_number(act_num)
                if act_data:
                    chapter_divisions = act_data.get("章节划分", [])
                    if chapter_divisions:
                        lines.append(f"=== 第{act_num}幕章节划分 ===")
                        for division in chapter_divisions:
                            lines.append(f"  • {division}")
                        lines.append("")
            lines.append("")

        # 新增：当前批次各章的梗概目标
        if self.chapter_summaries:
            lines.append("【本章梗概目标】")
            lines.append("以下是本批次各章的预设梗概，生成骨架时必须覆盖这些核心内容：")
            lines.append("")
            for ch in range(batch_start, batch_end + 1):
                key = f"第{ch}章"
                if key in self.chapter_summaries:
                    summary_data = self.chapter_summaries[key]
                    genggai = summary_data.get("梗概", "")
                    emotion = summary_data.get("情绪定位", "")
                    lines.append(f"★ {key}梗概：{genggai}（情绪：{emotion}）")
                else:
                    lines.append(f"★ {key}梗概：（从幕规划推断，需覆盖该章应有的核心事件）")
            lines.append("")
            lines.append("重要：生成的骨架核心事件必须涵盖梗概描述的内容，不得偏离！")
            lines.append("")

        lines.append("【输出格式】")
        lines.append("请以严格的JSON格式输出（必须使用英文双引号，绝不可用中文引号）：")
        lines.append("```json")
        lines.append("{")
        lines.append(f'  "第{batch_start}章": {{')
        lines.append('    "标题": "章节标题",')
        lines.append('    "字数目标": 2500,')
        lines.append('    "章节定位": "本章在幕中的角色",')
        lines.append('    "核心事件": "2-3句描述核心情节，写明因果链",')
        lines.append('    "与前章因果": "承接上章XX，推进YY，为下章ZZ埋笔",')
        lines.append('    "人物行动": {')
        lines.append('      "主角": "主角行动与动机",')
        lines.append('      "关键配角": "配角行动与主线关联"')
        lines.append("    },")
        lines.append('    "场景概览": [')
        lines.append('      "开场：XX地点 — 核心事件概述",')
        lines.append('      "发展：XX地点 — 核心事件概述",')
        lines.append('      "高潮：XX地点 — 核心事件概述",')
        lines.append('      "收束：XX地点 — 核心事件概述"')
        lines.append("    ],")
        lines.append('    "情绪曲线": "本章情绪走向",')
        lines.append('    "伏笔处理": {')
        lines.append('      "埋设": ["伏笔描述"],')
        lines.append('      "回收": ["回收描述（标注前章编号）"]')
        lines.append("    },")
        lines.append('    "结尾卡点": "章末悬念/钩子（具体描述）"')
        lines.append("  },")  # 注意这里要有逗号！
        lines.append(f'  "第{batch_start+1}章": {{')
        lines.append('    // ... 第2章内容，格式同上')
        lines.append("  },")  # 逗号分隔
        lines.append('  // ... 以此类推直到')
        lines.append(f'  "第{batch_end}章": {{')
        lines.append('    // 最后一章内容')
        lines.append("  }")  # 最后一章不加逗号
        lines.append("}")
        lines.append("```")
        lines.append(f"重要：必须为第{batch_start}-{batch_end}章的每一章输出完整骨架，章节之间用逗号分隔，最后一章不加逗号。")

        return "\n".join(lines)

    def _get_act_data_by_number(self, act_num: int) -> Optional[Dict[str, Any]]:
        """根据幕号获取幕数据"""
        acts = self.act_plan.get("幕规划", {})
        keys = list(acts.keys())
        if act_num <= len(keys):
            return acts.get(keys[act_num - 1])
        return acts.get(f"第{act_num}幕")

    def _get_involved_acts(self, start_ch: int, end_ch: int) -> List[int]:
        """获取涉及的幕号列表"""
        involved = []
        for act_num, (act_start, act_end) in self._act_chapter_ranges.items():
            if act_start <= end_ch and act_end >= start_ch:
                involved.append(act_num)
        return sorted(involved)

    def _get_involved_turning_points(self, start_ch: int, end_ch: int) -> List[str]:
        """获取当前批次涉及的关键转折点

        Args:
            start_ch: 批次起始章节号
            end_ch: 批次结束章节号

        Returns:
            List[str]: 当前批次涉及的关键转折点列表
        """
        involved = []
        acts = self.act_plan.get("幕规划", {})

        for act_data in acts.values():
            turning_points = act_data.get("关键转折点", [])
            for tp in turning_points:
                # 解析章节号，如 "第22章救下麒麟幼子墨麟"
                match = re.search(r"第(\d+)章", tp)
                if match:
                    ch = int(match.group(1))
                    if start_ch <= ch <= end_ch:
                        involved.append(tp)

        return involved

    def _call_ai_api(self) -> str:
        """调用AI API"""
        try:
            from novel_generator.core.ai_roles import AIRole

            # 动态计算所需token数：基于对话历史长度估算
            # 通常每批10章需要约12000-16000 token
            estimated_input = sum(len(m["content"]) for m in self.messages)
            # 输出通常是输入的1.5-2倍（章节生成）
            estimated_output = min(16000, max(12000, int(estimated_input * 0.5)))

            response = self.ai_role_manager.chat_completion(
                role=AIRole.GENERATOR,
                messages=self.messages,
                max_tokens=estimated_output,
            )
            return response or ""
        except Exception as e:
            self.logger.error(f"AI API调用失败: {e}")
            raise RetryableGenerationError(f"AI API调用失败: {e}")

    def _parse_batch_response(
        self, response: str, chapter_range: Tuple[int, int]
    ) -> Dict[str, Any]:
        """解析批次响应"""
        start_ch, end_ch = chapter_range
        try:
            cleaned = self._clean_markdown_response(response)
            data = json.loads(cleaned)

            if not isinstance(data, dict):
                raise ValueError("响应不是JSON对象")

            # 提取章节骨架
            skeletons = {}
            for ch in range(start_ch, end_ch + 1):
                key = f"第{ch}章"
                if key in data:
                    skeletons[key] = data[key]
                else:
                    # 尝试其他可能的键格式
                    for k in data.keys():
                        if str(ch) in k and "章" in k:
                            skeletons[key] = data[k]
                            break

            if skeletons:
                self.logger.info(f"解析到 {len(skeletons)} 章骨架")

            return skeletons

        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON解析失败: {e}，响应前500字符: {response[:500]}")
            return {}
        except Exception as e:
            self.logger.warning(f"解析批次响应失败: {e}")
            return {}

    def _clean_markdown_response(self, response: str) -> str:
        """清理Markdown格式的响应"""
        lines = response.split("\n")
        cleaned_lines = []
        for line in lines:
            if line.strip().startswith("```"):
                continue
            cleaned_lines.append(line)
        result = "\n".join(cleaned_lines)

        # 修复中文引号为英文引号（JSON标准）
        result = result.replace('"', '"').replace('"', '"')  # 双引号
        result = result.replace("'", "'").replace("'", "'")  # 单引号

        # 修复JSON字符串内未转义的控制字符
        in_string = False
        escaped = False
        chars = list(result)
        for i, ch in enumerate(chars):
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string and ord(ch) < 0x20 and ch not in ("\n",):
                chars[i] = " "
        return "".join(chars)

    def _build_retry_prompt(
        self, batch_start: int, batch_end: int, failed_response: str,
        missing_count: int = 0
    ) -> str:
        """构建重试提示词，强调JSON格式要求"""
        batch_count = batch_end - batch_start + 1
        lines = []

        if missing_count > 0:
            lines.append(f"【补全】第{batch_start}-{batch_end}章骨架（缺少{missing_count}章）")
            lines.append("")
            lines.append(f"之前的响应只生成了{batch_count - missing_count}/{batch_count}章，请补全缺少的{missing_count}章。")
        else:
            lines.append(f"【重试】第{batch_start}-{batch_end}章骨架生成")
            lines.append("")
            lines.append("之前的响应存在JSON格式错误，请重新生成并注意以下要求：")

        lines.append("")
        lines.append("【JSON格式要求】")
        lines.append('1. 必须使用英文双引号 " 包裹所有键和字符串值，不可用中文引号 ""')
        lines.append("2. 每个对象/字典的最后一个属性后不能有加逗号")
        lines.append("3. 对象之间必须用逗号分隔")
        lines.append('4. 键和值之间用冒号加空格分隔：": "')
        lines.append('5. 字符串值内部的换行必须用 \\n 转义')
        lines.append("")

        if missing_count > 0:
            lines.append(f"【要求】必须输出全部{batch_count}章的完整JSON，不得省略任何一章。")
            lines.append("")

        lines.append("【正确格式示例】")
        lines.append("```json")
        lines.append("{")
        lines.append(f'  \"第{batch_start}章\": {{')
        lines.append('    \"标题\": \"章节标题\",')
        lines.append('    \"核心事件\": \"事件描述\"')
        lines.append("  },")  # 注意逗号
        lines.append(f'  \"第{batch_start+1}章\": {{')
        lines.append('    \"标题\": \"章节标题\",')
        lines.append('    \"核心事件\": \"事件描述\"')
        lines.append("  }")  # 最后一章不加逗号
        lines.append("}")
        lines.append("```")
        lines.append("")
        lines.append(f"请输出第{batch_start}-{batch_end}章的完整JSON，确保格式严格正确。")

        return "\n".join(lines)

    def _fallback_single_generation(
        self, start_ch: int, end_ch: int, existing_skeletons: Dict[str, Any]
    ) -> Dict[str, Any]:
        """回退到单章生成模式"""
        self.logger.info(f"回退到单章模式: 第{start_ch}-{end_ch}章")

        all_skeletons = {}
        for ch in range(start_ch, end_ch + 1):
            try:
                # 使用原有的ChapterSkeletonGenerator逻辑
                # 这里简化处理，实际可以调用原有方法
                sk = self._generate_single_chapter(ch, existing_skeletons)
                if sk:
                    all_skeletons[f"第{ch}章"] = sk
            except Exception as e:
                self.logger.error(f"第{ch}章生成失败: {e}")

        return all_skeletons

    def _generate_single_chapter(
        self, ch: int, existing_skeletons: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """单章生成（简化版）"""
        # 构建单章提示词
        prompt = f"请生成第{ch}章的详细骨架。"

        # 添加前文上下文
        prev_context = self._format_previous_skeletons(
            max(1, ch - 15), ch - 1, existing_skeletons
        )
        if prev_context:
            prompt += f"\n\n前文大纲摘要：\n{prev_context}"

        try:
            from novel_generator.core.ai_roles import AIRole

            response = self.ai_role_manager.chat_completion(
                role=AIRole.GENERATOR,
                messages=[
                    {"role": "system", "content": "你是一个专业的小说章节规划师。"},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=2000,
            )

            # 解析单章响应
            return self._parse_single_chapter_response(response)
        except Exception as e:
            self.logger.error(f"单章生成失败: {e}")
            return None

    def _parse_single_chapter_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析单章响应"""
        try:
            cleaned = self._clean_markdown_response(response)
            data = json.loads(cleaned)

            # 尝试获取第一个章节数据
            for key, value in data.items():
                if "章" in key and isinstance(value, dict):
                    return value

            # 如果不是JSON对象，返回整个数据
            if isinstance(data, dict):
                return data

            return None
        except:
            return None

    def _trim_conversation_if_needed(self) -> None:
        """修剪过长的对话历史"""
        # 估算token数（中文字符数 * 1.5）
        total_chars = sum(len(m.get("content", "")) for m in self.messages)
        estimated_tokens = total_chars * 1.5

        # 如果超过800K token，修剪早期的user/assistant对
        max_tokens = getattr(
            self.config.get("generation", {}),
            "max_conversation_tokens",
            800000,
        )

        if estimated_tokens > max_tokens:
            self.logger.warning(
                f"对话历史过长({estimated_tokens:.0f} tokens)，修剪中..."
            )
            # 保留system和最近的消息
            while len(self.messages) > 20:  # 保留最近10轮对话
                if len(self.messages) > 2:
                    self.messages.pop(1)  # 移除最早的user
                    self.messages.pop(1)  # 移除最早的assistant
                else:
                    break


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
        self.summary_file = self.output_dir / "chapter_summary.json"
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

    def _load_existing_summaries(self) -> Dict[str, Any]:
        """加载已存在的章节梗概"""
        if self.summary_file.exists():
            try:
                with open(self.summary_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"加载章节梗概文件失败: {e}")
        return {}

    def _save_summaries(self, summaries: Dict[str, Any]) -> bool:
        """保存章节梗概"""
        try:
            with open(self.summary_file, "w", encoding="utf-8") as f:
                json.dump(summaries, f, ensure_ascii=False, indent=2)
            self.logger.info(f"章节梗概已保存: {self.summary_file}")
            return True
        except Exception as e:
            self.logger.error(f"保存章节梗概失败: {e}")
            return False

    def _summaries_complete(
        self, summaries: Dict[str, Any], start_ch: int, end_ch: int
    ) -> bool:
        """检查梗概是否完整"""
        for ch in range(start_ch, end_ch + 1):
            if f"第{ch}章" not in summaries:
                return False
        return True

    def verify_complete(
        self, summaries: Dict[str, Any], expected_total: int
    ) -> Tuple[bool, List[int]]:
        """验证大纲完整性，返回(是否完整, 缺失章节列表)

        Args:
            summaries: 章节梗概字典
            expected_total: 期望的总章数

        Returns:
            Tuple[bool, List[int]]: (是否完整, 缺失的章节号列表)
        """
        missing = []
        for ch in range(1, expected_total + 1):
            if f"第{ch}章" not in summaries:
                missing.append(ch)

        is_complete = len(missing) == 0
        return is_complete, missing

    def report_missing_chapters(
        self, summaries: Dict[str, Any], expected_total: int
    ) -> str:
        """生成缺失章节报告"""
        is_complete, missing = self.verify_complete(summaries, expected_total)

        if is_complete:
            return f"大纲完整，共{expected_total}章全部存在"

        # 将缺失章节转换为连续区间
        ranges = []
        in_gap = False
        gap_start = None
        for ch in missing:
            if not in_gap:
                in_gap = True
                gap_start = ch
            elif ch != gap_start + len(ranges[-1] if ranges else []) + 1:
                # 不连续，结束当前区间
                if ranges:
                    ranges[-1] = (ranges[-1][0], ch - 1)
                else:
                    ranges.append((gap_start, ch - 1))
                gap_start = ch

        if in_gap:
            ranges.append((gap_start, missing[-1]))

        # 格式化报告
        report_lines = [f"大纲不完整，缺失{len(missing)}章："]
        for start, end in ranges:
            count = end - start + 1
            report_lines.append(f"  - 第{start}-{end}章（{count}章）")

        return "\n".join(report_lines)

    def _need_regenerate_summaries(
        self, summaries: Dict[str, Any], chapter_range: Tuple[int, int]
    ) -> bool:
        """检查是否需要重新生成梗概"""
        start_ch, end_ch = chapter_range
        return not self._summaries_complete(summaries, start_ch, end_ch)

    def _generate_summaries_by_act(
        self,
        summary_generator: ChapterSummaryGenerator,
        act_plan: Dict[str, Any],
        chapter_range: Tuple[int, int],
    ) -> Dict[str, Any]:
        """按幕批次生成章节梗概"""
        start_ch, end_ch = chapter_range
        all_summaries = self._load_existing_summaries()

        # 解析幕的章节范围
        act_ranges = self._parse_act_ranges_from_plan(act_plan)

        for act_num, (act_start, act_end) in act_ranges.items():
            # 检查是否在目标范围内
            if act_start > end_ch or act_end < start_ch:
                continue

            actual_start = max(act_start, start_ch)
            actual_end = min(act_end, end_ch)

            # 检查是否已存在
            if self._summaries_complete(all_summaries, actual_start, actual_end):
                self.logger.info(f"第{actual_start}-{actual_end}章梗概已存在，跳过")
                continue

            # 生成该幕的梗概
            self.logger.info(f"生成第{actual_start}-{actual_end}章梗概（第{act_num}幕）")
            act_summaries = summary_generator.generate_summaries_for_act(
                act_num, (actual_start, actual_end)
            )
            all_summaries.update(act_summaries)
            # 中间保存，防止丢失
            self._save_summaries(all_summaries)

        return all_summaries

    def _parse_act_ranges_from_plan(
        self, act_plan: Dict[str, Any]
    ) -> Dict[int, Tuple[int, int]]:
        """从幕规划中解析章节范围

        如果幕规划中有"章节范围"字段，直接解析；
        否则根据"预估章数"累加计算。
        """
        ranges = {}
        acts = act_plan.get("幕规划", {})

        # 先尝试从"章节范围"字段解析（旧格式兼容）
        for i, (act_name, act_data) in enumerate(acts.items(), 1):
            chapter_range = act_data.get("章节范围", "")
            if chapter_range:
                match = re.search(r"第?(\d+)\s*[-–到]\s*第?(\d+)\s*章?", chapter_range)
                if match:
                    ranges[i] = (int(match.group(1)), int(match.group(2)))

        # 如果没有解析到范围，根据"预估章数"累加计算
        if not ranges:
            current_start = 1
            for i, (act_name, act_data) in enumerate(acts.items(), 1):
                estimated_chapters = act_data.get("预估章数", 0)
                if estimated_chapters > 0:
                    current_end = current_start + estimated_chapters - 1
                    ranges[i] = (current_start, current_end)
                    current_start = current_end + 1

        return ranges

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

    def generate_act_plan_only(
        self,
        core_setting: Dict[str, Any],
        overall_outline: Dict[str, Any],
        num_acts: int = 0,
    ) -> Dict[str, Any]:
        """
        仅执行幕规划（Stage 1）

        Args:
            core_setting: 核心设定
            overall_outline: 整体大纲
            num_acts: 幕数

        Returns:
            Dict: 幕规划结果
        """
        self.logger.info("开始幕规划生成（Stage 1）")

        total_chapters = self.extract_total_chapters(overall_outline)
        if num_acts <= 0:
            num_acts = self.extract_num_acts(overall_outline)

        act_planner = ActLevelPlanner(self.config, self.ai_role_manager)
        act_plan = act_planner.generate_act_plan(
            core_setting, overall_outline, num_acts, total_chapters
        )
        self._save_act_plan(act_plan)
        self.logger.info("幕规划生成完成")
        return act_plan

    def generate_summaries_only(
        self,
        core_setting: Dict[str, Any],
        overall_outline: Dict[str, Any],
        act_plan: Dict[str, Any],
        chapter_range: Tuple[int, int] = None,
        batch_size: int = None,
        force_regenerate: bool = False,
    ) -> Dict[str, Any]:
        """
        仅执行章节梗概生成（Stage 1.5）

        Args:
            core_setting: 核心设定
            overall_outline: 整体大纲
            act_plan: 幕规划（必须已存在）
            chapter_range: 章节范围
            batch_size: 梗概批次大小
            force_regenerate: 强制重新生成

        Returns:
            Dict: 章节梗概结果
        """
        self.logger.info("开始章节梗概生成（Stage 1.5）")

        total_chapters = self.extract_total_chapters(overall_outline)
        if chapter_range is None:
            chapter_range = (1, total_chapters)

        gen_config = self.config.get("generation", {})
        summary_batch_size = batch_size or gen_config.get("summary_batch_size", 150)

        summaries = self._load_existing_summaries()
        if force_regenerate:
            # 清除指定范围的已有梗概
            start_ch, end_ch = chapter_range
            for ch in range(start_ch, end_ch + 1):
                key = f"第{ch}章"
                if key in summaries:
                    del summaries[key]
            self.logger.info(f"强制重新生成：清除第{start_ch}-{end_ch}章已有梗概")

        summary_generator = ChapterSummaryGenerator(
            self.config,
            self.ai_role_manager,
            act_plan,
            core_setting,
            overall_outline,
            summaries,
            batch_size=summary_batch_size,
        )
        summaries = self._generate_summaries_by_act(
            summary_generator, act_plan, chapter_range
        )
        self.logger.info(f"章节梗概生成完成，共{len(summaries)}章")
        return summaries

    def generate_skeletons_only(
        self,
        core_setting: Dict[str, Any],
        overall_outline: Dict[str, Any],
        act_plan: Dict[str, Any],
        summaries: Dict[str, Any],
        chapter_range: Tuple[int, int] = None,
        batch_size: int = None,
        conversation_window: int = None,
    ) -> Dict[str, Any]:
        """
        仅执行章骨架生成（Stage 2）

        Args:
            core_setting: 核心设定
            overall_outline: 整体大纲
            act_plan: 幕规划（必须已存在）
            summaries: 章节梗概（可选）
            chapter_range: 章节范围
            batch_size: 骨架批次大小
            conversation_window: 对话窗口大小

        Returns:
            Dict: 章级骨架结果
        """
        self.logger.info("开始章骨架生成（Stage 2）")

        total_chapters = self.extract_total_chapters(overall_outline)
        if chapter_range is None:
            chapter_range = (1, total_chapters)

        return self._generate_sliding_window_skeletons(
            core_setting, overall_outline, act_plan, summaries,
            chapter_range, batch_size, conversation_window
        )

    def generate_outline_v2(
        self,
        core_setting: Dict[str, Any],
        overall_outline: Dict[str, Any],
        num_acts: int = 0,
        chapter_range: Optional[Tuple[int, int]] = None,
        batch_size: int = None,
        conversation_window: int = None,
        skip_summary: bool = False,
    ) -> Dict[str, Any]:
        """
        三阶段大纲生成（幕规划 → 章节梗概 → 章骨架），骨架直接驱动扩写。
        使用滑动窗口多轮模式。

        Args:
            core_setting: 核心设定
            overall_outline: 整体大纲
            num_acts: 幕数
            chapter_range: 章节范围元组 (start, end)
            batch_size: 每批生成章节数
            conversation_window: 对话窗口大小
            skip_summary: 是否跳过梗概生成（用于已有梗概时复用）

        Returns:
            Dict: 章级骨架（最终大纲）
        """
        self.logger.info("开始三阶段大纲生成（支持增量）")

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

        # Stage 1.5: 章节梗概生成（新增）
        self.logger.info("Stage 1.5: 章节梗概生成")
        summaries = self._load_existing_summaries()
        gen_config = self.config.get("generation", {})
        summary_batch_size = gen_config.get("summary_batch_size", 150)

        if skip_summary:
            self.logger.info("跳过梗概生成（使用已有梗概）")
        elif self._summaries_complete(summaries, start_ch, end_ch):
            self.logger.info(f"章节梗概已完整，范围 {start_ch}-{end_ch} 全部存在")
        else:
            summary_generator = ChapterSummaryGenerator(
                self.config,
                self.ai_role_manager,
                act_plan,
                core_setting,
                overall_outline,
                summaries,
                batch_size=summary_batch_size,
            )
            summaries = self._generate_summaries_by_act(
                summary_generator, act_plan, chapter_range
            )
            self.logger.info(f"章节梗概生成完成，共{len(summaries)}章")

        # Stage 2: 章级骨架生成（滑动窗口多轮模式，注入梗概上下文）
        return self._generate_sliding_window_skeletons(
            core_setting, overall_outline, act_plan, summaries,
            chapter_range, batch_size, conversation_window
        )

    def _generate_sliding_window_skeletons(
        self,
        core_setting: Dict[str, Any],
        overall_outline: Dict[str, Any],
        act_plan: Dict[str, Any],
        summaries: Dict[str, Any],
        chapter_range: Tuple[int, int],
        batch_size: int,
        conversation_window: int,
    ) -> Dict[str, Any]:
        """使用滑动窗口多轮模式生成章级骨架"""
        start_ch, end_ch = chapter_range

        # 从配置获取默认值
        gen_config = self.config.get("generation", {})
        batch_size = batch_size or gen_config.get("skeleton_batch_size", 10)
        conversation_window = conversation_window or gen_config.get("conversation_window", 100)
        summary_window = gen_config.get("summary_window", 100)

        # 加载已存在的骨架
        existing_skeletons = self._load_existing_skeletons()

        # 检查是否已全部完成
        first_missing = self._get_first_missing_chapter(
            existing_skeletons, start_ch, end_ch
        )
        if first_missing > end_ch:
            self.logger.info(f"章级骨架已完整，范围 {start_ch}-{end_ch} 全部存在")
            return existing_skeletons

        self.logger.info(
            f"从第 {first_missing} 章开始生成骨架（滑动窗口={conversation_window}，批次={batch_size}）"
        )

        # 创建滑动窗口生成器（注入梗概上下文）
        generator = SlidingWindowSkeletonGenerator(
            config=self.config,
            ai_role_manager=self.ai_role_manager,
            act_plan=act_plan,
            core_setting=core_setting,
            overall_outline=overall_outline,
            chapter_summaries=summaries,  # 新增：梗概上下文
            output_dir=self.output_dir,
            conversation_window=conversation_window,
            batch_size=batch_size,
            summary_window=summary_window,
        )

        # 生成骨架
        final_skeletons = generator.generate_skeletons(
            chapter_range=(first_missing, end_ch),
            existing_skeletons=existing_skeletons if first_missing > start_ch else None,
        )

        # 合并结果
        existing_skeletons.update(final_skeletons)
        self._save_skeletons(existing_skeletons)

        self.logger.info(f"三阶段大纲生成完成，共{len(existing_skeletons)}章")
        return existing_skeletons

    def _generate_batch_skeletons(
        self,
        core_setting: Dict[str, Any],
        overall_outline: Dict[str, Any],
        act_plan: Dict[str, Any],
        chapter_range: Tuple[int, int],
        batch_size: int,
    ) -> Dict[str, Any]:
        """使用传统批次模式生成章级骨架"""
        self.logger.info("Stage 2: 章级骨架生成（批次增量）")
        existing_skeletons = self._load_existing_skeletons()

        start_ch, end_ch = chapter_range
        context_window = self.config.get("generation", {}).get("skeleton_context_window", 15)

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

            total_chapters = end_ch
            num_acts = len(act_plan.get("幕规划", {}))
            chapters_per_act = total_chapters // max(num_acts, 1)

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
