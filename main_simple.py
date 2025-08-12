#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版小说改写系统 - 核心功能版本
专注于：小说导入、文本分割、智能改写、标准格式输出
"""

import json
import re
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from openai import OpenAI
from openai.types.chat import ChatCompletion

# 导入核心模块
from document_importer_simple import SimpleDocumentImporter
from text_splitter_simple import SimpleTextSplitter
from prompt_manager_simple import SimplePromptManager
from output_formatter_simple import SimpleOutputFormatter


class SimpleNovelRewriter:
    """简化版小说改写器"""
    
    def __init__(self, config_path: str = "config_simple.json"):
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 初始化API客户端
        self.client = OpenAI(
            api_key=self.config["api_key"],
            base_url=self.config.get("api_url", "https://api.deepseek.com")
        )
        
        # 初始化核心组件
        self.document_importer = SimpleDocumentImporter()
        self.text_splitter = SimpleTextSplitter(
            max_chunk_size=self.config.get("chunk_size", 2000),
            min_chunk_size=self.config.get("min_chunk_size", 300)
        )
        self.prompt_manager = SimplePromptManager(self.config)
        self.output_formatter = SimpleOutputFormatter()
        
        # 存储处理结果
        self.processed_chunks = []
        
        # 设置日志
        self._setup_logging()
    
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        default_config = {
            "api_key": "your_api_key_here",
            "api_url": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "temperature": 0.8,
            "max_tokens": 2000,
            "chunk_size": 2000,
            "min_chunk_size": 300,
            "max_retries": 2,
            "retry_delay": 1,
            "worldview": "现代都市世界观",
            "writing_style": "简洁明了的叙事风格",
            "literary_techniques": [
                "保持语言流畅自然",
                "适当运用环境描写",
                "确保对话真实可信"
            ]
        }
        
        try:
            if not Path(config_path).exists():
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
                print(f"已创建默认配置文件 {config_path}，请填入您的API密钥")
                exit(0)
            
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                return {**default_config, **user_config}
        except Exception as e:
            print(f"配置加载失败: {str(e)}")
            exit(1)
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('novel_rewriter_simple.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def process_file(self, input_path: Path) -> Optional[Path]:
        """处理单个文件"""
        try:
            self.logger.info(f"开始处理文件: {input_path}")
            
            # 清空之前的结果
            self.processed_chunks = []
            
            # 1. 导入文档
            print("📖 正在导入文档...")
            document_data = self.document_importer.import_document(input_path)
            text = document_data['full_text']
            
            print(f"✓ 文档导入成功: {document_data['title']}")
            print(f"   字数: {document_data['word_count']}")
            
            # 2. 分割文本
            print("✂️ 正在分割文本...")
            text_chunks = self.text_splitter.split_text(text)
            print(f"✓ 文本分割完成，共 {len(text_chunks)} 个文本块")
            
            # 3. 处理每个文本块
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            
            structured_output_path = output_dir / f"structured_{input_path.stem}.json"
            final_text_path = output_dir / f"rewritten_{input_path.stem}.txt"
            
            print("🔄 正在改写文本块...")
            
            for i, chunk in enumerate(text_chunks):
                chunk_id = f"chunk_{i+1}"
                
                # 构建提示词
                prompt_messages = self.prompt_manager.build_prompt(
                    text=chunk,
                    chunk_id=chunk_id,
                    metadata={
                        "source_file": input_path.name,
                        "document_title": document_data['title']
                    }
                )
                
                # 调用API改写
                rewritten_text = self._rewrite_with_api(prompt_messages, chunk.text)
                
                # 格式化输出
                structured_output = self.output_formatter.format_output(
                    original_text=chunk.text,
                    rewritten_text=rewritten_text,
                    chunk_id=chunk_id,
                    metadata={
                        "word_count": len(chunk.text),
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                self.processed_chunks.append(structured_output)
                
                # 显示进度
                rewritten_text_str = rewritten_text if isinstance(rewritten_text, str) else str(rewritten_text)
                print(f"   进度: {i+1}/{len(text_chunks)} - 字数: {len(rewritten_text)}")
                time.sleep(0.5)  # 避免API调用过于频繁
            
            # 4. 保存结果
            print("💾 正在保存结果...")
            
            # 保存结构化数据
            with open(structured_output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "metadata": {
                        "title": document_data['title'],
                        "author": document_data['author'],
                        "processing_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "total_chunks": len(self.processed_chunks),
                        "original_word_count": document_data['word_count']
                    },
                    "chunks": self.processed_chunks
                }, f, ensure_ascii=False, indent=2)
            
            # 生成最终文本
            final_text = self.output_formatter.assemble_final_text(self.processed_chunks)
            with open(final_text_path, 'w', encoding='utf-8') as f:
                f.write(final_text)
            
            print(f"✓ 处理完成!")
            print(f"   结构化数据: {structured_output_path}")
            print(f"   最终文本: {final_text_path}")
            
            return structured_output_path
            
        except Exception as e:
            self.logger.error(f"处理文件失败: {e}")
            return None
    
    def _rewrite_with_api(self, messages: List[Dict], original_text: str) -> str:
        """调用API进行文本改写"""
        for attempt in range(self.config["max_retries"]):
            try:
                response: ChatCompletion = self.client.chat.completions.create(
                    model=self.config["model"],
                    messages=messages,
                    temperature=self.config["temperature"],
                    max_tokens=self.config["max_tokens"],
                    top_p=0.9,
                    frequency_penalty=0.2
                )
                
                result = response.choices[0].message.content.strip()
                
                # 检查字数是否过短
                if len(result) < len(original_text) * 0.6:
                    if attempt < self.config["max_retries"] - 1:
                        time.sleep(self.config["retry_delay"] * (attempt + 1))
                        continue
                    else:
                        # 最后一次尝试，返回原文
                        return original_text
                
                return result
                
            except Exception as e:
                if attempt == self.config["max_retries"] - 1:
                    self.logger.error(f"API调用失败: {e}")
                    return original_text  # 返回原文作为回退
                time.sleep(self.config["retry_delay"] * (attempt + 1))
        
        return original_text
    
    def batch_process(self, directory: str = "source") -> List[Path]:
        """批量处理目录中的文件"""
        source_dir = Path(directory)
        if not source_dir.exists():
            print(f"错误：目录不存在: {directory}")
            return []
        
        # 查找所有TXT文件
        txt_files = list(source_dir.glob("*.txt"))
        
        if not txt_files:
            print(f"在 {directory} 目录中没有找到TXT文件")
            return []
        
        print(f"找到 {len(txt_files)} 个TXT文件:")
        for i, file in enumerate(txt_files, 1):
            print(f"  {i}. {file.name}")
        
        results = []
        for file_path in txt_files:
            print(f"\n▶ 处理文件: {file_path.name}")
            result = self.process_file(file_path)
            if result:
                results.append(result)
        
        return results


def main():
    """主函数"""
    print("""
    =========================================
     简化版小说改写系统 v1.0
     核心功能：导入、分割、改写、输出
    =========================================
    """)
    
    # 初始化改写器
    rewriter = SimpleNovelRewriter()
    
    # 检查source目录
    source_dir = Path("source")
    if not source_dir.exists():
        source_dir.mkdir(exist_ok=True)
        print(f"已创建source目录，请放入要处理的TXT文件")
        return
    
    # 查找要处理的文件
    txt_files = list(source_dir.glob("*.txt"))
    
    if not txt_files:
        print("source目录中没有找到TXT文件")
        print("已创建示例文件：example.txt")
        example_path = source_dir / "example.txt"
        example_content = """这是一个示例小说内容。

第一章 开始

镇上的金库给四个劫匪抢了，捕头柳暗单枪匹马连夜赶在他们前头，在四个劫匪的必经之路――十三山山脚的路上等待。

「老大，我们这次真是干了一票大的！」一个劫匪兴奋地说道。

「嗯，确实不少。」另一个劫匪冷静地回答，「但我们还是要小心点，别被官府的人追上。」

柳暗心中暗想：「这伙劫匪看起来很谨慎，我得想个好办法对付他们。」他悄悄地拔出了腰间的刀，准备随时出击。

天色渐暗，山间的风声越来越大。柳暗紧握着刀柄，眼神坚定地注视着前方的道路。
"""
        example_path.write_text(example_content, encoding='utf-8')
        txt_files = [example_path]
    
    # 处理文件
    results = rewriter.batch_process()
    
    # 显示结果
    if results:
        print(f"\n🎉 处理完成! 共处理 {len(results)} 个文件")
        for result in results:
            print(f"  结果: {result.name}")
    else:
        print("\n❌ 没有成功处理任何文件")


if __name__ == "__main__":
    main()