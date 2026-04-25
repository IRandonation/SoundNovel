# CLAUDE.md

本文档为 Claude Code (claude.ai/code) 提供在本代码库中工作的指导。

## 项目简介

SoundNovel 是一个基于 Python 的 AI 辅助小说创作工具，采用多模型大语言模型工作流（生成者 → 润色者 → 评审者）帮助作者创作长篇虚构作品。支持命令行（CLI）和图形界面（GUI/Streamlit）两种模式。

## 常用命令

### 开发命令

```bash
# 安装依赖（使用 uv）
uv sync

# 运行代码检查
uv run ruff check .

# 运行类型检查
uv run mypy novel_generator/

# 运行所有测试（带覆盖率）
uv run pytest

# 运行单个测试文件
uv run pytest tests/config/test_config_manager.py -v

# 运行测试并生成覆盖率报告
uv run pytest --cov=novel_generator --cov-report=html
```

### 运行应用

```bash
# GUI 模式（Streamlit）
python soundnovel.py gui
# 或
uv run streamlit run gui_app.py

# CLI 模式 - 初始化项目
python soundnovel.py cli init

# CLI 模式 - 生成章节大纲
python soundnovel.py cli outline

# CLI 模式 - 扩写单个章节
python soundnovel.py cli expand --chapter 1

# CLI 模式 - 扩写章节范围
python soundnovel.py cli expand --start 1 --end 10

# CLI 模式 - 从上次保存的章节继续
python soundnovel.py cli continue

# CLI 模式 - 查看项目状态
python soundnovel.py cli status

# CLI 模式 - 配置 AI 角色和设置
python soundnovel.py cli settings --interactive
```

### 构建可执行文件

```bash
# 仅构建 GUI 版本
python build_exe.py

# 仅构建 CLI 版本
python build_exe.py --cli

# 同时构建两个版本
python build_exe.py --both

# 清理构建产物
python build_exe.py --clean
```

输出目录为 `dist/`：
- `dist/SoundNovelAI_GUI.zip` - 带 Streamlit 的 GUI 版本
- `dist/SoundNovelAI_CLI.zip` - CLI 版本

## 架构概述

### 目录结构

```
SoundNovel/
├── 01_source/              # 用户小说源材料
│   ├── core_setting.yaml   # 世界观、人物、伏笔设定
│   └── overall_outline.yaml # 高层故事结构（幕、转折点）
├── 02_outline/             # 生成的章节大纲（输出）
├── 03_draft/               # 生成的章节草稿（输出）
├── 04_prompt/              # 提示词模板和风格指南
├── 05_script/              # 配置文件
│   ├── session.json        # 会话状态、API 密钥、进度
│   ├── config.json         # 用户配置
│   └── generation_config.json # AI 角色、提示词、质量阈值
├── 06_log/                 # 生成日志（输出）
├── novel_generator/        # 主 Python 包
│   ├── cli/               # CLI 命令
│   ├── config/            # 配置管理
│   ├── core/              # 核心逻辑（章节扩写、追踪）
│   ├── gui/               # Streamlit GUI 标签页
│   ├── templates/         # Jinja2 模板
│   └── utils/             # 工具（文件处理、日志、模型客户端）
├── soundnovel.py          # 统一入口（CLI/GUI 分发器）
├── gui_app.py             # Streamlit GUI 入口
└── build_exe.py           # PyInstaller 构建脚本
```

### 核心工作流

**三角色流程**（定义于 `novel_generator/core/chapter_expander.py`）：

1. **生成者**（`AIRole.GENERATOR`）：根据大纲创建初始章节内容
2. **润色者**（`AIRole.REFINER`）：首次润色，硬性规则检查
3. **评审者**（`AIRole.REVIEWER`）：质量评估 → JSON 输出含评分

如果评审失败（评分 < 阈值），润色者修复问题，评审者重新评估（最多 `max_refine_iterations` 次）。

### 关键类

- **`ChapterExpander`**（`core/chapter_expander.py`）：三角色流程的主协调器
- **`AIRoleManager`**（`core/ai_roles.py`）：管理角色特定的模型配置和 API 调用
- **`ConfigManager`**（`config/config_manager.py`）：会话配置和生成配置的统一接口
- **`CharacterTracker`** / **`ForeshadowingTracker`** / **`EmotionalArcTracker`**（`core/`）：跨章节上下文追踪
- **`MultiModelClient`**（`utils/multi_model_client.py`）：豆包和 DeepSeek API 调用的抽象层

### 配置系统

`ConfigManager` 合并两个配置文件：

1. **`05_script/session.json`**：会话状态、API 密钥、进度追踪
2. **`05_script/generation_config.json`**：AI 角色、提示词、质量阈值、服务商设置

AI 角色可以在 `generation_config.json` 的 `roles` 键下按服务商/模型/温度独立配置。

### 上下文注入

生成章节时，系统自动注入追踪上下文：

- **人物上下文**：当前位置、状态、目标、关系
- **伏笔上下文**：未解决的伏笔、超期提醒
- **情感上下文**：近3章的情感弧线、节奏建议

### 入口点

- **CLI**：`soundnovel.py cli <command>` → `novel_generator/cli/main.py` → `novel_generator/cli/commands/` 中的命令处理器
- **GUI**：`soundnovel.py gui` → 子进程调用 `streamlit run gui_app.py` → `novel_generator/gui/tabs/` 中的标签页渲染器

### 测试

测试使用 pytest，固件位于 `tests/conftest.py`。关键模式：
- 模型相关测试中模拟外部 API 调用
- 文件操作使用临时目录
- 测试 CLI 和配置管理逻辑

## 重要实现说明

- API 密钥存储于 `05_script/session.json`（已加入 gitignore）
- 章节文件命名为 `第0001章.txt`（4位零填充）
- `max_refine_iterations` 和 `pass_score_threshold` 控制生成配置中的评审循环
- 生成的上下文窗口：`context_before_full`（默认 10）前文章节 + `context_after_full`（默认 5）后文章节
- PyInstaller 冻结模式下运行时，路径相对于 `sys.executable` 解析
