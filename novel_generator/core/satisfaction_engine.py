"""
爽点引擎
用于设计和规划小说爽点的分布、类型和情感曲线
"""

import yaml
import random
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging


class SatisfactionType(Enum):
    """爽点类型枚举"""
    FACE_SLAP = "face_slap"           # 打脸
    POWER_UP = "power_up"             # 实力提升
    REVELATION = "revelation"         # 揭秘
    HARVEST = "harvest"               # 收获
    EMOTIONAL = "emotional"           # 情感
    STATUS_UP = "status_up"           # 地位跃升


# 爽点类型定义
SATISFACTION_TYPES = {
    SatisfactionType.FACE_SLAP.value: {
        "name": "打脸",
        "description": "反派嚣张后的反转打脸，主角展现实力震惊众人",
        "elements": ["反派嚣张", "主角隐忍", "反转触发", "实力展现", "震惊反应", "后续收益"],
        "emotional_curve": [
            ("压抑", 3),
            ("期待", 5),
            ("爆发", 8),
            ("满足", 7)
        ],
        "suitable_worlds": ["cultivation", "system", "politics", "general"],
        "intensity_range": (6, 10),
    },
    SatisfactionType.POWER_UP.value: {
        "name": "实力提升",
        "description": "主角突破瓶颈或获得强大能力，实力飞跃",
        "elements": ["困境/机缘", "努力/顿悟", "突破/获得", "展现实力", "地位提升"],
        "emotional_curve": [
            ("期待", 4),
            ("紧张", 6),
            ("突破", 8),
            ("狂喜", 9),
            ("稳定", 7)
        ],
        "suitable_worlds": ["cultivation", "system"],
        "intensity_range": (7, 10),
    },
    SatisfactionType.REVELATION.value: {
        "name": "揭秘",
        "description": "悬念揭晓，真相大白，带来恍然大悟的爽感",
        "elements": ["悬念累积", "线索汇集", "真相大白", "连锁反应"],
        "emotional_curve": [
            ("好奇", 5),
            ("猜测", 6),
            ("震惊", 8),
            ("恍然大悟", 7)
        ],
        "suitable_worlds": ["cultivation", "system", "politics", "general"],
        "intensity_range": (6, 9),
    },
    SatisfactionType.HARVEST.value: {
        "name": "收获",
        "description": "主角获得珍稀宝物、资源或达成目标",
        "elements": ["发现目标", "克服困难", "成功获得", "意外之喜"],
        "emotional_curve": [
            ("渴望", 4),
            ("努力", 5),
            ("获得", 7),
            ("惊喜", 8)
        ],
        "suitable_worlds": ["cultivation", "system", "general"],
        "intensity_range": (5, 8),
    },
    SatisfactionType.EMOTIONAL.value: {
        "name": "情感",
        "description": "情感关系的突破或确认，带来心灵满足",
        "elements": ["情感积累", "关系突破", "情感确认", "温暖满足"],
        "emotional_curve": [
            ("温暖", 5),
            ("感动", 7),
            ("共鸣", 8),
            ("满足", 7)
        ],
        "suitable_worlds": ["general", "politics", "cultivation"],
        "intensity_range": (5, 8),
    },
    SatisfactionType.STATUS_UP.value: {
        "name": "地位跃升",
        "description": "主角社会地位、身份认同的跃升",
        "elements": ["被轻视", "展现实力", "被认可", "进入新层级"],
        "emotional_curve": [
            ("不甘", 4),
            ("努力", 5),
            ("震惊", 7),
            ("荣耀", 8)
        ],
        "suitable_worlds": ["cultivation", "system", "politics"],
        "intensity_range": (6, 9),
    },
}


@dataclass
class SatisfactionPoint:
    """爽点设计数据类"""
    chapter: int
    sat_type: str
    intensity: int
    name: str
    description: str
    elements: List[str]
    emotional_curve: List[Tuple[str, int]]
    hooks: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    aftermath: List[str] = field(default_factory=list)


@dataclass
class PacingPlan:
    """爽点分布计划"""
    total_chapters: int
    num_acts: int
    major_climaxes: List[SatisfactionPoint]   # 幕末大爆点，强度9-10
    medium_peaks: List[SatisfactionPoint]     # 幕中中爆点，强度7-8
    minor_satisfactions: List[SatisfactionPoint]  # 小爽点，强度5-6
    low_points: List[Tuple[int, str]]         # 低谷期，情绪3-4


class SatisfactionEngine:
    """爽点引擎，用于设计和规划小说爽点"""

    # 世界观关键词映射
    WORLD_KEYWORDS = {
        "cultivation": ["修仙", "境界", "灵气", "功法", "宗门", "渡劫", "飞升",
                       "筑基", "金丹", "元婴", "化神", "大乘", "散仙"],
        "system": ["系统", "任务", "奖励", "属性", "升级", "技能", "商城",
                  "签到", "抽奖", "面板", "数据化"],
        "politics": ["朝廷", "官位", "权谋", "政治", "派系", "斗争", "谋略",
                    "科举", "皇帝", "宰相", "权臣", "党争"],
    }

    # 钩子模板
    HOOK_TEMPLATES = {
        "face_slap": [
            "{antagonist}当众嘲讽{protagonist}无能，却不知...",
            "所有人都认为{protagonist}必败，然而...",
            "{antagonist}设下陷阱，却不知{protagonist}早已洞悉...",
            "昔日被{antagonist}踩在脚下的{protagonist}，如今...",
        ],
        "power_up": [
            "在生死关头，{protagonist}终于突破了{current_realm}的桎梏...",
            "那颗沉寂已久的{treasure_name}突然绽放出耀眼光芒...",
            "多年苦修，今日终于水到渠成...",
            "面对绝境，{protagonist}领悟了{technique_name}的真谛...",
        ],
        "revelation": [
            "原来{mystery_person}的真实身份竟然是...",
            "当{clue_item}拼合完整的那一刻，真相终于浮出水面...",
            "所有人都被表象迷惑，唯独{protagonist}看穿了...",
            "那个困扰已久的谜团，答案竟藏在{hidden_place}...",
        ],
        "harvest": [
            "历经千辛万苦，{protagonist}终于获得了{treasure_name}...",
            "当{protagonist}打开{container}的瞬间，{item}的光芒照亮了...",
            "意外的发现让{protagonist}获得了意想不到的{reward}...",
            "这次探索的收获远超预期，尤其是{special_item}...",
        ],
        "emotional": [
            "在{emotional_scene}，{protagonist}终于向{love_interest}表达了心意...",
            "多年的误解在这一刻烟消云散，{protagonist}和{character}相视而笑...",
            "当{event}发生时，{protagonist}第一次感受到了{emotion}...",
            "那份藏在心底的情感，终于在{special_moment}得到了回应...",
        ],
        "status_up": [
            "当{authority}宣布{protagonist}的新身份时，全场哗然...",
            "从{old_status}到{new_status}，{protagonist}完成了惊人的蜕变...",
            "曾经轻视{protagonist}的{mocking_group}，此刻只能仰望...",
            "这{ceremony_name}标志着{protagonist}正式进入了{new_level}...",
        ],
    }

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.pacing_plan: Optional[PacingPlan] = None
        self.satisfaction_points: List[SatisfactionPoint] = []
        self.world_type: str = "general"

    def calculate_pacing(self, total_chapters: int, num_acts: int) -> PacingPlan:
        """
        计算爽点分布

        Args:
            total_chapters: 总章节数
            num_acts: 幕数

        Returns:
            PacingPlan: 爽点分布计划
        """
        chapters_per_act = total_chapters // num_acts

        major_climaxes = []
        medium_peaks = []
        minor_satisfactions = []
        low_points = []

        # 幕末大爆点：强度9-10
        for act in range(1, num_acts + 1):
            climax_chapter = act * chapters_per_act
            if climax_chapter <= total_chapters:
                major_climaxes.append(
                    SatisfactionPoint(
                        chapter=climax_chapter,
                        sat_type="",
                        intensity=random.randint(9, 10),
                        name=f"第{act}幕高潮",
                        description="幕末大爆点",
                        elements=[],
                        emotional_curve=[],
                    )
                )

        # 幕中中爆点：强度7-8
        for act in range(1, num_acts + 1):
            mid_chapter = (act - 1) * chapters_per_act + chapters_per_act // 2
            if mid_chapter <= total_chapters and mid_chapter not in [m.chapter for m in major_climaxes]:
                medium_peaks.append(
                    SatisfactionPoint(
                        chapter=mid_chapter,
                        sat_type="",
                        intensity=random.randint(7, 8),
                        name=f"第{act}幕中点",
                        description="幕中中爆点",
                        elements=[],
                        emotional_curve=[],
                    )
                )

        # 小爽点：每3-4章一个，强度5-6
        for chapter in range(3, total_chapters + 1, random.randint(3, 4)):
            if chapter not in [m.chapter for m in major_climaxes] and \
               chapter not in [m.chapter for m in medium_peaks]:
                minor_satisfactions.append(
                    SatisfactionPoint(
                        chapter=chapter,
                        sat_type="",
                        intensity=random.randint(5, 6),
                        name=f"小爽点",
                        description="常规爽点",
                        elements=[],
                        emotional_curve=[],
                    )
                )

        # 低谷期：情绪3-4，用于期待感
        for chapter in range(2, total_chapters + 1, 5):
            if chapter not in [m.chapter for m in major_climaxes] and \
               chapter not in [m.chapter for m in medium_peaks] and \
               chapter not in [m.chapter for m in minor_satisfactions]:
                low_points.append((chapter, "情绪铺垫期"))

        self.pacing_plan = PacingPlan(
            total_chapters=total_chapters,
            num_acts=num_acts,
            major_climaxes=major_climaxes,
            medium_peaks=medium_peaks,
            minor_satisfactions=minor_satisfactions,
            low_points=low_points,
        )

        self.logger.info(
            f"爽点分布计算完成: {len(major_climaxes)}个大爆点, "
            f"{len(medium_peaks)}个中爆点, {len(minor_satisfactions)}个小爽点, "
            f"{len(low_points)}个低谷期"
        )

        return self.pacing_plan

    def assign_satisfaction_types(
        self,
        pacing: PacingPlan,
        core_setting: Dict[str, Any],
        overall_outline: Dict[str, Any],
    ) -> List[SatisfactionPoint]:
        """
        根据世界观和剧情分配爽点类型

        Args:
            pacing: 爽点分布计划
            core_setting: 世界观设定
            overall_outline: 整体大纲

        Returns:
            List[SatisfactionPoint]: 分配好类型的爽点列表
        """
        self.world_type = self._detect_world_type(core_setting)
        self.satisfaction_points = []

        # 获取适合当前世界观的爽点类型
        suitable_types = self._get_suitable_types(self.world_type)

        # 为每个爽点分配类型
        all_points = (
            pacing.major_climaxes +
            pacing.medium_peaks +
            pacing.minor_satisfactions
        )
        all_points.sort(key=lambda x: x.chapter)

        for point in all_points:
            sat_type = random.choice(suitable_types)
            sat_design = self._design_satisfaction(
                sat_type, point.chapter, core_setting, overall_outline
            )
            sat_design.intensity = point.intensity
            self.satisfaction_points.append(sat_design)

        self.logger.info(f"已为{len(self.satisfaction_points)}个爽点分配类型")
        return self.satisfaction_points

    def generate_satisfaction_prompt(
        self,
        chapter_num: int,
        sat_design: SatisfactionPoint,
        context: Dict[str, Any],
    ) -> str:
        """
        生成爽点设计Prompt片段

        Args:
            chapter_num: 章节号
            sat_design: 爽点设计
            context: 上下文信息

        Returns:
            str: Prompt片段
        """
        if not sat_design:
            return ""

        type_info = SATISFACTION_TYPES.get(sat_design.sat_type, {})

        prompt_parts = [
            f"=== 本章爽点设计 ===",
            f"类型: {type_info.get('name', sat_design.sat_type)} (强度{sat_design.intensity}/10)",
            f"描述: {sat_design.description}",
            "",
            "必备元素:",
        ]

        for i, element in enumerate(sat_design.elements, 1):
            prompt_parts.append(f"  {i}. {element}")

        prompt_parts.extend([
            "",
            "情感曲线:",
        ])

        for emotion, intensity in sat_design.emotional_curve:
            bar = "█" * intensity + "░" * (10 - intensity)
            prompt_parts.append(f"  {emotion}: {bar} ({intensity}/10)")

        if sat_design.hooks:
            prompt_parts.extend([
                "",
                "建议钩子:",
            ])
            for hook in sat_design.hooks:
                prompt_parts.append(f"  - {hook}")

        if sat_design.prerequisites:
            prompt_parts.extend([
                "",
                "前置铺垫:",
            ])
            for prereq in sat_design.prerequisites:
                prompt_parts.append(f"  - {prereq}")

        if sat_design.aftermath:
            prompt_parts.extend([
                "",
                "后续影响:",
            ])
            for effect in sat_design.aftermath:
                prompt_parts.append(f"  - {effect}")

        return "\n".join(prompt_parts)

    def _detect_world_type(self, core_setting: Dict[str, Any]) -> str:
        """
        检测世界观类型

        Args:
            core_setting: 世界观设定

        Returns:
            str: 世界观类型 (cultivation/system/politics/general)
        """
        setting_text = str(core_setting)
        keyword_counts = {}

        for world_type, keywords in self.WORLD_KEYWORDS.items():
            count = sum(setting_text.count(kw) for kw in keywords)
            keyword_counts[world_type] = count

        if keyword_counts:
            max_type = max(keyword_counts.keys(), key=lambda k: keyword_counts[k])
            if keyword_counts[max_type] > 0:
                return max_type

        return "general"

    def _get_suitable_types(self, world_type: str) -> List[str]:
        """获取适合当前世界观的爽点类型"""
        suitable = []
        for sat_type, config in SATISFACTION_TYPES.items():
            if world_type in config.get("suitable_worlds", []) or "general" in config.get("suitable_worlds", []):
                suitable.append(sat_type)
        return suitable if suitable else list(SATISFACTION_TYPES.keys())

    def _design_satisfaction(
        self,
        sat_type: str,
        chapter: int,
        core_setting: Dict[str, Any],
        overall_outline: Dict[str, Any],
    ) -> SatisfactionPoint:
        """
        生成详细爽点设计

        Args:
            sat_type: 爽点类型
            chapter: 章节号
            core_setting: 世界观设定
            overall_outline: 整体大纲

        Returns:
            SatisfactionPoint: 爽点设计对象
        """
        type_config = SATISFACTION_TYPES.get(sat_type, {})

        # 提取世界观元素
        setting_elements = self._extract_setting_elements(core_setting)

        # 生成钩子
        hooks = self._generate_hooks(sat_type, core_setting)

        # 构建爽点设计
        point = SatisfactionPoint(
            chapter=chapter,
            sat_type=sat_type,
            intensity=0,  # 将在后续设置
            name=type_config.get("name", sat_type),
            description=type_config.get("description", ""),
            elements=type_config.get("elements", []),
            emotional_curve=type_config.get("emotional_curve", []),
            hooks=hooks,
            prerequisites=self._generate_prerequisites(sat_type, setting_elements),
            aftermath=self._generate_aftermath(sat_type),
        )

        return point

    def _extract_setting_elements(self, core_setting: Dict[str, Any]) -> Dict[str, Any]:
        """从世界观设定中提取关键元素"""
        elements = {
            "protagonist": "主角",
            "antagonist": "反派",
            "power_system": [],
            "factions": [],
            "key_items": [],
        }

        # 提取主角名
        characters = core_setting.get("人物", {})
        if characters:
            main_chars = [k for k in characters.keys() if "主" in k or "protagonist" in k.lower()]
            if main_chars:
                elements["protagonist"] = main_chars[0]

        # 提取势力
        factions = core_setting.get("势力", {})
        if factions:
            elements["factions"] = list(factions.keys())

        # 提取修炼体系
        power = core_setting.get("力量体系", {})
        if power:
            elements["power_system"] = power.get("境界", [])

        return elements

    def _generate_hooks(self, sat_type: str, core_setting: Dict[str, Any]) -> List[str]:
        """
        生成钩子示例

        Args:
            sat_type: 爽点类型
            core_setting: 世界观设定

        Returns:
            List[str]: 钩子示例列表
        """
        templates = self.HOOK_TEMPLATES.get(sat_type, [])
        if not templates:
            return []

        # 提取设定中的元素用于填充模板
        setting_elements = self._extract_setting_elements(core_setting)

        hooks = []
        for template in templates[:2]:  # 最多返回2个钩子
            hook = template.format(
                protagonist=setting_elements.get("protagonist", "主角"),
                antagonist=setting_elements.get("antagonist", "反派"),
                current_realm="当前境界",
                treasure_name="秘宝",
                technique_name="绝技",
                mystery_person="神秘人",
                clue_item="线索碎片",
                hidden_place="隐秘之地",
                item="宝物",
                container="宝盒",
                reward="奖励",
                special_item="特殊收获",
                emotional_scene="关键时刻",
                love_interest="心仪之人",
                character="重要角色",
                event="事件",
                emotion="真挚情感",
                special_moment="特殊时刻",
                authority="权威人士",
                old_status="旧身份",
                new_status="新身份",
                mocking_group="嘲笑者",
                ceremony_name="仪式",
                new_level="新层级",
            )
            hooks.append(hook)

        return hooks

    def _generate_prerequisites(self, sat_type: str, setting_elements: Dict[str, Any]) -> List[str]:
        """生成前置铺垫建议"""
        prerequisites_map = {
            "face_slap": [
                "前1-2章铺垫反派的嚣张态度",
                "暗示主角隐藏的实力或底牌",
                "营造众人对主角的轻视氛围",
            ],
            "power_up": [
                "前2-3章描写突破前的困境或瓶颈",
                "铺垫突破的契机或机缘",
                "暗示新境界/能力的非凡之处",
            ],
            "revelation": [
                "前置章节散落关键线索",
                "营造悬念和疑问",
                "让读者产生猜测但无法确定",
            ],
            "harvest": [
                "铺垫目标物品/资源的珍贵性",
                "描述获取的困难与风险",
                "暗示可能存在的意外收获",
            ],
            "emotional": [
                "前置章节积累情感张力",
                "铺垫双方的情感变化",
                "营造情感爆发的合适场景",
            ],
            "status_up": [
                "铺垫主角被轻视的现状",
                "暗示即将到来的转变契机",
                "描述新地位的重要性和意义",
            ],
        }
        return prerequisites_map.get(sat_type, ["前期做好相关铺垫"])

    def _generate_aftermath(self, sat_type: str) -> List[str]:
        """生成后续影响建议"""
        aftermath_map = {
            "face_slap": [
                "反派的反应与后续报复",
                "旁观者的态度转变",
                "主角获得实际利益或声望",
            ],
            "power_up": [
                "新能力的掌握与适应",
                "周围人的反应与态度变化",
                "开启新的剧情线或挑战",
            ],
            "revelation": [
                "真相带来的连锁反应",
                "相关人物的行为变化",
                "引发新的悬念或冲突",
            ],
            "harvest": [
                "收获的使用或分配",
                "因收获引起他人觊觎",
                "为主角带来新能力或机会",
            ],
            "emotional": [
                "关系的确立与发展",
                "情感对后续决策的影响",
                "可能的情感考验",
            ],
            "status_up": [
                "新层级的规则与挑战",
                "旧关系的处理与维护",
                "新敌人的出现",
            ],
        }
        return aftermath_map.get(sat_type, ["处理好爽点后的剧情过渡"])

    def get_satisfaction_for_chapter(self, chapter_num: int) -> Optional[SatisfactionPoint]:
        """获取指定章节的爽点设计"""
        for point in self.satisfaction_points:
            if point.chapter == chapter_num:
                return point
        return None

    def get_chapters_without_satisfaction(self) -> List[int]:
        """获取没有安排爽点的章节列表"""
        if not self.pacing_plan:
            return []

        all_chapters = set(range(1, self.pacing_plan.total_chapters + 1))
        sat_chapters = set(p.chapter for p in self.satisfaction_points)
        low_chapters = set(p[0] for p in self.pacing_plan.low_points)

        return sorted(list(all_chapters - sat_chapters - low_chapters))

    def export_pacing_plan(self, output_path: str) -> bool:
        """导出爽点分布计划为YAML"""
        try:
            data = {
                "爽点分布计划": {
                    "总章节": self.pacing_plan.total_chapters if self.pacing_plan else 0,
                    "幕数": self.pacing_plan.num_acts if self.pacing_plan else 0,
                    "世界观类型": self.world_type,
                    "大爆点": [
                        {
                            "章节": p.chapter,
                            "类型": SATISFACTION_TYPES.get(p.sat_type, {}).get("name", p.sat_type),
                            "强度": p.intensity,
                            "描述": p.description,
                        }
                        for p in (self.pacing_plan.major_climaxes if self.pacing_plan else [])
                    ],
                    "中爆点": [
                        {
                            "章节": p.chapter,
                            "类型": SATISFACTION_TYPES.get(p.sat_type, {}).get("name", p.sat_type),
                            "强度": p.intensity,
                        }
                        for p in (self.pacing_plan.medium_peaks if self.pacing_plan else [])
                    ],
                    "小爽点": [
                        {
                            "章节": p.chapter,
                            "类型": SATISFACTION_TYPES.get(p.sat_type, {}).get("name", p.sat_type),
                            "强度": p.intensity,
                        }
                        for p in (self.pacing_plan.minor_satisfactions if self.pacing_plan else [])
                    ],
                    "低谷期": [
                        {"章节": chapter, "说明": desc}
                        for chapter, desc in (self.pacing_plan.low_points if self.pacing_plan else [])
                    ],
                }
            }

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

            self.logger.info(f"爽点分布计划已导出: {output_path}")
            return True
        except Exception as e:
            self.logger.error(f"导出爽点分布计划失败: {e}")
            return False
