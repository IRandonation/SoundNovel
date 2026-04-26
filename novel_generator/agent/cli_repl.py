"""Agent REPL 主循环"""

import sys
from pathlib import Path
from typing import Optional

from novel_generator.cli.utils import print_success, print_info, print_warning, print_error
from novel_generator.config.config_manager import ConfigManager
from novel_generator.agent.intent.parser import IntentParser, UserIntent
from novel_generator.agent.memory.conversation import ConversationMemory


class AgentREPL:
    """Agent REPL 交互界面"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.config_manager = ConfigManager(str(self.project_root))
        self.intent_parser = IntentParser()
        self.memory = ConversationMemory(max_turns=50)
        self.running = False

        # 加载现有记忆
        self._load_memory()

    def _load_memory(self) -> None:
        """加载对话记忆"""
        memory_file = self.project_root / "05_script" / "agent_memory.json"
        if memory_file.exists():
            self.memory.load_from_file(str(memory_file))

    def _save_memory(self) -> None:
        """保存对话记忆"""
        memory_file = self.project_root / "05_script" / "agent_memory.json"
        memory_file.parent.mkdir(parents=True, exist_ok=True)
        self.memory.save_to_file(str(memory_file))

    def start(self) -> int:
        """启动 REPL 循环"""
        self.running = True
        self.display_welcome()

        try:
            while self.running:
                try:
                    # 读取用户输入
                    user_input = input("\n> ").strip()

                    if not user_input:
                        continue

                    # 处理命令
                    should_continue = self.process_command(user_input)
                    if not should_continue:
                        break

                except KeyboardInterrupt:
                    print("\n")
                    print_info("收到中断信号，使用 'exit' 或 'quit' 退出")
                    continue
                except EOFError:
                    print("\n")
                    break

        except Exception as e:
            print_error(f"发生错误: {e}")
            return 1

        finally:
            self._save_memory()
            print_info("已保存对话历史")

        return 0

    def display_welcome(self) -> None:
        """显示欢迎信息"""
        print("\n" + "=" * 50)
        print("🤖 SoundNovel Agent 模式")
        print("=" * 50)

        # 显示项目状态
        try:
            # 获取项目名
            project_name = self.config_manager.session_manager.state.project_name
            if project_name:
                print(f"当前项目：《{project_name}》")

            # 获取进度
            state = self.config_manager.session_manager.state.generation_state
            if state and state.last_draft_chapter > 0:
                print(f"已完成：{state.last_draft_chapter} 章")
            else:
                print("项目尚未开始")

        except Exception:
            print("项目状态：未初始化")

        print("\n你可以这样与我对话：")
        print("  生成第5章    - 生成指定章节")
        print("  查看状态     - 显示项目进度")
        print("  张三现在在哪 - 查询人物状态")
        print("  帮助         - 显示更多帮助")
        print("  退出         - 退出 Agent 模式")
        print("=" * 50)

    def process_command(self, user_input: str) -> bool:
        """处理用户命令，返回是否继续循环"""
        # 解析意图
        intent = self.intent_parser.parse(user_input)

        # 根据意图执行
        if intent.action == "exit":
            self._handle_exit()
            return False

        elif intent.action == "help":
            response = self._handle_help()

        elif intent.action == "status":
            response = self._handle_status()

        elif intent.action == "generate":
            chapter_num = self.intent_parser.extract_chapter_number(user_input)
            response = self._handle_generate(chapter_num)

        elif intent.action == "query_character":
            character_name = self.intent_parser.extract_character_name(user_input)
            response = self._handle_query_character(character_name)

        elif intent.action == "unknown":
            response = "抱歉，我不理解这个指令。输入 '帮助' 查看可用命令。"

        else:
            response = f"【{intent.action}】功能正在开发中..."

        # 记录对话
        self.memory.add_turn(user_input, response, intent.action)

        print(f"\nAgent: {response}")
        return True

    def _handle_exit(self) -> None:
        """处理退出"""
        print("\n👋 再见！已自动保存对话历史。")
        print("提示：使用 `python soundnovel.py cli agent` 继续对话")

    def _handle_help(self) -> str:
        """处理帮助请求"""
        help_text = """
可用命令：

【生成类】
  生成第N章    - 生成指定章节内容
  扩写第N章    - 扩写已有章节
  修改第N章    - 修改章节内容

【查询类】
  查看状态     - 显示项目整体进度
  XXX现在在哪  - 查询人物当前状态
  XXX怎么样    - 查询人物详细信息
  伏笔状态     - 查看伏笔追踪情况

【规划类】
  规划大纲     - 规划故事大纲
  情节建议     - 获取情节发展建议

【其他】
  帮助         - 显示此帮助信息
  退出/quit    - 退出 Agent 模式

提示：
- 章节号可以直接输入数字，如 "生成5" 等同于 "生成第5章"
- 人物名直接输入，如 "张三现在在哪"
"""
        return help_text.strip()

    def _handle_status(self) -> str:
        """处理状态查询"""
        try:
            # 使用 ConfigManager 获取状态
            state = self.config_manager.session_manager.state.generation_state
            project_name = self.config_manager.session_manager.state.project_name

            if not state or state.last_draft_chapter == 0:
                return "项目尚未开始生成章节。使用 '生成第1章' 开始创作。"

            status = f"""
项目：《{project_name or '未命名'}》
━━━━━━━━━━━━━━━━━━━━
已完成：{state.last_draft_chapter} 章
当前批次：{state.last_outline_chapter}
大纲文件：{state.outline_file or '未设置'}
最后更新：{state.last_session_at or '未知'}

使用 '生成第{state.last_draft_chapter + 1}章' 继续创作。
""".strip()
            return status

        except Exception as e:
            return f"获取状态失败: {e}"

    def _handle_generate(self, chapter_num: Optional[int]) -> str:
        """处理生成请求"""
        if chapter_num is None:
            return "请指定章节号，例如：生成第5章"

        return f"📖 准备生成第{chapter_num}章...\n（此功能需要集成 ChapterExpander，将在后续版本实现）"

    def _handle_query_character(self, character_name: Optional[str]) -> str:
        """处理人物查询"""
        if not character_name:
            return "请指定人物名，例如：张三现在在哪"

        return f"🔍 正在查询「{character_name}」的状态...\n（此功能需要集成 CharacterTracker，将在后续版本实现）"


def run_agent_repl(project_root: str = ".") -> int:
    """运行 Agent REPL"""
    repl = AgentREPL(project_root)
    return repl.start()
