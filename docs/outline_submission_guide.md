# 小说大纲提交指南（无图形界面版）

本文档说明如何在不使用图形界面的情况下，通过提供结构化小说大纲来生成完整章节内容。

---

## 目录结构要求

将大纲文件按以下结构放置在项目目录中：

```
01_source/
├── core_setting.yaml      # 小说核心设定（必需）
└── overall_outline.yaml   # 总体大纲（必需）

02_outline/               # 自动生成的章节大纲
├── chapter_01_outline.txt
├── chapter_02_outline.txt
└── ...
```

---

## 1. 核心设定文件 (core_setting.yaml)

**文件名**: `01_source/core_setting.yaml`

**作用**: 定义小说的世界观、核心设定和全局规则

**必需字段**:

```yaml
# 基础信息
novel:
  title: "小说标题"
  genre: "类型"                    # 如：玄幻、科幻、都市、悬疑
  style: "风格描述"                 # 如：热血爽文、悬疑烧脑、甜宠轻松
  target_word_count: 1000000       # 目标总字数（约数）
  target_chapters: 500             # 目标章节数

# 世界观设定
world:
  background: |
    详细描述世界背景，包括：
    - 时代背景（古代/现代/未来/异世界）
    - 地理环境（大陆分布、重要地点）
    - 社会结构（国家、势力、组织）
    - 特殊规则（修炼体系、魔法规则、科技水平）
  
  power_system: |
    如果适用，描述力量体系：
    - 等级划分（如：练气→筑基→金丹→元婴）
    - 能力来源
    - 限制条件

# 核心主题
themes:
  main_theme: "核心主题"            # 如：逆袭、复仇、成长、救赎
  sub_themes:
    - "副主题1"
    - "副主题2"
  
  tone: "整体基调"                 # 如：热血、黑暗、温馨、悬疑

# 全局规则
rules:
  - "规则1：禁止在战斗中使用XX技能"
  - "规则2：主角必须在X章内完成某个目标"
  - "规则3：反派不能在XX情况下被击败"
```

---

## 2. 总体大纲文件 (overall_outline.yaml)

**文件名**: `01_source/overall_outline.yaml`

**作用**: 定义整体剧情结构、主要角色和章节规划

**必需字段**:

```yaml
# 故事梗概
synopsis: |
  用 300-500 字概括整个故事：
  - 主角身份和初始状态
  - 主要冲突（核心矛盾）
  - 故事主线（主角要完成什么）
  - 高潮和结局方向（可以模糊）

# 主要角色
cast:
  protagonist:
    name: "主角姓名"
    age: 年龄
    appearance: "外貌特征"
    personality: "性格特点（3-5个关键词）"
    background: "出身/来历"
    goal: "核心目标/动机"
    growth_arc: "人物成长轨迹"
    traits:
      - "特征1：如冷静理智"
      - "特征2：如重情重义"
    
  supporting:
    - name: "配角1姓名"
      role: "与主角关系（如：师父/挚友/对手）"
      personality: "性格"
      function: "在故事中的作用"
      
    - name: "配角2姓名"
      role: "与主角关系"
      personality: "性格"
      function: "在故事中的作用"
      
  antagonist:
    - name: "反派姓名"
      type: "反派类型（如：宿敌、势力首领、体制）"
      motivation: "作恶动机"
      threat_level: "威胁程度描述"

# 故事结构（三段式）
structure:
  act1_setup:
    chapters: "第1-50章"
    content: |
      描述第一幕的内容：
      - 开场事件
      - 世界介绍
      - 主要角色登场
      - 第一个危机/触发事件
      - 第一幕高潮（第一个重大转折）
    key_events:
      - "第X章：XX事件发生"
      - "第Y章：主角做出XX选择"
      
  act2_confrontation:
    chapters: "第51-350章"
    content: |
      描述第二幕的内容：
      - 主角的成长过程
      - 主要冲突升级
      - 盟友和敌人的变化
      - 中期高潮（故事中段重大事件）
      - 第二幕高潮（最低谷/最大危机）
    key_events:
      - "第X章：XX事件发生"
      - "第Y章：XX转折"
      
  act3_resolution:
    chapters: "第351-500章"
    content: |
      描述第三幕的内容：
      - 最终冲突准备
      - 决战/高潮
      - 结局走向
      - 可能的后续/伏笔
    key_events:
      - "第X章：最终决战"
      - "第Y章：结局"

# 分卷/分篇规划（可选）
volumes:
  - name: "第一卷：XXXX"
    chapters: "第1-100章"
    summary: "本卷主要内容"
    climax: "卷末高潮事件"
    
  - name: "第二卷：XXXX"
    chapters: "第101-200章"
    summary: "本卷主要内容"
    climax: "卷末高潮事件"

# 关键情节点（里程碑）
plot_points:
  - chapter: 1
    event: "开局事件"
    importance: "critical"       # critical/major/minor
    
  - chapter: 30
    event: "第一个小高潮"
    importance: "major"
    
  - chapter: 100
    event: "第一卷高潮"
    importance: "critical"
    
  - chapter: 250
    event: "中点转折"
    importance: "critical"
    
  - chapter: 400
    event: "最终危机前奏"
    importance: "major"
    
  - chapter: 500
    event: "大结局"
    importance: "critical"

# 伏笔与回收（可选）
foreshadowing:
  - setup: "第X章埋下的伏笔"
    payoff: "第Y章回收"
    
  - setup: "另一个伏笔"
    payoff: "回收章节"
```

---

## 3. 章节大纲格式

**生成位置**: `02_outline/chapter_XX_outline.txt`

**说明**: 此文件由系统根据总体大纲自动生成，但你可以手动创建或修改

**格式**:

```markdown
# 第X章：章节标题

## 基本信息
- 章节序号: X
- 预估字数: 3000-4000
- 本章类型: [日常/战斗/对话/转折/高潮]
- 时间线: 故事第X天/某年某月
- 地点: 具体场景

## 剧情概要（100-200字）
简述本章发生了什么，主角做了什么，产生了什么结果。

## 详细情节

### 场景1：场景名称
- **地点**: 
- **时间**: 
- **人物**: 出场角色
- **内容**: 
  1. 具体发生了什么
  2. 角色的动作和对话要点
  3. 场景结果

### 场景2：场景名称
- **地点**: 
- **时间**: 
- **人物**: 
- **内容**: 
  1. ...

## 关键对话（可选）
列出本章必须出现的几句关键台词，或对话的核心要点。

## 人物状态变化
- **主角**: 获得了什么/失去了什么/心理变化
- **配角X**: 关系变化/态度变化

## 剧情推进
- **达成目标**: 本章完成了什么
- **产生问题**: 留下了什么悬念/新问题
- **后续衔接**: 下一章的直接引子

## 注意事项
- 需要强调的细节
- 不能违反的设定
- 埋下的伏笔（如果有）
```

---

## 4. 极简版提交格式

如果你只需要提供最基本的结构，可以使用以下简化格式：

### 简化 core_setting.yaml

```yaml
novel:
  title: "小说标题"
  genre: "类型"
  style: "风格"

world:
  background: |
    世界观简介（200-500字）
  
cast:
  protagonist:
    name: "主角名"
    goal: "核心目标"
    personality: "性格特点"
    
structure:
  act1: "前X章大致内容"
  act2: "中间部分大致内容"  
  act3: "结局部分大致内容"
```

### 简化 overall_outline.yaml

```yaml
synopsis: |
  故事梗概（300字以内）
  
cast:
  protagonist:
    name: "主角名"
    goal: "目标"
    
outline:
  - "第1-50章：开篇，主角遇到XX"
  - "第51-150章：发展阶段，主角XX"
  - "第151-300章：高潮前，XX冲突"
  - "第301-500章：最终决战和结局"
```

---

## 5. 提交检查清单

在提交大纲前，请确认：

- [ ] `01_source/core_setting.yaml` 存在且格式正确
- [ ] `01_source/overall_outline.yaml` 存在且格式正确
- [ ] YAML 语法正确（可以使用在线 YAML 验证器检查）
- [ ] 所有必需字段都已填写
- [ ] 角色名称前后一致
- [ ] 章节编号连续无跳跃
- [ ] 关键情节点有明确标记

---

## 6. 示例文件

### 示例 core_setting.yaml

```yaml
novel:
  title: "修真界赘婿"
  genre: "玄幻"
  style: "轻松幽默，打脸爽文"
  target_word_count: 800000
  target_chapters: 400

world:
  background: |
    修真世界，强者为尊。分为凡人界、修真界、仙界三层。
    主角所在为青云大陆，有九大仙门和无数小门派。
    实力等级：练气→筑基→金丹→元婴→化神→渡劫→大乘→真仙
  
  power_system: |
    修炼靠吸收天地灵气，需要灵根。
    灵根分金木水火土五种，天灵根最佳。
    主角开局获得系统，可以无视灵根限制修炼。

themes:
  main_theme: "逆袭打脸"
  tone: "轻松热血"

rules:
  - "主角不能在100章前暴露系统存在"
  - "每次打脸必须让对方心服口服"
```

### 示例 overall_outline.yaml

```yaml
synopsis: |
  叶尘本是地球程序员，穿越到修真界成为废物赘婿。
  开局激活"最强打脸系统"，只要完成打脸任务就能获得奖励。
  从此一路逆袭，从被人嘲笑的废物成长为一代强者，
  最终飞升仙界，找到回家的路。

cast:
  protagonist:
    name: "叶尘"
    age: 20
    personality: "表面温和，内心腹黑，记仇但恩怨分明"
    background: "地球穿越者，附体在废物赘婿身上"
    goal: "变强，寻找回家方法"
    
  supporting:
    - name: "苏婉儿"
      role: "名义上的妻子，后期真爱"
      personality: "外冷内热，傲娇"
      
    - name: "老管家"
      role: "忠仆，唯一初期对主角好的人"
      personality: "慈祥 loyal"
      
  antagonist:
    - name: "林天霸"
      type: "早期反派，家族大少爷"
      motivation: "嫉妒主角娶了苏婉儿"

structure:
  act1_setup:
    chapters: "第1-50章"
    content: |
      穿越开局，激活系统，首次打脸林天霸。
      赢得苏婉儿初步认可，开始修炼。
    
  act2_confrontation:
    chapters: "第51-300章"
    content: |
      参加宗门大比，崭露头角。
      得罪更大势力，被迫离开家族。
      建立自己势力，不断打脸各路天才。
    
  act3_resolution:
    chapters: "第301-400章"
    content: |
      与仙门大敌决战，飞升仙界。
      寻找地球坐标，悬念收尾。

plot_points:
  - chapter: 1
    event: "穿越激活系统"
    importance: "critical"
  - chapter: 10
    event: "首次打脸林天霸"
    importance: "major"
  - chapter: 50
    event: "宗门大比夺冠"
    importance: "critical"
  - chapter: 150
    event: "被迫离开，自立门户"
    importance: "critical"
  - chapter: 350
    event: "最终决战"
    importance: "critical"
  - chapter: 400
    event: "飞升仙界"
    importance: "critical"
```

---

## 7. 生成流程

1. **准备文件**: 按上述格式创建 `core_setting.yaml` 和 `overall_outline.yaml`
2. **放置文件**: 将文件放入 `01_source/` 目录
3. **生成章节大纲**: 运行 `uv run python 05_script/main.py`
4. **扩写章节**: 运行 `uv run python 05_script/expand_chapters.py --chapter X`
5. **查看结果**: 生成的章节内容在 `03_draft/chapter_XX.txt`

---

## 8. 进阶技巧

### 控制细节程度

- **粗略大纲**: 只提供剧情走向，AI 自动填充细节
- **中等大纲**: 提供每个场景的关键事件
- **详细大纲**: 提供具体对话和动作描述

### 保持一致性

- 在 `core_setting.yaml` 中定义所有固定设定
- 在 `overall_outline.yaml` 中标记所有伏笔和回收点
- 定期回顾已有内容，确保不冲突

### 修改和迭代

- 随时可以修改 `01_source/` 中的文件重新生成
- 可以手动编辑 `02_outline/` 中的单个章节大纲
- 扩写后的 `03_draft/` 文件可以手动修改

---

如有疑问，请参考 `novel_generator/templates/` 中的示例模板文件。
