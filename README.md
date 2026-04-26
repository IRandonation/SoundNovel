# 小说创作 AI Agent (SoundNovel)

一个基于多模型大语言模型的长篇小说创作助手，采用"核心设定 + 大纲锚定 + 三角色协作"的完整流水线，帮助你从素材到成书。

## 主要特性

- **三角色协作流程**：生成者→评审者→润色者，迭代优化确保质量
- **智能章节大纲生成**：从整体大纲自动拆分并批量生成详细章节大纲
- **上下文追踪系统**：人物状态、伏笔、情感弧线自动追踪
- **多模型支持**：豆包、DeepSeek多模型可独立配置
- **可配置Prompt系统**：所有prompt模板均可通过JSON配置文件管理
- **会话状态管理**：自动记录进度，支持断点续写
- **Agent 对话模式**：自然语言交互，更智能的创作体验

## 三角色协作流程

```
Generator生成 → Refiner首次润色(必做) → Reviewer评审 → [通过?]
                                                          ↓ 否
                                                    Refiner问题修复 → 再评审 → [通过?]
                                                                                ↓ 否
                                                                          循环(最多N次)
```

| 角色 | 职责 | 推荐配置 |
|------|------|----------|
| **Generator** | 章节生成、大纲创建 | temperature=0.7，注重创意 |
| **Refiner** | 首次润色（硬性规则检查）、问题修复 | temperature=0.5，平衡质量 |
| **Reviewer** | 质量评审、一致性检查 | temperature=0.3，注重精确 |

## Prompt系统

所有Prompt配置位于 `05_script/generation_config.json`:

```json
{
  "prompts": {
    "system_prompts": { "generator": "...", "reviewer": "...", "refiner": "..." },
    "generation_prompts": { "chapter_generation": {...} },
    "review_prompts": { "chapter_review": {...} },
    "refine_prompts": { "chapter_refine": {...} },
    "tracker_prompts": { "character_tracker": {...}, "foreshadowing_tracker": {...}, ... }
  }
}
```

### 上下文追踪注入

生成章节时自动注入三种追踪上下文：
- **人物追踪**: 位置、状态、目标、关系
- **伏笔追踪**: 待回收伏笔、超期提醒
- **情感弧线**: 近3章情感走向、节奏建议

## 目录结构

```
SoundNovel/
├── 01_source/                 # 核心素材与设定
├── 02_outline/                # [生成] 章节大纲
├── 03_draft/                  # [生成] 章节草稿
├── 04_prompt/                 # 提示词模板与风格指南
├── 05_script/                 # 配置文件
│   ├── generation_config.json # 生成配置(含所有prompt模板)
│   └── session.json           # 会话状态和API密钥
├── 06_log/                    # [生成] 日志目录
├── docs/                      # 项目文档
├── novel_generator/             # 核心代码包
│   ├── agent/                 # Agent 对话模式
│   ├── cli/                   # CLI 命令模块
│   ├── config/                # 配置与会话管理
│   ├── core/                  # 核心逻辑
│   ├── utils/                 # 通用工具
│   └── templates/             # 模板文件
├── soundnovel.py              # 统一入口
├── build_exe.py               # 打包脚本
└── pyproject.toml           # 依赖声明
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

本项目提供 **CLI 命令行** 和 **Agent 对话模式** 两种使用方式。

### 方式一：CLI 命令行（推荐）

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

# 查看项目状态
python soundnovel.py cli status

# 生成章节大纲
python soundnovel.py cli outline

# 扩写单个章节
python soundnovel.py cli expand --chapter 1

# 扩写章节范围
python soundnovel.py cli expand --start 1 --end 10

# 从上次结束处续写
python soundnovel.py cli continue

# 配置AI角色和生成参数
python soundnovel.py cli settings              # 查看当前配置
python soundnovel.py cli settings --interactive  # 交互式配置
python soundnovel.py cli settings --show-file    # 查看完整配置文件

# 配置生成参数
python soundnovel.py cli settings --max-iterations 5 --pass-score 75

# 配置角色模型
python soundnovel.py cli settings --role generator --provider deepseek --model deepseek-chat

# 启动 Agent 对话模式
python soundnovel.py cli agent

# 查看帮助
python soundnovel.py --help
python soundnovel.py cli --help
```

#### Agent 对话模式

```bash
# 启动对话模式
python soundnovel.py cli agent

# 交互示例
> 生成第5章
> 查看状态
> 张三现在在哪
> 帮助
> 退出
```

### 快速开始

#### 1. 初始化项目

```bash
python soundnovel.py cli init
```

初始化时会引导你配置 API 密钥。

#### 2. 填写小说设定

编辑 `01_source/core_setting.yaml` 和 `01_source/overall_outline.yaml`。

#### 3. 生成大纲和章节

```bash
# 生成章节大纲
python soundnovel.py cli outline

# 扩写章节
python soundnovel.py cli expand --chapter 1

# 查看进度
python soundnovel.py cli status

# 续写（从上次结束处继续）
python soundnovel.py cli continue
```

## 构建可执行文件

打包成 `.exe` 分享给其他人：

```bash
# 构建 CLI 版本
python build_exe.py

# 清理构建文件
python build_exe.py --clean
```

输出：
- `dist/SoundNovelAI_CLI.zip` - CLI 版本

## 隐私与安全

- API Key 存储在 `05_script/session.json` 中
- `session.json` 已被加入 `.gitignore`
- 生成的内容默认不提交到版本控制

## 许可证

MIT License
