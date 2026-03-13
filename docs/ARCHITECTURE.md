# 架构与技术细节

## 概述

SoundNovel 是一个 AI 辅助小说写作助手，旨在自动化从核心设定到完整小说草稿的创作流程。它利用多个大语言模型（LLM）来确保长篇叙事中的逻辑一致性、情节推进和风格统一。

## 系统架构

系统采用模块化架构组织：

### 1. 核心包 (`novel_generator/`)

这是应用程序的核心，包含业务逻辑和核心功能。

- **`core/`**:
  - [project_manager.py](file:///d:/Project/SoundNovel/novel_generator/core/project_manager.py): 负责项目结构的初始化和验证。
  - [outline_generator.py](file:///d:/Project/SoundNovel/novel_generator/core/outline_generator.py): 处理从整体大纲和核心设定生成章节大纲的逻辑。
  - [batch_outline_generator.py](file:///d:/Project/SoundNovel/novel_generator/core/batch_outline_generator.py): 管理大纲的批量生成，处理分页和上下文。
  - [chapter_expander.py](file:///d:/Project/SoundNovel/novel_generator/core/chapter_expander.py): 负责将章节大纲扩展为完整正文，确保符合风格指南。
  - [sliding_window.py](file:///d:/Project/SoundNovel/novel_generator/core/sliding_window.py): 实现滑动窗口上下文机制，以维持章节间的连贯性。

- **`utils/`**:
  - [multi_model_client.py](file:///d:/Project/SoundNovel/novel_generator/utils/multi_model_client.py): 一个强大的客户端，用于与各种 LLM 提供商（智谱AI、豆包、Ark）进行交互。处理模型路由、重试和降级。
  - [file_handler.py](file:///d:/Project/SoundNovel/novel_generator/utils/file_handler.py): 用于安全文件读取、写入和备份管理的工具。
  - [logger.py](file:///d:/Project/SoundNovel/novel_generator/utils/logger.py): 集中化的日志配置。

- **`config/`**:
  - [settings.py](file:///d:/Project/SoundNovel/novel_generator/config/settings.py): 定义 API 密钥、路径和生成参数的配置架构（使用 dataclasses）。

### 2. 接口层

- **命令行界面 (CLI) ([main.py](file:///d:/Project/SoundNovel/05_script/main.py))**: 用于运行生成流水线（初始化、大纲、扩写）的命令行接口。
- **图形用户界面 (GUI) ([gui_app.py](file:///d:/Project/SoundNovel/gui_app.py))**: 基于 Streamlit 的图形界面，提供更直观的交互体验。
- **脚本 (`05_script/`)**:
  - [expand_chapters.py](file:///d:/Project/SoundNovel/05_script/expand_chapters.py): 用于扩写特定章节或范围的独立脚本。

### 3. 数据流

1.  **输入**: 用户提供 `01_source/core_setting.yaml`（世界观、人物）和 `01_source/overall_outline.yaml`（情节节奏）。
2.  **大纲生成**: 系统将整体大纲分解为章节级大纲（存储在 `02_outline/`）。
3.  **正文扩写**: 使用滑动窗口上下文（前 N 章的摘要），系统将每个章节大纲扩展为正文草稿（存储在 `03_draft/`）。

## 技术要点

### 滑动窗口上下文
为了解决长篇小说中的上下文限制问题，系统采用了滑动窗口方法。在生成第 N 章时，它会将第 N-k 到 N-1 章的摘要和关键事件输入模型。这确保了 AI 能够记住近期的历史，而不会超过 Token 限制。

### 多模型策略
系统支持为不同任务切换不同的模型：
- **逻辑/规划**: 使用“长文本”模型（如 GLM-4-Long）进行高层级的大纲规划和一致性检查。
- **正文创作**: 使用更快速、更具成本效益的模型（如 GLM-4.5-Flash）进行正文扩写。

### 错误处理与恢复
- **API 重试**: 内置针对 API 失败的指数退避机制。
- **状态保存**: 每章生成后都会保存进度。如果批量任务失败，可以从最后一个成功的章节恢复。
- **备份**: 每次覆盖操作都会触发自动备份到 `_history/` 文件夹。

## 目录结构说明

- **`01_source/`**: 人工编写的创作输入。
- **`02_outline/`**: AI 生成的结构化中间件。
- **`03_draft/`**: AI 生成的原始正文内容。
- **`04_prompt/`**: 提示词工程模板。
- **`05_script/`**: 运行脚本。
- **`06_log/`**: 观测与调试日志。

## 安全与隐私

- **敏感数据**: API 密钥存储在 `05_script/config.json` 中，该文件已被 git 忽略。
- **环境**: 支持 `.env` 文件和环境变量。
- **日志**: API 日志是分离的，以避免在系统日志中意外泄露内容。
