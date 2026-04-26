# AGENTS.md - SoundNovel 智能编码指南

本文档为在此仓库中工作的智能编码代理提供规范指南。

## 项目概述

SoundNovel（小说创作 AI Agent）是一款 AI 辅助小说写作工具，使用多种 LLM 模型（豆包、DeepSeek）帮助生成长篇虚构作品，保持情节和人物发展的一致性。

**技术栈**: Python 3.13+, Flask, PyYAML, requests  
**依赖管理工具**: uv

---

## Prompt系统架构

### 三角色设计

本项目采用**三角色协作流程**：

| 角色 | 职责 | 文件位置 |
|------|------|----------|
| **Generator (生成者)** | 大纲生成、章节扩写 | `ai_roles.py` + `chapter_expander.py` |
| **Reviewer (评审者)** | 质量检查、一致性检查 | `ai_roles.py` + `chapter_expander.py` |
| **Refiner (润色者)** | 内容润色、问题修复 | `ai_roles.py` + `chapter_expander.py` |

### Prompt分类与位置

#### 1. System Prompt (角色定义)

**位置**: `novel_generator/core/ai_roles.py` 第26-65行

```
DEFAULT_SYSTEM_PROMPTS = {
    AIRole.GENERATOR: "你是一个专业的网络小说作家...",
    AIRole.REVIEWER: "你是一个专业的文学编辑...",
    AIRole.REFINER: "你是一个专业的文字润色专家..."
}
```

**可配置位置**:
- `05_script/generation_config.json` → `prompts.system_prompts`
- 运行时可通过CLI修改

#### 2. 生成Prompt (章节扩写)

**位置**: `novel_generator/core/chapter_expander.py` 第197-239行

**方法**: `_build_generation_prompt()`

**注入内容**:
- 核心设定 (core_setting)
- 前文剧情摘要 (previous_context)
- 本章大纲 (chapter_outline)
- **人物状态追踪** (character_tracker)
- **伏笔追踪** (foreshadowing_tracker)
- **情感弧线** (emotional_arc_tracker)
- 风格要求 (style_guide)

#### 3. 评审Prompt

**位置**: `novel_generator/core/chapter_expander.py` 第249-284行

**方法**: `_review_chapter()`

**评审维度**:
1. 剧情一致性 (0-100分)
2. 禁忌词检测 (0-100分)
3. AI感检测 (0-100分)
4. 情节推进 (0-100分)
5. 文笔质量 (0-100分)

**通过条件**: 总分≥70分且无严重问题

#### 4. 润色Prompt

**位置**: `novel_generator/core/chapter_expander.py` 第321-343行

**方法**: `_refine_chapter()`

**输入**: 原始内容 + 评审问题 + 润色建议

#### 5. Tracker Prompt (上下文生成)

| Tracker | 文件 | 方法 | 注入位置 |
|---------|------|------|----------|
| 人物追踪 | `character_tracker.py` | `get_context_for_chapter()` | 生成prompt第4部分 |
| 伏笔追踪 | `foreshadowing_tracker.py` | `get_context_for_chapter()` | 生成prompt第5部分 |
| 情感弧线 | `emotional_arc_tracker.py` | `get_context_for_chapter()` | 生成prompt第6部分 |

### Prompt注入流程

```
章节扩写流程:
  │
  ├─► 加载Tracker上下文 (chapter_expander.py:207-209)
  │     ├─ character_tracker.get_context_for_chapter()
  │     ├─ foreshadowing_tracker.get_context_for_chapter()
  │     └─ emotional_arc_tracker.get_context_for_chapter()
  │
  ├─► 构建生成Prompt (_build_generation_prompt)
  │     └─ 注入所有上下文到prompt模板
  │
  ├─► 调用Generator生成 (AIRole.GENERATOR)
  │
  └─► 评审循环 (最多max_refine_iterations次)
        ├─► Reviewer评审
        ├─► [通过?] → 返回内容
        └─► [未通过] → Refiner润色 → 再评审
```

### 配置文件优先级

```
用户修改 > generation_config.json > generation_config.py默认值 > ai_roles.py完整版
```

**修改Prompt的方式**:
1. **运行时修改**: 编辑 `05_script/generation_config.json`
2. **代码级修改**: 编辑 `ai_roles.py` 的 `DEFAULT_SYSTEM_PROMPTS`
3. **CLI命令**: `python soundnovel.py cli settings --interactive`

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
python soundnovel.py cli agent                          # 启动 Agent 对话模式

# 方式 2：使用模块方式（等效）
uv run python -m novel_generator.cli init
uv run python -m novel_generator.cli outline
uv run python -m novel_generator.cli expand --chapter 1

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

- **生成配置**: `05_script/generation_config.json`（包含所有prompt模板和角色配置）
- **API 配置**: `05_script/session.json`（API密钥存储，git忽略）
- **项目设置**: `novel_generator/config/settings.py`（数据类）
- **依赖**: `pyproject.toml`

### 配置文件结构

```json
// 05_script/generation_config.json
{
  "generation": {
    "max_refine_iterations": 3,    // 润色最大迭代次数
    "pass_score_threshold": 70,     // 评审通过分数
    "context_chapters": 10,         // 上下文章节数
    "default_word_count": 1500      // 默认字数目标
  },
  "roles": {
    "generator": { "provider": "doubao", "model": "doubao-lite", "temperature": 0.7 },
    "reviewer": { "provider": "deepseek", "model": "deepseek-chat", "temperature": 0.3 },
    "refiner": { "provider": "doubao", "model": "doubao-lite", "temperature": 0.5 }
  },
  "prompts": {
    "system_prompts": { "generator": "...", "reviewer": "...", "refiner": "..." },
    "generation_prompts": { "chapter_generation": {...} },
    "review_prompts": { "chapter_review": {...} },
    "refine_prompts": { "chapter_refine": {...} },
    "tracker_prompts": { "character_tracker": {...}, ... }
  }
}
```

### CLI配置命令

```bash
# 查看当前配置
python soundnovel.py cli settings

# 交互式配置
python soundnovel.py cli settings --interactive

# 查看完整配置文件
python soundnovel.py cli settings --show-file

# 配置生成流程参数
python soundnovel.py cli settings --max-iterations 5 --pass-score 75

# 配置角色模型
python soundnovel.py cli settings --role generator --provider deepseek --model deepseek-chat

# 配置角色参数
python soundnovel.py cli settings --role reviewer --temperature 0.4 --max-tokens 6000

# 导出/导入配置
python soundnovel.py cli settings --export my_config.json
python soundnovel.py cli settings --import-config my_config.json

# 重置为默认
python soundnovel.py cli settings --reset
```

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
├── novel_generator/             # 核心包
│   ├── agent/                 # Agent 对话模式
│   ├── cli/                   # CLI 命令模块
│   ├── core/                  # 核心业务逻辑
│   ├── config/                # 配置（数据类）
│   ├── utils/                 # 工具（API 客户端、日志、文件处理）
│   └── templates/             # 模板文件
├── soundnovel.py              # 统一入口
├── build_exe.py               # 打包脚本
├── pyproject.toml             # 依赖
└── uv.lock                    # 依赖锁定文件
```

---

## 快速参考：添加新功能

1. **新 API 模型**: 添加到 `novel_generator/utils/multi_model_client.py`
2. **新配置选项**: 添加到 `novel_generator/config/settings.py` 数据类
3. **新 CLI 命令**: 添加到 `novel_generator/cli/commands/` 目录
4. **新提示词模板**: 在 `05_script/generation_config.json` 的 `prompts` 部分添加
5. **修改生成Prompt**: 编辑 `chapter_expander.py` 的 `_build_generation_prompt()` 方法
6. **修改评审Prompt**: 编辑 `chapter_expander.py` 的 `_review_chapter()` 方法
7. **修改润色Prompt**: 编辑 `chapter_expander.py` 的 `_refine_chapter()` 方法
8. **修改Tracker上下文**: 编辑对应tracker的 `get_context_for_chapter()` 方法

## Prompt修改速查表

| 要修改的内容 | YAML文件 | 说明 |
|-------------|----------|------|
| 系统提示词(角色定义) | `04_prompt/system_prompts.yaml` | 三个角色的核心职责和行为准则 |
| 章节生成Prompt | `04_prompt/generation_prompts.yaml` | 章节扩写模板，包含写作法则 |
| 章节评审Prompt | `04_prompt/review_prompts.yaml` | 评审维度和评分标准 |
| 章节润色Prompt | `04_prompt/refine_prompts.yaml` | 润色规则和要求 |
| 状态卡Prompt | `04_prompt/state_card_prompt.yaml` | 章节结尾状态提取 |

### Prompt文件结构

```
04_prompt/
├── prompts/                      # 静态prompt配置（可编辑）
│   ├── system_prompts.yaml       # 角色定义（Generator/Reviewer/Refiner）
│   ├── generation_prompts.yaml   # 生成模板 + 禁忌词 + 负面示例
│   ├── review_prompts.yaml       # 评审维度和评分标准
│   ├── refine_prompts.yaml       # 润色规则
│   ├── state_card_prompt.yaml    # 状态卡模板
│   └── style_guide.yaml          # 风格指南
└── tracking/                     # 动态生成的追踪数据（自动更新）
    ├── character_tracking.yaml   # 人物状态追踪
    ├── foreshadowing_tracking.yaml # 伏笔追踪
    └── emotional_arc_tracking.yaml # 情感弧线
```

### 文件用途

| 文件 | 用途 | 是否需要编辑 |
|------|------|-------------|
| `prompts/system_prompts.yaml` | 定义三个AI角色的行为准则 | 可选 |
| `prompts/generation_prompts.yaml` | 章节生成模板、禁忌词、负面示例 | 推荐 |
| `prompts/review_prompts.yaml` | 评审维度和通过标准 | 可选 |
| `prompts/refine_prompts.yaml` | 润色规则 | 可选 |
| `prompts/style_guide.yaml` | 写作风格设置 | 推荐 |
| `tracking/*` | 自动生成，无需手动编辑 | 否 |

### 代码位置映射

| YAML配置 | 代码加载位置 | 使用方法 |
|----------|-------------|----------|
| system_prompts.yaml | `prompt_manager.get_system_prompt(role)` | AI角色初始化 |
| generation_prompts.yaml | `prompt_manager.build_generation_prompt(...)` | `_build_generation_prompt()` |
| review_prompts.yaml | `prompt_manager.build_review_prompt(...)` | `_review_chapter()` |
| refine_prompts.yaml | `prompt_manager.build_refine_prompt(...)` | `_refine_chapter()` |
| state_card_prompt.yaml | `prompt_manager.build_state_card_prompt(...)` | `_generate_state_card()` |

### 解决剧情重复问题

**问题原因**: AI不知道前文已经发生过什么，导致重复生成相同内容。

**解决方案**:
1. 状态卡机制：每章结尾生成状态卡，记录人物、位置、未完成事件
2. 生成Prompt中强调：添加"前文剧情已发生，不可重复"的警告
3. 评审维度增加：剧情一致性维度占30%权重，检查是否重复

如有疑问，请遵循代码库中的现有模式。
