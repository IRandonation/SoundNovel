# SoundNovel Agent 演进方案 v1.0

> 文档版本：v1.0  
> 创建时间：2025年4月25日  
> 目标：将 SoundNovel 从批量生成工具演进为对话式 AI 写作 Agent

---

## 1. 项目背景

### 1.1 现状分析

SoundNovel 目前已具备以下基础能力：

- **三角色流程**：Generator → Refiner → Reviewer 的质量保障循环
- **上下文追踪**：人物状态、伏笔、情感弧线三大追踪器
- **配置管理**：SessionManager + GenerationConfigManager 双配置系统
- **CLI 框架**：基于 argparse 的命令行界面

### 1.2 演进目标

将现有工具演进为**对话式 AI Agent**，实现：

| 能力 | 现状 | 目标 |
|-----|------|------|
| 交互方式 | 命令行参数 | 自然语言对话 |
| 任务执行 | 批量生成 | 规划-执行-观察循环 |
| 编辑粒度 | 整章重生成 | 段落级精细化修改 |
| 上下文 | 生成时注入 | Agent 主动查询 |
| 持续性 | 单次命令 | 多轮对话状态保持 |

---

## 2. 总体架构设计

### 2.1 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     用户交互层 (CLI)                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  传统 CLI    │  │  Agent REPL  │  │  对话式命令混合      │   │
│  │  (保留)      │  │  (新增)      │  │  (长期)              │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Agent 核心层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  意图解析器   │  │  任务规划器   │  │  记忆系统            │   │
│  │  Intent      │  │  Planner     │  │  Memory              │   │
│  │  Parser      │  │              │  │                      │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  工具执行器   │  │  上下文查询   │  │  对话管理器          │   │
│  │  Tool        │  │  Context     │  │  Dialog              │   │
│  │  Executor    │  │  Query       │  │  Manager             │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      工具层 (复用/扩展)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  生成工具     │  │  修改工具     │  │  分析工具            │   │
│  │  Generation  │  │  Modification│  │  Analysis            │   │
│  │  - 整章生成   │  │  - 段落修改   │  │  - 连续性检查        │   │
│  │  - 段落扩写   │  │  - 语气调整   │  │  - 人物状态查询      │   │
│  │  - 大纲生成   │  │  - 插入/删除  │  │  - 伏笔追踪          │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │  规划工具     │  │  研究工具     │                            │
│  │  Planning    │  │  Research    │                            │
│  │  - 情节规划   │  │  - 设定查询   │                            │
│  │  - 人物弧光   │  │  - 一致性检查 │                            │
│  └──────────────┘  └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      基础设施层 (复用)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  AIRole      │  │  MultiModel  │  │  PromptManager       │   │
│  │  Manager     │  │  Client      │  │                      │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  Character   │  │  Foreshadow  │  │  EmotionalArc        │   │
│  │  Tracker     │  │  Tracker     │  │  Tracker             │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心概念

#### Agent Loop（核心循环）

```python
# 简化版 Agent 循环
while True:
    user_input = get_input()

    # 1. 理解意图
    intent = intent_parser.parse(user_input)

    # 2. 检索记忆
    memories = memory.retrieve(intent)

    # 3. 规划任务
    plan = planner.create_plan(intent, memories)

    # 4. 执行并观察
    for step in plan.steps:
        result = tool_executor.execute(step)
        observe(result)

        # 动态调整
        if needs_replan(result):
            plan = planner.replan(plan)

    # 5. 生成回复
    response = synthesize(plan.results)

    # 6. 更新记忆
    memory.add_exchange(user_input, response)

    output(response)
```

---

## 3. 阶段规划

### 阶段一：对话式 CLI 界面（MVP，2-3天）

**目标**：建立 REPL 交互模式，验证用户接受度

**功能**：
- 启动 Agent 模式：`python soundnovel.py agent`
- 自然语言指令解析（规则为主）
- 复用现有 CLI 命令逻辑
- 基础对话历史显示

**示例交互**：
```
$ python soundnovel.py agent

🤖 SoundNovel Agent 模式

你可以这样与我对话：
- "生成第5章"
- "查看人物张三的状态"
- "帮我规划接下来的3章"

> 生成第5章
Agent: 正在为您生成第5章...
✅ 第5章生成完成，字数：3200字，评分：85/100

> 张三现在在哪里？
Agent: 根据追踪记录，张三当前位于「青云宗」，状态为「修炼中」。
他最后一次出场是在第4章，当时正在...（详细上下文）
```

**新增文件**：
- `novel_generator/agent/__init__.py`
- `novel_generator/agent/cli_repl.py` - REPL 主循环
- `novel_generator/agent/intent_parser.py` - 基础意图解析
- `novel_generator/agent/simple_memory.py` - 简单对话记忆

**复用文件**：
- `novel_generator/cli/commands/*.py` - 现有命令逻辑

---

### 阶段二：Agent Loop + 工具系统（1-2周）

**目标**：建立完整的 Agent 架构和工具注册机制

#### 3.2.1 意图解析器（Intent Parser）

**位置**：`novel_generator/agent/intent_parser.py`

**设计**：

```python
@dataclass
class UserIntent:
    """用户意图数据结构"""
    action: str              # generate, modify, review, plan, query
    target_type: str         # chapter, character, outline, section
    target_id: Optional[str] # 具体ID（章节号、人物名）
    parameters: Dict         # 参数
    constraints: List[str]   # 约束条件
    raw_input: str           # 原始输入
    confidence: float        # 解析置信度

class IntentParser:
    """混合意图解析器：规则 + LLM"""

    def __init__(self):
        self.rules = self._load_rules()  # 正则规则
        self.llm_client = ...            # LLM 客户端

    async def parse(self, user_input: str) -> UserIntent:
        # 1. 尝试规则匹配（快速、确定）
        rule_result = self._try_rules(user_input)
        if rule_result.confidence > 0.9:
            return rule_result

        # 2. 使用 LLM 解析（灵活、智能）
        llm_result = await self._llm_parse(user_input)

        # 3. 合并结果
        return self._merge_results(rule_result, llm_result)
```

**规则示例**：
```python
RULES = [
    # 生成章节
    (r"生成第?(\d+)章", {"action": "generate", "target_type": "chapter"}),
    (r"写第?(\d+)章", {"action": "generate", "target_type": "chapter"}),

    # 修改章节
    (r"修改第?(\d+)章", {"action": "modify", "target_type": "chapter"}),
    (r"调整第?(\d+)章", {"action": "modify", "target_type": "chapter"}),

    # 查询人物
    (r"(.+?)现在(在哪|怎么样|状态)", {"action": "query", "target_type": "character"}),

    # 扩写
    (r"扩写第?(\d+)章", {"action": "expand", "target_type": "chapter"}),

    # 规划
    (r"规划", {"action": "plan", "target_type": "outline"}),
]
```

#### 3.2.2 任务规划器（Planner）

**位置**：`novel_generator/agent/planner.py`

**设计**：

```python
@dataclass
class PlanStep:
    """计划步骤"""
    step_id: str
    tool_name: str           # 使用哪个工具
    parameters: Dict         # 工具参数
    depends_on: List[str]    # 依赖的步骤
    requires_confirmation: bool  # 是否需要用户确认
    description: str         # 人类可读描述

@dataclass
class Plan:
    """执行计划"""
    plan_id: str
    intent: UserIntent
    steps: List[PlanStep]
    estimated_time: int      # 预估时间（秒）
    created_at: datetime

class TaskPlanner:
    """任务规划器"""

    def create_plan(self, intent: UserIntent, context: Context) -> Plan:
        """根据意图创建执行计划"""

        if intent.action == "generate" and intent.target_type == "chapter":
            return self._plan_chapter_generation(intent, context)

        elif intent.action == "modify":
            return self._plan_modification(intent, context)

        elif intent.action == "query":
            return self._plan_query(intent, context)

        # ... 其他意图

    def _plan_chapter_generation(self, intent, context) -> Plan:
        chapter_num = intent.target_id

        steps = []

        # 步骤1：检查前置条件
        steps.append(PlanStep(
            step_id="check_prereq",
            tool_name="check_prerequisites",
            parameters={"chapter_num": chapter_num},
            requires_confirmation=False,
            description=f"检查第{chapter_num}章的前置条件"
        ))

        # 步骤2：准备上下文
        steps.append(PlanStep(
            step_id="prepare_context",
            tool_name="get_writing_context",
            parameters={"chapter_num": chapter_num},
            depends_on=["check_prereq"],
            requires_confirmation=False,
            description="准备写作上下文"
        ))

        # 步骤3：生成章节
        steps.append(PlanStep(
            step_id="generate",
            tool_name="generate_chapter",
            parameters={
                "chapter_num": chapter_num,
                **intent.parameters
            },
            depends_on=["prepare_context"],
            requires_confirmation=True,  # 需要确认
            description=f"生成第{chapter_num}章内容"
        ))

        return Plan(
            plan_id=generate_id(),
            intent=intent,
            steps=steps,
            estimated_time=60  # 预估60秒
        )

    def replan(self, plan: Plan, results: List[StepResult]) -> Plan:
        """根据执行结果重新规划"""
        # 分析失败步骤，调整计划
        pass
```

#### 3.2.3 工具系统

**位置**：`novel_generator/agent/tools/`

**设计**：

```python
# novel_generator/agent/tools/base.py

@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any
    message: str
    execution_time: float
    metadata: Dict

class BaseTool(ABC):
    """工具基类"""

    name: str
    description: str
    parameters: Dict  # JSON Schema

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        pass

class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict]:
        """列出所有工具（用于 LLM function calling）"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
            for tool in self._tools.values()
        ]
```

**工具实现示例**：

```python
# novel_generator/agent/tools/generation.py

class GenerateChapterTool(BaseTool):
    """生成章节工具"""

    name = "generate_chapter"
    description = "生成指定章节的完整内容"
    parameters = {
        "type": "object",
        "properties": {
            "chapter_num": {
                "type": "integer",
                "description": "章节号"
            },
            "word_count": {
                "type": "integer",
                "description": "目标字数（可选）"
            },
            "style_hints": {
                "type": "string",
                "description": "风格提示（可选）"
            }
        },
        "required": ["chapter_num"]
    }

    def __init__(self, chapter_expander: ChapterExpander):
        self.expander = chapter_expander

    async def execute(self, chapter_num: int, **kwargs) -> ToolResult:
        try:
            # 调用现有 ChapterExpander
            content, state_card = await self.expander.expand_chapter(
                chapter_num=chapter_num,
                **kwargs
            )

            return ToolResult(
                success=True,
                data={
                    "chapter_num": chapter_num,
                    "content": content,
                    "word_count": len(content),
                    "state_card": state_card
                },
                message=f"第{chapter_num}章生成完成，共{len(content)}字",
                execution_time=0,  # 实际计时
                metadata={}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"生成失败：{str(e)}",
                execution_time=0,
                metadata={"error": str(e)}
            )
```

**工具清单**：

| 工具类别 | 工具名 | 功能 | 复用/新建 |
|---------|-------|------|----------|
| 生成 | `generate_chapter` | 生成章节 | 复用 ChapterExpander |
| 生成 | `expand_section` | 扩写段落 | 复用+扩展 |
| 生成 | `generate_outline` | 生成大纲 | 复用 OutlineGenerator |
| 修改 | `modify_chapter` | 修改章节 | 新建 |
| 修改 | `adjust_tone` | 调整语气 | 新建 |
| 修改 | `insert_content` | 插入内容 | 新建 |
| 修改 | `delete_section` | 删除段落 | 新建 |
| 分析 | `analyze_consistency` | 连续性分析 | 复用 Tracker |
| 分析 | `get_character_status` | 人物状态 | 复用 CharacterTracker |
| 分析 | `get_pending_foreshadowing` | 待回收伏笔 | 复用 ForeshadowingTracker |
| 规划 | `plan_arc` | 规划情节弧线 | 新建 |
| 项目 | `get_project_status` | 项目状态 | 复用 SessionManager |

#### 3.2.4 记忆系统

**位置**：`novel_generator/agent/memory/`

**设计**：

```python
# novel_generator/agent/memory/conversation.py

@dataclass
class DialogTurn:
    """对话轮次"""
    turn_id: str
    timestamp: datetime
    user_input: str
    agent_response: str
    intent: Optional[UserIntent]
    tools_used: List[str]
    execution_results: List[ToolResult]

class ConversationMemory:
    """对话记忆（短期）"""

    def __init__(self, max_turns: int = 50):
        self.turns: deque[DialogTurn] = deque(maxlen=max_turns)

    def add_turn(self, turn: DialogTurn):
        self.turns.append(turn)

    def get_recent(self, n: int = 10) -> List[DialogTurn]:
        """获取最近 n 轮对话"""
        return list(self.turns)[-n:]

    def retrieve(self, query: str, top_k: int = 3) -> List[DialogTurn]:
        """基于语义检索相关对话"""
        # 使用 embedding + 向量检索
        pass

    def summarize(self) -> str:
        """生成对话摘要"""
        pass
```

```python
# novel_generator/agent/memory/project.py

class ProjectMemory:
    """项目记忆（长期）"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.memory_file = self.project_root / "05_script" / "agent_memory.json"

        # 扩展现有追踪器
        self.character_memories = CharacterMemory()
        self.plot_memories = PlotMemory()
        self.revision_memories = RevisionMemory()
        self.user_preferences = UserPreferences()

    def load(self):
        """从文件加载记忆"""
        if self.memory_file.exists():
            data = json.loads(self.memory_file.read_text())
            # 解析并加载

    def save(self):
        """保存到文件"""
        data = {
            "character_memories": self.character_memories.to_dict(),
            "plot_memories": self.plot_memories.to_dict(),
            "revision_memories": self.revision_memories.to_dict(),
            "user_preferences": self.user_preferences.to_dict(),
            "last_updated": datetime.now().isoformat()
        }
        self.memory_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def summarize_for_writing(self, chapter_num: int, depth: str = "standard") -> str:
        """
        生成写作上下文摘要

        depth:
        - minimal: 仅关键人物和核心情节（适合续写）
        - standard: 包含情感弧线和待回收伏笔（默认）
        - comprehensive: 完整前文梗概（适合长间隔续写）
        """
        pass
```

---

### 阶段三：精细化编辑（2-3周）

**目标**：实现段落级编辑，而非整章重生成

#### 3.3.1 章节编辑器

**位置**：`novel_generator/agent/editor/chapter_editor.py`

**设计**：

```python
class SectionSelector:
    """章节段落选择器"""

    @staticmethod
    def paragraph(index: int) -> "SectionSelector":
        """选择第 n 段（从1开始）"""
        pass

    @staticmethod
    def range(start_marker: str, end_marker: str) -> "SectionSelector":
        """按内容标记选择范围"""
        pass

    @staticmethod
    def by_content(content_snippet: str, fuzzy: bool = True) -> "SectionSelector":
        """按内容片段选择（支持模糊匹配）"""
        pass

    @staticmethod
    def by_position(position: str) -> "SectionSelector":
        """
        按位置选择：
        - "开头" / "beginning"
        - "中间" / "middle"
        - "结尾" / "ending"
        - "第2段到第4段"
        """
        pass

class ChapterEditor:
    """章节编辑器"""

    def __init__(self, ai_role_manager: AIRoleManager):
        self.role_manager = ai_role_manager

    async def edit(
        self,
        chapter_num: int,
        selector: SectionSelector,
        instruction: str,
        preserve_context: bool = True
    ) -> EditResult:
        """
        编辑指定章节段落

        Args:
            chapter_num: 章节号
            selector: 段落选择器
            instruction: 编辑指令（自然语言）
            preserve_context: 是否保持与上下文的连贯性
        """
        # 1. 读取章节
        chapter_content = self._read_chapter(chapter_num)

        # 2. 定位目标段落
        target_section = selector.locate(chapter_content)

        # 3. 提取上下文
        before_context = target_section.get_before_context()
        after_context = target_section.get_after_context()

        # 4. 使用 LLM 进行编辑
        edited_section = await self._llm_edit(
            target_section=target_section,
            instruction=instruction,
            before_context=before_context,
            after_context=after_context
        )

        # 5. 检查一致性
        if preserve_context:
            consistency_check = await self._check_consistency(
                edited_section, before_context, after_context
            )
            if not consistency_check.passed:
                edited_section = await self._fix_consistency(
                    edited_section, consistency_check.issues
                )

        # 6. 合并回章节
        new_chapter = self._merge_edits(chapter_content, target_section, edited_section)

        # 7. 保存
        self._save_chapter(chapter_num, new_chapter)

        return EditResult(
            chapter_num=chapter_num,
            original_section=target_section,
            edited_section=edited_section,
            changes_summary=...,
            word_count_change=...
        )

    async def expand(
        self,
        chapter_num: int,
        selector: SectionSelector,
        target_length: Optional[int] = None,
        direction: str = "auto"  # auto/before/after/both
    ) -> ExpandResult:
        """扩写指定段落"""
        pass

    async def delete(
        self,
        chapter_num: int,
        selector: SectionSelector,
        justification: str
    ) -> DeleteResult:
        """
        删除指定段落

        注意：删除前会检查对后续章节的影响
        """
        # 检查伏笔、人物状态等是否受影响
        impact_analysis = self._analyze_deletion_impact(chapter_num, selector)

        if impact_analysis.has_critical_impact:
            return DeleteResult(
                success=False,
                warning=impact_analysis.warning_message
            )

        # 执行删除
        pass

    async def insert(
        self,
        chapter_num: int,
        position: InsertPosition,
        content_description: str
    ) -> InsertResult:
        """在指定位置插入新内容"""
        pass
```

#### 3.3.2 编辑示例

```python
# 使用示例

# 修改第3章第2段，让主角更愤怒
result = await editor.edit(
    chapter_num=3,
    selector=SectionSelector.paragraph(2),
    instruction="让主角的语气更愤怒，增加内心独白的愤怒情绪",
    preserve_context=True
)

# 扩写第5章结尾，增加500字
result = await editor.expand(
    chapter_num=5,
    selector=SectionSelector.by_position("结尾"),
    target_length=500
)

# 删除第4章第3段（如果它无关紧要）
result = await editor.delete(
    chapter_num=4,
    selector=SectionSelector.by_content("张三打了个哈欠"),
    justification="这个细节对情节无贡献，且破坏紧张氛围"
)
```

---

### 阶段四：增强上下文管理（与阶段三并行）

**目标**：Agent 可主动查询上下文，智能注入

#### 3.4.1 上下文查询系统

**位置**：`novel_generator/agent/context/query.py`

**设计**：

```python
class ContextQueryEngine:
    """上下文查询引擎"""

    def __init__(
        self,
        character_tracker: CharacterTracker,
        foreshadowing_tracker: ForeshadowingTracker,
        emotional_tracker: EmotionalArcTracker
    ):
        self.character_tracker = character_tracker
        self.foreshadowing_tracker = foreshadowing_tracker
        self.emotional_tracker = emotional_tracker

        # 章节内容索引（用于语义检索）
        self.chapter_index = ChapterIndex()

    def query(self, query: str, chapter_scope: Optional[range] = None) -> QueryResult:
        """
        自然语言查询项目上下文

        支持查询：
        - "张三现在的状态"
        - "第10章埋下了哪些伏笔"
        - "主角的情感变化轨迹"
        - "第5章到第10章的关键事件"
        - "谁在第3章出场了"
        """
        # 解析查询意图
        query_type = self._classify_query(query)

        if query_type == "character_status":
            return self._query_character_status(query)

        elif query_type == "foreshadowing":
            return self._query_foreshadowing(query)

        elif query_type == "plot_summary":
            return self._query_plot_summary(query, chapter_scope)

        elif query_type == "emotional_arc":
            return self._query_emotional_arc(query)

        # ... 更多查询类型

    def _query_character_status(self, query: str) -> CharacterStatusResult:
        """查询人物状态"""
        # 从 query 中提取人物名
        character_name = self._extract_character_name(query)

        # 从 tracker 获取状态
        status = self.character_tracker.get_character_status(character_name)

        # 生成人类可读回复
        return CharacterStatusResult(
            character=character_name,
            status=status,
            narrative_summary=self._generate_status_summary(status)
        )

    def generate_writing_brief(self, chapter_num: int) -> WritingBrief:
        """
        生成写作简报（Agent 用于准备生成上下文）

        包含：
        - 前文梗概（按重要性分级）
        - 相关人物当前状态
        - 待回收伏笔清单
        - 情感节奏建议
        - 潜在冲突点
        """
        brief = WritingBrief()

        # 前文梗概
        brief.previous_summary = self._summarize_previous_chapters(chapter_num)

        # 人物状态
        brief.character_contexts = self.character_tracker.get_context_for_chapter(chapter_num)

        # 伏笔
        brief.foreshadowing_context = self.foreshadowing_tracker.get_context_for_chapter(chapter_num)

        # 情感弧线
        brief.emotional_context = self.emotional_tracker.get_context_for_chapter(chapter_num)

        # 潜在冲突（通过分析大纲和前文推断）
        brief.suggested_conflicts = self._infer_potential_conflicts(chapter_num)

        return brief
```

---

### 阶段五：多 Agent 协作（可选，高级特性）

**目标**：多个专业 Agent 协作完成复杂任务

#### 3.5.1 架构设计

```python
class AgentOrchestrator:
    """Agent 编排器"""

    def __init__(self):
        self.agents = {
            "writer": WriterAgent(),
            "editor": EditorAgent(),
            "critic": CriticAgent(),
            "planner": PlannerAgent(),
            "researcher": ResearcherAgent(),
        }
        self.message_bus = MessageBus()

    async def collaborative_write(
        self,
        task: WritingTask,
        workflow: str = "standard"
    ) -> WritingResult:
        """
        多 Agent 协作写作

        workflow:
        - standard: Planner → Writer → Critic → Editor（顺序）
        - debate: Writer vs Critic 多轮讨论
        - parallel: 多个 Writer 生成不同版本，择优
        """

        if workflow == "standard":
            return await self._standard_workflow(task)

        elif workflow == "debate":
            return await self._debate_workflow(task)

        elif workflow == "parallel":
            return await self._parallel_workflow(task)

    async def _standard_workflow(self, task: WritingTask) -> WritingResult:
        # 1. Planner 规划
        plan = await self.agents["planner"].plan(task)

        # 2. Writer 生成
        draft = await self.agents["writer"].write(plan)

        # 3. Critic 评审
        critique = await self.agents["critic"].review(draft)

        # 4. 如果需要修改
        if critique.score < 80:
            draft = await self.agents["writer"].revise(draft, critique)

        # 5. Editor 润色
        final = await self.agents["editor"].polish(draft)

        return WritingResult(content=final, process_log=...)
```

---

## 4. 文件结构规划

### 4.1 新增文件

```
novel_generator/
└── agent/
    ├── __init__.py
    ├── agent_loop.py              # Agent 核心循环
    ├── cli_repl.py                # REPL 界面
    │
    ├── intent/
    │   ├── __init__.py
    │   ├── parser.py              # 意图解析器
    │   ├── rules.py               # 规则定义
    │   └── llm_parser.py          # LLM 解析
    │
    ├── planner/
    │   ├── __init__.py
    │   ├── planner.py             # 任务规划器
    │   ├── strategies.py          # 规划策略
    │   └── templates.py           # 计划模板
    │
    ├── memory/
    │   ├── __init__.py
    │   ├── conversation.py        # 对话记忆
    │   ├── project.py             # 项目记忆
    │   ├── character_memory.py    # 人物记忆扩展
    │   └── embedding.py           # 向量嵌入
    │
    ├── tools/
    │   ├── __init__.py
    │   ├── base.py                # 工具基类
    │   ├── registry.py            # 工具注册表
    │   ├── generation.py          # 生成工具
    │   ├── modification.py        # 修改工具
    │   ├── analysis.py            # 分析工具
    │   └── planning.py            # 规划工具
    │
    ├── context/
    │   ├── __init__.py
    │   ├── query.py               # 上下文查询
    │   ├── brief.py               # 简报生成
    │   └── index.py               # 章节索引
    │
    └── editor/
        ├── __init__.py
        ├── chapter_editor.py      # 章节编辑器
        ├── selector.py            # 段落选择器
        └── consistency.py         # 一致性检查
```

### 4.2 修改文件

```
soundnovel.py                    # 新增 agent 子命令
novel_generator/cli/main.py      # 新增 agent 命令入口
novel_generator/config/session.py # 扩展存储 agent_memory
```

### 4.3 复用文件

| 现有文件 | 复用方式 |
|---------|---------|
| `novel_generator/core/chapter_expander.py` | 封装为 `generate_chapter` 工具 |
| `novel_generator/core/ai_roles.py` | Agent 内部使用，新增 PLANNER 角色 |
| `novel_generator/utils/multi_model_client.py` | 直接复用 |
| `novel_generator/utils/prompt_manager.py` | 复用，新增 Agent 专用提示词 |
| `novel_generator/core/character_tracker.py` | 扩展为记忆系统组件 |
| `novel_generator/core/foreshadowing_tracker.py` | 扩展为记忆系统组件 |
| `novel_generator/core/emotional_arc_tracker.py` | 扩展为记忆系统组件 |
| `novel_generator/config/session.py` | 复用，增加 agent_memory 字段 |

---

## 5. 交互示例

### 5.1 完整对话示例

```
$ python soundnovel.py agent

🤖 SoundNovel Agent 模式 v1.0
当前项目：《青云志》
已完成：12/100 章

> 帮我生成第13章

Agent: 📋 正在规划任务...

计划如下：
1. 检查前置条件
2. 准备写作上下文（前3章概要、人物状态、待回收伏笔）
3. 生成第13章内容（预计60秒）

是否确认执行？ [Y/n]

> Y

Agent: ✅ 前置检查通过
       📚 上下文准备完成
          - 前文概要：第12章张三与...（展开详情）
          - 关键人物：张三（修炼中）、李四（追查线索）
          - 待回收伏笔：神秘玉佩（第5章埋下，计划第15章回收）
       ✍️ 正在生成...

[进度条] ████████████████████ 100%

✅ 第13章生成完成！
   字数：3,240 字
   评分：87/100
   通过评审，无需润色

   📄 文件：03_draft/第0013章.txt

   本章概要：
   张三在修炼中突破境界，察觉到神秘玉佩的异常波动，
   决定前往禁地调查...（AI生成的概要）

> 张三的突破有点突兀，帮我在前面加一段铺垫

Agent: 📝 正在分析第13章...
       定位到境界突破段落（第3段）
       准备在前文增加铺垫内容

       建议添加：
       - 张三修炼遇到瓶颈的内心描写
       - 神秘玉佩散发微光的伏笔
       - 突破前的征兆暗示

       是否确认修改？ [Y/n]

> Y

Agent: ✏️ 正在修改...
       ✅ 在第3段前插入约300字铺垫
       主要修改：
       1. 增加修炼瓶颈的心理描写
       2. 玉佩散发微光的细节
       3. 天地灵气汇聚的征兆

       修改后字数：3,540 字
       是否需要重新评审？ [Y/n]

> n

> 查看李四现在的状态

Agent: 🔍 正在查询人物状态...

李四（配角）
━━━━━━━━━━━━━━━━━━━━
📍 当前位置：追查线索途中，接近禁地外围
💭 心理状态：焦虑、执着
🎯 当前目标：查清师父失踪真相
👥 关键关系：
   - 张三：师兄弟，关系微妙
   - 神秘人：追踪目标
📜 最近出场：第12章
🔮 预测走向：可能与张三在禁地相遇

> 第5章埋下的神秘玉佩伏笔，现在回收了吗？

Agent: 🔍 查询伏笔状态...

神秘玉佩（第5章）
━━━━━━━━━━━━━━━━━━━━
📖 埋设：第5章，从遗迹中获得
📅 计划回收：第15章（预计）
✅ 已提及：
   - 第5章：初次获得
   - 第13章：散发微光（本章）
⏳ 待回收：核心秘密揭晓
⚠️  提醒：建议在14-15章内完成回收，
          避免读者遗忘

> 帮我扩写第13章结尾，增加悬念

Agent: 📝 准备扩写结尾段落...
       当前结尾字数：约200字
       建议扩写至：约500字
       扩写方向：增加悬念、铺垫下一章冲突

       是否执行？ [Y/n]

> Y

Agent: ✍️ 正在扩写...
       ✅ 结尾扩写完成！
       新增约350字，主要增加：
       - 玉佩突然剧烈震动
       - 禁地深处传来异响
       - 张三面临抉择：继续追查 / 撤退求援

> exit

Agent: 👋 再见！已自动保存对话历史和项目状态。
       提示：使用 `python soundnovel.py agent` 继续对话
```

---

## 6. 实施建议

### 6.1 推荐实施路径

```
Week 1: 阶段一（MVP验证）
  Day 1-2: REPL 界面 + 基础意图解析
  Day 3: 复用现有命令，集成测试

Week 2-3: 阶段二（核心架构）
  Week 2: Agent Loop + 工具系统
  Week 3: 意图解析器 + 规划器 + 记忆系统

Week 4-6: 阶段三（精细化编辑）
  Week 4: 章节编辑器基础
  Week 5: 段落选择器 + 编辑工具
  Week 6: 一致性检查 + 集成测试

Week 7-8: 阶段四（上下文管理）
  Week 7: 上下文查询系统
  Week 8: 简报生成 + 智能注入

Week 9+: 阶段五（多Agent，可选）
  根据用户反馈决定是否投入
```

### 6.2 技术选型建议

| 组件 | 建议 | 理由 |
|-----|------|------|
| Agent 框架 | 自建轻量框架 | 现有代码完整，避免引入 LangChain 等重型框架的复杂度 |
| 意图解析 | 规则 + LLM 混合 | 简单指令快速响应，复杂指令灵活处理 |
| 记忆存储 | JSON 文件 + 内存 | 与现有 session.json 保持一致，简单可靠 |
| 向量检索 | 可选 faiss/chroma | 如果对话历史检索有性能需求再引入 |
| 异步框架 | asyncio | Python 原生，与现有 async 代码兼容 |

### 6.3 风险提示与应对

| 风险 | 概率 | 影响 | 应对策略 |
|-----|------|------|---------|
| LLM 意图解析不稳定 | 中 | 高 | 规则兜底 + 用户确认机制 |
| 上下文过长导致性能下降 | 中 | 中 | 分层摘要 + 动态检索 |
| 局部修改破坏全局一致性 | 高 | 高 | 自动检查 + 用户确认 + 影响分析 |
| 架构复杂度失控 | 中 | 高 | 分阶段交付，每阶段验证用户价值 |
| 用户体验不达预期 | 低 | 高 | 尽早发布 MVP 收集反馈 |

---

## 7. 成功指标

### 7.1 技术指标

- 意图解析准确率 > 80%（Top-1）
- 工具调用成功率 > 95%
- 平均响应时间 < 3秒（不含 LLM 生成时间）
- 代码覆盖率 > 70%

### 7.2 用户体验指标

- 用户完成一次生成任务的操作次数 < 5次（对比现有 CLI 的 3次）
- 用户满意度评分 > 4/5
- 对话式任务完成率 > 90%
- 用户主动使用 Agent 模式的比例 > 50%

---

## 8. 附录

### 8.1 新增命令参考

```bash
# 启动 Agent REPL 模式
python soundnovel.py agent

# 可选参数
python soundnovel.py agent --project /path/to/project
python soundnovel.py agent --resume  # 恢复上次对话

# 传统 CLI 仍保留
python soundnovel.py cli init
python soundnovel.py cli expand --chapter 1
```

### 8.2 配置文件扩展

```json
// 05_script/session.json 新增字段
{
  "agent_memory": {
    "conversation_history": [...],
    "user_preferences": {
      "default_tone": "serious",
      "auto_confirm_threshold": 0.9
    },
    "last_dialog_id": "xxx"
  }
}
```

---

## 9. 总结

本方案提出将 SoundNovel 从**批量生成工具**演进为**对话式 AI Agent** 的完整路线图：

1. **渐进式演进**：分 4-5 个阶段逐步交付，降低风险
2. **复用现有架构**：充分利用三角色流程、追踪器、配置系统
3. **用户价值优先**：MVP 快速验证，根据反馈调整
4. **技术务实**：自建轻量框架，避免过度工程

核心创新点：
- **Agent Loop**：理解-规划-执行-观察循环
- **精细化编辑**：段落级修改，非整章重生成
- **主动上下文**：Agent 可查询，智能注入
- **持久化记忆**：跨会话保持对话历史和项目状态
