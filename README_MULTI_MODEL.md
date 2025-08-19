# 多模型支持说明

本项目现在支持多种AI模型的调用和切换，包括智谱AI、豆包、火山引擎Ark等。

## 功能特性

- **多模型支持**: 支持智谱AI、豆包、火山引擎Ark等多种模型
- **动态切换**: 可以在运行时动态切换使用的模型
- **统一接口**: 提供统一的API接口，屏蔽不同模型的差异
- **自动重试**: 内置重试机制和熔断器，提高稳定性
- **限流控制**: 防止API调用过于频繁

## 安装依赖

首先需要安装必要的依赖：

```bash
pip install volcenginesdkarkruntime
```

## 配置说明

### 1. 配置文件

在 `config_example.json` 中提供了完整的配置示例。主要配置项包括：

#### 智谱AI配置
```json
{
  "api_key": "你的智谱AI API密钥",
  "api_base_url": "https://open.bigmodel.cn/api/paas/v4",
  "models": {
    "logic_analysis_model": "glm-4-long",
    "major_chapters_model": "glm-4-long",
    "sub_chapters_model": "glm-4-long",
    "expansion_model": "glm-4.5-flash",
    "default_model": "glm-4.5-flash"
  }
}
```

#### 豆包配置
```json
{
  "doubao_api_key": "你的豆包API密钥",
  "doubao_api_base_url": "https://ark.cn-beijing.volces.com/api/v3",
  "doubao_models": {
    "logic_analysis_model": "ep-20241210233657-lz8fv",
    "major_chapters_model": "ep-20241210233657-lz8fv",
    "sub_chapters_model": "ep-20241210233657-lz8fv",
    "expansion_model": "ep-20241210233657-lz8fv",
    "default_model": "ep-20241210233657-lz8fv"
  }
}
```

#### 火山引擎Ark配置
```json
{
  "ark_api_key": "你的Ark API密钥",
  "ark_models": {
    "logic_analysis_model": "ep-20241210233657-lz8fv",
    "major_chapters_model": "ep-20241210233657-lz8fv",
    "sub_chapters_model": "ep-20241210233657-lz8fv",
    "expansion_model": "ep-20241210233657-lz8fv",
    "default_model": "ep-20241210233657-lz8fv"
  }
}
```

#### 多模型配置
```json
{
  "default_model": "zhipu",
  "available_models": ["zhipu", "doubao", "ark"]
}
```

### 2. 环境变量

对于Ark模型，也可以通过环境变量配置API密钥：

```bash
export ARK_API_KEY="your_ark_api_key"
```

## 使用方法

### 1. 基本使用

```python
from novel_generator.utils.multi_model_client import MultiModelClient
from novel_generator.config.settings import create_default_config

# 创建配置
config = create_default_config()
config["api_key"] = "your_zhipu_api_key"
config["doubao_api_key"] = "your_doubao_api_key"
config["ark_api_key"] = "your_ark_api_key"

# 初始化客户端
client = MultiModelClient(config)

# 进行对话
messages = [
    {"role": "system", "content": "你是 AI 人工智能助手"},
    {"role": "user", "content": "常见的十字花科植物有哪些？"}
]

# 使用默认模型
response = client.chat_completion(messages=messages)
print(response)

# 指定模型类型
response = client.chat_completion(model_type="doubao", messages=messages)
print(response)
```

### 2. 模型切换

```python
# 切换到豆包模型
client.switch_model("doubao")

# 切换到Ark模型
client.switch_model("ark")

# 切换回智谱AI
client.switch_model("zhipu")

# 获取当前模型
current_model = client.get_current_model()
print(f"当前使用模型: {current_model}")
```

### 3. 连接测试

```python
# 测试所有模型连接
results = client.test_all_connections()
for model_type, is_connected in results.items():
    print(f"{model_type}: {'连接成功' if is_connected else '连接失败'}")

# 测试特定模型连接
is_connected = client.test_connection("zhipu")
print(f"智谱AI连接: {'成功' if is_connected else '失败'}")
```

### 4. 小说生成功能

```python
# 生成大纲
outline = client.generate_outline("请为一个科幻小说生成大纲")
print(outline)

# 扩写章节
chapter = client.expand_chapter("请扩写第一章内容")
print(chapter)

# 分析内容
analysis = client.analyze_content("小说内容...")
print(analysis)

# 优化内容
optimized = client.optimize_content("原始内容", "优化建议")
print(optimized)

# 检查一致性
consistency = client.check_consistency(["第一章内容", "第二章内容"])
print(consistency)
```

### 5. 获取可用模型

```python
# 获取可用模型列表
available_models = client.get_available_models()
print(f"可用模型: {available_models}")
```

## 示例代码

完整的示例代码请参考 `example_multi_model_usage.py` 文件。

## 注意事项

1. **API密钥安全**: 请妥善保管API密钥，不要在代码中硬编码
2. **模型限制**: 不同模型可能有不同的限制，如token数量、调用频率等
3. **错误处理**: 建议在使用时添加适当的错误处理逻辑
4. **成本控制**: 不同模型的调用成本可能不同，请根据需要选择合适的模型

## 故障排除

### 1. 连接失败

- 检查API密钥是否正确
- 检查网络连接是否正常
- 确认API服务是否可用

### 2. 模型不可用

- 确认模型名称是否正确
- 检查模型是否在可用列表中
- 验证模型是否有相应的权限

### 3. 调用频率限制

- 调整重试参数
- 增加调用间隔
- 考虑使用多个API密钥

## 扩展支持

如果需要支持更多模型，可以：

1. 继承 `BaseModelClient` 类创建新的模型客户端
2. 在 `MultiModelClient` 中注册新的客户端
3. 更新配置文件以支持新模型的配置

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。