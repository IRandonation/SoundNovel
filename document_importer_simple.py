#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版文档导入器 - 只支持TXT格式
专注于核心的文本导入和预处理功能
"""

import re
import chardet
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


class SimpleDocumentImporter:
    """简化版文档导入器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def import_document(self, file_path: Path) -> Dict:
        """导入TXT文档"""
        try:
            # 检查文件是否存在
            if not file_path.exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            # 检查文件扩展名
            if file_path.suffix.lower() not in ['.txt', '.text']:
                raise ValueError(f"不支持的文件格式: {file_path.suffix}. 只支持TXT格式")
            
            # 读取文件内容
            raw_data = file_path.read_bytes()
            
            # 检测编码
            encoding = self._detect_encoding(raw_data)
            
            # 解码文本
            text = raw_data.decode(encoding, errors='ignore')
            
            # 预处理文本
            text = self._preprocess_text(text)
            
            # 提取基本信息
            title = file_path.stem
            author = "未知作者"
            
            # 统计信息
            word_count = len(text)
            character_count = len(text.replace(' ', ''))
            
            return {
                'file_path': str(file_path),
                'file_type': 'txt',
                'title': title,
                'author': author,
                'full_text': text,
                'word_count': word_count,
                'character_count': character_count,
                'import_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"导入文档失败: {e}")
            raise
    
    def _detect_encoding(self, raw_data: bytes) -> str:
        """检测文件编码"""
        # 使用chardet检测编码
        detection = chardet.detect(raw_data)
        detected_encoding = detection['encoding']
        confidence = detection.get('confidence', 0)
        
        # 要尝试的编码列表（按优先级排序）
        encodings_to_try = []
        
        # 如果检测到编码且置信度较高，优先使用
        if detected_encoding and confidence > 0.7:
            encodings_to_try.append(detected_encoding)
        
        # 添加常见中文编码
        common_encodings = ['utf-8', 'gbk', 'gb18030', 'big5', 'gb2312']
        for enc in common_encodings:
            if enc not in encodings_to_try:
                encodings_to_try.append(enc)
        
        # 尝试各种编码
        for encoding in encodings_to_try:
            try:
                decoded_text = raw_data.decode(encoding)
                # 验证解码结果是否合理（包含中文字符）
                if any('\u4e00' <= char <= '\u9fff' for char in decoded_text[:1000]):
                    self.logger.info(f"成功使用 {encoding} 编码读取文件 (置信度: {confidence:.2f})")
                    return encoding
            except Exception:
                continue
        
        # 如果所有编码都失败，使用UTF-8并忽略错误
        self.logger.warning("使用UTF-8编码并忽略错误字符")
        return 'utf-8'
    
    def _preprocess_text(self, text: str) -> str:
        """预处理文本"""
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 移除常见的广告和无意义内容
        ad_patterns = [
            r'本书由.*?整理',
            r'更多精彩小说请访问.*?',
            r'【.*?】',
            r'第.*?页',
            r'\*\*\*.*?\*\*\*',
            r'—+',
            r'=+'
        ]
        
        for pattern in ad_patterns:
            text = re.sub(pattern, '', text)
        
        # 修复标点符号间距
        text = re.sub(r'([，。！？；：""''（）【】])\s*', r'\1', text)
        text = re.sub(r'\s*([，。！？；：""''（）【】])', r'\1', text)
        
        return text.strip()


# 测试函数
def main():
    """测试函数"""
    logging.basicConfig(level=logging.INFO)
    
    # 创建导入器
    importer = SimpleDocumentImporter()
    
    # 测试文件
    test_file = Path("source") / "11.txt"
    if test_file.exists():
        try:
            result = importer.import_document(test_file)
            print(f"\n导入成功: {result['title']}")
            print(f"字数: {result['word_count']}")
            print(f"字符数: {result['character_count']}")
            print(f"前100字符: {result['full_text'][:100]}...")
        except Exception as e:
            print(f"导入失败: {e}")
    else:
        print(f"测试文件不存在: {test_file}")


if __name__ == "__main__":
    main()