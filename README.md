# SoundNovel - AI辅助小说创作工具

一个基于多模型大语言模型的长篇小说创作助手，采用**三板块架构**（API板块 + 资源板块 + 逻辑板块），支持多小说项目管理，帮助你从核心设定到成书的高效创作。

## 核心特性

### 1. 三板块架构

```
┌─────────────────────────────────────────────────────────────┐
│                      SoundNovel                              │
├──────────────┬─────────────────────┬────────────────────────┤
│  API板块      │   资源板块           │     逻辑板块            │
│  api/         │   novels/           │     novel_generator/   │
├──────────────┼─────────────────────┼────────────────────────┤
│ • 多API配置   │ • 多小说项目管理     │ • 大纲生成逻辑          │
│ • 豆包/DeepSeek│ • 独立source/outline │ • 章节扩写逻辑          │
│ • 配置复用   │ • 独立prompts       │ • 状态管理              │
│               │ • 独立draft/logs    │ • CLI命令              │
└──────────────┴─────────────────────┴────────────────────────┘
```

**优势**:
- **API板块独立**: 一次配置，多小说复用
- **资源隔离**: 每个小说完全独立，互不干扰
- **逻辑复用**: 核心生成逻辑统一维护

### 2. 两阶段流水线架构

```
大纲生成阶段
    ├── Stage 1: 章节梗概（直接从 overall_outline.yaml 幕结构读取，批量生成章节核心内容）
    └── Stage 2: 章级骨架（章节定位/因果链/场景概览/情绪曲线/伏笔处理/结尾卡点）
            ↓
章节扩写阶段（上下文注入）
    ├── 前30章大纲上下文（骨架级摘要）
    ├── 前10章正文全文（原文注入）
    └── 当前章完整骨架
            ↓
    每章一次API调用，AI自然处理场景间过渡与节奏
```

**幕信息不再由 LLM 生成**：作者在 `overall_outline.yaml` 的幕结构中手写 `核心冲突` / `情感基调` / `关键转折点`，下游直接消费，保真度更高。

### 3. 上下文注入系统

章节扩写时，prompt由三部分组成：

- **前30章大纲上下文**: 骨架级摘要保证宏观连续性和伏笔贯通
- **前10章正文全文**: 原文注入不做摘要，保证文风、语气、细节的连贯
- **当前章完整骨架**: 章节定位/核心事件/因果链/场景概览/情绪曲线/结尾卡点

上下文窗口参数: `outline_window`（默认30）、`draft_window`（默认10）。

### 4. 章节状态系统

每章维护三种状态，智能管理重生成：

- **clean**: 正文与大纲一致
- **dirty**: 正文需要重生成（前文变更导致上下文变化）
- **cosmetic**: 仅润色修改，不触发级联

`touch`命令标记修改类型，`content`类型触发脏传播（N+1到N+draft_window标记为dirty）。

### 5. 多模型支持

支持豆包和DeepSeek API，可在API板块中配置多个服务商，在创建小说时选择使用。

---

## 目录结构

```
SoundNovel/
├── api/                        # 【API板块】API配置中心
│   ├── configs/                # API配置存储目录
│   │   ├── doubao-pro.json     # 豆包配置示例
│   │   └── deepseek-chat.json  # DeepSeek配置示例
│   └── manager.py              # APIManager类
│
├── novels/                     # 【资源板块】多小说项目目录
│   └── {novel_id}/             # 单个小说项目（完全隔离）
│       ├── source/             # 用户小说源材料
│       │   ├── core_setting.yaml      # 世界观、人物、伏笔设定
│       │   └── overall_outline.yaml   # 高层故事结构
│       ├── prompts/            # 小说专属提示词模板
│       │   ├── system_prompts.yaml    # AI角色定义
│       │   ├── style_guide.yaml       # 风格指导（需根据小说修改）
│       │   ├── generation_prompts.yaml # 生成提示词
│       │   └── satisfaction_prompts/  # 爽点提示词
│       ├── outline/            # 生成的大纲
│       ├── draft/              # 章节草稿
│       ├── logs/               # 生成日志
│       │   ├── ai_api_logs/
│       │   └── system_logs/
│       └── config/             # 小说专属配置
│           ├── novel.json      # 小说元数据（名称、API引用等）
│           ├── generation.json   # 生成参数（窗口、字数等）
│           └── state.json      # 生成状态（进度、章节状态）
│
├── novel_generator/            # 【逻辑板块】主Python包
│   ├── cli/                    # CLI命令
│   ├── config/                 # 配置管理
│   ├── core/                   # 核心逻辑（大纲生成、章节扩写）
│   ├── novel_manager.py        # 小说资源管理器
│   └── utils/                  # 工具函数
│
├── user/                       # 【旧版单小说目录】（保留兼容）
├── soundnovel.py               # 统一入口
└── pyproject.toml              # 依赖声明
```

---

## 安装与环境

推荐使用`uv`进行依赖管理：

```bash
# 安装uv
pip install uv

# 同步依赖
uv sync
```

---

## 使用方式

### 统一入口

```bash
# 使用统一入口
python soundnovel.py <板块> <命令> [选项]

# 或使用uv运行
uv run soundnovel.py <板块> <命令> [选项]
```

### 三大板块命令

#### 1. API板块命令 (`api`)

管理API服务商配置，支持多配置共存：

```bash
# 列出所有API配置
uv run soundnovel.py api list

# 创建新API配置（交互式）
uv run soundnovel.py api create

# 设置默认API配置
uv run soundnovel.py api use <config_id>

# 测试API连接
uv run soundnovel.py api test [config_id]

# 删除API配置
uv run soundnovel.py api delete <config_id>

# 编辑API配置
uv run soundnovel.py api edit <config_id>
```

**配置存储**: `api/configs/<config_id>.json`

#### 2. 资源板块命令 (`novel`)

管理多小说项目：

```bash
# 列出所有小说项目
uv run soundnovel.py novel list

# 创建新小说（交互式）
uv run soundnovel.py novel create

# 切换当前小说
uv run soundnovel.py novel switch <novel_id>

# 查看小说信息
uv run soundnovel.py novel info [novel_id]

# 重命名小说
uv run soundnovel.py novel rename <novel_id> <new_name>

# 删除小说（需确认）
uv run soundnovel.py novel delete <novel_id>

# 导出小说备份
uv run soundnovel.py novel export <novel_id> [--output <path>]

# 导入小说
uv run soundnovel.py novel import <zip_path>
```

**小说存储**: `novels/<novel_id>/`

**当前小说**: 记录在 `novels/.current` 文件中

#### 3. 逻辑板块命令

执行生成逻辑（操作当前小说或指定--novel）：

```bash
# 生成大纲（两阶段：章节梗概 → 章节骨架）
uv run soundnovel.py cli outline                        # 完整流程
uv run soundnovel.py cli outline --batch-size 20       # 每批20章
uv run soundnovel.py cli outline --start 50 --end 100  # 指定范围
uv run soundnovel.py cli outline --window 150          # 对话窗口150章
uv run soundnovel.py cli outline --skip-summary        # 跳过梗概依赖

# 分阶段大纲生成（调试用）
uv run soundnovel.py cli chapter-summary               # Stage 1: 章节梗概
uv run soundnovel.py cli chapter-summary --batch-size 200  # 梗概批次大小

# 扩写章节
uv run soundnovel.py cli expand --chapter 1            # 单章
uv run soundnovel.py cli expand --start 1 --end 10     # 范围扩写
uv run soundnovel.py cli expand --from-last            # 从上次继续
uv run soundnovel.py cli expand --batch-size 5         # 每批5章
uv run soundnovel.py cli expand --single               # 单章模式（禁用批量）
uv run soundnovel.py cli expand --outline-window 50    # 大纲窗口50章
uv run soundnovel.py cli expand --draft-window 15      # 正文窗口15章

# 续写章节
uv run soundnovel.py cli continue                      # 从上次位置继续
uv run soundnovel.py cli continue --end 100            # 到第100章停止
uv run soundnovel.py cli continue --cascade            # 级联重生成dirty章节
uv run soundnovel.py cli continue --dry-run            # 仅显示计划（不执行）

# 查看项目状态
uv run soundnovel.py cli status                        # 显示进度和章节状态

# 标记章节修改类型
uv run soundnovel.py cli touch --chapter 15 --type content    # 内容变更（触发级联）
uv run soundnovel.py cli touch --chapter 15 --type cosmetic   # 仅润色（不触发级联）
uv run soundnovel.py cli touch --chapter 15 --type content --no-cascade  # 不触发级联

# 重生成指定章节
uv run soundnovel.py cli regenerate --chapters 12-14   # 范围重生成
uv run soundnovel.py cli regenerate --chapter 15       # 单章重生成
uv run soundnovel.py cli regenerate --chapters 12-14 --outline  # 仅重生成大纲
uv run soundnovel.py cli regenerate --chapter 15 -y    # 跳过确认

# 配置生成参数
uv run soundnovel.py cli settings                      # 显示当前配置
uv run soundnovel.py cli settings --interactive        # 交互式配置
uv run soundnovel.py cli settings --show-file          # 显示完整配置文件
uv run soundnovel.py cli settings --reset              # 重置为默认配置
uv run soundnovel.py cli settings --outline-window 40  # 设置大纲窗口
uv run soundnovel.py cli settings --draft-window 12    # 设置正文窗口
uv run soundnovel.py cli settings --conversation-window 120  # 对话窗口（滑动窗口）
uv run soundnovel.py cli settings --max-conversation-tokens 1000000  # token上限

# 使用指定小说（不切换当前）
uv run soundnovel.py cli expand --chapter 1 --novel <novel_id>
```

---

## 快速开始

### 1. 配置API

```bash
# 创建豆包API配置
uv run soundnovel.py api create
# 按提示输入：配置ID、名称、API Key、模型等

# 或使用现有配置
# 系统会自动检测 user/config/session.json 中的配置并迁移
```

### 2. 创建小说

```bash
uv run soundnovel.py novel create

# 交互式输入：
# - 小说名称: 我的修仙小说
# - 描述: 一个逆天改命的故事
# - 选择API配置: 1 (豆包) 或 2 (DeepSeek)
```

**创建后自动生成**:
- `source/core_setting.yaml` - 核心设定模板
- `source/overall_outline.yaml` - 整体大纲模板
- `prompts/style_guide.yaml` - 风格指导（需根据小说修改）
- `prompts/system_prompts.yaml` - AI角色定义
- `config/*.json` - 配置和状态文件

### 3. 填写小说设定

编辑 `novels/{novel_id}/source/core_setting.yaml`:

```yaml
世界观:
  背景: 修仙世界，宗门林立，灵气充沛
  规则: 九重境界，每重三阶，突破需渡劫

核心冲突:
  主线: 主角为报灭门之仇踏上修仙路
  反派: 第一大宗门少主

人物小传:
  主角A:
    身份: 没落家族唯一幸存者
    性格: 隐忍坚韧，杀伐果断
    目标: 复仇+复兴家族
    金手指: 获得上古传承

伏笔清单:
  - 神秘玉佩（第3章获得，第25章揭示）
  - 主角血脉（第10章觉醒，第50章揭示）
```

编辑 `novels/{novel_id}/source/overall_outline.yaml`:

```yaml
整体结构:
  总章节: 100章
  分幕: 3幕

幕结构:
  第1幕（崛起）:
    章节范围: 第1-30章
    核心剧情: 主角获得金手指，进入宗门展现实力
    爽点布局:
      - 第5章: 打脸挑衅者
      - 第15章: 突破境界震惊全场
      - 第25章: 宗门大比夺冠
```

**重要**: 编辑 `prompts/style_guide.yaml` 调整风格指导，使其符合你的小说类型！

### 4. 生成大纲

```bash
# 两阶段大纲生成（章节梗概 → 章节骨架）
uv run soundnovel.py cli outline

# 产物保存在 novels/{novel_id}/outline/
# - chapter_summary.json: 章节梗概
# - outline.json: 章级骨架（最终大纲）
```

大纲包含：
- 章节梗概（批量生成章节核心内容，幕信息从 overall_outline.yaml 直接读取）
- 章级骨架（章节定位/因果链/场景概览/情绪曲线/伏笔处理/结尾卡点）

### 5. 扩写正文

```bash
# 扩写单章
uv run soundnovel.py cli expand --chapter 8

# 查看生成的正文
cat novels/{novel_id}/draft/第0008章.txt

# 从上次位置继续扩写
uv run soundnovel.py cli continue
```

---

## 多小说管理

### 典型工作流

```bash
# 1. 创建修仙小说
uv run soundnovel.py novel create
# 输入: honghuang, "洪荒修仙小说", 选择豆包API

# 2. 填写设定并生成...

# 3. 切换到都市小说
uv run soundnovel.py novel create
# 输入: dushi, "都市异能小说", 选择DeepSeekAPI

# 4. 两个小说完全独立，prompts、source、draft互不干扰

# 5. 随时切换
uv run soundnovel.py novel switch honghuang
uv run soundnovel.py cli expand --chapter 10

uv run soundnovel.py novel switch dushi
uv run soundnovel.py cli expand --chapter 5
```

### 小说导出/导入

```bash
# 导出小说（备份/分享）
uv run soundnovel.py novel export honghuang --output backup/honghuang_20250510.zip

# 导入小说
uv run soundnovel.py novel import backup/honghuang_20250510.zip
```

---

## 创作工作流

```
用户阶段
    ├── 1. 配置API（一次）
    │       └── uv run soundnovel.py api create
    ├── 2. 创建小说
    │       └── uv run soundnovel.py novel create
    ├── 3. 填写设定
    │       ├── source/core_setting.yaml
    │       ├── source/overall_outline.yaml
    │       └── prompts/style_guide.yaml（重要！）
    └── 4. 审查大纲
            └── 调整爽点时机、修改情节设计

系统阶段
    ├── 1. 生成章节梗概（Stage 1）
    ├── 2. 生成章级骨架（Stage 2）
    └── 3. 上下文注入扩写
            └── 30章大纲 + 10章正文 + 当前骨架

迭代阶段
    ├── 1. 人工审阅章节
    ├── 2. 如需修改 → 手动编辑draft
    ├── 3. 标记修改类型 → uv run soundnovel.py cli touch
    └── 4. 级联重生成受影响章节
```

---

## 配置系统

### 小说专属配置

每个小说独立配置，位于 `novels/{novel_id}/config/`:

| 文件 | 说明 | 示例 |
|------|------|------|
| `novel.json` | 元数据、API配置引用 | `{"name": "洪荒", "api_config_ref": "doubao-pro"}` |
| `generation.json` | 生成参数 | `{"outline_window": 30, "draft_window": 10}` |
| `state.json` | 生成进度和章节状态 | `{"last_draft_chapter": 50, "chapter_states": {...}}` |

### API配置

全局配置，位于 `api/configs/*.json`:

```json
{
  "id": "doubao-pro",
  "name": "豆包专业版",
  "provider": "doubao",
  "api_key": "xxx",
  "api_base_url": "https://ark.cn-beijing.volces.com/api/v3",
  "models": {
    "expansion_model": "doubao-seed-2-0-lite-260215"
  },
  "is_default": true
}
```

---

## 从旧版迁移

如果你使用过旧版单小说结构（`user/`目录）：

```bash
# 1. 备份旧数据（已完成）
cp -r user user.backup.$(date +%Y%m%d)

# 2. API配置会自动识别旧配置
uv run soundnovel.py api list

# 3. 将旧小说迁移到新结构
# 手动复制或创建新小说后导入
uv run soundnovel.py novel create
# 然后复制 user/source/* 到 novels/{id}/source/
# 复制 user/output/* 到 novels/{id}/

# 4. prompts模板已内置在代码中，会自动生成通用模板
# 根据你的小说类型修改 prompts/style_guide.yaml
```

---

## 关键优势

1. **创意集中在大纲阶段**: AI负责工程化实现，你负责核心创意
2. **多小说隔离**: 每个小说独立配置、独立prompts、独立输出
3. **API配置复用**: 一次配置，多小说共享
4. **上下文感知**: 自动感知用户修改，保证前后连贯
5. **人工可干预**: 可在任意阶段调整大纲，系统智能管理重生成
6. **质量稳定**: 扩写纯执行，不受AI状态波动影响
7. **成本优化**: 每章一次API调用，无中间状态

---

## 隐私与安全

- API Key存储在`api/configs/*.json`中（本地文件）
- 已加入`.gitignore`，不会提交到版本控制
- 生成的内容默认不提交到版本控制

---

## 许可证

MIT License
