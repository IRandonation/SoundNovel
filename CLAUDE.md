# CLAUDE.md

本文档为 Claude Code (claude.ai/code) 提供在本代码库中工作的指导。

## 项目简介

SoundNovel 是一个基于 Python 的 AI 辅助小说创作工具，采用两阶段流水线（大纲生成 → 上下文注入章节扩写）帮助作者创作长篇虚构作品。支持命令行（CLI）和 Agent 对话模式。

流水线详见: `docs/generation-pipeline.md`

## 规则
所有的python运行都使用uv环境来进行

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
# CLI 模式 - 初始化项目
uv run soundnovel.py cli init

# CLI 模式 - 生成章节大纲
uv run soundnovel.py cli outline

# CLI 模式 - 扩写单个章节
uv run soundnovel.py cli expand --chapter 1

# CLI 模式 - 扩写章节范围
uv run soundnovel.py cli expand --start 1 --end 10

# CLI 模式 - 从上次保存的章节继续
uv run soundnovel.py cli continue

# CLI 模式 - 级联重生成所有dirty章节
uv run soundnovel.py cli continue --cascade

# CLI 模式 - 查看项目状态（含章节clean/dirty状态）
uv run soundnovel.py cli status

# CLI 模式 - 配置 AI 角色和设置
uv run soundnovel.py cli settings --interactive

# CLI 模式 - 标记章节修改类型
uv run soundnovel.py cli touch --chapter 15 --type content

# CLI 模式 - 重生成指定章节
uv run soundnovel.py cli regenerate --chapters 12-14
```

## 架构概述

### 目录结构

```
SoundNovel/
├── source/                 # 用户小说源材料
│   ├── core_setting.yaml   # 世界观、人物、伏笔设定
│   └── overall_outline.yaml # 高层故事结构（幕、转折点）
├── output/                 # 生成输出
│   ├── outline/            # 章节大纲
│   ├── draft/              # 章节草稿
│   └── log/                # 生成日志
├── prompts/                # 提示词模板和风格指南
├── config/                 # 配置文件
│   ├── session.json        # 会话状态、API 密钥、进度、章节状态
│   └── generation_config.json # AI 角色、提示词、质量阈值
├── novel_generator/        # 主 Python 包
│   ├── agent/              # Agent 对话模式
│   ├── cli/                # CLI 命令
│   ├── config/             # 配置管理
│   ├── core/               # 核心逻辑（章节扩写、大纲生成）
│   ├── templates/          # Jinja2 模板
│   └── utils/              # 工具（文件处理、日志、模型客户端）
└── soundnovel.py           # 统一入口（CLI 分发器）
```

### 核心工作流

**两阶段流水线**：

1. **大纲生成**（`OutlineGenerator.generate_outline_v2()`）：两阶段
   - Stage 1: 幕级规划（注入网文节奏设计原则，自然融入爽点/爆点）
   - Stage 2: 章级骨架（含章节定位/因果链/场景概览/情绪曲线/伏笔处理/结尾卡点）
   - 产物：`skeletons.json`（即最终大纲，直接驱动扩写，不经过场景级细化）

2. **章节扩写**（`ChapterExpander.expand_chapter()`）：章节级一次生成
   - 上下文：30 章大纲 + 10 章已生成正文全文（滑动窗口）
   - 不拆场景、不拼装、无 Tracker、无状态卡
   - 每章一次 API 调用，AI 自然处理场景间过渡与节奏

### 关键类

- **`OutlineGenerator`**（`core/outline_generator.py`）：两阶段大纲生成，含幕规划/章骨架（骨架直接驱动扩写）
- **`ChapterExpander`**（`core/chapter_expander.py`）：章节扩写，一次调用生成完整章节正文
- **`ConfigManager`**（`config/config_manager.py`）：会话配置和生成配置的统一接口
- **`MultiModelClient`**（`utils/multi_model_client.py`）：豆包和 DeepSeek API 调用的抽象层
- **`PromptManager`**（`utils/prompt_manager.py`）：提示词模板管理和渲染

### 配置系统

配置统一管理：

1. **`config/session.json`**：会话状态、API 密钥、进度追踪、章节状态
2. **`config/generation_config.json`**：AI 角色、提示词、质量阈值、服务商设置

AI 角色可以在 `generation_config.json` 的 `roles` 键下按服务商/模型/温度独立配置。

### 上下文注入

章节扩写时，prompt 由三部分组成：

- **前 30 章大纲上下文**：骨架级摘要（标题/核心事件/场景概览/因果链/伏笔/情绪曲线/结尾卡点），保证宏观连续性和伏笔贯通
- **前 10 章正文全文**：原文注入不做摘要，保证文风、语气、细节的连贯；用户修改过的文本会自动影响后续生成
- **当前章完整骨架**：章节定位/核心事件/与前章因果/场景概览/角色行动/伏笔处理/情绪曲线/结尾卡点/爽点节奏指引

上下文窗口参数：`outline_window`（默认 30）、`draft_window`（默认 10）。

### 章节状态系统

每章维护三种状态：
- **clean**：正文与大纲一致
- **dirty**：正文需要重生成（因前文内容变更导致上下文变化）
- **cosmetic**：仅润色修改，不触发级联

`touch` 命令标记修改类型，`content` 类型触发脏传播（N+1 到 N+draft_window 标记为 dirty）。

### 入口点

- **CLI**：`soundnovel.py cli <command>` → `novel_generator/cli/main.py` → `novel_generator/cli/commands/` 中的命令处理器
- **Agent**：`soundnovel.py cli agent` → `novel_generator/agent/cli_repl.py` → Agent REPL 交互

### CLI 命令一览

| 命令 | 说明 |
|------|------|
| `init` | 初始化项目 |
| `outline` | 生成章节大纲 |
| `expand` | 扩写章节内容 |
| `continue` | 续写章节（支持 --cascade, --dry-run） |
| `status` | 查看项目状态和章节 clean/dirty 状态 |
| `settings` | 配置 AI 角色和生成参数 |
| `touch` | 标记章节修改类型（cosmetic/content） |
| `regenerate` | 重生成指定章节 |

### 测试

测试使用 pytest，固件位于 `tests/conftest.py`。关键模式：
- 模型相关测试中模拟外部 API 调用
- 文件操作使用临时目录
- 测试 CLI 和配置管理逻辑

## 重要实现说明

- API 密钥存储于 `config/session.json`（已加入 gitignore）
- 章节文件命名为 `第0001章.txt`（4位零填充）
- 大纲窗口：`outline_window`（默认 30，扩写时向前看过往大纲章数）
- 正文窗口：`draft_window`（默认 10，扩写时向前看过往已生成正文章数）
- 用户修改任意章节正文后，重新生成后续章节时上下文自动感知修改
- PyInstaller 冻结模式下运行时，路径相对于 `sys.executable` 解析

## 开发规范

### Git 提交

- 所有 commit message **不要**包含 `Co-Authored-By` 行
