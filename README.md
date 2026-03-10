# 小说创作 AI Agent (SoundNovel)

一个基于多模型大语言模型的长篇小说创作助手，采用"核心设定 + 大纲锚定 + 滑动窗口扩写 + 日志与版本管理"的完整流水线，帮助你从素材到成书。

## 主要特性

- **智能章节大纲生成**：从整体大纲自动拆分并批量生成详细章节大纲
- **滑动窗口扩写**：利用上下文窗口保持剧情连贯、人物一致
- **多模型支持**：内置智谱、豆包、Ark 多模型切换与容错
- **完整工程化**：目录模板、配置校验、日志记录、历史版本备份
- **批量处理能力**：适配长篇创作需求（几十到上百章）
- **双模式支持**：GUI 图形界面 + CLI 命令行，自由选择

## 目录结构

```
SoundNovel/
├── 01_source/                 # 核心素材与设定
├── 02_outline/                # [生成] 章节大纲
├── 03_draft/                  # [生成] 章节草稿
├── 04_prompt/                 # 提示词模板与风格指南
├── 05_script/                 # 配置文件
├── 06_log/                    # [生成] 日志目录
├── novel_generator/           # 核心代码包
│   ├── cli/                   # CLI 命令模块
│   ├── config/                # 配置管理
│   ├── core/                  # 核心逻辑
│   ├── utils/                 # 通用工具
│   └── templates/             # 模板文件
├── soundnovel.py              # 统一入口文件
├── gui_app.py                 # GUI 主程序
├── run_gui.py                 # GUI 启动器
├── build_exe.py               # 打包脚本
├── pyproject.toml             # 依赖声明
└── README.md                  # 本文件
```

## 安装与环境

推荐使用 `uv` 进行依赖管理：

```bash
# 安装 uv
pip install uv

# 同步依赖
uv sync
```

## 使用方式

本项目提供 **GUI 图形界面** 和 **CLI 命令行** 两种使用方式。

### 方式一：GUI 图形界面（推荐新手）

在浏览器中操作，可视化编辑设定、生成大纲、扩写章节。

```bash
# 方法 1：使用统一入口
python soundnovel.py gui

# 方法 2：直接使用 streamlit
uv run streamlit run gui_app.py
```

### 方式二：CLI 命令行（适合熟练用户）

在终端中操作，高效快捷。

```bash
# 使用统一入口
python soundnovel.py cli <command> [options]

# 或使用模块方式
uv run python -m novel_generator.cli <command> [options]
```

#### CLI 命令速查

```bash
# 初始化项目
python soundnovel.py cli init

# 生成章节大纲
python soundnovel.py cli outline

# 扩写单个章节
python soundnovel.py cli expand --chapter 1

# 扩写章节范围
python soundnovel.py cli expand --start 1 --end 10

# 查看帮助
python soundnovel.py --help
python soundnovel.py cli --help
```

### 快速开始

#### 1. 初始化项目

```bash
python soundnovel.py cli init
```

#### 2. 配置 API 密钥

编辑 `05_script/config.json`，填入你的 API Key。

#### 3. 填写小说设定

编辑 `01_source/core_setting.yaml` 和 `01_source/overall_outline.yaml`。

#### 4. 生成大纲和章节

```bash
# 生成章节大纲
python soundnovel.py cli outline

# 扩写章节
python soundnovel.py cli expand --chapter 1
```

## 构建可执行文件

打包成 `.exe` 分享给其他人：

```bash
# 构建 GUI 版本（默认）
python build_exe.py

# 构建 CLI 版本
python build_exe.py --cli

# 同时构建两者
python build_exe.py --both
```

输出：
- `dist/SoundNovelAI_GUI.zip` - GUI 版本
- `dist/SoundNovelAI_CLI.zip` - CLI 版本

## 隐私与安全

- API Key 存储在 `05_script/config.json` 中
- `05_script/config.json` 已被加入 `.gitignore`
- 生成的内容默认不提交到版本控制

## 许可证

MIT License
