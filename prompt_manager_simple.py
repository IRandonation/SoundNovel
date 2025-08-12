#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版提示词管理器
专注于基础的prompt构建，支持风格配置和上下文感知
"""

import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class NarrativeVoice(Enum):
    """叙事视角"""
    FIRST_PERSON = "第一人称"
    THIRD_PERSON_LIMITED = "第三人称有限视角"
    THIRD_PERSON_OMNISCIENT = "第三人称全知视角"


class Tone(Enum):
    """叙事语气"""
    SERIOUS = "严肃"
    HUMOROUS = "幽默"
    CASUAL = "轻松"
    FORMAL = "正式"


@dataclass
class StyleProfile:
    """风格配置文件"""
    narrative_voice: NarrativeVoice = NarrativeVoice.THIRD_PERSON_LIMITED
    tone: Tone = Tone.CASUAL
    description_density: float = 0.5  # 0-1，描写密度
    dialogue_ratio: float = 0.3  # 0-1，对话占比
    complexity_level: float = 0.5  # 0-1，复杂度


class SimplePromptManager:
    """简化版提示词管理器"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 初始化风格配置
        self.style_profile = self._init_style_profile()
        
        # 初始化提示词模板
        self.templates = self._init_templates()
    
    def _init_style_profile(self) -> StyleProfile:
        """初始化风格配置"""
        # 从配置中提取风格信息
        writing_style = self.config.get("writing_style", "")
        
        profile = StyleProfile()
        
        # 分析写作风格并设置相应参数
        if "幽默" in writing_style:
            profile.tone = Tone.HUMOROUS
        elif "严肃" in writing_style or "正式" in writing_style:
            profile.tone = Tone.SERIOUS
            profile.complexity_level = 0.8
        elif "轻松" in writing_style:
            profile.tone = Tone.CASUAL
            profile.complexity_level = 0.3
        
        if "描写丰富" in writing_style or "环境描写" in writing_style:
            profile.description_density = 0.8
        elif "简洁" in writing_style:
            profile.description_density = 0.3
        
        if "对话多" in writing_style:
            profile.dialogue_ratio = 0.6
        
        return profile
    
    def _init_templates(self) -> Dict:
        """初始化提示词模板"""
        templates = {
            "system_prompt": """你是一位资深小说作家，擅长文本改写和风格重塑。请按照以下设定进行高质量改写：

【世界观设定】
{worldview}

【写作风格】
{writing_style}

【文学手法要求】
{literary_techniques}

【风格配置】
{style_profile}

【改写核心要求】
1. 保持原文核心情节和人物关系不变，但彻底重塑表达方式和叙事结构
2. 确保改写后字数与原文相近（误差控制在±20%以内），不能过短
3. 严格遵循世界观设定，自然融入风格特征
4. 合理运用指定文学手法，增强文本表现力
5. 保持人物性格一致性，确保剧情逻辑连贯
6. 避免直接复制原文句式，用不同的表达方式传递相同信息
7. 保持段落结构完整性，确保上下文衔接自然流畅

【输出要求】
请直接输出改写后的文本，不要添加任何说明或解释。""",
            
            "user_prompt": """请改写以下文本，注意保持字数相近：

【原文】
{text}

【改写要求】
1. 保持核心情节和人物关系
2. 重塑表达方式，避免相似度过高
3. 确保改写后字数与原文相近
4. 自然融入世界观和风格特征
5. 遵循上述文学手法要求

{context_info}""",
            
            "long_text_user_prompt": """请改写以下长文本段落，注意保持情节连贯性和字数相近：

【原文 - 文本块 {chunk_id}】
{text}

【长文本改写要求】
1. 保持核心情节、人物关系和世界观设定
2. 重塑表达方式，避免相似度过高，但确保情节逻辑连贯
3. 确保改写后字数与原文相近（误差控制在±15%以内）
4. 充分利用长文本优势，保持上下文连贯性和情节发展逻辑
5. 自然融入世界观和风格特征，确保人物性格一致性
6. 遵循上述文学手法要求，注重修炼体系和境界描写
7. 确保段落结构完整，上下文衔接自然流畅

{context_info}

【重要提示】
- 这是长文本处理，请特别注意情节的连贯性和逻辑性
- 避免在段落中间突然改变叙事风格或人物性格
- 确保改写后的文本能够独立成章，同时与整体情节保持一致""",
            
            "ultra_long_text_user_prompt": """请改写以下超长文本段落，这是1M上下文处理的一部分，请特别注意整体连贯性：

【原文 - 文本块 {chunk_id}（长度：{text_length}字符）】
{text}

【超长文本改写要求】
1. 保持核心情节、人物关系和世界观设定的完整性
2. 重塑表达方式，避免相似度过高，但确保超长文本的情节逻辑连贯
3. 确保改写后字数与原文相近（误差控制在±10%以内）
4. 充分利用1M上下文优势，保持超长文本的上下文连贯性和情节发展逻辑
5. 自然融入世界观和风格特征，确保人物性格在超长文本中的一致性
6. 遵循上述文学手法要求，注重修炼体系和境界描写的连贯性
7. 确保段落结构完整，上下文衔接自然流畅，为后续处理提供良好基础

【超长文本处理策略】
- 这是超长文本处理的关键部分，请特别注意与前文和后文的衔接
- 保持叙事风格和人物性格在整个超长文本中的统一性
- 确保改写后的文本能够与前后文无缝衔接
- 适当增加过渡性内容，确保情节发展的连贯性

【重要提示】
- 这是1M上下文处理的核心部分，请特别注意整体故事的连贯性
- 避免在超长文本中间突然改变叙事风格或人物性格
- 确保改写后的文本能够作为超长文本的重要组成部分，保持整体一致性"""
        }
        
        return templates
    
    def build_prompt(self, text: str, chunk_id: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """构建提示词"""
        # 准备基本参数
        worldview = self.config.get("worldview", "通用现代世界观")
        writing_style = self.config.get("writing_style", "中立客观风格")
        literary_techniques = "，".join(self.config.get("literary_techniques", [])) or "无特殊要求"
        
        # 格式化风格配置
        style_profile_str = self._format_style_profile()
        
        # 构建上下文信息
        context_info = self._build_context_info(metadata)
        
        # 检查文本长度类型
        text_length = len(text)
        is_long_text = text_length > 10000
        is_ultra_long = text_length > 50000
        
        # 渲染提示词
        system_prompt = self.templates["system_prompt"].format(
            worldview=worldview,
            writing_style=writing_style,
            literary_techniques=literary_techniques,
            style_profile=style_profile_str
        )
        
        # 根据文本长度选择不同的用户提示词模板
        if is_ultra_long:
            user_prompt = self.templates["ultra_long_text_user_prompt"].format(
                text=text,
                context_info=context_info,
                chunk_id=chunk_id,
                text_length=text_length
            )
        elif is_long_text:
            user_prompt = self.templates["long_text_user_prompt"].format(
                text=text,
                context_info=context_info,
                chunk_id=chunk_id
            )
        else:
            user_prompt = self.templates["user_prompt"].format(
                text=text,
                context_info=context_info
            )
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    def _format_style_profile(self) -> str:
        """格式化风格配置"""
        profile = self.style_profile
        
        return f"""【叙事视角】{profile.narrative_voice.value}
【叙事语气】{profile.tone.value}
【描写密度】{profile.description_density:.1f}（0-1，0为最少描写，1为最多描写）
【对话比例】{profile.dialogue_ratio:.1f}（0-1，对话在文本中的占比）
【复杂度水平】{profile.complexity_level:.1f}（0-1，0为最简单，1为最复杂）"""
    
    def _build_context_info(self, metadata: Optional[Dict] = None) -> str:
        """构建上下文信息字符串"""
        context_parts = []
        
        # 添加元数据信息
        if metadata:
            if 'document_title' in metadata:
                context_parts.append(f"文档标题: {metadata['document_title']}")
            if 'source_file' in metadata:
                context_parts.append(f"来源文件: {metadata['source_file']}")
        
        # 如果有上下文部分，添加标题
        if context_parts:
            return "\n【上下文信息】\n" + "\n".join(context_parts)
        
        return ""
    
    def update_style_profile(self, **kwargs):
        """更新风格配置"""
        for key, value in kwargs.items():
            if hasattr(self.style_profile, key):
                setattr(self.style_profile, key, value)


# 测试函数
def main():
    """测试函数"""
    logging.basicConfig(level=logging.INFO)
    
    # 测试配置
    test_config = {
        "worldview": "现代都市世界观",
        "writing_style": "幽默风格，日常化叙事",
        "literary_techniques": [
            "保持语言流畅自然",
            "适当运用环境描写",
            "确保对话真实可信"
        ]
    }
    
    # 创建提示词管理器
    prompt_manager = SimplePromptManager(test_config)
    
    # 测试文本
    test_text = "镇上的金库给四个劫匪抢了，捕头柳暗单枪匹马连夜赶在他们前头，在四个劫匪的必经之路等待。"
    
    # 构建提示词
    prompts = prompt_manager.build_prompt(
        text=test_text,
        chunk_id="chunk_1",
        metadata={
            "document_title": "测试小说",
            "source_file": "test.txt"
        }
    )
    
    # 输出结果
    print("系统提示词:")
    print(prompts[0]["content"][:500] + "...")
    print("\n用户提示词:")
    print(prompts[1]["content"])


if __name__ == "__main__":
    main()