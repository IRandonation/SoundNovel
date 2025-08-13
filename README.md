# 小说生成系统

一个基于AI的小说生成系统，通过4个阶段的处理流程将长文本转换为结构化的小说内容。

## 功能特点

- **4阶段处理流程**：
  1. 长文本 → 剧情摘要和伏笔 (>150字)
  2. 基于摘要和伏笔 → 章节大纲 (100字/章)
  3. 章节大纲 → 1k字扩写
  4. 1k字 → 2k字最终扩写

- **多模型支持**：不同阶段使用不同模型
  - 阶段1（摘要）：使用更强大的模型（如gpt-4）
  - 阶段2-4（扩写）：使用高效的模型（如gpt-3.5-turbo）
- **可配置的prompts**：所有prompt都存储在 `prompts.yaml` 中，方便非程序员修改
- **标准化输出格式**：统一的输出格式，便于阅读和处理
- **API密钥安全**：配置文件独立管理，支持gitignore
- **错误处理**：完善的错误处理和日志记录

## 安装依赖

```bash
pip install -r requirements.txt
```

或者使用uv（推荐）：

```bash
uv sync
```

## 配置

1. 复制 `config.json` 文件并修改API密钥：

```json
{
  "api_key": "your_actual_api_key_here",
  "api_base_url": "https://api.openai.com/v1",
  "models": {
    "summary_model": "gpt-4",
    "expansion_model": "gpt-3.5-turbo",
    "default_model": "gpt-3.5-turbo"
  },
  "max_tokens": 2000,
  "temperature": 0.7
}
```

2. 确保 `config.json` 在 `.gitignore` 中，避免API密钥泄露

## 使用方法

### 基本使用

```bash
python novel_generator.py input.txt
```

### 高级使用

```bash
python novel_generator.py input.txt --config custom_config.json --output custom_output
```

### 参数说明

- `input_file`: 输入文本文件路径（必需）
- `--config`: 配置文件路径（默认：config.json）
- `--output`: 输出目录（默认：output）

## 输出结构

处理完成后，输出目录将包含：

```
output/
├── stage1_summary.txt              # 阶段1输出：剧情摘要和伏笔
├── stage2_chapter_outlines.txt     # 阶段2输出：章节大纲
├── stage3_expanded_chapter.txt     # 阶段3输出：1k字扩写
├── stage4_final_chapter.txt        # 阶段4输出：2k字最终扩写
├── novel_processing_result.json    # 完整处理结果（JSON格式）
└── [时间戳]_stage[阶段]_[内容].txt # 各阶段详细输出

logs/
└── novel_generator.log             # 运行日志

failed/
└── chapter_[章节号]_failed.txt     # 处理失败的章节
```

## 多模型配置

系统支持为不同任务配置不同的AI模型：

### 模型分配策略

- **summary_model**: 用于阶段1（剧情摘要和伏笔生成）
  - 推荐：GPT-4或其他强大模型
  - 原因：需要理解复杂文本和生成深度分析

- **expansion_model**: 用于阶段2-4（章节大纲和扩写）
  - 推荐：GPT-3.5-turbo或其他高效模型
  - 原因：需要大量生成内容，成本敏感

- **default_model**: 默认模型，用于未明确指定的阶段

### 配置示例

```json
{
  "models": {
    "summary_model": "gpt-4",
    "expansion_model": "gpt-3.5-turbo",
    "default_model": "gpt-3.5-turbo"
  }
}
```

### 成本优化建议

1. **摘要阶段**：使用高质量模型确保分析准确性
2. **扩写阶段**：使用高效模型降低成本
3. **批量处理**：考虑使用更经济的模型进行批量扩写

## 自定义Prompts

所有处理阶段的prompt都存储在 `prompts.yaml` 中。你可以根据需要修改：

```yaml
stage1_summary:
  name: "剧情摘要和伏笔生成"
  description: "将长文本转换为整篇剧情摘要和伏笔内容"
  prompt_template: |
    # 你的自定义prompt模板
    {input_text}
```

### 支持的变量

- `{input_text}`: 输入的文本内容
- `{summary}`: 剧情摘要
- `{foreshadowing}`: 伏笔分析
- `{chapter_outline}`: 章节大纲
- `{chapter_content}`: 章节内容

## 标准化输出格式

所有输出都遵循以下格式：

```
【阶段名称】
2024-01-01 12:00:00

实际内容

------------------------
```

## 错误处理

系统包含完善的错误处理机制：

- API调用失败时自动重试
- 处理失败的章节会保存到 `failed/` 目录
- 详细的日志记录，便于调试

## 示例

处理 `source/越女剑.txt`：

```bash
python novel_generator.py source/越女剑.txt
```

这将：
1. 生成剧情摘要和伏笔
2. 创建章节大纲
3. 扩写每个章节到1k字
4. 最终扩写到2k字

## 注意事项

1. 确保API密钥配置正确
2. 输入文件编码应为UTF-8
3. 处理大文件可能需要较长时间
4. 建议先在小文件上测试系统

## 技术栈

- Python 3.13+
- zai-sdk (API客户端)
- PyYAML (YAML解析)
- 标准库：json, logging, argparse等

## 许可证

MIT License
