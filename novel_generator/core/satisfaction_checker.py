"""
爽点质量检查器
用于检查章节内容中爽点的质量和完整性
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class SatisfactionElement:
    """爽点元素定义"""
    name: str
    pattern: str
    description: str = ""
    weight: int = 1


@dataclass
class SatisfactionResult:
    """爽点检查结果"""
    passed: bool
    completeness: str  # "完整", "基本完整", "部分缺失", "严重缺失"
    issues: List[str] = field(default_factory=list)
    score: int = 0  # 0-100
    matched_elements: List[str] = field(default_factory=list)
    missing_elements: List[str] = field(default_factory=list)


# 爽点检查清单 - 正则表达式
CHECKLIST: Dict[str, List[SatisfactionElement]] = {
    "face_slap": [
        SatisfactionElement(
            name="反派嚣张",
            pattern=r"(嘲笑|轻视|羞辱|看不起|废物|垃圾|配吗|也敢|讽刺|奚落|蔑视|嘲讽|贬低|践踏|凌辱|践踏尊严|趾高气扬|目中无人|得意洋洋|不可一世)",
            description="反派表现出对主角的轻视和羞辱",
            weight=2
        ),
        SatisfactionElement(
            name="主角隐忍",
            pattern=r"(冷静|平静|沉默|不为所动|淡淡|淡然|面无表情|冷眼旁观|不卑不亢|隐忍不发|按兵不动|泰然自若|从容不迫|心如止水|无动于衷)",
            description="主角表现出隐忍和冷静",
            weight=2
        ),
        SatisfactionElement(
            name="反转触发",
            pattern=r"(挑衅|逼迫|动手|过分|逼我|得寸进尺|咄咄逼人|欺人太甚|忍无可忍|触及底线|骑虎难下|箭在弦上|不得不发|最后一根稻草)",
            description="触发反转的导火索",
            weight=2
        ),
        SatisfactionElement(
            name="实力展现",
            pattern=r"(一击|瞬间|直接|轻松|碾压|不堪一击|不费吹灰之力|秒杀|完爆|碾压|摧枯拉朽|势如破竹|风卷残云|干净利落|一招制敌)",
            description="主角展现实力的爽感描写",
            weight=3
        ),
        SatisfactionElement(
            name="震惊反应",
            pattern=r"(震惊|不敢相信|愣住|寂静|失声|怎么可能|目瞪口呆|瞠目结舌|鸦雀无声|全场哗然|倒吸一口凉气|呆若木鸡|难以置信|惊骇欲绝)",
            description="周围人的震惊反应",
            weight=2
        ),
        SatisfactionElement(
            name="后续收益",
            pattern=r"(道歉|赔偿|长老|赏识|认可|奖励|收徒|尊敬|敬畏|刮目相看|另眼相看|刮目相看|地位提升|声名鹊起|名声大噪|名利双收|一雪前耻)",
            description="打脸后的实际收益和地位变化",
            weight=2
        ),
    ],
    "power_up": [
        SatisfactionElement(
            name="突破契机",
            pattern=r"(瓶颈|关卡|极限|临界点|契机|感悟|顿悟|豁然开朗|醍醐灌顶|茅塞顿开|水到渠成|厚积薄发|量变到质变)",
            description="突破的契机和时机",
            weight=2
        ),
        SatisfactionElement(
            name="能量积累",
            pattern=r"(吸收|凝聚|汇聚|积累|沉淀|汇聚|汹涌|澎湃|浩瀚|磅礴|源源不断|生生不息|汹涌澎湃|排山倒海)",
            description="能量汇聚积累的过程",
            weight=2
        ),
        SatisfactionElement(
            name="突破过程",
            pattern=r"(冲破|突破|撕裂|粉碎|破开|贯通|贯通|融会贯通|冲破桎梏|打破枷锁|脱胎换骨|涅槃重生|破茧成蝶|浴火重生)",
            description="突破过程中的描写",
            weight=3
        ),
        SatisfactionElement(
            name="天地异象",
            pattern=r"(异象|霞光|彩云|雷鸣|天地|色变|异香|瑞气|祥瑞|异象|天象|异变|奇观|天地感应|风云变色|日月无光)",
            description="突破引起的天地异象",
            weight=2
        ),
        SatisfactionElement(
            name="实力展现",
            pattern=r"(蜕变|飞跃|质变|强大|精进|精进|修为|境界|层次|飞跃|一日千里|突飞猛进|节节攀升|更上一层楼)",
            description="突破后实力的具体变化",
            weight=3
        ),
        SatisfactionElement(
            name="旁人反应",
            pattern=r"(惊骇|羡慕|嫉妒|震撼|敬畏|不可思议|难以置信|惊为天人|望尘莫及|望尘莫及|高不可攀|高山仰止)",
            description="他人对主角突破的反应",
            weight=1
        ),
    ],
    "revelation": [
        SatisfactionElement(
            name="悬念铺垫",
            pattern=r"(谜团|疑云|神秘|蹊跷|不对劲|奇怪|诡异|暗藏|蹊跷|蹊跷|疑点重重|扑朔迷离|错综复杂|迷雾重重)",
            description="真相揭露前的悬念铺垫",
            weight=2
        ),
        SatisfactionElement(
            name="线索收集",
            pattern=r"(线索|证据|蛛丝马迹|端倪|迹象|苗头|蛛丝马迹|抽丝剥茧|顺藤摸瓜|按图索骥|层层递进)",
            description="主角收集线索的过程",
            weight=2
        ),
        SatisfactionElement(
            name="真相揭露",
            pattern=r"(原来|真相|竟然是|万万没想到|竟然|真相大白|水落石出|柳暗花明|拨云见日|真相大白|恍然大悟)",
            description="真相揭露的关键时刻",
            weight=3
        ),
        SatisfactionElement(
            name="情节反转",
            pattern=r"(反转|逆转|转折|峰回路转|出乎意料|意想不到|大跌眼镜|戏剧性|惊天逆转|神来之笔)",
            description="真相揭露带来的情节反转",
            weight=3
        ),
    ],
    "harvest": [
        SatisfactionElement(
            name="探索过程",
            pattern=r"(探索|寻找|寻觅|探寻|搜寻|挖掘|发掘|探寻|历经艰辛|千辛万苦|九死一生|千辛万苦|踏破铁鞋)",
            description="获取宝物前的探索过程",
            weight=2
        ),
        SatisfactionElement(
            name="宝物描述",
            pattern=r"(至宝|神器|灵宝|奇珍|异宝|珍宝|瑰宝|绝世|稀世|独一无二|举世无双|价值连城|稀世珍宝)",
            description="对宝物的详细描述",
            weight=2
        ),
        SatisfactionElement(
            name="获得过程",
            pattern=r"(获得|得到|取得|收入囊中|据为己有|到手|收入囊中|满载而归|不虚此行|满载而归|盆满钵满)",
            description="主角获得宝物的描写",
            weight=2
        ),
        SatisfactionElement(
            name="效果展示",
            pattern=r"(提升|增强|强化|蜕变|进化|功效|威力|效果|立竿见影|如虎添翼|锦上添花|突飞猛进)",
            description="宝物带来的实际效果",
            weight=2
        ),
    ],
    "emotional": [
        SatisfactionElement(
            name="情感积累",
            pattern=r"(日积月累|日久生情|朝夕相处|患难与共|生死与共|同甘共苦|相濡以沫|风雨同舟|惺惺相惜)",
            description="情感关系的长期积累",
            weight=2
        ),
        SatisfactionElement(
            name="情感冲突",
            pattern=r"(误会|矛盾|挣扎|纠结|煎熬|痛苦|心碎|撕心裂肺|肝肠寸断|痛不欲生|心如刀绞|百爪挠心)",
            description="情感发展的冲突和波折",
            weight=2
        ),
        SatisfactionElement(
            name="情感爆发",
            pattern=r"(表白|告白|倾诉|坦露心声|真情流露|情难自已|情不自禁|情到深处|水到渠成|修成正果)",
            description="情感爆发的关键场景",
            weight=3
        ),
        SatisfactionElement(
            name="情感升华",
            pattern=r"(相知|相守|相许|白头|不离不弃|生死相依|海枯石烂|天长地久|地老天荒|相濡以沫)",
            description="情感的升华和确认",
            weight=3
        ),
    ],
    "status_up": [
        SatisfactionElement(
            name="地位落差",
            pattern=r"(卑微|低贱|底层|边缘|无名小卒|人微言轻|受尽欺凌|寄人篱下|仰人鼻息|看人脸色|被人轻视)",
            description="主角之前地位低下的描写",
            weight=2
        ),
        SatisfactionElement(
            name="崛起过程",
            pattern=r"(奋斗|拼搏|努力|进取|向上|不甘|逆袭|奋发图强|力争上游|不甘人后|力争上游|后来居上)",
            description="主角为提升地位付出的努力",
            weight=2
        ),
        SatisfactionElement(
            name="地位提升",
            pattern=r"(晋升|提拔|重用|赏识|认可|提拔|青云直上|平步青云|飞黄腾达|一步登天|鲤鱼跳龙门)",
            description="地位正式提升的关键场景",
            weight=3
        ),
        SatisfactionElement(
            name="地位对比",
            pattern=r"(今非昔比|刮目相看|另眼相看|不可同日而语|天壤之别|云泥之别|今非昔比|脱胎换骨|判若两人)",
            description="地位提升后的前后对比",
            weight=3
        ),
    ],
}


class SatisfactionChecker:
    """爽点质量检查器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.thresholds = {
            "完整": 85,
            "基本完整": 60,
            "部分缺失": 40,
        }

    def check_satisfaction_quality(
        self,
        content: str,
        sat_type: str
    ) -> SatisfactionResult:
        """
        检查爽点质量

        Args:
            content: 章节内容
            sat_type: 爽点类型 (face_slap, power_up, revelation, harvest, emotional, status_up)

        Returns:
            SatisfactionResult: 检查结果
        """
        if sat_type not in CHECKLIST:
            return SatisfactionResult(
                passed=False,
                completeness="未知类型",
                issues=[f"不支持的爽点类型: {sat_type}"],
                score=0
            )

        elements = CHECKLIST[sat_type]
        matched = []
        missing = []
        total_weight = sum(elem.weight for elem in elements)
        matched_weight = 0

        for element in elements:
            if self._check_element(content, element.pattern):
                matched.append(element.name)
                matched_weight += element.weight
            else:
                missing.append(element.name)

        # 计算完成度
        completion_rate = matched_weight / total_weight if total_weight > 0 else 0

        if completion_rate >= self.thresholds["完整"] / 100:
            completeness = "完整"
        elif completion_rate >= self.thresholds["基本完整"] / 100:
            completeness = "基本完整"
        elif completion_rate >= self.thresholds["部分缺失"] / 100:
            completeness = "部分缺失"
        else:
            completeness = "严重缺失"

        # 计算分数 (0-100)
        score = int(completion_rate * 100)

        # 生成问题列表
        issues = []
        if missing:
            issues.append(f"缺失元素: {', '.join(missing)}")

        # 判断是否通过 (基本完整及以上算通过)
        passed = completeness in ["完整", "基本完整"]

        return SatisfactionResult(
            passed=passed,
            completeness=completeness,
            issues=issues,
            score=score,
            matched_elements=matched,
            missing_elements=missing
        )

    def check_emotional_curve(
        self,
        content: str,
        expected_curve: List[str]
    ) -> SatisfactionResult:
        """
        检查情绪曲线是否符合预期

        Args:
            content: 章节内容
            expected_curve: 预期的情绪曲线 ["铺垫", "积累", "爆发", "回落"] 等

        Returns:
            SatisfactionResult: 检查结果
        """
        # 情绪阶段关键词
        emotion_keywords = {
            "铺垫": ["平静", "日常", "闲聊", "准备", "酝酿"],
            "积累": ["紧张", "焦虑", "期待", "压抑", "不安"],
            "冲突": ["争执", "对立", "冲突", "矛盾", "摩擦"],
            "爆发": ["爆发", "怒吼", "出手", "爆发", "高潮"],
            "回落": ["平静", "余波", "整理", "反思", "后续"],
        }

        issues = []
        detected_phases = []

        # 检测实际存在的情绪阶段
        for phase, keywords in emotion_keywords.items():
            for keyword in keywords:
                if keyword in content:
                    if phase not in detected_phases:
                        detected_phases.append(phase)
                    break

        # 比较预期和实际
        missing_phases = [p for p in expected_curve if p not in detected_phases]
        extra_phases = [p for p in detected_phases if p not in expected_curve]

        if missing_phases:
            issues.append(f"缺失预期阶段: {', '.join(missing_phases)}")
        if extra_phases:
            issues.append(f"出现意外阶段: {', '.join(extra_phases)}")

        # 检查阶段顺序
        phase_order_score = self._check_phase_order(expected_curve, detected_phases)

        # 计算总体分数
        if not expected_curve:
            score = 100
        else:
            matched_count = len(expected_curve) - len(missing_phases)
            base_score = (matched_count / len(expected_curve)) * 80
            order_score = phase_order_score * 20
            score = int(base_score + order_score)

        # 确定完成度
        if score >= 85:
            completeness = "完整"
        elif score >= 60:
            completeness = "基本完整"
        elif score >= 40:
            completeness = "部分缺失"
        else:
            completeness = "严重缺失"

        passed = completeness in ["完整", "基本完整"]

        return SatisfactionResult(
            passed=passed,
            completeness=completeness,
            issues=issues,
            score=score,
            matched_elements=detected_phases,
            missing_elements=missing_phases
        )

    def _check_element(self, content: str, pattern: str) -> bool:
        """
        检查单个元素是否存在

        Args:
            content: 章节内容
            pattern: 正则表达式模式

        Returns:
            bool: 是否匹配
        """
        try:
            return bool(re.search(pattern, content, re.MULTILINE | re.UNICODE))
        except re.error as e:
            self.logger.error(f"正则表达式错误: {e}, pattern={pattern}")
            return False

    def _check_phase_order(
        self,
        expected: List[str],
        actual: List[str]
    ) -> float:
        """
        检查阶段顺序是否正确

        Args:
            expected: 预期阶段顺序
            actual: 实际检测到的阶段

        Returns:
            float: 顺序匹配度 (0-1)
        """
        if not expected or not actual:
            return 1.0

        # 简化：只检查是否按预期顺序出现
        expected_indices = {phase: i for i, phase in enumerate(expected)}
        actual_indices = []

        for phase in actual:
            if phase in expected_indices:
                actual_indices.append(expected_indices[phase])

        if len(actual_indices) < 2:
            return 1.0

        # 检查是否单调递增
        inversions = 0
        for i in range(len(actual_indices) - 1):
            if actual_indices[i] > actual_indices[i + 1]:
                inversions += 1

        max_inversions = len(actual_indices) - 1
        if max_inversions == 0:
            return 1.0

        return 1.0 - (inversions / max_inversions)

    def get_available_types(self) -> List[str]:
        """获取所有可用的爽点类型"""
        return list(CHECKLIST.keys())

    def get_element_details(self, sat_type: str) -> List[Dict[str, Any]]:
        """
        获取指定爽点类型的元素详情

        Args:
            sat_type: 爽点类型

        Returns:
            List[Dict]: 元素详情列表
        """
        if sat_type not in CHECKLIST:
            return []

        return [
            {
                "name": elem.name,
                "description": elem.description,
                "weight": elem.weight
            }
            for elem in CHECKLIST[sat_type]
        ]
