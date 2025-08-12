#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版输出格式化器
确保标准JSON格式输出，支持组装完整文本
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path


class SimpleOutputFormatter:
    """简化版输出格式化器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def format_output(self, original_text: str, rewritten_text: str, 
                     chunk_id: str, metadata: Optional[Dict] = None) -> Dict:
        """格式化单个文本块的输出"""
        # 基础结构
        structured_output = {
            "chunk_id": chunk_id,
            "original_text": original_text,
            "rewritten_text": rewritten_text,
            "metadata": metadata or {}
        }
        
        # 添加质量评估
        structured_output["quality"] = self._assess_quality(rewritten_text, original_text)
        
        return structured_output
    
    def _assess_quality(self, rewritten_text: str, original_text: str) -> Dict:
        """评估改写质量"""
        original_length = len(original_text)
        rewritten_length = len(rewritten_text)
        
        # 字数比例检查
        length_ratio = rewritten_length / original_length if original_length > 0 else 0
        length_score = 1.0 if 0.8 <= length_ratio <= 1.2 else max(0, 1 - abs(length_ratio - 1.0))
        
        # 连贯性检查
        coherence_score = self._check_coherence(rewritten_text)
        
        # 风格一致性检查（简化版）
        style_score = self._check_style_consistency(rewritten_text)
        
        return {
            'length_ratio': length_ratio,
            'length_score': length_score,
            'coherence_score': coherence_score,
            'style_score': style_score,
            'overall_score': (length_score + coherence_score + style_score) / 3
        }
    
    def _check_coherence(self, text: str) -> float:
        """检查文本连贯性"""
        # 检查段落间的逻辑连接词
        transition_words = ['然而', '因此', '所以', '但是', '于是', '接着', '随后', '与此同时']
        paragraphs = text.split('\n')
        
        if len(paragraphs) < 2:
            return 1.0
        
        transition_count = 0
        for i in range(len(paragraphs) - 1):
            current_para = paragraphs[i].strip()
            next_para = paragraphs[i + 1].strip()
            
            # 检查是否有过渡词
            for word in transition_words:
                if word in next_para[:100]:  # 检查段落开头
                    transition_count += 1
                    break
        
        return min(1.0, transition_count / (len(paragraphs) - 1) * 2)
    
    def _check_style_consistency(self, text: str) -> float:
        """检查风格一致性（简化版）"""
        # 检查文学手法的使用
        style_indicators = {
            "古风": ["之", "乎", "者", "也", "矣", "焉"],
            "现代": ["的", "了", "着", "过", "吧", "呢"],
            "幽默": ["哈哈", "呵呵", "有趣", "搞笑", "笑"]
        }
        
        # 这里可以根据配置的风格来调整
        target_style = "现代"  # 默认现代风格
        indicators = style_indicators.get(target_style, style_indicators["现代"])
        
        indicator_count = sum(text.count(indicator) for indicator in indicators)
        return min(1.0, indicator_count / len(text.split()) * 10)
    
    def assemble_final_text(self, chunks: List[Dict]) -> str:
        """组装完整文本"""
        if not chunks:
            return ""
        
        # 按chunk_id排序
        sorted_chunks = sorted(chunks, key=lambda x: self._extract_chunk_number(x["chunk_id"]))
        
        # 组装文本
        final_text = ""
        for i, chunk in enumerate(sorted_chunks):
            rewritten_text = chunk.get("rewritten_text", "")
            
            # 如果不是第一个块，添加段落分隔
            if i > 0:
                final_text += "\n\n"
            
            final_text += rewritten_text
        
        return final_text.strip()
    
    def _extract_chunk_number(self, chunk_id: str) -> int:
        """从chunk_id中提取数字"""
        import re
        match = re.search(r'(\d+)', chunk_id)
        return int(match.group(1)) if match else 0
    
    def save_structured_data(self, chunks: List[Dict], output_path: Path, 
                           title: str = "未知小说", author: str = "未知作者"):
        """保存结构化数据到JSON文件"""
        structured_data = {
            "metadata": {
                "title": title,
                "author": author,
                "processing_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_chunks": len(chunks),
                "original_word_count": sum(len(chunk.get("original_text", "")) for chunk in chunks),
                "rewritten_word_count": sum(len(chunk.get("rewritten_text", "")) for chunk in chunks)
            },
            "chunks": chunks
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(structured_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"结构化数据已保存到: {output_path}")
    
    def generate_quality_report(self, chunks: List[Dict]) -> Dict:
        """生成质量报告"""
        if not chunks:
            return {}
        
        # 计算总体统计
        total_chunks = len(chunks)
        total_original_words = sum(len(chunk.get("original_text", "")) for chunk in chunks)
        total_rewritten_words = sum(len(chunk.get("rewritten_text", "")) for chunk in chunks)
        
        # 计算平均质量分数
        quality_scores = [chunk.get("quality", {}).get("overall_score", 0) for chunk in chunks]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # 计算长度比例
        avg_length_ratio = sum(chunk.get("quality", {}).get("length_ratio", 1) for chunk in chunks) / len(chunks)
        
        # 分析质量问题
        low_quality_chunks = [chunk for chunk in chunks if chunk.get("quality", {}).get("overall_score", 0) < 0.7]
        
        return {
            "summary": {
                "total_chunks": total_chunks,
                "total_original_words": total_original_words,
                "total_rewritten_words": total_rewritten_words,
                "average_quality": avg_quality,
                "average_length_ratio": avg_length_ratio
            },
            "quality_analysis": {
                "low_quality_chunks": len(low_quality_chunks),
                "low_quality_percentage": (len(low_quality_chunks) / total_chunks * 100) if total_chunks > 0 else 0
            },
            "recommendations": self._generate_recommendations(chunks)
        }
    
    def _generate_recommendations(self, chunks: List[Dict]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 分析整体质量
        avg_quality = sum(chunk.get("quality", {}).get("overall_score", 0) for chunk in chunks) / len(chunks)
        
        if avg_quality < 0.7:
            recommendations.append("整体质量偏低，建议调整改写参数或检查输入文本质量")
        
        # 分析长度一致性
        length_ratios = [chunk.get("quality", {}).get("length_ratio", 1) for chunk in chunks]
        if max(length_ratios) - min(length_ratios) > 0.5:
            recommendations.append("改写后文本长度差异较大，建议统一改写标准")
        
        # 分析连贯性
        coherence_scores = [chunk.get("quality", {}).get("coherence_score", 0) for chunk in chunks]
        avg_coherence = sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0
        
        if avg_coherence < 0.7:
            recommendations.append("文本连贯性有待提高，建议加强段落间的过渡")
        
        return recommendations


# 测试函数
def main():
    """测试函数"""
    logging.basicConfig(level=logging.INFO)
    
    # 创建输出格式化器
    formatter = SimpleOutputFormatter()
    
    # 测试文本块
    test_chunks = [
        {
            "chunk_id": "chunk_1",
            "original_text": "镇上的金库给四个劫匪抢了，捕头柳暗单枪匹马连夜赶在他们前头。",
            "rewritten_text": "金库遭劫，四名劫匪作案后逃离。捕头柳暗独自一人，抢先赶到了劫匪的必经之路上。",
            "metadata": {"word_count": 25}
        },
        {
            "chunk_id": "chunk_2",
            "original_text": "在四个劫匪的必经之路――十三山山脚的路上等待。",
            "rewritten_text": "他选择在十三山山脚这条必经之路上设伏，准备拦截劫匪。",
            "metadata": {"word_count": 18}
        }
    ]
    
    # 测试质量评估
    for chunk in test_chunks:
        quality = formatter._assess_quality(chunk["rewritten_text"], chunk["original_text"])
        chunk["quality"] = quality
        print(f"Chunk {chunk['chunk_id']} 质量评分: {quality['overall_score']:.2f}")
    
    # 测试组装完整文本
    final_text = formatter.assemble_final_text(test_chunks)
    print(f"\n组装后的完整文本:\n{final_text}")
    
    # 测试质量报告
    quality_report = formatter.generate_quality_report(test_chunks)
    print(f"\n质量报告:")
    print(f"平均质量: {quality_report['summary']['average_quality']:.2f}")
    print(f"建议: {quality_report['recommendations']}")


if __name__ == "__main__":
    main()