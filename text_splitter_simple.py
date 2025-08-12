#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版智能文本分割器
保留核心的语义分割功能，支持按章节和语义边界分割
"""

import re
import logging
from typing import List, Dict
from dataclasses import dataclass
from enum import Enum


class TextType(Enum):
    """文本类型枚举"""
    NARRATION = "叙述"  # 叙述性文本
    DIALOGUE = "对话"  # 对话文本
    DESCRIPTION = "描写"  # 环境或人物描写
    PSYCHOLOGY = "心理"  # 心理活动
    ACTION = "动作"  # 动作描写
    TRANSITION = "过渡"  # 场景过渡


@dataclass
class TextChunk:
    """文本块数据结构"""
    text: str
    chunk_type: TextType
    start_pos: int
    end_pos: int
    metadata: Dict


class SimpleTextSplitter:
    """简化版智能文本分割器"""
    
    def __init__(self, max_chunk_size: int = 2000, min_chunk_size: int = 300):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.logger = logging.getLogger(__name__)
        
        # 定义文本类型检测模式
        self.patterns = self._init_patterns()
        
        # 定义语义边界标记
        self.semantic_boundaries = self._init_semantic_boundaries()
    
    def _init_patterns(self) -> Dict:
        """初始化文本类型检测模式"""
        patterns = {
            TextType.DIALOGUE: [
                r'「[^」]*」',  # 中文引号
                r'"[^"]*"',    # 英文引号
                r"'[^']*'",    # 单引号
                r'[^说道：:]*[说道：:]「[^」]*」',  # 带说话人的对话
                r'[^说道：:]*[说道：:]"[^"]*"',     # 带说话人的对话
            ],
            TextType.DESCRIPTION: [
                r'天空|大地|风景|周围|环境|气氛|空气|阳光|月光|云彩|星辰',  # 环境描写
                r'外貌|长相|身材|面容|眼睛|头发|衣着|服装',  # 外貌描写
                r'房间|房屋|建筑|街道|城市|乡村|山林|河流',  # 场景描写
            ],
            TextType.PSYCHOLOGY: [
                r'心想|思考|感觉|情绪|内心|想法|回忆|想象|担忧',  # 心理活动
                r'暗自|默默|心中|脑子里|脑海里|心头',  # 心理状态
                r'疑惑|困惑|明白|理解|惊讶|震惊|恐惧|害怕',  # 情感反应
            ],
            TextType.ACTION: [
                r'跑|跳|打|杀|走|坐|站|躺|爬|滚|摔',  # 基本动作
                r'拿|抓|握|放|扔|接|推|拉|抬|举|提',  # 手部动作
                r'看|听|闻|尝|摸|感觉|观察|注视|凝视',  # 感官动作
            ],
            TextType.TRANSITION: [
                r'然而|但是|不过|可是|只是',  # 转折
                r'于是|因此|所以|因而|故而',  # 因果
                r'接着|随后|然后|之后|不久',  # 时间顺序
                r'此时|这时|此刻|当下|现在',  # 时间点
                r'那里|这里|那边|这边|远处|近处',  # 空间转换
            ]
        }
        
        return patterns
    
    def _init_semantic_boundaries(self) -> Dict:
        """初始化语义边界标记"""
        boundaries = {
            'strong': [
                r'第[一二三四五六七八九十百千万\d]+[章节回]',  # 章节标题
                r'\n\s*\n',  # 空行
                r'。！？\s*\n',  # 句子结束加换行
            ],
            'medium': [
                r'。[！？]',  # 句子结束
                r'[；；]',  # 分号
                r'，',  # 逗号
            ],
            'weak': [
                r'[、]',  # 顿号
                r'\s+',  # 空格
            ]
        }
        
        return boundaries
    
    def split_text(self, text: str) -> List[TextChunk]:
        """智能分割文本"""
        # 预处理文本
        text = self._preprocess_text(text)
        
        # 首先尝试按章节分割
        chapter_chunks = self._split_by_chapters(text)
        
        # 对每个章节进行进一步分割
        all_chunks = []
        for chapter_text in chapter_chunks:
            if len(chapter_text) <= self.max_chunk_size:
                # 如果章节本身不大，直接作为一个块
                chunk_type = self._detect_text_type(chapter_text)
                chunk = TextChunk(
                    text=chapter_text,
                    chunk_type=chunk_type,
                    start_pos=text.find(chapter_text),
                    end_pos=text.find(chapter_text) + len(chapter_text),
                    metadata={'chapter': True}
                )
                all_chunks.append(chunk)
            else:
                # 章节较大，需要进一步分割
                sub_chunks = self._split_semantically(chapter_text)
                all_chunks.extend(sub_chunks)
        
        # 后处理：合并过小的块
        all_chunks = self._merge_small_chunks(all_chunks)
        
        return all_chunks
    
    def _preprocess_text(self, text: str) -> str:
        """预处理文本"""
        # 统一换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # 移除多余的空格
        text = re.sub(r'\s+', ' ', text)
        
        # 确保标点符号后有空格（除了中文标点）
        text = re.sub(r'([a-zA-Z0-9])([,.!?])', r'\1 \2', text)
        text = re.sub(r'([,.!?])([a-zA-Z0-9])', r'\1 \2', text)
        
        return text.strip()
    
    def _split_by_chapters(self, text: str) -> List[str]:
        """按章节分割文本"""
        chapter_pattern = r'(第[一二三四五六七八九十百千万\d]+[章节回][^\n]*)'
        
        # 查找所有章节标题
        chapter_matches = list(re.finditer(chapter_pattern, text))
        
        if not chapter_matches:
            # 没有找到章节标题，返回整个文本
            return [text]
        
        chapters = []
        for i, match in enumerate(chapter_matches):
            start_pos = match.start()
            
            # 确定章节结束位置
            if i < len(chapter_matches) - 1:
                end_pos = chapter_matches[i + 1].start()
            else:
                end_pos = len(text)
            
            chapter_text = text[start_pos:end_pos].strip()
            if chapter_text:
                chapters.append(chapter_text)
        
        return chapters
    
    def _detect_text_type(self, text: str) -> TextType:
        """检测文本类型"""
        type_scores = {text_type: 0 for text_type in TextType}
        
        # 计算每种文本类型的得分
        for text_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text)
                type_scores[text_type] += len(matches)
        
        # 计算文本长度归一化得分
        text_length = len(text)
        for text_type in type_scores:
            type_scores[text_type] = type_scores[text_type] / max(1, text_length / 100)
        
        # 找出得分最高的文本类型
        best_type = max(type_scores, key=type_scores.get)
        
        # 如果最高得分太低，默认为叙述
        if type_scores[best_type] < 0.1:
            return TextType.NARRATION
        
        return best_type
    
    def _split_semantically(self, text: str) -> List[TextChunk]:
        """语义分割文本"""
        chunks = []
        current_pos = 0
        text_length = len(text)
        
        while current_pos < text_length:
            # 确定当前块的结束位置
            end_pos = min(current_pos + self.max_chunk_size, text_length)
            
            # 如果不是文本末尾，尝试在语义边界处分割
            if end_pos < text_length:
                # 从后向前寻找合适的分割点
                split_pos = self._find_semantic_split_point(text, current_pos, end_pos)
                end_pos = split_pos
            
            # 提取文本块
            chunk_text = text[current_pos:end_pos].strip()
            
            if chunk_text:
                # 检测文本类型
                chunk_type = self._detect_text_type(chunk_text)
                
                # 创建文本块
                chunk = TextChunk(
                    text=chunk_text,
                    chunk_type=chunk_type,
                    start_pos=current_pos,
                    end_pos=end_pos,
                    metadata=self._extract_chunk_metadata(chunk_text, chunk_type)
                )
                chunks.append(chunk)
            
            current_pos = end_pos
        
        return chunks
    
    def _find_semantic_split_point(self, text: str, start_pos: int, end_pos: int) -> int:
        """在语义边界处找到合适的分割点"""
        # 从后向前寻找分割点
        search_text = text[start_pos:end_pos]
        
        # 优先尝试强边界
        for pattern in self.semantic_boundaries['strong']:
            matches = list(re.finditer(pattern, search_text))
            if matches:
                # 取最后一个匹配位置
                last_match = matches[-1]
                split_pos = start_pos + last_match.start()
                
                # 确保分割后的块不会太小
                if split_pos - start_pos >= self.min_chunk_size:
                    return split_pos
        
        # 如果没有找到强边界，尝试中等边界
        for pattern in self.semantic_boundaries['medium']:
            matches = list(re.finditer(pattern, search_text))
            if matches:
                # 取最后一个匹配位置
                last_match = matches[-1]
                split_pos = start_pos + last_match.start()
                
                # 确保分割后的块不会太小
                if split_pos - start_pos >= self.min_chunk_size:
                    return split_pos
        
        # 如果仍然没有找到合适的分割点，按最大块大小分割
        return end_pos
    
    def _extract_chunk_metadata(self, text: str, chunk_type: TextType) -> Dict:
        """提取文本块元数据"""
        metadata = {
            'word_count': len(text),
            'sentence_count': len(re.split(r'[。！？!?]', text)),
            'paragraph_count': len(text.split('\n')),
            'chunk_type': chunk_type.value,
        }
        
        # 提取位置信息
        location_keywords = ["十三山", "镇上", "山脚", "树林", "路上", "房间", "街道", "城市"]
        for keyword in location_keywords:
            if keyword in text:
                metadata['location'] = keyword
                break
        
        # 提取时间信息
        time_keywords = ["早上", "晚上", "夜里", "白天", "黄昏", "清晨", "下午", "中午"]
        for keyword in time_keywords:
            if keyword in text:
                metadata['time'] = keyword
                break
        
        return metadata
    
    def _merge_small_chunks(self, chunks: List[TextChunk]) -> List[TextChunk]:
        """合并过小的文本块"""
        if not chunks:
            return chunks
        
        merged_chunks = []
        current_chunk = chunks[0]
        
        for next_chunk in chunks[1:]:
            # 如果当前块太小，且与下一个块类型相同或兼容，则合并
            if (len(current_chunk.text) < self.min_chunk_size and 
                current_chunk.chunk_type == next_chunk.chunk_type):
                # 合并文本块
                merged_text = current_chunk.text + "\n" + next_chunk.text
                current_chunk.text = merged_text
                current_chunk.end_pos = next_chunk.end_pos
                current_chunk.metadata.update(next_chunk.metadata)
            else:
                # 添加当前块到结果列表
                merged_chunks.append(current_chunk)
                current_chunk = next_chunk
        
        # 添加最后一个块
        merged_chunks.append(current_chunk)
        
        return merged_chunks


# 测试函数
def main():
    """测试函数"""
    logging.basicConfig(level=logging.INFO)
    
    # 测试文本
    test_text = """
    第一章 开始
    
    镇上的金库给四个劫匪抢了，捕头柳暗单枪匹马连夜赶在他们前头，在四个劫匪的必经之路――十三山山脚的路上等待。
    
    「老大，我们这次真是干了一票大的！」一个劫匪兴奋地说道。
    
    「嗯，确实不少。」另一个劫匪冷静地回答，「但我们还是要小心点，别被官府的人追上。」
    
    柳暗心中暗想：「这伙劫匪看起来很谨慎，我得想个好办法对付他们。」他悄悄地拔出了腰间的刀，准备随时出击。
    
    天色渐暗，山间的风声越来越大。柳暗紧握着刀柄，眼神坚定地注视着前方的道路。
    """
    
    # 创建分割器
    splitter = SimpleTextSplitter(max_chunk_size=200, min_chunk_size=50)
    
    # 分割文本
    chunks = splitter.split_text(test_text)
    
    # 输出结果
    print(f"分割结果: {len(chunks)} 个文本块")
    for i, chunk in enumerate(chunks):
        print(f"\n文本块 {i+1}:")
        print(f"类型: {chunk.chunk_type.value}")
        print(f"长度: {len(chunk.text)}")
        print(f"内容: {chunk.text[:50]}...")
        print(f"元数据: {chunk.metadata}")


if __name__ == "__main__":
    main()