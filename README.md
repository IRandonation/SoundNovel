# 全自动TXT洗稿系统（DeepSeek专用版）

## 功能特点
- 自动拆分超长文本满足API限制
- 智能保留关键故事元素
- 批量处理目录下所有TXT文件
- 自动规避相似内容

## 安装依赖
```bash
pip install -r requirements.txt
```

## 配置说明
1. 修改config.json文件中的`api_key`为您从DeepSeek获取的API密钥
2. 可根据需要调整`rewrite_rules`中的改写规则

## 使用方法
1. 将要改写的TXT文件放在程序同级目录
2. 运行程序：
```bash
python main.py
```
3. 改写后的文件将保存在`output`目录
4. 原始文件将被移动到`processed`目录

## 注意事项
- 确保网络连接正常
- 单个文件建议不超过50万字
- 处理过程中请不要关闭程序
