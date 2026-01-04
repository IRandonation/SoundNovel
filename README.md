# 小说创作 AI Agent (SoundNovel)

一个基于多模型大语言模型的长篇小说创作助手，采用“核心设定 + 大纲锚定 + 滑动窗口扩写 + 日志与版本管理”的完整流水线，帮助你从素材到成书。

详细架构设计请参阅 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 主要特性

- **智能章节大纲生成**：从整体大纲自动拆分并批量生成详细章节大纲
- **滑动窗口扩写**：利用上下文窗口保持剧情连贯、人物一致
- **多模型支持**：内置智谱、豆包、Ark 多模型切换与容错
- **完整工程化**：目录模板、配置校验、日志记录、历史版本备份
- **批量处理能力**：适配长篇创作需求（几十到上百章）

## 目录结构

```
SoundNovel/
├── 01_source/                 # 核心素材与设定 (core_setting.yaml, overall_outline.yaml)
├── 02_outline/                # [生成] 章节大纲
├── 03_draft/                  # [生成] 章节草稿
├── 04_prompt/                 # 提示词模板与风格指南
├── 05_script/                 # 脚本入口 (main.py, expand_chapters.py, merge_drafts.py)
├── 06_log/                    # [生成] 日志目录
├── 07_output/                 # [生成] 最终合并的成品
├── novel_generator/           # 核心代码包
├── gui_app.py                 # GUI 启动入口
├── pyproject.toml             # 依赖声明
└── uv.lock                    # 依赖锁
```

## 安装与环境

推荐使用 `uv` 进行依赖管理和运行。

1. **安装 uv**:
   ```bash
   pip install uv
   ```

2. **同步依赖**:
   ```bash
   uv sync
   ```

## 快速开始

### 1. 初始化项目

```bash
uv run python 05_script/main.py --init
```
此命令会生成配置文件 `05_script/config.json` 和必要的示例文件。

### 2. 配置 API

编辑 `05_script/config.json`，填入你的 API Key（支持智谱、豆包等）。

### 3. 填写设定

修改 `01_source/core_setting.yaml` 和 `01_source/overall_outline.yaml`，填入你的小说设定和大纲。

### 4. 运行生成

**命令行方式**:
```bash
# 生成章节大纲
uv run python 05_script/main.py

# 扩写章节 (例如第 1 章)
uv run python 05_script/expand_chapters.py --chapter 1

# 合并草稿
uv run python 05_script/merge_drafts.py
```

**GUI 方式**:
```bash
uv run streamlit run gui_app.py
```

## 隐私与安全

- 所有 API Key 存储在 `05_script/config.json` 中。
- `05_script/config.json` 已被加入 `.gitignore`，**请勿将其提交到版本控制系统**。
- 生成的内容（`02_outline`, `03_draft`, `07_output`）默认不提交，如需保存请手动管理。

## 许可证

MIT License
