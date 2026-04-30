"""
多模型API客户端
支持豆包、DeepSeek等多种模型的调用和切换
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

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from novel_generator.config.settings import Settings


class BaseModelClient:
    """基础模型客户端接口"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def chat_completion(
        self, model: str, messages: List[Dict[str, str]], **kwargs
    ) -> str:
        """聊天补全 - 子类需要实现"""
        raise NotImplementedError

    def test_connection(self) -> bool:
        """测试连接 - 子类需要实现"""
        raise NotImplementedError


class DoubaoClient(BaseModelClient):
    """豆包客户端 - 使用 OpenAI 兼容方式"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.settings = Settings(config)

        if not OPENAI_AVAILABLE:
            raise Exception("openai 未安装，请先安装: pip install openai")

        self.api_key = config.get("doubao_api_key", os.environ.get("ARK_API_KEY", ""))
        self.base_url = config.get(
            "doubao_api_base_url", "https://ark.cn-beijing.volces.com/api/v3"
        )
        self.max_tokens = config.get("max_tokens", 8000)
        self.temperature = config.get("temperature", 0.9)
        self.top_p = config.get("top_p", 0.9)

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        self.max_retries = config.get("system", {}).get("api", {}).get("max_retries", 5)
        self.retry_delay = config.get("system", {}).get("api", {}).get("retry_delay", 2)

        self.rate_limit_delay = 1.0
        self.last_request_time = 0

    def _apply_rate_limit(self):
        now = time.time()
        time_since_last_request = now - self.last_request_time

        if time_since_last_request < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last_request
            self.logger.debug(f"豆包限流中，等待 {sleep_time:.2f} 秒")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def chat_completion(
        self, model: str, messages: List[Dict[str, str]], **kwargs
    ) -> str:
        try:
            self._apply_rate_limit()

            self.logger.info(f"发送豆包API请求，模型: {model}")

            completion = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                top_p=kwargs.get("top_p", self.top_p),
                stream=False,
            )

            self.logger.info("豆包API请求成功")
            return completion.choices[0].message.content

        except Exception as e:
            raise Exception(f"豆包聊天补全失败: {e}")

    def test_connection(self) -> bool:
        """测试连接"""
        try:
            test_prompt = "请回复'连接成功'以确认API正常工作。"

            model = self.config.get("doubao_models", {}).get("expansion_model")
            if not model:
                raise ValueError("doubao_models.expansion_model 未配置")

            response = self.chat_completion(
                model,
                [{"role": "user", "content": test_prompt}],
            )
            return "连接成功" in response
        except Exception as e:
            print(f"豆包连接测试失败: {e}")
            return False


class DeepSeekClient(BaseModelClient):
    """DeepSeek客户端"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.settings = Settings(config)

        if not OPENAI_AVAILABLE:
            raise Exception("openai 未安装，请先安装: pip install openai")

        # API配置
        self.api_key = config.get(
            "deepseek_api_key", os.environ.get("DEEPSEEK_API_KEY", "")
        )
        self.base_url = config.get("deepseek_api_base_url", "https://api.deepseek.com")
        self.max_tokens = config.get("max_tokens", 8000)
        self.temperature = config.get("temperature", 0.7)
        self.top_p = config.get("top_p", 0.7)

        # 初始化OpenAI客户端
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

        # 请求配置
        self.max_retries = config.get("system", {}).get("api", {}).get("max_retries", 5)
        self.retry_delay = config.get("system", {}).get("api", {}).get("retry_delay", 2)

        # 限流配置
        self.rate_limit_delay = 1.0
        self.last_request_time = 0

    def _apply_rate_limit(self):
        """应用限流"""
        now = time.time()
        time_since_last_request = now - self.last_request_time

        if time_since_last_request < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last_request
            self.logger.debug(f"DeepSeek限流中，等待 {sleep_time:.2f} 秒")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def chat_completion(
        self, model: str, messages: List[Dict[str, str]], **kwargs
    ) -> str:
        """聊天补全，支持缓存统计"""
        try:
            self._apply_rate_limit()

            self.logger.info(f"发送DeepSeek API请求，模型: {model}")

            completion = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                top_p=kwargs.get("top_p", self.top_p),
                stream=False,
            )

            # 记录缓存统计
            self._log_cache_stats(completion)

            self.logger.info("DeepSeek API请求成功")
            return completion.choices[0].message.content

        except Exception as e:
            raise Exception(f"DeepSeek聊天补全失败: {e}")

    def _log_cache_stats(self, completion):
        """记录DeepSeek缓存统计"""
        try:
            usage = completion.usage
            if usage and hasattr(usage, 'prompt_cache_hit_tokens') and hasattr(usage, 'prompt_cache_miss_tokens'):
                hit_tokens = usage.prompt_cache_hit_tokens
                miss_tokens = usage.prompt_cache_miss_tokens
                total_input = usage.prompt_tokens
                total_output = usage.completion_tokens

                cache_rate = 0.0
                if total_input > 0:
                    cache_rate = hit_tokens / total_input * 100

                self.logger.info(
                    f"DeepSeek缓存统计: "
                    f"输入Token={total_input}, "
                    f"缓存命中={hit_tokens}, "
                    f"缓存未命中={miss_tokens}, "
                    f"命中率={cache_rate:.1f}%, "
                    f"输出Token={total_output}"
                )
        except Exception as e:
            # 缓存统计失败不影响主流程
            self.logger.debug(f"缓存统计记录失败: {e}")

    def test_connection(self) -> bool:
        """测试连接"""
        try:
            test_prompt = "请回复'连接成功'以确认API正常工作。"

            model = self.config.get("deepseek_models", {}).get("expansion_model")
            if not model:
                raise ValueError("deepseek_models.expansion_model 未配置")

            response = self.chat_completion(
                model, [{"role": "user", "content": test_prompt}]
            )
            return response == "连接成功"
        except Exception as e:
            print(f"DeepSeek连接测试失败: {e}")
            return False


class MultiModelClient:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.settings = Settings(config)
        self.logger = logging.getLogger(__name__)

        self.clients = {
            "doubao": DoubaoClient(config),
            "deepseek": DeepSeekClient(config) if OPENAI_AVAILABLE else None,
        }

        self.model_mapping = {
            "doubao": {
                "logic_analysis_model": "doubao-seed-2-0-lite-260215",
                "major_chapters_model": "doubao-seed-2-0-lite-260215",
                "sub_chapters_model": "doubao-seed-2-0-lite-260215",
                "expansion_model": "doubao-seed-2-0-lite-260215",
            },
            "deepseek": {
                "logic_analysis_model": "deepseek-chat",
                "major_chapters_model": "deepseek-chat",
                "sub_chapters_model": "deepseek-chat",
                "expansion_model": "deepseek-chat",
            },
        }

        if "doubao_models" in config:
            self.model_mapping["doubao"].update(config["doubao_models"])

        if "deepseek_models" in config:
            self.model_mapping["deepseek"].update(config["deepseek_models"])

    def get_client(self, model_type: str) -> BaseModelClient:
        """
        获取指定类型的客户端

        Args:
            model_type: 模型类型 ('doubao', 'deepseek')，必须显式指定

        Returns:
            BaseModelClient: 模型客户端

        Raises:
            ValueError: 如果 model_type 为空或未设置
            Exception: 如果不支持的模型类型或客户端未初始化
        """
        if not model_type:
            raise ValueError("model_type 不能为空，请通过 role_config.provider 或显式参数指定")

        if model_type not in self.clients:
            raise Exception(f"不支持的模型类型: {model_type}")

        client = self.clients[model_type]
        if client is None:
            raise Exception(f"模型客户端 {model_type} 未正确初始化")

        return client

    def chat_completion(
        self,
        model_type: str,
        model: str = None,
        messages: List[Dict[str, str]] = None,
        **kwargs,
    ) -> str:
        """
        聊天补全

        Args:
            model_type: 模型类型，必须显式指定
            model: 具体模型名称
            messages: 消息列表
            **kwargs: 其他参数

        Returns:
            str: AI回复内容
        """
        if not messages:
            raise Exception("消息列表不能为空")

        if not model_type:
            raise ValueError("model_type 不能为空，请通过 role_config.provider 或显式参数指定")

        client = self.get_client(model_type)

        if not model:
            # 根据阶段获取模型
            stage = kwargs.get("stage", "default")
            model = self.get_model_for_stage(model_type, stage)

        return client.chat_completion(model, messages, **kwargs)

    def chat_completion_with_role(
        self, role_config: Dict[str, Any], messages: List[Dict[str, str]], **kwargs
    ) -> str:
        """
        使用角色配置进行聊天补全

        Args:
            role_config: 角色配置，包含provider, model, temperature等
            messages: 消息列表
            **kwargs: 其他参数

        Returns:
            str: AI回复内容
        """
        if not messages:
            raise Exception("消息列表不能为空")

        provider = role_config.get("provider", "")
        if not provider:
            raise ValueError("role_config.provider 未设置，请先配置 AI 角色")

        model = role_config.get("model", "")

        client = self.get_client(provider)

        if not model:
            model = self.get_model_for_stage(provider, "default")

        merged_kwargs = {
            "temperature": role_config.get("temperature", 0.7),
            "top_p": role_config.get("top_p", 0.9),
            "max_tokens": role_config.get("max_tokens", 8000),
            **kwargs,
        }

        return client.chat_completion(model, messages, **merged_kwargs)

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
            "default": "expansion_model",
        }

        model_key = stage_mapping.get(stage, "expansion_model")
        return self.model_mapping[model_type].get(
            model_key, self.model_mapping[model_type].get("expansion_model", "")
        )

    def switch_model(self, model_type: str) -> bool:
        """
        验证模型是否可用（不再维护 default_model）

        Args:
            model_type: 模型类型

        Returns:
            bool: 模型是否可用
        """
        if model_type not in self.clients:
            self.logger.error(f"不支持的模型类型: {model_type}")
            return False

        if self.clients[model_type] is None:
            self.logger.error(f"模型客户端 {model_type} 未正确初始化")
            return False

        self.logger.info(f"模型可用: {model_type}")
        return True

    def test_connection(self, model_type: str) -> bool:
        """
        测试指定模型的连接

        Args:
            model_type: 模型类型，必须显式指定

        Returns:
            bool: 连接是否成功
        """
        if not model_type:
            raise ValueError("model_type 不能为空，请显式指定要测试的模型类型")

        try:
            client = self.get_client(model_type)
            return client.test_connection()
        except Exception as e:
            self.logger.error(f"测试 {model_type} 连接失败: {e}")
            return False

    def test_all_connections(self) -> Dict[str, bool]:
        """
        测试所有可用的模型连接

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
        已废弃：不再维护默认模型
        请使用 role_config.provider 获取当前使用的模型
        """
        raise NotImplementedError(
            "get_current_model 已废弃，请通过 role_config.provider 获取当前模型"
        )
