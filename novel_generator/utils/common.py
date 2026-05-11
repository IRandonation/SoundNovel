"""
公共工具函数模块

提供配置加载、日志设置、项目验证等共享功能（新架构版本）
"""

import os
import sys
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional


def get_project_root() -> Path:
    """
    获取项目根目录

    支持从脚本位置、工作目录或PyInstaller打包环境检测

    Returns:
        Path: 项目根目录路径
    """
    # 如果是PyInstaller打包的环境
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent

    # 尝试从当前文件位置推断（向上两级）
    try:
        current_file = Path(__file__)
        if current_file.exists():
            # novel_generator/utils/common.py -> 项目根目录
            return current_file.parent.parent.parent
    except:
        pass

    # 使用当前工作目录
    return Path.cwd()


def get_novels_dir(project_root: Optional[Path] = None) -> Path:
    """
    获取小说目录

    Args:
        project_root: 项目根目录，默认自动检测

    Returns:
        Path: 小说目录路径
    """
    if project_root is None:
        project_root = get_project_root()
    return project_root / "novels"


def get_current_novel_id(project_root: Optional[Path] = None) -> Optional[str]:
    """
    获取当前小说ID

    Args:
        project_root: 项目根目录

    Returns:
        Optional[str]: 当前小说ID，如果没有则返回None
    """
    from novel_generator.novel_manager import NovelManager

    if project_root is None:
        project_root = get_project_root()

    novel_manager = NovelManager(str(get_novels_dir(project_root)))
    return novel_manager.get_current_novel_id()


def get_current_novel_paths(project_root: Optional[Path] = None) -> Optional[Dict[str, Path]]:
    """
    获取当前小说的路径配置

    Args:
        project_root: 项目根目录

    Returns:
        Optional[Dict[str, Path]]: 路径配置字典，如果没有当前小说则返回None
    """
    from novel_generator.novel_manager import NovelManager

    if project_root is None:
        project_root = get_project_root()

    novel_id = get_current_novel_id(project_root)
    if not novel_id:
        return None

    novel_manager = NovelManager(str(get_novels_dir(project_root)))
    novel = novel_manager.get_novel(novel_id)
    if not novel:
        return None

    return novel.get_paths()


def setup_logging(
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    log_to_console: bool = True
) -> logging.Logger:
    """
    设置日志配置

    Args:
        log_file: 日志文件路径（默认: 当前小说的logs/system/novel_generator.log）
        level: 日志级别
        log_to_console: 是否输出到控制台

    Returns:
        logging.Logger: 配置好的logger实例
    """
    logger = logging.getLogger()
    logger.setLevel(level)

    # 清除现有处理器
    logger.handlers.clear()

    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 确定日志文件路径
    if log_file is None:
        project_root = get_project_root()
        novel_id = get_current_novel_id(project_root)
        if novel_id:
            log_path = project_root / "novels" / novel_id / "logs" / "system" / "novel_generator.log"
        else:
            log_path = project_root / "novels" / ".logs" / "novel_generator.log"
    else:
        log_path = Path(log_file)

    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 控制台处理器
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载配置（新架构版本）

    从当前小说配置加载API配置

    Args:
        config_path: 配置文件路径（已废弃，保留参数兼容性）

    Returns:
        Dict[str, Any]: 配置字典
    """
    from novel_generator.config.config_manager import ConfigManager

    project_root = get_project_root()
    novel_id = get_current_novel_id(project_root)

    if not novel_id:
        raise FileNotFoundError("未选择小说，请先运行 'soundnovel novel create' 创建小说")

    config_manager = ConfigManager(str(project_root), novel_id)
    config = config_manager.get_api_config()

    if 'paths' not in config:
        config['paths'] = {}
    config['paths']['project_root'] = str(project_root)

    return config


def load_yaml_file(file_path: Path, default: Optional[Dict] = None) -> Dict[str, Any]:
    """
    安全加载YAML文件

    Args:
        file_path: YAML文件路径
        default: 加载失败时返回的默认值

    Returns:
        Dict[str, Any]: YAML内容字典
    """
    try:
        if not file_path.exists():
            if default is not None:
                return default
            raise FileNotFoundError(f"文件不存在: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = yaml.safe_load(f)
            return content if content is not None else (default or {})

    except yaml.YAMLError as e:
        logging.error(f"YAML解析错误 {file_path}: {e}")
        if default is not None:
            return default
        raise

    except Exception as e:
        logging.error(f"加载文件失败 {file_path}: {e}")
        if default is not None:
            return default
        raise


def validate_project_structure(
    project_root: Optional[Path] = None,
    required_files: Optional[List[str]] = None,
    raise_on_error: bool = False
) -> bool:
    """
    验证项目结构完整性（新架构版本）

    Args:
        project_root: 项目根目录，默认自动检测
        required_files: 必需文件列表（相对于小说source目录）
        raise_on_error: 验证失败时是否抛出异常

    Returns:
        bool: 验证是否通过
    """
    if project_root is None:
        project_root = get_project_root()

    novel_id = get_current_novel_id(project_root)
    if not novel_id:
        error_msg = "未选择小说"
        if raise_on_error:
            raise FileNotFoundError(error_msg)
        return False

    # 默认必需文件（新架构）
    if required_files is None:
        required_files = [
            "core_setting.yaml",
            "overall_outline.yaml",
        ]

    paths = get_current_novel_paths(project_root)
    if not paths:
        error_msg = "无法获取小说路径"
        if raise_on_error:
            raise FileNotFoundError(error_msg)
        return False

    source_dir = paths.get("source_dir")
    if not source_dir:
        error_msg = "无法获取素材目录"
        if raise_on_error:
            raise FileNotFoundError(error_msg)
        return False

    missing_files = []
    for file_path in required_files:
        full_path = source_dir / file_path
        if not full_path.exists():
            missing_files.append(file_path)

    if missing_files:
        error_msg = f"缺少必要文件: {', '.join(missing_files)}"
        logging.error(error_msg)
        if raise_on_error:
            raise FileNotFoundError(error_msg)
        return False

    return True


def find_outline_files(project_root: Optional[Path] = None) -> List[Path]:
    """
    查找所有大纲文件（新架构版本）

    Args:
        project_root: 项目根目录

    Returns:
        List[Path]: 大纲文件路径列表
    """
    if project_root is None:
        project_root = get_project_root()

    paths = get_current_novel_paths(project_root)
    if not paths:
        return []

    outline_dir = paths.get("outline_dir")
    if not outline_dir or not outline_dir.exists():
        return []

    # 查找YAML、JSON和TXT文件
    yaml_files = list(outline_dir.glob("chapter_outline_*.yaml"))
    json_files = list(outline_dir.glob("*.json"))
    txt_files = list(outline_dir.glob("*.txt"))

    return sorted(yaml_files + json_files + txt_files)


def get_latest_outline_file(project_root: Optional[Path] = None) -> Optional[Path]:
    """
    获取最新的大纲文件（新架构版本）

    Args:
        project_root: 项目根目录

    Returns:
        Optional[Path]: 最新大纲文件路径，如果没有则返回None
    """
    outline_files = find_outline_files(project_root)
    return outline_files[-1] if outline_files else None


def ensure_directories(project_root: Optional[Path] = None) -> None:
    """
    确保项目目录结构存在（新架构版本）

    Args:
        project_root: 项目根目录
    """
    if project_root is None:
        project_root = get_project_root()

    novels_dir = get_novels_dir(project_root)
    novels_dir.mkdir(parents=True, exist_ok=True)


def load_core_setting(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    加载核心设定（新架构版本）

    Args:
        project_root: 项目根目录

    Returns:
        Dict[str, Any]: 核心设定字典
    """
    if project_root is None:
        project_root = get_project_root()

    paths = get_current_novel_paths(project_root)
    if not paths:
        return {}

    setting_path = paths.get("source_dir", Path()) / "core_setting.yaml"
    return load_yaml_file(setting_path, default={})


def load_overall_outline(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    加载整体大纲（新架构版本）

    Args:
        project_root: 项目根目录

    Returns:
        Dict[str, Any]: 整体大纲字典
    """
    if project_root is None:
        project_root = get_project_root()

    paths = get_current_novel_paths(project_root)
    if not paths:
        return {}

    outline_path = paths.get("source_dir", Path()) / "overall_outline.yaml"
    return load_yaml_file(outline_path, default={})


def load_style_guide(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    加载风格指导（新架构版本）

    Args:
        project_root: 项目根目录

    Returns:
        Dict[str, Any]: 风格指导字典
    """
    if project_root is None:
        project_root = get_project_root()

    paths = get_current_novel_paths(project_root)
    if not paths:
        return {}

    style_path = paths.get("prompts_dir", Path()) / "style_guide.yaml"
    return load_yaml_file(style_path, default={})


def save_yaml_file(file_path: Path, data: Dict[str, Any]) -> None:
    """
    保存数据到YAML文件

    Args:
        file_path: 目标文件路径
        data: 要保存的字典数据
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def parse_chapter_range(outline_data: Dict[str, Any]) -> tuple[int, int]:
    """
    从大纲数据解析章节范围

    Args:
        outline_data: 大纲字典

    Returns:
        tuple[int, int]: (起始章节, 结束章节)
    """
    import re

    chapters = []
    for key in outline_data.keys():
        # 支持 "第X章" 格式
        match = re.search(r'第?(\d+)章?', str(key))
        if match:
            chapters.append(int(match.group(1)))

    if not chapters:
        return 1, 1

    return min(chapters), max(chapters)


def format_chapter_key(chapter_num: int) -> str:
    """
    格式化章节键名

    Args:
        chapter_num: 章节号

    Returns:
        str: 格式化的章节键名（如"第1章"）
    """
    return f"第{chapter_num}章"


def get_chapter_data(outline_data: Dict[str, Any], chapter_num: int) -> Optional[Dict[str, Any]]:
    """
    获取指定章节的数据

    Args:
        outline_data: 大纲字典
        chapter_num: 章节号

    Returns:
        Optional[Dict]: 章节数据，未找到返回None
    """
    # 尝试多种键名格式
    keys_to_try = [
        format_chapter_key(chapter_num),
        str(chapter_num),
        f"Chapter {chapter_num}",
    ]

    for key in keys_to_try:
        if key in outline_data:
            return outline_data[key]

    return None
