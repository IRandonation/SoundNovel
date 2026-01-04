"""
滑动窗口模块
实现章节扩写的滑动窗口逻辑，确保故事连贯性
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

from novel_generator.config.settings import Settings


class SlidingWindow:
    """滑动窗口类"""
    
    def __init__(self, config: Dict[str, Any], multi_model_client=None):
        """
        初始化滑动窗口
        
        Args:
            config: 配置信息
            multi_model_client: 多模型客户端
        """
        self.config = config
        self.settings = Settings(config)
        self.logger = logging.getLogger(__name__)
        self.window_size = self.settings.get_context_chapters()
        self.context_cache = {}
        self.multi_model_client = multi_model_client
        
    def build_context(self, current_chapter: int, 
                     available_chapters: List[int],
                     draft_dir: str) -> str:
        """
        构建滑动窗口上下文
        
        Args:
            current_chapter: 当前章节号
            available_chapters: 可用章节列表
            draft_dir: 草稿目录
            
        Returns:
            str: 上下文内容
        """
        try:
            self.logger.info(f"为第{current_chapter}章构建上下文，窗口大小: {self.window_size}")
            
            # 获取前序章节
            previous_chapters = self._get_previous_chapters(
                current_chapter, available_chapters
            )
            
            # 构建上下文
            context = self._build_context_from_chapters(
                previous_chapters, draft_dir
            )
            
            # 缓存上下文
            self.context_cache[current_chapter] = context
            
            self.logger.info(f"上下文构建完成，长度: {len(context)} 字符")
            return context
            
        except Exception as e:
            self.logger.error(f"构建上下文失败: {e}")
            return ""
    
    def _get_previous_chapters(self, current_chapter: int, 
                             available_chapters: List[int]) -> List[int]:
        """
        获取前序章节列表
        
        Args:
            current_chapter: 当前章节号
            available_chapters: 可用章节列表
            
        Returns:
            List[int]: 前序章节号列表
        """
        # 获取当前章节之前的所有章节
        previous_chapters = [ch for ch in available_chapters if ch < current_chapter]
        
        # 只取最近的window_size个章节
        return previous_chapters[-self.window_size:] if len(previous_chapters) > self.window_size else previous_chapters
    
    def _build_context_from_chapters(self, chapter_numbers: List[int], 
                                   draft_dir: str) -> str:
        """
        从章节文件构建上下文
        
        Args:
            chapter_numbers: 章节号列表
            draft_dir: 草稿目录
            
        Returns:
            str: 上下文内容
        """
        context_parts = []
        draft_path = Path(draft_dir)
        
        for chapter_num in chapter_numbers:
            chapter_file = draft_path / f"chapter_{chapter_num:02d}.md"
            
            if chapter_file.exists():
                try:
                    with open(chapter_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 提取关键信息
                    key_info = self._extract_key_info(content, chapter_num, draft_dir)
                    context_parts.append(key_info)
                    
                except Exception as e:
                    self.logger.warning(f"读取第{chapter_num}章失败: {e}")
            else:
                self.logger.warning(f"第{chapter_num}章文件不存在: {chapter_file}")
        
        return "\n\n".join(context_parts)
    
    def _extract_key_info(self, content: str, chapter_num: int, draft_dir: str = None) -> str:
        """
        从章节内容中提取关键信息
        
        Args:
            content: 章节内容
            chapter_num: 章节号
            draft_dir: 草稿目录
            
        Returns:
            str: 关键信息
        """
        # 1. 尝试读取已存在的摘要文件
        if draft_dir:
            summary_path = Path(draft_dir) / f"chapter_{chapter_num:02d}.summary"
            if summary_path.exists():
                try:
                    with open(summary_path, 'r', encoding='utf-8') as f:
                        return f.read()
                except Exception as e:
                    self.logger.warning(f"读取摘要文件失败: {e}")

        # 2. 如果有 LLM 客户端，使用 LLM 生成摘要
        if self.multi_model_client:
            summary = self._generate_llm_summary(content, chapter_num)
            if summary:
                # 保存摘要
                if draft_dir:
                    try:
                        summary_path = Path(draft_dir) / f"chapter_{chapter_num:02d}.summary"
                        with open(summary_path, 'w', encoding='utf-8') as f:
                            f.write(summary)
                    except Exception as e:
                        self.logger.warning(f"保存摘要文件失败: {e}")
                return summary

        # 3. 降级方案：使用关键词提取
        # 提取章节标题（如果有）
        title = ""
        lines = content.split('\n')
        for line in lines:
            if line.startswith('#') and '第' in line and '章' in line:
                title = line.strip()
                break
        
        # 提取主要人物和事件
        key_events = []
        key_characters = []
        
        # 简单的关键词提取（实际应用中可以使用更复杂的NLP技术）
        event_keywords = ['发现', '遇到', '决定', '前往', '战斗', '学习', '获得', '失去']
        character_keywords = ['主角', '李明', '老者', '母亲', '朋友', '敌人']
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 检测事件关键词
            for keyword in event_keywords:
                if keyword in line:
                    key_events.append(line)
                    break
            
            # 检测人物关键词
            for keyword in character_keywords:
                if keyword in line:
                    key_characters.append(line)
                    break
        
        # 构建关键信息
        key_info = f"=== 第{chapter_num}章 {title} ===\n"
        
        if key_characters:
            key_info += f"主要人物: {'；'.join(key_characters[:3])}\n"
        
        if key_events:
            key_info += f"关键事件: {'；'.join(key_events[:3])}\n"
        
        # 添加章节开头和结尾
        if lines:
            key_info += f"章节开头: {lines[0][:50]}...\n"
            key_info += f"章节结尾: {lines[-1][:50]}...\n"
        
        return key_info
    
    def _generate_llm_summary(self, content: str, chapter_num: int) -> str:
        """使用 LLM 生成章节摘要"""
        try:
            self.logger.info(f"正在为第{chapter_num}章生成智能摘要...")
            
            # 截取适当长度的内容以避免超出 context window，保留开头和结尾
            if len(content) > 5000:
                content_snippet = content[:3000] + "\n...\n" + content[-2000:]
            else:
                content_snippet = content

            prompt = f"""请为小说第{chapter_num}章生成一份"剧情状态卡"，用于辅助下一章的创作。
要求提取以下信息（保持简洁，总字数控制在300字以内）：
1. 章节标题与核心事件：
2. 当前时间与地点：
3. 关键人物身心状态（位置、伤情、心情）：
4. 关键物品/道具变动：
5. 本章留下的即时悬念/未解决问题：

原文内容：
{content_snippet}
"""
            # 使用 logic_analysis_model
            summary = self.multi_model_client.chat_completion(
                stage='stage1',
                messages=[
                    {'role': 'system', 'content': '你是一个专业的小说助手，擅长分析剧情和提取关键信息。'},
                    {'role': 'user', 'content': prompt}
                ]
            )
            
            return f"=== 第{chapter_num}章 剧情状态卡 ===\n{summary}"
            
        except Exception as e:
            self.logger.error(f"生成摘要失败: {e}")
            return None

    def optimize_window(self, current_chapter: int,
                       context: str,
                       chapter_outline: Dict[str, Any]) -> str:
        """
        优化窗口上下文
        
        Args:
            current_chapter: 当前章节号
            context: 原始上下文
            chapter_outline: 当前章节大纲
            
        Returns:
            str: 优化后的上下文
        """
        try:
            # 如果上下文为空，创建基础上下文
            if not context:
                context = self._create_basic_context(current_chapter, chapter_outline)
            
            # 根据当前章节大纲调整上下文权重
            optimized_context = self._weight_context_by_outline(
                context, chapter_outline
            )
            
            # 确保上下文长度适中
            optimized_context = self._adjust_context_length(optimized_context)
            
            return optimized_context
            
        except Exception as e:
            self.logger.error(f"优化上下文失败: {e}")
            return context if context else self._create_basic_context(current_chapter, chapter_outline)
    
    def _weight_context_by_outline(self, context: str, 
                                  chapter_outline: Dict[str, Any]) -> str:
        """
        根据章节大纲调整上下文权重
        
        Args:
            context: 原始上下文
            chapter_outline: 章节大纲
            
        Returns:
            str: 加权后的上下文
        """
        # 提取当前章节的关键词
        core_event = chapter_outline.get('核心事件', '')
        key_characters = chapter_outline.get('主要人物', [])
        key_locations = chapter_outline.get('场景', '').split('、')
        
        # 这里可以实现更复杂的上下文加权逻辑
        # 例如：与当前章节相关的上下文信息给予更高权重
        
        return context
    
    def _adjust_context_length(self, context: str) -> str:
        """
        调整上下文长度
        
        Args:
            context: 原始上下文
            
        Returns:
            str: 调整后的上下文
        """
        # 计算目标长度（基于当前章节字数的比例）
        target_length = self.settings.get_default_word_count() * 2  # 上下文长度约为章节长度的2倍
        
        if len(context) > target_length * 1.5:
            # 如果上下文过长，进行截断
            # 保留最重要的信息（章节标题、关键事件、人物状态）
            lines = context.split('\n')
            important_lines = []
            
            for line in lines:
                if any(keyword in line for keyword in ['=== 第', '主要人物:', '关键事件:']):
                    important_lines.append(line)
                elif len(important_lines) < 10:  # 限制重要信息数量
                    important_lines.append(line)
            
            context = '\n'.join(important_lines)
        
        return context
    
    def _create_basic_context(self, current_chapter: int,
                            chapter_outline: Dict[str, Any]) -> str:
        """
        创建基础上下文（当没有前序章节时使用）
        
        Args:
            current_chapter: 当前章节号
            chapter_outline: 当前章节大纲
            
        Returns:
            str: 基础上下文
        """
        basic_context = f"=== 第{current_chapter}章 {chapter_outline.get('标题', '未知章节')} ===\n"
        basic_context += f"核心事件: {chapter_outline.get('核心事件', '')}\n"
        
        # 添加场景信息
        scene = chapter_outline.get('场景', '')
        if scene:
            basic_context += f"场景: {scene}\n"
        
        # 添加人物行动信息
        character_action = chapter_outline.get('人物行动', '')
        if character_action:
            basic_context += f"人物行动: {character_action}\n"
        
        # 添加伏笔回收信息
        foreshadowing = chapter_outline.get('伏笔回收', '')
        if foreshadowing:
            basic_context += f"伏笔回收: {foreshadowing}\n"
        
        # 添加字数目标
        word_count = chapter_outline.get('字数目标', 1500)
        basic_context += f"字数目标: {word_count}\n"
        
        return basic_context
    
    def get_context_similarity(self, context1: str, context2: str) -> float:
        """
        计算两个上下文之间的相似度
        
        Args:
            context1: 第一个上下文
            context2: 第二个上下文
            
        Returns:
            float: 相似度分数（0-1）
        """
        try:
            # 简单的词汇重叠度计算
            words1 = set(context1.lower().split())
            words2 = set(context2.lower().split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            similarity = len(intersection) / len(union)
            return similarity
            
        except Exception as e:
            self.logger.error(f"计算上下文相似度失败: {e}")
            return 0.0
    
    def detect_context_break(self, current_context: str, 
                           previous_context: str) -> bool:
        """
        检测上下文断裂
        
        Args:
            current_context: 当前上下文
            previous_context: 前序上下文
            
        Returns:
            bool: 是否检测到断裂
        """
        try:
            # 计算相似度
            similarity = self.get_context_similarity(current_context, previous_context)
            
            # 如果相似度低于阈值，认为存在断裂
            threshold = 0.3  # 可调整的阈值
            return similarity < threshold
            
        except Exception as e:
            self.logger.error(f"检测上下文断裂失败: {e}")
            return False
    
    def repair_context_break(self, current_chapter: int, 
                            draft_dir: str) -> str:
        """
        修复上下文断裂
        
        Args:
            current_chapter: 当前章节号
            draft_dir: 草稿目录
            
        Returns:
            str: 修复后的上下文
        """
        try:
            self.logger.warning(f"检测到第{current_chapter}章上下文断裂，尝试修复...")
            
            # 重新构建上下文
            available_chapters = self._get_available_chapters(draft_dir)
            new_context = self.build_context(current_chapter, available_chapters, draft_dir)
            
            # 验证修复效果
            if current_chapter > 1:
                previous_context = self.context_cache.get(current_chapter - 1, "")
                if self.detect_context_break(new_context, previous_context):
                    self.logger.error("上下文修复失败，可能需要人工干预")
                    return ""
            
            self.logger.info("上下文修复完成")
            return new_context
            
        except Exception as e:
            self.logger.error(f"修复上下文断裂失败: {e}")
            return ""
    
    def _get_available_chapters(self, draft_dir: str) -> List[int]:
        """
        获取可用章节列表
        
        Args:
            draft_dir: 草稿目录
            
        Returns:
            List[int]: 可用章节号列表
        """
        available_chapters = []
        draft_path = Path(draft_dir)
        
        for file_path in draft_path.glob("chapter_*.md"):
            try:
                # 从文件名提取章节号
                chapter_num = int(file_path.stem.split('_')[1])
                available_chapters.append(chapter_num)
            except (IndexError, ValueError):
                continue
        
        return sorted(available_chapters)
    
    def clear_cache(self):
        """清除上下文缓存"""
        self.context_cache.clear()
        self.logger.info("上下文缓存已清除")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        return {
            "cache_size": len(self.context_cache),
            "window_size": self.window_size,
            "cached_chapters": list(self.context_cache.keys())
        }


class ContextManager:
    """上下文管理器"""
    
    def __init__(self, config: Dict[str, Any], multi_model_client=None):
        """
        初始化上下文管理器
        
        Args:
            config: 配置信息
            multi_model_client: 多模型客户端
        """
        self.config = config
        self.settings = Settings(config)
        self.sliding_window = SlidingWindow(config, multi_model_client)
        self.logger = logging.getLogger(__name__)
        
    def prepare_context(self, current_chapter: int, 
                       outline_file: str, 
                       draft_dir: str) -> Tuple[str, bool]:
        """
        准备章节扩写所需的上下文
        
        Args:
            current_chapter: 当前章节号
            outline_file: 大纲文件路径
            draft_dir: 草稿目录
            
        Returns:
            Tuple[str, bool]: (上下文内容, 是否需要修复)
        """
        try:
            self.logger.info(f"准备第{current_chapter}章的上下文...")
            
            # 获取可用章节
            available_chapters = self.sliding_window._get_available_chapters(draft_dir)
            
            # 构建上下文
            context = self.sliding_window.build_context(
                current_chapter, available_chapters, draft_dir
            )
            
            # 检测上下文断裂
            needs_repair = False
            if current_chapter > 1 and context:
                previous_context = self.sliding_window.context_cache.get(current_chapter - 1, "")
                if self.sliding_window.detect_context_break(context, previous_context):
                    context = self.sliding_window.repair_context_break(
                        current_chapter, draft_dir
                    )
                    needs_repair = True
            
            # 优化上下文
            if context:
                # 加载当前章节大纲
                with open(outline_file, 'r', encoding='utf-8') as f:
                    outline = yaml.safe_load(f)
                
                if str(f"第{current_chapter}章") in outline:
                    chapter_outline = outline[str(f"第{current_chapter}章")]
                    context = self.sliding_window.optimize_window(
                        current_chapter, context, chapter_outline
                    )
            
            self.logger.info(f"上下文准备完成，需要修复: {needs_repair}")
            return context, needs_repair
            
        except Exception as e:
            self.logger.error(f"准备上下文失败: {e}")
            return "", False