# 小说创作AI Agent - 使用指南

## 📖 项目简介

小说创作AI Agent是一个基于智谱AI大语言模型的自动化小说创作辅助工具。它采用"大纲锚定+滑动窗口扩写+人工校验"的工作流程，帮助用户从原始素材生成完整的签约级小说内容。

### 🎯 核心特性

- **智能大纲生成**：基于核心设定自动生成章节大纲
- **滑动窗口扩写**：确保故事连贯性和人物一致性
- **多阶段创作流程**：从设定到草稿的完整创作链路
- **灵活的配置系统**：支持多种模型和参数调整
- **完善的日志记录**：追踪创作过程和API调用记录

## 🏗️ 项目结构

```
SoundNovel/
├── novel_generator/           # 核心代码模块
│   ├── core/                  # 核心功能模块
│   │   ├── chapter_expander.py # 章节扩写器
│   │   ├── outline_generator.py # 大纲生成器
│   │   ├── batch_outline_generator.py # 批量大纲生成器
│   │   ├── project_manager.py  # 项目管理器
│   │   └── sliding_window.py   # 滑动窗口模块
│   ├── config/                # 配置管理
│   │   └── settings.py        # 设置管理器
│   └── utils/                 # 工具模块
│       ├── api_client.py      # API客户端
│       ├── file_handler.py    # 文件处理器
│       └── logger.py          # 日志管理器
├── 01_source/                 # 原始素材区
│   ├── core_setting.yaml      # 核心设定文件
│   └── overall_outline.yaml   # 整体大纲文件
├── 02_outline/                # 大纲细化区
│   ├── chapter_outline_01-150.yaml # 章节大纲文件
│   └── outline_history/       # 大纲历史版本
├── 03_draft/                  # 小说草稿区
│   ├── chapter_01.md         # 章节草稿文件
│   ├── chapter_02.md         # 章节草稿文件
│   └── draft_history/        # 草稿历史版本
├── 04_prompt/                 # Prompt模板库
│   ├── chapter_expand_prompt.yaml # 扩写提示词模板
│   └── style_guide.yaml      # 风格指导文件
├── 05_script/                 # 工具脚本区
│   ├── main.py               # 主程序
│   ├── expand_chapters.py    # 章节扩写脚本
│   └── config.json           # 配置文件
├── 06_log/                    # 日志区
│   ├── ai_api_logs/          # API调用日志
│   └── system_logs/         # 系统日志
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

### 3. 配置API密钥

编辑 `05_script/config.json` 文件，添加您的智谱AI API密钥：

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
    "context_chapters": 5,
    "default_word_count": 1500,
    "copyright_bypass": true,
    "world_style": ""
  }
}
```

### 4. 填写核心设定

编辑 `01_source/core_setting.yaml` 文件，填写您的小说核心设定：

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
3. 使用批量大纲生成器分批生成详细章节大纲（每批30章）
4. 保存到 `02_outline/chapter_outline_01-{总章节数}.yaml`
5. 输出生成结果供您审核

### 批量大纲生成器特性

- **自动章节数量检测**：从整体大纲中自动提取总章节数量
- **分批处理**：大量章节自动分批生成，避免单次处理过多内容
- **智能幕名称识别**：支持数字格式（第1幕、第2幕）和中文格式（第一幕、第二幕）
- **错误恢复**：生成失败时自动使用模拟数据作为备用方案

### 阶段二：审核和优化大纲

查看生成的章节大纲文件，根据需要进行优化：

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

## 主要功能特性

### 1. 批量大纲生成器

新增批量大纲生成器，支持大规模小说创作：

- **自动章节数量提取**：从整体大纲中智能提取总章节数量
- **分批处理机制**：大量章节自动分批生成，避免单次处理过多内容
- **灵活的幕名称支持**：支持数字格式（第1幕、第2幕）和中文格式（第一幕、第二幕）
- **错误恢复机制**：生成失败时自动使用模拟数据作为备用方案

### 2. 滑动窗口技术

系统采用滑动窗口技术确保故事连贯性：

- **上下文管理**：自动提取前序章节的关键信息
- **人物状态追踪**：保持人物性格和行为的连续性
- **伏笔回收**：智能识别和回收前期埋下的伏笔
- **场景连贯性**：确保场景转换自然流畅

### 3. 多模型支持

支持多种智谱AI模型：

- **GLM-4-Long**：用于逻辑分析和复杂推理
- **GLM-4.5-Flash**：用于快速内容生成
- **自定义模型**：可根据需要配置不同模型

### 4. 智能提示词系统

内置智能提示词生成系统：

- **动态模板**：根据章节内容自动调整提示词
- **风格适配**：支持多种写作风格和语言特点
- **上下文融合**：将核心设定、风格指导等融入提示词

## ⚙️ 配置说明

### 主要配置参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `context_chapters` | 滑动窗口包含的前序章节数 | 5 |
| `default_word_count` | 章节默认字数目标 | 1500 |
| `expansion_model` | 章节扩写使用的模型 | "glm-4.5-flash" |
| `temperature` | AI生成温度参数 | 0.7 |
| `max_tokens` | 最大生成token数 | 4000 |
| `batch_size` | 批量大纲生成每批章节数 | 30 |

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
    "context_chapters": 5,
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
- 智能分批处理（默认每批30章）
- 支持自定义批次大小
- 错误恢复机制

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
- 合理设置批量处理批次大小（默认30章）
- 大规模项目建议分批次生成大纲
- 定期检查生成质量和连贯性
- 利用历史版本管理跟踪生成进度

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
