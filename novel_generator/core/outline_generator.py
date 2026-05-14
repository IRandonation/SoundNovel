"""
大纲生成器
负责基于原始素材生成章节大纲
使用 chapter_plan.yaml 的5章区间规划，直接生成章级骨架驱动扩写。
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


class SlidingWindowSkeletonGenerator:
    """滑动窗口多轮大纲生成器

    支持任意起始点的增量生成。
    以对话窗口（50-100章）为单位累积上下文。
    使用 chapter_plan.yaml 的5章区间规划替代幕结构和梗概。
    """

    def __init__(
        self,
        config: Dict[str, Any],
        ai_role_manager: Any,
        core_setting: Dict[str, Any] = None,
        chapter_plan: Dict[str, Any] = None,
        existing_skeletons: Optional[Dict[str, Any]] = None,
        output_dir: Optional[Path] = None,
        conversation_window: int = 100,
        batch_size: int = 5,
    ):
        self.config = config
        self.ai_role_manager = ai_role_manager
        self.core_setting = core_setting or {}
        self.chapter_plan = chapter_plan or {}
        self.conversation_window = conversation_window
        self.batch_size = batch_size
        self.output_dir = output_dir or Path(".")
        self.logger = logging.getLogger(__name__)

        # 对话状态
        self.messages: List[Dict[str, str]] = []
        self.window_start: int = 0

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
        """构建system消息内容（含核心设定、故事概述）"""
        parts = []

        # 核心设定
        if self.core_setting:
            core_yaml = yaml.dump(
                self.core_setting, allow_unicode=True, default_flow_style=False
            )
            parts.append(f"【核心设定】\n{core_yaml}")

        # 故事概述
        story_overview = self.chapter_plan.get("故事概述", "")
        if story_overview:
            parts.append(f"\n【故事概述】\n{story_overview}")

        # 系统指令
        parts.append("\n【你的任务】")
        parts.append("你是一个专业的小说章节规划师，擅长设计章节骨架结构。")
        parts.append("你会收到5章区间的核心内容（箭头链接的事件链），需要将其合理分配到每一章中。")

        return "\n\n".join(parts)

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
        """构建批次生成提示词 - 使用5章区间规划，AI自动拆解分配"""
        batch_count = batch_end - batch_start + 1

        # 总章节数
        total_chapters = self.chapter_plan.get("总章节数", 793)

        lines = []
        lines.append(f"【任务】生成第{batch_start}-{batch_end}章的详细骨架（共{batch_count}章）")
        lines.append("")
        lines.append(f"• 本小说总章节数：{total_chapters}章")
        lines.append(f"• 当前批次位置：第{batch_start}-{batch_end}章")
        lines.append("")

        # === 核心内容注入 ===
        involved_plans = self._get_involved_plans(batch_start, batch_end)
        if involved_plans:
            lines.append("══════════════════════════════════════")
            lines.append("—— 【本章区间核心内容】——")
            lines.append("══════════════════════════════════════")
            lines.append("")
            lines.append("以下是第{}章区间的核心内容（箭头链接的事件链）：".format(
                ", ".join([p["range"] for p in involved_plans])
            ))
            lines.append("")
            for plan in involved_plans:
                range_key = plan["range"]
                data = plan["data"]
                core_content = data.get("核心内容", "")
                lines.append(f"{range_key}: {core_content}")
                constraints = data.get("关键约束", [])
                if constraints:
                    lines.append(f"  关键约束: {', '.join(constraints)}")
                lines.append("")

            lines.append("══════════════════════════════════════")
            lines.append("—— 【拆解分配规则】——")
            lines.append("══════════════════════════════════════")
            lines.append("")
            lines.append(f"你需要将上述核心内容**合理分配到第{batch_start}-{batch_end}章**中：")
            lines.append("1. 核心内容中的箭头链接事件（如'A→B→C'）是按时间顺序发生的关键节点")
            lines.append("2. 将这些事件节点分配到每一章，每章覆盖1个或部分事件节点")
            lines.append("3. 确保每章有完整的故事弧线，事件展开充分")
            lines.append("4. 章节之间剧情自然衔接，前章结尾导向后章开场")
            lines.append("5. 遵守关键约束，不得违反")
            lines.append("")

        # === 前文骨架上下文 ===
        prev_context = self._format_previous_skeletons(
            max(1, batch_start - 50), batch_start - 1, all_skeletons
        )
        if prev_context:
            lines.append("══════════════════════════════════════")
            lines.append("—— 【前文骨架（上下文）】——")
            lines.append("══════════════════════════════════════")
            lines.append("")
            lines.append(prev_context)
            lines.append("")
            lines.append("注意：与前文保持连贯，承接前章伏笔和结尾卡点。")
            lines.append("")

        # === 输出格式 ===
        lines.append("══════════════════════════════════════")
        lines.append("—— 【JSON 输出格式】——")
        lines.append("══════════════════════════════════════")
        lines.append("")
        lines.append("请以严格的JSON格式输出（必须使用英文双引号）：")
        lines.append("```json")
        lines.append("{")
        lines.append(f'  "第{batch_start}章": {{')
        lines.append('    "标题": "章节标题",')
        lines.append('    "字数目标": 2500,')
        lines.append('    "章节定位": "本章在整体故事中的角色",')
        lines.append('    "核心事件": "2-3句描述核心情节，写明因果链",')
        lines.append('    "与前章因果": "承接上章XX，推进YY，为下章ZZ埋笔",')
        lines.append('    "人物行动": {')
        lines.append('      "主角": "主角行动与动机",')
        lines.append('      "关键配角": "配角行动与主线关联"')
        lines.append("    },")
        lines.append('    "场景概览": ["开场：XX地点", "发展：XX地点", "高潮：XX地点", "收束：XX地点"],')
        lines.append('    "情绪曲线": "本章情绪走向（如：绝望→觉醒→决心）",')
        lines.append('    "伏笔处理": { "埋设": [], "回收": [] },')
        lines.append('    "结尾卡点": "章末悬念/钩子"')
        lines.append("  },")
        lines.append(f'  "第{batch_start+1}章": {{ ... }},')
        lines.append("  // ... 以此类推")
        lines.append(f'  "第{batch_end}章": {{ ... }}')
        lines.append("}")
        lines.append("```")
        lines.append("")
        lines.append(f"【严格要求】必须为第{batch_start}-{batch_end}章的每一章输出完整骨架，不得省略。")

        return "\n".join(lines)

    def _get_involved_plans(self, start_ch: int, end_ch: int) -> List[Dict[str, Any]]:
        """获取当前批次涉及的5章规划区间"""
        involved = []
        plan_data = self.chapter_plan.get("剧情规划", {})

        for range_key, plan_item in plan_data.items():
            match = re.search(r"第(\d+)-(\d+)章", range_key)
            if match:
                plan_start, plan_end = int(match.group(1)), int(match.group(2))
                if plan_start <= end_ch and plan_end >= start_ch:
                    involved.append({
                        "range": range_key,
                        "data": plan_item
                    })

        involved.sort(key=lambda x: int(re.search(r"第(\d+)", x["range"]).group(1)))
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

        self.outline_file = self.output_dir / "outline.json"
        # skeletons_file 与 outline_file 统一，不再生成两个文件
        self.skeletons_file = self.outline_file

    def verify_complete(
        self, skeletons: Dict[str, Any], expected_total: int
    ) -> Tuple[bool, List[int]]:
        """验证大纲完整性，返回(是否完整, 缺失章节列表)

        Args:
            skeletons: 章节骨架字典
            expected_total: 期望的总章数

        Returns:
            Tuple[bool, List[int]]: (是否完整, 缺失的章节号列表)
        """
        missing = []
        for ch in range(1, expected_total + 1):
            if f"第{ch}章" not in skeletons:
                missing.append(ch)

        is_complete = len(missing) == 0
        return is_complete, missing

    def report_missing_chapters(
        self, skeletons: Dict[str, Any], expected_total: int
    ) -> str:
        """生成缺失章节报告"""
        is_complete, missing = self.verify_complete(skeletons, expected_total)

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

    def generate_skeletons_only(
        self,
        core_setting: Dict[str, Any],
        chapter_plan: Dict[str, Any],
        chapter_range: Tuple[int, int] = None,
        batch_size: int = None,
        conversation_window: int = None,
    ) -> Dict[str, Any]:
        """
        仅执行章骨架生成（Stage 2）

        Args:
            core_setting: 核心设定
            chapter_plan: 章节规划（使用5章区间规划）
            chapter_range: 章节范围
            batch_size: 骨架批次大小
            conversation_window: 对话窗口大小

        Returns:
            Dict: 章级骨架结果
        """
        self.logger.info("开始章骨架生成（Stage 2）")

        total_chapters = chapter_plan.get("总章节数", 793)
        if chapter_range is None:
            chapter_range = (1, total_chapters)

        return self._generate_sliding_window_skeletons(
            core_setting, chapter_plan,
            chapter_range, batch_size, conversation_window
        )

    def _generate_sliding_window_skeletons(
        self,
        core_setting: Dict[str, Any],
        chapter_plan: Dict[str, Any],
        chapter_range: Tuple[int, int],
        batch_size: int,
        conversation_window: int,
    ) -> Dict[str, Any]:
        """使用滑动窗口多轮模式生成章级骨架"""
        start_ch, end_ch = chapter_range

        # 从配置获取默认值
        gen_config = self.config.get("generation", {})
        batch_size = batch_size or gen_config.get("skeleton_batch_size", 5)
        conversation_window = conversation_window or gen_config.get("conversation_window", 100)

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

        # 创建滑动窗口生成器（使用5章区间规划）
        generator = SlidingWindowSkeletonGenerator(
            config=self.config,
            ai_role_manager=self.ai_role_manager,
            core_setting=core_setting,
            chapter_plan=chapter_plan,
            output_dir=self.output_dir,
            conversation_window=conversation_window,
            batch_size=batch_size,
        )

        # 生成骨架
        final_skeletons = generator.generate_skeletons(
            chapter_range=(first_missing, end_ch),
            existing_skeletons=existing_skeletons if first_missing > start_ch else None,
        )

        # 合并结果
        existing_skeletons.update(final_skeletons)
        self._save_skeletons(existing_skeletons)

        self.logger.info(f"骨架生成完成，共{len(existing_skeletons)}章")
        return existing_skeletons

    def _extract_chapter_number(self, chapter_key: str) -> int:
        """从章节键提取章节号"""
        matched = re.search(r"(\d+)", str(chapter_key))
        if matched:
            return int(matched.group(1))
        return 0

    # ==================== 辅助方法 ====================

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
