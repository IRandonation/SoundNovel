# 小说创作 AI Agent

一个基于多模型大语言模型的长篇小说创作助手，采用“核心设定 + 大纲锚定 + 滑动窗口扩写 + 日志与版本管理”的完整流水线，帮助你从素材到成书。

## 主要特性

- 智能章节大纲生成：从整体大纲自动拆分并批量生成详细章节大纲
- 滑动窗口扩写：利用上下文窗口保持剧情连贯、人物一致
- 多模型支持：内置智谱、豆包、Ark 多模型切换与容错
- 完整工程化：目录模板、配置校验、日志记录、历史版本备份
- 批量处理能力：适配长篇创作需求（几十到上百章）

## 目录结构

```
SoundNovel/
├── 01_source/                 # 核心素材与设定
│   ├── core_setting.yaml      # 核心设定（世界观/人物/冲突/伏笔）
│   └── overall_outline.yaml   # 整体大纲（按幕组织）
├── 02_outline/                # 章节大纲
│   └── chapter_outline_01-XX.yaml # 章节大纲（XX为总章节数）
├── 03_draft/                  # 章节草稿
│   └── chapter_01.txt         # 章节草稿
├── 04_prompt/                 # 提示词模板与风格指南
│   ├── chapter_expand_prompt.yaml
│   └── style_guide.yaml
├── 05_script/                 # 脚本入口
│   ├── main.py                # 项目初始化与大纲生成
│   ├── expand_chapters.py     # 章节扩写（单章/区间）
│   └── merge_drafts.py        # 合并草稿生成成书
├── 06_log/                    # 日志目录
│   ├── ai_api_logs/           # API 调用日志
│   └── system_logs/           # 系统运行日志
├── novel_generator/           # 核心代码
│   ├── core/                  # 大纲/扩写/项目管理/滑窗
│   ├── config/                # Settings 配置模型
│   └── utils/                 # API 客户端、日志、文件工具
├── pyproject.toml             # 依赖声明
└── uv.lock                    # 依赖锁（可选）
```

## 安装与环境

- Python 版本：`>=3.13.5`
- 操作系统：Windows（已验证），其他系统需自行适配

安装依赖（推荐方式二选一）：

- 方式 A（pip）
  - 在项目根目录执行：
    - 创建并激活虚拟环境（可选）：
      - `python -m venv .venv`
      - `.\.venv\Scripts\activate`
    - 升级 pip：`pip install -U pip`
    - 安装项目与依赖：`pip install .`

- 方式 B（uv，可复现实验环境）
  - 安装 uv：`pip install uv`
  - 在项目根目录执行同步：`uv sync`

提示：`pip install -r pyproject.toml`是无效命令，请使用以上两种方式之一。

## 快速开始

### 1. 初始化项目结构

在项目根目录执行：

```
python 05_script/main.py --init
```

该命令会：
- 创建标准目录结构
- 生成模板文件：`01_source/core_setting.yaml`、`01_source/overall_outline.yaml`
- 生成默认配置：`05_script/config.json`
- 准备日志目录

### 2. 配置 API 与生成参数

编辑 `05_script/config.json`，配置 API 与生成参数（以下为默认结构，按需调整）：

```
{
  "api_key": "你的智谱 API 密钥",
  "api_base_url": "https://open.bigmodel.cn/api/paas/v4",
  "models": {
    "logic_analysis_model": "glm-4-long",
    "major_chapters_model": "glm-4-long",
    "sub_chapters_model": "glm-4-long",
    "expansion_model": "glm-4.5-flash",
    "default_model": "glm-4.5-flash"
  },
  "doubao_api_key": "你的豆包 API 密钥（可选）",
  "doubao_api_base_url": "https://ark.cn-beijing.volces.com/api/v3",
  "ark_api_key": "你的 Ark API 密钥或设置环境变量 ARK_API_KEY（可选）",
  "default_model": "zhipu",                   
  "available_models": ["zhipu", "doubao", "ark"],
  "max_tokens": 4000,
  "temperature": 0.7,
  "top_p": 0.7,
  "system": {
    "api": {"max_retries": 5, "retry_delay": 2, "timeout": 60},
    "logging": {"level": "INFO", "file": "06_log/novel_generator.log"}
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

配置校验规则（`Settings.validate()`）：
- 必填：`api_key`、`api_base_url`、`paths.core_setting`
- 其余为可选，有默认值；可通过 `default_model` 切换模型类型

### 3. 填写核心设定与整体大纲

- `01_source/core_setting.yaml`：世界观、核心冲突、人物小传、伏笔清单等
- `01_source/overall_outline.yaml`：按幕描述剧情（支持“第1幕/第一幕”等命名），并列出关键转折点

示例（节选）：

```
世界观: "这是一个灵气充沛的修仙世界..."
核心冲突: "主线矛盾围绕两位角色的价值观冲突..."
人物小传:
  主角:
    姓名: "凛风"
    身份: "散修"
    性格: "自信"
    核心动机: "提升名声"
关键转折点:
  - 第6章: "相遇并发生冲突"
```

### 4. 生成章节大纲

```
python 05_script/main.py
```

流程与输出：
- 自动检测总章节数（支持中文/数字幕名）
- 按批（默认每批15章）生成章节大纲
- 输出文件：`02_outline/chapter_outline_01-{总章节数}.yaml`

### 5. 扩写章节草稿

支持单章或区间扩写：

- 单章扩写示例：
  - `python 05_script/expand_chapters.py --chapter 3 --config 05_script/config.json`

- 批量扩写示例（区间）：
  - `python 05_script/expand_chapters.py --start 1 --end 10 --config 05_script/config.json`

说明：
- 扩写脚本默认大纲文件名存在示例常量（如 `chapter_outline_01-58.yaml` 或 `chapter_outline_01-10.yaml`），请根据你生成的实际文件名调整脚本中的 `outline_file` 或保持生成文件名一致。
- 扩写过程使用 `04_prompt/chapter_expand_prompt.yaml` 与 `style_guide.yaml`，可自行定制风格与输出要求。
- 草稿输出在 `03_draft/chapter_XX.md`，自动备份至 `draft_history/`。

### 6. 合并成书输出

将草稿合并为一个 txt：

```
python 05_script/merge_drafts.py
```

可选参数：
- `--draft-dir` 草稿目录（默认读取配置中的 `paths.draft_dir`）
- `--output` 输出文件（默认写入 `07_output/merged_novel_YYYYMMDD_HHMMSS.txt`）
- `--no-toc` 关闭目录生成
- `--no-metadata` 关闭元数据头

## 提示词与风格

- `04_prompt/chapter_expand_prompt.yaml`：章节扩写模板，包含核心设定、上下文回顾、当前章节大纲与风格约束；强调避免提前透露未来情节、专注当前章节的细节展开。
- `04_prompt/style_guide.yaml`：风格指导模板（语言风格、对话特点、场景描写、节奏控制、心理描写、禁忌等），建议先按题材填写，再在扩写中迭代优化。

## 日志与备份

- 系统日志：`06_log/novel_generator.log`
- API 调用与统计：`06_log/ai_api_logs/`
- 章节草稿备份：`03_draft/draft_history/`
- 大纲历史备份：`02_outline/outline_history/`

## 常见问题

- 报错“API密钥未配置”：请在 `05_script/config.json` 中填写 `api_key`
- 报错“缺少必要文件”：运行 `python 05_script/main.py --init` 重新生成结构与模板
- 扩写脚本找不到大纲：确认 `02_outline/` 下文件名与脚本中 `outline_file` 常量一致，或调整脚本
- 章节不连续：`merge_drafts.py` 会提示缺失章节并允许继续，建议先补齐或在合并时保留目录方便校对

## 开发与扩展

- 核心模块
  - `novel_generator/core/outline_generator.py`：大纲生成与提示词构建
  - `novel_generator/core/chapter_expander.py`：章节扩写与质量评估
  - `novel_generator/core/sliding_window.py`：上下文管理与断裂修复
  - `novel_generator/core/project_manager.py`：初始化与结构校验
  - `novel_generator/utils/multi_model_client.py`：多模型路由、熔断与重试

- 依赖管理
  - 在 `pyproject.toml` 中声明依赖；使用 `pip install .` 或 `uv sync` 安装

## 许可与声明

本项目用于技术探索与写作辅助，请遵循相关平台与模型的使用条款，合理设置 `copyright_bypass`。

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
