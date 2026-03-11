"""
章节扩写器
负责基于大纲和滑动窗口技术生成章节内容
"""

import json
import yaml
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

from novel_generator.config.settings import Settings
from novel_generator.utils.multi_model_client import MultiModelClient


class RetryableGenerationError(Exception):
    pass


class ChapterExpander:
    """章节扩写器类"""
    
    def __init__(self, config: Dict[str, Any], multi_model_client: MultiModelClient = None):
        """
        初始化章节扩写器
        
        Args:
            config: 配置信息
            multi_model_client: 多模型客户端
        """
        self.config = config
        self.settings = Settings(config)
        self.logger = logging.getLogger(__name__)
        
        # 初始化AI API客户端
        if multi_model_client:
            self.multi_model_client = multi_model_client
        else:
            self.multi_model_client = MultiModelClient(config)
        
    def expand_chapter(self, chapter_num: int, 
                      chapter_outline: Dict[str, Any],
                      previous_context: str = "",
                      style_guide: Optional[Dict[str, Any]] = None) -> str:
        """
        扩写单个章节
        
        Args:
            chapter_num: 章节号
            chapter_outline: 章节大纲
            previous_context: 前序章节上下文
            style_guide: 风格指导
            
        Returns:
            str: 生成的章节内容
        """
        try:
            self.logger.info(f"开始扩写第{chapter_num}章...")
            
            # 构建提示词
            prompt = self._build_expand_prompt(
                chapter_num=chapter_num,
                chapter_outline=chapter_outline,
                previous_context=previous_context,
                style_guide=style_guide or {}
            )
            
            # 调用AI API
            response = self._call_ai_api(prompt)
            
            # 解析和优化响应
            content = self._parse_and_optimize_response(
                response=response,
                chapter_outline=chapter_outline,
                style_guide=style_guide or {}
            )
            
            self.logger.info(f"第{chapter_num}章扩写完成")
            return content
            
        except Exception as e:
            self.logger.error(f"扩写第{chapter_num}章失败: {e}")
            raise
    
    def _build_expand_prompt(self, chapter_num: int,
                           chapter_outline: Dict[str, Any],
                           previous_context: str,
                           style_guide: Dict[str, Any]) -> str:
        """构建章节扩写提示词"""
        
        # 加载章节扩写提示词模板
        prompt_template_path = Path(self.settings.path_config.prompt_dir) / "chapter_expand_prompt.yaml"
        try:
            with open(prompt_template_path, 'r', encoding='utf-8') as f:
                prompt_template = yaml.safe_load(f)['template']
        except:
            prompt_template = self._get_default_prompt_template()
        
        # 构建核心设定
        core_setting = self._load_core_setting()
        
        # 构建风格指导
        style_guide_str = self._format_style_guide(style_guide)
        
        # 构建上下文回顾
        context_str = self._build_context_review(previous_context, chapter_num)
        
        # 替换模板变量
        prompt = prompt_template.format(
            core_setting=json.dumps(core_setting, ensure_ascii=False),
            previous_context=context_str,
            chapter_outline=json.dumps(chapter_outline, ensure_ascii=False),
            style_guide=style_guide_str,
            word_count=self.settings.get_default_word_count(),
            key_scene=chapter_outline.get('核心事件', '')
        )
        
        return prompt
    
    def _get_default_prompt_template(self) -> str:
        """获取默认提示词模板"""
        return """
【任务】扩写小说章节，严格遵循以下要求：
  
1. 核心设定：{core_setting}
  
2. 上下文回顾：{previous_context}
   （前1-2章关键情节+人设，确保故事连贯性）
  
3. 本章大纲：{chapter_outline}
   （必须包含：标题、核心事件、场景、人物行动、伏笔回收）
  
4. 风格要求：{style_guide}
   （语言风格、对话特点、场景描写、禁忌等）
  
5. 输出要求：
   - 字数：必须严格控制在{word_count}字左右（误差不超过±100字）
   - 重点描写：{key_scene}
   - 格式：分段落，无冗余内容
   - 保持人物性格一致性
   - 注意伏笔的埋设和回收
   - 确保内容丰富，细节描写充分
   
请严格按照上述要求生成章节内容，确保故事逻辑连贯、人设统一、风格一致，并且字数符合要求。
"""
    
    def _load_core_setting(self) -> Dict[str, Any]:
        """加载核心设定"""
        try:
            core_setting_path = Path(self.settings.path_config.core_setting_file)
            with open(core_setting_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except:
            return {}
    
    def _format_style_guide(self, style_guide: Dict[str, Any]) -> str:
        """格式化风格指导"""
        result = []
        for key, value in style_guide.items():
            if isinstance(value, str) and value:
                result.append(f"{key}：{value}")
        return "；".join(result) if result else "无特殊要求"
    
    def _build_context_review(self, previous_context: str, chapter_num: int) -> str:
        """构建上下文回顾"""
        if not previous_context:
            return "无前序上下文"
        
        # 这里可以添加更复杂的上下文构建逻辑
        return previous_context
    
    def _call_ai_api(self, prompt: str) -> str:
        """调用AI API (Legacy wrapper)"""
        try:
            return self.multi_model_client.chat_completion(messages=[{"role": "user", "content": prompt}])
        except Exception as e:
            raise RetryableGenerationError(f"AI调用失败，可重试: {e}") from e
    
    def _get_mock_response(self) -> str:
        """获取模拟响应（用于测试）"""
        return """
清晨的阳光透过窗棂洒进小屋，照亮了空气中飞舞的尘埃。李明坐在书桌前，手中的毛笔在宣纸上缓缓移动，写下一个个苍劲有力的字迹。

"这已经是第三十遍了。"他轻声自语，放下毛笔，揉了揉有些酸涩的眼睛。

窗外，青山如黛，云雾缭绕。这里是青云村，一个远离尘嚣的小山村，也是李明出生和成长的地方。

"明儿，吃饭了！"母亲的声音从院子里传来。

"来了！"李明应了一声，迅速收拾好桌上的文房四宝。

走出房间，看到母亲已经准备好了早餐，简单的米粥和小菜，却散发着家的温暖。

"今天怎么起这么早？"母亲问道，一边为李明盛粥。

"想多练练字，听说城里的书院要招生了。"李明回答道，眼中闪烁着向往的光芒。

母亲欣慰地点点头："有志向是好事，但也要注意身体。"

用过早餐，李明来到村口的老槐树下。这里是他每天晨读的地方，也是他思考人生的地方。

"不知道外面的世界是什么样子。"他望着远方的群山，心中充满了憧憬。

就在这时，一位老者从山路上缓缓走来，手持一根竹杖，仙风道骨。

"小友，在此作甚？"老者问道，声音中带着一丝笑意。

李明连忙起身行礼："晚辈李明，在此晨读。"

老者上下打量了李明一番，眼中闪过一丝惊讶："小友根骨不凡，可有兴趣随老夫去外面走走？"

李明心中一动，但随即想到母亲："晚辈需要先征得母亲同意。"

老者微微一笑："这个无妨，老夫自会与你母亲相商。"

就这样，李明的人生轨迹即将发生改变...
"""
    
    def _parse_and_optimize_response(self, response: str,
                                   chapter_outline: Dict[str, Any],
                                   style_guide: Dict[str, Any]) -> str:
        """解析和优化AI响应"""
        try:
            # 基本清理
            content = response.strip()

            quality_result = self._evaluate_rule_quality(content, chapter_outline, style_guide)
            min_score = float(self.config.get('quality_gate', {}).get('min_score', 70))
            self.logger.info(
                f"规则评分: {quality_result['score']:.1f} / 100, "
                f"硬门槛通过: {quality_result['hard_pass']}"
            )
            if quality_result['soft_issues']:
                self.logger.warning("软性建议: " + "；".join(quality_result['soft_issues']))

            rewrite_needed = (not quality_result['hard_pass']) or quality_result['score'] < min_score
            if rewrite_needed:
                issue_text = quality_result['hard_issues'] if quality_result['hard_issues'] else quality_result['soft_issues']
                self.logger.warning("质量未达标，尝试自动重写一次: " + "；".join(issue_text[:5]))
                repaired_content = self._repair_content_once(
                    content=content,
                    chapter_outline=chapter_outline,
                    style_guide=style_guide,
                    hard_issues=quality_result['hard_issues'] if quality_result['hard_issues'] else quality_result['soft_issues']
                )
                if repaired_content:
                    repaired_result = self._evaluate_rule_quality(repaired_content, chapter_outline, style_guide)
                    if repaired_result['score'] >= quality_result['score']:
                        content = repaired_content
                        quality_result = repaired_result
                        self.logger.info(
                            f"自动修复后规则评分: {quality_result['score']:.1f} / 100, "
                            f"硬门槛通过: {quality_result['hard_pass']}"
                        )

            # 优化内容
            content = self._optimize_content(content)
            
            return content
            
        except Exception as e:
            self.logger.error(f"解析和优化响应失败: {e}")
            return response
    
    def _validate_content(self, content: str, chapter_outline: Dict[str, Any]) -> str:
        """
        (已弃用) 旧的机械验证逻辑
        """
        return content
    
    def _optimize_content(self, content: str) -> str:
        """优化内容"""
        # 这里可以添加内容优化逻辑
        return content

    def _evaluate_rule_quality(self, content: str,
                               chapter_outline: Dict[str, Any],
                               style_guide: Dict[str, Any]) -> Dict[str, Any]:
        """规则评分（硬门槛 + 软评分）"""
        target_count = self._get_target_word_count(chapter_outline)
        content_length = len(content)
        hard_issues: List[str] = []
        soft_issues: List[str] = []
        score = 100.0

        min_ratio = self.config.get('quality_gate', {}).get('min_ratio', 0.55)
        max_ratio = self.config.get('quality_gate', {}).get('max_ratio', 1.90)

        if target_count > 0:
            min_count = int(target_count * min_ratio)
            max_count = int(target_count * max_ratio)
            if content_length < min_count:
                hard_issues.append(f"字数偏少({content_length} < {min_count})")
            elif content_length < int(target_count * 0.8):
                soft_issues.append(f"字数略少({content_length} / 目标{target_count})")
                score -= 12
            elif content_length > max_count:
                hard_issues.append(f"字数过多({content_length} > {max_count})")
            elif content_length > int(target_count * 1.3):
                soft_issues.append(f"字数略多({content_length} / 目标{target_count})")
                score -= 8

        paragraphs = [line for line in content.splitlines() if line.strip()]
        if len(paragraphs) < 3:
            hard_issues.append("有效段落少于3段")
        elif len(paragraphs) < 5:
            soft_issues.append("段落偏少，可增加节奏变化")
            score -= 6

        core_event = str(chapter_outline.get('核心事件', '')).strip()
        if core_event:
            key_tokens = [token for token in re.split(r'[，。；、\s]+', core_event) if len(token) >= 2]
            if key_tokens:
                hit_count = sum(1 for token in key_tokens[:5] if token in content)
                if hit_count == 0:
                    soft_issues.append("核心事件关联词命中不足")
                    score -= 10
                elif hit_count <= 1:
                    soft_issues.append("核心事件展开可再加强")
                    score -= 5

        banned_words = self._get_banned_words(style_guide)
        hit_banned = [word for word in banned_words if word and word in content]
        if hit_banned:
            soft_issues.append(f"命中禁忌词: {', '.join(hit_banned[:5])}")
            score -= min(18, 4 * len(hit_banned))

        if re.search(r'([！？。])\1{2,}', content):
            soft_issues.append("存在连续重复标点")
            score -= 5

        score = max(0.0, min(100.0, score))
        return {
            "hard_pass": len(hard_issues) == 0,
            "hard_issues": hard_issues,
            "soft_issues": soft_issues,
            "score": score
        }

    def _repair_content_once(self, content: str,
                             chapter_outline: Dict[str, Any],
                             style_guide: Dict[str, Any],
                             hard_issues: List[str]) -> str:
        """基于硬门槛问题执行一次自动修复"""
        try:
            prompt = f"""请对以下小说章节进行一次修订，修复硬性问题，并保持原剧情不变。

【硬性问题】
{'; '.join(hard_issues)}

【章节大纲】
{json.dumps(chapter_outline, ensure_ascii=False)}

【风格约束】
{self._format_style_guide(style_guide)}

【原始正文】
{content}

【修订要求】
1. 保留原有剧情走向与人物关系。
2. 仅修复硬性问题，不要改成摘要。
3. 输出仅正文，不要解释。"""
            return self._call_ai_api(prompt).strip()
        except Exception as e:
            self.logger.warning(f"自动修复失败: {e}")
            return ""

    def _get_target_word_count(self, chapter_outline: Dict[str, Any]) -> int:
        """从章节大纲中提取目标字数"""
        raw_value = chapter_outline.get('字数目标', self.settings.get_default_word_count())
        if isinstance(raw_value, int):
            return raw_value
        if isinstance(raw_value, str):
            matched = re.search(r'(\d+)', raw_value)
            if matched:
                return int(matched.group(1))
        return self.settings.get_default_word_count()

    def _get_banned_words(self, style_guide: Dict[str, Any]) -> List[str]:
        """获取禁忌词列表（优先使用配置，其次使用默认词）"""
        configured_words = self.config.get('quality_gate', {}).get('banned_words', [])
        if isinstance(configured_words, list) and configured_words:
            return [str(word).strip() for word in configured_words if str(word).strip()]

        default_words = [
            "复杂的思绪", "难以言喻", "命运的齿轮", "心中五味杂陈",
            "一种莫名的", "仿佛", "似乎", "这一刻"
        ]
        guide_words: List[str] = []
        for key, value in style_guide.items():
            if "禁" in str(key) and isinstance(value, str):
                guide_words.extend([w.strip() for w in re.split(r'[，,；;、\n]', value) if w.strip()])
        return list(dict.fromkeys(default_words + guide_words))

    def save_chapter(self, chapter_num: int, content: str, 
                    output_dir: str, backup: bool = True) -> str:
        """
        保存章节内容
        
        Args:
            chapter_num: 章节号
            content: 章节内容
            output_dir: 输出目录
            backup: 是否备份
            
        Returns:
            str: 实际保存路径
        """
        try:
            # 清理内容
            content = self._clean_content(content)
            
            output_path = Path(output_dir) / f"chapter_{chapter_num:02d}.txt"
            
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 备份现有文件
            if backup and output_path.exists():
                backup_path = self._backup_chapter(output_path, chapter_num)
                self.logger.info(f"备份章节文件: {backup_path}")
            
            # 保存新文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

            state_card = self._generate_state_card(chapter_num, content)
            state_path = output_path.parent / f"chapter_{chapter_num:02d}.state.yaml"
            with open(state_path, 'w', encoding='utf-8') as f:
                yaml.dump(state_card, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

            summary_text = str(state_card.get("章节摘要", "")).strip()
            if summary_text:
                summary_path = output_path.parent / f"chapter_{chapter_num:02d}.summary"
                with open(summary_path, 'w', encoding='utf-8') as f:
                    f.write(f"=== 第{chapter_num}章 剧情状态卡 ===\n{summary_text}")
            
            self.logger.info(f"章节文件保存成功: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"保存章节文件失败: {e}")
            raise

    def _clean_content(self, content: str) -> str:
        """
        清理内容，移除所有空行
        
        Args:
            content: 原始内容
            
        Returns:
            str: 清理后的内容
        """
        if not content:
            return ""
            
        lines = content.splitlines()
        # 只保留非空行
        cleaned_lines = [line for line in lines if line.strip()]
        # 用单个换行符连接，形成紧凑的文本块
        return '\n'.join(cleaned_lines)

    def _generate_state_card(self, chapter_num: int, content: str) -> Dict[str, Any]:
        snippet = content[:2600] if len(content) > 2600 else content
        try:
            prompt = f"""请为小说第{chapter_num}章生成结构化剧情状态卡。
仅输出YAML，字段固定为：
章节标题:
章节摘要:
时间:
地点:
人物状态:
道具变动:
悬念:

其中“人物状态/道具变动/悬念”必须是列表。

原文：
{snippet}"""
            response = self.multi_model_client.chat_completion(
                stage='stage1',
                messages=[
                    {'role': 'system', 'content': '你是小说连续性分析助手，擅长提取结构化状态信息。'},
                    {'role': 'user', 'content': prompt}
                ]
            )
            cleaned = self._clean_yaml_response(response)
            parsed = yaml.safe_load(cleaned)
            if isinstance(parsed, dict):
                return self._normalize_state_card(parsed, chapter_num)
        except Exception as e:
            self.logger.warning(f"生成状态卡失败: {e}")
        return self._fallback_state_card(chapter_num, content)

    def _clean_yaml_response(self, response: str) -> str:
        lines = response.split('\n')
        cleaned_lines = []
        for line in lines:
            if line.strip() in ['```yaml', '```yml', '```']:
                continue
            cleaned_lines.append(line)
        return '\n'.join(cleaned_lines).strip()

    def _normalize_state_card(self, state_card: Dict[str, Any], chapter_num: int) -> Dict[str, Any]:
        normalized = {
            "章节标题": str(state_card.get("章节标题", f"第{chapter_num}章")).strip(),
            "章节摘要": str(state_card.get("章节摘要", "")).strip(),
            "时间": str(state_card.get("时间", "未明确")).strip(),
            "地点": str(state_card.get("地点", "未明确")).strip(),
            "人物状态": self._ensure_list(state_card.get("人物状态", [])),
            "道具变动": self._ensure_list(state_card.get("道具变动", [])),
            "悬念": self._ensure_list(state_card.get("悬念", []))
        }
        if not normalized["章节摘要"]:
            normalized["章节摘要"] = self._fallback_summary_text(chapter_num, "")
        return normalized

    def _ensure_list(self, value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in re.split(r'[，,；;\n、]', value) if item.strip()]
        return []

    def _fallback_summary_text(self, chapter_num: int, content: str) -> str:
        text = content.replace('\n', ' ').strip()
        if not text:
            return f"第{chapter_num}章主要情节待补充。"
        if len(text) > 180:
            return text[:180] + "..."
        return text

    def _fallback_state_card(self, chapter_num: int, content: str) -> Dict[str, Any]:
        return {
            "章节标题": f"第{chapter_num}章",
            "章节摘要": self._fallback_summary_text(chapter_num, content),
            "时间": "未明确",
            "地点": "未明确",
            "人物状态": [],
            "道具变动": [],
            "悬念": []
        }

    
    def _backup_chapter(self, file_path: Path, chapter_num: int) -> str:
        """
        备份章节文件
        注意：此方法保留是为了兼容性，但不再创建 draft_history 目录
        如果需要备份功能，建议使用版本控制系统
        """
        # 功能已禁用，直接返回空路径
        return ""
    
    def expand_multiple_chapters(self, chapter_range: Tuple[int, int],
                                outline_file: str,
                                style_guide: Optional[Dict[str, Any]] = None) -> bool:
        """
        扩写多个章节
        
        Args:
            chapter_range: 章节范围
            outline_file: 大纲文件路径
            style_guide: 风格指导
            
        Returns:
            bool: 是否成功
        """
        try:
            self.logger.info(f"开始批量扩写章节 {chapter_range[0]}-{chapter_range[1]}...")
            
            # 加载大纲
            with open(outline_file, 'r', encoding='utf-8') as f:
                outline = yaml.safe_load(f)
            
            # 构建滑动窗口上下文
            context_window = self.settings.get_context_chapters()
            previous_context = ""
            
            success_count = 0
            total_count = chapter_range[1] - chapter_range[0] + 1
            
            for chapter_num in range(chapter_range[0], chapter_range[1] + 1):
                if str(f"第{chapter_num}章") in outline:
                    chapter_outline = outline[str(f"第{chapter_num}章")]
                    
                    # 扩写章节（这里会调用真实的AI API）
                    content = self.expand_chapter(
                        chapter_num=chapter_num,
                        chapter_outline=chapter_outline,
                        previous_context=previous_context,
                        style_guide=style_guide
                    )
                    
                    # 保存章节
                    output_dir = Path(self.settings.path_config.draft_dir)
                    self.save_chapter(chapter_num, content, str(output_dir))
                    
                    # 更新上下文
                    if chapter_num > context_window:
                        # 移除最旧的章节
                        old_chapter = chapter_num - context_window - 1
                        if old_chapter >= chapter_range[0]:
                            old_content_file_txt = output_dir / f"chapter_{old_chapter:02d}.txt"
                            old_content_file_md = output_dir / f"chapter_{old_chapter:02d}.md"
                            
                            old_content_file = None
                            if old_content_file_txt.exists():
                                old_content_file = old_content_file_txt
                            elif old_content_file_md.exists():
                                old_content_file = old_content_file_md
                                
                            if old_content_file:
                                with open(old_content_file, 'r', encoding='utf-8') as f:
                                    old_content = f.read()
                                previous_context = previous_context.replace(
                                    old_content[:200],  # 移除旧内容开头部分
                                    ""
                                )
                    
                    # 添加新章节到上下文
                    new_content_file_txt = output_dir / f"chapter_{chapter_num:02d}.txt"
                    new_content_file_md = output_dir / f"chapter_{chapter_num:02d}.md"
                    
                    new_content_file = None
                    if new_content_file_txt.exists():
                        new_content_file = new_content_file_txt
                    elif new_content_file_md.exists():
                        new_content_file = new_content_file_md
                        
                    if new_content_file:
                        with open(new_content_file, 'r', encoding='utf-8') as f:
                            new_content = f.read()
                        previous_context += f"\n\n=== 第{chapter_num}章 ===\n{new_content}"
                    
                    success_count += 1
                    self.logger.info(f"第{chapter_num}章扩写完成 ({success_count}/{total_count})")
                else:
                    self.logger.warning(f"第{chapter_num}章大纲不存在，跳过")
            
            self.logger.info(f"批量扩写完成：{success_count}/{total_count} 章节成功")
            return success_count == total_count
            
        except Exception as e:
            self.logger.error(f"批量扩写失败: {e}")
            return False
