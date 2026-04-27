"""
大纲生成器
负责基于原始素材生成章节大纲
采用三阶段生成架构：幕级规划 → 章级骨架 → 场景级细化
"""

import json
import re
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

from novel_generator.config.settings import Settings
from novel_generator.utils.multi_model_client import MultiModelClient
from novel_generator.core.ai_roles import AIRoleManager, AIRole
from novel_generator.core.satisfaction_engine import SatisfactionEngine, SatisfactionPoint


class RetryableGenerationError(Exception):
    pass


class ActLevelPlanner:
    """幕级规划器"""

    def __init__(self, config: Dict[str, Any], ai_role_manager: AIRoleManager):
        self.config = config
        self.ai_role_manager = ai_role_manager
        self.satisfaction_engine = SatisfactionEngine(config)
        self.logger = logging.getLogger(__name__)

    def generate_act_plan(
        self,
        core_setting: Dict[str, Any],
        overall_outline: Dict[str, Any],
        num_acts: int = 3,
        total_chapters: int = 150,
    ) -> Dict[str, Any]:
        """
        生成幕级规划

        步骤:
        1. 调用 satisfaction_engine.calculate_pacing() 计算爽点分布
        2. 调用 satisfaction_engine.assign_satisfaction_types() 分配类型
        3. 构建Prompt（使用 04_prompt/prompts/outline_generation.yaml 中的幕级规划模板）
        4. 调用API生成幕规划
        5. 解析响应

        返回: Dict 包含幕规划
        """
        self.logger.info(f"开始生成幕级规划，共{num_acts}幕，{total_chapters}章")

        # 1. 计算爽点分布
        pacing = self.satisfaction_engine.calculate_pacing(total_chapters, num_acts)

        # 2. 分配爽点类型
        satisfaction_points = self.satisfaction_engine.assign_satisfaction_types(
            pacing, core_setting, overall_outline
        )

        # 3. 逐幕生成规划
        act_plan = {"幕规划": {}, "爽点分布": []}

        for act_num in range(1, num_acts + 1):
            prompt = self._build_act_planning_prompt(
                act_num, core_setting, overall_outline, pacing, satisfaction_points
            )

            # 4. 调用API
            response = self._call_ai_api(prompt)

            # 5. 解析响应
            act_data = self._parse_act_response(response, act_num)
            act_plan["幕规划"][f"第{act_num}幕"] = act_data

        # 保存爽点信息
        act_plan["爽点分布"] = [
            {
                "章节": p.chapter,
                "类型": p.sat_type,
                "强度": p.intensity,
                "描述": p.description,
            }
            for p in satisfaction_points
        ]

        self.logger.info(f"幕级规划生成完成，共{num_acts}幕")
        return act_plan

    def _build_act_planning_prompt(
        self,
        act_number: int,
        core_setting: Dict[str, Any],
        overall_outline: Dict[str, Any],
        pacing: Any,
        satisfaction_points: List[SatisfactionPoint],
    ) -> str:
        """构建幕规划Prompt"""
        # 加载模板
        template_path = Path("04_prompt/prompts/outline_generation.yaml")
        template_data = {}
        if template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                template_data = yaml.safe_load(f)

        template_str = template_data.get("templates", {}).get(
            "act_level_planning", {}
        ).get("template", self._get_default_act_template())

        # 提取前幕摘要
        previous_act_summary = ""
        if act_number > 1:
            prev_act_key = f"第{act_number - 1}幕"
            if "幕结构" in overall_outline:
                prev_act_data = overall_outline["幕结构"].get(prev_act_key, {})
                if isinstance(prev_act_data, dict):
                    previous_act_summary = prev_act_data.get("核心剧情", "")

        # 获取本幕的爽点分布
        chapters_per_act = pacing.total_chapters // pacing.num_acts
        act_start = (act_number - 1) * chapters_per_act + 1
        act_end = act_number * chapters_per_act

        act_satisfaction_counts = {"face_slap": 0, "power_up": 0, "revelation": 0, "harvest": 0, "emotional": 0, "status_up": 0}

        for p in satisfaction_points:
            if act_start <= p.chapter <= act_end and p.sat_type in act_satisfaction_counts:
                act_satisfaction_counts[p.sat_type] += 1

        # 构建整体故事文本
        overall_story = self._build_overall_story_text(overall_outline)

        # 格式化核心设定
        core_setting_text = yaml.dump(core_setting, allow_unicode=True, default_flow_style=False)

        return template_str.format(
            act_number=act_number,
            core_setting=core_setting_text,
            overall_story=overall_story,
            previous_act_summary=previous_act_summary,
            face_slap_count=act_satisfaction_counts["face_slap"],
            power_up_count=act_satisfaction_counts["power_up"],
            revelation_count=act_satisfaction_counts["revelation"],
            harvest_count=act_satisfaction_counts["harvest"],
            emotional_count=act_satisfaction_counts["emotional"],
            status_up_count=act_satisfaction_counts["status_up"],
        )

    def _get_default_act_template(self) -> str:
        """默认幕级规划模板"""
        return """
【任务】设计小说第{act_number}幕的整体结构

1. 核心设定：
{core_setting}

2. 整体故事框架：
{overall_story}

3. 前幕摘要（如有）：
{previous_act_summary}

【幕级规划要求】
1. 幕主题：明确本幕的核心主题和主线任务
2. 幕目标：本幕结束时需要达成的主要目标
3. 幕冲突：本幕的核心冲突和对抗
4. 情感基调：本幕的整体情感走向

【爽点战略布局】
请在本幕中规划以下爽点类型（根据实际情况选择）：
- 打脸爽点 (face_slap)：{face_slap_count} 处
- 实力提升 (power_up)：{power_up_count} 处
- 真相揭露 (revelation)：{revelation_count} 处
- 收获宝物 (harvest)：{harvest_count} 处
- 情感升华 (emotional)：{emotional_count} 处
- 地位提升 (status_up)：{status_up_count} 处

【输出格式】
请以YAML格式输出：
```yaml
主题: "幕主题"
目标: "幕目标"
核心冲突: "核心冲突描述"
情感基调: "情感基调"
预估章数: 数字
爽点布局:
  - 类型: "爽点类型"
    章节: "预计所在章节"
    描述: "爽点简要描述"
关键转折点:
  - "转折点描述"
章节划分:
  - "本章任务"
```
"""

    def _build_overall_story_text(self, overall_outline: Dict[str, Any]) -> str:
        """构建整体故事文本"""
        parts = []

        if "幕结构" in overall_outline:
            for key, value in overall_outline["幕结构"].items():
                if isinstance(value, dict):
                    plot = value.get("剧情逻辑脉络", value.get("核心剧情", ""))
                    parts.append(f"{key}: {plot}")
                else:
                    parts.append(f"{key}: {value}")
        else:
            for key, value in overall_outline.items():
                parts.append(f"{key}: {value}")

        return "\n".join(parts)

    def _call_ai_api(self, prompt: str) -> str:
        """调用AI API"""
        try:
            response = self.ai_role_manager.chat_completion(
                role=AIRole.GENERATOR,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的小说结构规划师，擅长设计幕级故事架构。",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            return response or ""
        except Exception as e:
            self.logger.error(f"AI API调用失败: {e}")
            raise RetryableGenerationError(f"AI API调用失败: {e}")

    def _parse_act_response(self, response: str, act_number: int) -> Dict[str, Any]:
        """解析幕规划响应"""
        try:
            cleaned = self._clean_markdown_response(response)
            data = yaml.safe_load(cleaned)

            if isinstance(data, dict):
                return data
            else:
                return {"原始响应": response[:500]}
        except Exception as e:
            self.logger.warning(f"解析幕规划响应失败: {e}")
            return {"原始响应": response[:500]}

    def _clean_markdown_response(self, response: str) -> str:
        """清理Markdown格式的响应"""
        lines = response.split("\n")
        cleaned_lines = []

        for line in lines:
            if line.strip() in ["```yaml", "```", "```yml"]:
                continue
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)


class ChapterSkeletonGenerator:
    """章级骨架生成器"""

    def __init__(self, config: Dict[str, Any], ai_role_manager: AIRoleManager, act_plan: Dict[str, Any]):
        self.config = config
        self.ai_role_manager = ai_role_manager
        self.act_plan = act_plan
        self.logger = logging.getLogger(__name__)

    def generate_chapter_skeletons(
        self, act_number: int, chapter_range: Tuple[int, int]
    ) -> Dict[str, Any]:
        """
        为指定幕生成章级骨架

        步骤:
        1. 获取该幕的爽点布局
        2. 构建Prompt（使用 yaml 文件中的章级骨架模板）
        3. 调用API批量生成章节骨架
        4. 解析响应

        返回: Dict {章节号: 骨架内容}
        """
        self.logger.info(f"开始生成第{act_number}幕的章级骨架，章节范围: {chapter_range}")

        skeletons = {}
        act_data = self.act_plan.get("幕规划", {}).get(f"第{act_number}幕", {})
        satisfaction_layout = self.act_plan.get("爽点分布", [])

        # 批量生成或逐章生成
        start_chapter, end_chapter = chapter_range
        batch_size = 5  # 每批生成5章

        for batch_start in range(start_chapter, end_chapter + 1, batch_size):
            batch_end = min(batch_start + batch_size - 1, end_chapter)

            prompt = self._build_skeleton_prompt(
                act_number, act_data, (batch_start, batch_end), satisfaction_layout
            )

            response = self._call_ai_api(prompt)
            batch_skeletons = self._parse_skeleton_response(response)
            skeletons.update(batch_skeletons)

        self.logger.info(f"章级骨架生成完成，共{len(skeletons)}章")
        return skeletons

    def _build_skeleton_prompt(
        self,
        act_number: int,
        act_data: Dict[str, Any],
        chapter_range: Tuple[int, int],
        satisfaction_layout: List[Dict[str, Any]],
    ) -> str:
        """构建章骨架Prompt"""
        # 加载模板
        template_path = Path("04_prompt/prompts/outline_generation.yaml")
        template_data = {}
        if template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                template_data = yaml.safe_load(f)

        template_str = template_data.get("templates", {}).get(
            "chapter_skeleton", {}
        ).get("template", self._get_default_skeleton_template())

        batch_start, batch_end = chapter_range
        prompts = []

        for chapter_num in range(batch_start, batch_end + 1):
            # 检查是否是爽点章节
            sat_info = None
            for sat in satisfaction_layout:
                if sat.get("章节") == chapter_num:
                    sat_info = sat
                    break

            # 计算幕进度
            chapters_in_act = act_data.get("预估章数", 50)
            chapter_in_act = chapter_num - (act_number - 1) * chapters_in_act
            act_progress = int((chapter_in_act / chapters_in_act) * 100) if chapters_in_act > 0 else 50

            # 确定约束标记
            continuity_required = chapter_num > batch_start
            narrative_line = "主线" if chapter_num % 5 != 0 else "新线"  # 每5章一个支线
            satisfaction_type = sat_info.get("类型", "") if sat_info else None
            word_count_target = 3000 if sat_info else 2000

            act_info = yaml.dump(act_data, allow_unicode=True, default_flow_style=False)

            prompt = template_str.format(
                chapter_num=chapter_num,
                act_info=act_info,
                core_setting="参见整体设定",
                previous_chapter_summary="参见前章",
                act_progress=act_progress,
                continuity_required=str(continuity_required).lower(),
                narrative_line=narrative_line,
                satisfaction_type=satisfaction_type if satisfaction_type else "",
                word_count_target=word_count_target,
            )
            prompts.append(prompt)

        return "\n\n".join(prompts)

    def _get_default_skeleton_template(self) -> str:
        """默认章级骨架模板"""
        return """
【任务】生成第{chapter_num}章的详细骨架

1. 所属幕信息：
{act_info}

2. 幕进度：{act_progress}%

【本章约束标记】
- continuity_required: {continuity_required}
- narrative_line: {narrative_line}
- satisfaction_type: {satisfaction_type}
- word_count_target: {word_count_target}

【输出格式】
请以YAML格式输出：
```yaml
第{chapter_num}章:
  标题: "章节标题"
  字数目标: {word_count_target}
  约束标记:
    continuity_required: {continuity_required}
    narrative_line: "{narrative_line}"
    satisfaction_type: "{satisfaction_type}"
  核心事件: "核心事件描述"
  人物行动:
    主角: "主角行动"
    关键配角: "配角行动"
  场景列表:
    - 场景1:
        地点: "场景地点"
        内容: "场景内容"
        字数: 预估字数
  情绪曲线: [铺垫, 积累, 爆发, 回落]
  伏笔处理:
    埋设: ["伏笔1"]
    回收: ["伏笔2"]
  结尾卡点: "结尾悬念"
```
"""

    def _call_ai_api(self, prompt: str) -> str:
        """调用AI API"""
        try:
            response = self.ai_role_manager.chat_completion(
                role=AIRole.GENERATOR,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的小说章节规划师，擅长设计章节骨架结构。",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            return response or ""
        except Exception as e:
            self.logger.error(f"AI API调用失败: {e}")
            raise RetryableGenerationError(f"AI API调用失败: {e}")

    def _parse_skeleton_response(self, response: str) -> Dict[str, Any]:
        """解析章骨架响应"""
        try:
            cleaned = self._clean_markdown_response(response)
            data = yaml.safe_load(cleaned)

            if isinstance(data, dict):
                return data
            else:
                return {}
        except Exception as e:
            self.logger.warning(f"解析章骨架响应失败: {e}")
            return {}

    def _clean_markdown_response(self, response: str) -> str:
        """清理Markdown格式的响应"""
        lines = response.split("\n")
        cleaned_lines = []

        for line in lines:
            if line.strip() in ["```yaml", "```", "```yml"]:
                continue
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)


class SceneLevelDetailer:
    """场景级细化器"""

    SATISFACTION_TEMPLATES = {
        "face_slap": "04_prompt/prompts/satisfaction_prompts/face_slap.yaml",
        "power_up": "04_prompt/prompts/satisfaction_prompts/power_up.yaml",
    }

    def __init__(self, config: Dict[str, Any], ai_role_manager: AIRoleManager):
        self.config = config
        self.ai_role_manager = ai_role_manager
        self.logger = logging.getLogger(__name__)

    def generate_scene_detail(
        self,
        chapter_num: int,
        chapter_skeleton: Dict[str, Any],
        previous_context: str = "",
        next_context: str = "",
    ) -> Dict[str, Any]:
        """
        将章骨架细化为场景级剧本

        判断:
        - 如果是爽点章节（is_satisfaction=true）: 调用 _generate_satisfaction_scene_detail()
        - 否则: 调用 _generate_normal_scene_detail()

        返回: Dict 场景级剧本
        """
        self.logger.info(f"开始细化第{chapter_num}章的场景")

        # 判断是否是爽点章节
        constraint_marks = chapter_skeleton.get("约束标记", {})
        is_satisfaction = bool(constraint_marks.get("satisfaction_type"))

        if is_satisfaction:
            detail = self._generate_satisfaction_scene_detail(
                chapter_num, chapter_skeleton, previous_context, next_context
            )
        else:
            detail = self._generate_normal_scene_detail(
                chapter_num, chapter_skeleton, previous_context, next_context
            )

        self.logger.info(f"第{chapter_num}章场景细化完成")
        return detail

    def _generate_satisfaction_scene_detail(
        self,
        chapter_num: int,
        skeleton: Dict[str, Any],
        prev_context: str,
        next_context: str,
    ) -> Dict[str, Any]:
        """
        生成爽点章节的场景级设计

        使用 04_prompt/prompts/satisfaction_prompts/ 中的专用模板
        输出必须包含4个场景：铺垫→执行→收益→钩子
        """
        sat_type = skeleton.get("约束标记", {}).get("satisfaction_type", "face_slap")

        # 加载爽点模板
        template_path = Path(self.SATISFACTION_TEMPLATES.get(sat_type, ""))
        template_data = {}
        if template_path and template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                template_data = yaml.safe_load(f)

        template_str = template_data.get("template", self._get_default_satisfaction_template(sat_type))

        # 构建场景列表（4场景结构）
        scenes = [
            {
                "场景ID": f"S{chapter_num}-1",
                "类型": "铺垫",
                "地点": skeleton.get("场景列表", [{}])[0].get("地点", "待定"),
                "节拍设计": {
                    "钩子": "设置悬念或冲突",
                    "上升动作": "情节推进",
                    "转折点": "关键变化",
                    "落点": "场景收束",
                },
                "对白要点": [],
                "感官细节": {},
            },
            {
                "场景ID": f"S{chapter_num}-2",
                "类型": "执行",
                "地点": skeleton.get("场景列表", [{}, {}])[1].get("地点", "待定") if len(skeleton.get("场景列表", [])) > 1 else "待定",
                "节拍设计": {
                    "钩子": "爽点触发",
                    "上升动作": "爽点展开",
                    "转折点": "高潮时刻",
                    "落点": "爽点达成",
                },
                "对白要点": [],
                "感官细节": {},
            },
            {
                "场景ID": f"S{chapter_num}-3",
                "类型": "收益",
                "地点": skeleton.get("场景列表", [{}, {}, {}])[2].get("地点", "待定") if len(skeleton.get("场景列表", [])) > 2 else "待定",
                "节拍设计": {
                    "钩子": "收益展现",
                    "上升动作": "收益累积",
                    "转折点": "认知转变",
                    "落点": "满足达成",
                },
                "对白要点": [],
                "感官细节": {},
            },
            {
                "场景ID": f"S{chapter_num}-4",
                "类型": "钩子",
                "地点": skeleton.get("场景列表", [{}, {}, {}, {}])[3].get("地点", "待定") if len(skeleton.get("场景列表", [])) > 3 else "待定",
                "节拍设计": {
                    "钩子": "悬念设置",
                    "上升动作": "暗示发展",
                    "转折点": "新线索出现",
                    "落点": "章节收束",
                },
                "对白要点": [],
                "感官细节": {},
            },
        ]

        return {
            "标题": skeleton.get("标题", f"第{chapter_num}章"),
            "总字数": skeleton.get("字数目标", 3000),
            "章节功能": "satisfaction",
            "爽点标记": {
                "is_satisfaction": True,
                "type": sat_type,
                "intensity": 7,
            },
            "场景列表": scenes,
        }

    def _get_default_satisfaction_template(self, sat_type: str) -> str:
        """获取默认爽点模板"""
        if sat_type == "face_slap":
            return """
【任务】撰写打脸爽点场景

1. 场景背景：
{scene_background}

【打脸爽点4场景结构】
## 场景1：压迫 - Setup
## 场景2：爆发 - Trigger
## 场景3：反转 - Climax
## 场景4：收束 - Resolution

请输出4场景正文。
"""
        else:
            return """
【任务】撰写爽点场景

【4场景结构】
## 场景1：铺垫
## 场景2：执行
## 场景3：收益
## 场景4：钩子

请输出4场景正文。
"""

    def _generate_normal_scene_detail(
        self,
        chapter_num: int,
        skeleton: Dict[str, Any],
        prev_context: str,
        next_context: str,
    ) -> Dict[str, Any]:
        """生成普通章节的场景级设计"""
        # 加载模板
        template_path = Path("04_prompt/prompts/outline_generation.yaml")
        template_data = {}
        if template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                template_data = yaml.safe_load(f)

        template_str = template_data.get("templates", {}).get(
            "scene_refinement", {}
        ).get("template", self._get_default_scene_template())

        # 构建Prompt
        skeleton_yaml = yaml.dump(skeleton, allow_unicode=True, default_flow_style=False)

        prompt = template_str.format(
            chapter_num=chapter_num,
            chapter_skeleton=skeleton_yaml,
            character_context=prev_context,
            foreshadowing_context="参见伏笔追踪",
            emotional_context="参见情感弧线",
        )

        # 调用API生成详细场景
        try:
            response = self.ai_role_manager.chat_completion(
                role=AIRole.GENERATOR,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的小说场景设计师，擅长细化场景细节。",
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            # 解析响应
            detail = self._parse_scene_response(response, chapter_num, skeleton)
            return detail

        except Exception as e:
            self.logger.error(f"生成普通场景失败: {e}")
            # 返回基础结构
            return self._build_fallback_scene_detail(chapter_num, skeleton)

    def _get_default_scene_template(self) -> str:
        """默认场景细化模板"""
        return """
【任务】细化第{chapter_num}章的场景内容

1. 章级骨架：
{chapter_skeleton}

【场景细化要求】
1. 每个场景拆分为具体的情节点
2. 标注人物情感变化节点
3. 标注感官描写重点
4. 标注对话要点
5. 标注动作戏细节（如有）

【输出格式】
请以YAML格式输出：
```yaml
场景细化:
  章节: {chapter_num}
  场景详情:
    - 场景编号: 1
      地点: "地点"
      氛围: "场景氛围"
      情节点:
        - 点1:
            内容: "情节内容"
            人物情感: "情感状态"
            感官重点: "感官描写"
            字数: 数字
```
"""

    def _parse_scene_response(
        self, response: str, chapter_num: int, skeleton: Dict[str, Any]
    ) -> Dict[str, Any]:
        """解析场景响应"""
        try:
            cleaned = self._clean_markdown_response(response)
            data = yaml.safe_load(cleaned)

            if isinstance(data, dict):
                # 提取场景详情
                scene_detail = data.get("场景细化", data)

                # 构建标准输出格式
                scenes = []
                scene_list = scene_detail.get("场景详情", [])

                for i, scene_data in enumerate(scene_list, 1):
                    scene = {
                        "场景ID": f"S{chapter_num}-{i}",
                        "类型": scene_data.get("类型", "叙事"),
                        "地点": scene_data.get("地点", skeleton.get("场景列表", [{}])[i-1].get("地点", "待定") if i <= len(skeleton.get("场景列表", [])) else "待定"),
                        "节拍设计": {
                            "钩子": scene_data.get("情节点", [{}])[0].get("内容", "场景开始"),
                            "上升动作": scene_data.get("情节点", [{}, {}])[1].get("内容", "情节发展") if len(scene_data.get("情节点", [])) > 1 else "情节发展",
                            "转折点": scene_data.get("情节点", [{}, {}, {}])[2].get("内容", "关键转折") if len(scene_data.get("情节点", [])) > 2 else "关键转折",
                            "落点": scene_data.get("情节点", [{}])[-1].get("内容", "场景收束"),
                        },
                        "对白要点": scene_data.get("关键对话", []),
                        "感官细节": scene_data.get("感官细节", {}),
                    }
                    scenes.append(scene)

                return {
                    "标题": skeleton.get("标题", f"第{chapter_num}章"),
                    "总字数": skeleton.get("字数目标", 2000),
                    "章节功能": "normal",
                    "爽点标记": {"is_satisfaction": False},
                    "场景列表": scenes,
                }

            else:
                return self._build_fallback_scene_detail(chapter_num, skeleton)

        except Exception as e:
            self.logger.warning(f"解析场景响应失败: {e}")
            return self._build_fallback_scene_detail(chapter_num, skeleton)

    def _build_fallback_scene_detail(self, chapter_num: int, skeleton: Dict[str, Any]) -> Dict[str, Any]:
        """构建回退场景详情"""
        scenes = []
        for i, scene_data in enumerate(skeleton.get("场景列表", []), 1):
            scene = {
                "场景ID": f"S{chapter_num}-{i}",
                "类型": "叙事",
                "地点": scene_data.get("地点", "待定"),
                "节拍设计": {
                    "钩子": "场景开始",
                    "上升动作": "情节发展",
                    "转折点": "关键转折",
                    "落点": "场景收束",
                },
                "对白要点": [],
                "感官细节": {},
            }
            scenes.append(scene)

        return {
            "标题": skeleton.get("标题", f"第{chapter_num}章"),
            "总字数": skeleton.get("字数目标", 2000),
            "章节功能": "normal",
            "爽点标记": {"is_satisfaction": False},
            "场景列表": scenes,
        }

    def _clean_markdown_response(self, response: str) -> str:
        """清理Markdown格式的响应"""
        lines = response.split("\n")
        cleaned_lines = []

        for line in lines:
            if line.strip() in ["```yaml", "```", "```yml"]:
                continue
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)


class OutlineGenerator:
    """大纲生成器（整合三阶段）"""

    def __init__(
        self, config: Dict[str, Any], multi_model_client: MultiModelClient = None
    ):
        self.config = config
        self.settings = Settings(config)
        self.logger = logging.getLogger(__name__)
        if multi_model_client:
            self.multi_model_client = multi_model_client
        else:
            self.multi_model_client = MultiModelClient(config)

        self.ai_role_manager = AIRoleManager(config, self.multi_model_client)

    def generate_outline_v2(
        self,
        core_setting: Dict[str, Any],
        overall_outline: Dict[str, Any],
        num_acts: int = 3,
        chapter_range: Optional[Tuple[int, int]] = None,
    ) -> Dict[str, Any]:
        """
        新版大纲生成（三阶段）

        流程:
        1. Stage 1: 幕级规划
        2. Stage 2: 章级骨架（批量）
        3. Stage 3: 场景级细化（按需）

        返回: Dict 完整大纲（场景级）
        """
        self.logger.info("开始三阶段大纲生成")

        # 提取总章节数
        total_chapters = self.extract_total_chapters(overall_outline)
        if chapter_range is None:
            chapter_range = (1, total_chapters)

        # Stage 1: 幕级规划
        self.logger.info("Stage 1: 幕级规划")
        act_planner = ActLevelPlanner(self.config, self.ai_role_manager)
        act_plan = act_planner.generate_act_plan(
            core_setting, overall_outline, num_acts, total_chapters
        )

        # Stage 2: 章级骨架（批量）
        self.logger.info("Stage 2: 章级骨架生成")
        skeleton_generator = ChapterSkeletonGenerator(
            self.config, self.ai_role_manager, act_plan
        )

        all_skeletons = {}
        chapters_per_act = total_chapters // num_acts

        for act_num in range(1, num_acts + 1):
            act_start = (act_num - 1) * chapters_per_act + 1
            act_end = min(act_num * chapters_per_act, total_chapters)

            # 只生成指定范围的章节
            if act_start > chapter_range[1] or act_end < chapter_range[0]:
                continue

            actual_start = max(act_start, chapter_range[0])
            actual_end = min(act_end, chapter_range[1])

            skeletons = skeleton_generator.generate_chapter_skeletons(
                act_num, (actual_start, actual_end)
            )
            all_skeletons.update(skeletons)

        # Stage 3: 场景级细化（按需）
        self.logger.info("Stage 3: 场景级细化")
        scene_detailer = SceneLevelDetailer(self.config, self.ai_role_manager)

        final_outline = {}
        sorted_chapters = sorted(all_skeletons.keys(), key=lambda x: self._extract_chapter_number(x))

        for chapter_key in sorted_chapters:
            skeleton = all_skeletons[chapter_key]
            chapter_num = self._extract_chapter_number(chapter_key)

            # 获取前后上下文
            prev_context = ""
            next_context = ""
            if chapter_num > chapter_range[0]:
                prev_chapter = f"第{chapter_num - 1}章"
                if prev_chapter in final_outline:
                    prev_context = final_outline[prev_chapter].get("标题", "")

            detail = scene_detailer.generate_scene_detail(
                chapter_num, skeleton, prev_context, next_context
            )
            final_outline[chapter_key] = detail

        self.logger.info(f"三阶段大纲生成完成，共{len(final_outline)}章")
        return final_outline

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

    def extract_total_chapters(self, overall_outline: Dict[str, Any]) -> int:
        try:
            total_chapters = 0
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

            outline_data = overall_outline

            if "幕结构" in overall_outline:
                outline_data = overall_outline["幕结构"]

            while True:
                act_key_numeric = f"第{act_number}幕"
                act_content = outline_data.get(act_key_numeric, "")

                if not act_content and act_number <= len(chinese_numbers):
                    act_key_chinese = f"第{chinese_numbers[act_number - 1]}幕"
                    act_content = outline_data.get(act_key_chinese, "")

                if act_content:
                    if isinstance(act_content, dict):
                        chapter_range = act_content.get("章节范围", "")
                        search_text = str(chapter_range)
                    else:
                        search_text = str(act_content)

                    chapter_patterns = [
                        r"第\s*(\d+)\s*-\s*(\d+)\s*章",
                        r"第\s*(\d+)\s*章\s*到\s*第\s*(\d+)\s*章",
                        r"(\d+)\s*-\s*(\d+)\s*章",
                        r"第\s*(\d+)\s*章",
                    ]

                    max_chapter_in_act = 0
                    for pattern in chapter_patterns:
                        matches = re.findall(pattern, search_text)
                        for match in matches:
                            if len(match) == 2:
                                end_chapter = int(match[1])
                                max_chapter_in_act = max(
                                    max_chapter_in_act, end_chapter
                                )
                            else:
                                chapter_num = int(match[0])
                                max_chapter_in_act = max(
                                    max_chapter_in_act, chapter_num
                                )

                    if max_chapter_in_act > 0:
                        total_chapters = max(total_chapters, max_chapter_in_act)

                    act_number += 1
                else:
                    break

            if total_chapters == 0:
                self.logger.warning("无法从整体大纲中提取章节数量，使用默认值150")
                return 150

            self.logger.info(f"从整体大纲中提取到总章节数量: {total_chapters}")
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
            # 跳过代码块开始和结束标记
            if line.strip() in ["```yaml", "```", "```yml"]:
                continue
            # 跳过空行（如果它们在代码块标记附近）
            elif (
                line.strip() == "" and cleaned_lines and cleaned_lines[-1].strip() == ""
            ):
                continue
            else:
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
