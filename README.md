# SoundNovel - AI辅助小说创作工具

一个基于多模型大语言模型的长篇小说创作助手，采用**"大纲即剧本"**的先进架构，实现爽点的工程化控制，帮助你从核心设定到成书的高效创作。

## 核心特性

### 1. 三阶段大纲生成（场景级剧本）

不同于传统的"简单概要→AI自由发挥"，我们采用**剧本式大纲**：

```
幕级规划（爽点战略布局）
    ↓
章级骨架（功能标记+约束）
    ↓
场景级剧本（节拍设计+对白+感官细节）
    ↓
扩写（纯执行，无需创意决策）
```

**优势**：
- 大纲即剧本，人工可精细调整每个场景
- 扩写阶段零创意负担，质量稳定可控
- API调用减少50%（从10+次/章降至5次/章）

### 2. 爽点工程化

**6种爽点类型**，每种都有标准元素清单和节拍结构：

| 类型 | 核心元素 | 经典节奏 |
|------|---------|---------|
| **打脸** | 反派嚣张→主角隐忍→反转触发→实力展现→震惊反应→后续收益 | 3章一小爽，幕末一大爽 |
| **实力提升** | 困境/机缘→努力/顿悟→突破/获得→展现实力→地位提升 | 幕中突破，幕末质变 |
| **揭秘** | 悬念累积→线索汇集→真相大白→连锁反应 | 幕末揭秘，全书高潮 |
| **收获** | 发现目标→克服困难→成功获得→意外之喜 | 穿插分布 |
| **情感** | 情感积累→关系突破→情感确认→温暖满足 | 人物关系转折点 |
| **地位跃升** | 被轻视→展现实力→被认可→进入新层级 | 阶段跨越时刻 |

**爽点节奏自动计算**：
- 每3-4章：小爽点（强度5-6）
- 幕中：中爆点（强度7-8）
- 幕末：大爆点（强度9-10）
- 低谷期待期：情绪3-4（不能连续爽）

### 3. 编码质量检查（零API成本）

90%的检查通过编码实现，无需API调用：

- **爽点完整性检查**：正则匹配6大元素
- **连续性检查**：根据大纲标记智能判断（支持多线叙事）
- **禁忌词检测**：实时正则匹配
- **重复词检测**：滑动窗口统计

### 4. 多线叙事支持

通过大纲标记避免连续性误报：

```yaml
约束标记:
  continuity_required: false  # 新线场景，不检查连续性
  narrative_line: B线         # 叙事线标识
  setup_required: true        # 需要检查Setup完整性
```

## 架构对比

| 维度 | 传统架构 | SoundNovel新架构 |
|------|---------|-----------------|
| 大纲详细度 | 6字段概要 | 场景级剧本（节拍+对白+感官） |
| 爽点控制 | 随机出现 | 按节奏规划（工程化） |
| 扩写复杂度 | 高（AI决定情节+文笔） | 低（纯执行，按剧本） |
| API调用/章 | 10+次（生成→润色→评审循环） | 5次（幕→章→场景） |
| 上下文注入 | 2000+ tokens（大量追踪） | 500 tokens（精简剧本） |
| 人工干预 | 难（只能重试扩写） | 易（改大纲即可） |
| 质量检查 | 依赖评审者（API） | 编码检查（毫秒级） |

## 目录结构

```
SoundNovel/
├── 01_source/                    # 【用户提供】核心素材与设定
│   ├── core_setting.yaml         # 世界观、人物、伏笔
│   └── overall_outline.yaml      # 幕结构、核心剧情脉络
├── 02_outline/                   # 【生成】章节大纲
│   ├── act_plan.yaml            # 幕级规划（含爽点布局）
│   ├── chapter_skeletons.yaml   # 章级骨架
│   └── chapter_*.yaml           # 场景级剧本
├── 03_draft/                     # 【生成】章节正文
├── 04_prompt/                    # 提示词模板
│   ├── prompts/
│   │   ├── outline_generation.yaml      # 三阶段生成Prompt
│   │   ├── scene_expansion.yaml         # 场景扩写Prompt
│   │   └── satisfaction_prompts/        # 爽点专用Prompt
│   │       ├── face_slap.yaml
│   │       ├── power_up.yaml
│   │       └── revelation.yaml
│   └── tracking/                 # 追踪文件
├── 05_script/                    # 配置文件
│   ├── generation_config.json   # 生成配置
│   └── session.json             # 会话状态（含API密钥）
├── 06_log/                       # 【生成】日志目录
├── novel_generator/              # 核心代码包
│   ├── cli/                      # CLI命令模块
│   ├── config/                   # 配置管理
│   ├── core/                     # 核心逻辑
│   │   ├── satisfaction_engine.py      # 爽点节奏引擎
│   │   ├── outline_generator.py        # 三阶段大纲生成
│   │   ├── scene_expander.py           # 场景级扩写
│   │   ├── scene_assembler.py          # 场景组装
│   │   ├── satisfaction_checker.py     # 爽点质量检查（编码）
│   │   ├── continuity_checker.py       # 连续性检查（编码）
│   │   └── chapter_expander.py         # 章节扩写（简化版）
│   └── utils/                    # 通用工具
├── soundnovel.py                 # 统一入口
├── build_exe.py                  # 打包脚本
└── pyproject.toml               # 依赖声明
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

### CLI 命令行

```bash
# 使用统一入口
python soundnovel.py cli <command> [options]

# 或使用模块方式
uv run python -m novel_generator.cli <command> [options]
```

#### 核心命令

```bash
# 初始化项目
python soundnovel.py cli init

# 三阶段大纲生成
python soundnovel.py cli outline --stage act      # 幕级规划
python soundnovel.py cli outline --stage chapter  # 章级骨架
python soundnovel.py cli outline --stage scene    # 场景级剧本

# 扩写章节（基于场景剧本）
python soundnovel.py cli expand --chapter 1       # 单章
python soundnovel.py cli expand --start 1 --end 10  # 范围
python soundnovel.py cli continue                 # 从上次继续

# 查看项目状态
python soundnovel.py cli status

# 配置AI角色和生成参数
python soundnovel.py cli settings --interactive

# 查看帮助
python soundnovel.py --help
python soundnovel.py cli --help
```

### 快速开始

#### 1. 初始化项目

```bash
python soundnovel.py cli init
```

#### 2. 填写小说设定

编辑 `01_source/core_setting.yaml`：

```yaml
世界观:
  背景: 修仙世界，宗门林立
  规则: 灵气修炼，境界划分

核心冲突:
  主线: 主角为报灭门之仇踏上修仙路
  反派: 第一大宗门少主

人物小传:
  主角A:
    身份: 没落家族唯一幸存者
    性格: 隐忍坚韧
    目标: 复仇+复兴家族
    金手指: 获得上古传承

伏笔清单:
  - 神秘玉佩（第3章获得，第25章揭示）
  - 主角血脉（第10章觉醒，第50章揭示）
```

编辑 `01_source/overall_outline.yaml`：

```yaml
整体结构:
  总章节: 100章
  分幕: 3幕

幕结构:
  第1幕（崛起）:
    章节范围: 第1-30章
    核心剧情: 主角获得金手指，进入宗门展现实力
```

#### 3. 生成大纲

```bash
# 幕级规划（含爽点战略布局）
python soundnovel.py cli outline --stage act

# 审查并调整幕规划
edit 02_outline/act_plan.yaml

# 章级骨架
python soundnovel.py cli outline --stage chapter

# 审查并调整章骨架
edit 02_outline/chapter_skeletons.yaml

# 场景级剧本（可单独生成某章）
python soundnovel.py cli outline --stage scene --chapter 8
```

#### 4. 扩写正文

```bash
# 基于场景剧本扩写
python soundnovel.py cli expand --chapter 8

# 查看生成的正文
 cat 03_draft/第0008章.txt
```

## 创作工作流

```
用户提供原材料
    ├── 世界观（种子）
    ├── 核心冲突（方向）
    ├── 人物小传（灵魂）
    └── 整体大纲（骨架）
            ↓
系统三阶段生成
    ├── 幕级规划（爽点战略布局）
    ├── 章级骨架（功能+约束标记）
    └── 场景级剧本（节拍+对白+感官）
            ↓
人工审查调整
    ├── 调整爽点时机
    ├── 修改节拍设计
    └── 优化对白要点
            ↓
系统扩写执行
    ├── 场景扩写（纯执行）
    ├── 场景组装（编码）
    └── 编码检查（毫秒级）
            ↓
成品章节
```

## 关键优势

1. **创意集中在大纲阶段**：AI负责工程化实现，你负责核心创意
2. **爽点可控**：不是随机出现，是按节奏规划的产物
3. **人工可干预**：可在任意阶段调整大纲，无需重试扩写
4. **质量稳定**：扩写纯执行，不受AI状态波动影响
5. **成本优化**：编码检查替代大部分API评审

## 构建可执行文件

打包成 `.exe` 分享给其他人：

```bash
# 构建 CLI 版本
python build_exe.py

# 清理构建文件
python build_exe.py --clean
```

输出：`dist/SoundNovelAI_CLI.zip`

## 隐私与安全

- API Key 存储在 `05_script/session.json` 中
- `session.json` 已被加入 `.gitignore`
- 生成的内容默认不提交到版本控制

## 许可证

MIT License
