# 小说创作AI Agent - 使用指南

## 📖 项目简介

小说创作AI Agent是一个基于多种AI大语言模型的自动化小说创作辅助工具。它采用"大纲锚定+滑动窗口扩写+人工校验"的工作流程，帮助用户从原始素材生成完整的签约级小说内容。

**支持的AI模型：**
- 智谱AI
- 豆包

**核心优势：**
- 智能大纲生成和批量处理
- 滑动窗口技术确保故事连贯性
- 多模型支持，可根据任务需求灵活选择
- 完善的版本管理和日志系统

### 🎯 核心特性

- **智能大纲生成**：基于核心设定自动生成章节大纲
- **滑动窗口扩写**：确保故事连贯性和人物一致性
- **多阶段创作流程**：从设定到草稿的完整创作链路
- **多模型AI支持**：支持智谱AI、豆包、Ark等多种AI模型
- **灵活的配置系统**：支持多种模型和参数调整
- **完善的日志记录**：追踪创作过程和API调用记录
- **批量处理能力**：支持大规模章节的批量生成和扩写

## 🏗️ 项目结构

### 核心模块说明

**novel_generator/** 是项目的核心代码模块，包含以下主要组件：

- **core/**: 核心功能模块
  - [`chapter_expander.py`](novel_generator/core/chapter_expander.py:1) - 章节扩写器，实现基于滑动窗口的章节内容生成
  - [`outline_generator.py`](novel_generator/core/outline_generator.py:1) - 大纲生成器，负责章节大纲的生成
  - [`batch_outline_generator.py`](novel_generator/core/batch_outline_generator.py:1) - 批量大纲生成器，支持大规模章节处理
  - [`project_manager.py`](novel_generator/core/project_manager.py:1) - 项目管理器，负责项目初始化和结构管理
  - [`sliding_window.py`](novel_generator/core/sliding_window.py:1) - 滑动窗口模块，确保故事连贯性

- **config/**: 配置管理
  - [`settings.py`](novel_generator/config/settings.py:1) - 设置管理器，处理所有配置相关的逻辑

- **utils/**: 工具模块
  - [`api_client.py`](novel_generator/utils/api_client.py:1) - API客户端，处理与AI模型的通信
  - [`file_handler.py`](novel_generator/utils/file_handler.py:1) - 文件处理器，负责文件读写操作
  - [`logger.py`](novel_generator/utils/logger.py:1) - 日志管理器，记录系统运行状态
  - [`multi_model_client.py`](novel_generator/utils/multi_model_client.py:1) - 多模型客户端，支持多种AI模型的切换和管理

### 目录结构

```
SoundNovel/
├── novel_generator/           # 核心代码模块
│   ├── core/                  # 核心功能模块
│   │   ├── chapter_expander.py    # 章节扩写器
│   │   ├── outline_generator.py   # 大纲生成器
│   │   ├── batch_outline_generator.py # 批量大纲生成器
│   │   ├── project_manager.py     # 项目管理器
│   │   └── sliding_window.py      # 滑动窗口模块
│   ├── config/                # 配置管理
│   │   └── settings.py        # 设置管理器
│   ├── templates/              # 模板文件
│   └── utils/                 # 工具模块
│       ├── api_client.py      # API客户端
│       ├── file_handler.py    # 文件处理器
│       ├── logger.py          # 日志管理器
│       └── multi_model_client.py # 多模型客户端
├── 01_source/                 # 原始素材区
│   ├── core_setting.yaml      # 核心设定文件
│   └── overall_outline.yaml   # 整体大纲文件
├── 02_outline/                # 大纲细化区
│   ├── chapter_outline_01-58.yaml # 章节大纲文件
│   └── outline_history/       # 大纲历史版本
├── 03_draft/                  # 小说草稿区
│   ├── chapter_01.md         # 章节草稿文件
│   ├── chapter_02.md         # 章节草稿文件
│   ├── draft_history/        # 草稿历史版本
│   └── merge_drafts.py       # 草稿合并脚本
├── 04_prompt/                 # Prompt模板库
│   ├── chapter_expand_prompt.yaml # 扩写提示词模板
│   └── style_guide.yaml      # 风格指导文件
├── 05_script/                 # 工具脚本区
│   ├── main.py               # 主程序
│   ├── expand_chapters.py    # 章节扩写脚本
│   └── merge_drafts.py       # 草稿合并脚本
├── 06_log/                    # 日志区
│   ├── ai_api_logs/          # API调用日志
│   └── system_logs/         # 系统日志
├── 07_output/                 # 最终输出区
├── source/                    # 源文件区
│   └── 越女剑.txt           # 示例源文件
└── README.md                 # 项目说明文档
```

## 🚀 快速开始

### 1. 环境准备

确保您的系统已安装以下依赖：

```bash
# 安装Python依赖
pip install -r pyproject.toml

# 或手动安装主要依赖
pip install pyyaml>=6.0.2 flask>=3.1.1 zhipuai>=2.1.5.20250801
```

### 2. 项目初始化

```bash
# 进入项目目录
cd d:\Project\SoundNovel

# 初始化项目
python 05_script/main.py --init
```

初始化过程会：
- 创建必要的目录结构
- 生成默认配置文件 `05_script/config.json`
- 创建核心设定和整体大纲的模板文件
- 设置日志系统

### 3. 配置API密钥

编辑 `05_script/config.json` 文件，配置您的AI API密钥。系统支持多种AI模型：

```json
{
  "api_key": "您的智谱AI API密钥",
  "api_base_url": "https://open.bigmodel.cn/api/paas/v4",
  "models": {
    "logic_analysis_model": "glm-4-long",
    "major_chapters_model": "glm-4-long",
    "sub_chapters_model": "glm-4-long",
    "expansion_model": "glm-4.5-flash",
    "default_model": "glm-4.5-flash"
  },
  "doubao_api_key": "您的豆包API密钥（可选）",
  "doubao_api_base_url": "https://ark.cn-beijing.volces.com/api/v3",
  "default_model": "zhipu",
  "available_models": ["zhipu", "doubao"],
  "max_tokens": 4000,
  "temperature": 0.7,
  "top_p": 0.7,
  "system": {
    "api": {
      "max_retries": 5,
      "retry_delay": 2,
      "timeout": 60
    },
    "logging": {
      "level": "INFO",
      "file": "06_log/novel_generator.log"
    }
  },
  "paths": {
    "core_setting": "01_source/core_setting.yaml",
    "outline_dir": "02_outline/",
    "draft_dir": "03_draft/",
    "prompt_dir": "04_prompt/",
    "log_dir": "06_log/"
  },
  "novel_generation": {
    "stage1_use_long_model": true,
    "stage2_use_long_model": true,
    "stage3_use_regular_model": true,
    "stage4_use_regular_model": true,
    "stage5_use_regular_model": true,
    "context_chapters": 10,
    "default_word_count": 1500,
    "copyright_bypass": true,
    "world_style": ""
  }
}
```

**多模型支持说明：**
- **智谱AI**：默认使用，支持GLM-4-Long（复杂推理）和GLM-4.5-Flash（快速生成）
- **豆包**：可选配置，支持ep-20241210233657-lz8fv模型

### 4. 填写核心设定

编辑 `01_source/core_setting.yaml` 文件，填写您的小说核心设定：

*例子*：
```yaml
世界观: "这是一个灵气充沛的修仙世界..."
核心冲突: "主线矛盾围绕凛风与曦羽之间的情感纠葛..."
人物小传:
  主角: 
    姓名: "凛风"
    身份: "散修"
    性格: "自信，看重名声"
    核心动机: "提升在修仙界的名声"
  配角1: 
    姓名: "曦羽"
    身份: "邻宗门修仙者"
    性格: "正义感，坚守原则"
    核心动机: "维护修仙界正义"
伏笔清单:
  - 伏笔1: "凛风的天赋极高"
  - 伏笔2: "木条法器的特殊作用"
  - 伏笔3: "心性变化的后果"
```

### 5. 制定整体大纲

编辑 `01_source/overall_outline.yaml` 文件，制定故事的整体框架：

*例子*：
```yaml
第一幕: "第1-5章，介绍凛风的身世背景..."
第二幕: "第6-15章，详细描述找灵犬过程中与曦羽的冲突..."
第三幕: "第16-20章，曦羽为报仇约凛风进行生死对决..."
关键转折点:
  - 第6章: "凛风为找灵犬与曦羽相遇并发生对决"
  - 第10章: "凛风与曦羽因心性暴躁爆发争吵"
  - 第16章: "曦羽与凛风打架决胜负"
```

## 📝 使用流程

### 阶段一：生成章节大纲

```bash
# 自动生成所有章节的详细大纲
python 05_script/main.py
```

程序会：
1. 读取您的核心设定和整体大纲
2. 自动从整体大纲中提取总章节数量
3. 使用批量大纲生成器分批生成详细章节大纲（每批15章）
4. 保存到 `02_outline/chapter_outline_01-{总章节数}.yaml`
5. 输出生成结果供您审核

### 批量大纲生成器特性

- **自动章节数量检测**：从整体大纲中自动提取总章节数量
- **分批处理**：大量章节自动分批生成，避免单次处理过多内容
- **智能幕名称识别**：支持数字格式（第1幕、第2幕）和中文格式（第一幕、第二幕）
- **错误恢复**：生成失败时自动使用模拟数据作为备用方案

### 阶段二：审核和优化大纲

查看生成的章节大纲文件，根据需要进行优化：

*例子*：
```yaml
第1章:
  标题: "开篇"
  核心事件: "凛风登场，接受找灵犬任务"
  场景: "修仙者聚集的酒楼"
  人物行动: "凛风接到曦羽的委托"
  伏笔回收: ""
  字数目标: 1500
```

### 阶段三：章节扩写

#### 方式一：交互式扩写

```bash
# 启动章节扩写器
python 05_script/expand_chapters.py
```

选择扩写模式：
1. **扩写单个章节** - 适合测试和调试
2. **批量扩写所有章节** - 适合完整创作
3. **批量扩写指定范围** - 适合分阶段创作

#### 方式二：命令行扩写

```bash
# 扩写单个章节
python 05_script/expand_chapters.py --chapter 1

# 批量扩写章节范围
python 05_script/expand_chapters.py --start 1 --end 5
```

### 阶段四：人工校验和修改

AI生成的章节草稿会保存在 `03_draft/` 目录下，格式为 Markdown：

```markdown
# 第1章 开篇

清晨的阳光洒进酒楼，凛风坐在靠窗的位置，悠闲地品着茶...

## 📁 目录说明

### 07_output/ - 最终输出区
用于存放最终生成的完整小说文件：
- **novel_final.md** - 最终完成的小说全文
- **novel_with_metadata.md** - 包含元数据的完整版本
- **exported_files/** - 导出的其他格式文件

### source/ - 源文件区
用于存放原始素材和参考文件：
- **xxx.txt** - 示例源文件，可作为参考或素材
- 可以添加其他参考文本、设定文档等

### merge_drafts.py - 草稿合并脚本
位于 `03_draft/merge_drafts.py` 和 `05_script/merge_drafts.py`，用于将生成的章节草稿合并为完整小说：

```bash
# 合并所有章节草稿
python 05_script/merge_drafts.py

# 合并指定范围的章节
python 05_script/merge_drafts.py --start 1 --end 10
```

合并功能：
- 自动按章节顺序合并Markdown文件
- 添加章节标题和分隔符
- 生成完整的小说文档
- 支持自定义输出格式

## ⚙️ 配置说明

### 主要配置参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `context_chapters` | 滑动窗口包含的前序章节数 | 10 |
| `default_word_count` | 章节默认字数目标 | 1500 |
| `expansion_model` | 章节扩写使用的模型 | "glm-4.5-flash" |
| `temperature` | AI生成温度参数 | 0.7 |
| `max_tokens` | 最大生成token数 | 4000 |
| `batch_size` | 批量大纲生成每批章节数 | 15 |

### API配置

```json
{
  "api_key": "您的智谱AI API密钥",
  "api_base_url": "https://open.bigmodel.cn/api/paas/v4",
  "models": {
    "logic_analysis_model": "glm-4-long",
    "major_chapters_model": "glm-4-long",
    "sub_chapters_model": "glm-4-long",
    "expansion_model": "glm-4.5-flash",
    "default_model": "glm-4.5-flash"
  },
  "max_tokens": 4000,
  "temperature": 0.7,
  "top_p": 0.7
}
```

### 系统配置

```json
{
  "system": {
    "api": {
      "max_retries": 5,
      "retry_delay": 2,
      "timeout": 60
    },
    "logging": {
      "level": "INFO",
      "file": "06_log/novel_generator.log"
    }
  }
}
```

### 生成配置

```json
{
  "novel_generation": {
    "stage1_use_long_model": true,
    "stage2_use_long_model": true,
    "stage3_use_regular_model": true,
    "stage4_use_regular_model": true,
    "stage5_use_regular_model": true,
    "context_chapters": 10,
    "default_word_count": 1500,
    "copyright_bypass": true,
    "world_style": ""
  }
}
```

### 风格指导配置

编辑 `04_prompt/style_guide.yaml` 来自定义写作风格：

```yaml
语言风格: "古风武侠"
对话特点: "符合人物身份，简洁有力"
场景描写: "侧重氛围营造和细节刻画"
禁忌: "禁止使用现代词汇，避免冗余心理描写"
```

## 🔧 高级功能

### 1. 批量大纲生成

使用批量大纲生成器处理大量章节：

```bash
# 使用主程序自动批量生成
python 05_script/main.py

# 或直接使用批量大纲生成器
python batch_outline_generator.py
```

批量生成特点：
- 自动检测总章节数量
- 智能分批处理（默认每批15章）
- 支持自定义批次大小
- 错误恢复机制

### 4. 草稿合并功能

使用merge_drafts.py脚本将生成的章节合并为完整小说：

```bash
# 合并所有章节草稿
python 05_script/merge_drafts.py

# 合并指定范围的章节
python 05_script/merge_drafts.py --start 1 --end 10

# 输出到指定目录
python 05_script/merge_drafts.py --output 07_output/
```

合并功能：
- 自动按章节顺序合并Markdown文件
- 添加章节标题和分隔符
- 生成完整的小说文档
- 支持自定义输出格式和目录

### 2. 日志查看

查看详细的操作日志：

```bash
# 查看系统日志
cat 06_log/system_logs/novel_generator.log

# 查看API调用日志
cat 06_log/ai_api_logs/
```

### 3. 历史版本管理

系统自动备份历史版本：

- 大纲历史：`02_outline/outline_history/`
- 草稿历史：`03_draft/draft_history/`

## 🐛 常见问题

### Q: API调用失败怎么办？
A: 检查以下几点：
1. 确认API密钥正确配置
2. 检查网络连接
3. 查看API调用日志获取详细错误信息

### Q: 生成的章节不符合预期？
A: 可以通过以下方式改进：
1. 优化核心设定和风格指导
2. 调整temperature等参数
3. 人工修改生成的章节大纲

### Q: 如何确保故事连贯性？
A: 系统使用滑动窗口技术：
1. 自动提取前序章节关键信息
2. 追踪人物状态和伏笔
3. 检测上下文断裂并自动修复

### Q: 如何批量处理大量章节？
A: 使用批量扩写功能：
```bash
python 05_script/expand_chapters.py --start 1 --end 20
```

## 📊 性能优化建议

### 1. 模型选择
- 复杂推理任务使用GLM-4-Long
- 快速生成使用GLM-4.5-Flash
- 根据任务复杂度选择合适模型

### 2. 参数调优
- 降低temperature获得更稳定输出
- 调整max_tokens控制输出长度
- 根据需要调整top_p参数

### 3. 批量处理优化
- 合理设置批量处理批次大小（默认15章）
- 大规模项目建议分批次生成大纲
- 定期检查生成质量和连贯性
- 利用历史版本管理跟踪生成进度

## ⚠️ 注意事项

### 使用建议
- **首次使用**：建议从小规模项目开始，熟悉工作流程后再处理大规模内容
- **模型选择**：复杂推理任务使用GLM-4-Long，快速生成使用GLM-4.5-Flash
- **参数调整**：根据生成质量调整temperature、max_tokens等参数
- **定期备份**：利用历史版本管理功能定期备份重要文件

### 性能优化
- **批量处理**：合理设置批次大小，避免单次处理过多内容
- **内存管理**：处理大量章节时注意内存使用情况
- **网络稳定**：确保网络连接稳定，避免API调用失败

### 内容质量
- **人工校验**：AI生成内容需要人工审核和修改
- **风格一致性**：通过style_guide.yaml保持写作风格一致
- **伏笔管理**：合理规划伏笔的埋设和回收

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进项目：

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 发起Pull Request

## 📄 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 📞 技术支持

如果您在使用过程中遇到问题，可以通过以下方式获取帮助：

1. 查看项目文档和FAQ
2. 提交GitHub Issue
3. 查看日志文件获取详细错误信息

---

**祝您创作愉快！🎉**
