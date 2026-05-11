"""
API配置管理器

负责管理多个API配置的CRUD操作、默认配置设置和连接测试
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class APIConfig:
    """API配置数据类"""

    id: str
    name: str
    provider: str  # "doubao" | "deepseek"
    api_key: str = ""
    api_base_url: str = ""
    models: Dict[str, str] = field(default_factory=dict)
    is_default: bool = False
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        """初始化后处理，设置默认URL"""
        if not self.api_base_url:
            if self.provider == "doubao":
                self.api_base_url = "https://ark.cn-beijing.volces.com/api/v3"
            elif self.provider == "deepseek":
                self.api_base_url = "https://api.deepseek.com"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "api_key": self.api_key,
            "api_base_url": self.api_base_url,
            "models": self.models,
            "is_default": self.is_default,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "APIConfig":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            provider=data.get("provider", ""),
            api_key=data.get("api_key", ""),
            api_base_url=data.get("api_base_url", ""),
            models=data.get("models", {}),
            is_default=data.get("is_default", False),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


class APIManager:
    """
    API配置管理器

    功能:
    - 多API配置的CRUD操作
    - 默认配置管理
    - API连接测试
    - 配置持久化存储
    """

    CONFIGS_DIR = "api/configs"

    # 默认模型配置
    DEFAULT_MODELS = {
        "doubao": {
            "expansion_model": "doubao-seed-2-0-lite-260215",
            "outline_model": "doubao-seed-2-0-lite-260215",
        },
        "deepseek": {
            "expansion_model": "deepseek-chat",
            "outline_model": "deepseek-chat",
        },
    }

    def __init__(self, project_root: str = "."):
        """
        初始化API管理器

        Args:
            project_root: 项目根目录路径
        """
        self.project_root = Path(project_root).resolve()
        self.configs_dir = self.project_root / self.CONFIGS_DIR
        self._ensure_configs_dir()

    def _ensure_configs_dir(self) -> None:
        """确保配置目录存在"""
        self.configs_dir.mkdir(parents=True, exist_ok=True)

    def _get_config_path(self, config_id: str) -> Path:
        """获取配置文件路径"""
        return self.configs_dir / f"{config_id}.json"

    def _generate_id(self, name: str) -> str:
        """根据名称生成配置ID"""
        import re

        # 转换为小写，替换空格为连字符，移除特殊字符
        config_id = re.sub(r'[^\w\s-]', '', name.lower())
        config_id = re.sub(r'[-\s]+', '-', config_id)

        # 如果ID已存在，添加时间戳后缀
        base_id = config_id
        counter = 1
        while self._get_config_path(config_id).exists():
            config_id = f"{base_id}-{counter}"
            counter += 1

        return config_id

    def _get_default_models(self, provider: str) -> Dict[str, str]:
        """获取指定服务商的默认模型配置"""
        return self.DEFAULT_MODELS.get(provider, {}).copy()

    # ========== CRUD 操作 ==========

    def list_configs(self) -> List[Dict[str, Any]]:
        """
        列出所有API配置

        Returns:
            List[Dict[str, Any]]: 配置列表（不包含敏感信息如api_key）
        """
        configs = []

        if not self.configs_dir.exists():
            return configs

        for config_file in sorted(self.configs_dir.glob("*.json")):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 返回配置摘要（隐藏API密钥）
                configs.append({
                    "id": data.get("id"),
                    "name": data.get("name"),
                    "provider": data.get("provider"),
                    "api_base_url": data.get("api_base_url"),
                    "is_default": data.get("is_default", False),
                    "has_api_key": bool(data.get("api_key")),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                })
            except Exception as e:
                logger.error(f"读取配置文件失败 {config_file}: {e}")

        return configs

    def get_config(self, config_id: str) -> Optional[APIConfig]:
        """
        获取指定配置

        Args:
            config_id: 配置ID

        Returns:
            Optional[APIConfig]: 配置对象，不存在则返回None
        """
        config_path = self._get_config_path(config_id)

        if not config_path.exists():
            logger.warning(f"配置不存在: {config_id}")
            return None

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return APIConfig.from_dict(data)
        except Exception as e:
            logger.error(f"读取配置失败 {config_id}: {e}")
            return None

    def create_config(self, config_data: Dict[str, Any]) -> Optional[APIConfig]:
        """
        创建新配置

        Args:
            config_data: 配置数据，包含 name, provider, api_key 等

        Returns:
            Optional[APIConfig]: 创建的配置对象，失败返回None
        """
        try:
            # 生成ID
            name = config_data.get("name", "")
            if not name:
                logger.error("配置名称不能为空")
                return None

            config_id = config_data.get("id") or self._generate_id(name)

            # 检查是否已存在
            if self._get_config_path(config_id).exists():
                logger.error(f"配置ID已存在: {config_id}")
                return None

            provider = config_data.get("provider", "")
            if provider not in ["doubao", "deepseek"]:
                logger.error(f"不支持的服务商: {provider}")
                return None

            # 创建配置对象
            now = datetime.now().isoformat()
            config = APIConfig(
                id=config_id,
                name=name,
                provider=provider,
                api_key=config_data.get("api_key", ""),
                api_base_url=config_data.get("api_base_url", ""),
                models=config_data.get("models") or self._get_default_models(provider),
                is_default=False,  # 新配置默认非默认
                created_at=now,
                updated_at=now,
            )

            # 保存配置
            self._save_config(config)

            # 如果是第一个配置，自动设为默认
            if len(self.list_configs()) == 1:
                self.set_default(config_id)

            logger.info(f"创建配置成功: {config_id}")
            return config

        except Exception as e:
            logger.error(f"创建配置失败: {e}")
            return None

    def update_config(
        self, config_id: str, config_data: Dict[str, Any]
    ) -> Optional[APIConfig]:
        """
        更新配置

        Args:
            config_id: 配置ID
            config_data: 更新的配置数据

        Returns:
            Optional[APIConfig]: 更新后的配置对象，失败返回None
        """
        config = self.get_config(config_id)
        if not config:
            logger.error(f"配置不存在: {config_id}")
            return None

        try:
            # 更新字段
            if "name" in config_data:
                config.name = config_data["name"]
            if "api_key" in config_data:
                config.api_key = config_data["api_key"]
            if "api_base_url" in config_data:
                config.api_base_url = config_data["api_base_url"]
            if "models" in config_data:
                config.models = config_data["models"]
            if "provider" in config_data and config_data["provider"] in [
                "doubao",
                "deepseek",
            ]:
                config.provider = config_data["provider"]
                # 如果切换了服务商且没有指定模型，使用默认模型
                if "models" not in config_data:
                    config.models = self._get_default_models(config.provider)

            config.updated_at = datetime.now().isoformat()

            self._save_config(config)
            logger.info(f"更新配置成功: {config_id}")
            return config

        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            return None

    def delete_config(self, config_id: str) -> bool:
        """
        删除配置

        Args:
            config_id: 配置ID

        Returns:
            bool: 是否删除成功
        """
        config_path = self._get_config_path(config_id)

        if not config_path.exists():
            logger.warning(f"配置不存在: {config_id}")
            return False

        try:
            # 如果删除的是默认配置，需要重新指定默认
            config = self.get_config(config_id)
            was_default = config.is_default if config else False

            os.remove(config_path)
            logger.info(f"删除配置成功: {config_id}")

            # 如果删除的是默认配置，重新指定第一个为默认
            if was_default:
                remaining = self.list_configs()
                if remaining:
                    self.set_default(remaining[0]["id"])

            return True

        except Exception as e:
            logger.error(f"删除配置失败: {e}")
            return False

    def _save_config(self, config: APIConfig) -> bool:
        """保存配置到文件"""
        try:
            config_path = self._get_config_path(config.id)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    # ========== 默认配置管理 ==========

    def set_default(self, config_id: str) -> bool:
        """
        设置默认配置

        Args:
            config_id: 配置ID

        Returns:
            bool: 是否设置成功
        """
        config = self.get_config(config_id)
        if not config:
            logger.error(f"配置不存在: {config_id}")
            return False

        try:
            # 取消其他配置的默认状态
            for other_config_file in self.configs_dir.glob("*.json"):
                try:
                    with open(other_config_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    if data.get("is_default"):
                        data["is_default"] = False
                        with open(other_config_file, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    logger.warning(f"更新其他配置默认状态失败: {e}")

            # 设置当前配置为默认
            config.is_default = True
            config.updated_at = datetime.now().isoformat()
            self._save_config(config)

            logger.info(f"设置默认配置成功: {config_id}")
            return True

        except Exception as e:
            logger.error(f"设置默认配置失败: {e}")
            return False

    def get_default(self) -> Optional[APIConfig]:
        """
        获取默认配置

        Returns:
            Optional[APIConfig]: 默认配置对象，不存在则返回None
        """
        try:
            # 查找标记为默认的配置
            for config_file in self.configs_dir.glob("*.json"):
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    if data.get("is_default"):
                        return APIConfig.from_dict(data)
                except Exception as e:
                    logger.warning(f"读取配置文件失败: {e}")

            # 如果没有标记为默认的，返回第一个
            configs = self.list_configs()
            if configs:
                return self.get_config(configs[0]["id"])

            return None

        except Exception as e:
            logger.error(f"获取默认配置失败: {e}")
            return None

    # ========== API连接测试 ==========

    def test_connection(self, config_id: str) -> Dict[str, Any]:
        """
        测试API连接

        Args:
            config_id: 配置ID

        Returns:
            Dict[str, Any]: 测试结果，包含 success, message, latency_ms
        """
        config = self.get_config(config_id)
        if not config:
            return {
                "success": False,
                "message": f"配置不存在: {config_id}",
                "latency_ms": 0,
            }

        if not config.api_key:
            return {
                "success": False,
                "message": "API密钥未配置",
                "latency_ms": 0,
            }

        import time

        start_time = time.time()

        try:
            # 根据服务商进行不同的连接测试
            if config.provider == "doubao":
                result = self._test_doubao_connection(config)
            elif config.provider == "deepseek":
                result = self._test_deepseek_connection(config)
            else:
                return {
                    "success": False,
                    "message": f"不支持的服务商: {config.provider}",
                    "latency_ms": 0,
                }

            latency_ms = int((time.time() - start_time) * 1000)
            result["latency_ms"] = latency_ms
            return result

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"连接测试失败: {e}")
            return {
                "success": False,
                "message": f"连接测试失败: {str(e)}",
                "latency_ms": latency_ms,
            }

    def _test_doubao_connection(self, config: APIConfig) -> Dict[str, str]:
        """测试豆包API连接"""
        try:
            import requests

            headers = {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            }

            # 尝试获取模型列表或进行简单的API调用
            response = requests.get(
                f"{config.api_base_url}/models",
                headers=headers,
                timeout=30,
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "连接成功",
                }
            else:
                return {
                    "success": False,
                    "message": f"API返回错误: HTTP {response.status_code}",
                }

        except ImportError:
            # 如果没有requests库，使用简单的socket测试
            return self._test_socket_connection(config.api_base_url)
        except Exception as e:
            return {
                "success": False,
                "message": f"连接失败: {str(e)}",
            }

    def _test_deepseek_connection(self, config: APIConfig) -> Dict[str, str]:
        """测试DeepSeek API连接"""
        try:
            import requests

            headers = {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            }

            # DeepSeek API测试 - 使用模型列表端点
            response = requests.get(
                f"{config.api_base_url}/models",
                headers=headers,
                timeout=30,
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "连接成功",
                }
            else:
                return {
                    "success": False,
                    "message": f"API返回错误: HTTP {response.status_code}",
                }

        except ImportError:
            return self._test_socket_connection(config.api_base_url)
        except Exception as e:
            return {
                "success": False,
                "message": f"连接失败: {str(e)}",
            }

    def _test_socket_connection(self, url: str) -> Dict[str, str]:
        """使用socket进行基础连接测试（当requests不可用时）"""
        try:
            import socket
            from urllib.parse import urlparse

            parsed = urlparse(url)
            host = parsed.hostname or ""
            port = parsed.port or (443 if parsed.scheme == "https" else 80)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                return {
                    "success": True,
                    "message": "网络连接成功（请安装requests库进行完整测试）",
                }
            else:
                return {
                    "success": False,
                    "message": f"无法连接到服务器: {host}:{port}",
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"连接测试失败: {str(e)}",
            }

    # ========== 便捷方法 ==========

    def get_config_for_provider(self, provider: str) -> Optional[APIConfig]:
        """
        获取指定服务商的配置

        Args:
            provider: 服务商名称 (doubao/deepseek)

        Returns:
            Optional[APIConfig]: 配置对象，不存在则返回None
        """
        configs = self.list_configs()
        for config_summary in configs:
            if config_summary["provider"] == provider:
                return self.get_config(config_summary["id"])
        return None

    def export_config(self, config_id: str) -> Optional[Dict[str, Any]]:
        """
        导出配置（包含敏感信息，谨慎使用）

        Args:
            config_id: 配置ID

        Returns:
            Optional[Dict[str, Any]]: 完整的配置数据
        """
        config = self.get_config(config_id)
        if config:
            return config.to_dict()
        return None

    def import_config(self, config_data: Dict[str, Any]) -> Optional[APIConfig]:
        """
        导入配置

        Args:
            config_data: 配置数据

        Returns:
            Optional[APIConfig]: 导入的配置对象
        """
        # 移除ID避免冲突，让系统生成新ID
        if "id" in config_data:
            del config_data["id"]

        # 重置时间戳
        config_data["created_at"] = datetime.now().isoformat()
        config_data["updated_at"] = config_data["created_at"]

        return self.create_config(config_data)


def get_api_manager(project_root: str = ".") -> APIManager:
    """
    获取API管理器实例

    Args:
        project_root: 项目根目录

    Returns:
        APIManager: API管理器实例
    """
    return APIManager(project_root)
