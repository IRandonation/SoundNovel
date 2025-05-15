#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全自动TXT洗稿系统（DeepSeek专用版）
功能：
1. 从source文件夹读取TXT文件（不修改源文件）
2. 自动拆分超长文本满足API限制
3. 智能保留关键故事元素
4. 批量处理所有TXT文件
5. 自动规避相似内容
"""

import os
import re
import json
import time
import random
import logging
import requests
import chardet
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rewriter.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DeepSeekRewriter:
    def __init__(self):
        # 检查依赖
        self._check_dependencies()
        
        # 初始化配置
        self.config = self._load_config()
        self._init_api_client()
        self.chunk_size = self.config['chunk_settings']['size']
        
        # 创建必要目录
        Path("source").mkdir(exist_ok=True)
        Path("output").mkdir(exist_ok=True)
        Path("failed").mkdir(exist_ok=True)

    def _check_dependencies(self) -> None:
        """检查必要的Python包是否已安装"""
        required = ['requests', 'chardet']
        missing = []
        
        for pkg in required:
            try:
                __import__(pkg)
            except ImportError:
                missing.append(pkg)
                
        if missing:
            logger.error(f"缺少必要依赖包: {', '.join(missing)}")
            logger.info("请运行: pip install " + " ".join(missing))
            exit(1)

    def _init_api_client(self):
        """初始化API客户端"""
        try:
            from deepseek import DeepSeekAPI
            self.client = DeepSeekAPI(self.config['api_key'])
            self._test_api_connection()
        except ImportError:
            logger.error("DeepSeek API客户端未安装，请运行: pip install deepseek")
            exit(1)
        except Exception as e:
            logger.error(f"API客户端初始化失败: {str(e)}")
            exit(1)

    def _test_api_connection(self):
        """测试API连接是否正常"""
        test_prompt = "测试连接"
        try:
            resp = self.client.chat_completion(
                model="deepseek-chat",
                messages=[{"role": "user", "content": test_prompt}],
                max_tokens=10
            )
            if isinstance(resp, dict) and 'error' in resp:
                raise ValueError(f"API密钥无效: {resp['error']}")
        except Exception as e:
            raise ValueError(f"API连接测试失败: {str(e)}")

    def _load_config(self) -> Dict[str, Any]:
        """加载并验证配置文件"""
        config_path = 'config.json'
        default_config = {
            "api_key": "your-api-key-here",
            "chunk_settings": {
                "size": 3000,
                "overlap": 200
            },
            "encoding_retry": ["utf-8", "gbk", "gb18030"]
        }
        
        try:
            if not Path(config_path).exists():
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
                logger.info("已生成默认配置文件config.json，请修改API密钥")
                exit(0)
                
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            if not self._validate_config(config):
                raise ValueError("配置文件格式错误")
                
            return config
        except Exception as e:
            logger.error(f"配置文件加载失败: {str(e)}")
            exit(1)

    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置格式和内容"""
        required_keys = {
            'api_key': str,
            'chunk_settings': dict
        }
        
        for key, key_type in required_keys.items():
            if key not in config or not isinstance(config[key], key_type):
                logger.error(f"配置缺少必需字段或类型错误: {key}")
                return False
                
        return True

    def _read_file_with_retry(self, file_path: Union[str, Path]) -> str:
        """尝试多种编码读取文件"""
        encodings = self.config.get('encoding_retry', ['utf-8', 'gbk', 'gb18030'])
        
        # 首先尝试检测编码
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                if result['confidence'] > 0.9:
                    encodings.insert(0, result['encoding'])
        except Exception:
            pass
            
        # 尝试各种编码
        last_error = None
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError as e:
                last_error = e
                continue
            except Exception as e:
                last_error = e
                break
                
        raise ValueError(f"无法解码文件 {file_path}，尝试的编码: {encodings}，最后错误: {str(last_error)}")

    def _preprocess_text(self, text: str) -> List[str]:
        """文本预处理"""
        start_time = time.time()
        
        # 移除特殊字符但保留中文标点
        text = re.sub(r'[^\w\s\u4e00-\u9fa5，。！？、；："\'《》【】（）]', '', text.strip())
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 智能分段
        paragraphs = []
        current_chunk = ""
        overlap_size = self.config['chunk_settings']['overlap']
        
        for para in text.split('\n\n'):
            para = para.strip()
            if not para:
                continue
                
            if len(current_chunk) + len(para) <= self.chunk_size:
                current_chunk += para + "\n\n"
            else:
                sentences = re.split(r'(?<=[。！？])', para)
                for sent in sentences:
                    sent = sent.strip()
                    if not sent:
                        continue
                        
                    if len(current_chunk) + len(sent) <= self.chunk_size:
                        current_chunk += sent
                    else:
                        if current_chunk:
                            if overlap_size > 0 and len(paragraphs) > 0:
                                last_para = paragraphs[-1]
                                overlap_text = last_para[-overlap_size:] if len(last_para) > overlap_size else last_para
                                current_chunk = overlap_text + current_chunk
                            paragraphs.append(current_chunk.strip())
                        current_chunk = sent
        
        if current_chunk:
            paragraphs.append(current_chunk.strip())
            
        logger.info(f"文本预处理完成，段落数: {len(paragraphs)}，耗时: {time.time()-start_time:.2f}s")
        return paragraphs

    def _analyze_structure(self, text_chunk: str) -> Dict[str, Any]:
        """深度分析文本结构（针对直接返回JSON格式优化版）"""
        start_time = time.time()
        prompt = """【结构分析指令】
    请从以下文本提取结构化数据（严格JSON格式）：
    ```json
    {
        "worldview": ["关键词1", "关键词2", "关键词3"],
        "characters": {
            "主角": "角色名",
            "相关角色1": "角色关系",
            "相关角色2": "角色关系"
        },
        "events": ["事件1", "事件2", "事件3"]
    }
    ```\n\n""" + text_chunk[:2000]

        retry = 0
        max_retry = 3
        timeout = 30
        
        while retry < max_retry:
            try:
                # 1. 调用API
                response = self.client.chat_completion(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1000,
                    timeout=timeout,
                    response_format={"type": "json_object"}  # 仍然声明需要JSON
                )
                
                # 2. 记录原始响应（调试用）
                logger.debug("API原始响应类型: %s", type(response))
                logger.debug("API原始响应内容: %s", str(response)[:500])
    
                # 3. 兼容处理字符串响应
                if isinstance(response, str):
                    try:
                        response = json.loads(response)  # 尝试解析字符串
                    except json.JSONDecodeError as e:
                        logger.warning("API返回字符串不是有效JSON: %s", str(e))
                        raise ValueError("API返回了非JSON字符串")
    
                # 4. 验证数据结构
                if isinstance(response, dict):
                    required_keys = ['worldview', 'characters', 'events']
                    if all(key in response for key in required_keys):
                        logger.info("结构分析成功，耗时: %.2fs", time.time()-start_time)
                        return response
                    
                    # 检查嵌套结构（兼容旧版）
                    if 'content' in response and isinstance(response['content'], dict):
                        if all(key in response['content'] for key in required_keys):
                            return response['content']
    
                raise ValueError(f"API返回缺少必要字段，响应类型: {type(response)}")
    
            except Exception as e:
                logger.error("分析尝试 %d/%d 失败: %s", retry+1, max_retry, str(e))
                retry += 1
                if retry < max_retry:
                    time.sleep(min(5 * retry, 30))
        
        logger.error("结构分析失败，已达最大重试次数 %d", max_retry)
        raise ValueError("无法获取有效结构")

    def _rewrite_chunk(self, chunk: str, context: Dict[str, Any]) -> str:
        """改写文本片段"""
        start_time = time.time()
        prompt = f"""【改写任务说明】
根据以下设定改写文本：

【世界观】{context.get('worldview', [])}
【角色】{json.dumps(context.get('characters', {}), ensure_ascii=False)}
【事件】{context.get('events', [])}

【要求】
1. 自然替换所有名称
2. 调整叙事结构
3. 增强文学性
4. 保持核心情节

【原文】:
{chunk}

直接输出改写后的完整文本："""

        retry = 0
        max_retry = 3
        
        while retry < max_retry:
            try:
                response = self.client.chat_completion(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=self.chunk_size * 2,
                    timeout=60,
                    response_format={"type": "text"}
                )
                
                result = ""
                if isinstance(response, str):
                    result = response.strip()
                elif isinstance(response, dict):
                    if 'content' in response:
                        result = str(response['content']).strip()
                    elif 'choices' in response:
                        result = str(response['choices'][0]['message']['content']).strip()
                
                if not result:
                    raise ValueError("API返回空内容")

                logger.info(f"文本改写完成，耗时: {time.time()-start_time:.2f}s")
                return result
                
            except Exception as e:
                logger.warning(f"改写尝试 {retry+1}/{max_retry} 失败: {str(e)}")
                retry += 1
                if retry < max_retry:
                    time.sleep(min(5 * retry, 30))
                    
        raise ValueError(f"文本改写失败，已达最大重试次数 {max_retry}")

    def _analyze_style(self, text: str) -> str:
        """分析文本风格特征"""
        features = {
            'dialogue_ratio': len(re.findall(r'["“”‘’].*?["“”‘’]', text)) / max(1, len(re.findall(r'[。！？]', text))),
            'descriptive_ratio': len(re.findall(r'的|地|得|着|了|过', text)) / len(text),
            'paragraph_length': sum(len(p) for p in re.split(r'\n+', text)) / max(1, len(re.split(r'\n+', text)))
        }
        
        style = []
        if features['dialogue_ratio'] > 0.3:
            style.append("对话驱动型")
        if features['descriptive_ratio'] > 0.15:
            style.append("描写细腻型")
        if features['paragraph_length'] > 200:
            style.append("段落较长型")
            
        return " | ".join(style) if style else "均衡型"

    def _post_process(self, text: str) -> str:
        """后处理增强"""
        # 优化段落结构
        paragraphs = []
        for para in text.split('\n\n'):
            para = para.strip()
            if len(para) > 500:
                sentences = re.split(r'(?<=[。！？])', para)
                current = ""
                for sent in sentences:
                    if len(current) + len(sent) > 450:
                        paragraphs.append(current)
                        current = sent
                    else:
                        current += sent
                if current:
                    paragraphs.append(current)
            else:
                paragraphs.append(para)
                
        return '\n\n'.join(paragraphs)

    def process_file(self, file_path: Union[str, Path]) -> Optional[Path]:
        """处理单个文件（不修改源文件）"""
        logger.info(f"开始处理文件: {file_path}")
        stats = {
            'original_size': 0,
            'processed_size': 0,
            'chunks': 0,
            'time_spent': 0,
            'success': False
        }
        start_time = time.time()
        
        try:
            # 1. 读取文件
            raw_text = self._read_file_with_retry(file_path)
            stats['original_size'] = len(raw_text)
            
            # 2. 预处理
            chunks = self._preprocess_text(raw_text)
            stats['chunks'] = len(chunks)
            
            # 3. 分析结构
            context = self._analyze_structure(chunks[0])
            
            # 4. 分段改写
            results = []
            for i, chunk in enumerate(chunks):
                logger.info(f"正在处理段落 {i+1}/{len(chunks)}")
                rewritten = self._rewrite_chunk(chunk, context)
                results.append(self._post_process(rewritten))
                time.sleep(0.5)
                
            # 5. 保存结果
            output_file = Path("output") / f"rewritten_{Path(file_path).name}"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n\n'.join(results))
            stats['processed_size'] = os.path.getsize(output_file)
            
            stats['time_spent'] = time.time() - start_time
            stats['success'] = True
            
            logger.info(f"处理成功: 原始大小={stats['original_size']} 改写大小={stats['processed_size']}")
            return output_file
            
        except Exception as e:
            logger.error(f"处理文件失败: {str(e)}")
            # 记录失败信息
            failed_log = Path("failed") / f"{Path(file_path).name}.log"
            with open(failed_log, 'w', encoding='utf-8') as f:
                f.write(f"处理失败: {file_path}\n错误信息: {str(e)}\n")
            return None

    def batch_process(self) -> Dict[str, int]:
        """批量处理source文件夹中的所有TXT文件"""
        source_files = list(Path("source").glob("*.txt"))
        if not source_files:
            logger.warning("source文件夹中没有找到任何TXT文件")
            return {'total': 0, 'success': 0, 'failed': 0}
        
        logger.info(f"开始批量处理 {len(source_files)} 个文件")
        
        stats = {'total': len(source_files), 'success': 0, 'failed': 0}
        
        for file in source_files:
            try:
                result = self.process_file(file)
                if result:
                    stats['success'] += 1
                    logger.info(f"处理成功: {file.name} -> {result}")
                else:
                    stats['failed'] += 1
                    logger.error(f"处理失败: {file.name}")
            except Exception as e:
                stats['failed'] += 1
                logger.error(f"处理文件 {file.name} 时发生异常: {str(e)}")
        
        logger.info(f"批量处理完成: 成功 {stats['success']}/{stats['total']} 失败 {stats['failed']}")
        return stats

def main():
    """主程序入口"""
    print("""
    ==============================
     全自动TXT洗稿系统 - DeepSeek版
    ==============================
    """)
    
    processor = DeepSeekRewriter()
    stats = processor.batch_process()
    
    print(f"\n处理结果:")
    print(f"总文件数: {stats['total']}")
    print(f"成功: {stats['success']}")
    print(f"失败: {stats['failed']}")
    print("\n详细日志请查看 rewriter.log")

if __name__ == '__main__':
    main()