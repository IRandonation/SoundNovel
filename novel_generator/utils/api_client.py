"""
API客户端
负责与智谱AI API的交互
"""

import json
import time
import random
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import requests
from pathlib import Path

from novel_generator.config.settings import Settings


class ZhipuAIClient:
    """智谱AI客户端"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化API客户端
        
        Args:
            config: 配置信息
        """
        self.config = config
        self.settings = Settings(config)
        
        # API配置
        self.api_key = config.get('api_key', '')
        self.api_base_url = config.get('api_base_url', 'https://open.bigmodel.cn/api/paas/v4')
        self.max_tokens = config.get('max_tokens', 4000)
        self.temperature = config.get('temperature', 0.7)
        self.top_p = config.get('top_p', 0.7)
        
        # 请求配置
        self.max_retries = config.get('system', {}).get('api', {}).get('max_retries', 5)
        self.retry_delay = config.get('system', {}).get('api', {}).get('retry_delay', 2)
        self.timeout = config.get('system', {}).get('api', {}).get('timeout', 60)
        
        # 限流和熔断配置
        self.rate_limit_delay = 1.0  # 请求间隔（秒）
        self.last_request_time = 0
        self.circuit_breaker_threshold = 5  # 连续失败次数阈值
        self.consecutive_failures = 0
        self.circuit_breaker_timeout = 60  # 熔断器超时时间（秒）
        self.circuit_breaker_until = 0
        
        # 日志
        self.logger = logging.getLogger(__name__)
        
        # 会话
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
        
    def _check_circuit_breaker(self) -> bool:
        """检查熔断器状态"""
        now = time.time()
        if now < self.circuit_breaker_until:
            self.logger.warning(f"熔断器激活中，还需等待 {self.circuit_breaker_until - now:.1f} 秒")
            return False
        
        # 重置熔断器
        if self.consecutive_failures >= self.circuit_breaker_threshold:
            self.logger.info("熔断器重置")
            self.consecutive_failures = 0
        
        return True
    
    def _update_circuit_breaker(self, success: bool):
        """更新熔断器状态"""
        if success:
            self.consecutive_failures = 0
            self.circuit_breaker_until = 0
        else:
            self.consecutive_failures += 1
            if self.consecutive_failures >= self.circuit_breaker_threshold:
                self.circuit_breaker_until = time.time() + self.circuit_breaker_timeout
                self.logger.warning(f"熔断器激活，将在 {self.circuit_breaker_timeout} 秒后重置")
    
    def _apply_rate_limit(self):
        """应用限流"""
        now = time.time()
        time_since_last_request = now - self.last_request_time
        
        if time_since_last_request < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last_request
            self.logger.debug(f"限流中，等待 {sleep_time:.2f} 秒")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, model: str, messages: List[Dict[str, str]],
                     **kwargs) -> Dict[str, Any]:
        """
        发送API请求
        
        Args:
            model: 模型名称
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: API响应
        """
        # 检查熔断器
        if not self._check_circuit_breaker():
            raise Exception("API服务暂时不可用，请稍后再试")
        
        url = f"{self.api_base_url}/chat/completions"
        
        # 构建请求参数
        request_data = {
            'model': model,
            'messages': messages,
            'max_tokens': kwargs.get('max_tokens', self.max_tokens),
            'temperature': kwargs.get('temperature', self.temperature),
            'top_p': kwargs.get('top_p', self.top_p),
            'stream': False
        }
        
        # 添加可选参数
        if 'frequency_penalty' in kwargs:
            request_data['frequency_penalty'] = kwargs['frequency_penalty']
        if 'presence_penalty' in kwargs:
            request_data['presence_penalty'] = kwargs['presence_penalty']
        
        # 重试机制
        for attempt in range(self.max_retries):
            try:
                # 应用限流
                self._apply_rate_limit()
                
                self.logger.info(f"发送API请求 (尝试 {attempt + 1}/{self.max_retries})")
                response = self.session.post(
                    url,
                    json=request_data,
                    timeout=self.timeout
                )
                
                # 检查响应状态
                if response.status_code == 429:
                    # 请求过于频繁
                    retry_after = int(response.headers.get('Retry-After', self.retry_delay * (2 ** attempt)))
                    self.logger.warning(f"请求过于频繁，等待 {retry_after} 秒后重试")
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                
                # 成功请求，更新熔断器状态
                self._update_circuit_breaker(True)
                
                result = response.json()
                self.logger.info("API请求成功")
                return result
                
            except requests.exceptions.Timeout as e:
                self.logger.warning(f"API请求超时: {e}")
                if attempt == self.max_retries - 1:
                    self._update_circuit_breaker(False)
                    raise Exception(f"API请求超时: {e}")
                
            except requests.exceptions.ConnectionError as e:
                self.logger.warning(f"API连接错误: {e}")
                if attempt == self.max_retries - 1:
                    self._update_circuit_breaker(False)
                    raise Exception(f"API连接错误: {e}")
                
            except requests.exceptions.HTTPError as e:
                self.logger.warning(f"API HTTP错误: {e}")
                if attempt == self.max_retries - 1:
                    self._update_circuit_breaker(False)
                    raise Exception(f"API HTTP错误: {e}")
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"API请求异常: {e}")
                if attempt == self.max_retries - 1:
                    self._update_circuit_breaker(False)
                    raise Exception(f"API请求失败: {e}")
            
            # 计算等待时间（指数退避 + 随机抖动）
            base_wait = self.retry_delay * (2 ** attempt)
            jitter = random.uniform(0.5, 1.5)  # 随机抖动因子
            wait_time = base_wait * jitter
            
            self.logger.warning(f"API请求失败，{wait_time:.1f}秒后重试... (尝试 {attempt + 1}/{self.max_retries})")
            time.sleep(wait_time)
        
        # 如果所有重试都失败，更新熔断器状态
        self._update_circuit_breaker(False)
        return {}
    
    def chat_completion(self, model: str, messages: List[Dict[str, str]], 
                       **kwargs) -> str:
        """
        聊天补全
        
        Args:
            model: 模型名称
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            str: AI回复内容
        """
        try:
            response = self._make_request(model, messages, **kwargs)
            return response.get('choices', [{}])[0].get('message', {}).get('content', '')
            
        except Exception as e:
            raise Exception(f"聊天补全失败: {e}")
    
    def generate_outline(self, prompt: str, model: str = None) -> str:
        """
        生成大纲
        
        Args:
            prompt: 提示词
            model: 模型名称
            
        Returns:
            str: 生成的大纲
        """
        if not model:
            model = self.settings.get_api_model('stage2')
        
        messages = [
            {'role': 'system', 'content': '你是一个专业的小说大纲策划师，擅长创作引人入胜的故事情节。'},
            {'role': 'user', 'content': prompt}
        ]
        
        return self.chat_completion(model, messages)
    
    def expand_chapter(self, prompt: str, model: str = None) -> str:
        """
        扩写章节
        
        Args:
            prompt: 提示词
            model: 模型名称
            
        Returns:
            str: 生成的章节内容
        """
        if not model:
            model = self.settings.get_api_model('stage4')
        
        messages = [
            {'role': 'system', 'content': '你是一个专业的小说作家，擅长创作生动有趣的小说内容。'},
            {'role': 'user', 'content': prompt}
        ]
        
        return self.chat_completion(model, messages)
    
    def analyze_content(self, content: str, model: str = None) -> str:
        """
        分析内容
        
        Args:
            content: 要分析的内容
            model: 模型名称
            
        Returns:
            str: 分析结果
        """
        if not model:
            model = self.settings.get_api_model('stage1')
        
        prompt = f"请分析以下小说内容：\n\n{content}\n\n请从情节、人物、语言风格等方面进行分析。"
        
        messages = [
            {'role': 'system', 'content': '你是一个专业的文学评论家，擅长分析小说作品。'},
            {'role': 'user', 'content': prompt}
        ]
        
        return self.chat_completion(model, messages)
    
    def optimize_content(self, content: str, suggestions: str, 
                        model: str = None) -> str:
        """
        优化内容
        
        Args:
            content: 原始内容
            suggestions: 优化建议
            model: 模型名称
            
        Returns:
            str: 优化后的内容
        """
        if not model:
            model = self.settings.get_api_model('stage5')
        
        prompt = f"请根据以下建议优化小说内容：\n\n原始内容：\n{content}\n\n优化建议：\n{suggestions}"
        
        messages = [
            {'role': 'system', 'content': '你是一个专业的小说编辑，擅长优化和改进小说内容。'},
            {'role': 'user', 'content': prompt}
        ]
        
        return self.chat_completion(model, messages)
    
    def check_consistency(self, chapters: List[str], model: str = None) -> str:
        """
        检查章节一致性
        
        Args:
            chapters: 章节内容列表
            model: 模型名称
            
        Returns:
            str: 一致性检查结果
        """
        if not model:
            model = self.settings.get_api_model('stage3')
        
        content = '\n\n'.join([f"第{i+1}章：\n{chapter}" for i, chapter in enumerate(chapters)])
        
        prompt = f"请检查以下小说章节的一致性：\n\n{content}\n\n请检查人物性格、情节发展、时间线等方面的一致性。"
        
        messages = [
            {'role': 'system', 'content': '你是一个专业的小说编辑，擅长检查小说内容的一致性。'},
            {'role': 'user', 'content': prompt}
        ]
        
        return self.chat_completion(model, messages)
    
    def get_model_info(self, model: str = None) -> Dict[str, Any]:
        """
        获取模型信息
        
        Args:
            model: 模型名称
            
        Returns:
            Dict[str, Any]: 模型信息
        """
        if not model:
            model = self.settings.get_api_model('default')
        
        url = f"{self.api_base_url}/models/{model}"
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            raise Exception(f"获取模型信息失败: {e}")
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        列出可用模型
        
        Returns:
            List[Dict[str, Any]]: 模型列表
        """
        url = f"{self.api_base_url}/models"
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json().get('data', [])
            
        except Exception as e:
            raise Exception(f"获取模型列表失败: {e}")
    
    def test_connection(self) -> bool:
        """
        测试API连接
        
        Returns:
            bool: 是否连接成功
        """
        try:
            # 使用简单的测试请求
            test_prompt = "请回复'连接成功'以确认API正常工作。"
            response = self.chat_completion(
                self.settings.get_api_model('default'),
                [{'role': 'user', 'content': test_prompt}]
            )
            
            return response == '连接成功'
            
        except Exception as e:
            print(f"API连接测试失败: {e}")
            return False
    
    def get_token_usage(self, response: Dict[str, Any]) -> Dict[str, int]:
        """
        获取token使用情况
        
        Args:
            response: API响应
            
        Returns:
            Dict[str, int]: token使用情况
        """
        try:
            usage = response.get('usage', {})
            return {
                'prompt_tokens': usage.get('prompt_tokens', 0),
                'completion_tokens': usage.get('completion_tokens', 0),
                'total_tokens': usage.get('total_tokens', 0)
            }
        except:
            return {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
    
    def estimate_tokens(self, text: str) -> int:
        """
        估算token数量
        
        Args:
            text: 文本内容
            
        Returns:
            int: 估算的token数量
        """
        # 简单的token估算（实际应该使用专业的tokenizer）
        # 中文：1个token约等于1-2个字符
        # 英文：1个token约等于4个字符
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        other_chars = len(text) - chinese_chars
        
        return int(chinese_chars * 1.5 + other_chars * 0.25)
    
    def close(self):
        """关闭会话"""
        self.session.close()


class APIMonitor:
    """API监控器"""
    
    def __init__(self, client: ZhipuAIClient):
        """
        初始化API监控器
        
        Args:
            client: API客户端
        """
        self.client = client
        self.request_count = 0
        self.total_tokens = 0
        self.start_time = datetime.now()
        
    def record_request(self, tokens_used: int = 0):
        """记录API请求"""
        self.request_count += 1
        self.total_tokens += tokens_used
        
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        return {
            'request_count': self.request_count,
            'total_tokens': self.total_tokens,
            'duration': duration,
            'requests_per_minute': self.request_count / (duration / 60) if duration > 0 else 0,
            'tokens_per_minute': self.total_tokens / (duration / 60) if duration > 0 else 0
        }
    
    def reset(self):
        """重置统计信息"""
        self.request_count = 0
        self.total_tokens = 0
        self.start_time = datetime.now()