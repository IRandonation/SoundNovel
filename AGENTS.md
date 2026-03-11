# AGENTS.md - SoundNovel 智能编码指南

本文档为在此仓库中工作的智能编码代理提供规范指南。

## 项目概述

SoundNovel（小说创作 AI Agent）是一款 AI 辅助小说写作工具，使用多种 LLM 模型（智谱 AI、豆包、Ark）帮助生成长篇虚构作品，保持情节和人物发展的一致性。

**技术栈**: Python 3.13+, Streamlit, Flask, PyYAML, requests  
**依赖管理工具**: uv

---

## 构建 / 代码检查 / 测试命令

### 核心命令

```bash
# 同步依赖
uv sync

# ========== CLI 模式（命令行）==========

# 方式 1：使用统一入口
python soundnovel.py cli init                           # 初始化项目
python soundnovel.py cli outline                        # 生成章节大纲
python soundnovel.py cli expand --chapter 1             # 扩写指定章节
python soundnovel.py cli expand --start 1 --end 10      # 扩写章节范围

# 方式 2：使用模块方式（等效）
uv run python -m novel_generator.cli init
uv run python -m novel_generator.cli outline
uv run python -m novel_generator.cli expand --chapter 1

# ========== GUI 模式（图形界面）==========

# 方式 1：使用统一入口
python soundnovel.py gui

# 方式 2：直接使用 streamlit
uv run streamlit run gui_app.py

# ========== 查看帮助 ==========
python soundnovel.py --help
python soundnovel.py cli --help
uv run python -m novel_generator.cli --help
```

### 运行单个测试

**注意**: 本项目目前**未配置**测试框架。如需添加测试：

```bash
# 安装 pytest（如需）
uv add --dev pytest

# 运行所有测试
uv run pytest

# 运行单个测试文件
uv run pytest tests/test_file.py

# 运行单个测试函数
uv run pytest tests/test_file.py::test_function_name
```

### 开发命令

```bash
# 使用指定 Python 版本运行（如需）
uv run --python 3.13 python script.py

# 检查 Python 版本
python --version  # 应 >= 3.13.5
```

---

## 代码风格规范

### 通用规则

1. **Python 版本**: 3.13.5+ (在 `pyproject.toml` 中强制执行)
2. **编码**: 所有文件必须使用 UTF-8 编码
3. **换行符**: 使用 LF（Unix 风格）保持一致性
4. **缩进**: 4 个空格（不使用制表符）

### 导入

**顺序**（严格）：
```python
# 1. Standard library
import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

# 2. Third-party packages
import yaml
import requests
from volcenginesdkarkruntime import Ark

# 3. Local project imports
from novel_generator.config.settings import Settings
from novel_generator.utils.multi_model_client import MultiModelClient
```

### 类型注解

- **始终使用类型提示**用于函数参数和返回值
- 对复杂类型使用 `typing` 模块：`Dict`、`List`、`Optional`、`Any`、`Union`
- 对配置对象使用数据类

```python
# 正确示例
def expand_chapter(self, chapter_num: int, config: Dict[str, Any]) -> str:
    ...

# 正确示例 - 使用数据类
from dataclasses import dataclass, field

@dataclass
class APIConfig:
    api_key: str = ""
    max_retries: int = 5
    models: Dict[str, str] = field(default_factory=dict)

# 避免这样写
def expand_chapter(chapter_num, config):  # 缺少类型提示
    ...
```

### 命名规范

| 元素 | 规范 | 示例 |
|------|------|------|
| 函数 | snake_case | `expand_chapter()`, `load_config()` |
| 变量 | snake_case | `chapter_num`, `config_dict` |
| 类 | PascalCase | `ChapterExpander`, `Settings` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRIES`, `DEFAULT_WORD_COUNT` |
| 私有方法 | 前缀加 `_` | `_build_prompt()`, `_call_api()` |

### 文档字符串

请使用中文或英文保持一致。格式如下：

```python
def expand_chapter(self, chapter_num: int, outline: Dict[str, Any]) -> str:
    """
    扩写单个章节

    参数:
        chapter_num: 章节号
        outline: 章节大纲

    返回:
        str: 生成的章节内容
    """
```

### 错误处理

- 始终使用 try/except 捕获特定的异常类型
- 在重新抛出错误前记录日志
- 切勿静默吞掉异常

```python
# 正确示例
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
except FileNotFoundError:
    logger.error(f"配置文件不存在: {file_path}")
    raise
except yaml.YAMLError as e:
    logger.error(f"YAML解析失败: {e}")
    raise

# 避免这样写
try:
    ...
except:  # 裸异常捕获 - 永远不要这样做
    pass
```

### 文件操作

- 读写文本文件时始终指定 encoding='utf-8'
- 使用 `pathlib.Path` 进行路径操作
- 使用 `mkdir(parents=True, exist_ok=True)` 创建父目录

```python
# 正确示例
from pathlib import Path

output_path = Path(output_dir) / f"chapter_{chapter_num:02d}.txt"
output_path.parent.mkdir(parents=True, exist_ok=True)

with open(output_path, 'w', encoding='utf-8') as f:
    f.write(content)
```

### 日志记录

- 使用模块级 logger：`logger = logging.getLogger(__name__)`
- 日志级别：DEBUG < INFO < WARNING < ERROR < CRITICAL
- 在日志消息中包含上下文信息

```python
# 正确示例
logger = logging.getLogger(__name__)

logger.info(f"开始扩写第{chapter_num}章...")
logger.warning(f"内容字数偏少：{word_count} < {target_count}")
logger.error(f"保存章节文件失败: {e}")
```

### Class Structure

类内部按以下顺序组织：
1. `__init__` 方法
2. 公有方法
3. 私有方法（前缀加 `_`）
4. 属性（如有）

```python
class ChapterExpander:
    """章节扩写器类"""

    def __init__(self, config: Dict[str, Any]):
        ...

    # 公有方法
    def expand_chapter(self, ...):
        ...

    def save_chapter(self, ...):
        ...

    # 私有方法
    def _build_prompt(self, ...):
        ...

    def _call_ai_api(self, ...):
        ...
```

---

## 配置

### 配置文件

- **API 配置**: `05_script/config.json`（git 忽略，不要提交）
- **项目设置**: `novel_generator/config/settings.py`（数据类）
- **依赖**: `pyproject.toml`

### API 配置方式

**方式一：CLI 初始化时交互式配置（推荐）**

```bash
# 运行 init 命令时会提示输入 API Key
python soundnovel.py cli init

# 如需跳过交互式配置
python soundnovel.py cli init --skip-config
```

**方式二：GUI 界面配置**

在 GUI 左侧边栏的「项目初始化」面板中：
1. 选择服务商（智谱/豆包）
2. 输入 API Key
3. 点击「保存并测试连接」

**方式三：手动编辑配置文件**

直接编辑 `05_script/config.json` 文件。

### 环境变量

支持的环境变量：
- `ARK_API_KEY` - Ark API 密钥
- 通过 config.json 自定义密钥

---

## 代理注意事项

1. **切勿提交 `05_script/config.json`** - 它已在 `.gitignore` 中
2. **始终使用 `uv run`** 而非直接调用 `python` 以保持一致性
3. **API 密钥敏感** - 切勿在日志中记录或暴露
4. **覆盖前备份** - 现有文件应提前备份
5. **中文语言支持** - 项目使用中文编写注释和输出

---

## 目录结构参考

```
SoundNovel/
├── 01_source/                 # 核心材料（core_setting.yaml、overall_outline.yaml）
├── 02_outline/                # 生成的章节大纲
├── 03_draft/                  # 生成的章节草稿
├── 04_prompt/                 # 提示词模板和风格指南
├── 05_script/                 # 配置文件（config.json）
├── 06_log/                    # 日志文件
├── novel_generator/           # 核心包
│   ├── cli/                   # CLI 命令模块
│   ├── core/                  # 核心业务逻辑
│   ├── config/                # 配置（数据类）
│   ├── utils/                 # 工具（API 客户端、日志、文件处理）
│   └── templates/             # 模板文件
├── soundnovel.py              # 统一入口
├── gui_app.py                 # Streamlit GUI 入口
├── build_exe.py               # 打包脚本
├── pyproject.toml             # 依赖
└── uv.lock                    # 依赖锁定文件
```

---

## 快速参考：添加新功能

1. **新 API 模型**: 添加到 `novel_generator/utils/multi_model_client.py`
2. **新配置选项**: 添加到 `novel_generator/config/settings.py` 数据类
3. **新 CLI 命令**: 添加到 `novel_generator/cli/commands/` 目录
4. **新提示词模板**: 在 `04_prompt/` 添加 YAML 文件

如有疑问，请遵循代码库中的现有模式。
