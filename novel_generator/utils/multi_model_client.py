"""
多模型API客户端
支持智谱AI、豆包等多种模型的调用和切换
"""

import os
import json
import time
import random
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import requests
from pathlib import Path

try:
    from volcenginesdkarkruntime import Ark
    ARK_AVAILABLE = True
except ImportError:
    ARK_AVAILABLE = False

from novel_generator.config.settings import Settings


class BaseModelClient:
    """基础模型客户端接口"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def chat_completion(self, model: str, messages: List[Dict[str, str]], **kwargs) -> str:
        """聊天补全 - 子类需要实现"""
        raise NotImplementedError
    
    def test_connection(self) -> bool:
        """测试连接 - 子类需要实现"""
        raise NotImplementedError


class ZhipuAIClient(BaseModelClient):
    """智谱AI客户端"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
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
        self.rate_limit_delay = 1.0
        self.last_request_time = 0
        self.circuit_breaker_threshold = 5
        self.consecutive_failures = 0
        self.circuit_breaker_timeout = 60
        self.circuit_breaker_until = 0
        
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
    
    def _make_request(self, model: str, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """发送API请求"""
        if not self._check_circuit_breaker():
            raise Exception("API服务暂时不可用，请稍后再试")
        
        url = f"{self.api_base_url}/chat/completions"
        
        request_data = {
            'model': model,
            'messages': messages,
            'max_tokens': kwargs.get('max_tokens', self.max_tokens),
            'temperature': kwargs.get('temperature', self.temperature),
            'top_p': kwargs.get('top_p', self.top_p),
            'stream': False
        }
        
        if 'frequency_penalty' in kwargs:
            request_data['frequency_penalty'] = kwargs['frequency_penalty']
        if 'presence_penalty' in kwargs:
            request_data['presence_penalty'] = kwargs['presence_penalty']
        
        for attempt in range(self.max_retries):
            try:
                self._apply_rate_limit()
                
                self.logger.info(f"发送智谱AI API请求 (尝试 {attempt + 1}/{self.max_retries})")
                response = self.session.post(url, json=request_data, timeout=self.timeout)
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', self.retry_delay * (1.5 ** attempt)))
                    self.logger.warning(f"请求过于频繁，等待 {retry_after} 秒后重试")
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                self._update_circuit_breaker(True)
                
                result = response.json()
                self.logger.info("智谱AI API请求成功")
                return result
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"智谱AI API请求异常: {e}")
                if attempt == self.max_retries - 1:
                    self._update_circuit_breaker(False)
                    raise Exception(f"智谱AI API请求失败: {e}")
                
                base_wait = self.retry_delay * (1.5 ** attempt)
                jitter = random.uniform(0.5, 1.5)
                wait_time = base_wait * jitter
                
                self.logger.warning(f"智谱AI API请求失败，{wait_time:.1f}秒后重试... (尝试 {attempt + 1}/{self.max_retries})")
                time.sleep(wait_time)
        
        self._update_circuit_breaker(False)
        return {}
    
    def chat_completion(self, model: str, messages: List[Dict[str, str]], **kwargs) -> str:
        """聊天补全"""
        try:
            response = self._make_request(model, messages, **kwargs)
            return response.get('choices', [{}])[0].get('message', {}).get('content', '')
        except Exception as e:
            raise Exception(f"智谱AI聊天补全失败: {e}")
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            test_prompt = "请回复'连接成功'以确认API正常工作。"
            response = self.chat_completion(
                self.settings.get_api_model('default'),
                [{'role': 'user', 'content': test_prompt}]
            )
            return response == '连接成功'
        except Exception as e:
            print(f"智谱AI连接测试失败: {e}")
            return False


class DoubaoClient(BaseModelClient):
    """豆包客户端"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.settings = Settings(config)
        
        if not ARK_AVAILABLE:
            raise Exception("volcenginesdkarkruntime 未安装，请先安装: pip install volcenginesdkarkruntime")
        
        # API配置
        self.api_key = config.get('doubao_api_key', os.environ.get("ARK_API_KEY", ''))
        self.max_tokens = config.get('max_tokens', 8000)
        self.temperature = config.get('temperature', 0.9)
        self.top_p = config.get('top_p', 0.9)
        
        # 初始化Ark客户端
        self.client = Ark(api_key=self.api_key)
        
        # 请求配置
        self.max_retries = config.get('system', {}).get('api', {}).get('max_retries', 5)
        self.retry_delay = config.get('system', {}).get('api', {}).get('retry_delay', 2)
        
        # 限流配置
        self.rate_limit_delay = 1.0
        self.last_request_time = 0
    
    def _apply_rate_limit(self):
        """应用限流"""
        now = time.time()
        time_since_last_request = now - self.last_request_time
        
        if time_since_last_request < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last_request
            self.logger.debug(f"豆包限流中，等待 {sleep_time:.2f} 秒")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def chat_completion(self, model: str, messages: List[Dict[str, str]], **kwargs) -> str:
        """聊天补全"""
        try:
            self._apply_rate_limit()
            
            self.logger.info(f"发送豆包API请求，模型: {model}")
            
            completion = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                temperature=kwargs.get('temperature', self.temperature),
                top_p=kwargs.get('top_p', self.top_p),
                stream=False
            )
            
            self.logger.info("豆包API请求成功")
            return completion.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"豆包聊天补全失败: {e}")
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            test_prompt = "请回复'连接成功'以确认API正常工作。"
            response = self.chat_completion(
                "doubao-seed-1-6-250615",  # 豆包默认模型
                [
                    {"role": "user", "content": test_prompt}
                ]
            )
            return response == '连接成功'
        except Exception as e:
            print(f"豆包连接测试失败: {e}")
            return False


class MultiModelClient:
    """多模型客户端管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化多模型客户端
        
        Args:
            config: 配置信息
        """
        self.config = config
        self.settings = Settings(config)
        self.logger = logging.getLogger(__name__)
        
        # 初始化各个模型客户端
        self.clients = {
            'zhipu': ZhipuAIClient(config),
            'doubao': DoubaoClient(config)
        }
        
        # 默认使用的模型
        self.default_model = config.get('default_model', 'zhipu')
        
        # 模型映射
        self.model_mapping = {
            'zhipu': {
                'logic_analysis_model': 'glm-4-long',
                'major_chapters_model': 'glm-4-long',
                'sub_chapters_model': 'glm-4-long',
                'expansion_model': 'glm-4.5-flash',
                'default_model': 'glm-4.5-flash'
            },
            'doubao': {
                'logic_analysis_model': 'doubao-seed-1-6-250615',
                'major_chapters_model': 'doubao-seed-1-6-250615',
                'sub_chapters_model': 'doubao-seed-1-6-250615',
                'expansion_model': 'doubao-seed-1-6-250615',
                'default_model': 'doubao-seed-1-6-250615'
            }
        }
    
    def get_client(self, model_type: str = None) -> BaseModelClient:
        """
        获取指定类型的客户端
        
        Args:
            model_type: 模型类型 ('zhipu', 'doubao', 'ark')
            
        Returns:
            BaseModelClient: 模型客户端
        """
        if not model_type:
            model_type = self.default_model
        
        if model_type not in self.clients:
            raise Exception(f"不支持的模型类型: {model_type}")
        
        client = self.clients[model_type]
        if client is None:
            raise Exception(f"模型客户端 {model_type} 未正确初始化")
        
        return client
    
    def chat_completion(self, model_type: str = None, model: str = None, 
                       messages: List[Dict[str, str]] = None, **kwargs) -> str:
        """
        聊天补全
        
        Args:
            model_type: 模型类型
            model: 具体模型名称
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            str: AI回复内容
        """
        if not messages:
            raise Exception("消息列表不能为空")
        
        client = self.get_client(model_type)
        
        if not model:
            # 根据阶段获取模型
            stage = kwargs.get('stage', 'default')
            model = self.get_model_for_stage(model_type or self.default_model, stage)
        
        return client.chat_completion(model, messages, **kwargs)
    
    def get_model_for_stage(self, model_type: str, stage: str) -> str:
        """
        获取指定模型类型和阶段的模型名称
        
        Args:
            model_type: 模型类型
            stage: 阶段名称
            
        Returns:
            str: 模型名称
        """
        stage_mapping = {
            "stage1": "logic_analysis_model",
            "stage2": "major_chapters_model", 
            "stage3": "sub_chapters_model",
            "stage4": "expansion_model",
            "stage5": "expansion_model",
            "default": "default_model"
        }
        
        model_key = stage_mapping.get(stage, "default_model")
        return self.model_mapping[model_type].get(model_key, self.model_mapping[model_type]["default_model"])
    
    def switch_model(self, model_type: str) -> bool:
        """
        切换默认模型
        
        Args:
            model_type: 模型类型
            
        Returns:
            bool: 切换是否成功
        """
        if model_type not in self.clients:
            self.logger.error(f"不支持的模型类型: {model_type}")
            return False
        
        if self.clients[model_type] is None:
            self.logger.error(f"模型客户端 {model_type} 未正确初始化")
            return False
        
        self.default_model = model_type
        self.logger.info(f"已切换到模型: {model_type}")
        return True
    
    def test_connection(self, model_type: str = None) -> bool:
        """
        测试指定模型的连接
        
        Args:
            model_type: 模型类型
            
        Returns:
            bool: 连接是否成功
        """
        try:
            client = self.get_client(model_type)
            return client.test_connection()
        except Exception as e:
            self.logger.error(f"测试 {model_type or self.default_model} 连接失败: {e}")
            return False
    
    def test_all_connections(self) -> Dict[str, bool]:
        """
        测试所有模型的连接
        
        Returns:
            Dict[str, bool]: 各模型连接状态
        """
        results = {}
        for model_type, client in self.clients.items():
            if client is not None:
                results[model_type] = self.test_connection(model_type)
            else:
                results[model_type] = False
        
        return results
    
    def get_available_models(self) -> List[str]:
        """
        获取可用的模型列表
        
        Returns:
            List[str]: 可用模型列表
        """
        available = []
        for model_type, client in self.clients.items():
            if client is not None:
                available.append(model_type)
        
        return available
    
    def get_current_model(self) -> str:
        """
        获取当前使用的模型
        
        Returns:
            str: 当前模型类型
        """
        return self.default_model
    
    def generate_outline(self, prompt: str, model_type: str = None) -> str:
        """生成大纲"""
        return self.chat_completion(
            model_type=model_type,
            stage='stage2',
            messages=[
                {'role': 'system', 'content': '你是一个专业的小说大纲策划师，擅长创作引人入胜的故事情节。'},
                {'role': 'user', 'content': prompt}
            ]
        )
    
    def expand_chapter(self, prompt: str, model_type: str = None) -> str:
        """扩写章节"""
        return self.chat_completion(
            model_type=model_type,
            stage='stage4',
            messages=[
                {'role': 'system', 'content': '你是一个专业的小说作家，擅长创作生动有趣的小说内容。'},
                {'role': 'user', 'content': prompt}
            ]
        )
    
    def analyze_content(self, content: str, model_type: str = None) -> str:
        """分析内容"""
        prompt = f"请分析以下小说内容：\n\n{content}\n\n请从情节、人物、语言风格等方面进行分析。"
        
        return self.chat_completion(
            model_type=model_type,
            stage='stage1',
            messages=[
                {'role': 'system', 'content': '你是一个专业的文学评论家，擅长分析小说作品。'},
                {'role': 'user', 'content': prompt}
            ]
        )
    
    def optimize_content(self, content: str, suggestions: str, model_type: str = None) -> str:
        """优化内容"""
        prompt = f"请根据以下建议优化小说内容：\n\n原始内容：\n{content}\n\n优化建议：\n{suggestions}"
        
        return self.chat_completion(
            model_type=model_type,
            stage='stage5',
            messages=[
                {'role': 'system', 'content': '你是一个专业的小说编辑，擅长优化和改进小说内容。'},
                {'role': 'user', 'content': prompt}
            ]
        )
    
    def check_consistency(self, chapters: List[str], model_type: str = None) -> str:
        """检查章节一致性"""
        content = '\n\n'.join([f"第{i+1}章：\n{chapter}" for i, chapter in enumerate(chapters)])
        
        prompt = f"请检查以下小说章节的一致性：\n\n{content}\n\n请检查人物性格、情节发展、时间线等方面的一致性。"
        
        return self.chat_completion(
            model_type=model_type,
            stage='stage3',
            messages=[
                {'role': 'system', 'content': '你是一个专业的小说编辑，擅长检查小说内容的一致性。'},
                {'role': 'user', 'content': prompt}
            ]
        )