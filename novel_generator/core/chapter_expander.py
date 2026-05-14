"""
章节扩写器
章节级一次生成，不拆场景。上下文注入：大纲窗口 + 正文窗口。
支持批量生成以优化 DeepSeek 缓存命中率。
"""

import re
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from novel_generator.config.settings import Settings
from novel_generator.utils.multi_model_client import MultiModelClient
from novel_generator.core.ai_roles import AIRoleManager, AIRole


class BatchExpansionError(Exception):
    """批量生成错误"""
    pass


class ChapterExpansionError(Exception):
    """单章生成错误"""
    pass


def _parse_chapter_range(section_key: str) -> Tuple[int, int]:
    """解析章节区间字符串，如 '第6-10章' -> (6, 10)"""
    import re
    match = re.match(r"第(\d+)-(\d+)章", section_key)
    if match:
        return (int(match.group(1)), int(match.group(2)))
    return (0, 0)


def _summarize_chapter_skeleton(ch_data: Dict[str, Any]) -> str:
    """从章级骨架提取简洁摘要（不含场景节拍细节）"""
    parts = []
    core_event = ch_data.get("核心事件", "")
    position = ch_data.get("章节定位", "")
    cause_chain = ch_data.get("与前章因果", "")
    scenes = ch_data.get("场景概览", [])
    emotion = ch_data.get("情绪曲线", "")
    foreshadowing = ch_data.get("伏笔处理", {})
    ending_hook = ch_data.get("结尾卡点", "")

    if position:
        parts.append(f"定位: {position}")
    if core_event:
        parts.append(f"事件: {core_event}")
    if cause_chain:
        parts.append(f"因果: {cause_chain}")
    if isinstance(scenes, list) and scenes:
        parts.append(f"场景: {'; '.join(str(s) for s in scenes[:4])}")
    if emotion:
        parts.append(f"情绪: {emotion}")
    if isinstance(foreshadowing, dict):
        buried = foreshadowing.get("埋设", [])
        recovered = foreshadowing.get("回收", [])
        if buried:
            parts.append(f"埋设: {', '.join(str(x) for x in buried[:2])}")
        if recovered:
            parts.append(f"回收: {', '.join(str(x) for x in recovered[:2])}")
    if ending_hook:
        parts.append(f"卡点: {ending_hook}")
    return " | ".join(parts)


def _build_outline_context(outline: Dict[str, Any], current_ch: int, window: int = 30) -> str:
    """构建前N章大纲上下文（骨架级摘要，含叙事逻辑链）"""
    start = max(1, current_ch - window)
    parts = []
    for ch in range(start, current_ch):
        ch_key = f"第{ch}章"
        ch_data = outline.get(ch_key)
        if not ch_data:
            continue
        title = ch_data.get("标题", "")
        summary = _summarize_chapter_skeleton(ch_data)

        block = f"【第{ch}章】"
        if title:
            block += f" {title}"
        block += "\n"
        if summary:
            block += f"  {summary}\n"
        parts.append(block)
    return "\n".join(parts) if parts else ""


def _build_draft_context(draft_dir: str, current_ch: int, window: int = 10) -> str:
    """构建前N章正文全文上下文（从磁盘读取）"""
    start = max(1, current_ch - window)
    parts = []
    draft_path = Path(draft_dir)
    for ch in range(start, current_ch):
        file_path = draft_path / f"第{ch:04d}章.txt"
        if not file_path.exists():
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
            parts.append(f"【第{ch}章】\n{content}")
        except Exception:
            continue
    return "\n\n".join(parts) if parts else ""


class ChapterExpander:
    """章节扩写器 — 章节级一次生成，不拆场景。支持批量生成以优化缓存。"""

    # 批量生成配置常量
    BATCH_SIZE_DEFAULT = 5
    BATCH_SIZE_MAX = 10
    CHAPTER_SEPARATOR = "===第{ch}章结束==="

    def __init__(
        self,
        config: Dict[str, Any],
        multi_model_client: MultiModelClient = None,
        project_root: str = ".",
        core_setting: Dict[str, Any] = None,
    ):
        self.config = config
        self.settings = Settings(config)
        self.logger = logging.getLogger(__name__)
        self.project_root = project_root
        self.multi_model_client = multi_model_client or MultiModelClient(config)
        self.ai_role_manager = AIRoleManager(config, self.multi_model_client)
        self.core_setting = core_setting or {}

        # 缓存优化状态跟踪
        self._static_prefix_built = False
        self._static_messages: List[Dict[str, str]] = []
        self._batch_stats = {
            "total_batches": 0,
            "total_chapters": 0,
        }

    def expand_chapter(
        self,
        chapter_num: int,
        chapter_outline: Dict[str, Any],
        outline_context: str = "",
        draft_context: str = "",
    ) -> str:
        """单章扩写（向后兼容，内部委托给 expand_range）"""
        results = self.expand_range(
            chapter_num, chapter_num,
            {f"第{chapter_num}章": chapter_outline},
            outline_context=outline_context,
            draft_context=draft_context,
        )
        return results.get(chapter_num, "")

    def expand_range(
        self,
        start_ch: int,
        end_ch: int,
        outline: Dict[str, Any],
        batch_size: int = None,
        outline_context: str = "",
        draft_context: str = "",
    ) -> Dict[int, str]:
        """
        范围扩写（新增主要入口）

        Args:
            start_ch: 起始章节号
            end_ch: 结束章节号
            outline: 完整大纲数据
            batch_size: 每批章节数，None则使用默认值
            outline_context: 前文大纲上下文（可选，用于批量优化）
            draft_context: 前文正文上下文（可选，用于批量优化）

        Returns:
            Dict[int, str]: {章节号: 正文内容}
        """
        if start_ch > end_ch:
            raise ValueError(f"起始章节 {start_ch} 不能大于结束章节 {end_ch}")

        batch_size = batch_size or self.BATCH_SIZE_DEFAULT
        batch_size = min(batch_size, self.BATCH_SIZE_MAX)

        results: Dict[int, str] = {}
        chapters = list(range(start_ch, end_ch + 1))

        # 分批处理
        for i in range(0, len(chapters), batch_size):
            batch = chapters[i:i + batch_size]
            self.logger.info(f"处理批次 {i//batch_size + 1}: 第{batch[0]}-{batch[-1]}章")

            try:
                batch_results = self._expand_batch(batch, outline)
                results.update(batch_results)
            except BatchExpansionError as e:
                self.logger.warning(f"批量生成失败，回退到单章模式: {e}")
                # 回退到单章模式
                for ch in batch:
                    try:
                        ch_key = f"第{ch}章"
                        ch_outline = outline.get(ch_key, {})
                        if not ch_outline:
                            self.logger.warning(f"第{ch}章无大纲数据，跳过")
                            continue
                        content = self._expand_single(ch, ch_outline, outline)
                        results[ch] = content
                    except Exception as e2:
                        self.logger.error(f"第{ch}章生成失败: {e2}")
                        raise ChapterExpansionError(f"第{ch}章生成失败: {e2}")

        return results

    def _expand_batch(
        self,
        chapters: List[int],
        outline: Dict[str, Any],
    ) -> Dict[int, str]:
        """
        批量生成核心实现

        构建缓存友好的消息结构，单次API调用生成多章
        """
        if not chapters:
            return {}

        # 构建消息（缓存优化结构）
        messages = self._build_batch_messages(chapters, outline)

        # 计算所需token：根据章节数和字数目标
        total_word_count = sum(
            outline.get(f"第{ch}章", {}).get("字数目标", self.settings.get_default_word_count())
            for ch in chapters
        )
        # 中文字符转token比例约1:1.5，添加buffer用于分隔符和额外内容
        required_tokens = int(total_word_count * 1.5) + 5000
        self.logger.info(f"批量生成{len(chapters)}章，预估字数{total_word_count}，设置max_tokens={required_tokens}")

        # 调用API
        self.logger.info(f"发送批量生成请求（{len(chapters)}章）...")
        response = self.ai_role_manager.chat_completion(
            role=AIRole.GENERATOR,
            messages=messages,
            max_tokens=required_tokens,
        )

        # 解析响应
        results = self._parse_batch_response(response, chapters)

        # 验证完整性
        if len(results) != len(chapters):
            missing = set(chapters) - set(results.keys())
            raise BatchExpansionError(f"解析结果不完整，缺失章节: {missing}")

        self._batch_stats["total_batches"] += 1
        self._batch_stats["total_chapters"] += len(chapters)

        return results

    def _expand_single(
        self,
        chapter_num: int,
        chapter_outline: Dict[str, Any],
        outline: Dict[str, Any],
    ) -> str:
        """
        单章生成（回退模式）
        保持原有逻辑，但使用缓存优化的消息结构
        """
        messages = self._build_single_messages(chapter_num, chapter_outline, outline)

        response = self.ai_role_manager.chat_completion(
            role=AIRole.GENERATOR,
            messages=messages,
        )

        return self._quick_polish(response)

    def _build_batch_messages(
        self,
        chapters: List[int],
        outline: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """
        构建DeepSeek缓存友好的消息结构

        消息分层：
        L1 (静态): System + 核心设定
        L2 (准静态): 整体故事框架
        L3 (共享): 前文上下文（大纲+正文窗口）
        L4 (动态): 多章骨架
        """
        messages: List[Dict[str, str]] = []
        start_ch = min(chapters)

        # ===== L1: System + 核心设定 =====
        system_content = self._build_system_content()
        if self.core_setting:
            core_setting_yaml = yaml.dump(
                self.core_setting,
                allow_unicode=True,
                default_flow_style=False
            )
            system_content += f"\n\n【核心设定】\n{core_setting_yaml}"

        messages.append({"role": "system", "content": system_content})

        # ===== L2: 故事概述 + chapter_plan 高层规划 =====
        story_overview = self._load_story_overview()
        if story_overview:
            messages.append({"role": "user", "content": f"【故事概述】\n{story_overview}"})
            messages.append({"role": "assistant", "content": "已理解故事概述和核心设定。"})

        # 加载 chapter_plan 并构建高层规划上下文（替代30章详细大纲）
        chapter_plan = self._load_chapter_plan()
        plan_context = self._build_chapter_plan_context(chapter_plan, start_ch)
        if plan_context:
            messages.append({"role": "user", "content": f"【整体故事走向（chapter_plan）】\n{plan_context}"})
            messages.append({"role": "assistant", "content": "已理解整体故事走向和关键约束。"})

        # ===== L3: 前文正文上下文（保持文风连贯） =====
        draft_ctx = _build_draft_context(
            str(self.settings.path_config.draft_dir), start_ch, self.settings.get_draft_window()
        )
        if draft_ctx:
            messages.append({"role": "user", "content": f"【前文正文（保持文风连贯）】\n{draft_ctx}"})
            messages.append({"role": "assistant", "content": "已接收前文正文。"})

        # ===== L4: 多章骨架（动态内容） =====
        batch_prompt = self._build_batch_prompt(chapters, outline)
        messages.append({"role": "user", "content": batch_prompt})

        # 记录消息结构用于调试
        self._log_message_structure(messages)

        return messages

    def _build_single_messages(
        self,
        chapter_num: int,
        chapter_outline: Dict[str, Any],
        outline: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """构建单章生成的消息结构"""
        messages: List[Dict[str, str]] = []

        # L1: System + 核心设定
        system_content = self._build_system_content()
        if self.core_setting:
            core_setting_yaml = yaml.dump(
                self.core_setting,
                allow_unicode=True,
                default_flow_style=False
            )
            system_content += f"\n\n【核心设定】\n{core_setting_yaml}"
        messages.append({"role": "system", "content": system_content})

        # L2: 故事概述 + chapter_plan 高层规划
        story_overview = self._load_story_overview()
        if story_overview:
            messages.append({"role": "user", "content": f"【故事概述】\n{story_overview}"})
            messages.append({"role": "assistant", "content": "已理解故事概述。"})

        # 加载 chapter_plan 并构建高层规划上下文（替代30章详细大纲）
        chapter_plan = self._load_chapter_plan()
        plan_context = self._build_chapter_plan_context(chapter_plan, chapter_num)
        if plan_context:
            messages.append({"role": "user", "content": f"【整体故事走向（chapter_plan）】\n{plan_context}"})
            messages.append({"role": "assistant", "content": "已理解整体故事走向和关键约束。"})

        # L3: 前文正文上下文（保持文风连贯）
        draft_ctx = _build_draft_context(
            str(self.settings.path_config.draft_dir), chapter_num, self.settings.get_draft_window()
        )
        if draft_ctx:
            messages.append({"role": "user", "content": f"【前文正文（保持文风连贯）】\n{draft_ctx}"})

        # L4: 当前章节骨架
        chapter_prompt = self._build_chapter_prompt(
            chapter_num, chapter_outline, "", draft_ctx  # outline_ctx 不再需要
        )
        messages.append({"role": "user", "content": chapter_prompt})

        return messages

    def _build_system_content(self) -> str:
        """构建系统提示词内容（从配置文件加载）"""
        # 从 PromptManager 加载 generator 角色的 system prompt
        from novel_generator.utils.prompt_manager import PromptManager

        prompt_manager = PromptManager(self.project_root)
        template = prompt_manager.get_system_prompt("generator")

        if template:
            base = template
        else:
            # 回退到简单默认
            base = "你是一位专业的小说作家，擅长根据大纲骨架扩写高质量的网文章节。"

        # 注入设定禁忌
        if self.core_setting:
            禁忌 = self.core_setting.get("设定禁忌", [])
            if 禁忌:
                taboo_lines = []
                # 设定禁忌是列表格式，包含分类标记和具体禁忌条目
                if isinstance(禁忌, list):
                    # 处理列表格式的禁忌
                    current_section = None
                    for item in 禁忌:
                        if isinstance(item, str):
                            # 检查是否是分类标记（如【龙魂禁忌】）
                            if item.startswith("【") and item.endswith("】"):
                                current_section = item
                                taboo_lines.append(f"\n{item}")
                            elif current_section and item.startswith("-"):
                                # 具体禁忌条目，去掉前导 -
                                taboo_lines.append(f"• {item.lstrip('- ').strip()}")
                            elif item.strip():
                                # 其他内容直接添加
                                taboo_lines.append(f"• {item}")
                elif isinstance(禁忌, dict):
                    # 兼容字典格式（如果将来格式变化）
                    for section, items in 禁忌.items():
                        if isinstance(items, list) and items:
                            taboo_lines.append(f"\n【{section}】")
                            taboo_lines.extend([f"• {t}" for t in items[:3]])
                elif isinstance(禁忌, str):
                    # 兼容字符串格式
                    taboo_lines.append(f"\n• {禁忌}")

                if taboo_lines:
                    base += "\n\n⚠️ 以下设定禁忌必须严格遵守，不得违反：\n" + "\n".join(taboo_lines)

        return base

    def _load_chapter_plan(self) -> Dict[str, Any]:
        """加载完整的 chapter_plan.yaml 数据"""
        try:
            # 尝试从多种路径加载
            paths_to_try = [
                Path(self.project_root) / "source" / "chapter_plan.yaml",
                Path(self.project_root) / "novels" / self.config.get("novel_id", "") / "source" / "chapter_plan.yaml",
            ]
            for path in paths_to_try:
                if path.exists():
                    with open(path, "r", encoding="utf-8") as f:
                        return yaml.safe_load(f) or {}
        except Exception as e:
            self.logger.debug(f"加载chapter_plan失败: {e}")
        return {}

    def _build_chapter_plan_context(
        self,
        chapter_plan: Dict[str, Any],
        current_ch: int,
    ) -> str:
        """
        构建 chapter_plan 高层规划上下文

        只注入当前区间及前后各1个区间（共3区间），
        提供宏观故事走向和关键约束
        """
        if not chapter_plan:
            return ""

        parts = []
        剧情规划 = chapter_plan.get("剧情规划", {})

        # 找到当前章节所在的区间
        current_section_key = None
        current_section_start = 0

        for section_key in 剧情规划.keys():
            start, end = _parse_chapter_range(section_key)
            if start <= current_ch <= end:
                current_section_key = section_key
                current_section_start = start
                break

        if not current_section_key:
            # 如果没找到当前区间，返回空
            return ""

        # 收集要注入的区间：当前区间、前一区间、后一区间
        sections_to_inject = []
        section_keys = list(剧情规划.keys())

        try:
            current_idx = section_keys.index(current_section_key)
            # 前一区间
            if current_idx > 0:
                sections_to_inject.append(section_keys[current_idx - 1])
            # 当前区间
            sections_to_inject.append(current_section_key)
            # 后一区间
            if current_idx < len(section_keys) - 1:
                sections_to_inject.append(section_keys[current_idx + 1])
        except ValueError:
            sections_to_inject = [current_section_key]

        # 构建上下文
        for section_key in sections_to_inject:
            section_data = 剧情规划.get(section_key, {})
            if not section_data:
                continue

            parts.append(f"\n【{section_key}】")

            核心内容 = section_data.get("核心内容", "")
            if 核心内容:
                parts.append(f"核心内容: {核心内容}")

            情绪基调 = section_data.get("情绪基调", "")
            if 情绪基调:
                parts.append(f"情绪基调: {情绪基调}")

            关键约束 = section_data.get("关键约束", [])
            if 关键约束:
                parts.append(f"关键约束:")
                for constraint in 关键约束:
                    parts.append(f"  - {constraint}")

        return "\n".join(parts) if parts else ""

    def _load_story_overview(self) -> Optional[str]:
        """从chapter_plan.yaml加载故事概述"""
        try:
            # 尝试从source目录加载chapter_plan.yaml
            chapter_plan_file = Path(self.project_root) / "source" / "chapter_plan.yaml"
            if chapter_plan_file.exists():
                with open(chapter_plan_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    return data.get("故事概述", "")
            # 也尝试从novels目录结构加载
            novel_plan_file = Path(self.project_root) / "novels" / self.config.get("novel_id", "") / "source" / "chapter_plan.yaml"
            if novel_plan_file.exists():
                with open(novel_plan_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    return data.get("故事概述", "")
        except Exception as e:
            self.logger.debug(f"加载故事概述失败: {e}")
        return None

    def _build_batch_prompt(
        self,
        chapters: List[int],
        outline: Dict[str, Any],
    ) -> str:
        """构建批量生成的用户提示"""
        lines: List[str] = []
        lines.append(f"请根据以上上下文，依次生成第{chapters[0]}章到第{chapters[-1]}章的完整正文。")
        lines.append("")

        # 从配置文件加载写作技巧
        from novel_generator.utils.prompt_manager import PromptManager
        prompt_manager = PromptManager(self.project_root)
        batch_rules = prompt_manager.generation_prompts.get("batch_writing_rules", {})

        if batch_rules:
            lines.append("【写作技巧要求】")
            # 感官描写
            sensory = batch_rules.get("sensory_details", {})
            if sensory:
                rules = sensory.get("rules", [])
                lines.append(f"1. {sensory.get('description', '感官描写')}:")
                for r in rules[:3]:
                    lines.append(f"   - {r}")
            # 心理渲染
            emotional = batch_rules.get("emotional_rendering", {})
            if emotional:
                rules = emotional.get("rules", [])
                lines.append(f"2. {emotional.get('description', '心理渲染')}:")
                for r in rules[:2]:
                    lines.append(f"   - {r}")
            # 剧情推进
            plot = batch_rules.get("plot_progression", {})
            if plot:
                rules = plot.get("rules", [])
                lines.append(f"3. {plot.get('description', '剧情推进')}:")
                for r in rules[:2]:
                    lines.append(f"   - {r}")
            # 结尾钩子
            ending = batch_rules.get("ending_hook", {})
            if ending:
                rules = ending.get("rules", [])
                lines.append(f"4. {ending.get('description', '结尾钩子')}:")
                for r in rules[:2]:
                    lines.append(f"   - {r}")
            lines.append("")
        else:
            # 回退到默认规则
            lines.append("【写作技巧要求】")
            lines.append("1. 感官描写：每个场景至少包含2种感官细节")
            lines.append("2. 心理渲染：用行为暗示情绪，禁止情绪标签")
            lines.append("3. 禁止流水账：用因果链代替时间线")
            lines.append("4. 结尾钩子：悬念式结尾，禁止总结升华")
            lines.append("")

        # 加载进度控制规则（从配置文件，避免硬编码）
        progress_rules = prompt_manager.generation_prompts.get("progress_control", {})
        if progress_rules:
            rules = progress_rules.get("rules", [])
            if rules:
                lines.append("【进度控制（必须遵守）】")
                for rule in rules:
                    lines.append(f"  - {rule}")
                lines.append("")
        else:
            # 回退到默认规则
            lines.append("【进度控制】")
            lines.append("  - 本章内容必须严格限定在核心事件范围内")
            lines.append("  - 禁止提前完成后续章节的核心事件")
            lines.append("  - 时间跨度必须遵守大纲设定")
            lines.append("  - 结尾状态必须精确匹配结尾卡点")
            lines.append("")

        lines.append("生成要求：")
        lines.append("1. 每章内容必须完整，包含场景描写、对话、动作等")
        lines.append("2. 章节之间用明确的分隔标记分割")
        lines.append("3. 确保人物设定、伏笔、文风在各章之间保持一致")
        lines.append("4. 严格按各章骨架的字数目标执行，不足时补充感官细节")
        lines.append("")
        lines.append(f"章节分隔格式：每章结束后必须包含标记 '{self.CHAPTER_SEPARATOR.format(ch='章节号')}'")
        lines.append("例如：第13章结束后写 '===第13章结束==='")
        lines.append("")
        lines.append("=" * 50)
        lines.append("【各章骨架】")
        lines.append("=" * 50)
        lines.append("")

        for ch_num in chapters:
            ch_key = f"第{ch_num}章"
            ch_outline = outline.get(ch_key, {})
            skeleton = self._build_compact_skeleton(ch_num, ch_outline)

            lines.append(f"\n>>> 第{ch_num}章 <<<")
            lines.append(skeleton)
            lines.append("")

        lines.append("")
        lines.append("=" * 50)
        lines.append("请开始生成各章正文（务必遵守每章结尾卡点）：")
        lines.append("=" * 50)

        return "\n".join(lines)

    def _build_compact_skeleton(self, ch_num: int, ch_outline: Dict[str, Any]) -> str:
        """构建紧凑的章节骨架"""
        parts: List[str] = []

        title = ch_outline.get("标题", f"第{ch_num}章")
        parts.append(f"标题: {title}")

        position = ch_outline.get("章节定位", "")
        if position:
            parts.append(f"定位: {position}")

        # 与前章因果 - 批量生成时必须明确传递
        cause_chain = ch_outline.get("与前章因果", "")
        if cause_chain:
            parts.append(f"\n【与前章因果（本章开头必须精确衔接）】")
            parts.append(cause_chain)

        core_event = ch_outline.get("核心事件", "")
        if core_event:
            parts.append(f"\n【核心事件（本章唯一内容范围，禁止超出）】")
            parts.append(core_event)
            parts.append("⚠ 本章内容不得超出此范围，不得提前完成后续章节事件")

        # 新增：人物行动（完整传递）
        character_actions = ch_outline.get("人物行动", {})
        if character_actions:
            parts.append(f"\n【人物行动（必须遵守）】")
            if isinstance(character_actions, dict):
                for role, action in character_actions.items():
                    parts.append(f"  {role}: {action}")
            else:
                parts.append(f"  {character_actions}")

        # 场景概览（完整传递，取消截断）
        scenes = ch_outline.get("场景概览", [])
        if scenes:
            parts.append(f"\n【场景概览 ({len(scenes)}个场景)】")
            for i, s in enumerate(scenes, 1):
                parts.append(f"  {i}. {s}")

        emotion = ch_outline.get("情绪曲线", "")
        if emotion:
            parts.append(f"\n情绪曲线: {emotion}")

        # 新增：伏笔处理（完整传递）
        foreshadowing = ch_outline.get("伏笔处理", {})
        if foreshadowing:
            parts.append(f"\n【伏笔处理】")
            if isinstance(foreshadowing, dict):
                buried = foreshadowing.get("埋设", [])
                recovered = foreshadowing.get("回收", [])
                if buried:
                    parts.append(f"  埋设: {'; '.join(str(x) for x in buried)}")
                if recovered:
                    parts.append(f"  回收: {'; '.join(str(x) for x in recovered)}")
            else:
                parts.append(f"  {foreshadowing}")

        ending = ch_outline.get("结尾卡点", "")
        if ending:
            # 强制标注结尾卡点要求，添加检查要点
            parts.append(f"\n【结尾卡点（必须精确匹配，不得超前或偏离）】")
            parts.append(ending)
            parts.append("⚠ 检查要点：")
            parts.append("  1. 时间跨度是否符合大纲设定")
            parts.append("  2. 人物状态是否符合大纲（如龙魂沉寂/苏醒）")
            parts.append("  3. 境界进度是否符合大纲（如未突破/已突破）")

        word_count = ch_outline.get("字数目标", self.settings.get_default_word_count())
        parts.append(f"\n字数目标: {word_count}字（最低{word_count}字，误差±50字）")
        parts.append(f"字数不足补救：")
        parts.append(f"  - 增加场景感官细节描写（视觉、听觉、触觉、嗅觉）")
        parts.append(f"  - 增加人物心理渲染（用动作/生理反应表现情绪）")
        parts.append(f"  - 增加环境氛围刻画")

        return "\n".join(parts)

    def _parse_batch_response(
        self,
        response: str,
        expected_chapters: List[int],
    ) -> Dict[int, str]:
        """从批量响应中解析各章内容"""
        results: Dict[int, str] = {}
        remaining = response

        for ch_num in expected_chapters:
            separator = self.CHAPTER_SEPARATOR.format(ch=ch_num)

            if separator in remaining:
                parts = remaining.split(separator, 1)
                content = parts[0].strip()
                content = self._clean_chapter_markers(content, ch_num)
                results[ch_num] = content

                if len(parts) > 1:
                    remaining = parts[1]
                else:
                    remaining = ""
            else:
                # 可能是最后一章
                if ch_num == expected_chapters[-1] and remaining.strip():
                    results[ch_num] = self._clean_chapter_markers(remaining.strip(), ch_num)
                    remaining = ""
                else:
                    self.logger.warning(f"第{ch_num}章的分隔符未找到")
                    break

        return results

    def _clean_chapter_markers(self, content: str, ch_num: int) -> str:
        """清理AI自动生成的章节标记"""
        patterns = [
            rf"^第{ch_num}章[：:\s]*",
            rf"^Chapter\s*{ch_num}[：:\s]*",
            rf"^\d+[\.、\s]+",
        ]

        for pattern in patterns:
            content = re.sub(pattern, "", content, flags=re.IGNORECASE)

        return content.strip()

    def _log_message_structure(self, messages: List[Dict[str, str]]):
        """记录消息结构用于调试"""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        self.logger.debug(f"消息结构: {len(messages)}条消息, 总计{total_chars}字符")
        for i, msg in enumerate(messages):
            preview = msg.get("content", "")[:100].replace("\n", " ")
            self.logger.debug(f"  [{i}] {msg.get('role')}: {preview}...")

    def get_batch_stats(self) -> Dict[str, Any]:
        """获取批量生成统计"""
        return self._batch_stats.copy()

    def _build_chapter_prompt(
        self,
        chapter_num: int,
        chapter_outline: Dict[str, Any],
        outline_context: str,
        draft_context: str,
    ) -> str:
        """构建章节扩写prompt：大纲上下文 + 正文上下文 + 当前章骨架"""
        title = chapter_outline.get("标题", f"第{chapter_num}章")
        core_event = chapter_outline.get("核心事件", "")
        position = chapter_outline.get("章节定位", "")
        cause_chain = chapter_outline.get("与前章因果", "")
        scene_overview = chapter_outline.get("场景概览", [])
        emotion_target = chapter_outline.get("情绪曲线", "")
        character_actions = chapter_outline.get("人物行动", "")
        foreshadowing = chapter_outline.get("伏笔处理", "")
        ending_hook = chapter_outline.get("结尾卡点", "")
        word_count = chapter_outline.get("字数目标", self.settings.get_default_word_count())

        parts = []

        # 注意：core_setting 已在 system 消息中注入，此处不再重复

        if outline_context:
            parts.append(f"【前文大纲上下文（保证宏观连续性）】\n{outline_context}")

        if draft_context:
            parts.append(f"【前文正文全文（保持文风、语气、细节连贯）】\n{draft_context}")

        parts.append(f"【当前章节骨架 - 第{chapter_num}章】")
        parts.append(f"标题: {title}")
        if position:
            parts.append(f"章节定位: {position}")
        if cause_chain:
            # 强制标注与前章因果，强调衔接要求
            parts.append(f"\n【与前章因果（本章开头必须精确衔接）】")
            parts.append(cause_chain)
        if core_event:
            parts.append(f"核心事件: {core_event}")
        if emotion_target:
            parts.append(f"情绪曲线: {emotion_target}")
        if character_actions:
            if isinstance(character_actions, dict):
                for role, action in character_actions.items():
                    parts.append(f"  {role}: {action}")
            else:
                parts.append(f"角色行动: {character_actions}")
        if foreshadowing:
            if isinstance(foreshadowing, dict):
                buried = foreshadowing.get("埋设", [])
                recovered = foreshadowing.get("回收", [])
                if buried:
                    parts.append(f"伏笔埋设: {', '.join(str(x) for x in buried)}")
                if recovered:
                    parts.append(f"伏笔回收: {', '.join(str(x) for x in recovered)}")
            else:
                parts.append(f"伏笔处理: {foreshadowing}")

        if isinstance(scene_overview, list) and scene_overview:
            parts.append(f"\n场景概览 ({len(scene_overview)}个场景):")
            for s in scene_overview:
                parts.append(f"  - {s}")

        if ending_hook:
            # 强制标注结尾卡点要求，添加详细说明
            parts.append(f"\n【结尾卡点（必须严格遵守）】")
            parts.append(ending_hook)
            parts.append("注意：结尾卡点是剧情进度控制的关键节点，必须精确匹配上述描述的状态。")
            parts.append("不得超前（写入后续章节内容）或偏离（改变结尾状态）。")

        parts.append(f"\n字数目标: {word_count}字")
        parts.append("\n请根据以上骨架和上下文，生成完整的章节正文。")
        parts.append("场景概览是粗粒度的剧情推进指引，场景间的具体过渡、对话细节、感官描写由你自然发挥。")
        parts.append("")
        parts.append("【核心约束】")
        parts.append("1. 与前章因果必须精确衔接：章节开头的状态、事件必须与前章结尾保持完全一致，确保故事连贯")
        parts.append("2. 结尾卡点必须精确匹配：章节结尾的状态、场景、人物位置必须与结尾卡点描述一致")
        parts.append("3. 文风一致、细节连贯、伏笔贯通、情绪到位")

        return "\n\n".join(parts)

    def _quick_polish(self, content: str) -> str:
        """轻量级润色（编码实现，无需API调用）"""
        if not content:
            return ""

        content = re.sub(r"\n{3,}", "\n\n", content)
        content = content.replace('"', '"').replace('"', '"')
        content = content.replace("'", "'").replace("'", "'")
        lines = [line.strip() for line in content.split("\n")]
        content = "\n".join(lines)
        paragraphs = content.split("\n\n")
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        content = "\n\n".join(paragraphs)

        return content.strip()

    def save_chapter(
        self, chapter_num: int, content: str, output_dir: str = None
    ) -> str:
        """保存章节到文件"""
        output_path = Path(output_dir or self.settings.path_config.draft_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        file_path = output_path / f"第{chapter_num:04d}章.txt"
        file_path.write_text(content, encoding="utf-8")

        self.logger.info(f"章节已保存: {file_path}")
        return str(file_path)

    def load_existing_chapter(self, chapter_num: int, draft_dir: str = None) -> str:
        """读取已存在的章节内容"""
        output_path = Path(draft_dir or self.settings.path_config.draft_dir)
        file_path = output_path / f"第{chapter_num:04d}章.txt"

        if file_path.exists():
            try:
                return file_path.read_text(encoding="utf-8")
            except Exception as e:
                self.logger.warning(f"读取章节 {chapter_num} 失败: {e}")
        return ""

    def get_existing_chapters(self, draft_dir: str = None) -> List[int]:
        """获取已存在的章节列表"""
        output_path = Path(draft_dir or self.settings.path_config.draft_dir)
        existing = []

        if output_path.exists():
            for f in output_path.glob("第*章.txt"):
                try:
                    match = re.search(r"第(\d+)章", f.name)
                    if match:
                        existing.append(int(match.group(1)))
                except Exception:
                    continue

        return sorted(existing)

    def expand_multiple_chapters(
        self,
        outline: Dict[str, Any],
        start_chapter: int,
        end_chapter: int,
        outline_window: int = 30,
        draft_window: int = 10,
        draft_dir: str = None,
    ) -> List[Dict[str, Any]]:
        """批量扩写多个章节"""
        results = []
        _draft_dir = draft_dir or self.settings.path_config.draft_dir

        for chapter_num in range(start_chapter, end_chapter + 1):
            chapter_key = f"第{chapter_num}章"
            chapter_outline = outline.get(chapter_key, {})

            if not chapter_outline:
                self.logger.warning(f"未找到第{chapter_num}章的大纲，跳过")
                continue

            outline_ctx = _build_outline_context(outline, chapter_num, outline_window)
            draft_ctx = _build_draft_context(_draft_dir, chapter_num, draft_window)

            try:
                content = self.expand_chapter(
                    chapter_num=chapter_num,
                    chapter_outline=chapter_outline,
                    outline_context=outline_ctx,
                    draft_context=draft_ctx,
                )

                file_path = self.save_chapter(chapter_num, content, _draft_dir)

                results.append({
                    "chapter": chapter_num,
                    "file_path": file_path,
                    "word_count": len(content),
                    "success": True,
                })

            except Exception as e:
                self.logger.error(f"扩写第{chapter_num}章失败: {e}")
                results.append({"chapter": chapter_num, "error": str(e), "success": False})

        return results
