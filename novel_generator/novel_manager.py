"""
小说资源管理器
负责多小说项目的创建、管理和切换
"""

import json
import os
import uuid
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class NovelProject:
    """单个小说项目"""

    def __init__(self, novel_dir: Path):
        self.novel_dir = Path(novel_dir).resolve()
        self.config_dir = self.novel_dir / "config"
        self.source_dir = self.novel_dir / "source"
        self.outline_dir = self.novel_dir / "outline"
        self.draft_dir = self.novel_dir / "draft"
        self.logs_dir = self.novel_dir / "logs"
        self.prompts_dir = self.novel_dir / "prompts"

    @property
    def novel_id(self) -> str:
        """从小说目录名获取novel_id"""
        return self.novel_dir.name

    def initialize(self, name: str, description: str = "", api_config_ref: str = "") -> bool:
        """初始化小说目录结构"""
        try:
            # 创建目录结构
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self.source_dir.mkdir(parents=True, exist_ok=True)
            self.outline_dir.mkdir(parents=True, exist_ok=True)
            self.draft_dir.mkdir(parents=True, exist_ok=True)
            self.logs_dir.mkdir(parents=True, exist_ok=True)

            # 创建子目录
            (self.logs_dir / "ai_api_logs").mkdir(exist_ok=True)
            (self.logs_dir / "system_logs").mkdir(exist_ok=True)

            # 初始化 novel.json (元数据)
            novel_config = {
                "novel_id": self.novel_id,
                "name": name,
                "description": description,
                "api_config_ref": api_config_ref,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            self.save_config(novel_config)

            # 初始化 generation.json (生成参数)
            generation_config = {
                "context_chapters": 10,
                "default_word_count": 1500,
                "outline_window": 30,
                "draft_window": 10,
                # 滑动窗口多轮配置（完全替换原有batch模式）
                "conversation_window": 100,  # 对话窗口大小（章节数）
                "skeleton_batch_size": 10,   # 每批生成章节数
                "enable_act_plan_injection": True,  # 是否动态注入幕规划
                "save_conversation_checkpoints": True,  # 是否保存检查点
                "max_conversation_tokens": 800000,  # 单对话最大token数（触发修剪）
            }
            self._save_json(self.config_dir / "generation.json", generation_config)

            # 初始化 state.json (状态)
            state_config = {
                "total_chapters": 0,
                "last_outline_chapter": 0,
                "last_draft_chapter": 0,
                "outline_file": "",
                "last_session_at": "",
                "chapter_states": {},
            }
            self._save_json(self.config_dir / "state.json", state_config)

            # 创建 prompts 目录并复制系统 prompts
            self._init_prompts()

            # 生成模板文件
            self._generate_template_files()

            return True
        except Exception as e:
            raise Exception(f"初始化小说项目失败: {e}")

    def _generate_template_files(self):
        """生成模板文件"""
        # 核心设定模板
        core_setting_template = """# 核心设定模板
# 请根据您的小说创作需求填写以下内容

世界观:
  # 【请填写】故事背景、世界规则等
  # 例如：这是一个修仙世界，灵气复苏，人人可修炼，但修炼资源稀缺...

核心冲突:
  # 【请填写】主线矛盾、核心目标
  # 例如：主角需要寻找传说中的神器来拯救即将毁灭的世界，但各大势力都在争夺...

人物小传:
  主角:
    # 【请填写】姓名、身份、性格、核心动机
    # 姓名：
    # 身份：
    # 性格：
    # 核心动机：

  配角1:
    # 【请填写】姓名、身份、性格、核心动机
    # 姓名：
    # 身份：
    # 性格：
    # 核心动机：

  配角2:
    # 【请填写】姓名、身份、性格、核心动机
    # 姓名：
    # 身份：
    # 性格：
    # 核心动机：

伏笔清单:
  # 【请填写】重要伏笔及其计划回收章节
  # - 伏笔1: [描述+计划回收章节]
  # - 伏笔2: [描述+计划回收章节]
  # - 伏笔3: [描述+计划回收章节]

# 补充设定（可选）
# 可以添加其他您认为重要的设定信息
"""

        core_setting_path = self.source_dir / "core_setting.yaml"
        with open(core_setting_path, "w", encoding="utf-8") as f:
            f.write(core_setting_template)

        # 整体大纲模板
        overall_outline_template = """# 整体大纲模板
# 请根据您的小说创作需求填写以下内容

第一幕:
  # 【请填写】章节范围+核心剧情
  # 例如：第1-15章，主角踏入江湖，初露锋芒

第二幕:
  # 【请填写】章节范围+核心剧情
  # 例如：第16-40章，揭秘阴谋，势力角逐

第三幕:
  # 【请填写】章节范围+核心剧情
  # 例如：第41-60章，最终对决，尘埃落定

关键转折点:
  # 【请填写】重要转折点及其章节
  # - 第X章: [具体事件，如"主角发现父亲秘密"]
  # - 第Y章: [具体事件，如"重要角色牺牲"]
  # - 第Z章: [具体事件，如"真相大白"]

# 章节规划（可选）
# 可以添加更详细的章节规划
# 第一章: [开篇介绍，主角背景]
# 第二章: [事件发生，主角行动]
# ...

# 故事主题（可选）
# 主题：
# 核心思想：
"""

        overall_outline_path = self.source_dir / "overall_outline.yaml"
        with open(overall_outline_path, "w", encoding="utf-8") as f:
            f.write(overall_outline_template)

    def _init_prompts(self):
        """初始化 prompts 目录，使用硬编码通用模板"""
        self.prompts_dir.mkdir(parents=True, exist_ok=True)

        # 创建 satisfaction_prompts 子目录
        satisfaction_dir = self.prompts_dir / "satisfaction_prompts"
        satisfaction_dir.mkdir(exist_ok=True)

        # 定义所有 prompts 模板
        prompts_templates = {
            "system_prompts.yaml": self._get_system_prompts_template(),
            "style_guide.yaml": self._get_style_guide_template(),
            "generation_prompts.yaml": self._get_generation_prompts_template(),
            "outline_generation.yaml": self._get_outline_generation_template(),
            "satisfaction_prompts/face_slap.yaml": self._get_face_slap_template(),
            "satisfaction_prompts/power_up.yaml": self._get_power_up_template(),
        }

        for filepath, content in prompts_templates.items():
            full_path = self.prompts_dir / filepath
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

    def _get_system_prompts_template(self) -> str:
        """系统提示词模板"""
        return '''# 系统提示词配置
# 用于定义AI角色的核心职责和行为准则

generator:
  name: "生成者"
  description: "负责小说内容创作"
  core_rules:
    - "展示而非讲述：用具体动作、神态、对话展现情绪"
    - "细节落地：每段描写都要有具体感官细节"
    - "禁止重复前文：前文已发生的剧情绝对不能重复写"
    - "剧情推进：每章必须有新的情节发展"
  banned_words:
    - "复杂的思绪"
    - "难以言喻"
    - "命运的齿轮"
    - "一种莫名的"
    - "心中五味杂陈"
  template: |
    你是一个专业的网络小说作家，擅长根据大纲创作引人入胜的章节内容。

    核心写作原则：
    1. 展示而非讲述：用具体动作、神态、对话展现人物情绪，避免"他感到..."等直接陈述
    2. 细节落地：每段描写都要有具体的感官细节，避免空洞的概括
    3. 剧情推进：每章必须有新的情节发展，不能重复前文已发生的内容
    4. 节奏把控：张弛有度，动作场景简洁有力，情感场景细腻动人

    禁忌词汇（绝对不可使用）：
    - "复杂的思绪"、"难以言喻"、"命运的齿轮"
    - "一种莫名的"、"心中五味杂陈"
    - "仿佛"、"似乎"、"这一刻"（减少使用）
'''

    def _get_style_guide_template(self) -> str:
        """风格指导模板（通用版本，需根据具体小说修改）"""
        return '''# 风格指导模板
# 用于指导AI生成内容的风格和特点
# 【重要】请根据你的小说类型修改以下内容

语言风格:
  # 【请填写】例如：语言风格华丽，具有张力，善于运用侧面描写调动读者情绪
  # 请描述你想要的语言风格特点

对话特点:
  # 【请填写】例如：严格贴合人物身份、性格设定
  # 主角对话风格如何？配角对话风格如何？

场景描写:
  # 【请填写】例如：大场景如何描写？小场景如何描写？
  # 动静结合方式？氛围营造方式？

节奏控制:
  # 【请填写】例如：开篇快节奏切入？中期如何铺垫？高潮如何处理？
  # 过渡段落如何处理？

心理描写:
  # 【请填写】例如：主角心理描写克制精准？配角通过行为侧面展现？
  # 内心独白和侧面描写的平衡？

禁忌:
  # 【请填写】你的小说需要避免的内容
  # 例如：
  # - 禁止战力崩坏、越级强杀
  # - 禁止人物OOC
  # - 禁止冗余水字数描写
  # - 禁止后宫、情爱相关剧情（如无女主设定）

补充说明:
  # 【请填写】其他需要AI注意的写作要求
'''

    def _get_generation_prompts_template(self) -> str:
        """章节生成提示词模板"""
        return '''# 章节生成提示词配置
# 用于指导AI生成章节内容

template: |
  【任务】撰写小说第{chapter_num}章正文

  1. 核心设定：
  {core_setting}

  2. 前文剧情全文（已发生，不可重复）：
  {previous_context}

  ⚠️ 以上是第{chapter_num}章之前已经发生的剧情，绝对不能重复！

  3. 本章大纲：
  {chapter_outline}

  4. {character_context}

  5. {foreshadowing_context}

  6. {emotional_context}

  7. 风格要求：
  {style_guide}

  【写作法则】
  1. 禁止重复前文：前文剧情已经发生，本章必须是全新剧情推进
  2. 展示而非讲述：用具体动作代替情绪标签
  3. 结尾落地：结尾必须落在具体感官细节上，禁止总结、升华
  4. 字数要求：{word_count}字左右（误差不超过±100字）

  请直接输出章节正文内容，不要添加任何解释或标记。

writing_rules:
  - "展示而非讲述"
  - "细节落地"
  - "剧情推进"
  - "节奏把控"
'''

    def _get_outline_generation_template(self) -> str:
        """大纲生成提示词模板"""
        return '''# 大纲生成提示词配置
# 用于指导AI生成章节大纲

act_plan_prompt: |
  【任务】基于以下设定，生成小说幕级规划

  世界观与核心设定：
  {core_setting}

  整体故事结构：
  {overall_outline}

  请生成{total_chapters}章小说的幕级规划，包括：
  - 每一幕的章节范围
  - 每一幕的核心冲突和目标
  - 幕与幕之间的转折关系

chapter_skeleton_prompt: |
  【任务】基于幕级规划，生成章节骨架

  幕级规划：
  {act_plan}

  需要生成的章节范围：第{start_chapter}章 到 第{end_chapter}章

  每章骨架应包含：
  - 章节定位
  - 核心事件
  - 与前章的因果关系
  - 场景概览
  - 角色行动
  - 伏笔处理
  - 情绪曲线
  - 结尾卡点
  - 爽点节奏
'''

    def _get_face_slap_template(self) -> str:
        """打脸爽点提示词模板"""
        return '''# 打脸爽点提示词
# 用于指导AI创作打脸场景

principles:
  - "铺垫充分：反派必须足够嚣张，让读者产生强烈反感"
  - "时机精准：主角反击必须在最合适的时机"
  - "反差巨大：前后对比要强烈，形成巨大落差"
  - "细节具体：打脸过程要有具体动作和对话"
  - "围观反应：要有旁观者的反应来烘托效果"

template: |
  【打脸场景创作指南】

  当前场景需要创作打脸剧情：
  - 反派：{antagonist}
  - 主角当前状态：{protagonist_state}
  - 打脸方式：{method}

  创作要点：
  1. 先充分展现反派的嚣张和轻视
  2. 主角反击要干脆利落
  3. 反派被打脸后的震惊和不可置信
  4. 围观者的反应和议论
  5. 主角的淡然或霸气回应

  注意：
  - 避免主角主动挑衅
  - 避免圣母式原谅
  - 反派被打脸后不能马上反击成功
'''

    def _get_power_up_template(self) -> str:
        """升级爽点提示词模板"""
        return '''# 升级爽点提示词
# 用于指导AI创作突破升级场景

principles:
  - "困难充分：升级前必须有足够的积累和压力"
  - "过程详细：突破过程要描写具体感受"
  - "异象衬托：升级时要有天地异象或特殊征兆"
  - "对比强烈：与升级前形成鲜明对比"
  - "他人震惊：要有旁观者见证和震惊"

template: |
  【升级场景创作指南】

  当前场景需要创作突破升级剧情：
  - 主角当前境界：{current_level}
  - 目标境界：{target_level}
  - 突破契机：{trigger}

  创作要点：
  1. 升级前的瓶颈和困境描写
  2. 突破契机到来时的感悟
  3. 突破过程的具体感受（能量流动、身体变化等）
  4. 天地异象或特殊征兆
  5. 突破后的力量感对比
  6. 他人见证后的震惊反应

  注意：
  - 避免毫无铺垫突然突破
  - 避免升级过于轻松
  - 升级后要立即展现新能力
'''

    def load_config(self) -> Dict:
        """加载novel.json"""
        config_path = self.config_dir / "novel.json"
        return self._load_json(config_path)

    def save_config(self, config: Dict) -> bool:
        """保存novel.json"""
        config_path = self.config_dir / "novel.json"
        config["updated_at"] = datetime.now().isoformat()
        return self._save_json(config_path, config)

    def load_state(self) -> Dict:
        """加载state.json"""
        state_path = self.config_dir / "state.json"
        return self._load_json(state_path)

    def save_state(self, state: Dict) -> bool:
        """保存state.json"""
        state_path = self.config_dir / "state.json"
        return self._save_json(state_path, state)

    def load_generation_config(self) -> Dict:
        """加载generation.json"""
        gen_path = self.config_dir / "generation.json"
        return self._load_json(gen_path)

    def save_generation_config(self, config: Dict) -> bool:
        """保存generation.json"""
        gen_path = self.config_dir / "generation.json"
        return self._save_json(gen_path, config)

    def _load_json(self, file_path: Path) -> Dict[str, Any]:
        """加载JSON文件"""
        if not file_path.exists():
            return {}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
                return data
        except Exception as e:
            raise Exception(f"读取JSON文件失败 {file_path}: {e}")

    def _save_json(self, file_path: Path, data: Dict) -> bool:
        """保存JSON文件"""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            raise Exception(f"保存JSON文件失败 {file_path}: {e}")

    def get_paths(self) -> Dict[str, Path]:
        """获取所有路径"""
        return {
            "novel_dir": self.novel_dir,
            "config_dir": self.config_dir,
            "source_dir": self.source_dir,
            "outline_dir": self.outline_dir,
            "draft_dir": self.draft_dir,
            "logs_dir": self.logs_dir,
            "prompts_dir": self.prompts_dir,
            "core_setting": self.source_dir / "core_setting.yaml",
            "overall_outline": self.source_dir / "overall_outline.yaml",
            "system_prompts": self.prompts_dir / "system_prompts.yaml",
            "style_guide": self.prompts_dir / "style_guide.yaml",
            "generation_prompts": self.prompts_dir / "generation_prompts.yaml",
            "outline_generation": self.prompts_dir / "outline_generation.yaml",
            "novel_config": self.config_dir / "novel.json",
            "generation_config": self.config_dir / "generation.json",
            "state_file": self.config_dir / "state.json",
        }

    def exists(self) -> bool:
        """检查小说项目是否存在"""
        return self.novel_dir.exists() and self.config_dir.exists()

    def is_valid(self) -> bool:
        """检查小说项目是否有效（包含必要的文件）"""
        required_files = [
            self.config_dir / "novel.json",
            self.config_dir / "generation.json",
            self.config_dir / "state.json",
        ]
        return all(f.exists() for f in required_files)

    def get_info(self) -> Dict[str, Any]:
        """获取小说项目信息"""
        config = self.load_config()
        state = self.load_state()

        return {
            "novel_id": self.novel_id,
            "name": config.get("name", "未命名"),
            "description": config.get("description", ""),
            "created_at": config.get("created_at", ""),
            "updated_at": config.get("updated_at", ""),
            "total_chapters": state.get("total_chapters", 0),
            "last_draft_chapter": state.get("last_draft_chapter", 0),
            "api_config_ref": config.get("api_config_ref", ""),
        }


class NovelManager:
    """小说资源管理器"""

    CURRENT_FILE = ".current"

    def __init__(self, novels_dir: str = "novels"):
        self.novels_dir = Path(novels_dir).resolve()
        self._ensure_novels_dir()

    def _ensure_novels_dir(self):
        """确保 novels 目录存在"""
        self.novels_dir.mkdir(parents=True, exist_ok=True)

    def _generate_novel_id(self, name: str) -> str:
        """生成小说ID"""
        # 使用时间戳 + UUID 的前8位，确保唯一性
        timestamp = datetime.now().strftime("%Y%m%d")
        short_uuid = uuid.uuid4().hex[:8]

        # 尝试从名称生成slug
        import re

        # 移除非字母数字字符，保留中文
        slug = re.sub(r'[^\w一-鿿]+', '-', name).strip('-')
        if len(slug) > 20:
            slug = slug[:20]

        if slug:
            return f"{slug}-{timestamp}-{short_uuid}"
        else:
            return f"novel-{timestamp}-{short_uuid}"

    def list_novels(self) -> List[Dict[str, Any]]:
        """列出所有小说"""
        novels: List[Dict[str, Any]] = []

        if not self.novels_dir.exists():
            return novels

        for item in self.novels_dir.iterdir():
            if item.is_dir():
                project = NovelProject(item)
                if project.is_valid():
                    novels.append(project.get_info())

        # 按创建时间排序
        novels.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return novels

    def create_novel(
        self, name: str, description: str = "", api_config_ref: str = ""
    ) -> str:
        """创建新小说，返回novel_id"""
        # 生成novel_id
        novel_id = self._generate_novel_id(name)

        # 创建小说目录
        novel_dir = self.novels_dir / novel_id
        if novel_dir.exists():
            # 如果目录已存在，生成新的ID
            novel_id = f"{novel_id}-{uuid.uuid4().hex[:4]}"
            novel_dir = self.novels_dir / novel_id

        # 初始化小说项目
        project = NovelProject(novel_dir)
        project.initialize(name, description, api_config_ref)

        return novel_id

    def delete_novel(self, novel_id: str) -> bool:
        """删除小说"""
        novel_dir = self.novels_dir / novel_id

        if not novel_dir.exists():
            return False

        try:
            shutil.rmtree(novel_dir)

            # 如果删除的是当前活跃小说，清除当前标记
            current_id = self.get_current_novel_id()
            if current_id == novel_id:
                self._clear_current_novel()

            return True
        except Exception as e:
            raise Exception(f"删除小说失败: {e}")

    def rename_novel(self, novel_id: str, new_name: str) -> bool:
        """重命名小说"""
        project = self.get_novel(novel_id)
        if not project or not project.exists():
            return False

        try:
            config = project.load_config()
            config["name"] = new_name
            project.save_config(config)
            return True
        except Exception as e:
            raise Exception(f"重命名小说失败: {e}")

    def get_novel(self, novel_id: str) -> Optional[NovelProject]:
        """获取小说项目"""
        novel_dir = self.novels_dir / novel_id

        if not novel_dir.exists():
            return None

        return NovelProject(novel_dir)

    def get_current_novel_id(self) -> Optional[str]:
        """获取当前活跃小说ID"""
        current_file = self.novels_dir / self.CURRENT_FILE

        if not current_file.exists():
            return None

        try:
            with open(current_file, "r", encoding="utf-8") as f:
                novel_id = f.read().strip()

            # 验证novel_id是否有效
            if novel_id and (self.novels_dir / novel_id).exists():
                return novel_id
            return None
        except Exception:
            return None

    def set_current_novel(self, novel_id: str) -> bool:
        """设置当前活跃小说"""
        # 验证小说是否存在
        project = self.get_novel(novel_id)
        if not project or not project.exists():
            return False

        try:
            current_file = self.novels_dir / self.CURRENT_FILE
            with open(current_file, "w", encoding="utf-8") as f:
                f.write(novel_id)
            return True
        except Exception as e:
            raise Exception(f"设置当前小说失败: {e}")

    def _clear_current_novel(self):
        """清除当前活跃小说标记"""
        current_file = self.novels_dir / self.CURRENT_FILE
        if current_file.exists():
            try:
                current_file.unlink()
            except Exception:
                pass

    def get_current_novel(self) -> Optional[NovelProject]:
        """获取当前活跃小说项目"""
        current_id = self.get_current_novel_id()
        if current_id:
            return self.get_novel(current_id)
        return None

    def novel_exists(self, novel_id: str) -> bool:
        """检查小说是否存在"""
        project = self.get_novel(novel_id)
        return project is not None and project.exists()

    def get_novel_count(self) -> int:
        """获取小说数量"""
        return len(self.list_novels())

    def search_novels(self, keyword: str) -> List[Dict]:
        """搜索小说"""
        all_novels = self.list_novels()
        keyword = keyword.lower()

        results = []
        for novel in all_novels:
            if (
                keyword in novel.get("name", "").lower()
                or keyword in novel.get("description", "").lower()
                or keyword in novel.get("novel_id", "").lower()
            ):
                results.append(novel)

        return results
